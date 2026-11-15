# FIREWATCH AI — Development Log

This is the running record for the final project report. Each stage records actions, evidence, outcomes, risks, and next steps. Dates use the project environment's local date (Africa/Douala).

## 2026-11-14 — Stage 01: Dataset reconnaissance

- Inspected workspace: extracted 2025/2026 FIRMS files and matching ZIP bundles; no existing application implementation or dependency manifest.
- Inventory: 12 CSVs, four product codes, 712,234 rows in 2025, 417,793 rows in partial 2026.
- Schemas: 15 columns in archive; 14 in NRT (`type` omitted). No blank cells or exact duplicate rows in initial scan.
- Coverage: 2025 date spans are Jan 1-Dec 31; 2026 spans vary by product. MODIS archive ends Aug 29 and NRT starts Sep 9.
- Environment: Python 3.11/Jupyter/pandas/NumPy/Matplotlib/scikit-learn/PyArrow available; GeoPandas absent. NVIDIA RTX 5070-series GPU detected with about 12 GB VRAM. No GPU need established for tabular QC.
- Deliverables: executed `notebooks/01_dataset_reconnaissance.ipynb`; `reports/01_dataset_reconnaissance.md`.
- Challenge: distinguish observation date gaps from actual satellite coverage; downloaded CSVs are detections, not coverage records.

## 2026-11-14 — Stage 02: Delivery integrity and data contract

- Compared all 20 ZIP members against extracted files by SHA-256; all exact matches.
- Confirmed no calendar-date overlap between 2026 archive and NRT sets for each product in this snapshot. VIIRS archive/NRT handoff is Jul 31/Aug 1; MODIS handoff is Aug 29/Sep 9.
- Counted distinct dates with at least one row; many files have dates within their overall span with no rows, so these gaps cannot imply no fire or absent sensor coverage.
- Defined normalized observation contract and separate event-association records in `reports/DATA_CONTRACT.md`.
- Deliverables: `notebooks/02_delivery_and_contract_audit.ipynb`, `reports/02_delivery_and_contract_audit.md`, this log. Notebook syntax parsed; standalone integrity audit completed.
- Challenge: Windows Jupyter kernel reset during nbconvert, leaving no saved execution outputs for notebook 02. Reconstructed notebook and validated code syntax; ZIP verification rerun independently and succeeded.
- Open decisions: confirm product acquisition-time semantics, definitions/units/valid ranges, confidence meaning, archive/NRT refresh semantics, and geographic download extent from authoritative product documentation.

## 2026-11-14 — Stage 03: NASA product documentation review

- Reviewed official FIRMS and NASA VIIRS product documentation for UTC acquisition time, confidence encodings, resolution, archive/NRT replacement, and missed-detection caveats.
- Key change: archive and NRT are alternate processing states for detections as archive standard processing becomes available, not independent evidence; future merges must prefer standard archive where available, use NRT for the recent tail, and retain lineage.
- UTC timestamps will be minute-precision; raw date/time tokens remain in derived records.
- Confidence stays source-specific; cross-source FRP comparisons deferred.
- Observed coordinate envelope is Central African/Cameroon-focused, but does not establish requested download bounds or complete Cameroon coverage.
- Deliverable: `reports/03_product_documentation_review.md`. Official references and detailed implications are recorded there.
- Open issue: no original download query metadata was found, so geographic completeness remains unverified.

## 2026-11-14 — Stage 04: Ingestion and normalization

- Implemented `src/firewatch/data_pipeline.py` with source checksums, recursive discovery restricted to year directories, source metadata, raw-token retention, numeric derived fields, UTC timestamps, quality flags, and snapshot/row-based IDs.
- Processed all 12 CSVs / 1,130,027 rows to `data/processed/observations.parquet` and a file-level CSV summary. All rows passed current required-field, time, and coordinate checks; none were dropped or quarantined.
- Fixed/covered four implementation issues: pandas missing-value assertion in a test; mixed all-null NRT type column warning; Suomi-NPP confidence family detection using product code instead of `instrument`; derived CSV accidentally eligible for rediscovery.
- Added `notebooks/03_ingestion_and_normalization.ipynb` with metrics and visualizations, plus six unit tests.
- Verification: six unit tests passed; real data pipeline rerun completed; notebook syntax/format checks passed. Notebook 03's cells were not run in Jupyter; the same ingestion function ran directly. Stage 02 notebook execution still has a documented Windows kernel failure.
- Main limitation: checks confirm structural/temporal/coordinate validity, not scientific correctness, full spatial coverage, or cross-sensor comparability.
- Detailed report: `reports/04_ingestion_and_normalization.md`.

## 2026-11-14 — Stage 05: Candidate association exploration

