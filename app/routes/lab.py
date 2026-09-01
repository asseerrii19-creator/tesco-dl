from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role, SampleRequest, SampleStatus
from ..security import require_user
from ..services.audit import add_audit
from ..services.workflow import add_event
from ..services.lab_operations import sync_sample_to_operations

router = APIRouter(prefix="/lab", tags=["laboratory"])
ALLOWED = {
    Role.LAB_TECHNICIAN.value,
    Role.SENIOR_CHEMIST.value,
    Role.QUALITY.value,
    Role.TECHNICAL_MANAGER.value,
    Role.SYSTEM_ADMIN.value,
}


@router.get("")
def workspace(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    stmt = select(SampleRequest).where(
        SampleRequest.status.in_([
            SampleStatus.RECEIVED.value,
            SampleStatus.REGISTERED.value,
            SampleStatus.TESTING.value,
            SampleStatus.TECHNICAL_REVIEW.value,
        ])
    )
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        stmt = stmt.where(SampleRequest.site_id == user.site_id)
    samples = db.scalars(stmt.order_by(SampleRequest.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse("lab_workspace.html", {"request": request, "user": user, "samples": samples})


@router.post("/{sample_id}/status")
def update_status(
    sample_id: int,
    request: Request,
    action: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    sample = db.get(SampleRequest, sample_id)
    if not sample or (user.role != Role.SYSTEM_ADMIN.value and user.site_id and sample.site_id != user.site_id):
        return RedirectResponse("/lab", status_code=303)
    if action == "START_TESTING" and sample.status in {SampleStatus.RECEIVED.value, SampleStatus.REGISTERED.value}:
        sample.status = SampleStatus.TESTING.value
        add_event(db, sample, user, "LAB_TESTING_STARTED", sample.status, note.strip())
        sync_sample_to_operations(db, sample, user, phase="TESTING")
    elif action == "SUBMIT_REVIEW" and sample.status == SampleStatus.TESTING.value:
        sample.status = SampleStatus.TECHNICAL_REVIEW.value
        add_event(db, sample, user, "SUBMITTED_FOR_TECHNICAL_REVIEW", sample.status, note.strip())
        sync_sample_to_operations(db, sample, user, phase="TECHNICAL_REVIEW")
    else:
        return RedirectResponse("/lab", status_code=303)
    add_audit(db, actor=user, request=request, action="SAMPLE_STATUS_CHANGED", entity_type="SampleRequest", entity_id=sample.id, summary=f"{sample.request_number} → {sample.status}", details={"note": note})
    db.commit()
    return RedirectResponse("/lab", status_code=303)
