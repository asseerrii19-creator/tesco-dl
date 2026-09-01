from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Asset, ClientUnit, Role, SampleRequest
from ..security import current_user, require_user
from ..services.scope import allowed_client_unit_ids, can_access_asset, client_scope_labels
from ..services.workflow import STATUS_LABELS, STATUS_ORDER

router = APIRouter(tags=["client"])


@router.get("/client")
def client_dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, {Role.CLIENT.value, Role.SYSTEM_ADMIN.value})
    stmt = select(SampleRequest).order_by(SampleRequest.created_at.desc())
    scope_labels: list[str] = []
    if user.role == Role.CLIENT.value:
        stmt = stmt.where(SampleRequest.client_id == user.client_id)
        allowed_units = allowed_client_unit_ids(db, user, user.client_id)
        if allowed_units is not None:
            if allowed_units:
                stmt = stmt.join(Asset, SampleRequest.asset_id == Asset.id).where(Asset.client_unit_id.in_(allowed_units))
            else:
                stmt = stmt.where(SampleRequest.id == -1)
        scope_labels = client_scope_labels(db, user)
    samples = db.scalars(stmt.limit(100)).all()
    return templates.TemplateResponse(
        "client_dashboard.html",
        {"request": request, "user": user, "samples": samples, "status_labels": STATUS_LABELS, "scope_labels": scope_labels},
    )


@router.get("/track/{token}")
def public_tracking(token: str, request: Request, db: Session = Depends(get_db)):
    sample = db.scalar(select(SampleRequest).where(SampleRequest.public_token == token))
    if not sample:
        return templates.TemplateResponse("not_found.html", {"request": request}, status_code=404)
    public_enabled = os.getenv("ENABLE_PUBLIC_TRACKING", "false").strip().lower() in {"1", "true", "yes", "on"}
    user = current_user(request, db)
    if not public_enabled:
        if not user:
            return RedirectResponse("/login/client", status_code=303)
        if user.role == Role.CLIENT.value and not can_access_asset(db, user, sample.asset):
            return templates.TemplateResponse("not_found.html", {"request": request, "user": user}, status_code=404)
    completed = {event.status for event in sample.events}
    completed.add(sample.status)
    return templates.TemplateResponse(
        "public_track.html",
        {
            "request": request,
            "user": user,
            "sample": sample,
            "status_labels": STATUS_LABELS,
            "status_order": STATUS_ORDER,
            "completed": completed,
        },
    )
