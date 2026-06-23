"""Source adapter for the NCRB district-wise IPC crimes dataset (2001-2013).

Real data: National Crime Records Bureau, via the data.gov.in / OGD open dataset
"District-wise crimes committed under IPC". Two release files share this exact
33-column schema and are ingested together:
  - ncrb_district_ipc_2001_2012.csv  (2001-2012)
  - ncrb_district_ipc_2013.csv       (2013; header uses "STATE/UT" + spaced names
    instead of "STATE.UT" + dotted names — handled by header normalization)

This adapter:
  - filters to the pilot state (Karnataka),
  - maps NCRB district names onto Census-2011 district names (and aggregates
    commissionerate / city / rural splits into one census district),
  - maps the LEAF crime columns onto canonical taxonomy codes, deliberately
    EXCLUDING totals/subtotals so the ingested numbers reconcile EXACTLY to NCRB's
    own TOTAL.IPC.CRIMES.

NOTE on later years: NCRB's 2014/2015/2017 district tables use a much wider,
sub-split schema (and 2016 publishes no state column), so they are NOT reconcilable
against this contract without bespoke per-year adapters; district-wise IPC data is
not published in this machine-readable form for 2019+. 2013 is the latest year that
ingests cleanly and reconciles exactly. See roadmap.md §3.2.

Output: long rows {census_district, year, category_code, count} + a reconciliation
record the data-quality stage checks.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

STATE = "Karnataka"


def _norm(s) -> str:
    """Normalize a header/value: lowercase, collapse non-alphanumerics to single
    spaces. Makes "STATE.UT"/"STATE/UT" and "ATTEMPT.TO.MURDER"/"Attempt to Murder"
    compare equal across the differently-formatted yearly files."""
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


# NCRB district name (normalized) -> Census-2011 district name (matches the GeoJSON)
_CROSSWALK_RAW = {
    "bagalkot": "Bagalkote",
    "bangalore commr.": "Bengaluru Urban",
    "bangalore rural": "Bengaluru Rural",
    "belgaum": "Belagavi",
    "bellary": "Ballari",
    "bidar": "Bidar",
    "bijapur": "Vijayapura",
    "cbpura": "Chikkaballapura",
    "chamarajnagar": "Chamarajanagara",
    "chickmagalur": "Chikkamagaluru",
    "chitradurga": "Chitradurga",
    "dakshin kannada": "Dakshina Kannada",
    "davanagere": "Davanagere",
    "dharwad commr.": "Dharwad",
    "dharwad rural": "Dharwad",
    "gadag": "Gadag",
    "gulbarga": "Kalaburagi",
    "hassan": "Hassan",
    "haveri": "Haveri",
    "k.g.f.": "Kolar",
    "kodagu": "Kodagu",
    "kolar": "Kolar",
    "koppal": "Koppal",
    "mandya": "Mandya",
    "mangalore city": "Dakshina Kannada",
    "mysore commr.": "Mysuru",
    "mysore rural": "Mysuru",
    "raichur": "Raichur",
    "ramanagar": "Ramanagara",
    "shimoga": "Shivamogga",
    "tumkur": "Tumakuru",
    "udupi": "Udupi",
    "uttar kannada": "Uttara Kannada",
    "yadgiri": "Yadgir",
}
DISTRICT_CROSSWALK = {_norm(k): v for k, v in _CROSSWALK_RAW.items()}

# LEAF crime column (normalized name) -> canonical taxonomy code. These columns sum
# to TOTAL.IPC.CRIMES; totals and subtotals (custodial/other rape, kidnap sub-rows,
# auto/other theft) are intentionally omitted to avoid double counting.
COLUMN_MAP = {
    "murder": "MURDER",
    "attempt to murder": "ATTEMPT_MURDER",
    "culpable homicide not amounting to murder": "CULP_HOMICIDE",
    "rape": "RAPE",
    "kidnapping abduction": "KIDNAP_ABDUCT",
    "dacoity": "DACOITY",
    "preparation and assembly for dacoity": "DACOITY",
    "robbery": "ROBBERY",
    "burglary": "BURGLARY",
    "theft": "THEFT",
    "riots": "RIOTS",
    "criminal breach of trust": "CBT",
    "cheating": "CHEATING",
    "counterfieting": "FORGERY",
    "arson": "ARSON",
    "hurt grevious hurt": "GRIEVOUS_HURT",
    "dowry deaths": "DOWRY_DEATH",
    "assault on women with intent to outrage her modesty": "ASSAULT_WOMEN_MODESTY",
    "insult to modesty of women": "INSULT_MODESTY",
    "cruelty by husband or his relatives": "CRUELTY_HUSBAND",
    "importation of girls from foreign countries": "OTHER",
    "causing death by negligence": "OTHER",
    "other ipc crimes": "OTHER",
}


def _load_one(csv_path) -> tuple[list, int, int, set]:
    df = pd.read_csv(csv_path)
    # normalized header -> original column name (first occurrence wins)
    cols: dict[str, str] = {}
    for c in df.columns:
        cols.setdefault(_norm(c), c)

    state_col = next((cols[k] for k in cols if k in ("state ut", "states uts") or k.startswith("state ")), None)
    dist_col = cols.get("district")
    year_col = cols.get("year")
    total_col = next((cols[k] for k in cols if "total" in k and "ipc" in k and "crimes" in k), None)
    if dist_col is None or year_col is None:
        raise ValueError(f"{Path(csv_path).name}: missing DISTRICT/YEAR column")

    sub = df
    if state_col:
        sub = df[df[state_col].astype(str).str.upper().str.contains(STATE.upper(), na=False)]

    present = [(orig, COLUMN_MAP[n]) for n, orig in cols.items() if n in COLUMN_MAP]
    rows, unmapped = [], set()
    ingested = reported = 0

    for _, r in sub.iterrows():
        raw = _norm(r[dist_col])
        if not raw or "total" in raw or "railway" in raw:
            continue
        census = DISTRICT_CROSSWALK.get(raw)
        if census is None:
            unmapped.add(str(r[dist_col]).strip())
            continue
        year = int(r[year_col])
        for orig, code in present:
            count = r.get(orig)
            if pd.isna(count):
                continue
            rows.append({"district": census, "year": year, "category_code": code, "count": int(count)})
            ingested += int(count)
        if total_col is not None and not pd.isna(r.get(total_col)):
            reported += int(r[total_col])

    return rows, ingested, reported, unmapped


def load(csv_paths) -> dict:
    """Ingest one or more NCRB district-IPC CSVs sharing the 33-column schema.

    Returns {'rows': [...], 'reconciliation': {...}, 'unmapped_districts': [...]}.
    rows: list of {'district': <census name>, 'year': int, 'category_code': str, 'count': int}
    """
    if isinstance(csv_paths, (str, Path)):
        csv_paths = [csv_paths]

    all_rows = []
    ingested = reported = 0
    unmapped: set = set()
    for p in csv_paths:
        rows, ing, rep, unm = _load_one(p)
        all_rows.extend(rows)
        ingested += ing
        reported += rep
        unmapped |= unm

    reconciliation = {
        "ingested_leaf_sum": ingested,
        "ncrb_reported_total": reported,
        "difference": ingested - reported,
        "matches": ingested == reported,
    }
    return {"rows": all_rows, "reconciliation": reconciliation, "unmapped_districts": sorted(unmapped)}
