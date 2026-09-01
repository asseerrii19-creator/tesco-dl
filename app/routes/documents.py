from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import ControlledDocument, Role, User
from ..security import require_user

router = APIRouter(tags=["controlled documents"])
ALLOWED = {
    Role.LAB_TECHNICIAN.value,
    Role.SENIOR_CHEMIST.value,
    Role.QUALITY.value,
    Role.TECHNICAL_MANAGER.value,
    Role.MANAGEMENT.value,
    Role.SYSTEM_ADMIN.value,
}
DOC_DIR = Path(__file__).resolve().parents[1] / "data" / "controlled_documents"


def _user(request: Request, db: Session) -> User:
    return require_user(request, db, ALLOWED)


@router.get("/documents")
def document_library(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    stmt = select(ControlledDocument).where(ControlledDocument.status == "ACTIVE")
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        stmt = stmt.where(or_(ControlledDocument.site_id.is_(None), ControlledDocument.site_id == user.site_id))
    documents = db.scalars(stmt.order_by(ControlledDocument.document_type, ControlledDocument.code)).all()
    return templates.TemplateResponse("documents.html", {"request": request, "user": user, "documents": documents})


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    doc = db.get(ControlledDocument, document_id)
    if not doc:
        return templates.TemplateResponse("not_found.html", {"request": request, "user": user}, status_code=404)
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id and doc.site_id not in {None, user.site_id}:
        return templates.TemplateResponse("not_found.html", {"request": request, "user": user}, status_code=404)
    path = DOC_DIR / Path(doc.stored_filename).name
    if not path.exists():
        return templates.TemplateResponse("not_found.html", {"request": request, "user": user}, status_code=404)
    return FileResponse(path, filename=doc.original_filename)
