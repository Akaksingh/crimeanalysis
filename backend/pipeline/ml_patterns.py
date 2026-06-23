"""Phase 6 — Advanced AI/ML Pattern Detection.

Integrates crime trends (NCRB 2001-2013) with Census 2011 socio-economic
indicators for a richer, multi-dimensional ML analysis pipeline.
All outputs run on real aggregated data — no PII.

Models
------
1. PCA               — unified crime+SE district fingerprint (dimensionality reduction)
2. KMeans on PCA     — socio-economically-aware cluster grouping (k=4)
3. Random Forest     — SE indicators → crime rate prediction + feature importance
4. SHAP (Tree)       — per-district explainability: what drives each district's risk
5. Isolation Forest  — robust multi-dim anomaly detection across crime+SE space
6. Linear Forecast   — per-district next-year OLS case estimate (numpy.polyfit)
7. Hotspot Prob.     — composite 0–1 risk probability combining all ML signals
"""
from __future__ import annotations

import datetime
import json

import numpy as np
import pandas as pd
import shap
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import contracts, paths
from .socioeconomic import SE_INDICATORS, build_se_facts

SEED = 42
K_CLUSTERS = 4
N_PCA = 3
ISO_CONTAMINATION = 0.15   # expect ~15% of districts to be anomalous


# ---------------------------------------------------------------------------
# Feature assembly — combine crime group shares + SE indicators
# ---------------------------------------------------------------------------

