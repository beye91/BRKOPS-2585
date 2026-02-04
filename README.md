# BRKOPS-2585: AI-Driven Network Operations

> **"From Chaos to Control"** - A Cisco Live technical session demonstrating how AI, Model Context Protocol (MCP), and digital twins transform network operations.

## The Story

Network operations have always been a high-stakes game. One wrong command, one misconfigured interface, and suddenly your morning coffee turns into a war room situation with executives asking "when will it be fixed?"

I built this platform after watching too many experienced engineers hesitate before hitting enter on a config change. Not because they didn't know what they were doing, but because there was no safe way to validate changes before production.

**What if we could:**
- Test network changes in a digital twin before touching production?
- Have AI analyze the impact of changes across logs, metrics, and telemetry?
- Keep humans in the loop while automating the tedious parts?

That's what BRKOPS-2585 demonstrates.

## What It Does

This platform creates a voice-driven workflow for network operations:

1. **Speak your intent** - "I want to change OSPF on Router-1 to area 10"
2. **AI parses the request** - GPT-4 understands the intent and generates IOS configuration
3. **Deploy to digital twin** - Changes hit a CML lab (4 Cat8000v routers) first
4. **Monitor and analyze** - Splunk collects logs, telemetry streams in, AI analyzes the impact
5. **Human decides** - You see the analysis and approve or reject the change

No config touches production without human approval. The AI does the heavy lifting; you stay in control.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BRKOPS-2585 Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    Voice/Text     ┌─────────────────────────────────┐    │
│   │   Browser   │ ─────────────────>│      Next.js Frontend           │    │
│   │  (Demo UI)  │<───────────────── │   - Voice Input (Web Speech)    │    │
│   │             │   Real-time WS    │   - Pipeline Visualization      │    │
│   │  ┌───────┐  │                   │   - Network Topology            │    │
│   │  │ Admin │  │                   │   - Admin Panel                 │    │
│   │  │ Panel │  │                   └───────────────┬─────────────────┘    │
│   │  └───────┘  │                                   │                      │
│   └─────────────┘                                   │ REST API             │
│                                                     ▼                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     FastAPI Backend                                  │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│   │  │   Voice     │  │   LLM       │  │   Pipeline  │  │ WebSocket  │  │  │
│   │  │  Service    │  │  Service    │  │   Worker    │  │  Manager   │  │  │
│   │  │ (Whisper)   │  │(GPT-4/Claude│  │   (arq)     │  │            │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │  │
│   │                                                                      │  │
│   │  ┌─────────────────────────────────────────────────────────────┐    │  │
│   │  │                    MCP Clients                                │    │  │
│   │  │   ┌─────────────────┐         ┌─────────────────┐            │    │  │
│   │  │   │   CML Client    │         │  Splunk Client  │            │    │  │
│   │  │   │                 │         │                 │            │    │  │
│   │  │   └────────┬────────┘         └────────┬────────┘            │    │  │
│   │  └────────────┼───────────────────────────┼─────────────────────┘    │  │
│   └───────────────┼───────────────────────────┼──────────────────────────┘  │
│                   │ MCP Protocol              │ MCP Protocol                │
│                   ▼                           ▼                             │
│   ┌───────────────────────────┐   ┌───────────────────────────┐            │
│   │     CML MCP Server        │   │    Splunk MCP Server      │            │
│   │  - Lab Management         │   │  - SPL Query Execution    │            │
│   │  - Node Configuration     │   │  - Log Analysis           │            │
│   │  - CLI Command Execution  │   │  - Natural Language Query │            │
│   │  - Topology Discovery     │   │                           │            │
│   └───────────┬───────────────┘   └───────────────────────────┘            │
│               │                                                             │
│               ▼                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    Cisco Modeling Labs (CML)                       │    │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │    │
│   │  │Router-1 │──│Router-2 │──│Router-3 │──│Router-4 │               │    │
│   │  │Cat8000v │  │Cat8000v │  │Cat8000v │  │Cat8000v │               │    │
│   │  │  .201   │  │  .202   │  │  .203   │  │  .204   │               │    │
│   │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘               │    │
│   │       │            │            │            │                     │    │
│   │       └────────────┴─────┬──────┴────────────┘                     │    │
│   │                          │ Full Mesh OSPF Area 0                   │    │
│   │                          │ MDT Telemetry -> Splunk                 │    │
│   │                          │ Syslog, SNMP, NETCONF                   │    │
│   └──────────────────────────┼─────────────────────────────────────────┘    │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                    Data Stores                                    │     │
│   │   ┌──────────────┐              ┌──────────────┐                 │     │
│   │   │  PostgreSQL  │              │    Redis     │                 │     │
│   │   │  - Config    │              │  - Job Queue │                 │     │
│   │   │  - Jobs      │              │  - Pub/Sub   │                 │     │
│   │   │  - Users     │              │  - Cache     │                 │     │
│   │   └──────────────┘              └──────────────┘                 │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Demo Lab Topology

```
                    ┌─────────────┐
                    │  External   │
                    │  Connector  │
                    │  (bridge1)  │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  Mgmt-Switch│
                    │ (unmanaged) │
                    └──────┬──────┘
              ┌────────┬───┴───┬────────┐
              │        │       │        │
        ┌─────┴─────┐  │       │  ┌─────┴─────┐
        │  Router-1 │  │       │  │  Router-2 │
        │ 198.18.1. │  │       │  │ 198.18.1. │
        │    201    │──┼───────┼──│    202    │
        │ Lo: .255.1│  │       │  │ Lo: .255.2│
        └─────┬─────┘  │       │  └─────┬─────┘
              │\       │       │       /│
              │ \──────┼───────┼──────/ │
              │  \     │       │     /  │
              │   \    │       │    /   │
              │    \   │       │   /    │
              │     \  │       │  /     │
              │      \ │       │ /      │
              │       \│       │/       │
        ┌─────┴─────┐  │       │  ┌─────┴─────┐
        │  Router-3 │──┼───────┼──│  Router-4 │
        │ 198.18.1. │  │       │  │ 198.18.1. │
        │    203    │──┴───────┴──│    204    │
        │ Lo: .255.3│             │ Lo: .255.4│
        └───────────┘             └───────────┘

    Full Mesh OSPF Area 0 | 10.1.x.0/30 Inter-router Links
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Access to Cisco Modeling Labs (CML) instance
- OpenAI API key (for GPT-4)
- Optional: Anthropic API key (Claude fallback)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/beye91/BRKOPS-2585.git
cd BRKOPS-2585

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - OPENAI_API_KEY
# - CML_HOST, CML_USERNAME, CML_PASSWORD
# - SPLUNK_TOKEN (optional)
```

### Run with Docker

```bash
# Build all containers (no cache)
docker compose build --no-cache

# Start services
docker compose up -d

# Check health
curl http://localhost:8000/health
```

### Access

| Service | URL |
|---------|-----|
| Demo Dashboard | http://localhost:3000/demo |
| Admin Panel | http://localhost:3000/admin |
| API Documentation | http://localhost:8000/docs |

## Features

### Voice-Driven Operations
Speak your network intent naturally. The system transcribes, parses, and generates the appropriate configuration.

### Digital Twin Testing
Every change hits the CML lab first. Watch OSPF converge, monitor telemetry, analyze logs before production.

### AI-Powered Analysis
GPT-4 analyzes Splunk logs, identifies issues, and provides recommendations with severity ratings.

### Human-in-the-Loop
The AI suggests, you decide. Approve or reject changes with full context and analysis.

### Reset Lab Button
After demo changes, click "Reset Lab" to restore all router configurations to baseline. No need to stop/wipe/restart.

## Admin Panel

The admin interface lets you configure:

- **MCP Servers** - Connect CML and Splunk MCP servers
- **CML Labs** - Build, start, stop, reset, and delete labs
- **LLM Config** - Set GPT-4/Claude parameters
- **Use Cases** - Define automated workflows
- **Notifications** - Configure WebEx and ServiceNow alerts
- **Pipeline** - Monitor job execution

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, TailwindCSS |
| Backend | FastAPI, Python 3.12 |
| Job Queue | Redis + arq |
| Database | PostgreSQL 16 |
| AI/LLM | OpenAI GPT-4, Anthropic Claude |
| Network | Cisco CML, Cat8000v, OSPF |
| Protocol | Model Context Protocol (MCP) |

## Project Structure

```
BRKOPS-2585/
├── backend/
│   ├── routers/          # API endpoints
│   ├── services/         # CML, Splunk, LLM clients
│   ├── models/           # Pydantic schemas
│   ├── db/               # Database models
│   └── tasks/            # arq background jobs
├── frontend/
│   ├── src/app/          # Next.js pages
│   ├── src/components/   # React components
│   └── src/services/     # API client
├── cml-lab/
│   └── brkops-ospf-demo.yaml  # Lab topology
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEMO_RUNBOOK.md
│   └── DCLOUD_DEPLOYMENT.md
└── scripts/
    └── deploy.sh
```

## API Endpoints

### CML Lab Management
```
GET  /api/v1/mcp/cml/labs                    # List all labs
GET  /api/v1/mcp/cml/labs/demo-status        # Demo lab status
POST /api/v1/mcp/cml/labs/build-demo         # Build demo lab
POST /api/v1/mcp/cml/labs/{id}/start         # Start lab
POST /api/v1/mcp/cml/labs/{id}/stop          # Stop lab
POST /api/v1/mcp/cml/labs/{id}/reset         # Reset configs
DELETE /api/v1/mcp/cml/labs/{id}             # Delete lab
```

### Operations
```
POST /api/v1/operations/start                # Start pipeline
GET  /api/v1/operations/{id}                 # Get status
POST /api/v1/operations/{id}/approve         # Human approval
```

## Demo Flow

1. Open Demo Dashboard
2. Click microphone, say: "Change OSPF on Router-1 to area 10"
3. Watch the pipeline stages:
   - Voice Input -> Intent Parsing -> Config Generation
   - CML Deployment -> Monitoring -> Splunk Analysis
   - AI Analysis -> Notifications -> Human Decision
4. Review the analysis report
5. Approve or Reject the change
6. Click "Reset Lab" to restore baseline

## Deployment

### dCloud (Cisco Demo Environment)
```bash
# Deploy to dCloud instance
./scripts/deploy-dcloud.sh
```

### Production
```bash
# Deploy to remote server
make deploy DEPLOY_HOST=your-server.com
```

## Contributing

This is a demo platform for Cisco Live session BRKOPS-2585.
Contributions welcome for bug fixes and enhancements.

## License

MIT License - See LICENSE file

## Acknowledgments

- **Cisco DevNet** for CML and network automation resources
- **Anthropic** for Claude and the Model Context Protocol
- **OpenAI** for GPT-4 API
- **Cisco Live** attendees for feedback and inspiration

---

**Built for Cisco Live | BRKOPS-2585 | "De-Risk Your Network Using CML, Splunk and MCP Server"**
