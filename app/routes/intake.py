from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import DataQualityIssue, Role, SampleRequest, SampleStatus
from ..security import require_user
from ..services.workflow import add_event, register_in_lms
from ..services.audit import add_audit
from ..services.scope import can_access_site

router = APIRouter(prefix="/intake", tags=["intake"])
ALLOWED = {Role.DATA_ENTRY.value, Role.SAMPLE_RECEIVING.value, Role.SYSTEM_ADMIN.value}


@router.get("")
def queue(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    stmt = select(SampleRequest).order_by(SampleRequest.submitted_at.desc())
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        stmt = stmt.where(SampleRequest.site_id == user.site_id)
    if q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                SampleRequest.request_number.ilike(term),
                SampleRequest.barcode_value.ilike(term),
                SampleRequest.lms_number.ilike(term),
            )
        )
    samples = db.scalars(stmt.limit(100)).all()
    return templates.TemplateResponse("intake_queue.html", {"request": request, "user": user, "samples": samples, "q": q})


@router.get("/{sample_id}")
def review(sample_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    sample = db.get(SampleRequest, sample_id)
    if not sample or not can_access_site(user, sample.site_id):
        return RedirectResponse("/intake", status_code=303)
    return templates.TemplateResponse("intake_review.html", {"request": request, "user": user, "sample": sample})


@router.post("/{sample_id}/decision")
def decision(
    sample_id: int,
    request: Request,
    action: str = Form(...),
    note: str = Form(""),
    issue_type: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    sample = db.get(SampleRequest, sample_id)
    if not sample or not can_access_site(user, sample.site_id):
        return RedirectResponse("/intake", status_code=303)

    action = action.upper()
    if action == "ACCEPT_AND_REGISTER":
        sample.status = SampleStatus.ACCEPTED.value
        sample.accepted_at = datetime.utcnow()
        sample.data_entry_note = note.strip()
        add_event(db, sample, user, "DATA_ACCEPTANCE", sample.status, note.strip())
        register_in_lms(db, sample, user)
    elif action == "ACCEPT":
        sample.status = SampleStatus.ACCEPTED.value
        sample.accepted_at = datetime.utcnow()
        sample.data_entry_note = note.strip()
        add_event(db, sample, user, "DATA_ACCEPTANCE", sample.status, note.strip())
    elif action == "RETURN":
        sample.status = SampleStatus.RETURNED.value
        sample.return_reason = note.strip()
        add_event(db, sample, user, "RETURN_FOR_CORRECTION", sample.status, note.strip())
        db.add(
            DataQualityIssue(
                sample_request_id=sample.id,
                issue_type=issue_type.strip() or "FIELD_DATA_ERROR",
                severity="MEDIUM",
                description=note.strip() or "Returned for correction",
                reported_by_id=user.id,
            )
        )
    elif action == "REJECT":
        sample.status = SampleStatus.REJECTED.value
        sample.rejection_reason = note.strip()
        add_event(db, sample, user, "REJECTION", sample.status, note.strip())
        db.add(
            DataQualityIssue(
                sample_request_id=sample.id,
                issue_type=issue_type.strip() or "SAMPLE_REJECTED",
                severity="HIGH",
                description=note.strip() or "Sample rejected",
                reported_by_id=user.id,
            )
        )
    elif action == "REGISTER_LMS":
        if sample.status not in {SampleStatus.ACCEPTED.value, SampleStatus.RECEIVED.value}:
            sample.data_entry_note = "Sample must be accepted or received before LMS registration."
        else:
            register_in_lms(db, sample, user)
    add_audit(
        db,
        actor=user,
        request=request,
        action=f"INTAKE_{action}",
        entity_type="SampleRequest",
        entity_id=sample.id,
        summary=f"{sample.request_number}: {action}",
        details={"note": note, "issue_type": issue_type, "status": sample.status},
    )
    db.commit()
    return RedirectResponse(f"/intake/{sample.id}", status_code=303)
