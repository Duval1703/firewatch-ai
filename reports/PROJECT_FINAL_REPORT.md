# FIREWATCH AI - implementation and evidence report

**Project:** NASA Space Apps Challenge 2026, “Harmonization of MODIS and VIIRS Hot Spots”  
**Demonstration area:** Cameroon  
**Status:** Local application implemented and verified. Public deployment, demo publication, and challenge-portal submission remain external tasks.

## Executive summary

FIREWATCH AI is a source-preserving active-fire observation explorer for the supplied FIRMS MODIS and VIIRS extracts. The app now has eight separately addressable pages, shared source filters, a Cameroon map, a daily activity calendar, archive-wide satellite analytics, a cautious robust daily-volume screen, inspectable cross-satellite candidate links, printable/CSV reporting, and a data quality and provenance view.

The current normalized archive contains **1,130,027 rows from 2025-01-01 through 2026-11-02**. The live quality endpoint reports all rows as valid, zero duplicate normalized observation IDs, and zero missing values in the fields it checks. For October 2025 the default app view shows 4,727 observations and 3,985 pairs that satisfy the default 1 km / 3 hour candidate-link rule. Those pairs are observation relationships for review, not 3,985 fires.

## Dataset exploration and inventory

The original data were inspected in the supplied year directories and retained as immutable inputs. Ingestion discovers source CSVs instead of assuming a fixed schema, identifies their product/platform and stream, records file provenance, and preserves original source values alongside normalized analytical fields.

The inventory endpoint currently reports **12 distinct source filenames** and **15 year/product/platform/stream groups**. The archive contains MODIS Collection 6.1 records from Terra and Aqua and VIIRS Collection 2 records from Suomi-NPP, NOAA-20, and NOAA-21. Product/platform identity and `archive` versus `near_real_time` stream remain separate in the normalized records.

The latest quality inspection reports:

- Rows: 1,130,027; validation status `valid`: 1,130,027.
- Duplicate normalized observation IDs: 0.
- Missing values among the inspected lineage, time, coordinate, confidence, and FRP fields: 0.
- Available timestamp extent: 2025-01-01 to 2026-11-02.

These results describe the loaded normalized snapshot and the fields checked by `/api/quality`; they do not establish complete satellite coverage, fire truth, or global availability. Detailed file/schema reconnaissance is in `reports/01_dataset_reconnaissance.md`; the canonical field contract is in `reports/DATA_CONTRACT.md`.

## Data pipeline

The reproducible pipeline is implemented in `src/firewatch/data_pipeline.py` and documented in the numbered notebooks and stage reports.

1. Discover source CSV inputs under the supplied year directories; ignore derived outputs.
2. Retain original fields, source filename, year folder, source checksum, row number, product code, satellite, and stream.
3. Normalize coordinates, numeric measurements, confidence representation, and acquisition date/time into a UTC observation timestamp without erasing source values.
4. Assign a stable observation identifier and validation status. Invalid core coordinates/times are quarantined and recorded rather than silently dropped.
5. Persist derived observations to Parquet under `data/processed/`. Source files are not overwritten.
6. Serve read-only filtered queries through FastAPI for summaries, maps, daily calendars, monthly trends, pair associations, and quality/provenance.

The map API aggregates at coarse zoom levels and uses a deterministic sample at close zoom when necessary; it avoids trying to draw the full million-row archive as individual browser markers. Original MODIS HDF4 and VIIRS NetCDF4/HDF5 readers and checksum-verified bounded downloads support the native-pixel case studies described in `reports/13_bounded_granule_download.md` and later validation reports.

## Harmonization method

FIREWATCH does not equate a nearby point with a confirmed shared event. `src/firewatch/association.py` searches cross-platform observation pairs using a spatial index over unit-sphere coordinates, checks exact great-circle distance, and applies a configurable time window. The day-partitioned search checks adjacent UTC dates so a valid pair near midnight is not excluded. Candidate records retain both source observation IDs, satellites, products, timestamps, distance, time separation, method version, and configured limits.

Candidate rows are not merged into the source table, converted into validated event clusters, or scored as event probabilities. The UI and report state these limits. Independent sample and native-mask work is documented in the linked-pixel, common-coverage, three-sensor, and unlinked-opportunity stage reports. Those selected case studies are not population-level association accuracy tests.

## Analytics and anomaly screen

`/api/trends` groups actual observation rows by calendar month, product, satellite, and stream. The Analytics page shows all delivered months under the active platform/stream filters; choosing a month updates the month-specific comparison and highlights that calendar month in the chart. Months without rows remain blank/unknown rather than being treated as zero activity.

The Anomaly Intelligence page computes a modified robust Z score over daily observation counts for the selected month:

`modified_Z = 0.6745 * (daily_rows - median_daily_rows) / MAD`

