"""Phase 3 — Core Intelligence: repeat-offender tracking, network/link analysis,
and AI/ML pattern detection.

Two data planes, per the Phase 0 governance split:
  * PERSON-LEVEL (repeat-offender, co-offending network): there is NO open
    person-level Indian crime data (PII law), so this runs on **synthetic**
    offenders (source_id=synthetic_fir, pii_level=high). The synthetic population
    is anchored to the REAL district crime volumes and category mix, and is fully
    deterministic (seeded) so it is reproducible. Clearly labelled as synthetic.
  * AREA-LEVEL (pattern detection): runs on the REAL NCRB data — KMeans clustering
    of districts by crime signature + per-district anomaly detection.
"""
from __future__ import annotations

import json
import random

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from . import contracts, paths

SEED = 42
OFFENDERS_PER_1000_CASES = 6   # synthetic offender density
GENDERS = ["M", "M", "M", "F"]  # offending skews male in recorded data
AGE_BANDS = ["18-25", "26-35", "36-45", "46-60"]
FIRST_NAMES = ["Ravi", "Suresh", "Manju", "Anil", "Kiran", "Prakash", "Lokesh",
               "Ramesh", "Vinod", "Shankar", "Naveen", "Mahesh", "Girish", "Basava"]
LAST_INITIALS = ["K", "M", "S", "R", "N", "B", "G", "P", "H", "V"]


# --------------------------------------------------------------------------- #
# Synthetic offender population + co-offending network
# --------------------------------------------------------------------------- #
def _synthesize(geo_units, incidents, rng):
    districts = [u for u in geo_units if u["level"] == "DISTRICT"]
    inc = pd.DataFrame(incidents)
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    latest = int(inc["year"].max())
    cur = inc[inc["year"] == latest]

    entities, links = [], []
    # co-offending adjacency: offender -> {co-offender: weight}
    adj: dict[str, dict[str, int]] = {}
    oid = 0

    for d in districts:
        gid = d["geo_unit_id"]
        dcur = cur[cur["geo_unit_id"] == gid]
        total = int(dcur["case_count"].sum())
        if total <= 0:
            continue
        # category distribution for realistic offence assignment
        cats = dcur.groupby("category_code")["case_count"].sum()
        cat_codes = cats.index.tolist()
        cat_p = (cats / cats.sum()).tolist()

        n_off = max(3, round(total / 1000 * OFFENDERS_PER_1000_CASES))
        district_offenders = []
        for _ in range(n_off):
            oid += 1
            eid = f"ENT-SYN-{oid:05d}"
            district_offenders.append(eid)
            entities.append({
                "entity_id": eid,
                "role": "offender",
                "display_name_masked": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}.",
                "aliases": [],
                "gender": rng.choice(GENDERS),
                "age_band": rng.choice(AGE_BANDS),
                "home_geo_unit_id": gid,
                "incident_count": 0,
                "first_seen": None,
                "last_seen": None,
                "resolution_confidence": round(rng.uniform(0.7, 0.98), 2),
                "source_id": "synthetic_fir",
            })

        # synthesize individual cases and attach 1-3 offenders (co-offending)
        n_cases = int(n_off * 1.6)
        for c in range(n_cases):
            category = rng.choices(cat_codes, weights=cat_p, k=1)[0]
            year = rng.randint(latest - 4, latest)
            case_id = f"SYNC-{gid}-{latest}-{c:04d}"
            k = rng.choices([1, 2, 3], weights=[0.7, 0.22, 0.08], k=1)[0]
            crew = rng.sample(district_offenders, min(k, len(district_offenders)))
            for eid in crew:
                links.append({"entity_id": eid, "case_id": case_id,
                              "geo_unit_id": gid, "year": year, "category_code": category})
            # co-offending edges within the crew
            for i in range(len(crew)):
                for j in range(i + 1, len(crew)):
                    a, b = crew[i], crew[j]
                    adj.setdefault(a, {}).setdefault(b, 0)
                    adj.setdefault(b, {}).setdefault(a, 0)
                    adj[a][b] += 1
                    adj[b][a] += 1

    # roll up per-offender stats
    by_off: dict[str, list] = {}
    for ln in links:
        by_off.setdefault(ln["entity_id"], []).append(ln)
    ent_by_id = {e["entity_id"]: e for e in entities}
    for eid, ls in by_off.items():
        years = sorted(l["year"] for l in ls)
        e = ent_by_id[eid]
        e["incident_count"] = len(ls)
        e["first_seen"] = f"{years[0]}-01-01"
        e["last_seen"] = f"{years[-1]}-12-31"

    return entities, links, adj, latest


