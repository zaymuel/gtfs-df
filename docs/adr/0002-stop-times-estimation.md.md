# ADR / Spec: Stop Times Extraction & Spatial-Temporal Interpolation (`stop_times.txt`)

## 1. Context & Problem Statement
The official DFTrans REST API (`sistemas.dftrans.df.gov.br`) provides:
- Departure schedules from the origin terminal (`/horario/linha/{sequencial}`).
- Ordered or spatial bus stops per direction (`/parada/linha/{sequencial}/geo`).
- Route polyline geometry in EPSG:3857 meters (`/percurso/linha/numero/{numero}/`).

However, the API does **not** directly expose a static schedule of arrival/departure times for each intermediate bus stop (`stop_times.txt` in GTFS). Meanwhile, the front-end web app (`dfnoponto.com.br/pesquisa-geral/`) displays estimated pass-through times per stop (e.g., Line `0.110`: 16h34 at Rodoviária -> 16h35 at Biblioteca Nacional -> 16h45 at UnB CDT).

## 2. Investigation & Extraction Strategy

### Step 1: Verify Hidden XHR Endpoints on `dfnoponto.com.br/pesquisa-geral/`
Before computing synthetically, inspect the SPA network traffic when selecting a line in `dfnoponto.com.br/pesquisa-geral/`:
1. Open Chrome DevTools -> **Network** -> Filter by **Fetch/XHR**.
2. Click on a line (e.g., `0.110 - Rodoviária / UnB`)[cite: 3] and inspect responses for endpoints containing `previsao`, `estimativa`, `itinerario`, or `parada`.
3. **Check if the SPA calculates times locally:** Search the loaded `.js` bundles in DevTools (`Ctrl+Shift+F`) for terms like `velocidade`, `previsao`, `getDistance`, or `horario`.

### Step 2: Algorithmic Generation via Linear Referencing (Fallback / Standard GTFS Synthesis)
Because `percurso` coordinates are already in **EPSG:3857 (meters)**, calculating exact cumulative distances along the route polyline is straightforward and fast using `shapely`.

#### Mathematical Model
Given:
- Route polyline $L$ with total length $D_{\text{total}}$ (in meters).
- Ordered sequence of stops $S = \{s_0, s_1, \dots, s_n\}$.
- Departure time at origin terminal $t_0$ (from `/horario/linha/{sequencial}`).
- Estimated total trip duration $T_{\text{trip}}$ (or average operational speed $v_{\text{avg}}$, typically $18\text{–}25\text{ km/h}$ in urban Brasília, or derived from GPS feed `/gps/linha/{numero}/geo/recent`).

For each stop $s_i$:
1. Project $s_i$ onto polyline $L$ to obtain cumulative distance along the route:
   $$d_i = \text{project}(L, s_i)$$
2. Compute arrival time $t_i$:
   - **Method A (Constant Operational Speed $v$ in m/s):**
     $$t_i = t_0 + \frac{d_i}{v}$$
   - **Method B (Proportional Trip Duration $T_{\text{trip}}$):**
     $$t_i = t_0 + T_{\text{trip}} \cdot \left(\frac{d_i}{D_{\text{total}}}\right)$$

## 3. Reference Python Implementation (`shapely`)

```python
import requests
from datetime import datetime, timedelta
from shapely.geometry import LineString, Point

BASE_URL = "[https://www.sistemas.dftrans.df.gov.br](https://www.sistemas.dftrans.df.gov.br)"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def generate_stop_times(numero_linha: str, sequencial: int, departure_hhmm: str, avg_speed_kmh: float = 22.0):
    """
    Projects stop coordinates onto the route LineString (in EPSG:3857 meters)
    and interpolates arrival times for GTFS stop_times.txt.
    """
    # 1. Fetch route polyline (already in EPSG:3857 meters)
    r_geo = requests.get(f"{BASE_URL}/percurso/linha/{sequencial}/geo", headers=HEADERS).json()
    coords_3857 = r_geo["features"][0]["geometry"]["coordinates"]
    route_line = LineString(coords_3857)

    # 2. Fetch stops for this sequencial
    r_stops = requests.get(f"{BASE_URL}/parada/linha/{sequencial}/geo", headers=HEADERS).json()
    stop_features = r_stops.get("features", [])

    # 3. Project stops onto route line to get cumulative distance (meters)
    projected_stops = []
    for feat in stop_features:
        pt_coords = feat["geometry"]["coordinates"]
        pt = Point(pt_coords[0], pt_coords[1])
        
        # Distance along the polyline from origin (0.0) to the point closest to the stop
        dist_along_route = route_line.project(pt)
        
        props = feat.get("properties", {})
        projected_stops.append({
            "stop_id": props.get("codDftrans") or props.get("sequencial"),
            "stop_name": props.get("descricao") or props.get("sentido"),
            "dist_m": dist_along_route
        })

    # Sort stops by their physical sequence along the polyline
    projected_stops.sort(key=lambda x: x["dist_m"])

    # Normalize so the first stop is at 0 meters
    if projected_stops:
        offset = projected_stops[0]["dist_m"]
        for s in projected_stops:
            s["dist_m"] = max(0.0, s["dist_m"] - offset)

    # 4. Calculate arrival times based on average speed (or segment speed)
    # Note: EPSG:3857 scale factor at latitude -15.8° is cos(-15.8°) ≈ 0.9622
    scale_factor = 0.9622
    speed_m_per_sec = (avg_speed_kmh / 3.6)

    t0 = datetime.strptime(departure_hhmm, "%H:%M")
    stop_times_output = []

    for idx, s in enumerate(projected_stops, start=1):
        real_dist_m = s["dist_m"] * scale_factor
        travel_seconds = real_dist_m / speed_m_per_sec
        arrival_dt = t0 + timedelta(seconds=travel_seconds)

        stop_times_output.append({
            "stop_sequence": idx,
            "stop_id": s["stop_id"],
            "stop_name": s["stop_name"],
            "shape_dist_traveled_m": round(real_dist_m, 1),
            "arrival_time": arrival_dt.strftime("%H:%M:00"),
            "departure_time": arrival_dt.strftime("%H:%M:00")
        })

    return stop_times_output