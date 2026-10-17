# Feature Spec: DFTrans Data Extraction and GTFS Synthesis

**Status:** Design Complete (Rounds 1–4 Settled) — Ready for Implementation  
**Target Engine:** `r5py` (Multimodal accessibility and transport equity analysis)  
**Workspace:** `Dados GTFS DF` (PPGT / UnB)  

---

## 1. Objectives & Scope

1. **Extract complete transit network data** for Brasília / Distrito Federal from the official DFTrans REST API (`https://www.sistemas.dftrans.df.gov.br`).
2. **Synthesize a validated GTFS static feed** (`gtfs_df.zip`) specifically designed to satisfy `r5py` validation rules (monotonically increasing stop times, valid coordinate system, snapped connected shapes).
3. **Persist all artifacts** in structured, reproducible folders.
4. **Document methodology** for academic publication on accessibility and spatial equity.

---

## 2. Settled Design Decisions

### Source & Catalog
* **Dynamic Catalog Discovery**: The crawler (`extract.py`) dynamically queries and parses the live DOM of `https://brasiliamobilidade.com.br` on each run, capturing all current `[data-linha]` elements to generate a real-time `data/catalog/lines.json` (merged with any user-supplied new line overrides). Usually done just one time (if `data/catalog/lines.json` is absent).
* **Per-line Extraction**:
  * Line metadata: `GET /linha/numero/{numero}`
  * Route geometry (EPSG:3857): `GET /percurso/linha/numero/{numero}/`
  * Bus stops per direction: `GET /parada/linha/{sequencial}/geo`
  * Timetable departures: `GET /horario/linha/numero/{numero}`

### Output & r5py Requirements
* **Output**: Strictly static GTFS (`.zip` containing `agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, `shapes.txt`).
* **Coordinate Reference System**: EPSG:4326 (WGS84). Converted from EPSG:3857.
* **Stop Times & Speed Separation**:
  * **Conventional**: Mean speed of 20 km/h, 30s dwell per stop.
  * **BRT (Expresso DF / Troncal BRT)**: Mean speed of 40 km/h (running up to 60 km/h on dedicated corridors), 30s dwell per stop.
* **Calendar**: 3 canonical service IDs: `weekday`, `saturday`, `sunday`, active from `20260101` to `20261231` (replicated for every week of the year).
* **Directionality**: `IDA` -> `0`, `VOLTA` -> `1`, `CIRCULAR` -> `0` (closed loop).
* **Linear Referencing**: Stops projected onto the nearest polyline segment to calculate `shape_dist_traveled` and enforce forward-moving stop sequencing.

### Quality Filtering & Auditability
* Strict validation gate: Lines lacking valid geometry or having fewer than 2 stops are excluded and logged to `data/catalog/skipped_lines.json`.
* Academic methodology documented in `docs/methodology_data_filtering.md`.

### Storage Architecture
```text
data/
├── catalog/
│   ├── lines.json               # Full discovered line catalog from /linha/find/{0..9}
│   ├── bus2_routes.json         # Master Bus2/Mobilibus routes catalog (1,048 routes)
│   ├── bus2_route_map.json      # Mapping DFTrans line number -> Bus2 Base36 route IDs
│   ├── bus2_agencies.json       # Bus2 concessionaires / agencies
│   ├── skipped_lines.json       # Audit log of lines omitted due to missing data
│   └── out_of_bounds_stops.json # Audit log of stops outside DF bounding box
├── raw/
│   └── {line_number}.json       # Raw response cache per line for offline reruns
├── bus2 drafts/
│   └── {bundle}.js, {probe}.json # Raw reverse-engineering captures from Bus2
└── gtfs/
    ├── agency.txt
    ├── routes.txt
    ├── stops.txt
    ├── trips.txt
    ├── stop_times.txt
    ├── calendar.txt
    ├── shapes.txt
    ├── fare_attributes.txt      # Fare tiers (R$ 2.70, R$ 3.80, R$ 5.50)
    ├── fare_rules.txt           # Route-to-fare tier associations
    └── gtfs_df.zip              # Final zipped feed ready for r5py

scripts/
├── config.py                    # Constants, speeds, dwell times, and paths
├── build_gtfs.py                # GTFS static compiler and linear referencing engine
├── extract.py                   # Multi-threaded resilient harvester with Bus2 fallback
├── discover_catalog.py          # Official line catalog discovery
├── audit_dfnoponto.py           # Landing page crawler and completeness audit
├── bus2_client.py               # Mobilibus API client with public key deciphering
└── http_client.py               # Resilient HTTP session pool with backoff

tests/
├── run_tests.py                 # Offline test runner and coverage orchestrator
├── test_compiler.py             # Unit tests for GTFS compiler & linear referencing
├── test_clients.py              # Unit tests for HTTP and Bus2 API clients
├── test_catalog.py              # Unit tests for catalog discovery and BRT validation
└── test_audit_and_extract.py    # Unit tests for audit logic and extractor pipelines

Python drafts/                   # Exploratory probe scripts, reverse-engineering notes
```

### Module Architecture
* `scripts/config.py`: Speeds (20 km/h baseline, 40 km/h BRT, configurable via env vars), 30s dwell, calendar dates (`20260101`–`20261231`), directory paths.
* `scripts/extract.py`: Scrapes line catalog via `[0..9]` digit loop, then downloads per-line payloads to `data/raw/{line}.json` with rate limiting, thread safety, and Bus2 fallback.
* `scripts/build_gtfs.py`: Offline processor reading `data/raw/`, converting CRS (EPSG:3857 -> EPSG:4326), snapping stops, calculating stop times, generating GTFS CSVs, modeling fares, and packaging `data/gtfs/gtfs_df.zip`.
* `tests/run_tests.py`: Offline pytest suite maintaining $>88\%$ coverage over `scripts/`.

---

## 3. Economic Disparity & Fares

* [x] **Fare Modeling (`fare_attributes.txt` & `fare_rules.txt`)**:
  * Incorporates DFTrans `faixaTarifaria` (e.g. Circular R$ 2.70, Metropolitana 1 R$ 3.80, Metropolitana 2 R$ 5.50) into the data model to calculate generalized travel cost matrices and evaluate economic disparity in transport accessibility across administrative regions of DF. Emitted directly in `build_gtfs.py` and packaged into `gtfs_df.zip`.

---

## 4. Design Status: COMPLETE
All 4 rounds of the design tree have been settled and confirmed. Ready for implementation.
