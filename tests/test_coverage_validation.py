import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
from pyhdf.SD import SD, SDC

from src.firewatch.coverage_validation import nearest_viirs_geolocation, paired_mask_class, paired_viirs_point


class CoverageValidationTests(unittest.TestCase):
    def make_viirs_pair(self, root: Path) -> tuple[Path, Path]:
        geo_path = root / "geo.nc"
        mask_path = root / "mask.nc"
        latitude = np.array([[10.0, 10.0], [11.0, -999.9]], dtype=np.float32)
        longitude = np.array([[20.0, 21.0], [20.0, -999.9]], dtype=np.float32)
        with h5py.File(geo_path, "w") as file:
            group = file.create_group("geolocation_data")
            lat = group.create_dataset("latitude", data=latitude)
            lat.attrs["_FillValue"] = np.float32(-999.9)
            lon = group.create_dataset("longitude", data=longitude)
            lon.attrs["_FillValue"] = np.float32(-999.9)
            group.create_dataset("quality_flag", data=np.zeros((2, 2), dtype=np.uint8))
        with h5py.File(mask_path, "w") as file:
            file.create_dataset("fire mask", data=np.array([[5, 4], [8, 0]], dtype=np.uint8))
        return geo_path, mask_path

    def test_nearest_viirs_filters_fill_and_retains_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            geo, _ = self.make_viirs_pair(Path(temp))
            result = nearest_viirs_geolocation(geo, 11.0, 20.0, chunk_rows=1)
        self.assertEqual((result["row"], result["column"]), (1, 0))
        self.assertAlmostEqual(result["distance_km"], 0.0, places=8)
        self.assertEqual(result["quality_flag"], 0)

    def test_paired_viirs_lookup_requires_matching_grid_and_reads_mask(self):
        with tempfile.TemporaryDirectory() as temp:
            geo, mask = self.make_viirs_pair(Path(temp))
            result = paired_viirs_point(geo, mask, 11.0, 20.0)
            self.assertEqual(result["fire_mask_class"], 8)
            self.assertEqual(result["fire_mask_label"], "fire_nominal_confidence")
            self.assertTrue(result["quality_flag_usable"])

    def test_mask_labels_keep_water_cloud_and_clear_land_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mask.nc"
            with h5py.File(path, "w") as file:
                file.create_dataset("fire mask", data=np.array([[3, 4, 5]], dtype=np.uint8))
            self.assertEqual(paired_mask_class(path, 0, 0, format="hdf5")["fire_mask_label"], "water")
            self.assertEqual(paired_mask_class(path, 0, 1, format="hdf5")["fire_mask_label"], "cloud")
            self.assertEqual(paired_mask_class(path, 0, 2, format="hdf5")["fire_mask_label"], "clear_land")

    def test_class_one_is_sensor_specific_bowtie_for_viirs_and_obsolete_for_modis(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            viirs_path = root / "viirs.nc"
            with h5py.File(viirs_path, "w") as file:
                file.create_dataset("fire mask", data=np.array([[0, 1, 2]], dtype=np.uint8))
            self.assertEqual(paired_mask_class(viirs_path, 0, 1, format="hdf5")["fire_mask_label"], "bowtie")
            self.assertEqual(paired_mask_class(viirs_path, 0, 2, format="hdf5")["fire_mask_label"], "glint")
            modis_path = root / "modis.hdf"
            file = SD(str(modis_path), SDC.CREATE | SDC.WRITE)
            mask = file.create("fire mask", SDC.UINT8, (1, 2))
            mask[:] = np.array([[0, 1]], dtype=np.uint8)
            mask.endaccess()
            file.end()
            self.assertEqual(paired_mask_class(modis_path, 0, 1, format="hdf4")["fire_mask_label"], "not_processed_obsolete")


if __name__ == "__main__":
    unittest.main()
