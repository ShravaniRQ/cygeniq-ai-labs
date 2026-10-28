import os
import uuid
import html as html_lib
import markdown
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    def get_real_client_ip(request: Request) -> str:
        """Extract client IP, checking X-Forwarded-For header for reverse proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return get_remote_address(request)

    limiter = Limiter(key_func=get_real_client_ip, default_limits=["10/minute"])
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False
    class _DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = _DummyLimiter()

import agent
from agent import init_agent, LLM_GUARDRAILS_DISABLED
from auth import (
    authenticate_user,
    create_access_token,
    ensure_users_table,
    get_current_user,
    is_tool_allowed,
    RoleUser,
    ROLE_LABELS,
    ROLE_STARTER_CARDS,
    ROLE_DENIED_TOOLS,
)
from security_simulator import run_security_simulation_stream, cancel_active_test, get_available_mcp_tools
import security_db

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Cygeniq AI Labs Agent", version="2.0.0")

if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global agent references (primary production agent and adversarial testing agent)
cygeniq_agent = None
cygeniq_adversarial_agent = None

# ---------------------------------------------------------------------------
# Source attribution helpers
# ---------------------------------------------------------------------------
_TOOL_SOURCES = {
    # Postgres
    "query":                          ("db",         "Postgres (Supabase)",            "Database Query"),
    "list_tables":                    ("db",         "Postgres (Supabase)",            "Database Schema"),
    "describe_table":                 ("db",         "Postgres (Supabase)",            "Database Schema"),
    # Filesystem
    "read_file":                      ("file",       "Filesystem (Knowledge)",         "Policy Document"),
    "list_directory":                 ("file",       "Filesystem (Knowledge)",         "Policy Document"),
    "list_allowed_directories":       ("file",       "Filesystem (Knowledge)",         "Policy Document"),
    # Memory knowledge-graph
    "read_graph":                     ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "create_entities":                ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "create_relations":               ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "add_observations":               ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "delete_entities":                ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "delete_observations":            ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "delete_relations":               ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "search_nodes":                   ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    "open_nodes":                     ("memory",     "Memory (Knowledge Graph)",       "Persistent Memory"),
    # SharePoint
    "search_sharepoint":              ("sharepoint", "SharePoint (Knowledge)",         "SharePoint Document"),
    "read_sharepoint_document":       ("sharepoint", "SharePoint (Knowledge)",         "SharePoint Document"),
    "list_knowledge_areas":           ("sharepoint", "SharePoint (Knowledge)",         "SharePoint Document"),
    "upload_sharepoint_document":     ("sharepoint", "SharePoint (Knowledge)",         "SharePoint Upload"),
    # Policy MCP
    "search_policies":                ("policy",     "Policy Intelligence",            "Policy Document"),
    "get_policy_details":             ("policy",     "Policy Intelligence",            "Policy Document"),
    "list_available_policies":        ("policy",     "Policy Intelligence",            "Policy Document"),
    "check_compliance_requirement":   ("policy",     "Policy Intelligence",            "Compliance Check"),
    # Product MCP
    "list_products":                  ("product",    "Product Intelligence",           "Cygeniq Products"),
    "get_product_datasheet":          ("product",    "Product Intelligence",           "Product Datasheet"),
    "search_product_capabilities":    ("product",    "Product Intelligence",           "Product Capability"),
    "match_rfp_requirement_to_features": ("product", "Product Intelligence",           "RFP Mapping"),
    # GRC MCP
    "list_regulatory_frameworks":     ("grc",        "GRC & Regulatory Intelligence",  "Regulatory Framework"),
    "get_framework_controls":         ("grc",        "GRC & Regulatory Intelligence",  "Framework Controls"),
    "map_control_to_product_evidence":("grc",        "GRC & Regulatory Intelligence",  "Control Evidence"),
    "evaluate_compliance_gap":        ("grc",        "GRC & Regulatory Intelligence",  "Gap Analysis"),
    "generate_compliance_checklist":  ("grc",        "GRC & Regulatory Intelligence",  "Audit Checklist"),
    # Gmail MCP
    "search_emails":                  ("mail",       "Gmail (Inbox)",                  "Gmail Search"),
    "read_email":                     ("mail",       "Gmail (Inbox)",                  "Gmail Email Read"),
    "draft_email":                    ("mail",       "Gmail (Draft)",                  "Gmail Draft"),
    "send_email":                     ("mail",       "Gmail (Outbox)",                 "Gmail Send Confirmation"),
}


def _extract_sources(messages: list) -> list:
    """
    Collect every distinct tool call in this agent response turn.
    Returns a list of source dicts (one per unique tool name called),
    preserving call order and deduplicating by tool name.
    """
    seen: set = set()
    sources: list = []
    for msg in messages:
        if getattr(msg, "type", None) != "tool":
            continue
        name = getattr(msg, "name", None)
        if not name or name in seen:
            continue
        seen.add(name)
        meta = _TOOL_SOURCES.get(name)
        if not meta:
            continue
        badge_type, label, drawer_title = meta
        snippet = html_lib.escape(str(msg.content)[:400])
        sources.append({
            "type":        badge_type,
            "label":       label,
            "tool":        name,
            "drawerTitle": drawer_title,
            "drawerBody":  (
                f"<h4>Tool Called</h4><pre>{html_lib.escape(name)}</pre>"
                f"<h4>Result Snippet</h4>"
                f"<div class='excerpt'><pre style='white-space:pre-wrap'>{snippet}</pre></div>"
            ),
        })
    return sources


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    global cygeniq_agent, cygeniq_adversarial_agent
    print("Initializing Cygeniq Agent backend...")
    # Ensure RBAC users table exists in Supabase
    try:
        await ensure_users_table()
    except Exception as e:
        print(f"Warning: ensure_users_table: {e}")

    res = await init_agent()
    if isinstance(res, tuple):
        cygeniq_agent, cygeniq_adversarial_agent = res
    else:
        cygeniq_agent = res
        cygeniq_adversarial_agent = res

    if cygeniq_agent is None:
        print("WARNING: Agent failed to initialize. Check environment variables.")


# ---------------------------------------------------------------------------
# Routes — public
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    """Lightweight health check used by Render and uptime monitors."""
    return {
        "status": "ok",
        "agent_ready": cygeniq_agent is not None,
        "tool_count": agent.get_tool_count(),
        "mcp_servers": agent.MCP_SERVER_COUNT,
        "model": agent.LLM_MODEL,
        "rbac_enabled": True,
    }


# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------
@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request):
    """
    POST /auth/login  { "username": "...", "password": "..." }
    Returns a signed JWT on success.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body."})

    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return JSONResponse(status_code=400, content={"error": "username and password are required."})

    user = await authenticate_user(username, password)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid username or password."},
        )

    token = create_access_token(user.username, user.role)
    role_meta = ROLE_LABELS.get(user.role, {})
    starter_cards = ROLE_STARTER_CARDS.get(user.role, [])

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "role_icon": role_meta.get("icon", "👤"),
        "role_color": role_meta.get("color", "#888"),
        "role_bg": role_meta.get("bg", "rgba(0,0,0,0.1)"),
        "starter_cards": starter_cards,
    }


