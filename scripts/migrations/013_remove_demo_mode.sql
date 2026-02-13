-- Migration 013: Remove demo mode config variables
-- Demo mode has been removed from the pipeline. All stages now always use real LLM calls.

DELETE FROM config_variables WHERE key IN ('pipeline.demo_mode', 'pipeline.demo_stage_pause_seconds');

INSERT INTO audit_logs (actor, resource_type, resource_id, action, details)
VALUES ('system', 'database', 'migration_013_remove_demo_mode', 'migration',
        '{"description": "Removed demo_mode and demo_stage_pause_seconds config variables. Pipeline always uses real LLM calls now."}');
