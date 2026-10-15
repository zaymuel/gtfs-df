import os
import re
import json
import time
import math
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DFTRANS = "https://www.sistemas.dftrans.df.gov.br"
BASE_BMOB = "https://brasiliamobilidade.com.br"
OUT_DIR = "data/raw_lines"
os.makedirs(OUT_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
})

def epsg3857_to_4326(x: float, y: float) -> list[float]:
    lon = (x * 180.0) / 20037508.34
    lat = (math.atan(math.exp((y * math.pi) / 20037508.34)) * 360.0 / math.pi) - 90.0
    return [round(lat, 6), round(lon, 6)]

def get_json(url: str):
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200 and r.text.strip():
            return r.json()
    except Exception:
        pass
    return None

def fallback_bmob_geometry(slug: str):
    """Fetches WGS84 [lat, lng] directly from brasiliamobilidade HTML if DFTrans fails."""
    try:
        r = SESSION.get(f"{BASE_BMOB}/linhas/{slug}", timeout=15)
        if r.status_code == 200:
            m = re.search(r"data-percurso='([^']+)'|data-percurso=\"([^\"]+)\"", r.text)
            if m:
                raw = (m.group(1) or m.group(2)).replace("&quot;", '"')
                return json.loads(raw)
    except Exception:
        pass
    return None

def process_line(item: dict) -> str:
    numero = item["numero"].strip()
    slug = item.get("slug") or numero
    safe_name = numero.replace("/", "_")
    out_path = os.path.join(OUT_DIR, f"{safe_name}.json")

    # Skip if already downloaded (resumable)
    if os.path.exists(out_path):
        return f"SKIP: {numero}"

    # 1. Line metadata (contains directional 'sequencial' IDs)
    meta = get_json(f"{BASE_DFTRANS}/linha/numero/{numero}")
    if not meta:
        meta = get_json(f"{BASE_DFTRANS}/linha/find/{numero}")

    # 2. Route geometry (EPSG:3857 -> WGS84)
    geo_raw = get_json(f"{BASE_DFTRANS}/percurso/linha/numero/{numero}/")
    routes_wgs84 = []
    if geo_raw and "features" in geo_raw:
        for feat in geo_raw["features"]:
            coords = feat.get("geometry", {}).get("coordinates", [])
            routes_wgs84.append({
                "properties": feat.get("properties", {}),
                "coords_lat_lng": [epsg3857_to_4326(c[0], c[1]) for c in coords]
            })

    # Fallback to brasiliamobilidade if DFTrans has no shape
    bmob_shape = None
    if not routes_wgs84:
        bmob_shape = fallback_bmob_geometry(slug)

    # 3. Stops and Schedules per directional 'sequencial'
    directions = {}
    if isinstance(meta, list):
        for d in meta:
            seq = d.get("sequencial")
            sentido = d.get("sentido", str(seq))
            if seq:
                stops = get_json(f"{BASE_DFTRANS}/parada/linha/{seq}/geo")
                sched = get_json(f"{BASE_DFTRANS}/horario/linha/{seq}")
                directions[sentido] = {
                    "sequencial": seq,
                    "stops_geojson": stops,
                    "schedule": sched
                }

    payload = {
        "numero": numero,
        "slug": slug,
        "catalog_desc": item.get("descricao"),
        "metadata": meta,
        "routes_wgs84": routes_wgs84,
        "fallback_bmob_shape": bmob_shape,
        "directions": directions
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    time.sleep(0.15)  # Polite rate limit
    return f"OK: {numero}"

def main():
    with open("data/catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Deduplicate by line number
    unique_lines = {item["numero"]: item for item in catalog if item.get("numero")}.values()
    print(f"Total unique lines to harvest: {len(unique_lines)}")

    # Also grab the master DF stops file once
    if not os.path.exists("data/all_stops_df.geojson"):
        print("Downloading master bus stops GeoJSON...")
        all_stops = get_json(f"{BASE_DFTRANS}/parada/geo/paradas")
        if all_stops:
            with open("data/all_stops_df.geojson", "w", encoding="utf-8") as f:
                json.dump(all_stops, f, ensure_ascii=False)

    # Run with 4 threads (fast, but avoids IP ban)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(process_line, item) for item in unique_lines]
        for i, fut in enumerate(as_completed(futures), 1):
            if i % 25 == 0 or i == len(unique_lines):
                print(f"[{i}/{len(unique_lines)}] Last status: {fut.result()}")

if __name__ == "__main__":
    main()