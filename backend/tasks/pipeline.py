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

from config import settings
from db.database import async_session
from db.models import PipelineJob, UseCase, JobStatus, PipelineStage
from services.llm_service import LLMService
from services.cml_client import CMLClient
from services.splunk_client import SplunkClient
from services.notification_service import NotificationService
from services.websocket_manager import manager

logger = structlog.get_logger()


async def process_pipeline_job(ctx: dict, job_id: str, demo_mode: bool = True):
    """
    Main pipeline job processor.
    Orchestrates all 9 stages of the pipeline.
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
            # Process each stage
            stages = [
                (PipelineStage.VOICE_INPUT, process_voice_input),
                (PipelineStage.INTENT_PARSING, process_intent_parsing),
                (PipelineStage.CONFIG_GENERATION, process_config_generation),
                (PipelineStage.CML_DEPLOYMENT, process_cml_deployment),
                (PipelineStage.MONITORING, process_monitoring),
                (PipelineStage.SPLUNK_ANALYSIS, process_splunk_analysis),
                (PipelineStage.AI_ANALYSIS, process_ai_analysis),
                (PipelineStage.NOTIFICATIONS, process_notifications),
                (PipelineStage.HUMAN_DECISION, process_human_decision),
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
                    stage_result = await processor(ctx, job, use_case, db)

                    # Update stage data
                    job.stages_data[stage.value] = {
                        "status": "completed",
                        "data": stage_result,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
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
                if demo_mode and stage != PipelineStage.HUMAN_DECISION:
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

            # Job completed successfully
            if job.current_stage == PipelineStage.HUMAN_DECISION:
                # Wait for human decision (handled by approve endpoint)
                job.status = JobStatus.PAUSED
                await db.commit()

                await manager.broadcast({
                    "type": "operation.awaiting_approval",
                    "job_id": job_id,
                })
            else:
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


async def process_voice_input(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Process voice input stage."""
    logger.info("Processing voice input", job_id=str(job.id))

    # Voice input is already processed (transcript in input_text)
    # This stage validates and prepares the input

    return {
        "transcript": job.input_text,
        "audio_url": job.input_audio_url,
        "processed": True,
    }


async def process_intent_parsing(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Parse intent from transcript using LLM."""
    logger.info("Parsing intent", job_id=str(job.id))

    llm_service = LLMService()

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


async def process_config_generation(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Generate configuration from intent."""
    logger.info("Generating config", job_id=str(job.id))

    llm_service = LLMService()

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


async def process_cml_deployment(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
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


async def process_monitoring(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Wait for network convergence and collect initial logs."""
    logger.info("Monitoring convergence", job_id=str(job.id))

    # Get convergence wait time
    wait_seconds = use_case.convergence_wait_seconds if use_case else settings.pipeline_convergence_wait

    # Wait for convergence
    await asyncio.sleep(wait_seconds)

    return {
        "wait_seconds": wait_seconds,
        "monitoring_complete": True,
    }


async def process_splunk_analysis(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
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


async def process_ai_analysis(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Analyze Splunk results with AI."""
    logger.info("AI analysis", job_id=str(job.id))

    llm_service = LLMService()

    # Get data from previous stages
    config = job.stages_data.get("config_generation", {}).get("data", {})
    splunk_results = job.stages_data.get("splunk_analysis", {}).get("data", {})

    # Get analysis prompt
    analysis_prompt = use_case.analysis_prompt if use_case else """
    Analyze the following Splunk results after configuration change:

    Configuration: {{config}}
    Splunk Results: {{splunk_results}}
    Time Window: {{time_window}}

    Provide analysis in JSON format with:
    - severity: INFO, WARNING, or CRITICAL
    - findings: List of findings
    - recommendation: Recommended action
    - requires_action: Boolean
    """

    analysis = await llm_service.analyze_results(
        config=config,
        splunk_results=splunk_results,
        analysis_prompt=analysis_prompt,
        time_window="5 minutes",
    )

    logger.info(
        "Analysis complete",
        job_id=str(job.id),
        severity=analysis.get("severity"),
    )

    return analysis


async def process_notifications(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Send notifications based on analysis."""
    logger.info("Sending notifications", job_id=str(job.id))

    notification_service = NotificationService()

    # Get analysis results
    analysis = job.stages_data.get("ai_analysis", {}).get("data", {})
    severity = analysis.get("severity", "INFO")

    # Get notification template
    template = use_case.notification_template if use_case else {}

    # Build context
    context = {
        "job_id": str(job.id),
        "use_case": job.use_case_name,
        "severity": severity,
        "findings": str(analysis.get("findings", [])),
        "recommendation": analysis.get("recommendation", ""),
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
                description=f"Analysis Results:\n{analysis}",
                category=snow_template.get("category", "Network"),
                priority="2" if severity == "CRITICAL" else "3",
            )
            results.append({"channel": "servicenow", "success": result.get("success")})

    return {
        "notifications_sent": len(results),
        "results": results,
    }


async def process_human_decision(ctx: dict, job: PipelineJob, use_case: UseCase, db) -> Dict[str, Any]:
    """Prepare for human decision."""
    logger.info("Awaiting human decision", job_id=str(job.id))

    # Compile summary for human review
    summary = {
        "job_id": str(job.id),
        "use_case": job.use_case_name,
        "input": job.input_text,
        "intent": job.stages_data.get("intent_parsing", {}).get("data", {}),
        "config": job.stages_data.get("config_generation", {}).get("data", {}),
        "deployment": job.stages_data.get("cml_deployment", {}).get("data", {}),
        "analysis": job.stages_data.get("ai_analysis", {}).get("data", {}),
        "awaiting_approval": True,
    }

    return summary
