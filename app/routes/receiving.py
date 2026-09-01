from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role, SampleRequest, SampleStatus
from ..security import require_user
from ..services.workflow import add_event
from ..services.lab_operations import sync_sample_to_operations
from ..services.audit import add_audit
from ..services.scope import can_access_site

router = APIRouter(prefix="/receiving", tags=["receiving"])
ALLOWED = {Role.SAMPLE_RECEIVING.value, Role.DATA_ENTRY.value, Role.SYSTEM_ADMIN.value}


@router.get("")
def scan_page(request: Request, barcode: str = "", error: str = "", db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    sample = None
    if barcode.strip():
        stmt = select(SampleRequest).where(
            or_(SampleRequest.barcode_value == barcode.strip(), SampleRequest.request_number == barcode.strip())
        )
        if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
            stmt = stmt.where(SampleRequest.site_id == user.site_id)
        sample = db.scalar(stmt)
    return templates.TemplateResponse("receiving.html", {"request": request, "user": user, "sample": sample, "barcode": barcode, "error": error})


@router.post("/{sample_id}/receive")
def receive(
    sample_id: int,
    request: Request,
    seal_status: str = Form("Intact"),
    condition_note: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    sample = db.get(SampleRequest, sample_id)
    if sample and can_access_site(user, sample.site_id):
        if not sample.lms_number:
            return RedirectResponse(f"/receiving?barcode={sample.barcode_value}&error=Data+Entry+must+accept+and+register+this+sample+before+receipt", status_code=303)
        sample.status = SampleStatus.RECEIVED.value
        sample.received_at = datetime.utcnow()
        add_event(db, sample, user, "PHYSICAL_RECEIPT", sample.status, f"Seal: {seal_status}. {condition_note}".strip())
        sync_sample_to_operations(db, sample, user, phase="RECEIVED")
        add_audit(
            db,
            actor=user,
            request=request,
            action="PHYSICAL_SAMPLE_RECEIVED",
            entity_type="SampleRequest",
            entity_id=sample.id,
            summary=f"Received {sample.request_number}",
            details={"seal_status": seal_status, "condition_note": condition_note},
        )
        db.commit()
    return RedirectResponse(f"/receiving?barcode={sample.barcode_value if sample else ''}", status_code=303)
