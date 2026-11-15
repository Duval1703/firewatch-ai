# FIREWATCH AI — Stage 15: L2 source-pixel validation pilot

**Date:** 2026-11-14  
**Status:** Two real granules downloaded and inspected; positive product-internal pixel correspondences found. This is not independent validation of event identity or detection accuracy.

## Retrieval and integrity

The bounded October sample plan was retrieved to `data/reference/granules/oct2025_pilot/`. The user token was read only from the local PowerShell process environment and removed after the transfer. It is not present in repository files or the download manifest.

| Product | Bytes | SHA-256 | Collection | Algorithm/process version |
|---|---:|---|---:|---|
| Aqua MODIS MYD14 | 232,775 | `33fe211d434fed8784a39f3082fb688718acee6bea14d5b42ccc50e72ab32927` | 061 | 6.2.3 |
| Suomi-NPP VIIRS VNP14IMG | 2,626,193 | `fd0fb6ffa8bcca1c3e5d628407cfe4b5cf2414d5bf0a3ebb0fb8b3f4e0dbc987` | 002 | 3.1.9 |

The actual byte counts are consistent with CMR's approximate sizes. The download manifest stores filenames, counts, retrieval times, and SHA-256 digests. The granule directory is ignored by Git so these binary reference inputs are not accidentally committed.

## Method

Added `src/firewatch/swath_validation.py`. For each sample-plan row it:

1. Reads the sensor-native active-fire pixel latitude/longitude list (VIIRS NetCDF4/HDF5 via `h5py`; MODIS HDF4 via `pyhdf`).
2. Calculates haversine distance from the original FIRMS point to every listed fire-pixel center and selects the nearest record.
3. Reads that record's line/sample and checks the product's native fire-mask raster at that cell.
4. Preserves collection/process version, pixel coordinates, product-native confidence field, FRP, and mask class separately.

Notebook `notebooks/13_source_pixel_validation.ipynb` verifies checksums first, checks each CSV observation time against the native granule interval, displays the comparison and plot, and writes `data/processed/source_pixel_validation_oct2025.csv`.

## Results

| FIRMS observation | Nearest native fire pixel from CSV point | Native fire mask | Product-native confidence | FRP |
|---|---:|---:|---:|---:|
| Aqua MYD14, 2025-10-20 13:26 UTC | 0.004711 km (4.71 m) | 8, nominal-confidence fire | 50 percent | 29.827 MW |
| Suomi-NPP VNP14IMG, 2025-10-20 13:10 UTC | 0.000396 km (0.40 m) | 8, nominal-confidence fire | code 8 (nominal category) | 4.300 MW |

Both CSV times fall inside their granule intervals: MYD14 13:25–13:30 UTC and VNP14IMG 13:06–13:12 UTC. The selected CSV observations themselves were 0.5554 km apart and 16 minutes apart. Their native granules contain 262 MODIS and 818 VIIRS active-fire pixel records, respectively. In those granules, MODIS masks contain 5 low-, 194 nominal-, and 63 high-confidence fire pixels; VIIRS contains 40 low-, 725 nominal-, and 53 high-confidence fire pixels.

## Interpretation and limits

The close coordinate matches plus class-8 fire-mask cells provide direct product-internal evidence that each FIRMS row is represented among the selected L2 granule's active-fire pixels. This supports the row-to-granule join and validates the basic reader/indexing path for these two products.

The sample was deliberately selected from an existing candidate association, so it is selection-biased. The result does not prove the two sensor detections correspond to the same physical fire, estimate precision/recall, characterize missed detections, or establish a calibrated harmonized count. MODIS `FP_confidence` is a percentage whereas VIIRS uses categorical confidence codes; their raw values must not be compared. The two FRP values are retained as sensor-specific and are not treated as cross-calibrated. Pixel masks identify product algorithm classes, not ground truth.

The fire mask line/sample indices read at the selected active-fire list record resolve to class 8 in both native products. Other mask values are interpreted only through the legend embedded in each granule. No neighboring pixels were promoted to detections.

## Environment and verification

- Installed `pyhdf==0.11.7` locally after confirming a compatible CPython 3.11 Windows wheel; pinned it with `h5py==3.14.0` in `requirements.txt`.
- Added three offline tests for haversine distances, VIIRS metadata/pixel-mask matching, and required-dataset validation.
- Executed notebook 13 end-to-end successfully; it writes the real two-row derived CSV and embeds the output table/figure.
- A Windows `pyzmq` Proactor event-loop warning appeared during notebook execution but was non-fatal.
- Granules remain local in the Git-ignored reference directory; original 2025/2026 FIRMS inputs were not changed.

## Next step

Expand this pixel-join check to a reproducible, stratified sample of candidate and non-candidate observations across months and instrument pairs. Before evaluating association quality, define valid observation opportunities/coverage from the source masks and add an independent reference. Harmonization should retain one row per sensor observation, product-native confidence/FRP, processing lineage, and explicit association evidence; do not collapse to inferred events until a validation design supports it.
