"""Transparent spatial-temporal candidate links between FIRMS observations."""

from __future__ import annotations

from hashlib import sha256
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

EARTH_RADIUS_KM = 6371.0088
ASSOCIATION_METHOD_VERSION = "candidate-links-0.1.0"
VIIRS_PRODUCTS = {"SV-C2", "J1V-C2", "J2V-C2"}


def _unit_sphere(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    lat = np.deg2rad(latitude)
    lon = np.deg2rad(longitude)
    cos_lat = np.cos(lat)
    return np.column_stack((cos_lat * np.cos(lon), cos_lat * np.sin(lon), np.sin(lat)))


def _great_circle_km(lat_a, lon_a, lat_b, lon_b) -> np.ndarray:
    lat_a = np.deg2rad(lat_a)
    lat_b = np.deg2rad(lat_b)
    delta_lat = lat_b - lat_a
    delta_lon = np.deg2rad(lon_b - lon_a)
    haversine = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat_a) * np.cos(lat_b) * np.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(haversine, 0, 1)))


def _platform_family(product_code: str) -> str:
    return "VIIRS" if product_code in VIIRS_PRODUCTS else "MODIS" if product_code == "M-C61" else "unknown"


def find_candidate_links(
    observations: pd.DataFrame,
    *,
    max_distance_km: float = 5.0,
    max_time_delta_hours: float = 12.0,
) -> pd.DataFrame:
    """Find cross-platform observation pairs within configured space/time bounds.

    Links are possible associations, not deduplications, event clusters, or
    probabilities. Raw observations remain untouched. The caller is expected
    to pass normalized observations and select a study period first.
    """
    if max_distance_km <= 0 or max_time_delta_hours <= 0:
        raise ValueError("Distance and time limits must be positive")

    required = {
        "observation_id",
        "satellite",
        "product_code",
        "latitude_num",
        "longitude_num",
        "observation_datetime_utc",
        "validation_status",
    }
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError(f"Normalized observations missing fields: {missing}")

    eligible = observations.loc[
        observations["validation_status"].eq("valid")
        & observations["latitude_num"].notna()
        & observations["longitude_num"].notna()
        & observations["observation_datetime_utc"].notna()
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    eligible["_day"] = eligible["observation_datetime_utc"].dt.floor("D")
    grouped: dict[tuple[str, pd.Timestamp], pd.DataFrame] = {
        (str(platform), day): group.reset_index(drop=True)
        for (platform, day), group in eligible.groupby(["satellite", "_day"], sort=True)
    }
    platforms = sorted(eligible["satellite"].dropna().astype(str).unique())
    max_time_seconds = max_time_delta_hours * 3600
    chord_radius = 2 * np.sin((max_distance_km / EARTH_RADIUS_KM) / 2)
    rows: list[pd.DataFrame] = []

    # Compare each platform pair once. The ±1 day search catches valid matches
    # around UTC midnight; the actual time threshold decides whether to retain.
    for platform_a, platform_b in combinations(platforms, 2):
        day_a_values = sorted(day for platform, day in grouped if platform == platform_a)
        for day_a in day_a_values:
            frame_a = grouped[(platform_a, day_a)]
            for offset in (-1, 0, 1):
                day_b = day_a + pd.Timedelta(days=offset)
                frame_b = grouped.get((platform_b, day_b))
                if frame_b is None or frame_a.empty or frame_b.empty:
                    continue

                coords_a = _unit_sphere(
                    frame_a["latitude_num"].to_numpy(dtype=float),
                    frame_a["longitude_num"].to_numpy(dtype=float),
                )
                coords_b = _unit_sphere(
                    frame_b["latitude_num"].to_numpy(dtype=float),
                    frame_b["longitude_num"].to_numpy(dtype=float),
                )
                neighbor_lists = cKDTree(coords_a).query_ball_tree(
                    cKDTree(coords_b), r=chord_radius
                )
                pair_rows = [
                    (index_a, index_b)
                    for index_a, neighbors in enumerate(neighbor_lists)
                    for index_b in neighbors
                ]
                if not pair_rows:
                    continue

                pair_array = np.asarray(pair_rows, dtype=np.int64)
                ia, ib = pair_array[:, 0], pair_array[:, 1]
                time_a = frame_a["observation_datetime_utc"].array.asi8[ia]
                time_b = frame_b["observation_datetime_utc"].array.asi8[ib]
                delta_seconds = np.abs(time_a - time_b) / 1_000_000_000
                within_time = delta_seconds <= max_time_seconds
                if not within_time.any():
                    continue
                ia, ib = ia[within_time], ib[within_time]
                delta_seconds = delta_seconds[within_time]

                distance = _great_circle_km(
                    frame_a.iloc[ia]["latitude_num"].to_numpy(dtype=float),
                    frame_a.iloc[ia]["longitude_num"].to_numpy(dtype=float),
                    frame_b.iloc[ib]["latitude_num"].to_numpy(dtype=float),
                    frame_b.iloc[ib]["longitude_num"].to_numpy(dtype=float),
                )
                a = frame_a.iloc[ia].reset_index(drop=True)
                b = frame_b.iloc[ib].reset_index(drop=True)
                platform_family_a = a["product_code"].map(_platform_family)
                platform_family_b = b["product_code"].map(_platform_family)
                link_family = np.where(
                    platform_family_a.eq(platform_family_b),
                    platform_family_a + "-platform",
                    "MODIS-VIIRS",
                )
                rows.append(
                    pd.DataFrame(
                        {
                            "left_observation_id": a["observation_id"].astype(str),
                            "right_observation_id": b["observation_id"].astype(str),
                            "left_satellite": a["satellite"].astype(str),
                            "right_satellite": b["satellite"].astype(str),
                            "left_product_code": a["product_code"].astype(str),
                            "right_product_code": b["product_code"].astype(str),
                            "left_latitude": a["latitude_num"].to_numpy(dtype=float),
                            "left_longitude": a["longitude_num"].to_numpy(dtype=float),
                            "right_latitude": b["latitude_num"].to_numpy(dtype=float),
                            "right_longitude": b["longitude_num"].to_numpy(dtype=float),
                            "left_datetime_utc": a["observation_datetime_utc"].to_numpy(),
                            "right_datetime_utc": b["observation_datetime_utc"].to_numpy(),
                            "distance_km": distance,
                            "time_difference_minutes": delta_seconds / 60,
                            "link_family": link_family,
                            "max_distance_km": max_distance_km,
                            "max_time_delta_hours": max_time_delta_hours,
                            "method_version": ASSOCIATION_METHOD_VERSION,
                        }
                    )
                )

    if not rows:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)
    output = pd.concat(rows, ignore_index=True)
    output["candidate_link_id"] = output.apply(
        lambda row: sha256(
            f"{row.left_observation_id}:{row.right_observation_id}:"
            f"{max_distance_km}:{max_time_delta_hours}:{ASSOCIATION_METHOD_VERSION}".encode("utf-8")
        ).hexdigest(),
        axis=1,
    )
    output = output.drop_duplicates(
        subset=["left_observation_id", "right_observation_id"], keep="first"
    )
    return output[_OUTPUT_COLUMNS]


_OUTPUT_COLUMNS = [
    "candidate_link_id",
    "left_observation_id",
    "right_observation_id",
    "left_satellite",
    "right_satellite",
    "left_product_code",
    "right_product_code",
    "left_latitude",
    "left_longitude",
    "right_latitude",
    "right_longitude",
    "left_datetime_utc",
    "right_datetime_utc",
    "distance_km",
    "time_difference_minutes",
    "link_family",
    "max_distance_km",
    "max_time_delta_hours",
    "method_version",
]
