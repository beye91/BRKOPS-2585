-- =============================================================================
-- Migration 005: Add per-use-case LLM provider/model selector
-- =============================================================================
-- Allows each use case to specify which LLM provider and model to use.
-- If NULL, falls back to global settings from config_variables.
-- =============================================================================

-- Add LLM provider column (openai, anthropic, or NULL for default)
ALTER TABLE use_cases
  ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50) DEFAULT NULL;

-- Add LLM model column (e.g., gpt-4-turbo-preview, claude-3-sonnet-20240229)
ALTER TABLE use_cases
  ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100) DEFAULT NULL;

-- Add CHECK constraint for valid providers
-- NULL means "use global default"
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_use_cases_llm_provider'
  ) THEN
    ALTER TABLE use_cases
      ADD CONSTRAINT chk_use_cases_llm_provider
      CHECK (llm_provider IS NULL OR llm_provider IN ('openai', 'anthropic'));
  END IF;
END $$;