- Implemented `src/firewatch/association.py` using a unit-sphere cKDTree candidate search and great-circle distance evidence. It checks adjacent UTC date buckets, filters by actual UTC time delta, compares distinct satellite platforms only, and retains thresholds/method version on every edge.
- It creates candidate links only; no raw row is removed and no event clusters are asserted.
- Ran October 2025 real data (4,727 observations, five satellite platforms) with broad 5 km/12 hour envelope: 12,596 candidate links; 1,925 cross MODIS-VIIRS, 10,645 among VIIRS platforms, 26 MODIS-platform.
- Sensitivity: candidate totals for 0.5 km/1 h, 1 km/3 h, 2 km/6 h, and 5 km/12 h are 1,668; 3,985; 6,789; 12,596. Cross-family counts are broken out in the stage report.
- Deliverables: `notebooks/04_candidate_association_exploration.ipynb`, association module, and `data/processed/candidate_links_2025_10.parquet`.
- Verification: all nine unit tests pass; direct real-data run completed; all notebook code syntax checked. Notebook itself was not run due the documented notebook execution issue.
- Key scientific caution: candidate density and thresholds alone do not establish shared fire identity; no reference labels exist yet. Same-family VIIRS candidates dominate this example and must be separated in analytics from MODIS-VIIRS links.

## 2026-11-14 — Stage 06: Activity calendar and anomaly readiness

- Added `src/firewatch/analytics.py` and `notebooks/05_activity_calendar_and_history.ipynb` for UTC daily observation counts, source-specific summaries, and same-month descriptive comparison.
- Calendar cells with no records are explicitly coverage-unknown; no rows are not treated as zero fires. Archive and NRT remain separate, with source file/year/product/platform provenance.
- Direct run against real Parquet data: Oct 2025 = 4,727 rows (archive); Oct 2026 = 8,387 rows (NRT). Because stream processing states and coverage are different, these are not anomaly evidence or directly comparable true-fire counts.
- Decision: no anomaly model yet. One complete year plus a partial second year and no independent coverage data cannot support a defensible seasonal anomaly baseline.
- Verification: all 11 unit tests pass; real calendar outputs reconciled to data; five notebooks parse and code cells syntax-check. Notebook 05 itself was not executed under Jupyter.
- Detailed report: `reports/06_activity_calendar_and_anomaly_readiness.md`.

## 2026-11-14 — Stage 07: Interactive application

- Built the read-only FastAPI service and Vite/React/TypeScript dashboard. Month, satellite, stream, map zoom, clicked day, daily calendar, and candidate links are connected through shared filter/query state.
- Map uses a source-colored aggregation at wider zoom and deterministic samples for close-up views; candidate overlay only draws MODIS-VIIRS lines and explains that proximity is not confirmation.
- Added pinned frontend/backend dependency manifests and `README.md` setup/run guidance.
- Tests: 14 Python unit/API tests pass; production Vite build passes; npm reported zero audit vulnerabilities. Build emits a 764 kB uncompressed JS chunk warning.
- Local endpoint smoke results for Oct 2025: 4,727 detections, 1,224 map cells at zoom 6, 155 calendar cells, 3,985 candidate links under 1 km/3 h; API loaded all 1,130,027 rows; frontend root returned HTTP 200.
- Browser visual review is not complete: browser helper script absent, CUA tab/window actions timed out, and Playwright wheel download was cancelled due slow transfer. No visual screenshot/interaction verification is claimed.
- Detailed report: `reports/07_interactive_application.md`.

## Remaining work

- Expand source-pixel checks across periods/platforms, then compare candidate links only under common valid observation opportunities and with independent reference data.
- Seek independent incident/perimeter references and decide whether EUMETSAT SEVIRI adds useful temporal corroboration.
- Complete browser visual QA and an end-to-end demo; then prepare the final technical report.

## 2026-11-14 — Stage 08: Cameroon boundary and spatial-scope reconnaissance

- Verified current Cameroon ADM0 metadata from geoBoundaries. Candidate boundary is represented as 2016; source/license metadata is retained in report and API source is cited.
- The shell `python` alias points to the Windows Store stub. The project interpreter is `py -3.11`; it has pandas, NumPy, Matplotlib, and PyArrow but not Shapely/GeoPandas. Used vectorized Matplotlib Path containment, avoiding dependency installation.
- Decision: keep all points and label the dataset as Cameroon-centered/regional; ADM0 containment is an extent diagnostic, never a coverage mask.
- Results and limits are recorded in `reports/07_interactive_application.md` and `notebooks/06_cameroon_boundary_scope_audit.ipynb`.

- Stage 08 completed: pinned the Cameroon ADM0 boundary, computed the point-in-polygon split (1,122,291 inside; 7,736 outside), and saved a checksum-verifying notebook. The analysis retained every point and does not equate the ADM0 boundary to FIRMS coverage.
- Boundary artifact: `data/reference/geoBoundaries-CMR-ADM0-2016.geojson`; notebook: `notebooks/06_cameroon_boundary_scope_audit.ipynb`; details in `reports/07_interactive_application.md`.


- Executed `notebooks/06_cameroon_boundary_scope_audit.ipynb` end to end with nbconvert; the checksum assertion, 1,130,027-row spatial split, source table, and visual outputs were stored in the notebook. Notebook ran successfully; Windows printed a pyzmq Proactor-loop warning that did not stop execution.

## 2026-11-14 — Stage 09: Multi-period cross-sensor association review

