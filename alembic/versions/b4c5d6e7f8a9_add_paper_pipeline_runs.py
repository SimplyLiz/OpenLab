"""add_paper_pipeline_runs

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-02-17 09:03:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'paper_pipeline_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pdf_filename', sa.String(500), nullable=False),
        sa.Column('pdf_hash', sa.String(64), nullable=False),
        sa.Column('methods_text', sa.Text(), nullable=True),
        sa.Column('techniques_found', sa.JSON(), nullable=True),
        sa.Column('pipeline_yaml', sa.Text(), nullable=True),
        sa.Column('pipeline_config', sa.JSON(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('stages_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('manual_review_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_doi', sa.String(200), nullable=True),
        sa.Column('agent_run_id', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_paper_pipeline_runs')),
        sa.ForeignKeyConstraint(
            ['agent_run_id'], ['agent_runs.run_id'],
            name=op.f('fk_paper_pipeline_runs_agent_run_id_agent_runs'),
        ),
    )
    op.create_index(
        op.f('ix_paper_pipeline_runs_pdf_hash'),
        'paper_pipeline_runs', ['pdf_hash'],
    )


def downgrade() -> None:
    op.drop_table('paper_pipeline_runs')
