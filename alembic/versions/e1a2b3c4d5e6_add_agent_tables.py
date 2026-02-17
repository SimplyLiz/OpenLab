"""add_agent_tables

Revision ID: e1a2b3c4d5e6
Revises: d5a1f3e89b02
Create Date: 2026-02-17 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'd5a1f3e89b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### agent_runs ###
    op.create_table(
        'agent_runs',
        sa.Column('run_id', sa.String(32), primary_key=True),
        sa.Column('gene_symbol', sa.String(50), nullable=False),
        sa.Column('cancer_type', sa.String(100), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', native_enum=False),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('started_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.Column('total_tool_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dossier_json', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('run_id', name=op.f('pk_agent_runs')),
    )
    op.create_index(op.f('ix_agent_runs_gene_symbol'), 'agent_runs', ['gene_symbol'])

    # ### provenance_logs ###
    op.create_table(
        'provenance_logs',
        sa.Column('log_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.String(32), nullable=False),
        sa.Column('call_id', sa.String(24), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('parent_call_id', sa.String(24), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('log_id', name=op.f('pk_provenance_logs')),
        sa.ForeignKeyConstraint(
            ['run_id'], ['agent_runs.run_id'],
            name=op.f('fk_provenance_logs_run_id_agent_runs'),
        ),
    )
    op.create_index(op.f('ix_provenance_logs_run_id'), 'provenance_logs', ['run_id'])
    op.create_index(op.f('ix_provenance_logs_call_id'), 'provenance_logs', ['call_id'])
    op.create_index(
        'ix_provenance_logs_run_id_call_id', 'provenance_logs', ['run_id', 'call_id']
    )

    # ### claim_records ###
    op.create_table(
        'claim_records',
        sa.Column('claim_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.String(32), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column(
            'citation_status',
            sa.Enum('VALID', 'INVALID', 'UNCHECKED', native_enum=False),
            nullable=False,
            server_default='UNCHECKED',
        ),
        sa.Column('is_speculative', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('section_title', sa.String(200), nullable=True),
        sa.Column('source_tool_calls', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('claim_id', name=op.f('pk_claim_records')),
        sa.ForeignKeyConstraint(
            ['run_id'], ['agent_runs.run_id'],
            name=op.f('fk_claim_records_run_id_agent_runs'),
        ),
    )
    op.create_index(op.f('ix_claim_records_run_id'), 'claim_records', ['run_id'])


def downgrade() -> None:
    op.drop_table('claim_records')
    op.drop_table('provenance_logs')
    op.drop_table('agent_runs')
