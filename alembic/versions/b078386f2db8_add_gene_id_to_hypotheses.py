"""add_gene_id_to_hypotheses

Revision ID: b078386f2db8
Revises: 
Create Date: 2026-02-07 16:49:51.709918
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b078386f2db8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hypotheses",
        sa.Column("gene_id", sa.Integer(), sa.ForeignKey("genes.gene_id"), nullable=True),
    )
    op.create_index("ix_hypotheses_gene_id", "hypotheses", ["gene_id"])


def downgrade() -> None:
    op.drop_index("ix_hypotheses_gene_id", table_name="hypotheses")
    op.drop_column("hypotheses", "gene_id")
