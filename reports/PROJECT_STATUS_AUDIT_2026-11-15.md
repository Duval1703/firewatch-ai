# FIREWATCH AI — Project status and scientific-readiness audit

**Audit date:** 2026-11-15  
**Demonstration area:** Cameroon  
**Archive inspected by the running local API:** 1,130,027 records, 2025-01-01 through 2026-11-02

## Executive assessment

FIREWATCH is a functioning, data-backed exploration prototype. It preserves MODIS and VIIRS source identity, gives users connected map, calendar and platform views, exposes transparent proximity-based observation pairs, reports measurable data-quality checks, and now includes an experimental daily source-row forecast with in-app review watches. The application is useful for exploring how the source products relate.

It does **not yet establish unique fire events or demonstrate population-level accuracy**. The candidate-link engine reports spatial/temporal pairs under user-selected thresholds. It does not resolve those pairs into event tracks or deduplicated fires. No independent ground-truth reference set has been used to estimate precision, recall, missed-event rate or false-link rate. Therefore, the system addresses the challenge as an interactive harmonization and evidence-review prototype, but it cannot yet claim that it accurately counts distinct fires.

## Feature audit

| Capability | Current state | What has been checked | Limitation / next step |
|---|---|---|---|
| Source-preserving archive and provenance | Working | API reports 1,130,027 rows over the archive date range; quality endpoint reports zero duplicate normalized IDs and zero missing values in its inspected fields | Confirm archive/NRT version handling for every comparison; successive processing versions may represent repeated reports |
| Cameroon observation map | Working | Live API returned 1,224 display cells for October 2025 at zoom 6 | Map is a visualization of rows/cells, not fire perimeters or confirmed events; external basemap requires connectivity |
| Shared date, platform, and stream filters | Working for checked flows | Browser verified the month picker updates observed-volume alerts and toggling SNPP updates the forecast from 936 to 636 rows/day MAE | Continue checking shared-filter propagation on every analytics module and on the final hosted build |
| Satellite comparison | Working | Source/platform summary endpoint feeds the comparison view; five platform identities are represented | Raw counts are affected by product characteristics, overpass frequency, coverage and archive/NRT versions; they are not directly comparable fire counts |
| Daily calendar | Working | October 2025 calendar endpoint returned observations; date selection is wired to the shared workspace | Missing rows represent unknown coverage, not zero activity |
| Candidate associations | Working as candidate generation | Live endpoint returned 3,985 October 2025 pairs at 1 km and 3 h; UI exposes limits, evidence and exports | Pairs are not confirmed shared fires, clustered events, or a deduplicated count. Threshold sensitivity and independent labels are outstanding |
| Alerts & forecast | Implemented; forecast remains experimental | Historical month volume flags use robust median/MAD; seven-day seasonal-window forecast compares against same-date last year in rolling chronological holdout | Predicts valid FIRMS row volume only. Backtest MAE is 936.4 rows/day and WAPE is 68.6%; archive ends 2026-11-02 and is stale for live warning |
| In-app alerts | Implemented as review signals | Historical volume flags and forecast watches use explicit thresholds and link users to inspect historical dates | No email, SMS, browser push, or live feed. Neither signal identifies or predicts a fire |
| Data quality and lineage | Working | Live endpoint reports 1,130,027 rows, zero repeated normalized IDs and zero missing values in inspected normalized fields | These checks do not demonstrate observation correctness or source granule completeness |
| Reports and CSV exports | Locally smoke-tested | Candidate, calendar, daily, platform, and inventory CSVs downloaded with valid headers and expected row counts; A4 print preview is a one-page PDF | Check native print-to-PDF once on the presentation machine; report is an observation summary, not a validated fire-event report |
| Data assistant | Working as deterministic helper | Answers route through fixed rules and loaded workspace values | No language model is connected; it is not an independent scientific analyst and has limited question coverage |
| Landing page | Redesigned and locally bundled | New `#home` route; uses local NASA Earth Observatory imagery with source links and historical captions | Scenes are archival West Africa context, not the Cameroon extract or current conditions |

## Data and harmonization interpretation

The product set includes MODIS C6.1 observations from Terra and Aqua, and VIIRS C2 observations from Suomi-NPP, NOAA-20 and NOAA-21. They retain separate platform/product/stream fields. Confidence and fire-radiative-power values remain in source-specific fields rather than being collapsed into a common confidence score.

The current association method is a useful transparent baseline: compare eligible records from distinct platforms, calculate spatial distance and UTC time separation, and emit a candidate link when both values fall under selected limits. This supports exploration of cross-sensor overlap. It is not sufficient for scientifically defensible unique-event reconstruction by itself because point proximity ignores the full pixel footprint, scan geometry, geolocation uncertainty, acquisition context, fire evolution and repeated processing versions.

Recommended next scientific iteration:

