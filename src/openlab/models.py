"""Core data models for the GeneLife analysis pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class InputType(str, Enum):
    SYMBOL = "symbol"          # e.g. "TP53"
    NCBI_ACCESSION = "ncbi"    # e.g. "NM_000546.6"
    ENSEMBL_ID = "ensembl"     # e.g. "ENSG00000141510"
    UNIPROT_ID = "uniprot"     # e.g. "P04637"
    FASTA = "fasta"            # raw sequence
    GENBANK_GENOME = "genbank" # e.g. "CP014992.1" (whole genome)
    SYNTHETIC = "synthetic"    # e.g. "JCVI-syn3.0" (named synthetic organisms)


class GeneInput(BaseModel):
    query: str
    input_type: InputType | None = None  # auto-detected if None


# ---------------------------------------------------------------------------
# Gene Record (output of Ingest stage)
# ---------------------------------------------------------------------------

class GeneIdentifiers(BaseModel):
    symbol: str = ""
    name: str = ""               # full name, e.g. "tumor protein p53"
    ncbi_gene_id: str = ""       # e.g. "7157"
    refseq_mrna: str = ""        # e.g. "NM_000546.6"
    refseq_protein: str = ""     # e.g. "NP_000537.3"
    ensembl_gene: str = ""       # e.g. "ENSG00000141510"
    ensembl_transcript: str = ""
    uniprot_id: str = ""         # e.g. "P04637"
    hgnc_id: str = ""
    organism: str = "Homo sapiens"
    chromosome: str = ""
    map_location: str = ""


class Sequence(BaseModel):
    accession: str = ""
    seq_type: str = ""           # "genomic", "mrna", "cds", "protein"
    sequence: str = ""
    length: int = 0


class GeneRecord(BaseModel):
    identifiers: GeneIdentifiers = GeneIdentifiers()
    sequences: list[Sequence] = Field(default_factory=list)
    summary: str = ""
    aliases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sequence Analysis (output of Stage 2)
# ---------------------------------------------------------------------------

class ORF(BaseModel):
    start: int
    end: int
    frame: int             # 0, 1, or 2
    length_aa: int
    start_codon: str = "ATG"


class CodonUsage(BaseModel):
    codon: str
    amino_acid: str
    count: int
    frequency: float       # per thousand
    rscu: float = 0.0      # relative synonymous codon usage


class GCProfile(BaseModel):
    overall: float
    window_size: int = 100
    profile: list[float] = Field(default_factory=list)  # GC% per window


class CpGIsland(BaseModel):
    start: int
    end: int
    length: int
    gc_percent: float
    obs_exp_ratio: float   # observed/expected CpG ratio


class SpliceSite(BaseModel):
    position: int
    site_type: str         # "donor" or "acceptor"
    sequence: str          # flanking dinucleotide + context
    score: float = 0.0


class SequenceAnalysisResult(BaseModel):
    orfs: list[ORF] = Field(default_factory=list)
    primary_orf: ORF | None = None
    codon_usage: list[CodonUsage] = Field(default_factory=list)
    cai: float = 0.0                          # Codon Adaptation Index
    gc_profile: GCProfile = GCProfile(overall=0.0)
    cpg_islands: list[CpGIsland] = Field(default_factory=list)
    splice_sites: list[SpliceSite] = Field(default_factory=list)
    seq_length: int = 0
    exon_count: int = 0


# ---------------------------------------------------------------------------
# Annotation (output of Stage 3)
# ---------------------------------------------------------------------------

class GOTerm(BaseModel):
    go_id: str
    name: str
    category: str          # "molecular_function", "biological_process", "cellular_component"
    evidence: str = ""


class DiseaseAssociation(BaseModel):
    disease: str
    source: str            # "OMIM", "ClinVar", etc.
    relationship: str = "" # "causal", "risk factor", etc.
    mim_id: str = ""


class Pathway(BaseModel):
    pathway_id: str
    name: str
    source: str            # "KEGG", "Reactome"
    url: str = ""


class DrugTarget(BaseModel):
    drug_name: str
    drug_id: str = ""
    action: str = ""       # "inhibitor", "activator", etc.
    status: str = ""       # "approved", "investigational"


class AnnotationResult(BaseModel):
    go_terms: list[GOTerm] = Field(default_factory=list)
    diseases: list[DiseaseAssociation] = Field(default_factory=list)
    pathways: list[Pathway] = Field(default_factory=list)
    drugs: list[DrugTarget] = Field(default_factory=list)
    pubmed_count: int = 0
    top_pubmed_ids: list[str] = Field(default_factory=list)
    function_summary: str = ""


# ---------------------------------------------------------------------------
# Genome-level models (for whole synthetic genomes)
# ---------------------------------------------------------------------------

class FunctionalCategory(str, Enum):
    GENE_EXPRESSION = "gene_expression"         # transcription, translation
    CELL_MEMBRANE = "cell_membrane"             # membrane structure & function
    METABOLISM = "metabolism"                     # cytosolic metabolism
    GENOME_PRESERVATION = "genome_preservation"  # DNA replication, repair
    PREDICTED = "predicted"                      # function predicted but unconfirmed
    UNKNOWN = "unknown"                          # no known function


class GenomeGene(BaseModel):
    """A single gene within a genome."""
    locus_tag: str                         # e.g. "MMSYN1_0001" or "JCVISYN3A_0001"
    product: str = ""                      # annotated product name
    gene_name: str = ""                    # gene symbol if known (e.g. "dnaA")
    start: int = 0                         # genomic position
    end: int = 0
    strand: int = 1                        # 1 or -1
    dna_sequence: str = ""
    protein_sequence: str = ""
    protein_length: int = 0
    functional_category: FunctionalCategory = FunctionalCategory.UNKNOWN
    is_hypothetical: bool = False          # annotated as "hypothetical protein"
    is_essential: bool = True              # assumed essential until proven otherwise
    color: str = "#888888"                 # for visualization
    # Where the annotation comes from:
    #   "genbank"  — original GenBank/NCBI annotation
    #   "dnasyn"   — DNASyn evidence pipeline (computational)
    #   "curated"  — expert-curated from published research
    #   "genelife" — GeneLife's live analysis pipeline
    #   ""         — unknown / not yet classified
    prediction_source: str = ""


class GenomeRecord(BaseModel):
    """A complete genome (e.g. JCVI-syn3.0)."""
    accession: str = ""
    organism: str = ""
    description: str = ""
    genome_length: int = 0
    is_circular: bool = True
    gc_content: float = 0.0
    genes: list[GenomeGene] = Field(default_factory=list)
    total_genes: int = 0
    genes_known: int = 0
    genes_predicted: int = 0
    genes_unknown: int = 0


# ---------------------------------------------------------------------------
# Functional Prediction (mystery gene analysis)
# ---------------------------------------------------------------------------

class DomainHit(BaseModel):
    """A conserved domain found in a protein."""
    domain_id: str             # e.g. "cd00001" or "pfam00001"
    name: str
    description: str = ""
    evalue: float = 0.0
    score: float = 0.0
    start: int = 0
    end: int = 0


class BlastHit(BaseModel):
    """A BLAST homology hit."""
    accession: str
    description: str
    organism: str = ""
    identity: float = 0.0     # percent identity
    coverage: float = 0.0     # query coverage
    evalue: float = 0.0
    score: float = 0.0


class ProteinFeatures(BaseModel):
    """Predicted features of a protein."""
    molecular_weight: float = 0.0
    isoelectric_point: float = 0.0
    hydrophobicity: float = 0.0      # GRAVY score
    has_signal_peptide: bool = False
    has_transmembrane: bool = False
    transmembrane_count: int = 0
    is_secreted: bool = False
    charged_residues_pct: float = 0.0
    disorder_pct: float = 0.0


class EvidenceRecord(BaseModel):
    """A single piece of evidence collected from an external source."""
    source: str                          # "cdd", "blast", "interpro", "string", "uniprot", "literature", "protein_features"
    payload: dict = Field(default_factory=dict)  # raw evidence data
    confidence: float = 0.0

    # Normalized fields (filled after normalization)
    go_terms: list[str] = Field(default_factory=list)
    ec_numbers: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """LLM-synthesized hypothesis about a gene's function."""
    predicted_function: str = ""
    raw_response: str = ""
    confidence_score: float = 0.0        # 0.0-1.0
    suggested_category: str = ""


