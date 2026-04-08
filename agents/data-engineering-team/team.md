# Data Engineering Team

## Mission
Build robust data pipelines that ingest, normalize, and unify data from all CAE simulation tools into a common representation suitable for ML training.

## Agents & Model Assignments
- **Parser Developer** (Sonnet): Builds format-specific parsers for each CAE tool
- **Schema Architect** (Opus): Designs and maintains the unified data schema — foundational decision
- **Pipeline Engineer** (Sonnet): Builds ETL pipelines from raw to ML-ready data
- **Data Quality Agent** (Haiku): Validates data integrity and detects anomalies — rule-based checks

## Supported Tools (Priority Order)
1. Abaqus (ODB/HDF5) — most common FEA tool
2. Moldex3D (XML/binary) — SMC/RTM simulation
3. Digimat (DAF) — material modeling
4. AniForm — forming simulation
5. Simutence — multi-process simulation
6. cadfil — filament winding

## Code Location
- `src/data/parsers/` — Tool-specific parsers
- `src/data/schemas/` — Unified data schema definitions
- `src/data/pipelines/` — ETL pipeline code
- `src/data/quality/` — Data validation rules

## Key Principles
- Every parser must output the unified schema
- All unit conversions happen in the normalization layer
- Data versioning with DVC
- Every dataset must have metadata (source tool, material, process type)
