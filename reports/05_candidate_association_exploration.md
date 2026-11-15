# FIREWATCH AI — Stage 05: Candidate Association Exploration

**Date:** 2026-11-14  
**Status:** Candidate-link method implemented and explored on one real month; no event clusters or automated fire decisions created.

## Objective

Test a transparent spatial-temporal association method that makes cross-satellite relationships inspectable without deleting or merging source observations. The candidate links are hypotheses that meet configurable proximity rules, not a measure of truth or a prediction.

## Method

- Input: normalized observations passing the current validation checks.
- Platform identity: source `satellite` field, distinguishing Aqua, Terra, Suomi-NPP (`SNPP`), NOAA-20 (`N20`), and NOAA-21 (`N21`).
- Spatial search: a SciPy `cKDTree` over unit-sphere coordinates finds points within a geodesic search radius; retained distances are calculated with a great-circle formula.
- Temporal search: UTC time difference is computed in minutes. Groups on adjacent UTC dates are compared so a valid near-midnight pair is not lost by daily bucketing.
- Pair scope: a source platform is never linked to itself. Cross-platform candidate links are labeled as MODIS–VIIRS, VIIRS-platform, or MODIS-platform relationships.
- Evidence stored per candidate: observation IDs, satellites, product codes, UTC times, distance, time difference, search thresholds, method version, and a stable candidate link ID.
- Interpretation: candidate links remain pairwise. They do not form event clusters, imply a shared fire, or count as additional fire events.

Implementation: `src/firewatch/association.py`. Interactive exploration: `notebooks/04_candidate_association_exploration.ipynb`.

## Real-data exploratory result

For October 2025, the selected study period had 4,727 normalized observations across five satellite platforms: N20 1,619; N21 1,440; SNPP 1,449; Aqua 171; Terra 48.

Using a deliberately broad **5 km / 12 hour** search envelope produced **12,596 candidate pairs** involving 3,620 distinct observations:

- 10,645 VIIRS-platform pairs.
- 1,925 MODIS–VIIRS pairs.
- 26 MODIS-platform pairs.

This is not a validated setting. Most broad-window links were between VIIRS satellites, which confirms that the application should visibly distinguish cross-instrument links from same-family platform comparisons.

| Maximum distance | Maximum time difference | All candidate pairs | MODIS–VIIRS | VIIRS-platform | MODIS-platform |
|---:|---:|---:|---:|---:|---:|
| 0.5 km | 1 hour | 1,668 | 24 | 1,644 | 0 |
| 1 km | 3 hours | 3,985 | 332 | 3,653 | 0 |
| 2 km | 6 hours | 6,789 | 909 | 5,867 | 13 |
| 5 km | 12 hours | 12,596 | 1,925 | 10,645 | 26 |

The threshold table demonstrates sensitivity, not accuracy. A tighter rule creates fewer candidates but cannot establish that remaining pairs represent the same underlying event. The association output is saved at `data/processed/candidate_links_2025_10.parquet` for reproducibility against the current normalized snapshot.

## Tests and checks

`py -3.11 -m unittest discover -s tests -v` passed **9 tests**, including three association checks:

- A plausible MODIS/VIIRS pair crossing UTC midnight is returned with distance, time, and method parameters.
- Same-satellite observations are not linked to each other.
- Spatial and temporal thresholds exclude an implausibly distant/late pair.

The real October sample ran successfully and the candidate Parquet was written. The notebook is valid nbformat v4 and its code cells pass syntax parsing; it has not been executed as a notebook because of the previously recorded Windows Jupyter kernel reset. The underlying candidate method was run directly on the same data slice.

## Risks and decisions

- Proximity can associate separate nearby fires, especially during dense burning. It can also miss the same evolving fire as its active area spreads beyond the threshold.
- Repeated satellite passes and platform density cause one observation to appear in multiple pair links. This is expected in the evidence graph and must not be counted as multiple fires.
- A simple distance/time threshold is not a probability, event identity, or performance score.
- Connected components can create transitive chains (A near B, B near C, while A is not near C); do not turn this graph into event clusters without a safeguard and evaluation.
- No reference labels or independent fire-perimeter/event data have been assembled, so precision/recall and an “optimal” threshold cannot be claimed.
- The initial candidate pool is bounded at 5 km and 12 hours. Any looser threshold requires rerunning the candidate search, not just filtering the saved pool.

## Next stage

Evaluate candidate behavior across multiple months and compare candidate observation counts with raw detections. Decide whether to add conservative one-to-one matching or keep an evidence graph only. Build coverage-aware daily/monthly activity summaries separately from event inference, and do not publish a harmonized fire-event count until the association method has a defensible validation strategy.
