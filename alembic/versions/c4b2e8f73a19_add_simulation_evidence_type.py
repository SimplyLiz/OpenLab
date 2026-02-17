"""add_simulation_evidence_type

Revision ID: c4b2e8f73a19
Revises: a3e7c9d12f01
Create Date: 2026-02-11 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4b2e8f73a19'
down_revision: Union[str, None] = 'a3e7c9d12f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: add new value to existing enum type
    # This is a no-op on SQLite (which stores enums as strings)
    op.execute("ALTER TYPE evidencetype ADD VALUE IF NOT EXISTS 'SIMULATION'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    # Delete any SIMULATION evidence rows, then leave the enum value
    # (harmless orphan). Full reversal requires recreating the type.
    op.execute("DELETE FROM evidence WHERE evidence_type = 'SIMULATION'")
