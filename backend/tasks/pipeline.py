# =============================================================================
# BRKOPS-2585 Pipeline Tasks
# Background job tasks for pipeline processing
# =============================================================================

import asyncio
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

    intent = await llm_service.parse_intent(job.input_text, intent_prompt)

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

    logger.info("Intent parsed and validated", job_id=str(job.id), action=intent.get("action"))

    return intent


async def process_config_generation(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Generate configuration from intent."""
    logger.info("Generating config", job_id=str(job.id))

    llm_service = LLMService(
        demo_mode=demo_mode,
        provider=getattr(use_case, 'llm_provider', None) if use_case else None,
        model=getattr(use_case, 'llm_model', None) if use_case else None,
    )

    # Get previous stage data
    intent = job.stages_data.get("intent_parsing", {}).get("data", {})

    # Get config prompt from use case or default
    config_prompt = use_case.config_prompt if use_case else """
    Generate Cisco IOS configuration for the following intent:

    Intent: {{intent}}

    Respond in JSON format with:
    - commands: List of configuration commands
    - rollback_commands: List of rollback commands
    - explanation: Brief explanation
    """

    config = await llm_service.generate_config(intent, config_prompt)

    logger.info("Config generated", job_id=str(job.id), command_count=len(config.get("commands", [])))

    return config


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

    advice = await llm_service.generate_advice(intent, config)

    logger.info(
        "AI advice generated",
        job_id=str(job.id),
        recommendation=advice.get("recommendation"),
        risk_level=advice.get("risk_level"),
    )

    return advice


async def process_cml_deployment(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Deploy configuration to CML."""
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

        # Find target lab
        lab_id = use_case.cml_target_lab if use_case else None

        if not lab_id:
            # Get first available lab
            labs = await client.get_labs()
            if labs:
                lab_id = labs[0].get("id")

        if not lab_id:
            return {"deployed": False, "error": "No lab available"}

        # Find target device
        target_devices = intent.get("target_devices", [])
        if not target_devices:
            return {"deployed": False, "error": "No target devices specified"}

        device_label = target_devices[0]
        node = await client.find_node_by_label(lab_id, device_label)

        if not node:
            return {"deployed": False, "error": f"Device {device_label} not found in lab"}

        # Apply configuration
        commands = config.get("commands", [])
        config_text = "\n".join(commands)

        await client.apply_config(lab_id, node["id"], config_text)

        return {
            "deployed": True,
            "lab_id": lab_id,
            "node_id": node["id"],
            "device": device_label,
            "commands_applied": len(commands),
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

    Collects post-deployment state and compares with baseline to determine
    if the deployment was successful. The diff helps AI validation assess
    the change impact.
    """
    logger.info("Monitoring convergence", job_id=str(job.id))

    # Get baseline data from previous stage
    baseline_stage = job.stages_data.get("baseline_collection", {}).get("data", {})
    baseline = baseline_stage.get("baseline", {})

    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    # Get deployment info
    deployment = job.stages_data.get("cml_deployment", {}).get("data", {})
    device_label = deployment.get("device", baseline_stage.get("device", "Router-1"))
    lab_id = deployment.get("lab_id", baseline_stage.get("lab_id"))

    # Get convergence wait time
    wait_seconds = use_case.convergence_wait_seconds if use_case else settings.pipeline_convergence_wait

    monitoring_data = {
        "wait_seconds": wait_seconds,
        "device": device_label,
        "checks": [],
        "ospf_neighbors": [],
        "interface_status": [],
        "routes": [],
        "errors": [],
        "baseline": baseline,
        "current": {},
        "diff": {},
    }

    if not cml_server or not lab_id:
        # No CML connection, just wait
        logger.warning("No CML server or lab_id, performing basic wait only")
        await asyncio.sleep(wait_seconds)
        monitoring_data["monitoring_complete"] = True
        monitoring_data["deployment_healthy"] = None  # Unknown without monitoring
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

            # Broadcast progress
            await manager.broadcast({
                "type": "monitoring.progress",
                "job_id": str(job.id),
                "elapsed": elapsed,
                "total": wait_seconds,
                "message": f"Monitoring convergence... {elapsed}/{wait_seconds}s",
            })

        # Collect post-deployment state
        logger.info("Collecting post-deployment network state", device=device_label)
        current = await collect_network_state(client, lab_id, device_label)

        monitoring_data["current"] = current
        monitoring_data["ospf_neighbors"] = current.get("ospf_neighbors", [])
        monitoring_data["ospf_neighbor_count"] = len(current.get("ospf_neighbors", []))
        monitoring_data["interface_status"] = current.get("interfaces", [])
        monitoring_data["routes"] = current.get("routes", [])
        monitoring_data["errors"].extend(current.get("errors", []))

        # Calculate diff with baseline
        baseline_neighbors = len(baseline.get("ospf_neighbors", []))
        current_neighbors = len(current.get("ospf_neighbors", []))

        baseline_interfaces_up = count_interfaces_up(baseline.get("interfaces", []))
        current_interfaces_up = count_interfaces_up(current.get("interfaces", []))

        baseline_routes = len(baseline.get("routes", []))
        current_routes = len(current.get("routes", []))

        diff = {
            "ospf_neighbors": {
                "before": baseline_neighbors,
                "after": current_neighbors,
                "change": current_neighbors - baseline_neighbors,
            },
            "interfaces_up": {
                "before": baseline_interfaces_up,
                "after": current_interfaces_up,
                "change": current_interfaces_up - baseline_interfaces_up,
            },
            "routes": {
                "before": baseline_routes,
                "after": current_routes,
                "change": current_routes - baseline_routes,
            },
        }
        monitoring_data["diff"] = diff

        # Determine deployment health based on diff
        # Healthy if: neighbors didn't decrease, interfaces didn't go down, routes exist
        deployment_healthy = (
            diff["ospf_neighbors"]["after"] >= diff["ospf_neighbors"]["before"]
            and diff["interfaces_up"]["after"] >= diff["interfaces_up"]["before"]
            and diff["routes"]["after"] > 0
        )
        monitoring_data["deployment_healthy"] = deployment_healthy

        # Add checks
        monitoring_data["checks"].append({
            "name": "OSPF Neighbor Comparison",
            "status": "completed" if diff["ospf_neighbors"]["change"] >= 0 else "warning",
            "message": f"Neighbors: {baseline_neighbors} → {current_neighbors} ({diff['ospf_neighbors']['change']:+d})",
            "timestamp": datetime.utcnow().isoformat(),
        })

        monitoring_data["checks"].append({
            "name": "Interface Status Comparison",
            "status": "completed" if diff["interfaces_up"]["change"] >= 0 else "warning",
            "message": f"Interfaces up: {baseline_interfaces_up} → {current_interfaces_up} ({diff['interfaces_up']['change']:+d})",
            "timestamp": datetime.utcnow().isoformat(),
        })

        monitoring_data["checks"].append({
            "name": "OSPF Route Comparison",
            "status": "completed" if diff["routes"]["after"] > 0 else "error",
            "message": f"OSPF routes: {baseline_routes} → {current_routes} ({diff['routes']['change']:+d})",
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Final status
        monitoring_data["monitoring_complete"] = True
        monitoring_data["convergence_detected"] = current_neighbors > 0

        logger.info(
            "Monitoring complete with diff",
            job_id=str(job.id),
            deployment_healthy=deployment_healthy,
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

        # Determine query based on use case
        index = use_case.splunk_index if use_case else "netops"

        if "ospf" in job.use_case_name.lower():
            results = await client.search_ospf_events("-5m", device)
        elif "credential" in job.use_case_name.lower():
            results = await client.search_authentication_events("-5m", device)
        elif "security" in job.use_case_name.lower():
            results = await client.search_config_changes("-5m", device)
        else:
            # General query
            results = await client.get_device_logs(device, "-5m") if device else {}

        return {
            "queried": True,
            "query": results.get("query", ""),
            "result_count": results.get("result_count", 0),
            "results": results.get("results", [])[:50],  # Limit results
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
    context = {
        "job_id": str(job.id),
        "use_case": job.use_case_name,
        "severity": severity,
        "findings": str(validation.get("findings", [])),
        "recommendation": validation.get("recommendation", ""),
        **job.stages_data.get("intent_parsing", {}).get("data", {}),
        **job.stages_data.get("cml_deployment", {}).get("data", {}),
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
                "enabled": servicenow_enabled,
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
            "error": "No CML server configured",
            "collected": False,
        }

    # Get target device from intent parsing
    intent = job.stages_data.get("intent_parsing", {}).get("data", {})
    target_devices = intent.get("target_devices", [])
    device_label = target_devices[0] if target_devices else "Router-1"

    # Get lab ID from use case or find the first available lab
    lab_id = use_case.cml_target_lab if use_case else None

    try:
        client = CMLClient(cml_server.endpoint, cml_server.auth_config)

        if not lab_id:
            # Get first available lab
            labs = await client.get_labs()
            if labs:
                lab_id = labs[0].get("id")

        if not lab_id:
            return {
                "baseline": {},
                "error": "No lab available for baseline collection",
                "collected": False,
            }

        # Collect baseline state
        baseline = await collect_network_state(client, lab_id, device_label)
        baseline["lab_id"] = lab_id
        baseline["device"] = device_label

        logger.info(
            "Baseline collection complete",
            job_id=str(job.id),
            ospf_neighbors=len(baseline.get("ospf_neighbors", [])),
            interfaces=len(baseline.get("interfaces", [])),
            routes=len(baseline.get("routes", [])),
        )

        return {
            "baseline": baseline,
            "collected": True,
            "lab_id": lab_id,
            "device": device_label,
        }

    except Exception as e:
        logger.error("Baseline collection failed", job_id=str(job.id), error=str(e))
        return {
            "baseline": {},
            "error": str(e),
            "collected": False,
        }
