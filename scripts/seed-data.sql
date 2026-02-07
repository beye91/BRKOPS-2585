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
    ARRAY['ospf', 'routing', 'modify_ospf_area', 'change_area', 'add_network', 'remove_network'],
    true,
    NULL,
    NULL,
    true,
    1
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    intent_prompt = EXCLUDED.intent_prompt,
    config_prompt = EXCLUDED.config_prompt,
    analysis_prompt = EXCLUDED.analysis_prompt,
    notification_template = EXCLUDED.notification_template;

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
    ARRAY['credential', 'password', 'rotate', 'username', 'authentication'],
    true,
    NULL,
    NULL,
    true,
    2
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    notification_template = EXCLUDED.notification_template;

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
    ARRAY['security', 'advisory', 'cve', 'vulnerability', 'patch', 'remediation'],
    true,
    NULL,
    NULL,
    true,
    3
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    notification_template = EXCLUDED.notification_template;

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
