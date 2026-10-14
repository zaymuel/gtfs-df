# Feature Spec: DFTrans Data Extraction and GTFS Synthesis

**Status:** Under Active Design (Grilling Session in Progress)  
**Target Engine:** `r5py` (Multimodal accessibility and transport equity analysis)  
**Workspace:** `Dados GTFS DF` (PPGT / UnB)  

---

## 1. Objectives & Scope

1. **Extract complete transit network data** for Brasília / Distrito Federal from the official DFTrans REST API (`https://www.sistemas.dftrans.df.gov.br`).
2. **Synthesize a validated GTFS static feed** (`gtfs_df.zip`) specifically designed to satisfy `r5py` validation rules (monotonically increasing stop times, valid coordinate system, connected shapes).
3. **Persist all artifacts** in structured, reproducible folders.

---

## 2. Settled Design Decisions

### Source & Catalog
* **Endpoint**: `GET /linha/find/%25` yields all active lines and their `sequencial` identifiers.
* **Per-line Extraction**:
  * Line metadata: `GET /linha/numero/{numero}`
  * Route geometry (EPSG:3857): `GET /percurso/linha/numero/{numero}/`
  * Bus stops per direction: `GET /parada/linha/{sequencial}/geo`
  * Timetable departures: `GET /horario/linha/numero/{numero}`

### Output & r5py Requirements
* **Output**: Strictly static GTFS (`.zip` containing `agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, `shapes.txt`).
* **Coordinate Reference System**: EPSG:4326 (WGS84). Converted from EPSG:3857 using standard projection formula.
* **Stop Times**: Departure times taken from `/horario`. Intermediate arrivals/departures interpolated using cumulative distance along `shapes.txt` at ~20 km/h + 30s dwell time per stop.
* **Calendar**: 3 canonical service IDs: `weekday`, `saturday`, `sunday`.

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

---

## 3. Pending Decisions (Round 3 Queue)

* **Q1 (Directionality)**: Map `IDA` -> `0`, `VOLTA` -> `1`, `CIRCULAR` -> `0` (closed loop).
* **Q2 (Stop Snapping)**: Project stops onto route polylines to guarantee monotonic `shape_dist_traveled`.
* **Q3 (Quality Filtering)**: Filter lines with < 2 stops or missing shapes, logging them to `skipped_lines.json`.
* **Q4 (Agency & Fares)**: Unified `agency.txt` (SEMOB/DFTrans); fare rules deferred for Phase 1.

