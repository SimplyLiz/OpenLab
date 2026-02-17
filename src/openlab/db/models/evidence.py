import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite in tests)
JSONPayload = JSON().with_variant(JSONB, "postgresql")

from openlab.db.models.base import Base, TimestampMixin


class EvidenceType(str, enum.Enum):
    HOMOLOGY = "HOMOLOGY"
    STRUCTURE = "STRUCTURE"
    EXPRESSION = "EXPRESSION"
    GROWTH_CURVE = "GROWTH_CURVE"
    TRANSPOSON = "TRANSPOSON"
    PROTEOMICS = "PROTEOMICS"
    LITERATURE = "LITERATURE"
    COMPUTATIONAL = "COMPUTATIONAL"
    SIMULATION = "SIMULATION"


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.gene_id"), index=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType))
    payload: Mapped[dict] = mapped_column(JSONPayload, default=dict)
    source_ref: Mapped[Optional[str]] = mapped_column(String(500))
    confidence: Mapped[Optional[float]]
    quality_score: Mapped[Optional[float]]
    notes: Mapped[Optional[str]] = mapped_column(Text)

    gene: Mapped["Gene"] = relationship(back_populates="evidence")  # noqa: F821
    hypothesis_links: Mapped[list["HypothesisEvidence"]] = relationship(  # noqa: F821
        back_populates="evidence"
    )

    def __repr__(self) -> str:
        return f"<Evidence {self.evidence_type.value} gene={self.gene_id}>"
