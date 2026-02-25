# OpenLab

Open bioinformatics platform for gene analysis, cancer research, and autonomous scientific investigation.

> **Status: Early-stage (v0.1.0)** — Under active development. APIs, schemas, and agent behavior will change. Not suitable for clinical use.

OpenLab extends a mature genomics platform (BioLab) with AI agents that autonomously investigate cancer genes, produce fully-cited research dossiers, and publish findings to a public feed where humans can challenge, correct, and fork research.

---

## What It Does

### Inherited from BioLab

Genome management, gene analysis, evidence synthesis from public databases (BRENDA, KEGG, SABIO-RK), LLM-powered functional prediction, multi-scale cell simulation, CellForge whole-cell engine, population dynamics.

### New in OpenLab

**Gene Dossier Agent** — Autonomous 5-phase pipeline that investigates a gene's role in cancer. Fetches identity from NCBI/Ensembl/UniProt, gathers literature from EuropePMC, pulls evidence from 6 cancer databases, synthesizes findings via LLM, validates citations through a critic pass, and produces a fully-cited Markdown or JSON report with complete provenance tracking.

**ResearchBook** — Public feed where agent-generated research is published as threads. Humans can comment, challenge specific claims (triggers automated re-evaluation), submit corrections, endorse findings, and fork threads with modified parameters.

**Cancer Evidence Sources** — Six cancer databases integrated into the convergence scoring engine: ClinVar, COSMIC, OncoKB, cBioPortal, CIViC, and TCGA/GDC. Evidence is scored with tiered weighting — cancer sources carry the most weight, followed by functional annotations, then literature.

**Variant Interpretation** — Parse VCF files locally, annotate variants against multiple databases in parallel, compute consensus pathogenicity classification, and render reports. VCF data stays local — only gene symbol and HGVS notation are sent to external APIs.

**Paper-to-Pipeline** — Extract methods sections from PDFs, detect bioinformatics techniques, map them to pipeline stages, and generate validated YAML configs.

**CellForge** — Whole-cell simulation engine written in Rust, compiled as a Python extension via Maturin/PyO3. ODE and stochastic solvers, metabolic and expression processes, thermodynamic constraints, time-series storage in Zarr/HDF5.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic, Typer |
| Frontend | React 19, TypeScript, Vite, Three.js, D3.js, Zustand |
| Simulation | Rust (PyO3/Maturin), ndarray, nalgebra, rayon |
| Database | SQLite (default), PostgreSQL (optional), Alembic migrations |
| LLM | Anthropic, OpenAI, Gemini, Grok, Ollama (auto-detected) |
| Infra | Docker, Docker Compose, Redis |

---

## Quick Start

```bash
git clone https://github.com/SimplyLiz/OpenLab.git
cd OpenLab

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm]"

# Database
cp .env.example .env           # edit with your API keys
openlab init                    # create tables
alembic upgrade head            # run migrations

# Frontend
cd frontend && npm install && cd ..

# Launch (backend :8000 + frontend :5173)
python launch.py
```

Backend: `http://localhost:8000` | Frontend: `http://localhost:5173`

### Docker

```bash
docker-compose up
```

The Dockerfile is a multi-stage build: Rust compilation, frontend build, then a slim Python runtime. The compose file includes Redis for CellForge simulation data caching.

### Rust Engine (Optional)

The CellForge engine compiles as a Python extension. If you need simulation features:

```bash
cargo check --manifest-path crates/cellforge-engine/Cargo.toml
pip install -e ".[cellforge]"
```

---

## CLI

```bash
# Gene dossier — autonomous cancer gene investigation
openlab dossier TP53 --cancer colorectal
openlab dossier BRAF --cancer melanoma --format json --output braf.json

# Variant interpretation — annotate a VCF file
openlab variants interpret sample.vcf --tumor-type breast --genome hg38

# Paper to pipeline — extract methods from a research paper
openlab paper-to-pipeline extract methods.pdf --output pipeline.yaml

# Agent management
openlab agent run TP53 --cancer colorectal
openlab agent status <run_id>
openlab agent history --limit 20

# Gene analysis
openlab genes list
openlab genes search TP53
openlab analyze <gene> --deep

# Database & utilities
openlab init
openlab evidence list
openlab pipeline run <genome_id>
openlab export <gene> --format json
```