- Ran the existing 1 km / 3 hour candidate-link method on seven archive-only month slices across 2025 and Jan–Jul 2026. Analysis completed in ~20 seconds; output: 317,546 candidate pairs in Jan 2025, 3,985 in Oct 2025, and 188,017 in Jan 2026, with selected months and breakdowns recorded in `reports/08_multi_period_association_review.md`.
- VIIRS-platform edges dominate all selected periods; MODIS–VIIRS links vary with source counts. Some months have more candidate pairs than input rows, confirming multi-neighbor graph density. No edges were collapsed into events.
- Created `notebooks/07_multi_period_association_review.ipynb` with the fixed protocol, summary table, satellite-pair breakdown, and visualizations. Treat as exploratory because no reference labels exist and month volumes are highly unbalanced.
- Maintained the decision to defer event clustering, one-to-one matching, true-fire counts, and anomaly modeling until validation data and coverage context are available.
- Executed `notebooks/07_multi_period_association_review.ipynb` with nbconvert successfully; all four code cells completed and tables/plots were embedded. Initial run found `src` missing from Jupyter's notebook-directory import path; added project-root discovery and `sys.path` setup, then reran cleanly. Windows pyzmq Proactor-loop warning persisted but was non-fatal.

## 2026-11-14 — Stage 10: Association null comparison

- Implemented a conditional coordinate-time permutation null on October 2025 archive observations: independently permuted coordinate pairs within each satellite × UTC day while leaving observation times and source metadata fixed. Counted only MODIS–VIIRS edges at 0.5 km/1 h, 1 km/3 h, and 2 km/6 h.
- Ran 29 deterministic permutations (seed `20261114`, NumPy Generator); saved 87 threshold-replicate counts to `data/processed/null_comparison_oct2025.csv`.
- Observed counts 24, 332, 909 versus null means 22.72, 321.86, 902.14. Empirical upper-tail fractions were 0.233, 0.033, 0.233. At the intermediate threshold the observed count exceeded all 29 null draws, but resolution is 1/30 and only ~10 edges separate observation from the null mean. Do not treat this as match accuracy or threshold-selection evidence; thresholds were exploratory and not adjusted.
- Created and executed `notebooks/08_association_null_comparison.ipynb`, embedding summary tables and null-distribution plots. `reports/09_association_null_comparison.md` explains assumptions, results, and scientific limits.
- This result shows the null reproduces most candidate proximity. Retain evidence edges only; defer event matching, clustering, and anomaly model until independent labels or overpass/coverage references exist.

## 2026-11-14 — Stage 11: Validation references and coverage readiness

- Audited source-native fields over 1,130,027 rows. All `scan`/`track` dimensions are populated. `type` is missing on exactly 10,938 NRT rows; archive rows have algorithm-inferred Type codes 0–3. Preserved source-native interpretations; Type is not treated as independent truth. NASA documentation identifies a VIIRS monthly Type-field revision issue, and delivered row metadata/readmes do not identify the exact monthly packaging revision.
- Checked CMR for Oct 2025 Level-2 granules intersecting the dashboard bbox across MOD14/MYD14 and VNP14IMG/VJ114IMG/VJ214IMG. Counts and duplicate NOAA-21 processing variants are reported in `reports/10_validation_reference_and_source_field_audit.md`. Granule bbox presence is not pixel-level coverage.
- Identified L2 fire masks + per-pixel QA as best next source for observation opportunity, EUMETSAT LSA SAF SEVIRI/MSG FRP-Pixel as optional independent temporal corroboration, and monthly MCD64A1/VNP64A1 as later burn-scar corroboration rather than point labels.
- Created and successfully executed `notebooks/09_source_field_and_reference_readiness.ipynb` and `notebooks/10_validation_reference_and_coverage_readiness.ipynb`. `README.md` now lists both.
- No new granules downloaded; data access/authentication and granule-to-CSV linkage remain the next implementation step. No original FIRMS data or production code was changed.


## 2026-11-14 — Stage 12: Reproducible NASA CMR granule manifest

- Implemented `src/firewatch/cmr_manifest.py`, a paginated CMR metadata-only query/manifest writer for the five selected MODIS/VIIRS L2 products. It stores CMR entry and acquisition/processing IDs, collection version, granule time/size/polygons, data/browse URLs, query window/bounds, and retrieval metadata; no granule data are downloaded.
- Generated `data/reference/cmr_manifest_2025-10.csv` (759 entries, 577,975 bytes) and companion `.metadata.json`. Counts: 165 VNP14IMG, 158 VJ114IMG, 172 VJ214IMG, 122 MOD14, 142 MYD14. NOAA-21 records include 12 alternate processing metadata entries for acquisitions; none were discarded.
- All 759 entries provide a direct science URL and browse URL. Science links point to protected LP DAAC product storage; Earthdata access must be configured before download. No credential values were requested, read, or logged.
- Added four `tests/test_cmr_manifest.py` tests; targeted unit tests pass. Executed `notebooks/11_cmr_granule_manifest.ipynb` successfully with summary and daily-availability plot. Added run instructions to README.
- Detailed record: `reports/11_cmr_granule_manifest.md`. Next step: test a small authenticated granule subset and inspect HDF/NetCDF layers before any bulk transfer.
- Full project verification after the manifest implementation: 18 unit/API tests passed. Existing upstream `StarletteDeprecationWarning` about `httpx` with `TestClient`; no test failures.
- Environment readiness check: Python 3.11 has `h5py` but lacks `netCDF4`, `pyhdf`, GDAL, Rasterio, xarray, and `earthaccess`. VIIRS HDF5 probing can begin with h5py; MODIS HDF4 reader support must be selected before the paired-source pilot. No packages added.
- Added manifest self-integrity fields to the metadata sidecar (`manifest_rows`, `manifest_sha256`), regenerated the live CMR manifest, and independently verified the SHA-256 against the CSV bytes. Recorded the final hash in the stage report.
- Added a fifth offline manifest test for checksum metadata and reran the full suite: 19 tests passed. Re-executed notebook 11 against the final saved manifest; all code cells completed without error outputs.

