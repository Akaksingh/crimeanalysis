"""Phase 7 — FIR-record intelligence, modelled on the KSP "Police FIR System" schema.

The hackathon target data model is the record-level Police FIR System (CaseMaster +
Accused / Victim / Complainant / ArrestSurrender / Chargesheet + Act/Section/CrimeHead
masters). No real record-level dump is shipped (it is confidential PII), so this module
generates a **schema-shaped synthetic FIR dataset** that is:

  * structurally faithful to the provided ER diagram (same tables, keys, lookups),
  * anchored to the REAL latest-year district crime volumes & category mix (from the
    NCRB ingest), so totals/heatmaps stay realistic,
  * fully deterministic (seeded) and clearly labelled synthetic.

From those records it derives the record-level analytics the brief asks for and the
open NCRB aggregates cannot provide:
  - police-station drill-down,
  - spatiotemporal hotspots (GPS point + time-of-day),
  - a REAL co-accused network + repeat-offender / Modus-Operandi profiles,
  - case-lifecycle / detection (chargesheet A/B/C) analytics,
  - case-level demographics (caste / religion / occupation / gender / age).
"""
from __future__ import annotations

import json
import math
import random

from . import contracts, paths

SEED = 42

# scale real district volumes down to a demo-sized, network-rich sample
CASE_DIVISOR = 500
CASES_MIN, CASES_MAX = 20, 320
POINTS_CAP = 1500           # cap GPS points in the spatiotemporal payload
SAMPLE_CASE_ROWS = 200      # raw FIR rows surfaced for the case table

# ---- lookup masters (mirror the schema's *Master / lookup tables) ----
CASE_CATEGORIES = [("FIR", "1", 0.70), ("UDR", "3", 0.12), ("PAR", "4", 0.12), ("Zero FIR", "8", 0.06)]
CASE_STATUSES = ["Under Investigation", "Charge Sheeted", "Pending Trial", "Disposed", "Closed"]
CS_TYPES = [("A", "Chargesheet"), ("B", "False Case"), ("C", "Undetected")]
GENDERS = [("M", 0.74), ("F", 0.24), ("T", 0.02)]
AGE_BANDS = [("18-25", 0.30), ("26-35", 0.34), ("36-45", 0.21), ("46-60", 0.12), ("60+", 0.03)]
RELIGIONS = [("Hindu", 0.84), ("Muslim", 0.11), ("Christian", 0.03), ("Jain", 0.01), ("Other", 0.01)]
CASTES = [("General", 0.30), ("OBC", 0.40), ("SC", 0.18), ("ST", 0.07), ("Other", 0.05)]
OCCUPATIONS = ["Farmer", "Daily Wage Labourer", "Business", "Government Employee",
               "Private Employee", "Student", "Unemployed", "Driver", "Homemaker"]
STATION_SUFFIX = ["Town PS", "Rural PS", "Market PS", "City PS", "East PS", "West PS",
                  "Women PS", "Cyber PS", "Traffic PS"]
FIRST_NAMES = ["Ravi", "Suresh", "Manju", "Anil", "Kiran", "Prakash", "Lokesh", "Ramesh",
               "Vinod", "Shankar", "Naveen", "Mahesh", "Girish", "Basava", "Imran", "Arjun",
               "Deepa", "Latha", "Kavya", "Roopa", "Yusuf", "Santosh", "Mallesh", "Nagaraj"]
LAST_INITIALS = ["K", "M", "S", "R", "N", "B", "G", "P", "H", "V", "D", "T"]

# hour-of-day weighting (offences skew to evening / late night)
HOUR_WEIGHTS = [3, 2, 2, 1, 1, 1, 2, 3, 4, 5, 6, 6, 5, 5, 5, 6, 7, 8, 9, 9, 8, 7, 5, 4]
GROUP_NAME = {g["code"]: g["name"] for g in contracts.taxonomy()["groups"]}


