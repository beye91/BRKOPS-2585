# =============================================================================
# BRKOPS-2585 arq Worker Configuration
# Background job processing for pipeline stages
# =============================================================================

from arq import cron
from arq.connections import RedisSettings

from config import settings
from tasks.pipeline import (
    process_pipeline_job,
    process_intent_parsing,
    process_config_generation,
    process_cml_deployment,
    process_monitoring,
    process_splunk_analysis,
    process_ai_analysis,
    process_notifications,
)
from tasks.health import check_mcp_health


async def startup(ctx: dict) -> None:
    """Worker startup - initialize connections."""
    import structlog
    from db.database import init_db

    logger = structlog.get_logger()
    logger.info("arq worker starting up")

    # Initialize database connection
    await init_db()
    logger.info("Worker database initialized")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown - cleanup connections."""
    import structlog
    from db.database import close_db

    logger = structlog.get_logger()
    logger.info("arq worker shutting down")

    await close_db()
    logger.info("Worker database closed")


class WorkerSettings:
    """arq worker settings."""

    # Redis connection
    redis_settings = RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
    )

    # Job functions available to the worker
    functions = [
        process_pipeline_job,
        process_intent_parsing,
        process_config_generation,
        process_cml_deployment,
        process_monitoring,
        process_splunk_analysis,
        process_ai_analysis,
        process_notifications,
    ]

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Check MCP server health every 5 minutes
        cron(check_mcp_health, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker configuration
    max_jobs = 10  # Max concurrent jobs
    job_timeout = 600  # 10 minute timeout for long-running jobs
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5  # Poll every 500ms for new jobs
    queue_read_limit = 10  # Read up to 10 jobs at once

    # Retry configuration
    max_tries = 3
    retry_delay = 5.0  # 5 second delay between retries
