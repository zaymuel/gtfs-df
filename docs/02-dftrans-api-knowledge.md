# Knowledge Base: Official DFTrans REST API & Data Extraction Spec

> **Status:** Authoritative Spatial Reference  
> **Primary System:** DFTrans / Semob-DF REST API (`https://www.sistemas.dftrans.df.gov.br`)  
> **Role:** Primary Source of Truth for Network Topology, Geometries, Stops, and Line Definitions  

---

## 1. Architectural Role & Source Hierarchy

As established in [`01-initial-project-context.md`](01-initial-project-context.md), transit network data extraction follows a strict two-tier source hierarchy:

```
                      ┌────────────────────────────────────────┐
                      │          Source Hierarchy              │
                      └──────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │      PRIMARY SOURCE       │                   │     SECONDARY SOURCE      │
   │        DFTrans API        │                   │    Bus2 (dfnoponto)       │
   │ (sistemas.dftrans.df.gov) │                   │       (bus2.info)         │
   ├───────────────────────────┤                   ├───────────────────────────┤
   │ • Line definitions        │                   │ • Recent departure tables │
   │ • Directional variants    │                   │   (e.g., 65 trips on      │
   │ • Route shapes (3857)     │                   │   Line 110.2 vs. 54)      │
   │ • Exact stop coordinates  │                   │ • Calendar validity tags  │
   │ • Vehicle / operator meta │                   │                           │
   └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                 │                                               │
                 │   ┌───────────────────────────────────────┐   │
                 └──►│       GTFS Feed Synthesis Engine      │◄──┘
                     │  • Linear Referencing for stop_times  │
                     │  • EPSG:3857 -> EPSG:4326 conversion  │
                     │  • ANTT/Entorno filtering (semob="1") │
                     └───────────────────┬───────────────────┘
                                         ▼
                               ┌───────────────────┐
                               │    gtfs_df.zip    │
                               │   (for r5py)      │
                               └───────────────────┘
```

1. **Primary Source (Official DFTrans API):**
   * The official backend REST API (`https://www.sistemas.dftrans.df.gov.br`) is the core of this project.
   * Authoritative source for all **spatial and structural transit data**: line numbers, directional sequential IDs (`IDA`, `VOLTA`, `CIRCULAR`), full route geometries (`shapes.txt`), bus stop coordinates (`stops.txt`), and concessionaire/vehicle metadata (`operadoras`, `tiposOnibus`).
2. **Secondary Source (Bus2 / DF no Ponto):**
   * The `bus2.info` platform (`https://dfnoponto.semob.df.gov.br/pesquisa-por-linhas/`) is used **strictly for line scheduling**.
   * It provides more recent departure tables (e.g., actual 65 weekday departures for Line 110.2 compared to older records in legacy APIs).
   * Intermediate stop passing times displayed on Bus2 are secondary information; if not cleanly accessible via XHR, they are computed algorithmically via Linear Referencing (`shapely`) along DFTrans route polylines (see [`adr/0002-stop-times-estimation.md`](adr/0002-stop-times-estimation.md)).
3. **Deprecated / Reference Source (Brasília Mobilidade):**
   * `brasiliamobilidade.com.br` was utilized during project inception but is deprecated as a primary data source due to outdated schedules and lack of intermediate bus stops.
   * **Crucial Discovery Retained:** Its HTML catalog provides the **ANTT vs. Semob Distinction**:
     * `data-semob="1"`: Official Federal District urban lines (in-scope for DF GTFS).
     * `data-semob="0"`: Interstate ANTT / Entorno lines (e.g., `ANTT-12502670` for Novo Gama — excluded from the DF urban model).

---

## 2. API Overview & Authentication

* **Base URL:** `https://www.sistemas.dftrans.df.gov.br`
* **Authentication:** None required (public government API).
* **Mandatory Request Headers:**
  Standard browser headers are required to prevent HTTP 403 Forbidden blocks:

  ```python
  HEADERS = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      "Accept": "application/json"
  }
  ```

---

## 3. Verified Endpoints & Payload Behavior

### 3.1 Line Search & Discovery: `GET /linha/find/{termo}`

* **Purpose:** Substring search on line numbers or descriptions.
* **Payload Structure:** Returns an array of basic line objects:

  ```json
  [
    {
      "sequencial": 127,
      "numero": "0.761",
      "descricao": "Paranoá / Rodoviária do Plano Piloto (Ponte JK)",
      "sentido": "IDA",
      "faixaTarifaria": { "sequencial": 3, "descricao": "METROPOLITANA 1", "tarifa": 3.80 },
      "ativa": true,
      "bacia": { "sequencial": 2, "descricao": "Sudeste" },
      "tipoLinha": "R",
      "operadoras": null,
      "tiposOnibus": null
    }
  ]
  ```

