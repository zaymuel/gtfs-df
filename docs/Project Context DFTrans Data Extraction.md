# Project Context: DF Bus Route & Stop Data Extraction (Brasília)

## 1. Objective

Extract bus route geometries (polylines) and bus stop coordinates for the Federal District (Brasília - DF) transit network for an academic project, given that Semob-DF does not provide public GTFS feeds or downloadable WFS/Shapefiles on GeoPortal.

## 2. Target Sources Discovered

### Source A: Third-Party Transit Website (`brasiliamobilidade.com.br`)

* **Architecture:** Server-side rendered HTML with vanilla JS progressive enhancement and Leaflet maps.
* **Route Geometry Storage:** Route polylines are embedded directly in the HTML on individual line pages (`/linhas/{numero}`) inside the `#mapa-trajeto` element's `data-percurso` attribute.
  * **Format:** `{"ida": [[lat, lng], ...], "volta": [[lat, lng], ...]}` (Note: `[lat, lng]` order).
  * **Limitation:** Contains route vertices (`LineString`) and marks first/last points as Origin/Destination, but does not explicitly flag intermediate bus stops.
* **Full Line Catalog:** The homepage embeds the entire catalog of bus lines in the DOM inside `#linhas-lista` as elements with the `[data-linha]` attribute (excess items are simply hidden via CSS `.hidden` and `data-extra`).
  * **Extraction snippet (Browser Console):**

    ```javascript
    // Extract all line slugs/numbers from homepage
    copy(Array.from(document.querySelectorAll('[data-linha]')).map(el => el.getAttribute('data-linha')));
    
    // Extract route coordinates on a specific line page
    JSON.parse(document.getElementById('mapa-trajeto').getAttribute('data-percurso'));
    ```

### Source B: Official DFTrans / Semob REST API

* **Base URL:** `https://www.sistemas.dftrans.df.gov.br`
* **Characteristics:** Publicly accessible JSON/GeoJSON endpoints (no API key required), but requires a valid browser `User-Agent` header in Python `requests` to avoid 403 blocks.
* **Coordinate Order:** GeoJSON endpoints return standard `[longitude, latitude]` (inverse of Leaflet).
* **Key Endpoints:**
  * **Search/List Lines:** `GET /linha/find/{termo}`
  * **Line Metadata (returns internal `sequencial` ID):** `GET /linha/numero/{numero}`
  * **Route Geometry (GeoJSON `LineString`):** `GET /percurso/linha/numero/{numero}/geo` or `GET /percurso/linha/{sequencial}/geo`
  * **Bus Stops per Line (GeoJSON):** `GET /parada/linha/{sequencial}/geo` or `GET /parada/geo/paradas/linha/{numero}`
  * **All Bus Stops in DF (Full GeoJSON):** `GET /parada/geo/paradas`
  * **Schedules:** `GET /horario/linha/numero/{numero}`
  * **Real-Time GPS (Single Line):** `GET /gps/linha/{numero}/geo/recent`
  * **Real-Time GPS (Entire Fleet):** `GET /gps/operacoes/recent`

## 3. Reference Python Boilerplate

```python
import requests
import json

BASE_URL = "[https://www.sistemas.dftrans.df.gov.br](https://www.sistemas.dftrans.df.gov.br)"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_line_data(line_number: str):
    info = requests.get(f"{BASE_URL}/linha/numero/{line_number}", headers=HEADERS).json()
    geo = requests.get(f"{BASE_URL}/percurso/linha/numero/{line_number}/geo", headers=HEADERS).json()
    stops = requests.get(f"{BASE_URL}/parada/geo/paradas/linha/{line_number}", headers=HEADERS).json()
    return {"info": info, "route_geojson": geo, "stops_geojson": stops}

```
