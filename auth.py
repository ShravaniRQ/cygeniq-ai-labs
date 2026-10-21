"""
auth.py — Cygeniq AI Labs RBAC Authentication Module
=====================================================
Handles:
  - Role definitions and per-role tool allow-lists
  - Password hashing (bcrypt via passlib)
  - JWT creation and verification (python-jose)
  - Supabase (asyncpg) user lookup at login time
  - FastAPI dependency: get_current_user() → injects RoleUser into endpoints
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()

import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, status
import bcrypt

try:
    from jose import JWTError, jwt as _jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "cygeniq-dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours

# ---------------------------------------------------------------------------
# Password hashing (direct bcrypt)
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    plain_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(plain_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        plain_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

# Tools that are permanently BLOCKED for each role (deny-list approach)
ROLE_DENIED_TOOLS: dict[str, set[str]] = {
    "admin": set(),  # admin: no restrictions

    "analyst": {
        # No SharePoint write
        "upload_sharepoint_document",
        # No memory graph mutations
        "create_entities", "create_relations", "add_observations",
        "delete_entities", "delete_observations", "delete_relations",
    },

    "presales": {
        # No DB access
        "query", "list_tables", "describe_table",
        # No GRC tools
        "list_regulatory_frameworks", "get_framework_controls",
        "map_control_to_product_evidence", "evaluate_compliance_gap",
        "generate_compliance_checklist",
        # No SharePoint write
        "upload_sharepoint_document",
        # No memory mutations
        "create_entities", "create_relations", "add_observations",
        "delete_entities", "delete_observations", "delete_relations",
    },
}

# UI starter cards shown per role (list of {icon, label, prompt})
ROLE_STARTER_CARDS: dict[str, list[dict]] = {
    "admin": [
        {"icon": "🗄️", "label": "Employee risk report",   "prompt": "Show me all high-risk employees from the database"},
        {"icon": "⚖️", "label": "RBI compliance gap",     "prompt": "Evaluate our current security posture against RBI Cybersecurity Framework controls"},
        {"icon": "🛡️", "label": "HexaShield overview",   "prompt": "Get the full HexaShield AI product datasheet"},
        {"icon": "📜", "label": "Policy audit",           "prompt": "Search all policies related to data retention"},
        {"icon": "☁️", "label": "SharePoint upload",      "prompt": "Upload a compliance audit report to SharePoint"},
        {"icon": "🧠", "label": "Memory graph",           "prompt": "Read the current knowledge graph memory"},
    ],
    "analyst": [
        {"icon": "⚖️", "label": "RBI compliance gap",    "prompt": "Evaluate our current security posture against RBI Cybersecurity Framework controls"},
        {"icon": "📊", "label": "Regulatory frameworks",  "prompt": "List all supported regulatory frameworks"},
        {"icon": "🛡️", "label": "Product capabilities",  "prompt": "Search product capabilities for AI red teaming"},
        {"icon": "📜", "label": "Policy search",          "prompt": "Search all policies related to data retention"},
        {"icon": "🗄️", "label": "Employee records",      "prompt": "Show me all employees in the engineering department"},
        {"icon": "📑", "label": "Audit checklist",        "prompt": "Generate a compliance checklist for banking sector"},
    ],
    "presales": [
        {"icon": "🛡️", "label": "HexaShield datasheet",  "prompt": "Get the full HexaShield AI product datasheet"},
        {"icon": "🎯", "label": "Match RFP requirement",  "prompt": "Match this RFP requirement to product features: AI red teaming and runtime monitoring"},
        {"icon": "📦", "label": "List products",          "prompt": "List all Cygeniq products with a brief summary"},
        {"icon": "🔍", "label": "Product capabilities",   "prompt": "Search product capabilities for prompt injection testing"},
        {"icon": "📜", "label": "Policy overview",        "prompt": "List all available internal policies"},
        {"icon": "☁️", "label": "SharePoint search",      "prompt": "Search SharePoint for AI governance documents"},
    ],
}

ROLE_LABELS = {
    "admin":    {"color": "#ef4444", "bg": "rgba(239,68,68,0.12)",   "icon": "🔑"},
    "analyst":  {"color": "#3b82f6", "bg": "rgba(59,130,246,0.12)",  "icon": "📊"},
    "presales": {"color": "#10b981", "bg": "rgba(16,185,129,0.12)",  "icon": "🎯"},
}


def is_tool_allowed(role: str, tool_name: str) -> bool:
    """Return True if the given role may call this tool."""
    denied = ROLE_DENIED_TOOLS.get(role, set())
    return tool_name not in denied


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

class RoleUser:
    """Lightweight user model attached to each request after auth."""
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

    def to_dict(self) -> dict:
        return {"username": self.username, "role": self.role}


def create_access_token(username: str, role: str) -> str:
    if not HAS_JOSE:
        raise RuntimeError("python-jose is not installed. Run: pip install python-jose[cryptography]")
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify JWT. Returns payload dict or None on failure."""
    if not HAS_JOSE:
        return None
    try:
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def extract_bearer_token(request: Request) -> Optional[str]:
    """Pull Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def get_current_user(request: Request) -> RoleUser:
    """
    FastAPI dependency. Raises HTTP 401 if token is missing/invalid.
    Usage:  user: RoleUser = Depends(get_current_user)
    """
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("sub")
    role = payload.get("role")
    if not username or role not in ROLE_DENIED_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown role '{role}'. Contact your administrator.",
        )
    return RoleUser(username=username, role=role)


# ---------------------------------------------------------------------------
# Supabase user store (asyncpg)
# ---------------------------------------------------------------------------

async def get_db_connection() -> asyncpg.Connection:
    db_url = os.getenv("SUPABASE_URL", "")
    if not db_url:
        raise RuntimeError("SUPABASE_URL is not configured.")
    return await asyncpg.connect(db_url)


async def ensure_users_table() -> None:
    """
    Create the cygeniq_users table if it doesn't exist.
    Called once at startup.
    """
    try:
        conn = await get_db_connection()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cygeniq_users (
                    id            SERIAL PRIMARY KEY,
                    username      TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'presales')),
                    full_name     TEXT,
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    is_active     BOOLEAN DEFAULT TRUE
                );
            """)
            # Ensure default seed users exist for all 3 roles
            initial_users = [
                ("admin", os.getenv("ADMIN_DEFAULT_PASSWORD", "CygeniqAdmin2024!"), "admin", "System Administrator"),
                ("analyst1", "Analyst2024!", "analyst", "Compliance Analyst"),
                ("presales1", "Presales2024!", "presales", "Presales Consultant"),
            ]
            for u, p, r, fn in initial_users:
                await conn.execute("""
                    INSERT INTO cygeniq_users (username, password_hash, role, full_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (username) DO NOTHING;
                """, u, hash_password(p), r, fn)
            print("[auth] Ensured default RBAC users exist (admin, analyst1, presales1)")
        finally:
            await conn.close()
    except Exception as e:
        print(f"[auth] WARNING: Could not set up users table: {e}")
        print("[auth] Auth will fall back to env-var user registry.")


async def authenticate_user(username: str, password: str) -> Optional[RoleUser]:
    """
    Verify username + password against cygeniq_users table.
    Falls back to CYGENIQ_USERS env var if not in DB or DB is unavailable.
    Returns RoleUser on success, None on failure.
    """
    # --- Primary: Supabase DB ---
    try:
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow(
                "SELECT username, password_hash, role FROM cygeniq_users WHERE username = $1 AND is_active = TRUE",
                username
            )
        finally:
            await conn.close()

        if row:
            if verify_password(password, row["password_hash"]):
                return RoleUser(username=row["username"], role=row["role"])
            return None  # User found in DB but wrong password

    except Exception as e:
        print(f"[auth] DB auth failed ({e}), falling back to ENV registry.")

    # --- Fallback: environment variable registry ---
    # Format: CYGENIQ_USERS=admin:password:admin,bob:pass123:analyst
    registry_str = os.getenv("CYGENIQ_USERS", "")
    if registry_str:
        for entry in registry_str.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 3:
                u, p, r = parts
                if u == username and p == password and r in ROLE_DENIED_TOOLS:
                    return RoleUser(username=u, role=r)

    return None
