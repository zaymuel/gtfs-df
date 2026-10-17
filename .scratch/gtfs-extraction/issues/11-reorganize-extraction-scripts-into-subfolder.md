# 11: Clean and Organize Extraction Scripts into Dedicated Subfolder

**What to build:** An architectural restructuring task to relocate extraction utilities and processing pipelines (such as `extract.py`, `harvest_dftrans.py`, `discover_catalog.py`, `audit_dfnoponto.py`, `http_client.py`, and `bus2_client.py`) into a dedicated directory (e.g., `src/` or `scripts/`) to avoid cluttering the project root, adjust module import paths, provide clean root execution entrypoints compliant with `python <filename>.py`, and document the project layout in `README.md`.

**Blocked by:** None

**Category:** refactoring
**Status:** completed

- [x] Select and create the destination directory structure (e.g., `src/` or `scripts/`)
- [x] Move extraction and client scripts into the designated folder
- [x] Adjust relative import paths and `sys.path` resolution for `config.py` and helper modules
- [x] Provide lightweight root-level runners or clean module invocation so the project can still be executed via `python <filename>.py` without breaking permission constraints
- [x] Update documentation and `README.md` to reflect the clean directory structure

## Comments

> *Completed: Extraction programs and client libraries organized into `scripts/` (`scripts/extract.py`, `scripts/harvest_dftrans.py`, `scripts/discover_catalog.py`, `scripts/build_gtfs.py`, `scripts/audit_dfnoponto.py`, `scripts/bus2_client.py`, `scripts/http_client.py`), root clutter eliminated, and project layout documented in `README.md`.*

## Agent Brief

**Category:** refactoring
**Summary:** Move extraction scripts into a dedicated folder to keep the root directory tidy.

**Current behavior:**
Multiple script files (`extract.py`, `harvest_dftrans.py`, `discover_catalog.py`, `audit_dfnoponto.py`, `http_client.py`, `bus2_client.py`, `test_gtfs.py`) are located directly in the workspace root, creating visual clutter alongside configuration files, `README.md`, and top-level directories.

**Desired behavior:**
Organize operational scripts into a dedicated folder (e.g. `scripts/` or `src/`) while keeping root files focused on documentation, top-level configuration, and primary entrypoints. All imports and execution paths must remain robust.

**Key interfaces:**

- Dedicated script directory: `scripts/` or `src/`
- Top-level entrypoints: `build_gtfs.py`, `extract.py`, `audit_dfnoponto.py`, etc.
- Docs: `README.md` project structure section

**Acceptance criteria:**

- [x] Scripts and client libraries are neatly organized without breaking imports
- [x] All tests and entrypoints execute properly
- [x] Project layout is clearly documented in `README.md`
- [x] `TODO.md` is updated with a reference link to this ticket
