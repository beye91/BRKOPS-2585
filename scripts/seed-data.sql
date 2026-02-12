-- =============================================================================
-- BRKOPS-2585: Seed Data
-- Default configuration and use case templates
-- =============================================================================

-- =============================================================================
-- Default Admin User (Password: Admin123!)
-- =============================================================================
INSERT INTO users (username, email, password_hash, full_name, role, is_active)
VALUES (
    'admin',
    'admin@brkops.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGYxB5Dz1Ey', -- Admin123!
    'System Administrator',
    'admin',
    true
) ON CONFLICT (username) DO NOTHING;

-- =============================================================================
-- Configuration Variables
-- =============================================================================

-- LLM Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('llm.primary_provider', '"openai"', 'Primary LLM provider (openai or anthropic)', 'llm', false),
('llm.fallback_provider', '"anthropic"', 'Fallback LLM provider', 'llm', false),
('llm.openai_model', '"gpt-4-turbo-preview"', 'OpenAI model to use', 'llm', false),
('llm.anthropic_model', '"claude-3-sonnet-20240229"', 'Anthropic model to use', 'llm', false),
('llm.temperature', '0.7', 'LLM temperature setting', 'llm', false),
('llm.max_tokens', '4096', 'Maximum tokens for LLM response', 'llm', false),
('llm.timeout_seconds', '30', 'LLM request timeout', 'llm', false),
('llm.retry_attempts', '3', 'Number of retry attempts on failure', 'llm', false),
('openai_api_key', '""', 'OpenAI API key for GPT models', 'llm', true),
('anthropic_api_key', '""', 'Anthropic API key for Claude models', 'llm', true)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Pipeline Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('pipeline.convergence_wait_seconds', '45', 'Seconds to wait for network convergence after config push', 'pipeline', false),
('pipeline.mcp_timeout_seconds', '60', 'Timeout for MCP server requests', 'pipeline', false),
('pipeline.max_retries', '3', 'Maximum retry attempts for failed stages', 'pipeline', false),
('pipeline.demo_mode', 'true', 'Enable step-by-step advancement in demo', 'pipeline', false),
('pipeline.auto_advance', 'false', 'Auto-advance through stages without pausing', 'pipeline', false)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Notification Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('notifications.webex_enabled', 'true', 'Enable WebEx notifications', 'notifications', false),
('notifications.servicenow_enabled', 'true', 'Enable ServiceNow ticket creation', 'notifications', false),
('notifications.email_enabled', 'false', 'Enable email notifications', 'notifications', false),
('notifications.webex_room_id', '""', 'Default WebEx room ID for notifications', 'notifications', false),
('notifications.webex_webhook_url', '""', 'WebEx incoming webhook URL', 'notifications', true),
('notifications.servicenow_instance', '""', 'ServiceNow instance URL', 'notifications', false),
('notifications.servicenow_username', '""', 'ServiceNow API username', 'notifications', false),
('notifications.servicenow_password', '""', 'ServiceNow API password', 'notifications', true)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- UI Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('ui.theme', '"dark"', 'UI theme (dark or light)', 'ui', false),
('ui.primary_color', '"#049FD9"', 'Primary accent color (Cisco blue)', 'ui', false),
('ui.show_topology', 'true', 'Show network topology visualization', 'ui', false),
('ui.show_logs', 'true', 'Show real-time log stream', 'ui', false),
('ui.animation_speed', '"normal"', 'Animation speed (slow, normal, fast)', 'ui', false)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Validation Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('validation.score_failed', '45', 'Overall score when validation status is FAILED', 'validation', false),
('validation.score_warning', '75', 'Overall score when validation status is WARNING', 'validation', false),
('validation.score_success', '95', 'Overall score when validation status is PASSED', 'validation', false),
('validation.fallback_score_unhealthy', '30', 'Fallback score when deployment is unhealthy', 'validation', false),
('validation.fallback_score_healthy', '90', 'Fallback score when deployment is healthy', 'validation', false),
('validation.route_loss_threshold', '-2', 'Route loss threshold that triggers rollback', 'validation', false),
('validation.missing_field_default_score', '50', 'Default score for missing validation fields', 'validation', false),
('validation.api_key_min_length', '20', 'Minimum length for API key validation', 'validation', false)
ON CONFLICT (key) DO NOTHING;

