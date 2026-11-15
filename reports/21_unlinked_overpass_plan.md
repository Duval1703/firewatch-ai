# Stage 22: Unlinked-observation overpass plan

**Date:** 2026-11-14  
**Status:** One NOAA-20 Level-2 overpass selected from the real CMR manifest; dry-run passed; transfer pending.

## Question

For an Aqua sample detection with no cross-platform FIRMS candidate inside the 1 km / 3 h rule, did a nearby NOAA-20 Level-2 swath pass over the same coordinate, and how did its full fire-mask grid classify that coordinate? The archive candidate label cannot answer this; the selected swath's native product mask can add opportunity context.

## Actual case selection

The sample row is Aqua, Q3, 2025-09-18 14:06 UTC at 4.0848 N, 9.3146 E. Its recorded status is `no_candidate_link_under_1km_3h`. Using the saved 2025 CMR Level-2 manifest, the notebook filtered NOAA-20 VJ114IMG granules to those whose time intervals overlap ±3 h and whose CMR polygon contains the coordinate. It selected the closest granule-center time, breaking ties by producer granule ID:

- `VJ114IMG.A2025261.1330.002.2025261205555`
- CMR interval: 13:30–13:36 UTC; center is 33 minutes before the Aqua point.
- CMR size estimate: 2.706 MiB.
- Bounded plan: one file, 10 MiB aggregate cap; dry-run accepted without network access.

This is a deliberately matched single case to compare with the Q3 candidate-linked Aqua neighborhood. CMR polygon containment is only coarse metadata selection. It does not establish that a valid pixel covers the coordinate or that the pixel is clear, land, cloud-free, or capable of detecting fire.

## Artifacts

- Executed notebook: `notebooks/20_unlinked_overpass_plan.ipynb`.
- One-granule plan: `data/reference/unlinked_opportunity_l2_plan_2025.csv` and metadata sidecar.
- Selected counterpart Level-2 product: NOAA-20 VJ114IMG.

## Next step and limits

Download this one NOAA-20 L2 granule. Its native input metadata will identify the exact VJ103IMG companion; resolve that exact ID through CMR, then inspect the NOAA-20 geolocation QA and fire mask at the Aqua coordinate. The Aqua source MYD14 granule is already locally available, but its exact geolocation companion for this September observation must also be resolved and downloaded before nearest-pixel comparisons. A mask result at one time/location remains case-study evidence, not an unbiased no-link evaluation or independent truth label.
