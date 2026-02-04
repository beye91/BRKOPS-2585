# BRKOPS-2585: De-Risk Your Network Using CML, Splunk and MCP Server

## Complete Presentation & Demo Planning Document

**Session:** Cisco Live — BRKOPS-2585
**Presenters:** Chris Beye & Abay
**Theme:** From Chaos to Control

---

## 1. OVERARCHING THEME & NARRATIVE

### Title Concept
**"From Chaos to Control"** — The entire session follows a three-act narrative arc:

| Arc | Theme | Emotional State |
|-----|-------|-----------------|
| **Act 1** | Chaos → Confidence | "I can't manage this" → "I understand the problem" |
| **Act 2** | Chaos → Control | "Things keep breaking" → "I have the tools to prevent it" |
| **Act 3** | Chaos → Stress-Free Morning Coffee | "2 AM nightmares" → "Peaceful, validated operations" |

### Opening Roleplay (CRITICAL — Sets the Tone)
Chris and Abay perform a **live roleplay** on stage:
- One person pretends to be **in the chaos** (panicked network engineer at 2 AM)
- The other is the **voice of confidence** (calm, showing the path forward)
- Walk the audience through the journey — ending with: *"Abba, I don't feel the chaos anymore. What about you guys?"*

### Storytelling Anchor
> *"Imagine it's Wednesday, 2:00 AM. Your phone rings. Management calls — someone pushed changes to production. You open Splunk and everything is red. How would you feel?"*

This scenario is the **narrative thread** that ties the entire session together. Every component and demo circles back to: **"How do we make sure you never have that 2 AM nightmare again?"**

### Presentation Style Inspiration
- **Hank Preston's style**: Put yourself in the audience's shoes, talk about yourself, take people on a journey, be relatable and entertaining — not just technical
- People need to **connect** — make it entertaining, not just informative
- **Repeat key messages** — reinforcement matters

---

## 2. PRESENTATION FLOW — THREE PHASES

### PHASE 1: The Pain (Chaos)
**Goal:** Establish the problem. Make the audience feel the pain they already know.

**Content:**
- Network complexity is growing — multi-vendor, multi-domain, multi-cloud
- Making changes in production is risky, time-consuming, costly
- Human errors cause outages (the 2 AM scenario)
- Compliance requirements (DORA, security advisories) create pressure to act fast
- Current approaches don't scale — manual testing, tribal knowledge, spreadsheet-driven change management

**Slides needed:**
- Network challenges / complexity overview
- The cost of downtime (stats, real-world impact)
- The human error problem
- Compliance pressure (DORA, security patches, credential rotation)

**Key message:** *"This is the chaos. This is what we all deal with. And it's only getting worse."*

---

### PHASE 2: The Solution Building Blocks
**Goal:** Introduce each component BEFORE jumping to the agent. Build understanding layer by layer.

#### 2A. The Building Blocks (Individual Components)

**CML (Cisco Modeling Labs)**
- What it is: Network digital twin / simulation environment
- Why it matters: Safe place to test changes before production
- Role in our solution: The "sandbox" where configurations get validated
- *Slides already exist from previous sessions — reuse and enhance*

**Splunk (or any telemetry/monitoring platform)**
- What it is: Operational data collection and analysis
- Why it matters: Visibility into what's actually happening on the network
- Role in our solution: The "eyes and ears" — collects logs, events, telemetry from devices
- Used to consume and analyze the results of changes
- *Need slides — can leverage Splunk webhook admin tool Chris already built*

**Controller (Catalyst Center / NDFC / Meraki / any controller)**
- What it is: Network management and orchestration platform
- Why it matters: Single pane of glass for network operations
- Role in our solution: Source of truth for current network state
- **CRITICAL FRAMING:** *"This is NOT about Catalyst Center. This is NOT about Nexus Dashboard. This is about the BLUEPRINT. You can use ANY controller — Ansible, your own scripts, whatever. This is about the approach."*
- *Slides from Amsterdam session — reframe for this context*

**LLM (Large Language Model)**
- What it is: The "brain" that understands natural language and can reason about network state
- Why it matters: Bridges the gap between human intent and machine execution
- Role in our solution: Interprets user intent, reasons about configurations, generates recommendations
- *Need slides explaining LLM role in networking context*

**MCP (Model Context Protocol)**
- What it is: The protocol that connects LLMs to external tools and data sources
- Why it matters: Without MCP, LLMs can't interact with your infrastructure
- What it does: Provides the LLM access to CML, Splunk, controllers — all through a standardized interface
- MCP risks and considerations (security, trust, evolving ecosystem)
- *Slides already exist — enhance with current MCP ecosystem developments*

