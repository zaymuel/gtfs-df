# 16: Spatial Buffer & Linear Referencing Fallback Methodology

**What to build:** Document in detail the spatial snapping and linear referencing algorithm used in `scripts/build_gtfs.py` (§ "2. Fallback espacial: Buffer de 35 metros sobre as paradas mestres"). Clarify how the 35m buffer corridor around route polylines works, why 35 meters was chosen (road widths, bays, sidewalk offsets), how `STRtree` accelerates lookup across 5,466 global DF stops, and how `shapely.project()` guarantees monotonic stop ordering for `r5py`.

**Blocked by:** 04: End-to-End GTFS Synthesis & Linear Referencing Engine

**Category:** documentation
**Status:** completed

- [x] Document the spatial rationale for the 35-meter route buffer in `docs/` and ADRs
- [x] Explain the two-phase spatial algorithm: R-Tree indexing (`STRtree`) + Orthogonal projection (`LineString.project()`)
- [x] Clarify why this fallback exists: upstream failure of DFTrans `GET /parada/linha/{sequencial}/geo` (HTTP 404)
- [x] Detail distance-based deduplication (15m threshold) to eliminate opposing-curb or duplicate inventory markers
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Completed: Full mathematical and spatial documentation articulated for the 35m corridor buffer fallback, R-tree candidate filtering, orthogonal projection, and monotonic stop ordering.*

## Agent Brief

**Category:** documentation
**Summary:** Explain the 35m spatial buffer fallback methodology and linear referencing used to reconstruct stop sequences.

**User Question:**
*"o que seria o '2. Fallback espacial: Buffer de 35 metros sobre as paradas mestres'? pelo que entendi, é uma estratégia para associar paradas que não caem exatamente sobre as coordenadas mestres, mas que estão próximas dentro de um raio de 35 metros, e depois tenta encaixar uma dentro desse raio"*

**Explanation & Solution:**

1. **The Root Cause:** DFTrans endpoint `GET /parada/linha/{sequencial}/geo` returns HTTP 404, so directional stop sequences per line cannot be downloaded directly from DFTrans.
2. **The Available Inputs:**
   - Directional route geometry: `LineString` in `EPSG:3857` representing the bus path along the roadway.
   - Master stop catalog: `data/all_stops_df.geojson` containing all 5,466 bus stop shelters/poles in the DF.
3. **The 35m Buffer Corridor:**
   Instead of searching around individual stops, the algorithm creates a 35-meter continuous polygonal buffer envelope on either side of the bus route polyline (`line.buffer(35.0)`). 35 meters corresponds to typical arterial street widths in Brasília (including medians, multi-lane carriageways, and sidewalk bus bays).
4. **STRtree Spatial Indexing:**
   Shapely's `STRtree` queries which of the 5,466 candidate stop points fall inside this 35m buffer corridor in sub-millisecond time.
5. **Orthogonal Projection (`LineString.project`):**
   Each intercepted stop point is projected perpendicularly onto the route line to calculate its linear distance from the trip origin (`shape_dist_traveled`).
6. **Monotonic Sorting & Deduplication:**
   Stops are sorted in ascending order of projected distance along the route. Consecutive points closer than 15 meters are deduplicated, preventing direction-reversal errors in `r5py`.

**Key interfaces:**

- `scripts/build_gtfs.py`: `snap_stops_along_line()`
- `docs/01-dftrans-api-knowledge.md`
- `docs/adr/0002-stop-times-estimation.md`
