"""FastAPI read-only service over the normalized FIRMS observation store."""

from __future__ import annotations

import os
import gzip
from contextlib import asynccontextmanager
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analytics import build_daily_activity_calendar
from .association import find_candidate_links
from .forecast import forecast_observation_volume

DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "processed"
DEPLOY_DATA_PATH = DATA_DIRECTORY / "observations.deploy.parquet.gz"
DEFAULT_DATA_PATH = DEPLOY_DATA_PATH if DEPLOY_DATA_PATH.is_file() else DATA_DIRECTORY / "observations.parquet"
OBSERVATION_COLUMNS = [
    "observation_id", "source_file", "year_folder", "product_code", "stream_type",
    "satellite", "latitude_num", "longitude_num", "observation_datetime_utc",
    "validation_status", "frp_num", "confidence_raw", "confidence_family",
]


class ObservationStore:
    def __init__(self, path: Path):
        if not path.is_file():
            raise FileNotFoundError(f"Normalized observation file not found: {path}")
        self.path = path
        source = gzip.open(path, "rb") if path.suffix == ".gz" else path
        self.frame = pd.read_parquet(source, columns=OBSERVATION_COLUMNS, dtype_backend="pyarrow")
        utc_values = self.frame["observation_datetime_utc"].to_numpy(
            dtype="datetime64[ns]"
        )
        self.frame["observation_datetime_utc"] = pd.Series(
            pd.to_datetime(utc_values, utc=True)
        )

    def filter(
        self,
        start: pd.Timestamp,
        end: pd.Timestamp,
        satellites: list[str] | None = None,
        products: list[str] | None = None,
        streams: list[str] | None = None,
    ) -> pd.DataFrame:
        mask = (
            self.frame["observation_datetime_utc"].ge(start)
            & self.frame["observation_datetime_utc"].lt(end + pd.Timedelta(days=1))
            & self.frame["validation_status"].eq("valid")
        )
        if satellites:
            mask &= self.frame["satellite"].isin(satellites)
        if products:
            mask &= self.frame["product_code"].isin(products)
        if streams:
            mask &= self.frame["stream_type"].isin(streams)
        return self.frame.loc[mask]


def _parse_date(value: str, name: str) -> pd.Timestamp:
    try:
        date = pd.Timestamp(value)
        return (date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")).normalize()
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail=f"{name} must be an ISO date (YYYY-MM-DD)")