**Key insight to highlight:**
> *"The LLM + MCP together is the BRAIN of the solution. Everything else — CML, Splunk, controllers — those are the hands and eyes. The brain ties it all together."*

#### 2B. AI Agents
**After** building blocks are understood, introduce the agent concept:

- What is an AI agent?
- How does it leverage the LLM?
- How do multiple agents communicate?
- How the agent orchestrates: reads from MCP → reasons with LLM → takes action via MCP
- **Human in the loop** — agents propose, humans approve
  - *"People are afraid to lose their jobs. We're not replacing engineers — we're giving them superpowers."*
- *Agent slides already exist*

**Key message:** *"We're moving from static networks to intent-based operations. You express your intent, the agent configures, tests, and validates — and gives you the results before anything touches production."*

---

### PHASE 3: Use Cases & Live Demo
**Goal:** Show it working. Bring the chaos-to-control story to a resolution.

#### The Workflow (What We Show End-to-End)

```
1. USER HAS AN INTENT
   "I want to change OSPF configuration on Router X"
        ↓
2. DON'T TOUCH PRODUCTION!
   "Can I somehow simulate this change first?"
        ↓
3. CML — DIGITAL TWIN
   Agent pushes the config change to the CML simulation
        ↓
4. OBSERVE — SPLUNK
   Collect logs, telemetry, events from the simulated change
        ↓
5. ANALYZE — LLM
   "What went right? What went wrong? Any routing loops?"
        ↓
6. RECOMMEND — AGENT
   "This change will cause X. Here are the failed test cases.
    Here's an alternative approach."
        ↓
7. NOTIFY — WEBEX / SERVICENOW
   Alert sent to WebEx, ticket auto-created in ServiceNow
        ↓
8. HUMAN DECISION
   Engineer reviews, approves or rejects → stress-free morning coffee ☕
```

#### Live Demo Concept (Showstopper Moment)

**Voice-to-Intent Demo on Stage:**
- Chris gives Abay a separate podcast microphone on stage
- Abay speaks his intent into the microphone: *"I want to change the OSPF configuration on this router"*
- A keybind triggers voice-to-text conversion
- The text becomes the input to the agentic pipeline
- The system automatically:
  1. Interprets the intent
  2. Generates the configuration
  3. Pushes it to CML
  4. Runs tests
  5. Analyzes results via Splunk
  6. Reports back with findings

**Framing to audience:**
> *"Look guys, this is nothing new. All of this has been there. But the way HOW to do it and HOW FAST we can achieve something like this — that's what's going to change. That's why we go from chaos to control. Everything gets simpler, not harder. With these tools and LLMs, we can do more in less time."*

---

## 3. USE CASES (3 Scenarios)

### Use Case 1: OSPF Configuration Change (Primary Demo)
**Scenario:** Change OSPF routing configuration
**The twist:** The change introduces a routing loop (human error simulation)
**What happens:**
- Agent receives configuration intent
- Pushes to CML
- CML devices log routing loop detection
- Splunk consumes the logs
- LLM analyzes and detects: *"Routing loop detected between Router A and Router B"*
- Notification sent to WebEx (with humorous LLM-generated message)
- ServiceNow ticket auto-created
- Recommendation provided: *"This change would cause a routing loop. Here's the corrected configuration."*

**WebEx notification tone:** Make it funny!
> *"What have you done, dude? Did you sip your coffee too much? You've created a routing loop! 🔄"*

### Use Case 2: Credential Rotation / Username-Password Change
**Scenario:** Compliance-driven credential rotation (happens every 6 months in European enterprises)
**Why it matters:**
- DORA compliance, security policies require regular credential changes
- Nobody wants to spend regression cycles on routine credential updates
- Automated: push changes → validate all tests pass → done

**What happens:**
- Agent receives: *"Rotate credentials on all datacenter switches"*
- Generates new configurations
- Pushes to CML for validation
- Runs connectivity and access tests
- Reports: *"All 47 devices updated. All test cases passed. No connectivity impact."*

### Use Case 3: Security Advisory / Template Configuration Push
**Scenario:** Urgent security advisory requires config changes across the fleet
**Why it matters:**
- Security advisories can't wait — if you delay, you're exposed
- Need to validate quickly that the remediation doesn't break anything
- Could reference a real Cisco security advisory for authenticity

**What happens:**
- Agent receives the security advisory template configuration (golden config from IT security)
- Pushes the patch configuration to all affected devices in CML
- Runs validation: *"10 commands applied across 25 devices. 2 test cases failed on Router-C due to conflicting ACL."*
- Reports impact analysis before production deployment

