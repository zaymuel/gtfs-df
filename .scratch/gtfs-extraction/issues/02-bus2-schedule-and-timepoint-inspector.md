# 02: Bus2 (`dfnoponto`) Schedule & Timepoint API Inspector

**What to build:** An inspection and extraction utility for the official `dfnoponto.semob.df.gov.br` (`bus2.info`) secondary schedule source that captures the master `Company`/`Route`/`Trip` Base36 ID mapping, extracts up-to-date departure tables (`weekday`, `saturday`, `sunday`), and verifies whether intermediate stop passing times (`View as table`, `Stops and route`, and `pesquisa-geral`) come from a structured backend payload or client-side interpolation.

**Blocked by:** None (can start immediately)

**Category:** enhancement
**Status:** completed

- [x] Intercept and document the XHR/JSON request on `bus2.info/reports/2you/3c189` that populates the `Company`, `Route`, and `Trip` dropdowns, producing a complete lookup mapping between DFTrans `numero` (e.g., `0.110`, `110.2`) and Bus2 Base36 internal IDs (`route`, `trip`)
- [x] Inspect the `View as table` and `Stops and route` JSON responses on `bus2.info` to determine whether intermediate stop timepoints or stop-to-stop time offsets are returned by the API
- [x] Inspect the network calls on `dfnoponto.semob.df.gov.br/pesquisa-geral/` to verify whether minute-by-minute stop predictions are served by a REST endpoint or computed client-side
- [x] Provide a clean interface/function to fetch updated origin departure tables from Bus2 so the GTFS synthesis pipeline can augment or replace stale DFTrans `/horario` schedules

## Comments

> *Completed: Implemented in `bus2_client.py` and documented in `docs/03-bus2-reverse-engineering.md` with full Base36 and AES decryption.*

## Agent Brief

**Category:** enhancement
**Summary:** Reverse-engineer and extract `bus2.info` / `dfnoponto` XHR payloads for master Base36 ID mapping, updated departure schedules, and potential intermediate stop offsets.

**Current behavior:**
We established that `dfnoponto.semob.df.gov.br/pesquisa-por-linhas/` embeds `bus2.info/reports/2you/3c189`, which uses Base36-encoded sequential database IDs (`route=kt6a`, `trip=3gp36`) and holds fresher departure tables than legacy sources (e.g., 65 weekday departures for Line `110.2` vs. 54). However, we do not yet have the automated mapping from DFTrans line numbers to Bus2 Base36 IDs, nor have we confirmed if `View as table` or `pesquisa-geral` expose intermediate stop time offsets via JSON.

**Desired behavior:**
Capture the underlying XHR endpoints for `bus2.info/reports/2you/3c189` and `dfnoponto.semob.df.gov.br/pesquisa-geral/`, build the automated DFTrans-to-Bus2 route/trip ID mapping, verify whether stop-to-stop offsets exist in the JSON responses, and expose a schedule fetcher that returns normalized departure lists (`dias_uteis`, `sabado`, `domingo_feriado`) and validity metadata.

**Key interfaces:**
- `base36_decode(token: str) -> int` and `base36_encode(num: int) -> str`
- Bus2 catalog mapper: maps DFTrans `numero` and `sentido` (`IDA`/`VOLTA`/`CIRCULAR`) to Bus2 `route` and `trip` Base36 identifiers
- Schedule payload normalized output compatible with the raw line cache consumed by the GTFS compiler

**Acceptance criteria:**
- [x] Complete mapping between DFTrans line numbers and Bus2 internal `route`/`trip` IDs is extracted and saved in `data/bus2/route_map.json`
- [x] `View as table`, `Stops and route`, and `pesquisa-geral` network calls are inspected and their exact payload schemas documented
- [x] Updated departure timetables per service calendar (`Weekdays`, `Saturday`, `Sunday and holidays`) can be fetched programmatically from Bus2

**Out of scope:**
- Primary route geometry (`shapes.txt`) and stop coordinate (`stops.txt`) extraction, which remain strictly sourced from the official DFTrans REST API (`sistemas.dftrans.df.gov.br`)

