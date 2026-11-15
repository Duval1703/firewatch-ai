# FIREWATCH AI — Stage 07: Interactive Application

**Date:** 2026-11-14  
**Status:** First data-backed local web prototype implemented; API/build smoke checks passed; visual browser review blocked by local browser automation timeouts.

## Product direction

Designed the first screen as a working observation-analysis tool for a Cameroon demonstration. A disciplined graphite masthead frames a warm, low-glare workspace; source colors distinguish MODIS, Suomi-NPP, NOAA-20, and NOAA-21. The map is the main working surface, with the daily calendar and source counts beside it. Copy calls out the difference between detections and confirmed fires.

## Backend

Added `src/firewatch/api.py` with read-only FastAPI endpoints:

- `/api/health` — loaded row count and data file.
- `/api/metadata` — date range, source/platform counts, default Cameroon map view, limitations.
- `/api/summary` — filtered raw detection counts by product, satellite, and stream.
- `/api/calendar` — source-specific daily activity states and counts.
- `/api/map` — source-colored spatial aggregation that becomes individual detections at closer zoom, with deterministic sampling above 5,000 points.
- `/api/candidate-links` — candidate pairs with distance/time evidence; capped at 5,000 returned links and limited to a 32-day request window.

The API reads the normalized Parquet store and exposes GET-only endpoints. It distinguishes archive/NRT processing streams and includes caveats in the metadata.

## Frontend

Added a Vite/React/TypeScript dashboard under `web/` with:

- Month picker, satellite filters, and archive/NRT stream filters.
- Shared filter state updating the summary, map, daily chart, and candidate-link query.
- Leaflet/OpenStreetMap visualization with resolution-dependent spatial aggregation and source-specific colors.
- Clickable daily bars that focus summary/map to one day.
- Optional dashed MODIS–VIIRS candidate-link overlay, labeled as unconfirmed.
- Responsive layout, semantic controls, visible focus states, and reduced-motion handling.

Frontend dependencies are pinned exactly in `web/package.json` and `package-lock.json`. Backend versions are pinned in `requirements.txt`. `README.md` documents setup, data processing, app start, notebooks, and tests.

## Verification

- `py -3.11 -m unittest discover -s tests -v`: **14 tests passed**, including FastAPI metadata, filtering, calendar, map, candidate links, and invalid-query handling.
- `npm run build` in `web/`: passed. Vite warns the combined JavaScript chunk is ~764 kB before gzip (~227 kB gzip); later bundle splitting is an optimization opportunity.
- Dependency audit during installation: 0 known vulnerabilities reported by npm.
- Live local smoke check: API `/api/health` reports 1,130,027 rows; October 2025 returns 4,727 raw detections, 1,224 aggregated map cells at zoom 6, 155 source-calendar cells, and 3,985 candidate links at 1 km / 3 hours; frontend root returns HTTP 200.
- Browser visual QA could not be completed. The supplied `webapp-testing` helper script is missing, the in-app browser tab creation and local browser-window inspection both timed out, and downloading the Python Playwright wheel was cancelled after extended network delay. This limitation is recorded rather than claiming a screenshot-based review.

## Known limits

- The local prototype has only Cameroon data and a fixed default map extent; multi-country selection/boundaries are not yet implemented.
- OpenStreetMap tiles and Google Fonts require internet access in the browser.
- Detailed zoom returns at most 5,000 individual observations by deterministic sample; wide zoom uses per-grid counts. The UI indicates sampled/aggregated modes.
- Candidate links are hypotheses; no clustering or verified unique fire-event counts are shown.
- The anomaly module remains deferred because the current history cannot support a validated seasonal baseline.
- Build chunk size and browser visual QA should be addressed before a public demo.

## Next stage

Review the local dashboard visually in a working browser, improve any layout issues, assess map coverage and country boundaries, and add end-to-end testing. Then decide whether to acquire more historical/coverage data before anomaly work or prioritize a demonstrable calibrated event-association comparison.

## Stage 08 reconnaissance — country-boundary scope

- Checked the current geoBoundaries API metadata for Cameroon ADM0 (ISO3 CMR). It returns one Cameroon polygon, represented year 2016, boundary ID `CMR-ADM0-59405334`, source `geoBoundaries, Wikimedia`, boundary license `CC BY 3.0`, and a pinned GitHub-backed GeoJSON URL. geoBoundaries requires attribution; its individual-country boundaries follow the country representation and do not encode disputed-area alternatives.
- Downloaded and pinned the exact GeoJSON artifact locally under `data/reference/`; it is a contextual administrative boundary, not a NASA FIRMS coverage mask, and cannot prove that the delivered FIRMS extracts cover all of Cameroon.

- The active project interpreter is py -3.11; Shapely/GeoPandas are absent, but pandas, NumPy, Matplotlib, and PyArrow are available. A vectorized Matplotlib Path containment calculation was used and verified in the new notebook, without installing packages.

- Source: [geoBoundaries API documentation](https://www.geoboundaries.org/api.html) and [Cameroon gbOpen ADM0 metadata](https://www.geoboundaries.org/api/current/gbOpen/CMR/ADM0/).

### Stage 08 — Cameroon boundary audit (completed 2026-11-14)

- Downloaded the pinned geoBoundaries Cameroon ADM0 GeoJSON from commit `9469f09` to `data/reference/geoBoundaries-CMR-ADM0-2016.geojson`. Metadata: boundary ID `CMR-ADM0-59405334`, represented year 2016, source geoBoundaries/Wikimedia, boundary license CC BY 3.0. SHA-256: `2688A0D9B15237A71E2620222F963BA5D00F06D7376F0497B807605DF2D5B1A3`.
- Ran vectorized point-in-polygon across all 1,130,027 normalized coordinates: 1,122,291 inside Cameroon ADM0 (99.3154%); 7,736 outside. Exterior points occur in all sensor/product families. Kept all points; did not treat exterior coordinates as bad records.
- Reproducible notebook: `notebooks/06_cameroon_boundary_scope_audit.ipynb`. It verifies the boundary checksum before evaluating, summarizes source-wise distribution, and visualizes the scope check.
- Interpretation: supports a Cameroon-centered/regional extract characterization, not proof of complete national FIRMS coverage. Country boundary is contextual, not a sensing/coverage mask. No detections were removed.
- Verification: `py -3.11 -m jupyter nbconvert --to notebook --execute --inplace notebooks\\06_cameroon_boundary_scope_audit.ipynb` completed successfully; checksum assertion, counts, source breakdown, and plot rendered into the notebook. No packages were installed. Windows emitted a pyzmq Proactor-loop runtime warning; execution completed and outputs were written.

