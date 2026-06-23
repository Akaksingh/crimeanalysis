# AI-Driven Crime Analytics & Visualization Platform Roadmap

## 1. Challenge Context

### Challenge

Build a modern AI-powered analytics platform that transforms fragmented crime records into actionable intelligence.

### Problem Statement

Current systems rely on siloed data and manual reporting, limiting advanced analytics and proactive policing capabilities.

## 2. Target Outcomes

- Unify disconnected crime and contextual datasets into a single analytical layer.
- Enable faster, evidence-backed decision-making at command, district, and station levels.
- Move from reactive reporting to proactive prevention through risk prediction and anomaly detection.
- Provide intuitive geospatial and dashboard experiences for field and leadership users.

## 3. Scope and Key Capabilities

### In Scope (from challenge brief)

- Network and link analysis of criminals
- Repeat offender tracking
- Socio-economic crime correlation
- Predictive risk scoring
- AI/ML-based pattern detection
- Interactive dashboards and geospatial maps
- Crime hotspot detection
- District-level drilldowns
- Trend alerts and anomaly detection

### Out of Scope for Phase 1

- Full national-scale integrations across all states
- Public-facing open data portals
- End-to-end judicial workflow management

## 3.1 Problem-Statement Compliance & Status (as of 2026-06-22)

Every capability named in **Challenge 02 — AI-Driven Crime Analytics & Visualization
Platform** is implemented and serving from real data. Status legend: ✅ Done ·
🟡 Partial / baseline · ⬜ Not started.

| # | Challenge capability                     | Status | Where it lives                                                                                                                                                                                            |
| - | ---------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Interactive dashboards & geospatial maps | ✅     | [CrimeMap.jsx](frontend/src/CrimeMap.jsx) (Leaflet, dark basemap) + [App.jsx](frontend/src/App.jsx); `/api/districts`, `/api/meta`                                                                          |
| 2 | Crime hotspot detection                  | ✅     | z-score on severity-weighted index in[build_kpis.py](backend/pipeline/build_kpis.py); `/api/hotspots`                                                                                                      |
| 3 | District-level drilldowns                | ✅     | KPIs + trend + category mix + explainable risk;`/api/districts/{id}`                                                                                                                                    |
| 4 | Trend alerts & anomaly detection         | 🟡     | year-over-year z-score anomalies in[intelligence.py](backend/pipeline/intelligence.py); `/api/intelligence/patterns`, `/api/trends`. **Detection done; push/notification alerting still pending.** |
| 5 | Network & link analysis of criminals     | ✅*    | co-offending graph, degree centrality, components in[intelligence.py](backend/pipeline/intelligence.py); `/api/intelligence/network`                                                                       |
| 6 | Repeat offender tracking                 | ✅*    | repeat-offender resolution + timelines;`/api/intelligence/repeat-offenders`                                                                                                                             |
| 7 | Socio-economic crime correlation         | ✅     | Pearson/Spearman + hypotheses in[socioeconomic.py](backend/pipeline/socioeconomic.py); `/api/socioeconomic/correlations`                                                                                   |
| 8 | Predictive risk scoring                  | 🟡     | transparent baseline 0–100 with Low/Med/High/Critical bands in[build_kpis.py](backend/pipeline/build_kpis.py). **Heuristic/explainable; a trained/calibrated forecast model is still pending.**       |
| 9 | AI/ML-based pattern detection            | ✅     | K-means clustering of districts by crime signature;`/api/intelligence/patterns`                                                                                                                         |

`*` Tracks 5 and 6 require person-level records that **do not exist as open data** in
India. They run on **synthetic, deterministic offenders** anchored to the real district
crime volumes/mix (governance split defined in Phase 0). Swap in pilot-shared,
anonymized FIR/case extracts to make these production-real — no code changes to the
contract are needed.

### What remains (gap list)

- **Trend alerting/notifications** — anomalies are detected and surfaced in the UI, but
  there is no alert center, email/push, or watchlist-trigger delivery yet.
- **Calibrated predictive model** — current risk score is an explainable heuristic; a
  validated time-series/ML forecast (with backtesting) is not built.
- **Real person-level intelligence** — link analysis & repeat-offender tracking await a
  data-sharing MOU; today they are synthetic.
- **Live / latest data ingestion** — see §3.2; the platform runs on a static NCRB
  **2001–2013** snapshot (2013 is the latest open, reconcilable district-IPC year).
- **Pilot validation & production signoff** — RBAC/audit/containerization are done
  (Phase 5), but threshold tuning with real analysts and governance signoff are pending.

## 3.2 Data Freshness — current state and path to "live/latest"

