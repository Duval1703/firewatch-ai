"""Discover and record NASA CMR granule metadata without downloading data."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
PAGE_SIZE = 2000
DATA_REL = "http://esipfed.org/ns/fedsearch/1.1/data#"
BROWSE_REL = "http://esipfed.org/ns/fedsearch/1.1/browse#"

# Standard, science-quality Level-2 swaths corresponding to the FIRMS sources.
PRODUCTS = (
    {"platform": "SNPP", "short_name": "VNP14IMG", "version": "002"},
    {"platform": "N20", "short_name": "VJ114IMG", "version": "002"},
    {"platform": "N21", "short_name": "VJ214IMG", "version": "002"},
    {"platform": "Terra", "short_name": "MOD14", "version": "061"},
    {"platform": "Aqua", "short_name": "MYD14", "version": "061"},
)

MANIFEST_COLUMNS = [
    "platform", "short_name", "collection_version", "cmr_entry_id",
    "collection_concept_id", "producer_granule_id", "acquisition_id",
    "dataset_id", "data_center", "time_start_utc", "time_end_utc",
    "updated_utc", "day_night_flag", "granule_size_cmr_mb",
    "online_access", "spatial_polygons", "data_url", "browse_url",
    "query_start_utc", "query_end_utc", "query_bbox_wsen",
]


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Parse and validate a CMR west,south,east,north bounding box."""
    try:
        west, south, east, north = (float(part.strip()) for part in value.split(","))
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox must be west,south,east,north") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox coordinates must be valid and ordered west,south,east,north")
    return west, south, east, north


def build_query_url(
    *, short_name: str, version: str, start: date, end: date,
    bbox: tuple[float, float, float, float], page_num: int = 1,
) -> str:
    if start > end:
        raise ValueError("start date must be on or before end date")
    west, south, east, north = bbox
    params = {
        "short_name": short_name,
        "version": version,
        "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
        "bounding_box": f"{west:g},{south:g},{east:g},{north:g}",
        "page_size": str(PAGE_SIZE),
        "page_num": str(page_num),
    }
    return f"{CMR_GRANULES_URL}?{urlencode(params)}"


def _select_link(links: list[dict[str, Any]], relation: str) -> str | None:
    candidates = [
        link for link in links
        if link.get("rel") == relation
        and not link.get("inherited", False)
        and str(link.get("href", "")).startswith("https://")
    ]
    if relation == DATA_REL:
        candidates = [
            link for link in candidates
            if "search.earthdata.nasa.gov/search/granules" not in link.get("href", "")
        ]
    if not candidates:
        return None
    return candidates[0].get("href")


def acquisition_id(producer_granule_id: str) -> str:
    """Remove a 13-digit processing timestamp while retaining acquisition identity."""
    return re.sub(r"\.\d{13}$", "", producer_granule_id)


