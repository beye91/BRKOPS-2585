-- Add selected_lab_id field to pipeline_jobs table
-- This enables user override of target lab during operations

ALTER TABLE pipeline_jobs ADD COLUMN IF NOT EXISTS selected_lab_id VARCHAR(255);

-- Add comment for documentation
COMMENT ON COLUMN pipeline_jobs.selected_lab_id IS 'User-selected lab ID override (takes precedence over use case default)';
