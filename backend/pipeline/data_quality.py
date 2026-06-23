"""Data-quality gate for the canonical layer.

Runs after ingestion and fails the pipeline (non-zero exit) on hard errors, while
surfacing warnings analysts/engineers should see. Checks:
  - schema validation of geo_units & incidents
  - taxonomy mapping: heads that fell through to OTHER via FALLBACK (unmapped) are warned
  - geo referential integrity (incident.geo_unit_id + parent_id resolve)
  - non-negative case counts
  - district coverage and OTHER-share alarm
  - missing official codes (LGD/Census) -> warning to verify before production
"""
from __future__ import annotations

import json

from . import contracts, paths
from .sources import ncrb_ipc

OTHER_SHARE_ALARM = 0.45  # if OTHER > 45% of a district's cases, taxonomy needs work
EXPECTED_DISTRICTS = 30   # Karnataka Census-2011 districts


def _check_schemas(geo_units, incidents):
    errors = []
    sg = contracts.schema("geo_unit")
    si = contracts.schema("incident")
    bad_geo = bad_inc = 0
    for u in geo_units:
        e = contracts.validate(sg, u, u.get("geo_unit_id", "geo"))
        if e:
            bad_geo += 1
            errors.extend(e[:2])
    for i in incidents:
        e = contracts.validate(si, i, i.get("incident_id", "inc"))
        if e:
            bad_inc += 1
            errors.extend(e[:2])
    return {
        "geo_units_total": len(geo_units), "geo_units_invalid": bad_geo,
        "incidents_total": len(incidents), "incidents_invalid": bad_inc,
        "errors": errors[:20],
    }


def _check_mapping():
    """Validate the NCRB adapter's column map targets real taxonomy codes, and
    surface any column routed to OTHER (catch-all) for review."""
    mapped, to_other, invalid = [], [], []
    for col, code in ncrb_ipc.COLUMN_MAP.items():
        rec = {"raw_head": col, "code": code}
        if contracts.category_meta(code) is None:
            invalid.append(rec)
        elif code == "OTHER":
            to_other.append(rec)
        else:
            mapped.append(rec)
    return {"mapped": mapped, "routed_to_other": to_other, "invalid_target": invalid}


def _check_reconciliation():
    """Ingested leaf-column sum must equal NCRB's own reported IPC total."""
    rec = ncrb_ipc.load(paths.NCRB_RAW)["reconciliation"]
    return rec


def _check_referential(geo_units, incidents):
    ids = {u["geo_unit_id"] for u in geo_units}
    errors, warnings = [], []
    for i in incidents:
        if i["geo_unit_id"] not in ids:
            errors.append(f"incident {i['incident_id']}: geo_unit_id '{i['geo_unit_id']}' not found")
    for u in geo_units:
        p = u.get("parent_id")
        if p and p not in ids:
            warnings.append(f"geo {u['geo_unit_id']}: parent_id '{p}' not found")
    return errors, warnings


def _check_counts(incidents):
    errors = []
    for i in incidents:
        if i.get("case_count") is None or i["case_count"] < 0:
            errors.append(f"incident {i['incident_id']}: invalid case_count {i.get('case_count')}")
    return errors


def _check_coverage(geo_units, incidents):
    districts = {u["geo_unit_id"] for u in geo_units if u["level"] == "DISTRICT"}
    with_data = {i["geo_unit_id"] for i in incidents}
    missing = sorted(districts - with_data)
    # OTHER share per district
    by_dist = {}
    for i in incidents:
        d = by_dist.setdefault(i["geo_unit_id"], {"total": 0, "other": 0})
        d["total"] += i["case_count"]
        if i["category_code"] == "OTHER":
            d["other"] += i["case_count"]
    alarms = [
        {"geo_unit_id": g, "other_share": round(v["other"] / v["total"], 3)}
        for g, v in by_dist.items()
        if v["total"] and v["other"] / v["total"] > OTHER_SHARE_ALARM
    ]
    return {"districts_without_data": missing, "other_share_alarms": alarms}


