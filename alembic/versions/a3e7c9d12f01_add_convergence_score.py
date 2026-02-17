"""add_convergence_score

Revision ID: a3e7c9d12f01
Revises: f8c66d251166
Create Date: 2026-02-11 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3e7c9d12f01'
down_revision: Union[str, None] = 'f8c66d251166'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hypotheses', sa.Column('convergence_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('hypotheses', 'convergence_score')
