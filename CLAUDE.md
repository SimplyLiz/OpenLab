# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Tests
pytest                                    # all tests
pytest tests/test_agents/ -v              # one suite
pytest tests/ -k "test_dossier"           # by name
pytest tests/test_services/test_llm_service.py::test_synthesize_ollama  # single test

# Lint & type check
ruff check src/ tests/
mypy src/openlab/ --ignore-missing-imports

# Database
openlab init                              # create tables
alembic upgrade head                      # run migrations
alembic revision --autogenerate -m "desc" # new migration

# CLI examples
openlab dossier TP53 --cancer colorectal
openlab variants interpret sample.vcf
openlab paper-to-pipeline extract methods.pdf

# Full dev stack (backend :8000 + frontend :5173)
python launch.py
```

Build system is Maturin — the Rust CellForge engine compiles as a Python extension (`openlab.cellforge._engine`). Rust checks: `cargo check/test/clippy --manifest-path crates/cellforge-engine/Cargo.toml`.

## Architecture

**Core pipeline**: CLI/API request -> Agent runner (async generator yielding `AgentEvent`) -> parallel tool calls via `ToolRegistry` -> LLM synthesis -> Critic QA -> output

**Key modules under `src/openlab/`**:

- **agents/**: Autonomous dossier generation. 5-phase flow: planning -> identity retrieval -> evidence gathering -> LLM synthesis -> critic validation. All async generators yielding `AgentEvent`. Every tool call tracked via `ProvenanceLedger`.
- **services/**: Stateless service layer. Two LLM modules: `llm_synthesis.py` (async, used by agents) and `llm_service.py` (sync, used by validation). Both share the same provider abstraction (Anthropic/OpenAI/Gemini/Grok/Ollama) with `_openai_compatible()` helper for OpenAI-format APIs. Provider auto-detection prefers Ollama when available.
- **contrib/cancer/**: Six evidence sources (ClinVar, COSMIC, OncoKB, cBioPortal, CIViC, TCGA/GDC) all implementing `CancerEvidenceSource` ABC with `async fetch()` + `normalize()`. Registered via `register_source()` with convergence weights.
- **researchbook/**: Public research feed (threads, comments, challenges, forks). SQLAlchemy models + stateless service functions (db: Session first arg).
- **cancer/**: Variant interpretation pipeline. VCF parsing -> annotation -> consensus classification -> HTML report.
- **api/**: FastAPI with factory pattern (`create_app()`), lifespan-managed shared `httpx.AsyncClient`, WebSocket streaming for agents.
- **cli/**: Typer-based. `main.py` uses `_register_lazy()` to defer heavy imports for fast startup. The `dossier` command is registered as a flat command (not a sub-Typer group).
- **config.py**: Pydantic `AppConfig` built from env vars. Two access patterns: `config.llm.provider` (modern) and `settings.llm_provider` (legacy DNASyn compat adapter).
- **db/**: SQLAlchemy 2.0+ with `mapped_column`/`Mapped`. Alembic migrations. All Enum columns use `native_enum=False` for SQLite compat.

## Critical Rules

- **Provenance is mandatory**: Every external API call in agents must go through `ToolRegistry.call()` — never bypass it. The `_sources` key in tool return dicts feeds provenance tracking.
- **Citations enforced**: Every factual claim in agent output must cite a PMID or DOI. Uncited claims get `confidence=0.0, is_speculative=True`.
- **VCF privacy**: VCF files stay local. Only gene symbol + HGVS notation sent to external APIs.
- **Variant disclaimers**: All variant interpretation output includes research-use-only disclaimer (enforced at 5 layers).

## Code Conventions

- Python 3.11+ — use `str | None` (PEP 604), `StrEnum`, `from __future__ import annotations`
- Line length: 100 (ruff-enforced)
- All public functions need type hints
- Async everywhere for agents/services/API; sync wrappers only for legacy callers
- Absolute imports only (`from openlab.config import config`)
- Logging: `logger = logging.getLogger(__name__)` per module
- LLM synthesis temperature: 0.3

## Testing Patterns

- Directory mirrors source: `src/openlab/agents/` -> `tests/test_agents/`
- Async mocking: use `respx` for httpx, or `httpx.MockTransport` for simple fixtures
- Database tests: in-memory SQLite via conftest.py `db` fixture (transaction-scoped, auto-rollback)
- Cancer source tests use canned responses in `tests/fixtures/cancer_responses/`
- B008 is suppressed for `src/openlab/cli/*.py` (typer.Option in defaults is intentional)
