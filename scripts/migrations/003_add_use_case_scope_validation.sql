-- Migration: Add scope validation and ServiceNow configuration to use_cases table
-- This enables per-use-case control over ServiceNow ticket creation and validates
-- that incoming requests match the defined scope of each use case.

ALTER TABLE use_cases
  ADD COLUMN IF NOT EXISTS servicenow_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS allowed_actions TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS scope_validation_enabled BOOLEAN DEFAULT TRUE;

-- Initialize existing use cases with sensible defaults
UPDATE use_cases SET
  servicenow_enabled = false,  -- Disable by default to avoid noise, enable per use case
  allowed_actions = trigger_keywords,  -- Use trigger_keywords as initial scope
  scope_validation_enabled = true
WHERE servicenow_enabled IS NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_use_cases_scope_validation ON use_cases(scope_validation_enabled) WHERE scope_validation_enabled = true;

COMMENT ON COLUMN use_cases.servicenow_enabled IS 'Enable automatic ServiceNow ticket creation for validation warnings/failures';
COMMENT ON COLUMN use_cases.allowed_actions IS 'List of allowed action types for scope validation (e.g., ospf, bgp, routing)';
COMMENT ON COLUMN use_cases.scope_validation_enabled IS 'Enable validation that parsed intent matches use case scope';
