"""Chunked cross-sensor geolocation and paired fire-mask coverage checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from pyhdf.SD import SD, SDC

EARTH_RADIUS_KM = 6371.0088
MODIS_MASK_LABELS = {
    0: "missing_input_data", 1: "not_processed_obsolete",
    2: "not_processed_obsolete", 3: "water", 4: "cloud",
    5: "clear_land", 6: "unknown",
    7: "fire_low_confidence", 8: "fire_nominal_confidence",
    9: "fire_high_confidence",
}
VIIRS_MASK_LABELS = {
    0: "not_processed_nonzero_qf", 1: "bowtie", 2: "glint",
    3: "water", 4: "cloud", 5: "clear_land", 6: "unclassified",
    7: "fire_low_confidence", 8: "fire_nominal_confidence",
    9: "fire_high_confidence",
}


class _HDF4ArrayAdapter:
    """Expose pyhdf's start/count reads through a sliceable, shape-aware wrapper."""

    def __init__(self, sds: Any):
        self.sds = sds
        self.shape = tuple(int(x) for x in sds.info()[2])

    def __getitem__(self, key: tuple[slice, slice]) -> np.ndarray:
        row_slice, col_slice = key
        row_start, row_stop, _ = row_slice.indices(self.shape[0])
        col_start, col_stop, _ = col_slice.indices(self.shape[1])
        return self.sds.get(
            start=(row_start, col_start),
            count=(row_stop - row_start, col_stop - col_start),
        )


