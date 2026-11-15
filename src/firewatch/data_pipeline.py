"""Read-only source discovery and auditable FIRMS normalization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import pandas as pd

PIPELINE_VERSION = "0.1.0"
PRODUCT_CODES = ("M-C61", "SV-C2", "J1V-C2", "J2V-C2")
REQUIRED_SOURCE_FIELDS = (
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
)
NUMERIC_FIELDS = (
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "bright_t31",
    "frp",
    "type",
)


@dataclass(frozen=True)
class SourceDescriptor:
    path: Path
    relative_path: str
    year_folder: str
    product_code: str
    stream_type: str
    source_sha256: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_product_code(path: Path) -> str:
    for product_code in PRODUCT_CODES:
        if product_code in path.name:
            return product_code
    return "unknown"


def infer_stream_type(path: Path) -> str:
    if "fire_archive_" in path.name:
        return "archive"
    if "fire_nrt_" in path.name:
        return "near_real_time"
    return "unknown"


def discover_sources(data_root: Path) -> list[SourceDescriptor]:
    """Find FIRMS CSVs recursively under year folders without modifying them."""
    data_root = Path(data_root).resolve()
    sources: list[SourceDescriptor] = []
    year_dirs = sorted(
        path for path in data_root.iterdir() if path.is_dir() and path.name.isdigit()
    )
    for year_dir in year_dirs:
        for path in sorted(year_dir.rglob("*.csv")):
            sources.append(
                SourceDescriptor(
                    path=path,
                    relative_path=path.relative_to(data_root).as_posix(),
                    year_folder=year_dir.name,
                    product_code=infer_product_code(path),
                    stream_type=infer_stream_type(path),
                    source_sha256=sha256_file(path),
                )
            )
    if not sources:
        raise FileNotFoundError(f"No CSV files found under {data_root}")
    return sources


def _raw_csv(path: Path) -> pd.DataFrame:
    # Strings preserve source tokens, including acquisition-time leading zeros,
    # categorical confidence, and version labels.
    return pd.read_csv(path, dtype="string", keep_default_na=False, low_memory=False)


def normalize_source(source: SourceDescriptor) -> pd.DataFrame:
    """Return all source rows plus normalized fields and quality flags.

    No invalid row is dropped. Raw columns remain strings and unmodified.
    """
    raw = _raw_csv(source.path)
    missing_columns = sorted(set(REQUIRED_SOURCE_FIELDS) - set(raw.columns))
    if missing_columns:
        raise ValueError(
            f"{source.relative_path} is missing required source columns: {missing_columns}"
        )

    result = raw.copy()
    result["source_file"] = source.relative_path
    result["source_sha256"] = source.source_sha256
    result["year_folder"] = source.year_folder
    result["product_code"] = source.product_code
    result["stream_type"] = source.stream_type
    result["source_row_number"] = pd.Series(range(1, len(raw) + 1), dtype="int64")
    result["pipeline_version"] = PIPELINE_VERSION
    # IDs are reproducible for this exact source snapshot and row position.
    result["observation_id"] = result["source_row_number"].map(
        lambda row_number: sha256(
            f"{source.source_sha256}:{row_number}".encode("utf-8")
        ).hexdigest()
    )

    for field in NUMERIC_FIELDS:
        if field in raw.columns:
            result[f"{field}_num"] = pd.to_numeric(raw[field], errors="coerce").astype("Float64")
        else:
            result[f"{field}_num"] = pd.Series(pd.NA, index=result.index, dtype="Float64")

    # Keep MODIS numeric confidence and VIIRS categorical confidence distinct.
    confidence = raw.get("confidence", pd.Series("", index=raw.index)).astype("string")
    is_viirs = source.product_code in {"SV-C2", "J1V-C2", "J2V-C2"}
    result["confidence_raw"] = confidence
    result["confidence_family"] = "categorical" if is_viirs else "numeric_or_product_specific"
    if not is_viirs:
        result.loc[pd.to_numeric(confidence, errors="coerce").isna() & confidence.ne(""), "confidence_family"] = "product_specific"
    result.loc[confidence.eq(""), "confidence_family"] = "missing"
    result["confidence_numeric"] = pd.to_numeric(confidence, errors="coerce").astype("Float64")

    time_token = raw["acq_time"].str.strip()
    time_digits = time_token.str.fullmatch(r"\d{1,4}").fillna(False)
    padded_time = time_token.where(time_digits).str.zfill(4)
    hour = pd.to_numeric(padded_time.str[:2], errors="coerce")
    minute = pd.to_numeric(padded_time.str[2:], errors="coerce")
    valid_clock = time_digits & hour.between(0, 23) & minute.between(0, 59)
    timestamp = pd.to_datetime(
        raw["acq_date"].str.strip() + " " + padded_time,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )
    result["observation_datetime_utc"] = timestamp.where(valid_clock)
    result["timestamp_precision"] = "minute"

    flags: list[list[str]] = [[] for _ in range(len(raw))]
    for field in REQUIRED_SOURCE_FIELDS:
        blank_mask = raw[field].str.strip().eq("").to_numpy()
        for idx in blank_mask.nonzero()[0]:
            flags[idx].append(f"missing_required:{field}")

    parsed_date = pd.to_datetime(raw["acq_date"], errors="coerce", format="%Y-%m-%d")
    for idx in parsed_date.isna().to_numpy().nonzero()[0]:
        flags[idx].append("invalid_acq_date")
    for idx in (~valid_clock).to_numpy().nonzero()[0]:
        flags[idx].append("invalid_acq_time")
    for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        values = result[f"{field}_num"]
        invalid = values.isna() | ~values.between(low, high)
        for idx in invalid.to_numpy().nonzero()[0]:
            flags[idx].append(f"invalid_{field}")

    result["quality_flags"] = [";".join(row_flags) for row_flags in flags]
    result["validation_status"] = ["quarantine" if row_flags else "valid" for row_flags in flags]
    return result


def ingest_workspace(data_root: Path, output_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize all discovered CSVs and save Parquet plus a file-level summary."""
    sources = discover_sources(data_root)
    normalized = pd.concat((normalize_source(source) for source in sources), ignore_index=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_parquet(output_path, index=False)

    summary = (
        normalized.groupby(
            ["year_folder", "product_code", "stream_type", "source_file"],
            dropna=False,
        )
        .agg(
            records=("observation_id", "size"),
            valid_records=("validation_status", lambda values: int(values.eq("valid").sum())),
            quarantine_records=("validation_status", lambda values: int(values.eq("quarantine").sum())),
            first_observation=("observation_datetime_utc", "min"),
            last_observation=("observation_datetime_utc", "max"),
        )
        .reset_index()
    )
    summary_path = output_path.with_name("ingestion_summary.csv")
    summary.to_csv(summary_path, index=False)
    return normalized, summary
