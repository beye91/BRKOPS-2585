# BRKOPS-2585 Platform Architecture

## De-Risk Your Network Using CML, Splunk and MCP Server

**Version:** 2.0.0
**Last Updated:** 2026-02-03
**Architecture:** Simplified 4-Container Design

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Service Definitions](#3-service-definitions)
4. [Database Schema](#4-database-schema)
5. [API Specification](#5-api-specification)
6. [Real-Time Events](#6-real-time-events)
7. [MCP Integration](#7-mcp-integration)
8. [Deployment](#8-deployment)
9. [Demo Scenarios](#9-demo-scenarios)

---

## 1. Overview

### 1.1 Purpose

This platform enables AI-driven network operations demonstration for Cisco Live BRKOPS-2585. It showcases how voice-to-intent workflows, combined with CML (Cisco Modeling Labs) digital twins and Splunk observability, can de-risk network changes.

**Theme:** "From Chaos to Control"
**Audience:** Hundreds of network engineers at Cisco Live

### 1.2 Key Capabilities

- Voice-to-text intent capture (OpenAI Whisper)
- AI-powered intent interpretation (GPT-4 + Claude fallback)
- Automated configuration generation
- CML-based configuration validation via MCP
- Splunk-based log analysis via MCP
- Intelligent result analysis and recommendations
- Multi-channel notifications (WebEx, ServiceNow)
- Human-in-the-loop approval workflow

### 1.3 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TailwindCSS, Framer Motion |
| Backend | FastAPI (Python), arq (async Redis queue) |
| Database | PostgreSQL 16, Redis 7 |
| AI/LLM | OpenAI GPT-4 / Anthropic Claude (fallback) |
| Voice | OpenAI Whisper API |
| MCP | External CML MCP Server, Splunk MCP Server |
| Infrastructure | Docker Compose (4 containers) |

---

## 2. System Architecture

### 2.1 High-Level Architecture (4 Containers)

```
+====================================================================================+
|                    BRKOPS-2585 PLATFORM (Optimized - 4 Containers)                 |
+====================================================================================+
|                                                                                    |
|  +-------------------------------------------------------------------------------+ |
|  |                         FRONTEND (Next.js :3000)                              | |
|  |  +-------------+ +-------------+ +-------------+ +-----------------------+    | |
|  |  |  Demo Page  | | Voice Input | |  Pipeline   | |  Admin Panel          |    | |
|  |  |  Dashboard  | |  Waveform   | |  Visualizer | |  Config Management    |    | |
|  |  +-------------+ +-------------+ +-------------+ +-----------------------+    | |
|  |  +-------------+ +-------------+ +-------------+                              | |
|  |  |  Topology   | | Log Stream  | |  Analysis   |  WebSocket <-----------+    | |
|  |  |    Graph    | |  (Splunk)   | |   Report    |  Connection            |    | |
|  |  +-------------+ +-------------+ +-------------+                        |    | |
|  +-------------------------------------------------------------------------+----+ |
|                                                                            |      |
|  +-------------------------------------------------------------------------v----+ |
|  |                         BACKEND (FastAPI :8000)                              | |
|  |                                                                              | |
|  |   +-------------+  +-------------+  +-------------+  +-------------+        | |
|  |   |   REST API  |  |Orchestrator |  | LLM Service |  |   Voice     |        | |
|  |   |   Routers   |  |State Machine|  | GPT-4/Claude|  |  Whisper    |        | |
|  |   +-------------+  +-------------+  +-------------+  +-------------+        | |
|  |                                                                              | |
|  |   +-------------+  +-------------+  +-------------+  +-------------+        | |
|  |   | CML Client  |  |Splunk Client|  | Notification|  | arq Worker  |        | |
|  |   | MCP Bridge  |  | MCP Bridge  |  | WebEx/SNOW  |  | Background  |        | |
|  |   +------+------+  +------+------+  +-------------+  +-------------+        | |
|  +----------|----------------|--------------------------------------------------+ |
|             |                |                                                    |
|  +----------v----------------v--------------------------------------------------+ |
|  |                      EXTERNAL MCP SERVERS                                    | |
|  |       +-------------------+          +-------------------+                   | |
|  |       |  CML MCP Server   |          | Splunk MCP Server |                   | |
|  |       |    (47 tools)     |          |    (11 tools)     |                   | |
|  |       |  Labs, Nodes, CLI |          |  SPL, Queries     |                   | |
|  |       +-------------------+          +-------------------+                   | |
|  +------------------------------------------------------------------------------+ |
|                                                                                    |
|  +------------------------------------------------------------------------------+ |
|  |                           DATA LAYER                                         | |
|  |       +-------------------+          +-------------------+                   | |
|  |       |    PostgreSQL     |          |      Redis        |                   | |
|  |       |      :5432        |          |      :6379        |                   | |
|  |       | Config, Jobs, Logs|          | PubSub, Cache     |                   | |
|  |       +-------------------+          +-------------------+                   | |
|  +------------------------------------------------------------------------------+ |
+====================================================================================+
```

### 2.2 Demo Pipeline Flow (11 Stages)

**Key Design:** Human approval happens BEFORE deployment, not after!
Baseline collection captures network state before changes for comparison.

```
+--------------------------------------------------------------------------------+
|                              DEMO PIPELINE FLOW                                |
|           (Human Approval BEFORE Deployment + Baseline Collection)             |
+--------------------------------------------------------------------------------+
|                                                                                |
|  Stage 1: VOICE INPUT                                                         |
|  +--------------------------------------------------------------------------+ |
|  |  "I want to change OSPF configuration on Router-X to use area 10"        | |
|  |     --> Whisper API --> Transcript --> WebSocket to Frontend             | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 2: INTENT PARSING (LLM)                                                |
|  +--------------------------------------------------------------------------+ |
|  |  GPT-4 analyzes transcript:                                              | |
|  |  * Action: MODIFY_OSPF_CONFIG                                            | |
|  |  * Target: Router-X                                                      | |
|  |  * Parameters: area_id=10 (was 0)                                        | |
|  |  * Confidence: 94%                                                       | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 3: CONFIG GENERATION (LLM)                                             |
|  +--------------------------------------------------------------------------+ |
|  |  router ospf 1                                                           | |
|  |    network 10.0.0.0 0.0.0.255 area 10                                    | |
|  |  ! Changed from area 0 to area 10                                        | |
|  |  ! Rollback commands also generated                                      | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 4: AI ADVICE (LLM)                                                     |
|  +--------------------------------------------------------------------------+ |
|  |  GPT-4 reviews proposed changes:                                         | |
|  |  * Risk Level: MEDIUM                                                    | |
|  |  * Risk Factors: OSPF area change causes neighbor adjacency reset        | |
|  |  * Mitigation: Ensure backup paths exist                                 | |
|  |  * Recommendation: APPROVE                                               | |
|  |  * Pre-checks: Verify current OSPF state, confirm rollback commands      | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 5: HUMAN DECISION                                                      |
|  +--------------------------------------------------------------------------+ |
|  |  Engineer reviews AI Advice and proposed config:                         | |
|  |  [Approve & Deploy] [Reject]                                             | |
|  |                                                                          | |
|  |  -> Pipeline PAUSES here until human approves                            | |
|  |  -> NO deployment has occurred yet!                                      | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v (only if approved)                     |
|  Stage 6: BASELINE COLLECTION (MCP)                                           |
|  +--------------------------------------------------------------------------+ |
|  |  Collect current network state BEFORE deployment:                        | |
|  |  * OSPF neighbors (count, states)                                        | |
|  |  * Interface status (up/down)                                            | |
|  |  * OSPF routes                                                           | |
|  |  -> This "before" snapshot enables diff comparison                       | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 7: CML DEPLOYMENT (MCP)                                                |
|  +--------------------------------------------------------------------------+ |
|  |  CML MCP Server Tools:                                                   | |
|  |  * get_labs() -> Find target lab                                         | |
|  |  * get_nodes() -> Find Router-X                                          | |
|  |  * apply_config() -> Push OSPF configuration                             | |
|  |  * run_command() -> Verify config applied                                | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 8: MONITORING (Wait + Diff Comparison)                                 |
|  +--------------------------------------------------------------------------+ |
|  |  * Wait 30-60 seconds for convergence                                    | |
|  |  * Collect post-deployment state (OSPF, interfaces, routes)              | |
|  |  * Compare with baseline: before/after diff calculated                   | |
|  |  * Determine if deployment is "healthy" based on diff                    | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 9: SPLUNK ANALYSIS (MCP)                                               |
|  +--------------------------------------------------------------------------+ |
|  |  Splunk MCP Server Tools:                                                | |
|  |  * generate_spl("OSPF errors in last 60 seconds")                        | |
|  |  * run_splunk_query() -> Execute SPL, get results                        | |
|  |  * Results: Post-deployment telemetry collected                          | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 10: AI VALIDATION (LLM)                                                |
|  +--------------------------------------------------------------------------+ |
|  |  GPT-4 validates deployment results using baseline diff:                 | |
|  |  * Validation Status: PASSED / WARNING / FAILED                          | |
|  |  * Diff Analysis: Neighbors +0, Interfaces +0, Routes +2                 | |
|  |  * Findings: OSPF neighbors stable, routes increased (expected)          | |
|  |  * Deployment Verified: TRUE                                             | |
|  +--------------------------------------------------------------------------+ |
|                                       |                                        |
|                                       v                                        |
|  Stage 11: NOTIFICATIONS                                                      |
|  +--------------------------------------------------------------------------+ |
|  |  WebEx: "Configuration deployed successfully. All health checks passed." | |
|  |  ServiceNow: Auto-create change record with validation results           | |
|  +--------------------------------------------------------------------------+ |
|                                                                                |
+--------------------------------------------------------------------------------+
```

### 2.3 Component Communication

```
                    INTER-SERVICE COMMUNICATION

+------------+          REST/WS           +------------+
|  Frontend  |<-------------------------->|   Backend  |
|  Next.js   |                            |   FastAPI  |
+------------+                            +------+-----+
                                                 |
                         +-----------------------+------------------------+
                         |                       |                        |
                         v                       v                        v
                  +------------+          +------------+          +------------+
                  | PostgreSQL |          |   Redis    |          | MCP Bridge |
                  |   :5432    |          |   :6379    |          |   (HTTP)   |
                  +------------+          +------------+          +------+-----+
                                                                         |
                                                 +-----------------------+
                                                 |                       |
                                                 v                       v
                                          +----------+           +----------+
                                          | CML MCP  |           |Splunk MCP|
                                          | Server   |           | Server   |
                                          +----------+           +----------+
```

---

## 3. Service Definitions

### 3.1 Service Matrix (4 Containers)

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| `frontend` | 3000 | Next.js 14 | Demo UI, Voice Interface, Topology View, Admin Panel |
| `backend` | 8000 | FastAPI + arq | API + Background job processing (single container) |
| `postgres` | 5432 | PostgreSQL 16 | Configuration, jobs, audit logs |
| `redis` | 6379 | Redis 7 | Job queue + pub/sub for real-time events |

### 3.2 Backend Architecture

The backend runs two processes in a single container:

1. **FastAPI Server** (`uvicorn main:app`)
   - REST API endpoints
   - WebSocket connections
   - Request handling

2. **arq Worker** (`arq worker.WorkerSettings`)
   - Background job processing
   - Pipeline stage execution
   - Async task handling

```
backend/
|-- main.py                    # FastAPI app entry point
|-- worker.py                  # arq worker entry point
|-- config.py                  # Environment config
|-- routers/
|   |-- operations.py          # Pipeline start/status/approve
|   |-- voice.py               # Whisper transcription
|   |-- mcp.py                 # CML + Splunk MCP interface
|   |-- notifications.py       # WebEx, ServiceNow
|   |-- admin.py               # Configuration management
|   +-- jobs.py                # Job queue status/history
|-- tasks/
|   +-- pipeline.py            # Main pipeline orchestration (9 stages)
|-- services/
|   |-- llm_service.py         # GPT-4 + Claude with fallback
|   |-- cml_client.py          # CML MCP Server client
|   |-- splunk_client.py       # Splunk MCP Server client
|   |-- voice_service.py       # Whisper API integration
|   |-- notification_service.py # WebEx/ServiceNow delivery
|   +-- websocket_manager.py   # Real-time event broadcasting
|-- models/                    # Pydantic schemas
+-- db/                        # SQLAlchemy models + database
```

### 3.3 Frontend Architecture

```
frontend/
|-- src/
|   |-- app/                   # Next.js 14 app router
|   |   |-- page.tsx           # Home page
|   |   |-- demo/page.tsx      # Demo dashboard
|   |   +-- admin/page.tsx     # Admin panel
|   |-- components/
|   |   |-- Pipeline.tsx       # 9-stage visualization
|   |   |-- VoiceInput.tsx     # Mic button + waveform
|   |   |-- Topology.tsx       # Network graph (React Flow)
|   |   |-- LogStream.tsx      # Real-time logs
|   |   |-- AnalysisReport.tsx # AI findings panel
|   |   +-- ApprovalPanel.tsx  # Human decision UI
|   |-- store/
|   |   |-- websocket.ts       # WebSocket state
|   |   +-- operations.ts      # Operation state
|   +-- services/
|       +-- api.ts             # API client
```

---

## 4. Database Schema

### 4.1 Entity Relationship

```
+------------------+       +------------------+       +------------------+
| config_variables |       |   mcp_servers    |       |    use_cases     |
+------------------+       +------------------+       +------------------+
| PK id            |       | PK id            |       | PK id            |
|    key (unique)  |       |    name          |       |    name          |
|    value (JSONB) |       |    type          |       |    description   |
|    description   |       |    endpoint      |       |    intent_prompt |
|    category      |       |    auth_config   |       |    config_prompt |
|    is_secret     |       |    is_active     |       |    analysis_prompt|
|    created_at    |       |    health_status |       |    notification_ |
|    updated_at    |       |    last_check    |       |      template    |
+------------------+       +------------------+       |    is_active     |
                                                      +--------+---------+
                                                               |
+------------------+                                           |
|  pipeline_jobs   |<------------------------------------------+
+------------------+
| PK id (UUID)     |
| FK use_case_id   |
|    input_text    |
|    audio_url     |
|    current_stage |
|    status        |
|    stages_data   |
|    result        |
|    error_message |
|    started_at    |
|    completed_at  |
|    created_by    |
+--------+---------+
         |
         |  1:n
         v
+------------------+       +------------------+       +------------------+
|  notifications   |       |   audit_logs     |       |     users        |
+------------------+       +------------------+       +------------------+
| PK id            |       | PK id            |       | PK id            |
| FK job_id        |       |    action        |       |    username      |
|    channel       |       |    entity_type   |       |    password_hash |
|    recipient     |       |    entity_id     |       |    email         |
|    message       |       |    user_id       |       |    role          |
|    status        |       |    details       |       |    is_active     |
|    response_data |       |    ip_address    |       |    last_login    |
|    sent_at       |       |    created_at    |       |    created_at    |
+------------------+       +------------------+       +------------------+
```

### 4.2 Key Tables

**config_variables** - All platform configuration (nothing hardcoded)
```sql
CREATE TABLE config_variables (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(100),
    is_secret BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**pipeline_jobs** - Pipeline execution state
```sql
CREATE TABLE pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id INTEGER REFERENCES use_cases(id),
    input_text TEXT NOT NULL,
    input_audio_url TEXT,
    current_stage VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    stages_data JSONB DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by VARCHAR(100)
);
```

---

## 5. API Specification

### 5.1 REST Endpoints

```
/api/v1/
|-- /operations
|   |-- POST   /start           # Start new operation (voice or text)
|   |-- GET    /{id}            # Get operation status
|   |-- POST   /{id}/approve    # Human approval
|   |-- POST   /{id}/reject     # Human rejection
|   |-- POST   /{id}/rollback   # Execute rollback of deployed config
|   +-- DELETE /{id}            # Cancel operation
|
|-- /voice
|   +-- POST   /transcribe      # Upload audio for transcription
|
|-- /mcp
|   |-- GET    /servers         # List MCP servers
|   |-- GET    /tools           # List available tools
|   +-- POST   /execute         # Execute MCP tool
|
|-- /cml
|   |-- GET    /labs            # List labs
|   |-- GET    /labs/{id}/nodes # List nodes in lab
|   +-- GET    /topology/{id}   # Get topology for visualization
|
|-- /splunk
|   |-- POST   /query           # Execute SPL query
|   +-- POST   /generate-spl    # Natural language to SPL
|
|-- /notifications
|   |-- POST   /webex           # Send WebEx message
|   |-- POST   /servicenow      # Create ServiceNow ticket
|   +-- GET    /history         # Notification history
|
|-- /admin
|   |-- GET    /config          # Get all configuration
|   |-- PUT    /config/{key}    # Update configuration
|   |-- GET    /use-cases       # Get use case templates
|   +-- PUT    /use-cases/{id}  # Update use case
|
|-- /jobs
|   |-- GET    /                # List all jobs
|   |-- GET    /{id}            # Get job details
|   +-- POST   /{id}/retry      # Retry failed job
|
+-- /health                      # Health check endpoint
```

### 5.2 WebSocket Events

```
ws://api/events

Events:
|-- operation.started           # New operation began
|-- operation.stage_changed     # Pipeline stage transition
|-- operation.completed         # Operation finished
|-- operation.error             # Error occurred
|-- operation.rollback.started  # Rollback execution started
|-- operation.rollback.completed # Rollback completed successfully
|-- operation.rollback.failed   # Rollback execution failed
|-- voice.transcript_update     # Live transcription
|-- voice.intent_detected       # Intent parsed
|-- config.generated            # Config ready
|-- cml.deployment_started      # Pushing to CML
|-- cml.deployment_complete     # CML config applied
|-- splunk.query_started        # Splunk query running
|-- splunk.results_ready        # Splunk results available
|-- analysis.started            # AI analysis begun
|-- analysis.complete           # Findings ready
|-- notification.sent           # WebEx/ServiceNow sent
+-- log.entry                   # Real-time log entry
```

---

## 6. Real-Time Events

### 6.1 Event Flow

```
                         REAL-TIME EVENT FLOW

+----------+                                                +----------+
| Frontend |                                                | Backend  |
+----+-----+                                                | (arq)    |
     |                                                      +-----+----+
     |  Connect WebSocket                                         |
     |------------------------->+----------+                      |
     |                          |  FastAPI |                      |
     |  Subscribe to operation  |WebSocket |                      |
     |  {"operation_id": "abc"} |          |                      |
     |------------------------->|          |                      |
     |                          |          |                      |
     |                          |          |  Redis PubSub        |
     |                          |          |<---------------------+
     |                          |          |  stage_changed       |
     |                          |          |                      |
     |  operation.stage_changed |          |                      |
     |<-------------------------|          |                      |
     |                          |          |                      |
     |                          |          |  analysis.complete   |
     |                          |          |<---------------------+
     |                          |          |                      |
     |  analysis.complete       |          |                      |
     |<-------------------------|          |                      |
     |                          +----------+                      |
     |                                                            |
```

---

## 7. MCP Integration

### 7.1 CML MCP Server Tools

| Category | Tool | Description |
|----------|------|-------------|
| Lab Management | `get_labs` | List all labs |
| Lab Management | `start_lab` | Start lab |
| Lab Management | `stop_lab` | Stop lab |
| Node Management | `get_nodes` | List nodes in lab |
| Node Management | `apply_config` | Push configuration |
| Node Management | `run_command` | Execute CLI command |
| Topology | `get_topology` | Get topology data |

### 7.2 Splunk MCP Server Tools

| Tool | Description |
|------|-------------|
| `generate_spl` | Natural language to SPL |
| `run_query` | Execute SPL query |
| `explain_spl` | SPL to plain English |
| `get_indexes` | List available indexes |

### 7.3 MCP Client Architecture

```python
class CMLClient:
    """CML MCP Server client with fallback and retry"""

    async def get_labs(self) -> List[Lab]:
        return await self._call_mcp("get_labs", {})

    async def apply_config(self, lab_id: str, node: str, config: str):
        return await self._call_mcp("apply_config", {
            "lab_id": lab_id,
            "node": node,
            "config": config
        })

    async def _call_mcp(self, tool: str, params: dict):
        # HTTP call to MCP server with retry logic
        pass
```

---

## 8. Deployment

### 8.1 Docker Compose (4 Services)

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_WS_URL=ws://backend:8000
    depends_on: [backend]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=...
      - ANTHROPIC_API_KEY=...
      - CML_MCP_URL=...
      - SPLUNK_MCP_URL=...
    depends_on: [postgres, redis]

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./scripts/seed-data.sql:/docker-entrypoint-initdb.d/02-seed.sql

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 8.2 Deployment Target

- **Host:** 192.168.1.213
- **User:** cbeye (SSH key auth enabled)
- **Deploy Path:** /opt/brkops-2585

### 8.3 Deploy Command

```bash
# Quick deploy
make deploy

# Or manually
ssh cbeye@192.168.1.213 "cd /opt/brkops-2585 && \
  docker compose down && \
  docker compose build --no-cache && \
  docker compose up -d"
```

---

## 9. CML Lab Topology

### 9.1 BRKOPS-2585 Demo Lab

The demo uses a 4-router full mesh topology with Cat8000v devices.

```
                    External Connector (bridge1)
                           |
            +--------------+--------------+
            |              |              |
    +-------+---+   +------+----+   +-----+-----+   +-----------+
    |  Router-1 |---|  Router-2 |---|  Router-3 |---|  Router-4 |
    | Cat8000v  |   | Cat8000v  |   | Cat8000v  |   | Cat8000v  |
    |198.18.1.201|   |198.18.1.202|   |198.18.1.203|   |198.18.1.204|
    +-----+-----+   +-----+-----+   +-----+-----+   +-----+-----+
          |               |               |               |
          +---------------+---------------+---------------+
                        Full Mesh (6 Links)

    Links:
    - R1 <-> R2 (10.1.12.0/30)
    - R1 <-> R3 (10.1.13.0/30)
    - R1 <-> R4 (10.1.14.0/30)
    - R2 <-> R3 (10.1.23.0/30)
    - R2 <-> R4 (10.1.24.0/30)
    - R3 <-> R4 (10.1.34.0/30)
```

### 9.2 IP Addressing

| Router   | Management IP    | Loopback0        | OSPF Router-ID |
|----------|------------------|------------------|----------------|
| Router-1 | 198.18.1.201/24  | 10.255.255.1/32  | 10.255.255.1   |
| Router-2 | 198.18.1.202/24  | 10.255.255.2/32  | 10.255.255.2   |
| Router-3 | 198.18.1.203/24  | 10.255.255.3/32  | 10.255.255.3   |
| Router-4 | 198.18.1.204/24  | 10.255.255.4/32  | 10.255.255.4   |

### 9.3 Lab Features

| Feature | Configuration |
|---------|---------------|
| OSPF | Area 0, point-to-point network type |
| MDT Telemetry | CPU, memory, interfaces, OSPF to 198.18.134.22:57400 |
| Syslog | Forwarding to 198.18.134.22:514 |
| SNMP | Communities: public (RO), private (RW) |
| NETCONF/YANG | Enabled for programmatic access |

### 9.4 Lab Management API

New endpoints for CML lab management:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mcp/cml/labs/demo-status` | Check demo lab status |
| POST | `/api/v1/mcp/cml/labs/build-demo` | Build the demo lab |
| POST | `/api/v1/mcp/cml/labs/create` | Create lab from YAML |
| POST | `/api/v1/mcp/cml/labs/{lab_id}/start` | Start a lab |
| POST | `/api/v1/mcp/cml/labs/{lab_id}/stop` | Stop a lab |
| DELETE | `/api/v1/mcp/cml/labs/{lab_id}` | Delete a lab |
| GET | `/api/v1/mcp/cml/labs/{lab_id}/status` | Get detailed lab status |
| GET | `/api/v1/mcp/cml/labs/{lab_id}/topology` | Get topology for visualization |

### 9.5 Lab Files

The CML lab topology and configurations are stored in `/cml-lab/`:

| File | Purpose |
|------|---------|
| `brkops-ospf-demo.yaml` | CML topology definition |
| `configs/router-1.cfg` | Router-1 startup config |
| `configs/router-2.cfg` | Router-2 startup config |
| `configs/router-3.cfg` | Router-3 startup config |
| `configs/router-4.cfg` | Router-4 startup config |

---

## 10. Demo Scenarios

### 10.1 OSPF Configuration Change (Primary Demo)

**Voice:** "I want to change OSPF on Router-1 to area 10"

**Flow:**
1. Whisper transcribes voice
2. GPT-4 parses intent (router: Router-1, area: 10)
3. Config generated (router ospf commands)
4. Pushed to CML via MCP
5. Wait 45s for convergence
6. Query Splunk for OSPF logs
7. Analysis detects routing loop (intentional)
8. WebEx notification sent
9. Human approves/rejects

### 10.2 Credential Rotation

**Voice:** "Rotate credentials on all datacenter switches"

**Flow:**
1. Intent: credential rotation, scope: datacenter
2. Generate new credentials
3. Push to all switches in CML
4. Validate connectivity
5. Report success/failure
6. ServiceNow ticket for compliance

### 10.3 Security Advisory

**Voice:** "Apply security advisory to affected routers"

**Flow:**
1. Load advisory template
2. Identify affected devices
3. Push security config
4. Check for conflicts
5. Report partial success
6. Urgent notification

---

## Appendix: Environment Variables

```bash
# Database
POSTGRES_USER=brkops
POSTGRES_PASSWORD=your-password
POSTGRES_DB=brkops
DATABASE_URL=postgresql://brkops:password@postgres:5432/brkops

# Redis
REDIS_URL=redis://redis:6379

# LLM (Primary + Fallback)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# MCP Servers (External)
CML_MCP_URL=http://cml-mcp-server:5000
SPLUNK_MCP_URL=http://splunk-mcp-server:5001

# Notifications
WEBEX_WEBHOOK_URL=https://webexapis.com/v1/...
SERVICENOW_INSTANCE=instance.service-now.com
SERVICENOW_USER=admin
SERVICENOW_PASSWORD=password

# Frontend
NEXT_PUBLIC_API_URL=http://192.168.1.213:8000
NEXT_PUBLIC_WS_URL=ws://192.168.1.213:8000
```

---

**Document End**
