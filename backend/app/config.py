"""Runtime configuration (env-driven). Safe dev defaults; hardened via env in prod.

Env vars:
  CRIME_API_KEYS    "key1:admin,key2:analyst,key3:viewer" — enables RBAC when set.
                    When UNSET, auth is OPEN (dev mode) so the demo runs with no setup.
  CRIME_CORS_ORIGINS  comma-separated allowed origins (default "*").
  CRIME_LOG_DIR       directory for audit logs (default backend/logs).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# role hierarchy: higher index = more privilege
ROLES = ["viewer", "analyst", "admin"]


def _parse_keys(raw: str) -> dict[str, str]:
    keys = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        k, role = pair.split(":", 1)
        role = role.strip().lower()
        if role in ROLES:
            keys[k.strip()] = role
    return keys


API_KEYS: dict[str, str] = _parse_keys(os.getenv("CRIME_API_KEYS", ""))
AUTH_ENABLED: bool = len(API_KEYS) > 0

CORS_ORIGINS = [o.strip() for o in os.getenv("CRIME_CORS_ORIGINS", "*").split(",") if o.strip()]

LOG_DIR = Path(os.getenv("CRIME_LOG_DIR", str(BACKEND_DIR / "logs")))
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def role_rank(role: str) -> int:
    return ROLES.index(role) if role in ROLES else -1