## 2026-11-14 — Stage 13: Bounded cross-sensor granule selection

- Recalculated the October 2025 1 km/3 h candidate links and deterministically selected the shortest-time MODIS–VIIRS pair, breaking ties by distance: Aqua MODIS at 13:26 UTC and SNPP VIIRS at 13:10 UTC on Oct 20; center separation 0.555 km.
- Matched both points to CMR granules by acquisition interval plus CMR polygon containment: MYD14 Collection 061 granule `MYD14.A2025293.1325.061.2025294143419` and VNP14IMG Collection 002 granule `VNP14IMG.A2025293.1306.002.2025293205847`. Combined reported size ~2.727 MB. This does not establish valid pixel coverage or true event identity.
- Saved the two-row plan as `data/reference/cmr_sample_plan_oct2025.csv` and companion metadata. Created and executed `notebooks/12_candidate_granule_selection.ipynb` successfully, including an overpass timeline plot and parent manifest checksum verification.
- No data downloaded because science URLs are protected and Earthdata access is not configured. Next: obtain/access a local Earthdata auth setup, then download only these two granules, inspect VIIRS with installed h5py, add a MODIS HDF4 reader, and reconcile each CSV row to its own L2 fire pixel.
- Detailed report: `reports/12_candidate_granule_selection.md`.

## 2026-11-14 — Stage 14: Bounded authenticated granule retrieval

- Anonymous requests to the selected protected LP DAAC science URLs were redirected to protected object delivery and returned HTTP 403. No credentials or granule bytes were used.
- Added `src/firewatch/granule_download.py` for a maximum two-file HDF/NetCDF pilot, 10 MB default aggregate limit, local-process Earthdata bearer token, redirect credential isolation, no-overwrite staging, file-signature/content-length checks, and a SHA-256 download manifest.
- Dry-run validated the planned MYD14 and VNP14IMG granules without network access. Eight focused manifest/downloader tests and all 22 project tests passed. One existing Starlette/httpx deprecation warning persists.
- Added local retrieval instructions to README. Actual transfer is pending user-side Earthdata token/LP DAAC authorization; token values are not requested or recorded.
- Detailed report: `reports/13_bounded_granule_download.md`.
- Next: once token access is configured, download the sample, inspect VIIRS HDF5 arrays, select an HDF4 reader, and validate the two CSV detections against real pixel QA/coverage.

## 2026-11-14 — Stage 15: L2 source-pixel validation pilot

- Retrieved the two prepared protected science granules locally (MYD14: 232,775 bytes; VNP14IMG: 2,626,193 bytes), verified HDF4/HDF5 signatures and retained SHA-256 values in `data/reference/granules/oct2025_pilot/download_manifest.json`. Token was not written to files. Added the granule directory to `.gitignore`.
- Installed Windows CPython 3.11 wheel `pyhdf==0.11.7` and pinned it plus existing `h5py==3.14.0` in requirements, enabling native inspection of both formats.
- Added `src/firewatch/swath_validation.py` and executable notebook `notebooks/13_source_pixel_validation.ipynb`. Each CSV observation time was within its granule interval; nearest native fire pixel distances were 4.71 m for MYD14 and 0.40 m for VNP14IMG; both native masks returned class 8 (nominal). Native confidence remains 50% for MODIS and code 8 for VIIRS; FRP 29.827 MW and 4.300 MW remains source-specific.
- Granule whole-file native fire-pixel counts: MODIS 262 (mask classes low/nominal/high: 5/194/63); VIIRS 818 (40/725/53). Because the pilot was selected from an existing candidate, it supports source row/granule linkage and reader indexing, not event identity or detection accuracy.
- Notebook wrote `data/processed/source_pixel_validation_oct2025.csv`. Three new unit tests cover haversine, VIIRS dataset/metadata/mask handling, and missing dataset errors. Full project suite after the final metadata parser edit: **25 tests passed**; the authenticated-download dry run and both local SHA-256/byte-count checks passed. Existing Starlette/httpx deprecation warning remains.
- Detailed report: `reports/14_source_pixel_validation.md`. Notebook emitted a non-fatal Windows pyzmq Proactor warning.
- Next: stratify candidate and non-candidate samples across months/platforms, establish independent reference/coverage information, then test harmonization before any inferred event collapse.

## 2026-11-14 — Stage 16: Stratified validation sample and bounded batch plan