class ConvergenceResult(BaseModel):
    """Convergence scoring result for a gene."""
    score: float = 0.0                   # 0.0-1.0
    confidence_tier: int = 3             # 1=High, 2=Moderate, 3=Low, 4=Flagged
    n_evidence_sources: int = 0
    bootstrap_stable: bool | None = None


class FunctionalPrediction(BaseModel):
    """Predicted function for a mystery gene — now with full evidence chain."""
    locus_tag: str
    confidence: str = "none"    # "high", "medium", "low", "none"
    predicted_function: str = ""
    prediction_source: str = ""  # "genbank", "dnasyn", "curated", "genelife"
    evidence_summary: list[str] = Field(default_factory=list)  # human-readable reasoning chain
    blast_hits: list[BlastHit] = Field(default_factory=list)
    domain_hits: list[DomainHit] = Field(default_factory=list)
    protein_features: ProteinFeatures = ProteinFeatures()
    suggested_category: FunctionalCategory = FunctionalCategory.UNKNOWN

    # New: DNASyn-style evidence + convergence
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    convergence: ConvergenceResult = ConvergenceResult()
    hypothesis: Hypothesis | None = None


class GenomeFunctionalAnalysis(BaseModel):
    """Analysis of all mystery genes in a genome."""
    total_analyzed: int = 0
    predictions: list[FunctionalPrediction] = Field(default_factory=list)
    category_summary: dict[str, int] = Field(default_factory=dict)
    mean_convergence: float = 0.0
    genes_with_hypothesis: int = 0


