# FIREWATCH AI — Stage 14: Bounded authenticated granule retrieval

**Date:** 2026-11-14  
**Status:** Downloader implemented and offline-verified; no science files retrieved.

## Access finding

An anonymous request to each selected LP DAAC science URL returned a redirect to NASA's protected object delivery, followed by HTTP 403. The plan remains metadata-only: two granules, approximately 2.727 MB by CMR estimates. No credentials were entered or stored, and no granule bytes were downloaded.

## Implementation

Added `src/firewatch/granule_download.py`, a deliberately narrow pilot downloader. It:

- accepts no more than two rows and only HTTPS science URLs on the LP DAAC protected product host, ending in `.hdf` or `.nc`;
- enforces the configured maximum plan size (10 MB by default), then independently caps actual streamed bytes across the plan and each file;
- reads `FIREWATCH_EARTHDATA_TOKEN` from the invoking process only; it does not print, persist, or include the token in error messages;
- follows HTTPS redirects and sends the bearer token only to the original host, never to a different host;
- refuses to overwrite existing granules or partial files, stages each transfer as `.part`, validates HDF4/HDF5 signature and content length, then atomically renames it;
- writes `download_manifest.json` with file sizes, UTC retrieval timestamps, and SHA-256 digests after all planned transfers succeed.

The utility is intentionally scoped to the current small source-lineage pilot. It does not imply that CMR polygon/time overlap is valid pixel coverage, nor that the two detections represent one fire.

## Verification

- `py -3.11 -m src.firewatch.granule_download --dry-run` validated the two planned granules and explicitly reported no network access.
- Eight focused CMR/download tests passed, including plan bounds, approved URL validation, redirect token isolation, and VIIRS NetCDF4 signature validation.
- Full project suite: **22 tests passed**. An existing Starlette/httpx deprecation warning remains; it did not affect test results.
- No Earthdata token is configured in the project. The actual download remains pending local token setup and LP DAAC authorization.

## Next step

After the user configures an Earthdata Login token in their local PowerShell process, retrieve the two files into `data/reference/granules/oct2025_pilot/`. Then inspect VIIRS datasets with `h5py`, select a compatible HDF4 reader for Aqua MODIS, and compare the actual pixel masks/QA and source coordinates with the chosen CSV records. Record any reader/environment changes before attempting broader sampling.