---

## API

All endpoints under `/api/v1/`. WebSocket streaming available for real-time agent events.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents/dossier` | Start dossier generation |
| GET | `/agents/dossier/{run_id}` | Get completed dossier |
| WS | `/agents/dossier/{run_id}/stream` | Stream agent events in real-time |
| GET | `/researchbook/feed` | Paginated research thread feed |
| GET | `/researchbook/threads/{id}` | Thread detail with comments |
| POST | `/researchbook/threads/{id}/challenge` | Challenge a specific claim |
| POST | `/researchbook/threads/{id}/fork` | Fork thread with modified parameters |
| GET | `/genes/{id}` | Gene detail |
| GET | `/evidence` | Search evidence |
| POST | `/hypotheses` | Generate research hypothesis |
| POST | `/cellforge/simulate` | Run whole-cell simulation |
| GET | `/health` | Health check |

Interactive docs at `http://localhost:8000/docs` when running.

---

## Architecture

```
CLI / API request
    |
    v
Agent Runner (async generator yielding AgentEvent)
    |
    +-- Phase 1: Planning
    +-- Phase 2: Identity retrieval (NCBI, Ensembl, UniProt)
    +-- Phase 3: Evidence gathering (parallel)
    |       +-- Literature (EuropePMC)
    |       +-- Database evidence
    |       +-- Cancer sources (ClinVar, COSMIC, OncoKB, cBioPortal, CIViC, TCGA/GDC)
    +-- Phase 4: LLM synthesis (temperature 0.3, mandatory citations)
    +-- Phase 5: Critic QA (citation validation, speculation detection)
    |
    v
Dossier output (Markdown / JSON) with provenance ledger
```

Every external API call is tracked through `ToolRegistry.call()` and recorded in the `ProvenanceLedger`. Every factual claim must cite a PMID or DOI — uncited claims are automatically flagged as speculative with confidence 0.0.

### Project Structure

```
src/openlab/
  agents/           Autonomous agent framework (runner, planner, retriever,
                    synthesizer, critic, provenance, 30+ registered tools)
  researchbook/     Public research feed (threads, comments, challenges, forks)
  cancer/           Variant interpretation (VCF parsing, annotation, classification)
  contrib/cancer/   Cancer evidence sources (6 databases, all async)
  paper/            Paper-to-pipeline (PDF extraction, methods parsing, YAML)
  cellforge/        Whole-cell simulation engine (Rust/PyO3 backend)
  api/v1/           FastAPI routes (REST + WebSocket)
  cli/              Typer CLI (lazy-loaded for fast startup)
  services/         Stateless services (LLM, convergence, evidence, ETL,
                    NCBI, Ensembl, UniProt, gene lookup, hypothesis)
  db/               SQLAlchemy 2.0 models, Alembic migrations
  config.py         Pydantic config from env vars

frontend/
  src/pages/        React pages (dashboard, ResearchBook, dossier viewer)
  src/components/   UI components (claims table, confidence bars, 3D protein viewer)
  src/stores/       Zustand state management
  src/hooks/        WebSocket streaming hooks

crates/
  cellforge-engine/ Rust whole-cell simulation (ODE, SSA, metabolic processes)

tests/              418 tests mirroring source structure
  fixtures/         Canned API responses, sample VCF files
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values. All settings have sensible defaults — you only need an LLM provider key to get started.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///openlab.db` |
| `LLM_PROVIDER` | `anthropic`, `openai`, `gemini`, `grok`, or `ollama` | `anthropic` |
| `LLM_MODEL` | Model identifier for chosen provider | `claude-sonnet-4-5-20250929` |
| `ANTHROPIC_API_KEY` | Claude API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `GROK_API_KEY` | xAI Grok API key | — |
| `OLLAMA_URL` | Ollama server URL (local, free) | `http://localhost:11434` |
| `NCBI_API_KEY` | NCBI E-utilities key (10 req/s vs 3) | — |
| `ONCOKB_TOKEN` | OncoKB API token (free academic registration) | — |
| `COSMIC_TOKEN` | COSMIC API token (academic registration) | — |
| `AGENT_TIMEOUT_SECONDS` | Max agent run duration | `600` |
| `AGENT_MAX_TOOL_CALLS` | Max tool calls per agent run | `50` |
| `SIM_DURATION` | CellForge simulation duration (seconds) | `72000` |
| `ENABLE_ESM2` | Enable ESM-2 protein folding (needs GPU) | `false` |

