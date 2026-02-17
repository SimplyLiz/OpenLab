# BioLab

Unified bioinformatics platform for gene analysis, evidence synthesis, and whole-cell simulation.

BioLab combines genomic data ingestion, LLM-powered functional prediction, and multi-scale cell simulation into a single interactive environment. Load a genome, analyze genes against public databases, synthesize function hypotheses with AI, and simulate cellular behavior — all from one interface.

## Features

- **Multi-genome management** — load genomes from GenBank, NCBI accessions, Ensembl, or FASTA files
- **Gene analysis & evidence synthesis** — aggregate functional evidence from BRENDA, SABIO-RK, KEGG, and Datanator
- **LLM-powered predictions** — synthesize gene function hypotheses using Claude, OpenAI, or local Ollama models
- **Cell simulation** — multi-timescale ODE engine covering metabolism, gene expression, growth, mutation, and epigenetics
- **CellForge** — advanced whole-cell simulation with thermodynamic constraints, stochastic processes (Gillespie SSA), and FBA
- **Population dynamics** — population-level growth, division, and genetic drift simulation
- **Interactive frontend** — React/TypeScript UI with genome browser, petri dish visualization, knockout lab, and real-time charts
- **CLI & API** — full Typer CLI and FastAPI REST/WebSocket API

## Requirements

- Python 3.11+
- Node.js 18+ (for frontend)
- Rust toolchain (optional, for native CellForge engine)

## Quick Start

```bash
# Clone
git clone https://github.com/SimplyLiz/BioLab.git
cd BioLab

# Python setup
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -e ".[dev,llm]"

# Frontend setup
cd frontend && npm install && cd ..

# Initialize database
biolab init

# Launch both backend and frontend
python launch.py
```

Backend runs on `http://localhost:8000`, frontend on `http://localhost:5173`.

## Configuration

Set via environment variables or a `.env` file:

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key for LLM synthesis | — |
| `OPENAI_API_KEY` | OpenAI API key (alternative provider) | — |
| `LLM_PROVIDER` | `anthropic`, `openai`, or `ollama` | `anthropic` |
| `LLM_MODEL` | Model name | `claude-sonnet-4-5-20250929` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///biolab.db` |
| `NCBI_API_KEY` | NCBI E-utilities key (10 req/s vs 3) | — |
| `NCBI_EMAIL` | Required by NCBI for identification | — |
| `BIOLAB_BACKEND_PORT` | Backend port | `8000` |
| `BIOLAB_FRONTEND_PORT` | Frontend port | `5173` |

## CLI

```
biolab genes       Gene operations (list, import, search)
biolab analyze     Deep gene analysis & LLM synthesis
biolab evidence    Evidence source management
biolab synthesize  LLM function synthesis
biolab pipeline    Multi-phase evidence pipeline
biolab validate    Validation and quality checks
biolab cellforge   CellForge whole-cell simulation engine
biolab init        Initialize database
```

### CellForge subcommands

```
biolab cellforge annotate <fasta>   Run genome annotation pipeline
biolab cellforge run <config.json>  Run a whole-cell simulation
biolab cellforge serve              Start the CellForge API server
biolab cellforge benchmark          Run performance benchmarks
biolab cellforge info               Show version and dependency info
```

## Docker

```bash
docker-compose up
```

This starts the backend (port 8000) and Redis cache (port 6379).

For GPU-accelerated workloads:

```bash
docker build -f docker/Dockerfile.gpu -t biolab-gpu .
```

## Project Structure

```
src/biolab/
  api/              REST API (FastAPI)
  cli/              CLI commands (Typer)
  services/         Business logic (LLM, ETL, import)
  ingestion/        GenBank/FASTA parsing
  simulation/       Core simulation engine
  cellforge/        Advanced whole-cell simulation
    core/           Simulation kernel
    processes/      Biological processes (transcription, translation, etc.)
    constraints/    Thermodynamic & energy constraints
    annotation/     Genome annotation pipeline
    api/            CellForge REST API
  contrib/          Plugin modules (DNASyn evidence pipeline)
  db/               Database models & migrations

frontend/
  src/pages/        React page components
  src/components/   UI components (genome browser, petri dish, charts)
  src/hooks/        Data fetching & state hooks
  src/stores/       Zustand state management

crates/
  cellforge-engine/ Rust native simulation engine (optional)
```

## Optional Dependencies

Install extras for additional capabilities:

```bash
pip install -e ".[cellforge]"    # CellForge (COBRApy, GillesPy2, Redis, Zarr)
pip install -e ".[ml]"           # ML models (PyTorch, Transformers)
pip install -e ".[validation]"   # Validation (libRoadRunner, matplotlib)
pip install -e ".[dashboard]"    # Streamlit dashboard
pip install -e ".[postgres]"     # PostgreSQL support
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests
ruff check src/           # Lint
mypy src/                 # Type check
```

## License

All rights reserved.
