"""Move routine conflict rules out of code into a table.

Revision ID: 0002_conflict_rules
Revises: 0001_initial
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_conflict_rules"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conflict_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("function_a", sa.String(160), nullable=False),
        sa.Column("function_b", sa.String(160), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.UniqueConstraint("function_a", "function_b", name="uq_conflict_pair"),
        sa.CheckConstraint("severity in ('low','medium','high')", name="ck_conflict_severity"),
    )
    # Ingredient functions are compared case-insensitively when checking routines.
    op.create_index("ix_ingredients_function", "ingredients", [sa.text("lower(function)")])


def downgrade() -> None:
    op.drop_index("ix_ingredients_function", table_name="ingredients")
    op.drop_table("conflict_rules")
