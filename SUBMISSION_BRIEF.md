# FIREWATCH AI — NASA Space Apps submission brief

## One-line description

FIREWATCH AI is a Cameroon-first, data-backed tool for exploring NASA FIRMS thermal-anomaly observations from MODIS and three VIIRS platforms, inspecting cross-sensor proximity evidence, and understanding when an apparent absence of detections may reflect sensor coverage or product-mask conditions.

## Problem and approach

FIRMS distributes observations from multiple instruments with different spatial resolutions, processing streams, confidence meanings, and overpass times. Showing all points on one map can encourage users to treat nearby observations as duplicate reports—or interpret no points as no fire. FIREWATCH preserves each source observation and its product lineage, then presents configurable space/time candidate links as evidence for review. A linked pair is not an event identity or confirmed wildfire.

## What is working

- Source-preserving ingestion of the supplied 2025 and 2026 FIRMS extracts into a reproducible Parquet dataset.
- Interactive local application with eight separate browser routes: Overview, Satellite explorer, Activity calendar, Fire analytics, Anomaly intelligence, Candidate links, Reports, and Data quality.
- Shared platform and stream filters, period-aware date selection, browser back/forward navigation, interactive map, daily calendar, platform comparisons, and candidate-link overlays.
- Historical monthly source-row comparison with missing months presented as unknown coverage.
- Explainable within-month robust-Z screen for high daily observation volume (median/MAD, default threshold 3.5, minimum 14 observed days); explicitly not a seasonal anomaly or wildfire-prediction model.
- Candidate association controls for distance/time, platform/family filtering, evidence table, and CSV export. The default October 2025 example returns 3,985 pairs at 1 km / 3 h; these are candidate pairs, not confirmed events.
- Printable observation report (browser Save as PDF) containing measured activity, platform totals, candidate-link summary, anomaly-screen context, and scientific limits; daily and platform CSV exports.
- Data quality/provenance page and read-only API inventory covering validation status, duplicate identifiers, missing values, source files, products, satellites, streams, and years.
- FastAPI read-only data endpoints and a Vite/React/Leaflet client.
- Native MODIS HDF4 and VIIRS NetCDF4/HDF5 readers, bounded NASA granule retrieval, checksum manifests, and executable Jupyter notebooks.
- Pixel-level case studies that retain geolocation quality and sensor-specific fire-mask categories, including a linked three-platform neighborhood and an unlinked Aqua case.

## Evidence from the downloaded data

The normalized archive contains 1,130,027 source rows (current saved build: 2025-01-01 through 2026-11-02). A 39-observation 2025 Cameroon sample was matched to native source fire pixels: all 39 coordinates were within 7.17 m of a source fire-pixel coordinate and had fire-mask class 7–9 in their own source granule. This validates the sample's source-row/granule linkage, not fire truth or cross-sensor accuracy.

In one linked July 6, 2025 case, Aqua, NOAA-20, and NOAA-21 source pixels were compared across their native masks. In one September 18 no-candidate Aqua case, the earlier NOAA-20 nearest pixel was bowtie, so that coordinate was not a clear-land observation opportunity. Its available same-acquisition geolocation reprocessing matched all 16 source L2 fire-pixel coordinates with maximum residual 0.074 m. These examples show why product-specific QA and coverage state matter; they are illustrative case studies, not a representative evaluation.

## Demo walkthrough (3–4 minutes)

1. Start the API and web client using README commands; open the local Vite URL.
2. Use the left sidebar to visit all eight pages. On mobile, swipe the module bar horizontally.
3. Choose a month and toggle individual satellites and streams. Point out how period views and cross-page platform filters change the map, calendar, platform breakdown, and pair results.
4. Select a daily chart bar to focus the map and counts on that day; use the clear-day control to return to the full month.
5. Open Candidate links and explain that lines encode distance/time proximity, not confirmed fire identity.
6. Show the robust-Z anomaly screen and explain it as a within-month observation-volume flag; it is not a seasonal baseline or fire forecast.
7. Generate the observation report and CSV exports, then show `notebooks/19_three_sensor_pixel_opportunity.ipynb` and `notebooks/22_unlinked_opportunity_coverage.ipynb` for native-mask coverage examples.
8. End with the main limitation: no independent ground-truth reference sample or population accuracy metric has been established yet.

## Claims to avoid

- Do not call detections confirmed wildfires.
- Do not call candidate edges deduplicated events.
- Do not claim precision, recall, false-negative rates, true-fire counts, or a validated seasonal anomaly model.
- Do not interpret a missing row or a not-processed, bowtie, glint, cloud, water, or unknown mask as clear non-fire.
- Do not claim the FIRMS extracts cover every fire or every location in Cameroon.

## Run locally

Install Python dependencies from the repository root with `py -3.11 -m pip install -r requirements.txt`; install the client with `cd web; npm ci`. Start the API with `py -3.11 -m uvicorn src.firewatch.api:app --host 127.0.0.1 --port 8000`, then in another terminal start the client with `cd web; npm run dev`. The current local dataset and granule files are git-ignored; a submitted demo must include the data or a clear setup path appropriate to the submission platform.

## Verification snapshot

- Production frontend build: `npm run build` passed on 2026-11-15. Vite reports an 801.53 kB minified JavaScript chunk (235.53 kB gzip), a non-blocking bundle optimization opportunity.
- Live local API: `/api/health` returned `ok` and 1,130,027 rows; `/api/quality` reports 1,130,027 valid records, zero duplicate IDs, and zero missing values in the inspected fields. `/api/trends` returned 115 source/platform/month groups.
- Full Python suite: 38 tests passed. Frontend browser smoke checks visited all eight routes, exercised shared platform/month filters, selected a calendar day, recalculated candidate results after parameter changes, exported a real CSV, and checked browser history with no uncaught runtime exceptions.
- Mobile emulation: 390 px viewport has no page-level horizontal overflow; the month input was visually corrected and rechecked. Desktop, mobile, analytics, and report screenshots are in `reports/`.
- Browser print output was rendered and checked as a one-page A4 report: `reports/FIREWATCH_AI_Cameroon_2025-10_Report.pdf`. There is no committed visual baseline or automated axe-core audit; describe the coverage as manual smoke testing.

## Submission checklist

- [ ] Confirm the project title, team members, challenge category, and submission page fields.
- [ ] Add a short demo video or live demo link if the form supports it.
- [ ] Verify that the final link is accessible to judges outside the developer's computer.
- [ ] The application remains a local prototype; public deployment and the challenge portal submission have not been completed from this workspace.
- [ ] Include a concise data/source attribution and explain the evidence limits above.
- [ ] Submit before 11:59 pm Africa/Douala time on 2026-11-15.
