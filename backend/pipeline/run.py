"""Phase 1+2 pipeline orchestrator: ingest -> build KPIs -> data quality.

Runs on REAL data in data/raw/ (see data/manifest.json):
  - karnataka_districts.geojson
  - ncrb_district_ipc_2001_2012.csv

Usage:  python -m pipeline.run
"""
from __future__ import annotations

import sys

from . import build_kpis, data_quality, ingest, intelligence, paths, socioeconomic


def main() -> int:
    paths.ensure_dirs()
    missing = [p.name for p in (paths.GEOJSON_RAW, paths.NCRB_RAW, paths.CENSUS_SE_RAW) if not p.exists()]
    if missing:
        print("ERROR: missing real source files in data/raw/:", ", ".join(missing))
        print("Download them per data/manifest.json (the geojson + NCRB IPC csv).")
        return 2

    print("=" * 64)
    print("Crime Analytics pipeline — Karnataka (REAL data)")
    print("=" * 64)

    ing = ingest.run()
    rec = ing["ncrb"]["reconciliation"]
    print(f"[1/5] ingest     : {ing['districts']} districts, {ing['incidents']} incidents, "
          f"{ing['total_cases']:,} cases, years {ing['years'][0]}-{ing['years'][-1]}")
    print(f"                   NCRB reconciliation: ingested {rec['ingested_leaf_sum']:,} vs "
          f"reported {rec['ncrb_reported_total']:,} -> {'MATCH' if rec['matches'] else 'MISMATCH'}")

    kpi = build_kpis.build()
    hr = kpi["highest_risk"]
    print(f"[2/5] build kpis : {kpi['kpi_facts']} facts, {kpi['hotspots']} hotspot(s); "
          f"highest risk = {hr['name']} ({hr['risk_band']} {hr['risk_score']})")

    rep = data_quality.run()
    s = rep["summary"]
    print(f"[3/5] data qual  : {rep['status']} — {s['errors']} error(s), {s['warnings']} warning(s)")

    intel = intelligence.run()
    net = intel["network"]
    print(f"[4/5] intelligence: {intel['entities']} synthetic offenders "
          f"({intel['repeat_offenders']} repeat), network {net['nodes']}n/{net['edges']}e "
          f"in {net['components']} components; {intel['clusters']} pattern clusters, "
          f"{intel['anomalies']} anomalies")

    se = socioeconomic.run()
    print(f"[5/5] socio-econ : {se['districts']} districts, {se['correlations']} correlations "
          f"({se['significant']} significant; {se['confirmed']} confirm / {se['contradicted']} contradict hypotheses)")
    for c in se["top"]:
        print(f"                   {c['indicator']} ~ {c['crime_group']}: r={c['pearson_r']} (p={c['pearson_p']}) {c['verdict']}")

    print("-" * 64)
    print(f"outputs -> {paths.PROCESSED_DIR}")
    print(f"api     -> {paths.API_DIR}")
    print(f"map     -> {paths.FRONTEND_PUBLIC / 'karnataka_districts.geojson'}")
    return 1 if rep["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