def _check_codes(geo_units):
    """Warn only when a district has NO official identifier (no Census code). LGD
    codes are a nice-to-have crosswalk and are added when the LGD file is ingested."""
    warnings = []
    for u in geo_units:
        if u["level"] == "DISTRICT" and not u.get("codes", {}).get("census_district_code"):
            warnings.append(f"district {u['geo_unit_id']}: missing Census district code")
    return warnings


def run() -> dict:
    geo_units = json.loads(paths.GEO_UNITS.read_text(encoding="utf-8"))
    incidents = json.loads(paths.INCIDENTS.read_text(encoding="utf-8"))

    schemas = _check_schemas(geo_units, incidents)
    mapping = _check_mapping()
    recon = _check_reconciliation()
    ref_err, ref_warn = _check_referential(geo_units, incidents)
    count_err = _check_counts(incidents)
    coverage = _check_coverage(geo_units, incidents)
    code_warn = _check_codes(geo_units)
    n_districts = sum(1 for u in geo_units if u["level"] == "DISTRICT")

    errors = []
    errors += [f"schema: {schemas['geo_units_invalid']} geo + {schemas['incidents_invalid']} incidents invalid"] if (schemas["geo_units_invalid"] or schemas["incidents_invalid"]) else []
    errors += ref_err + count_err
    errors += [f"invalid mapping target '{m['raw_head']}' -> {m['code']}" for m in mapping["invalid_target"]]
    if not recon["matches"]:
        errors.append(f"NCRB reconciliation mismatch: ingested {recon['ingested_leaf_sum']:,} vs reported {recon['ncrb_reported_total']:,}")

    warnings = ref_warn + code_warn
    warnings += [f"district {a['geo_unit_id']} OTHER share {a['other_share']:.0%} exceeds alarm" for a in coverage["other_share_alarms"]]
    if coverage["districts_without_data"]:
        warnings.append(f"{len(coverage['districts_without_data'])} district(s) have no crime data")
    if n_districts != EXPECTED_DISTRICTS:
        warnings.append(f"district count {n_districts} != expected {EXPECTED_DISTRICTS}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "summary": {
            "errors": len(errors), "warnings": len(warnings),
            "geo_units": schemas["geo_units_total"], "districts": n_districts,
            "incidents": schemas["incidents_total"],
            "heads_mapped": len(mapping["mapped"]), "heads_to_other": len(mapping["routed_to_other"]),
            "ncrb_reconciles": recon["matches"],
        },
        "schema_validation": schemas,
        "taxonomy_mapping": mapping,
        "ncrb_reconciliation": recon,
        "referential_integrity": {"errors": ref_err, "warnings": ref_warn},
        "coverage": coverage,
        "errors": errors,
        "warnings": warnings,
    }
    paths.DQ_REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    paths.DQ_REPORT_MD.write_text(_to_md(report), encoding="utf-8")
    return report


def _to_md(r: dict) -> str:
    s = r["summary"]
    lines = [
        "# Data Quality Report",
        "",
        f"**Status:** {r['status']}  |  errors: {s['errors']}  |  warnings: {s['warnings']}",
        "",
        f"- geo_units: {s['geo_units']} ({s['districts']} districts)",
        f"- incidents: {s['incidents']}",
        f"- NCRB columns mapped to specific categories: {s['heads_mapped']}  |  routed to OTHER: {s['heads_to_other']}",
        f"- NCRB total reconciliation: {'MATCH' if s['ncrb_reconciles'] else 'MISMATCH'} "
        f"(ingested {r['ncrb_reconciliation']['ingested_leaf_sum']:,} vs reported {r['ncrb_reconciliation']['ncrb_reported_total']:,})",
        "",
        "## Errors",
    ]
    lines += [f"- {e}" for e in r["errors"]] or ["- none"]
    lines += ["", "## Warnings"]
    lines += [f"- {w}" for w in r["warnings"]] or ["- none"]
    lines += ["", "## NCRB columns routed to OTHER (review candidates for taxonomy expansion)"]
    for m in r["taxonomy_mapping"]["routed_to_other"]:
        lines.append(f"- `{m['raw_head']}`")
    if not r["taxonomy_mapping"]["routed_to_other"]:
        lines.append("- none")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    rep = run()
    print(json.dumps(rep["summary"], indent=2))
    print("status:", rep["status"])
