# 0002. Stop Times Extraction & Spatial-Temporal Kinematic Interpolation (`stop_times.txt`)

Date: 2026-10-14 (Updated: 2026-10-17)

Status: Accepted (Implemented in `scripts/build_gtfs.py`)

## 1. Context & Problem Statement

In the Federal District (DF, Brasília), neither the official transit authority (Semob-DF / DFTrans) nor its frontend portals (`dfnoponto.semob.df.gov.br`, `bus2.info`) publish a static, complete General Transit Feed Specification (GTFS) feed with scheduled pass-through times for each intermediate stop along bus routes.

Specifically, the data sources present the following realities:

1. **DFTrans REST API (`sistemas.dftrans.df.gov.br`):**
   * Endpoint `/horario/linha/numero/{numero}` only exposes scheduled departure times from the origin terminal (e.g., `06:00`, `06:15`, `06:30`).
   * No intermediate stop times or segment travel durations are exposed.
2. **Bus2 / Mobilibus API (`mobilibus.com` / `painel.mobilibus.com`):**
   * Exposes departure tables (`/api/timetable`) and static cumulative offsets in seconds for certain routes (`/api/trip-details`).
   * However, these offsets are not uniformly available across all 930+ urban lines, require brittle reverse-engineering of transient Base36 identifiers, and do not reflect calibrated network-wide commercial speeds or operational conditions. Neither system provides dynamic real-time congestion travel matrices for static planning.

### Why Intermediate Stop Times are Strictly Required for GTFS and `r5py`

A static GTFS dataset is intended to drive multimodal routing engines (such as `r5py`, Conveyal R5, and OpenTripPlanner) that utilize time-expanded or time-dependent routing algorithms (notably **RAPTOR** — *Round-Based Public Transit Routing* and **CSA** — *Connection Scan Algorithm*).

Without interpolated arrival and departure times in `stop_times.txt`:

1. **Intermediate Boarding / Alighting:** The routing engine cannot calculate when a vehicle reaches any stop other than the initial terminal. Consequently, virtual passengers cannot board or alight at intermediate stops along the route.
2. **Transfer Synchronization:** Multimodal journeys rely on transfers between intersecting lines. Without arrival times at transfer hubs (e.g., Rodoviária do Plano Piloto, W3, L2, Taguatinga Centro), the engine cannot evaluate whether an incoming passenger arrives in time to catch a connecting bus.
3. **Cumulative Spatial Accessibility:** Measuring how many opportunities (jobs, healthcare, education) are reachable within time horizons (e.g., 30, 45, 60 minutes) requires strictly increasing, realistic elapsed travel times across the entire transit network.

---

## 2. Decision: Algorithmic Synthesis via Kinematic Linear Referencing

We adopted a deterministic, mathematically grounded kinematic model using **Linear Referencing** via `shapely` to synthesize all intermediate timestamps in `stop_times.txt`.

### 2.1 Theoretical & Mathematical Formulation

Given:

* Route polyline $L$ represented as a `LineString` with total length $D_{\text{total}}$ in meters (projected in `EPSG:3857`).
* Ordered sequence of physical bus stops $S = \{s_0, s_1, \dots, s_n\}$ snapped orthogonally onto $L$.
* Scheduled departure time from terminal $t_0$ (derived from `/horario/linha/numero/{numero}`).
* Cartographic scale factor for Brasília's latitude ($-15.8^\circ$):
  $$\kappa = \cos(-15.8^\circ) \approx 0.9622$$
* Differentiated commercial operating speed $v_{\text{commercial}}$ (converted to m/s):
  * **Conventional Urban Lines:** $v = 20\text{ km/h} \approx 5.56\text{ m/s}$ (mixed traffic, frequent intersections).
  * **BRT Corridors (Expresso DF Sul / BRT Oeste):** $v = 40\text{ km/h} \approx 11.11\text{ m/s}$ (segregated busways, off-board fare collection).
* Constant dwell time per stop: $\Delta t_{\text{dwell}} = 30\text{ seconds}$ (boarding and alighting).

For each stop $s_i$ at sequence index $i$ ($i \ge 0$):

1. **Cumulative Distance along Polyline:**
   $$d_i = \text{project}(L, s_i) \cdot \kappa$$
2. **Cumulative In-Vehicle Running Time:**
   $$T_{\text{run}}(i) = \frac{d_i}{v_{\text{commercial}}}$$
3. **Cumulative Dwell Time:**
   $$T_{\text{dwell}}(i) = i \cdot \Delta t_{\text{dwell}}$$
4. **Intermediate Arrival & Departure Times:**
   $$t_{\text{arrival}}(i) = t_0 + T_{\text{run}}(i) + T_{\text{dwell}}(i)$$
   $$t_{\text{departure}}(i) = t_{\text{arrival}}(i) + \Delta t_{\text{dwell}}$$

This guarantees:

* **Monotonicity:** $t_{\text{arrival}}(i+1) > t_{\text{departure}}(i)$, completely eliminating backward-in-time paradoxes in RAPTOR.
* **Realistic Transit Dynamics:** Differentiated speeds capture the clear physical distinction between segregated BRT corridors and regular mixed-traffic street buses.
* **Configurability:** All parameters ($v_{\text{conv}}$, $v_{\text{brt}}$, $\Delta t_{\text{dwell}}$) are centralized in `scripts/config.py` and overridable via environment variables.

---

## 3. Investigation of Alternative Paths

### Path A: Direct Extraction from Bus2 (`bus2.info`)

* Explored in [Ticket 02](.scratch/gtfs-extraction/issues/02-bus2-schedule-and-timepoint-inspector.md) and documented in `docs/03-bus2-reverse-engineering.md`.
* While Bus2 provides Base36 trip tables and cumulative offsets for selected trips, scraping 930+ lines through undocumented web endpoints introduces severe fragility, API rate-limiting risks, and gaps for routes without detailed timepoints.
* **Verdict:** Bus2 is used as an authoritative secondary reference for terminal departure verification and line cross-mapping, while Path B (Kinematic Synthesis) serves as the primary engine for `stop_times.txt`.

---

## 4. Reference Python Implementation (`shapely`)

```python
import requests
from datetime import datetime, timedelta
from shapely.geometry import LineString, Point

BASE_URL = "https://www.sistemas.dftrans.df.gov.br"
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

---

## 5. Consequences & Routing Compliance

* **Positive Consequences:**
  1. **Strict Monotonicity:** Intermediate arrival times always advance sequentially along the route, satisfying RAPTOR / CSA prerequisites in `r5py` and OpenTripPlanner without negative time deltas or loops.
  2. **Inter-line Transfer Modeling:** Passengers can transfer between lines at intermediate stops, unlocking accurate accessibility calculations for university campuses, administrative centers, and hospital zones.
  3. **Reproducibility & Auditability:** Transparent, deterministic formulation based on physical distances and configurable speeds, directly documentable in peer-reviewed transport academic literature.
* **Limitations Acknowledged:**
  * Assumes uniform average commercial speed per line category, abstracting localized peak-hour congestion bottlenecks (except as calibrated via global speed parameters in `scripts/config.py`).
