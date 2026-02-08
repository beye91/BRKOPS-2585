-- =============================================================================
-- Migration 007: Dynamic Use Case Pipeline
-- Adds pipeline configuration columns to use_cases table so that
-- config generation, explanation, impact, Splunk queries, pre/post checks,
-- and risk profiles are all DB-driven instead of hardcoded.
-- =============================================================================

-- Explanation template with {{variable}} placeholders
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS explanation_template TEXT
    DEFAULT 'Configuration change on {{device_count}} device(s)';

-- Human-readable impact description
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS impact_description TEXT
    DEFAULT 'Minimal impact expected';

-- Splunk query routing config
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS splunk_query_config JSONB
    DEFAULT '{"query_type": "general"}';

-- Pre-deployment checks (array of strings)
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS pre_checks JSONB
    DEFAULT '["Validate configuration syntax"]';

-- Post-deployment checks (array of strings)
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS post_checks JSONB
    DEFAULT '["Verify device reachability", "Confirm expected state"]';

-- Risk profile with factors, mitigation, and affected services
ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS risk_profile JSONB
    DEFAULT '{"risk_factors": ["Configuration change"], "mitigation_steps": ["Review carefully before approval"], "affected_services": ["Network services"]}';

-- =============================================================================
-- Backfill existing use cases with specific values
-- =============================================================================

-- OSPF Configuration Change
UPDATE use_cases SET
    explanation_template = 'Change OSPF area to {{new_area}} on {{device_count}} device(s)',
    impact_description = 'Brief OSPF neighbor flap during area transition',
    splunk_query_config = '{"query_type": "ospf_events"}',
    pre_checks = '["Verify current OSPF neighbor state on all target devices", "Confirm no active maintenance on affected devices", "Review per-device rollback commands"]',
    post_checks = '["Verify OSPF neighbors re-establish", "Check routing table convergence", "Confirm no routing loops"]',
    risk_profile = '{"risk_factors": ["OSPF area change causes temporary neighbor adjacency reset"], "mitigation_steps": ["Ensure backup paths exist", "Apply during maintenance window", "Per-device rollback ready"], "affected_services": ["OSPF routing", "Inter-area traffic"]}'
WHERE name = 'ospf_configuration_change';

-- Credential Rotation
UPDATE use_cases SET
    explanation_template = 'Rotate credentials on {{device_count}} device(s) with SHA-256 hashed password',
    impact_description = 'Device access may be briefly affected',
    splunk_query_config = '{"query_type": "authentication_events"}',
    pre_checks = '["Verify current access to affected devices", "Confirm new password meets complexity requirements"]',
    post_checks = '["Test login with new credentials", "Verify no authentication failures in logs"]',
    risk_profile = '{"risk_factors": ["Credential change affects device access", "Concurrent sessions may be impacted"], "mitigation_steps": ["Ensure new credentials are documented securely", "Test access with new credentials immediately"], "affected_services": ["Device access", "Management sessions"]}'
WHERE name = 'credential_rotation';

-- Security Advisory Response
UPDATE use_cases SET
    explanation_template = 'Apply security ACL on {{device_count}} device(s) to block exploit traffic',
    impact_description = 'ACL changes may affect traffic matching deny rules',
    splunk_query_config = '{"query_type": "config_changes"}',
    pre_checks = '["Review ACL entries for correctness", "Verify interface attachment points"]',
    post_checks = '["Verify ACL hit counters", "Confirm no legitimate traffic blocked", "Check vulnerability status"]',
    risk_profile = '{"risk_factors": ["ACL changes may impact legitimate traffic", "Blocking rules are permanent until removed"], "mitigation_steps": ["Monitor traffic after applying ACL", "Have NOC on standby for user reports"], "affected_services": ["Network traffic filtering", "Security posture"]}'
WHERE name = 'security_advisory';
