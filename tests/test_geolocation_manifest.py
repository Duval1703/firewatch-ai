import json
from io import BytesIO
import unittest
from unittest.mock import patch

import numpy as np

from src.firewatch.geolocation_manifest import (
    geolocation_filename_from_modis_attributes,
    geolocation_filename_from_viirs_attributes,
    query_exact_geolocation_manifest,
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

    def test_exact_manifest_selects_direct_data_and_browse_links(self):
        granule_id = "VNP03IMG.A2025187.1230.002.2025187150000.nc"
        reference = {
            "geolocation_short_name": "VNP03IMG",
            "cmr_version": "2",
            "geolocation_granule_id": granule_id,
        }
        payload = {
            "feed": {
                "entry": [{
                    "producer_granule_id": granule_id,
                    "links": [
                        {"rel": "http://esipfed.org/ns/fedsearch/1.1/data#", "inherited": True,
                         "href": "https://search.earthdata.nasa.gov/search/granules?id=entry"},
                        {"rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                         "href": "https://data.example/geolocation.nc"},
                        {"rel": "http://esipfed.org/ns/fedsearch/1.1/browse#",
                         "href": "https://data.example/preview.jpg"},
                    ],
                }],
            },
        }
        with patch(
            "src.firewatch.geolocation_manifest.urlopen",
            return_value=BytesIO(json.dumps(payload).encode()),
        ):
            rows, metadata = query_exact_geolocation_manifest([reference])

        self.assertEqual(rows[0]["data_url"], "https://data.example/geolocation.nc")
        self.assertEqual(rows[0]["browse_url"], "https://data.example/preview.jpg")
        self.assertEqual(metadata["granule_files_downloaded"], 0)


if __name__ == "__main__":
    unittest.main()
