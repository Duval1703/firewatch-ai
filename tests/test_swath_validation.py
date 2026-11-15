import tempfile
import unittest
from pathlib import Path
import gc

import h5py
import numpy as np
from pyhdf.SD import SD, SDC

from src.firewatch.swath_validation import great_circle_km, inspect_modis_granule, inspect_viirs_granule


class SwathValidationTests(unittest.TestCase):
    def _write_modis(self, path: Path) -> None:
        f = SD(str(path), SDC.CREATE | SDC.WRITE)
        arrays = [
            ("FP_latitude", SDC.FLOAT32, np.array([1.0], dtype=np.float32)),
            ("FP_longitude", SDC.FLOAT32, np.array([2.0], dtype=np.float32)),
            ("FP_confidence", SDC.UINT8, np.array([50], dtype=np.uint8)),
            ("FP_power", SDC.FLOAT32, np.array([9.0], dtype=np.float32)),
            ("FP_line", SDC.UINT16, np.array([1], dtype=np.uint16)),
            ("FP_sample", SDC.UINT16, np.array([1], dtype=np.uint16)),
            ("fire mask", SDC.UINT8, np.array([[5, 5], [5, 8]], dtype=np.uint8)),
        ]
        for name, dtype, values in arrays:
            dataset = f.create(name, dtype, values.shape)
            dataset[:] = values
            if name == "fire mask":
                dataset.attr("legend").set(SDC.CHAR8, "8 nominal fire")
            dataset.endaccess()
        core = (
            'OBJECT = LOCALGRANULEID NUM_VAL = 1 VALUE = "MYD14.synthetic.hdf" '
            'END_OBJECT LOCALGRANULEID OBJECT = RANGEBEGINNINGDATE NUM_VAL = 1 VALUE = "2025-01-01" '
            'END_OBJECT RANGEBEGINNINGDATE OBJECT = RANGEBEGINNINGTIME NUM_VAL = 1 VALUE = "12:00:00" '
            'END_OBJECT RANGEBEGINNINGTIME OBJECT = RANGEENDINGDATE NUM_VAL = 1 VALUE = "2025-01-01" '
            'END_OBJECT RANGEENDINGDATE OBJECT = RANGEENDINGTIME NUM_VAL = 1 VALUE = "12:05:00" '
            'END_OBJECT RANGEENDINGTIME'
        )
        f.attr("Satellite").set(SDC.CHAR8, "Aqua")
        f.attr("ProcessVersionNumber").set(SDC.CHAR8, "6.2.3")
        f.attr("CoreMetadata.0").set(SDC.CHAR8, core)
        f.end()
        del f, dataset
        gc.collect()

    def _write_viirs(self, path: Path, *, include_fields: bool = True) -> None:
        with h5py.File(path, "w") as f:
            for key, value in {
                "ShortName": b"VNP14IMG", "PlatformShortName": b"SUOMI-NPP",
                "VersionID": b"002", "ProcessVersionNumber": b"3.1.9",
                "LocalGranuleID": b"sample.nc", "StartTime": b"2025-10-20 13:06:00.000",
                "EndTime": b"2025-10-20 13:12:00.000",
            }.items():
                f.attrs[key] = value
            if include_fields:
                for key, value in {
                    "FP_latitude": [1.0], "FP_longitude": [2.0],
                    "FP_confidence": [8], "FP_power": [4.5],
                    "FP_line": [1], "FP_sample": [1],
                }.items():
                    f.create_dataset(key, data=np.asarray(value))
                mask = f.create_dataset("fire mask", data=np.zeros((2, 2), dtype=np.uint8))
                mask[1, 1] = 8
                mask.attrs["legend"] = np.bytes_(b"8 nominal confidence fire pixel")

    def test_haversine_zero_and_one_degree(self):
        d = great_circle_km(0, 0, np.array([0, 0]), np.array([0, 1]))
        self.assertAlmostEqual(float(d[0]), 0.0, places=8)
        self.assertAlmostEqual(float(d[1]), 111.195, places=2)

    def test_viirs_reader_matches_pixel_and_mask_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.nc"
            self._write_viirs(path)
            result = inspect_viirs_granule(path, observation_latitude=1.0, observation_longitude=2.0)
        self.assertEqual(result["product"], "VNP14IMG")
        self.assertEqual(result["process_version"], "3.1.9")
        self.assertEqual(result["fire_mask_class"], 8)
        self.assertEqual(result["confidence_code_or_percent"], 8)
        self.assertEqual(result["frp_mw"], 4.5)
        self.assertAlmostEqual(result["distance_km"], 0.0, places=8)

    def test_viirs_reader_rejects_missing_required_datasets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "incomplete.nc"
            self._write_viirs(path, include_fields=False)
            with self.assertRaisesRegex(ValueError, "lacks required datasets"):
                inspect_viirs_granule(path, observation_latitude=1.0, observation_longitude=2.0)

    def test_modis_hdf4_reader_matches_pixel_mask_and_core_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MYD14.synthetic.hdf"
            self._write_modis(path)
            result = inspect_modis_granule(path, observation_latitude=1.0, observation_longitude=2.0)
        self.assertEqual(result["product"], "MYD14")
        self.assertEqual(result["granule_id"], "MYD14.synthetic.hdf")
        self.assertEqual(result["start_time"], "2025-01-01T12:00:00")
        self.assertEqual(result["fire_mask_class"], 8)
        self.assertEqual(result["confidence_code_or_percent"], 50)
        self.assertAlmostEqual(result["distance_km"], 0.0, places=8)


if __name__ == "__main__":
    unittest.main()
