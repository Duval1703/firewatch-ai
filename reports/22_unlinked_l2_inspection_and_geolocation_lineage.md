# Stage 23: Unlinked L2 inspection and geolocation-lineage exception

**Date:** 2026-11-14  
**Status:** L2 verified and inspected; exact geolocation lineage exception documented; companion plan ready for an explicit reprocessing-consistency check.

## Download integrity and full-swath mask

The one-file NOAA-20 plan was verified against its saved plan hash and SHA-256 manifest. The downloaded file is `VJ114IMG.A2025261.1330.002.2025261205555.nc`, 2,836,999 bytes, SHA-256 `b23479ae7b10861151db2e2a8d7cabaf35f497245e2361fd96e63c9f26f73cf8`.

Its native fire mask has shape `(6464, 6400)` and 16 active-fire records. Full-grid mask class counts:

| Class | VIIRS class meaning | Pixels |
|---:|---|---:|
| 0 | Not processed (non-zero QF) | 2,080 |
| 1 | Bowtie | 5,326,336 |
| 2 | Glint | 2,637,588 |
| 3 | Water | 4,310,442 |
| 4 | Cloud | 9,583,401 |
| 5 | Clear land | 19,509,735 |
| 6 | Unclassified | 2 |
| 7 | Fire, low confidence | 0 |
| 8 | Fire, nominal confidence | 16 |
| 9 | Fire, high confidence | 0 |

The global histogram does not identify the class at the Aqua coordinate. That requires paired geolocation. The 16 nominal-fire records are in this NOAA-20 granule, but none was a candidate link to the selected Aqua point under the archive 1 km / 3 h rule; that distinction is precisely what the next pixel lookup is intended to inspect.

## Provenance issue found

The NOAA-20 L2 file names its processing geolocation input as:

`VJ103IMG.A2025261.1330.021.2025261182205.nc`

An exact CMR query for this producer granule ID returns no record. The NOAA-20 product's official LAADS archive directory for collection 5201 and day 261 lists a same-acquisition reprocessed geolocation file:

`VJ103IMG.A2025261.1330.021.2025267192836.nc`

CMR resolves the reprocessed file to collection version 2.1, with reported size 182.365 MiB. Its acquisition day, scan start time, and collection segment match, but its trailing processing timestamp differs from the ID recorded in the L2 metadata. Therefore this is not asserted to be the L2 file's original geolocation input. The original ID, unresolved exact lookup, alternate ID, and reason are all retained in plan metadata. The [LAADS archive directory](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5201/VJ103IMG/2025/261/) supports the currently listed processing instance.

The Aqua source observation's exact companion, `MYD03.A2025261.1405.061.2025262150419.hdf`, resolves through CMR at 31.719 MiB. The combined two-file plan (Aqua exact companion plus NOAA-20 reprocessed candidate) is 214.084 MiB by CMR estimates and passes the two-file/250 MiB downloader dry run.

## Scientific safeguard for the next step

Before using reprocessed NOAA-20 coordinates to sample the L2 mask, compare its latitude/longitude at every NOAA-20 L2 `FP_line` / `FP_sample` active-fire index with the L2 embedded `FP_latitude` / `FP_longitude`. Report median, maximum, and percentile coordinate residuals and inspect any outliers. A low source-fire-pixel residual supports consistency at those locations but cannot prove unchanged geolocation across the entire swath. If the residuals are material or indices do not align, do not interpret the cross-swath class as a reliable opportunity result; keep it unresolved and pursue the archived original or another independently justified source.

## Mask-label correction recorded

This inspection also exposed a prior label bug: the three-sensor notebook initially applied MODIS mask class semantics to VIIRS class numbers. VIIRS class 1 is bowtie and class 2 is glint; MODIS class 1/2 are obsolete not-processed classes. The implementation now uses separate sensor-specific mappings, carries the native mask legend into output, and plots semantic categories. Notebook 19 was re-executed with corrected labels. A regression test now explicitly checks the class-one difference.

## Artifacts and verification

- Notebook: `notebooks/21_unlinked_overpass_geolocation_plan.ipynb` (executed without errors).
- Geolocation plan: `data/reference/unlinked_opportunity_geolocation_plan_2025.csv` and `.metadata.json`.
- Updated coverage implementation: `src/firewatch/coverage_validation.py`.
- Regression tests: `tests/test_coverage_validation.py`; full test suite: **36 passed**.
- The geolocation plan dry run passed with 2 files / 214.084 CMR MiB and no network transfer. Notebook 19 was regenerated with corrected labels. `git diff --check` passed.

## Next step

Download the two planned geolocation files to `data/reference/granules/unlinked_opportunity_geolocation_pilot`, run the source-fire-index consistency check, and only then decide whether to report the Aqua-point NOAA-20 mask class as usable coverage evidence.
