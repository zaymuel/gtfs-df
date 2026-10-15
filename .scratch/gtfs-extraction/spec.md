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
│   ├── lines.json               # Full discovered line catalog from /linha/find/%
│   └── skipped_lines.json       # Audit log of lines omitted due to missing data
├── raw/
│   └── {line_number}.json       # Raw response cache per line for offline reruns
└── gtfs/
    ├── agency.txt
    ├── routes.txt
    ├── stops.txt
    ├── trips.txt
    ├── stop_times.txt
    ├── calendar.txt
    ├── shapes.txt
    └── gtfs_df.zip              # Final zipped feed ready for r5py
```

### Module Architecture
* `config.py`: Speeds (20 km/h baseline, 40 km/h BRT), 30s dwell, calendar dates (`20260101`–`20261231`), directory paths.
* `extract.py`: Scrapes line catalog via `[0..9]` digit loop, then downloads per-line payloads to `data/raw/{line}.json` with rate limiting.
* `build_gtfs.py`: Offline processor reading `data/raw/`, converting CRS, snapping stops, calculating stop times, generating GTFS CSVs, and creating `gtfs_df.zip`.

---

## 3. Backlog / TODO: Economic Disparity & Fares

* [ ] **Fare Modeling (`fare_attributes.txt` & `fare_rules.txt`)**:
  * Incorporate DFTrans `faixaTarifaria` (e.g. Circular R$ 2.70, Metropolitana 1 R$ 3.80, Metropolitana 2 R$ 5.50) into the data model to calculate generalized travel cost matrices and evaluate economic disparity in transport accessibility across administrative regions of DF.

---

## 4. Design Status: COMPLETE
All 4 rounds of the design tree have been settled and confirmed. Ready for implementation.
