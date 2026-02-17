"""add_variant_interpretations

Revision ID: a3b4c5d6e7f8
Revises: f2b3c4d5e6f7
Create Date: 2026-02-17 09:02:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'variant_interpretations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sample_id', sa.String(200), nullable=True),
        sa.Column('vcf_file_hash', sa.String(64), nullable=False),
        sa.Column('tumor_type', sa.String(100), nullable=True),
        sa.Column('genome_build', sa.String(10), nullable=False, server_default='hg38'),
        sa.Column('total_variants', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pathogenic_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vus_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('benign_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('actionable_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('report_json', sa.JSON(), nullable=True),
        sa.Column('report_markdown', sa.Text(), nullable=True),
        sa.Column('reproducibility', sa.JSON(), nullable=True),
        sa.Column('agent_run_id', sa.String(32), nullable=True),
        sa.Column(
            'disclaimer_version', sa.String(10), nullable=False, server_default='1.0'
        ),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_variant_interpretations')),
        sa.ForeignKeyConstraint(
            ['agent_run_id'], ['agent_runs.run_id'],
            name=op.f('fk_variant_interpretations_agent_run_id_agent_runs'),
        ),
    )
    op.create_index(
        op.f('ix_variant_interpretations_vcf_file_hash'),
        'variant_interpretations', ['vcf_file_hash'],
    )
    op.create_index(
        op.f('ix_variant_interpretations_tumor_type'),
        'variant_interpretations', ['tumor_type'],
    )


def downgrade() -> None:
    op.drop_table('variant_interpretations')