-- Matching Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('matching.mismatch_threshold', '30', 'Minimum confidence for best match to trigger mismatch warning', 'matching', false),
('matching.confidence_delta_threshold', '20', 'Required confidence delta between best and selected match', 'matching', false),
('matching.demo_intent_confidence', '85', 'Default confidence score for demo intent parsing', 'matching', false),
('matching.intent_matcher_temperature', '0.3', 'LLM temperature for intent matching', 'matching', false)
ON CONFLICT (key) DO NOTHING;

-- Devices Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('devices.router_node_definitions', '["cat8000v","iosv","csr1000v","iosxrv9000","iosxrv","iosvl2"]', 'CML router node definition types', 'devices', false),
('devices.active_node_states', '["BOOTED","STARTED"]', 'Node states considered active/targetable', 'devices', false),
('devices.all_keywords', '["all","all routers","all devices","every router","every device","all network devices","all of them","all the routers"]', 'Keywords that mean target all routers', 'devices', false),
('devices.management_ip_mapping', '{"Router-1":"198.18.1.201","Router-2":"198.18.1.202","Router-3":"198.18.1.203","Router-4":"198.18.1.204"}', 'Router label to management IP mapping', 'devices', false),
('devices.demo_lab_title', '"BRKOPS-2585-OSPF-Demo"', 'Title of the demo lab in CML', 'devices', false)
ON CONFLICT (key) DO NOTHING;

-- Network Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('network.ospf_state_patterns', '["FULL","TWO-WAY","2WAY"]', 'OSPF neighbor state patterns to detect', 'network', false),
('network.interface_patterns', '["GigabitEthernet","Loopback"]', 'Interface name patterns', 'network', false),
('network.cpu_cli_command', '"show processes cpu | include CPU utilization"', 'CLI command for CPU utilization', 'network', false),
('network.memory_cli_command', '"show processes memory | include Processor"', 'CLI command for memory utilization', 'network', false)
ON CONFLICT (key) DO NOTHING;

-- Splunk Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('splunk.query_ospf_events', '"index=netops (OSPF OR \"routing\" OR \"adjacency\")"', 'SPL query for OSPF events', 'splunk', false),
('splunk.query_routing_errors', '"index=netops (error OR warning OR critical) (routing OR OSPF OR BGP OR EIGRP)"', 'SPL query for routing errors', 'splunk', false),
('splunk.query_config_changes', '"index=netops (\"config\" OR \"configuration\") (\"change\" OR \"modified\" OR \"updated\")"', 'SPL query for config changes', 'splunk', false),
('splunk.query_auth_events', '"index=netops (authentication OR login OR \"access\" OR \"denied\" OR \"failed\")"', 'SPL query for authentication events', 'splunk', false),
('splunk.fallback_indexes', '["network","main","security"]', 'Fallback index list when get_indexes fails', 'splunk', false),
('splunk.default_index', '"netops"', 'Default Splunk index', 'splunk', false),
('splunk.query_result_limit', '100', 'Default max results for Splunk queries', 'splunk', false)
ON CONFLICT (key) DO NOTHING;

-- Extended Pipeline Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('pipeline.config_truncation_limit', '12000', 'Max total chars for lab context configs', 'pipeline', false),
('pipeline.monitoring_interval_max', '5', 'Max seconds per monitoring progress interval', 'pipeline', false),
('pipeline.demo_stage_pause_seconds', '1', 'Seconds to pause between demo stages', 'pipeline', false)
ON CONFLICT (key) DO NOTHING;

-- Operational Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('operational.cml_max_retries', '5', 'Max retries for CML lab config reset', 'operational', false),
('operational.cml_retry_delay', '30', 'Delay in seconds between CML retries', 'operational', false),
('operational.config_fetch_max_retries', '3', 'Max retries for fetching running configs', 'operational', false),
('operational.config_fetch_retry_delay', '10', 'Delay in seconds between config fetch retries', 'operational', false),
('operational.jwt_expiry_seconds', '86400', 'JWT token expiry in seconds', 'operational', false),
('operational.audio_max_size_mb', '25', 'Max audio file upload size in MB', 'operational', false),
('operational.http_timeout_notification', '30', 'HTTP timeout for notification requests', 'operational', false),
('operational.http_timeout_voice', '60', 'HTTP timeout for voice transcription requests', 'operational', false),
('operational.servicenow_default_priority', '"3"', 'Default ServiceNow ticket priority', 'operational', false),
('operational.servicenow_default_impact', '"2"', 'Default ServiceNow ticket impact', 'operational', false),
('operational.servicenow_default_urgency', '"2"', 'Default ServiceNow ticket urgency', 'operational', false),
('operational.job_cleanup_retention_hours', '24', 'Hours to retain completed jobs before cleanup', 'operational', false),
('operational.health_check_interval_minutes', '5', 'MCP health check interval in minutes', 'operational', false)
ON CONFLICT (key) DO NOTHING;

