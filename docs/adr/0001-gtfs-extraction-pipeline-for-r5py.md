# 0001. DFTrans Data Extraction and GTFS Synthesis for r5py

Date: 2026-10-14
Status: Accepted (Rounds 1 & 2 Settled; Round 3 Pending)

## Context

The Federal District (Brasília - DF) transit authority (Semob-DF) does not publish open GTFS feeds or downloadable geospatial layers on GeoPortal. For the Transport Modeling course (PPGT/UnB) accessibility and spatial equity study, we need to extract the transit network data and construct a valid static GTFS feed to feed the `r5py` routing engine (OpenTripPlanner/R5 Java backend).

Through exploratory reverse-engineering, we identified the official DFTrans REST API (`https://www.sistemas.dftrans.df.gov.br`), which provides public endpoints for line search, rich vehicle/operator metadata, route geometry (in EPSG:3857), bus stop coordinates, and timetable departure schedules.

## Decisions Made (Rounds 1 & 2)

### 1. Data Source & Catalog Discovery
* **Decision**: Use the official DFTrans REST API as the exclusive source of truth for geometries, stops, metadata, and schedules.
* **Discovery Strategy**: Use a single HTTP request to `GET /linha/find/%25` to discover all active bus lines in DFTrans, rather than scraping third-party websites.

### 2. Target Output Contract
* **Decision**: Target solely a fully compliant, validated GTFS feed (`gtfs_df.zip`).
* **Rationale**: `r5py` operates strictly on OpenStreetMap (`.osm.pbf`) and GTFS feeds. Standalone GIS formats (GeoPackage / Shapefile) are omitted to keep the pipeline streamlined.

### 3. Temporal Modeling & Timetables
* **Decision**: Extract timetables via `GET /horario/linha/numero/{numero}` from the outset.
* **Stop Times Synthesis**: Since DFTrans supplies terminal departure times rather than per-stop schedules, intermediate stop arrival and departure times will be interpolated using cumulative distance along route polylines at a nominal urban bus speed (20 km/h) plus a standard 30-second dwell time per stop.
* **Calendar Mapping**: DFTrans schedules (`dias_uteis`, `sabado`, `domingo_feriado`) map to three standard service IDs in `calendar.txt` (`weekday`, `saturday`, `sunday`) over a representative study period.

### 4. Storage Architecture & Crawl Resilience
* **Decision**: Implement a 3-tier persistent storage architecture:
  * `data/catalog/`: Discovered lines master index (`lines.json`) and audit logs.
  * `data/raw/`: Atomic per-line raw JSON payloads (`{line_number}.json`) for full offline reproducibility and resumable scraping.
  * `data/gtfs/`: Generated GTFS CSV tables and final `gtfs_df.zip`.
* **Rate Limiting**: Polite delays (0.5s–1s) with exponential backoff on HTTP 429/5xx errors to prevent API IP blocking.

### 5. Coordinate Transformation
* **Decision**: DFTrans route geometries returned in EPSG:3857 (Web Mercator) must be reprojected to EPSG:4326 (WGS84 decimal degrees) before writing `shapes.txt` and `stops.txt`.

---

## Decisions Pending Review (Round 3)

The following decisions are queued on the frontier for the user's return:
1. **Directionality**: Map `IDA` -> `direction_id=0`, `VOLTA` -> `direction_id=1`, and `CIRCULAR` -> `direction_id=0` as closed loops.
2. **Stop Snapping**: Project stop coordinates onto route polylines to calculate `shape_dist_traveled` and guarantee strictly forward-moving stop sequences.
3. **Data Quality & Filtering**: Exclude lines lacking valid geometry or having fewer than 2 stops from `trips.txt`, logging them to `data/catalog/skipped_lines.json`.
4. **Agency & Fare Scope**: Unified `agency.txt` (SEMOB/DFTrans) with fare tables deferred for Phase 1.

