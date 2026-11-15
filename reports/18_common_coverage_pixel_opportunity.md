# Stage 19: Common-coverage pixel opportunity pilot

**Date:** 2026-11-14  
**Status:** Two-swath geolocation and fire-mask pilot completed; interpretation remains bounded to the selected observations and nearest pixels.

## Purpose

This stage tests whether the 1 km Aqua MODIS and 375 m NOAA-21 VIIRS swaths provide valid, classified pixels at each other's reported observation coordinates. It follows stage 18's exact geolocation lineage plan and preserves the distinction between “no cross-sensor candidate association” and “no valid observation opportunity.”

## Inputs and integrity

The local download manifest references the exact saved geolocation plan. Both plan SHA-256 and per-file SHA-256/byte counts were verified in notebook 17 before reading pixel arrays:

| File | Bytes | SHA-256 |
|---|---:|---|
| MYD03.A2025187.1345.061.2025188145533.hdf | 34,574,718 | `083146b1a1b71b49eff2852be9390fc9c2012c9b0b27cfea0c57a6da9a67fc4c` |
| VJ203IMG.A2025187.1230.021.2025187181751.nc | 193,640,420 | `b87e4523fbbe780d3cdd9cfc884ebd9c288c815af24ad275eb01852178f55e10` |

The geolocation shapes are MODIS `(2040, 1354)` and VIIRS `(6432, 6400)`. Each matched its exact paired Level-2 fire-mask shape before sampling. The notebook processes geolocation rows in 128-row chunks and does not materialize the full VIIRS latitude or longitude arrays.

## Method

For each of the two CSV point coordinates, the analysis exhaustively finds its nearest valid pixel center in each swath using haversine distance, then retrieves the fire-mask class at the same row/column from that swath's native Level-2 active-fire product. Fill values and out-of-range coordinates are excluded. VIIRS per-pixel quality flags are recorded, with bits 1, 2, and 4 (input invalid, pointing bad, terrain bad) used for the pilot's usable flag. The raw flags and meanings are retained.

MOD03 Collection 6.1 `gflags` values are recorded and decoded for invalid input data, no ellipsoid intersection, no valid terrain, inferior/missing DEM, invalid sensor range, and near-limb geometry, following the [NASA MOD03 Collection 6.1 file specification](https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD03_c61). This pilot does not reduce those flags to a single validity score.

Mask categories remain distinct: water (3), cloud (4), clear land (5), unknown (6), and fire confidence classes (7–9), plus missing/not-processed categories (0–2). A clear-land class means the product classified that sampled pixel as clear land; it does not guarantee fire detectability.

## Results

The observations are Aqua at 13:48 UTC and NOAA-21 at 12:30 UTC on 2025-07-06, 78 minutes apart and about 0.254 km apart by supplied coordinates.

| Target coordinate | Queried swath | Nearest-center distance | Mask at nearest pixel | QA note |
|---|---|---:|---|---|
| Aqua observation | Aqua MODIS | 0.0016 km | class 8, nominal fire | MOD03 gflags 0 |
| Aqua observation | NOAA-21 VIIRS | 0.2151 km | class 5, clear land | VIIRS quality flag 0; usable under selected bit screen |
| NOAA-21 observation | Aqua MODIS | 0.2532 km | class 8, nominal fire | MOD03 gflags 0 |
| NOAA-21 observation | NOAA-21 VIIRS | 0.0002 km | class 8, nominal fire | VIIRS quality flag 0; usable under selected bit screen |

The two source observations each map closely to a native fire pixel, independently corroborating their source-row-to-granule linkage. At the Aqua point, the earlier NOAA-21 swath's nearest pixel is clear land. At the NOAA-21 point, the later Aqua swath's nearest pixel is nominal fire. This asymmetric cross-swath mask pattern is scientifically useful for examining the candidate-association rule and temporal/resolution effects, but does not prove that one sensor missed a fire. The observations are not simultaneous; the products use different spatial resolutions, footprints, algorithms, and detection thresholds. Nearest-center distance alone also does not establish that two pixel footprints overlap.

## Artifacts and verification

- Implementation: `src/firewatch/coverage_validation.py`
- Runnable notebook: `notebooks/17_common_coverage_pixel_opportunity.ipynb`
- Output table: `data/processed/common_coverage_pixel_opportunity_2025_pilot.csv`
- Tests: `tests/test_coverage_validation.py`
- Notebook executed successfully with all cells error-free. Full suite: **35 tests passed**; `git diff --check` passed. Non-blocking existing Starlette/httpx deprecation warning remains.

## Limits and next work

This is a single, deliberately selected association and not a representative accuracy evaluation. It does not yield sensitivity, precision/recall, false-negative rates, fire duration, ground truth, or event identity. The pixel-center lookup does not use true pixel polygons, view-angle uncertainty thresholds, MODIS land/water flags, or a calibrated cross-sensor detection model. Next, extend the same approach to a stratified set of linked and unlinked detections, retain opportunity classes and QA, then evaluate harmonization thresholds against independent reference data. Only after that should an anomaly model be trained or presented as validated.