- Generated a full-year CMR metadata manifest for the five L2 products and Cameroon-centered bbox: 8,862 entries (1,624 MOD14; 1,665 MYD14; 1,845 VNP14IMG; 1,890 VJ114IMG; 1,838 VJ214IMG), SHA-256 `6b7d4410af4d895aa087a5fd35560efef2d0c70f9c72aa8b42342098d160f923`.
- Built a reproducible 2025 archive cross-family candidate-presence table month by month with a 3-hour halo. Source archive frame contains 712,234 valid rows; 106,069 rows have at least one MODIS–VIIRS candidate edge at 1 km / 3 h, while 606,165 have no such edge. The latter is not a negative or no-fire label. Local archive starts at 2025-01-01, so earlier boundary neighbors are unavailable.
- Added `src/firewatch/validation_sampling.py`, selecting one deterministic SHA-256-ranked observation per quarter × satellite × candidate status in Cameroon. Time/polygon CMR matches were found for 39/40 strata; only Terra Q3 candidate status was empty. Matched observations map to 39 unique granules, CMR size field sum 69.353.
- Added/executed `notebooks/14_stratified_validation_sample_design.ipynb`; it rebuilds candidate flags, visualizes monthly counts/stratum availability, and writes the sample audit, unique granule plan, and checksum metadata.
- Generalized the downloader while retaining its two-file/10 MB default: explicit batch limits hard-cap at 40 granules/100 MB; duplicate filenames are rejected; each completed file is written to a plan-hash-linked manifest, and resume accepts only size/checksum-verified files from the identical plan. Added deterministic sampler and resume/hard-limit tests.
- Dry run accepted all 39 planned granules without network access. The expanded granule batch has not been downloaded. Scientific scope remains source-row pixel linkage only; candidate status is not event identity and CMR polygons are not valid-pixel masks.
- Verification after notebook regeneration and downloader changes: **28 project tests passed**; notebook 14 and notebook 13 have no error outputs; the 39-granule dry run validated with no network access; `git diff --check` passed. Existing Starlette/httpx deprecation warning and Windows notebook pyzmq warning remain non-fatal.
- Detailed report: `reports/15_stratified_validation_sample_design.md`.
- Next: user can run the documented masked local-token command for the 39-file, 100 MB capped plan; then inspect those files with the sensor-native readers and extend notebook 13 checks.

## 2026-11-14 — Stage 17: Stratified L2 source-pixel validation

- User retrieved the 39-file plan. Verified the plan SHA-256, all filenames, all byte counts, and all 39 SHA-256 digests against the download manifest. Total: 72,722,137 bytes (69.353 MiB / 72.722 decimal MB), under the 100 MB transfer cap.
- Inspected every observation in `validation_sample_2025.csv` against its native L2 active-fire record and fire mask: 39/39 CSV times inside granule intervals; nearest active-fire pixel center 0.15–7.17 m (median 0.53 m); 39/39 mask classes were 7–9 (4 low, 31 nominal, 4 high).
- The sample contains 19 rows with a MODIS–VIIRS candidate association and 20 without one under 1 km / 3 h. All 20 “no candidate link” rows still have native L2 fire-mask detections in their source granules (1 low, 17 nominal, 2 high), demonstrating that candidate-link absence must not be interpreted as no source detection or no fire.
- Added/executed `notebooks/15_stratified_pixel_validation.ipynb`; saved `data/processed/source_pixel_validation_2025_stratified.csv` and metadata sidecar. Added a synthetic HDF4 MODIS reader test alongside VIIRS HDF5 tests.
- This selected sample validates the matching/readers, not cross-sensor event identity, model accuracy, true-fire counts, or unbiased precision/recall. No model trained; independent references and coverage opportunity remain necessary.
- Detailed report: `reports/16_stratified_source_pixel_validation.md`.
- After adding the synthetic MODIS test, full-suite verification: **29 tests passed**. Notebook 15 executed without error cells; Windows pyzmq warning remains non-fatal.
- Next: establish coverage-derived observation opportunities and an independent reference sample; then evaluate association and anomaly methods only with those data.

## 2026-11-14 — Stage 18: Common-coverage geolocation plan

- Used source L2 metadata to preserve exact lineage from the selected Aqua–NOAA-21 association to `MYD03.A2025187.1345.061.2025188145533.hdf` and `VJ203IMG.A2025187.1230.021.2025187181751.nc`. The observations are 78 minutes apart and 0.253693 km apart by reported coordinates; this is a pilot selection, not event-identity evidence.
- Queried CMR for those exact IDs. The two files are 32.973 and 184.670 MiB (217.643 MiB total), versions 6.1 and 2.1. Kept processing filename segments distinct from collection versions.
- Added `src/firewatch/geolocation_manifest.py` and executed `notebooks/16_common_coverage_geolocation_plan.ipynb`, which writes `data/reference/geolocation_coverage_plan_2025.csv` and metadata. Corrected the CMR version fallback and verified notebook execution.
- Dry-run exposed that the bounded downloader accepted only LP DAAC URLs and fire-granule plan IDs, while the exact geolocation records use LAADS URLs and `geolocation_granule_id`. Added the strict LAADS HTTPS host/path allowlist and companion-ID handling. Re-ran the dry-run successfully: exactly two files accepted, total 217.643 MiB, no network access.
- Focused CMR/geolocation tests: **12 passed**. No companion files downloaded; common valid coverage remains unmeasured until download and pixel-QA inspection.
- Detailed report: `reports/17_common_coverage_geolocation_plan.md`.
- Next user action: download the two geolocation companions with the documented bounded command. Next engineering step: create a chunked geolocation-to-mask coverage inspection notebook.

