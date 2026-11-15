# FIREWATCH AI

FIREWATCH AI is a Cameroon-first exploration tool for NASA FIRMS MODIS and VIIRS active-fire observations. It keeps original observations, processing lineage, and inferred spatial-temporal links separate.

## Current implementation

- Read-only dataset reconnaissance and ZIP integrity notebooks.
- Source-preserving normalization into Parquet with UTC timestamps and quality flags.
- Pairwise cross-satellite candidate links with distance/time evidence.
- Coverage-cautious daily observation calendar.
- FastAPI endpoints and a Vite/React/Leaflet application with a project landing page and nine addressable workspace modules: Overview, Satellite explorer, Activity calendar, Fire analytics, Alerts & forecast, Candidate links, Reports, Data quality, and Data assistant. Sidebar navigation uses URL routes and browser back/forward; platform and stream filters are shared across pages.
- Monthly platform comparison over the delivered archive, with periods without rows left unfilled because coverage is unknown.
- Explainable robust-Z screening for unusually high daily observation volume within the selected month, surfaced as archive review alerts.
- Experimental seven-day seasonal-window forecast of FIRMS row volume with chronological baseline metrics and month-specific high-volume watches. It forecasts source rows, not fires or fire risk; the archive is not a live alert feed.
- Candidate-link review with adjustable distance/time limits, platform/family filters, map overlay, evidence table, and CSV export. Candidate edges remain possible associations, never deduplicated or confirmed fires.
- Printable observation reports with measured counts, platform breakdown, candidate-link context, forecast/backtest summary, and limitations, plus daily/platform CSV exports.
- A read-only quality API and provenance page showing source inventory, validation status, duplicate IDs, and missing-value counts.

Candidate links are not confirmed fires. A detection date with no rows does not prove there was no fire or that a sensor had valid coverage. See `reports/` for the staged technical record and methodology.

The archive alert screen compares daily counts across observed dates in the selected month using median absolute deviation (modified robust Z score, default threshold 3.5) and requires at least 14 observed days. The row-volume forecast averages a 15-day window around the same date in the prior year; it is benchmarked against the single same-date-last-year count. On the current 306-day rolling holdout, MAE was 936 rows/day versus 1,022 for the baseline and WAPE was 68.6%. This is experimental, forecasts row volume only, and must not be presented as a fire-risk model or operational alarm.

## Environment

Python 3.11+, Node.js 20.19+ or 22.12+, and npm are required. The current local Parquet dataset is approximately 127 MB. No GPU is required for the tabular processing or current map.

Install Python dependencies from the project root:

```powershell
py -3.11 -m pip install -r requirements.txt
```

This installs JupyterLab and the Python kernel required to run the project notebooks.

Install frontend dependencies:

```powershell
cd web
npm ci
```

## Run the data pipeline

From the project root:

```powershell
py -3.11 -c "from pathlib import Path; from src.firewatch.data_pipeline import ingest_workspace; ingest_workspace(Path('.'), Path('data/processed/observations.parquet'))"
```

The command writes only derived outputs under `data/processed/`; it does not modify the original CSVs or ZIPs.

## Discover NASA Level-2 granules

The metadata-only CMR manifest records candidate swaths and direct data URLs. It does not download granule contents.

```powershell
py -3.11 -m src.firewatch.cmr_manifest --start 2025-10-01 --end 2025-10-31 --bbox 8,1,17,14 --output data/reference/cmr_manifest_2025-10.csv
```

This writes a CSV plus query metadata JSON under `data/reference/`. NASA science granule retrieval may require Earthdata authentication.

To build the full 2025 Level-2 metadata inventory used by the validation sampling notebook:

```powershell
py -3.11 -m src.firewatch.cmr_manifest --start 2025-01-01 --end 2025-12-31 --bbox 8,1,17,14 --output data/reference/cmr_manifest_2025.csv
```

The bounded downloader caps transfers at 40 files / 250 MB, verifies file signatures and SHA-256, avoids overwrites, resumes verified plans, and strips authorization across NASA redirects. The 39-file Level-2 sample and all coverage-pilot granules described in the stage reports are downloaded and verified. Downloaded data are local and git-ignored.

The latest unlinked-observation case found that the nearest NOAA-20 pixel was bowtie, not a clear-land opportunity. Its same-acquisition reprocessed geolocation matched all 16 active-fire coordinates in the NOAA-20 Level-2 granule with a maximum residual of 0.074 m. See reports/23_unlinked_opportunity_coverage.md for evidence and caveats.

