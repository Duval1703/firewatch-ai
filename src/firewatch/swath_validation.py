"""Inspect whether FIRMS point detections correspond to L2 fire-pixel records."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import h5py
import numpy as np
from pyhdf.SD import SD, SDC


def great_circle_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorized haversine distance from one point to arrays of points."""
    lat1_rad = np.deg2rad(float(lat1))
    lat2_rad = np.deg2rad(np.asarray(lat2, dtype=float))
    dlat = lat2_rad - lat1_rad
    dlon = np.deg2rad(np.asarray(lon2, dtype=float) - float(lon1))
    hav = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))


def _pixel_match(
    *, lat: np.ndarray, lon: np.ndarray, observation_latitude: float,
    observation_longitude: float, confidence: np.ndarray, frp_mw: np.ndarray,
    line: np.ndarray, sample: np.ndarray, fire_mask: np.ndarray,
) -> dict[str, Any]:
    distances = great_circle_km(observation_latitude, observation_longitude, lat, lon)
    if distances.size == 0:
        raise ValueError("Granule contains no active-fire pixel records")
    i = int(np.nanargmin(distances))
    row, col = int(line[i]), int(sample[i])
    if row < 0 or col < 0 or row >= fire_mask.shape[0] or col >= fire_mask.shape[1]:
        raise ValueError(f"Active-fire line/sample index is outside fire-mask shape {fire_mask.shape}")
    return {
        "nearest_pixel_index": i,
        "distance_km": float(distances[i]),
        "fire_pixel_latitude": float(lat[i]),
        "fire_pixel_longitude": float(lon[i]),
        "confidence_code_or_percent": int(confidence[i]),
        "frp_mw": float(frp_mw[i]),
        "line": row,
        "sample": col,
        "fire_mask_class": int(fire_mask[row, col]),
        "fire_mask_shape": tuple(int(x) for x in fire_mask.shape),
        "active_fire_pixel_count": int(len(lat)),
    }


def _core_metadata_value(core: str, object_name: str) -> str | None:
    match = re.search(
        rf"OBJECT\s*=\s*{re.escape(object_name)}\s+NUM_VAL\s*=\s*\d+\s+VALUE\s*=\s*\"([^\"]+)\"",
        core,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else None


def inspect_viirs_granule(
    path: str | Path, *, observation_latitude: float, observation_longitude: float,
) -> dict[str, Any]:
    """Match a CSV coordinate to the closest VIIRS fire-pixel record and mask cell."""
    with h5py.File(path, "r") as f:
        required = ["FP_latitude", "FP_longitude", "FP_confidence", "FP_power", "FP_line", "FP_sample", "fire mask"]
        missing = [name for name in required if name not in f]
        if missing:
            raise ValueError(f"VIIRS granule lacks required datasets: {missing}")
        attrs = f.attrs
        def scalar(name: str) -> Any:
            value = attrs.get(name)
            if isinstance(value, np.ndarray):
                value = value.reshape(-1)[0]
            if isinstance(value, (bytes, np.bytes_)):
                return value.decode("utf-8", errors="replace")
            return value.item() if isinstance(value, np.generic) else value
        legend = f["fire mask"].attrs.get("legend")
        if isinstance(legend, np.ndarray):
            legend = legend.reshape(-1)[0]
        if isinstance(legend, (bytes, np.bytes_)):
            legend = legend.decode("utf-8", errors="replace")
        match = _pixel_match(
            lat=f["FP_latitude"][...], lon=f["FP_longitude"][...],
            observation_latitude=observation_latitude, observation_longitude=observation_longitude,
            confidence=f["FP_confidence"][...], frp_mw=f["FP_power"][...],
            line=f["FP_line"][...], sample=f["FP_sample"][...], fire_mask=f["fire mask"],
        )
        return {
            "product": scalar("ShortName"), "satellite": scalar("PlatformShortName"),
            "collection_version": scalar("VersionID"),
            "process_version": scalar("ProcessVersionNumber"),
            "granule_id": scalar("LocalGranuleID"),
            "start_time": scalar("StartTime"), "end_time": scalar("EndTime"),
            "confidence_semantics": "Categorical code: 7 low, 8 nominal, 9 high",
            "fire_mask_legend": legend,
            **match,
        }


def inspect_modis_granule(
    path: str | Path, *, observation_latitude: float, observation_longitude: float,
) -> dict[str, Any]:
    """Match a CSV coordinate to the closest MODIS fire-pixel record and mask cell."""
    f = SD(str(path), SDC.READ)
    try:
        attrs = f.attributes()
        datasets = f.datasets()
        core = attrs.get("CoreMetadata.0", "")
        required = ["FP_latitude", "FP_longitude", "FP_confidence", "FP_power", "FP_line", "FP_sample", "fire mask"]
        missing = [name for name in required if name not in datasets]
        if missing:
            raise ValueError(f"MODIS granule lacks required SDS datasets: {missing}")
        mask_sds = f.select("fire mask")
        mask = mask_sds.get()
        match = _pixel_match(
            lat=f.select("FP_latitude").get(), lon=f.select("FP_longitude").get(),
            observation_latitude=observation_latitude, observation_longitude=observation_longitude,
            confidence=f.select("FP_confidence").get(), frp_mw=f.select("FP_power").get(),
            line=f.select("FP_line").get(), sample=f.select("FP_sample").get(), fire_mask=mask,
        )
        return {
            "product": "MYD14", "satellite": attrs.get("Satellite"),
            "collection_version": "61",
            "process_version": attrs.get("ProcessVersionNumber"),
            "granule_id": _core_metadata_value(core, "LOCALGRANULEID") or Path(path).name,
            "start_time": "T".join(filter(None, [
                _core_metadata_value(core, "RANGEBEGINNINGDATE"),
                _core_metadata_value(core, "RANGEBEGINNINGTIME"),
            ])),
            "end_time": "T".join(filter(None, [
                _core_metadata_value(core, "RANGEENDINGDATE"),
                _core_metadata_value(core, "RANGEENDINGTIME"),
            ])),
            "confidence_semantics": "Percent (0–100); fire-mask class carries low/nominal/high category",
            "fire_mask_legend": mask_sds.attributes().get("legend"),
            "file_attributes": {k: attrs.get(k) for k in ["FirePix", "MissingPix", "DayPix"]},
            **match,
        }
    finally:
        f.end()


def summarize_match(result: dict[str, Any]) -> str:
    """Return neutral wording that does not overstate event identity."""
    return (
        f"{result['product']} nearest L2 fire-pixel record is {result['distance_km']:.4f} km "
        f"from the FIRMS point; mask class {result['fire_mask_class']}, "
        f"FRP {result['frp_mw']:.3f} MW."
    )
