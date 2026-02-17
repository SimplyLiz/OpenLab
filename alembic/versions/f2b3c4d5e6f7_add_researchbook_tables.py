"""add_researchbook_tables

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-02-17 09:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### research_threads ###
    op.create_table(
        'research_threads',
        sa.Column('thread_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'PUBLISHED', 'CHALLENGED', 'SUPERSEDED', 'ARCHIVED',
                     native_enum=False),
            nullable=False,
            server_default='DRAFT',
        ),
        sa.Column('agent_run_id', sa.String(32), nullable=True),
        sa.Column('gene_symbol', sa.String(50), nullable=False),
        sa.Column('cancer_type', sa.String(100), nullable=True),
        sa.Column('forked_from_id', sa.Integer(), nullable=True),
        sa.Column('claims_snapshot', sa.JSON(), nullable=True),
        sa.Column('evidence_snapshot', sa.JSON(), nullable=True),
        sa.Column('convergence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence_tier', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('challenge_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fork_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('thread_id', name=op.f('pk_research_threads')),
        sa.ForeignKeyConstraint(
            ['agent_run_id'], ['agent_runs.run_id'],
            name=op.f('fk_research_threads_agent_run_id_agent_runs'),
        ),
        sa.ForeignKeyConstraint(
            ['forked_from_id'], ['research_threads.thread_id'],
            name=op.f('fk_research_threads_forked_from_id_research_threads'),
        ),
    )
    op.create_index(
        op.f('ix_research_threads_agent_run_id'), 'research_threads', ['agent_run_id']
    )
    op.create_index(
        op.f('ix_research_threads_gene_symbol'), 'research_threads', ['gene_symbol']
    )
    op.create_index(
        op.f('ix_research_threads_cancer_type'), 'research_threads', ['cancer_type']
    )
    op.create_index('ix_research_threads_status', 'research_threads', ['status'])
    op.create_index(
        'ix_research_threads_gene_cancer', 'research_threads', ['gene_symbol', 'cancer_type']
    )

    # ### human_comments ###
    op.create_table(
        'human_comments',
        sa.Column('comment_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('author_name', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column(
            'comment_type',
            sa.Enum('COMMENT', 'CHALLENGE', 'CORRECTION', 'ENDORSEMENT', native_enum=False),
            nullable=False,
            server_default='COMMENT',
        ),
        sa.Column('reply_to_comment_id', sa.Integer(), nullable=True),
        sa.Column('referenced_claim_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('comment_id', name=op.f('pk_human_comments')),
        sa.ForeignKeyConstraint(
            ['thread_id'], ['research_threads.thread_id'],
            name=op.f('fk_human_comments_thread_id_research_threads'),
        ),
        sa.ForeignKeyConstraint(
            ['reply_to_comment_id'], ['human_comments.comment_id'],
            name=op.f('fk_human_comments_reply_to_comment_id_human_comments'),
        ),
    )
    op.create_index(op.f('ix_human_comments_thread_id'), 'human_comments', ['thread_id'])

    # ### thread_forks ###
    op.create_table(
        'thread_forks',
        sa.Column('fork_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('parent_thread_id', sa.Integer(), nullable=False),
        sa.Column('child_thread_id', sa.Integer(), nullable=False),
        sa.Column('modification_summary', sa.Text(), nullable=True),
        sa.Column('modification_params', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('fork_id', name=op.f('pk_thread_forks')),
        sa.ForeignKeyConstraint(
            ['parent_thread_id'], ['research_threads.thread_id'],
            name=op.f('fk_thread_forks_parent_thread_id_research_threads'),
        ),
        sa.ForeignKeyConstraint(
            ['child_thread_id'], ['research_threads.thread_id'],
            name=op.f('fk_thread_forks_child_thread_id_research_threads'),
        ),
        sa.UniqueConstraint('child_thread_id', name=op.f('uq_thread_forks_child_thread_id')),
    )
    op.create_index(
        op.f('ix_thread_forks_parent_thread_id'), 'thread_forks', ['parent_thread_id']
    )

    # ### thread_watchers ###
    op.create_table(
        'thread_watchers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('watcher_name', sa.String(200), nullable=False),
        sa.Column(
            'notify_on',
            sa.Enum('ALL', 'CHALLENGES', 'CORRECTIONS', native_enum=False),
            nullable=False,
            server_default='ALL',
        ),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_thread_watchers')),
        sa.ForeignKeyConstraint(
            ['thread_id'], ['research_threads.thread_id'],
            name=op.f('fk_thread_watchers_thread_id_research_threads'),
        ),
    )
    op.create_index(op.f('ix_thread_watchers_thread_id'), 'thread_watchers', ['thread_id'])


def downgrade() -> None:
    op.drop_table('thread_watchers')
    op.drop_table('thread_forks')
    op.drop_table('human_comments')
    op.drop_table('research_threads')
