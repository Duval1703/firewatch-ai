import unittest

import numpy as np
import pandas as pd

from src.firewatch.forecast import forecast_observation_volume


class ObservationVolumeForecastTests(unittest.TestCase):
    def _seasonal_observations(self, days=500):
        dates = pd.date_range("2025-01-01", periods=days, freq="D", tz="UTC")
        rng = np.random.default_rng(27)
        counts = [
            int(rng.poisson(35 + 20 * (1 + np.sin(2 * np.pi * day / 365.25))))
            for day in range(days)
        ]
        timestamps = [date for date, count in zip(dates, counts, strict=True) for _ in range(count)]
        return pd.DataFrame({
            "observation_id": [f"row-{index}" for index in range(len(timestamps))],
            "observation_datetime_utc": timestamps,
            "validation_status": "valid",
        }), dates[-1], counts

    def test_forecast_uses_seasonal_window_and_returns_backtest(self):
        observations, last_date, _counts = self._seasonal_observations()
        result = forecast_observation_volume(observations, today=last_date)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["target"], "daily_valid_observation_rows")
        self.assertEqual(result["history_days"], 500)
        self.assertEqual(result["data_stale_days"], 0)
        self.assertEqual(len(result["forecasts"]), 7)
        self.assertEqual(result["forecasts"][0]["date"], (last_date + pd.Timedelta(days=1)).date().isoformat())
        self.assertEqual(result["backtest"]["holdout_days"], 135)
        self.assertTrue(all(type(day["watch"]) is bool for day in result["forecasts"]))

    def test_forecast_requires_a_season_and_holdout_window(self):
        observations, _last_date, _counts = self._seasonal_observations(days=400)
        result = forecast_observation_volume(observations)
        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["required_history_days"], 455)

    def test_horizon_is_bounded(self):
        observations, _last_date, _counts = self._seasonal_observations()
        with self.assertRaises(ValueError):
            forecast_observation_volume(observations, horizon_days=15)


if __name__ == "__main__":
    unittest.main()
