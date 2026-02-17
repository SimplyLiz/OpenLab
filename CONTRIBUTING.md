# Contributing to OpenLab

## Getting Started

```bash
git clone https://github.com/SimplyLiz/OpenLab.git
cd OpenLab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm]"
openlab init && alembic upgrade head
cd frontend && npm install && cd ..
```

Run the test suite to verify your setup:

```bash
pytest
```

## Architecture

OpenLab is a Python 3.11+ / FastAPI / React 18 platform. The core pattern:

- **Backend services** (`src/openlab/services/`) are stateless functions that take a DB session or HTTP client
- **Agents** (`src/openlab/agents/`) are async generators that yield `AgentEvent` objects for streaming
- **Evidence sources** (`src/openlab/contrib/`) register via `register_source()` and follow the `CancerEvidenceSource` ABC
- **Frontend** uses Zustand stores, fetches from `/api/v1/`, and streams via WebSocket

### Key patterns

**Adding a new evidence source:**

1. Create `src/openlab/contrib/cancer/sources/your_source.py`
2. Implement `CancerEvidenceSource` (async `fetch()` + `normalize()`)
3. Add `async def search_your_source(http, gene_symbol)` entry point
4. Register in `src/openlab/contrib/cancer/__init__.py` with a convergence weight
5. Add tests in `tests/test_contrib/test_cancer/`

**Adding a new agent tool:**

1. Add the async function to `src/openlab/agents/tools.py`
2. Register it in `ToolRegistry._register_builtins()`
3. The function should return `{"_sources": [...], ...}` — sources are automatically tracked in provenance

**Adding a ResearchBook feature:**

1. Backend: add to `src/openlab/researchbook/service.py` (stateless function, `db: Session` first arg)
2. API: add route in `src/openlab/researchbook/api.py`
3. Frontend: update store in `frontend/src/stores/researchBookStore.ts`, add UI components

## Testing

Every new feature needs tests. The project uses pytest with these conventions:

- Tests mirror source structure: `src/openlab/agents/` → `tests/test_agents/`
- Use `respx` for mocking httpx (async HTTP)
- Use `conftest.py` fixtures for shared setup (DB sessions use in-memory SQLite with StaticPool)
- Cancer source tests use canned API responses from `tests/fixtures/cancer_responses/`

```bash
pytest tests/test_agents/ -v          # Agent framework
pytest tests/test_researchbook/ -v    # ResearchBook
pytest tests/test_contrib/ -v         # Evidence sources
pytest tests/test_variant_interpretation/ -v  # Variant interpretation
pytest tests/test_paper_parser/ -v    # Paper-to-pipeline
```

## Code Quality

Before submitting a PR:

```bash
ruff check src/ tests/       # Lint (must pass with 0 errors)
mypy src/ --ignore-missing-imports  # Type check
pytest                        # All tests pass
```

The project enforces:
- Line length: 100 characters
- Import sorting via ruff (isort rules)
- StrEnum over `(str, Enum)` pattern
- Type annotations on all public functions
- `native_enum=False` on all SQLAlchemy Enum columns (SQLite compatibility)

## Pull Requests

1. Fork the repo and create a branch from `main`
2. Write tests for your changes
3. Make sure all checks pass (`pytest`, `ruff`, `mypy`)
4. Open a PR with a clear description of what and why

## Areas to Contribute

- **New cancer evidence sources** — any public cancer database with an API
- **Agent improvements** — better citation validation, multi-step reasoning, adaptive planning
- **Variant annotation** — ACMG/AMP guideline implementation, pharmacogenomics
- **ResearchBook UX** — thread visualization, claim graphs, evidence provenance explorer
- **Paper parsing** — better methods section detection, support for supplementary materials
- **Documentation** — API docs, tutorials, example notebooks

## Safety Rules

These are non-negotiable:

- **Citations**: every factual claim in agent output must cite a PMID or DOI. Uncited claims are marked speculative with confidence 0.0
- **Variant disclaimers**: all variant interpretation output must include the research-use-only disclaimer. It's enforced at 5 layers — don't bypass any of them
- **VCF privacy**: VCF files stay local. Only gene symbol + HGVS notation are sent to external APIs
- **Provenance**: every external API call is tracked in the provenance ledger. Don't bypass `ToolRegistry.call()`
