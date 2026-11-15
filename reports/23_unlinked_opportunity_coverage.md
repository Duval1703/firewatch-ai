# Stage 24: Unlinked-case pixel opportunity

**Date:** 2026-11-15  
**Status:** Download integrity, reprocessing consistency, and two-swath mask lookup completed for one sampled case.

## File integrity

Both geolocation files passed plan-linked manifest checks:

| File | Bytes | SHA-256 |
|---|---:|---|
| MYD03.A2025261.1405.061.2025262150419.hdf | 33,260,201 | `84b7948a73ba2a2626bc60e915db1f318a21df0b40c6e041593214e147c5b2bd` |
| VJ103IMG.A2025261.1330.021.2025267192836.nc | 191,223,131 | `5061c25308ac6da716bbe6e48ff911a835355608af4ccf693e8e114b335ace60` |

The NOAA-20 source L2 file also passed its SHA-256 manifest check. The NOAA-20 grid `(6464, 6400)` matches its paired L2 mask dimensions.

## Reprocessed NOAA-20 geolocation consistency

The exact VJ103IMG processing timestamp named in the NOAA-20 L2 global metadata is absent from current CMR. A currently listed same-acquisition reprocessing was used with the original-vs-reprocessed lineage exception retained. We checked the candidate reprocessing against the L2 product's 16 `FP_line`/`FP_sample` indices and embedded `FP_latitude`/`FP_longitude` values:

- Median coordinate residual: **0.025 m**.
- 95th percentile: **0.059 m**.
- Maximum: **0.074 m**.
- All 16 embedded fire-pixel locations were below 0.1 m residual.
- VIIRS geolocation quality flags at those indices were 0.

This is strong consistency evidence at the active-fire pixels in this granule. It is not proof that every geolocation coordinate across the entire swath is byte-for-byte or pointwise identical to the missing prior processing instance.

## Aqua target result

The Aqua Q3 sample row is from 2025-09-18 at 14:06 UTC, coordinate 4.0848 N, 9.3146 E, and has no FIRMS candidate link under the configured 1 km / 3 h rule. The NOAA-20 L2 granule covers 13:30–13:36 UTC, about 33 minutes earlier.

| Swath mask queried at Aqua coordinate | Nearest pixel-center distance | Native mask class | QA |
|---|---:|---|---|
| Aqua MODIS | 0.0038 km | Class 8: nominal fire | MOD03 `gflags=0` |
| NOAA-20 VIIRS | 0.2399 km | Class 1: bowtie | VIIRS geolocation quality flag 0 |

The Aqua point is inside the NOAA-20 swath's geolocation grid, but its nearest NOAA-20 fire-mask pixel is **bowtie**, not clear land. Therefore this case does not show a valid clear-land NOAA-20 observation opportunity at that coordinate. The absent candidate association cannot be interpreted as a NOAA-20 fire miss from this point. The product mask and geolocation QA remain separate: the nearest coordinate's geolocation QA is good, while the Level-2 mask category is bowtie.

## Artifacts and verification

- Executed notebook: `notebooks/22_unlinked_opportunity_coverage.ipynb`.
- Output table: `data/processed/unlinked_opportunity_pixel_coverage_2025.csv`.
- Plan and download metadata: `data/reference/unlinked_opportunity_geolocation_plan_2025.csv` and `data/reference/granules/unlinked_opportunity_geolocation_pilot/download_manifest.json`.
- The notebook verified byte counts and SHA-256, measured all 16 fire-pixel coordinate residuals, and performed both nearest-coordinate/mask lookups. All code cells completed without errors.

## Limits and next work

This is one matched case from one candidate-status stratum, not a representative sample. The comparison uses nearest pixel centers rather than full pixel footprints and is asynchronous by 33 minutes. The result is an observation-opportunity classification for the chosen pixel, not ground truth, missed-fire evidence, event identity, or a model performance score. Extend to multiple satellites, regions, seasons, and linked/unlinked strata before estimating association quality; retain bowtie, glint, cloud, water, clear land, and fire as distinct classes.
