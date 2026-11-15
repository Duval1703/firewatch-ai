# FIREWATCH AI — Stage 17: Stratified 2025 source-pixel validation

**Date:** 2026-11-14  
**Status:** All 39 planned granules verified and inspected. Source-pixel correspondence passed across the selected engineering sample; no event-identity or detection-accuracy claim is made.

## Download integrity

The downloaded manifest matches the SHA-256 of `data/reference/validation_granule_plan_2025.csv`. All 39 planned filenames were present; each file's byte count and SHA-256 matched the `download_manifest.json`. Download total: **72,722,137 bytes** (69.353 MiB / 72.722 decimal MB), below the configured 100 MB hard cap. CMR's size sum was 69.353 MiB and matched the actual byte total for this sample. The 39 files are stored under `data/reference/granules/validation_2025/`, which is Git-ignored.

Products: 7 MOD14, 8 MYD14, 8 VNP14IMG, 8 VJ114IMG, and 8 VJ214IMG. MODIS Collection 061 files were opened as HDF4 with `pyhdf`; VIIRS Collection 002 files were opened as NetCDF4/HDF5 with `h5py`.

## Pixel-join protocol

Notebook `notebooks/15_stratified_pixel_validation.ipynb` verifies every file before reading it. For each of the 39 sample observations, it:

1. Opens the same-source L2 granule named in the sample-plan CMR URL.
2. Verifies the original FIRMS observation timestamp is inside the granule's native time interval.
3. Computes haversine distance from the FIRMS coordinate to every active-fire pixel record in that granule and selects the nearest.
4. Uses the listed native line/sample to read the corresponding fire-mask class.
5. Retains product, collection, processing version, native confidence meaning, FRP, candidate-presence label, and file SHA-256 in row-level output.

## Results

- **39/39** observation times fall within the selected L2 granule intervals.
- **39/39** nearest native active-fire pixel centers are within 50 m of the FIRMS CSV coordinate. Overall distance range is **0.15–7.17 m**; median **0.53 m**.
- **39/39** nearest pixels have native fire-mask class 7, 8, or 9: 4 low, 31 nominal, and 4 high-confidence classes by each product's embedded legend.
- Sample candidate status is 19 with a cross-sensor edge and 20 without one under the 1 km / 3 h threshold. Among the latter, all 20 still resolve to an active-fire pixel in their own source granule (1 class-7, 17 class-8, 2 class-9 masks). This is direct evidence that “no cross-sensor candidate link” cannot be interpreted as “no source detection.”
- All 15 MODIS (Terra/Aqua) nearest-point distances are below 7.18 m; the 24 VIIRS distances are below 0.61 m. These distributions reflect source geolocation/encoding precision, not sensor resolution or accuracy relative to ground truth.

Native confidence values remain distinct: MODIS `FP_confidence` is a percent (33–91% in the Terra sample; 60–100% in the Aqua sample), while VIIRS `FP_confidence` uses categorical codes 7–9. FRP is kept as a source attribute and was not compared across products as if calibrated. The masks are each algorithm's own output, not an independent reference.

## Interpretation

This supports two engineering claims: the matched CMR granule selection is coherent for these sample rows, and the HDF4/HDF5 readers correctly join the normalized FIRMS points to source-native fire-pixel coordinates and mask cells. It does **not** show that two different satellites observed the same physical fire, nor estimate association precision/recall, false alarms, missed detections, or true-fire counts.

The pilot intentionally sampled one row per available Cameroon quarter × satellite × candidate-status stratum. Each row was required to have a CMR time/polygon match; this source-matched selection conditions the sample and inflates expected correspondence. The 39/39 result is therefore a linkage/reader check, not a random validation accuracy estimate. Candidate status is also a thresholded relationship label, not ground truth. A future model needs independent incident/perimeter references and valid observation opportunities derived from pixel QA/coverage.

## Artifacts and verification

- Executed `notebooks/15_stratified_pixel_validation.ipynb` end-to-end. It embeds row-level outputs, aggregate tables, and a residual plot.
- Saved `data/processed/source_pixel_validation_2025_stratified.csv` and companion `.metadata.json` with source manifest checksums, row counts, mask counts, and limits.
- Added an offline synthetic HDF4 regression test to ensure the MODIS reader preserves CoreMetadata time/granule lineage and aligns line/sample to a class-8 mask cell. The VIIRS synthetic HDF5 tests remain in place.
- Full project suite after this addition: **29 tests passed**. The Windows pyzmq Proactor warning during notebook execution and the existing Starlette/httpx deprecation warning remain non-fatal.
- No GPU use was necessary for file hashing or native swath pixel joins. No anomaly/classification model was trained because there are still no independent labels or validated coverage-derived negative examples.

## Next

Use the 39 row-level checks to expand the reusable source-pixel validation pipeline. Then prioritize coverage-opportunity mapping and independent reference-data linkage. Only after those exist should we decide whether a scientific anomaly model can be trained/evaluated; the present data support descriptive activity and evidence links but not a defensible classifier.
