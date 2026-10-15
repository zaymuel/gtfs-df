# 0001. DFTrans Data Extraction and GTFS Synthesis for r5py

Date: 2026-10-14
Status: Accepted (All Rounds 1–4 Settled)

## Context

The Federal District (Brasília - DF) transit authority (Semob-DF) does not publish open GTFS feeds or downloadable geospatial layers on GeoPortal. For the Transport Modeling course (PPGT/UnB) accessibility and spatial equity study, we need to extract the transit network data and construct a valid static GTFS feed to feed the `r5py` routing engine (OpenTripPlanner/R5 Java backend).

Through exploratory reverse-engineering, we identified the official DFTrans REST API (`https://www.sistemas.dftrans.df.gov.br`), which provides public endpoints for line search, rich vehicle/operator metadata, route geometry (in EPSG:3857), bus stop coordinates, and timetable departure schedules.

---

## Decisions Made (Rounds 1, 2, 3 & 4)

### 1. Data Source & Catalog Discovery

* **Decision**: Use the official DFTrans REST API as the exclusive source of truth for geometries, stops, metadata, and schedules, paired with automated, live catalog discovery.
* **Discovery Strategy**:
  * **API Limitation**: The DFTrans search endpoint `GET /linha/find/{termo}` enforces a hard server-side cap of 30 records per search, preventing complete network enumeration via wildcards or single digits.
  * **Authoritative Ingestion**: For each line number, the pipeline executes an exact, un-capped lookup against `GET /linha/numero/{numero}` on the official DFTrans REST API, ensuring 100% authoritative, real-time operational data for directions, `sequencial` IDs, geometries, stops, and timetables.

### 2. Target Output Contract

* **Decision**: Target solely a fully compliant, validated GTFS feed (`gtfs_df.zip`).
* **Rationale**: `r5py` operates strictly on OpenStreetMap (`.osm.pbf`) and GTFS feeds. Standalone GIS formats (GeoPackage / Shapefile) are omitted to keep the pipeline streamlined.

### 3. Temporal Modeling & Timetables

* **Decision**: Extract timetables via `GET /horario/linha/numero/{numero}` from the outset.
* **Stop Times Synthesis & Speed Separation**:
  * **Conventional Urban Lines**: Simulated at an average operating speed of 20 km/h with 30 seconds dwell time per stop.
  * **BRT Lines (Expresso DF Sul / BRT Santa Maria & Gama / BRT Oeste)**: Operating on dedicated busways up to 60 km/h, simulated at an average operating speed of 40 km/h with 30 seconds dwell time per stop.
  * **Detection**: Identified via vehicle metadata (`tiposOnibus` containing "Padron BRT" or "Articulado BRT") and line numbering/naming conventions (e.g., `TR 20`, `2201`, `2202`, `2205`, `2301`, `2304`).
* **Calendar Mapping**: DFTrans schedules (`dias_uteis`, `sabado`, `domingo_feriado`) map to three standard recurring service IDs in `calendar.txt` (`weekday`, `saturday`, `sunday`) with an active validity range of `20260101` to `20261231`. In GTFS, this single schedule definition automatically replicates across all 365 days of the year for `r5py`.

### 4. Storage Architecture & Crawl Resilience

* **Decision**: Implement a 3-tier persistent storage architecture:
  * `data/catalog/`: Discovered lines master index (`lines.json`) and audit logs.
  * `data/raw/`: Atomic per-line raw JSON payloads (`{line_number}.json`) for full offline reproducibility and resumable scraping.
  * `data/gtfs/`: Generated GTFS CSV tables and final `gtfs_df.zip`.
* **Rate Limiting**: Polite delays (0.5s–1s) with exponential backoff on HTTP 429/5xx errors to prevent API IP blocking.

### 5. Coordinate Transformation

* **Decision**: DFTrans route geometries returned in EPSG:3857 (Web Mercator) must be reprojected to EPSG:4326 (WGS84 decimal degrees) before writing `shapes.txt` and `stops.txt`.

### 6. Network Topology & Directionality

* **Decision**:
  * `IDA` mapped to `direction_id = 0`.
  * `VOLTA` mapped to `direction_id = 1`.
  * `CIRCULAR` mapped to `direction_id = 0` as a continuous closed-loop trip.

### 7. Stop Snapping & Linear Referencing

* **Decision**: Bus stop coordinates are orthogonally snapped onto the nearest segment of the route polyline (`LineString`). The linear distance along the line (`shape_dist_traveled`) is calculated to enforce strictly increasing, forward-moving stop sequences, preventing `r5py` backward-travel errors.

### 8. Data Quality Filtering & Academic Methodology

* **Decision**: Implement rigorous quality gates: any line lacking valid geometry, having fewer than 2 stops, or missing valid departure schedules is excluded from `trips.txt` and recorded in `data/catalog/skipped_lines.json` with the exclusion rationale.
* **Documentation**: The methodological rationale and exclusion criteria are formally documented in `docs/methodology_data_filtering.md` for direct inclusion in the paper's Methodology section.

### 9. Agency & Fare Roadmap

* **Decision**: `agency.txt` models SEMOB/DFTrans as the unified transit authority.
* **Roadmap / Backlog**: Fares are cataloged in project TODOs for subsequent economic disparity and transit affordability modeling.

### 10. Modular Implementation Architecture

* **Decision**: Decouple the software into three distinct modules:
  * `config.py`: Centralized configuration (speeds, dwells, calendar dates, file paths).
  * `extract.py`: Online crawler that generates `data/catalog/lines.json` and caches `data/raw/{line}.json`.
  * `build_gtfs.py`: Offline GTFS synthesizer that performs reprojection, stop snapping, speed interpolation, quality validation, and builds `gtfs_df.zip`.
