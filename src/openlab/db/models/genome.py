"""Genome model — top-level entity that groups genes."""

from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openlab.db.models.base import Base, TimestampMixin


class Genome(TimestampMixin, Base):
    __tablename__ = "genomes"

    genome_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    accession: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    organism: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    genome_length: Mapped[int] = mapped_column(Integer)
    is_circular: Mapped[bool] = mapped_column(Boolean, default=False)
    gc_content: Mapped[Optional[float]] = mapped_column(Float)

    genes: Mapped[list["Gene"]] = relationship(  # noqa: F821
        back_populates="genome", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Genome {self.accession} ({self.organism})>"