# ---------------------------------------------------------------------------
# Pipeline Events (WebSocket messages)
# ---------------------------------------------------------------------------

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineEvent(BaseModel):
    stage: str
    status: StageStatus
    data: dict | None = None
    error: str | None = None
    progress: float = 0.0  # 0.0 – 1.0


# ---------------------------------------------------------------------------
# DNAView Integration: Kinetics, CellSpec, Simulation
# ---------------------------------------------------------------------------

class TrustLevel(str, Enum):
    MEASURED = "measured"
    MEASURED_HOMOLOG = "measuredHomolog"
    COMPUTED = "computed"
    ESTIMATED = "estimated"
    PREDICTED = "predicted"
    ASSUMED = "assumed"


class Provenance(BaseModel):
    trust_level: TrustLevel = TrustLevel.ASSUMED
    source: str = ""
    source_id: str = ""
    retrieved_at: str = ""
    notes: str = ""


class ProvenancedValue(BaseModel):
    value: float = 0.0
    lower_bound: float | None = None
    upper_bound: float | None = None
    cv: float = 0.0  # coefficient of variation
    provenance: Provenance = Provenance()


class KineticsEntry(BaseModel):
    reaction_id: str = ""
    ec_number: str = ""
    kcat: ProvenancedValue = ProvenancedValue()
    km: dict[str, ProvenancedValue] = Field(default_factory=dict)
    ki: dict[str, ProvenancedValue] = Field(default_factory=dict)
    delta_g: ProvenancedValue | None = None
    reversible: bool = False


class ReactionParticipant(BaseModel):
    metabolite_id: str
    coefficient: float = 1.0