### LLM Provider Priority

When `LLM_PROVIDER` is not explicitly set, the system auto-detects in this order:
1. **Ollama** (if reachable at `OLLAMA_URL`) — free, local, no API key needed
2. **Anthropic** / **OpenAI** / **Gemini** / **Grok** — whichever has a key configured

### Optional Dependencies

Install only what you need:

```bash
pip install -e ".[dev]"           # Testing + linting (pytest, ruff, mypy)
pip install -e ".[llm]"           # OpenAI SDK
pip install -e ".[cancer]"        # VCF parsing, CIViC, liftover, PDF extraction
pip install -e ".[cellforge]"     # Whole-cell simulation (COBRA, GillesPy2, Zarr)
pip install -e ".[validation]"    # Hypothesis validation (libroadrunner, pandas)
pip install -e ".[ml]"            # PyTorch + Transformers (GPU recommended)
pip install -e ".[dashboard]"     # Streamlit dashboards
pip install -e ".[postgres]"      # PostgreSQL support
```

---

## Safety Rules

These are non-negotiable and enforced in code:

- **Citations are mandatory.** Every factual claim in agent output must cite a PMID or DOI. Uncited claims automatically get `confidence=0.0` and `is_speculative=True`.
- **Variant disclaimers.** All variant interpretation output includes a research-use-only disclaimer, enforced at 5 independent layers.
- **VCF privacy.** VCF files never leave the local machine. Only gene symbol + HGVS notation are sent to external APIs.
- **Provenance tracking.** Every external API call goes through `ToolRegistry.call()` — never bypass it. The `_sources` key in tool return dicts feeds the provenance ledger.

---

## Development

```bash
# Tests
pytest                                    # full suite (418 tests)
pytest tests/test_agents/ -v              # agent framework
pytest tests/test_contrib/test_cancer/ -v # cancer evidence sources
pytest tests/test_researchbook/ -v        # ResearchBook
pytest tests/ -k "test_dossier"           # by name

# Lint & type check
ruff check src/ tests/
mypy src/openlab/ --ignore-missing-imports

# Rust engine
cargo check --manifest-path crates/cellforge-engine/Cargo.toml
cargo test --manifest-path crates/cellforge-engine/Cargo.toml
cargo clippy --manifest-path crates/cellforge-engine/Cargo.toml

# Database migrations
alembic upgrade head                      # apply all
alembic revision --autogenerate -m "desc" # create new migration
```

### Code Conventions

- Python 3.11+ — `str | None` (PEP 604), `StrEnum`, `from __future__ import annotations`
- Line length 100, enforced by ruff
- Type hints on all public functions
- Async everywhere for agents, services, and API; sync wrappers only for legacy callers
- Absolute imports only (`from openlab.config import config`)
- LLM synthesis temperature: 0.3
- SQLAlchemy Enum columns use `native_enum=False` for SQLite compatibility

---

## Documentation

- **[User Guide](docs/user-guide.md)** — Step-by-step guide for researchers. Covers installation, the web interface, generating dossiers, interpreting variants, and the ResearchBook. No programming experience required.
- **[Contributing](CONTRIBUTING.md)** — For developers: architecture, patterns for adding evidence sources and agent tools, testing conventions.

## License

[MIT](LICENSE)
