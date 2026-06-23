"""API-key RBAC. Person-level (synthetic offender) endpoints are gated to analyst+
per the Phase 0 governance split. When no keys are configured (dev), all access is
open so the demo runs without setup; configure CRIME_API_KEYS to enforce.
"""
from __future__ import annotations

from fastapi import Header, HTTPException

from . import config


def identify(x_api_key: str | None) -> dict:
    """Resolve an API key to {role, authenticated}. Dev mode (no keys) => admin/open."""
    if not config.AUTH_ENABLED:
        return {"role": "admin", "authenticated": False, "mode": "open"}
    role = config.API_KEYS.get(x_api_key or "")
    if role is None:
        return {"role": None, "authenticated": False, "mode": "enforced"}
    return {"role": role, "authenticated": True, "mode": "enforced"}


def require_role(min_role: str):
    """FastAPI dependency factory: require >= min_role (no-op in dev/open mode)."""
    def dep(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
        who = identify(x_api_key)
        if not config.AUTH_ENABLED:
            return who
        if who["role"] is None:
            raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")
        if config.role_rank(who["role"]) < config.role_rank(min_role):
            raise HTTPException(status_code=403, detail=f"requires role '{min_role}' or higher")
        return who
    return dep


analyst_required = require_role("analyst")
