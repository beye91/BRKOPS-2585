-- =============================================================================
-- Migration: Add input_metadata to pipeline_jobs
-- Purpose: Store LLM matching results (confidence, reasoning, extracted intent)
-- =============================================================================

-- Add input_metadata JSONB column to pipeline_jobs table
ALTER TABLE pipeline_jobs
ADD COLUMN IF NOT EXISTS input_metadata JSONB DEFAULT '{}';

-- Add comment explaining the field
COMMENT ON COLUMN pipeline_jobs.input_metadata IS 'Metadata from intent matching: match_confidence, match_reasoning, extracted_intent, force_mode';
