"""add_genomes_table

Revision ID: d5a1f3e89b02
Revises: c4b2e8f73a19
Create Date: 2026-02-15 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a1f3e89b02'
down_revision: Union[str, None] = 'c4b2e8f73a19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create genomes table
    op.create_table(
        'genomes',
        sa.Column('genome_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('accession', sa.String(length=50), nullable=False),
        sa.Column('organism', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('genome_length', sa.Integer(), nullable=False),
        sa.Column('is_circular', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('gc_content', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('genome_id', name=op.f('pk_genomes')),
        sa.UniqueConstraint('accession', name=op.f('uq_genomes_accession')),
    )
    op.create_index(op.f('ix_genomes_accession'), 'genomes', ['accession'], unique=True)

    # 2. Add nullable genome_id column to genes
    op.add_column('genes', sa.Column('genome_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_genes_genome_id'), 'genes', ['genome_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_genes_genome_id_genomes'),
        'genes', 'genomes',
        ['genome_id'], ['genome_id'],
    )

    # 3. Backfill: create Syn3A genome row and link all existing genes
    op.execute(
        "INSERT INTO genomes (accession, organism, description, genome_length, is_circular, gc_content) "
        "VALUES ('CP016816.2', 'Synthetic Mycoplasma mycoides JCVI-syn3A', "
        "'Minimal synthetic bacterial genome JCVI-syn3A', 543379, 1, 24.0)"
    )
    # Link all existing genes to the newly created genome
    # SQLite doesn't support subqueries in UPDATE easily, so we use a simple approach
    op.execute(
        "UPDATE genes SET genome_id = (SELECT genome_id FROM genomes WHERE accession = 'CP016816.2')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_genes_genome_id_genomes'), 'genes', type_='foreignkey')
    op.drop_index(op.f('ix_genes_genome_id'), table_name='genes')
    op.drop_column('genes', 'genome_id')
    op.drop_index(op.f('ix_genomes_accession'), table_name='genomes')
    op.drop_table('genomes')
