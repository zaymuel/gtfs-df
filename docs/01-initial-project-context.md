# 01 - Project Context: Transit Data Extraction & Source Evolution

> **Project:** DF Bus Route & Stop Data Extraction (Brasília / Distrito Federal)  
> **Academic Context:** Transport Modeling Course, Graduate Program in Transport (PPGT / UnB)  
> **Goal:** Synthesize a validated, static GTFS feed (`gtfs_df.zip`) for multimodal accessibility and spatial equity analysis with `r5py`.  
> **Series Hierarchy:**  
> `01-initial-project-context.md` ➔ `02-dftrans-api-knowledge.md` ➔ `03-bus2-reverse-engineering.md` ➔ `04-dfnoponto-main-page-audit.md` ➔ `05-methodology-data-filtering.md`

---

## 1. Problem Statement & Motivation

In the Federal District (Brasília - DF, Brazil), the public transit regulatory authority (**Semob-DF**, formerly DFTrans) does **not** provide an open, standardized General Transit Feed Specification (GTFS) feed, nor does it supply downloadable up-to-date shapefiles or WFS layers on the district's GeoPortal.

To model accessibility and spatial equity using modern routing engines like `r5py` (Conveyal R5 / OpenTripPlanner backend), transport researchers must reconstruct the transit network from online operational sources. This document outlines the project context and records the **evolution and correction of discovered data sources**.

---

## 2. Evolution & Correction of Target Sources

During reverse-engineering, three distinct sources were evaluated. Their roles have been formally clarified based on officiality, data freshness, and spatial accuracy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SOURCE EVOLUTION                                 │
└─────────────────────────────────────────────────────────────────────────────┘

 [Source A: brasiliamobilidade.com.br] (DEPRECATED AS PRIMARY)
    │  • Unofficial third-party website
    │  • Contains full line list in DOM with [data-linha]
    │  • KEY VALUE RETAINED: `data-semob` attribute distinguishes
    │    DF Urban lines ("1") from interstate ANTT/Entorno lines ("0")
    │  • FLAW: Outdated schedules (e.g., 54 departures) & lacks intermediate stops
    ▼
 [Source B: Official DFTrans REST API] (PRIMARY SOURCE OF TRUTH)
    │  • sistemas.dftrans.df.gov.br (Official Semob-DF backend)
    │  • PRIMARY CORE FOR SPATIAL DATA:
    │    - Exact line numbers & directional sequential IDs (IDA, VOLTA, CIRCULAR)
    │    - Route shapes (FeatureCollection LineString in EPSG:3857)
    │    - Exact directional bus stops (/parada/linha/{seq}/geo)
    │    - Master bus stop catalog (/parada/geo/paradas)
    │    - Operator & fleet metadata (operadoras, tiposOnibus)
    │  • LIMITATION: /linha/find/ has a hard server cap (LIMIT 30)
    ▼
 [Source C: DF no Ponto / Bus2] (SECONDARY SOURCE FOR SCHEDULES)
       • dfnoponto.semob.df.gov.br / bus2.info (Official Semob-DF tracking portal)
       • PRIMARY CORE FOR TIMETABLES:
         - Fresh departure tables (e.g., 65 departures for Line 110.2)
         - Service day calendars (Weekdays, Saturdays, Sundays/Holidays)
       • Base36 auto-incrementing database keys
```

---

### Source A: Third-Party Transit Website (`brasiliamobilidade.com.br`) — *Deprecated as Primary*

* **Original Status:** Explored during project inception when official endpoints were unknown.
* **Architecture:** Server-side rendered HTML with vanilla JS and Leaflet. Route coordinates were stored on individual line pages (`/linhas/{numero}`) in the `data-percurso` attribute of `#mapa-trajeto` as `[lat, lng]` pairs.
* **Why Deprecated:**
  1. It is an unofficial commercial/third-party website.
  2. It contains route geometries but completely lacks intermediate bus stop coordinates (only marking start and end vertices).
  3. Its schedule tables are outdated compared to the active DF no Ponto service (e.g., listing 54 departures for Line 110.2 instead of 65).
* **Crucial Discovery Retained (The `data-semob` Attribute):**
  The site's line catalog embeds a metadata attribute that distinguishes administrative jurisdictions:
  * `data-semob="1"`: Official Federal District urban lines managed by Semob-DF (in-scope).
  * `data-semob="0"`: Interstate Entorno lines regulated by ANTT (e.g., `ANTT-12502670` for Novo Gama — out of scope for the DF urban accessibility study).
* **Historical Extraction Script (Browser Console):**

  ```javascript
  // Extract all lines from homepage DOM with semob classification
  const linhas = Array.from(document.querySelectorAll('[data-linha]')).map(el => {
    const fav = el.querySelector('[data-fav-numero]');
    const link = el.querySelector('a');
    return {
      numero: (fav && fav.getAttribute('data-fav-numero')) || el.getAttribute('data-linha'),
      slug: (fav && fav.getAttribute('data-fav-slug')) || null,
      url: link ? link.getAttribute('href') : null,
      descricao: el.getAttribute('data-busca'),
      semob: el.getAttribute('data-semob') // "1" = DF Urban, "0" = ANTT Interstate
    };
  });
  copy(linhas);
  ```