def sha256_file(path: str | Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def _distance_km(lat: np.ndarray, lon: np.ndarray, target_lat: float, target_lon: float) -> np.ndarray:
    lat1 = np.radians(lat.astype(np.float64, copy=False))
    lon1 = np.radians(lon.astype(np.float64, copy=False))
    lat2, lon2 = np.radians(target_lat), np.radians(target_lon)
    dlat, dlon = lat1 - lat2, lon1 - lon2
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _nearest_in_chunks(
    lat_ds: Any, lon_ds: Any, target_lat: float, target_lon: float,
    *, chunk_rows: int, fill_value: float,
) -> dict[str, Any]:
    rows, cols = lat_ds.shape
    best_distance = float("inf")
    best_row = best_col = -1
    for start in range(0, rows, chunk_rows):
        stop = min(start + chunk_rows, rows)
        lat = np.asarray(lat_ds[start:stop, :])
        lon = np.asarray(lon_ds[start:stop, :])
        valid = (
            np.isfinite(lat) & np.isfinite(lon)
            & (lat != fill_value) & (lon != fill_value)
            & (lat >= -90) & (lat <= 90) & (lon >= -180) & (lon <= 180)
        )
        if not valid.any():
            continue
        distances = _distance_km(lat, lon, target_lat, target_lon)
        distances[~valid] = np.inf
        flat = int(np.argmin(distances))
        local_row, col = np.unravel_index(flat, distances.shape)
        distance = float(distances[local_row, col])
        if distance < best_distance:
            best_distance = distance
            best_row, best_col = start + int(local_row), int(col)
    if best_row < 0:
        raise ValueError("No valid geolocation pixels were found")
    return {
        "row": best_row, "column": best_col,
        "distance_km": best_distance, "grid_shape": (rows, cols),
        "target_latitude": float(target_lat), "target_longitude": float(target_lon),
    }


def nearest_modis_geolocation(
    path: str | Path, target_lat: float, target_lon: float, *, chunk_rows: int = 128,
) -> dict[str, Any]:
    file = SD(str(path), SDC.READ)
    try:
        lat_sds, lon_sds = file.select("Latitude"), file.select("Longitude")
        result = _nearest_in_chunks(
            _HDF4ArrayAdapter(lat_sds), _HDF4ArrayAdapter(lon_sds), target_lat, target_lon, chunk_rows=chunk_rows,
            fill_value=float(lat_sds.attributes().get("_FillValue", -999.0)),
        )
        gflags = int(file.select("gflags")[result["row"]:result["row"] + 1, result["column"]:result["column"] + 1][0, 0])
        result["geolocation_product"] = Path(path).name
        result["gflags"] = gflags
        result["gflags_invalid_input"] = bool(gflags & (1 << 7))
        result["gflags_no_ellipsoid_intersection"] = bool(gflags & (1 << 6))
        result["gflags_no_valid_terrain"] = bool(gflags & (1 << 5))
        result["gflags_dem_missing_or_inferior"] = bool(gflags & (1 << 4))
        result["gflags_invalid_sensor_range"] = bool(gflags & (1 << 3))
        result["gflags_near_earth_limb"] = bool(gflags & (1 << 2))
        result["geolocation_quality"] = "MOD03 raw gflags retained and decoded per NASA Collection 6.1 file specification"
        return result
    finally:
        file.end()


def nearest_viirs_geolocation(
    path: str | Path, target_lat: float, target_lon: float, *, chunk_rows: int = 128,
) -> dict[str, Any]:
    with h5py.File(path, "r") as file:
        geo = file["geolocation_data"]
        lat_ds, lon_ds = geo["latitude"], geo["longitude"]
        quality_ds = geo.get("quality_flag")
        result = _nearest_in_chunks(
            lat_ds, lon_ds, target_lat, target_lon, chunk_rows=chunk_rows,
            fill_value=float(np.asarray(lat_ds.attrs.get("_FillValue", -999.9)).reshape(-1)[0]),
        )
        row, col = result["row"], result["column"]
        qflag = int(quality_ds[row, col]) if quality_ds is not None else None
        result.update({
            "geolocation_product": Path(path).name,
            "quality_flag": qflag,
            "quality_flag_meanings": "Input_invalid=1, Pointing_bad=2, Terrain_bad=4, SolarAngle_bad=8",
            "geolocation_quality": "valid coordinate; inspect quality_flag bit mask separately" if qflag is not None else "quality flag unavailable",
        })
        return result


def paired_mask_class(path: str | Path, row: int, column: int, *, format: str) -> dict[str, Any]:
    if format == "hdf4":
        file = SD(str(path), SDC.READ)
        try:
            sds = file.select("fire mask")
            shape = tuple(int(x) for x in sds.info()[2])
            legend = sds.attributes().get("legend")
            if not (0 <= row < shape[0] and 0 <= column < shape[1]):
                raise IndexError("Geolocation index does not fit paired MODIS fire-mask grid")
            value = int(sds[row:row + 1, column:column + 1][0, 0])
        finally:
            file.end()
    elif format == "hdf5":
        with h5py.File(path, "r") as file:
            sds = file["fire mask"]
            shape = tuple(int(x) for x in sds.shape)
            legend = sds.attrs.get("legend")
            if not (0 <= row < shape[0] and 0 <= column < shape[1]):
                raise IndexError("Geolocation index does not fit paired VIIRS fire-mask grid")
            value = int(sds[row, column])
    else:
        raise ValueError("format must be 'hdf4' or 'hdf5'")
    labels = MODIS_MASK_LABELS if format == "hdf4" else VIIRS_MASK_LABELS
    if isinstance(legend, bytes):
        legend = legend.decode("utf-8", errors="replace")
    elif isinstance(legend, np.ndarray):
        legend = "\n".join(
            item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
            for item in legend.reshape(-1)
        )
    return {
        "fire_mask_class": value, "fire_mask_label": labels.get(value, "invalid_class"),
        "fire_mask_shape": shape, "fire_mask_legend": legend,
    }


def paired_modis_point(
    geolocation_path: str | Path, mask_path: str | Path,
    target_lat: float, target_lon: float,
) -> dict[str, Any]:
    result = nearest_modis_geolocation(geolocation_path, target_lat, target_lon)
    mask = paired_mask_class(mask_path, result["row"], result["column"], format="hdf4")
    if tuple(result["grid_shape"]) != tuple(mask["fire_mask_shape"]):
        raise ValueError("MODIS geolocation and active-fire mask dimensions differ")
    return {**result, **mask}


def paired_viirs_point(
    geolocation_path: str | Path, mask_path: str | Path,
    target_lat: float, target_lon: float,
) -> dict[str, Any]:
    result = nearest_viirs_geolocation(geolocation_path, target_lat, target_lon)
    mask = paired_mask_class(mask_path, result["row"], result["column"], format="hdf5")
    if tuple(result["grid_shape"]) != tuple(mask["fire_mask_shape"]):
        raise ValueError("VIIRS geolocation and active-fire mask dimensions differ")
    qflag = result.get("quality_flag")
    result["quality_flag_usable"] = qflag is not None and (qflag & 0b0111) == 0
    return {**result, **mask}
