# FIREWATCH AI — Stage 03: Product Documentation Review

**Date:** 2026-11-14  
**Status:** Initial NASA product guidance reviewed; decisions and limits recorded.

## Authoritative sources reviewed

- [NASA FIRMS active-fire data](https://firms.modaps.eosdis.nasa.gov/content/active_fire/) — source products, NRT replacement in archive, and stated archive lag.
- [NASA FIRMS archive download](https://firms.modaps.eosdis.nasa.gov/download/) — archive products and science-quality replacement note.
- [NASA FIRMS fire-alert notes](https://firms.modaps.eosdis.nasa.gov/alerts/notes.php) — acquisition time UTC, MODIS/VIIRS resolution context, confidence caution, and missed-detection limitations.
- [NASA FIRMS data descriptions](https://firms.modaps.eosdis.nasa.gov/descriptions/FIRMS_MODIS_Firehotspots.html) — field definitions and version information.
- [NASA VIIRS Land Products active-fire description](https://viirsland.gsfc.nasa.gov/Products/NASA/FireESDR.html) — 750 m and 375 m VIIRS products, algorithm and resolution context.
- [NASA FIRMS ingestion tutorial](https://firms.modaps.eosdis.nasa.gov/content/academy/data_ingest/firms_data_ingest.html) — CSV time conversion examples and confidence field distinction.
- [NASA FIRMS regional coordinates](https://firms.modaps.eosdis.nasa.gov/active_fire/coordinates.html) — regional download boxes. The region list does not expose a Cameroon-only box.

## Findings and engineering implications

### Observation time

FIRMS states acquisition time is UTC. The source CSV provides `acq_date` and `acq_time` at minute precision (HHMM-style values; leading zeros may be present). The normalized pipeline can construct a UTC timestamp after zero-padding and validation, while retaining the raw tokens and avoiding any implication of second-level precision.

### Product and resolution differences

MODIS C6.1 includes Terra and Aqua and is described by FIRMS at approximately 1 km; the VIIRS FIRMS streams here are the 375 m products for Suomi-NPP, NOAA-20, and NOAA-21. Higher spatial resolution increases response to smaller fires, so raw counts across MODIS and VIIRS are not directly comparable measures of fire activity. The interface must expose instrument filters and show raw detection counts as sensor observations, not a sensor-neutral quantity.

### Confidence

MODIS confidence is numeric (0–100) and NASA cautions it is experimental and can vary in meaning across geography. VIIRS confidence is categorical (`l`, `n`, `h` in these files). Keep source-specific confidence fields and avoid a pooled ranking or universal threshold. Any product-specific filters should be labelled and explained.

### Archive and NRT

NASA FIRMS says archive NRT data are replaced with observations extracted from standard MODIS/VIIRS products as those become available, typically after roughly 2–3 months and sometimes up to about 5 months. Therefore, archive/NRT records for the same source/time are alternate processing states, not independent corroborating detections. Preserve original snapshots and lineage; in a combined analytical view, prefer science-quality archive rows for dates they cover and use NRT for the recent tail, with explicit source status. Never sum both versions blindly. The current 2026 files have no calendar-date overlap, but the policy must handle overlap in later snapshots.

### Measurement caution

NASA VIIRS product materials distinguish the 375 m detection product from the 750 m product. The 375 m product uses higher-resolution imagery channels for detection and incorporates M13 for characterization; the FRP workflow can distribute a coarser measurement across coincident finer pixels. FRP and brightness must retain original product context, and direct cross-sensor FRP comparison should not be a headline metric without an explicit validation/normalization method.

### Detection gaps and interpretation

NASA notes fires may be missed when they start and end between overpasses or are obscured by cloud, smoke, or canopy; MODIS may also miss small/cool fires within its coarser footprint. A date without records is not a confirmed zero-activity day or proof of coverage. Future activity calendars should display data-presence/coverage cautions and distinguish no detections from unavailable observations.

### Geographic scope

Observed coordinates in all files fall within a tight Central African envelope, consistent with the intended Cameroon demonstration. Point extrema describe where detections occurred; they do not reveal the original request bounding box or source region metadata. We cannot claim these files cover Cameroon completely until download request metadata or a documented country-boundary comparison is available. NASA's listed North and Central Africa regional box is much broader than Cameroon.

## Stage 03 decisions

1. Normalize acquisition timestamps as timezone-aware UTC at minute precision while retaining the original date/time strings.
2. Keep MODIS Terra and Aqua and all three VIIRS satellites independently filterable.
3. Keep MODIS numeric confidence and VIIRS categorical confidence source-native.
4. Treat NRT and archive as processing lineage states. Prefer standard archive for periods it covers and use NRT for the recent tail; retain source snapshots and replacement audit details.
5. Keep raw sensor measurements intact; defer cross-sensor FRP ranking/thresholds.
6. Treat missing detection dates as unknown activity/coverage, not zero fires.
7. Do not claim complete Cameroon coverage from coordinate extents alone.

## Next stage

Implement an immutable-source ingestion/normalization pipeline using these decisions, and validate counts, UTC parsing, normalized schemas, and quality flags against all 12 CSVs.
