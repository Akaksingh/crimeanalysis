"""Ingestion: REAL Karnataka data -> canonical geo_units & incidents.

Sources (downloaded into data/raw/, see data/manifest.json):
  - karnataka_districts.geojson  : Census-2011 district boundaries + codes (30 districts)
  - ncrb_district_ipc_2001_2012.csv + ncrb_district_ipc_2013.csv : NCRB district-wise
    IPC crimes (real, 2001-2013; both share the 33-column schema, reconcile exactly)
  - ka_census2011_population.json : real Census-2011 district populations

Every raw crime head is mapped onto a canonical taxonomy code (via the NCRB source
adapter) and every record tied to a canonical geo_unit_id. Open NCRB data is
aggregated, so each emitted incident carries case_count (the dual-path design).
Also writes a boundary GeoJSON (geometry + geo_unit_id) for the frontend map.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import contracts, geoarea, paths
from .sources import ncrb_ipc

SOURCE_ID = "ogd_district_ipc"


def _slug(name: str) -> str:
    return "DISTRICT:KA-" + name.upper().replace(".", "").replace(" ", "-")


def _centroid(geometry: dict) -> dict | None:
    """Approximate centroid = mean of all coordinate pairs (good enough for markers)."""
    pts = []

    def walk(coords):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            pts.append(coords)
        else:
            for c in coords:
                walk(c)

    walk(geometry.get("coordinates"))
    if not pts:
        return None
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return {"lat": round(lat, 5), "lon": round(lon, 5)}


def build_geo_and_boundaries():
    """Returns (geo_units, name_to_id, boundary_geojson)."""
    gj = json.loads(paths.GEOJSON_RAW.read_text(encoding="utf-8"))
    pop = json.loads(paths.POP_SEED.read_text(encoding="utf-8"))
    pops = pop["districts"]
    fshare = pop["female_share"]

    geo_units = [
        {"geo_unit_id": "NATION:IN", "level": "NATION", "name": "India", "parent_id": None,
         "codes": {"lgd_state_code": None, "lgd_district_code": None, "census_state_code": None, "census_district_code": None},
         "centroid": {"lat": 22.5937, "lon": 78.9629}, "boundary_ref": None,
         "area_km2": None, "population": None, "female_population": None, "population_year": None},
        {"geo_unit_id": "STATE:KA", "level": "STATE", "name": "Karnataka", "parent_id": "NATION:IN",
         "codes": {"lgd_state_code": 29, "lgd_district_code": None, "census_state_code": 29, "census_district_code": None},
         "centroid": {"lat": 15.3173, "lon": 75.7139}, "boundary_ref": None,
         "area_km2": None, "population": 61095297, "female_population": round(61095297 * fshare),
         "population_year": 2011},
    ]

    name_to_id = {}
    out_features = []
    for f in gj["features"]:
        props = f["properties"]
        name = props["district"]
        gid = _slug(name)
        name_to_id[name] = gid
        population = pops.get(name)
        geo_units.append({
            "geo_unit_id": gid,
            "level": "DISTRICT",
            "name": name,
            "parent_id": "STATE:KA",
            "codes": {
                "lgd_state_code": 29,
                "lgd_district_code": None,
                "census_state_code": 29,
                "census_district_code": int(props["dt_code"]) if props.get("dt_code") else None,
            },
            "centroid": _centroid(f["geometry"]),
            "boundary_ref": f"census2011:dt:{props.get('dt_code')}",
            "area_km2": geoarea.area_km2(f["geometry"]),
            "population": population,
            "female_population": round(population * fshare) if population else None,
            "population_year": 2011,
        })
        out_features.append({
            "type": "Feature",
            "properties": {"geo_unit_id": gid, "name": name, "dt_code": props.get("dt_code")},
            "geometry": f["geometry"],
        })

    boundary_geojson = {"type": "FeatureCollection", "features": out_features}
    return geo_units, name_to_id, boundary_geojson


def build_incidents(name_to_id: dict):
    src = ncrb_ipc.load(paths.NCRB_RAW_FILES)
    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    agg: dict[tuple, dict] = {}
    unmatched = set()

    for row in src["rows"]:
        gid = name_to_id.get(row["district"])
        if gid is None:
            unmatched.add(row["district"])
            continue
        year, code = row["year"], row["category_code"]
        key = (gid, year, code)
        if key not in agg:
            cat = contracts.category_meta(code)
            agg[key] = {
                "incident_id": f"AGG-{year}-{gid}-{code}",
                "fir_no": None,
                "category_code": code,
                "act": "IPC",
                "section": None,
                "is_cognizable": bool(cat["is_cognizable"]) if cat and cat.get("is_cognizable") is not None else None,
                "occurrence_datetime": None,
                "registration_date": f"{year}-12-31",
                "geo_unit_id": gid,
                "lat": None,
                "lon": None,
                "geo_precision": "district_centroid",
                "victim_count": None,
                "value_stolen": None,
                "value_recovered": None,
                "investigation_status": None,
                "trial_status": None,
                "case_count": 0,
                "source_id": SOURCE_ID,
                "ingested_at": ingested_at,
            }
        agg[key]["case_count"] += row["count"]

    # Drop zero-count aggregates: an aggregated incident with 0 cases is meaningless
    # (and the canonical schema requires case_count >= 1). Counts still reconcile.
    incidents = [a for a in agg.values() if a["case_count"] > 0]
    return incidents, {"reconciliation": src["reconciliation"], "unmatched_districts": sorted(unmatched),
                       "adapter_unmapped": src["unmapped_districts"]}


def run() -> dict:
    paths.ensure_dirs()
    geo_units, name_to_id, boundaries = build_geo_and_boundaries()
    incidents, ncrb_meta = build_incidents(name_to_id)

    # attach district centroids to incidents for map/heatmap
    cmap = {u["geo_unit_id"]: u["centroid"] for u in geo_units}
    for i in incidents:
        c = cmap.get(i["geo_unit_id"])
        if c:
            i["lat"], i["lon"] = c["lat"], c["lon"]

    paths.GEO_UNITS.write_text(json.dumps(geo_units, indent=2), encoding="utf-8")
    paths.INCIDENTS.write_text(json.dumps(incidents, indent=2), encoding="utf-8")
    # boundary geojson -> processed + frontend public (for the Leaflet map)
    bj = json.dumps(boundaries)
    paths.BOUNDARIES.write_text(bj, encoding="utf-8")
    (paths.FRONTEND_PUBLIC / "karnataka_districts.geojson").write_text(bj, encoding="utf-8")

    return {
        "geo_units": len(geo_units),
        "districts": sum(1 for u in geo_units if u["level"] == "DISTRICT"),
        "incidents": len(incidents),
        "total_cases": sum(i["case_count"] for i in incidents),
        "years": sorted({int(i["registration_date"][:4]) for i in incidents}),
        "ncrb": ncrb_meta,
    }


if __name__ == "__main__":
    s = run()
    print(json.dumps({k: v for k, v in s.items() if k != "ncrb"}, indent=2, default=str))
    print("reconciliation:", s["ncrb"]["reconciliation"])