-- Extended UI Configuration
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('ui.polling_interval_ms', '3000', 'Frontend polling interval in milliseconds', 'ui', false),
('ui.websocket_reconnect_delay_ms', '3000', 'WebSocket reconnect delay in milliseconds', 'ui', false),
('ui.duration_threshold_fast_seconds', '2', 'Threshold for fast duration (green)', 'ui', false),
('ui.duration_threshold_medium_seconds', '10', 'Threshold for medium duration (yellow)', 'ui', false),
('ui.log_error_regex', '"(%OSPF-[45]-\\\\w+|ERROR|FAILED|DOWN)"', 'Regex for error highlighting in logs', 'ui', false),
('ui.pipeline_stages', '[{"key":"voice_input","label":"Voice Input","icon":"mic"},{"key":"intent_parsing","label":"Intent Parsing","icon":"brain"},{"key":"config_generation","label":"Config Generation","icon":"code"},{"key":"ai_advice","label":"AI Advice","icon":"lightbulb"},{"key":"human_decision","label":"Human Decision","icon":"user"},{"key":"baseline_collection","label":"Baseline Collection","icon":"chart"},{"key":"cml_deployment","label":"CML Deployment","icon":"server"},{"key":"monitoring","label":"Monitoring","icon":"activity"},{"key":"splunk_analysis","label":"Splunk Analysis","icon":"search"},{"key":"ai_validation","label":"AI Validation","icon":"check"},{"key":"notifications","label":"Notifications","icon":"bell"}]', 'Pipeline stage definitions for frontend', 'ui', false)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- Use Case Templates
-- =============================================================================

