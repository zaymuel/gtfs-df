# Knowledge Base: DFTrans REST API & Geometry Spec

## 1. Official DFTrans API (`https://www.sistemas.dftrans.df.gov.br`)
* **Headers Required:** Standard browser `User-Agent` and `Accept: application/json` to prevent HTTP 403 blocks.
* **Verified Endpoints:**
  * `GET /linha/find/{termo}` — Search lines in bulk (e.g., `/linha/find/0`); returns `"operadoras": null` and `"tiposOnibus": null`.
  * `GET /linha/numero/{numero}` — Returns directional objects (`IDA` and `VOLTA`), each with a unique internal `sequencial` ID (e.g., Line `2304`: `19117` for IDA, `19129` for VOLTA), plus populated `operadoras` and `tiposOnibus` arrays.
  * `GET /percurso/linha/numero/{numero}/` or `GET /percurso/linha/{sequencial}/geo` — Returns `FeatureCollection` `LineString` geometries (e.g., 518 points outbound, 475 inbound for Line 2304).
  * `GET /parada/linha/{sequencial}/geo` — Bus stops for a specific direction.
  * `GET /parada/geo/paradas` — Master GeoJSON of all bus stops in the Federal District.
  * `GET /horario/linha/{sequencial}` — Origin terminal departure times.

## 2. Coordinate Reference System (CRS) Conversion
* **Percurso CRS:** Route geometries from `/percurso/linha/numero/{numero}/` are returned in **EPSG:3857 (Web Mercator meters)** (e.g., `[-5341795.614957, -1805015.442655]`).
* **Target CRS:** Convert to **EPSG:4326 (WGS84 decimal degrees)** (`[-16.00253, -47.98617]`) before exporting to GTFS `shapes.txt`.
* **Scale Factor:** At Brasília's latitude ($\approx -15.8^\circ$), $1\text{ m}$ in EPSG:3857 equals $\cos(-15.8^\circ) \approx 0.9622\text{ m}$ of true ground distance.

## 3. Fallback HTML Source (`brasiliamobilidade.com.br`)
* **Catalog:** Full line list is embedded in `#linhas-lista` inside `[data-linha]` attributes.
* **Geometries:** Individual line pages (`/linhas/{numero}`) store pre-converted WGS84 `[lat, lng]` arrays inside `#mapa-trajeto` (`data-percurso` attribute) rather than inside `<script>` tags.