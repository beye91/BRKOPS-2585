-- =============================================================================
-- Migration 004: Deduplicate MCP servers and add unique constraint
-- =============================================================================
-- Problem: mcp_servers table had no unique constraint on (name, type),
-- allowing duplicate entries to be created. The seed data ON CONFLICT DO NOTHING
-- also had no effect without a unique constraint.
-- =============================================================================

-- Step 1: Remove duplicate entries, keeping only the most recently updated one
DELETE FROM mcp_servers a
USING mcp_servers b
WHERE a.id < b.id
  AND a.name = b.name
  AND a.type = b.type;

-- Step 2: Remove inactive duplicates where an active version exists
-- (e.g., old Splunk entry pointing to docker internal URL)
DELETE FROM mcp_servers
WHERE is_active = false
  AND name IN (
    SELECT name FROM mcp_servers
    GROUP BY name, type
    HAVING COUNT(*) > 1
  );

-- Step 3: Add unique constraint on (name, type)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mcp_servers_name_type
ON mcp_servers(name, type);

-- Step 4: Update Splunk Primary endpoint if still pointing to old docker URL
-- IMPORTANT: Only update endpoint, NEVER overwrite auth_config (contains API token)
UPDATE mcp_servers
SET endpoint = 'https://198.18.133.50:8089/services/mcp',
    is_active = true
WHERE name = 'Splunk Primary'
  AND type = 'splunk'
  AND endpoint = 'http://splunk-mcp-server:8080';
