"""add scalable configuration tables

Revision ID: 8f2f23c2c8a1
Revises: 2c30c15720e2
Create Date: 2026-08-31 22:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8f2f23c2c8a1"
down_revision: Union[str, Sequence[str], None] = "2c30c15720e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "controlled_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("revision", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("effective_date", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.String(length=240), nullable=False),
        sa.Column("stored_filename", sa.String(length=300), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_index("ix_controlled_documents_site_id", "controlled_documents", ["site_id"], unique=False)
    op.create_index("ix_controlled_documents_document_type", "controlled_documents", ["document_type"], unique=False)
    op.create_index("ix_controlled_documents_code", "controlled_documents", ["code"], unique=False)
    op.create_index("ix_controlled_documents_title", "controlled_documents", ["title"], unique=False)
    op.create_index("ix_controlled_documents_status", "controlled_documents", ["status"], unique=False)
    op.create_index("ix_controlled_documents_created_at", "controlled_documents", ["created_at"], unique=False)

    op.create_table(
        "test_package_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("tests_json", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_package_configs_site_id", "test_package_configs", ["site_id"], unique=False)
    op.create_index("ix_test_package_configs_code", "test_package_configs", ["code"], unique=True)
    op.create_index("ix_test_package_configs_name", "test_package_configs", ["name"], unique=False)
    op.create_index("ix_test_package_configs_active", "test_package_configs", ["active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_test_package_configs_active", table_name="test_package_configs")
    op.drop_index("ix_test_package_configs_name", table_name="test_package_configs")
    op.drop_index("ix_test_package_configs_code", table_name="test_package_configs")
    op.drop_index("ix_test_package_configs_site_id", table_name="test_package_configs")
    op.drop_table("test_package_configs")
    op.drop_index("ix_controlled_documents_created_at", table_name="controlled_documents")
    op.drop_index("ix_controlled_documents_status", table_name="controlled_documents")
    op.drop_index("ix_controlled_documents_title", table_name="controlled_documents")
    op.drop_index("ix_controlled_documents_code", table_name="controlled_documents")
    op.drop_index("ix_controlled_documents_document_type", table_name="controlled_documents")
    op.drop_index("ix_controlled_documents_site_id", table_name="controlled_documents")
    op.drop_table("controlled_documents")
