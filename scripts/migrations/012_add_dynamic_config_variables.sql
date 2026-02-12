-- =============================================================================
-- Migration 012: Add dynamic config variables for all hardcoded values
-- Makes ~52 previously hardcoded values database-configurable
-- Uses ON CONFLICT DO NOTHING to preserve admin-set values
-- =============================================================================

-- Category: validation (scoring thresholds, rollback criteria)
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

-- Category: matching (intent matching thresholds)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('matching.mismatch_threshold', '30', 'Minimum confidence for best match to trigger mismatch warning', 'matching', false),
('matching.confidence_delta_threshold', '20', 'Required confidence delta between best and selected match', 'matching', false),
('matching.demo_intent_confidence', '85', 'Default confidence score for demo intent parsing', 'matching', false),
('matching.intent_matcher_temperature', '0.3', 'LLM temperature for intent matching', 'matching', false)
ON CONFLICT (key) DO NOTHING;

-- Category: devices (router definitions, lab config, IP mappings)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('devices.router_node_definitions', '["cat8000v","iosv","csr1000v","iosxrv9000","iosxrv","iosvl2"]', 'CML router node definition types', 'devices', false),
('devices.active_node_states', '["BOOTED","STARTED"]', 'Node states considered active/targetable', 'devices', false),
('devices.all_keywords', '["all","all routers","all devices","every router","every device","all network devices","all of them","all the routers"]', 'Keywords that mean target all routers', 'devices', false),
('devices.management_ip_mapping', '{"Router-1":"198.18.1.201","Router-2":"198.18.1.202","Router-3":"198.18.1.203","Router-4":"198.18.1.204"}', 'Router label to management IP mapping', 'devices', false),
('devices.demo_lab_title', '"BRKOPS-2585-OSPF-Demo"', 'Title of the demo lab in CML', 'devices', false)
ON CONFLICT (key) DO NOTHING;

-- Category: network (OSPF patterns, CLI commands)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('network.ospf_state_patterns', '["FULL","TWO-WAY","2WAY"]', 'OSPF neighbor state patterns to detect', 'network', false),
('network.interface_patterns', '["GigabitEthernet","Loopback"]', 'Interface name patterns to detect in show ip interface brief', 'network', false),
('network.cpu_cli_command', '"show processes cpu | include CPU utilization"', 'CLI command for CPU utilization', 'network', false),
('network.memory_cli_command', '"show processes memory | include Processor"', 'CLI command for memory utilization', 'network', false)
ON CONFLICT (key) DO NOTHING;

-- Category: splunk (SPL query templates, indexes)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('splunk.query_ospf_events', '"index=netops (OSPF OR \"routing\" OR \"adjacency\")"', 'SPL query for OSPF events', 'splunk', false),
('splunk.query_routing_errors', '"index=netops (error OR warning OR critical) (routing OR OSPF OR BGP OR EIGRP)"', 'SPL query for routing errors', 'splunk', false),
('splunk.query_config_changes', '"index=netops (\"config\" OR \"configuration\") (\"change\" OR \"modified\" OR \"updated\")"', 'SPL query for config changes', 'splunk', false),
('splunk.query_auth_events', '"index=netops (authentication OR login OR \"access\" OR \"denied\" OR \"failed\")"', 'SPL query for authentication events', 'splunk', false),
('splunk.fallback_indexes', '["network","main","security"]', 'Fallback index list when get_indexes fails', 'splunk', false),
('splunk.default_index', '"netops"', 'Default Splunk index', 'splunk', false),
('splunk.query_result_limit', '100', 'Default max results for Splunk queries', 'splunk', false)
ON CONFLICT (key) DO NOTHING;

-- Category: pipeline (extend existing)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('pipeline.config_truncation_limit', '12000', 'Max total chars for lab context configs', 'pipeline', false),
('pipeline.monitoring_interval_max', '5', 'Max seconds per monitoring progress interval', 'pipeline', false),
('pipeline.demo_stage_pause_seconds', '1', 'Seconds to pause between demo stages', 'pipeline', false)
ON CONFLICT (key) DO NOTHING;

-- Category: operational (timeouts, retries, ServiceNow defaults)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('operational.cml_max_retries', '5', 'Max retries for CML lab config reset', 'operational', false),
('operational.cml_retry_delay', '30', 'Delay in seconds between CML retries', 'operational', false),
('operational.config_fetch_max_retries', '3', 'Max retries for fetching running configs', 'operational', false),
('operational.config_fetch_retry_delay', '10', 'Delay in seconds between config fetch retries', 'operational', false),
('operational.jwt_expiry_seconds', '86400', 'JWT token expiry in seconds (24h default)', 'operational', false),
('operational.audio_max_size_mb', '25', 'Max audio file upload size in MB', 'operational', false),
('operational.http_timeout_notification', '30', 'HTTP timeout for notification requests', 'operational', false),
('operational.http_timeout_voice', '60', 'HTTP timeout for voice transcription requests', 'operational', false),
('operational.servicenow_default_priority', '"3"', 'Default ServiceNow ticket priority', 'operational', false),
('operational.servicenow_default_impact', '"2"', 'Default ServiceNow ticket impact', 'operational', false),
('operational.servicenow_default_urgency', '"2"', 'Default ServiceNow ticket urgency', 'operational', false),
('operational.job_cleanup_retention_hours', '24', 'Hours to retain completed jobs before cleanup', 'operational', false),
('operational.health_check_interval_minutes', '5', 'MCP health check interval (arq cron is compile-time, this is for documentation)', 'operational', false)
ON CONFLICT (key) DO NOTHING;

-- Category: ui (extend existing)
INSERT INTO config_variables (key, value, description, category, is_secret) VALUES
('ui.polling_interval_ms', '3000', 'Frontend polling interval in milliseconds', 'ui', false),
('ui.websocket_reconnect_delay_ms', '3000', 'WebSocket reconnect delay in milliseconds', 'ui', false),
('ui.duration_threshold_fast_seconds', '2', 'Threshold in seconds for fast duration (green)', 'ui', false),
('ui.duration_threshold_medium_seconds', '10', 'Threshold in seconds for medium duration (yellow)', 'ui', false),
('ui.log_error_regex', '"(%OSPF-[45]-\\\\w+|ERROR|FAILED|DOWN)"', 'Regex pattern for error highlighting in logs', 'ui', false),
('ui.pipeline_stages', '[{"key":"voice_input","label":"Voice Input","icon":"mic"},{"key":"intent_parsing","label":"Intent Parsing","icon":"brain"},{"key":"config_generation","label":"Config Generation","icon":"code"},{"key":"ai_advice","label":"AI Advice","icon":"lightbulb"},{"key":"human_decision","label":"Human Decision","icon":"user"},{"key":"baseline_collection","label":"Baseline Collection","icon":"chart"},{"key":"cml_deployment","label":"CML Deployment","icon":"server"},{"key":"monitoring","label":"Monitoring","icon":"activity"},{"key":"splunk_analysis","label":"Splunk Analysis","icon":"search"},{"key":"ai_validation","label":"AI Validation","icon":"check"},{"key":"notifications","label":"Notifications","icon":"bell"}]', 'Pipeline stage definitions for frontend', 'ui', false)
ON CONFLICT (key) DO NOTHING;

-- Log migration
INSERT INTO audit_logs (entity_type, entity_id, action, actor, extra_data)
VALUES ('system', 'database', 'migration_012_dynamic_config', 'system',
        jsonb_build_object('version', '1.0.12', 'timestamp', NOW()::text, 'new_keys', 52));
