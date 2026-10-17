# 10: Comprehensive README Documentation

**What to build:** Expand `README.md` into a publication-grade, open-source project repository documentation, incorporating standard architectural and user-facing sections: Funcionalidades (Features), Pré-requisitos, Instalação, Como Usar (Usage), Estrutura dos Dados de Saída (Output Data Schema), Limitações Conhecidas (Caveats), and Contribuição (Contributing).

**Blocked by:** None (can start immediately)

**Category:** documentation
**Status:** completed

- [x] Write "Funcionalidades (Features)" detailing official line discovery, resilient multithreaded extraction, Bus2 timetable decoding, and Shapely linear referencing GTFS compiler
- [x] Write "Pré-requisitos" specifying Python 3.10+, `shapely`, `pyproj`, `pandas`, `requests`, `cryptography`, and Java JDK (for `r5py`)
- [x] Write "Instalação" with virtual environment setup and dependency installation
- [x] Write "Como Usar" with step-by-step CLI execution instructions (`discover_catalog.py`, `extract.py`, `build_gtfs.py`)
- [x] Write "Estrutura dos Dados de Saída" explaining the GTFS static tables inside `data/gtfs/gtfs_df.zip` and validation artifacts
- [x] Write "Limitações Conhecidas (Caveats)" documenting upstream DFTrans quirks (e.g. `/parada/linha/{seq}/geo` 404, stop time interpolation vs real telemetry, lack of subway data)
- [x] Write "Contribuição" and open license notice (AGPLv3)

## Comments

> *Completed: All 7 sections authored and integrated into `README.md`.*

## Agent Brief

**Category:** documentation
**Summary:** Author comprehensive, publication-ready project README sections.

**Current behavior:**
`README.md` currently contains an initial summary paragraph, a section on Open Transit Data context in the Federal District, and a BibTeX citation block. Operational instructions, installation steps, and usage workflows are not yet present in the document.

**Desired behavior:**
Provide a fully structured, bilingual or clean Portuguese `README.md` that guides researchers and transport modelers on cloning the project, running the pipeline, generating `gtfs_df.zip`, and understanding the output dataset.

**Acceptance criteria:**

- [x] All 7 requested sections are authored with technical accuracy
- [x] Preserves existing Open Data context paragraph and BibTeX citation
- [x] Documented CLI commands match the current project execution rules
- [x] `TODO.md` is updated with a reference link to this ticket
