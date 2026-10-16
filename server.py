import os
import uuid
import html as html_lib
import markdown
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    def get_real_client_ip(request: Request) -> str:
        """Extract client IP, checking X-Forwarded-For header for reverse proxies (Render, Nginx, Cloudflare)."""
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

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Cygeniq AI Labs Agent", version="1.0.0")
if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global agent reference
cygeniq_agent = None

# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
_API_KEY = (os.getenv("CYGENIQ_API_KEY") or "").strip()

def _check_auth(request: Request) -> bool:
    """Return True if auth passes. When CYGENIQ_API_KEY is unset, allow all (dev mode)."""
    if not _API_KEY:
        return True  # dev mode — no key configured
    provided = (request.headers.get("X-API-Key") or "").strip()
    return provided == _API_KEY


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
    cygeniq_agent = await init_agent()
    if cygeniq_agent is None:
        print("WARNING: Agent failed to initialize. Check environment variables.")


# ---------------------------------------------------------------------------
# Routes
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
        "auth_enabled": bool(_API_KEY),
    }


@app.post("/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request):
    # --- 1. Authentication ---
    if not _check_auth(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized. Provide a valid X-API-Key header."},
        )

    # --- 2. Agent readiness ---
    if not cygeniq_agent:
        return JSONResponse(status_code=503, content={"error": "Agent not ready. Check server logs."})

    # --- 3. Parse & validate input ---
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

    # --- 4. /status shortcut (no LLM call, dynamic counts) ---
    if user_input.strip().lower() in {"status", "/status"}:
        auth_line = "ON  (X-API-Key)" if _API_KEY else "OFF (dev mode) "
        rate_line  = "10 req/min/IP  "
        tools_available = agent.get_tool_count()
        dashboard = f"""```text
╔══════════════════════════════════════════════════╗
║            CYGENIQ AI LABS AGENT                 ║
╠══════════════════════════════════════════════════╣
║ LLM              {agent.LLM_MODEL:<32}║
║ Framework        LangGraph                       ║
║ MCP Servers      {agent.MCP_SERVER_COUNT:<32}║
║ Tools Available  {tools_available:<32}║
║ Database         Supabase / PostgreSQL           ║
║ Memory           Persistent (SQLite)             ║
║ Authentication   {auth_line:<32}║
║ Rate Limiting    {rate_line:<32}║
║ Status           ● Connected                     ║
╚══════════════════════════════════════════════════╝
```"""
        return {"blocks": [markdown.markdown(dashboard)], "sources": [], "source": None}

    # --- 5. Invoke the agent ---
    try:
        config = {"configurable": {"thread_id": session_id}}
        result = await cygeniq_agent.ainvoke(
            {"messages": [("user", user_input)]}, config
        )

        messages = result["messages"]
        final_message = messages[-1].content

        # --- 6. Full multi-source attribution ---
        sources = _extract_sources(messages)

        # Backwards-compatible single `source` field: first source (or None)
        primary_source = sources[0] if sources else None

        # --- 7. Render markdown → HTML ---
        html_message = markdown.markdown(
            final_message,
            extensions=["tables", "fenced_code"],
        )

        return {
            "blocks":  [html_message],
            "sources": sources,          # new: full list
            "source":  primary_source,   # legacy: first source (UI badge)
        }

    except Exception as e:
        print(f"[ERROR] chat_endpoint: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
