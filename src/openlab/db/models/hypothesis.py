import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openlab.db.models.base import Base, TimestampMixin


class HypothesisScope(str, enum.Enum):
    GENE = "GENE"
    PATHWAY = "PATHWAY"
    SYSTEM = "SYSTEM"


class HypothesisStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"


class EvidenceDirection(str, enum.Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class Hypothesis(TimestampMixin, Base):
    __tablename__ = "hypotheses"

    hypothesis_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[Optional[str]] = mapped_column(Text)
    scope: Mapped[HypothesisScope] = mapped_column(Enum(HypothesisScope))
    status: Mapped[HypothesisStatus] = mapped_column(
        Enum(HypothesisStatus), default=HypothesisStatus.DRAFT
    )
    confidence_score: Mapped[Optional[float]]
    convergence_score: Mapped[Optional[float]]
    gene_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("genes.gene_id"), index=True, nullable=True
    )

    gene: Mapped[Optional["Gene"]] = relationship(  # noqa: F821
        back_populates="hypotheses", foreign_keys=[gene_id]
    )
    evidence_links: Mapped[list["HypothesisEvidence"]] = relationship(
        back_populates="hypothesis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hypothesis {self.title!r} [{self.status.value}]>"


class HypothesisEvidence(Base):
    __tablename__ = "hypothesis_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[int] = mapped_column(
        ForeignKey("hypotheses.hypothesis_id")
    )
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.evidence_id"))
    direction: Mapped[EvidenceDirection] = mapped_column(Enum(EvidenceDirection))
    weight: Mapped[float] = mapped_column(default=1.0)

    hypothesis: Mapped["Hypothesis"] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship(  # noqa: F821
        back_populates="hypothesis_links"
    )

    def __repr__(self) -> str:
        return f"<HypothesisEvidence h={self.hypothesis_id} e={self.evidence_id}>"
