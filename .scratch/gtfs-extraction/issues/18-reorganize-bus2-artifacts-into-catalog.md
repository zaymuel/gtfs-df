# 18: Reorganize Bus2 Artifacts into Catalog and Isolate JS Bundle Scratches

**What to build:** Move production catalog files currently output to `data/bus2 drafts/` (`route_map.json`, `routes.json`, and `agencies.json`) directly into `data/catalog/` with standardized names (`bus2_route_map.json`, `bus2_routes.json`, `bus2_agencies.json`). Move the 21 Angular JavaScript bundles and probe HTML files out of the top-level `data/bus2 drafts/` into a dedicated subfolder `data/bus2 drafts/scratches/` to avoid cluttering `data/`. Update `scripts/config.py`, `scripts/discover_catalog.py`, `scripts/extract.py`, `scripts/audit_dfnoponto.py`, `README.md`, and all tests accordingly.

**Blocked by:** 01: Official Catalog Discovery & Compaction, 11: Reorganize Extraction Scripts into Subfolder

**Category:** architecture
**Status:** completed

- [x] Move existing `route_map.json` and `routes.json` from `data/bus2 drafts/` to `data/catalog/bus2_route_map.json` and `data/catalog/bus2_routes.json`
- [x] Move vendor JS bundles (`main.*.js`, chunks `*.js`), probe HTMLs, and test timetable files into `data/bus2 drafts/scratches/`
- [x] Update `scripts/config.py` paths (`BUS2_ROUTE_MAP_PATH`, `BUS2_ROUTES_PATH`) to point to `data/catalog/`
- [x] Update `scripts/discover_catalog.py`, `scripts/extract.py`, and `scripts/audit_dfnoponto.py` to reference `data/catalog/`
- [x] Update `README.md` data architecture section reflecting the clean `data/catalog/` layout
- [x] Update unit tests under `Python drafts/` and ensure all tests pass with $\ge 85\%$ coverage (88.84% achieved)
- [x] Mark item in `TODO.md` as completed

## Comments

> *All 21 JS bundles, probe HTMLs, and timetable test dumps were moved into `data/bus2 drafts/scratches/`. Real catalog artifacts (`bus2_route_map.json`, `bus2_routes.json`, `bus2_agencies.json`) were migrated to `data/catalog/`. `scripts/config.py`, operational scripts, `README.md`, and unit tests were updated, maintaining 100% test pass rate and 88.84% coverage.*
