"""Resolve exact geolocation inputs referenced by MODIS/VIIRS fire granules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import h5py
from pyhdf.SD import SD, SDC

from .cmr_links import BROWSE_REL, DATA_REL, select_link as _select_link

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
CMR_VERSION_BY_PRODUCT = {
    "MOD03": "6.1", "MYD03": "6.1", "VNP03IMG": "2",
    "VJ103IMG": "2.1", "VJ203IMG": "2.1",
}
def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "reshape"):
        value = value.reshape(-1)[0]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "item"):
        value = value.item()
    return str(value)


def geolocation_filename_from_modis_attributes(attributes: dict[str, Any]) -> str:
    """Extract the exact MOD03/MYD03 input named by a MOD14/MYD14 HDF4 granule."""
    keys = [key for key in attributes if str(key).endswith("03 input file")]
    if len(keys) != 1:
        raise ValueError(f"Expected one MODIS '*03 input file' metadata attribute; found {keys}")
    filename = Path(str(attributes[keys[0]]).replace("\\", "/")).name
    if not filename.startswith(("MOD03.", "MYD03.")):
        raise ValueError(f"Unexpected MODIS geolocation input filename: {filename}")
    return filename


def geolocation_filename_from_viirs_attributes(attributes: Any) -> str:
    """Extract the exact VIIRS image geolocation input filename from HDF5 attrs."""
    key = next((name for name in attributes if str(name).endswith("03IMG")), None)
    if key is None:
        raise ValueError("VIIRS fire granule has no *03IMG geolocation input attribute")
    filename = Path(_decode(attributes[key]).replace("\\", "/")).name
    if not filename.startswith(("VNP03IMG.", "VJ103IMG.", "VJ203IMG.")):
        raise ValueError(f"Unexpected VIIRS geolocation input filename: {filename}")
    return filename


def extract_geolocation_reference(l2_path: str | Path) -> dict[str, str]:
    """Read the source-native exact geolocation input reference from an L2 fire file."""
    path = Path(l2_path)
    if path.suffix.lower() == ".hdf":
        f = SD(str(path), SDC.READ)
        try:
            filename = geolocation_filename_from_modis_attributes(f.attributes())
        finally:
            f.end()
    elif path.suffix.lower() == ".nc":
        with h5py.File(path, "r") as f:
            filename = geolocation_filename_from_viirs_attributes(f.attrs)
    else:
        raise ValueError(f"Unsupported L2 fire granule suffix: {path.suffix}")
    short_name = filename.split(".", 1)[0]
    if short_name not in CMR_VERSION_BY_PRODUCT:
        raise ValueError(f"No CMR version mapping for geolocation product {short_name}")
    return {
        "source_l2_filename": path.name,
        "geolocation_short_name": short_name,
        "geolocation_granule_id": filename,
        "cmr_version": CMR_VERSION_BY_PRODUCT[short_name],
        "file_version_segment": filename.split(".")[3],
    }


def query_exact_geolocation_manifest(
    references: list[dict[str, Any]], *, timeout: int = 60,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Query CMR for exactly the geolocation files named by L2 input metadata."""
    if not references or len(references) > 40:
        raise ValueError("Geolocation metadata query requires 1–40 exact granule references")
    rows: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    requested_by_product: dict[tuple[str, str], list[str]] = {}
    for ref in references:
        key = (str(ref["geolocation_short_name"]), str(ref["cmr_version"]))
        requested_by_product.setdefault(key, []).append(str(ref["geolocation_granule_id"]))

    entries_by_filename: dict[str, dict[str, Any]] = {}
    for (short_name, version), filenames in sorted(requested_by_product.items()):
        unique_filenames = sorted(set(filenames))
        params: list[tuple[str, str]] = [
            ("short_name", short_name), ("version", version),
            *(('producer_granule_id[]', name) for name in unique_filenames),
            ("page_size", "100"),
        ]
        url = f"{CMR_GRANULES_URL}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "FIREWATCH-AI/0.1 exact geolocation lineage query"})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"CMR exact geolocation query failed for {short_name}: {type(exc).__name__}") from exc
        entries = payload.get("feed", {}).get("entry", [])
        for entry in entries:
            filename = str(entry.get("producer_granule_id", ""))
            if filename in entries_by_filename:
                raise ValueError(f"CMR returned duplicate exact geolocation granule: {filename}")
            entries_by_filename[filename] = entry
        queries.append({
            "short_name": short_name, "cmr_version": version,
            "requested_ids": unique_filenames, "returned_entries": len(entries),
            "request_url": url,
        })

    requested_names = {str(ref["geolocation_granule_id"]) for ref in references}
    missing = sorted(requested_names - set(entries_by_filename))
    if missing:
        raise ValueError(f"CMR did not return {len(missing)} exact geolocation granule(s): {missing}")

    for ref in references:
        entry = entries_by_filename[str(ref["geolocation_granule_id"])]
        rows.append({
            **ref,
            "cmr_entry_id": entry.get("id"),
            "collection_concept_id": entry.get("collection_concept_id"),
            "cmr_collection_version": entry.get("version") or ref.get("cmr_version"),
            "time_start_utc": entry.get("time_start"),
            "time_end_utc": entry.get("time_end"),
            "updated_utc": entry.get("updated"),
            "granule_size_cmr_mb": float(entry["granule_size"]) if entry.get("granule_size") is not None else None,
            "data_url": _select_link(entry.get("links", []), DATA_REL),
            "browse_url": _select_link(entry.get("links", []), BROWSE_REL),
            "spatial_polygons": json.dumps(entry.get("polygons", []), separators=(",", ":")),
        })
    metadata = {
        "cmr_endpoint": CMR_GRANULES_URL,
        "query_type": "exact producer granule IDs extracted from selected L2 fire files' input metadata",
        "reference_count": len(references),
        "unique_geolocation_granules": len(requested_names),
        "query_groups": queries,
        "granule_files_downloaded": 0,
        "limitations": [
            "CMR metadata presence/extent is not proof of pixel-level coverage.",
            "Exact filenames are from L2 processing input attributes; collection version mapping is retained separately from filename version segment.",
        ],
    }
    return rows, metadata
