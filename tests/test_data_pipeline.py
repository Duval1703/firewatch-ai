import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.firewatch.data_pipeline import discover_sources, normalize_source
from src.firewatch.association import find_candidate_links
from src.firewatch.analytics import build_daily_activity_calendar, summarize_calendar


ARCHIVE_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_t31,frp,daynight,type\n"
)
NRT_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_t31,frp,daynight\n"
)


class DataPipelineTests(unittest.TestCase):
    def _source(self, tmp: Path, name: str, content: str):
        folder = tmp / "2026" / name.replace(".csv", "")
        folder.mkdir(parents=True)
        path = folder / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_preserves_raw_values_and_builds_utc_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "2.5,10.5,305.0,1.0,1.0,2026-01-01,0018,Aqua,MODIS,39,61.03,292.2,9.3,N,0\n",
            )
            source = discover_sources(root)[0]
            frame = normalize_source(source)
            row = frame.iloc[0]
            self.assertEqual(row["acq_time"], "0018")
            self.assertEqual(row["confidence"], "39")
            self.assertEqual(row["confidence_family"], "numeric_or_product_specific")
            self.assertEqual(str(row["observation_datetime_utc"]), "2026-01-01 00:18:00+00:00")
            self.assertEqual(row["validation_status"], "valid")

    def test_viirs_categories_and_optional_type_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_nrt_J1V-C2_1.csv",
                NRT_HEADER
                + "2.5,10.5,305.0,0.5,0.5,2026-08-01,18,N20,VIIRS,n,2.0NRT,292.2,9.3,D\n",
            )
            frame = normalize_source(discover_sources(root)[0])
            row = frame.iloc[0]
            self.assertEqual(row["confidence"], "n")
            self.assertEqual(row["confidence_family"], "categorical")
            self.assertTrue(pd.isna(row["type_num"]))
            self.assertEqual(row["validation_status"], "valid")

    def test_suomi_npp_confidence_is_recognized_as_viirs_category(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_SV-C2_1.csv",
                ARCHIVE_HEADER
                + "2.5,10.5,305.0,0.5,0.5,2026-01-01,18,SNPP,SNPP,n,2,292.2,9.3,N,0\n",
            )
            row = normalize_source(discover_sources(root)[0]).iloc[0]
            self.assertEqual(row["confidence_family"], "categorical")

    def test_invalid_coordinate_and_time_are_quarantined_not_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "95,10.5,305.0,1.0,1.0,2026-01-01,2460,Aqua,MODIS,39,61.03,292.2,9.3,N,0\n",
            )
            frame = normalize_source(discover_sources(root)[0])
            self.assertEqual(len(frame), 1)
            self.assertEqual(frame.iloc[0]["validation_status"], "quarantine")
            self.assertIn("invalid_latitude", frame.iloc[0]["quality_flags"])
            self.assertIn("invalid_acq_time", frame.iloc[0]["quality_flags"])

    def test_observation_id_is_stable_for_same_source_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "2.5,10.5,305.0,1.0,1.0,2026-01-01,0018,Aqua,MODIS,39,61.03,292.2,9.3,N,0\n",
            )
            source = discover_sources(root)[0]
            first = normalize_source(source).iloc[0]["observation_id"]
            second = normalize_source(source).iloc[0]["observation_id"]
            self.assertEqual(first, second)

    def test_discovery_ignores_derived_csvs_outside_year_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "2.5,10.5,305.0,1.0,1.0,2026-01-01,0018,Aqua,MODIS,39,61.03,292.2,9.3,N,0\n",
            )
            derived = root / "data" / "processed"
            derived.mkdir(parents=True)
            (derived / "ingestion_summary.csv").write_text("summary,value\nrows,1\n")
            self.assertEqual(len(discover_sources(root)), 1)

    def test_candidate_link_crosses_utc_midnight_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "5.00000,10.00000,305,1,1,2026-01-01,2350,Aqua,MODIS,60,61.03,292,9,N,0\n",
            )
            self._source(
                root,
                "fire_archive_J1V-C2_1.csv",
                ARCHIVE_HEADER
                + "5.00500,10.00000,305,.5,.5,2026-01-02,0010,N20,VIIRS,n,2,292,9,N,0\n",
            )
            data = pd.concat(
                [normalize_source(source) for source in discover_sources(root)],
                ignore_index=True,
            )
            links = find_candidate_links(data, max_distance_km=1, max_time_delta_hours=1)
            self.assertEqual(len(links), 1)
            self.assertLess(links.iloc[0]["distance_km"], 1)
            self.assertEqual(links.iloc[0]["time_difference_minutes"], 20)
            self.assertEqual(links.iloc[0]["link_family"], "MODIS-VIIRS")
            self.assertEqual(links.iloc[0]["max_distance_km"], 1)

    def test_same_satellite_is_not_linked_to_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "5.00000,10.00000,305,1,1,2026-01-01,1000,Aqua,MODIS,60,61.03,292,9,N,0\n"
                + "5.00100,10.00000,306,1,1,2026-01-01,1010,Aqua,MODIS,60,61.03,293,9,N,0\n",
            )
            data = normalize_source(discover_sources(root)[0])
            self.assertTrue(find_candidate_links(data).empty)

    def test_candidate_thresholds_exclude_distant_or_late_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._source(
                root,
                "fire_archive_M-C61_1.csv",
                ARCHIVE_HEADER
                + "5.00000,10.00000,305,1,1,2026-01-01,1000,Aqua,MODIS,60,61.03,292,9,N,0\n",
            )
            self._source(
                root,
                "fire_archive_J1V-C2_1.csv",
                ARCHIVE_HEADER
                + "5.20000,10.00000,305,.5,.5,2026-01-01,1800,N20,VIIRS,n,2,292,9,N,0\n",
            )
            data = pd.concat(
                [normalize_source(source) for source in discover_sources(root)],
                ignore_index=True,
            )
            self.assertTrue(
                find_candidate_links(data, max_distance_km=1, max_time_delta_hours=1).empty
            )

    def test_calendar_marks_empty_dates_as_unknown_coverage_not_zero_fire(self):
        rows = pd.DataFrame(
            {
                "year_folder": ["2026", "2026"],
                "product_code": ["M-C61", "M-C61"],
                "satellite": ["Aqua", "Aqua"],
                "stream_type": ["archive", "archive"],
                "source_file": ["2026/archive.csv", "2026/archive.csv"],
                "observation_datetime_utc": pd.to_datetime(
                    ["2026-01-01T10:00:00Z", "2026-01-03T10:00:00Z"], utc=True
                ),
                "validation_status": ["valid", "valid"],
            }
        )
        calendar = build_daily_activity_calendar(rows, "2026-01-01", "2026-01-03")
        self.assertEqual(calendar.detection_count.tolist(), [1, 0, 1])
        self.assertEqual(
            calendar.activity_state.tolist(),
            ["detections_present", "no_rows_coverage_unknown", "detections_present"],
        )
        summary = summarize_calendar(calendar).iloc[0]
        self.assertEqual(summary["raw_detections"], 2)
        self.assertEqual(summary["dates_without_rows_coverage_unknown"], 1)

    def test_calendar_respects_utc_day_bounds_and_source_filters(self):
        rows = pd.DataFrame(
            {
                "year_folder": ["2026", "2026"],
                "product_code": ["M-C61", "J1V-C2"],
                "satellite": ["Aqua", "N20"],
                "stream_type": ["archive", "near_real_time"],
                "source_file": ["2026/archive.csv", "2026/nrt.csv"],
                "observation_datetime_utc": pd.to_datetime(
                    ["2026-01-01T23:59:00Z", "2026-01-02T00:01:00Z"], utc=True
                ),
                "validation_status": ["valid", "valid"],
            }
        )
        calendar = build_daily_activity_calendar(
            rows,
            "2026-01-01",
            "2026-01-01",
            product_codes=["M-C61"],
        )
        self.assertEqual(len(calendar), 1)
        self.assertEqual(calendar.iloc[0]["detection_count"], 1)


if __name__ == "__main__":
    unittest.main()