@app.get("/auth/me")
async def auth_me(request: Request):
    """GET /auth/me — returns current user info from JWT (no DB call)."""
    try:
        user: RoleUser = get_current_user(request)
    except Exception as e:
        return JSONResponse(status_code=401, content={"error": str(e)})

    role_meta = ROLE_LABELS.get(user.role, {})
    starter_cards = ROLE_STARTER_CARDS.get(user.role, [])
    denied = list(ROLE_DENIED_TOOLS.get(user.role, set()))

    return {
        "username": user.username,
        "role": user.role,
        "role_icon": role_meta.get("icon", "👤"),
        "role_color": role_meta.get("color", "#888"),
        "role_bg": role_meta.get("bg", "rgba(0,0,0,0.1)"),
        "starter_cards": starter_cards,
        "denied_tools": denied,
    }


# ---------------------------------------------------------------------------
# Routes — Chat (protected + RBAC enforced)
# ---------------------------------------------------------------------------
@app.post("/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request):
    # Optional JWT Authentication for Chat (supports both authenticated session & open testing)
    user = None
    try:
        user = get_current_user(request)
    except Exception:
        # Fall back to default admin role if not signed in via UI
        user = RoleUser(username="admin", role="admin")

    # Parse & validate input
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body."})

    user_input = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))

    if not user_input or not user_input.strip():
        return JSONResponse(status_code=400, content={"error": "No message provided."})

    if len(user_input) > 10_000:
        return JSONResponse(
            status_code=413,
            content={"error": "Message exceeds maximum allowed length of 10,000 characters."},
        )

    # /status shortcut (no LLM call, dynamic counts)
    if user_input.strip().lower() in {"status", "/status"}:
        role_meta = ROLE_LABELS.get(user.role, {})
        role_badge = (
            f'<span class="status-pill" style="background:{role_meta.get("bg","")};color:{role_meta.get("color","")}">'
            f'{role_meta.get("icon","👤")} {user.role.capitalize()}'
            f'</span>'
        )
        denied_tools = ROLE_DENIED_TOOLS.get(user.role, set())
        denied_list = (
            ", ".join(sorted(denied_tools)) if denied_tools else "None — full access"
        )
        tools_available = agent.get_tool_count()
        dashboard_html = f"""
<div class="system-dashboard-card">
  <div class="sdc-header">
    <div class="sdc-title-row">
      <span class="sdc-live-dot"></span>
      <strong class="sdc-title">Cygeniq AI Labs Agent</strong>
    </div>
    <span class="sdc-badge live">● Connected (Live)</span>
  </div>

  <div class="sdc-grid">
    <div class="sdc-metric">
      <span class="sdc-label">LLM Engine</span>
      <span class="sdc-val mono">{agent.LLM_MODEL}</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Orchestration</span>
      <span class="sdc-val">LangGraph (StateGraph)</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">MCP Servers</span>
      <span class="sdc-val highlight">{agent.MCP_SERVER_COUNT} Active Subsystems</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Tools Available</span>
      <span class="sdc-val highlight">{tools_available} Tools Loaded</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Knowledge Base</span>
      <span class="sdc-val">Supabase + SharePoint Graph</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Persistent Memory</span>
      <span class="sdc-val">SQLite Checkpointer (/app/data)</span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Signed In As</span>
      <span class="sdc-val">{role_badge} &nbsp;<code style="opacity:.7">{user.username}</code></span>
    </div>
    <div class="sdc-metric">
      <span class="sdc-label">Restricted Tools</span>
      <span class="sdc-val mono" style="font-size:.75rem;opacity:.8">{denied_list}</span>
    </div>
  </div>

  <div class="sdc-footer">
    <span class="sdc-footer-label">Active MCP Subsystems:</span>
    <div class="sdc-chips">
      <span class="schip db">🗄️ Supabase Postgres</span>
      <span class="schip file">📁 Knowledge Filesystem</span>
      <span class="schip memory">🧠 Persistent Knowledge Graph</span>
      <span class="schip sp">☁️ SharePoint &amp; OneDrive</span>
      <span class="schip policy">📜 Policy Intelligence</span>
      <span class="schip product">🛡️ Product Intelligence</span>
      <span class="schip grc">⚖️ GRC Regulatory Engine</span>
      <span class="schip mail">✉️ Gmail Integration</span>
    </div>
  </div>
</div>
"""
        return {"blocks": [dashboard_html], "sources": [], "source": None}

    # Agent readiness check
    if not cygeniq_agent:
        return JSONResponse(status_code=503, content={"error": "Agent is initializing or not ready. Please try again in a few moments."})

    # RBAC tool-guard: inject restriction notice into prompt
    denied_tools = ROLE_DENIED_TOOLS.get(user.role, set())
    rbac_prefix = ""
    if denied_tools:
        rbac_prefix = (
            f"\n\n[RBAC] The current user '{user.username}' has role '{user.role}'. "
            f"The following tools are FORBIDDEN for this session and must NOT be called: "
            f"{', '.join(sorted(denied_tools))}. "
            f"If the user requests something that requires a forbidden tool, politely explain "
            f"that their role does not permit access to that capability.\n\n"
        )

    # Invoke the agent
    try:
        config = {"configurable": {"thread_id": session_id}}
        augmented_input = rbac_prefix + user_input if rbac_prefix else user_input
        result = await cygeniq_agent.ainvoke(
            {"messages": [("user", augmented_input)]}, config
        )

        messages = result["messages"]
        final_message = messages[-1].content

        # Full multi-source attribution (filter out denied tools)
        all_sources = _extract_sources(messages)
        sources = [s for s in all_sources if is_tool_allowed(user.role, s["tool"])]

        # Backwards-compatible single `source` field
        primary_source = sources[0] if sources else None

        # Render markdown to HTML
        html_message = markdown.markdown(
            final_message,
            extensions=["tables", "fenced_code"],
        )

        return {
            "blocks":  [html_message],
            "sources": sources,
            "source":  primary_source,
            "user":    user.to_dict(),
        }

    except Exception as e:
        err_msg = str(e)
        print(f"[ERROR] chat_endpoint: {err_msg}")
        if "429" in err_msg or "rate_limit" in err_msg.lower():
            err_msg = "Groq LLM daily token rate limit reached (429). Quota resets shortly. You can use the AI Security Simulator in Safe Simulation mode to run offline risk analysis and test guardrails."
        return JSONResponse(status_code=500, content={"error": err_msg})


