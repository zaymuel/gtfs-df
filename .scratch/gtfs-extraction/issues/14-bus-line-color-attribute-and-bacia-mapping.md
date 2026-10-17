# 14: Clarify Bus Line "cor" Attribute & Map Concession Basin Color Schemes

**What to build:** Document the meaning and operational purpose of the `"cor"` attribute (e.g., `#bbff00`, `#449612`, `#FF8200`, `#ffd200`) present in `data/catalog/lines.json` and Bus2 feeds, map these colors to their respective Semob-DF concession operational basins (Bacias 1 a 5) and transit operators, and ensure that the offline GTFS compiler (`build_gtfs.py`) propagates these hex colors into `route_color` and `route_text_color` in `routes.txt`.

**Blocked by:** 01: Official Active Line Catalog Discovery & Catalog Compaction

**Category:** documentation
**Status:** completed

- [x] Document the operational and regulatory meaning of `"cor"`: visual identity mandated by Semob-DF for the 5 concession basins and operators (Piracicabana, Pioneira, Urbi, Marechal, BsBus)
- [x] Document the mapping between `operadora_id`, `agencyId`, basin color hex codes, and text contrast colors in `docs/`
- [x] Verify that `scripts/build_gtfs.py` assigns `route_color` and `route_text_color` matching the catalog's visual identity rather than generic static fallbacks
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Completed: Documented Semob-DF operational basin colors (Bacias 1–5) and integrated automatic `route_color` extraction with luminance-based `route_text_color` contrast calculation in `scripts/build_gtfs.py`, verified in `test_compiler.py`.*

## Agent Brief

**Category:** documentation / enhancement
**Summary:** Explain the "cor" attribute in the bus line data and ensure proper GTFS `route_color`/`route_text_color` emission.

**Current behavior:**
`data/catalog/lines.json` contains a `"cor"` field (e.g., `"#bbff00"`, `"#449612"`, `"#FF8200"`) extracted from Bus2/Mobilibus, but its operational meaning within Semob-DF regulation is undocumented, and `build_gtfs.py` currently uses static fallback colors (`"E60000"` for BRT, `"175898"` for conventional).

**Desired behavior:**
Document that `"cor"` represents the official livery and operational basin color scheme of the Distrito Federal public transport system (STPC/DF), established during the licitation of the 5 operational basins:
- **Bacia 1 (Piracicabana):** Verde (`#449612`)
- **Bacia 2 (Pioneira):** Amarelo Dourado (`#ffd200` / `#FFCC00`)
- **Bacia 3 (Urbi):** Azul (`#0072CE` / `#0055A5`)
- **Bacia 4 (Marechal):** Laranja (`#FF8200` / `#FF6600`)
- **Bacia 5 (BsBus / Expresso São José):** Verde-Limão (`#bbff00`)

Ensure `build_gtfs.py` uses the line's catalog `"cor"` to populate `route_color` and calculates high-contrast `route_text_color` (`#000000` or `#FFFFFF`).

**Key interfaces:**

- `data/catalog/lines.json`
- `scripts/build_gtfs.py`
- GTFS `routes.txt` (`route_color`, `route_text_color`)
- `docs/01-dftrans-api-knowledge.md` / `docs/03-bus2-reverse-engineering.md`

**Acceptance criteria:**

- [ ] Clear documentation of color codes by operational basin and concessionaire
- [ ] `build_gtfs.py` populates `route_color` from catalog `"cor"` with appropriate contrast `route_text_color`
- [ ] `TODO.md` updated with ticket link
