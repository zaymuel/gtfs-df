# 15: BRT Numbering Scheme & Subsystem Identification (Trunk 22xx/23xx vs Feeder 32xx/33xx)

**What to build:** Comprehensive support for the BRT Sul (Expresso DF) transit numbering hierarchy across `config.py`, `scripts/discover_catalog.py`, `scripts/extract.py`, and `scripts/build_gtfs.py`. Correctly distinguish between BRT Trunk lines (4-digit codes `22xx`, `23xx`, `24xx` operating on exclusive busways at 40 km/h) and BRT Feeder lines (4-digit codes `32xx`, `33xx` such as `3320` operating as terminal feeders in mixed traffic at 20 km/h), ensuring lines without dots (`.`) are fully recognized and never filtered out.

**Blocked by:** 01: Official Active Line Catalog Discovery & Catalog Compaction, 04: End-to-End GTFS Synthesis & Linear Referencing Engine

**Category:** enhancement
**Status:** completed

- [x] Document the DFTrans BRT numbering structure: Troncal BRT (`22xx`, `23xx`, `24xx`), Alimentadora BRT Gama (`32xx`), Alimentadora BRT Santa Maria (`33xx`, e.g., `3320`)
- [x] Update `config.py` with expanded BRT categorization (`BRT_TRUNK_PREFIXES`, `BRT_FEEDER_PREFIXES`)
- [x] Ensure `scripts/build_gtfs.py` accurately identifies trunk BRT services for 40 km/h corridor speed while assigning feeder BRT lines (like `3320`) appropriate conventional speed (20 km/h) and correct terminal stop snapping
- [x] Verify that no parsing or cataloging logic in `scripts/discover_catalog.py` or `scripts/extract.py` expects a dot (`.`) in line numbers
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Completed: Full BRT Sul numbering hierarchy codified in `config.py` and `scripts/build_gtfs.py`. All 56 four-digit lines without dots (troncais 21xx/22xx/23xx/24xx at 40 km/h and alimentadoras 32xx/33xx like 3320 at 20 km/h) validated in `test_compiler.py`.*

## Agent Brief

**Category:** enhancement
**Summary:** Properly categorize and process 4-digit bus lines without dots (BRT trunk vs. BRT feeder services).

**Current behavior:**
`config.py` hardcodes only 5 line numbers in `BRT_LINE_NUMBERS = {"2201", "2202", "2205", "2301", "2304"}`. There are actually 56 lines in `data/catalog/lines.json` that have 4 digits without dots, including other trunk lines (`2203`, `2206-2213`, `2302-2311`, `2401`) and BRT feeder lines (`3201-3213` feeding Terminal BRT Gama and `3300-3322` feeding Terminal BRT Santa Maria, such as `3320`).

**Desired behavior:**
1. Acknowledge and document that all 4-digit lines without dots belong to the BRT Sul operational system (Expresso DF Sul).
2. Differentiate kinematics:
   - **BRT Troncais (`22xx`, `23xx`, `24xx`):** Operate along the exclusive BRT busway (DF-040 / DF-003 / Eixo Sul / EPAR) with Padron/Articulado BRT vehicles at `SPEED_BRT_KMH = 40.0`.
   - **BRT Alimentadoras (`32xx`, `33xx`, e.g., `3320`):** Operate in local neighborhoods (Gama, Santa Maria, Santos Dumont, Alagados) feeding into the BRT integration terminals at `SPEED_CONVENTIONAL_KMH = 20.0`.
3. Ensure both types are recognized as valid DF urban services, with appropriate route branding and speed synthesis.

**Key interfaces:**
- `config.py`: `BRT_TRUNK_PREFIXES = ("22", "23", "24")`, `BRT_FEEDER_PREFIXES = ("32", "33")`
- `scripts/build_gtfs.py`: `is_brt_trunk()`, `is_brt_feeder()`
- `docs/01-dftrans-api-knowledge.md` / `docs/adr/0001-gtfs-pipeline-architecture.md`

**Acceptance criteria:**
- [x] All 56 lines without dots are preserved and correctly classified in catalog and compilation
- [x] Kinematic modeling uses 40 km/h for BRT trunk lines and 20 km/h for BRT feeder lines
- [x] `TODO.md` updated with ticket link
