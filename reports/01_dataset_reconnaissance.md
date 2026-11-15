# FIREWATCH AI — Stage 01: Dataset Reconnaissance

**Date:** 2026-11-14  
**Stage status:** Baseline inventory completed; implementation has not started.

## Objective

Establish what FIRMS data is present in the workspace before making ingestion, harmonization, model, or frontend decisions. This stage is read-only. Original CSVs and ZIP files were not modified.

## Environment reconnaissance

- Workspace contains extracted data under `2025/` and `2026/`; no application source or dependency manifest was present at inspection.
- Python 3.11 is installed. Jupyter, pandas, NumPy, Matplotlib, Seaborn, scikit-learn, and PyArrow are available.
- GeoPandas was not installed at inspection; it is not required for initial CSV inspection.
- Windows detects an NVIDIA GeForce RTX 5070-series GPU with 12,227 MiB VRAM; CUDA 13.1 is installed. A GPU is not needed for CSV validation, descriptive statistics, or a transparent first-pass spatial association method. GPU use will be evaluated only if a later workload benefits from it.

## Data inventory

The workspace contains 12 extracted CSVs and four corresponding ZIP files in each year directory. Product codes imply the following sources: `M-C61` MODIS C6.1 (Terra and Aqua), `SV-C2` Suomi-NPP VIIRS, `J1V-C2` NOAA-20 VIIRS, and `J2V-C2` NOAA-21 VIIRS. The row-level satellite and instrument fields agree with those product identities in the inspected files.

| Year | MODIS C6.1 | Suomi-NPP | NOAA-20 | NOAA-21 | Total records |
|---|---:|---:|---:|---:|---:|
| 2025 | 42,120 | 227,320 | 224,606 | 218,188 | 712,234 |
| 2026 | 19,151 | 132,671 | 136,272 | 129,699 | 417,793 |

2026 totals include archive and NRT records. They are partial-year data and are not directly comparable with complete 2025 totals.

## Coverage findings

- All 2025 archive CSVs span 2025-01-01 through 2025-12-31.
- 2026 VIIRS archive files span 2026-01-01 through 2026-07-31; VIIRS NRT files span 2026-08-01 through 2026-11-02.
- 2026 MODIS archive spans 2026-01-01 through 2026-08-29; MODIS NRT spans 2026-09-09 through 2026-11-02. This leaves September 1–8 without MODIS observations in the delivered files.
- Date-span endpoints do not prove continuous daily coverage. Missing days must be checked explicitly before interpreting low counts or no detections.

## Schema and quality findings

Archive CSVs contain 15 columns: `latitude`, `longitude`, `brightness`, `scan`, `track`, `acq_date`, `acq_time`, `satellite`, `instrument`, `confidence`, `version`, `bright_t31`, `frp`, `daynight`, and `type`. NRT files contain the same 14 fields except `type`.

Observed archive versions are MODIS `61.03` and VIIRS `2`; NRT labels are `6.1NRT` for MODIS and `2.0NRT` for VIIRS. Preserve these exact source values and file/stream provenance.

Initial file-level inspection found no empty cells and no exact duplicate rows among the 12 CSVs. All records had parseable observation dates and coordinates within legal latitude/longitude bounds. This is a baseline check, not a complete validation of ranges, product-specific flag domains, timestamp validity, or duplicates across different files.

Confidence representation differs by instrument family: MODIS confidence is numeric while VIIRS confidence uses categorical `n`, `l`, `h`. Do not pool these as a common score. MODIS source identity must also retain Terra versus Aqua; these share a product file.

## MODIS and VIIRS implications

The delivered products differ by instrument family and platform: MODIS C6.1 records identify Aqua/Terra, while three VIIRS C2 products identify Suomi-NPP, NOAA-20, and NOAA-21. This provides four satellite streams for comparison, not simply a binary MODIS/VIIRS split. Their confidence encodings and product metadata differ, so harmonization should align observation identity and provenance without assuming measurement equivalence. Product resolution, detection characteristics, confidence semantics, and measurement units should be cited from official product documentation before analytics are built.

## Recommended next technical decisions

1. Verify the CSVs against their ZIP members and record download/readme metadata.
2. Confirm geographic extent and whether the delivery is a Cameroon-region extract; the sample coordinates suggest Central Africa, but that should be checked across every row before relying on it.
3. Build an immutable raw-observation layer with `source_file`, `product_code`, `stream_type`, ingestion timestamp, original version, and a stable observation identifier.
4. Normalize dates/times and numeric types in a derived table while retaining all original columns. Validate the time zone convention and timestamp construction against the product spec.
5. Keep archive and NRT provenance distinct. Establish overlap/replacement rules; do not sum overlapping streams blindly.
6. Build candidate cross-sensor associations with explicit spatial and temporal evidence and tunable thresholds. Keep observations distinct and event clusters explicitly inferred. Avoid blindly using connected-components/DBSCAN chaining that can merge spatially extended, unrelated fire activity.
7. Report separate raw detections and inferred clusters in maps and calendar analytics. Use source-appropriate confidence handling and do not compare FRP/confidence directly unless the relevant product documentation supports the comparison.
8. Establish daily coverage metrics, seasonal baselines, and anomaly rules only after the coverage and stream policies are settled.

## GPU decision

The RTX 5070 Ti with 12 GB VRAM is available for future workloads, but the scientifically central work—CSV processing, spatial joins, matching evidence, and seasonal count baselines—is primarily data- and I/O-bound and can run on CPU for this dataset scale. A GPU should be used only for a justified later task (for example, large raster inference or a validated learned model); it should not drive model selection.

## Files created

- `notebooks/01_dataset_reconnaissance.ipynb` — runnable, read-only notebook for discovery, schema, coverage, quality, and distribution summaries, with a coverage visualization.
- `reports/01_dataset_reconnaissance.md` — this findings and decision log.

## Next stage

Stage 02 should formalize the raw and normalized data contracts, reconcile archive/NRT delivery behavior, and turn the notebook into a reproducible ingestion/validation pipeline. The harmonization algorithm and UI should follow those decisions, not precede them.
