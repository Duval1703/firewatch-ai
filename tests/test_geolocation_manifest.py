import unittest

import numpy as np

from src.firewatch.geolocation_manifest import (
    geolocation_filename_from_modis_attributes,
    geolocation_filename_from_viirs_attributes,
)


class GeolocationManifestTests(unittest.TestCase):
    def test_modis_reference_preserves_exact_input_filename(self):
        filename = "MYD03.A2025187.1345.061.2025188145533.hdf"
        self.assertEqual(
            geolocation_filename_from_modis_attributes({"MOD03 input file": f"/MODAPS/path/{filename}"}),
            filename,
        )

    def test_viirs_reference_uses_satellite_specific_filename_value(self):
        filename = b"VJ203IMG.A2025187.1230.021.2025187181751.nc"
        self.assertEqual(
            geolocation_filename_from_viirs_attributes({"VNP03IMG": np.asarray([filename])}),
            filename.decode(),
        )

    def test_modis_reference_rejects_ambiguous_or_missing_input(self):
        with self.assertRaises(ValueError):
            geolocation_filename_from_modis_attributes({})
        with self.assertRaises(ValueError):
            geolocation_filename_from_modis_attributes({
                "MOD03 input file": "/a/MOD03.x.hdf", "other 03 input file": "/b/MYD03.y.hdf",
            })


if __name__ == "__main__":
    unittest.main()
