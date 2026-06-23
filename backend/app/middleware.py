"""Observability + security middleware: per-request audit log with timing, and
standard security response headers.
"""
from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler

from starlette.middleware.base import BaseHTTPMiddleware

from . import config

config.LOG_DIR.mkdir(parents=True, exist_ok=True)
_audit = logging.getLogger("crime.audit")
if not _audit.handlers:
    _audit.setLevel(logging.INFO)
    fh = RotatingFileHandler(config.LOG_DIR / "audit.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _audit.addHandler(fh)
    _audit.addHandler(logging.StreamHandler())


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        dur_ms = round((time.perf_counter() - start) * 1000, 1)
        role = "open"
        if config.AUTH_ENABLED:
            from .security import identify
            role = identify(request.headers.get("X-API-Key"))["role"] or "anon"
        client = request.client.host if request.client else "-"
        # only audit API calls (skip static asset noise)
        if request.url.path.startswith("/api") or request.url.path in ("/health", "/docs"):
            _audit.info(f"{client} role={role} {request.method} {request.url.path} "
                        f"-> {response.status_code} {dur_ms}ms")
        response.headers["X-Response-Time-ms"] = str(dur_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        return response
