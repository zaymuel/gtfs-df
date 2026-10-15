# DFTrans API Reference & Data Extraction Spec (Verified Payloads)

## 1. Key Payload Insights

1. **Directional Sequential IDs:** Each direction (`IDA` / `VOLTA`) has its own unique internal `sequencial` ID (e.g., Line `2304` -> IDA: `19117`, VOLTA: `19129`).
2. **Rich Metadata Difference:**
   - `GET /linha/find/{termo}` returns `"operadoras": null` and `"tiposOnibus": null`.
   - `GET /linha/numero/{numero}` populates both arrays (e.g., Viação Pioneira, Ônibus Padron BRT - 37 seats).
3. **Coordinate Reference System (CRS) Warning:**
   - The endpoint `GET /percurso/linha/numero/{numero}/` returns coordinates in **EPSG:3857 (Web Mercator / meters)**, e.g., `[-5341795.614957, -1805015.442655]`.
   - These must be reprojected to **EPSG:4326 (WGS84 / `[lat, lon]` or `[lon, lat]`)** for standard GIS/Leaflet usage.
4. **Server-Side Limit on `/linha/find/{termo}` (Hard Cap: 30 records):**
   - Empirical testing confirmed that `GET /linha/find/{termo}` enforces a hard server-side limit of **30 records** per query (e.g., `find/%25` and every digit `find/0` through `find/9` all return exactly 30 items).
   - Therefore, `/linha/find/` cannot be used to scrape the entire network exhaustively.
   - **Solution**: The master catalog is provided by `data/lines.json` (961 unique active lines extracted from the complete DOM catalog). Each line number is then queried directly against `GET /linha/numero/{numero}`, which performs an exact lookup without the 30-record limit, reliably retrieving all directional metadata and `sequencial` IDs.

## 2. Reprojection & Extraction Script (Python)

```python
import math
import requests
import json

BASE_URL = "[https://www.sistemas.dftrans.df.gov.br](https://www.sistemas.dftrans.df.gov.br)"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def epsg3857_to_epsg4326(x: float, y: float) -> tuple[float, float]:
    """
    Converts Web Mercator (EPSG:3857) [x, y] in meters
    to WGS84 (EPSG:4326) [latitude, longitude] in decimal degrees.
    """
    lon = (x * 180.0) / 20037508.34
    lat = (math.atan(math.exp((y * math.pi) / 20037508.34)) * 360.0 / math.pi) - 90.0
    return round(lat, 6), round(lon, 6)

def extract_full_line(numero_linha: str) -> dict:
    # 1. Fetch metadata and sequencial IDs for each direction
    r_meta = requests.get(f"{BASE_URL}/linha/numero/{numero_linha}", headers=HEADERS)
    r_meta.raise_for_status()
    sentidos_meta = r_meta.json()

    # 2. Fetch route geometry (EPSG:3857) and convert to WGS84
    r_geo = requests.get(f"{BASE_URL}/percurso/linha/numero/{numero_linha}/", headers=HEADERS)
    raw_features = r_geo.json().get("features", []) if r_geo.status_code == 200 else []

    percursos_wgs84 = []
    for feat in raw_features:
        coords_3857 = feat.get("geometry", {}).get("coordinates", [])
        coords_4326 = [epsg3857_to_epsg4326(pt[0], pt[1]) for pt in coords_3857]
        percursos_wgs84.append({
            "properties": feat.get("properties", {}),
            "coordinates_lat_lon": coords_4326
        })

    # 3. Fetch stops per direction using 'sequencial'
    paradas_por_sentido = {}
    for item in sentidos_meta:
        seq = item.get("sequencial")
        sentido = item.get("sentido")
        r_paradas = requests.get(f"{BASE_URL}/parada/linha/{seq}/geo", headers=HEADERS)
        if r_paradas.status_code == 200:
            paradas_por_sentido[sentido] = r_paradas.json()

    return {
        "numero": numero_linha,
        "metadata": sentidos_meta,
        "routes_wgs84": percursos_wgs84,
        "stops_geojson": paradas_por_sentido
    }

if __name__ == "__main__":
    data = extract_full_line("2304")
    with open("dftrans_2304_wgs84.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

```

*(Observação: caso o endpoint `/parada/linha/{sequencial}/geo` também retorne coordenadas na casa dos milhões `[-5341..., -1805...]`, basta passar a mesma função `epsg3857_to_epsg4326` nas coordenadas das paradas ou usar `gdf.set_crs(epsg=3857).to_crs(epsg=4326)` direto no GeoPandas).*