class CellSpecReaction(BaseModel):
    id: str
    name: str = ""
    ec_number: str = ""
    kegg_id: str = ""
    gene_locus_tags: list[str] = Field(default_factory=list)
    substrates: list[ReactionParticipant] = Field(default_factory=list)
    products: list[ReactionParticipant] = Field(default_factory=list)
    kinetics: KineticsEntry = KineticsEntry()
    subsystem: str = ""
    provenance: Provenance = Provenance()


class CellSpecMetabolite(BaseModel):
    id: str
    name: str = ""
    kegg_id: str = ""
    formula: str = ""
    charge: int = 0
    compartment: str = "cytoplasm"
    initial_concentration: float = 1.0  # mM


class CellSpecGene(BaseModel):
    locus_tag: str
    gene_name: str = ""
    start: int = 0
    end: int = 0
    strand: int = 1
    dna_sequence: str = ""
    aa_sequence: str = ""
    classification: str = "unknown"
    product: str = ""
    ec_number: str = ""
    is_essential: bool = True
    expression_rate: float = 1.0
    predicted_function: str = ""
    confidence_score: float = 0.0
    convergence_score: float = 0.0
    provenance: Provenance = Provenance()


class SimulationParameters(BaseModel):
    metabolism_dt: float = 0.5       # seconds
    expression_dt: float = 60.0     # seconds
    total_duration: float = 72000.0  # seconds (20 hours)
    temperature: float = 310.0      # Kelvin
    ph: float = 7.5
    initial_volume: float = 0.05    # femtoliters
    stochastic: bool = False
    seed: int = 42
    mutation_rate: float = 1e-4     # per gene per division
    population_size: int = 1        # 1 = single-cell, >1 = population
    grid_size: int = 8
    nutrient_diffusion_rate: float = 0.1


class CellSpec(BaseModel):
    organism: str = ""
    version: str = "1.0"
    created_at: str = ""
    genes: list[CellSpecGene] = Field(default_factory=list)
    reactions: list[CellSpecReaction] = Field(default_factory=list)
    metabolites: list[CellSpecMetabolite] = Field(default_factory=list)
    stoichiometric_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    simulation_parameters: SimulationParameters = SimulationParameters()
    provenance_summary: dict[str, int] = Field(default_factory=dict)


class SimulationSnapshot(BaseModel):
    time: float = 0.0
    volume: float = 0.0
    dry_mass: float = 0.0
    growth_rate: float = 0.0
    division_count: int = 0
    total_protein: float = 0.0
    total_mrna: float = 0.0
    atp: float = 0.0
    gtp: float = 0.0
    glucose: float = 0.0
    aa_pool: float = 0.0
    cell_id: int = 0
    generation: int = 0
    mutation_count: int = 0
    fitness: float = 0.0


class SimulationResult(BaseModel):
    metadata: dict = Field(default_factory=dict)
    time_series: list[SimulationSnapshot] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class CellSnapshotData(BaseModel):
    cell_id: int = 0
    row: int = 0
    col: int = 0
    generation: int = 0
    volume: float = 0.0
    growth_rate: float = 0.0
    mutation_count: int = 0
    fitness: float = 0.0


class PopulationSnapshot(BaseModel):
    time: float = 0.0
    total_cells: int = 0
    grid_size: int = 8
    cells: list[CellSnapshotData] = Field(default_factory=list)
    nutrient_field: list[list[float]] = Field(default_factory=list)
    mean_fitness: float = 0.0
    total_mutations: int = 0
    generations_max: int = 0


class ValidationCheck(BaseModel):
    name: str
    passed: bool = False
    expected: str = ""
    actual: str = ""
    score: float = 0.0


class ValidationResult(BaseModel):
    checks: list[ValidationCheck] = Field(default_factory=list)
    overall_score: float = 0.0
    mcc: float | None = None
    doubling_time_hours: float | None = None
