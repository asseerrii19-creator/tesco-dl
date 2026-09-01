from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ApprovalPolicy, Site, WorkflowDefinition

DEFAULT_WORKFLOW = [
    {"step_key":"sampling_order","label":"Sampling Order","responsible_role":"operations_manager"},
    {"step_key":"supervisor_assignment","label":"Supervisor Assignment","responsible_role":"sampling_supervisor"},
    {"step_key":"field_capture","label":"Field Sampling & Capture","responsible_role":"field_sampler"},
    {"step_key":"data_entry","label":"Data Entry Verification","responsible_role":"data_entry"},
    {"step_key":"lms_registration","label":"LMS Registration","responsible_role":"data_entry"},
    {"step_key":"receiving","label":"Physical Receiving","responsible_role":"sample_receiving"},
    {"step_key":"laboratory","label":"Laboratory Operations","responsible_role":"lab_technician"},
    {"step_key":"technical_review","label":"Technical Review","responsible_role":"senior_chemist","approval_required":True},
    {"step_key":"report_release","label":"Report Release","responsible_role":"technical_manager","approval_required":True,"terminal":True},
]

def active_workflow(db: Session, site_id: int | None):
    if site_id is not None:
        row = db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.site_id == site_id, WorkflowDefinition.active.is_(True)).order_by(WorkflowDefinition.version.desc()))
        if row:
            return row
    return db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.site_id.is_(None), WorkflowDefinition.active.is_(True)).order_by(WorkflowDefinition.version.desc()))

def approval_stages(policy: ApprovalPolicy) -> list[dict]:
    try:
        value = json.loads(policy.stages_json or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []
