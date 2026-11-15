# FIREWATCH AI — Stage 04: Ingestion and Normalization

**Date:** 2026-11-14  
**Status:** Initial pipeline implemented and run against all delivered CSVs.

## Implementation

- Added `src/firewatch/data_pipeline.py` for source discovery, source checksums, product/stream identification, raw-token preservation, normalized numeric columns, minute-precision timezone-aware UTC timestamps, per-row quality flags, and a deterministic ID tied to the exact source snapshot and row number.
- The loader only discovers CSVs within numeric year directories, so derived summary files are not re-ingested.
- No source CSV is edited. Invalid rows remain in the output and receive `quarantine` status with reason flags; the pipeline does not silently discard them.
- MODIS and VIIRS confidence are kept source-specific. Product codes identify VIIRS categorical confidence, including Suomi-NPP rows whose `instrument` field says `SNPP` rather than `VIIRS`.
- Added `notebooks/03_ingestion_and_normalization.ipynb` with source discovery, execution, quality summaries, monthly analytics, and a spatial point-cloud visualization.
- Added six focused unit tests in `tests/test_data_pipeline.py`.

## Real-data run

The pipeline processed all **1,130,027 rows** from the 12 source CSVs:

- 2025: 712,234 rows.
- 2026: 417,793 rows.
- Valid by current checks: 1,130,027.
- Quarantined: 0.
- Input files: 12, all represented in the output summary.
- Output: `data/processed/observations.parquet` (about 126.8 MB) and `data/processed/ingestion_summary.csv`.

The 38-column normalized Parquet includes all original columns as text plus provenance, source snapshot IDs, numeric conversion columns, confidence family, UTC timestamp, precision, and validation results. `type_num` remains null for NRT because the source CSV has no `type` field.

## Testing

`py -3.11 -m unittest discover -s tests -v` passed all six tests. Coverage includes raw string preservation, UTC timestamp construction, categorical VIIRS confidence, NRT optional `type`, quarantine behavior for invalid coordinate/time, deterministic source-snapshot IDs, and excluding derived CSVs from input discovery.

Notebook files parse successfully as nbformat v4 and their Python code cells pass syntax parsing. Notebook 03 itself was not run through Jupyter; the same real-data ingestion function was executed directly and its outputs were inspected. Notebook 02 also remains unexecuted inside Jupyter due to the documented Windows kernel reset, although its checksum audit passed independently.

## Challenges and limitations

- A first test asserted `pd.NA` equality directly and failed because pandas missing values do not support boolean equality. The assertion was corrected to use `pd.isna`; all tests now pass.
- The first real ingestion run emitted a pandas warning for concatenating all-null NRT `type_num` columns. Numeric fields were changed to a consistent nullable Float64 type and the real run was repeated without the warning.
- Testing revealed that the Suomi-NPP `instrument` value is `SNPP`, so instrument-string matching would misclassify its confidence field. Classification now uses the known FIRMS product code, with a dedicated regression test.
- A derived summary CSV initially could have been rediscovered as source data. Source discovery is now scoped to year-named directories, with a regression test.
- Validation currently covers required source fields, date/time parsing, and coordinate ranges. It does not yet enforce product-specific numeric ranges or scientific plausibility limits; those need authoritative field documentation.
- The output is an observation table only. It has not deduplicated detections, created events, or calculated harmonized fire activity.

## Next stage

Stage 05 will build transparent candidate cross-sensor associations and evaluate spatial/time thresholds. Candidate links will not overwrite or remove any raw observation. We will compare raw detections with associated observations and report sensitivity before selecting a calendar aggregation policy.
