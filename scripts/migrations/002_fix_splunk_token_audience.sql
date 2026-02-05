-- =============================================================================
-- BRKOPS-2585: Fix Splunk JWT Token Audience
-- Migration: 002
-- Description: Update Splunk MCP server configuration with correct JWT token
--
-- IMPORTANT: This migration template needs a valid JWT token from Splunk.
-- The token must be generated with audience="mcp" for MCP server authentication.
--
-- To generate a new token in Splunk:
-- 1. SSH to Splunk server
-- 2. Go to Settings > Tokens (or use CLI)
-- 3. Create a new token with:
--    - Name: brkops-mcp
--    - Audience: mcp  (CRITICAL!)
--    - Expires: as needed
-- 4. Copy the token and replace <YOUR_JWT_TOKEN_HERE> below
-- =============================================================================

-- Update Splunk server endpoint and enable it
-- Replace <YOUR_JWT_TOKEN_HERE> with the actual JWT token from Splunk
UPDATE mcp_servers
SET
    endpoint = 'http://splunk-mcp-server:8080',
    auth_config = jsonb_build_object(
        'host', 'https://splunk.example.com:8089',
        'token', '<YOUR_JWT_TOKEN_HERE>'
    ),
    is_active = true,
    health_status = 'unknown'
WHERE type = 'splunk';

-- If Splunk server doesn't exist, insert it
INSERT INTO mcp_servers (name, type, endpoint, auth_config, is_active)
SELECT
    'Splunk Primary',
    'splunk',
    'http://splunk-mcp-server:8080',
    '{"host": "https://splunk.example.com:8089", "token": "<YOUR_JWT_TOKEN_HERE>"}',
    true
WHERE NOT EXISTS (SELECT 1 FROM mcp_servers WHERE type = 'splunk');

-- Log the migration
INSERT INTO audit_logs (entity_type, entity_id, action, actor, extra_data)
VALUES (
    'migration',
    '002_fix_splunk_token_audience',
    'applied',
    'system',
    jsonb_build_object(
        'description', 'Updated Splunk MCP server with correct JWT token audience',
        'timestamp', NOW()::text
    )
);
