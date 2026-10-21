import os
import uuid
import html as html_lib
import markdown
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
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
from agent import init_agent
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

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Cygeniq AI Labs Agent", version="2.0.0")
if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global agent reference
cygeniq_agent = None

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
        if msg.type != "tool":
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
    global cygeniq_agent
    print("Initializing Cygeniq Agent backend...")
    # Ensure RBAC users table exists in Supabase
    await ensure_users_table()
    cygeniq_agent = await init_agent()
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
    # --- 1. JWT Authentication ---
    try:
        user: RoleUser = get_current_user(request)
    except Exception as exc:
        return JSONResponse(status_code=401, content={"error": str(exc)})

    # --- 2. Parse & validate input ---
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

    # --- 3. /status shortcut (no LLM call, dynamic counts) ---
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
      <span class="schip file">📂 Knowledge Filesystem</span>
      <span class="schip memory">🧠 Persistent Knowledge Graph</span>
      <span class="schip sp">☁️ SharePoint &amp; OneDrive</span>
      <span class="schip policy">📜 Policy Intelligence</span>
      <span class="schip product">🛡️ Product Intelligence</span>
      <span class="schip grc">⚖️ GRC Regulatory Engine</span>
    </div>
  </div>
</div>
"""
        return {"blocks": [dashboard_html], "sources": [], "source": None}

    # --- 4. Agent readiness check (for LLM queries) ---
    if not cygeniq_agent:
        return JSONResponse(status_code=503, content={"error": "Agent is initializing or not ready. Please try again in a few moments."})

    # --- 5. RBAC tool-guard: inject restriction notice into prompt ---
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

    # --- 6. Invoke the agent ---
    try:
        config = {"configurable": {"thread_id": session_id}}
        augmented_input = rbac_prefix + user_input if rbac_prefix else user_input
        result = await cygeniq_agent.ainvoke(
            {"messages": [("user", augmented_input)]}, config
        )

        messages = result["messages"]
        final_message = messages[-1].content

        # --- 7. Full multi-source attribution (filter out denied tools) ---
        all_sources = _extract_sources(messages)
        sources = [s for s in all_sources if is_tool_allowed(user.role, s["tool"])]

        # Backwards-compatible single `source` field
        primary_source = sources[0] if sources else None

        # --- 8. Render markdown → HTML ---
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
        print(f"[ERROR] chat_endpoint: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
