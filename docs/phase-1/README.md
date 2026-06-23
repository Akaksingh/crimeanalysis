# Phase 1 & 2 — Data Foundation + Geospatial MVP

Phase 1 turns the Phase 0 contracts into a working data layer; Phase 2 adds the
interactive map. Both run on **real, verified data** for **all 30 Karnataka
districts**.

## Real data sources (no hardcoded numbers)

| Data | Source | Used for |
|------|--------|----------|
| District-wise IPC crimes, 2001–2012 | NCRB (via data.gov.in open dataset) | all crime counts / KPIs / hotspots / risk |
| District populations | Census of India 2011 | rate denominators (`per 100k`) |
| District boundaries + Census codes | Census 2011 (datameet GeoJSON, 30 districts) | the map + geo spine |

Files land in `backend/data/raw/` (see [manifest](../../backend/data/manifest.json)).
**Verification:** the ingested leaf-column sum reconciles **exactly** to NCRB's own
reported IPC total (1,473,476 cases; 0 difference) — checked every run by the
data-quality stage.

## Pipeline (`python -m pipeline.run`)

```
ingest        real GeoJSON + NCRB CSV  ->  canonical geo_units + incidents (case_count)
              + boundary geojson (with geo_unit_id) for the map
build_kpis    KPI facts + z-score hotspots + explainable baseline risk + API payloads
data_quality  schema validation, NCRB reconciliation, 30-district coverage, mapping audit
```

A **source adapter** ([pipeline/sources/ncrb_ipc.py](../../backend/pipeline/sources/ncrb_ipc.py))
isolates the messy real source: it maps 2012-era NCRB district names → Census-2011
names (aggregating commissionerate/city/rural splits) and selects only leaf crime
columns (excluding totals/subtotals) so nothing double-counts.

## API (FastAPI — `uvicorn app.main:app --reload`, docs at `/docs`)

| Endpoint | Returns |
|----------|---------|
| `GET /api/meta` | platform metadata, years, sources |
| `GET /api/districts` | 30 districts (latest year), sorted by risk |
| `GET /api/districts/{geo_unit_id}` | drilldown: KPIs, 2001–2012 trend, category breakdown, hotspot, explainable risk |
| `GET /api/hotspots` | districts flagged emerging/established |
| `GET /api/trends` | state-level yearly totals |
| `GET /api/kpi-catalog` · `GET /api/categories` | Phase 0 contracts (passthrough) |

## Map (Phase 2 — React + Leaflet)

[frontend/src/CrimeMap.jsx](../../frontend/src/CrimeMap.jsx): choropleth of the 30
district polygons colored by risk band, **hotspot markers** at district centroids
(red = established, amber = emerging), and a **crime heatmap** layer weighted by the
severity-weighted index. All layers are data-driven from the API + boundary GeoJSON —
nothing static. Click a district (map or table) to drill down.

## Run it

```bash
cd backend && pip install -r requirements.txt && python -m pipeline.run
uvicorn app.main:app --reload                       # API :8000
cd ../frontend && npm install && npm run dev        # UI  :5173
```

## Status / caveats

- ✅ All 30 districts, real NCRB + Census + boundaries, exact reconciliation.
- ⚠️ NCRB district-level machine-readable data is **2001–2012** (latest clean public
  series); recent years are PDF-only. Risk for newly-formed districts (e.g. Ramanagara,
  est. 2007) is trend-inflated — a known recorded-crime caveat.
- ⏳ Store is JSON files (→ PostgreSQL/PostGIS later); LGD codes + socio-economic
  layer to be ingested next.