Only dates with at least one row enter the baseline; no-row dates are excluded because coverage is unknown. A minimum of 14 observed days is required. The default display flags positive scores of at least 3.5, and the threshold is adjustable. On the current October 2025 default selection, the median is 154 rows/day, MAD is 96, and no day exceeds that threshold.

This is a transparent within-month observation-volume screen, not a seasonal baseline, environmental fire model, outbreak detector, or future prediction. Observation count can vary with overpass and coverage, and the supplied two-year span is insufficient to validate a multi-year month-specific seasonal detector. No trained GPU model is claimed. The user’s RTX 5070 Ti is not needed for this tabular and geospatial workflow; CPU processing is sufficient and avoids adding an unjustified deep-learning layer.

## Application pages and interactions

The React client uses hash routes and browser history so modules open as distinct pages. Date selection and platform/stream filters stay connected to the data views.

| Page | Working behavior |
|---|---|
| Overview | Aggregated Cameroon-area map, counts, platform breakdown, daily chart, optional candidate overlay |
| Satellite explorer | Platform-specific map and counts; platform cards filter shared views |
| Activity calendar | Month grid; day selection narrows shared summary/map; no-row days explicitly mean unknown coverage |
| Fire analytics | Full-period monthly source comparison, same-month 2025/2026 comparison, interactive month selection |
| Anomaly intelligence | Adjustable median/MAD robust-Z daily observation-volume screen with limitations and evidence |
| Candidate links | Editable spatial/time rules, platform-family and text filters, map edges, evidence table, CSV export |
| Reports | Current-filter observation report; browser print/save-to-PDF and daily/platform CSV downloads |
| Data quality | Actual source inventory, validation, duplicate-ID and field-completeness statistics, interpretation guidance |

The running API additionally exposes `/api/health`, `/api/metadata`, `/api/summary`, `/api/map`, `/api/calendar`, `/api/trends`, `/api/candidate-links`, and `/api/quality`. The browser UI is Vite/React, the map is Leaflet, charts use Recharts, and the API/data layer is FastAPI with pandas/Parquet.

## Verification record

- `npm run build`: passed (TypeScript and Vite production build). Current bundle warning: 801.53 kB minified / 235.53 kB gzip; optimization is still possible.
- `py -3.11 -m unittest discover -s tests -v`: **38 passed**. Coverage includes source pipeline, API filters, quality/trend endpoints, CMR manifests, safe downloads, candidate association, and sensor-specific pixel/mask logic.
- `git diff --check`: passed after implementation changes.
- Local Chrome browser smoke test: all eight routes opened, no page error banner or uncaught runtime exceptions; source toggle changed October 2025 count from 4,727 to 4,556; selecting September changed the total to 454; calendar day selection changed the selected-period count; candidate rule changed results when distance was reduced; CSV output contained five actual platform rows.
- Mobile browser emulation at 390 px: document and body widths were both 390 px. The month input’s label overlap was found in screenshot review, fixed, and visually checked again.
- The report’s browser print output was rendered and visually inspected as a one-page A4 PDF. The PDF includes real October counts, the calculated 3,985 candidate-pair total, the robust-screen summary, and limitations.
- Screenshots: `reports/ui_dashboard_overview.png`, `reports/ui_dashboard_mobile.png`, `reports/ui_dashboard_analytics.png`, and `reports/ui_dashboard_reports.png`.

Manual browser testing is not a comprehensive accessibility certification; there is no automated axe-core audit or visual regression baseline. A Vite large-chunk advisory remains. External OSM tiles require network access.

## Artifacts and operating notes

- Data exploration, ingestion, product inspection, harmonization, native pixel validation, and geolocation lineage: `reports/01_*.md` through `reports/23_*.md` and the 22 executable notebooks under `notebooks/`.
- Current submission narrative: `SUBMISSION_BRIEF.md`.
- Local start-up and notebook/test commands: `README.md`.
- Demonstration report: `reports/FIREWATCH_AI_Cameroon_2025-10_Report.pdf`.
- Default local UI: `http://127.0.0.1:5173`; API docs: `http://127.0.0.1:8000/docs`.

### Visual identity refinement

The initial flame-and-AI header treatment was replaced with a custom vector geospatial locator mark and a restrained `FIREWATCH / EARTH OBSERVATION` wordmark. Sparkle-style symbols were removed from the anomaly and insight UI; the printable report uses the same locator mark. The product title remains FIREWATCH AI in metadata and technical materials.

## Completion boundary

The local prototype is implemented and reviewable with the actual downloaded data. This workspace has not published a public deployment, uploaded a demo video, or submitted the challenge form. Those external submission actions and team/form details must be completed in the NASA Space Apps portal; a local URL is not accessible to judges outside this computer. The project also has no independent ground-truth set or validated event/anomaly performance metric, and its claims must remain within the evidence stated above.
