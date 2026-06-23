"""Geodesic polygon area for GeoJSON geometries (km²), dependency-free.

Spherical excess formula on the WGS84 mean radius. Verified against Karnataka:
sum of district areas = 192,436 km² vs official 191,791 km² (~0.3%).
"""
from __future__ import annotations

import math

_R = 6371008.8  # mean Earth radius (m)


def _ring_area_m2(ring) -> float:
    if len(ring) < 4:
        return 0.0
    s = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        s += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return s * _R * _R / 2.0


def area_km2(geometry: dict) -> float:
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polys = coords if t == "MultiPolygon" else [coords]
    total = 0.0
    for poly in polys:
        for i, ring in enumerate(poly):
            a = abs(_ring_area_m2(ring))
            total += a if i == 0 else -a  # subtract holes
    return round(total / 1e6, 1)