## 2026-11-14 — Stage 19: Common-coverage pixel opportunity pilot

- Verified the geolocation plan hash and both staged files' byte counts/SHA-256 values against the downloader manifest. Sizes: MYD03 34,574,718 bytes; VJ203IMG 193,640,420 bytes. Geolocation grids `(2040, 1354)` and `(6432, 6400)` exactly match their paired MYD14 and VJ214IMG fire-mask grids.
- Implemented `src/firewatch/coverage_validation.py` with chunked haversine nearest-center search, HDF4 row-slice adapter, VIIRS per-pixel quality flag capture, native mask lookup and class separation. MODIS `gflags` are retained and decoded from the official Collection 6.1 file specification; no opaque quality scalar is invented.
- Created and executed `notebooks/17_common_coverage_pixel_opportunity.ipynb`. All four target-point/swath lookups completed and wrote `data/processed/common_coverage_pixel_opportunity_2025_pilot.csv`.
- Results: both original coordinates map to native nominal-fire pixels. At the Aqua point, the NOAA-21 VIIRS nearest center is 0.215 km away and classifies clear land (mask 5, VIIRS quality 0). At the NOAA-21 point, Aqua's nearest center is 0.253 km away and is nominal fire (mask 8, MODIS gflags 0). The source observations are 78 minutes apart. This asymmetric cross-mask pattern is useful harmonization evidence, but not proof of a sensor miss, event identity, or continuous burning because observations are not simultaneous and pixel footprints/algorithms differ.
- Added three synthetic VIIRS coverage tests. Full project suite: **35 passed**; notebook 17 completed without error outputs; `git diff --check` passed. Existing Starlette/httpx deprecation warning remains.
- Detailed report: `reports/18_common_coverage_pixel_opportunity.md`.
- Next: repeat coverage/opportunity sampling across linked and unlinked strata, and obtain independent reference evidence before reporting association performance or model accuracy.

## 2026-11-14 — Stage 20: Three-sensor pilot plan

- Inspected the Q3 linked rows in the actual 39-observation sample and selected Aqua (13:48 UTC) plus NOAA-20 (11:39 UTC) from the same July 6, 2025 Cameroon neighborhood. Recomputed great-circle distance 0.889563 km and time separation 129 minutes; both fall within configured 1 km / 3 h candidate thresholds. The existing NOAA-21 point remains the third source in this neighborhood.
- Parsed the exact geolocation input filename from the downloaded NOAA-20 VJ114IMG file: `VJ103IMG.A2025187.1136.021.2025187154117.nc`. Exact CMR query resolves collection 2.1 and 177.333 MiB; no data transferred.
- Added and executed `notebooks/18_three_sensor_geolocation_plan.ipynb`; it recreates the observed-pair selection, validates thresholds, traces source L2 lineage, queries CMR, and writes the one-file plan plus metadata. The downloader's dry-run accepted the exact plan under the 200 MiB limit.
- Detailed report: `reports/19_three_sensor_pilot_plan.md`. README download steps now point to the NOAA-20 extension.
- Next user action: download this single geolocation companion to extend the same case to Aqua, NOAA-20, and NOAA-21. Limits remain: this is a selected candidate neighborhood, not a representative accuracy or event-duration evaluation.

## 2026-11-14 — Stage 21: Three-sensor pixel-opportunity case study

- Verified NOAA-20 VJ103IMG at 185,946,697 bytes with SHA-256 `b25a295b3cbe262800f9016a5e9db5527541e021e9604e32e6ee28782a88e60a`; notebook 19 also reverified the original Aqua/NOAA-21 geolocation downloads and plan hashes. All three geolocation grids match their paired native fire-mask dimensions.
- Created and executed `notebooks/19_three_sensor_pixel_opportunity.ipynb`. It queries three actual sampled coordinates against three corresponding sensor geolocation/mask grids (nine lookups), with chunked VIIRS coordinate reads, QA retention, native mask classes, and an annotated categorical matrix plot. Wrote `data/processed/three_sensor_pixel_opportunity_2025_pilot.csv`.
- Own-source pixels are nominal fire for Aqua, NOAA-20, and NOAA-21. At the Aqua target, NOAA-20 and NOAA-21 masks are clear land. At the NOAA-21 target, NOAA-20 mask class 1 is **bowtie** (not MODIS-style “not processed”); Aqua is nominal fire. Distances, QA, and time offsets are detailed in `reports/20_three_sensor_pixel_opportunity.md`.
- A sensor-schema audit subsequently found the shared mask decoder had used MODIS semantics for VIIRS class numbers. Corrected separate product dictionaries (VIIRS 0=not processed, 1=bowtie, 2=glint; MODIS class 1=obsolete not processed), retained raw legends in output, and changed the matrix visualization to semantic categories. Re-executed notebook 19. Added regression coverage; full suite is **36 passed**. This candidate-selected, asynchronous case study does not establish event identity, sensor misses, continuous fire, or performance metrics.
- Next: develop a broader stratified linked/unlinked coverage sample and independent reference strategy before evaluating anomaly or association performance.

