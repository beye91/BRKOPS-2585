# =============================================================================
# BRKOPS-2585 Jobs Router
# Job queue status and management endpoints
# =============================================================================

from typing import List, Optional
from datetime import datetime, timedelta

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db
from db.models import PipelineJob

logger = structlog.get_logger()
router = APIRouter()


@router.get("/stats")
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get job queue statistics."""
    # Count jobs by status
    result = await db.execute(
        select(PipelineJob.status, func.count(PipelineJob.id))
        .group_by(PipelineJob.status)
    )
    status_counts = dict(result.all())

    # Recent job counts (last hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    result = await db.execute(
        select(func.count(PipelineJob.id))
        .where(PipelineJob.created_at >= one_hour_ago)
    )
    recent_count = result.scalar() or 0

    # Average completion time for successful jobs
    result = await db.execute(
        select(func.avg(
            func.extract('epoch', PipelineJob.completed_at - PipelineJob.started_at)
        ))
        .where(
            PipelineJob.status == 'completed',
            PipelineJob.completed_at.isnot(None),
            PipelineJob.started_at.isnot(None),
        )
    )
    avg_duration = result.scalar()

    return {
        "by_status": {
            status.value if hasattr(status, 'value') else status: count
            for status, count in status_counts.items()
        },
        "recent_count": recent_count,
        "average_duration_seconds": round(avg_duration, 2) if avg_duration else None,
        "total": sum(status_counts.values()),
    }


@router.get("/queue")
async def get_queue_info():
    """Get information about the arq job queue."""
    try:
        redis_pool = await create_pool(
            RedisSettings(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
            )
        )

        # Get queue info from Redis
        # arq stores jobs in various keys
        import redis.asyncio as redis

        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
        )

        # Get pending jobs count
        queue_length = await r.llen("arq:queue")

        # Get running jobs (approximation)
        # arq uses job_id keys with prefix
        running_keys = []
        async for key in r.scan_iter(match="arq:job:*"):
            running_keys.append(key)

        await r.close()
        await redis_pool.close()

        return {
            "queue_length": queue_length,
            "active_jobs": len(running_keys),
            "redis_connected": True,
        }

    except Exception as e:
        logger.error("Failed to get queue info", error=str(e))
        return {
            "queue_length": 0,
            "active_jobs": 0,
            "redis_connected": False,
            "error": str(e),
        }


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed job."""
    from uuid import UUID

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    result = await db.execute(select(PipelineJob).where(PipelineJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status not in ['failed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry failed or cancelled jobs (current status: {job.status})",
        )

    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job has exceeded maximum retry attempts ({job.max_retries})",
        )

    # Reset job for retry
    job.status = 'queued'
    job.retry_count += 1
    job.error_message = None
    job.error_details = None
    await db.commit()

    # Enqueue job
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
            job_id,
            True,  # demo_mode
        )
        await redis_pool.close()

        logger.info("Job retried", job_id=job_id, retry_count=job.retry_count)

        return {
            "success": True,
            "message": f"Job {job_id} queued for retry (attempt {job.retry_count})",
        }

    except Exception as e:
        logger.error("Failed to retry job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}",
        )


@router.delete("/completed")
async def clear_completed_jobs(
    older_than_hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """Clear completed jobs older than specified hours."""
    cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)

    result = await db.execute(
        select(func.count(PipelineJob.id))
        .where(
            PipelineJob.status.in_(['completed', 'cancelled']),
            PipelineJob.completed_at < cutoff,
        )
    )
    count = result.scalar() or 0

    if count > 0:
        from sqlalchemy import delete
        await db.execute(
            delete(PipelineJob)
            .where(
                PipelineJob.status.in_(['completed', 'cancelled']),
                PipelineJob.completed_at < cutoff,
            )
        )
        await db.commit()

    logger.info("Cleared completed jobs", count=count, older_than_hours=older_than_hours)

    return {
        "success": True,
        "deleted_count": count,
        "older_than_hours": older_than_hours,
    }


@router.get("/recent")
async def get_recent_jobs(
    limit: int = 10,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get recent jobs with optional status filter."""
    query = select(PipelineJob).order_by(PipelineJob.created_at.desc())

    if status_filter:
        valid_statuses = ['pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled']
        if status_filter.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.where(PipelineJob.status == status_filter.lower())

    query = query.limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": str(job.id),
                "use_case": job.use_case_name,
                "input_text": job.input_text[:100] + "..." if len(job.input_text) > 100 else job.input_text,
                "current_stage": job.current_stage,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error": job.error_message,
            }
            for job in jobs
        ],
        "count": len(jobs),
    }
