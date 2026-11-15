"""Coverage-cautious summaries for raw FIRMS observation counts."""

from __future__ import annotations

import pandas as pd

SOURCE_DIMENSIONS = ["year_folder", "product_code", "satellite", "stream_type"]


def build_daily_activity_calendar(
    observations: pd.DataFrame,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
    *,
    product_codes: list[str] | None = None,
    satellites: list[str] | None = None,
    stream_types: list[str] | None = None,
) -> pd.DataFrame:
    """Build raw detection counts with an explicit no-row/unknown-coverage state."""
    required = set(SOURCE_DIMENSIONS + [
        "source_file", "observation_datetime_utc", "validation_status"
    ])
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError(f"Normalized observations missing fields: {missing}")

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    else:
        end = end.tz_convert("UTC")
    start, end = start.normalize(), end.normalize()
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    scope = observations
    for column, selected in (
        ("product_code", product_codes),
        ("satellite", satellites),
        ("stream_type", stream_types),
    ):
        if selected is not None:
            scope = scope.loc[scope[column].isin(selected)]

    source_spans = (
        scope.loc[scope["observation_datetime_utc"].notna()]
        .groupby(SOURCE_DIMENSIONS, as_index=False)
        .agg(
            source_first_date=("observation_datetime_utc", "min"),
            source_last_date=("observation_datetime_utc", "max"),
            source_files=("source_file", lambda values: ", ".join(sorted(values.unique()))),
        )
    )
    if source_spans.empty:
        return pd.DataFrame(columns=SOURCE_DIMENSIONS + [
            "source_files", "date_utc", "detection_count", "has_observation_rows",
            "within_first_last_detection_bounds", "activity_state"
        ])
    calendar_parts = []
    for row in source_spans.itertuples(index=False):
        year_start = pd.Timestamp(year=int(row.year_folder), month=1, day=1, tz="UTC")
        year_end = pd.Timestamp(year=int(row.year_folder), month=12, day=31, tz="UTC")
        first = max(start, year_start)
        last = min(end, year_end)
        if first > last:
            continue
        first, last = first.normalize(), last.normalize()
        span_start, span_end = row.source_first_date.floor("D"), row.source_last_date.floor("D")
        for date in pd.date_range(first, last, freq="D", tz="UTC"):
            calendar_parts.append({
                **dict(zip(SOURCE_DIMENSIONS, row[:len(SOURCE_DIMENSIONS)])),
                "source_files": row.source_files,
                "date_utc": date,
                "within_first_last_detection_bounds": span_start <= date <= span_end,
            })
    if not calendar_parts:
        return pd.DataFrame(columns=SOURCE_DIMENSIONS + [
            "source_files", "date_utc", "detection_count", "has_observation_rows",
            "within_first_last_detection_bounds", "activity_state"
        ])
    calendar = pd.DataFrame(calendar_parts)

    in_period = scope.loc[
        scope["validation_status"].eq("valid")
        & scope["observation_datetime_utc"].ge(start)
        & scope["observation_datetime_utc"].lt(end + pd.Timedelta(days=1))
    ].copy()
    in_period["date_utc"] = in_period["observation_datetime_utc"].dt.floor("D")
    counts = (
        in_period.groupby(SOURCE_DIMENSIONS + ["date_utc"], as_index=False)
        .size()
        .rename(columns={"size": "detection_count"})
    )
    calendar = calendar.merge(counts, on=SOURCE_DIMENSIONS + ["date_utc"], how="left")
    calendar["detection_count"] = calendar["detection_count"].fillna(0).astype("int64")
    calendar["has_observation_rows"] = calendar["detection_count"].gt(0)
    calendar["activity_state"] = "no_rows_coverage_unknown"
    calendar.loc[calendar.has_observation_rows, "activity_state"] = "detections_present"
    return calendar.sort_values(SOURCE_DIMENSIONS + ["date_utc"]).reset_index(drop=True)


def summarize_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    """Summarize detections and row-presence days without claiming coverage."""
    if calendar.empty:
        return pd.DataFrame(columns=SOURCE_DIMENSIONS + [
            "calendar_days", "raw_detections", "dates_with_rows", "dates_without_rows_coverage_unknown",
            "dates_outside_first_last_detection_bounds", "mean_detections_per_date_with_rows"
        ])
    summary = (
        calendar.groupby(SOURCE_DIMENSIONS, as_index=False)
        .agg(
            calendar_days=("date_utc", "size"),
            raw_detections=("detection_count", "sum"),
            dates_with_rows=("has_observation_rows", "sum"),
            dates_outside_first_last_detection_bounds=("within_first_last_detection_bounds", lambda values: int((~values).sum())),
        )
    )
    means = (
        calendar.loc[calendar.has_observation_rows]
        .groupby(SOURCE_DIMENSIONS)["detection_count"]
        .mean()
        .rename("mean_detections_per_date_with_rows")
        .reset_index()
    )
    summary = summary.merge(means, on=SOURCE_DIMENSIONS, how="left")
    no_rows = (
        calendar.loc[~calendar.has_observation_rows]
        .groupby(SOURCE_DIMENSIONS).size().rename("dates_without_rows_coverage_unknown")
        .reset_index()
    )
    summary = summary.merge(no_rows, on=SOURCE_DIMENSIONS, how="left")
    summary["dates_without_rows_coverage_unknown"] = summary["dates_without_rows_coverage_unknown"].fillna(0).astype("int64")
    return summary