def entry_to_row(
    entry: dict[str, Any], product: dict[str, str], *,
    query_start: date, query_end: date,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    granule_id = str(entry.get("producer_granule_id") or entry.get("title") or "")
    return {
        "platform": product["platform"],
        "short_name": product["short_name"],
        "collection_version": product["version"],
        "cmr_entry_id": entry.get("id"),
        "collection_concept_id": entry.get("collection_concept_id"),
        "producer_granule_id": granule_id,
        "acquisition_id": acquisition_id(granule_id),
        "dataset_id": entry.get("dataset_id"),
        "data_center": entry.get("data_center"),
        "time_start_utc": entry.get("time_start"),
        "time_end_utc": entry.get("time_end"),
        "updated_utc": entry.get("updated"),
        "day_night_flag": entry.get("day_night_flag"),
        "granule_size_cmr_mb": entry.get("granule_size"),
        "online_access": entry.get("online_access_flag"),
        # Preserve CMR's original polygon representation; do not imply it is a pixel mask.
        "spatial_polygons": json.dumps(entry.get("polygons", []), separators=(",", ":")),
        "data_url": _select_link(entry.get("links", []), DATA_REL),
        "browse_url": _select_link(entry.get("links", []), BROWSE_REL),
        "query_start_utc": query_start.isoformat(),
        "query_end_utc": query_end.isoformat(),
        "query_bbox_wsen": ",".join(f"{part:g}" for part in bbox),
    }


def fetch_product_entries(
    product: dict[str, str], *, start: date, end: date,
    bbox: tuple[float, float, float, float], timeout: int = 60,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    """Fetch every CMR result page for one collection; no granule files are fetched."""
    entries: list[dict[str, Any]] = []
    urls: list[str] = []
    feed_updated: str | None = None
    page_num = 1
    while True:
        url = build_query_url(
            short_name=product["short_name"], version=product["version"],
            start=start, end=end, bbox=bbox, page_num=page_num,
        )
        urls.append(url)
        request = Request(url, headers={"User-Agent": "FIREWATCH-AI/0.1 (NASA CMR metadata manifest)"})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"CMR metadata request failed for {product['short_name']} page {page_num}: {exc}"
            ) from exc
        feed = payload.get("feed", {})
        page_entries = feed.get("entry", [])
        feed_updated = feed.get("updated", feed_updated)
        entries.extend(page_entries)
        if len(page_entries) < PAGE_SIZE:
            break
        page_num += 1
    return entries, urls, feed_updated


def build_manifest(
    *, start: date, end: date,
    bbox: tuple[float, float, float, float],
    products: tuple[dict[str, str], ...] = PRODUCTS,
    timeout: int = 60,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if start > end:
        raise ValueError("start date must be on or before end date")
    rows: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    for product in products:
        entries, urls, feed_updated = fetch_product_entries(
            product, start=start, end=end, bbox=bbox, timeout=timeout
        )
        rows.extend(
            entry_to_row(entry, product, query_start=start, query_end=end, bbox=bbox)
            for entry in entries
        )
        queries.append({
            "platform": product["platform"],
            "short_name": product["short_name"],
            "collection_version": product["version"],
            "result_entries": len(entries),
            "unique_acquisition_ids": len({
                acquisition_id(str(e.get("producer_granule_id") or e.get("title") or ""))
                for e in entries
            }),
            "cmr_feed_updated": feed_updated,
            "request_urls": urls,
        })
    frame = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    if not frame.empty:
        frame = frame.sort_values(
            ["platform", "time_start_utc", "producer_granule_id"], kind="stable"
        ).reset_index(drop=True)
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "cmr_endpoint": CMR_GRANULES_URL,
        "query_start_utc": start.isoformat(),
        "query_end_utc": end.isoformat(),
        "query_bbox_wsen": ",".join(f"{part:g}" for part in bbox),
        "page_size": PAGE_SIZE,
        "result_entries": len(frame),
        "granule_files_downloaded": 0,
        "queries": queries,
        "limitations": [
            "CMR granule bounding polygons are catalog extents, not pixel-level observation masks.",
            "Reprocessing variants are retained as separate manifest rows.",
            "A data URL records access metadata only; this command does not retrieve granule contents.",
        ],
    }
    return frame, metadata


def write_manifest(frame: pd.DataFrame, metadata: dict[str, Any], output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    metadata["manifest_csv"] = output_path.name
    metadata["manifest_rows"] = len(frame)
    metadata["manifest_sha256"] = sha256(output_path.read_bytes()).hexdigest()
    metadata_path = output_path.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2025-10-01", help="Inclusive UTC date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-10-31", help="Inclusive UTC date (YYYY-MM-DD)")
    parser.add_argument("--bbox", default="8,1,17,14", help="west,south,east,north")
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/reference/cmr_manifest_2025-10.csv"),
        help="CSV manifest path; companion .metadata.json is written beside it",
    )
    args = parser.parse_args()
    try:
        start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        bbox = parse_bbox(args.bbox)
        frame, metadata = build_manifest(start=start, end=end, bbox=bbox)
        write_manifest(frame, metadata, args.output)
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Wrote {len(frame):,} CMR metadata entries to {args.output}")
    print(f"No granule data downloaded. Metadata: {args.output.with_suffix('.metadata.json')}")


if __name__ == "__main__":
    main()
