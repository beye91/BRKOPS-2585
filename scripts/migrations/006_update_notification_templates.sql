-- Migration 006: Update notification templates with formatted issues, AI recommendations, and rollback guidance
-- Fixes: WebEx notifications showing literal {{issues}} instead of actual issue details
-- Adds: {{recommendation}}, {{rollback_action}} placeholders to all templates

-- Update OSPF Configuration Change
UPDATE use_cases
SET notification_template = '{
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
}'
WHERE name = 'ospf_configuration_change';

-- Update Credential Rotation
UPDATE use_cases
SET notification_template = '{
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
}'
WHERE name = 'credential_rotation';

-- Update Security Advisory Response
UPDATE use_cases
SET notification_template = '{
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
}'
WHERE name = 'security_advisory';
