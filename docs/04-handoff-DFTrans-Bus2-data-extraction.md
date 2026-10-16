# Session Handoff: DFTrans GTFS Extraction & Schedule Enhancements

## Objective for Next Session

- Compile a GTFS dataset for Brasília using the official DFTrans REST API as the primary source for all spatial and structural transit data.
- Utilize the `bus2.info` application endpoints strictly as a secondary source to extract updated schedule tables, replacing earlier deprecated data sources.

## Key Knowledge and Decisions

- **Primary Source (DFTrans API):** The official API (`sistemas.dftrans.df.gov.br`) is the absolute core of this project. It provides the most important data points: line definitions, route geometries (returned in EPSG:3857 meters, requiring WGS84 conversion), and exact bus stop coordinates.
- **Secondary Source (Bus2 / dfnoponto.com.br):** The `bus2.info` platform is relevant **only for line scheduling**. It contains more recent departure tables (e.g., finding 65 weekday departures for Line 110.2). Intermediate bus stop passing times displayed on this platform are secondary information; if they cannot be easily scraped, they will be derived algorithmically via linear referencing using the primary DFTrans coordinate data.
- **Deprecated Source (Brasília Mobilidade):** `brasiliamobilidade.com.br` was only analyzed at the project's inception due to a lack of known alternatives. It is no longer the main source. However, raw HTML analysis yielded important discoveries:
  - **ANTT vs. Semob Distinction:** The site's HTML catalog tags lines with a `data-semob` attribute. `data-semob="1"` indicates official DF urban lines, while `data-semob="0"` identifies interstate ANTT/Entorno lines (e.g., `ANTT-12502670` for Novo Gama).
  - **Embedded Geometries:** It stores pre-calculated `[lat, lng]` arrays directly in the `data-percurso` HTML attribute.
  - **Outdated Schedules:** It lists older timetable data (e.g., 54 departures for Line 110.2) compared to the active Bus2 system.
- **Bus2 Base36 Encoding:** The `bus2.info` platform uses Base36 to encode sequential database IDs in its URLs (e.g., `route=kt6a` decodes to ID `970930`).

## Referenced Artifacts

- `01-dftrans-api-knowledge.md`: DFTrans API endpoints and EPSG:3857 to WGS84 conversion logic.
- `02-adr-stop-times-estimation.md`: Linear Referencing strategy using `shapely` to derive secondary passing times.
- `03-bus2-reverse-engineering.md`: Bus2 Base36 encoding logic and report URL structures.
- `harvest_dftrans.py`: Batch download script targeting the primary DFTrans API.

## Suggested Skills and Context

- Python data engineering (`pandas`, `geopandas`, `shapely`, `requests`).
- Browser DevTools network interception (XHR/Fetch) for JSON API analysis.

## Immediate Next Steps

1. Execute the primary extraction of routes, geometries (`shapes.txt`), and bus stops (`stops.txt`) using the official DFTrans API.
2. Inspect the JSON payloads on `https://bus2.info/reports/2you/3c189` strictly to extract the updated departure schedule tables.
3. Filter out ANTT/Entorno lines from the processing pipeline using the `data-semob` logic if the GTFS scope is strictly limited to the Federal District operations.