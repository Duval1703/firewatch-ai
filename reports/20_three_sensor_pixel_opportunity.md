# Stage 21: Three-sensor pixel-opportunity case study

**Date:** 2026-11-14  
**Status:** Complete for one selected Q3 candidate neighborhood; not a population accuracy evaluation.

## Input integrity and grid matching

The third companion, `VJ103IMG.A2025187.1136.021.2025187154117.nc`, was verified against the NOAA-20 one-file download manifest: 185,946,697 bytes and SHA-256 `b25a295b3cbe262800f9016a5e9db5527541e021e9604e32e6ee28782a88e60a`. Notebook 19 also rechecked plan hashes and SHA-256/byte counts for the two earlier companions. Shapes matched paired L2 masks exactly:

- Aqua MYD03 / MYD14: `(2040, 1354)`.
- NOAA-20 VJ103IMG / VJ114IMG: `(6464, 6400)`.
- NOAA-21 VJ203IMG / VJ214IMG: `(6432, 6400)`.

The VIIRS geolocation grids are processed in row chunks. The analysis finds each target's nearest valid geolocation center over the full swath, then reads the mask class from the same row/column of the corresponding active-fire product. It records VIIRS per-pixel quality flags and MODIS `gflags`. The 9 resulting combinations are in the CSV and visualized as a target-coordinate × swath mask-class matrix.

## Results

The selected records on 2025-07-06 are Aqua at 13:48 UTC, NOAA-21 at 12:30 UTC, and NOAA-20 at 11:39 UTC. Aqua–NOAA-21 centers are about 0.254 km apart with 78 minutes between observations; Aqua–NOAA-20 centers are about 0.890 km apart with 129 minutes between observations.

| Target coordinate | Aqua MODIS | NOAA-20 VIIRS | NOAA-21 VIIRS |
|---|---|---|---|
| Aqua (13:48 UTC) | 0.0016 km; class 8 nominal fire | 0.1446 km; class 5 clear land | 0.2151 km; class 5 clear land |
| NOAA-20 (11:39 UTC) | 0.2192 km; class 5 clear land | 0.0005 km; class 8 nominal fire | 0.2411 km; class 8 nominal fire |
| NOAA-21 (12:30 UTC) | 0.2532 km; class 8 nominal fire | 0.1543 km; class 1 bowtie | 0.0002 km; class 8 nominal fire |

All three source coordinates map to a nominal-fire class in their own active-fire product, at sub-pixel-center distances. The two cross-swath clear-land values occur at Aqua's later coordinate in the earlier NOAA-20 and NOAA-21 fire masks. The NOAA-20 mask at the NOAA-21 target is class 1, **bowtie**, so it is not a valid clear-land opportunity and must not be coded as a clear non-fire. These spatially adjacent but time-separated mask patterns motivate harmonizing observation time, footprint/resolution, product QA, and mask category before associating detections.

## What this does and does not establish

It establishes source-grid linkage and the exact mask/quality categories nearest to three candidate-linked FIRMS coordinates. It does not establish event identity, true fire/no-fire labels, detection misses, continuous burning, detection probabilities, or accuracy metrics. Nearest center is not footprint intersection. The overpasses are asynchronous (up to 129 minutes apart), and the products differ in sensor resolution and fire algorithms. The three observations were purposefully selected from a candidate-linked stratum, not sampled to estimate population performance.

## Artifacts and checks

- Runnable notebook: `notebooks/19_three_sensor_pixel_opportunity.ipynb`.
- Machine-readable output: `data/processed/three_sensor_pixel_opportunity_2025_pilot.csv`.
- Exact NOAA-20 geolocation plan and download manifest: `data/reference/geolocation_coverage_plan_2025_noaa20.csv`, `data/reference/granules/geolocation_noaa20_pilot/download_manifest.json`.
- Initial notebook output incorrectly mapped VIIRS class 1 through a MODIS-compatible shared label map. A schema audit exposed the sensor-specific meaning (VIIRS class 1 is bowtie; MODIS class 1 is obsolete not-processed). Corrected the implementation to retain separate MODIS/VIIRS class dictionaries and updated the visualization to plot semantic labels rather than shared numeric classes. Notebook 19 was re-executed; the full suite now has 36 passing tests, including a sensor-specific class-one regression test. `git diff --check` was rerun.

## Next work

Move from this selected case to a broader validation design: acquire and inspect source L2/geolocation pairs for a deterministic, stratified subset of linked and unlinked records, preserve not-processed/cloud/water/clear-land opportunity states, and compare association thresholds against independent reference data. Avoid training or presenting an anomaly detector as validated until the sample and labels support it.
