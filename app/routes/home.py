from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import current_user

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/welcome", status_code=303)
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)
    route = {
        "field_sampler": "/field",
        "client_sampler": "/field",
        "client_operations": "/field",
        "sampling_supervisor": "/sampling-supervision",
        "operations_manager": "/operations",
        "data_entry": "/intake",
        "sample_receiving": "/receiving",
        "lab_technician": "/lab/operations?section=labprogress",
        "quality": "/lab/operations?section=quality",
        "client": "/client",
        "management": "/management",
        "technical_manager": "/management",
        "senior_chemist": "/lab/operations?section=supervisor",
        "system_admin": "/admin",
    }.get(user.role, "/welcome")
    return RedirectResponse(route, status_code=303)
