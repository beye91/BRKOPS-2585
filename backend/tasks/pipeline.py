# =============================================================================
# BRKOPS-2585 Pipeline Tasks
# Background job tasks for pipeline processing
# =============================================================================

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import async_session
from db.models import PipelineJob, UseCase, JobStatus, PipelineStage, MCPServer, MCPServerType
from services.llm_service import LLMService
from services.cml_client import CMLClient
from services.splunk_client import SplunkClient
from services.notification_service import NotificationService
from services.websocket_manager import manager

logger = structlog.get_logger()


# =============================================================================
# MCP Validation Helper
# =============================================================================
async def validate_mcp_servers(db: AsyncSession) -> Tuple[bool, List[str]]:
    """
    Validate that CML MCP server is available before pipeline starts.

    Returns:
        Tuple of (cml_ok, errors_list)
    """
    errors = []
    cml_ok = False

    # Check CML server
    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    if cml_server:
        try:
            client = CMLClient(cml_server.endpoint, cml_server.auth_config)
            tools = await client.list_tools()
            cml_ok = len(tools) > 0
            if not cml_ok:
                errors.append("CML MCP server returned no tools")
        except Exception as e:
            errors.append(f"CML connection failed: {str(e)}")
    else:
        errors.append("No active CML MCP server configured")

    return cml_ok, errors


# =============================================================================
# Lab Resolution Helper
# =============================================================================
async def get_target_lab_id(job: PipelineJob, use_case: Optional[UseCase], client: CMLClient) -> Optional[str]:
    """
    Resolve lab ID with precedence:
    1. User selection (job.selected_lab_id) - HIGHEST
    2. Use case default (use_case.cml_target_lab)
    3. First available lab (fallback)

    Args:
        job: Pipeline job with optional selected_lab_id
        use_case: Use case with optional cml_target_lab
        client: CML client instance

    Returns:
        Lab ID string or None if no labs available
    """
    # Priority 1: User selection
    if job.selected_lab_id:
        logger.info("Using user-selected lab", lab_id=job.selected_lab_id, job_id=str(job.id))
        return job.selected_lab_id

    # Priority 2: Use case default
    if use_case and use_case.cml_target_lab:
        logger.info("Using use case default lab", lab_id=use_case.cml_target_lab, job_id=str(job.id))
        return use_case.cml_target_lab

    # Priority 3: First available lab
    try:
        labs = await client.get_labs()
        if labs:
            first_lab_id = labs[0].get("id")
            logger.info("Using first available lab", lab_id=first_lab_id, job_id=str(job.id))
            return first_lab_id
    except Exception as e:
        logger.error("Failed to fetch labs", error=str(e), job_id=str(job.id))

    return None


# =============================================================================
# Lab Context Builder for LLM
# =============================================================================
async def build_lab_context(
    client: CMLClient,
    lab_id: str,
    target_devices: List[str],
    max_chars: int = 12000,
) -> Dict[str, Any]:
    """
    Build comprehensive lab context for LLM.

    Fetches configs from ALL devices in the lab to give the LLM
    full topology awareness, not just the single target device.

    Args:
        client: CML client instance
        lab_id: Lab UUID
        target_devices: List of target device labels
        max_chars: Maximum total characters (truncate if exceeded)

    Returns:
        Dictionary with lab topology and all device configs
    """
    try:
        nodes = await client.get_nodes(lab_id)

        # Fetch ALL device configs in parallel
        async def _fetch_config(label: str) -> Tuple[str, str]:
            try:
                cfg = await client.run_command(lab_id, label, "show running-config")
                return label, cfg
            except Exception as e:
                logger.warning("Failed to fetch config", device=label, error=str(e))
                return label, ""

        tasks = [_fetch_config(n.get("label")) for n in nodes if n.get("label")]
        results = await asyncio.gather(*tasks)
        device_configs = {label: cfg for label, cfg in results}

        # Smart truncation if total exceeds max_chars
        total_chars = sum(len(c) for c in device_configs.values())
        if total_chars > max_chars:
            # Truncate each config proportionally
            chars_per_device = max_chars // len(device_configs)
            device_configs = {
                label: cfg[:chars_per_device] if len(cfg) > chars_per_device else cfg
                for label, cfg in device_configs.items()
            }

        return {
            "target_devices": target_devices,
            "lab_topology": {
                "total_devices": len(nodes),
                "devices": [
                    {
                        "label": n.get("label"),
                        "type": n.get("node_definition"),
                        "state": n.get("state"),
                    }
                    for n in nodes
                ]
            },
            "device_configs": device_configs,
        }
    except Exception as e:
        logger.error("Failed to build lab context", error=str(e), lab_id=lab_id)
        return {
            "target_devices": target_devices,
            "lab_topology": {"total_devices": 0, "devices": []},
            "device_configs": {},
            "error": str(e),
        }


# =============================================================================
# Network State Collection Helper
# =============================================================================
async def collect_network_state(
    client: CMLClient,
    lab_id: str,
    device_label: str,
) -> Dict[str, Any]:
    """
    Collect current network state from a device (OSPF neighbors, interfaces, routes).

    Args:
        client: CML client instance
        lab_id: Lab UUID
        device_label: Device label/name

    Returns:
        Dictionary with ospf_neighbors, interfaces, routes, and errors
    """
    state = {
        "ospf_neighbors": [],
        "interfaces": [],
        "routes": [],
        "collected_at": datetime.utcnow().isoformat(),
        "errors": [],
    }

    # Collect OSPF neighbors
    try:
        ospf_output = await client.run_command(lab_id, device_label, "show ip ospf neighbor")
        neighbors = []
        for line in ospf_output.split('\n'):
            if 'FULL' in line or 'TWO-WAY' in line or '2WAY' in line:
                parts = line.split()
                if len(parts) >= 6:
                    neighbors.append({
                        "neighbor_id": parts[0],
                        "state": parts[2] if len(parts) > 2 else "UNKNOWN",
                        "interface": parts[-1] if parts else "Unknown",
                    })
        state["ospf_neighbors"] = neighbors
    except Exception as e:
        state["errors"].append(f"OSPF collection failed: {str(e)}")

    # Collect interface status
    try:
        intf_output = await client.run_command(lab_id, device_label, "show ip interface brief")
        interfaces = []
        for line in intf_output.split('\n'):
            if 'GigabitEthernet' in line or 'Loopback' in line:
                parts = line.split()
                if len(parts) >= 5:
                    interfaces.append({
                        "interface": parts[0],
                        "ip_address": parts[1],
                        "status": parts[4] if len(parts) > 4 else "unknown",
                        "protocol": parts[5] if len(parts) > 5 else "unknown",
                    })
        state["interfaces"] = interfaces
    except Exception as e:
        state["errors"].append(f"Interface collection failed: {str(e)}")

    # Collect OSPF routes
    try:
        routes_output = await client.run_command(lab_id, device_label, "show ip route ospf")
        routes = []
        for line in routes_output.split('\n'):
            if line.strip().startswith('O ') or line.strip().startswith('O*'):
                routes.append(line.strip())
        state["routes"] = routes
    except Exception as e:
        state["errors"].append(f"Route collection failed: {str(e)}")

    # Collect CPU utilization
    try:
        import re as _re
        cpu_output = await client.run_command(
            lab_id, device_label, "show processes cpu | include CPU utilization"
        )
        cpu_match = _re.search(r'five seconds:\s*(\d+)%', cpu_output)
        state["cpu_utilization_percent"] = int(cpu_match.group(1)) if cpu_match else None
    except Exception as e:
        state["errors"].append(f"CPU collection failed: {str(e)}")

    # Collect memory utilization
    try:
        import re as _re
        mem_output = await client.run_command(
            lab_id, device_label, "show processes memory | include Processor"
        )
        mem_match = _re.search(r'Total:\s*(\d+)\s*Used:\s*(\d+)', mem_output)
        if mem_match:
            total = int(mem_match.group(1))
            used = int(mem_match.group(2))
            state["memory_utilization_percent"] = round(used / total * 100, 1) if total > 0 else None
    except Exception as e:
        state["errors"].append(f"Memory collection failed: {str(e)}")

    return state


