# Project Glossary: DFTrans GTFS Data Extraction

Domain terms, concepts, and conventions used across this codebase.

## Domain Concepts

### DFTrans / Semob-DF
Secretaria de Transporte e Mobilidade do Distrito Federal (Semob-DF), previously DFTrans. The public transit regulatory and management agency of Brasília / DF.

### r5py
A Python library for rapid realistic transit routing and accessibility calculations, powered by Conveyal's R5 routing engine. Operates natively on OpenStreetMap (`.osm.pbf`) and standard GTFS feeds.

### sequencial
The internal integer primary key used by DFTrans API to identify a specific operating variant/direction of a bus line (e.g., line `2304` has separate `sequencial` IDs for `IDA` and `VOLTA`).

### Sentidos (Directions)
* **IDA**: Outbound trajectory (`direction_id = 0`).
* **VOLTA**: Inbound return trajectory (`direction_id = 1`).
* **CIRCULAR**: A single continuous loop route originating and terminating at the same terminal (`direction_id = 0`).

### CRS Transformation (EPSG:3857 to EPSG:4326)
DFTrans geometry endpoints return coordinates in EPSG:3857 (Web Mercator meters: `[-5341..., -1805...]`). GTFS requires standard EPSG:4326 (WGS84 decimal degrees: `[lat, lon]`).

### Synthetic Stop Times Interpolation
DFTrans provides terminal departure times (`/horario`) but no intermediate scheduled stop arrivals. Arrival and departure times at each stop are interpolated using the cumulative distance along the route shape at an average urban transit speed (20 km/h) plus a 30s dwell time per stop.
