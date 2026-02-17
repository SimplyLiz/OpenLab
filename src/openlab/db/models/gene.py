from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openlab.db.models.base import Base, TimestampMixin


class Gene(TimestampMixin, Base):
    __tablename__ = "genes"

    gene_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locus_tag: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    sequence: Mapped[str] = mapped_column(Text)
    protein_sequence: Mapped[Optional[str]] = mapped_column(Text)
    length: Mapped[int]
    strand: Mapped[int]
    start: Mapped[int]
    end: Mapped[int]
    product: Mapped[Optional[str]] = mapped_column(String(500))
    essentiality: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Foreign key to genome
    genome_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("genomes.genome_id"), index=True
    )

    # Graduation: inferred function (keeps GenBank `product` untouched)
    proposed_function: Mapped[Optional[str]] = mapped_column(String(500))
    graduated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True
    )
    graduation_hypothesis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "hypotheses.hypothesis_id",
            ondelete="SET NULL",
            use_alter=True,
        )
    )

    graduation_hypothesis: Mapped[Optional["Hypothesis"]] = relationship(  # noqa: F821
        foreign_keys=[graduation_hypothesis_id],
    )
    genome: Mapped[Optional["Genome"]] = relationship(  # noqa: F821
        back_populates="genes",
    )

    features: Mapped[list["ProteinFeature"]] = relationship(
        back_populates="gene", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="gene", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list["Hypothesis"]] = relationship(  # noqa: F821
        back_populates="gene",
        foreign_keys="[Hypothesis.gene_id]",
    )

    def __repr__(self) -> str:
        return f"<Gene {self.locus_tag} ({self.name or 'unknown'})>"


class ProteinFeature(Base):
    __tablename__ = "protein_features"

    feature_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.gene_id"))
    feature_type: Mapped[str] = mapped_column(String(100))
    start: Mapped[int]
    end: Mapped[int]
    score: Mapped[Optional[float]]
    source: Mapped[str] = mapped_column(String(100))
    source_version: Mapped[Optional[str]] = mapped_column(String(50))

    gene: Mapped["Gene"] = relationship(back_populates="features")

    def __repr__(self) -> str:
        return f"<ProteinFeature {self.feature_type} {self.start}-{self.end}>"