def _network_metrics(adj):
    """Degree centrality + connected components via union-find."""
    nodes = list(adj.keys())
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    edges = 0
    for a, nbrs in adj.items():
        for b in nbrs:
            if a < b:
                edges += 1
                union(a, b)

    comps: dict[str, int] = {}
    for n in nodes:
        comps[find(n)] = comps.get(find(n), 0) + 1
    degree = {n: len(adj[n]) for n in nodes}
    # stable small integer id per component (largest first) for node coloring
    roots_by_size = sorted(comps, key=lambda r: comps[r], reverse=True)
    comp_id = {r: i for i, r in enumerate(roots_by_size)}
    node_component = {n: comp_id[find(n)] for n in nodes}
    return {"nodes": len(nodes), "edges": edges,
            "components": len(comps), "largest_component": max(comps.values()) if comps else 0,
            "degree": degree, "node_component": node_component}


def _network_graph(adj, ent_by_id, names, degree, node_component):
    """Build a node/edge graph payload for the interactive 3D force graph.
    Only offenders that co-offend with someone (degree >= 1) are nodes."""
    nodes = []
    for eid in adj:
        e = ent_by_id.get(eid, {})
        nodes.append({
            "id": eid,
            "name": e.get("display_name_masked", eid),
            "district": names.get(e.get("home_geo_unit_id")),
            "incidents": e.get("incident_count", 0),
            "degree": degree.get(eid, 0),
            "component": node_component.get(eid, 0),
        })
    links = []
    for a, nbrs in adj.items():
        for b, w in nbrs.items():
            if a < b:  # undirected — emit once
                links.append({"source": a, "target": b, "weight": w})
    return {"nodes": nodes, "links": links}


def _case_graph(links, ent_by_id, names, degree, node_component):
    """Bipartite person<->case graph for the 3D view.

    Shows the OTHER relationship the co-offending graph can't: the SAME person
    (matched by entity_id) appearing across MULTIPLE cases. Two node kinds:
      * kind="person" — an offender; size scales with how many cases they have.
      * kind="case"   — a single case (case_id); size scales with crew size.
    An edge person->case means "this person was involved in this case", so a
    repeat offender visibly branches out to several case nodes."""
    case_members: dict[str, set] = {}
    case_meta: dict[str, dict] = {}
    for ln in links:
        cid = ln["case_id"]
        case_members.setdefault(cid, set()).add(ln["entity_id"])
        case_meta.setdefault(cid, {"year": ln["year"], "category_code": ln["category_code"],
                                   "geo_unit_id": ln["geo_unit_id"]})

    persons = {ln["entity_id"] for ln in links}
    nodes = []
    for eid in persons:
        e = ent_by_id.get(eid, {})
        nodes.append({
            "id": eid,
            "kind": "person",
            "name": e.get("display_name_masked", eid),
            "district": names.get(e.get("home_geo_unit_id")),
            "incidents": e.get("incident_count", 0),
            "degree": degree.get(eid, 0),
            # solo-only offenders have no crew/component -> null (neutral colour)
            "component": node_component.get(eid),
        })
    for cid, members in case_members.items():
        meta = case_meta[cid]
        nodes.append({
            "id": cid,
            "kind": "case",
            "name": cid,
            "district": names.get(meta["geo_unit_id"]),
            "year": meta["year"],
            "category": meta["category_code"],
            "size": len(members),
        })

    edges = [{"source": ln["entity_id"], "target": ln["case_id"]} for ln in links]
    cases_per_person: dict[str, int] = {}
    for ln in links:
        cases_per_person[ln["entity_id"]] = cases_per_person.get(ln["entity_id"], 0) + 1
    summary = {
        "persons": len(persons),
        "cases": len(case_members),
        "memberships": len(edges),
        "repeat_offenders": sum(1 for c in cases_per_person.values() if c >= 2),
    }
    return {"nodes": nodes, "links": edges, "summary": summary}


