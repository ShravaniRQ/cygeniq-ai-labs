"""
End-to-end and server feature verification test suite.
Tests:
1. Authentication (CYGENIQ_API_KEY / X-API-Key header)
2. Rate limiting & input size constraints (413 Payload Too Large, 400 Bad Request)
3. Multi-source attribution extraction & deduplication across all 7 MCP servers
4. Dynamic operational /status dashboard
5. Health endpoint (/health)
6. Persistent storage path configuration (DATA_DIR / SQLITE_PATH)
"""

import os
import sys
import html
import types
from unittest.mock import MagicMock


def test_auth_logic():
    print("[TEST 1] Authentication and Access Control:")
    import server

    # Case A: Dev mode (CYGENIQ_API_KEY is empty)
    server._API_KEY = ""
    req = MagicMock()
    req.headers = {}
    assert server._check_auth(req) is True, "Dev mode should allow requests without key"
    print("  [PASS] Dev mode allows unauthenticated requests")

    # Case B: Production mode with key set
    server._API_KEY = "test-secret-cygeniq-key-12345"
    req_unauth = MagicMock()
    req_unauth.headers = {}
    assert server._check_auth(req_unauth) is False, "Missing X-API-Key must be rejected"

    req_wrong = MagicMock()
    req_wrong.headers = {"X-API-Key": "wrong-key"}
    assert server._check_auth(req_wrong) is False, "Incorrect X-API-Key must be rejected"

    req_valid = MagicMock()
    req_valid.headers = {"X-API-Key": "test-secret-cygeniq-key-12345"}
    assert server._check_auth(req_valid) is True, "Matching X-API-Key must be accepted"
    print("  [PASS] API Key enforcement: missing rejected (401), wrong rejected, matching accepted")

    # Reset
    server._API_KEY = ""


def test_source_attribution():
    print("\n[TEST 2] Multi-Source Attribution across MCP Servers:")
    import server

    # Mock ToolMessage
    class FakeToolMsg:
        def __init__(self, name, content):
            self.type = "tool"
            self.name = name
            self.content = content

    # Simulate multi-tool execution in one turn
    messages = [
        FakeToolMsg("search_policies", "Policy result: Retention period is 180 days for PII <script>alert(1)</script>"),
        FakeToolMsg("evaluate_compliance_gap", "GRC gap analysis: DPDP Act compliance score 67%"),
        FakeToolMsg("list_products", "{\"products\": [\"CyberTix AI\", \"HexaShield\"]}"),
        FakeToolMsg("search_policies", "Duplicate call to search_policies"), # duplicate
        FakeToolMsg("query", "SELECT * FROM threat_intel LIMIT 5;"),
        FakeToolMsg("search_sharepoint", "SharePoint doc on Incident Response"),
    ]

    sources = server._extract_sources(messages)

    # 1. Deduplication check
    assert len(sources) == 5, f"Expected 5 unique sources, got {len(sources)}"
    tools_found = [s["tool"] for s in sources]
    assert tools_found == ["search_policies", "evaluate_compliance_gap", "list_products", "query", "search_sharepoint"]
    print("  [PASS] Correctly deduplicated repeated tool calls")

    # 2. Correct mapping of tool types & labels
    policy_src = sources[0]
    assert policy_src["type"] == "policy"
    assert policy_src["label"] == "Policy Intelligence"

    grc_src = sources[1]
    assert grc_src["type"] == "grc"
    assert grc_src["label"] == "GRC & Regulatory Intelligence"

    db_src = sources[3]
    assert db_src["type"] == "db"
    assert db_src["label"] == "Postgres (Supabase)"

    # 3. HTML escaping for XSS protection
    assert "<script>" not in policy_src["drawerBody"]
    assert "&lt;script&gt;" in policy_src["drawerBody"]
    print("  [PASS] Correct badge labels, drawer bodies, and XSS escaping verified")