-- Use Case 1: OSPF Configuration Change (Primary Demo)
INSERT INTO use_cases (
    name,
    display_name,
    description,
    trigger_keywords,
    intent_prompt,
    config_prompt,
    analysis_prompt,
    notification_template,
    convergence_wait_seconds,
    servicenow_enabled,
    allowed_actions,
    scope_validation_enabled,
    llm_provider,
    llm_model,
    explanation_template,
    impact_description,
    splunk_query_config,
    pre_checks,
    post_checks,
    risk_profile,
    ospf_config_strategy,
    is_active,
    sort_order
) VALUES (
    'ospf_configuration_change',
    'OSPF Configuration Change',
    'Modify OSPF routing configuration on network devices. This use case demonstrates voice-driven OSPF area changes with automated validation.',
    ARRAY['ospf', 'routing', 'area', 'router ospf', 'network statement'],
    E'You are a network intent parser. Analyze the following voice command and extract structured intent.

Voice Command: {{input_text}}

Extract the following information:
1. Action type: MODIFY_OSPF_CONFIG, ADD_NETWORK, REMOVE_NETWORK, CHANGE_AREA
2. Target device(s): router name or pattern
3. Parameters: area_id, network_address, wildcard_mask, process_id
4. Confidence score (0-100)

IMPORTANT - Target Device Rules:
- If the user says "all routers", "all devices", "every router", or similar: set target_devices to ["all"]
- If the user names specific routers (e.g. "Router-1 and Router-3"): list each one, e.g. ["Router-1", "Router-3"]
- If no device is mentioned: default to ["Router-1"]

Respond in JSON format:
{
    "action": "string",
    "target_devices": ["string"],
    "parameters": {
        "area_id": "number or null",
        "network": "string or null",
        "wildcard": "string or null",
        "process_id": "number, default 1"
    },
    "confidence": "number",
    "clarification_needed": "string or null"
}',
    E'You are a Cisco IOS configuration generator. Generate the exact CLI commands for the following intent.

Intent: {{intent}}
Current Device Config (if available): {{current_config}}

Requirements:
- Generate valid Cisco IOS/IOS-XE commands
- Include comments explaining changes
- Use proper indentation for configuration mode
- Consider rollback commands if appropriate

Respond in JSON format:
{
    "commands": ["string"],
    "rollback_commands": ["string"],
    "config_mode": "configure terminal",
    "warnings": ["string"],
    "explanation": "string"
}',
    E'You are a network operations analyst. Analyze the following Splunk query results after an OSPF configuration change.

Configuration Applied: {{config}}
Splunk Results: {{splunk_results}}
Time Window: {{time_window}}

Analyze for:
1. OSPF adjacency changes (neighbor up/down)
2. Routing table changes
3. Routing loops or suboptimal paths
4. Error messages or warnings
5. Convergence time

Provide analysis in JSON format:
{
    "severity": "INFO|WARNING|CRITICAL",
    "findings": [
        {
            "type": "string",
            "description": "string",
            "affected_devices": ["string"],
            "evidence": "string"
        }
    ],
    "root_cause": "string or null",
    "recommendation": "string",
    "requires_action": "boolean",
    "suggested_remediation": "string or null"
}',
    '{
        "webex": {
            "success": "✅ **BRKOPS-2585** | Configuration applied successfully to **{{devices}}**. OSPF area changed to {{area_id}}. Network is stable.\n\n**AI Assessment:** {{recommendation}}",
            "warning": "⚠️ **BRKOPS-2585** | Configuration applied but issues detected on **{{devices}}**:\n\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}",
            "critical": "🚨 **BRKOPS-2585 CRITICAL** | Configuration caused network issues on **{{devices}}**!\n\n**Issues Found:**\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}\n\n**Action Required:** {{rollback_action}}"
        },
        "servicenow": {
            "short_description": "OSPF Configuration Change - {{devices}}",
            "category": "Network",
            "subcategory": "Routing",
            "priority": "{{priority}}"
        }
    }',
    45,
    true,
    ARRAY['modify_ospf_area', 'modify_ospf_config', 'change_area'],
    true,
    NULL,
    NULL,
    'Change OSPF area to {{new_area}} on {{device_count}} device(s)',
    'Brief OSPF neighbor flap during area transition',
    '{"query_type": "ospf_events"}',
    '["Verify current OSPF neighbor state on all target devices", "Confirm no active maintenance on affected devices", "Review per-device rollback commands"]',
    '["Verify OSPF neighbors re-establish", "Check routing table convergence", "Confirm no routing loops"]',
    '{"risk_factors": ["OSPF area change causes temporary neighbor adjacency reset"], "mitigation_steps": ["Ensure backup paths exist", "Apply during maintenance window", "Per-device rollback ready"], "affected_services": ["OSPF routing", "Inter-area traffic"]}',
    'dual',
    true,
    1
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    intent_prompt = EXCLUDED.intent_prompt,
    config_prompt = EXCLUDED.config_prompt,
    analysis_prompt = EXCLUDED.analysis_prompt,
    notification_template = EXCLUDED.notification_template,
    allowed_actions = EXCLUDED.allowed_actions,
    explanation_template = EXCLUDED.explanation_template,
    impact_description = EXCLUDED.impact_description,
    splunk_query_config = EXCLUDED.splunk_query_config,
    pre_checks = EXCLUDED.pre_checks,
    post_checks = EXCLUDED.post_checks,
    risk_profile = EXCLUDED.risk_profile;

