from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, SampleRequest
from ..security import current_user
from ..services.workflow import STATUS_LABELS

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.get("/tracking/{token}")
def tracking(token: str, request: Request, db: Session = Depends(get_db)):
    sample = db.scalar(select(SampleRequest).where(SampleRequest.public_token == token))
    if not sample:
        raise HTTPException(404, "Sample not found")
    public_enabled = os.getenv("ENABLE_PUBLIC_TRACKING", "false").strip().lower() in {"1", "true", "yes", "on"}
    user = current_user(request, db)
    if not public_enabled:
        if not user:
            raise HTTPException(401, "Authentication required")
        if user.role == Role.CLIENT.value and user.client_id != sample.client_id:
            raise HTTPException(404, "Sample not found")
    return {
        "request_number": sample.request_number,
        "lms_number": sample.lms_number,
        "client": sample.client.name,
        "asset_code": sample.asset.asset_code,
        "status": sample.status,
        "status_label": STATUS_LABELS.get(sample.status, sample.status),
        "events": [
            {
                "event": event.event_type,
                "status": event.status,
                "status_label": STATUS_LABELS.get(event.status, event.status),
                "at": event.event_at.isoformat(),
            }
            for event in sorted(sample.events, key=lambda item: item.event_at)
        ],
    }

@router.get("/health")
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "tsco-digital-laboratory-platform", "version": "2.1.0"}
