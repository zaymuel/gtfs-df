# 07: Bus2 Encryption Passphrase Tracking and Documentation Consolidation

**What to build:** An operational and architectural task to (1) document the Bus2 (`bus2.info` / `mobilibus.com`) frontend AES encryption passphrase extraction procedure, rotation contingency, and configuration decoupling, and (2) consolidate redundant reverse engineering notes across project documentation into a single authoritative reference location.

**Blocked by:** None (can start immediately)

**Category:** documentation / refactoring
**Status:** ready-for-agent

- [ ] Document the current public frontend constant passphrase (`"GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n"`) and the exact extraction procedure from Bus2 Angular webpack bundles (`main.*.js` / chunk `244.*.js`)
- [ ] Implement passphrase configurability in `config.py` (and fallback / auto-sniffing or environment variable override in `bus2_client.py`) to prevent pipeline breakage if Bus2 updates frontend builds
- [ ] Audit and remove redundant Bus2 notes spread across `docs/00-initial-project-context.md`, `docs/01-dftrans-api-knowledge.md`, and other project files
- [ ] Consolidate all Bus2/Mobilibus protocol specifications, endpoint schemas, Base36 conversion algorithms, and decryption workflows into `docs/03-bus2-reverse-engineering.md` as the single authoritative reference

## Comments

> *Created from user backlog item in `TODO.md`.*

## Agent Brief

**Category:** documentation / refactoring
**Summary:** Centralize Bus2 encryption key lifecycle management and unify all reverse engineering documentation into a single thematic reference.

**Current behavior:**
- The AES encryption passphrase (`"GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n"`) is currently hardcoded in `bus2_client.py` and documented in `docs/03-bus2-reverse-engineering.md`. If Bus2 deploys a new Angular bundle with a rotated key, encrypted endpoints (`/painel/api/*`) will fail without a quick procedure to update it.
- Notes and discoveries regarding Bus2 endpoints, HTML iframe embeds, and query parameters are partially duplicated across `docs/00-initial-project-context.md`, `docs/01-dftrans-api-knowledge.md`, and `docs/03-bus2-reverse-engineering.md`.

**Desired behavior:**
- Establish `docs/03-bus2-reverse-engineering.md` as the definitive, single source of truth for all Bus2/Mobilibus mechanics.
- Prune redundant Bus2 paragraphs from earlier exploratory docs, replacing them with clean hyperlinks pointing to `docs/03-bus2-reverse-engineering.md`.
- Explicitly document the passphrase lifecycle, how it was located in `mobilibus.com` Angular source maps/bundles, and how `config.py` exposes `BUS2_ENCRYPTION_KEY` so operators can override it without touching extraction code.

**Key interfaces:**
- Config: `config.py` (`BUS2_ENCRYPTION_KEY`)
- Client: `bus2_client.py`
- Authoritative documentation: `docs/03-bus2-reverse-engineering.md`

**Acceptance criteria:**
- [ ] Passphrase lifecycle, extraction regex/procedure, and rotation response are fully documented in `docs/03-bus2-reverse-engineering.md`
- [ ] `config.py` centrally defines `BUS2_ENCRYPTION_KEY` and `bus2_client.py` imports it from config
- [ ] Redundant references in `docs/00-initial-project-context.md` and `docs/01-dftrans-api-knowledge.md` are cross-referenced to `docs/03-bus2-reverse-engineering.md`
- [ ] `TODO.md` is updated with a reference link to this ticket

**Out of scope:**
- GTFS linear referencing engine (Ticket 04)
- Fare modeling (Ticket 05)