## 2026-11-14 — Stage 22: Unlinked-observation overpass plan

- Selected the real Q3 Aqua no-candidate sample point (2025-09-18 14:06 UTC; 4.0848 N, 9.3146 E) and queried the saved 2025 Level-2 CMR manifest for NOAA-20 VJ114IMG granules within ±3 hours whose coarse CMR polygon contains the point.
- Selected nearest granule-center time deterministically: `VJ114IMG.A2025261.1330.002.2025261205555`, 33 minutes earlier, size estimate 2.706 MiB. The candidate label remains only “no link under 1 km / 3 h”; the swath's pixel opportunity and mask remain unknown until native files are inspected.
- Added/executed `notebooks/20_unlinked_overpass_plan.ipynb`; it filters by real sample coordinates and manifest metadata, selects one granule, writes a provenance sidecar, and validates the bounded downloader plan in dry-run mode (one file, 10 MiB cap).
- Detailed report: `reports/21_unlinked_overpass_plan.md`; README includes the exact next transfer command.
- Next: user retrieves this small L2 file. Then read its input metadata to resolve exact geolocation lineage, query CMR for companion files, and evaluate source swath/mask opportunity at the Aqua coordinate. CMR polygon is not proof of pixel coverage.

## 2026-11-15 — Stage 24: Unlinked-case pixel opportunity

- Both planned geolocation companions downloaded and passed byte-count/SHA-256 verification. Aqua MYD03: 33,260,201 bytes; NOAA-20 VJ103IMG reprocessing: 191,223,131 bytes. The source NOAA-20 L2 granule also remains checksum-verified.
- Compared the CMR-available same-acquisition NOAA-20 geolocation reprocessing against all 16 L2 `FP_line`/`FP_sample` embedded coordinate records. Median residual 0.025 m, p95 0.059 m, max 0.074 m; all 16 below 0.1 m and VIIRS quality flags zero. This supports the reprocessing at the source fire pixels while retaining the original processing-timestamp lineage caveat.
- Created/executed `notebooks/22_unlinked_opportunity_coverage.ipynb`; saved `data/processed/unlinked_opportunity_pixel_coverage_2025.csv`. At the Aqua no-candidate coordinate, Aqua's own nearest pixel is nominal fire at 0.0038 km (MODIS gflags 0); the earlier NOAA-20 nearest pixel is 0.2399 km away and VIIRS class 1 bowtie (geolocation quality flag 0). This is not a valid clear-land NOAA-20 opportunity and does not establish a detection miss.
- Detailed report: `reports/23_unlinked_opportunity_coverage.md`. Notebook ran with no error cells.
- Download attempts earlier exposed repeated short-body transfers; the downloader was amended to resume HTTP byte ranges from retained `.part` files when the server honors ranges. User's successful transfer completed with correct final size and SHA-256.
- Next: broaden opportunity checks across a deterministic, stratified linked/unlinked sample and obtain independent reference data before reporting model or association performance.

## 2026-11-14 — Stage 23: Unlinked L2 inspection and geolocation-lineage exception

- Verified NOAA-20 VJ114IMG `VJ114IMG.A2025261.1330.002.2025261205555.nc`: 2,836,999 bytes; SHA-256 `b23479ae7b10861151db2e2a8d7cabaf35f497245e2361fd96e63c9f26f73cf8`. Its 6,464 × 6,400 native mask contains 16 nominal fire pixels, 19,509,735 clear-land pixels, 9,583,401 cloud pixels, 4,310,442 water pixels, 5,326,336 bowtie pixels, 2,637,588 glint pixels, 2 unclassified pixels and 2,080 not-processed pixels; all other mask categories count zero.
- Verified the existing Aqua Q3 no-candidate source L2 file against the 39-file SHA manifest. Extracted exact source geolocation input IDs from both L2 products. Aqua MYD03 resolves exactly through CMR (31.719 MiB). NOAA-20 L2 names `VJ103IMG.A2025261.1330.021.2025261182205.nc`, which CMR does not return and which is absent from the current public LAADS archive directory listing.
- CMR and the official LAADS archive directory do list a reprocessed same-acquisition VJ103IMG granule, `VJ103IMG.A2025261.1330.021.2025267192836.nc` (CMR 182.365 MiB). This is **not** the exact L2 input processing instance. The two-file plan retains both original requested ID and alternate ID/status; combined CMR estimate 214.084 MiB, dry-run passes under 250 MiB. Do not use the alternate for spatial conclusions until coordinate consistency is checked at all NOAA-20 L2 FP_line/FP_sample indices.
- Notebook 21 inspected source integrity/mask histogram and created the exact-vs-reprocessed geolocation plan. It executed without errors. This lineage issue is recorded as a scientific limitation, not silently normalized away.
- Detailed report: `reports/22_unlinked_l2_inspection_and_geolocation_lineage.md`.
- Next: retrieve the two geolocation files (the NOAA-20 file is a documented reprocessing candidate), compare alternative geolocation coordinates against L2 active-fire pixel coordinates, and proceed only if the residuals and pixel indexing support their use for this case. If they do not, preserve the unresolved status.

