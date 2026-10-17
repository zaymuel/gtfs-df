# 12: Methodological Nuance on Line Deletions ("More Lines ≠ Better Base")

**What to build:** Refine the methodological documentation across `docs/04-dfnoponto-main-page-audit.md` and `docs/05-methodology-data-filtering.md` to articulate that `data/catalog/lines.json` serves as a master candidate baseline, but because transit networks evolve dynamically and routes are restructured or deprecated by Semob-DF, raw cardinality ("more lines") does not guarantee higher data quality. Document how the pipeline systematically validates line viability through active departure schedules and geometric traces.

**Blocked by:** 06: Inspect dfnoponto.com.br Main Page for Active Lines

**Category:** documentation
**Status:** completed

- [x] Update `docs/04-dfnoponto-main-page-audit.md` to clarify the master baseline role of `data/catalog/lines.json` and the possibility of historical/deleted lines
- [x] Detail the "More Lines ≠ Better Base" paradox in `docs/05-methodology-data-filtering.md`
- [x] Explain how quality gates (`data/catalog/skipped_lines.json`) filter unoperated candidate lines (empty schedules or missing geometries) to prevent artificial connectivity inflation in `r5py`
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Completed: Methodological nuance on line deletions and 'More Lines ≠ Better Base' paradox fully articulated in `docs/04-dfnoponto-main-page-audit.md` §3 and `docs/05-methodology-data-filtering.md` §3.1, with downstream operational filtering logged to `data/catalog/skipped_lines.json`.*

## Agent Brief

**Category:** documentation
**Summary:** Clarify that a higher line count in the master catalog may include deprecated services and document operational filtering criteria.

**Current behavior:**
`docs/04-dfnoponto-main-page-audit.md` established `data/catalog/lines.json` (933 lines) as having 100% coverage compared to Brasília Mobilidade's 928 DF lines, noting 5 extra lines. However, transit routes frequently get deleted or restructured in the DFTrans system, meaning some catalog entries could be legacy or discontinued lines.

**Desired behavior:**
Document transparently that higher catalog cardinality is not inherently superior ("more ≠ better"). The master catalog acts as a set of candidate services; the downstream synthesis pipeline validates active operation by requiring non-empty departure schedules (`/horario/`) and valid geometries (`/percurso/`), routing dormant entries to `skipped_lines.json`.

**Key interfaces:**
- `docs/04-dfnoponto-main-page-audit.md`
- `docs/05-methodology-data-filtering.md`
- `data/catalog/skipped_lines.json`

**Acceptance criteria:**
- [x] Methodological nuance explicitly articulated in both audit and filtering documentation
- [x] Academic context provided for `r5py` accessibility modeling (avoiding ghost transit connectivity)
- [x] `TODO.md` updated with ticket link
