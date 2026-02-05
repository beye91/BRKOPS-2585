# =============================================================================
# BRKOPS-2585 SQLAlchemy Database Models
# =============================================================================

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID, ENUM
from sqlalchemy.orm import relationship

from db.database import Base


# =============================================================================
# Enums
# =============================================================================
class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStage(str, enum.Enum):
    """
    Pipeline stages in execution order:
    1. VOICE_INPUT - Capture and transcribe voice command
    2. INTENT_PARSING - LLM extracts structured intent
    3. CONFIG_GENERATION - LLM generates Cisco IOS commands
    4. AI_ADVICE - LLM reviews proposed changes, provides risk assessment (NEW)
    5. HUMAN_DECISION - Approve/reject BEFORE deployment (MOVED)
    6. CML_DEPLOYMENT - Deploy to CML lab (only if approved)
    7. MONITORING - Wait for convergence
    8. SPLUNK_ANALYSIS - Collect post-deployment telemetry
    9. AI_VALIDATION - LLM validates deployment results (RENAMED from AI_ANALYSIS)
    10. NOTIFICATIONS - Send alerts with final status
    """
    VOICE_INPUT = "voice_input"
    INTENT_PARSING = "intent_parsing"
    CONFIG_GENERATION = "config_generation"
    AI_ADVICE = "ai_advice"
    HUMAN_DECISION = "human_decision"
    CML_DEPLOYMENT = "cml_deployment"
    MONITORING = "monitoring"
    SPLUNK_ANALYSIS = "splunk_analysis"
    AI_VALIDATION = "ai_validation"
    NOTIFICATIONS = "notifications"


# PostgreSQL ENUM types (must match database schema)
pipeline_stage_enum = ENUM(
    'voice_input', 'intent_parsing', 'config_generation', 'ai_advice',
    'human_decision', 'cml_deployment', 'monitoring', 'splunk_analysis',
    'ai_validation', 'notifications',
    name='pipeline_stage', create_type=False
)

job_status_enum = ENUM(
    'pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled',
    name='job_status', create_type=False
)


class NotificationChannel(str, enum.Enum):
    WEBEX = "webex"
    SERVICENOW = "servicenow"
    EMAIL = "email"
    SLACK = "slack"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class MCPServerType(str, enum.Enum):
    CML = "cml"
    SPLUNK = "splunk"
    CUSTOM = "custom"


class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


# =============================================================================
# Models
# =============================================================================
class ConfigVariable(Base):
    """Configuration variables stored in database."""

    __tablename__ = "config_variables"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    is_secret = Column(Boolean, default=False)
    validation_schema = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MCPServer(Base):
    """MCP Server registry."""

    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'cml', 'splunk', 'custom'
    endpoint = Column(String(500), nullable=False)
    auth_config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    health_status = Column(String(50), default='unknown')  # 'healthy', 'unhealthy', 'unknown'
    last_health_check = Column(DateTime(timezone=True))
    available_tools = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PipelineJob(Base):
    """Pipeline job tracking."""

    __tablename__ = "pipeline_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    use_case_id = Column(Integer, ForeignKey("use_cases.id", ondelete="SET NULL"))
    use_case_name = Column(String(100), nullable=False)
    input_text = Column(Text, nullable=False)
    input_audio_url = Column(Text)
    current_stage = Column(pipeline_stage_enum, nullable=False, default='voice_input')
    status = Column(job_status_enum, nullable=False, default='pending')
    stages_data = Column(JSONB, default={})
    result = Column(JSONB)
    error_message = Column(Text)
    error_details = Column(JSONB)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    use_case = relationship("UseCase", back_populates="jobs")
    notifications = relationship("Notification", back_populates="job")


class UseCase(Base):
    """Use case templates."""

    __tablename__ = "use_cases"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    trigger_keywords = Column(ARRAY(Text), default=[])
    intent_prompt = Column(Text, nullable=False)
    config_prompt = Column(Text, nullable=False)
    analysis_prompt = Column(Text, nullable=False)
    notification_template = Column(JSONB, default={})
    cml_target_lab = Column(String(100))
    splunk_index = Column(String(100), default="network")
    convergence_wait_seconds = Column(Integer, default=45)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    jobs = relationship("PipelineJob", back_populates="use_case")


class Notification(Base):
    """Notification history."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"))
    channel = Column(String(50), nullable=False)
    recipient = Column(Text, nullable=False)
    subject = Column(Text)
    message = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    response_data = Column(JSONB)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("PipelineJob", back_populates="notifications")


class AuditLog(Base):
    """Audit log for tracking actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False, default="system")
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    extra_data = Column(JSONB, default={})
    ip_address = Column(INET)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """User accounts for admin panel."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(String(50), default='viewer')
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
