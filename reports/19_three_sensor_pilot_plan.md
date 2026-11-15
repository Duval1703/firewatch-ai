# Stage 20: Three-sensor geolocation extension plan

**Date:** 2026-11-14  
**Status:** Exact NOAA-20 companion resolved; one-file dry-run passed; download pending.

## Why this extension

The first common-coverage analysis compared Aqua and NOAA-21 for the July 6, 2025 Q3 Cameroon sample. The 39-row stratified sample also contains a NOAA-20 detection in the same Q3 neighborhood. Adding NOAA-20 permits a three-instrument view of the same area while using a second VIIRS platform, whose observation time differs from the NOAA-21 and Aqua overpasses.

The selected records are the actual Aqua and NOAA-20 sample rows. The Aqua observation is at 13:48 UTC (11.83500 N, 14.99200 E); NOAA-20 is at 11:39 UTC (11.84300 N, 14.99202 E). Their centers are 0.889563 km apart and their observations are 129 minutes apart, within the recorded 1 km / 3 h candidate-link thresholds. NOAA-21 remains the prior 12:30 UTC point and is 78 minutes from Aqua.

## Exact source lineage and transfer bound

The NOAA-20 L2 file `VJ114IMG.A2025187.1136.002.2025187162721.nc`, already staged and pixel-validated, names this exact geolocation input in its processing metadata:

`VJ103IMG.A2025187.1136.021.2025187154117.nc`

CMR exact-ID lookup resolved collection version 2.1, the direct LAADS science URL, and a size estimate of **177.333 MiB**. The new plan contains one file and passes the downloader's explicit 200 MiB aggregate cap in dry-run mode. It has a separate output directory so its plan/checksum manifest does not collide with the existing two-file geolocation pilot manifest.

## Reproducibility and artifacts

- Notebook: `notebooks/18_three_sensor_geolocation_plan.ipynb`; executed successfully against the downloaded Q3 L2 sample and live CMR exact-ID metadata.
- One-file plan: `data/reference/geolocation_coverage_plan_2025_noaa20.csv` and its `.metadata.json` sidecar.
- Dry-run: accepted the exact VJ103IMG ID at 177.333 MiB; no network transfer occurred.
- The notebook selects the sample rows, recomputes their great-circle separation/time gap, asserts the 1 km / 3 h criteria, parses the exact input ID from the NOAA-20 L2 file, and queries CMR. This is selection by known candidate status and is not an unbiased validation sample.

## Next step and limits

After the user stages the single NOAA-20 geolocation granule, extend the three-sensor pixel-opportunity notebook to query the Aqua, NOAA-20, and NOAA-21 geolocation/mask grids at all three actual observation coordinates. Differences will remain time-, footprint-, resolution-, QA-, and algorithm-dependent. The case study cannot estimate population detection accuracy or prove fire continuity.
