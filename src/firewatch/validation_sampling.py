"""Deterministic, coverage-transparent validation sample selection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
from matplotlib.path import Path as PolygonPath

PRODUCT_FOR_SATELLITE = {
    "Aqua": "MYD14", "Terra": "MOD14", "SNPP": "VNP14IMG",
    "N20": "VJ114IMG", "N21": "VJ214IMG",
}
QUARTERS = ("Q1", "Q2", "Q3", "Q4")


def _rings_from_geometry(geometry: dict[str, Any]) -> list[list[tuple[float, float]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    rings: list[list[tuple[float, float]]] = []
    for polygon in polygons:
        if polygon and len(polygon[0]) >= 3:
            rings.append([(float(x), float(y)) for x, y in polygon[0]])
    if not rings:
        raise ValueError("Country boundary has no usable Polygon/MultiPolygon exterior ring")
    return rings


def _cmr_contains(polygons_json: str, lon: float, lat: float) -> bool:
    for ring_group in json.loads(polygons_json or "[]"):
        if not ring_group:
            continue
        values = [float(value) for value in ring_group[0].split()]
        ring = list(zip(values[::2], values[1::2]))
        if len(ring) >= 3 and PolygonPath(ring).contains_point((float(lon), float(lat))):
            return True
    return False


def _granule_candidates(
    row: Any, manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    product = PRODUCT_FOR_SATELLITE.get(str(row.satellite))
    if product is None:
        return manifest.iloc[0:0], 0
    stamp = pd.Timestamp(row.observation_datetime_utc)
    candidates = manifest.loc[
        manifest.short_name.eq(product)
        & manifest.time_start_utc.le(stamp)
        & manifest.time_end_utc.ge(stamp)
    ].copy()
    if candidates.empty:
        return candidates, 0
    candidates = candidates.loc[
        candidates.spatial_polygons.map(
            lambda polygons: _cmr_contains(polygons, row.longitude_num, row.latitude_num)
        )
    ].copy()
    if candidates.empty:
        return candidates, 0
    candidates["center_delta_seconds"] = (
        candidates.time_start_utc
        + (candidates.time_end_utc - candidates.time_start_utc) / 2
        - stamp
    ).abs().dt.total_seconds()
    nearest_delta = candidates.center_delta_seconds.min()
    nearest_acquisitions = candidates.loc[
        candidates.center_delta_seconds.eq(nearest_delta), "acquisition_id"
    ].drop_duplicates()
    # In a tie, keep each acquisition available for transparent processing-version choice.
    candidates = candidates.loc[candidates.acquisition_id.isin(nearest_acquisitions)].copy()
    return candidates, len(nearest_acquisitions)


def select_validation_sample(
    presence: pd.DataFrame,
    manifest: pd.DataFrame,
    boundary_geojson: dict[str, Any],
    *,
    seed: str = "firewatch-2025-pixel-validation-v1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select one deterministic observation per platform × quarter × candidate status.

    Candidate status means at least one cross-family candidate association exists
    under the recorded 1 km/3 h method. False means no such link was found; it is
    not a negative fire label. The returned audit includes empty and unmatched
    strata rather than hiding them.
    """
    required_presence = {
        "observation_id", "satellite", "product_code", "latitude_num", "longitude_num",
        "observation_datetime_utc", "validation_status", "candidate_cross_platform_1km_3h",
    }
    required_manifest = {
        "short_name", "producer_granule_id", "acquisition_id", "time_start_utc", "time_end_utc",
        "updated_utc", "granule_size_cmr_mb", "data_url", "browse_url", "spatial_polygons",
        "collection_version", "cmr_entry_id",
    }
    missing = sorted(required_presence - set(presence.columns))
    if missing:
        raise ValueError(f"Candidate-presence table missing fields: {missing}")
    missing = sorted(required_manifest - set(manifest.columns))
    if missing:
        raise ValueError(f"CMR manifest missing fields: {missing}")

    frame = presence.loc[
        presence.validation_status.eq("valid")
        & presence.observation_datetime_utc.notna()
        & presence.latitude_num.notna()
        & presence.longitude_num.notna()
        & presence.satellite.isin(PRODUCT_FOR_SATELLITE)
    ].copy()
    frame["observation_datetime_utc"] = pd.to_datetime(frame.observation_datetime_utc, utc=True)
    frame = frame.loc[
        frame.observation_datetime_utc.ge("2025-01-01T00:00:00Z")
        & frame.observation_datetime_utc.lt("2026-01-01T00:00:00Z")
    ].copy()
    rings = _rings_from_geometry(boundary_geojson["features"][0]["geometry"])
    coordinates = frame[["longitude_num", "latitude_num"]].to_numpy(dtype=float)
    in_country = np.zeros(len(frame), dtype=bool)
    for ring in rings:
        in_country |= PolygonPath(ring).contains_points(coordinates)
    frame = frame.loc[in_country].copy()
    frame["quarter"] = "Q" + frame.observation_datetime_utc.dt.quarter.astype(str)
    manifest = manifest.copy()
    for col in ("time_start_utc", "time_end_utc", "updated_utc"):
        manifest[col] = pd.to_datetime(manifest[col], utc=True)

    rows: list[dict[str, Any]] = []
    platforms = sorted(PRODUCT_FOR_SATELLITE)
    for quarter in QUARTERS:
        for satellite in platforms:
            for is_candidate in (True, False):
                stratum = frame.loc[
                    frame.quarter.eq(quarter)
                    & frame.satellite.eq(satellite)
                    & frame.candidate_cross_platform_1km_3h.eq(is_candidate)
                ].copy()
                stratum["_rank"] = stratum.observation_id.map(
                    lambda value: hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()
                )
                stratum = stratum.sort_values(["_rank", "observation_id"], kind="stable")
                base = {
                    "quarter": quarter,
                    "satellite": satellite,
                    "short_name": PRODUCT_FOR_SATELLITE[satellite],
                    "cross_platform_candidate": is_candidate,
                    "stratum_frame_size_cameroon": len(stratum),
                    "sample_seed": seed,
                }
                if stratum.empty:
                    rows.append({**base, "selection_status": "empty_stratum"})
                    continue

                chosen = None
                chosen_granules = None
                attempted = 0
                first_row = next(stratum.itertuples(index=False))
                first_granules = None
                first_acquisition_count = 0
                for candidate_row in stratum.itertuples(index=False):
                    attempted += 1
                    granules, acquisition_count = _granule_candidates(candidate_row, manifest)
                    if first_granules is None:
                        first_granules = (candidate_row, granules, acquisition_count)
                    if not granules.empty:
                        chosen = candidate_row
                        chosen_granules = granules
                        first_acquisition_count = acquisition_count
                        break
                if chosen is None:
                    chosen, chosen_granules, first_acquisition_count = first_granules
                    rows.append({
                        **base,
                        "selection_status": "no_cmr_time_polygon_match",
                        "selection_attempts": attempted,
                        "observation_id": chosen.observation_id,
                        "observation_time_utc": chosen.observation_datetime_utc.isoformat(),
                        "latitude": float(chosen.latitude_num), "longitude": float(chosen.longitude_num),
                        "cmr_acquisition_candidates_at_best_time": first_acquisition_count,
                    })
                    continue

                chosen_granules = chosen_granules.sort_values(
                    ["acquisition_id", "updated_utc", "producer_granule_id"], kind="stable"
                )
                selected = chosen_granules.iloc[-1]
                variants = int(chosen_granules.acquisition_id.eq(selected.acquisition_id).sum())
                rows.append({
                    **base,
                    "selection_status": "matched",
                    "selection_attempts": attempted,
                    "observation_id": chosen.observation_id,
                    "product_code": chosen.product_code,
                    "observation_time_utc": chosen.observation_datetime_utc.isoformat(),
                    "latitude": float(chosen.latitude_num), "longitude": float(chosen.longitude_num),
                    "cmr_acquisition_candidates_at_best_time": first_acquisition_count,
                    "cmr_entry_id": selected.cmr_entry_id,
                    "platform": selected.get("platform", chosen.satellite),
                    "producer_granule_id": selected.producer_granule_id,
                    "acquisition_id": selected.acquisition_id,
                    "collection_version": selected.collection_version,
                    "granule_start_utc": selected.time_start_utc.isoformat(),
                    "granule_end_utc": selected.time_end_utc.isoformat(),
                    "updated_utc": selected.updated_utc.isoformat(),
                    "granule_center_delta_seconds": float(selected.center_delta_seconds),
                    "reprocessing_variants_for_acquisition": variants,
                    "granule_size_cmr_mb": float(selected.granule_size_cmr_mb),
                    "data_url": selected.data_url,
                    "browse_url": selected.browse_url,
                    "spatial_polygons": selected.spatial_polygons,
                })
    sample = pd.DataFrame(rows)
    audit = sample.groupby(["quarter", "satellite", "cross_platform_candidate", "selection_status"], dropna=False).size().rename("strata_count").reset_index()
    return sample, audit
