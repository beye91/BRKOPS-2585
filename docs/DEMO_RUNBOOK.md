# BRKOPS-2585 Demo Runbook

## Cisco Live Presentation: De-Risk Your Network Using CML, Splunk and MCP Server

**Session:** BRKOPS-2585
**Theme:** "From Chaos to Control"
**Duration:** Demo segment approximately 10-15 minutes

---

## Table of Contents

1. [Pre-Demo Setup](#1-pre-demo-setup)
2. [System Verification](#2-system-verification)
3. [Demo Flow](#3-demo-flow)
4. [Troubleshooting](#4-troubleshooting)
5. [Recovery Procedures](#5-recovery-procedures)

---

## 1. Pre-Demo Setup

### 1.1 Day Before Checklist

**dCloud Environment (198.18.134.22):**
- [ ] Verify dCloud session is active and accessible
- [ ] Verify CML instance (198.18.130.201) is reachable
- [ ] Confirm CML lab is provisioned with OSPF routers
- [ ] Confirm Splunk is receiving logs from CML devices (if configured)
- [ ] Test WebEx webhook is working
- [ ] Review Admin Panel configuration
- [ ] Do a full end-to-end test run

### 1.2 One Hour Before

```bash
# Connect to dCloud environment
# Use provided access method (VPN, RDP, etc.)

# Verify all containers are running
cd ~/brkops-2585
docker compose -f docker-compose.dcloud.yml ps

# Expected output:
# NAME                    STATUS
# brkops-frontend-dcloud  Up
# brkops-backend-dcloud   Up (healthy)
# brkops-postgres-dcloud  Up (healthy)
# brkops-redis-dcloud     Up (healthy)
# cml-mcp-server-dcloud   Up

# Check backend health
curl http://198.18.134.22:8003/health | jq .

# Check frontend is accessible
curl -I http://198.18.134.22:3003

# Check CML MCP Server
curl http://198.18.134.22:9001/mcp
```

### 1.3 Quick Restart if Needed

```bash
# If any container is unhealthy, restart everything
docker compose -f docker-compose.dcloud.yml down
docker compose -f docker-compose.dcloud.yml up -d

# Wait for services to initialize
sleep 30

# Verify again
docker compose -f docker-compose.dcloud.yml ps
```

---

## 2. System Verification

### 2.1 Backend API Health

```bash
# Full health check
curl http://198.18.134.22:8003/health | jq .

# Expected response:
{
  "status": "healthy",
  "service": "brkops-2585-backend",
  "version": "1.0.0"
}
```

### 2.2 MCP Server Connectivity

Open Admin Panel: `http://198.18.134.22:3003/admin`

Navigate to **MCP Servers** tab and verify:
- [ ] CML MCP Server (198.18.134.22:9001): Status shows "Connected"
- [ ] Splunk MCP Server: Status shows "Connected" (if configured)

Click "Test Connection" for each server to confirm.

### 2.3 CML Lab Verification

```bash
# Via API
curl http://198.18.134.22:8003/api/v1/cml/labs | jq .

# Should return list of labs with at least one demo lab
```

In the demo UI, verify:
- [ ] Network Topology loads correctly
- [ ] Devices show as "BOOTED" (green status)

### 2.4 Voice Input Test

1. Open Demo Page: `http://198.18.134.22:3003/demo`
2. Click the microphone button
3. Say: "Test voice input"
4. Verify transcript appears in the interface

### 2.5 Reset CML Lab Configuration

After running demos that modify router configurations, reset all routers to their baseline state:

**Via Admin Panel (Recommended):**
1. Navigate to Admin Panel: `http://198.18.134.22:3003/admin`
2. Select **CML Lab** tab
3. Click **Reset Lab** button (yellow outline)
4. Confirm the dialog

**Via API:**
```bash
# Reset all router configs to default
curl -X POST http://198.18.134.22:8003/api/v1/mcp/cml/labs/{LAB_ID}/reset

# Verify OSPF neighbors are re-established
# (The reset re-applies baseline interface configs and OSPF settings)
```

The reset applies:
- Default interface configurations (GigabitEthernet2-4)
- Correct IP addresses and point-to-point OSPF network types
- OSPF process with proper area 0 networks
- All interfaces brought up (no shutdown)

### 2.6 Pre-Demo Database Reset

If needed, clear previous demo data:

```bash
# Connect to postgres
docker exec -it brkops-postgres-dcloud psql -U brkops -d brkops2585

# Clear previous jobs (optional)
DELETE FROM notifications;
DELETE FROM pipeline_jobs;
\q
```

---

## 3. Demo Flow

### 3.1 Introduction (Browser Setup)

Open two browser windows side-by-side:

**Window 1:** Demo Dashboard
```
http://198.18.134.22:3003/demo
```

**Window 2:** Admin Panel (for showing configuration)
```
http://198.18.134.22:3003/admin
```

### 3.2 Demo Script: OSPF Configuration Change

#### Step 1: Voice Input

**Speaking:** "I want to change the OSPF configuration on Router-1 to use area 10"

**Expected on screen:**
- Waveform visualization shows recording
- Transcript appears in real-time
- Pipeline visualization starts

#### Step 2: Intent Parsing

**Narration:** "The system uses GPT-4 to understand my intent..."

**Expected on screen:**
- Stage 1 (Voice Input) completes with checkmark
- Stage 2 (Intent Parsing) becomes active
- Parsed intent appears showing:
  - Action: Configure OSPF
  - Target: Router-1
  - Parameters: area = 10

#### Step 3: Configuration Generation

**Narration:** "Based on the intent, it generates the appropriate IOS configuration..."

**Expected on screen:**
- Stage 3 (Config Generation) becomes active
- Configuration preview appears:
  ```
  router ospf 1
    network 10.0.0.0 0.0.0.255 area 10
  ```

#### Step 4: CML Deployment

**Narration:** "Now we push this to our digital twin in CML..."

**Expected on screen:**
- Stage 4 (CML Deployment) becomes active
- Topology view highlights Router-1 (pulses cyan)
- Deployment status shows "Pushing configuration..."

#### Step 5: Monitoring

**Narration:** "We wait for the network to converge and collect logs..."

**Expected on screen:**
- Stage 5 (Monitoring) becomes active
- Progress indicator showing wait time
- Log Stream starts populating with syslog entries

#### Step 6: Splunk Analysis

**Narration:** "Splunk MCP server queries for OSPF-related events..."

**Expected on screen:**
- Stage 6 (Splunk Query) becomes active
- SPL query displayed
- Log entries from Splunk appear in Log Stream

#### Step 7: AI Analysis

**Narration:** "The AI analyzes the Splunk results to identify any issues..."

**Expected on screen:**
- Stage 7 (Analysis) becomes active
- Analysis Report panel updates with:
  - **Severity: CRITICAL**
  - **Finding:** Routing loop detected
  - **Affected Devices:** Router-1, Router-2
  - **Root Cause:** Area mismatch
  - **Recommendation:** Use area 0 or update neighbors

#### Step 8: Notifications

**Narration:** "The system automatically notifies the team..."

**Expected on screen:**
- Stage 8 (Notifications) becomes active
- WebEx notification shown as sent
- ServiceNow ticket reference displayed

**Show on mobile/WebEx:** The actual WebEx message received

#### Step 9: Human Decision

**Narration:** "And now the human stays in the loop..."

**Expected on screen:**
- Stage 9 (Human Decision) becomes active
- Approval Panel appears with:
  - Summary of analysis
  - Approve / Reject buttons
  - Optional comment field

**Click:** Reject button

**Narration:** "I'll reject this because the analysis shows it would cause a routing loop. The system learned, the network is safe, and I can enjoy my morning coffee."

### 3.3 Optional: Show Admin Panel

**Narration:** "All of this is configurable through the admin panel..."

Switch to Admin Panel window and briefly show:
- MCP Server configuration
- LLM settings (GPT-4 primary, Claude fallback)
- Use Case templates
- Notification settings

---

## 4. Troubleshooting

### 4.1 Voice Not Working

**Symptom:** Clicking mic button does nothing

**Solution:**
1. Check browser microphone permissions
2. Verify browser is Chrome/Firefox (Safari may have issues)
3. Check backend logs: `docker compose logs backend -f`

### 4.2 Pipeline Stuck

**Symptom:** Pipeline freezes at a stage

**Solution:**
1. Check backend logs for errors
2. Check Redis connection: `docker compose exec redis redis-cli ping`
3. If LLM timeout, check OpenAI/Anthropic API keys in Admin Panel

### 4.3 Topology Not Loading

**Symptom:** Topology shows "Failed to load CML labs"

**Solution:**
1. Check CML MCP server connectivity in Admin Panel
2. Verify CML credentials are correct
3. Test CML MCP endpoint directly:
   ```bash
   curl -X POST http://CML_MCP_URL/tools/get_labs
   ```

### 4.4 No Logs in Splunk

**Symptom:** Log Stream stays empty

**Solution:**
1. Check Splunk MCP server in Admin Panel
2. Verify CML devices are sending syslog to Splunk
3. Check Splunk index configuration

### 4.5 WebSocket Disconnected

**Symptom:** Real-time updates stop, UI shows stale data

**Solution:**
1. Refresh the browser page
2. Check backend WebSocket: `docker compose logs backend | grep websocket`
3. Verify Redis is running: `docker compose ps redis`

---

## 5. Recovery Procedures

### 5.1 Quick Service Restart

```bash
# Restart just the backend (keeps database intact)
docker compose -f docker-compose.dcloud.yml restart backend

# Wait 10 seconds
sleep 10

# Verify health
curl http://198.18.134.22:8003/health
```

### 5.2 Full Stack Restart

```bash
# Stop everything
docker compose -f docker-compose.dcloud.yml down

# Start fresh
docker compose -f docker-compose.dcloud.yml up -d

# Wait for initialization
sleep 30

# Verify all services
docker compose -f docker-compose.dcloud.yml ps
curl http://198.18.134.22:8003/health
```

### 5.3 Reset Lab Configurations

If demo changes broke the lab topology, reset all router configs to baseline:

**Via Admin Panel:**
1. Navigate to Admin Panel > CML Lab tab
2. Click **Reset Lab** button
3. Wait for confirmation (usually within 30 seconds)
4. Verify OSPF neighbors re-establish

**Via API:**
```bash
curl -X POST http://198.18.134.22:8003/api/v1/mcp/cml/labs/{LAB_ID}/reset
```

### 5.4 Database Reset

**Warning:** This clears all data including configuration!

```bash
# Stop services
docker compose -f docker-compose.dcloud.yml down

# Remove postgres volume
docker volume rm brkops-postgres-data-dcloud

# Restart (will re-initialize from scripts)
docker compose -f docker-compose.dcloud.yml up -d
```

### 5.5 Emergency Fallback

If all else fails during the demo:

1. Have pre-recorded video backup ready
2. Switch to showing static screenshots
3. Explain the architecture from slides

---

## Quick Reference Card

### URLs (dCloud Environment)

| Service | URL |
|---------|-----|
| Demo UI | http://198.18.134.22:3003/demo |
| Admin Panel | http://198.18.134.22:3003/admin |
| API Health | http://198.18.134.22:8003/health |
| API Docs | http://198.18.134.22:8003/docs |
| CML MCP Server | http://198.18.134.22:9001 |
| CML Instance | https://198.18.130.201 |

### Commands

```bash
# Navigate to project
cd ~/brkops-2585

# Check status
docker compose -f docker-compose.dcloud.yml ps

# View logs
docker compose -f docker-compose.dcloud.yml logs -f backend
docker compose -f docker-compose.dcloud.yml logs -f frontend
docker logs cml-mcp-server-dcloud

# Restart
docker compose -f docker-compose.dcloud.yml restart backend

# Full restart
docker compose -f docker-compose.dcloud.yml down && docker compose -f docker-compose.dcloud.yml up -d
```

### Demo Voice Commands

1. "I want to change OSPF on Router-1 to area 10"
2. "Rotate credentials on all datacenter switches"
3. "Apply security advisory to affected routers"

---

## Post-Demo

### Cleanup

```bash
# Optional: Clear demo data
docker exec -it brkops-postgres-dcloud psql -U brkops -d brkops2585 -c "DELETE FROM pipeline_jobs"
```

### Collect Feedback

- Note any issues encountered
- Document workarounds used
- Update this runbook as needed

---

**End of Runbook**