def _pick(rng, weighted):
    vals = [v for v, _ in weighted]
    wts = [w for _, w in weighted]
    return rng.choices(vals, weights=wts, k=1)[0]


def _pretty(code: str) -> str:
    return code.replace("_", " ").title()


def _legal_for(code: str):
    """(major head, sub head, act, section) for a canonical category code."""
    cat = contracts.category_meta(code) or {}
    group = cat.get("group")
    major = GROUP_NAME.get(group, "Other")
    sub = _pretty(code)
    ipc = (cat.get("ipc_sections") or [None])[0]
    bns = (cat.get("bns_sections") or [None])[0]
    act, section = ("IPC", ipc) if ipc else (("BNS", bns) if bns else ("SLL", None))
    return major, sub, act, section


# --------------------------------------------------------------------------- #
# Synthetic FIR generation (schema-shaped)
# --------------------------------------------------------------------------- #
def _generate(geo_units, incidents, rng):
    districts = [u for u in geo_units if u["level"] == "DISTRICT"]
    names = {u["geo_unit_id"]: u["name"] for u in geo_units}

    # latest-year district volumes + category mix from the real ingest
    latest = max(int(i["registration_date"][:4]) for i in incidents)
    vol: dict[str, dict] = {}
    for i in incidents:
        if int(i["registration_date"][:4]) != latest:
            continue
        d = vol.setdefault(i["geo_unit_id"], {})
        d[i["category_code"]] = d.get(i["category_code"], 0) + i["case_count"]

    cases, accused_rows, victim_rows, complainant_rows = [], [], [], []
    arrests, chargesheets, stations = [], [], []
    accused_index: dict[str, dict] = {}   # persistent accused identity -> profile
    adj: dict[str, dict[str, int]] = {}   # co-accused adjacency
    person_cases: dict[str, list] = {}    # accused -> [case_id,...]
    case_people: dict[str, list] = {}     # case_id -> [accused,...]

    serial = 0
    for d in districts:
        gid = d["geo_unit_id"]
        mix = vol.get(gid)
        if not mix:
            continue
        cen = d.get("centroid") or {"lat": 15.3, "lon": 75.7}
        total = sum(mix.values())
        n_cases = max(CASES_MIN, min(CASES_MAX, round(total / CASE_DIVISOR)))
        cat_codes = list(mix.keys())
        cat_wts = list(mix.values())

        # police stations for this district
        n_stn = max(3, min(len(STATION_SUFFIX), 3 + n_cases // 60))
        d_stations = []
        for s in range(n_stn):
            uid = f"UNIT-{gid.split(':')[-1]}-{s + 1:02d}"
            sname = f"{d['name']} {STATION_SUFFIX[s]}"
            d_stations.append(uid)
            stations.append({"unit_id": uid, "name": sname, "district": d["name"],
                             "geo_unit_id": gid, "lat": cen["lat"], "lon": cen["lon"]})

        # persistent accused pool (smaller than cases -> natural repeat offenders)
        pool_size = max(5, round(n_cases * 0.7))
        pool = []
        for _ in range(pool_size):
            serial_a = len(accused_index) + 1
            pid = f"ACC-{serial_a:05d}"
            pool.append(pid)
            accused_index[pid] = {
                "person_id": pid,
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}.",
                "gender": _pick(rng, GENDERS),
                "age_band": _pick(rng, AGE_BANDS),
                "home_geo_unit_id": gid,
                "district": d["name"],
            }
        # weight pool so a few become prolific repeat offenders (power-law-ish)
        pool_wts = [1.0 / (r + 1) ** 0.6 for r in range(pool_size)]

        for _ in range(n_cases):
            serial += 1
            cat = rng.choices(cat_codes, weights=cat_wts, k=1)[0]
            major, sub, act, section = _legal_for(cat)
            sev = contracts.severity_weight(cat)
            gravity = "Heinous" if sev >= 4 else "Non-Heinous"
            cat_label, cat_code = (lambda c: (c[0], c[1]))(_pick(rng, [(c[:2], c[2]) for c in CASE_CATEGORIES]))
            unit = rng.choice(d_stations)
            hour = rng.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
            month, day = rng.randint(1, 12), rng.randint(1, 28)
            dist_code = f"{(d['codes'].get('census_district_code') or 0):04d}"
            crime_no = f"{cat_code}{dist_code}{(hash(unit) % 10000):04d}{latest}{serial % 100000:05d}"

            lat = round(cen["lat"] + rng.gauss(0, 0.16), 5)
            lon = round(cen["lon"] + rng.gauss(0, 0.16), 5)

            status = rng.choices(CASE_STATUSES, weights=[34, 30, 14, 14, 8], k=1)[0]
            cs_type = None
            if status in ("Charge Sheeted", "Disposed"):
                cs_type = rng.choices(["A", "B", "C"], weights=[80, 10, 10], k=1)[0]
            elif status == "Closed":
                cs_type = rng.choices(["A", "B", "C"], weights=[20, 45, 35], k=1)[0]

            case_id = f"CASE-{serial:06d}"
            cases.append({
                "case_id": case_id, "crime_no": crime_no, "category": cat_label,
                "crime_major_head": major, "crime_minor_head": sub, "act": act,
                "section": section, "gravity": gravity, "status": status,
                "cs_type": cs_type, "district": d["name"], "geo_unit_id": gid,
                "unit_id": unit, "year": latest, "month": month, "day": day,
                "hour": hour, "lat": lat, "lon": lon, "category_code": cat,
            })
            if cs_type:
                chargesheets.append({"case_id": case_id, "cs_type": cs_type,
                                     "cs_date": f"{latest}-{month:02d}-{min(28, day + 2):02d}"})

            # complainant
            complainant_rows.append({
                "case_id": case_id, "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}.",
                "age": rng.randint(18, 70), "gender": _pick(rng, GENDERS),
                "religion": _pick(rng, RELIGIONS), "caste": _pick(rng, CASTES),
                "occupation": rng.choice(OCCUPATIONS),
            })
            # victims (0-2; women/violent crimes more likely to have a named victim)
            n_vic = rng.choices([0, 1, 2], weights=[0.35, 0.5, 0.15], k=1)[0]
            for _ in range(n_vic):
                victim_rows.append({
                    "case_id": case_id, "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}.",
                    "age": rng.randint(5, 80), "gender": _pick(rng, GENDERS),
                    "victim_police": 0,
                })
            # accused (1-3, drawn from the persistent district pool -> repeats + crews)
            k = rng.choices([1, 2, 3], weights=[0.62, 0.27, 0.11], k=1)[0]
            crew = []
            for _ in range(k):
                pid = rng.choices(pool, weights=pool_wts, k=1)[0]
                if pid not in crew:
                    crew.append(pid)
            case_people[case_id] = crew
            for n_i, pid in enumerate(crew):
                prof = accused_index[pid]
                accused_rows.append({
                    "case_id": case_id, "person_id": pid, "sort": f"A{n_i + 1}",
                    "name": prof["name"], "age_band": prof["age_band"], "gender": prof["gender"],
                })
                person_cases.setdefault(pid, []).append(case_id)
                if status in ("Charge Sheeted", "Disposed"):
                    arrests.append({"case_id": case_id, "person_id": pid, "unit_id": unit,
                                    "type": "Arrest", "date": f"{latest}-{month:02d}-{day:02d}"})
            # co-accused edges
            for a_i in range(len(crew)):
                for b_i in range(a_i + 1, len(crew)):
                    a, b = crew[a_i], crew[b_i]
                    adj.setdefault(a, {}).setdefault(b, 0)
                    adj.setdefault(b, {}).setdefault(a, 0)
                    adj[a][b] += 1
                    adj[b][a] += 1

    tables = {
        "cases": cases, "accused": accused_rows, "victims": victim_rows,
        "complainants": complainant_rows, "arrests": arrests, "chargesheets": chargesheets,
        "stations": stations,
    }
    ctx = {"accused_index": accused_index, "adj": adj, "person_cases": person_cases,
           "case_people": case_people, "names": names, "latest": latest}
    return tables, ctx


# --------------------------------------------------------------------------- #
# Network metrics (degree centrality + connected components via union-find)
# --------------------------------------------------------------------------- #
def _network(adj):
    nodes = list(adj.keys())
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = 0
    for a, nbrs in adj.items():
        for b in nbrs:
            if a < b:
                edges += 1
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb

    comps: dict[str, int] = {}
    for n in nodes:
        comps[find(n)] = comps.get(find(n), 0) + 1
    degree = {n: len(adj[n]) for n in nodes}
    roots = sorted(comps, key=lambda r: comps[r], reverse=True)
    comp_id = {r: i for i, r in enumerate(roots)}
    node_comp = {n: comp_id[find(n)] for n in nodes}
    summary = {"nodes": len(nodes), "edges": edges, "components": len(comps),
               "largest_component": max(comps.values()) if comps else 0}
    return summary, degree, node_comp


def _hist(values, n):
    h = [0] * n
    for v in values:
        if 0 <= v < n:
            h[v] += 1
    return h


# --------------------------------------------------------------------------- #
def run() -> dict:
    paths.ensure_dirs()
    geo_units = json.loads(paths.GEO_UNITS.read_text(encoding="utf-8"))
    incidents = json.loads(paths.INCIDENTS.read_text(encoding="utf-8"))
    rng = random.Random(SEED)

    tables, ctx = _generate(geo_units, incidents, rng)
    cases = tables["cases"]
    accused_index = ctx["accused_index"]
    adj, person_cases, case_people = ctx["adj"], ctx["person_cases"], ctx["case_people"]
    latest = ctx["latest"]
    note = ("SYNTHETIC FIR records, schema-shaped to the KSP Police FIR System ER model "
            "(confidential record-level data is not public). Anchored to real latest-year "
            f"district crime volumes & category mix ({latest}); deterministic (seed {SEED}).")

    def counts(key):
        out: dict[str, int] = {}
        for c in cases:
            out[c[key]] = out.get(c[key], 0) + 1
        return out

    # ---- 1. overview / lifecycle / demographics ----
    by_status = counts("status")
    cs_a = sum(1 for c in cases if c["cs_type"] == "A")
    cs_b = sum(1 for c in cases if c["cs_type"] == "B")
    cs_c = sum(1 for c in cases if c["cs_type"] == "C")
    resolved = cs_a + cs_b + cs_c
    head_counts = counts("crime_major_head")
    overview = {
        "data_note": note, "total_cases": len(cases), "latest_year": latest,
        "by_category": [{"label": k, "count": v} for k, v in sorted(counts("category").items(), key=lambda x: -x[1])],
        "by_gravity": [{"label": k, "count": v} for k, v in sorted(counts("gravity").items(), key=lambda x: -x[1])],
        "by_status": [{"label": k, "count": v} for k, v in sorted(by_status.items(), key=lambda x: -x[1])],
        "by_major_head": [{"label": k, "count": v} for k, v in sorted(head_counts.items(), key=lambda x: -x[1])],
        "detection": {
            "chargesheeted": cs_a, "false": cs_b, "undetected": cs_c,
            "detection_rate": round(cs_a / resolved, 3) if resolved else 0,
        },
        "demographics": {
            "accused_gender": _dist(tables["accused"], "gender"),
            "accused_age": _dist(tables["accused"], "age_band"),
            "victim_gender": _dist(tables["victims"], "gender"),
            "complainant_religion": _dist(tables["complainants"], "religion"),
            "complainant_caste": _dist(tables["complainants"], "caste"),
            "complainant_occupation": _dist(tables["complainants"], "occupation"),
        },
    }

    # ---- 2. police-station drill-down ----
    stn_by_id = {s["unit_id"]: s for s in tables["stations"]}
    stn_agg: dict[str, dict] = {}
    for c in cases:
        a = stn_agg.setdefault(c["unit_id"], {"cases": 0, "heinous": 0, "detected": 0, "cats": {}})
        a["cases"] += 1
        a["heinous"] += 1 if c["gravity"] == "Heinous" else 0
        a["detected"] += 1 if c["cs_type"] == "A" else 0
        a["cats"][c["crime_major_head"]] = a["cats"].get(c["crime_major_head"], 0) + 1
    station_rows = []
    for uid, a in stn_agg.items():
        s = stn_by_id[uid]
        top_cat = max(a["cats"], key=a["cats"].get) if a["cats"] else "—"
        station_rows.append({
            "unit_id": uid, "name": s["name"], "district": s["district"],
            "cases": a["cases"], "heinous": a["heinous"],
            "heinous_share": round(a["heinous"] / a["cases"], 3),
            "detection_rate": round(a["detected"] / a["cases"], 3),
            "top_category": top_cat,
        })
    station_rows.sort(key=lambda r: -r["cases"])
    stations_payload = {"data_note": note, "total_stations": len(station_rows), "stations": station_rows}

    # ---- 3. spatiotemporal hotspots ----
    points = [{"lat": c["lat"], "lon": c["lon"], "hour": c["hour"], "gravity": c["gravity"],
               "category": c["crime_major_head"], "district": c["district"]} for c in cases]
    if len(points) > POINTS_CAP:
        step = math.ceil(len(points) / POINTS_CAP)
        points = points[::step]
    # grid-bin hotspots (0.1deg cells) with peak hour
    grid: dict[tuple, dict] = {}
    for c in cases:
        key = (round(c["lat"] * 10) / 10, round(c["lon"] * 10) / 10)
        g = grid.setdefault(key, {"count": 0, "hours": [0] * 24, "district": c["district"], "heinous": 0})
        g["count"] += 1
        g["hours"][c["hour"]] += 1
        g["heinous"] += 1 if c["gravity"] == "Heinous" else 0
    hotspots = sorted((
        {"lat": k[0], "lon": k[1], "count": g["count"], "district": g["district"],
         "heinous": g["heinous"], "peak_hour": g["hours"].index(max(g["hours"]))}
        for k, g in grid.items()), key=lambda h: -h["count"])[:20]
    spatiotemporal = {
        "data_note": note,
        "hour_histogram": _hist([c["hour"] for c in cases], 24),
        "gravity_by_hour": {
            "Heinous": _hist([c["hour"] for c in cases if c["gravity"] == "Heinous"], 24),
            "Non-Heinous": _hist([c["hour"] for c in cases if c["gravity"] != "Heinous"], 24),
        },
        "points": points, "hotspots": hotspots,
    }

    # ---- 4. real co-accused network ----
    summary, degree, node_comp = _network(adj)
    net_nodes = [{
        "id": pid, "name": accused_index[pid]["name"], "district": accused_index[pid]["district"],
        "incidents": len(person_cases.get(pid, [])), "degree": degree.get(pid, 0),
        "component": node_comp.get(pid, 0),
    } for pid in adj]
    net_links = [{"source": a, "target": b, "weight": w}
                 for a, nbrs in adj.items() for b, w in nbrs.items() if a < b]
    # bipartite person<->case graph (repeat-offender view)
    case_meta = {c["case_id"]: c for c in cases}
    persons_in_graph = set(adj)
    cg_person = [{"id": pid, "kind": "person", "name": accused_index[pid]["name"],
                  "district": accused_index[pid]["district"], "incidents": len(person_cases.get(pid, [])),
                  "degree": degree.get(pid, 0), "component": node_comp.get(pid, 0)}
                 for pid in persons_in_graph]
    cg_cases, cg_links = [], []
    for cid, crew in case_people.items():
        crew_in = [p for p in crew if p in persons_in_graph]
        if len(crew_in) < 1:
            continue
        cm = case_meta[cid]
        cg_cases.append({"id": cid, "kind": "case", "district": cm["district"], "year": cm["year"],
                         "category": cm["crime_major_head"], "size": len(crew)})
        for pid in crew_in:
            cg_links.append({"source": pid, "target": cid})
    central = sorted(degree.items(), key=lambda kv: -kv[1])[:12]
    network_payload = {
        "data_note": note, "summary": summary,
        "top_central_offenders": [{"entity_id": pid, "name": accused_index[pid]["name"],
                                   "district": accused_index[pid]["district"], "co_offenders": deg}
                                  for pid, deg in central if deg > 0],
        "graph": {"nodes": net_nodes, "links": net_links},
        "case_graph": {"nodes": cg_person + cg_cases, "links": cg_links},
    }

    # ---- 5. repeat offenders + Modus Operandi ----
    repeat = []
    for pid, clist in person_cases.items():
        if len(clist) < 2:
            continue
        prof = accused_index[pid]
        heads, sections, units, hours, gravities = {}, {}, set(), [], {}
        for cid in clist:
            cm = case_meta[cid]
            heads[cm["crime_minor_head"]] = heads.get(cm["crime_minor_head"], 0) + 1
            if cm["section"]:
                sections[f"{cm['act']} {cm['section']}"] = sections.get(f"{cm['act']} {cm['section']}", 0) + 1
            units.add(cm["unit_id"])
            hours.append(cm["hour"])
            gravities[cm["gravity"]] = gravities.get(cm["gravity"], 0) + 1
        mo_head = max(heads, key=heads.get)
        peak = max(set(hours), key=hours.count)
        repeat.append({
            "person_id": pid, "name": prof["name"], "district": prof["district"],
            "gender": prof["gender"], "age_band": prof["age_band"], "cases": len(clist),
            "co_offenders": degree.get(pid, 0), "jurisdictions": len(units),
            "mo": mo_head, "top_sections": sorted(sections, key=sections.get, reverse=True)[:3],
            "peak_hour": peak, "heinous_cases": gravities.get("Heinous", 0),
        })
    repeat.sort(key=lambda r: (-r["cases"], -r["co_offenders"]))
    total_accused = len(accused_index)
    offenders_payload = {
        "data_note": note, "total_accused": total_accused, "repeat_offenders": len(repeat),
        "repeat_ratio": round(len(repeat) / total_accused, 3) if total_accused else 0,
        "top": repeat[:30],
    }

    # ---- 6. sample raw FIR rows (case table) ----
    cases_payload = {
        "data_note": note,
        "columns": ["crime_no", "category", "crime_major_head", "crime_minor_head",
                    "act", "section", "gravity", "status", "district", "unit_id", "hour"],
        "rows": [{k: c[k] for k in ("crime_no", "category", "crime_major_head", "crime_minor_head",
                                    "act", "section", "gravity", "status", "district", "unit_id", "hour")}
                 for c in cases[:SAMPLE_CASE_ROWS]],
    }

    # ---- write API payloads ----
    api = paths.API_DIR
    out = {
        "fir_overview.json": overview, "fir_stations.json": stations_payload,
        "fir_spatiotemporal.json": spatiotemporal, "fir_network.json": network_payload,
        "fir_offenders.json": offenders_payload, "fir_cases.json": cases_payload,
        "fir_schema.json": _schema_payload(),
    }
    for fname, payload in out.items():
        (api / fname).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "cases": len(cases), "stations": len(station_rows), "accused": total_accused,
        "repeat": len(repeat), "network_nodes": summary["nodes"], "network_edges": summary["edges"],
        "components": summary["components"], "detection_rate": overview["detection"]["detection_rate"],
    }


