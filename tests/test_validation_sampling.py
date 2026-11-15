import unittest

import pandas as pd

from src.firewatch.validation_sampling import select_validation_sample


def _boundary():
    return {"features": [{"geometry": {"type": "Polygon", "coordinates": [[
        [0, 0], [10, 0], [10, 10], [0, 10], [0, 0]
    ]]}}]}


def _manifest(*, polygon="1 1 3 1 3 3 1 3 1 1"):
    return pd.DataFrame([{
        "short_name": "MYD14", "producer_granule_id": "MYD14.test.hdf",
        "acquisition_id": "MYD14.test", "time_start_utc": "2025-01-01T12:00:00Z",
        "time_end_utc": "2025-01-01T12:05:00Z", "updated_utc": "2025-01-02T00:00:00Z",
        "granule_size_cmr_mb": 1.0,
        "data_url": "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/a.hdf",
        "browse_url": "https://example.test/a.jpg", "spatial_polygons": f'[["{polygon}"]]',
        "collection_version": "061", "cmr_entry_id": "G1",
    }])


def _presence():
    return pd.DataFrame([
        {"observation_id": "candidate", "satellite": "Aqua", "product_code": "M-C61",
         "latitude_num": 2.0, "longitude_num": 2.0,
         "observation_datetime_utc": "2025-01-01T12:02:00Z", "validation_status": "valid",
         "candidate_cross_platform_1km_3h": True},
        {"observation_id": "noncandidate", "satellite": "Aqua", "product_code": "M-C61",
         "latitude_num": 2.5, "longitude_num": 2.5,
         "observation_datetime_utc": "2025-01-01T12:03:00Z", "validation_status": "valid",
         "candidate_cross_platform_1km_3h": False},
    ])


class ValidationSamplingTests(unittest.TestCase):
    def test_selects_one_per_nonempty_stratum_deterministically(self):
        first, _ = select_validation_sample(_presence(), _manifest(), _boundary())
        second, _ = select_validation_sample(_presence(), _manifest(), _boundary())
        chosen = first.loc[first.selection_status.eq("matched")]
        self.assertEqual(len(chosen), 2)
        self.assertEqual(set(chosen.observation_id), {"candidate", "noncandidate"})
        self.assertEqual(chosen.producer_granule_id.nunique(), 1)
        self.assertEqual(first.observation_id.fillna("").tolist(), second.observation_id.fillna("").tolist())
        self.assertEqual(int(first.selection_status.eq("empty_stratum").sum()), 38)

    def test_no_matching_cmr_extent_is_retained_in_audit(self):
        sample, _ = select_validation_sample(_presence().iloc[[0]], _manifest(polygon="20 20 21 20 21 21 20 21 20 20"), _boundary())
        row = sample.loc[sample.satellite.eq("Aqua") & sample.quarter.eq("Q1") & sample.cross_platform_candidate].iloc[0]
        self.assertEqual(row.selection_status, "no_cmr_time_polygon_match")
        self.assertEqual(row.observation_id, "candidate")


if __name__ == "__main__":
    unittest.main()
