# Phase 5 — Hardening & Rollout

Production-readiness layer over the Phase 0–4 platform: one-origin serving, access
control, auditability, security headers, and containerized deployment.

## What was added

| Area | Delivered | Where |
|------|-----------|-------|
| Single-origin serving | FastAPI serves the built frontend at `/` — no proxy, eliminates stale-route/proxy 404s | [app/main.py](../../backend/app/main.py) |
| RBAC (API key + roles) | `viewer < analyst < admin`; person-level (intelligence) endpoints require **analyst+**. Dev-open when no keys set | [app/security.py](../../backend/app/security.py) |
| Audit logging | Per-request log (client, role, method, path, status, ms) → rotating file + stdout | [app/middleware.py](../../backend/app/middleware.py) |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection` | [app/middleware.py](../../backend/app/middleware.py) |
| Configurable CORS | `CRIME_CORS_ORIGINS` (default `*` for dev) | [app/config.py](../../backend/app/config.py) |
| Containerization | Multi-stage Docker build (frontend → FastAPI) + compose; bakes the data layer | [Dockerfile](../../Dockerfile), [docker-compose.yml](../../docker-compose.yml) |

## Run

**Single server (production-style):**
```bash
cd frontend && npm install && npm run build      # produces frontend/dist
cd ../backend && pip install -r requirements.txt && python -m pipeline.run
uvicorn app.main:app --host 0.0.0.0 --port 8000   # whole app at http://localhost:8000
```

**Docker:**
```bash
docker compose up --build                          # http://localhost:8000
```

**Dev (hot reload):** `npm run dev` (proxies `/api` → `:8000`) + a **freshly restarted**
`uvicorn app.main:app --reload` backend.

## Access control

| Config | Behaviour |
|--------|-----------|
| `CRIME_API_KEYS` unset (default) | **open** — every endpoint accessible (demo) |
| `CRIME_API_KEYS="k1:admin,k2:analyst,k3:viewer"` | enforced — send `X-API-Key`; `/api/intelligence/*` needs analyst+ |

`GET /api/whoami` reports the caller's resolved role and auth mode.

## Governance checklist (ties to roadmap §9)

- [x] Person-level (synthetic) data gated behind analyst role.
- [x] Full request audit trail (who/what/when/status).
- [x] PII minimization enforced at the schema level (Phase 0 `entity` schema: masked names, age bands).
- [x] Ethical caveats surfaced in the socio-economic UI (ecological fallacy, non-causality, protected attributes).
- [ ] Replace API-key auth with real IdP/SSO + per-user roles before production.
- [ ] Move processed store from JSON files to PostgreSQL/PostGIS.
- [ ] Pen-test, secrets management, TLS termination at the edge.

## Notes
- The Docker image bakes the canonical/API layer at build time from the committed
  real data; rebuild to refresh.
- Audit logs persist to the `audit-logs` volume in compose.
