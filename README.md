# Cygeniq AI Labs — Enterprise AI Agent & Security Simulator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143.2-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0.1-orange.svg)](https://github.com/langchain-ai/langgraph)
[![MCP](https://img.shields.io/badge/MCP-45%20Tools%20Loaded-purple.svg)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade conversational AI platform and real-time **AI Security Simulator** built for the **Cygeniq AI Practice Team**. The platform orchestrates **45 live Model Context Protocol (MCP) tools** across 8 distinct subsystems, enforces cryptographic Role-Based Access Control (RBAC), and features a live adversarial penetration testing suite with Server-Sent Events (SSE) streaming.

---

## 📑 Table of Contents
- [Organizational Context](#-organizational-context)
- [System Architecture](#-system-architecture)
- [Core Features](#-core-features)
  - [1. Enterprise Conversational Agent](#1-enterprise-conversational-agent)
  - [2. AI Security Simulator](#2-ai-security-simulator)
  - [3. Role-Based Access Control (RBAC)](#3-role-based-access-control-rbac)
- [MCP Subsystems Fleet (45 Tools)](#-mcp-subsystems-fleet-45-tools)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Docker Setup](#docker-setup)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Running Automated Test Suites](#-running-automated-test-suites)
- [Deployment on Render](#-deployment-on-render)
- [API Reference](#-api-reference)

---

## 🏛️ Organizational Context

- **Cygeniq** is a unified cybersecurity and AI governance organization.
- **Cygeniq AI Labs** is the internal application used by the **AI Practice Team** to access organizational knowledge, product intelligence, compliance policies, and adversarial testing workflows.
- **The AI Practice Team** conducts research into LLM vulnerabilities, maps regulatory frameworks (NIST AI RMF, ISO 42001, OWASP), and analyzes client requirements.
- **The Developing Team** designs, builds, and maintains Cygeniq's core commercial products:
  - 🛡️ **HexaShield AI**: Enterprise AI gateway protecting LLMs and RAG pipelines against prompt injection, jailbreaks, and sensitive data leakage.
  - ⚖️ **GRCortex**: Continuous AI governance automation mapping models and data pipelines to international regulations.
  - 🎫 **CyberTix AI**: Intelligent Tier-1 SOC ticket triage and incident response assistant.

---

## 📐 System Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend Layer (HTML5 / Modern CSS / Vanilla JS)"]
        UI_AUTH["JWT Login & Role Session"]
        UI_CHAT["AI Chatbot View<br/><i>Markdown typography & Source pills</i>"]
        UI_SIM["AI Security Simulator<br/><i>Real-time SSE Timeline & Finding Cards</i>"]
    end

    subgraph Gateway["API Gateway (FastAPI server.py)"]
        EP_AUTH["/auth/login & /auth/me"]
        EP_CHAT["/chat (RBAC Guarded & Rate-Limited)"]
        EP_SIM["/simulator/stream (SSE Streaming)"]
        EP_EXPORT["/simulator/report & /export"]
    end

    subgraph AgenticCore["Agentic Core (LangGraph agent.py)"]
        ORCH["StateGraph ReAct Loop"]
        LLM["Groq LLM (openai/gpt-oss-120b)"]
        CHECKPOINTER["SQLite Checkpointer (cygeniq_memory.db)"]
    end

    subgraph SecuritySim["Security Simulator Engine (security_simulator.py)"]
        ANALYZER["Risk Analyzer (13 Check Suites)"]
        GATE["Server-Side Enforcement Gate"]
        AUDIT_DB["SQLite Audit DB (security_simulator.db)"]
    end

    subgraph MCPFleet["Model Context Protocol Fleet (8 Subsystems - 45 Tools)"]
        MCP_FS["1. Filesystem MCP"]
        MCP_PG["2. Supabase Postgres MCP"]
        MCP_MEM["3. Knowledge Graph Memory MCP"]
        MCP_SP["4. SharePoint MS Graph MCP"]
        MCP_POL["5. Policy Intelligence MCP"]
        MCP_PROD["6. Product Intelligence MCP"]
        MCP_GRC["7. GRC Regulatory MCP"]
        MCP_MAIL["8. Gmail Integration MCP"]
    end

    Frontend --> Gateway
    Gateway --> AgenticCore
    Gateway --> SecuritySim
    AgenticCore --> LLM
    AgenticCore --> MCPFleet
    AgenticCore --> CHECKPOINTER
    SecuritySim --> GATE
    GATE --> AUDIT_DB
```

---

## ⚡ Core Features

### 1. Enterprise Conversational Agent
- **Multi-Tool ReAct Loop**: Employs LangGraph's cyclic state graphs for dynamic multi-step reasoning, query formulation, and tool selection.
- **Evidence-Based Grounding**: Classifies factual assertions into `Confirmed`, `In Progress`, `Proposed`, and `Needs Verification` to guarantee zero hallucinations.
- **Source Attribution Chips**: Inspects executed tool outputs and renders transparent visual citations for database records, policy documents, and knowledge files.
- **Conversation State Checkpointing**: Preserves multi-turn conversational context in `cygeniq_memory.db`.

### 2. AI Security Simulator
- **Live SSE Streaming**: Telemetry events stream in real-time via `text/event-stream` to the frontend dashboard.
- **13 Security Check Categories**: Evaluates prompt injections, secret exposure, destructive SQL queries, path traversal, PII leaks, privilege escalation, and more.
- **Dual Execution Modes**:
  - `Safe Simulation`: Evaluates prompt risk and guardrail strength without mutating system state.
  - `Adversarial Testing`: Temporarily relaxes LLM guardrails under controlled conditions to stress-test backend enforcement gates.
- **Server-Side Enforcement Gates**: Intercepts destructive SQL commands (`DROP TABLE`, `DELETE FROM`) and unauthorized outbound emails at the backend layer.
- **Full Audit Trail**: Stores all test runs in `security_simulator.db` with one-click export to **JSON** or **CSV**.

### 3. Role-Based Access Control (RBAC)
- **Roles**:
  - 🔑 **Admin**: Full, unrestricted access to all 45 tools, database queries, and email dispatches.
  - 🔬 **Analyst**: Access to policy analysis, GRC frameworks, and research files; blocked from direct database mutations.
  - 💼 **Presales**: Access to product datasheets, RFP matching, and gap analysis; blocked from database querying and direct email dispatch.
- **Cryptographic Security**: Issues HS256 JWT tokens with bcrypt password hashing (Cost Factor 12).
- **Prompt Guard Injection**: Restricts unauthorized tool calls at both the system prompt layer and the execution wrapper.

---

## 🔌 MCP Subsystems Fleet (45 Tools)

| Subsystem | Transport | Key Tools Loaded | Primary Function |
|---|---|---|---|
| **1. Filesystem** | Node.js stdio | `read_file`, `list_directory` | Reads local technical knowledge base within `/knowledge` boundary. |
| **2. Supabase Postgres** | Node.js stdio | `query`, `list_tables`, `describe_table` | Relational query execution over corporate database with destructive SQL blocking. |
| **3. Persistent Memory**| Node.js stdio | `create_entities`, `read_graph`, `search_nodes`, `open_nodes` | Persistent organizational knowledge graph stored in `./data/memory.jsonl`. |
| **4. SharePoint** | Python stdio | `search_sharepoint`, `read_sharepoint_document`, `upload_sharepoint_document` | MS Graph OAuth2 search and extraction of `.docx`, `.pdf`, and `.txt` documents. |
| **5. Policy Engine** | Python in-proc| `search_policies`, `get_policy_details`, `check_compliance_requirement` | Corporate policy intelligence covering data retention, acceptable use, and access control. |
| **6. Product Engine** | Python in-proc| `list_products`, `get_product_datasheet`, `search_product_capabilities`, `match_rfp_requirement_to_features` | Official datasheets, capabilities, and RFP responses for HexaShield AI, GRCortex, and CyberTix AI. |
| **7. GRC Regulatory** | Python in-proc| `list_regulatory_frameworks`, `get_framework_controls`, `evaluate_compliance_gap`, `generate_compliance_checklist` | Control mappings and evidence checks for NIST AI RMF, ISO 42001, OWASP LLM Top 10, and DPDP Act. |
| **8. Gmail** | Python stdio | `search_emails`, `read_email`, `draft_email`, `send_email` | IMAP/SMTP integration with a mandatory human-in-the-loop confirmation gate on outbound sending. |

---

## 💻 Tech Stack

- **Backend Framework:** FastAPI `0.143.2` + Uvicorn `0.54.0`
- **Agentic Engine:** LangGraph `1.0.1` + LangChain Core `0.3.86` + `langchain-mcp-adapters 0.1.10`
- **Inference LLM:** Groq Cloud API (`openai/gpt-oss-120b`)
- **Relational Databases:** Supabase PostgreSQL (`asyncpg 0.32.0`)
- **Embedded Databases:** SQLite (`aiosqlite 0.22.1`)
- **Security & Crypto:** `python-jose[cryptography] 3.5.0` + `bcrypt 5.0.0`
- **Rate Limiting:** SlowAPI `0.1.10` (10 req/min/IP)
- **Frontend:** Vanilla HTML5, modern CSS3 variables, ES6 JavaScript (Zero npm build required)
- **Containerization:** Docker (Python 3.11-slim + Node.js 20)

---

## 📁 Project Structure

```
cygeniq-ai-labs/
├── agent.py                  # LangGraph agent orchestration & MCP client initialization
├── server.py                 # FastAPI application, auth endpoints, chat & simulator routes
├── auth.py                   # RBAC implementation, JWT HS256, bcrypt hashing, Supabase migrations
├── security_simulator.py     # AI Security Simulator streaming engine & verdict logic
├── security_checks.py        # 13 check definitions, risk categories, and severities
├── security_db.py            # SQLite audit persistence & CSV/JSON export handlers
├── gmail_mcp.py              # Gmail IMAP/SMTP MCP server with confirmation gate
├── sharepoint_mcp.py         # Azure AD / SharePoint MS Graph MCP server
├── policy_mcp.py             # Internal corporate policy intelligence MCP server
├── product_mcp.py            # Commercial product suite intelligence MCP server
├── grc_mcp.py                # GRC regulatory framework & compliance checklist MCP server
├── static/
│   ├── index.html            # Unified dual-view frontend (Chatbot + Security Simulator)
│   ├── simulator.css         # Dark-mode enterprise UI styling
│   └── simulator.js          # SSE streaming timeline & UI event handler
├── knowledge/                # Markdown knowledge base & architecture documents
├── data/                     # Persistent storage (memory.jsonl, cygeniq_memory.db)
├── test_security_simulator.py# Automated test suite (15 checks)
├── test_rbac_e2e.py          # End-to-end RBAC test suite
├── test_adversarial.py       # Controlled adversarial stress test suite
├── Dockerfile                # Production multi-stage Docker build
├── render.yaml               # Infrastructure-as-code blueprint for Render
├── requirements.txt          # Pinned Python dependencies
└── .env.example              # Environment variables template
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ (for npm MCP servers: `@modelcontextprotocol/server-*`)
- Groq Cloud API Key

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ShravaniRQ/cygeniq-ai-labs.git
   cd cygeniq-ai-labs
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install pinned dependencies**:
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

4. **Configure your environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your GROQ_API_KEY and SUPABASE_URL
   ```

5. **Start the server**:
   ```bash
   uvicorn server:app --host 127.0.0.1 --port 8000 --reload
   ```
   Open **http://127.0.0.1:8000** in your browser.

---

### Docker Setup

1. **Build the container**:
   ```bash
   docker build -t cygeniq-agent .
   ```

2. **Run the container**:
   ```bash
   docker run -d -p 8000:8000 \
     -e GROQ_API_KEY="your_groq_api_key" \
     -e SUPABASE_URL="your_supabase_url" \
     -e JWT_SECRET_KEY="your_secret_key" \
     -v cygeniq_data:/app/data \
     --name cygeniq-app cygeniq-agent
   ```

---

## 🔐 Configuration & Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | **Yes** | Groq Cloud API key for LLM inference (`openai/gpt-oss-120b`). |
| `SUPABASE_URL` | **Yes** | PostgreSQL connection string (`postgresql://postgres:...@host:5432/postgres`). |
| `JWT_SECRET_KEY`| **Yes** | Secret key for signing and validating JWT authentication tokens. |
| `JWT_EXPIRE_MINUTES`| No | Token expiry duration in minutes (Default: `1440` = 24 hours). |
| `ADMIN_DEFAULT_PASSWORD` | No | Default admin password seeded on first database boot. |
| `DATA_DIR` | No | Path to persistent storage directory (Default: `./data` locally, `/app/data` in Docker). |
| `SECURITY_AUDIT_DB` | No | SQLite database for simulator audits (Default: `/app/data/security_simulator.db`). |
| `AZURE_TENANT_ID` | Optional | Azure Active Directory Tenant ID for SharePoint MCP. |
| `AZURE_CLIENT_ID` | Optional | Azure App Registration Client ID for SharePoint MCP. |
| `AZURE_CLIENT_SECRET` | Optional | Azure App Registration Client Secret for SharePoint MCP. |
| `GMAIL_EMAIL` | Optional | Gmail address for Gmail MCP integration. |
| `GMAIL_APP_PASSWORD` | Optional | Google App Password (16 characters) for Gmail IMAP/SMTP access. |

---

## 🧪 Running Automated Test Suites

```bash
# 1. Full Security Simulator Suite (15 comprehensive checks)
python -m unittest test_security_simulator.py -v

# 2. Role-Based Access Control (RBAC) End-to-End Suite
python test_rbac_e2e.py

# 3. Controlled Adversarial Stress-Testing Suite
python test_adversarial.py
```

---

## ☁️ Deployment on Render

This repository includes a native [`render.yaml`](./render.yaml) configuration for 1-click deployment on Render:

1. Connect your GitHub repository to [Render](https://dashboard.render.com).
2. Create a new **Web Service** selecting **Docker Runtime**.
3. In the Render Dashboard **Environment** tab, configure:
   - `GROQ_API_KEY`
   - `SUPABASE_URL`
   - `JWT_SECRET_KEY`
4. Deploy! Render will build the container, install Node.js and Python dependencies, pre-cache MCP daemons, and launch the service with auto-healing health checks on `/health`.

---

## 📡 API Reference

### Authentication
- `POST /auth/login`: `{ "username": "...", "password": "..." }` → Returns JWT bearer token and starter cards.
- `GET /auth/me`: Returns the authenticated user's role and display metadata.

### Conversational Agent
- `POST /chat`: `{ "message": "...", "thread_id": "optional" }` → Returns synthesized response blocks and source attribution cards.
- `GET /health`: Returns service status, active tool count, connected MCP servers, and LLM model.

### AI Security Simulator
- `POST /simulator/stream`: Streams real-time test execution events over Server-Sent Events (SSE).
- `POST /simulator/stop`: `{ "test_id": "..." }` → Gracefully halts an active test stream.
- `GET /simulator/history`: Returns list of historical audit runs.
- `GET /simulator/report/{test_id}`: Returns full JSON report for a test run.
- `GET /simulator/export/{test_id}?format=csv`: Downloads audit report as an RFC 4180 CSV file.
- `GET /simulator/tools`: Lists all 45 live MCP tools available to the simulator.

---

## 📄 License
MIT License — © 2026 Cygeniq AI Labs.