**Alternative mention:** DORA compliance discussion — what it requires, how critical infrastructure must be managed, what enterprises need to keep in mind. Can be mentioned without a full demo.

---

## 4. KEY ASPECTS TO HIGHLIGHT

### Technical Components
- **MCP Servers available:** CML MCP Server, Splunk MCP Server
- **LLM integration:** OpenAI (confirmed working), potentially others
- **Notification integrations:** WebEx (webhook), ServiceNow (ticket creation), Email
- **Voice-to-text:** For the live demo stage interaction

### Philosophical Points
- **Controller-agnostic approach:** Not about Catalyst Center or Nexus Dashboard — it's the BLUEPRINT that matters. Any controller, any vendor.
- **Human in the loop:** Agents assist, humans decide. Nobody loses their job.
- **Intent-based operations:** Moving from static configuration management to expressing intent and letting AI figure out the "how"
- **Speed advantage:** The same validation that took days now takes minutes
- **Democratization:** Natural language queries mean less specialized scripting knowledge needed

### What's New vs. What's Not
- CML, Splunk, controllers — **not new**
- LLMs, MCP, AI agents — **the new glue** that ties everything together
- The approach, the speed, the simplicity — **that's what changes everything**

---

## 5. WHAT NEEDS TO BE BUILT (Software/Demo)

### Demo Infrastructure

| Component | Status | Action Needed |
|-----------|--------|---------------|
| CML topology with OSPF-enabled routers | Existing | Extend with routing loop scenario |
| CML MCP Server | Existing | Verify all functions work end-to-end |
| Splunk instance receiving device logs | Existing/Partial | Configure syslog ingestion from CML devices |
| Splunk MCP Server | Existing | Test query capabilities for demo |
| LLM integration (OpenAI) | Working | Configure for demo scenarios |
| WebEx webhook notification | Working (Chris built it) | Customize message templates, add humor |
| ServiceNow ticket creation | Working (Chris built it) | Verify connectivity from demo environment |
| Voice-to-text pipeline | New | Build: microphone → speech-to-text → agent input |
| Splunk Webhook Admin UI | Built by Chris | Potential showcase during demo |
| Agent orchestration layer | Build/Enhance | Needs to chain: CML → Splunk → LLM → Notify |

### CML Lab Topology Requirements
- Multiple routers with OSPF configured
- Ability to introduce a misconfiguration that causes a routing loop
- Syslog configured to send to Splunk
- Device access via CML MCP Server

### Agent Workflow Pipeline (Core Build)
```
[Voice Input / Text Input]
        ↓
[Intent Parser — LLM]
  "What does the user want to do?"
        ↓
[Configuration Generator — LLM]
  "Generate the OSPF config change"
        ↓
[CML MCP Server]
  → Push configuration to CML lab devices
        ↓
[Wait / Monitor]
  → Devices process configuration
  → Logs stream to Splunk
        ↓
[Splunk MCP Server]
  → Query: "Any errors in last 60 seconds?"
  → Query: "OSPF adjacency status?"
  → Query: "Routing loop indicators?"
        ↓
[Analysis — LLM]
  → "Based on the Splunk data, here's what happened..."
  → "Routing loop detected between X and Y"
  → "Recommendation: Change cost on interface Gi0/1"
        ↓
[Notification]
  → WebEx message with summary + humor
  → ServiceNow ticket with details
        ↓
[Human Review]
  → Engineer reviews recommendation
  → Approves / Rejects / Modifies
```