# --------------------------------------------------------------------------- #
# AI/ML pattern detection on the REAL data
# --------------------------------------------------------------------------- #
def _patterns(geo_units, incidents):
    inc = pd.DataFrame(incidents)
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    inc["group"] = inc["category_code"].map(contracts.group_of)
    latest = int(inc["year"].max())
    names = {u["geo_unit_id"]: u["name"] for u in geo_units}

    # --- district clustering by crime signature (group shares, latest year) ---
    # Exclude the OTHER_SLL catch-all so clusters reflect the meaningful crime mix
    # (violent vs property vs crimes-against-women etc.), not the residual bucket.
    cur = inc[(inc["year"] == latest) & (inc["group"] != "OTHER_SLL")]
    pivot = cur.pivot_table(index="geo_unit_id", columns="group", values="case_count",
                            aggfunc="sum", fill_value=0)
    shares = pivot.div(pivot.sum(axis=1), axis=0)  # normalize to composition
    X = StandardScaler().fit_transform(shares.values)
    k = 4
    km = KMeans(n_clusters=k, random_state=SEED, n_init=10).fit(X)
    clusters = {}
    for gid, lab in zip(shares.index, km.labels_):
        clusters.setdefault(int(lab), []).append(gid)
    # describe each cluster by its dominant crime group
    cluster_desc = []
    for lab, gids in sorted(clusters.items()):
        sub = shares.loc[gids].mean()
        dominant = sub.sort_values(ascending=False).index[:2].tolist()
        cluster_desc.append({
            "cluster": lab,
            "dominant_groups": dominant,
            "districts": [names[g] for g in gids],
            "size": len(gids),
        })

    # --- anomaly detection: per-district year z-score of total cases ---
    tot = inc.groupby(["geo_unit_id", "year"])["case_count"].sum().reset_index()
    anomalies = []
    for gid, g in tot.groupby("geo_unit_id"):
        vals = g.sort_values("year")
        mu, sd = vals["case_count"].mean(), vals["case_count"].std(ddof=0)
        if sd < 1e-9:
            continue
        for _, r in vals.iterrows():
            z = (r["case_count"] - mu) / sd
            if abs(z) >= 1.8:
                anomalies.append({
                    "geo_unit_id": gid, "name": names[gid],
                    "year": int(r["year"]), "cases": int(r["case_count"]),
                    "zscore": round(float(z), 2),
                    "direction": "spike" if z > 0 else "drop",
                })
    anomalies.sort(key=lambda a: abs(a["zscore"]), reverse=True)
    return {"latest_year": latest, "clusters": cluster_desc, "anomalies": anomalies[:25]}


# --------------------------------------------------------------------------- #
def run() -> dict:
    paths.ensure_dirs()
    geo_units = json.loads(paths.GEO_UNITS.read_text(encoding="utf-8"))
    incidents = json.loads(paths.INCIDENTS.read_text(encoding="utf-8"))
    rng = random.Random(SEED)

    entities, links, adj, latest = _synthesize(geo_units, incidents, rng)
    net = _network_metrics(adj)
    degree = net.pop("degree")
    node_component = net.pop("node_component")

    # validate synthetic entities against the canonical schema
    se = contracts.schema("entity")
    invalid = sum(1 for e in entities if contracts.validate(se, e))

    paths.ENTITIES.write_text(json.dumps(entities, indent=2), encoding="utf-8")
    paths.OFFENDER_LINKS.write_text(json.dumps(links, indent=2), encoding="utf-8")

    names = {u["geo_unit_id"]: u["name"] for u in geo_units}
    repeat = [e for e in entities if e["incident_count"] >= 2]
    repeat.sort(key=lambda e: e["incident_count"], reverse=True)
    top_repeat = [{
        "entity_id": e["entity_id"], "name": e["display_name_masked"],
        "district": names.get(e["home_geo_unit_id"]), "incident_count": e["incident_count"],
        "first_seen": e["first_seen"], "last_seen": e["last_seen"],
        "degree": degree.get(e["entity_id"], 0),
    } for e in repeat[:25]]

    # most central offenders (link analysis)
    central = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:15]
    top_central = [{
        "entity_id": eid, "name": next(e["display_name_masked"] for e in entities if e["entity_id"] == eid),
        "district": names.get(next(e["home_geo_unit_id"] for e in entities if e["entity_id"] == eid)),
        "co_offenders": deg,
    } for eid, deg in central if deg > 0]

    patterns = _patterns(geo_units, incidents)

    # ---- API payloads ----
    api = paths.API_DIR
    repeat_payload = {
        "data_note": "SYNTHETIC offenders (no open person-level data exists). Anchored to real district crime volumes/mix; deterministic.",
        "total_offenders": len(entities),
        "repeat_offenders": len(repeat),
        "repeat_ratio": round(len(repeat) / len(entities), 3) if entities else 0,
        "top": top_repeat,
    }
    ent_by_id = {e["entity_id"]: e for e in entities}
    network_payload = {
        "data_note": "SYNTHETIC co-offending network.",
        "summary": net,
        "top_central_offenders": top_central,
        "graph": _network_graph(adj, ent_by_id, names, degree, node_component),
        "case_graph": _case_graph(links, ent_by_id, names, degree, node_component),
    }
    (api / "intel_repeat_offenders.json").write_text(json.dumps(repeat_payload, indent=2), encoding="utf-8")
    (api / "intel_network.json").write_text(json.dumps(network_payload, indent=2), encoding="utf-8")
    (api / "intel_patterns.json").write_text(json.dumps(patterns, indent=2), encoding="utf-8")

    return {
        "entities": len(entities), "entities_invalid": invalid,
        "links": len(links), "repeat_offenders": len(repeat),
        "network": net, "clusters": len(patterns["clusters"]), "anomalies": len(patterns["anomalies"]),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
