# ADR / Spec: Stop Times Extraction & Spatial-Temporal Interpolation (`stop_times.txt`)

## 1. Context & Problem Statement (Updated)

While `sistemas.dftrans.df.gov.br` only exposes origin terminal departure times (`/horario/linha/{sequencial}`), `dfnoponto.com.br` exposes two distinct front-end modules:

1. **`/pesquisa-geral/`:** Displays estimated pass-through times per intermediate stop (e.g., Line `0.110`: `16h 34` at Terminal Rodoviário -> `16h 35` at Biblioteca Nacional -> `16h 45` at UnB CDT -> `16h 49` at UNB Área 1).
2. **`/pesquisa-por-linhas/`:** Embeds a third-party schedule and route viewer powered by **Bus2** (`bus2.info/reports/2you/3c189`), which provides departure tables (`View as departures` / `View as table`), effective dates (`Effective from: 23/08/2025`), and a `Stops and route` view.

## 2. Investigation & Extraction Strategy (Updated)

### Path A: Direct Extraction from Bus2 (`bus2.info`) & `pesquisa-geral` APIs

1. Inspect XHR traffic on `https://bus2.info/reports/2you/3c189` when toggling **Schedules -> View as table** and **Stops and route**.
2. Inspect XHR traffic on `https://dfnoponto.com.br/pesquisa-geral/` when selecting a line and direction to capture the JSON payload that populates the `PREVISÃO` / `PONTO DE PARADA` sidebar.
3. If the backend returns pre-calculated stop offsets (or segment travel times), map them directly to GTFS `stop_times.txt`.

### Path B: Algorithmic Generation via Linear Referencing (Fallback)

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
```
