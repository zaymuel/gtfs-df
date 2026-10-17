# 08: Research and Integrate Metrô-DF (Subway/Rail) into GTFS Dataset

**What to build:** An exploratory research and data synthesis task to identify, harvest, and integrate the Federal District subway network (Companhia do Metropolitano do Distrito Federal - Metrô-DF) into the unified GTFS feed (`gtfs_df.zip`), providing multimodal transit routing (`route_type = 1`) for `r5py` and regional mobility analyses.

**Blocked by:** Primary bus GTFS pipeline completion (Ticket 04)

**Category:** enhancement / backlog
**Status:** backlog

- [ ] Investigate candidate data sources for Metrô-DF stations, alignment geometries, and timetables (Bus2/Mobilibus, OpenStreetMap, Geoportal DF, and official Metrô-DF portals)
- [ ] Document the network topology for Linha Verde (Central ↔ Ceilândia) and Linha Laranja (Central ↔ Samambaia), including the shared trunk between Central and Águas Claras
- [ ] Determine timetable modeling approach: explicit synthetic trips in `trips.txt` / `stop_times.txt` based on published headways vs. `frequencies.txt`
- [ ] Implement extraction/generation script to produce Metrô-DF GTFS entities (`agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`, `shapes.txt`) with `route_type = 1`
- [ ] Merge Metrô-DF entities with the urban bus feed in `build_gtfs.py` and validate station connectivity (e.g., transfers at Rodoviária do Plano Piloto / Estação Central and Terminal Asa Sul)

## Comments

> *Created from backlog idea in `TODO.md`.*

## Agent Brief

**Category:** enhancement
**Summary:** Research and synthesize Metrô-DF (subway) data to supplement the bus network in GTFS format.

**Current behavior:**
The GTFS pipeline currently targets the road-based urban bus network (DFTrans / Semob-DF). Rail transit operated by Metrô-DF is absent, limiting multimodal journey planning in `r5py` for high-capacity corridors between Plano Piloto, Guará, Águas Claras, Taguatinga, Ceilândia, and Samambaia.

**Desired behavior:**
Include Metrô-DF as an agency in `agency.txt` (`agency_id: METRO_DF`), with two routes in `routes.txt` (`route_type = 1`):
1. **Linha Verde (Green Line):** Central ↔ Ceilândia (Estação Ceilândia Norte / Terminal Ceilândia)
2. **Linha Laranja (Orange Line):** Central ↔ Samambaia (Terminal Samambaia)

### Candidate Data Sources:
1. **Bus2 / Mobilibus API (`data/bus2/routes.json`):**
   - The master catalog already captures 2 route objects with `shortName: null` and Metrô agency associations. We should inspect if `mobilibus.com/api/timetable` or `/trip-details` contains subway stop sequences and schedules.
2. **OpenStreetMap (OSM):**
   - High-fidelity geometries for tracks (`railway=subway`) and all 27 passenger stations (`railway=station` / `public_transport=station`).
3. **Geoportal DF (SEDUR / GDF):**
   - Official geospatial layers for rail tracks and station polygons in SIRGAS 2000 (EPSG:31983 / EPSG:4674).
4. **Official Metrô-DF Website (`metro.df.gov.br`):**
   - Operating hours (Monday–Saturday 05:30–23:30, Sundays/Holidays 07:00–19:00), peak/off-peak headway intervals (e.g., 3.5 min on shared trunk, 7–10 min on branch lines).

**Key interfaces:**
- `build_gtfs.py` / `extract_metro.py`
- GTFS Output: merged into `data/gtfs/gtfs_df.zip`

**Acceptance criteria:**
- [ ] Candidate sources evaluated and best source documented in `docs/`
- [ ] 27 Metrô stations digitized into `stops.txt` with WGS84 coordinates and parent station IDs
- [ ] Rail alignments converted to `shapes.txt`
- [ ] Weekday, Saturday, and Sunday timetable schedules generated with accurate travel times (~35-45 min end-to-end)
- [ ] Verified compatible with `r5py` alongside bus routes

**Out of scope:**
- Real-time GTFS-RT subway vehicle positions
- Non-revenue maintenance yard movements

