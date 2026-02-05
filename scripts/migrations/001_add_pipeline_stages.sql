-- =============================================================================
-- Migration 001: Add new pipeline stages (ai_advice, ai_validation)
-- Reorder pipeline to have human approval BEFORE deployment
-- =============================================================================

-- Add new enum values to pipeline_stage
-- Note: PostgreSQL allows adding values but not removing or reordering
-- We need to handle this carefully for existing data

-- Add ai_advice before human_decision
ALTER TYPE pipeline_stage ADD VALUE IF NOT EXISTS 'ai_advice' BEFORE 'human_decision';

-- Add ai_validation (we can't rename ai_analysis, so we add new and migrate)
ALTER TYPE pipeline_stage ADD VALUE IF NOT EXISTS 'ai_validation' AFTER 'splunk_analysis';

-- Migrate existing jobs that have ai_analysis to ai_validation
-- This updates the JSONB stages_data to use the new key name
UPDATE pipeline_jobs
SET stages_data = (
    stages_data - 'ai_analysis'
    || jsonb_build_object('ai_validation', COALESCE(stages_data->'ai_analysis', '{"status": "pending", "data": null}'::jsonb))
    || CASE
        WHEN NOT (stages_data ? 'ai_advice')
        THEN jsonb_build_object('ai_advice', '{"status": "pending", "data": null}'::jsonb)
        ELSE '{}'::jsonb
    END
)
WHERE stages_data ? 'ai_analysis';

-- Update jobs where current_stage was ai_analysis to ai_validation
-- Note: We can't directly update enum values in a WHERE clause for the old value
-- if it no longer exists, but since we added ai_validation, this should work
-- We'll do this conditionally

-- For any job that has already run through ai_analysis, update the stages_data
UPDATE pipeline_jobs
SET stages_data = stages_data || jsonb_build_object('ai_advice', '{"status": "pending", "data": null}'::jsonb)
WHERE NOT (stages_data ? 'ai_advice');

-- Ensure all jobs have the new stage keys in stages_data
UPDATE pipeline_jobs
SET stages_data = stages_data || jsonb_build_object('ai_validation', '{"status": "pending", "data": null}'::jsonb)
WHERE NOT (stages_data ? 'ai_validation');

-- Add comment documenting the new pipeline order
COMMENT ON TYPE pipeline_stage IS 'Pipeline stages in order: voice_input -> intent_parsing -> config_generation -> ai_advice -> human_decision -> cml_deployment -> monitoring -> splunk_analysis -> ai_validation -> notifications';