**Current state: STATIC, not live.** All analytics run on data files that were
downloaded once and committed to the repo — the pipeline reads local files, it does not
fetch anything at runtime:

- `backend/data/raw/ncrb_district_ipc_2001_2012.csv` + `ncrb_district_ipc_2013.csv` —
  NCRB district-wise IPC crimes, **2001–2013**, ingested together (same 33-column
  schema; ingested totals reconcile **exactly** to NCRB's reported totals,
  1,609,252 = 1,609,252).
- `backend/data/raw/karnataka_districts.geojson` + Census 2011 population/socio-economic
  seeds.

To refresh today you must manually re-download into `data/raw/` (same filename) and
re-run `python -m pipeline.run` (documented in `backend/data/manifest.json`).

**Why the data stops at 2013 (the hard ceiling we hit while extending it):**

- **2013** is the latest year published in the clean, machine-readable, 33-column
  district-IPC schema — it ingests and reconciles exactly, so it's in.
- **2014, 2015, 2017** exist but in NCRB's much wider "Crime in India" tables (90–250
  columns, multi-row banner headers, sub-split crime heads). They cannot be reconciled
  against the canonical contract without bespoke per-year adapters and carry real risk of
  wrong numbers — deliberately **not** ingested.
- **2016** publishes district rows with **no state column** (796 all-India districts);
  only 17 of Karnataka's 30 districts are name-matchable, so it would yield incomplete,
  possibly mis-attributed data — **not** ingested.
- **2019–2026** district-wise IPC data **does not exist** in any machine-readable open
  form. NCRB releases annually (~1 year late, latest volume 2022) as PDF/Excel
  state/national tables, not district CSVs. Truly current data requires a police
  CCTNS/FIR feed under a data-sharing MOU.

So **2013 is the genuine latest reconcilable year** from open sources. Reaching 2014–2018
would require manual PDF/wide-table extraction per year (approximate, not exact);
reaching 2019+ requires a pilot data agreement.

## 4. Product Architecture (High-Level)

### Data Layer

- Ingestion pipelines for crime records, FIR/case metadata, geography, and socio-economic indicators.
- Canonical schema to normalize district/station/incident entities.
- Geospatial storage for boundaries and coordinates.

### Intelligence Layer

- Graph/link analysis engine for person-case-location relationships.
- Repeat offender resolution and profile enrichment.
- Risk scoring service combining temporal, spatial, and behavioral factors.
- Pattern and anomaly detection models for spikes, clusters, and recurring signatures.

### Experience Layer

- Role-based dashboards for command, analysts, and district teams.
- Interactive map views with heatmaps, clusters, and district drilldowns.
- Alert center for trend breaks and abnormal incident patterns.

## 5. User Personas

- Command Leadership: strategy, district comparisons, resource prioritization.
- Crime Analysts: pattern mining, hotspot analysis, trend explanation.
- District/Station Officers: local drilldowns, repeat offender visibility, tactical action.
- Admin/Operations: data quality, access control, model monitoring.

## 6. Phased Delivery Plan

### Phase 0: Discovery and Data Contract (Week 1-2) — DELIVERED

- Finalize crime taxonomy, district/station hierarchy, and core KPIs.
- Confirm available data sources and legal/access constraints.
- Define baseline metrics for hotspot detection and risk scoring.
- **Deliverables built in [docs/phase-0/](docs/phase-0/README.md)** — canonical taxonomy,
  geo hierarchy, KPI catalog, data-source register, JSON Schemas, and baseline hotspot/risk
  methods, all with machine-readable contracts and a passing validator
  (`node docs/phase-0/contracts/validate.mjs`).

### Phase 1: Foundation and Unified Data Model (Week 3-5) — DELIVERED

- Build ingestion for primary crime records and geography datasets.
- Implement canonical model and data quality checks.
- Deliver first district-level aggregate APIs.
- **Built in [backend/](backend/README.md), documented in [docs/phase-1/](docs/phase-1/README.md).**
  Stack: React (Vite) + Python FastAPI (pandas/numpy/scikit-learn). Pipeline
  (`ingest → build_kpis → data_quality`) maps real NCRB data onto the Phase 0
  taxonomy/geo, validates against the JSON Schemas, and serves district-level
  aggregates via FastAPI. Runs on **real data** (see Phase 2).

### Phase 2: Dashboard and Geospatial MVP (Week 6-8) — DELIVERED

