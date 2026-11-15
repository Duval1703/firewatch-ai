# FIREWATCH AI — Stage 13: Bounded cross-sensor granule sample plan

**Date:** 2026-11-14  
**Status:** Completed reproducible sample selection; no science files retrieved.

## Selection

From October 2025 archive records, reran candidate association at 1 km / 3 hours and filtered to MODIS–VIIRS pairs. Selected the candidate with the smallest time difference, breaking ties by distance. This is a deterministic way to choose a small lineage/reader pilot, not a claim that the pair represents a shared fire.

- Candidate ID: `627beea4e144d68a848088c9471a445fc6fa70915ecddf0527761e117e39956d`
- Center distance: 0.555 km; acquisition time difference: 16 minutes.
- Aqua MODIS CSV observation: 2025-10-20 13:26 UTC, 11.01460°N, 13.85750°E. Matching CMR product: MYD14 Collection 061 granule `MYD14.A2025293.1325.061.2025294143419`, interval 13:25–13:30 UTC, CMR reported size 0.221992 MB.
- Suomi-NPP VIIRS CSV observation: 2025-10-20 13:10 UTC, 11.01529°N, 13.86254°E. Matching CMR product: VNP14IMG Collection 002 granule `VNP14IMG.A2025293.1306.002.2025293205847`, interval 13:06–13:12 UTC, CMR reported size 2.504533 MB.
- Each observation time falls within its selected granule interval and each center lies inside that granule’s CMR catalog polygon. This is catalog-level extent matching only; it does not establish pixel QA, source-pixel identity, or actual coverage.

The pair totals about **2.727 MB** by CMR-reported sizes. Science URLs are in protected NASA product storage and require appropriate access. No downloads or credentials were used.

## Artifacts and verification

- `notebooks/12_candidate_granule_selection.ipynb` recalculates the edge, verifies the parent manifest SHA-256, locates matching time/polygon granules, saves a two-row plan and plots the overpass intervals. Executed end-to-end with no error cells.
- `data/reference/cmr_sample_plan_oct2025.csv` has one manifest row per source observation/granule; companion `.metadata.json` records selection rule, candidate ID, parent manifest hash, and that zero files were downloaded.
- Source manifest: 759 metadata entries, SHA-256 `bbf94498f5e22fb1ab9c1c614d6931e5f87ed265210bb6f054d8f3a44db373e9`.

## Next implementation step

After setting up Earthdata access safely, download these two files only. Verify byte sizes and checksums where provided; inspect the VIIRS NetCDF4/HDF5 arrays using installed `h5py`; add a compatible HDF4 reader for MYD14; reconcile the two CSV detections with the source fire-pixel arrays. This verifies source lineage. Continue to treat cross-sensor event identity as unvalidated until common valid coverage and an independent reference are available.
