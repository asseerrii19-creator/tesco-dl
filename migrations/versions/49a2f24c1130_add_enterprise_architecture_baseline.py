"""add enterprise architecture baseline

Revision ID: 49a2f24c1130
Revises: 8f2f23c2c8a1
Create Date: 2026-08-31 23:25:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "49a2f24c1130"
down_revision: Union[str, Sequence[str], None] = "8f2f23c2c8a1"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("departments",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("site_id",sa.Integer(),nullable=True),sa.Column("code",sa.String(40),nullable=False),sa.Column("name",sa.String(160),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.ForeignKeyConstraint(["site_id"],["sites.id"]),sa.UniqueConstraint("site_id","code",name="uq_department_site_code"))
    op.create_index("ix_departments_site_id","departments",["site_id"]); op.create_index("ix_departments_code","departments",["code"]); op.create_index("ix_departments_name","departments",["name"]); op.create_index("ix_departments_active","departments",["active"])
    op.create_table("client_units",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("client_id",sa.Integer(),nullable=False),sa.Column("parent_id",sa.Integer(),nullable=True),sa.Column("unit_type",sa.String(40),nullable=False),sa.Column("code",sa.String(80),nullable=False),sa.Column("name",sa.String(180),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.ForeignKeyConstraint(["client_id"],["clients.id"]),sa.ForeignKeyConstraint(["parent_id"],["client_units.id"]),sa.UniqueConstraint("client_id","code",name="uq_client_unit_code"))
    for ix,col in [("ix_client_units_client_id","client_id"),("ix_client_units_parent_id","parent_id"),("ix_client_units_unit_type","unit_type"),("ix_client_units_code","code"),("ix_client_units_name","name"),("ix_client_units_active","active")]: op.create_index(ix,"client_units",[col])
    op.add_column("users",sa.Column("department_id",sa.Integer(),nullable=True)); op.create_foreign_key("fk_users_department","users","departments",["department_id"],["id"])
    op.add_column("assets",sa.Column("client_unit_id",sa.Integer(),nullable=True)); op.create_index("ix_assets_client_unit_id","assets",["client_unit_id"]); op.create_foreign_key("fk_assets_client_unit","assets","client_units",["client_unit_id"],["id"])
    op.create_table("workflow_definitions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("site_id",sa.Integer(),nullable=True),sa.Column("code",sa.String(80),nullable=False),sa.Column("name",sa.String(180),nullable=False),sa.Column("sample_type",sa.String(80),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.ForeignKeyConstraint(["site_id"],["sites.id"]),sa.UniqueConstraint("site_id","code","version",name="uq_workflow_site_code_version"))
    for ix,col in [("ix_workflow_definitions_site_id","site_id"),("ix_workflow_definitions_code","code"),("ix_workflow_definitions_name","name"),("ix_workflow_definitions_active","active")]: op.create_index(ix,"workflow_definitions",[col])
    op.create_table("workflow_steps",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("workflow_id",sa.Integer(),nullable=False),sa.Column("step_order",sa.Integer(),nullable=False),sa.Column("step_key",sa.String(80),nullable=False),sa.Column("label",sa.String(160),nullable=False),sa.Column("responsible_role",sa.String(40),nullable=False),sa.Column("approval_required",sa.Boolean(),nullable=False),sa.Column("terminal",sa.Boolean(),nullable=False),sa.ForeignKeyConstraint(["workflow_id"],["workflow_definitions.id"]),sa.UniqueConstraint("workflow_id","step_order",name="uq_workflow_step_order")); op.create_index("ix_workflow_steps_workflow_id","workflow_steps",["workflow_id"])
    op.create_table("approval_policies",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("site_id",sa.Integer(),nullable=True),sa.Column("code",sa.String(80),nullable=False),sa.Column("name",sa.String(180),nullable=False),sa.Column("entity_type",sa.String(80),nullable=False),sa.Column("stages_json",sa.Text(),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.ForeignKeyConstraint(["site_id"],["sites.id"]),sa.UniqueConstraint("site_id","code",name="uq_approval_site_code"))
    for ix,col in [("ix_approval_policies_site_id","site_id"),("ix_approval_policies_code","code"),("ix_approval_policies_name","name"),("ix_approval_policies_active","active")]: op.create_index(ix,"approval_policies",[col])
    op.create_table("integration_queue",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("sample_request_id",sa.Integer(),nullable=True),sa.Column("integration",sa.String(40),nullable=False),sa.Column("direction",sa.String(20),nullable=False),sa.Column("operation",sa.String(80),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("payload_json",sa.Text(),nullable=False),sa.Column("attempts",sa.Integer(),nullable=False),sa.Column("external_reference",sa.String(120),nullable=False),sa.Column("last_error",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.ForeignKeyConstraint(["sample_request_id"],["sample_requests.id"]))
    for ix,col in [("ix_integration_queue_sample_request_id","sample_request_id"),("ix_integration_queue_integration","integration"),("ix_integration_queue_operation","operation"),("ix_integration_queue_status","status"),("ix_integration_queue_created_at","created_at")]: op.create_index(ix,"integration_queue",[col])

def downgrade() -> None:
    for ix in ["ix_integration_queue_created_at","ix_integration_queue_status","ix_integration_queue_operation","ix_integration_queue_integration","ix_integration_queue_sample_request_id"]: op.drop_index(ix,table_name="integration_queue")
    op.drop_table("integration_queue")
    for ix in ["ix_approval_policies_active","ix_approval_policies_name","ix_approval_policies_code","ix_approval_policies_site_id"]: op.drop_index(ix,table_name="approval_policies")
    op.drop_table("approval_policies")
    op.drop_index("ix_workflow_steps_workflow_id",table_name="workflow_steps"); op.drop_table("workflow_steps")
    for ix in ["ix_workflow_definitions_active","ix_workflow_definitions_name","ix_workflow_definitions_code","ix_workflow_definitions_site_id"]: op.drop_index(ix,table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
    op.drop_constraint("fk_assets_client_unit","assets",type_="foreignkey"); op.drop_index("ix_assets_client_unit_id",table_name="assets"); op.drop_column("assets","client_unit_id")
    op.drop_constraint("fk_users_department","users",type_="foreignkey"); op.drop_column("users","department_id")
    for ix in ["ix_client_units_active","ix_client_units_name","ix_client_units_code","ix_client_units_unit_type","ix_client_units_parent_id","ix_client_units_client_id"]: op.drop_index(ix,table_name="client_units")
    op.drop_table("client_units")
    for ix in ["ix_departments_active","ix_departments_name","ix_departments_code","ix_departments_site_id"]: op.drop_index(ix,table_name="departments")
    op.drop_table("departments")
