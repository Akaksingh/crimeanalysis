"""Crime Analytics API + (optionally) the built frontend, on one origin.

Serves the district-level aggregates produced by the pipeline
(backend/data/processed/api/*.json). If a payload is missing the endpoint returns
503 with a hint to run `python -m pipeline.run`. When frontend/dist exists it is
served at / so the whole app runs from one server (no proxy, no stale-route 404s).

Phase 5 hardening: audit logging, security headers, configurable CORS, and
API-key RBAC gating the person-level (intelligence) endpoints.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pipeline import paths

from . import config
from .middleware import AuditMiddleware, SecurityHeadersMiddleware
from .security import analyst_required, identify

app = FastAPI(
    title="AI-Driven Crime Analytics API",
    version="0.5.0",
    description="District crime analytics, intelligence, and socio-economic correlation (pilot: Karnataka).",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load(name: str):
    path: Path = paths.API_DIR / name
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{name} not built. Run `python -m pipeline.run` first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _load(name: str):
    path: Path = paths.API_DIR / name
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{name} not built. Run `python -m pipeline.run` first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api")
def api_root():
    # API index. "/" is left for the served frontend (StaticFiles mount below).
    return {
        "service": "AI-Driven Crime Analytics API",
        "version": "0.5.0",
        "endpoints": [
            "/health", "/api/meta", "/api/districts", "/api/districts/{geo_unit_id}",
            "/api/hotspots", "/api/trends", "/api/kpi-catalog", "/api/categories",
            "/api/whoami", "/api/intelligence/repeat-offenders", "/api/intelligence/network",
            "/api/intelligence/patterns", "/api/socioeconomic", "/api/socioeconomic/correlations",
            "/api/socioeconomic/schema",
        ],
        "docs": "/docs",
    }


@app.get("/health")
def health():
    built = (paths.API_DIR / "districts.json").exists()
    return {"status": "ok", "data_built": built}


@app.get("/api/meta")
def meta():
    return _load("meta.json")


@app.get("/api/districts")
def districts():
    """District summary list (latest year), sorted by risk score desc."""
    return _load("districts.json")


@app.get("/api/districts/{geo_unit_id}")
def district_detail(geo_unit_id: str):
    """Full drilldown for one district: KPIs, yearly trend, category breakdown,
    hotspot status, and explainable risk-score components."""
    detail = _load("district_detail.json")
    rec = detail.get(geo_unit_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"district '{geo_unit_id}' not found")
    return rec


@app.get("/api/hotspots")
def hotspots():
    return _load("hotspots.json")


@app.get("/api/trends")
def trends():
    return _load("trends.json")


@app.get("/api/kpi-catalog")
def kpi_catalog():
    return _load("kpi_catalog.json")


@app.get("/api/categories")
def categories():
    return _load("categories.json")


@app.get("/api/whoami")
def whoami(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    who = identify(x_api_key)
    return {"role": who["role"], "auth_mode": who["mode"], "auth_enabled": config.AUTH_ENABLED}


# ---- Phase 3: intelligence (synthetic person-level + real-data ML) ----
# Person-level endpoints are gated to analyst+ (governance: synthetic PII). In dev
# (no CRIME_API_KEYS configured) access is open so the demo runs without setup.
@app.get("/api/intelligence/repeat-offenders")
def repeat_offenders(_=Depends(analyst_required)):
    """Top repeat offenders (SYNTHETIC data — see data_note). Requires analyst role when auth enabled."""
    return _load("intel_repeat_offenders.json")


@app.get("/api/intelligence/network")
def network(_=Depends(analyst_required)):
    """Co-offending network (SYNTHETIC). Requires analyst role when auth enabled."""
    return _load("intel_network.json")


@app.get("/api/intelligence/patterns")
def patterns():
    """AI/ML pattern detection on REAL data: district clusters + anomalies (no PII; open)."""
    return _load("intel_patterns.json")


# ---- Phase 4: socio-economic correlation (real Census 2011) ----
@app.get("/api/socioeconomic")
def socioeconomic():
    """Per-district socio-economic indicators (Census 2011)."""
    return _load("se_indicators.json")


@app.get("/api/socioeconomic/correlations")
def socioeconomic_correlations():
    """Correlation matrix: each indicator x each crime group (Pearson/Spearman,
    p-values, hypothesis verdicts) + ethical caveats."""
    return _load("se_correlations.json")


@app.get("/api/socioeconomic/schema")
def socioeconomic_schema():
    """The logically-backed indicator definitions + crime hypotheses."""
    return _load("se_schema.json")


# ---- serve the built frontend (single origin; eliminates proxy/stale-route 404s) ----
# Mounted LAST so all /api routes take precedence. Only active after `npm run build`.
if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
