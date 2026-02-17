"""Pydantic request/response schemas for API v1."""

from datetime import datetime

from pydantic import BaseModel, Field

from openlab.db.models.evidence import EvidenceType
from openlab.db.models.hypothesis import EvidenceDirection, HypothesisScope, HypothesisStatus


# --- Gene schemas ---

class GeneBase(BaseModel):
    locus_tag: str
    name: str | None = None
    product: str | None = None
    length: int
    strand: int
    start: int
    end: int
    essentiality: str | None = None
    proposed_function: str | None = None
    graduated_at: datetime | None = None


class GeneListItem(GeneBase):
    gene_id: int

    model_config = {"from_attributes": True}


class ProteinFeatureOut(BaseModel):
    feature_id: int
    feature_type: str
    start: int
    end: int
    score: float | None = None
    source: str
    source_version: str | None = None

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    evidence_id: int
    evidence_type: EvidenceType
    payload: dict
    source_ref: str | None = None
    confidence: float | None = None
    quality_score: float | None = None

    model_config = {"from_attributes": True}


class GeneDetail(GeneBase):
    gene_id: int
    sequence: str
    protein_sequence: str | None = None
    notes: str | None = None
    features: list[ProteinFeatureOut] = []
    evidence: list[EvidenceOut] = []

    model_config = {"from_attributes": True}


class GeneDossier(BaseModel):
    gene_id: int
    locus_tag: str
    name: str | None = None
    product: str | None = None
    essentiality: str | None = None
    proposed_function: str | None = None
    graduated_at: datetime | None = None
    graduation_hypothesis_id: int | None = None
    evidence_count: int
    evidence_by_type: dict[str, list]
    features: list[dict]


class GraduateRequest(BaseModel):
    proposed_function: str = Field(max_length=500)
    hypothesis_id: int | None = None


# --- Evidence schemas ---

class EvidenceCreate(BaseModel):
    gene_id: int
    evidence_type: EvidenceType
    payload: dict = Field(default_factory=dict)
    source_ref: str | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    quality_score: float | None = Field(None, ge=0, le=1)
    notes: str | None = None


class EvidenceCreated(EvidenceOut):
    gene_id: int
    notes: str | None = None


# --- Import schemas ---

class ImportResult(BaseModel):
    file: str
    accession: str | None = None
    organism: str | None = None
    total_features: int | None = None
    total_entries: int | None = None
    imported: int
    skipped: int
    unknown_function: int | None = None


# --- Hypothesis schemas ---

class HypothesisEvidenceLinkOut(BaseModel):
    evidence_id: int
    direction: str
    weight: float

    model_config = {"from_attributes": True}


class HypothesisListItem(BaseModel):
    hypothesis_id: int
    title: str
    scope: HypothesisScope
    status: HypothesisStatus
    confidence_score: float | None = None
    convergence_score: float | None = None
    gene_id: int | None = None

    model_config = {"from_attributes": True}


class HypothesisDetail(HypothesisListItem):
    description: str | None = None
    evidence_links: list[HypothesisEvidenceLinkOut] = []

    model_config = {"from_attributes": True}


class HypothesisCreate(BaseModel):
    title: str = Field(max_length=300)
    description: str | None = None
    scope: HypothesisScope = HypothesisScope.GENE
    gene_id: int | None = None


class HypothesisUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: HypothesisStatus | None = None


class EvidenceLinkCreate(BaseModel):
    evidence_id: int
    direction: EvidenceDirection
    weight: float = Field(default=1.0, ge=0, le=5)


class ScoreOut(BaseModel):
    hypothesis_id: int
    confidence_score: float


class ConvergenceResponse(BaseModel):
    gene_id: int
    convergence_score: float
    evidence_count: int
    disagreement_count: int = 0


class DisagreementPairOut(BaseModel):
    evidence_id_a: int
    evidence_id_b: int
    source_a: str
    source_b: str
    evidence_type_a: str
    evidence_type_b: str
    agreement_score: float
    categories_a: list[str] = []
    categories_b: list[str] = []


class DisagreementResponse(BaseModel):
    gene_id: int
    convergence_score: float
    total_pairs: int
    disagreeing_pairs: list[DisagreementPairOut] = []


# --- Research cycle schemas ---

class ResearchStatus(BaseModel):
    gene_id: int
    locus_tag: str
    stored: bool
    evidence: list[EvidenceOut] = []
    hypothesis: HypothesisDetail | None = None
    convergence_score: float = 0.0
    tier: int = 3
    graduated: bool = False
    proposed_function: str | None = None
    disagreement_count: int = 0


class ApproveRequest(BaseModel):
    proposed_function: str | None = None


class CorrectRequest(BaseModel):
    corrected_function: str = Field(max_length=500)


class ResearchSummary(BaseModel):
    total_stored: int = 0
    total_with_evidence: int = 0
    total_with_hypothesis: int = 0
    total_graduated: int = 0
    total_unknown: int = 0
    needs_review: list[dict] = []
    graduation_candidates: list[dict] = []
    disagreements: list[dict] = []


# --- Genome hydration schemas ---

class GenomeStatusResponse(BaseModel):
    has_genome: bool
    gene_count: int = 0


class ResearchQueueItem(BaseModel):
    locus_tag: str
    gene_name: str | None = None
    product: str | None = None
    protein_sequence: str | None = None
    priority: int = 0


# --- Usage schemas ---

class UsageGeneBreakdown(BaseModel):
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class UsageSessionResponse(BaseModel):
    total_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_gene: dict[str, UsageGeneBreakdown] = {}


class UsageTotalResponse(BaseModel):
    total_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class UsageLogEntry(BaseModel):
    provider: str
    model: str
    purpose: str
    gene_locus_tag: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    duration_ms: int = 0
    success: bool = True
    error_message: str | None = None
    created_at: str | None = None
