import unittest
from datetime import date
from email.message import Message
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError

import pandas as pd

from src.firewatch.cmr_manifest import (
    DATA_REL,
    PRODUCTS,
    acquisition_id,
    build_query_url,
    entry_to_row,
    parse_bbox,
    write_manifest,
)
from src.firewatch.granule_download import (
    _open_response,
    _validate_signature,
    download_plan,
    validate_data_url,
    validate_plan,
)


class CMRManifestTests(unittest.TestCase):
    def test_bbox_parser_accepts_valid_bounds_and_rejects_invalid_order(self):
        self.assertEqual(parse_bbox("8, 1, 17, 14"), (8.0, 1.0, 17.0, 14.0))
        with self.assertRaises(ValueError):
            parse_bbox("17,1,8,14")

    def test_query_url_records_date_bbox_and_collection(self):
        url = build_query_url(
            short_name="VNP14IMG",
            version="002",
            start=date(2025, 10, 1),
            end=date(2025, 10, 31),
            bbox=(8, 1, 17, 14),
        )
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["short_name"], ["VNP14IMG"])
        self.assertEqual(params["version"], ["002"])
        self.assertEqual(
            params["temporal"],
            ["2025-10-01T00:00:00Z,2025-10-31T23:59:59Z"],
        )
        self.assertEqual(params["bounding_box"], ["8,1,17,14"])

    def test_acquisition_id_excludes_processing_timestamp(self):
        producer_id = "VJ214IMG.A2025274.0048.002.2025339035534"
        self.assertEqual(acquisition_id(producer_id), "VJ214IMG.A2025274.0048.002")

    def test_row_preserves_granule_lineage_and_selects_direct_data_link(self):
        entry = {
            "id": "G123-LPCLOUD",
            "collection_concept_id": "C123-LPCLOUD",
            "producer_granule_id": "VNP14IMG.A2025274.0118.002.2025274111358",
            "time_start": "2025-10-01T01:18:00.000Z",
            "time_end": "2025-10-01T01:24:00.000Z",
            "links": [
                {"rel": DATA_REL, "inherited": True,
                 "href": "https://search.earthdata.nasa.gov/search/granules?p=C123"},
                {"rel": DATA_REL, "href": "https://data.example/granule.nc"},
            ],
        }
        row = entry_to_row(
            entry,
            PRODUCTS[0],
            query_start=date(2025, 10, 1),
            query_end=date(2025, 10, 31),
            bbox=(8, 1, 17, 14),
        )
        self.assertEqual(row["cmr_entry_id"], "G123-LPCLOUD")
        self.assertEqual(row["acquisition_id"], "VNP14IMG.A2025274.0118.002")
        self.assertEqual(row["data_url"], "https://data.example/granule.nc")
        self.assertEqual(row["query_bbox_wsen"], "8,1,17,14")

    def test_writer_records_manifest_checksum_and_row_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            metadata = {"result_entries": 1}
            write_manifest(pd.DataFrame([{"platform": "SNPP"}]), metadata, path)
            saved = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(saved["manifest_sha256"], expected)
            self.assertEqual(saved["manifest_rows"], 1)

    def test_sample_plan_is_bounded_and_rejects_unapproved_urls(self):
        plan = pd.DataFrame([
            {"data_url":"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MYD14.061/a.hdf",
             "granule_size_cmr_mb":0.2,"producer_granule_id":"a"},
            {"data_url":"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/VNP14IMG.002/b.nc",
             "granule_size_cmr_mb":2.5,"producer_granule_id":"b"},
        ])
        validate_plan(plan, max_total_mb=10)
        with self.assertRaises(ValueError):
            validate_plan(plan, max_total_mb=2)
        too_many = pd.concat([plan, plan.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            validate_plan(too_many, max_total_mb=10)
        third = plan.iloc[[0]].copy()
        third.loc[:, "data_url"] = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD14.061/c.hdf"
        third.loc[:, "producer_granule_id"] = "c"
        validate_plan(pd.concat([plan, third], ignore_index=True), max_total_mb=10, max_files=3)
        with self.assertRaises(ValueError):
            validate_plan(plan, max_total_mb=10, max_files=41)
        with self.assertRaises(ValueError):
            validate_plan(plan, max_total_mb=251)
        with self.assertRaises(ValueError):
            validate_data_url("https://evil.example/lp-prod-protected/file.nc")

    def test_download_plan_resumes_only_checksum_verified_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.csv"
            pd.DataFrame([{
                "data_url":"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/VNP14IMG.002/a.nc",
                "granule_size_cmr_mb":0.000001,"producer_granule_id":"a",
            }]).to_csv(plan_path,index=False)
            output = root / "out"
            data = b"\x89HDF\r\n\x1a\nverified"

            def fake_download(row, *, output_dir, token, max_file_mb):
                target = output_dir / "a.nc"
                target.write_bytes(data)
                return {
                    "producer_granule_id":"a", "filename":"a.nc", "path":str(target),
                    "bytes":len(data), "sha256":hashlib.sha256(data).hexdigest(),
                    "downloaded_utc":"2025-01-01T00:00:00+00:00",
                }

            with patch("src.firewatch.granule_download.download_one", side_effect=fake_download) as mocked:
                first = download_plan(plan_path, output, token="secret", max_total_mb=2)
                self.assertEqual(mocked.call_count, 1)
            with patch("src.firewatch.granule_download.download_one", side_effect=AssertionError("must resume")):
                second = download_plan(plan_path, output, token="secret", max_total_mb=2)
            self.assertEqual(first, second)
            with self.assertRaisesRegex(ValueError, "exceed the configured aggregate size limit"):
                download_plan(plan_path, output, token="secret", max_total_mb=0.00001)
            saved = json.loads((output / "download_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["download_count"], 1)
            self.assertNotIn("secret", json.dumps(saved))

    def test_redirect_does_not_forward_bearer_token_to_other_host(self):
        class Response:
            status = 200
            headers = {"Content-Length":"0"}
            def __enter__(self): return self
            def __exit__(self, *_): return False

        class Opener:
            def __init__(self): self.requests=[]
            def open(self, request, timeout):
                self.requests.append(request)
                if len(self.requests)==1:
                    headers=Message(); headers["Location"]="https://cdn.example/granule.nc"
                    raise HTTPError(request.full_url,303,"See Other",headers,None)
                return Response()

        opener=Opener()
        with patch("src.firewatch.granule_download.build_opener",return_value=opener):
            response=_open_response(
                "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/a.nc",
                "do-not-leak-this-token",5,
            )
        self.assertEqual(opener.requests[0].get_header("Authorization"),"Bearer do-not-leak-this-token")
        self.assertIsNone(opener.requests[1].get_header("Authorization"))
        self.assertEqual(response.status,200)

    def test_viirs_netcdf4_signature_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"granule.nc"
            path.write_bytes(b"\x89HDF\r\n\x1a\nmock")
            _validate_signature(path)
            path.write_bytes(b"not a NetCDF/HDF5 file")
            with self.assertRaises(ValueError):
                _validate_signature(path)


if __name__ == "__main__":
    unittest.main()
