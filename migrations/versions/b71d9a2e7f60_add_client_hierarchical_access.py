"""add client hierarchical access

Revision ID: b71d9a2e7f60
Revises: 49a2f24c1130
Create Date: 2026-09-01 00:35:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b71d9a2e7f60"
down_revision: Union[str, Sequence[str], None] = "49a2f24c1130"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "user_client_unit_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_unit_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["client_unit_id"], ["client_units.id"]),
        sa.UniqueConstraint("user_id", "client_unit_id", name="uq_user_client_unit_assignment"),
    )
    op.create_index("ix_user_client_unit_assignments_user_id", "user_client_unit_assignments", ["user_id"])
    op.create_index("ix_user_client_unit_assignments_client_unit_id", "user_client_unit_assignments", ["client_unit_id"])

def downgrade() -> None:
    op.drop_index("ix_user_client_unit_assignments_client_unit_id", table_name="user_client_unit_assignments")
    op.drop_index("ix_user_client_unit_assignments_user_id", table_name="user_client_unit_assignments")
    op.drop_table("user_client_unit_assignments")