def count_interfaces_up(interfaces: List[Dict[str, Any]]) -> int:
    """Count number of interfaces with status 'up'."""
    return sum(1 for i in interfaces if i.get("status", "").lower() == "up")


async def continue_pipeline_after_approval(ctx: dict, job_id: str, demo_mode: bool = True):
    """
    Continue pipeline processing after human approval.
    Runs stages 6-10: CML_DEPLOYMENT, MONITORING, SPLUNK_ANALYSIS, AI_VALIDATION, NOTIFICATIONS
    """
    logger.info("Continuing pipeline after approval", job_id=job_id, demo_mode=demo_mode)

    async with async_session() as db:
        # Get job
        result = await db.execute(select(PipelineJob).where(PipelineJob.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        # Verify job is in the right state
        if job.current_stage != PipelineStage.HUMAN_DECISION:
            logger.error("Job not at human_decision stage", job_id=job_id, stage=job.current_stage)
            return

        # Get use case
        use_case = None
        if job.use_case_id:
            result = await db.execute(select(UseCase).where(UseCase.id == job.use_case_id))
            use_case = result.scalar_one_or_none()

        # Update job status
        job.status = JobStatus.RUNNING
        await db.commit()

        # Broadcast resume
        await manager.broadcast({
            "type": "operation.resumed",
            "job_id": job_id,
            "message": "Continuing after approval",
        })

        # Post-approval stages (baseline_collection runs BEFORE deployment)
        post_approval_stages = [
            (PipelineStage.BASELINE_COLLECTION, process_baseline_collection),
            (PipelineStage.CML_DEPLOYMENT, process_cml_deployment),
            (PipelineStage.MONITORING, process_monitoring),
            (PipelineStage.SPLUNK_ANALYSIS, process_splunk_analysis),
            (PipelineStage.AI_VALIDATION, process_ai_validation),
            (PipelineStage.NOTIFICATIONS, process_notifications),
        ]

        try:
            for stage, processor in post_approval_stages:
                # Check if job was cancelled
                await db.refresh(job)
                if job.status == JobStatus.CANCELLED:
                    logger.info("Job cancelled", job_id=job_id)
                    return

                # Update current stage
                job.current_stage = stage
                job.stages_data[stage.value] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
                flag_modified(job, 'stages_data')
                await db.commit()

                # Broadcast stage change
                await manager.send_stage_update(
                    job_id=job_id,
                    stage=stage.value,
                    status="running",
                    message=f"Processing {stage.value.replace('_', ' ')}...",
                )

                # Process stage
                try:
                    stage_result = await processor(ctx, job, use_case, db, demo_mode=demo_mode)

                    # Update stage data
                    job.stages_data[stage.value] = {
                        "status": "completed",
                        "data": stage_result,
                        "started_at": job.stages_data[stage.value].get("started_at"),
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    flag_modified(job, 'stages_data')
                    await db.commit()

                    # Broadcast completion
                    await manager.send_stage_update(
                        job_id=job_id,
                        stage=stage.value,
                        status="completed",
                        data=stage_result,
                    )

                except Exception as e:
                    logger.error(f"Stage {stage.value} failed", job_id=job_id, error=str(e))

                    job.stages_data[stage.value] = {
                        "status": "failed",
                        "error": str(e),
                        "started_at": job.stages_data[stage.value].get("started_at"),
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    flag_modified(job, 'stages_data')
                    job.status = JobStatus.FAILED
                    job.error_message = f"Stage {stage.value} failed: {str(e)}"
                    await db.commit()

                    # Broadcast error
                    await manager.broadcast({
                        "type": "operation.error",
                        "job_id": job_id,
                        "stage": stage.value,
                        "error": str(e),
                    })
                    return

                # Demo mode: pause after each stage
                if demo_mode:
                    job.status = JobStatus.PAUSED
                    await db.commit()

                    await manager.broadcast({
                        "type": "operation.paused",
                        "job_id": job_id,
                        "stage": stage.value,
                        "message": "Waiting for manual advancement",
                    })

                    await asyncio.sleep(1)
                    job.status = JobStatus.RUNNING
                    await db.commit()

            # Job completed successfully
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            await db.commit()

            await manager.broadcast({
                "type": "operation.completed",
                "job_id": job_id,
            })

        except Exception as e:
            logger.error("Pipeline continuation failed", job_id=job_id, error=str(e))
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await db.commit()

            await manager.broadcast({
                "type": "operation.error",
                "job_id": job_id,
                "error": str(e),
            })


async def process_pipeline_job(ctx: dict, job_id: str, demo_mode: bool = True):
    """
    Main pipeline job processor.
    Orchestrates all 11 stages of the pipeline.
    Pauses at HUMAN_DECISION stage for approval before deployment.
    """
    logger.info("Processing pipeline job", job_id=job_id, demo_mode=demo_mode)

    async with async_session() as db:
        # Get job
        result = await db.execute(select(PipelineJob).where(PipelineJob.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        # Validate MCP servers before starting pipeline
        cml_ok, mcp_errors = await validate_mcp_servers(db)
        if not cml_ok:
            error_msg = f"CML MCP unavailable: {'; '.join(mcp_errors)}"
            logger.error("MCP validation failed", job_id=job_id, errors=mcp_errors)
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            await db.commit()

            await manager.broadcast({
                "type": "operation.error",
                "job_id": job_id,
                "error": error_msg,
            })
            return

        # Get use case
        use_case = None
        if job.use_case_id:
            result = await db.execute(select(UseCase).where(UseCase.id == job.use_case_id))
            use_case = result.scalar_one_or_none()

        # Update job status
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        await db.commit()

        # Broadcast start
        await manager.broadcast({
            "type": "operation.started",
            "job_id": job_id,
            "use_case": job.use_case_name,
        })

        try:
            # Process each stage in correct order
            # Human decision now happens BEFORE deployment!
            # Stages after human_decision only run via continue_pipeline_after_approval
            stages = [
                (PipelineStage.VOICE_INPUT, process_voice_input),
                (PipelineStage.INTENT_PARSING, process_intent_parsing),
                (PipelineStage.CONFIG_GENERATION, process_config_generation),
                (PipelineStage.AI_ADVICE, process_ai_advice),
                (PipelineStage.HUMAN_DECISION, process_human_decision),
                # Stages below only run if human approves (via continue_pipeline_after_approval)
                (PipelineStage.BASELINE_COLLECTION, process_baseline_collection),
                (PipelineStage.CML_DEPLOYMENT, process_cml_deployment),
                (PipelineStage.MONITORING, process_monitoring),
                (PipelineStage.SPLUNK_ANALYSIS, process_splunk_analysis),
                (PipelineStage.AI_VALIDATION, process_ai_validation),
                (PipelineStage.NOTIFICATIONS, process_notifications),
            ]

            for stage, processor in stages:
                # Check if job was cancelled
                await db.refresh(job)
                if job.status == JobStatus.CANCELLED:
                    logger.info("Job cancelled", job_id=job_id)
                    return

                # Update current stage
                job.current_stage = stage
                job.stages_data[stage.value] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
                flag_modified(job, 'stages_data')
                await db.commit()

                # Broadcast stage change
                await manager.send_stage_update(
                    job_id=job_id,
                    stage=stage.value,
                    status="running",
                    message=f"Processing {stage.value.replace('_', ' ')}...",
                )

                # Process stage
                try:
                    stage_result = await processor(ctx, job, use_case, db, demo_mode=demo_mode)

                    # Check if stage result indicates failure
                    stage_failed = False
                    error_message = None
                    if isinstance(stage_result, dict):
                        # Check common failure indicators
                        if stage_result.get("deployed") is False:
                            stage_failed = True
                            error_message = stage_result.get("error", "Deployment failed")
                        elif stage_result.get("success") is False:
                            stage_failed = True
                            error_message = stage_result.get("error", "Stage failed")
                        elif stage_result.get("error") and not stage_result.get("deployed") and not stage_result.get("success"):
                            stage_failed = True
                            error_message = stage_result.get("error")

                    if stage_failed:
                        raise Exception(error_message or f"Stage {stage.value} failed")

                    # Update stage data
                    job.stages_data[stage.value] = {
                        "status": "completed",
                        "data": stage_result,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    flag_modified(job, 'stages_data')
                    await db.commit()

                    # Broadcast completion
                    await manager.send_stage_update(
                        job_id=job_id,
                        stage=stage.value,
                        status="completed",
                        data=stage_result,
                    )

                except Exception as e:
                    logger.error(f"Stage {stage.value} failed", job_id=job_id, error=str(e))

                    job.stages_data[stage.value] = {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    flag_modified(job, 'stages_data')
                    job.status = JobStatus.FAILED
                    job.error_message = f"Stage {stage.value} failed: {str(e)}"
                    await db.commit()

                    # Broadcast error
                    await manager.broadcast({
                        "type": "operation.error",
                        "job_id": job_id,
                        "stage": stage.value,
                        "error": str(e),
                    })
                    return

                # Human decision stage: pause and wait for approval BEFORE deployment
                if stage == PipelineStage.HUMAN_DECISION:
                    job.status = JobStatus.PAUSED
                    await db.commit()

                    await manager.broadcast({
                        "type": "operation.awaiting_approval",
                        "job_id": job_id,
                        "message": "Awaiting human approval before deployment",
                    })

                    # Stop processing here - approve endpoint will resume pipeline
                    logger.info("Pipeline paused for human approval", job_id=job_id)
                    return

                # Demo mode: pause after each stage (except human_decision which pauses above)
                if demo_mode:
                    job.status = JobStatus.PAUSED
                    await db.commit()

                    await manager.broadcast({
                        "type": "operation.paused",
                        "job_id": job_id,
                        "stage": stage.value,
                        "message": "Waiting for manual advancement",
                    })

                    # Wait for resume (in production, this would be handled differently)
                    # For now, we continue after a short delay
                    await asyncio.sleep(1)
                    job.status = JobStatus.RUNNING
                    await db.commit()

            # Job completed successfully (after all stages including post-approval)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            await db.commit()

            await manager.broadcast({
                "type": "operation.completed",
                "job_id": job_id,
            })

        except Exception as e:
            logger.error("Pipeline job failed", job_id=job_id, error=str(e))
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await db.commit()

            await manager.broadcast({
                "type": "operation.error",
                "job_id": job_id,
                "error": str(e),
            })


async def process_voice_input(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Process voice input stage."""
    logger.info("Processing voice input", job_id=str(job.id))

    # Voice input is already processed (transcript in input_text)
    # This stage validates and prepares the input

    return {
        "transcript": job.input_text,
        "audio_url": job.input_audio_url,
        "processed": True,
    }


async def process_intent_parsing(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Parse intent from transcript using LLM."""
    logger.info("Parsing intent", job_id=str(job.id))

    llm_service = LLMService(
        demo_mode=demo_mode,
        provider=getattr(use_case, 'llm_provider', None) if use_case else None,
        model=getattr(use_case, 'llm_model', None) if use_case else None,
    )

    # Get intent prompt from use case or default
    intent_prompt = use_case.intent_prompt if use_case else """
    Analyze the following voice command and extract structured intent:

    Voice Command: {{input_text}}

    Respond in JSON format with:
    - action: The type of action requested
    - target_devices: List of target devices
    - parameters: Dictionary of parameters
    - confidence: Confidence score (0-100)
    """

    intent = await llm_service.parse_intent(job.input_text, intent_prompt, use_case=use_case)

    # Validate intent scope if use case is provided
    if use_case:
        from services.intent_validator import validate_intent_scope
        is_valid, error_msg = validate_intent_scope(intent, use_case)

        if not is_valid:
            logger.warning(
                "Intent validation failed",
                job_id=str(job.id),
                use_case=use_case.name,
                error=error_msg
            )
            raise ValueError(error_msg)

    # -------------------------------------------------------------------
    # Device Resolution: expand "all" or validate specific device names
    # against actual CML lab nodes
    # -------------------------------------------------------------------
    raw_targets = intent.get("target_devices", [])
    if raw_targets:
        try:
            from services.device_resolver import resolve_target_devices, is_all_keyword

            # Get CML client + lab_id (same pattern as process_cml_deployment)
            result = await db.execute(
                select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
            )
            cml_server = result.scalar_one_or_none()

            if cml_server:
                client = CMLClient(cml_server.endpoint, cml_server.auth_config)

                lab_id = use_case.cml_target_lab if use_case else None
                if not lab_id:
                    labs = await client.get_labs()
                    if labs:
                        lab_id = labs[0].get("id")

                if lab_id:
                    resolved, errors = await resolve_target_devices(raw_targets, client, lab_id)

                    if not resolved:
                        # Complete failure: no devices could be resolved
                        raise ValueError(
                            f"Could not resolve target devices: {'; '.join(errors)}"
                        )

                    # Store resolution metadata
                    intent["_device_resolution"] = {
                        "raw_targets": raw_targets,
                        "resolved": resolved,
                        "errors": errors,
                        "was_all_keyword": is_all_keyword(raw_targets),
                    }

                    # Replace target_devices with resolved list
                    intent["target_devices"] = resolved

                    if errors:
                        logger.warning(
                            "Partial device resolution",
                            job_id=str(job.id),
                            resolved=resolved,
                            errors=errors,
                        )
                    else:
                        logger.info(
                            "Device resolution complete",
                            job_id=str(job.id),
                            resolved=resolved,
                        )
                else:
                    logger.warning("No CML lab found for device resolution", job_id=str(job.id))
            else:
                logger.warning("No CML server for device resolution", job_id=str(job.id))

        except ValueError:
            raise  # Re-raise resolution failures
        except Exception as e:
            logger.warning(
                "Device resolution failed, proceeding with raw targets",
                job_id=str(job.id),
                error=str(e),
            )

    logger.info(
        "Intent parsed and validated",
        job_id=str(job.id),
        action=intent.get("action"),
        target_devices=intent.get("target_devices"),
    )

    return intent


async def process_config_generation(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Generate configuration from intent using real running configs from CML devices."""
    logger.info("Generating config", job_id=str(job.id))

    from services.config_builder import (
        parse_running_config,
        build_config_for_action,
    )

    intent = job.stages_data.get("intent_parsing", {}).get("data", {})
    target_devices = intent.get("target_devices", [])
    action = intent.get("action", "")
    params = intent.get("parameters", {})

    # Add OSPF config strategy from use case
    if use_case and hasattr(use_case, 'ospf_config_strategy'):
        params['config_strategy'] = use_case.ospf_config_strategy
    else:
        params.setdefault('config_strategy', 'dual')

    # --- Fetch running configs from CML ---
    running_configs = {}
    try:
        result = await db.execute(
            select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
        )
        cml_server = result.scalar_one_or_none()

        if cml_server and target_devices:
            client = CMLClient(cml_server.endpoint, cml_server.auth_config)
            lab_id = await get_target_lab_id(job, use_case, client)

            if lab_id:
                # Fetch running configs in parallel with retry logic
                async def _fetch(device_label: str) -> Tuple[str, str]:
                    max_retries = 3
                    retry_delay = 10  # seconds

                    for attempt in range(max_retries):
                        try:
                            output = await client.run_command(lab_id, device_label, "show running-config")
                            if output and len(output) > 100:  # Valid config should be substantial
                                logger.info("Successfully fetched running config", device=device_label, attempt=attempt+1)
                                return device_label, output
                            else:
                                logger.warning("Empty or invalid config received", device=device_label, attempt=attempt+1)
                        except Exception as e:
                            logger.warning(
                                "Failed to fetch running config",
                                device=device_label,
                                attempt=attempt+1,
                                max_retries=max_retries,
                                error=str(e)
                            )

                        if attempt < max_retries - 1:
                            logger.info("Retrying after delay", device=device_label, delay=retry_delay)
                            await asyncio.sleep(retry_delay)

                    logger.error("Failed to fetch running config after all retries", device=device_label)
                    return device_label, ""

                tasks = [_fetch(d) for d in target_devices]
                results = await asyncio.gather(*tasks)
                running_configs = {label: cfg for label, cfg in results}

                logger.info(
                    "Running configs fetched",
                    job_id=str(job.id),
                    devices=list(running_configs.keys()),
                    non_empty=sum(1 for v in running_configs.values() if v),
                )
    except Exception as e:
        logger.warning("CML running config fetch failed, proceeding without", error=str(e))

    # --- Build per-device configs using config_builder ---
    per_device_configs = {}

    if running_configs:
        for device_label in target_devices:
            raw_config = running_configs.get(device_label, "")
            if not raw_config:
                per_device_configs[device_label] = {
                    "commands": [],
                    "rollback_commands": [],
                    "warnings": [f"No running config available for {device_label}"],
                }
                continue

            parsed = parse_running_config(raw_config)

            # Registry dispatch - try registered builder first, then LLM fallback
            change = build_config_for_action(action, parsed, params)

            if change is None:
                # No registered builder -> LLM fallback with running config context
                llm_service = LLMService(
                    demo_mode=demo_mode,
                    provider=getattr(use_case, 'llm_provider', None) if use_case else None,
                    model=getattr(use_case, 'llm_model', None) if use_case else None,
                )
                config_prompt = use_case.config_prompt if use_case else "Generate Cisco IOS configuration.\n\nIntent: {{intent}}\nCurrent Config: {{current_config}}"
                prompt = config_prompt.replace("{{intent}}", json.dumps(intent))
                prompt = prompt.replace("{{current_config}}", raw_config[:8000])
                response = await llm_service.complete(prompt=prompt, json_response=True)
                result_data = json.loads(response)
                from services.config_builder import ConfigChangeResult
                change = ConfigChangeResult(
                    commands=result_data.get("commands", []),
                    rollback_commands=result_data.get("rollback_commands", []),
                    warnings=result_data.get("warnings", []),
                )

            # For credential rotation: reuse generated password across devices
            if action == "rotate_credentials" and not params.get("new_password"):
                for w in change.warnings:
                    if w.startswith("Generated password:"):
                        params["new_password"] = w.split(": ", 1)[1]
                        break

            per_device_configs[device_label] = {
                "commands": change.commands,
                "rollback_commands": change.rollback_commands,
                "warnings": change.warnings,
                "affected_interfaces": change.affected_interfaces,
                "ospf_process_id": change.ospf_process_id,
                "running_config_snapshot": raw_config[:5000],
                "hostname": parsed.hostname,
            }

    # --- Fallback to LLM-based config generation if no running configs ---
    if not per_device_configs:
        logger.warning("No running configs, falling back to LLM config generation", job_id=str(job.id))
        llm_service = LLMService(
            demo_mode=demo_mode,
            provider=getattr(use_case, 'llm_provider', None) if use_case else None,
            model=getattr(use_case, 'llm_model', None) if use_case else None,
        )
        config_prompt = use_case.config_prompt if use_case else """
        Generate Cisco IOS configuration for the following intent:

        Intent: {{intent}}

        Respond in JSON format with:
        - commands: List of configuration commands
        - rollback_commands: List of rollback commands
        - explanation: Brief explanation
        """
        config = await llm_service.generate_config(intent, config_prompt)
        logger.info("Config generated via LLM", job_id=str(job.id), command_count=len(config.get("commands", [])))
        return config

    # --- Build response with backward-compat flat fields + per_device_configs ---
    first_device = target_devices[0] if target_devices else None
    first_cfg = per_device_configs.get(first_device, {}) if first_device else {}

    # Determine risk level based on scope
    device_count = len(per_device_configs)
    risk_level = "high" if device_count > 2 else ("medium" if device_count > 1 else "low")

    # Build explanation from use case template (DB-driven)
    template = getattr(use_case, 'explanation_template', None) or 'Configuration change on {{device_count}} device(s)'
    explanation = template.replace("{{device_count}}", str(device_count))
    for k, v in params.items():
        explanation = explanation.replace(f"{{{{{k}}}}}", str(v))

    config_result = {
        "commands": first_cfg.get("commands", []),
        "rollback_commands": first_cfg.get("rollback_commands", []),
        "per_device_configs": per_device_configs,
        "target_devices": target_devices,
        "explanation": explanation,
        "risk_level": risk_level,
        "estimated_impact": getattr(use_case, 'impact_description', None) or "Minimal impact expected",
    }

    total_commands = sum(len(c.get("commands", [])) for c in per_device_configs.values())
    logger.info(
        "Config generated from running configs",
        job_id=str(job.id),
        devices=device_count,
        total_commands=total_commands,
    )

    return config_result


async def process_ai_advice(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Generate AI advice and risk assessment before human decision."""
    logger.info("Generating AI advice", job_id=str(job.id))

    llm_service = LLMService(
        demo_mode=demo_mode,
        provider=getattr(use_case, 'llm_provider', None) if use_case else None,
        model=getattr(use_case, 'llm_model', None) if use_case else None,
    )

    # Get data from previous stages
    intent = job.stages_data.get("intent_parsing", {}).get("data", {})
    config = job.stages_data.get("config_generation", {}).get("data", {})

    advice = await llm_service.generate_advice(intent, config, use_case=use_case)

    logger.info(
        "AI advice generated",
        job_id=str(job.id),
        recommendation=advice.get("recommendation"),
        risk_level=advice.get("risk_level"),
    )

    return advice


async def process_cml_deployment(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Deploy configuration to CML. Deploys to ALL target devices."""
    logger.info("Deploying to CML", job_id=str(job.id))

    # Get MCP server configuration
    from db.models import MCPServer, MCPServerType

    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    if not cml_server:
        return {
            "deployed": False,
            "error": "No active CML server configured",
            "simulated": True,
        }

    try:
        client = CMLClient(cml_server.endpoint, cml_server.auth_config)

        # Get config and intent from previous stages
        config = job.stages_data.get("config_generation", {}).get("data", {})
        intent = job.stages_data.get("intent_parsing", {}).get("data", {})

        # Find target lab with precedence: user selection > use case default > first available
        lab_id = await get_target_lab_id(job, use_case, client)

        if not lab_id:
            return {"deployed": False, "error": "No lab available"}

        # Get all target devices
        target_devices = intent.get("target_devices", [])
        if not target_devices:
            return {"deployed": False, "error": "No target devices specified"}

        # Get per-device configs (if available) or fall back to flat commands
        per_device_configs = config.get("per_device_configs", {})
        flat_commands = config.get("commands", [])

        # Deploy to ALL target devices with per-device commands
        device_results = {}
        deployed_devices = []
        failed_devices = []

        for device_label in target_devices:
            try:
                node = await client.find_node_by_label(lab_id, device_label)
                if not node:
                    device_results[device_label] = {
                        "deployed": False,
                        "error": f"Device {device_label} not found in lab",
                    }
                    failed_devices.append(device_label)
                    continue

                # Use per-device commands if available, else flat commands
                device_cfg = per_device_configs.get(device_label, {})
                device_commands = device_cfg.get("commands", flat_commands)
                config_text = "\n".join(device_commands)

                if not device_commands:
                    device_results[device_label] = {
                        "deployed": False,
                        "error": f"No commands for {device_label}",
                    }
                    failed_devices.append(device_label)
                    continue

                await client.apply_config(lab_id, node["id"], config_text)

                device_results[device_label] = {
                    "deployed": True,
                    "node_id": node["id"],
                    "commands_count": len(device_commands),
                }
                deployed_devices.append(device_label)

                logger.info(
                    "Config deployed to device",
                    device=device_label,
                    node_id=node["id"],
                    job_id=str(job.id),
                )

            except Exception as e:
                logger.error(
                    "Deployment failed for device",
                    device=device_label,
                    error=str(e),
                    job_id=str(job.id),
                )
                device_results[device_label] = {
                    "deployed": False,
                    "error": str(e),
                }
                failed_devices.append(device_label)

        all_deployed = len(failed_devices) == 0 and len(deployed_devices) > 0

        # Backward-compat: "device" and "node_id" point to first device
        first_device = target_devices[0]
        first_result = device_results.get(first_device, {})

        return {
            "deployed": all_deployed or len(deployed_devices) > 0,
            "all_deployed": all_deployed,
            "lab_id": lab_id,
            "node_id": first_result.get("node_id"),        # backward-compat
            "device": first_device,                          # backward-compat
            "devices": deployed_devices,                     # all deployed
            "failed_devices": failed_devices,
            "device_results": device_results,                # per-device detail
            "commands_applied": sum(
                r.get("commands_count", len(flat_commands))
                for r in device_results.values() if r.get("deployed")
            ),
        }

    except Exception as e:
        logger.error("CML deployment failed", error=str(e))
        return {
            "deployed": False,
            "error": str(e),
        }


async def process_monitoring(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """
    Monitor network convergence after deployment.

    Collects post-deployment state from ALL deployed devices and compares
    with baseline to determine if the deployment was successful.
    """
    logger.info("Monitoring convergence", job_id=str(job.id))

    # Get baseline data from previous stage
    baseline_stage = job.stages_data.get("baseline_collection", {}).get("data", {})
    baselines = baseline_stage.get("baselines", {})
    # Backward-compat fallback
    if not baselines and baseline_stage.get("baseline"):
        fallback_device = baseline_stage.get("device", "Router-1")
        baselines = {fallback_device: baseline_stage["baseline"]}

    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    # Get deployment info - use deployed device list
    deployment = job.stages_data.get("cml_deployment", {}).get("data", {})
    deployed_devices = deployment.get("devices", [])
    # Backward-compat fallback
    if not deployed_devices:
        fallback_device = deployment.get("device", baseline_stage.get("device", "Router-1"))
        deployed_devices = [fallback_device]

    lab_id = deployment.get("lab_id", baseline_stage.get("lab_id"))

    # Get convergence wait time
    wait_seconds = use_case.convergence_wait_seconds if use_case else settings.pipeline_convergence_wait

    monitoring_data = {
        "wait_seconds": wait_seconds,
        "device": deployed_devices[0] if deployed_devices else "Router-1",  # backward-compat
        "devices": deployed_devices,
        "checks": [],
        "ospf_neighbors": [],
        "interface_status": [],
        "routes": [],
        "errors": [],
        "baseline": baselines.get(deployed_devices[0], {}) if deployed_devices else {},  # backward-compat
        "current": {},
        "diff": {},
        "per_device": {},
    }

    if not cml_server or not lab_id:
        logger.warning("No CML server or lab_id, performing basic wait only")
        await asyncio.sleep(wait_seconds)
        monitoring_data["monitoring_complete"] = True
        monitoring_data["deployment_healthy"] = None
        monitoring_data["checks"].append({
            "name": "Convergence Wait",
            "status": "completed",
            "message": f"Waited {wait_seconds}s for convergence (no CML monitoring available)"
        })
        return monitoring_data

    try:
        client = CMLClient(cml_server.endpoint, cml_server.auth_config)

        # Wait for convergence (split into intervals for progress updates)
        interval = min(5, wait_seconds)
        elapsed = 0
        while elapsed < wait_seconds:
            await asyncio.sleep(interval)
            elapsed += interval

            await manager.broadcast({
                "type": "monitoring.progress",
                "job_id": str(job.id),
                "elapsed": elapsed,
                "total": wait_seconds,
                "message": f"Monitoring convergence... {elapsed}/{wait_seconds}s",
            })

        # Collect post-deployment state from ALL deployed devices
        per_device = {}
        agg_neighbors_change = 0
        agg_interfaces_change = 0
        agg_routes_change = 0
        agg_neighbors_before = 0
        agg_neighbors_after = 0
        agg_interfaces_before = 0
        agg_interfaces_after = 0
        agg_routes_before = 0
        agg_routes_after = 0
        all_healthy = True

        for device_label in deployed_devices:
            logger.info("Collecting post-deployment state", device=device_label)
            current = await collect_network_state(client, lab_id, device_label)
            device_baseline = baselines.get(device_label, {})

            # Calculate per-device diff
            b_neighbors = len(device_baseline.get("ospf_neighbors", []))
            c_neighbors = len(current.get("ospf_neighbors", []))
            b_intf_up = count_interfaces_up(device_baseline.get("interfaces", []))
            c_intf_up = count_interfaces_up(current.get("interfaces", []))
            b_routes = len(device_baseline.get("routes", []))
            c_routes = len(current.get("routes", []))

            device_diff = {
                "ospf_neighbors": {"before": b_neighbors, "after": c_neighbors, "change": c_neighbors - b_neighbors},
                "interfaces_up": {"before": b_intf_up, "after": c_intf_up, "change": c_intf_up - b_intf_up},
                "routes": {"before": b_routes, "after": c_routes, "change": c_routes - b_routes},
            }

            device_healthy = (
                c_neighbors >= b_neighbors
                and c_intf_up >= b_intf_up
                and c_routes > 0
            )
            if not device_healthy:
                all_healthy = False

            per_device[device_label] = {
                "baseline": device_baseline,
                "current": current,
                "diff": device_diff,
                "healthy": device_healthy,
            }

            # Aggregate totals
            agg_neighbors_before += b_neighbors
            agg_neighbors_after += c_neighbors
            agg_interfaces_before += b_intf_up
            agg_interfaces_after += c_intf_up
            agg_routes_before += b_routes
            agg_routes_after += c_routes

            monitoring_data["errors"].extend(current.get("errors", []))

        # Aggregate diff across all devices
        diff = {
            "ospf_neighbors": {
                "before": agg_neighbors_before,
                "after": agg_neighbors_after,
                "change": agg_neighbors_after - agg_neighbors_before,
            },
            "interfaces_up": {
                "before": agg_interfaces_before,
                "after": agg_interfaces_after,
                "change": agg_interfaces_after - agg_interfaces_before,
            },
            "routes": {
                "before": agg_routes_before,
                "after": agg_routes_after,
                "change": agg_routes_after - agg_routes_before,
            },
        }
        monitoring_data["diff"] = diff
        monitoring_data["per_device"] = per_device
        monitoring_data["deployment_healthy"] = all_healthy

        # Backward-compat: first device's data
        first_device = deployed_devices[0] if deployed_devices else None
        if first_device and first_device in per_device:
            first_current = per_device[first_device]["current"]
            monitoring_data["current"] = first_current
            monitoring_data["ospf_neighbors"] = first_current.get("ospf_neighbors", [])
            monitoring_data["ospf_neighbor_count"] = len(first_current.get("ospf_neighbors", []))
            monitoring_data["interface_status"] = first_current.get("interfaces", [])
            monitoring_data["routes"] = first_current.get("routes", [])

        # Add aggregate checks
        monitoring_data["checks"].append({
            "name": "OSPF Neighbor Comparison (All Devices)",
            "status": "completed" if diff["ospf_neighbors"]["change"] >= 0 else "warning",
            "message": f"Neighbors: {agg_neighbors_before} → {agg_neighbors_after} ({diff['ospf_neighbors']['change']:+d}) across {len(deployed_devices)} device(s)",
            "timestamp": datetime.utcnow().isoformat(),
        })

        monitoring_data["checks"].append({
            "name": "Interface Status Comparison (All Devices)",
            "status": "completed" if diff["interfaces_up"]["change"] >= 0 else "warning",
            "message": f"Interfaces up: {agg_interfaces_before} → {agg_interfaces_after} ({diff['interfaces_up']['change']:+d}) across {len(deployed_devices)} device(s)",
            "timestamp": datetime.utcnow().isoformat(),
        })

        monitoring_data["checks"].append({
            "name": "OSPF Route Comparison (All Devices)",
            "status": "completed" if diff["routes"]["after"] > 0 else "error",
            "message": f"OSPF routes: {agg_routes_before} → {agg_routes_after} ({diff['routes']['change']:+d}) across {len(deployed_devices)} device(s)",
            "timestamp": datetime.utcnow().isoformat(),
        })

        monitoring_data["monitoring_complete"] = True
        monitoring_data["convergence_detected"] = agg_neighbors_after > 0

        logger.info(
            "Monitoring complete with diff",
            job_id=str(job.id),
            deployment_healthy=all_healthy,
            devices_monitored=len(deployed_devices),
            neighbor_change=diff["ospf_neighbors"]["change"],
            interface_change=diff["interfaces_up"]["change"],
            route_change=diff["routes"]["change"],
        )

    except Exception as e:
        logger.error("Monitoring failed", job_id=str(job.id), error=str(e))
        monitoring_data["errors"].append(f"Monitoring failed: {str(e)}")
        monitoring_data["monitoring_complete"] = True
        monitoring_data["deployment_healthy"] = None

    return monitoring_data


def normalize_splunk_timestamp(timestamp_value: Any) -> str:
    """
    Normalize Splunk timestamp to ISO 8601 format.

    Handles:
    - Unix epoch (seconds): 1707123456
    - Unix epoch (milliseconds): 1707123456789
    - ISO 8601 strings: "2024-02-05T14:30:00Z"
    - Malformed values: Returns current time with warning

    Returns:
        ISO 8601 formatted timestamp string
    """
    from datetime import datetime, timezone

    # Handle None/empty
    if not timestamp_value:
        logger.warning("Empty timestamp, using current time")
        return datetime.now(timezone.utc).isoformat()

    # Try parsing as Unix epoch (seconds or milliseconds)
    try:
        num = float(timestamp_value)
        # Epoch seconds (10 digits)
        if 1e9 < num < 1e12:
            dt = datetime.fromtimestamp(num, tz=timezone.utc)
            return dt.isoformat()
        # Epoch milliseconds (13 digits)
        elif 1e12 < num < 1e15:
            dt = datetime.fromtimestamp(num / 1000, tz=timezone.utc)
            return dt.isoformat()
    except (ValueError, TypeError):
        pass

    # Try parsing as ISO string
    try:
        dt = datetime.fromisoformat(str(timestamp_value).replace('Z', '+00:00'))
        return dt.isoformat()
    except (ValueError, TypeError):
        pass

    # Fallback: log warning and return current time
    logger.warning("Malformed timestamp, using current time",
                   raw_value=str(timestamp_value))
    return datetime.now(timezone.utc).isoformat()


async def process_splunk_analysis(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Query Splunk for post-change logs."""
    logger.info("Querying Splunk", job_id=str(job.id))

    # Get MCP server configuration
    from db.models import MCPServer, MCPServerType

    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.SPLUNK, MCPServer.is_active == True)
    )
    splunk_server = result.scalar_one_or_none()

    if not splunk_server:
        return {
            "queried": False,
            "error": "No active Splunk server configured",
            "simulated": True,
            "results": [],
        }

    try:
        client = SplunkClient(splunk_server.endpoint, splunk_server.auth_config)

        # Get deployment info
        deployment = job.stages_data.get("cml_deployment", {}).get("data", {})
        device = deployment.get("device")

        # Determine query based on use case DB config (no more hardcoded branching)
        splunk_cfg = getattr(use_case, 'splunk_query_config', None) or {"query_type": "general"}
        query_type = splunk_cfg.get("query_type", "general")

        SPLUNK_DISPATCH = {
            "ospf_events": client.search_ospf_events,
            "authentication_events": client.search_authentication_events,
            "config_changes": client.search_config_changes,
        }
        query_fn = SPLUNK_DISPATCH.get(query_type)
        if query_fn:
            results = await query_fn("-5m", device)
        else:
            results = await client.get_device_logs(device, "-5m") if device else {}

        # Normalize timestamps for frontend display
        normalized_results = []
        for log_entry in results.get("results", [])[:50]:
            if "_time" in log_entry:
                log_entry["_time"] = normalize_splunk_timestamp(log_entry["_time"])
            normalized_results.append(log_entry)

        return {
            "queried": True,
            "query": results.get("query", ""),
            "result_count": results.get("result_count", 0),
            "results": normalized_results,
        }

    except Exception as e:
        logger.error("Splunk query failed", error=str(e))
        return {
            "queried": False,
            "error": str(e),
            "results": [],
        }


async def process_ai_validation(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Validate deployment results with AI (post-deployment analysis)."""
    logger.info("AI validation", job_id=str(job.id))

    # Get data from previous stages
    config = job.stages_data.get("config_generation", {}).get("data", {})
    deployment_result = job.stages_data.get("cml_deployment", {}).get("data", {})
    monitoring_result = job.stages_data.get("monitoring", {}).get("data", {})
    splunk_results = job.stages_data.get("splunk_analysis", {}).get("data", {})

    # Get diff data from monitoring
    diff = monitoring_result.get("diff", {})
    deployment_healthy = monitoring_result.get("deployment_healthy")

    # Check if Splunk data collection failed
    splunk_queried = splunk_results.get("queried", False)
    splunk_error = splunk_results.get("error")

    if not splunk_queried or splunk_error:
        # Return warning when Splunk data is unavailable
        logger.warning(
            "AI validation without Splunk data",
            job_id=str(job.id),
            splunk_error=splunk_error,
        )
        return {
            "validation_status": "WARNING",
            "overall_score": 50,
            "summary": "Cannot fully validate deployment - Splunk data unavailable",
            "findings": [
                {
                    "category": "Data Collection",
                    "status": "warning",
                    "message": f"Splunk query failed: {splunk_error or 'No data returned'}",
                    "severity": "warning"
                },
                {
                    "category": "Deployment Status",
                    "status": "ok" if deployment_result.get("deployed") else "error",
                    "message": "Configuration was applied to device" if deployment_result.get("deployed") else "Deployment failed",
                    "severity": "info" if deployment_result.get("deployed") else "error"
                }
            ],
            "deployment_verified": False,
            "recommendation": "Manual verification recommended - check Splunk connectivity and device logs",
            "recommendation_reason": "Automated validation requires Splunk log data to verify deployment success",
            "metrics": {
                "splunk_events_analyzed": 0,
                "data_collection_status": "failed"
            }
        }

    llm_service = LLMService(
        demo_mode=demo_mode,
        provider=getattr(use_case, 'llm_provider', None) if use_case else None,
        model=getattr(use_case, 'llm_model', None) if use_case else None,
    )

    # Get validation/analysis prompt
    validation_prompt = use_case.analysis_prompt if use_case else """
    Validate the following deployment results:

    Configuration: {{config}}
    Deployment Result: {{deployment_result}}
    Monitoring Diff: {{monitoring_diff}}
    Splunk Results: {{splunk_results}}
    Time Window: {{time_window}}

    Provide validation in JSON format with:
    - validation_status: PASSED, WARNING, or FAILED
    - findings: List of findings
    - recommendation: Recommended action
    - deployment_verified: Boolean
    """

    validation = await llm_service.validate_deployment(
        config=config,
        deployment_result=deployment_result,
        splunk_results=splunk_results,
        validation_prompt=validation_prompt,
        time_window="5 minutes",
        monitoring_diff=diff,
    )

    # Augment validation with diff-based assessment
    if deployment_healthy is not None:
        validation["deployment_healthy_from_diff"] = deployment_healthy
        if deployment_healthy and validation.get("validation_status") == "WARNING":
            # Diff shows healthy, might upgrade status
            validation["findings"].append({
                "category": "Network State",
                "status": "ok",
                "message": "Network diff shows stable or improved state after deployment",
                "severity": "info",
            })
        elif not deployment_healthy:
            # Diff shows issues
            validation["findings"].append({
                "category": "Network State",
                "status": "warning",
                "message": f"Network state degraded: OSPF neighbors {diff.get('ospf_neighbors', {}).get('change', 0):+d}, interfaces {diff.get('interfaces_up', {}).get('change', 0):+d}",
                "severity": "warning",
            })

    logger.info(
        "Validation complete",
        job_id=str(job.id),
        status=validation.get("validation_status"),
        deployment_healthy=deployment_healthy,
    )

    return validation


async def process_notifications(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Send notifications based on validation results."""
    logger.info("Sending notifications", job_id=str(job.id))

    notification_service = NotificationService()

    # Get validation results (renamed from ai_analysis)
    validation = job.stages_data.get("ai_validation", {}).get("data", {})
    # Determine severity from validation status
    validation_status = validation.get("validation_status", "PASSED")
    if validation_status == "FAILED":
        severity = "CRITICAL"
    elif validation_status == "WARNING":
        severity = "WARNING"
    else:
        severity = "INFO"

    # Get notification template
    template = use_case.notification_template if use_case else {}

    # Build context
    # Format findings as human-readable bullet list
    raw_findings = validation.get("findings", [])
    if raw_findings and isinstance(raw_findings, list):
        issues_text = "\n".join(
            f"- [{f.get('category', f.get('type', 'General'))}] {f.get('message', f.get('description', 'Unknown issue'))}"
            for f in raw_findings
            if isinstance(f, dict)
        )
    else:
        issues_text = "No specific issues identified"

    # Determine rollback guidance
    rollback_recommended = validation.get("rollback_recommended", False)
    if rollback_recommended or validation_status in ("FAILED", "ROLLBACK_REQUIRED"):
        rollback_action = "Rollback is recommended. Use the BRKOPS-2585 platform to initiate automatic rollback or contact the network team."
    else:
        rollback_action = ""

    # Derive 'devices' from target_devices (list from intent) or device (string from cml)
    intent_data = job.stages_data.get("intent_parsing", {}).get("data", {})
    cml_data = job.stages_data.get("cml_deployment", {}).get("data", {})
    target_devices = intent_data.get("target_devices", [])
    if isinstance(target_devices, list) and target_devices:
        devices_str = ", ".join(target_devices)
    elif cml_data.get("device"):
        devices_str = cml_data["device"]
    else:
        devices_str = "unknown device"

    context = {
        "job_id": str(job.id),
        "use_case": job.use_case_name,
        "severity": severity,
        "issues": issues_text,
        "findings": str(raw_findings),
        "recommendation": validation.get("recommendation", "Review deployment status manually"),
        "rollback_action": rollback_action,
        "summary": validation.get("summary", ""),
        **intent_data,
        **cml_data,
        "devices": devices_str,
    }

    results = []

    # Send WebEx notification if configured
    webex_template = template.get("webex", {})
    if webex_template:
        message_key = severity.lower() if severity.lower() in webex_template else "success"
        message = webex_template.get(message_key, "")

        # Substitute variables
        for key, value in context.items():
            message = message.replace("{{" + key + "}}", str(value))

        if message:
            result = await notification_service.send_webex(markdown=message)
            results.append({"channel": "webex", "success": result.get("success")})

    # Determine if we should create a ServiceNow ticket
    servicenow_enabled = use_case.servicenow_enabled if use_case else False
    rollback_recommended = validation.get("rollback_recommended", False)

    should_create_ticket = False
    ticket_reason = None

    if servicenow_enabled:
        if rollback_recommended:
            # Always create ticket if rollback recommended
            should_create_ticket = True
            ticket_reason = "Deployment requires rollback"
            severity = "CRITICAL"
        elif validation_status == "FAILED" or validation_status == "ROLLBACK_REQUIRED":
            should_create_ticket = True
            ticket_reason = "Validation failed - rollback required"
            severity = "CRITICAL"
        elif severity == "WARNING":
            # Create ticket for real warnings (not test breaks)
            should_create_ticket = True
            ticket_reason = "Deployment completed with warnings"
        # else: SUCCESS or intentional test - no ticket

    # Create ServiceNow ticket only if conditions met
    if should_create_ticket:
        snow_template = template.get("servicenow", {})
        if snow_template:
            result = await notification_service.create_servicenow_ticket(
                short_description=f"{snow_template.get('short_description', f'Network Alert - {job.use_case_name}')} - {ticket_reason}",
                description=f"Validation Status: {validation_status}\n\nReason: {ticket_reason}\n\nDetails:\n{validation}",
                category=snow_template.get("category", "Network"),
                priority="1" if severity == "CRITICAL" else "3",
            )
            results.append({
                "channel": "servicenow",
                "success": result.get("success"),
                "reason": ticket_reason,
                "error": result.get("error", ""),
                "enabled": servicenow_enabled,
                "ticket_number": result.get("response", {}).get("number", ""),
                "ticket_link": result.get("response", {}).get("link", ""),
            })

    return {
        "notifications_sent": len(results),
        "results": results,
    }


async def process_human_decision(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Prepare for human decision BEFORE deployment."""
    logger.info("Awaiting human decision before deployment", job_id=str(job.id))

    # Compile summary for human review (pre-deployment)
    # Note: This happens BEFORE CML deployment - human approves the plan, not the result
    summary = {
        "job_id": str(job.id),
        "use_case": job.use_case_name,
        "input": job.input_text,
        "intent": job.stages_data.get("intent_parsing", {}).get("data", {}),
        "config": job.stages_data.get("config_generation", {}).get("data", {}),
        "ai_advice": job.stages_data.get("ai_advice", {}).get("data", {}),
        "awaiting_approval": True,
        "message": "Please review the proposed configuration and AI advice before deployment.",
    }

    return summary


async def process_baseline_collection(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """
    Collect baseline network state BEFORE deployment.

    This stage runs after human approval but BEFORE CML deployment.
    It captures the current state of OSPF neighbors, interfaces, and routes
    so we can compare after deployment to determine if the change was successful.

    Collects from ALL target_devices, not just the first one.
    """
    logger.info("Collecting baseline network state", job_id=str(job.id))

    # Get MCP server configuration
    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    if not cml_server:
        logger.warning("No CML server configured for baseline collection", job_id=str(job.id))
        return {
            "baseline": {},
            "baselines": {},
            "error": "No CML server configured",
            "collected": False,
        }

    # Get target devices from intent parsing
    intent = job.stages_data.get("intent_parsing", {}).get("data", {})
    target_devices = intent.get("target_devices", [])
    if not target_devices:
        target_devices = ["Router-1"]

    # Get lab ID with precedence: user selection > use case default > first available
    try:
        client = CMLClient(cml_server.endpoint, cml_server.auth_config)
        lab_id = await get_target_lab_id(job, use_case, client)

        if not lab_id:
            return {
                "baseline": {},
                "baselines": {},
                "error": "No lab available for baseline collection",
                "collected": False,
            }

        # Collect baseline state from ALL target devices
        baselines = {}
        for device_label in target_devices:
            logger.info("Collecting baseline for device", device=device_label, job_id=str(job.id))
            baseline = await collect_network_state(client, lab_id, device_label)
            baseline["lab_id"] = lab_id
            baseline["device"] = device_label
            baselines[device_label] = baseline

        # Backward-compat: "baseline" and "device" point to first device
        first_device = target_devices[0]
        first_baseline = baselines.get(first_device, {})

        logger.info(
            "Baseline collection complete",
            job_id=str(job.id),
            devices=list(baselines.keys()),
            device_count=len(baselines),
        )

        return {
            "baseline": first_baseline,       # backward-compat: first device
            "baselines": baselines,            # all devices
            "collected": True,
            "lab_id": lab_id,
            "device": first_device,            # backward-compat
            "devices": target_devices,         # all device labels
        }

    except Exception as e:
        logger.error("Baseline collection failed", job_id=str(job.id), error=str(e))
        return {
            "baseline": {},
            "baselines": {},
            "error": str(e),
            "collected": False,
        }