## 2026-11-15 — Stage 25: Interactive dashboard modules and verification

- Replaced the single-row page navigation with a persistent desktop sidebar and a horizontally scrollable module bar on narrow screens: Overview, Satellite explorer, Activity calendar, Candidate links, and Data quality. Module controls share the same global date, satellite, stream, map, and analytics state; Candidate links enables its overlay when opened.
- Added direct daily chart-bar selection and a clear-day control so the map and summary can focus on the selected UTC day.
- Fresh local Chromium smoke check: all five modules render, each sidebar item becomes active on click, Candidate links sets its overlay to enabled, and there is no error banner on initial load. Mobile emulation at 390 px reports document/body widths of 390 px (no page-level horizontal overflow).
- Captured `reports/ui_sidebar_desktop.png` for the submission/demo record.
- Verification: frontend TypeScript/Vite production build passed; Python unittest discovery: 36 passed; `git diff --check` passed. Existing Starlette/httpx deprecation warning and Vite large-chunk advisory remain non-blocking.
- Submission status: local demo and scientific notebooks are available. Public judge-accessible deployment, demo recording/link, team/category form fields, and final portal submission still require completion outside this code workspace. Maintain the stated scientific limits; current pilot examples do not establish event identity or model accuracy.

## 2026-11-15 — Stage 26: Separate application modules and end-to-end review

- Reworked the former scroll-only dashboard into eight addressable, browser-history-aware routes: Overview, Satellite explorer, Activity calendar, Fire analytics, Anomaly intelligence, Candidate links, Reports, and Data quality. Shared platform/stream filters persist across routes; date selection is period-aware. Desktop sidebar and narrow-screen scrollable navigation remain responsive.
- Added `GET /api/quality` for full-archive validation status, duplicate observation IDs, inspected missing fields, source filenames, year/product/platform/stream groups, and data extent. The current archive result is 1,130,027 valid rows, zero duplicate IDs, zero missing values in inspected fields, 12 distinct source filenames, and 15 inventory groups.
- Added `GET /api/trends` for monthly observation-row groups by month/product/platform/stream. The archive produces 115 platform/month/stream groups and 23 months with rows; no-row periods are not converted to a zero-activity claim.
- Implemented configurable distance/time candidate review with table/map, family and satellite filters, and CSV. October 2025 returns 3,985 candidate pairs under default 1 km / 3 hour parameters. In the browser, narrowing to 0.5 km recalculated the selected-day pair count from 19 to 9.
- Implemented an explicitly limited within-month robust-Z daily volume screen using median/MAD, default cutoff 3.5, and at least 14 observed days. October 2025 filtered selection: median 154 rows/day, MAD 96, zero flags. No-row dates are excluded and the view states that it is neither a seasonal fire anomaly nor a prediction.
- Added print-optimized reports with current activity/platform totals, candidate-link and robust-screen context, scientific limitations, browser PDF output, plus daily/platform CSV exports. Generated and visually inspected `reports/FIREWATCH_AI_Cameroon_2025-10_Report.pdf` (one A4 page, 3,985 candidate pairs) and the desktop/mobile/module screenshots.
- Browser smoke coverage: all eight routes opened; shared satellite filter changed 4,727 to 4,556 records in October 2025; month selection showed 454 records in September 2025; selected-day calendar filtering worked; candidate threshold changes recalculated; report CSV contained five platform rows; browser back/forward worked; 390 px layout had no page-level horizontal overflow; no uncaught runtime errors observed.
- Added regression tests for quality and trend endpoints. Full suite: **38 passed**. Production client build passed (801.53 kB minified JavaScript / 235.53 kB gzip; Vite large-chunk advisory remains). Mobile screenshot review found and corrected a month-input label overlap. `git diff --check` passed after the final source/doc changes.
- Refreshed README, NASA submission brief, screenshots, and `reports/PROJECT_FINAL_REPORT.md` with actual metrics and limitations.
- External completion boundary: local application is implemented and running; public deployment, demo publication, and portal submission still require the NASA submission account and project/team form details. No public judging URL is claimed. No independent ground-truth fire labels or population model accuracy metrics are available.

## 2026-11-15 — Stage 27: Professional visual identity pass

- Replaced the header flame-and-AI wordmark treatment with a custom vector geospatial locator mark and a restrained `FIREWATCH / EARTH OBSERVATION` wordmark. The project title remains FIREWATCH AI in metadata and project materials.
- Replaced sparkle-style symbols in anomaly/insight areas with chart and information icons, and applied the locator mark to the generated report identity.
- Rebuilt the frontend successfully (801.99 kB minified JavaScript / 235.69 kB gzip; existing large-chunk advisory remains). Desktop and 390 px mobile screenshots were refreshed; the desktop page reports 12/12 map tiles loaded. Regenerated and visually checked the one-page A4 sample report with the updated mark. `git diff --check` passes.
