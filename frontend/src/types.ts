// Mirrors backend models

export interface GeneIdentifiers {
  symbol: string;
  name: string;
  ncbi_gene_id: string;
  refseq_mrna: string;
  refseq_protein: string;
  ensembl_gene: string;
  ensembl_transcript: string;
  uniprot_id: string;
  hgnc_id: string;
  organism: string;
  chromosome: string;
  map_location: string;
}

export interface Sequence {
  accession: string;
  seq_type: string;
  sequence: string;
  length: number;
}

export interface GeneRecord {
  identifiers: GeneIdentifiers;
  sequences: Sequence[];
  summary: string;
  aliases: string[];
}

export interface ORF {
  start: number;
  end: number;
  frame: number;
  length_aa: number;
  start_codon: string;
}

export interface GCProfile {
  overall: number;
  window_size: number;
  profile: number[];
}

export interface CpGIsland {
  start: number;
  end: number;
  length: number;
  gc_percent: number;
  obs_exp_ratio: number;
}

export interface CodonUsage {
  codon: string;
  amino_acid: string;
  count: number;
  frequency: number;
  rscu: number;
}

export interface SequenceAnalysisResult {
  orfs: ORF[];
  primary_orf: ORF | null;
  codon_usage: CodonUsage[];
  cai: number;
  gc_profile: GCProfile;
  cpg_islands: CpGIsland[];
  splice_sites: { position: number; site_type: string; sequence: string; score: number }[];
  seq_length: number;
  exon_count: number;
}

export interface GOTerm {
  go_id: string;
  name: string;
  category: string;
  evidence: string;
}

export interface DiseaseAssociation {
  disease: string;
  source: string;
  relationship: string;
  mim_id: string;
}

export interface Pathway {
  pathway_id: string;
  name: string;
  source: string;
  url: string;
}

export interface AnnotationResult {
  go_terms: GOTerm[];
  diseases: DiseaseAssociation[];
  pathways: Pathway[];
  drugs: { drug_name: string; drug_id: string; action: string; status: string }[];
  pubmed_count: number;
  top_pubmed_ids: string[];
  function_summary: string;
}

// ---------------------------------------------------------------------------
// Genome-level models (synthetic organisms)
// ---------------------------------------------------------------------------

export type FunctionalCategory =
  | "gene_expression"
  | "cell_membrane"
  | "metabolism"
  | "genome_preservation"
  | "predicted"
  | "unknown";

export type PredictionSource = "genbank" | "dnasyn" | "curated" | "genelife" | "";

export interface GenomeGene {
  locus_tag: string;
  product: string;
  gene_name: string;
  start: number;
  end: number;
  strand: number;
  dna_sequence: string;
  protein_sequence: string;
  protein_length: number;
  functional_category: FunctionalCategory;
  is_hypothetical: boolean;
  is_essential: boolean;
  color: string;
  prediction_source: PredictionSource;
}

export interface GenomeRecord {
  accession: string;
  organism: string;
  description: string;
  genome_length: number;
  is_circular: boolean;
  gc_content: number;
  genes: GenomeGene[];
  total_genes: number;
  genes_known: number;
  genes_predicted: number;
  genes_unknown: number;
}

export interface GenomeSummary {
  genome_id: number;
  accession: string;
  organism: string;
  genome_length: number;
  gc_content: number | null;
  is_circular: boolean;
  total_genes: number;
  genes_known: number;
  genes_unknown: number;
  description: string | null;
}

