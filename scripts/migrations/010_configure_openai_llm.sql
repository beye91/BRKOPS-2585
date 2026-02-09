-- Migration: Configure OpenAI as LLM Provider for All Use Cases
-- Date: 2026-02-09
-- Description: Set OpenAI (GPT-4 Turbo) as the LLM provider for all use cases
--              to enable LLM fallback when CML connections fail during config generation

-- Set OpenAI as LLM provider for all use cases that don't have one configured
UPDATE use_cases
SET
    llm_provider = 'openai',
    llm_model = 'gpt-4-turbo-preview',
    updated_at = NOW()
WHERE llm_provider IS NULL OR llm_provider = '';

-- Verify the update
SELECT id, name, llm_provider, llm_model
FROM use_cases
ORDER BY id;
