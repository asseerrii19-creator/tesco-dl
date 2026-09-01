from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Asset, Client, PurchaseOrder, Quotation, Role, SamplingAssignment, SamplingOrder, Site, User
from ..security import require_user
from ..services.audit import add_audit
from ..services.identifiers import next_assignment_code, next_sampling_order_identifiers
from ..services.lab_operations import package_catalog

router = APIRouter(prefix="/operations", tags=["sampling operations"])
ALLOWED = {Role.OPERATIONS_MANAGER.value, Role.TECHNICAL_MANAGER.value, Role.MANAGEMENT.value, Role.SYSTEM_ADMIN.value}


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    site_id = user.site_id
    orders_stmt = select(SamplingOrder).order_by(SamplingOrder.created_at.desc())
    if user.role != Role.SYSTEM_ADMIN.value and site_id:
        orders_stmt = orders_stmt.where(SamplingOrder.site_id == site_id)
    orders = db.scalars(orders_stmt.limit(100)).all()
    clients = db.scalars(select(Client).where(Client.active.is_(True)).order_by(Client.name)).all()
    quotes = db.scalars(select(Quotation).where(Quotation.status == "ACTIVE").order_by(Quotation.number)).all()
    pos = db.scalars(select(PurchaseOrder).where(PurchaseOrder.status == "ACTIVE").order_by(PurchaseOrder.number)).all()
    assets = db.scalars(select(Asset).where(Asset.active.is_(True)).order_by(Asset.asset_code)).all()
    supervisors_stmt = select(User).where(User.role == Role.SAMPLING_SUPERVISOR.value, User.active.is_(True))
    samplers_stmt = select(User).where(User.role.in_([Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value]), User.active.is_(True))
    if user.role != Role.SYSTEM_ADMIN.value and site_id:
        supervisors_stmt = supervisors_stmt.where(User.site_id == site_id)
        samplers_stmt = samplers_stmt.where(User.site_id == site_id)
    supervisors = db.scalars(supervisors_stmt.order_by(User.full_name)).all()
    samplers = db.scalars(samplers_stmt.order_by(User.full_name)).all()
    return templates.TemplateResponse("operations_dashboard.html", {"request": request, "user": user, "orders": orders, "clients": clients, "quotes": quotes, "pos": pos, "assets": assets, "supervisors": supervisors, "samplers": samplers, "package_names": [p["name"] for p in package_catalog(db, user.site_id)]})


@router.post("/orders")
def create_order(
    request: Request,
    client_id: int = Form(...), quotation_id: str = Form(""), purchase_order_id: str = Form(""),
    supervisor_id: str = Form(""), title: str = Form("Sampling request"), priority: str = Form("Normal"),
    due_at: str = Form(""), notes: str = Form(""), db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    site = db.get(Site, user.site_id) if user.site_id else db.scalar(select(Site).where(Site.code == "DMM"))
    client = db.get(Client, client_id)
    quote = db.get(Quotation, int(quotation_id)) if quotation_id else None
    po = db.get(PurchaseOrder, int(purchase_order_id)) if purchase_order_id else None
    supervisor = db.get(User, int(supervisor_id)) if supervisor_id else None
    if not client or not client.active:
        raise ValueError("Active client is required")
    if quote and quote.client_id != client_id:
        raise ValueError("Quotation does not belong to the selected client")
    if po and po.client_id != client_id:
        raise ValueError("Purchase order does not belong to the selected client")
    if supervisor and supervisor.role != Role.SAMPLING_SUPERVISOR.value:
        raise ValueError("Selected user is not a sampling supervisor")
    if supervisor and supervisor.site_id and supervisor.site_id != site.id:
        raise ValueError("Sampling supervisor must belong to the order site")
    order_number, _ = next_sampling_order_identifiers(db, site)
    order = SamplingOrder(
        order_number=order_number, site_id=site.id, client_id=client_id,
        quotation_id=int(quotation_id) if quotation_id else None,
        purchase_order_id=int(purchase_order_id) if purchase_order_id else None,
        created_by_id=user.id, supervisor_id=int(supervisor_id) if supervisor_id else None,
        title=title.strip() or "Sampling request", priority=priority, due_at=datetime.fromisoformat(due_at) if due_at else None,
        notes=notes.strip(), status="OPEN",
    )
    db.add(order); db.flush()
    add_audit(db, actor=user, request=request, action="SAMPLING_ORDER_CREATED", entity_type="SamplingOrder", entity_id=order.id, summary=f"Created {order.order_number}", details={"client_id": client_id, "supervisor_id": supervisor_id})
    db.commit()
    return RedirectResponse(f"/operations#order-{order.id}", status_code=303)


@router.post("/orders/{order_id}/assignments")
def add_assignment(
    order_id: int, request: Request, asset_id: str = Form(""), assigned_sampler_id: str = Form(""),
    source_party: str = Form("TSCO"), requested_package: str = Form("Routine Test"),
    sampling_point: str = Form("Main Tank Bottom"), container_count: int = Form(1), instructions: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, ALLOWED)
    order = db.get(SamplingOrder, order_id)
    if not order:
        return RedirectResponse("/operations", status_code=303)
    source_party = source_party.strip().upper()
    if source_party not in {"TSCO", "CLIENT"}:
        raise ValueError("Source party must be TSCO or CLIENT")
    asset = db.get(Asset, int(asset_id)) if asset_id else None
    sampler_id = int(assigned_sampler_id) if assigned_sampler_id else None
    sampler = db.get(User, sampler_id) if sampler_id else None
    if asset and asset.client_id != order.client_id:
        raise ValueError("Asset does not belong to the order client")
    if sampler and sampler.role not in {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}:
        raise ValueError("Selected user is not a sampler")
    if source_party == "CLIENT" and sampler and sampler.client_id != order.client_id:
        raise ValueError("Client-side sampler must belong to the order client")
    if source_party == "TSCO" and sampler and sampler.client_id is not None:
        raise ValueError("TSCO assignment cannot be allocated to a client-side account")
    if sampler and sampler.site_id and sampler.site_id != order.site_id:
        raise ValueError("Sampler and sampling order must belong to the same site")
    assignment = SamplingAssignment(
        order_id=order.id, asset_id=int(asset_id) if asset_id else None, assigned_sampler_id=sampler_id,
        assignment_code=next_assignment_code(order.site), source_party=source_party,
        requested_package=requested_package, sampling_point=sampling_point, container_count=max(1, container_count),
        status="ASSIGNED" if sampler_id else "UNASSIGNED", instructions=instructions.strip(),
        assigned_at=datetime.utcnow() if sampler_id else None,
    )
    db.add(assignment); db.flush()
    add_audit(db, actor=user, request=request, action="SAMPLING_ASSIGNMENT_CREATED", entity_type="SamplingAssignment", entity_id=assignment.id, summary=f"{order.order_number} / {assignment.assignment_code}", details={"source_party": source_party, "sampler_id": sampler_id})
    db.commit()
    return RedirectResponse(f"/operations#order-{order.id}", status_code=303)
