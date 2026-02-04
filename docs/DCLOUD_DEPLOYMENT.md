# BRKOPS-2585 dCloud Deployment Guide

## Overview

This guide covers deploying the BRKOPS-2585 platform on Cisco dCloud environment.

## dCloud Environment Details

| Component | Address | Credentials |
|-----------|---------|-------------|
| dCloud Host | 198.18.134.22 | - |
| CML Instance | 198.18.130.201 | admin / C1sco12345 |
| Frontend | :3003 | - |
| Backend API | :8003 | - |
| CML MCP Server | :9001 | - |
| PostgreSQL | :5434 | brkops / brkops2585dcloud |
| Redis | :6380 | - |

## Files for dCloud Deployment

- `docker-compose.dcloud.yml` - Docker Compose configuration for dCloud
- `.env.dcloud` - Environment variables for dCloud
- `scripts/deploy-dcloud.sh` - Automated deployment script

## Quick Deployment

### Option 1: Using the Deployment Script

```bash
# Copy project to dCloud host
scp -r /path/to/brkops-2585 user@198.18.134.22:~/

# SSH to dCloud host
ssh user@198.18.134.22

# Run deployment script
cd ~/brkops-2585
chmod +x scripts/deploy-dcloud.sh
./scripts/deploy-dcloud.sh
```

### Option 2: Manual Deployment

```bash
# 1. Copy project to dCloud host
cd ~/brkops-2585

# 2. Copy environment file
cp .env.dcloud .env

# 3. Build containers (no cache)
docker compose -f docker-compose.dcloud.yml build --no-cache

# 4. Start infrastructure services first
docker compose -f docker-compose.dcloud.yml up -d postgres redis

# 5. Wait for database to be ready
sleep 15

# 6. Start backend
docker compose -f docker-compose.dcloud.yml up -d backend

# 7. Wait for backend to be healthy
sleep 15

# 8. Start frontend
docker compose -f docker-compose.dcloud.yml up -d frontend

# 9. Deploy CML MCP Server
docker run -d \
  --name cml-mcp-server-dcloud \
  --restart unless-stopped \
  --network brkops-dcloud-network \
  -p 9001:9001 \
  -e CML_MCP_TRANSPORT=http \
  -e CML_MCP_BIND=0.0.0.0 \
  -e CML_MCP_PORT=9001 \
  -e CML_URL=https://198.18.130.201 \
  -e CML_USERNAME=admin \
  -e CML_PASSWORD=C1sco12345 \
  -e CML_VERIFY_SSL=false \
  -e PYATS_USERNAME=admin \
  -e PYATS_PASSWORD=cisco \
  -e DEBUG=false \
  xorrkaz/cml-mcp:latest

# 10. Verify deployment
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

## Verification

### Check Container Status

```bash
docker ps --filter name=brkops --filter name=cml-mcp
```

Expected output:
```
NAMES                    STATUS              PORTS
brkops-frontend-dcloud   Up (healthy)        0.0.0.0:3003->3000/tcp
brkops-backend-dcloud    Up (healthy)        0.0.0.0:8003->8000/tcp
brkops-postgres-dcloud   Up (healthy)        0.0.0.0:5434->5432/tcp
brkops-redis-dcloud      Up (healthy)        0.0.0.0:6380->6379/tcp
cml-mcp-server-dcloud    Up                  0.0.0.0:9001->9001/tcp
```

### Check Backend Health

```bash
curl http://198.18.134.22:8003/health
```

Expected:
```json
{"status":"healthy","service":"brkops-2585-backend","version":"1.0.0"}
```

### Check Frontend

Open in browser: `http://198.18.134.22:3003`

### Check CML MCP Server

```bash
curl http://198.18.134.22:9001/mcp
```

Expected: JSON-RPC response (may show session error, which is normal)

### Check CML MCP Server Logs

```bash
docker logs cml-mcp-server-dcloud
```

Should show: "All tools registered successfully"

## Configuration

### LLM API Keys

You need to configure OpenAI and/or Anthropic API keys for the LLM features to work.

**Option 1: Via Admin Panel**
1. Open: http://198.18.134.22:3003/admin
2. Go to Configuration section
3. Add your API keys

**Option 2: Via Environment Variables**
Edit `.env.dcloud` before deployment:
```
OPENAI_API_KEY=sk-your-actual-key
ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### WebEx Notifications

Configure WebEx webhook URL in Admin Panel or `.env.dcloud`:
```
WEBEX_WEBHOOK_URL=https://webexapis.com/v1/webhooks/incoming/your-webhook-id
```

### ServiceNow Integration (Optional)

Configure in Admin Panel or `.env.dcloud`:
```
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your-password
```

## URLs After Deployment

| Service | URL |
|---------|-----|
| Demo Dashboard | http://198.18.134.22:3003/demo |
| Admin Panel | http://198.18.134.22:3003/admin |
| Backend API | http://198.18.134.22:8003 |
| API Documentation | http://198.18.134.22:8003/docs |
| CML MCP Server | http://198.18.134.22:9001 |

## Troubleshooting

### Backend Won't Start

Check logs:
```bash
docker logs brkops-backend-dcloud
```

Common issues:
- Database not ready: Wait longer before starting backend
- Missing environment variables: Check `.env` file exists

### Frontend Shows "Disconnected"

This is the WebSocket connection status. It should connect when:
- Backend is healthy
- Correct API URL is configured in frontend

Check frontend build args match environment:
```bash
docker inspect brkops-frontend-dcloud | grep NEXT_PUBLIC
```

### CML MCP Server Not Connecting

Check logs:
```bash
docker logs cml-mcp-server-dcloud
```

Common issues:
- CML instance unreachable from dCloud network
- Wrong credentials
- SSL verification issues (already disabled with CML_VERIFY_SSL=false)

### Reset Everything

```bash
# Stop all containers
docker compose -f docker-compose.dcloud.yml down
docker stop cml-mcp-server-dcloud
docker rm cml-mcp-server-dcloud

# Remove volumes (WARNING: Deletes all data)
docker volume rm brkops-postgres-data-dcloud brkops-redis-data-dcloud brkops-backend-uploads-dcloud

# Start fresh
./scripts/deploy-dcloud.sh
```

## Architecture Diagram

```
dCloud Environment (198.18.134.22)
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐│
│  │   Frontend     │  │    Backend     │  │    CML MCP Server          ││
│  │   :3003        │◄─┤    :8003       │──┤    :9001                   ││
│  │   Next.js      │  │   FastAPI      │  │    xorrkaz/cml-mcp         ││
│  └────────────────┘  └───────┬────────┘  └─────────────┬──────────────┘│
│                              │                         │                │
│  ┌────────────────┐  ┌───────┴────────┐                │                │
│  │   PostgreSQL   │  │     Redis      │                │                │
│  │   :5434        │  │     :6380      │                │                │
│  └────────────────┘  └────────────────┘                │                │
│                                                         │                │
└─────────────────────────────────────────────────────────┼────────────────┘
                                                          │
                                              ┌───────────▼───────────────┐
                                              │   CML Instance            │
                                              │   198.18.130.201          │
                                              │   admin / C1sco12345      │
                                              └───────────────────────────┘
```
