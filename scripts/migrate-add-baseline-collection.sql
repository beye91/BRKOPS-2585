-- =============================================================================
-- Migration: Add baseline_collection stage to pipeline_stage enum
-- =============================================================================
-- This migration adds the baseline_collection stage between human_decision
-- and cml_deployment in the pipeline_stage enum.
--
-- Run this on existing databases to update the enum type.
-- =============================================================================

-- Add the new enum value
ALTER TYPE pipeline_stage ADD VALUE IF NOT EXISTS 'baseline_collection' AFTER 'human_decision';

-- Update any existing jobs that might be stuck to include the new stage in stages_data
UPDATE pipeline_jobs
SET stages_data = stages_data || '{"baseline_collection": {"status": "pending", "data": null}}'::jsonb
WHERE NOT (stages_data ? 'baseline_collection');

-- Log the migration
INSERT INTO audit_logs (entity_type, entity_id, action, actor, new_values)
VALUES (
    'migration',
    'add_baseline_collection_stage',
    'schema_update',
    'system',
    '{"description": "Added baseline_collection stage to pipeline_stage enum"}'::jsonb
);
