"""Loads the Phase 0 contracts and exposes mapping + validation helpers.

The Phase 0 contracts (docs/phase-0/contracts/*.json) are the single source of
truth. Nothing here hard-codes taxonomy/geo/KPI knowledge — it all reads the JSON.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# repo_root/backend/pipeline/contracts.py -> repo_root
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "docs" / "phase-0" / "contracts"


def _read(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def taxonomy() -> dict:
    return _read("crime_taxonomy.json")


@lru_cache(maxsize=None)
def geo_hierarchy() -> dict:
    return _read("geo_hierarchy.json")


@lru_cache(maxsize=None)
def kpi_catalog() -> dict:
    return _read("kpi_catalog.json")


@lru_cache(maxsize=None)
def data_sources() -> dict:
    return _read("data_sources.json")


@lru_cache(maxsize=None)
def schema(name: str) -> dict:
    return _read(f"schema_{name}.json")


# --------------------------------------------------------------------------- #
# Taxonomy mapping: raw NCRB head / legal section -> canonical category code
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


@lru_cache(maxsize=None)
def _indexes():
    head_index: dict[str, str] = {}
    section_index: dict[str, str] = {}
    cat_by_code: dict[str, dict] = {}
    for c in taxonomy()["categories"]:
        cat_by_code[c["code"]] = c
        for h in c.get("ncrb_heads", []):
            head_index[_norm(h)] = c["code"]
        for s in list(c.get("ipc_sections", [])) + list(c.get("bns_sections", [])):
            section_index.setdefault(str(s).strip(), c["code"])
    return head_index, section_index, cat_by_code


def map_to_category(head: str | None = None, section: str | None = None) -> dict:
    """Map a raw label to a canonical code. Returns dict with code + method.

    method: 'ncrb_head' | 'section' | 'fallback' (unmapped -> OTHER, flagged by DQ).
    """
    head_index, section_index, _ = _indexes()
    if head is not None:
        code = head_index.get(_norm(head))
        if code:
            return {"code": code, "method": "ncrb_head"}
    if section is not None:
        code = section_index.get(str(section).strip())
        if code:
            return {"code": code, "method": "section"}
    return {"code": "OTHER", "method": "fallback", "raw": head if head is not None else section}


def category_meta(code: str) -> dict | None:
    return _indexes()[2].get(code)


def severity_weight(code: str) -> int:
    c = category_meta(code)
    return int(c["severity_weight"]) if c else 1


def group_of(code: str) -> str | None:
    c = category_meta(code)
    return c["group"] if c else None


def is_cognizable(code: str) -> bool | None:
    c = category_meta(code)
    return c.get("is_cognizable") if c else None


# --------------------------------------------------------------------------- #
# Tiny JSON-Schema validator (same subset as the Phase 0 validate.mjs)
# --------------------------------------------------------------------------- #
_PY_TYPES = {
    "string": str,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _match_type(t: str, v) -> bool:
    if t == "null":
        return v is None
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _PY_TYPES.get(t, object))


def validate(schema_obj: dict, obj: dict, path: str = "row") -> list[str]:
    errs: list[str] = []
    props = schema_obj.get("properties", {})
    for req in schema_obj.get("required", []):
        if obj.get(req) is None and req not in obj:
            errs.append(f"{path}: missing required '{req}'")
    if schema_obj.get("additionalProperties") is False:
        for k in obj:
            if k not in props:
                errs.append(f"{path}: unexpected '{k}'")
    for k, spec in props.items():
        if k not in obj or obj[k] is None and "null" not in _types(spec):
            if k in obj and obj[k] is None and "null" not in _types(spec):
                errs.append(f"{path}.{k}: null not allowed")
            continue
        if obj.get(k) is None:
            continue
        v = obj[k]
        types = _types(spec)
        if types and not any(_match_type(t, v) for t in types):
            errs.append(f"{path}.{k}: bad type {v!r} (want {types})")
        if "enum" in spec and v not in spec["enum"]:
            errs.append(f"{path}.{k}: {v!r} not in enum")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if "minimum" in spec and v < spec["minimum"]:
                errs.append(f"{path}.{k}: {v} < {spec['minimum']}")
            if "maximum" in spec and v > spec["maximum"]:
                errs.append(f"{path}.{k}: {v} > {spec['maximum']}")
        if "pattern" in spec and isinstance(v, str) and not re.search(spec["pattern"], v):
            errs.append(f"{path}.{k}: {v!r} fails pattern")
    return errs


def _types(spec: dict) -> list[str]:
    t = spec.get("type")
    if t is None:
        return []
    return t if isinstance(t, list) else [t]