- Release interactive dashboard with district drilldowns.
- Add geospatial map with incident points, heatmaps, and time filters.
- Launch initial hotspot detection view.
- **Built on REAL, verified data for all 30 Karnataka districts:** NCRB district-wise
  IPC crimes 2001–2012 (ingested total reconciles exactly to NCRB's reported total),
  Census 2011 populations, and Census 2011 district boundaries. The
  [Leaflet map](frontend/src/CrimeMap.jsx) renders a risk choropleth, hotspot markers,
  and a data-driven crime heatmap; district drilldowns show KPIs, the 2001–2012 trend,
  category breakdown, and explainable risk. A
  [source adapter](backend/pipeline/sources/ncrb_ipc.py) normalizes the messy real
  NCRB source onto the canonical contract.

### Phase 3: Core Intelligence Features (Week 9-12) — DELIVERED

- Implement repeat offender tracking and profile linking.
- Deliver network and link analysis for criminal relationships.
- Add AI/ML pattern detection for recurring signatures and clusters.
- **Built in [backend/pipeline/intelligence.py](backend/pipeline/intelligence.py) +
  [frontend Intelligence panel](frontend/src/Intelligence.jsx).** Two data planes per
  the Phase 0 governance split: person-level features (repeat-offender tracking,
  co-offending network with degree centrality + connected components) run on
  **synthetic** offenders (no open person-level data exists), anchored to the real
  district crime volumes/mix and deterministic; pattern detection runs on the **real**
  NCRB data — K-means clustering of districts by crime signature and per-district
  year-over-year anomaly detection. Exposed via `/api/intelligence/*`.

### Phase 4: Predictive and Correlation Layer (Week 13-15) — IN PROGRESS

- Introduce predictive risk scoring by district/station/zone. *(baseline risk score delivered in Phase 2; calibrated model pending)*
- Add socio-economic correlation insights for explanatory analysis. **DELIVERED.**
- Enable trend alerts and anomaly notifications. *(anomaly detection delivered in Phase 3; alerting/notifications pending)*
- **Socio-economic correlation built on REAL Census 2011 district data** (literacy,
  workers, SC/ST, urbanization, income brackets, internet) + geodesic population
  density. A logically-backed schema
  ([socioeconomic_schema.json](docs/phase-0/contracts/socioeconomic_schema.json))
  defines each indicator's exact formula and a theory-grounded hypothesis about its
  relationship to specific crime groups. [socioeconomic.py](backend/pipeline/socioeconomic.py)
  correlates every indicator × every crime group (Pearson + Spearman, p-values,
  hypothesis verdicts) and the [frontend](frontend/src/Correlations.jsx) shows the
  matrix with ethical caveats (ecological fallacy, non-causality, protected attributes).

### Phase 5: Hardening and Rollout (Week 16-18) — IN PROGRESS

- Security, RBAC, audit logs, and observability hardening. **DELIVERED.**
- Validation with pilot users; refine model thresholds. *(pending real pilot)*
- Production rollout and governance checklist signoff. *(containerized; signoff pending)*
- **Built in [docs/phase-5/](docs/phase-5/README.md):** FastAPI serves the built
  frontend at one origin (no proxy); API-key RBAC (`viewer<analyst<admin`) gates the
  person-level intelligence endpoints; per-request audit logging + security headers +
  configurable CORS; multi-stage [Dockerfile](Dockerfile) + [compose](docker-compose.yml).
  Auth is dev-open until `CRIME_API_KEYS` is set, so the demo runs with no setup.

## 7. Detailed Capability Tracks

### A. Network and Link Analysis

- Build entity graph: offenders, incidents, associates, locations.
- Surface central actors, high-risk clusters, and relationship paths.
- Provide explainable graph evidence for analyst review.

### B. Repeat Offender Tracking

- Entity resolution to detect duplicate identities/aliases.
- Timeline view of repeat incidents and escalation risk.
- Flag probable repeat offenders for district watchlists.

### C. Socio-Economic Correlation

- Integrate socio-economic variables at district/zone granularity.
- Compute statistically meaningful crime-correlation indicators.
- Present correlations with confidence notes to avoid misuse.

### D. Predictive Risk Scoring

- Combine trend history, hotspot density, repeat-offender presence, and contextual signals.
- Produce transparent risk bands (Low/Medium/High/Critical).
- Refresh scores on schedule and after major incident updates.

### E. AI/ML Pattern Detection

- Unsupervised anomaly detection for sudden spikes.
- Temporal pattern mining (hour/day/seasonal signatures).
- Cluster detection for recurring location-type combinations.

## 8. KPI and Success Metrics

- Reduction in time-to-insight for district incident analysis.
- Precision/recall of hotspot and anomaly flags at pilot sites.
- Detection rate improvement for repeat offender identification.
- Adoption metrics: active users, dashboard sessions, map interactions.
- Alert usefulness score from analyst feedback.

## 9. Governance, Privacy, and Safety

- Role-based access and least-privilege data visibility.
- PII minimization/masking in analyst-facing views.
- Full audit logs for queries, exports, and alert actions.
- Model monitoring for drift, bias checks, and threshold re-tuning.
- Human-in-the-loop review for high-impact recommendations.

## 10. Risks and Mitigation

- Data fragmentation risk: enforce schema contracts and validation gates.
- False positives in alerts: threshold tuning with analyst feedback loops.
- Entity resolution errors: confidence scoring and manual merge review.
- Misinterpretation of correlations: add confidence and non-causality notes.
- Operational adoption risk: role-specific training and phased onboarding.

## 11. Deliverables Checklist

- Unified data model and ingestion pipelines.
- District-level dashboard with drilldowns.
- Geospatial hotspot map and filter controls.
- Network/link analysis module.
- Repeat offender tracking module.
- Predictive risk scoring and anomaly alerts.
- Governance controls, auditability, and rollout documentation.

## 12. Immediate Next Build Tasks

1. Finalize data dictionary for incidents, entities, and geo hierarchy.
2. Implement district aggregate endpoints used by dashboard cards/charts.
3. Integrate map layers and hotspot rendering in Crime Map page.
4. Design alert rules and anomaly scoring baseline.
5. Add first version of repeat offender and network graph APIs.

## 13. Free Public Dataset Sources (India)

Maps each capability to open, no-cost sources for a working demo/POC. NCRB/OGD
data is district/state-aggregated (not incident-level FIRs), so use it for trends,
hotspots, correlation, and risk baselines; use synthetic or pilot-shared records
for person-level link analysis and repeat-offender tracking.

### A. Core crime records (trends, hotspots, district drilldowns)

- [NCRB &#34;Crime in India&#34; official tables](https://ncrb.gov.in/crime-in-india-table-content.html) — yearly, state/district/city
- [OGD Platform India – district-wise IPC crimes](https://www.data.gov.in/catalog/district-wise-crimes-under-various-sections-indian-penal-code-ipc-crimes)
- [OGD Platform India – NCRB catalog (all years)](https://www.data.gov.in/catalogs/?ministry=National+Crime+Records+Bureau+%28NCRB%29)
- [OpenCity – Crime in India (cleaned CSV resources)](https://data.opencity.in/dataset/crime-in-india-2023)
- [Dataful – NCRB Crime in India 2016–2023 (CSV/XLSX/Parquet)](https://dataful.in/collections/1108/)
- [Kaggle – Crime in India (2001+ machine-readable)](https://www.kaggle.com/datasets/rajanand/crime-in-india)

### B. Socio-economic correlation

- [OGD Platform India – Socio-Economic Census](https://www.data.gov.in/catalog/socio-economic-census)
- [Socio Economic and Caste Census (SECC) 2011](https://secc.gov.in/) ([overview](https://en.wikipedia.org/wiki/2011_Socio_Economic_and_Caste_Census))
- [Census of India 2011](https://censusindia.gov.in/) — population, literacy, employment by district
- [RBI Handbook of Statistics on Indian States](https://www.rbi.org.in/) — income, fiscal, social indicators
- [World Bank Open Data](https://data.worldbank.org/) — cross-region indicators

### C. Geospatial boundaries & basemaps (maps, heatmaps, drilldowns)

- [DataMeet Indian maps](https://github.com/datameet/maps) — state/district/sub-district GeoJSON/SHP
- [GADM administrative boundaries](https://gadm.org/download_country.html) — India levels 0–3
- [Survey of India boundaries](https://surveyofindia.gov.in/)
- [OpenStreetMap / Geofabrik India extract](https://download.geofabrik.de/asia/india.html) — POIs, roads, basemap

### D. Person-level link analysis & repeat-offender (no open PII source — use these)

- Synthetic generation: [Faker](https://faker.readthedocs.io/) or [SDV](https://sdv.dev/)
- Pilot-shared anonymized FIR/case extracts (under data-sharing MOU, see §9 governance)
- [Stanford SNAP graph datasets](https://snap.stanford.edu/data/) — reference data for modeling/testing only

### Usage notes

- Aggregated NCRB/OGD data drives Tracks C, D, E and the dashboard/hotspot views.
- Incident-level coordinates are rarely public in India; geocode to district/station
  centroids for the demo and reserve point-level mapping for pilot data.
- Always record source, license, and vintage in the data dictionary (§12.1).
