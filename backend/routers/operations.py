# =============================================================================
# BRKOPS-2585 Operations Router
# Pipeline job management endpoints
# =============================================================================

from typing import List, Optional
from uuid import UUID

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from db.models import PipelineJob, UseCase
from models.operations import (
    OperationCreate,
    OperationResponse,
    OperationSummary,
    ApprovalRequest,
    RollbackRequest,
    RollbackResponse,
)
from db.models import MCPServer
from services.cml_client import CMLClient
from services.websocket_manager import manager

logger = structlog.get_logger()
router = APIRouter()


@router.post("/start", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def start_operation(
    operation: OperationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new pipeline operation.

    This endpoint accepts either text input or an audio URL and begins
    the 9-stage pipeline process. The operation runs asynchronously,
    and status can be tracked via the GET endpoint or WebSocket.
    """
    logger.info("Starting new operation", text=operation.text, use_case=operation.use_case)

    # Validate input
    if not operation.text and not operation.audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or audio_url must be provided",
        )

    # Find or default use case
    use_case = None
    use_case_name = operation.use_case or "ospf_configuration_change"

    if operation.use_case:
        result = await db.execute(
            select(UseCase).where(UseCase.name == operation.use_case, UseCase.is_active == True)
        )
        use_case = result.scalar_one_or_none()
        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Use case '{operation.use_case}' not found or inactive",
            )
        use_case_name = use_case.name

    # Create pipeline job with new stage order
    # Stages: voice_input -> intent_parsing -> config_generation -> ai_advice ->
    #         human_decision -> baseline_collection -> cml_deployment -> monitoring ->
    #         splunk_analysis -> ai_validation -> notifications
    job = PipelineJob(
        use_case_id=use_case.id if use_case else None,
        use_case_name=use_case_name,
        input_text=operation.text or "",
        input_audio_url=operation.audio_url,
        current_stage='voice_input',
        status='queued',
        stages_data={
            "voice_input": {"status": "pending", "data": None},
            "intent_parsing": {"status": "pending", "data": None},
            "config_generation": {"status": "pending", "data": None},
            "ai_advice": {"status": "pending", "data": None},
            "human_decision": {"status": "pending", "data": None},
            "baseline_collection": {"status": "pending", "data": None},
            "cml_deployment": {"status": "pending", "data": None},
            "monitoring": {"status": "pending", "data": None},
            "splunk_analysis": {"status": "pending", "data": None},
            "ai_validation": {"status": "pending", "data": None},
            "notifications": {"status": "pending", "data": None},
        },
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("Pipeline job created", job_id=str(job.id))

    # Enqueue background job
    try:
        redis_pool = await create_pool(
            RedisSettings(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
            )
        )
        await redis_pool.enqueue_job(
            "process_pipeline_job",
            str(job.id),
            operation.demo_mode,
        )
        await redis_pool.close()
        logger.info("Job enqueued for processing", job_id=str(job.id))
    except Exception as e:
        logger.error("Failed to enqueue job", error=str(e))
        # Update job status to failed
        job.status = 'failed'
        job.error_message = f"Failed to enqueue job: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start operation processing",
        )

    # Broadcast event via WebSocket
    await manager.broadcast({
        "type": "operation.started",
        "job_id": str(job.id),
        "use_case": use_case_name,
        "input_text": operation.text,
    })

    return OperationResponse(
        id=job.id,
        use_case_name=job.use_case_name,
        input_text=job.input_text,
        input_audio_url=job.input_audio_url,
        current_stage=job.current_stage,
        status=job.status,
        stages=job.stages_data,
        created_at=job.created_at,
    )


@router.get("", response_model=List[OperationSummary])
async def list_operations(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all pipeline operations with optional filtering."""
    query = select(PipelineJob).order_by(PipelineJob.created_at.desc())

    if status:
        valid_statuses = ['pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled']
        if status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.where(PipelineJob.status == status.lower())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        OperationSummary(
            id=job.id,
            use_case_name=job.use_case_name,
            input_text=job.input_text,
            current_stage=job.current_stage,
            status=job.status,
            created_at=job.created_at,
        )
        for job in jobs
    ]


@router.get("/{operation_id}", response_model=OperationResponse)
async def get_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a specific operation."""
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == operation_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )

    return OperationResponse(
        id=job.id,
        use_case_name=job.use_case_name,
        input_text=job.input_text,
        input_audio_url=job.input_audio_url,
        current_stage=job.current_stage,
        status=job.status,
        stages=job.stages_data,
        result=job.result,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@router.post("/{operation_id}/approve")
async def approve_operation(
    operation_id: UUID,
    approval: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve or reject an operation awaiting human decision.

    This endpoint is called when the pipeline reaches the human_decision stage.
    If approved, the pipeline continues with CML deployment and subsequent stages.
    If rejected, the pipeline is cancelled.
    """
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == operation_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )

    if job.current_stage != 'human_decision':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation is not awaiting approval (current stage: {job.current_stage})",
        )

    from datetime import datetime

    # Update job with decision
    job.stages_data["human_decision"] = {
        "status": "completed",
        "data": {
            "approved": approval.approved,
            "comment": approval.comment,
            "modified_config": approval.modified_config,
            "decided_at": datetime.utcnow().isoformat(),
        },
        "started_at": job.stages_data.get("human_decision", {}).get("started_at"),
        "completed_at": datetime.utcnow().isoformat(),
    }

    if approval.approved:
        # Continue pipeline with deployment stages
        job.status = 'running'  # Update status so frontend knows approval was processed
        job.result = {
            "decision": "approved",
            "comment": approval.comment,
        }
        await db.commit()

        logger.info(
            "Operation approved, continuing pipeline",
            job_id=str(operation_id),
        )

        # Broadcast approval
        await manager.broadcast({
            "type": "operation.approved",
            "job_id": str(operation_id),
            "comment": approval.comment,
        })

        # Enqueue continuation of pipeline (stages 6-10)
        try:
            redis_pool = await create_pool(
                RedisSettings(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password or None,
                )
            )
            await redis_pool.enqueue_job(
                "continue_pipeline_after_approval",
                str(operation_id),
                True,  # demo_mode
            )
            await redis_pool.close()
            logger.info("Pipeline continuation enqueued", job_id=str(operation_id))
        except Exception as e:
            logger.error("Failed to enqueue pipeline continuation", error=str(e))
            job.status = 'failed'
            job.error_message = f"Failed to continue pipeline: {str(e)}"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to continue pipeline after approval",
            )

        return {"success": True, "approved": True, "message": "Pipeline continuing with deployment"}
    else:
        # Rejected - cancel the operation
        job.status = 'cancelled'
        job.result = {
            "decision": "rejected",
            "comment": approval.comment,
        }
        await db.commit()

        logger.info(
            "Operation rejected",
            job_id=str(operation_id),
        )

        # Broadcast rejection
        await manager.broadcast({
            "type": "operation.rejected",
            "job_id": str(operation_id),
            "comment": approval.comment,
        })

        return {"success": True, "approved": False, "message": "Operation rejected"}


