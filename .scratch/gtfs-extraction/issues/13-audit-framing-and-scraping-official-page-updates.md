# 13: Audit Reframing: Scraping Official Portals for Dynamic Line Updates

**What to build:** Refine the core research framing of `docs/04-dfnoponto-main-page-audit.md` from a static homepage landing DOM audit to addressing the primary engineering and operational question: *Can we reliably and systematically scrape the official Semob-DF / DF no Ponto portals to capture all bus lines whenever they are updated?* Document the concrete scraping architecture, change detection mechanisms, update frequencies, and pipeline triggers for continuous network synchronization.

**Blocked by:** 06: Inspect dfnoponto.com.br Main Page for Active Lines, 12: Methodological Nuance on Line Deletions ("More Lines ≠ Better Base")

**Category:** documentation
**Status:** completed

- [x] Reframe §1 of `docs/04-dfnoponto-main-page-audit.md` to establish that checking the landing page is only a preliminary sanity check, while the core operational objective is scraping official line updates
- [x] Detail the exact automated scraping path for updated lines using official DFTrans endpoints and the Bus2 synchronization API (`https://mobilibus.com/api/routes?project_hash=3c189`)
- [x] Document change detection strategies (comparing live route hashes against local catalog to trigger delta extractions)
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Completed: Section 1 reframed with preliminary vs. principal questions, and Section 5 added with full operational delta-scraping architecture, change detection protocol, and GTFS rebuild pipeline in `docs/04-dfnoponto-main-page-audit.md`.*

## Agent Brief

**Category:** documentation
**Summary:** Shift the audit documentation focus from a preliminary landing page inspection to the primary operational capability of scraping line updates from official sources.

**Current behavior:**
`docs/04-dfnoponto-main-page-audit.md` opens with: *"This audit answers the question: Does the main landing page of dfnoponto.com.br (or dfnoponto.semob.df.gov.br) contain an independent, direct catalog or search autocomplete list of all active bus lines?"* This is only a preliminary DOM check, missing the deeper question of whether and how official pages and endpoints can be harvested when Semob updates lines.

**Desired behavior:**
Clearly explain that checking the landing page was a first step to identify data sources, but the primary question is whether we can actually scrape the official portal for all lines as they are modified. Document the authoritative scraping workflow: querying the Bus2 master route feed (which Semob's official portal embeds via iframe) to detect additions/deletions, cross-referencing with DFTrans REST endpoints, and executing incremental updates.

**Key interfaces:**
- `docs/04-dfnoponto-main-page-audit.md`
- `scripts/discover_catalog.py`
- `scripts/audit_dfnoponto.py`
- Endpoints: `https://mobilibus.com/api/routes?project_hash=3c189` & `http://geoserver.semob.df.gov.br/semob/linha/numero/{numero}`

**Acceptance criteria:**
- [x] Document framing in `04-dfnoponto-main-page-audit.md` updated with primary vs. preliminary questions
- [x] Complete operational update scraping architecture clearly detailed with data flow diagram
- [x] `TODO.md` updated with ticket link
