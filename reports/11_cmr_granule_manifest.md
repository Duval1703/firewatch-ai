# FIREWATCH AI — Stage 12: Reproducible NASA granule manifest

**Date:** 2026-11-14  
**Status:** Complete; CMR metadata queried and saved. No science granule files downloaded.

## Implementation

Added `src/firewatch/cmr_manifest.py`, a standard-library HTTP client for NASA CMR that:

- queries the five standard Level-2 collections matching our FIRMS source platforms (`VNP14IMG`, `VJ114IMG`, `VJ214IMG`, `MOD14`, `MYD14`);
- records each collection version, CMR entry ID, producer granule ID, normalized acquisition ID, collection concept, acquisition and update times, day/night flag, reported size, granule polygon metadata, direct data URL and browse URL;
- saves the exact per-collection request URLs, query bounds/window, CMR feed timestamps, and result/acquisition counts in companion metadata JSON;
- retains reprocessing variants as separate manifest rows and performs no source-data download.

Run from the project root:

```powershell
py -3.11 -m src.firewatch.cmr_manifest --start 2025-10-01 --end 2025-10-31 --bbox 8,1,17,14 --output data/reference/cmr_manifest_2025-10.csv
```

The command writes `data/reference/cmr_manifest_2025-10.csv` and `data/reference/cmr_manifest_2025-10.metadata.json`. The metadata snapshot time makes this dynamic catalog query auditable; future queries may differ as CMR updates records.

## October 2025 result

- 759 CMR entries returned across five products: VNP14IMG 165, VJ114IMG 158, VJ214IMG 172, MOD14 122, MYD14 142.
- 747 unique platform/acquisition IDs after removing only the 13-digit processing timestamp from producer IDs. NOAA-21 has 12 extra metadata rows for alternate processing of the same acquisitions; all rows and producer IDs remain in the manifest.
- All 759 records include a direct science-data URL and browse URL. Science URLs point to `lp-prod-protected`; catalog discovery does not itself grant the authenticated download. Browse URLs point to public browse imagery and are not replacements for HDF/NetCDF fire-mask and QA arrays.
- CMR `online_access_flag` is metadata and does not establish that the current user has Earthdata authorization.

## Verification

- Added five offline unit tests for bounding-box validation, request construction, acquisition/processing ID parsing, correct direct-link selection, and manifest checksum writing.
- `notebooks/11_cmr_granule_manifest.ipynb` executed successfully with no cell errors; it summarizes product counts and plots unique daily acquisitions while preserving alternate processing versions in the saved CSV.
- Live CMR query completed for all five collections. The metadata sidecar records the 759-row manifest SHA-256 as `bbf94498f5e22fb1ab9c1c614d6931e5f87ed265210bb6f054d8f3a44db373e9`. No granule content was downloaded and no credentials were requested or read.
- Full project suite `py -3.11 -m unittest discover -s tests -v`: **19 tests passed**. The existing Starlette/httpx deprecation warning appeared. Windows Jupyter emits a pyzmq Proactor-loop warning; `nbconvert` exits successfully, writes outputs, and the saved notebook has no error-output cells.

## Next step

The next code stage can make authenticated access explicit and bounded: select one or two example granules, check account/access configuration without printing secrets, retrieve to a dedicated staging directory with checksum/size verification, and prototype the HDF/NetCDF fire-mask/QA read. Do not bulk-download all 759 entries until format, storage requirements, and common-coverage method are demonstrated on the small sample.

## Parser environment check

The active Python 3.11 has `h5py` available, but `netCDF4`, `pyhdf`, GDAL (`osgeo`), Rasterio, xarray, and `earthaccess` are not installed. VIIRS C2 swaths use NetCDF4/HDF5 and can be probed with h5py, while MODIS L2 granules are HDF4 and need a compatible reader (for example pyhdf or GDAL). The metadata client itself uses only Python's standard HTTP/JSON library plus the existing pandas dependency. No packages were added during this stage.

Final full test suite after checksum support: `py -3.11 -m unittest discover -s tests -v` — **19 tests passed**. One existing upstream Starlette deprecation warning about using `httpx` with TestClient was emitted; no failures.