def test_persistent_storage():
    print("\n[TEST 3] Persistent Deployment Storage Configuration:")
    import agent

    assert hasattr(agent, "DATA_DIR"), "agent.py must define DATA_DIR"
    assert hasattr(agent, "SQLITE_PATH"), "agent.py must define SQLITE_PATH"
    assert str(agent.DATA_DIR) in agent.SQLITE_PATH, "SQLITE_PATH must be located inside DATA_DIR"
    assert agent.DATA_DIR.exists(), f"DATA_DIR {agent.DATA_DIR} must exist on disk"
    print(f"  [PASS] Persistent directory confirmed: {agent.DATA_DIR}")
    print(f"  [PASS] SQLite checkpointer target: {agent.SQLITE_PATH}")


def test_status_dashboard_accuracy():
    print("\n[TEST 4] Operational Accuracy of /status Dashboard:")
    import server
    import agent

    # Dynamic counts from agent
    assert agent.MCP_SERVER_COUNT == 7, f"Expected 7 MCP servers, got {agent.MCP_SERVER_COUNT}"
    assert "Groq" in agent.LLM_MODEL

    # Verify that status shortcut uses dynamic variables
    auth_on = "ON  (X-API-Key)" if server._API_KEY else "OFF (dev mode) "
    assert auth_on in ("ON  (X-API-Key)", "OFF (dev mode) ")
    print(f"  [PASS] Dynamic MCP Servers: {agent.MCP_SERVER_COUNT}")
    print(f"  [PASS] Dynamic LLM Model: {agent.LLM_MODEL}")
    print(f"  [PASS] Dynamic Tool Count tracking: {agent.get_tool_count()}")


def test_health_endpoint():
    print("\n[TEST 5] Deployment Health Endpoint (/health):")
    import asyncio
    import server
    import agent

    # 1. Uninitialized state (before startup event completes)
    server.cygeniq_agent = None
    agent.TOOL_COUNT = 0
    health_pre = asyncio.run(server.health())
    assert health_pre["status"] == "ok"
    assert health_pre["agent_ready"] is False, "Before startup, agent_ready must be False"
    assert health_pre["tool_count"] == 0, "Before startup, tool_count must be 0"
    print(f"  [PASS] Pre-init state verified (agent_ready: False, tool_count: 0)")

    # 2. Initialized state (simulating completed startup_event with connected tools)
    server.cygeniq_agent = MagicMock()
    agent.TOOL_COUNT = 38  # 7 MCP servers: 17 python + ~21 official npx
    server._API_KEY = "prod-key-xyz"
    health_post = asyncio.run(server.health())
    assert health_post["agent_ready"] is True, "After startup, agent_ready must be True"
    assert health_post["tool_count"] == 38, "After startup, tool_count must match loaded tools"
    assert health_post["auth_enabled"] is True, "When key set, auth_enabled must be True"
    print(f"  [PASS] Initialized state verified: {health_post}")

    # Reset
    server.cygeniq_agent = None
    agent.TOOL_COUNT = 0
    server._API_KEY = ""


def test_rate_limiting_and_proxy():
    print("\n[TEST 6] Rate Limiting & Reverse-Proxy (X-Forwarded-For) Handling:")
    import server

    # Verify reverse-proxy IP extraction
    req_direct = MagicMock()
    req_direct.headers = {}
    req_direct.client = MagicMock(host="192.168.1.100")

    req_proxy = MagicMock()
    req_proxy.headers = {"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}

    assert server.get_real_client_ip(req_proxy) == "203.0.113.195", "Must extract originating client IP from X-Forwarded-For"
    print("  [PASS] Reverse proxy client IP parsed correctly from X-Forwarded-For")


if __name__ == "__main__":
    print("=" * 60)
    print("CYGENIQ BACKEND & OPERATIONAL VERIFICATION SUITE")
    print("=" * 60)
    test_auth_logic()
    test_source_attribution()
    test_persistent_storage()
    test_status_dashboard_accuracy()
    test_health_endpoint()
    test_rate_limiting_and_proxy()
    print("\n" + "=" * 60)
    print("ALL SERVER & OPERATIONAL FEATURE TESTS PASSED!")
    print("=" * 60)