export interface KnockoutRequest {
  genome_id: number;
  knockouts: string[];
  cellspec: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Evidence & Hypothesis (DNASyn integration)
// ---------------------------------------------------------------------------

export interface EvidenceRecord {
  source: string;
  payload: Record<string, unknown>;
  confidence: number;
  go_terms: string[];
  ec_numbers: string[];
  categories: string[];
  keywords: string[];
}

export interface ConvergenceResult {
  score: number;
  confidence_tier: number;
  n_evidence_sources: number;
  bootstrap_stable: boolean | null;
}

export interface Hypothesis {
  predicted_function: string;
  raw_response: string;
  confidence_score: number;
  suggested_category: string;
}

export interface FunctionalPrediction {
  locus_tag: string;
  confidence: string;
  predicted_function: string;
  prediction_source: PredictionSource;
  evidence_summary: string[];
  protein_features: {
    molecular_weight: number;
    isoelectric_point: number;
    hydrophobicity: number;
    has_transmembrane: boolean;
    transmembrane_count: number;
    is_secreted: boolean;
    charged_residues_pct: number;
    disorder_pct: number;
  };
  suggested_category: FunctionalCategory;
  evidence: EvidenceRecord[];
  convergence: ConvergenceResult;
  hypothesis: Hypothesis | null;
}

export interface GenomeFunctionalAnalysis {
  total_analyzed: number;
  predictions: FunctionalPrediction[];
  category_summary: Record<string, number>;
  mean_convergence: number;
  genes_with_hypothesis: number;
}

export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface PipelineEvent {
  stage: string;
  status: StageStatus;
  data: Record<string, unknown> | null;
  error: string | null;
  progress: number;
}

// ---------------------------------------------------------------------------
// DNAView Integration: Simulation + Validation
// ---------------------------------------------------------------------------

export interface EssentialityResult {
  total_essential: number;
  total_nonessential: number;
  predictions: Record<string, boolean>;
}

export interface KineticsEntry {
  reaction_id: string;
  gene_locus_tag?: string;
  ec_number: string;
  kcat: { value: number; provenance: { trust_level: string; source: string } };
  km: Record<string, { value: number }>;
  source: string;
  trust_level: string;
}

export interface KineticsResult {
  coverage_report: Record<string, { count: number; pct: number }>;
  total_reactions: number;
  kinetics: KineticsEntry[];
}

export interface CellSpecSimParams {
  metabolism_dt: number;
  expression_dt: number;
  total_duration: number;
  temperature: number;
  ph: number;
  initial_volume: number;
}

export interface CellSpec {
  organism: string;
  version: string;
  genes: { locus_tag: string; gene_name: string; is_essential: boolean; expression_rate: number }[];
  reactions: { id: string; name: string; ec_number: string; gene_locus_tags: string[] }[];
  metabolites: { id: string; name: string; initial_concentration: number }[];
  simulation_parameters: CellSpecSimParams;
  provenance_summary: Record<string, number>;
}

export interface SimulationSnapshot {
  time: number;
  volume: number;
  dry_mass: number;
  growth_rate: number;
  division_count: number;
  total_protein: number;
  total_mrna: number;
  atp: number;
  gtp: number;
  glucose: number;
  aa_pool: number;
}

export interface SimulationResult {
  summary: Record<string, unknown>;
  time_series: SimulationSnapshot[];
  total_divisions: number;
  doubling_time: number | null;
}

export interface ValidationCheck {
  name: string;
  passed: boolean;
  expected: string;
  actual: string;
  score: number;
}

export interface ValidationResult {
  checks: ValidationCheck[];
  overall_score: number;
  mcc: number | null;
  doubling_time_hours: number | null;
}

// ---------------------------------------------------------------------------
// Research Cycle (DB-backed state)
// ---------------------------------------------------------------------------

export interface DBEvidence {
  evidence_id: number;
  evidence_type: string;
  payload: Record<string, unknown>;
  source_ref: string;
  confidence: number | null;
  quality_score: number | null;
}

export interface DBHypothesis {
  hypothesis_id: number;
  title: string;
  description: string | null;
  scope: string;
  status: "DRAFT" | "TESTING" | "SUPPORTED" | "REJECTED";
  confidence_score: number | null;
  convergence_score: number | null;
  gene_id: number | null;
  evidence_links: { evidence_id: number; direction: string; weight: number }[];
}

export interface ResearchStatus {
  gene_id: number;
  locus_tag: string;
  stored: boolean;
  evidence: DBEvidence[];
  hypothesis: DBHypothesis | null;
  convergence_score: number;
  tier: number;
  graduated: boolean;
  proposed_function: string | null;
  disagreement_count: number;
}

export interface ResearchSummary {
  total_stored: number;
  total_with_evidence: number;
  total_with_hypothesis: number;
  total_graduated: number;
  total_unknown: number;
  needs_review: { locus_tag: string; product: string; hypothesis_title: string; confidence: number }[];
  graduation_candidates: { locus_tag: string; product: string; hypothesis_title: string; confidence: number; proposed_function: string }[];
  disagreements: { locus_tag: string; convergence_score: number; disagreement_count: number; top_disagreement: string }[];
}
