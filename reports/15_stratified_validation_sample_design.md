# FIREWATCH AI — Stage 16: 2025 stratified validation sample design

**Date:** 2026-11-14  
**Status:** Candidate-presence pipeline and 40-stratum sample plan built and notebook-executed; 39 granules identified, not yet downloaded.

## Full-year source inventory and association frame

Generated `data/reference/cmr_manifest_2025.csv` by querying CMR metadata for the five L2 source products across 2025 and the Cameroon-centered bounding box `8,1,17,14`. The manifest contains **8,862 records** (1,624 MOD14, 1,665 MYD14, 1,845 VNP14IMG, 1,890 VJ114IMG, 1,838 VJ214IMG) and retains processing variants. Its SHA-256 is `6b7d4410af4d895aa087a5fd35560efef2d0c70f9c72aa8b42342098d160f923`. No science granules were retrieved in this metadata query.

Recomputed 1 km / 3 hour links month by month over the local 2025 archive using a three-hour halo at each month boundary. The halo includes adjacent-year archive records when available; the source archive begins on 2025-01-01, so observations before that boundary are unavailable. The candidate-presence output contains **712,234** source observations, all structurally valid. **106,069** observations are incident to at least one MODIS–VIIRS candidate edge; the other **606,165** have no edge under this specific envelope. This is an association-presence flag, not a fire/no-fire label.

Monthly edge counts demonstrate why the selected sample is stratified: 33,395 (Jan), 47,839 (Feb), 12,149 (Mar), 1,076 (Apr), 394 (May), 243 (Jun), 18 (Jul), 1 (Aug), 5 (Sep), 332 (Oct), 2,066 (Nov), and 10,850 (Dec). These totals are candidate edges, not unique events; dense many-to-many neighborhoods may contribute several edges per detection.

## Sampling and granule matching protocol

`src/firewatch/validation_sampling.py` uses a stable SHA-256 ranking to select one observation per quarter × satellite × candidate-presence stratum after restricting points to Cameroon ADM0. It scans the deterministic ranking until it finds a sample observation with a CMR match, retaining the number of attempts; a no-match stratum retains its top-ranked point in the audit. Each selected point is matched to a same-platform Level-2 CMR acquisition using:

1. FIRMS satellite → source product mapping (Aqua/MYD14, Terra/MOD14, SNPP/VNP14IMG, N20/VJ114IMG, N21/VJ214IMG).
2. Observation time inside the CMR granule interval.
3. Point inside the CMR catalog polygon.
4. Closest granule interval midpoint; where a processing-revision set exists, latest CMR update for the selected acquisition.

The audit retains every one of the **40** possible strata. **39** have a selected point with CMR metadata and **one is explicitly empty**: Terra Q3 has no candidate-linked Cameroon observation in the 2025 local frame. There are no nonempty strata that failed the CMR time/polygon match. The 39 observations map to **39 unique granules**: 7 MOD14, 8 MYD14, 8 VNP14IMG, 8 VJ114IMG, and 8 VJ214IMG. The sum of CMR `granule_size_cmr_mb` values is **69.353**. Stage 17 measured the subsequent transfer at 72,722,137 bytes (69.353 MiB), exactly matching that numeric sum after converting bytes to binary MiB.

## Artifacts

- `notebooks/14_stratified_validation_sample_design.ipynb` rebuilds the 2025 association-presence table, displays month diagnostics, selects the deterministic sample, visualizes frame availability, and writes the audit/plan files.
- `data/processed/candidate_presence_2025.parquet` plus metadata: one source observation per row and its cross-family candidate-presence flag.
- `data/reference/validation_sample_2025.csv`: 40-stratum observation audit including the empty stratum and CMR join evidence.
- `data/reference/validation_granule_plan_2025.csv`: deduplicated 39-granule transfer plan.
- `data/reference/validation_sample_2025.metadata.json`: selection seed and input hashes, status counts, total size, and limitations.

No files from the expanded plan have been downloaded. The bounded downloader now retains its default of 2 files / 10 MB but supports an explicit maximum of 40 files / 100 MB, rejects duplicate filenames and unapproved URLs, saves a manifest after each completed file, and resumes only when the plan hash and existing file checksums match. Dry-run validation listed all 39 granules without network access.

## Scientific limits

This deliberately small, balanced engineering sample is conditional on source, season, Cameroon location, candidate status, and CMR metadata match. It is suitable for testing source-pixel linkage and reader behavior after retrieval. It is not a probability sample and cannot estimate cross-sensor association precision/recall, false alarms, true-fire counts, or algorithm accuracy. A non-candidate is not a negative fire label. CMR granule time and polygons do not provide per-pixel valid observation opportunities. Independent incident/perimeter reference data and coverage-aware sampling are still required before any model evaluation.

## Verification

- Executed notebook 14 end-to-end; all 12 monthly association cells, CMR matching, 40-stratum audit, figures, and CSV/JSON outputs completed without notebook error cells.
- `py -3.11 -m src.firewatch.granule_download --plan data/reference/validation_granule_plan_2025.csv --output-dir data/reference/granules/validation_2025 --max-files 40 --max-total-mb 100 --dry-run` validated all 39 entries and made no network request.
- Full project suite: **28 tests passed**. Added unit tests for deterministic strata, retained unmatched/empty strata, 40-file/100-MB hard limits, and checksum-verified resume behavior.

## Next step

Run the 39-file bounded authenticated retrieval from the local PowerShell prompt in README. Then scale notebook 13's sensor-native pixel lookup over the resulting files, preserving each row's candidate status and source-specific confidence/FRP. The first batch should be treated as an engineering validation set only; design an independent coverage/reference sample before fitting or evaluating any anomaly/classification model.