---

### Source B: Official DFTrans / Semob-DF REST API (`sistemas.dftrans.df.gov.br`) — *Primary Source*

* **Status:** **The authoritative backbone** for all network structure, spatial geometry, and vehicle metadata.
* **Characteristics:** Public REST endpoints managed directly by Semob-DF. Requires standard browser `User-Agent` and `Accept: application/json` headers.
* **Core Responsibilities:**
  1. **Line Definitions & Directions:** `GET /linha/numero/{numero}` returns directional branches (`IDA`, `VOLTA`, `CIRCULAR`), each identified by an internal integer `sequencial` ID.
  2. **Route Trajectories:** `GET /percurso/linha/numero/{numero}/` returns high-resolution `LineString` features.
  3. **Bus Stop Locations:** `GET /parada/linha/{sequencial}/geo` yields all authorized boarding points for that direction.
  4. **Concessionaire & Fleet Data:** Populates `operadoras` (Bacias 1 to 5) and `tiposOnibus` (e.g., *ÔNIBUS PADRON BRT*, *ARTICULADO BRT*).
* **Key Technical Caveats:**
  * **Coordinate System:** Geometry is returned in **EPSG:3857 (Web Mercator meters)** and must be reprojected to **EPSG:4326 (WGS84 degrees)**.
  * **Search Limit:** `GET /linha/find/{termo}` has a hard **`LIMIT 30`** server cap. The crawler bypasses this by iterating through the catalog (`data/lines.json`) and querying `GET /linha/numero/{numero}` directly.
* *Detailed documentation:* See [`01-dftrans-api-knowledge.md`](01-dftrans-api-knowledge.md).

---

### Source C: Official DF no Ponto & Bus2 (`dfnoponto.semob.df.gov.br` / `bus2.info`) — *Secondary Source*

* **Status:** **Authoritative source for active timetables and departure schedules**.
* **Architecture:** The official portal `dfnoponto.semob.df.gov.br/pesquisa-por-linhas/` embeds the **Bus2 Reports** application (`bus2.info/reports/2you/3c189`).
* **Core Responsibilities:**
  1. **Departure Schedules:** Up-to-date departure lists for Weekdays, Saturdays, and Sundays/Holidays.
  2. **Validity Horizons:** Metadata indicating service effective dates (e.g., `Effective from: 23/08/2025`).
* **URL Parameter Structure:**
  Uses auto-incrementing integer primary keys encoded in **Base36** (e.g., Agency `3c189` = `5600313`; Route `kt6a` = `970930`).
* *Detailed documentation:* See [`03-bus2-reverse-engineering.md`](03-bus2-reverse-engineering.md).

---

## 3. Component Allocation Matrix for GTFS Synthesis

The table below summarizes which source populates each file of the final `gtfs_df.zip`:

| GTFS Component | Primary Source | Secondary / Derived Logic | Detailed Documentation |
| :--- | :--- | :--- | :--- |
| `agency.txt` | DFTrans API | Unified SEMOB-DF entity | [`01-dftrans-api-knowledge.md`](01-dftrans-api-knowledge.md) |
| `routes.txt` | DFTrans API (`/linha/numero/`) | Filtered by `data-semob="1"` (excludes ANTT) | [`01-dftrans-api-knowledge.md`](01-dftrans-api-knowledge.md) |
| `shapes.txt` | DFTrans API (`/percurso/`) | Reprojected from EPSG:3857 to EPSG:4326 | [`01-dftrans-api-knowledge.md`](01-dftrans-api-knowledge.md) |
| `stops.txt` | DFTrans API (`/parada/linha/`) | Deduplicated against `/parada/geo/paradas` | [`01-dftrans-api-knowledge.md`](01-dftrans-api-knowledge.md) |
| `trips.txt` | DFTrans API (Directions) | Trip departures augmented from Bus2 (`dfnoponto`) | [`03-bus2-reverse-engineering.md`](03-bus2-reverse-engineering.md) |
| `stop_times.txt` | Derived Algorithmically | Linear Referencing (`shapely`) at 20 km/h (Bus) / 40 km/h (BRT) + 30s dwell | [`adr/0002-stop-times-estimation.md`](adr/0002-stop-times-estimation.md) |
| `calendar.txt` | Synthesized | Canonical service IDs (`weekday`, `saturday`, `sunday`) for 2026 | [`05-methodology-data-filtering.md`](05-methodology-data-filtering.md) |

---

## 4. Pipeline Scripts & Artifacts

* **Batch Crawler:** `extract.py` (extracts raw payloads into `data/raw/{numero}.json` with rate-limiting and local caching).
* **Master Line Catalog:** `data/lines.json` (compiled active catalog filtered for DF urban lines).
* **GTFS Compiler (Planned):** `build_gtfs.py` (reads local raw JSONs, reprojects shapes, snaps stops, interpolates passing times, and outputs `gtfs_df.zip`).
