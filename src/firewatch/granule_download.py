"""Download a small, explicitly bounded NASA granule sample plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import pandas as pd

ALLOWED_HOSTS = {
    "data.lpdaac.earthdatacloud.nasa.gov": "/lp-prod-protected/",
    "data.laadsdaac.earthdatacloud.nasa.gov": "/prod-lads/",
}
HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"
HDF4_SIGNATURE = b"\x0e\x03\x13\x01"
DEFAULT_MAX_SAMPLE_FILES = 2
HARD_MAX_SAMPLE_FILES = 40
DEFAULT_MAX_TOTAL_MB = 10.0
HARD_MAX_TOTAL_MB = 250.0
CHUNK_SIZE = 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, msg, headers, new_url):
        return None


def validate_data_url(url: str) -> str:
    parsed = urlparse(url)
    expected_prefix = ALLOWED_HOSTS.get(parsed.hostname or "")
    if parsed.scheme != "https" or expected_prefix is None:
        raise ValueError("Granule URL must use an approved HTTPS NASA Earthdata host")
    if not parsed.path.startswith(expected_prefix):
        raise ValueError("Only approved NASA science-granule paths from the sample plan are accepted")
    filename = Path(parsed.path).name
    if not filename.lower().endswith((".hdf", ".nc")):
        raise ValueError("Sample downloader accepts only HDF/NetCDF granules")
    return filename


def validate_plan(
    plan: pd.DataFrame, max_total_mb: float = DEFAULT_MAX_TOTAL_MB,
    max_files: int = DEFAULT_MAX_SAMPLE_FILES,
) -> None:
    required = {"data_url", "granule_size_cmr_mb"}
    missing = sorted(required - set(plan.columns))
    if not ({"producer_granule_id", "geolocation_granule_id"} & set(plan.columns)):
        missing.append("producer_granule_id or geolocation_granule_id")
    if missing:
        raise ValueError(f"Sample plan missing fields: {missing}")
    if max_files < 1 or max_files > HARD_MAX_SAMPLE_FILES:
        raise ValueError(f"--max-files must be between 1 and {HARD_MAX_SAMPLE_FILES}")
    if plan.empty or len(plan) > max_files:
        raise ValueError(f"Sample plan must contain between 1 and {max_files} granules")
    if max_total_mb <= 0 or max_total_mb > HARD_MAX_TOTAL_MB:
        raise ValueError(f"--max-total-mb must be positive and no greater than {HARD_MAX_TOTAL_MB:g} MB")
    for url in plan.data_url.astype(str):
        validate_data_url(url)
    filenames = [validate_data_url(url) for url in plan.data_url.astype(str)]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Sample plan contains duplicate granule filenames")
    sizes = pd.to_numeric(plan.granule_size_cmr_mb, errors="coerce")
    if sizes.isna().any() or (sizes < 0).any():
        raise ValueError("CMR-reported granule sizes must be non-negative numeric values")
    if float(sizes.sum()) > max_total_mb:
        raise ValueError(
            f"Sample plan reports {sizes.sum():.3f} MB, exceeding the {max_total_mb:.3f} MB limit"
        )


def _validate_signature(path: Path) -> None:
    with path.open("rb") as stream:
        prefix = stream.read(4096)
    suffix = path.suffix.lower()
    if suffix == ".nc" and not prefix.startswith(HDF5_SIGNATURE):
        raise ValueError(f"Downloaded NetCDF4/HDF5 file has an unexpected signature: {path.name}")
    if suffix == ".hdf":
        offsets = [0, *range(512, min(len(prefix), 4096), 512)]
        if not any(prefix[offset:offset + len(HDF4_SIGNATURE)] == HDF4_SIGNATURE for offset in offsets):
            raise ValueError(f"Downloaded HDF4 file has an unexpected signature: {path.name}")


def _open_response(url: str, token: str, timeout: int):
    """Follow redirects without forwarding the bearer token to another host."""
    opener = build_opener(_NoRedirect)
    initial_host = urlparse(url).hostname
    current_url = url
    for _ in range(6):
        headers = {"User-Agent": "FIREWATCH-AI/0.1 bounded granule pilot"}
        if urlparse(current_url).hostname == initial_host:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(current_url, headers=headers)
        try:
            return opener.open(request, timeout=timeout)
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get("Location")
                if not location:
                    raise RuntimeError(f"NASA granule redirect returned HTTP {exc.code} without a location") from None
                next_url = urljoin(current_url, location)
                parsed = urlparse(next_url)
                if parsed.scheme != "https":
                    raise RuntimeError("NASA granule redirect did not use HTTPS") from None
                current_url = next_url
                continue
            if exc.code in {401, 403}:
                raise PermissionError(
                    f"NASA rejected granule access with HTTP {exc.code}; check Earthdata token and LP DAAC authorization"
                ) from None
            raise RuntimeError(f"NASA granule request failed with HTTP {exc.code}") from None
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"NASA granule request failed: {type(exc).__name__}") from None
    raise RuntimeError("NASA granule access exceeded the redirect limit")


def _open_range_response(url: str, token: str, timeout: int, offset: int):
    """Open a byte-range request, preserving the existing cross-host token rule."""
    opener = build_opener(_NoRedirect)
    initial_host = urlparse(url).hostname
    current_url = url
    for _ in range(6):
        headers = {"User-Agent": "FIREWATCH-AI/0.1 bounded granule pilot", "Range": f"bytes={offset}-"}
        if urlparse(current_url).hostname == initial_host:
            headers["Authorization"] = f"Bearer {token}"
        try:
            return opener.open(Request(current_url, headers=headers), timeout=timeout)
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get("Location")
                if not location:
                    raise RuntimeError(f"NASA granule redirect returned HTTP {exc.code} without a location") from None
                next_url = urljoin(current_url, location)
                if urlparse(next_url).scheme != "https":
                    raise RuntimeError("NASA granule redirect did not use HTTPS") from None
                current_url = next_url
                continue
            if exc.code == 416:
                raise RuntimeError("NASA rejected the resume range; remove the .part file and retry") from None
            if exc.code in {401, 403}:
                raise PermissionError(
                    f"NASA rejected granule access with HTTP {exc.code}; check Earthdata token and LP DAAC authorization"
                ) from None
            raise RuntimeError(f"NASA granule range request failed with HTTP {exc.code}") from None
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"NASA granule range request failed: {type(exc).__name__}") from None
    raise RuntimeError("NASA granule access exceeded the redirect limit")


def download_one(
    row: Any, *, output_dir: Path, token: str,
    max_file_mb: float, timeout: int = 60,
) -> dict[str, Any]:
    url = str(row.data_url)
    filename = validate_data_url(url)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = (output_dir / filename).resolve()
    if target.parent != output_dir:
        raise ValueError("Granule output path escaped the configured staging directory")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite an existing staged granule: {filename}")
    part_path = target.with_name(target.name + ".part")
    max_bytes = int(max_file_mb * 1024 * 1024)
    digest = hashlib.sha256()
    byte_count = part_path.stat().st_size if part_path.exists() else 0
    if byte_count > max_bytes:
        raise ValueError(f"Existing partial file exceeds the per-file {max_file_mb:g} MB limit")
    if byte_count:
        with part_path.open("rb") as partial:
            while chunk := partial.read(CHUNK_SIZE):
                digest.update(chunk)
    try:
        response_opener = _open_range_response if byte_count else None
        response = response_opener(url, token, timeout, byte_count) if byte_count else _open_response(url, token, timeout)
        with response:
            if byte_count and response.status != 206:
                raise RuntimeError("NASA did not honor the resume range; remove the .part file and retry")
            if not byte_count and response.status != 200:
                raise RuntimeError(f"Granule download returned HTTP {response.status}")
            content_length = response.headers.get("Content-Length")
            content_range = response.headers.get("Content-Range")
            if byte_count:
                if not content_range or not content_range.startswith(f"bytes {byte_count}-"):
                    raise RuntimeError("NASA returned an unexpected Content-Range; partial file was preserved")
                total_text = content_range.rsplit("/", 1)[-1]
                expected_total = int(total_text) if total_text.isdigit() else None
            else:
                expected_total = int(content_length) if content_length and content_length.isdigit() else None
            if expected_total and expected_total > max_bytes:
                raise ValueError(f"Granule exceeds the per-file {max_file_mb:g} MB limit")
            with part_path.open("ab" if byte_count else "xb") as output:
                while chunk := response.read(CHUNK_SIZE):
                    byte_count += len(chunk)
                    if byte_count > max_bytes:
                        raise ValueError(f"Granule exceeded the per-file {max_file_mb:g} MB limit")
                    digest.update(chunk)
                    output.write(chunk)
        if expected_total and byte_count != expected_total:
            raise IOError(f"Granule length mismatch: expected {expected_total} bytes, received {byte_count}; partial data preserved for resume")
        _validate_signature(part_path)
        part_path.replace(target)
    except Exception as exc:
        if part_path.exists() and not (
            isinstance(exc, IOError) and "partial data preserved for resume" in str(exc)
        ):
            part_path.unlink()
        raise

    return {
        "producer_granule_id": str(
            getattr(row, "producer_granule_id", getattr(row, "geolocation_granule_id", ""))
        ),
        "filename": filename,
        "path": str(target),
        "bytes": byte_count,
        "sha256": digest.hexdigest(),
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }


def download_plan(
    plan_path: Path, output_dir: Path, *, token: str,
    max_total_mb: float = DEFAULT_MAX_TOTAL_MB,
    max_files: int = DEFAULT_MAX_SAMPLE_FILES,
) -> list[dict[str, Any]]:
    plan = pd.read_csv(plan_path)
    validate_plan(plan, max_total_mb=max_total_mb, max_files=max_files)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_sha256 = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()
    manifest_path = output_dir / "download_manifest.json"
    existing_records: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("plan_sha256") != plan_sha256:
            raise ValueError("Existing download manifest belongs to a different sample plan")
        existing_records = {item["filename"]: item for item in previous.get("downloads", [])}
    # CMR size is an estimate; allow per-file headroom while enforcing the total cap on actual bytes.
    records: list[dict[str, Any]] = []
    remaining_mb = max_total_mb
    for row in plan.itertuples(index=False):
        filename = validate_data_url(str(row.data_url))
        target = (output_dir / filename).resolve()
        prior = existing_records.get(filename)
        if target.exists():
            if not prior:
                raise FileExistsError(f"Existing granule has no matching resumable manifest record: {filename}")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if target.stat().st_size != int(prior["bytes"]) or digest != prior["sha256"]:
                raise ValueError(f"Existing granule failed resumable size/checksum validation: {filename}")
            record = prior
        else:
            if prior:
                raise FileNotFoundError(f"Manifest records a granule that is missing from staging: {filename}")
            file_cap = min(remaining_mb, max(float(row.granule_size_cmr_mb) * 1.5, 1.0))
            record = download_one(
                row, output_dir=output_dir, token=token, max_file_mb=file_cap
            )
        records.append(record)
        remaining_mb -= int(record["bytes"]) / (1024 * 1024)
        if remaining_mb < -1e-9:
            raise ValueError("Verified staged granules exceed the configured aggregate size limit")
        metadata = {
            "plan_file": Path(plan_path).name,
            "plan_sha256": plan_sha256,
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            "download_count": len(records),
            "plan_count": len(plan),
            "max_files": max_files,
            "max_total_mb": max_total_mb,
            "downloads": records,
        }
        manifest_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("data/reference/cmr_sample_plan_oct2025.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/reference/granules/oct2025_pilot"))
    parser.add_argument("--max-total-mb", type=float, default=DEFAULT_MAX_TOTAL_MB)
    parser.add_argument(
        "--max-files", type=int, default=DEFAULT_MAX_SAMPLE_FILES,
        help=f"Maximum granules for this run (default {DEFAULT_MAX_SAMPLE_FILES}; hard limit {HARD_MAX_SAMPLE_FILES})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and list files without accessing NASA")
    args = parser.parse_args()
    try:
        plan = pd.read_csv(args.plan)
        validate_plan(plan, max_total_mb=args.max_total_mb, max_files=args.max_files)
        if args.dry_run:
            for row in plan.itertuples(index=False):
                granule_id = getattr(
                    row, "producer_granule_id", getattr(row, "geolocation_granule_id", "unknown")
                )
                product = getattr(row, "short_name", getattr(row, "geolocation_short_name", "NASA"))
                print(f"{product}: {granule_id} ({float(row.granule_size_cmr_mb):.3f} CMR MB)")
            print(f"Validated {len(plan)} files; no network access attempted.")
            return
        token = os.environ.get("FIREWATCH_EARTHDATA_TOKEN")
        if not token:
            parser.error("Set FIREWATCH_EARTHDATA_TOKEN in the local shell; never paste the token into chat or commit it.")
        records = download_plan(
            args.plan, args.output_dir, token=token,
            max_total_mb=args.max_total_mb, max_files=args.max_files,
        )
    except (OSError, ValueError, RuntimeError, PermissionError) as exc:
        parser.error(str(exc))
    for record in records:
        print(f"Downloaded {record['filename']} ({record['bytes']} bytes; SHA-256 {record['sha256']})")
    print(f"Download manifest written under {args.output_dir}")


if __name__ == "__main__":
    main()
