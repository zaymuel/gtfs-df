# 17: Comprehensive Unit Test Suite with >= 75% Coverage on Core Modules

**What to build:** Expand the test suite under `Python drafts/` to achieve at least 75% automated test coverage across the most relevant operational modules in `scripts/` (`build_gtfs.py`, `config.py`, `http_client.py`, `bus2_client.py`, and `discover_catalog.py`). Ensure all tests execute reliably offline using mocks/fixtures and integrate seamlessly with the GitHub Actions CI pipeline.

**Blocked by:** 04: End-to-End GTFS Synthesis & Linear Referencing Engine, 05: GTFS Fare Modeling

**Category:** testing
**Status:** completed

- [x] Write unit tests for `scripts/http_client.py` verifying polite delay, exponential backoff, retry counting, HTTP 429/5xx handling, and 404/204 graceful returns (using mocked requests)
- [x] Write unit tests for `scripts/bus2_client.py` verifying Base36 encode/decode, OpenSSL `Salted__` AES payload decryption, and `_evp_bytes_to_key` derivation
- [x] Write unit tests for `scripts/discover_catalog.py` testing line validation (`is_valid_df_urban_line`, 8-digit ANTT line exclusion, 4-digit BRT line inclusion) and description cleaning
- [x] Expand tests for `scripts/build_gtfs.py` covering out-of-bounds stop logging, fare table generation, trip headsign derivation, and skipped line logging
- [x] Configure `pytest --cov=scripts --cov-report=term-missing` and verify overall coverage reaches at least 75%
- [x] Update `TODO.md` with a direct reference link to this ticket

## Comments

> *Implemented comprehensive offline unit test suite across `Python drafts/` (`test_compiler.py`, `test_clients.py`, `test_catalog.py`, `test_audit_and_extract.py`) comprising 44 test cases running in ~1.1s. Codebase-wide coverage reached 88.82%, with core modules reaching between 89% and 95% (`config.py`: 95%, `http_client.py`: 94%, `discover_catalog.py`: 93%, `audit_dfnoponto.py`: 92%, `build_gtfs.py`: 91%, `extract.py`: 90%, `bus2_client.py`: 89%). CI pipeline configured in `.github/workflows/ci.yml` with `--cov-fail-under=75` across Ubuntu and Windows runner matrix.*

## Agent Brief

**Category:** testing
**Summary:** Build out comprehensive automated tests to achieve >= 75% test coverage for all core extraction, compilation, and utility modules.

**Current behavior:**
Previously, only basic compiler sanity tests were in place, yielding ~27% overall coverage with critical network, crypto, and catalog modules untested.

**Desired behavior:**
A modular, offline unit test suite that comprehensively tests core business logic, cryptography, network resilience policies, and GTFS synthesis algorithms, raising test coverage to $\ge 75\%$ across `scripts/` and failing the CI build if coverage drops below this threshold.

**Key interfaces:**

- Test directory: `Python drafts/` (`test_compiler.py`, `test_clients.py`, `test_catalog.py`, `test_audit_and_extract.py`, `run_tests.py`)
- Modules under test: `scripts/build_gtfs.py`, `scripts/config.py`, `scripts/http_client.py`, `scripts/bus2_client.py`, `scripts/discover_catalog.py`, `scripts/audit_dfnoponto.py`, `scripts/extract.py`, `scripts/harvest_dftrans.py`
- CI integration: `.github/workflows/ci.yml` with `pytest "Python drafts" -v --cov=scripts --cov-fail-under=75`

**Acceptance criteria:**

- [x] Test suite runs completely offline in seconds with zero live network calls (44 tests in ~1.1s)
- [x] Total code coverage across `scripts/` measured by `pytest-cov` is $\ge 75\%$ (88.82% achieved)
- [x] CI pipeline passes on GitHub Actions for both Ubuntu and Windows environments (`.github/workflows/ci.yml`)
- [x] `TODO.md` updated with ticket link