@router.delete("/{operation_id}")
async def cancel_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or pending operation."""
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == operation_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )

    if job.status in ['completed', 'cancelled', 'failed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation already {job.status}",
        )

    job.status = 'cancelled'
    await db.commit()

    logger.info("Operation cancelled", job_id=str(operation_id))

    # Broadcast event
    await manager.broadcast({
        "type": "operation.cancelled",
        "job_id": str(operation_id),
    })

    return {"success": True, "message": "Operation cancelled"}


@router.post("/{operation_id}/advance")
async def advance_operation(
    operation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually advance operation to next stage (demo mode).

    Used when demo_mode is enabled to step through the pipeline manually.
    """
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == operation_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )

    if job.status != 'paused':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation is not paused for advancement",
        )

    # Resume job processing
    try:
        redis_pool = await create_pool(
            RedisSettings(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
            )
        )
        await redis_pool.enqueue_job(
            "process_pipeline_job",
            str(job.id),
            True,  # demo_mode
        )
        await redis_pool.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to advance operation: {str(e)}",
        )

    return {"success": True, "message": "Operation advancing to next stage"}


@router.post("/{operation_id}/rollback", response_model=RollbackResponse)
async def rollback_operation(
    operation_id: UUID,
    rollback: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute rollback of deployed configuration.

    This endpoint applies the rollback commands generated during config_generation
    to revert the CML device to its previous state.
    """
    from datetime import datetime

    # Validate confirmation
    if not rollback.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rollback requires confirmation (confirm=True)",
        )

    # Get the operation
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == operation_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found",
        )

    # Validate operation has completed deployment
    cml_deployment = job.stages_data.get("cml_deployment", {})
    if cml_deployment.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation has not completed CML deployment stage",
        )

    if not cml_deployment.get("data", {}).get("deployed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No successful deployment to rollback",
        )

    # Check if rollback already executed
    if job.stages_data.get("rollback", {}).get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rollback has already been executed for this operation",
        )

    # Get rollback commands from config_generation stage
    config_gen = job.stages_data.get("config_generation", {})
    rollback_commands = config_gen.get("data", {}).get("rollback_commands", [])

    if not rollback_commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rollback commands available for this operation",
        )

    # Get CML deployment info
    deployment_data = cml_deployment.get("data", {})
    lab_id = deployment_data.get("lab_id")
    device_results = deployment_data.get("device_results", {})

    # Backward-compat: if no device_results, use old single-device fields
    if not device_results:
        node_id = deployment_data.get("node_id")
        device = deployment_data.get("device")
        if node_id and device:
            device_results = {device: {"deployed": True, "node_id": node_id}}

    if not lab_id or not device_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing CML deployment information (lab_id or device_results)",
        )

    # Collect devices that were successfully deployed
    devices_to_rollback = [
        (label, info.get("node_id"))
        for label, info in device_results.items()
        if info.get("deployed") and info.get("node_id")
    ]

    if not devices_to_rollback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No successfully deployed devices to rollback",
        )

    logger.info(
        "Starting rollback",
        job_id=str(operation_id),
        devices=[d[0] for d in devices_to_rollback],
        commands_count=len(rollback_commands),
        reason=rollback.reason,
    )

    # Initialize rollback stage
    job.stages_data["rollback"] = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "data": {
            "reason": rollback.reason,
            "commands": rollback_commands,
        },
    }
    await db.commit()

    # Broadcast rollback started event
    await manager.broadcast({
        "type": "operation.rollback.started",
        "job_id": str(operation_id),
        "devices": [d[0] for d in devices_to_rollback],
        "commands_count": len(rollback_commands),
    })

    try:
        # Get CML server from database
        cml_result = await db.execute(
            select(MCPServer).where(MCPServer.type == "cml", MCPServer.is_active == True)
        )
        cml_server = cml_result.scalar_one_or_none()

        if not cml_server:
            raise Exception("No active CML server configured")

        client = CMLClient(cml_server.endpoint, cml_server.auth_config)
        config_block = "\n".join(rollback_commands)

        # Rollback ALL deployed devices
        rollback_results = {}
        rollback_success_count = 0
        rollback_fail_count = 0

        for device_label, node_id in devices_to_rollback:
            try:
                result = await client.apply_config(
                    lab_id=lab_id,
                    node_id=node_id,
                    config=config_block,
                    save=True,
                )
                rollback_results[device_label] = {
                    "success": True,
                    "output": result.get("output", ""),
                }
                rollback_success_count += 1
                logger.info("Rollback succeeded for device", device=device_label)
            except Exception as e:
                rollback_results[device_label] = {
                    "success": False,
                    "error": str(e),
                }
                rollback_fail_count += 1
                logger.error("Rollback failed for device", device=device_label, error=str(e))

        overall_success = rollback_fail_count == 0

        # Update rollback stage
        job.stages_data["rollback"] = {
            "status": "completed",
            "started_at": job.stages_data["rollback"]["started_at"],
            "completed_at": datetime.utcnow().isoformat(),
            "data": {
                "reason": rollback.reason,
                "commands": rollback_commands,
                "commands_executed": len(rollback_commands),
                "success": overall_success,
                "device_results": rollback_results,
                "devices_rolled_back": rollback_success_count,
                "devices_failed": rollback_fail_count,
            },
        }
        await db.commit()

        devices_display = ", ".join(d[0] for d in devices_to_rollback)

        logger.info(
            "Rollback completed",
            job_id=str(operation_id),
            success=overall_success,
            rolled_back=rollback_success_count,
            failed=rollback_fail_count,
        )

        await manager.broadcast({
            "type": "operation.rollback.completed",
            "job_id": str(operation_id),
            "devices": [d[0] for d in devices_to_rollback],
            "success": overall_success,
        })

        if not overall_success:
            failed_names = [label for label, r in rollback_results.items() if not r["success"]]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Rollback failed on: {', '.join(failed_names)}",
            )

        return RollbackResponse(
            success=True,
            message=f"Rollback completed successfully on {rollback_success_count} device(s): {devices_display}",
            commands_executed=len(rollback_commands),
            rollback_output=str(rollback_results),
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        error_message = str(e)
        logger.error(
            "Rollback failed",
            job_id=str(operation_id),
            error=error_message,
        )

        job.stages_data["rollback"] = {
            "status": "failed",
            "started_at": job.stages_data["rollback"]["started_at"],
            "completed_at": datetime.utcnow().isoformat(),
            "data": {
                "reason": rollback.reason,
                "commands": rollback_commands,
                "success": False,
                "error": error_message,
            },
        }
        await db.commit()

        await manager.broadcast({
            "type": "operation.rollback.failed",
            "job_id": str(operation_id),
            "error": error_message,
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {error_message}",
        )
