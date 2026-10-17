# 06: Inspect dfnoponto.com.br Main Page for Active Line Numbers

**What to build:** An inspection and extraction task to analyze the homepage and main portal pages of `dfnoponto.com.br` (and `dfnoponto.semob.df.gov.br`) to verify whether they embed, link to, or query a comprehensive list or autocomplete catalog of all active DFTrans bus line numbers, and cross-reference any findings with the master catalog.

**Blocked by:** None (can start immediately)

**Category:** enhancement
**Status:** completed

- [x] Inspect the DOM, embedded scripts, and network traffic on `https://dfnoponto.com.br/` and `https://dfnoponto.semob.df.gov.br/` for full line catalogs or search autocomplete datasets
- [x] Determine whether the main portal exposes pre-rendered HTML lists, client-side arrays, or dedicated search endpoints for line enumeration
- [x] Extract any discovered line numbers and cross-reference with `data/catalog/lines.json` (and `data/bus2/routes.json`) to verify network completeness
- [x] Document the inspection outcome and update catalog discovery if new official line sources are identified

## Comments

> *Completed in `audit_dfnoponto.py` and documented in `docs/04-dfnoponto-main-page-audit.md`.*

## Agent Brief

**Category:** enhancement
**Summary:** Inspect the main landing page of dfnoponto.com.br for embedded or linked catalogs of all active line numbers.

**Current behavior:**
Active line numbers are currently discovered through the Bus2 backend reports route catalog (`https://mobilibus.com/api/routes?project_hash=3c189`) and DFTrans API endpoints (`/linha/numero/{numero}`). While subpages like `/pesquisa-por-linhas/` and `/pesquisa-geral/` were analyzed, the root landing page `https://dfnoponto.com.br` has not been systematically inspected to see if it embeds a direct, public listing, autocomplete index, or client-side JSON of all active lines.

**Desired behavior:**
Fetch and inspect the HTML, scripts, and API calls made by the main page of `dfnoponto.com.br` (and `dfnoponto.semob.df.gov.br`). If an active line listing or search index is present, extract it, normalize the line numbers, and cross-reference against `data/catalog/lines.json` to verify 100% network capture.

**Key interfaces:**
- Inspection targets: `https://dfnoponto.com.br/` and `https://dfnoponto.semob.df.gov.br/`
- Output: Documented findings and comparison against `data/catalog/lines.json`

**Acceptance criteria:**
- [x] `dfnoponto.com.br` and `dfnoponto.semob.df.gov.br` main landing pages are fetched and audited for line catalogs
- [x] Client-side autocompletion datasets, search input bindings, or REST endpoints used on the main page are checked
- [x] Any discovered line numbers are compared with `data/catalog/lines.json`
- [x] Findings and status are recorded in `docs/04-dfnoponto-main-page-audit.md`

**Out of scope:**
- Primary GTFS synthesis (Ticket 04)
- Fare modeling (Ticket 05)

