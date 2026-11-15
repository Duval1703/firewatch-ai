# FIREWATCH AI — Stage 06: Activity Calendar and Anomaly Readiness

**Date:** 2026-11-14  
**Status:** Coverage-cautious raw-observation calendar and descriptive comparison implemented; anomaly model deferred for lack of history/coverage evidence.

## Implementation

- Added `src/firewatch/analytics.py` with daily raw-observation calendar and source-level summary functions.
- Each calendar cell carries raw detection count, a boolean for whether rows exist, source year/product/satellite/stream, source file provenance, and an explicit state.
- A zero-row day is represented as `no_rows_coverage_unknown`; it is never presented as a confirmed zero-fire day. The supplied FIRMS CSVs do not include independent sensor coverage logs.
- Calendars retain archive and NRT as separate processing streams and distinguish observation sources. The first and last dates with detections are recorded as data bounds, not asserted coverage bounds.
- Added `notebooks/05_activity_calendar_and_history.ipynb` with month selection, daily heatmap, source summaries, and same-month comparisons.

## Real-data check

October 2025 contains **4,727** raw observations (archive stream). October 2026 contains **8,387** raw observations (NRT stream). These counts describe delivered detections; the stream processing states differ, and counts are not standardized for sensor coverage, confidence, or cross-sensor measurement differences. They must not be called a fire-activity anomaly or direct year-over-year increase in actual fires.

The calendar displays 2025 October rows only for its four archive files and 2026 October rows for the archive and NRT stream dimensions represented in the delivered 2026 sources. Dates with no records remain explicitly unknown for fire activity/coverage.

## Anomaly decision

There is one complete calendar year of archive data (2025) and a partial year of mixed archive/NRT data (2026). This is insufficient independent seasonal history to build and validate a stable month-of-year baseline. In addition, FIRMS detection CSVs alone do not tell us when a sensor had valid observing conditions. Therefore this stage implements no anomaly score or alert. A descriptive same-month comparison is available, clearly labeled with counts and source stream. A future anomaly model needs more consistently processed historical years, a defensible seasonal baseline, and ideally observation-coverage context.

## Testing

- `py -3.11 -m unittest discover -s tests -v`: **11 tests passed** across ingestion, candidate associations, and calendar summaries.
- Calendar tests verify inclusive UTC date bounds, source filters, and that dates without rows are marked coverage-unknown.
- The calendar function was run directly against the full Parquet input for October 2025 and October 2026; totals matched the normalized observations.
- All five notebooks parse as nbformat v4, and Python code cells pass syntax parsing. Notebook 05 itself was not run under Jupyter due the prior Windows kernel-execution issue; its analytics functions were executed directly.

## Limitations

- A date with records does not quantify observing opportunity or clear-sky coverage.
- A date with no records is not evidence that there was no fire.
- Archive and NRT must stay separate in comparisons, especially as archive snapshots replace NRT with standard processing.
- No anomaly detection or future prediction is made at this stage.

## Next stage

Begin the interactive application around the verified local Parquet data: shared country/month/satellite/stream filters, linked map/calendar/analytics, event-link inspection with distance/time evidence, and visible provenance/coverage caveats. Keep the interface read-only until the data semantics are surfaced clearly.
