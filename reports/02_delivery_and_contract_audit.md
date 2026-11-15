# FIREWATCH AI — Stage 02: Delivery Integrity and Data Contract

**Date:** 2026-11-14  
**Status:** ZIP integrity and source schema/coverage audit completed. No source files were modified.

## Work carried out

1. Enumerated all ZIP bundles and their member files.
2. Compared SHA-256 digests of every ZIP member with the corresponding extracted file.
3. Rechecked record dates per CSV and counted dates with at least one record.
4. Compared archive and NRT distinct calendar dates by product/year.
5. Formalized a proposed raw-to-normalized observation contract, documented in `DATA_CONTRACT.md`.
6. Added the runnable notebook `notebooks/02_delivery_and_contract_audit.ipynb`. Its code cells passed Python syntax parsing. A Windows Jupyter kernel reset prevented saving notebook execution outputs; ZIP integrity was instead verified independently with a standalone Python script. The notebook remains available for interactive execution.

## Integrity results

All **20 ZIP members** (12 CSVs and eight readmes) had matching extracted files, and all extracted bytes were an exact SHA-256 match for the corresponding ZIP member. This verifies extraction integrity only; it does not independently validate NASA product semantics.

## Date-presence results

The CSVs contain detections, not satellite coverage logs. These date counts describe dates with at least one row, not days with confirmed sensor coverage. A day with no row cannot be interpreted as no fire. Within the first-to-last record-date span, there are additional calendar dates without rows in each file, reinforcing the need for coverage-aware calendars.

In 2026 the archive/NRT sets have **zero overlapping calendar dates** in this snapshot for all four product codes. VIIRS streams transition from an archive last date of July 31 to NRT beginning August 1. MODIS archive ends August 29, and MODIS NRT begins September 9, leaving September 1–8 without MODIS observations in the provided files. The handoff in these downloaded files does not establish future FIRMS archive/NRT refresh behavior.

| Year/product | Records in archive | Records in NRT | Archive dates with rows | NRT dates with rows |
|---|---:|---:|---:|---:|
| 2026 J1V-C2 (NOAA-20) | 132,632 | 3,640 | 206 | 81 |
| 2026 J2V-C2 (NOAA-21) | 126,367 | 3,332 | 207 | 86 |
| 2026 M-C61 (MODIS Terra/Aqua) | 18,845 | 306 | 187 | 30 |
| 2026 SV-C2 (Suomi-NPP) | 129,011 | 3,660 | 194 | 77 |

## Data contract decision

The unified observation record must retain source file/checksum, product code, archive/NRT stream, original satellite/instrument/version, original date/time tokens, and source measurements. Normalize values in additional fields and record warnings or rejection reasons instead of silently discarding bad rows. Archive `type` is nullable because it is absent from NRT. MODIS numeric confidence and VIIRS categorical confidence remain distinct. Candidate event links will be represented separately from raw detections, with the evidence and threshold configuration recorded.

## Challenges and open questions

- A notebook execution reset occurred on Windows during nbconvert. The notebook is reconstructed and code-cell syntax checked, but this execution did not produce stored outputs. Stage 01's notebook has executed successfully.
- Download README files are brief pointers and do not provide full product definitions. Official FIRMS documentation is still needed for acquisition time semantics, measurement units/valid ranges, confidence meanings, and NRT/archive update behavior.
- Files have date gaps and no observation-date stream can be used as a substitute for coverage information.
- Spatial extent must be confirmed across all rows before making Cameroon or neighboring-country coverage claims.

## Next stage

Implement a reproducible ingestion and validation pipeline using the contract, then test it against these files. Before deriving UTC timestamps, association thresholds, or source confidence mappings, verify the relevant product documentation. Preserve raw data and make all exclusions auditable.
