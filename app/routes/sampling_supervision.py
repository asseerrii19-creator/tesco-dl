from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role, SamplingAssignment, SamplingOrder, User
from ..security import require_user
from ..services.audit import add_audit

router = APIRouter(prefix="/sampling-supervision", tags=["sampling supervision"])
ALLOWED = {Role.SAMPLING_SUPERVISOR.value, Role.OPERATIONS_MANAGER.value, Role.TECHNICAL_MANAGER.value, Role.SYSTEM_ADMIN.value}


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    stmt = select(SamplingAssignment).join(SamplingOrder).order_by(SamplingAssignment.created_at.desc())
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        stmt = stmt.where(SamplingOrder.site_id == user.site_id)
    if user.role == Role.SAMPLING_SUPERVISOR.value:
        stmt = stmt.where(SamplingOrder.supervisor_id == user.id)
    assignments = db.scalars(stmt.limit(200)).all()
    samplers_stmt = select(User).where(User.role.in_([Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value]), User.active.is_(True))
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        samplers_stmt = samplers_stmt.where(User.site_id == user.site_id)
    samplers = db.scalars(samplers_stmt.order_by(User.full_name)).all()
    return templates.TemplateResponse("sampling_supervision.html", {"request": request, "user": user, "assignments": assignments, "samplers": samplers})


@router.post("/assignment/{assignment_id}/assign")
def assign(assignment_id: int, request: Request, sampler_id: int = Form(...), note: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    assignment = db.get(SamplingAssignment, assignment_id)
    sampler = db.get(User, sampler_id)
    if not assignment or not sampler:
        return RedirectResponse("/sampling-supervision", status_code=303)
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id and assignment.order.site_id != user.site_id:
        return RedirectResponse("/sampling-supervision", status_code=303)
    if user.role == Role.SAMPLING_SUPERVISOR.value and assignment.order.supervisor_id != user.id:
        return RedirectResponse("/sampling-supervision", status_code=303)
    if sampler.role not in {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}:
        raise ValueError("Selected user is not an authorized sampler")
    if assignment.source_party == "CLIENT" and sampler.client_id != assignment.order.client_id:
        raise ValueError("Client-side sampler must belong to the order client")
    if assignment.source_party == "TSCO" and sampler.client_id is not None:
        raise ValueError("TSCO assignment cannot be allocated to a client-side account")
    if sampler.site_id and sampler.site_id != assignment.order.site_id:
        raise ValueError("Sampler and sampling order must belong to the same site")
    assignment.assigned_sampler_id = sampler.id
    assignment.assigned_at = datetime.utcnow()
    assignment.status = "ASSIGNED"
    if note.strip():
        assignment.instructions = (assignment.instructions + "\n" + note.strip()).strip()
    add_audit(db, actor=user, request=request, action="SAMPLING_ASSIGNMENT_ASSIGNED", entity_type="SamplingAssignment", entity_id=assignment.id, summary=f"Assigned {assignment.assignment_code} to {sampler.full_name}")
    db.commit()
    return RedirectResponse("/sampling-supervision", status_code=303)
