# Frontend — React (Vite)

Phase 1 frontend: a minimal dashboard that consumes the district-level aggregate
API (district risk table + drilldown with KPIs, trend, category breakdown, and
the explainable risk components). The rich dashboards and the geospatial map are
**Phase 2** — this scaffold proves the API wiring and is the starting point.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The dev server proxies `/api` → `http://127.0.0.1:8000`, so start the backend first:

```bash
cd ../backend
python -m pipeline.run
uvicorn app.main:app --reload
```

To point at a deployed backend, copy `.env.example` → `.env` and set `VITE_API_BASE`.

## Next (Phase 2)
- MapLibre/Leaflet choropleth + hotspot heatmap (uses district boundaries from the manifest).
- Charting lib (Recharts) for trends/anomalies.
- Filters (crime type, year), district→station drilldown, alert center.