1. Keep row-level ingestion and source lineage immutable, including product/version, stream, acquisition time, coordinates and native quality fields.
2. Treat archive/NRT version reconciliation as a separate, explicitly documented stage. Do not silently sum versions and label them independent detections.
3. Generate cross-sensor candidate edges with documented, sensor-aware spatial and temporal criteria. Where source granules support it, add native pixel geometry, geolocation QA and mask/coverage state.
4. Make candidate groups or event tracks a separate layer with a versioned method and auditable edge membership. Preserve the original observation rows.
5. Build an independently reviewed, stratified evaluation set across platforms, seasons, regions, link distances, time gaps and no-link cases. Report precision/recall and uncertainty by subgroup before making accuracy claims.
6. Evaluate robustness to thresholds and compare a simple baseline to any later model. Keep model output interpretable and avoid GPU training until a validated task and sufficient labeled data justify it.

The available NVIDIA RTX 5070 Ti is not needed for the current ingestion, tabular filters, spatial indexing, median/MAD screen, or this small seasonal forecast. It may help with future large raster workloads or a suitably labeled learning task, but GPU use alone would not improve scientific validity.

## UI changes in this audit

- Added an art-directed project landing page as the first route (`#home`), with a direct action into the existing dashboard.
- Replaced project screenshots with NASA Earth Observatory imagery of West and Central African fire scenes; each image links to its NASA source and is captioned as archival regional context, not current Cameroon data.
- Updated the landing page to use locally bundled Aqua MODIS and Suomi-NPP VIIRS imagery from NASA Earth Observatory so both scenes render without third-party image requests. Kept image descriptions, acquisition dates and direct NASA source links with the visuals.
- Reworked the visual hierarchy around a forest-green field-atlas palette, larger editorial headings, IBM Plex Sans body text, a map-first workspace, clearer module navigation, and short page-entry transitions. Reduced-motion settings disable the motion.
- Replaced the target-like brand mark with an original satellite-to-ground observation mark and removed the AI suffix from the public product title.
- Added sections explaining source preservation, proximity association, linked time views and scientific caveats.
- Added mobile layout rules, keyboard-visible focus inherited from the app, semantic section/navigation elements, descriptive image alt text and reduced-motion handling.
- Added a Home item to the existing module navigation; existing dashboard views retain their own routes.
- Removed repeated page kickers, sidebar microcopy, redundant footer text, and the shared-filter helper sentence. Supporting UI text is larger and the module navigation now uses one clear label per destination.
- Renamed the former anomaly-only module to **Alerts & forecast**. It shows historical volume flags, archive freshness, a seven-day volume estimate, backtest comparison and threshold-based review watches.
- Clarified the forecast page as an archive-based projection, and dynamically warns when the projection window has already passed. On this snapshot the archive ends 2026-11-02, while the projected window is 2026-11-03 to 2026-11-09; it is not a current future warning.
- Added the API and CPU-only seasonal 15-day window forecast. The 306-day rolling holdout MAE is 936.4 versus 1,021.5 rows/day for the one-year naive baseline; WAPE remains 68.6%, so it is labeled experimental.
- Added the Jupyter walkthrough [23_observation_volume_forecast.ipynb](../notebooks/23_observation_volume_forecast.ipynb).
- Completed browser-driven responsive and interaction checks using a temporary Playwright installation outside the project dependencies. Confirmed all eight dashboard module links open their route and render the expected page heading.
- Confirmed month and satellite filters update visible results; the 390 px layout has no document-level horizontal overflow on the nine main application routes.
- Ran axe WCAG 2.1 A/AA checks on the landing page and the forecast page at desktop and mobile widths, including the deselected-satellite state. The final scans report zero violations. The audit found and corrected low-contrast text, the brand link's mismatched accessible name, and a missing favicon that produced a 404.

## Verification performed on 2026-11-15