# ===========================================================================
# AI Security Simulator Endpoints
# ===========================================================================

@app.get("/testing/status")
async def testing_status():
    """Returns the current security testing mode state."""
    return {
        "llm_guardrails_disabled": LLM_GUARDRAILS_DISABLED,
        "agent_mode": "SECURITY_TESTING_MODE" if LLM_GUARDRAILS_DISABLED else "PRODUCTION",
        "note": "AI Security Simulator is ready with 13 check categories and evidence-based verdicts."
    }

@app.post("/simulator/stream")
async def simulator_stream(request: Request):
    """
    Accepts a test request and streams live real-time Server-Sent Events (SSE).
    """
    body = await request.json()
    prompt = body.get("prompt")
    if not prompt or not prompt.strip():
        return JSONResponse(status_code=400, content={"error": "Prompt is required for security testing."})

    execution_mode = body.get("execution_mode", "safe_simulation")
    categories = body.get("categories")
    target_tools = body.get("target_tools")
    disable_llm_guardrails = bool(
        LLM_GUARDRAILS_DISABLED or
        body.get("disable_llm_guardrails", False) or
        execution_mode in ["adversarial_testing", "adversarial_test", "controlled_testing_relaxed"]
    )
    target_agent = cygeniq_adversarial_agent if (disable_llm_guardrails and cygeniq_adversarial_agent) else cygeniq_agent

    return StreamingResponse(
        run_security_simulation_stream(
            prompt=prompt,
            execution_mode=execution_mode,
            categories_override=categories,
            target_tools=target_tools,
            cygeniq_agent=target_agent,
            disable_llm_guardrails=disable_llm_guardrails
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/simulator/stop")
async def simulator_stop(request: Request):
    """Cancels a currently executing security simulation stream."""
    body = await request.json()
    test_id = body.get("test_id")
    if not test_id:
        return JSONResponse(status_code=400, content={"error": "test_id is required."})
    success = cancel_active_test(test_id)
    return {"success": success, "test_id": test_id}

@app.get("/simulator/history")
async def simulator_history():
    """Returns list of past security test runs."""
    return security_db.list_test_history()

@app.get("/simulator/report/{test_id}")
async def simulator_report(test_id: str):
    """Returns full structured report for a given test ID."""
    report = security_db.get_test_run(test_id)
    if not report:
        return JSONResponse(status_code=404, content={"error": f"Report '{test_id}' not found."})
    return report

@app.get("/simulator/export/{test_id}")
async def simulator_export(test_id: str, format: str = "json"):
    """Exports test report as JSON or CSV."""
    if format.lower() == "csv":
        csv_data = security_db.export_report_csv(test_id)
        if not csv_data:
            return JSONResponse(status_code=404, content={"error": f"Report '{test_id}' not found."})
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=security_audit_{test_id}.csv"}
        )
    else:
        report = security_db.get_test_run(test_id)
        if not report:
            return JSONResponse(status_code=404, content={"error": f"Report '{test_id}' not found."})
        return JSONResponse(
            content=report,
            headers={"Content-Disposition": f"attachment; filename=security_audit_{test_id}.json"}
        )

@app.get("/simulator/tools")
async def simulator_tools():
    """Lists available MCP tools and security capabilities dynamically."""
    return get_available_mcp_tools()

@app.post("/simulator/clear")
async def simulator_clear():
    """Clears all stored test runs and audit history."""
    security_db.clear_test_history()
    return {"success": True, "message": "Test history cleared."}


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
