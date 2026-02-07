-- =============================================================================
-- BRKOPS-2585: Database Schema Initialization
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Configuration Variables Table
-- Stores all configurable settings (no hardcoded values)
-- =============================================================================
CREATE TABLE IF NOT EXISTS config_variables (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    is_secret BOOLEAN DEFAULT FALSE,
    validation_schema JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by category
CREATE INDEX idx_config_variables_category ON config_variables(category);
CREATE INDEX idx_config_variables_key ON config_variables(key);

-- =============================================================================
-- MCP Server Registry
-- Tracks external MCP servers (CML, Splunk)
-- =============================================================================
CREATE TABLE IF NOT EXISTS mcp_servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('cml', 'splunk', 'custom')),
    endpoint VARCHAR(500) NOT NULL,
    auth_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    health_status VARCHAR(50) DEFAULT 'unknown' CHECK (health_status IN ('healthy', 'unhealthy', 'unknown')),
    last_health_check TIMESTAMPTZ,
    available_tools JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mcp_servers_name_type ON mcp_servers(name, type);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_type ON mcp_servers(type);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_active ON mcp_servers(is_active);

-- =============================================================================
-- Pipeline Jobs
-- Tracks all demo operations through the 9-stage pipeline
-- =============================================================================
CREATE TYPE job_status AS ENUM ('pending', 'queued', 'running', 'paused', 'completed', 'failed', 'cancelled');
-- Pipeline stages in execution order:
-- 1. voice_input - Capture and transcribe voice command
-- 2. intent_parsing - LLM extracts structured intent
-- 3. config_generation - LLM generates Cisco IOS commands
-- 4. ai_advice - LLM reviews proposed changes, provides risk assessment
-- 5. human_decision - Approve/reject BEFORE deployment
-- 6. baseline_collection - Collect network state BEFORE deployment
-- 7. cml_deployment - Deploy to CML lab (only if approved)
-- 8. monitoring - Wait for convergence and collect post-state with diff
-- 9. splunk_analysis - Collect post-deployment telemetry
-- 10. ai_validation - LLM validates deployment results
-- 11. notifications - Send alerts with final status
CREATE TYPE pipeline_stage AS ENUM (
    'voice_input',
    'intent_parsing',
    'config_generation',
    'ai_advice',
    'human_decision',
    'baseline_collection',
    'cml_deployment',
    'monitoring',
    'splunk_analysis',
    'ai_validation',
    'notifications'
);

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id INTEGER,
    use_case_name VARCHAR(100) NOT NULL,
    input_text TEXT NOT NULL,
    input_audio_url TEXT,
    current_stage pipeline_stage NOT NULL DEFAULT 'voice_input',
    status job_status NOT NULL DEFAULT 'pending',
    stages_data JSONB DEFAULT '{
        "voice_input": {"status": "pending", "data": null},
        "intent_parsing": {"status": "pending", "data": null},
        "config_generation": {"status": "pending", "data": null},
        "ai_advice": {"status": "pending", "data": null},
        "human_decision": {"status": "pending", "data": null},
        "baseline_collection": {"status": "pending", "data": null},
        "cml_deployment": {"status": "pending", "data": null},
        "monitoring": {"status": "pending", "data": null},
        "splunk_analysis": {"status": "pending", "data": null},
        "ai_validation": {"status": "pending", "data": null},
        "notifications": {"status": "pending", "data": null}
    }',
    result JSONB,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX idx_pipeline_jobs_stage ON pipeline_jobs(current_stage);
CREATE INDEX idx_pipeline_jobs_created ON pipeline_jobs(created_at DESC);
CREATE INDEX idx_pipeline_jobs_use_case ON pipeline_jobs(use_case_name);

-- =============================================================================
-- Use Case Templates
-- Configurable demo scenarios with prompts
-- =============================================================================
CREATE TABLE IF NOT EXISTS use_cases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    trigger_keywords TEXT[] DEFAULT '{}',
    intent_prompt TEXT NOT NULL,
    config_prompt TEXT NOT NULL,
    analysis_prompt TEXT NOT NULL,
    notification_template JSONB DEFAULT '{}',
    cml_target_lab VARCHAR(100),
    splunk_index VARCHAR(100) DEFAULT 'netops',
    convergence_wait_seconds INTEGER DEFAULT 45,
    llm_provider VARCHAR(50) DEFAULT NULL CHECK (llm_provider IS NULL OR llm_provider IN ('openai', 'anthropic')),
    llm_model VARCHAR(100) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_use_cases_active ON use_cases(is_active);
CREATE INDEX idx_use_cases_name ON use_cases(name);

-- =============================================================================
-- Notification History
-- Tracks all sent notifications
-- =============================================================================
CREATE TYPE notification_channel AS ENUM ('webex', 'servicenow', 'email', 'slack');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'delivered', 'failed');

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES pipeline_jobs(id) ON DELETE SET NULL,
    channel notification_channel NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
    response_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_job ON notifications(job_id);
CREATE INDEX idx_notifications_channel ON notifications(channel);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);

-- =============================================================================
-- Audit Log
-- Tracks all significant actions for compliance and debugging
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(100) NOT NULL DEFAULT 'system',
    old_values JSONB,
    new_values JSONB,
    extra_data JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- =============================================================================
-- Users Table (for Admin panel)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'operator', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- =============================================================================
-- Trigger for updated_at timestamps
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_config_variables_updated_at BEFORE UPDATE ON config_variables
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_servers_updated_at BEFORE UPDATE ON mcp_servers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipeline_jobs_updated_at BEFORE UPDATE ON pipeline_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_use_cases_updated_at BEFORE UPDATE ON use_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Grant permissions
-- =============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO brkops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO brkops;
