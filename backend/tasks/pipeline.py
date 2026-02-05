# =============================================================================
# BRKOPS-2585 Pipeline Tasks
# Background job tasks for pipeline processing
# =============================================================================

import asyncio
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from config import settings
from db.database import async_session
from db.models import PipelineJob, UseCase, JobStatus, PipelineStage
from services.llm_service import LLMService
from services.cml_client import CMLClient
from services.splunk_client import SplunkClient
from services.notification_service import NotificationService
from services.websocket_manager import manager

logger = structlog.get_logger()


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

        # Post-approval stages
        post_approval_stages = [
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
    Orchestrates all 10 stages of the pipeline.
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
            stages = [
                (PipelineStage.VOICE_INPUT, process_voice_input),
                (PipelineStage.INTENT_PARSING, process_intent_parsing),
                (PipelineStage.CONFIG_GENERATION, process_config_generation),
                (PipelineStage.AI_ADVICE, process_ai_advice),
                (PipelineStage.HUMAN_DECISION, process_human_decision),
                # Stages below only run if human approves
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

    llm_service = LLMService(demo_mode=demo_mode)

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

    logger.info("Intent parsed", job_id=str(job.id), action=intent.get("action"))

    return intent


async def process_config_generation(ctx: dict, job: PipelineJob, use_case: UseCase, db, demo_mode: bool = False) -> Dict[str, Any]:
    """Generate configuration from intent."""
    logger.info("Generating config", job_id=str(job.id))

    llm_service = LLMService(demo_mode=demo_mode)

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

    llm_service = LLMService(demo_mode=demo_mode)

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
    """Monitor network convergence after deployment - collect OSPF status and interface states."""
    logger.info("Monitoring convergence", job_id=str(job.id))

    # Get MCP server configuration
    from db.models import MCPServer, MCPServerType

    result = await db.execute(
        select(MCPServer).where(MCPServer.type == MCPServerType.CML, MCPServer.is_active == True)
    )
    cml_server = result.scalar_one_or_none()

    # Get deployment info
    deployment = job.stages_data.get("cml_deployment", {}).get("data", {})
    device_label = deployment.get("device", "Router-1")
    lab_id = deployment.get("lab_id")

    # Get convergence wait time
    wait_seconds = use_case.convergence_wait_seconds if use_case else settings.pipeline_convergence_wait

    monitoring_data = {
        "wait_seconds": wait_seconds,
        "device": device_label,
        "checks": [],
        "ospf_neighbors": [],
        "interface_status": [],
        "errors": [],
    }

    if not cml_server or not lab_id:
        # No CML connection, just wait
        logger.warning("No CML server or lab_id, performing basic wait only")
        await asyncio.sleep(wait_seconds)
        monitoring_data["monitoring_complete"] = True
        monitoring_data["checks"].append({
            "name": "Convergence Wait",
            "status": "completed",
            "message": f"Waited {wait_seconds}s for convergence (no CML monitoring available)"
        })
        return monitoring_data

    try:
        client = CMLClient(cml_server.endpoint, cml_server.auth_config)

        # Initial OSPF check
        logger.info("Collecting initial OSPF neighbor status", device=device_label)
        try:
            ospf_output_before = await client.run_command(lab_id, device_label, "show ip ospf neighbor")
            monitoring_data["checks"].append({
                "name": "Initial OSPF Check",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            ospf_output_before = f"Error: {str(e)}"
            monitoring_data["errors"].append(f"Initial OSPF check failed: {str(e)}")

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

        # Post-convergence OSPF check
        logger.info("Collecting post-convergence OSPF neighbor status", device=device_label)
        try:
            ospf_output_after = await client.run_command(lab_id, device_label, "show ip ospf neighbor")

            # Parse OSPF neighbors
            neighbors = []
            for line in ospf_output_after.split('\n'):
                if 'FULL' in line or 'TWO-WAY' in line or '2WAY' in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        neighbors.append({
                            "neighbor_id": parts[0],
                            "state": parts[2] if len(parts) > 2 else "UNKNOWN",
                            "interface": parts[-1] if parts else "Unknown",
                        })

            monitoring_data["ospf_neighbors"] = neighbors
            monitoring_data["ospf_neighbor_count"] = len(neighbors)
            monitoring_data["checks"].append({
                "name": "OSPF Neighbor Verification",
                "status": "completed" if neighbors else "warning",
                "message": f"Found {len(neighbors)} OSPF neighbor(s)",
                "timestamp": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            ospf_output_after = f"Error: {str(e)}"
            monitoring_data["errors"].append(f"Post-convergence OSPF check failed: {str(e)}")

        # Interface status check
        logger.info("Checking interface status", device=device_label)
        try:
            interface_output = await client.run_command(lab_id, device_label, "show ip interface brief")

            interfaces = []
            for line in interface_output.split('\n'):
                if 'GigabitEthernet' in line or 'Loopback' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        interfaces.append({
                            "interface": parts[0],
                            "ip_address": parts[1],
                            "status": parts[4] if len(parts) > 4 else "unknown",
                            "protocol": parts[5] if len(parts) > 5 else "unknown",
                        })

            monitoring_data["interface_status"] = interfaces
            up_count = sum(1 for i in interfaces if i.get("status") == "up")
            monitoring_data["checks"].append({
                "name": "Interface Status Check",
                "status": "completed",
                "message": f"{up_count}/{len(interfaces)} interfaces up",
                "timestamp": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            monitoring_data["errors"].append(f"Interface check failed: {str(e)}")

        # Final status
        monitoring_data["monitoring_complete"] = True
        monitoring_data["convergence_detected"] = len(monitoring_data.get("ospf_neighbors", [])) > 0

        logger.info(
            "Monitoring complete",
            job_id=str(job.id),
            ospf_neighbors=len(monitoring_data.get("ospf_neighbors", [])),
            errors=len(monitoring_data.get("errors", [])),
        )

    except Exception as e:
        logger.error("Monitoring failed", job_id=str(job.id), error=str(e))
        monitoring_data["errors"].append(f"Monitoring failed: {str(e)}")
        monitoring_data["monitoring_complete"] = True

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
        index = use_case.splunk_index if use_case else "network"

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
    splunk_results = job.stages_data.get("splunk_analysis", {}).get("data", {})

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

    llm_service = LLMService(demo_mode=demo_mode)

    # Get validation/analysis prompt
    validation_prompt = use_case.analysis_prompt if use_case else """
    Validate the following deployment results:

    Configuration: {{config}}
    Deployment Result: {{deployment_result}}
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
    )

    logger.info(
        "Validation complete",
        job_id=str(job.id),
        status=validation.get("validation_status"),
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

    # Create ServiceNow ticket for warnings/critical
    if severity in ["WARNING", "CRITICAL"]:
        snow_template = template.get("servicenow", {})
        if snow_template:
            result = await notification_service.create_servicenow_ticket(
                short_description=snow_template.get("short_description", f"Network Alert - {job.use_case_name}"),
                description=f"Analysis Results:\n{validation}",
                category=snow_template.get("category", "Network"),
                priority="2" if severity == "CRITICAL" else "3",
            )
            results.append({"channel": "servicenow", "success": result.get("success")})

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