def _dist(rows, key):
    out: dict[str, int] = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return [{"label": k, "count": v} for k, v in sorted(out.items(), key=lambda x: -x[1])]


def _schema_payload():
    """Compact description of the KSP Police FIR System ER model (for the Data-Model view)."""
    return {
        "title": "KSP Police FIR System — Data Model",
        "note": "Record-level ER model the platform is designed around (source: KSP confidential DB schema).",
        "tables": [
            {"name": "CaseMaster", "role": "Core FIR / case record",
             "columns": ["CaseMasterID (PK)", "CrimeNo", "CaseNo", "CrimeRegisteredDate",
                         "IncidentFromDate", "IncidentToDate", "latitude", "longitude", "BriefFacts",
                         "PolicePersonID (FK)", "PoliceStationID (FK)", "CaseCategoryID (FK)",
                         "GravityOffenceID (FK)", "CrimeMajorHeadID (FK)", "CrimeMinorHeadID (FK)",
                         "CaseStatusID (FK)", "CourtID (FK)"]},
            {"name": "Accused", "role": "Persons accused in a case (A1, A2, …)",
             "columns": ["AccusedMasterID (PK)", "CaseMasterID (FK)", "AccusedName", "AgeYear",
                         "GenderID", "PersonID"]},
            {"name": "Victim", "role": "Victims linked to a case",
             "columns": ["VictimMasterID (PK)", "CaseMasterID (FK)", "VictimName", "AgeYear",
                         "GenderID", "VictimPolice"]},
            {"name": "ComplainantDetails", "role": "Complainant + demographics",
             "columns": ["ComplainantID (PK)", "CaseMasterID (FK)", "ComplainantName", "AgeYear",
                         "OccupationID (FK)", "ReligionID (FK)", "CasteID (FK)", "GenderID"]},
            {"name": "ArrestSurrender", "role": "Arrest / surrender events",
             "columns": ["ArrestSurrenderID (PK)", "CaseMasterID (FK)", "AccusedMasterID (FK)",
                         "ArrestSurrenderDate", "IOID (FK)", "CourtID (FK)", "PoliceStationID (FK)"]},
            {"name": "ChargesheetDetails", "role": "Final report (A=chargesheet / B=false / C=undetected)",
             "columns": ["CSID (PK)", "CaseMasterID (FK)", "csdate", "cstype", "PolicePersonID (FK)"]},
            {"name": "Act / Section / ActSectionAssociation", "role": "Legal acts & sections per case",
             "columns": ["ActCode (PK)", "SectionCode", "ActSectionAssociation.CaseMasterID (FK)"]},
            {"name": "CrimeHead / CrimeSubHead", "role": "Major & minor crime classification",
             "columns": ["CrimeHeadID (PK)", "CrimeGroupName", "CrimeSubHeadID (PK)", "CrimeHeadName"]},
            {"name": "Unit / UnitType", "role": "Police station hierarchy",
             "columns": ["UnitID (PK)", "UnitName", "TypeID (FK)", "ParentUnit", "DistrictID (FK)"]},
            {"name": "Employee / Rank / Designation", "role": "Police officers",
             "columns": ["EmployeeID (PK)", "UnitID (FK)", "RankID (FK)", "DesignationID (FK)", "KGID"]},
            {"name": "District / State / Court", "role": "Geo & judicial masters",
             "columns": ["DistrictID (PK)", "StateID (FK)", "CourtID (PK)", "CourtName"]},
        ],
        "relationships": [
            "CaseMaster 1—* Victim / Accused / ComplainantDetails / ArrestSurrender / ActSectionAssociation",
            "CaseMaster *—1 CaseCategory / GravityOffence / CrimeHead / CrimeSubHead / CaseStatus / Court / Employee",
            "CrimeSubHead *—1 CrimeHead ; Section *—1 Act",
            "Unit *—1 District ; District *—1 State ; Employee *—1 Unit/Rank/Designation",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))