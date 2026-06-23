# Phase 0 — Data Contract (the source of truth)

The machine-readable contracts in [contracts/](contracts/) define *what the data is*.
All pipeline code reads these — nothing about crime types, geography, or KPIs is
hard-coded. Validate them with `node contracts/validate.mjs`.

| Contract | Defines |
|----------|---------|
| [crime_taxonomy.json](contracts/crime_taxonomy.json) | Canonical crime categories (IPC/BNS/SLL → one code) + `severity_weight` (1–5) |
| [geo_hierarchy.json](contracts/geo_hierarchy.json) | Geographic spine: Nation→State→Range→District→Station→Beat; pilot = Karnataka |
| [kpi_catalog.json](contracts/kpi_catalog.json) | Every KPI with exact formula, grain, unit, direction |
| [data_sources.json](contracts/data_sources.json) | Source register: license, access, PII level, refresh |
| [socioeconomic_schema.json](contracts/socioeconomic_schema.json) | Logically-backed socio-economic indicators: exact formula + theory-grounded crime-group hypotheses + ethical constraints |
| [schema_*.json](contracts/) | JSON Schemas for `geo_unit`, `incident`, `entity`, `socioeconomic` (validation gates) |

## Baseline methods (hotspot & risk)

- **Hotspot:** per district, z-score of the population-normalized severity-weighted
  index vs peer districts. `z > 1.5` = established; `z > 1.0` with a rising trend =
  emerging. (Getis-Ord Gi\* upgrade when point data exists.)
- **Risk (0–100, banded Low/Med/High/Critical):** additive, explainable weighted sum
  of crime intensity (0.30), trend momentum (0.20), hotspot membership (0.20),
  repeat-offender (0.15), socio-economic (0.15). Components unavailable on open data
  have their weight redistributed and the score is flagged `partial`. Every score
  stores its per-component contribution (governance: explainability).

Implemented in [backend/pipeline/build_kpis.py](../../backend/pipeline/build_kpis.py).

## Key design decisions

- **Dual-path incident:** the `incident` schema fits both aggregated NCRB rows
  (`case_count = N`) and per-FIR pilot rows (`case_count = 1`) — KPIs sum identically.
- **No open person-level data:** link analysis / repeat-offender run on synthetic or
  MOU pilot data only (`pii_level: high`); everything else uses open aggregated data.