## Start the local application

Start the API in one terminal from the project root:

```powershell
py -3.11 -m uvicorn src.firewatch.api:app --host 127.0.0.1 --port 8000
```

Start the web client in a second terminal:

```powershell
cd web
npm run dev
```

Open `http://127.0.0.1:5173`. The client proxies `/api` requests to the local FastAPI service. Each sidebar item opens its own route; on narrow screens the module navigation becomes horizontally scrollable.

## Run notebooks and checks

Run the notebooks in order from the project root:

1. `notebooks/01_dataset_reconnaissance.ipynb`
2. `notebooks/02_delivery_and_contract_audit.ipynb`
3. `notebooks/03_ingestion_and_normalization.ipynb`
4. `notebooks/04_candidate_association_exploration.ipynb`
5. `notebooks/05_activity_calendar_and_history.ipynb`
6. `notebooks/06_cameroon_boundary_scope_audit.ipynb` (uses the pinned, attributed geoBoundaries Cameroon ADM0 reference file)
7. `notebooks/07_multi_period_association_review.ipynb` (seven archive-only periods; exploratory candidate-edge diagnostics)
8. `notebooks/08_association_null_comparison.ipynb` (29 day-stratified coordinate permutations per threshold)
9. `notebooks/09_source_field_and_reference_readiness.ipynb` (source fields, pixel dimensions, coverage-reference readiness)
10. `notebooks/10_validation_reference_and_coverage_readiness.ipynb` (validation strategy and coverage caveats)
11. `notebooks/11_cmr_granule_manifest.ipynb` (inspect the saved CMR Level-2 granule manifest)
12. `notebooks/12_candidate_granule_selection.ipynb` (select a two-granule October cross-sensor pilot)
13. `notebooks/13_source_pixel_validation.ipynb` (verify the pilot CSV points against actual MODIS/VIIRS fire-pixel records and masks)
14. `notebooks/14_stratified_validation_sample_design.ipynb` (rebuild 2025 candidate-presence flags and design a Cameroon × quarter × satellite × candidate-status validation sample)
15. `notebooks/15_stratified_pixel_validation.ipynb` (verify the 39 downloaded sample points against source L2 fire-pixel records, mask classes, granule times, and checksums)
16. `notebooks/16_common_coverage_geolocation_plan.ipynb` (select a real cross-sensor pair and resolve the exact geolocation input granules needed for pixel-level common-coverage inspection)
17. `notebooks/17_common_coverage_pixel_opportunity.ipynb` (verify companion-file checksums; compare each observation coordinate with both swaths' nearest geolocation pixel, QA, and native fire-mask class; save the pilot coverage table)
18. `notebooks/18_three_sensor_geolocation_plan.ipynb` (rebuild the NOAA-20 companion plan from the Q3 sample and resolve its exact geolocation input through CMR)
19. `notebooks/19_three_sensor_pixel_opportunity.ipynb` (verify three geolocation companions; compare three actual coordinates against three source swaths and visualize native mask classes)
20. `notebooks/20_unlinked_overpass_plan.ipynb` (select a real NOAA-20 L2 overpass for an Aqua sample detection with no candidate link, using the saved CMR manifest)
21. `notebooks/21_unlinked_overpass_geolocation_plan.ipynb` (verify the selected L2 inputs, inspect its product-specific mask legend, resolve exact/reprocessed geolocation records, and preserve the processing-lineage exception)
22. `notebooks/22_unlinked_opportunity_coverage.ipynb` (validate reprocessed geolocation consistency at source fire-pixel indices and compare nearest native masks for an unlinked Aqua coordinate)

Run unit and API tests:

```powershell
py -3.11 -m unittest discover -s tests -v
```

The read-only API exposes `/api/health`, `/api/metadata`, `/api/summary`, `/api/map`, `/api/calendar`, `/api/trends`, `/api/candidate-links`, `/api/quality`, and `/api/forecast`. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Data and design record

- `reports/DEVELOPMENT_LOG.md` is the running record for the final project report.
- `reports/DATA_CONTRACT.md` defines source lineage and normalized observation fields.
- Each stage report records methods, decisions, test results, and open limitations.
- The original FIRMS CSV and ZIP data are treated as read-only inputs.






**Granule format note:** `requirements.txt` includes `h5py` for VIIRS NetCDF4/HDF5 and `pyhdf` for MODIS HDF4. The source-pixel notebook keeps the products' different confidence field meanings separate.

