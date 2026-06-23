"""Aggregate canonical incidents -> KPI facts, hotspot flags, baseline risk scores,
and the static district-level API payloads the frontend consumes.

Formulas follow docs/phase-0/contracts/kpi_catalog.json and the baseline methods in
docs/phase-0/06-baseline-metrics.md. Everything here runs on open aggregated data;
person-level components (repeat-offender) are absent, so the risk score redistributes
their weight and flags itself `partial` — exactly as the baseline doc prescribes.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import contracts, paths

# baseline risk weights (docs/phase-0/06-baseline-metrics.md, Part B)
RISK_WEIGHTS = {
    "crime_intensity": 0.30,
    "trend_momentum": 0.20,
    "hotspot_membership": 0.20,
    "repeat_offender": 0.15,   # unavailable on open data -> redistributed
    "socioeconomic": 0.15,     # unavailable on open data -> redistributed
}
AVAILABLE_COMPONENTS = ["crime_intensity", "trend_momentum", "hotspot_membership"]
HOTSPOT_Z = 1.5
EMERGING_Z = 1.0


def _band(score: float) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Medium"
    if score <= 75:
        return "High"
    return "Critical"


def _minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi - lo < 1e-9:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


def _load_frames():
    geo = pd.DataFrame(json.loads(paths.GEO_UNITS.read_text(encoding="utf-8")))
    inc = pd.DataFrame(json.loads(paths.INCIDENTS.read_text(encoding="utf-8")))
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    inc["group"] = inc["category_code"].map(contracts.group_of)
    inc["severity"] = inc["category_code"].map(contracts.severity_weight)
    return geo, inc


def _district_year_metrics(geo: pd.DataFrame, inc: pd.DataFrame) -> pd.DataFrame:
    districts = geo[geo["level"] == "DISTRICT"][
        ["geo_unit_id", "name", "parent_id", "population", "female_population", "centroid"]
    ].copy()

    grp = inc.groupby(["geo_unit_id", "year"])
    total = grp["case_count"].sum().rename("total_cognizable_cases")
    sev = (
        inc.assign(weighted=inc["case_count"] * inc["severity"])
        .groupby(["geo_unit_id", "year"])["weighted"].sum().rename("severity_weighted_cases")
    )
    violent = (
        inc[inc["group"] == "VIOLENT"].groupby(["geo_unit_id", "year"])["case_count"]
        .sum().rename("violent_cases")
    )
    women = (
        inc[inc["group"] == "WOMEN"].groupby(["geo_unit_id", "year"])["case_count"]
        .sum().rename("women_cases")
    )

    m = pd.concat([total, sev, violent, women], axis=1).reset_index().fillna(0)
    m = m.merge(districts, on="geo_unit_id", how="left")

    m["crime_rate_per_100k"] = m["total_cognizable_cases"] / m["population"] * 1e5
    m["severity_weighted_index"] = m["severity_weighted_cases"] / m["population"] * 1e5
    m["violent_crime_share"] = np.where(
        m["total_cognizable_cases"] > 0, m["violent_cases"] / m["total_cognizable_cases"], 0.0
    )
    m["crime_against_women_rate"] = np.where(
        m["female_population"] > 0, m["women_cases"] / m["female_population"] * 1e5, np.nan
    )
    return m.round(3)


def _trend_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    return float(np.polyfit(x, values, 1)[0])


def build() -> dict:
    paths.ensure_dirs()
    geo, inc = _load_frames()
    metrics = _district_year_metrics(geo, inc)
    years = sorted(metrics["year"].unique().tolist())
    latest = years[-1]

    # ---- kpi_facts (long format) ----
    fact_cols = [
        "total_cognizable_cases", "crime_rate_per_100k", "severity_weighted_index",
        "violent_crime_share", "crime_against_women_rate",
    ]
    kpi_facts = []
    for _, r in metrics.iterrows():
        for metric_id in fact_cols:
            val = r[metric_id]
            if pd.isna(val):
                continue
            kpi_facts.append({
                "geo_unit_id": r["geo_unit_id"],
                "period": int(r["year"]),
                "metric_id": metric_id,
                "value": round(float(val), 3),
            })
    paths.KPI_FACTS.write_text(json.dumps(kpi_facts, indent=2), encoding="utf-8")

    # ---- per-district trend + hotspot + risk (latest year) ----
    cur = metrics[metrics["year"] == latest].copy().set_index("geo_unit_id")

    # trend slope of total cases across years, per district
    slope = {}
    for gid, g in metrics.sort_values("year").groupby("geo_unit_id"):
        slope[gid] = _trend_slope(g["total_cognizable_cases"].tolist())
    cur["trend_slope"] = pd.Series(slope)

    # hotspot z-score on severity_weighted_index, peers = districts in the state
    swi = cur["severity_weighted_index"]
    mu, sd = swi.mean(), swi.std(ddof=0)
    cur["hotspot_z"] = (swi - mu) / sd if sd > 1e-9 else 0.0
    cur["hotspot_status"] = "none"
    cur.loc[(cur["hotspot_z"] > EMERGING_Z) & (cur["trend_slope"] > 0), "hotspot_status"] = "emerging"
    cur.loc[cur["hotspot_z"] > HOTSPOT_Z, "hotspot_status"] = "established"

    # risk components, min-max normalized across districts
    ci = _minmax(cur["severity_weighted_index"])
    tm = _minmax(cur["trend_slope"])
    hm = cur["hotspot_status"].map({"none": 0.0, "emerging": 0.5, "established": 1.0})
    avail_w = sum(RISK_WEIGHTS[c] for c in AVAILABLE_COMPONENTS)  # 0.70
    comp_vals = {"crime_intensity": ci, "trend_momentum": tm, "hotspot_membership": hm}

    detail = {}
    districts_summary = []
    for gid in cur.index:
        components = {}
        score = 0.0
        for c in AVAILABLE_COMPONENTS:
            w = RISK_WEIGHTS[c] / avail_w  # redistribute to sum to 1
            v = float(comp_vals[c][gid])
            contrib = round(100 * w * v, 2)
            components[c] = {"value": round(v, 3), "weight": round(w, 3), "contribution": contrib}
            score += contrib
        score = round(score, 1)
        band = _band(score)

        # yearly trend series for this district
        gseries = metrics[metrics["geo_unit_id"] == gid].sort_values("year")
        trend = [
            {"year": int(y), "total": int(t), "rate_per_100k": round(float(rt), 1)}
            for y, t, rt in zip(gseries["year"], gseries["total_cognizable_cases"], gseries["crime_rate_per_100k"])
        ]
        # category breakdown (latest year)
        bd = (
            inc[(inc["geo_unit_id"] == gid) & (inc["year"] == latest)]
            .groupby(["category_code", "group"])["case_count"].sum()
            .reset_index().sort_values("case_count", ascending=False)
        )
        breakdown = [
            {"category_code": cc, "group": gp, "cases": int(n)}
            for cc, gp, n in zip(bd["category_code"], bd["group"], bd["case_count"])
        ]

        row = cur.loc[gid]
        rec = {
            "geo_unit_id": gid,
            "name": row["name"],
            "year": int(latest),
            "population": int(row["population"]) if not pd.isna(row["population"]) else None,
            "kpis": {
                "total_cognizable_cases": int(row["total_cognizable_cases"]),
                "crime_rate_per_100k": round(float(row["crime_rate_per_100k"]), 1),
                "severity_weighted_index": round(float(row["severity_weighted_index"]), 1),
                "violent_crime_share": round(float(row["violent_crime_share"]), 3),
                "crime_against_women_rate": None if pd.isna(row["crime_against_women_rate"]) else round(float(row["crime_against_women_rate"]), 1),
            },
            "hotspot": {
                "zscore": round(float(row["hotspot_z"]), 2),
                "trend_slope": round(float(row["trend_slope"]), 1),
                "status": row["hotspot_status"],
            },
            "risk": {"score": score, "band": band, "partial": True, "components": components},
            "trend": trend,
            "breakdown": breakdown,
        }
        detail[gid] = rec
        districts_summary.append({
            "geo_unit_id": gid,
            "name": row["name"],
            "total_cognizable_cases": rec["kpis"]["total_cognizable_cases"],
            "crime_rate_per_100k": rec["kpis"]["crime_rate_per_100k"],
            "severity_weighted_index": rec["kpis"]["severity_weighted_index"],
            "hotspot_status": row["hotspot_status"],
            "risk_score": score,
            "risk_band": band,
            "centroid": row["centroid"],
        })

    districts_summary.sort(key=lambda d: d["risk_score"], reverse=True)

    # ---- state-level trend ----
    state_trend = [
        {"year": int(y), "total_cognizable_cases": int(metrics[metrics["year"] == y]["total_cognizable_cases"].sum())}
        for y in years
    ]

    # ---- write API payloads ----
    api = paths.API_DIR
    meta = {
        "platform": "AI-Driven Crime Analytics & Visualization Platform",
        "pilot_state": "Karnataka",
        "phase": "2",
        "data_note": "Real data: NCRB district-wise IPC crimes (2001-2012) + Census 2011 population + Census 2011 district boundaries.",
        "sources": ["NCRB (data.gov.in) district-wise IPC crimes", "Census of India 2011", "Census 2011 district boundaries (datameet)"],
        "years": years,
        "latest_year": int(latest),
        "district_count": len(districts_summary),
        "metrics_available": fact_cols,
    }
    _write(api / "meta.json", meta)
    _write(api / "districts.json", districts_summary)
    _write(api / "district_detail.json", detail)
    _write(api / "hotspots.json", [d for d in districts_summary if d["hotspot_status"] != "none"])
    _write(api / "trends.json", {"state": "Karnataka", "series": state_trend})
    _write(api / "kpi_catalog.json", contracts.kpi_catalog())
    _write(api / "categories.json", contracts.taxonomy())

    return {
        "years": years, "latest_year": latest,
        "districts": len(districts_summary),
        "kpi_facts": len(kpi_facts),
        "hotspots": sum(1 for d in districts_summary if d["hotspot_status"] != "none"),
        "highest_risk": districts_summary[0] if districts_summary else None,
    }


def _write(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


if __name__ == "__main__":
    s = build()
    print(json.dumps(s, indent=2))
