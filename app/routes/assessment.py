from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role, SampleRequest, SampleStatus, TechnicalAssessmentRecord
from ..security import require_user
from ..services.audit import add_audit
from ..services.technical_assessment import assess_sample
from ..services.workflow import add_event

router = APIRouter(prefix="/assessment", tags=["technical assessment"])
ALLOWED = {Role.SENIOR_CHEMIST.value, Role.QUALITY.value, Role.TECHNICAL_MANAGER.value, Role.SYSTEM_ADMIN.value}
DECISIONS = {"DRAFT", "RETEST", "RESAMPLE", "ESCALATED", "APPROVED"}
VISIBLE_STATUSES = [
    SampleStatus.RECEIVED.value,
    SampleStatus.TESTING.value,
    SampleStatus.TECHNICAL_REVIEW.value,
    SampleStatus.REPORT_APPROVED.value,
    SampleStatus.REPORT_RELEASED.value,
]


def _visible_to_user(sample: SampleRequest | None, user) -> bool:
    return bool(sample) and (user.role == Role.SYSTEM_ADMIN.value or not user.site_id or sample.site_id == user.site_id)


@router.get("")
def queue(request: Request, sample_id: int | None = None, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    stmt = select(SampleRequest).where(SampleRequest.status.in_(VISIBLE_STATUSES)).order_by(SampleRequest.created_at.desc())
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        stmt = stmt.where(SampleRequest.site_id == user.site_id)
    samples = db.scalars(stmt.limit(200)).all()
    selected = db.get(SampleRequest, sample_id) if sample_id else (samples[0] if samples else None)
    if not _visible_to_user(selected, user) or (selected and selected.status not in VISIBLE_STATUSES):
        selected = samples[0] if samples else None
    assessment = assess_sample(db, selected) if selected else None
    record = (
        db.scalar(select(TechnicalAssessmentRecord).where(TechnicalAssessmentRecord.sample_request_id == selected.id))
        if selected else None
    )
    return templates.TemplateResponse(
        "assessment.html",
        {"request": request, "user": user, "samples": samples, "selected": selected, "assessment": assessment, "record": record},
    )


@router.post("/{sample_id}")
def save(
    sample_id: int,
    request: Request,
    recommendation: str = Form(""),
    decision: str = Form("DRAFT"),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    sample = db.get(SampleRequest, sample_id)
    if not _visible_to_user(sample, user):
        return RedirectResponse("/assessment", status_code=303)
    decision = decision.strip().upper()
    if decision not in DECISIONS:
        decision = "DRAFT"
    findings = assess_sample(db, sample)
    record = db.scalar(
        select(TechnicalAssessmentRecord).where(TechnicalAssessmentRecord.sample_request_id == sample.id)
    )
    if not record:
        record = TechnicalAssessmentRecord(sample_request_id=sample.id)
        db.add(record)
    record.profile = findings["profile"]
    record.system_findings_json = json.dumps(findings, ensure_ascii=False)
    record.recommendation = recommendation.strip()
    record.decision = decision
    record.reviewed_by_id = user.id
    record.updated_at = datetime.utcnow()

    event_note = record.recommendation or decision.replace("_", " ").title()
    if decision == "RETEST":
        add_event(db, sample, user, "TECHNICAL_RETEST_REQUESTED", sample.status, event_note)
    elif decision == "RESAMPLE":
        add_event(db, sample, user, "TECHNICAL_RESAMPLE_REQUESTED", sample.status, event_note)
    elif decision == "ESCALATED":
        add_event(db, sample, user, "TECHNICAL_ASSESSMENT_ESCALATED", sample.status, event_note)
    elif decision == "APPROVED":
        if sample.status == SampleStatus.TECHNICAL_REVIEW.value:
            sample.status = SampleStatus.REPORT_APPROVED.value
        add_event(db, sample, user, "TECHNICAL_COMMENT_APPROVED", sample.status, event_note)

    add_audit(
        db,
        actor=user,
        request=request,
        action="TECHNICAL_ASSESSMENT_SAVED",
        entity_type="SampleRequest",
        entity_id=sample.id,
        summary=f"{sample.request_number}: {decision}",
        details={"profile": record.profile, "recommendation": record.recommendation},
    )
    db.commit()
    return RedirectResponse(f"/assessment?sample_id={sample.id}", status_code=303)
