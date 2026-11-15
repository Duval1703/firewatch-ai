# FIREWATCH AI — Raw and normalized observation contract

## Principles

1. Raw source files are immutable. Derived data always points back to source file and checksum.
2. Product identity, source satellite, instrument, version, and archive/NRT stream are explicit dimensions.
3. Normalize for queryability without deleting or rewriting original field values.
4. Distinguish missing field, invalid value, absent observation date, and absent coverage evidence.
5. Harmonized events are inferences linked to observations, not replacements for them.

## Source schemas

Archive products share 15 columns: `latitude`, `longitude`, `brightness`, `scan`, `track`, `acq_date`, `acq_time`, `satellite`, `instrument`, `confidence`, `version`, `bright_t31`, `frp`, `daynight`, `type`. NRT files share the same observed fields except `type`; therefore `type` is nullable in a unified table and must not be synthesized.

## Required normalized fields

- Identity/provenance: `observation_id`, `source_file`, `source_sha256`, `product_code`, `stream_type`, `source_row_number`, `ingested_at`, `pipeline_version`.
- Sensor metadata: `source_satellite`, `source_instrument`, `source_version`; retain source text exactly.
- Position/time: original latitude/longitude and acquisition date/time, normalized numeric coordinates, and a derived timestamp only after time semantics are confirmed.
- Measurements/flags: source brightness, `bright_t31`, scan, track, FRP, day/night, confidence, and type. Preserve raw values/missingness and keep the confidence family.
- Data quality: parse/validation status and a list of rejection or warning reasons. Do not silently drop rows.

## Stream policy

Keep archive and NRT records as separate source observations with explicit stream labels. This snapshot shows adjacent date spans for the 2026 product streams, but downloaded snapshots may overlap or be updated. A later ingestion policy must compare source product, satellite, date/time, spatial identity, and source versions before deciding whether to retain, supersede, or deduplicate records. Never deduplicate solely because two observations are geographically close.

## Event association table

A separate relation should connect one or more source observations to a candidate event using `event_id`, `observation_id`, algorithm/version, spatial distance, time difference, threshold configuration, and association evidence. Associations are uncertain and revisable.

## Decisions pending product documentation

- FIRMS acquisition-time timezone/semantics and safe UTC construction.
- Definitions, units, validity ranges, and comparability of sensor measurements.
- Confidence class semantics by product.
- NRT/archive refresh and overlap semantics.
- Spatial coverage/download query bounds for these files.