- `py -3.11 -m pytest -q`: **45 passed**. One dependency deprecation warning was reported by Starlette/httpx; no test failed.
- `npm run build`: **passed**. Vite reports an 822.95 kB minified JavaScript chunk (241.34 kB gzip), above the 500 kB advisory threshold. This is a performance optimization opportunity, not a build failure.
- Live API smoke check: `/api/health` returned `ok`; `/api/metadata` reported the archive through 2026-11-02; `/api/quality` returned 1,130,027 rows, zero normalized duplicate IDs and zero missing values in inspected fields.
- Representative October 2025 endpoint checks: summary 4,727 rows; map 1,224 cells; candidate association 3,985 pairs at 1 km / 3 h. Calendar endpoint returned the expected grouped daily/platform records.
- Live `/api/forecast`: data through 2026-11-02, 13 days stale on the audit date; it produced a 2026-11-03 to 2026-11-09 archive-volume projection and no month-p90 watches.
- All four NASA imagery URLs returned HTTP 200 at the NASA Science asset host.
- `git diff --check`: passed.
- Browser QA: all eight dashboard module routes opened; the source filter changed the forecast score from 936 to 636 rows/day MAE; the October 2026 month selection appeared in the observed-alert module; 13 API responses completed without HTTP errors; no browser console errors remained. Desktop and mobile axe scans of the landing and forecast pages returned zero WCAG 2.1 A/AA violations.
- Responsive smoke check: all nine principal application routes were checked at 390 px; each had matching viewport and document widths, with no horizontal page overflow.
- Workflow smoke checks: calendar selection focused 2025-10-01 and showed 29 source observations; candidate pairs for that selected date fell from 19 to 9 when the maximum distance changed from 1 km to 0.5 km; the data assistant answered with the selected date's live count; and map zoom controls responded with 22 map features rendered.
- CSV checks: candidate links 3,985 data rows, calendar 155, daily observations 155, platform summary 5, and source inventory 15. Each exported file had a non-empty header, sample row, and no download failure. VIIRS-only filtering reduced the candidate table to 3,653 of 3,985 pairs.
- Print check: report action invoked and Chromium generated a valid one-page A4 PDF. Visual inspection found an orphaned source line on a second page; hiding the screen-only page heading in print CSS fixed the layout. The final render contains the full report and source attribution on one page.
- Browser responses across these workflows had no HTTP errors. A hosted deployment remains untested.

## Visual redesign and free-hosting preparation (2026-11-15)

- Replaced external image loading with two local NASA Earth Observatory images: Aqua MODIS over West Africa (22 Jan 2008) and Suomi-NPP VIIRS over West Africa (10 Dec 2015). Captions identify the date and sensor and state that these are regional archival context, not current Cameroon conditions.
- Browser inspection at 1440 px and 390 px confirmed both local images load, the landing page has no horizontal overflow, the atlas opens on its Overview route, and the mobile page fits its viewport. No browser console or page errors were observed.
- The Overview screenshot initially appeared to highlight Data quality because the pointer hovered that sidebar row after the landing-page layout changed. DOM inspection confirmed `aria-current="page"` and the active class are correctly on Overview.
- `npm run build`: passed after the redesign. The existing Vite large-chunk advisory remains at about 820 kB minified / 241 kB gzip.
- `py -3.11 -m pytest -q`: 46 passed, with one existing Starlette/httpx deprecation warning.
- PyArrow-backed DataFrame loading reduced the measured normalized archive frame from 761.1 MiB to 244.3 MiB. The source Parquet remains unchanged. A separate gzip-compressed deployment copy is 83.77 MiB; it can be read through a gzip stream at API startup. A regression test covers compressed-Parquet loading.
- Initial Arrow-backed tests exposed a Windows timezone database error in Arrow temporal rounding and formatting. Keeping date values as NumPy-backed UTC datetimes while the other columns use Arrow fixed the issue; the full suite then passed.
- Added a Vercel deployment profile with runtime-only `pyproject.toml` dependencies, FastAPI frontend serving, a 60-second function duration, inclusion of the compressed archive, and exclusions for raw downloads, granule files, notebooks and reports. No Earthdata credentials are in the profile.
- Hosting research: Vercel Hobby is free for personal, non-commercial projects; FastAPI functions allow up to 2 GB memory and Python bundles up to 500 MB. The 84 MiB deploy archive and runtime dependency profile are intended to fit, but the provider build must confirm the final bundle size. Render Free has 512 MB RAM and idles out after 15 minutes; its documented cold start is about one minute. Local API startup measured around 512 MiB, so Render is not the selected backend.
- No deployment has been published. The repository has no Git remote and Vercel CLI is not installed or logged in. A provider build check is underway; hosted API and browser flows still need verification before the app can be called deployed.

## Remaining priorities

### Before describing the product as accurate

- Create and document a representative independent reference set.
- Quantify candidate-link precision/recall, threshold sensitivity and failure modes.
- Define how archive/NRT records are reconciled in count views.
- Add event grouping only after the link rules and labels are evaluated.

### Before an external judge can use the application

- Publish the app or provide a judge-accessible hosted demo.
- Package or securely serve the required archive; local git-ignored data is not present in a public checkout.
- Repeat browser interaction and keyboard/accessibility checks against the final deployed build; verify native print-to-PDF output on the presentation machine.
- Reduce the main JavaScript bundle by splitting route-specific charts/maps if performance warrants it.

## Safe presentation statement

> FIREWATCH is a Cameroon-first NASA FIRMS observation explorer that keeps MODIS and VIIRS source context visible, compares observations through explicit space/time candidate links, and connects the map, calendar and analytics. Candidate links are review evidence, not confirmed fires or deduplicated events; the prototype has not yet been evaluated against an independent population-level fire-event reference set.
