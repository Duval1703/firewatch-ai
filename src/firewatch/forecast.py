"""Short-horizon seasonal forecast for daily FIRMS observation-row volume."""

from __future__ import annotations

import numpy as np
import pandas as pd


MODEL_NAME = "seasonal-window-mean-0.1.0"
MIN_HISTORY_DAYS = 455
FORECAST_HORIZON_DAYS = 7


def _seasonal_window_mean(values: np.ndarray, target_index: int, *, radius: int = 7) -> float:
    """Average the same seasonal window one year earlier, using past data only."""
    center = target_index - 365
    start = max(0, center - radius)
    stop = min(target_index, center + radius + 1)
    if stop <= start:
        return 0.0
    return float(np.mean(values[start:stop]))


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    errors = predicted - actual
    denominator = float(actual.sum())
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "wape": float(np.abs(errors).sum() / denominator) if denominator else None,
    }


def forecast_observation_volume(
    observations: pd.DataFrame,
    *,
    horizon_days: int = FORECAST_HORIZON_DAYS,
    today: pd.Timestamp | None = None,
) -> dict:
    """Chronologically backtest and forecast counts of FIRMS source rows."""
    if horizon_days < 1 or horizon_days > 14:
        raise ValueError("horizon_days must be between 1 and 14")
    if observations.empty:
        return {"status": "no_observations", "model": MODEL_NAME, "target": "daily_valid_observation_rows"}

    valid = observations.loc[
        observations["validation_status"].eq("valid"),
        ["observation_datetime_utc", "observation_id"],
    ].copy()
    if valid.empty:
        return {"status": "no_valid_observations", "model": MODEL_NAME, "target": "daily_valid_observation_rows"}

    valid["observation_datetime_utc"] = pd.to_datetime(valid["observation_datetime_utc"], utc=True)
    daily = valid.groupby(valid.observation_datetime_utc.dt.floor("D")).size()
    first_day, last_day = daily.index.min().normalize(), daily.index.max().normalize()
    day_index = pd.date_range(first_day, last_day, freq="D", tz="UTC")
    values = daily.reindex(day_index, fill_value=0).to_numpy(dtype=float)
    if len(values) < MIN_HISTORY_DAYS:
        return {
            "status": "insufficient_history",
            "model": MODEL_NAME,
            "target": "daily_valid_observation_rows",
            "history_days": len(values),
            "required_history_days": MIN_HISTORY_DAYS,
            "data_as_of": last_day.date().isoformat(),
        }

    test_start = 365
    test_indexes = range(test_start, len(values))
    test_prediction = np.array([_seasonal_window_mean(values, index) for index in test_indexes])
    seasonal_baseline = np.array([values[index - 365] for index in test_indexes], dtype=float)
    actual = values[test_start:]
    model_metrics = _metrics(actual, test_prediction)
    baseline_metrics = _metrics(actual, seasonal_baseline)

    future_index = pd.date_range(last_day + pd.Timedelta(days=1), periods=horizon_days, freq="D", tz="UTC")
    predicted = np.array([_seasonal_window_mean(values, len(values) + offset) for offset in range(horizon_days)])
    current_day = (today or pd.Timestamp.now(tz="UTC")).normalize()
    month_thresholds = {
        str(month): float(np.quantile(values[day_index.month == month], 0.9))
        for month in range(1, 13)
        if np.any(day_index.month == month)
    }
    forecast_rows = []
    for date, count in zip(future_index, predicted, strict=True):
        threshold = month_thresholds.get(str(date.month))
        watch = bool(threshold is not None and count > threshold)
        forecast_rows.append({
            "date": date.date().isoformat(),
            "expected_rows": round(float(count), 1),
            "historical_month_p90_rows": round(threshold, 1) if threshold is not None else None,
            "watch": watch,
        })

    return {
        "status": "ok",
        "model": MODEL_NAME,
        "target": "daily_valid_observation_rows",
        "history_days": len(values),
        "data_as_of": last_day.date().isoformat(),
        "data_stale_days": max(0, int((current_day - last_day).days)),
        "horizon_days": horizon_days,
        "backtest": {
            "method": "rolling-origin seasonal holdout after the first 365 archive days",
            "holdout_days": len(actual),
            "model": model_metrics,
            "seasonal_naive_365d": baseline_metrics,
            "beats_seasonal_naive_on_mae": model_metrics["mae"] < baseline_metrics["mae"],
        },
        "forecasts": forecast_rows,
        "alert_rule": "watch when expected observation rows exceed the historical 90th percentile for that calendar month",
        "limitations": [
            "Forecasts source-row volume, not fire occurrence, spread, severity, or risk.",
            "Rows are presence-only detections; a zero-row day is a row-volume zero, not proof of no fire or sensor coverage.",
            "The archive is a historical snapshot and is not a live alert feed.",
            "Archive and near-real-time stream filters affect row counts and should remain visible.",
        ],
    }
