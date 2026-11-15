# FIREWATCH AI — Stage 11: Validation reference and source-field audit

**Date:** 2026-11-14  
**Status:** Completed documentation/catalog reconnaissance and source-field audit; no new granules downloaded and no validation labels created.

## Supplied data: validation-relevant fields

The normalized Parquet has 1,130,027 rows. `scan_num` and `track_num` have **0 missing values**. NASA FIRMS defines these as along-scan and along-track pixel sizes in km; scan/track dimensions vary with geometry. Observed medians are around 0.42–0.44 km for the VIIRS platforms and 1.1–1.2 km for MODIS, with substantially larger upper tails at some viewing angles. The per-row values make a pixel-scale-aware distance analysis feasible. The source is still only a pixel center plus two dimensions: no corner coordinates or ground-oriented footprint polygon is present, so exact overlap cannot be recovered from this CSV alone.

The `type` field is null on **10,938 rows**, exactly the total NRT row count; all archive rows have a value. Archive distribution:

| Code | Interpretation in product guides | Rows |
|---:|---|---:|
| 0 | Presumed vegetation fire | 1,115,388 |
| 1 | Active volcano | 35 |
| 2 | Other static land source | 2,899 |
| 3 | Offshore | 767 |

This is an algorithm-inferred category, not independent reference truth. NASA’s VIIRS guide documents a Type-field error in monthly product versions 1 and 2 and says affected files were reprocessed as version 3 in May 2025. The supplied ZIP readmes only point to the generic FIRMS README; source filenames and row-level `version=2` do not identify the monthly product packaging revision. Therefore, keep `type` as provenance and a quality-review field, and do not use it as an association label until the exact production lineage is resolved. MODIS and VIIRS product-specific definitions must remain explicit.

`daynight` and `confidence` are populated. VIIRS confidence remains categorical; MODIS confidence remains numeric. These can support stratified descriptive checks but not a pooled confidence score.

The findings are reproducible in `notebooks/09_source_field_and_reference_readiness.ipynb`, which executed successfully and embeds the field summary and dimension distributions.

## Official coverage and validation data options

### 1. MODIS and VIIRS Level-2 active-fire swaths — best next coverage source

For October 2025, NASA CMR granule metadata returned spatial-temporal matches to the dashboard bounding box (8°E–17°E, 1°N–14°N) for all five source platforms. Collection/product identifiers and catalog counts:

| Platform | Standard L2 product | Collection | CMR entries | Unique acquisition IDs* |
|---|---|---:|---:|---:|
| Suomi-NPP | VNP14IMG | 002 | 165 | 165 |
| NOAA-20 | VJ114IMG | 002 | 158 | 158 |
| NOAA-21 | VJ214IMG | 002 | 172 | 160 |
| Terra | MOD14 | 061 | 122 | 122 |
| Aqua | MYD14 | 061 | 142 | 142 |

\*Unique IDs were estimated by removing the processing timestamp suffix. NOAA-21’s 12 extra catalog records are reprocessing variants, not additional independent overpasses. The query yielded at least one granule acquisition on each October day for each source; NOAA-20 also returned a preceding-day granule intersecting the query time interval. These counts come from CMR granule metadata; a granule bounding-box hit is **not** proof that all pixels in Cameroon were observed validly.

NASA’s VIIRS 375 m L2 swath contains the fire-mask class array and same-grid algorithm QA. Its classes distinguish fire-confidence categories from land, water, cloud, unprocessed, and other conditions. MODIS MOD14/MYD14 L2 likewise includes fire masks and QA layers. These products can supply an observation-opportunity denominator and help distinguish “validly observed without fire” from “unknown/unprocessed,” which the FIRMS detection-only CSV cannot do. Source collection references: [VIIRS C2 375 m Active Fire User Guide](https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf), [MODIS C6/C6.1 Active Fire User Guide](https://www.earthdata.nasa.gov/s3fs-public/2023-09/MODIS_C6_C6.1_Fire_User_Guide_1.0.pdf), and NASA CMR granule catalog (query parameters are recorded in the notebook).

The point CSVs do not include the full swath mask, pixel vertices/orientation, or stable per-granule identifiers. A useful next ingestion needs a granule manifest, authenticated archive retrieval if required, per-pixel geolocation/QA, and an auditable join back to CSV detections. This is coverage validation, not independent truth: each L2 product under study is the source from which its own detections were derived.

### 2. EUMETSAT LSA SAF SEVIRI/MSG FRP-PIXEL — independent temporal corroboration

The LSA SAF product page lists Africa coverage, approximately 3 km sampling and 15-minute temporal resolution for the MSG SEVIRI FRP-Pixel product, including historical data record/NRT access. Its geostationary cadence could indicate whether fire activity persists around a polar-orbiter observation. It uses a different sensor and detection process, but its coarser pixels and own omission/commission behavior make it corroboration rather than ground truth. [LSA SAF fire products and access](https://lsa-saf.eumetsat.int/en/data/products/fire-products/).

### 3. Monthly burned area — post-event corroboration only

MODIS MCD64A1 and VIIRS VNP64A1 are 500 m monthly burned-area products. They can help check whether an area was mapped as burned after the active-fire period, but they do not label an exact FIRMS observation or time. Their QA and unmapped/insufficient-observation information must be included; a mapped burn scar is not a complete reference for small, short-lived or cloud-obscured fire activity. Sources: [MCD64A1 guide](https://lpdaac.usgs.gov/documents/875/MCD64_User_Guide_V6.pdf) and [VNP64A1 guide](https://lpdaac.usgs.gov/documents/2124/VNP64_User_Guide_v1.1.pdf).

## Recommended validation ladder

1. Use one mature demonstration month, October 2025; download only its MOD14, MYD14, and three VIIRS L2 swaths after confirming access and exact collection versions.
2. Build an immutable granule manifest (collection, platform, acquisition time, processing time/version, spatial bounds, source checksum).
3. Reconcile each FIRMS CSV hotspot with its source L2 fire pixel and retain the matched granule/pixel ID plus coordinate/time residuals.
4. Construct per-source valid-observation footprints from pixel geolocation, fire mask and QA. Keep fire, valid non-fire land, cloud, water, glint, bow-tie deletion, and unprocessed/unknown states separate as supported by each guide.
5. Compare sensors only for explicit temporal/spatial opportunity overlaps. Recompute candidate edges and nulls over eligible common coverage; do not penalize a sensor where it did not observe validly.
6. Add SEVIRI persistence and/or QA-filtered burned-area corroboration only as separate evidence layers. Seek Cameroon agency or field incident/perimeter data for eventual external validation.

## Environment and execution

CMR catalog metadata queries succeeded without downloading the granules. This stage did not test NASA Earthdata or EUMETSAT authenticated data access. The notebook ran end-to-end with Python 3.11; Windows printed non-fatal Jupyter/pyzmq event-loop messages. No production source code or original NASA files were changed. No GPU is warranted for this catalog/attribute audit or a modest October coverage pilot.

## Decisions

- Promote `scan` and `track` to first-class retained source metadata in association diagnostics; initially use them only in an explicitly approximate sensitivity method.
- Do not call any `type` value a ground-truth label. Resolve the VIIRS monthly production revision before using Type analytically.
- Prioritize standard L2 swath coverage masks as the next technical work, with SEVIRI as optional independent temporal corroboration.
- Keep model/anomaly work deferred until there is a reliable exposure/coverage denominator and independent evaluation target.
