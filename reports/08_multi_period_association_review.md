
# FIREWATCH AI — Stage 09: Multi-period association review

**Date:** 2026-11-14  
**Status:** exploratory sensitivity review on seven archive-only month slices; no labeled validation or deduplication.

## Question and protocol

Does the current candidate-link method behave consistently across multiple periods, and how dense is the evidence graph? For January, April, July, and October 2025, plus January, April, and July 2026, run the existing pairwise method at a fixed 1 km / 3 hour envelope. Each selected slice uses `archive` only. Output remains pairwise evidence and source rows are untouched.

## Results

| Month | Archive rows | Candidate pairs | Pairs / 1,000 rows | Rows participating in ≥1 edge | MODIS–VIIRS pairs | VIIRS-platform pairs | MODIS-platform pairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025-01 | 221,667 | 317,546 | 1,432.5 | 161,818 (73.0%) | 33,268 | 284,278 | 0 |
| 2025-04 | 12,790 | 17,294 | 1,352.1 | 7,629 (59.7%) | 1,076 | 16,218 | 0 |
| 2025-07 | 430 | 157 | 365.1 | 154 (35.8%) | 18 | 139 | 0 |
| 2025-10 | 4,727 | 3,985 | 842.8 | 2,340 (49.5%) | 332 | 3,653 | 0 |
| 2026-01 | 146,995 | 188,017 | 1,279.1 | 100,040 (68.1%) | 14,312 | 173,705 | 0 |
| 2026-04 | 6,522 | 6,422 | 984.7 | 3,083 (47.3%) | 335 | 6,087 | 0 |
| 2026-07 | 937 | 981 | 1,047.0 | 476 (50.8%) | 42 | 939 | 0 |

The candidate graph is dominated by VIIRS-platform pairs for every selected period. MODIS–VIIRS matches in these samples are mostly Aqua-N20/N21/SNPP; Terra has few observation rows. Median edge distances ranged from 0.389 to 0.526 km, and median time differences ranged from 26 to 51 minutes.

## Interpretation and decisions

- Candidate edges exceed the raw input-row count in several periods because an observation can have multiple neighboring observations on other platforms. This is expected in a pairwise graph and demonstrates why edges cannot be counted as fires or deduplicated detections.
- A large share of rows participating in at least one edge is not evidence of match precision. No reference labels, independent active-fire events, or validated sensor revisit constraints are available.
- The selected month slices have highly uneven row volumes. This is an exploratory stress review, not a balanced seasonal test or evidence of changing sensor performance.
- Keep a transparent evidence graph as the current harmonization product. Do not add one-to-one matching, event clustering, or an anomaly score until an evaluation dataset/protocol is established.
- Preserve each source's native confidence and FRP fields; these are not treated as cross-sensor equivalent measures.

Notebook: `notebooks/07_multi_period_association_review.ipynb`. It reproduces the seven month slices, the summary table, satellite-pair breakdown, and plots from the normalized Parquet.

## Verification

`py -3.11 -m jupyter nbconvert --to notebook --execute --inplace notebooks\\07_multi_period_association_review.ipynb` completed successfully with no cell errors; summary tables and both plots are embedded. The first execution exposed that the notebook kernel starts in `notebooks/`, so a project-root `sys.path` setup was added before importing `src`. Subsequent execution passed. Windows printed a pyzmq Proactor-loop warning, which did not interrupt execution. The seven-period calculation takes around 20–30 seconds.

