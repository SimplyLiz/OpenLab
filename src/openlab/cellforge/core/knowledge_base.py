"""Knowledge base models (PRD §4.4)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Gene(BaseModel):
    """A gene in the knowledge base."""

    id: str
    name: str = ""
    locus_tag: str = ""
    start: int = 0
    end: int = 0
    strand: int = 1
    product: str = ""
    sequence: str = ""
    function: str = ""
    ec_numbers: list[str] = Field(default_factory=list)
    go_terms: list[str] = Field(default_factory=list)
    cog_category: str = ""
    essential: bool | None = None


class Protein(BaseModel):
    """A protein in the knowledge base."""

    id: str
    name: str = ""
    gene_id: str = ""
    sequence: str = ""
    molecular_weight: float = 0.0
    half_life: float = 0.0
    copy_number: int = 0
    compartment: str = "cytoplasm"
    is_enzyme: bool = False
    catalyzes: list[str] = Field(default_factory=list)


class Metabolite(BaseModel):
    """A metabolite in the knowledge base."""

    id: str
    name: str = ""
    formula: str = ""
    charge: int = 0
    compartment: str = "cytoplasm"
    concentration: float = 0.0
    kegg_id: str = ""
    bigg_id: str = ""


class Reaction(BaseModel):
    """A metabolic reaction in the knowledge base."""

    id: str
    name: str = ""
    equation: str = ""
    reactants: dict[str, float] = Field(default_factory=dict)
    products: dict[str, float] = Field(default_factory=dict)
    lower_bound: float = -1000.0
    upper_bound: float = 1000.0
    gene_reaction_rule: str = ""
    ec_number: str = ""
    subsystem: str = ""
    reversible: bool = True
    delta_g: float | None = None


class TranscriptionUnit(BaseModel):
    """A transcription unit (operon) in the knowledge base."""

    id: str
    name: str = ""
    gene_ids: list[str] = Field(default_factory=list)
    promoter_start: int = 0
    promoter_end: int = 0
    sigma_factor: str = ""
    transcription_rate: float = 0.0


class KnowledgeBase(BaseModel):
    """Structured knowledge base for a whole-cell model (PRD §4.4).

    Contains all genes, proteins, metabolites, reactions, and
    transcription units needed to parameterize the simulation.
    """

    organism: str = "unknown"
    genome_length: int = 0
    gc_content: float = 0.0
    genes: list[Gene] = Field(default_factory=list)
    proteins: list[Protein] = Field(default_factory=list)
    metabolites: list[Metabolite] = Field(default_factory=list)
    reactions: list[Reaction] = Field(default_factory=list)
    transcription_units: list[TranscriptionUnit] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_cobra_model(self) -> Any:
        """Convert metabolic network to a COBRApy Model.

        Returns:
            cobra.Model instance.
        """
        raise NotImplementedError("to_cobra_model not yet implemented")

    def summary(self) -> dict[str, Any]:
        """Return a summary of the knowledge base contents.

        Returns:
            Dictionary with counts of genes, proteins, metabolites, etc.
        """
        return {
            "organism": self.organism,
            "genome_length": self.genome_length,
            "gc_content": self.gc_content,
            "num_genes": len(self.genes),
            "num_proteins": len(self.proteins),
            "num_metabolites": len(self.metabolites),
            "num_reactions": len(self.reactions),
            "num_transcription_units": len(self.transcription_units),
        }
