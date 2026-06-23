"""Phase 4 (socio-economic correlation): build per-district socio-economic facts
from Census 2011 and correlate them against crime-group rates.

For every indicator (socioeconomic_schema.json) x every crime group (crime_taxonomy.json)
plus the overall crime rate, we compute Pearson (linear) and Spearman (rank)
correlations across the 30 districts, the p-value, the strength band, and a verdict
that compares the observed sign to the indicator's hypothesised sign for that group.

This is the explicit "relate every socio-economic factor to every crime group to
surface all patterns" layer — grounded in the logically-backed schema, not vague.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from . import contracts, paths

SE_INDICATORS = [
    "population_density", "urbanization_rate", "literacy_rate", "graduate_rate",
    "low_income_share", "marginal_worker_share", "nonworker_share",
    "work_participation_rate", "scst_share", "sex_ratio", "internet_penetration",
]
ALPHA = 0.05


def _strength(r: float) -> str:
    a = abs(r)
    if a < 0.2:
        return "negligible"
    if a < 0.4:
        return "weak"
    if a < 0.6:
        return "moderate"
    if a < 0.8:
        return "strong"
    return "very_strong"


def _hypothesis_index():
    """{ (indicator_id, crime_group): {'sign': '+'/'-', 'confidence':..., 'theory':...} }"""
    se = json.loads((contracts.CONTRACTS_DIR / "socioeconomic_schema.json").read_text(encoding="utf-8"))
    idx = {}
    for ind in se["indicators"]:
        for h in ind.get("hypotheses", []):
            idx[(ind["id"], h["crime_group"])] = h
    return idx, se


def build_se_facts(geo_units):
    from .sources import census_se
    census = census_se.load(paths.CENSUS_SE_RAW)
    facts = []
    for u in geo_units:
        if u["level"] != "DISTRICT":
            continue
        code = u["codes"].get("census_district_code")
        c = census.get(code, {})
        density = None
        if u.get("population") and u.get("area_km2"):
            density = round(u["population"] / u["area_km2"], 1)
        facts.append({
            "geo_unit_id": u["geo_unit_id"],
            "name": u["name"],
            "source_year": 2011,
            "source_id": "census_2011",
            "population_density": density,
            "urbanization_rate": c.get("urbanization_rate"),
            "literacy_rate": c.get("literacy_rate"),
            "graduate_rate": c.get("graduate_rate"),
            "low_income_share": c.get("low_income_share"),
            "marginal_worker_share": c.get("marginal_worker_share"),
            "nonworker_share": c.get("nonworker_share"),
            "work_participation_rate": c.get("work_participation_rate"),
            "scst_share": c.get("scst_share"),
            "sex_ratio": c.get("sex_ratio"),
            "internet_penetration": c.get("internet_penetration"),
        })
    return facts


def _crime_group_rates(geo_units, incidents):
    """DataFrame indexed by geo_unit_id: overall + per-group crime rate / 100k (latest year)."""
    inc = pd.DataFrame(incidents)
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    inc["group"] = inc["category_code"].map(contracts.group_of)
    latest = int(inc["year"].max())
    cur = inc[inc["year"] == latest]
    pop = {u["geo_unit_id"]: u.get("population") for u in geo_units if u["level"] == "DISTRICT"}

    grp = cur.groupby(["geo_unit_id", "group"])["case_count"].sum().unstack(fill_value=0).astype(float)
    grp["__overall"] = cur.groupby("geo_unit_id")["case_count"].sum()
    pops = pd.Series({gid: pop.get(gid) for gid in grp.index}, dtype=float)
    rates = grp.div(pops, axis=0) * 1e5  # per-100k for each district row
    rates.columns = [("crime_overall" if c == "__overall" else f"crime_{c}") for c in rates.columns]
    return rates.round(2), latest


def _correlate(se_df, crime_df, hyp):
    targets = [c for c in crime_df.columns]
    joined = se_df.join(crime_df, how="inner")
    results = []
    for ind in SE_INDICATORS:
        if ind not in joined.columns:
            continue
        for tgt in targets:
            sub = joined[[ind, tgt]].dropna()
            n = len(sub)
            if n < 5 or sub[ind].nunique() < 3 or sub[tgt].nunique() < 3:
                continue
            pr, pp = stats.pearsonr(sub[ind], sub[tgt])
            sr, sp = stats.spearmanr(sub[ind], sub[tgt])
            group = tgt.replace("crime_", "").upper() if tgt != "crime_overall" else "OVERALL"
            h = hyp.get((ind, group if group != "OVERALL" else None))  # group hypotheses only
            sign = "+" if pr >= 0 else "-"
            verdict = "exploratory"
            if h:
                if pp < ALPHA:
                    verdict = "confirmed" if sign == h["expected_sign"] else "contradicted"
                else:
                    verdict = "inconclusive"
            results.append({
                "indicator": ind,
                "crime_group": group,
                "pearson_r": round(float(pr), 3),
                "pearson_p": round(float(pp), 4),
                "spearman_r": round(float(sr), 3),
                "spearman_p": round(float(sp), 4),
                "n": n,
                "strength": _strength(pr),
                "significant": bool(pp < ALPHA),
                "observed_sign": sign,
                "hypothesized_sign": h["expected_sign"] if h else None,
                "theory": h["theory"] if h else None,
                "verdict": verdict,
                "ethics_flag": bool(h.get("ethics_flag")) if h else False,
            })
    return results


def run() -> dict:
    paths.ensure_dirs()
    geo_units = json.loads(paths.GEO_UNITS.read_text(encoding="utf-8"))
    incidents = json.loads(paths.INCIDENTS.read_text(encoding="utf-8"))

    facts = build_se_facts(geo_units)
    # validate against the JSON Schema
    schema = contracts.schema("socioeconomic")
    invalid = sum(1 for f in facts if contracts.validate(schema, f))

    paths.SOCIOECONOMIC.write_text(json.dumps(facts, indent=2), encoding="utf-8")

    se_df = pd.DataFrame(facts).set_index("geo_unit_id")[SE_INDICATORS]
    crime_df, latest = _crime_group_rates(geo_units, incidents)
    hyp, se_contract = _hypothesis_index()
    correlations = _correlate(se_df, crime_df, hyp)

    # headline: significant, non-negligible correlations, strongest first
    key = sorted(
        [c for c in correlations if c["significant"] and c["strength"] not in ("negligible",)],
        key=lambda c: abs(c["pearson_r"]), reverse=True,
    )

    api = paths.API_DIR
    (api / "se_indicators.json").write_text(json.dumps({
        "source": "Census of India 2011 (district) + geodesic area",
        "indicators": [i["id"] for i in se_contract["indicators"]],
        "districts": facts,
    }, indent=2), encoding="utf-8")
    (api / "se_correlations.json").write_text(json.dumps({
        "method": se_contract["correlation_method"],
        "ethical_constraints": se_contract["ethical_constraints"],
        "crime_year": latest,
        "n_districts": len(facts),
        "matrix": correlations,
        "key_findings": key[:15],
    }, indent=2), encoding="utf-8")
    (api / "se_schema.json").write_text(json.dumps(se_contract, indent=2), encoding="utf-8")

    return {
        "districts": len(facts), "facts_invalid": invalid,
        "correlations": len(correlations),
        "significant": sum(1 for c in correlations if c["significant"]),
        "confirmed": sum(1 for c in correlations if c["verdict"] == "confirmed"),
        "contradicted": sum(1 for c in correlations if c["verdict"] == "contradicted"),
        "top": key[:3],
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