def _build_feature_matrix(
    geo_units: list, incidents: list
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Return (combined_df, crime_rates_df, latest_year).

    combined_df  — indexed by geo_unit_id; columns = crime_<group> + SE indicators
    crime_rates  — indexed by geo_unit_id; column = crime_rate_per_100k
    """
    inc = pd.DataFrame(incidents)
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    inc["group"] = inc["category_code"].map(contracts.group_of)
    latest = int(inc["year"].max())
    cur = inc[inc["year"] == latest]

    # Crime composition shares (normalized so each district sums to 1)
    pivot = cur.pivot_table(
        index="geo_unit_id", columns="group",
        values="case_count", aggfunc="sum", fill_value=0,
    )
    shares = pivot.div(pivot.sum(axis=1), axis=0).fillna(0)
    shares.columns = [f"crime_{c}" for c in shares.columns]

    # Overall crime rate per 100k (RF target)
    pop_map = {
        u["geo_unit_id"]: u.get("population")
        for u in geo_units if u["level"] == "DISTRICT"
    }
    total_cases = cur.groupby("geo_unit_id")["case_count"].sum()
    pop_s = pd.Series(
        {gid: pop_map.get(gid) for gid in total_cases.index}, dtype=float
    )
    crime_rate = (total_cases / pop_s * 1e5).rename("crime_rate_per_100k").to_frame()

    # Socio-economic features from Census 2011
    facts = build_se_facts(geo_units)
    se_df = pd.DataFrame(facts).set_index("geo_unit_id")[SE_INDICATORS]

    # Inner join — only districts with both crime and SE data
    combined = shares.join(se_df, how="inner")
    combined.dropna(thresh=len(combined.columns) // 2, inplace=True)

    return combined, crime_rate, latest


# ---------------------------------------------------------------------------
# 1. PCA — dimensionality reduction + component interpretation
# ---------------------------------------------------------------------------

def _run_pca(
    X_scaled: np.ndarray, feature_names: list[str], n_components: int = N_PCA
) -> tuple:
    n_comp = min(n_components, X_scaled.shape[0] - 1, X_scaled.shape[1])
    pca = PCA(n_components=n_comp, random_state=SEED)
    components = pca.fit_transform(X_scaled)

    explained = pca.explained_variance_ratio_.tolist()
    cumulative = float(np.cumsum(explained)[-1])

    component_info = []
    for i, loading in enumerate(pca.components_):
        top_pos = np.argsort(loading)[-3:][::-1].tolist()
        top_neg = np.argsort(loading)[:3].tolist()
        component_info.append({
            "component": i + 1,
            "variance_explained": round(float(explained[i]), 4),
            "top_positive_features": [feature_names[j] for j in top_pos],
            "top_negative_features": [feature_names[j] for j in top_neg],
        })

    return pca, components, component_info, explained, cumulative


# ---------------------------------------------------------------------------
# 2. KMeans on PCA — socio-crime integrated clusters
# ---------------------------------------------------------------------------

def _run_kmeans(
    pca_components: np.ndarray,
    original_df: pd.DataFrame,
    feature_names: list[str],
    names: dict[str, str],
) -> tuple[list, float, np.ndarray, np.ndarray]:

    km = KMeans(n_clusters=K_CLUSTERS, random_state=SEED, n_init=20)
    labels = km.fit_predict(pca_components)

    sil = (
        float(silhouette_score(pca_components, labels))
        if len(set(labels)) > 1 else 0.0
    )

    # Confidence: 1 − (d_nearest / d_second_nearest), clamped [0,1]
    center_dists = km.transform(pca_components)          # (n, k)
    sorted_dists = np.sort(center_dists, axis=1)
    confidence = np.clip(
        1 - sorted_dists[:, 0] / (sorted_dists[:, 1] + 1e-9), 0, 1
    )

    gids = original_df.index.tolist()
    X_orig = original_df.values

    cluster_members: dict[int, list[dict]] = {}
    for i, (gid, lab) in enumerate(zip(gids, labels)):
        cluster_members.setdefault(int(lab), []).append({
            "geo_unit_id": gid,
            "name": names.get(gid, gid),
            "confidence": round(float(confidence[i]), 3),
            "pca_x": round(float(pca_components[i, 0]), 4),
            "pca_y": (
                round(float(pca_components[i, 1]), 4)
                if pca_components.shape[1] > 1 else 0.0
            ),
        })

    crime_cols = [f for f in feature_names if f.startswith("crime_")]
    se_cols = [f for f in feature_names if not f.startswith("crime_")]

    clusters_out = []
    for lab in sorted(cluster_members.keys()):
        member_idx = [i for i, l in enumerate(labels) if l == lab]
        member_vals = X_orig[member_idx]
        mean_profile = dict(
            zip(feature_names, np.nanmean(member_vals, axis=0).round(4))
        )

        crime_profile = {
            k.replace("crime_", ""): round(float(mean_profile[k]), 3)
            for k in crime_cols if k in mean_profile
        }
        dominant_crime = sorted(
            crime_profile, key=crime_profile.get, reverse=True  # type: ignore[arg-type]
        )[:2]

        se_profile = {
            k: round(float(mean_profile[k]), 3)
            for k in se_cols if k in mean_profile
        }

        clusters_out.append({
            "cluster": lab,
            "dominant_crime_groups": dominant_crime,
            "crime_profile": crime_profile,
            "se_profile": se_profile,
            "avg_confidence": round(
                float(np.mean([d["confidence"] for d in cluster_members[lab]])), 3
            ),
            "districts": cluster_members[lab],
            "size": len(cluster_members[lab]),
        })

    return clusters_out, sil, labels, confidence


# ---------------------------------------------------------------------------
# 3+4. Random Forest + SHAP explainability
# ---------------------------------------------------------------------------

def _run_rf_shap(
    combined_df: pd.DataFrame,
    crime_rates: pd.DataFrame,
    names: dict[str, str],
) -> tuple[dict | None, list | None]:

    se_cols = [c for c in combined_df.columns if not c.startswith("crime_")]
    joined = combined_df[se_cols].join(crime_rates, how="inner").dropna()

    if len(joined) < 8:
        return None, None     # too few samples to train meaningfully

    X = joined[se_cols].values.astype(float)
    y = joined["crime_rate_per_100k"].values.astype(float)

    rf = RandomForestRegressor(
        n_estimators=300,
        max_depth=4,           # cap depth to prevent overfitting on n≈30
        min_samples_leaf=2,
        max_features="sqrt",
        oob_score=True,
        random_state=SEED,
    )
    rf.fit(X, y)

    oob_r2 = round(float(rf.oob_score_), 4)
    y_pred = rf.predict(X)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    train_r2 = round(1 - ss_res / (ss_tot + 1e-9), 4)

    # Feature importance ranking
    importances = rf.feature_importances_
    feature_importance = sorted(
        [
            {"feature": se_cols[i], "importance": round(float(importances[i]), 4)}
            for i in range(len(se_cols))
        ],
        key=lambda x: x["importance"],
        reverse=True,
    )

    # SHAP explanations via TreeExplainer (no kernel approximation needed for RF)
    explainer = shap.TreeExplainer(rf, feature_perturbation="tree_path_dependent")
    shap_values = explainer.shap_values(X)

    shap_insights = []
    for i, gid in enumerate(joined.index):
        sv = shap_values[i]
        top_idx = np.argsort(np.abs(sv))[-4:][::-1].tolist()
        shap_insights.append({
            "geo_unit_id": gid,
            "name": names.get(gid, gid),
            "predicted_rate": round(float(y_pred[i]), 1),
            "actual_rate": round(float(y[i]), 1),
            "prediction_error": round(float(y_pred[i] - y[i]), 1),
            "top_drivers": [
                {
                    "feature": se_cols[j],
                    "shap_value": round(float(sv[j]), 3),
                    "direction": "increases_risk" if sv[j] > 0 else "reduces_risk",
                }
                for j in top_idx
            ],
        })

    # Sort by highest predicted crime rate
    shap_insights.sort(key=lambda x: x["predicted_rate"], reverse=True)

    return {
        "oob_r2": oob_r2,
        "train_r2": train_r2,
        "feature_importance": feature_importance,
    }, shap_insights


# ---------------------------------------------------------------------------
# 5. Isolation Forest — multi-dimensional anomaly detection
# ---------------------------------------------------------------------------

def _run_isolation_forest(
    combined_df: pd.DataFrame, names: dict[str, str]
) -> list[dict]:

    df_clean = combined_df.fillna(combined_df.median(numeric_only=True))
    X = df_clean.values.astype(float)
    gids = df_clean.index.tolist()

    iso = IsolationForest(
        n_estimators=300,
        contamination=ISO_CONTAMINATION,
        random_state=SEED,
    )
    iso.fit(X)
    raw_scores = iso.score_samples(X)    # more negative → more anomalous
    preds = iso.predict(X)               # -1 = anomaly, 1 = normal

    # Normalize to [0, 1] anomaly probability (1 = most anomalous)
    lo, hi = raw_scores.min(), raw_scores.max()
    norm_scores = 1.0 - (raw_scores - lo) / (hi - lo + 1e-9)

    anomalies = [
        {
            "geo_unit_id": gids[i],
            "name": names.get(gids[i], gids[i]),
            "anomaly_score": round(float(norm_scores[i]), 3),
            "is_anomaly": bool(preds[i] == -1),
        }
        for i in range(len(gids))
    ]
    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return anomalies


# ---------------------------------------------------------------------------
# 6. Linear trend forecast (per-district OLS, numpy.polyfit)
# ---------------------------------------------------------------------------

def _run_forecasts(
    incidents: list, names: dict[str, str]
) -> tuple[list[dict], int]:

    inc = pd.DataFrame(incidents)
    inc["year"] = inc["registration_date"].str.slice(0, 4).astype(int)
    latest = int(inc["year"].max())
    tot = inc.groupby(["geo_unit_id", "year"])["case_count"].sum().reset_index()

    forecasts = []
    for gid, g in tot.groupby("geo_unit_id"):
        g = g.sort_values("year")
        years = g["year"].values.astype(float)
        cases = g["case_count"].values.astype(float)

        if len(years) < 3:
            continue

        # OLS linear fit
        coeffs = np.polyfit(years, cases, 1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])
        forecast_year = int(latest) + 1
        forecast_cases = max(0, int(slope * forecast_year + intercept))

        # R² of the linear fit
        y_pred_hist = np.polyval(coeffs, years)
        ss_res = float(np.sum((cases - y_pred_hist) ** 2))
        ss_tot = float(np.sum((cases - cases.mean()) ** 2))
        r2 = float(1 - ss_res / (ss_tot + 1e-9))

        # 95% prediction interval for next-year point
        n = len(years)
        se = float(np.sqrt(ss_res / max(n - 2, 1)))
        x_mean = float(years.mean())
        x_var = float(np.sum((years - x_mean) ** 2))
        pi_factor = se * float(
            np.sqrt(1 + 1 / n + (forecast_year - x_mean) ** 2 / (x_var + 1e-9))
        )

        if slope > 10:
            trend = "rising"
        elif slope < -10:
            trend = "dropping"
        else:
            trend = "stable"

        forecasts.append({
            "geo_unit_id": gid,
            "name": names.get(str(gid), str(gid)),
            "forecast_year": forecast_year,
            "forecast_cases": forecast_cases,
            "slope_per_year": round(slope, 2),
            "r2": round(r2, 3),
            "trend": trend,
            "ci_low": max(0, int(forecast_cases - 1.96 * pi_factor)),
            "ci_high": int(forecast_cases + 1.96 * pi_factor),
        })

    forecasts.sort(key=lambda x: x["forecast_cases"], reverse=True)
    return forecasts, latest


# ---------------------------------------------------------------------------
# 7. Hotspot probability — composite score from all ML signals
# ---------------------------------------------------------------------------

def _hotspot_probability(
    forecasts: list[dict],
    iso_anomalies: list[dict],
    labels: np.ndarray,
    clusters: list[dict],
    gids: list[str],
    names: dict[str, str],
) -> list[dict]:

    # Normalised slope score: 0 (biggest drop) → 1 (biggest rise)
    slopes = {f["geo_unit_id"]: f["slope_per_year"] for f in forecasts}
    if slopes:
        max_abs = max(abs(s) for s in slopes.values()) or 1.0
        slope_score = {
            gid: float(np.clip((s / max_abs + 1) / 2, 0, 1))
            for gid, s in slopes.items()
        }
    else:
        slope_score = {}

    # Isolation anomaly score (already 0–1)
    iso_score = {a["geo_unit_id"]: a["anomaly_score"] for a in iso_anomalies}

    # Cluster risk weight: rank clusters by avg crime intensity (sum of crime_profile values)
    cluster_intensity = {
        c["cluster"]: sum(c["crime_profile"].values()) for c in clusters
    }
    max_intensity = max(cluster_intensity.values()) or 1.0
    cluster_score_map = {
        lab: float(v / max_intensity)
        for lab, v in cluster_intensity.items()
    }

    lab_of: dict[str, int] = {gid: int(labels[i]) for i, gid in enumerate(gids)}

    results = []
    for gid in gids:
        s_slope = slope_score.get(gid, 0.5)
        s_iso = iso_score.get(gid, 0.5)
        s_cluster = cluster_score_map.get(lab_of.get(gid, -1), 0.5)

        # Weighted composite: trend drives 40%, isolation 35%, cluster 25%
        prob = round(float(np.clip(0.40 * s_slope + 0.35 * s_iso + 0.25 * s_cluster, 0, 1)), 3)

        if prob >= 0.72:
            tier = "Critical"
        elif prob >= 0.56:
            tier = "High"
        elif prob >= 0.40:
            tier = "Medium"
        else:
            tier = "Low"

        results.append({
            "geo_unit_id": gid,
            "name": names.get(gid, gid),
            "probability": prob,
            "risk_tier": tier,
            "signal_breakdown": {
                "trend_score": round(s_slope, 3),
                "isolation_score": round(s_iso, 3),
                "cluster_risk_score": round(s_cluster, 3),
            },
        })

    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Orchestrator — called from pipeline/run.py
# ---------------------------------------------------------------------------

def run() -> dict:
    paths.ensure_dirs()
    geo_units = json.loads(paths.GEO_UNITS.read_text(encoding="utf-8"))
    incidents = json.loads(paths.INCIDENTS.read_text(encoding="utf-8"))
    names = {u["geo_unit_id"]: u["name"] for u in geo_units}

    # ── 1. Build unified feature matrix ────────────────────────────────────
    combined_df, crime_rates, latest = _build_feature_matrix(geo_units, incidents)
    feature_names = combined_df.columns.tolist()
    gids = combined_df.index.tolist()

    # ── 2. Standardise (fit on median-imputed matrix) ───────────────────────
    df_imputed = combined_df.fillna(combined_df.median(numeric_only=True))
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_imputed.values.astype(float))

    # ── 3. PCA ──────────────────────────────────────────────────────────────
    _pca_model, pca_components, pca_info, explained, cumulative = _run_pca(
        X_scaled, feature_names
    )

    # ── 4. KMeans on PCA ────────────────────────────────────────────────────
    clusters, sil, labels, confidence = _run_kmeans(
        pca_components, df_imputed, feature_names, names
    )

    # ── 5. Random Forest + SHAP ─────────────────────────────────────────────
    rf_results, shap_insights = _run_rf_shap(combined_df, crime_rates, names)

    # ── 6. Isolation Forest ─────────────────────────────────────────────────
    iso_anomalies = _run_isolation_forest(combined_df, names)

    # ── 7. Linear forecasts ─────────────────────────────────────────────────
    forecasts, _latest = _run_forecasts(incidents, names)

    # ── 8. Hotspot probability ──────────────────────────────────────────────
    hotspot_preds = _hotspot_probability(
        forecasts, iso_anomalies, labels, clusters, gids, names
    )

    # ── Assemble & write payload ────────────────────────────────────────────
    inc_df = pd.DataFrame(incidents)
    years_trained = (
        f"{inc_df['registration_date'].str.slice(0,4).astype(int).min()}–{latest}"
    )

    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "latest_crime_year": latest,
        "model_meta": {
            "algorithms": [
                "PCA (dimensionality reduction)",
                "KMeans k=4 (socio-crime integrated clusters)",
                "RandomForest (SE → crime rate prediction)",
                "SHAP TreeExplainer (per-district explainability)",
                "IsolationForest (multi-dimensional anomaly detection)",
                "OLS Linear Forecast (numpy.polyfit)",
            ],
            "n_districts": len(gids),
            "n_features": len(feature_names),
            "features_used": feature_names,
            "pca_components_used": int(pca_components.shape[1]),
            "pca_cumulative_variance_explained": round(cumulative, 4),
            "kmeans_k": K_CLUSTERS,
            "kmeans_silhouette_score": round(sil, 4),
            "rf_oob_r2": rf_results["oob_r2"] if rf_results else None,
            "rf_train_r2": rf_results["train_r2"] if rf_results else None,
            "isolation_forest_contamination": ISO_CONTAMINATION,
            "years_trained": years_trained,
            "socioeconomic_source": "Census of India 2011",
            "crime_data_source": "NCRB District IPC",
        },
        "pca_components": pca_info,
        "clusters": clusters,
        "rf_feature_importance": (
            rf_results["feature_importance"] if rf_results else []
        ),
        "shap_insights": shap_insights or [],
        "isolation_anomalies": iso_anomalies,
        "forecasts": forecasts[:20],
        "hotspot_predictions": hotspot_preds[:15],
    }

    (paths.API_DIR / "ml_insights.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    return {
        "districts": len(gids),
        "features": len(feature_names),
        "clusters": len(clusters),
        "silhouette_score": round(sil, 3),
        "pca_variance_explained": round(cumulative, 3),
        "rf_oob_r2": rf_results["oob_r2"] if rf_results else None,
        "isolation_anomalies_flagged": sum(
            1 for a in iso_anomalies if a["is_anomaly"]
        ),
        "forecasts_generated": len(forecasts),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