-- Use Case 2: Credential Rotation
INSERT INTO use_cases (
    name,
    display_name,
    description,
    trigger_keywords,
    intent_prompt,
    config_prompt,
    analysis_prompt,
    notification_template,
    convergence_wait_seconds,
    servicenow_enabled,
    allowed_actions,
    scope_validation_enabled,
    llm_provider,
    llm_model,
    explanation_template,
    impact_description,
    splunk_query_config,
    pre_checks,
    post_checks,
    risk_profile,
    is_active,
    sort_order
) VALUES (
    'credential_rotation',
    'Credential Rotation',
    'Rotate device credentials across multiple network devices with validation and compliance tracking.',
    ARRAY['credential', 'password', 'rotate', 'username', 'authentication', 'login'],
    E'You are a network security intent parser. Analyze the voice command for credential rotation.

Voice Command: {{input_text}}

Extract:
1. Scope: all devices, datacenter, specific devices
2. Credential type: local user, enable secret, SNMP community
3. Target username (if applicable)
4. Urgency level

Respond in JSON format:
{
    "action": "ROTATE_CREDENTIALS",
    "scope": "string",
    "target_devices": ["string"] or "all",
    "credential_type": "local_user|enable_secret|snmp",
    "username": "string or null",
    "urgency": "normal|urgent|emergency",
    "confidence": "number"
}',
    E'Generate secure credential rotation commands.

Intent: {{intent}}
Device Platform: {{platform}}

Requirements:
- Generate cryptographically strong passwords
- Include both add new and remove old commands
- Consider service account impacts
- Include verification commands

Respond in JSON format:
{
    "commands": ["string"],
    "new_credentials": {
        "username": "string",
        "password": "GENERATED_SECURE",
        "privilege": "number"
    },
    "verification_commands": ["string"],
    "warnings": ["string"]
}',
    E'Analyze credential rotation results from Splunk.

Splunk Results: {{splunk_results}}

Check for:
1. Authentication failures after rotation
2. Service disruptions
3. Devices not updated
4. Compliance status

Respond in JSON format:
{
    "severity": "INFO|WARNING|CRITICAL",
    "devices_updated": ["string"],
    "devices_failed": ["string"],
    "auth_failures_detected": "boolean",
    "compliance_status": "compliant|non_compliant|partial",
    "recommendation": "string"
}',
    '{
        "webex": {
            "success": "✅ **BRKOPS-2585** | Credential rotation completed on {{count}} devices. All authentications verified.\n\n**AI Assessment:** {{recommendation}}",
            "warning": "⚠️ **BRKOPS-2585** | Credential rotation completed with warnings:\n\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}",
            "critical": "🚨 **BRKOPS-2585 CRITICAL** | Credential rotation failed on {{failed_count}} devices!\n\n**Issues Found:**\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}\n\n**Action Required:** {{rollback_action}}"
        },
        "servicenow": {
            "short_description": "Credential Rotation - {{scope}}",
            "category": "Security",
            "subcategory": "Access Management",
            "priority": "{{priority}}"
        }
    }',
    30,
    true,
    ARRAY['rotate_credentials'],
    true,
    NULL,
    NULL,
    'Rotate credentials on {{device_count}} device(s) with SHA-256 hashed password',
    'Device access may be briefly affected',
    '{"query_type": "authentication_events"}',
    '["Verify current access to affected devices", "Confirm new password meets complexity requirements"]',
    '["Test login with new credentials", "Verify no authentication failures in logs"]',
    '{"risk_factors": ["Credential change affects device access", "Concurrent sessions may be impacted"], "mitigation_steps": ["Ensure new credentials are documented securely", "Test access with new credentials immediately"], "affected_services": ["Device access", "Management sessions"]}',
    true,
    2
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    notification_template = EXCLUDED.notification_template,
    allowed_actions = EXCLUDED.allowed_actions,
    explanation_template = EXCLUDED.explanation_template,
    impact_description = EXCLUDED.impact_description,
    splunk_query_config = EXCLUDED.splunk_query_config,
    pre_checks = EXCLUDED.pre_checks,
    post_checks = EXCLUDED.post_checks,
    risk_profile = EXCLUDED.risk_profile;

