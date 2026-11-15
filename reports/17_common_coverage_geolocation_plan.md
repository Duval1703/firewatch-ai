# Stage 18: Common-coverage geolocation plan

**Date:** 2026-11-14  
**Status:** Metadata plan prepared and dry-run validated; companion granule transfer pending.

## Objective

Establish the exact geolocation inputs required to test whether two different satellite swaths had valid source-pixel coverage at the other sensor's reported detection coordinate. This is a prerequisite for interpreting the absence of a cross-sensor association. It is not yet a coverage result or a fire-absence claim.

## Selection and lineage

Starting with the 39-observation stratified 2025 validation sample and the exact L2 inputs recorded in the NASA fire-product granules, the notebook recomputed sample candidate associations and chose the tightest time/distance link. The selected observation is Aqua MYD14 at 2025-07-06 13:48 UTC. Its NOAA-21 VJ214IMG partner is at 12:30 UTC, 78 minutes apart, with reported center separation of 0.253693 km. This choice makes a bounded, interpretable pilot; it does not imply that the two detections represent one continuous fire event.

The original L2 product metadata identifies the exact geolocation companions:

| Fire product | Exact geolocation input | Collection version | CMR-reported size |
|---|---|---:|---:|
| MYD14.A2025187.1345.061.2025188110859 | MYD03.A2025187.1345.061.2025188145533.hdf | 6.1 | 32.973 MiB |
| VJ214IMG.A2025187.1230.002.2025327203213 | VJ203IMG.A2025187.1230.021.2025187181751.nc | 2.1 | 184.670 MiB |

The two-file plan totals 217.643 MiB, under the explicit 250 MiB bound. Product lineage is parsed from the downloaded L2 metadata, then exact granule IDs are resolved through CMR. Filename processing-version segments are preserved separately from CMR collection versions.

NASA describes MOD03 as providing Terra geolocation at 1 km pixel centers and identifies VNP03IMG/VJ103IMG/VJ203IMG as VIIRS 375 m geolocation products. These product-specific arrays must be paired with their corresponding active-fire masks and dimensions; nominal sensor resolution or a nearby swath polygon alone is insufficient to establish valid pixel opportunity. See [NASA MOD03](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD03/), [NASA VIIRS L1 geolocation products](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/science-domain/viirs-L0-L1/), and [NASA VNP03IMG](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP03IMG/).

## Implementation and verification

- Added `src/firewatch/geolocation_manifest.py` to extract exact product-specific geolocation input filenames from L2 metadata and query exact CMR granules while retaining source lineage and both version identifiers.
- Added `notebooks/16_common_coverage_geolocation_plan.ipynb`; it rebuilds the selected edge, records why it was selected, resolves exact companion IDs, and writes the plan and its metadata sidecar.
- Extended the bounded downloader to allow the official LAADS Earthdata host/path used by these geolocation companions, while preserving strict HTTPS host/path allowlists, file-count and aggregate-size limits, checksum manifests, no-overwrite behavior, and cross-host authorization stripping. The validator now accepts a plan's explicit `geolocation_granule_id` field as well as the existing fire-granule ID field.
- Notebook 16 executed successfully after the collection-version fallback fix. Dry-run validated exactly two granules and their sizes without a network request. The focused manifest/geolocation suite passed: 12 tests.

## Limitations and next step

No geolocation bytes have been downloaded in this stage. We therefore have not inspected geolocation QA, matched dimensions, or tested cross-swath valid-pixel coverage. Once these two exact companion granules are staged and checksum verified, the next notebook will read coordinates in bounded chunks, locate the nearest native grid cell at each cross-sensor coordinate, validate its QA and paired active-fire mask, and report water/cloud/missing/clear-land/fire opportunity categories separately. A mask classification is product evidence, not independent ground truth.

## Artifacts

- Plan: `data/reference/geolocation_coverage_plan_2025.csv`
- Plan metadata: `data/reference/geolocation_coverage_plan_2025.metadata.json`
- Notebook: `notebooks/16_common_coverage_geolocation_plan.ipynb`
- Downloader: `src/firewatch/granule_download.py`
- Tests: `tests/test_geolocation_manifest.py`, `tests/test_cmr_manifest.py`
