import tempfile
import unittest
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from src.firewatch.api import create_app
from src.firewatch.data_pipeline import discover_sources, normalize_source


ARCHIVE_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_t31,frp,daynight,type\n"
)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_source(
            "fire_archive_M-C61_1.csv",
            ARCHIVE_HEADER
            + "5.00000,10.00000,305,1,1,2026-01-01,1000,Aqua,MODIS,60,61.03,292,9,N,0\n",
        )
        self._write_source(
            "fire_archive_J1V-C2_1.csv",
            ARCHIVE_HEADER
            + "5.00500,10.00000,305,.5,.5,2026-01-01,1010,N20,VIIRS,n,2,292,9,N,0\n",
        )
        observations = pd.concat(
            [normalize_source(source) for source in discover_sources(self.root)],
            ignore_index=True,
        )
        self.parquet = self.root / "observations.parquet"
        observations.to_parquet(self.parquet, index=False)
        self.client = TestClient(create_app(self.parquet))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def _write_source(self, filename, body):
        folder = self.root / "2026" / filename.replace(".csv", "")
        folder.mkdir(parents=True)
        (folder / filename).write_text(body, encoding="utf-8")

    def test_metadata_and_filtered_summary_use_real_rows(self):
        metadata = self.client.get("/api/metadata").json()
        self.assertEqual(metadata["total_records"], 2)
        self.assertEqual(metadata["date_min"], "2026-01-01")
        summary = self.client.get(
            "/api/summary",
            params={"start": "2026-01-01", "end": "2026-01-01", "satellites": "N20"},
        ).json()
        self.assertEqual(summary["total_detections"], 1)
        self.assertEqual(summary["sources"][0]["satellite"], "N20")

    def test_map_calendar_and_candidate_link_endpoints(self):
        common = {"start": "2026-01-01", "end": "2026-01-01"}
        points = self.client.get("/api/map", params=common).json()
        self.assertEqual(points["total_detections"], 2)
        self.assertGreaterEqual(points["displayed_cells"], 1)
        detail_points = self.client.get("/api/map", params={**common, "zoom": 12}).json()
        self.assertEqual(detail_points["displayed_cells"], 2)
        self.assertIn("frp", detail_points["cells"][0])
        calendar = self.client.get("/api/calendar", params=common).json()
        self.assertTrue(calendar)
        self.assertEqual(sum(row["detection_count"] for row in calendar), 2)
        candidates = self.client.get(
            "/api/candidate-links",
            params={**common, "max_distance_km": 1, "max_time_delta_hours": 1},
        ).json()
        self.assertEqual(candidates["total_candidate_links"], 1)
        self.assertEqual(candidates["links"][0]["link_family"], "MODIS-VIIRS")

    def test_quality_endpoint_reports_lineage_nulls_and_duplicate_ids(self):
        quality = self.client.get("/api/quality").json()
        self.assertEqual(quality["total_rows"], 2)
        self.assertEqual(quality["validation_status"], {"valid": 2})
        self.assertEqual(quality["duplicate_observation_ids"], 0)
        self.assertEqual(quality["missing_values"]["observation_id"], 0)
        self.assertEqual(quality["source_files"], 2)
        self.assertEqual(len(quality["sources"]), 2)

    def test_trends_endpoint_returns_real_monthly_source_counts(self):
        trends = self.client.get(
            "/api/trends", params={"start": "2026-01-01", "end": "2026-01-31"}
        ).json()
        self.assertEqual(sum(row["detection_count"] for row in trends), 2)
        self.assertEqual({row["satellite"] for row in trends}, {"Aqua", "N20"})
        self.assertTrue(all(row["month"] == "2026-01" for row in trends))

    def test_invalid_date_order_and_map_bounds_are_rejected(self):
        response = self.client.get(
            "/api/summary", params={"start": "2026-01-02", "end": "2026-01-01"}
        )
        self.assertEqual(response.status_code, 422)
        response = self.client.get(
            "/api/map", params={"start": "2026-01-01", "end": "2026-01-01", "west": 12, "east": 8}
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
