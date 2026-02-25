# OpenLab User Guide

This guide is for researchers who want to use OpenLab for cancer gene investigation, variant interpretation, or evidence synthesis. You don't need programming experience — the web interface covers most workflows. The command line is available for power users and automation.

> **OpenLab is early-stage software (v0.1.0).** Results are for research purposes only. All variant interpretation output includes a research-use-only disclaimer. Never use OpenLab output for clinical decisions.

---

## Table of Contents

- [Getting Started](#getting-started)
- [The Web Interface](#the-web-interface)
- [Gene Dossiers](#gene-dossiers)
- [Variant Interpretation](#variant-interpretation)
- [The ResearchBook](#the-researchbook)
- [Understanding the Results](#understanding-the-results)
- [Command Line Reference](#command-line-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### What You Need

- A computer running macOS, Linux, or Windows
- Python 3.11 or newer ([download here](https://www.python.org/downloads/))
- An LLM provider — either:
  - **Ollama** (free, runs locally — [install here](https://ollama.ai)) — recommended for getting started
  - An API key from Anthropic, OpenAI, Google Gemini, or xAI Grok

### Installation

Open a terminal (on macOS: search for "Terminal" in Spotlight) and run:

```bash
git clone https://github.com/SimplyLiz/OpenLab.git
cd OpenLab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm]"
```

Set up the database:

```bash
openlab init
alembic upgrade head
```

If you want the web interface (recommended):

```bash
cd frontend && npm install && cd ..
```

### Setting Up Your LLM

OpenLab uses a large language model to synthesize evidence into readable research summaries. You have two options:

**Option A: Ollama (free, local)**

Install Ollama from [ollama.ai](https://ollama.ai), then pull a model:

```bash
ollama pull llama3.1
```

That's it — OpenLab detects Ollama automatically.

**Option B: Cloud provider**

Copy the example configuration and add your API key:

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in one of:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
GROK_API_KEY=xai-...
```

### Launching OpenLab

```bash
python launch.py
```

This starts both the backend and the web interface. Open your browser to:

- **Web interface:** http://localhost:5173
- **API docs:** http://localhost:8000/docs

Press `Ctrl+C` in the terminal to stop.

---

## The Web Interface

### First Steps

When you open the web interface, you'll land on the **Genome Selector** page. This shows your available genomes as cards — each displaying the organism name, accession number, genome size, and GC content.

To import a new genome, use the search bar to query NCBI by organism name, then click to import.

Once you select a genome, a sidebar appears with six sections:

| Section | What It's For |
|---------|--------------|
| **Dashboard** | Overview of your genome — gene counts, research progress, category breakdown |
| **Petri Dish** | 2D animated cell visualization with gene knockout experiments |
| **Genome Map** | Circular or linear view of gene positions, color-coded by function |
| **Research** | The main workspace for gene investigation and hypothesis review |
| **Simulation** | Metabolic flux results — concentrations, pathway flows, expression |
| **CellForge 3D** | Advanced 3D cell visualization with real-time perturbation controls |

### The Research Workspace

This is where most of the gene investigation happens. It's a two-panel layout:

**Left sidebar** has four tabs:
- **Queue** — Genes with unknown function, waiting to be analyzed. Click "Analyze" on any gene, or hit "Research All Unknown" to batch-process them.
- **Review** — Genes where the AI has proposed a function. Each shows a confidence percentage. Your job: approve, reject, or correct the proposal.
- **Grads** — Graduated genes — ones where you've approved a proposed function.
- **Conflicts** — Genes where evidence sources disagree. These need your expert judgment.

**Right panel** shows the full detail for whichever gene you've selected:
- Gene coordinates, product annotation, sequence
- Convergence score — how well evidence sources agree
- AI hypothesis with confidence percentage
- Evidence from each source (STRING, BLAST, InterPro, etc.)
- Action buttons: **Approve**, **Reject**, or **Correct**

### Quick Gene Search

Press `Cmd+K` (macOS) or `Ctrl+K` (Windows/Linux) anywhere in the interface to open the command palette. Type a gene name, locus tag, or product description to jump straight to it.

---

## Gene Dossiers

A dossier is a comprehensive, fully-cited research summary about a gene's role in cancer. OpenLab's agent gathers evidence from multiple databases, synthesizes it through an LLM, and validates every citation.

### From the Web Interface

Navigate to the **ResearchBook** section (the `/research` route). If you've run a dossier agent, the results appear here as research threads.

### From the Command Line

The simplest way to generate a dossier:

```bash
openlab dossier TP53 --cancer colorectal
```

This prints the dossier directly to your terminal. To save it as a file:

```bash
openlab dossier TP53 --cancer colorectal --output tp53_colorectal.md
```

For machine-readable output:

```bash
openlab dossier BRAF --cancer melanoma --format json --output braf.json
```

### What Happens Behind the Scenes

The dossier agent runs five phases:

1. **Planning** — Decides which evidence sources to query based on the gene and cancer type.
2. **Identity retrieval** — Fetches gene information from NCBI, Ensembl, and UniProt in parallel.
3. **Evidence gathering** — Queries six cancer databases (ClinVar, COSMIC, OncoKB, cBioPortal, CIViC, TCGA/GDC) plus literature from EuropePMC. All queries run in parallel.
4. **LLM synthesis** — The language model reads all evidence and writes a structured summary. Every factual claim must cite a PMID or DOI.
5. **Critic validation** — A second pass checks that citations are real, flags unsupported claims as speculative, and assigns confidence scores.

You'll see a progress spinner in the terminal while this runs. A typical dossier takes 1-3 minutes depending on your LLM provider.

### Reading the Output

A dossier contains several sections (Gene Identity, Molecular Biology, Clinical Significance, etc.). Each section has:

- **Claims** — Individual factual statements extracted from the synthesis
- **Citations** — PMID or DOI references in `[PMID:12345678]` format
- **Confidence scores** — A number from 0.0 to 1.0 after each claim
- **Speculation markers** — Claims without citations are marked `[SPECULATIVE]`

At the end you'll see a summary: total claims, cited vs. speculative, convergence score, and how many tool calls the agent made.

---

## Variant Interpretation

OpenLab can annotate variants from VCF files against multiple cancer databases and compute a consensus pathogenicity classification.

### Important Privacy Note

Your VCF file never leaves your computer. OpenLab only sends the gene symbol and HGVS notation (e.g., "TP53 p.R175H") to external databases — never raw genomic coordinates or patient identifiers.

### Running an Interpretation

```bash
openlab variants interpret sample.vcf --tumor-type breast
```

Options:

| Flag | What It Does | Default |
|------|-------------|---------|
| `--tumor-type, -t` | Cancer type for context-specific annotation | none |
| `--genome, -g` | Genome build | `hg38` |
| `--output, -o` | Save report to file | prints to terminal |
| `--format, -f` | `markdown` or `json` | `markdown` |

### Reading the Report

The report shows:
- Total variants found in your VCF
- How many are pathogenic or likely pathogenic
- How many are actionable (have therapeutic implications)
- Per-variant evidence from each cancer database
- Consensus classification

Every report includes a **research-use-only disclaimer**. This is intentional and cannot be removed.

---

## The ResearchBook

The ResearchBook is a public feed where research findings are shared for peer review. Think of it as a discussion board specifically for gene research results.

### Browsing the Feed

Open the web interface and navigate to the ResearchBook (`/research`). You'll see a list of research threads, each showing:

- Gene symbol and cancer type
- Status badge (Draft, Published, Challenged, Superseded, Archived)
- Convergence score — how well the evidence sources agree
- Comment count, challenge count, fork count

Use the filters at the top to narrow by gene, cancer type, or status. Sort by recency, convergence score, or number of challenges.

### Reading a Thread

Click any thread to see the full research content:

- **Summary** — The synthesized research text
- **Claims table** — Every extracted claim with its confidence score and citations
- **Comments** — Discussion from other researchers

### Challenging a Claim

If you disagree with a specific claim, scroll to the comment section and check "Challenge a claim." Describe what you think is wrong and why. Challenges are flagged visually and can trigger re-evaluation.

### Forking a Thread

If you want to explore a different angle — say, the same gene but in a different cancer type, or with different parameters — click "Fork." This creates a new thread linked to the original, with your modifications noted.

### Thread Lifecycle

Threads progress through these stages:

```
Draft → Published → Challenged → Superseded → Archived
                  ↗
       (or stays Published if unchallenged)
```

- **Draft** — Not yet visible to others
- **Published** — Visible in the feed
- **Challenged** — Someone has disputed a claim
- **Superseded** — A newer version (fork) has replaced this thread
- **Archived** — No longer active

---

## Understanding the Results

### Convergence Score

The convergence score (0–100%) measures how much independent evidence sources agree with each other. It's weighted by evidence tier:

| Tier | Sources | Weight | Why |
|------|---------|--------|-----|
| Cancer | ClinVar, COSMIC, OncoKB, cBioPortal, CIViC, TCGA/GDC | Highest (3x) | Direct cancer evidence — most relevant |
| Functional | BLAST, InterPro, STRING, etc. | Medium (2x) | Functional context supports cancer role |
| Literature | EuropePMC articles | Lower (0.5x) | Supports but shouldn't dominate score |

Identity sources (NCBI, Ensembl, UniProt) are excluded — they describe the same gene differently, which isn't independent evidence.

**Interpreting the score:**
- **70–100%** — Strong agreement across sources. High confidence in findings.
- **40–70%** — Moderate agreement. Some sources may conflict. Worth reviewing the evidence breakdown.
- **Below 40%** — Weak agreement or limited evidence. Treat findings with caution.

### Confidence Scores

Each individual claim has a confidence score from 0.0 to 1.0:

- **0.7–1.0** — Well-supported by cited evidence
- **0.4–0.7** — Supported but with caveats
- **Below 0.4** — Weak support or speculative
- **0.0** — No citation found; automatically marked as speculative

### Citations

OpenLab enforces citations on every factual claim. You'll see them in two formats:

- `[PMID:12345678]` — A PubMed identifier. Look it up at `pubmed.ncbi.nlm.nih.gov/12345678`
- `[DOI:10.1038/...]` — A DOI. Look it up at `doi.org/10.1038/...`

Claims without citations are tagged `[SPECULATIVE]` and get a confidence of 0.0. This is by design — it's better to be explicit about uncertainty than to present unverified claims as fact.

### Cancer Evidence Sources

OpenLab queries six cancer databases. Here's what each one provides:

| Source | What It Contains | Access |
|--------|-----------------|--------|
| **ClinVar** | Variant pathogenicity classifications from clinical labs | Free, public |
| **COSMIC** | Cancer-specific mutation frequencies and distributions | Free academic registration |
| **OncoKB** | Oncogenicity annotations and therapeutic implications | Free academic registration |
| **cBioPortal** | Mutation data across large-scale cancer studies (e.g., MSK-IMPACT) | Free, public |
| **CIViC** | Community-curated clinical interpretations of variants | Free, public |
| **TCGA/GDC** | Pan-cancer genomic data from The Cancer Genome Atlas | Free, public |

Not all sources require API tokens. ClinVar, cBioPortal, CIViC, and TCGA/GDC work out of the box. COSMIC and OncoKB need free academic registration — see [Configuration](#configuration) for details.

---

## Command Line Reference

If you prefer working from the terminal, or need to automate analyses, here are the most useful commands.

### Gene Dossiers

```bash
# Basic dossier
openlab dossier TP53 --cancer colorectal

# Save to file
openlab dossier BRAF --cancer melanoma --output braf_report.md

# JSON format (for scripts or other tools)
openlab dossier KRAS --cancer pancreatic --format json --output kras.json

# Skip the critic validation step (faster, less rigorous)
openlab dossier EGFR --cancer lung --no-critic
```

### Variant Interpretation

```bash
# Basic interpretation
openlab variants interpret sample.vcf

# With cancer context
openlab variants interpret tumor_variants.vcf --tumor-type breast --genome hg38

# Save report
openlab variants interpret sample.vcf --output report.md
```

### Paper-to-Pipeline

Extract methods from a research paper and generate a pipeline configuration:

```bash
openlab paper-to-pipeline extract methods.pdf --output pipeline.yaml
```

### Gene Management

```bash
# Import genes from a GenBank or FASTA file
openlab genes import my_genome.gbk

# List all genes
openlab genes list

# List only genes with unknown function
openlab genes list --unknown-only

# Show full details for a gene
openlab genes show JCVISYN3A_0001

# Approve an AI-proposed function
openlab genes graduate JCVISYN3A_0001 --function "ATP synthase subunit"

# Batch-approve high-confidence predictions
openlab genes graduate-batch --threshold 0.7 --dry-run   # preview first
openlab genes graduate-batch --threshold 0.7              # then for real
```

### Analysis & Validation

```bash
# Full evidence dossier for a gene
openlab analyze dossier JCVISYN3A_0005

# Run LLM analysis
openlab analyze deep JCVISYN3A_0005

# Batch analyze unknown genes
openlab analyze batch --limit 20 --unknown-only

# Check pipeline status
openlab analyze status

# Compute convergence scores
openlab analyze convergence --min-score 0.5

# Run validation suite
openlab analyze validate-all --export validation.json

# Check for conflicting evidence
openlab analyze disagreements
```

### Evidence Collection

```bash
# Run all evidence sources
openlab evidence run-all

# Run a specific source
openlab evidence run esmfold

# Check what evidence you have
openlab evidence status
```

### Multi-Phase Pipeline

The pipeline runs evidence collection in five phases, from quick annotations to deep analysis:

```bash
# Run all phases
openlab pipeline run

# Run specific phases
openlab pipeline run --phase 1          # Homology & basic annotation
openlab pipeline run --phases 1,2,3     # First three phases

# Check coverage
openlab pipeline status
```

| Phase | What It Does | Speed |
|-------|-------------|-------|
| 1 | Homology & basic annotation (EuropePMC, eggNOG) | Fast |
| 2 | Structure prediction (ESMFold, AlphaFold, Foldseek) | Medium |
| 3 | Context & localization (operons, transmembrane, signal peptides) | Medium |
| 4 | Deep homology (HHpred, HHblits, HMMscan) | Slow |
| 5 | LLM synthesis — combines all evidence into predictions | Depends on LLM |

---

## Configuration

### Cancer Database Tokens

Some cancer databases require free academic registration:

**OncoKB** — Register at [oncokb.org/account/register](https://www.oncokb.org/account/register) and request an API token. Add to your `.env`:
```
ONCOKB_TOKEN=your-token-here
```

**COSMIC** — Register at [cancer.sanger.ac.uk/cosmic/register](https://cancer.sanger.ac.uk/cosmic/register). After approval, add:
```
COSMIC_TOKEN=your-token-here
```

**NCBI** — Optional but recommended. An API key increases your rate limit from 3 to 10 requests per second. Register at [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/):
```
NCBI_API_KEY=your-key-here
```

The remaining sources (ClinVar, cBioPortal, CIViC, TCGA/GDC) work without any registration.

### All Configuration Options

These go in your `.env` file:

| Variable | What It Does | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Where to store data | `sqlite:///openlab.db` |
| `LLM_PROVIDER` | Which LLM to use | auto-detected |
| `LLM_MODEL` | Specific model name | provider default |
| `OLLAMA_URL` | Ollama server address | `http://localhost:11434` |
| `ANTHROPIC_API_KEY` | Claude API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `GROK_API_KEY` | xAI Grok API key | — |
| `NCBI_API_KEY` | NCBI E-utilities key | — |
| `ONCOKB_TOKEN` | OncoKB API token | — |
| `COSMIC_TOKEN` | COSMIC API token | — |
| `AGENT_TIMEOUT_SECONDS` | Max time for dossier generation | `600` (10 min) |
| `AGENT_MAX_TOOL_CALLS` | Max API calls per dossier run | `50` |
| `ENABLE_ESM2` | Protein structure prediction (needs GPU) | `false` |

---

## Troubleshooting

### "No LLM provider available"

OpenLab needs a language model to synthesize evidence. Either:
- Install and start Ollama (`ollama serve`), then pull a model (`ollama pull llama3.1`)
- Or add an API key to your `.env` file (see [Configuration](#configuration))

### Dossier takes too long or times out

The default timeout is 10 minutes. If your LLM is slow (common with local Ollama on CPU):
- Increase the timeout: set `AGENT_TIMEOUT_SECONDS=1200` in `.env`
- Or use a cloud LLM provider for faster results

### "Module not found" errors for cancer/variant features

Some features need extra dependencies:

```bash
pip install -e ".[cancer]"      # VCF parsing, CIViC, PDF extraction
pip install -e ".[cellforge]"   # Whole-cell simulation
```

### Database errors after updating

If you pull new code and get database errors, run the migrations:

```bash
alembic upgrade head
```

### Frontend won't start

Make sure Node.js is installed, then:

```bash
cd frontend
npm install
cd ..
python launch.py
```

### Low convergence scores

A low convergence score doesn't mean the results are wrong — it means the evidence sources have limited overlap. This is common for:
- Less-studied genes
- Rare cancer types
- Genes with primarily functional (non-cancer) evidence

Check the tier breakdown in the dossier output to see which evidence categories are contributing.

### Many speculative claims

If most claims in a dossier are marked speculative, the LLM may not be citing properly. This can happen with:
- Smaller local models that don't follow citation instructions well
- Genes with very little published literature

Try a larger model (e.g., `llama3.1:70b` in Ollama, or a cloud provider) for better citation compliance.

### Port already in use

If `python launch.py` fails because port 8000 or 5173 is busy, the launcher will try to free it automatically. If that doesn't work:

```bash
# macOS/Linux
lsof -ti :8000 | xargs kill
lsof -ti :5173 | xargs kill
python launch.py
```