def _parse_filter(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def create_app(data_path: Path | None = None) -> FastAPI:
    source_path = Path(data_path or os.environ.get("FIREWATCH_DATA", DEFAULT_DATA_PATH))

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.store = ObservationStore(source_path)
        yield

    app = FastAPI(title="FIREWATCH Observation API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    def store() -> ObservationStore:
        current = getattr(app.state, "store", None)
        if current is None:
            try:
                current = ObservationStore(source_path)
                app.state.store = current
            except FileNotFoundError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
        return current

    def selected(
        start: str,
        end: str,
        satellites: str | None,
        products: str | None,
        streams: str | None,
    ) -> tuple[ObservationStore, pd.DataFrame, pd.Timestamp, pd.Timestamp]:
        first, last = _parse_date(start, "start"), _parse_date(end, "end")
        if first > last:
            raise HTTPException(status_code=422, detail="start must be on or before end")
        db = store()
        return db, db.filter(first, last, _parse_filter(satellites), _parse_filter(products), _parse_filter(streams)), first, last

    @app.get("/api/health")
    def health():
        return {"status": "ok", "rows": len(store().frame), "data_file": store().path.name}

    @app.get("/api/metadata")
    def metadata():
        frame = store().frame
        sources = (
            frame.groupby(["product_code", "satellite", "stream_type"], as_index=False)
            .agg(records=("observation_id", "size"))
            .sort_values(["product_code", "satellite", "stream_type"])
            .to_dict("records")
        )
        return {
            "date_min": frame.observation_datetime_utc.min().date().isoformat(),
            "date_max": frame.observation_datetime_utc.max().date().isoformat(),
            "total_records": len(frame),
            "sources": sources,
            "default_location": {"name": "Cameroon", "center": [7.5, 12.5], "zoom": 6},
            "limitations": [
                "A hotspot is a satellite thermal-anomaly observation, not a confirmed wildfire.",
                "Dates with no rows do not establish zero fire activity or satellite coverage.",
                "Archive and NRT streams are kept separate because archive processing replaces NRT over time.",
            ],
        }

    @app.get("/api/quality")
    def quality():
        """Return source-preserving quality indicators for the loaded archive."""
        frame = store().frame
        required = [
            "observation_id", "source_file", "year_folder", "product_code",
            "stream_type", "satellite", "latitude_num", "longitude_num",
            "observation_datetime_utc",
        ]
        optional = ["confidence_raw", "frp_num"]
        missing = {column: int(frame[column].isna().sum()) for column in required + optional}
        status_counts = {
            str(status): int(count)
            for status, count in frame["validation_status"].value_counts(dropna=False).items()
        }
        source_counts = (
            frame.groupby(["year_folder", "product_code", "satellite", "stream_type"], as_index=False)
            .agg(records=("observation_id", "size"), source_files=("source_file", "nunique"))
            .sort_values(["year_folder", "product_code", "satellite", "stream_type"])
            .to_dict("records")
        )
        return {
            "total_rows": len(frame),
            "validation_status": status_counts,
            "duplicate_observation_ids": int(frame["observation_id"].duplicated().sum()),
            "missing_values": missing,
            "sources": source_counts,
            "date_min": frame.observation_datetime_utc.min().date().isoformat(),
            "date_max": frame.observation_datetime_utc.max().date().isoformat(),
            "source_files": int(frame.source_file.nunique()),
        }

    @app.get("/api/trends")
    def trends(
        start: str = "2025-01-01",
        end: str = "2026-11-02",
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
    ):
        _, frame, _, _ = selected(start, end, satellites, products, streams)
        if frame.empty:
            return []
        monthly = frame.assign(
            month=frame.observation_datetime_utc.dt.strftime("%Y-%m"),
            observation_day=frame.observation_datetime_utc.dt.floor("D"),
        )
        return (
            monthly.groupby(["month", "product_code", "satellite", "stream_type"], as_index=False)
            .agg(
                detection_count=("observation_id", "size"),
                dates_with_rows=("observation_day", "nunique"),
            )
            .sort_values(["month", "product_code", "satellite", "stream_type"])
            .to_dict("records")
        )

    @app.get("/api/forecast")
    def forecast(
        horizon_days: int = Query(default=7, ge=1, le=14),
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
    ):
        """Forecast historical daily source-row volume; this is not fire-risk prediction."""
        frame = store().frame
        if values := _parse_filter(satellites):
            frame = frame.loc[frame.satellite.isin(values)]
        if values := _parse_filter(products):
            frame = frame.loc[frame.product_code.isin(values)]
        if values := _parse_filter(streams):
            frame = frame.loc[frame.stream_type.isin(values)]
        return forecast_observation_volume(frame, horizon_days=horizon_days)

    @app.get("/api/summary")
    def summary(
        start: str = "2025-10-01",
        end: str = "2025-10-31",
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
    ):
        _, frame, _, _ = selected(start, end, satellites, products, streams)
        counts = (
            frame.groupby(["product_code", "satellite", "stream_type"], as_index=False)
            .agg(detections=("observation_id", "size"))
            .sort_values(["product_code", "satellite", "stream_type"])
            .to_dict("records")
        )
        dates = frame.observation_datetime_utc.dt.floor("D").nunique()
        return {"total_detections": len(frame), "dates_with_rows": int(dates), "sources": counts}

    @app.get("/api/calendar")
    def calendar(
        start: str = "2025-10-01",
        end: str = "2025-10-31",
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
    ):
        first, last = _parse_date(start, "start"), _parse_date(end, "end")
        if first > last:
            raise HTTPException(status_code=422, detail="start must be on or before end")
        db = store()
        scope = db.frame
        if values := _parse_filter(satellites):
            scope = scope.loc[scope.satellite.isin(values)]
        if values := _parse_filter(products):
            scope = scope.loc[scope.product_code.isin(values)]
        if values := _parse_filter(streams):
            scope = scope.loc[scope.stream_type.isin(values)]
        data = build_daily_activity_calendar(scope, first, last)
        return data.assign(date_utc=data.date_utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_dict("records")

    @app.get("/api/map")
    def map_points(
        start: str = "2025-10-01",
        end: str = "2025-10-31",
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
        west: float = 8.0,
        south: float = 1.0,
        east: float = 17.0,
        north: float = 14.0,
        zoom: int = Query(default=6, ge=1, le=18),
    ):
        _, frame, _, _ = selected(start, end, satellites, products, streams)
        if west >= east or south >= north:
            raise HTTPException(status_code=422, detail="Map bounds must have west < east and south < north")
        frame = frame.loc[
            frame.longitude_num.between(west, east)
            & frame.latitude_num.between(south, north)
        ]
        if frame.empty:
            return {"total_detections": 0, "displayed_cells": 0, "aggregation_degrees": None, "cells": []}
        grid = 0.05 if zoom <= 6 else 0.02 if zoom <= 8 else 0.005 if zoom <= 11 else 0.0
        if grid == 0:
            sampled = len(frame) > 5000
            points = frame.sample(5000, random_state=42) if sampled else frame
            records_frame = points[["latitude_num", "longitude_num", "satellite", "product_code", "stream_type", "confidence_raw", "frp_num"]].rename(
                columns={"latitude_num": "latitude", "longitude_num": "longitude", "frp_num": "frp"}
            )
            records_frame = records_frame.astype(object).where(pd.notna(records_frame), None)
            records = records_frame.to_dict("records")
            return {"total_detections": len(frame), "displayed_cells": len(records), "sampled": sampled, "aggregation_degrees": None, "cells": records}
        frame = frame.copy()
        frame["latitude"] = (frame.latitude_num // grid) * grid + grid / 2
        frame["longitude"] = (frame.longitude_num // grid) * grid + grid / 2
        cells = (
            frame.groupby(["latitude", "longitude", "satellite", "product_code", "stream_type"], as_index=False)
            .agg(detection_count=("observation_id", "size"))
            .to_dict("records")
        )
        return {"total_detections": len(frame), "displayed_cells": len(cells), "sampled": False, "aggregation_degrees": grid, "cells": cells}

    @app.get("/api/candidate-links")
    def candidate_links(
        start: str = "2025-10-01",
        end: str = "2025-10-31",
        satellites: str | None = None,
        products: str | None = None,
        streams: str | None = None,
        max_distance_km: float = Query(default=1.0, gt=0, le=5),
        max_time_delta_hours: float = Query(default=3.0, gt=0, le=12),
    ):
        _, frame, first, last = selected(start, end, satellites, products, streams)
        if (last - first).days > 31:
            raise HTTPException(status_code=422, detail="Candidate inspection is limited to 32 days per request")
        links = find_candidate_links(
            frame,
            max_distance_km=max_distance_km,
            max_time_delta_hours=max_time_delta_hours,
        )
        total = len(links)
        if total > 5000:
            links = links.sort_values(["distance_km", "time_difference_minutes"]).head(5000)
        return {"total_candidate_links": total, "returned_candidate_links": len(links), "truncated": total > len(links), "links": links.to_dict("records")}

    return app


app = create_app()