* **Critical Limitation (Hard Cap: 30 records):**
  Empirical testing confirmed that the server enforces `LIMIT 30` on search queries. Querying wildcards (`find/%25`) or single digits (`find/0` through `find/9`) returns at most 30 records per query.
* **Resolution:** Network discovery cannot rely solely on `/linha/find/`. It uses the catalog index (`data/lines.json`), filtered by `data-semob="1"`, and queries each line individually via `GET /linha/numero/{numero}`.

### 3.2 Exact Line Metadata: `GET /linha/numero/{numero}`

* **Purpose:** Un-capped exact lookup for a specific line number (e.g., `GET /linha/numero/2304`).
* **Behavior:**
  * Returns an array of directional objects (`IDA`, `VOLTA`, or `CIRCULAR`).
  * **Directional Sequential IDs:** Each direction carries a unique internal integer `sequencial` ID (e.g., Line `2304` -> IDA: `19117`, VOLTA: `19129`).
  * **Rich Metadata:** Unlike the search endpoint, this endpoint fully populates:
    * `operadoras`: Concessionaire details (e.g., Viação Pioneira, Piracicabana, Urbi, Marechal, São José).
    * `tiposOnibus`: Assigned fleet types (e.g., *ÔNIBUS PADRON BRT - 37 assentos*, *ÔNIBUS ARTICULADO BRT*).
    * `faixaTarifaria`: Fare category and value in BRL (e.g., R$ 3.80, R$ 5.50).

### 3.3 Route Geometries: `GET /percurso/linha/numero/{numero}/` or `GET /percurso/linha/{sequencial}/geo`

* **Purpose:** Route alignment polylines.
* **Payload Format:** GeoJSON `FeatureCollection` with `LineString` geometries.
* **Coordinate System Warning:** Coordinates are encoded in **EPSG:3857 (Web Mercator meters)** (e.g., `[-5341795.614957, -1805015.442655]`). Must be reprojected to EPSG:4326 before GTFS compilation.

### 3.4 Directional Bus Stops: `GET /parada/linha/{sequencial}/geo`

* **Purpose:** Bus stop locations assigned to a specific directional variant.
* **Payload Format:** GeoJSON `FeatureCollection` of points.
* **Sequencing Note:** Stop positions must be linearly snapped onto the route `LineString` to calculate monotonic `shape_dist_traveled` and eliminate sequencing ambiguities.

### 3.5 Master Bus Stop Inventory: `GET /parada/geo/paradas`

* **Purpose:** Complete spatial catalog of all authorized bus stops in the Federal District (~5,466 features).
* **Properties:** Includes `sequencial`, `codDftrans`, `sentido` (*BAIRRO-CENTRO*, *CENTRO-BAIRRO*). Useful for global stop deduplication in `stops.txt`.

### 3.6 Schedules: `GET /horario/linha/numero/{numero}` or `GET /horario/linha/{sequencial}`

* **Purpose:** Official departure timetables from the origin terminal.
* **Categorization:** Partidas split by operating profile: `DIAS ÚTEIS`, `SÁBADO`, `DOMINGO/FERIADO`.
* **Augmentation:** Compare and augment with Bus2 (`dfnoponto`) departure tables when available, as Bus2 reflects the most up-to-date active scheduling adjustments.

---

## 4. Coordinate Reference System (CRS) Transformation

The route geometries returned by `/percurso/` are in **EPSG:3857 (Web Mercator in meters)**. They must be reprojected to **EPSG:4326 (WGS84 decimal degrees: `[latitude, longitude]`)** for GTFS `shapes.txt` and `stops.txt`.

### 4.1 Mathematical Conversion Formula

For a point $(x, y)$ in EPSG:3857:
$$\text{lon} = \frac{x \times 180.0}{20037508.34}$$
$$\text{lat} = \left(\arctan\left(\exp\left(\frac{y \times \pi}{20037508.34}\right)\right) \times \frac{360.0}{\pi}\right) - 90.0$$

### 4.2 Scale Factor & Metric Distortion at Brasília Latitude

Because Web Mercator projection stretches distances away from the equator:

* Brasília's latitude is $\phi \approx -15.8^\circ$.
* Ground distance scale factor: $k = \cos(\phi) \approx \cos(-15.8^\circ) \approx 0.9622$.
* Every $1\text{ m}$ measured in EPSG:3857 coordinates corresponds to $\approx 0.962\text{ m}$ of true ground distance. Linear referencing calculations for stop times interpolation should account for this when converting shape distance to travel times.

---

## 5. Reference Python Extraction Implementation

