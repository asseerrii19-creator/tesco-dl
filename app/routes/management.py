from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import DataQualityIssue, Role, SampleRequest, Site, User
from ..security import require_user

router = APIRouter(prefix="/management", tags=["management"])
ALLOWED = {Role.MANAGEMENT.value, Role.TECHNICAL_MANAGER.value, Role.SENIOR_CHEMIST.value, Role.SYSTEM_ADMIN.value}


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    sample_stmt = select(SampleRequest).order_by(SampleRequest.created_at.desc())
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        sample_stmt = sample_stmt.where(SampleRequest.site_id == user.site_id)
    samples = db.scalars(sample_stmt).all()
    status_counts = Counter(sample.status for sample in samples)
    sampler_stmt = select(User).where(User.role.in_([Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value]))
    if user.role != Role.SYSTEM_ADMIN.value and user.site_id:
        sampler_stmt = sampler_stmt.where(User.site_id == user.site_id)
    samplers = db.scalars(sampler_stmt).all()
    all_issues = db.scalars(select(DataQualityIssue).order_by(DataQualityIssue.created_at.desc())).all()
    visible_sample_ids = {sample.id for sample in samples}
    issues = [issue for issue in all_issues if issue.sample_request_id in visible_sample_ids]
    issue_counts = Counter(issue.issue_type for issue in issues)

    sites = db.scalars(select(Site).order_by(Site.code)).all()
    site_breakdown = []
    for site in sites:
        site_samples = [sample for sample in samples if sample.site_id == site.id]
        site_breakdown.append({
            "code": site.code,
            "name": site.name,
            "laboratory": site.laboratory_name,
            "active": site.active,
            "total": len(site_samples),
            "testing": sum(1 for sample in site_samples if sample.status in {"RECEIVED", "REGISTERED", "TESTING"}),
            "review": sum(1 for sample in site_samples if sample.status == "TECHNICAL_REVIEW"),
            "released": sum(1 for sample in site_samples if sample.status == "REPORT_RELEASED"),
        })

    performance = []
    for sampler in samplers:
        own = [sample for sample in samples if sample.sampler_id == sampler.id]
        own_issues = [issue for issue in issues if issue.sample.sampler_id == sampler.id]
        performance.append(
            {
                "name": sampler.full_name,
                "role": sampler.role,
                "organization": sampler.client.name if sampler.client else "TSCO",
                "samples": len(own),
                "returned": sum(1 for sample in own if sample.status == "RETURNED"),
                "rejected": sum(1 for sample in own if sample.status == "REJECTED"),
                "missing_gps": sum(1 for sample in own if sample.gps_latitude is None or sample.gps_longitude is None),
                "missing_photos": sum(1 for sample in own if not sample.photos),
                "issues": len(own_issues),
            }
        )

    return templates.TemplateResponse(
        "management.html",
        {
            "request": request,
            "user": user,
            "samples": samples,
            "status_counts": status_counts,
            "issue_counts": issue_counts,
            "performance": performance,
            "site_breakdown": site_breakdown,
            "corporate_view": user.site_id is None or user.role == Role.SYSTEM_ADMIN.value,
        },
    )