-- Use Case 3: Security Advisory Response
INSERT INTO use_cases (
    name,
    display_name,
    description,
    trigger_keywords,
    intent_prompt,
    config_prompt,
    analysis_prompt,
    notification_template,
    convergence_wait_seconds,
    servicenow_enabled,
    allowed_actions,
    scope_validation_enabled,
    llm_provider,
    llm_model,
    explanation_template,
    impact_description,
    splunk_query_config,
    pre_checks,
    post_checks,
    risk_profile,
    is_active,
    sort_order
) VALUES (
    'security_advisory',
    'Security Advisory Response',
    'Respond to security advisories and CVEs by applying remediation configurations across affected devices.',
    ARRAY['security', 'advisory', 'cve', 'vulnerability', 'patch', 'remediation'],
    E'Parse security advisory response intent.

Voice Command: {{input_text}}

Extract:
1. Advisory ID or CVE number
2. Affected device scope
3. Remediation urgency
4. Specific mitigation requested

Respond in JSON format:
{
    "action": "SECURITY_REMEDIATION",
    "advisory_id": "string or null",
    "cve_id": "string or null",
    "scope": "string",
    "urgency": "critical|high|medium|low",
    "specific_mitigation": "string or null",
    "confidence": "number"
}',
    E'Generate security remediation commands.

Intent: {{intent}}
Advisory Details: {{advisory_details}}
Golden Config Template: {{golden_config}}

Requirements:
- Apply minimum necessary changes
- Include compliance verification
- Document all changes
- Provide rollback procedure

Respond in JSON format:
{
    "commands": ["string"],
    "rollback_commands": ["string"],
    "compliance_checks": ["string"],
    "risk_assessment": "string",
    "warnings": ["string"]
}',
    E'Analyze security remediation results.

Splunk Results: {{splunk_results}}
Expected Changes: {{expected_changes}}

Verify:
1. Configuration applied correctly
2. No service disruption
3. Vulnerability mitigated
4. Compliance achieved

Respond in JSON format:
{
    "severity": "INFO|WARNING|CRITICAL",
    "remediation_status": "complete|partial|failed",
    "devices_remediated": ["string"],
    "devices_pending": ["string"],
    "vulnerability_status": "mitigated|exposed|unknown",
    "compliance_status": "compliant|non_compliant",
    "recommendation": "string"
}',
    '{
        "webex": {
            "success": "✅ **BRKOPS-2585** | Security remediation for {{advisory_id}} completed on {{count}} devices.\n\n**AI Assessment:** {{recommendation}}",
            "warning": "⚠️ **BRKOPS-2585** | Security remediation partially completed. {{pending_count}} devices pending.\n\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}",
            "critical": "🚨 **BRKOPS-2585 CRITICAL** | Security remediation failed. {{exposed_count}} devices still vulnerable!\n\n**Issues Found:**\n{{issues}}\n\n**AI Recommendation:** {{recommendation}}\n\n**Action Required:** {{rollback_action}}"
        },
        "servicenow": {
            "short_description": "Security Advisory {{advisory_id}} - Remediation",
            "category": "Security",
            "subcategory": "Vulnerability",
            "priority": "1"
        }
    }',
    60,
    true,
    ARRAY['apply_security_patch', 'security_remediation'],
    true,
    NULL,
    NULL,
    'Apply security ACL on {{device_count}} device(s) to block exploit traffic',
    'ACL changes may affect traffic matching deny rules',
    '{"query_type": "config_changes"}',
    '["Review ACL entries for correctness", "Verify interface attachment points"]',
    '["Verify ACL hit counters", "Confirm no legitimate traffic blocked", "Check vulnerability status"]',
    '{"risk_factors": ["ACL changes may impact legitimate traffic", "Blocking rules are permanent until removed"], "mitigation_steps": ["Monitor traffic after applying ACL", "Have NOC on standby for user reports"], "affected_services": ["Network traffic filtering", "Security posture"]}',
    true,
    3
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    notification_template = EXCLUDED.notification_template,
    allowed_actions = EXCLUDED.allowed_actions,
    explanation_template = EXCLUDED.explanation_template,
    impact_description = EXCLUDED.impact_description,
    splunk_query_config = EXCLUDED.splunk_query_config,
    pre_checks = EXCLUDED.pre_checks,
    post_checks = EXCLUDED.post_checks,
    risk_profile = EXCLUDED.risk_profile;

-- =============================================================================
-- Default MCP Server Entries for dCloud deployment
-- =============================================================================
INSERT INTO mcp_servers (name, type, endpoint, auth_config, is_active) VALUES
(
    'CML Primary',
    'cml',
    'http://198.18.134.22:9001',
    '{"host": "https://198.18.130.201", "username": "admin", "password": "C1sco12345"}',
    true
),
(
    'Splunk Primary',
    'splunk',
    'https://198.18.133.50:8089/services/mcp',
    '{"host": "198.18.133.50", "token": ""}',
    true
)
ON CONFLICT (name, type) DO NOTHING;

-- =============================================================================
-- Log successful seeding
-- =============================================================================
INSERT INTO audit_logs (entity_type, entity_id, action, actor, extra_data)
VALUES ('system', 'database', 'seed_completed', 'system', jsonb_build_object('version', '1.0.0', 'timestamp', NOW()::text));
