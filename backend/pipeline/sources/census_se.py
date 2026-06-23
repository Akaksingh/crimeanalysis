"""Source adapter for the Census 2011 district socio-economic dataset.

Real data: Census of India 2011, district-level primary census abstract
(640 districts, 118 columns). This adapter filters to Karnataka and derives the
socio-economic indicators defined in docs/phase-0/contracts/socioeconomic_schema.json
exactly per their formulas. Joins to geo_units on the Census district code.
(population_density is added later in socioeconomic.py using the geodesic area.)
"""
from __future__ import annotations

import pandas as pd

STATE_COL = "State name"
CODE_COL = "District code"


def _pct(num, den):
    return round(float(num) / float(den) * 100, 2) if den else None


def load(csv_path) -> dict:
    """Returns {census_district_code(int): {indicator: value, ...}, ...} for Karnataka."""
    df = pd.read_csv(csv_path)
    ka = df[df[STATE_COL].astype(str).str.upper().str.contains("KARNATAKA", na=False)].copy()

    out = {}
    for _, r in ka.iterrows():
        code = int(r[CODE_COL])
        P = r["Population"]
        workers = r["Workers"]
        households = r["Households"]
        ppp_total = r.get("Total_Power_Parity")
        out[code] = {
            "census_name": r["District name"],
            "urbanization_rate": _pct(r["Urban_Households"], households),
            "literacy_rate": _pct(r["Literate"], P),
            "graduate_rate": _pct(r["Graduate_Education"], P),
            "low_income_share": _pct(r["Power_Parity_Less_than_Rs_45000"], ppp_total) if pd.notna(ppp_total) else None,
            "marginal_worker_share": _pct(r["Marginal_Workers"], workers),
            "nonworker_share": _pct(r["Non_Workers"], P),
            "work_participation_rate": _pct(workers, P),
            "scst_share": _pct(r["SC"] + r["ST"], P),
            "sex_ratio": round(float(r["Female"]) / float(r["Male"]) * 1000, 1) if r["Male"] else None,
            "internet_penetration": _pct(r["Households_with_Internet"], households),
        }
    return out
