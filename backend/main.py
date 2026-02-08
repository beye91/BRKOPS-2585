# =============================================================================
# BRKOPS-2585 Backend - FastAPI Application
# AI-Driven Network Operations Demo Platform
# =============================================================================

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from db.database import init_db, close_db
from routers import operations, voice, mcp, notifications, admin, jobs
from services.websocket_manager import manager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def sync_mcp_credentials_from_env():
    """
    Sync MCP server credentials from environment variables into the database.

    This ensures that tokens/passwords set via environment variables (e.g. .env.dcloud)
    are always applied to the database, even after a DB re-seed that inserts empty defaults.
    Credentials configured via the Admin UI are stored in the DB and take precedence,
    but if the DB has empty credentials and env vars have values, the env vars are applied.
    """
    from sqlalchemy import select, update
    from db.database import async_session
    from db.models import MCPServer

    async with async_session() as db:
        # Sync Splunk token from env
        if settings.splunk_token and settings.splunk_host:
            result = await db.execute(
                select(MCPServer).where(MCPServer.type == 'splunk')
            )
            splunk_server = result.scalar_one_or_none()
            if splunk_server:
                current_token = (splunk_server.auth_config or {}).get("token", "")
                if not current_token:
                    # DB has empty token but env has one - sync it
                    new_auth = {
                        "host": settings.splunk_host,
                        "token": settings.splunk_token,
                    }
                    splunk_server.auth_config = new_auth
                    if settings.splunk_mcp_url:
                        splunk_server.endpoint = settings.splunk_mcp_url
                    splunk_server.is_active = True
                    await db.commit()
                    logger.info("Synced Splunk credentials from environment to database")

        # Sync CML credentials from env
        if settings.cml_host and settings.cml_username:
            result = await db.execute(
                select(MCPServer).where(MCPServer.type == 'cml')
            )
            cml_server = result.scalar_one_or_none()
            if cml_server:
                current_password = (cml_server.auth_config or {}).get("password", "")
                if not current_password:
                    new_auth = {
                        "host": settings.cml_host,
                        "username": settings.cml_username,
                        "password": settings.cml_password,
                    }
                    cml_server.auth_config = new_auth
                    if settings.cml_mcp_url:
                        cml_server.endpoint = settings.cml_mcp_url
                    await db.commit()
                    logger.info("Synced CML credentials from environment to database")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Starting BRKOPS-2585 Backend", version=settings.app_version)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Sync MCP credentials from environment into DB
    await sync_mcp_credentials_from_env()

    yield

    # Shutdown
    logger.info("Shutting down BRKOPS-2585 Backend")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="BRKOPS-2585 API",
    description="AI-Driven Network Operations Demo Platform for Cisco Live",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# =============================================================================
# CORS Middleware
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Include Routers
# =============================================================================
app.include_router(operations.router, prefix="/api/v1/operations", tags=["Operations"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["MCP"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])


# =============================================================================
# Health Check
# =============================================================================
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "brkops-2585-backend",
            "version": settings.app_version,
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "BRKOPS-2585 API",
        "description": "AI-Driven Network Operations Demo Platform",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# =============================================================================
# WebSocket Endpoint for Real-time Events
# =============================================================================
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pipeline events.

    Events:
    - operation.started
    - operation.stage_changed
    - operation.completed
    - operation.error
    - operation.approved
    - operation.rejected
    - operation.awaiting_approval
    - operation.paused
    - operation.resumed
    - monitoring.progress
    - voice.transcript_update
    - config.generated
    - cml.deployment_complete
    - splunk.results_ready
    - analysis.complete
    - notification.sent
    - log.entry
    """
    await manager.connect(websocket)
    logger.info("WebSocket client connected")

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()

            # Handle client messages (e.g., subscribe to specific job)
            # Support both JSON format and legacy colon-separated format
            job_id = None

            # Try JSON format first
            try:
                import json
                message = json.loads(data)
                if message.get("type") == "subscribe" and message.get("job_id"):
                    job_id = message["job_id"]
            except (json.JSONDecodeError, TypeError):
                pass

            # Fallback to legacy colon-separated format
            if not job_id and data.startswith("subscribe:"):
                job_id = data.split(":")[1]

            if job_id:
                await manager.subscribe_to_job(websocket, job_id)
                await websocket.send_json({"type": "subscribed", "job_id": job_id})
                logger.debug("WebSocket subscribed to job", job_id=job_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


# =============================================================================
# Error Handlers
# =============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