```python
"""
dftrans_client.py - Reference extraction and reprojection logic for DFTrans REST API.
"""

import math
import json
import requests
from typing import Dict, Any, List, Tuple

BASE_URL = "https://www.sistemas.dftrans.df.gov.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json"
}

def epsg3857_to_epsg4326(x: float, y: float) -> Tuple[float, float]:
    """
    Converts Web Mercator (EPSG:3857) [x, y] in meters to
    WGS84 (EPSG:4326) [latitude, longitude] in decimal degrees.
    """
    lon = (x * 180.0) / 20037508.34
    lat = (math.atan(math.exp((y * math.pi) / 20037508.34)) * 360.0 / math.pi) - 90.0
    return round(lat, 6), round(lon, 6)

def extract_full_line(numero_linha: str, session: requests.Session = None) -> Dict[str, Any]:
    """
    Performs complete extraction for a single bus line:
    1. Line metadata and directional sequential IDs
    2. Route geometries with EPSG:3857 -> EPSG:4326 conversion
    3. Directional bus stops
    4. Official departure schedules
    """
    s = session or requests.Session()

    # 1. Fetch metadata and directional variants
    r_meta = s.get(f"{BASE_URL}/linha/numero/{numero_linha}", headers=HEADERS, timeout=15)
    r_meta.raise_for_status()
    sentidos_meta = r_meta.json()

    # 2. Fetch route geometries and reproject to WGS84
    r_geo = s.get(f"{BASE_URL}/percurso/linha/numero/{numero_linha}/", headers=HEADERS, timeout=15)
    raw_features = r_geo.json().get("features", []) if r_geo.status_code == 200 else []

    routes_wgs84 = []
    for feat in raw_features:
        coords_3857 = feat.get("geometry", {}).get("coordinates", [])
        coords_4326 = [epsg3857_to_epsg4326(pt[0], pt[1]) for pt in coords_3857]
        routes_wgs84.append({
            "properties": feat.get("properties", {}),
            "coordinates_lat_lon": coords_4326  # [ [lat, lon], ... ]
        })

    # 3. Fetch stops per direction using 'sequencial'
    paradas_por_sentido = {}
    for item in sentidos_meta:
        seq = item.get("sequencial")
        sentido = item.get("sentido", "UNICO")
        if seq:
            r_paradas = s.get(f"{BASE_URL}/parada/linha/{seq}/geo", headers=HEADERS, timeout=15)
            if r_paradas.status_code == 200:
                paradas_por_sentido[sentido] = r_paradas.json()

    # 4. Fetch schedule departures
    r_horarios = s.get(f"{BASE_URL}/horario/linha/numero/{numero_linha}", headers=HEADERS, timeout=15)
    horarios = r_horarios.json() if r_horarios.status_code == 200 else []

    return {
        "numero": numero_linha,
        "metadata": sentidos_meta,
        "routes_wgs84": routes_wgs84,
        "stops_geojson": paradas_por_sentido,
        "schedules": horarios
    }

if __name__ == "__main__":
    line_data = extract_full_line("2304")
    print(f"Extracted Line {line_data['numero']}:")
    print(f"  Directions: {[s['sentido'] for s in line_data['metadata']]}")
    print(f"  Reprojected Shapes: {len(line_data['routes_wgs84'])}")
    print(f"  Stops per Direction: {list(line_data['stops_geojson'].keys())}")
```

---

## 6. Synthesis Pipeline Integration & Cross-References

| Pipeline Component | Data Source | Document Reference |
| :--- | :--- | :--- |
| **Network & Lines** (`routes.txt`) | DFTrans API `/linha/numero/{numero}` filtered by `data-semob="1"` | This document (`01-dftrans-api-knowledge.md`) |
| **Geometries** (`shapes.txt`) | DFTrans API `/percurso/` reprojected to EPSG:4326 | Section 4 & Section 5 |
| **Stop Locations** (`stops.txt`) | DFTrans API `/parada/linha/{seq}/geo` | Section 3.4 |
| **Stop Times Estimation** (`stop_times.txt`) | Derived via Linear Referencing (`shapely`) at 20 km/h (conventional) or 40 km/h (BRT) | [`adr/0002-stop-times-estimation.md`](adr/0002-stop-times-estimation.md) |
| **Updated Schedules** (`trips.txt`) | Secondary extraction from Bus2 / DF no Ponto (`bus2.info`) | [`03-bus2-reverse-engineering.md`](03-bus2-reverse-engineering.md) |
| **Quality Gate & Filtering** | Exclude lines lacking geometry or having < 2 stops (`skipped_lines.json`) | [`05-methodology-data-filtering.md`](05-methodology-data-filtering.md) |