### Voice-to-Intent Pipeline (Stage Demo)
- Physical microphone (Chris's podcast mic)
- Speech-to-text engine (Whisper API or similar)
- Text output feeds into the agent pipeline
- Triggered by a keyboard shortcut on Chris's laptop
- Output visible on the presentation screen in real-time

---

## 6. SLIDE DECK STRUCTURE (Revised)

| # | Slide Topic | Phase | Notes |
|---|-------------|-------|-------|
| 1 | Title: "De-Risk Your Network Using CML, Splunk & MCP Server" | — | Session ID, speakers |
| 2 | Opening — The 2 AM Nightmare (Chaos Scenario) | Phase 1 | Storytelling slide, set the scene |
| 3 | Roleplay intro — "From Chaos to..." | Phase 1 | Three arcs: Confidence, Control, Stress-Free Coffee |
| 4 | Network Challenges Today | Phase 1 | Complexity, multi-vendor, scale |
| 5 | The Cost of Getting It Wrong | Phase 1 | Downtime stats, compliance risk |
| 6 | DORA & Compliance Pressures | Phase 1 | European context, security advisories |
| 7 | Transition: "So how do we go from chaos to control?" | — | Bridge slide |
| 8 | Solution Building Block: CML | Phase 2 | Digital twin, safe simulation |
| 9 | Solution Building Block: Splunk / Telemetry | Phase 2 | Operational visibility, log analysis |
| 10 | Solution Building Block: Controller | Phase 2 | Catalyst Center as example (but any controller) |
| 11 | Solution Building Block: LLM | Phase 2 | The "brain" — reasoning, natural language |
| 12 | Solution Building Block: MCP | Phase 2 | The "connector" — bridges LLM to infrastructure |
| 13 | MCP Deep Dive: Risks, Considerations, Ecosystem | Phase 2 | What MCP is, current state, security |
| 14 | The Brain: LLM + MCP = Intelligence Layer | Phase 2 | Key insight slide |
| 15 | What is an AI Agent? | Phase 2 | Agent concepts, multi-agent communication |
| 16 | Human in the Loop | Phase 2 | Trust, safety, "nobody loses their job" |
| 17 | Solution Architecture (End-to-End) | Phase 2 | Full diagram: Intent → CML → Splunk → LLM → Notify |
| 18 | Transition: "Let's see it in action" | — | Bridge to demos |
| 19 | Use Case 1: OSPF Change + Routing Loop Detection | Phase 3 | Primary demo |
| 20 | Use Case 2: Credential Rotation / Compliance | Phase 3 | Automation for routine changes |
| 21 | Use Case 3: Security Advisory Rapid Response | Phase 3 | Template push + validation |
| 22 | Self-Healing Networks with Human in the Loop | Phase 3 | Vision: where this is heading |
| 23 | What's New vs. What's Not | Phase 3 | "The tools aren't new. The glue is." |
| 24 | From Chaos to ☕ Stress-Free Morning Coffee | — | Closing — full circle |
| 25 | Q&A / Resources | — | Links, references, contact |

---

## 7. ACTION ITEMS & DIVISION OF WORK

### Chris (Building the Demo)
- [ ] Build the full agent orchestration pipeline (CML → Splunk → LLM → Notify)
- [ ] Configure CML topology with OSPF routing loop scenario
- [ ] Set up voice-to-text pipeline for stage demo
- [ ] Enhance the Splunk Webhook Admin tool for demo showcase
- [ ] Configure WebEx webhook with humorous LLM-generated messages
- [ ] Configure ServiceNow integration for auto-ticket creation
- [ ] Test OpenAI LLM integration end-to-end
- [ ] Build credential rotation use case
- [ ] Build security advisory template push use case
- [ ] Upload slides to SharePoint and share with Abay

### Abay (Building the Slides)
- [ ] Add/enhance CML building block slides
- [ ] Add Splunk / telemetry building block slides
- [ ] Add Controller slides (reframe from Amsterdam session)
- [ ] Add LLM explanation slides
- [ ] Add AI Agent concept slides (may already exist)
- [ ] Enhance MCP slides (already in deck)
- [ ] Build the storyline narrative slides (chaos opening, transitions)
- [ ] Create the solution architecture diagram slide
- [ ] Build use case description slides

### Together
- [ ] Speaker training — Monday evening, 1 hour
- [ ] Perfect the opening roleplay
- [ ] Rehearse demo flow
- [ ] Finalize slide order and transitions

---

## 8. KEY QUOTES & TALKING POINTS

**Opening:**
> "Imagine it's Wednesday, 2 AM. Your phone rings..."

**On the approach:**
> "This is NOT about Catalyst Center. This is NOT about Nexus Dashboard. This is about the BLUEPRINT — how to get data, make sense of it, test it, validate it, and come to a conclusion."

**On what's new:**
> "This is nothing new. All of this has been there. But the way HOW to do it and HOW FAST — that's what changes. That's why we go from chaos to control."

**On MCP + LLM:**
> "The LLM and MCP together — that's the brain of the solution. The brain ties everything together."

**On humans:**
> "Self-healing networks WITH human in the loop. Nobody loses their job."

**On the promise:**
> "So you could avoid the 2 AM nightmare. More time, less stress, stress-free morning coffee."

**On tools:**
> "With the tools we have nowadays — LLMs, MCP, agents — we can make sense of them and use them in a very powerful way. We can do more in less time."

**Closing (after demo):**
> "Abba, I don't feel the chaos anymore. What about you guys?"
