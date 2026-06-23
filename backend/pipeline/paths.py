"""Canonical filesystem locations for the data layer."""
from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
API_DIR = PROCESSED_DIR / "api"

# Frontend static assets (district boundaries for the Leaflet map)
FRONTEND_PUBLIC = REPO_ROOT / "frontend" / "public" / "data"

# Real source data (downloaded into raw/; see data/manifest.json)
GEOJSON_RAW = RAW_DIR / "karnataka_districts.geojson"
# NCRB district-wise IPC crimes — two releases sharing the same 33-column schema.
# 2013 is the latest year that ingests cleanly and reconciles exactly (see ncrb_ipc.py).
NCRB_RAW_FILES = [
    RAW_DIR / "ncrb_district_ipc_2001_2012.csv",
    RAW_DIR / "ncrb_district_ipc_2013.csv",
]
NCRB_RAW = NCRB_RAW_FILES[0]  # kept for backward compatibility
CENSUS_SE_RAW = RAW_DIR / "india_districts_census2011.csv"
POP_SEED = SEED_DIR / "ka_census2011_population.json"

# Boundary file the frontend map loads (raw geometry + canonical geo_unit_id)
BOUNDARIES = PROCESSED_DIR / "karnataka_districts.geojson"

# Canonical processed outputs
GEO_UNITS = PROCESSED_DIR / "geo_units.json"
INCIDENTS = PROCESSED_DIR / "incidents.json"
KPI_FACTS = PROCESSED_DIR / "kpi_facts.json"
ENTITIES = PROCESSED_DIR / "entities.json"            # Phase 3 synthetic offenders
OFFENDER_LINKS = PROCESSED_DIR / "offender_case_links.json"
SOCIOECONOMIC = PROCESSED_DIR / "socioeconomic.json"  # Phase 4 socio-economic facts
DQ_REPORT_JSON = PROCESSED_DIR / "data_quality_report.json"
DQ_REPORT_MD = PROCESSED_DIR / "data_quality_report.md"


def ensure_dirs() -> None:
    for d in (SEED_DIR, RAW_DIR, PROCESSED_DIR, API_DIR, FRONTEND_PUBLIC):
        d.mkdir(parents=True, exist_ok=True)
