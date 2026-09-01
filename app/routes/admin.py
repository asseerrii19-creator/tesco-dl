from __future__ import annotations

import csv
import io
import json
import secrets
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import (
    Asset,
    AuditLog,
    Client,
    ClientUnit,
    ControlledDocument,
    Department,
    PurchaseOrder,
    SamplingOrder,
    Quotation,
    Role,
    SampleRequest,
    Site,
    TestPackageConfig,
    WorkflowDefinition,
    WorkflowStep,
    ApprovalPolicy,
    IntegrationQueueItem,
    User,
    UserClientAssignment,
    UserClientUnitAssignment,
)
from ..security import hash_password, require_user
from ..services.audit import add_audit

router = APIRouter(prefix="/admin", tags=["administration"])
ALLOWED = {Role.SYSTEM_ADMIN.value}
ROLE_OPTIONS = [role.value for role in Role]


def _admin(request: Request, db: Session) -> User:
    return require_user(request, db, ALLOWED)


def _redirect(path: str, *, ok: str = "", error: str = "") -> RedirectResponse:
    params = {}
    if ok:
        params["ok"] = ok
    if error:
        params["error"] = error
    return RedirectResponse(path + (("?" + urlencode(params)) if params else ""), status_code=303)


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    counts = {
        "clients": db.scalar(select(func.count()).select_from(Client)) or 0,
        "sites": db.scalar(select(func.count()).select_from(Site)) or 0,
        "departments": db.scalar(select(func.count()).select_from(Department).where(Department.active.is_(True))) or 0,
        "client_units": db.scalar(select(func.count()).select_from(ClientUnit).where(ClientUnit.active.is_(True))) or 0,
        "workflows": db.scalar(select(func.count()).select_from(WorkflowDefinition).where(WorkflowDefinition.active.is_(True))) or 0,
        "integration_pending": db.scalar(select(func.count()).select_from(IntegrationQueueItem).where(IntegrationQueueItem.status.in_(["PENDING","FAILED"]))) or 0,
        "documents": db.scalar(select(func.count()).select_from(ControlledDocument).where(ControlledDocument.status == "ACTIVE")) or 0,
        "packages": db.scalar(select(func.count()).select_from(TestPackageConfig).where(TestPackageConfig.active.is_(True))) or 0,
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "assets": db.scalar(select(func.count()).select_from(Asset)) or 0,
        "samples": db.scalar(select(func.count()).select_from(SampleRequest)) or 0,
        "orders": db.scalar(select(func.count()).select_from(SamplingOrder)) or 0,
        "open_orders": db.scalar(select(func.count()).select_from(SamplingOrder).where(SamplingOrder.status != "COMPLETED")) or 0,
        "intake_pending": db.scalar(select(func.count()).select_from(SampleRequest).where(SampleRequest.status.in_(["SUBMITTED", "RETURNED", "ACCEPTED", "AWAITING_RECEIPT"]))) or 0,
        "lab_active": db.scalar(select(func.count()).select_from(SampleRequest).where(SampleRequest.status.in_(["RECEIVED", "REGISTERED", "TESTING"]))) or 0,
        "technical_review": db.scalar(select(func.count()).select_from(SampleRequest).where(SampleRequest.status == "TECHNICAL_REVIEW")) or 0,
    }
    sites = db.scalars(select(Site).order_by(Site.code)).all()
    recent = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(12)).all()
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request, "user": user, "counts": counts, "sites": sites, "recent": recent},
    )


@router.get("/clients")
def clients_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    clients = db.scalars(select(Client).order_by(Client.active.desc(), Client.name)).all()
    return templates.TemplateResponse(
        "admin_clients.html",
        {"request": request, "user": user, "clients": clients, "ok": ok, "error": error},
    )


@router.post("/clients")
def create_client(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    code = code.strip().upper()
    name = name.strip()
    if not code or not name:
        return _redirect("/admin/clients", error="Company code and name are required")
    client = Client(
        code=code,
        name=name,
        contact_email=contact_email.strip(),
        contact_phone=contact_phone.strip(),
        notes=notes.strip(),
    )
    db.add(client)
    try:
        db.flush()
        add_audit(
            db,
            actor=user,
            request=request,
            action="CLIENT_CREATED",
            entity_type="Client",
            entity_id=client.id,
            summary=f"Created client {client.code} — {client.name}",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/clients", error="Company code already exists")
    return _redirect("/admin/clients", ok="Company added")


@router.post("/clients/{client_id}/update")
def update_client(
    client_id: int,
    request: Request,
    name: str = Form(...),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _admin(request, db)
    client = db.get(Client, client_id)
    if not client:
        return _redirect("/admin/clients", error="Company not found")
    client.name = name.strip()
    client.contact_email = contact_email.strip()
    client.contact_phone = contact_phone.strip()
    client.notes = notes.strip()
    add_audit(
        db,
        actor=user,
        request=request,
        action="CLIENT_UPDATED",
        entity_type="Client",
        entity_id=client.id,
        summary=f"Updated client {client.code}",
    )
    db.commit()
    return _redirect("/admin/clients", ok="Company updated")


@router.post("/clients/{client_id}/toggle")
def toggle_client(client_id: int, request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    client = db.get(Client, client_id)
    if client:
        client.active = not client.active
        add_audit(
            db,
            actor=user,
            request=request,
            action="CLIENT_STATUS_CHANGED",
            entity_type="Client",
            entity_id=client.id,
            summary=f"{client.code} set to {'Active' if client.active else 'Inactive'}",
        )
        db.commit()
    return RedirectResponse("/admin/clients", status_code=303)


@router.get("/users")
def users_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    users = db.scalars(select(User).order_by(User.active.desc(), User.full_name)).all()
    clients = db.scalars(select(Client).where(Client.active.is_(True)).order_by(Client.name)).all()
    sites = db.scalars(select(Site).order_by(Site.code)).all()
    departments = db.scalars(select(Department).order_by(Department.name)).all()
    client_units = db.scalars(select(ClientUnit).where(ClientUnit.active.is_(True)).order_by(ClientUnit.client_id, ClientUnit.unit_type, ClientUnit.name)).all()
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "clients": clients,
            "sites": sites,
            "departments": departments,
            "client_units": client_units,
            "roles": ROLE_OPTIONS,
            "ok": ok,
            "error": error,
        },
    )


@router.post("/users")
def create_user(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    job_title: str = Form(""),
    phone: str = Form(""),
    site_id: str = Form(""),
    department_id: str = Form(""),
    client_id: str = Form(""),
    assigned_client_ids: list[int] = Form(default=[]),
    assigned_client_unit_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    email = email.lower().strip()
    if role not in ROLE_OPTIONS:
        return _redirect("/admin/users", error="Invalid role")
    if len(password) < 10:
        return _redirect("/admin/users", error="Temporary password must be at least 10 characters")
    linked_client_id = int(client_id) if client_id else None
    linked_site_id = int(site_id) if site_id else None
    if role in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} and not linked_client_id:
        return _redirect("/admin/users", error="Client users must be linked to a company")
    new_user = User(
        email=email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role=role,
        job_title=job_title.strip(),
        phone=phone.strip(),
        client_id=linked_client_id if role in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} else None,
        site_id=linked_site_id,
        department_id=int(department_id) if department_id else None,
        must_change_password=True,
    )
    db.add(new_user)
    try:
        db.flush()
        if role not in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}:
            for cid in sorted(set(assigned_client_ids)):
                db.add(UserClientAssignment(user_id=new_user.id, client_id=cid))
        else:
            valid_units = db.scalars(select(ClientUnit).where(ClientUnit.id.in_(set(assigned_client_unit_ids)), ClientUnit.client_id == linked_client_id)).all() if assigned_client_unit_ids else []
            for unit in valid_units:
                db.add(UserClientUnitAssignment(user_id=new_user.id, client_unit_id=unit.id))
        add_audit(
            db,
            actor=actor,
            request=request,
            action="USER_CREATED",
            entity_type="User",
            entity_id=new_user.id,
            summary=f"Created {new_user.email} as {new_user.role}",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/users", error="Email already exists or assignment is duplicated")
    return _redirect("/admin/users", ok="User created")


@router.post("/users/{user_id}/toggle")
def toggle_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _admin(request, db)
    target = db.get(User, user_id)
    if target and target.id != actor.id:
        target.active = not target.active
        add_audit(
            db,
            actor=actor,
            request=request,
            action="USER_STATUS_CHANGED",
            entity_type="User",
            entity_id=target.id,
            summary=f"{target.email} set to {'Active' if target.active else 'Inactive'}",
        )
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)




@router.post("/users/{user_id}/profile")
def update_user_profile(
    user_id: int,
    request: Request,
    full_name: str = Form(...),
    role: str = Form(...),
    job_title: str = Form(""),
    phone: str = Form(""),
    site_id: str = Form(""),
    department_id: str = Form(""),
    client_id: str = Form(""),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    target = db.get(User, user_id)
    if not target:
        return _redirect("/admin/users", error="User not found")
    if role not in ROLE_OPTIONS:
        return _redirect("/admin/users", error="Invalid role")
    linked_client_id = int(client_id) if client_id else None
    if role in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} and not linked_client_id:
        return _redirect("/admin/users", error="Client accounts must be linked to a company")
    target.full_name = full_name.strip()
    target.role = role
    target.job_title = job_title.strip()
    target.phone = phone.strip()
    target.site_id = int(site_id) if site_id else None
    target.department_id = int(department_id) if department_id else None
    target.client_id = linked_client_id if role in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} else None
    if target.client_id is not None:
        for row in list(target.client_assignments):
            db.delete(row)
        for row in list(target.client_unit_assignments):
            if row.client_unit.client_id != target.client_id:
                db.delete(row)
    else:
        for row in list(target.client_unit_assignments):
            db.delete(row)
    add_audit(db, actor=actor, request=request, action="USER_PROFILE_UPDATED", entity_type="User", entity_id=target.id, summary=f"Updated role/site profile for {target.email}")
    db.commit()
    return _redirect("/admin/users", ok="User profile updated")

@router.post("/users/{user_id}/password")
def reset_password(
    user_id: int,
    request: Request,
    temporary_password: str = Form(...),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    target = db.get(User, user_id)
    if not target:
        return _redirect("/admin/users", error="User not found")
    if len(temporary_password) < 10:
        return _redirect("/admin/users", error="Temporary password must be at least 10 characters")
    target.password_hash = hash_password(temporary_password)
    target.must_change_password = True
    add_audit(
        db,
        actor=actor,
        request=request,
        action="PASSWORD_RESET",
        entity_type="User",
        entity_id=target.id,
        summary=f"Temporary password issued for {target.email}",
    )
    db.commit()
    return _redirect("/admin/users", ok="Temporary password set")


@router.post("/users/{user_id}/assignments")
def update_assignments(
    user_id: int,
    request: Request,
    assigned_client_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    target = db.get(User, user_id)
    if not target or target.role in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value}:
        return _redirect("/admin/users", error="Assignments apply to employee users only")
    existing = db.scalars(select(UserClientAssignment).where(UserClientAssignment.user_id == target.id)).all()
    for row in existing:
        db.delete(row)
    for cid in sorted(set(assigned_client_ids)):
        db.add(UserClientAssignment(user_id=target.id, client_id=cid))
    add_audit(
        db,
        actor=actor,
        request=request,
        action="CLIENT_ASSIGNMENTS_UPDATED",
        entity_type="User",
        entity_id=target.id,
        summary=f"Updated company scope for {target.email}",
        details={"client_ids": assigned_client_ids},
    )
    db.commit()
    return _redirect("/admin/users", ok="Company assignments updated")


@router.post("/users/{user_id}/client-unit-scope")
def update_client_unit_scope(
    user_id: int,
    request: Request,
    assigned_client_unit_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    target = db.get(User, user_id)
    if not target or target.role not in {Role.CLIENT.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} or not target.client_id:
        return _redirect("/admin/users", error="Unit scope applies to client accounts only")
    existing = db.scalars(select(UserClientUnitAssignment).where(UserClientUnitAssignment.user_id == target.id)).all()
    for row in existing:
        db.delete(row)
    valid_units = db.scalars(
        select(ClientUnit).where(
            ClientUnit.id.in_(set(assigned_client_unit_ids)),
            ClientUnit.client_id == target.client_id,
            ClientUnit.active.is_(True),
        )
    ).all() if assigned_client_unit_ids else []
    for unit in valid_units:
        db.add(UserClientUnitAssignment(user_id=target.id, client_unit_id=unit.id))
    add_audit(
        db, actor=actor, request=request, action="CLIENT_UNIT_SCOPE_UPDATED", entity_type="User", entity_id=target.id,
        summary=f"Updated organization scope for {target.email}", details={"client_unit_ids": [u.id for u in valid_units]},
    )
    db.commit()
    return _redirect("/admin/users", ok="Client organization scope updated")


@router.get("/commercial")
def commercial_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    clients = db.scalars(select(Client).where(Client.active.is_(True)).order_by(Client.name)).all()
    quotes = db.scalars(select(Quotation).order_by(Quotation.id.desc()).limit(150)).all()
    pos = db.scalars(select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(150)).all()
    return templates.TemplateResponse(
        "admin_commercial.html",
        {"request": request, "user": user, "clients": clients, "quotes": quotes, "pos": pos, "ok": ok, "error": error},
    )


@router.post("/commercial/quotation")
def create_quotation(
    request: Request,
    client_id: int = Form(...),
    number: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    quote = Quotation(client_id=client_id, number=number.strip(), description=description.strip())
    db.add(quote)
    try:
        db.flush()
        add_audit(db, actor=actor, request=request, action="QUOTATION_CREATED", entity_type="Quotation", entity_id=quote.id, summary=f"Created quotation {quote.number}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/commercial", error="Quotation already exists for this company")
    return _redirect("/admin/commercial", ok="Quotation added")


@router.post("/commercial/po")
def create_po(
    request: Request,
    client_id: int = Form(...),
    number: str = Form(...),
    quotation_id: str = Form(""),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    po = PurchaseOrder(client_id=client_id, number=number.strip(), quotation_id=int(quotation_id) if quotation_id else None)
    db.add(po)
    try:
        db.flush()
        add_audit(db, actor=actor, request=request, action="PO_CREATED", entity_type="PurchaseOrder", entity_id=po.id, summary=f"Created PO {po.number}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/commercial", error="PO already exists for this company")
    return _redirect("/admin/commercial", ok="Purchase order added")


@router.get("/assets")
def assets_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    clients = db.scalars(select(Client).where(Client.active.is_(True)).order_by(Client.name)).all()
    client_units = db.scalars(select(ClientUnit).where(ClientUnit.active.is_(True)).order_by(ClientUnit.client_id, ClientUnit.unit_type, ClientUnit.name)).all()
    assets = db.scalars(select(Asset).order_by(Asset.id.desc()).limit(250)).all()
    return templates.TemplateResponse(
        "admin_assets.html",
        {"request": request, "user": user, "clients": clients, "client_units": client_units, "assets": assets, "ok": ok, "error": error},
    )


@router.post("/assets")
def create_asset(
    request: Request,
    client_id: int = Form(...),
    client_unit_id: str = Form(""),
    asset_code: str = Form(...),
    serial_number: str = Form(...),
    equipment_type: str = Form("Power Transformer"),
    manufacturer: str = Form(""),
    voltage_kv: str = Form(""),
    rated_mva: str = Form(""),
    station_name: str = Form(""),
    asset_location_label: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    unit_id = int(client_unit_id) if client_unit_id else None
    if unit_id:
        unit = db.get(ClientUnit, unit_id)
        if not unit or unit.client_id != client_id:
            return _redirect("/admin/assets", error="Organization unit must belong to the selected company")
    def f(value: str):
        return float(value) if value.strip() else None
    asset = Asset(
        client_id=client_id,
        client_unit_id=unit_id,
        asset_code=asset_code.strip(),
        serial_number=serial_number.strip(),
        equipment_type=equipment_type.strip(),
        manufacturer=manufacturer.strip(),
        voltage_kv=f(voltage_kv),
        rated_mva=f(rated_mva),
        station_name=station_name.strip(),
        asset_location_label=asset_location_label.strip(),
        latitude=f(latitude),
        longitude=f(longitude),
    )
    db.add(asset)
    try:
        db.flush()
        add_audit(db, actor=actor, request=request, action="ASSET_CREATED", entity_type="Asset", entity_id=asset.id, summary=f"Created asset {asset.asset_code}")
        db.commit()
    except (IntegrityError, ValueError):
        db.rollback()
        return _redirect("/admin/assets", error="Asset code exists or numeric fields are invalid")
    return _redirect("/admin/assets", ok="Asset added")


@router.post("/assets/{asset_id}/toggle")
def toggle_asset(asset_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _admin(request, db)
    asset = db.get(Asset, asset_id)
    if asset:
        asset.active = not asset.active
        add_audit(db, actor=actor, request=request, action="ASSET_STATUS_CHANGED", entity_type="Asset", entity_id=asset.id, summary=f"{asset.asset_code} set to {'Active' if asset.active else 'Inactive'}")
        db.commit()
    return RedirectResponse("/admin/assets", status_code=303)


@router.get("/import")
def import_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    return templates.TemplateResponse(
        "admin_import.html",
        {"request": request, "user": user, "result": None, "errors": []},
    )


@router.post("/import")
def import_master_data(
    request: Request,
    import_type: str = Form(...),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    try:
        raw = csv_file.file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return templates.TemplateResponse(
            "admin_import.html",
            {"request": request, "user": actor, "result": None, "errors": ["CSV must use UTF-8 encoding"]},
            status_code=400,
        )
    reader = csv.DictReader(io.StringIO(raw))
    inserted = 0
    skipped = 0
    errors: list[str] = []

    def num(value: str | None):
        return float(value) if value and value.strip() else None

    for row_number, row in enumerate(reader, start=2):
        try:
            if import_type == "clients":
                code = (row.get("code") or "").strip().upper()
                name = (row.get("name") or "").strip()
                if not code or not name:
                    raise ValueError("code and name are required")
                if db.scalar(select(Client).where(Client.code == code)):
                    skipped += 1
                    continue
                db.add(
                    Client(
                        code=code,
                        name=name,
                        contact_email=(row.get("contact_email") or "").strip(),
                        contact_phone=(row.get("contact_phone") or "").strip(),
                        notes=(row.get("notes") or "").strip(),
                    )
                )
                db.flush()
                inserted += 1
            elif import_type == "assets":
                client_code = (row.get("client_code") or "").strip().upper()
                asset_code = (row.get("asset_code") or "").strip()
                serial_number = (row.get("serial_number") or "").strip()
                client = db.scalar(select(Client).where(Client.code == client_code))
                if not client:
                    raise ValueError(f"unknown client_code {client_code}")
                if not asset_code or not serial_number:
                    raise ValueError("asset_code and serial_number are required")
                if db.scalar(select(Asset).where(Asset.client_id == client.id, Asset.asset_code == asset_code)):
                    skipped += 1
                    continue
                db.add(
                    Asset(
                        client_id=client.id,
                        asset_code=asset_code,
                        serial_number=serial_number,
                        equipment_type=(row.get("equipment_type") or "Power Transformer").strip(),
                        manufacturer=(row.get("manufacturer") or "").strip(),
                        voltage_kv=num(row.get("voltage_kv")),
                        rated_mva=num(row.get("rated_mva")),
                        station_name=(row.get("station_name") or "").strip(),
                        asset_location_label=(row.get("asset_location_label") or "").strip(),
                        latitude=num(row.get("latitude")),
                        longitude=num(row.get("longitude")),
                    )
                )
                db.flush()
                inserted += 1
            else:
                raise ValueError("unsupported import type")
        except (ValueError, IntegrityError) as exc:
            db.rollback()
            errors.append(f"Row {row_number}: {exc}")
            # A rollback clears prior uncommitted rows; commit successful rows per batch below is avoided.
            # Restart the count conservatively and stop to prevent a misleading partial import.
            inserted = 0
            break

    if not errors:
        add_audit(
            db,
            actor=actor,
            request=request,
            action="MASTER_DATA_IMPORTED",
            entity_type=import_type,
            summary=f"Imported {inserted} {import_type}; skipped {skipped}",
            details={"filename": csv_file.filename, "inserted": inserted, "skipped": skipped},
        )
        db.commit()
    return templates.TemplateResponse(
        "admin_import.html",
        {
            "request": request,
            "user": actor,
            "result": {"inserted": inserted, "skipped": skipped, "type": import_type} if not errors else None,
            "errors": errors,
        },
        status_code=400 if errors else 200,
    )


@router.get("/audit")
def audit_page(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            AuditLog.summary.ilike(term) | AuditLog.action.ilike(term) | AuditLog.entity_type.ilike(term)
        )
    rows = db.scalars(stmt.limit(500)).all()
    return templates.TemplateResponse("admin_audit.html", {"request": request, "user": user, "rows": rows, "q": q})


DOC_DIR = Path(__file__).resolve().parents[1] / "data" / "controlled_documents"
DOC_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/sites")
def sites_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    sites = db.scalars(select(Site).order_by(Site.active.desc(), Site.code)).all()
    return templates.TemplateResponse("admin_sites.html", {"request": request, "user": user, "sites": sites, "ok": ok, "error": error})


@router.post("/sites")
def create_site(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    laboratory_name: str = Form(...),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    code = code.strip().upper()
    if not code or not name.strip() or not laboratory_name.strip():
        return _redirect("/admin/sites", error="Site code, name and laboratory name are required")
    site = Site(code=code, name=name.strip(), laboratory_name=laboratory_name.strip(), active=True)
    db.add(site)
    try:
        db.flush()
        add_audit(db, actor=actor, request=request, action="SITE_CREATED", entity_type="Site", entity_id=site.id, summary=f"Created site {site.code} — {site.name}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/sites", error="Site code already exists")
    return _redirect("/admin/sites", ok="Site added")


@router.post("/sites/{site_id}/update")
def update_site(site_id: int, request: Request, name: str = Form(...), laboratory_name: str = Form(...), db: Session = Depends(get_db)):
    actor = _admin(request, db)
    site = db.get(Site, site_id)
    if not site:
        return _redirect("/admin/sites", error="Site not found")
    site.name = name.strip()
    site.laboratory_name = laboratory_name.strip()
    add_audit(db, actor=actor, request=request, action="SITE_UPDATED", entity_type="Site", entity_id=site.id, summary=f"Updated site {site.code}")
    db.commit()
    return _redirect("/admin/sites", ok="Site updated")


@router.post("/sites/{site_id}/toggle")
def toggle_site(site_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _admin(request, db)
    site = db.get(Site, site_id)
    if site:
        site.active = not site.active
        add_audit(db, actor=actor, request=request, action="SITE_STATUS_CHANGED", entity_type="Site", entity_id=site.id, summary=f"{site.code} set to {'Active' if site.active else 'Inactive'}")
        db.commit()
    return RedirectResponse("/admin/sites", status_code=303)


@router.get("/documents")
def documents_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    documents = db.scalars(select(ControlledDocument).order_by(ControlledDocument.created_at.desc())).all()
    sites = db.scalars(select(Site).order_by(Site.code)).all()
    return templates.TemplateResponse("admin_documents.html", {"request": request, "user": user, "documents": documents, "sites": sites, "ok": ok, "error": error})


@router.post("/documents")
def upload_document(
    request: Request,
    document_type: str = Form(...),
    code: str = Form(...),
    title: str = Form(...),
    revision: str = Form("00"),
    effective_date: str = Form(""),
    site_id: str = Form(""),
    notes: str = Form(""),
    document_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    doc_type = document_type.strip().upper()
    if doc_type not in {"SOP", "METHOD", "EOP", "QUICK GUIDE", "FORM", "OTHER"}:
        return _redirect("/admin/documents", error="Unsupported document type")
    clean_code = code.strip().upper()
    clean_revision = revision.strip() or "00"
    if not clean_code or not title.strip() or not document_file.filename:
        return _redirect("/admin/documents", error="Document code, title and file are required")
    suffix = Path(document_file.filename).suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".xlsx", ".xls", ".txt"}:
        return _redirect("/admin/documents", error="Allowed files: PDF, Word, Excel or TXT")
    linked_site_id = int(site_id) if site_id else None
    # Controlled revision behavior: a new ACTIVE revision supersedes previous active revisions of the same code/scope.
    previous_stmt = select(ControlledDocument).where(ControlledDocument.code == clean_code, ControlledDocument.status == "ACTIVE")
    if linked_site_id is None:
        previous_stmt = previous_stmt.where(ControlledDocument.site_id.is_(None))
    else:
        previous_stmt = previous_stmt.where(ControlledDocument.site_id == linked_site_id)
    for previous in db.scalars(previous_stmt).all():
        previous.status = "SUPERSEDED"
    stored = f"{clean_code.replace('/', '-')}_{clean_revision}_{secrets.token_hex(5)}{suffix}"
    path = DOC_DIR / stored
    path.write_bytes(document_file.file.read())
    doc = ControlledDocument(
        site_id=linked_site_id, document_type=doc_type, code=clean_code, title=title.strip(), revision=clean_revision,
        status="ACTIVE", effective_date=effective_date.strip(), original_filename=Path(document_file.filename).name,
        stored_filename=stored, notes=notes.strip(), uploaded_by_id=actor.id,
    )
    db.add(doc); db.flush()
    add_audit(db, actor=actor, request=request, action="CONTROLLED_DOCUMENT_UPLOADED", entity_type="ControlledDocument", entity_id=doc.id, summary=f"{doc.code} Rev {doc.revision} uploaded")
    db.commit()
    return _redirect("/admin/documents", ok="Controlled document published")


@router.post("/documents/{document_id}/status")
def document_status(document_id: int, request: Request, status: str = Form(...), db: Session = Depends(get_db)):
    actor = _admin(request, db)
    doc = db.get(ControlledDocument, document_id)
    new_status = status.strip().upper()
    if not doc or new_status not in {"ACTIVE", "SUPERSEDED", "WITHDRAWN"}:
        return _redirect("/admin/documents", error="Invalid document or status")
    doc.status = new_status
    add_audit(db, actor=actor, request=request, action="DOCUMENT_STATUS_CHANGED", entity_type="ControlledDocument", entity_id=doc.id, summary=f"{doc.code} Rev {doc.revision} → {new_status}")
    db.commit()
    return _redirect("/admin/documents", ok="Document status updated")


@router.get("/test-packages")
def test_packages_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    packages = db.scalars(select(TestPackageConfig).order_by(TestPackageConfig.active.desc(), TestPackageConfig.name)).all()
    for package in packages:
        try:
            rows = json.loads(package.tests_json or "[]")
        except Exception:
            rows = []
        package.tests_text = "\n".join(
            " | ".join([str(row.get("test", "")), str(row.get("method", "")), str(row.get("station", "")), str(row.get("unit", ""))]).rstrip(" |")
            for row in rows if isinstance(row, dict)
        )
    sites = db.scalars(select(Site).order_by(Site.code)).all()
    return templates.TemplateResponse("admin_test_packages.html", {"request": request, "user": user, "packages": packages, "sites": sites, "ok": ok, "error": error})


def _tests_from_lines(raw: str) -> list[dict]:
    tests = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        parts += [""] * (4 - len(parts))
        tests.append({"test": parts[0], "method": parts[1], "station": parts[2], "unit": parts[3]})
    return tests


@router.post("/test-packages")
def create_test_package(
    request: Request,
    code: str = Form(...), name: str = Form(...), scope: str = Form("GENERAL"), site_id: str = Form(""), tests: str = Form(""),
    db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    item = TestPackageConfig(
        code=code.strip().upper(), name=name.strip(), scope=scope.strip().upper() or "GENERAL",
        site_id=int(site_id) if site_id else None, tests_json=json.dumps(_tests_from_lines(tests), ensure_ascii=False), active=True,
    )
    if not item.code or not item.name:
        return _redirect("/admin/test-packages", error="Package code and name are required")
    db.add(item)
    try:
        db.flush()
        add_audit(db, actor=actor, request=request, action="TEST_PACKAGE_CREATED", entity_type="TestPackageConfig", entity_id=item.id, summary=f"Created test package {item.name}")
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect("/admin/test-packages", error="Package code already exists")
    return _redirect("/admin/test-packages", ok="Test package added")


@router.post("/test-packages/{package_id}/update")
def update_test_package(
    package_id: int, request: Request, name: str = Form(...), scope: str = Form("GENERAL"), site_id: str = Form(""), tests: str = Form(""), db: Session = Depends(get_db),
):
    actor = _admin(request, db)
    item = db.get(TestPackageConfig, package_id)
    if not item:
        return _redirect("/admin/test-packages", error="Package not found")
    item.name = name.strip(); item.scope = scope.strip().upper() or "GENERAL"; item.site_id = int(site_id) if site_id else None
    item.tests_json = json.dumps(_tests_from_lines(tests), ensure_ascii=False)
    add_audit(db, actor=actor, request=request, action="TEST_PACKAGE_UPDATED", entity_type="TestPackageConfig", entity_id=item.id, summary=f"Updated test package {item.code}")
    db.commit()
    return _redirect("/admin/test-packages", ok="Test package updated")


@router.post("/test-packages/{package_id}/toggle")
def toggle_test_package(package_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _admin(request, db)
    item = db.get(TestPackageConfig, package_id)
    if item:
        item.active = not item.active
        add_audit(db, actor=actor, request=request, action="TEST_PACKAGE_STATUS_CHANGED", entity_type="TestPackageConfig", entity_id=item.id, summary=f"{item.code} set to {'Active' if item.active else 'Inactive'}")
        db.commit()
    return RedirectResponse("/admin/test-packages", status_code=303)


@router.get("/master-data")
def master_data_page(request: Request, db: Session = Depends(get_db)):
    user = _admin(request, db)
    counts = {
        "sites": db.scalar(select(func.count()).select_from(Site)) or 0,
        "departments": db.scalar(select(func.count()).select_from(Department)) or 0,
        "clients": db.scalar(select(func.count()).select_from(Client)) or 0,
        "client_units": db.scalar(select(func.count()).select_from(ClientUnit)) or 0,
        "assets": db.scalar(select(func.count()).select_from(Asset)) or 0,
        "documents": db.scalar(select(func.count()).select_from(ControlledDocument)) or 0,
        "packages": db.scalar(select(func.count()).select_from(TestPackageConfig)) or 0,
        "workflows": db.scalar(select(func.count()).select_from(WorkflowDefinition)) or 0,
    }
    return templates.TemplateResponse("admin_master_data.html", {"request":request,"user":user,"counts":counts})


@router.get("/hierarchy")
def hierarchy_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user = _admin(request, db)
    sites = db.scalars(select(Site).order_by(Site.code)).all()
    departments = db.scalars(select(Department).order_by(Department.site_id, Department.name)).all()
    clients = db.scalars(select(Client).order_by(Client.name)).all()
    units = db.scalars(select(ClientUnit).order_by(ClientUnit.client_id, ClientUnit.parent_id, ClientUnit.name)).all()
    return templates.TemplateResponse("admin_hierarchy.html", {"request":request,"user":user,"sites":sites,"departments":departments,"clients":clients,"units":units,"ok":ok,"error":error})


@router.post("/hierarchy/departments")
def create_department(request: Request, code: str = Form(...), name: str = Form(...), site_id: str = Form(""), db: Session = Depends(get_db)):
    actor = _admin(request, db)
    item = Department(site_id=int(site_id) if site_id else None, code=code.strip().upper(), name=name.strip(), active=True)
    if not item.code or not item.name:
        return _redirect("/admin/hierarchy", error="Department code and name are required")
    db.add(item)
    try:
        db.flush(); add_audit(db, actor=actor, request=request, action="DEPARTMENT_CREATED", entity_type="Department", entity_id=item.id, summary=f"Created department {item.code} — {item.name}"); db.commit()
    except IntegrityError:
        db.rollback(); return _redirect("/admin/hierarchy", error="Department code already exists in this scope")
    return _redirect("/admin/hierarchy", ok="Department added")


@router.post("/hierarchy/departments/{item_id}/toggle")
def toggle_department(item_id: int, request: Request, db: Session = Depends(get_db)):
    actor=_admin(request,db); item=db.get(Department,item_id)
    if item:
        item.active=not item.active; add_audit(db,actor=actor,request=request,action="DEPARTMENT_STATUS_CHANGED",entity_type="Department",entity_id=item.id,summary=f"{item.code} set to {'Active' if item.active else 'Inactive'}"); db.commit()
    return RedirectResponse("/admin/hierarchy",status_code=303)


@router.post("/hierarchy/client-units")
def create_client_unit(request: Request, client_id: int = Form(...), unit_type: str = Form("SITE"), code: str = Form(...), name: str = Form(...), parent_id: str = Form(""), db: Session = Depends(get_db)):
    actor=_admin(request,db)
    parent=int(parent_id) if parent_id else None
    if parent:
        p=db.get(ClientUnit,parent)
        if not p or p.client_id != client_id:
            return _redirect("/admin/hierarchy", error="Parent unit must belong to the same client")
    item=ClientUnit(client_id=client_id,parent_id=parent,unit_type=unit_type.strip().upper() or "SITE",code=code.strip().upper(),name=name.strip(),active=True)
    db.add(item)
    try:
        db.flush(); add_audit(db,actor=actor,request=request,action="CLIENT_UNIT_CREATED",entity_type="ClientUnit",entity_id=item.id,summary=f"Created {item.unit_type} {item.code} for {item.client.name}"); db.commit()
    except IntegrityError:
        db.rollback(); return _redirect("/admin/hierarchy",error="Client unit code already exists for this client")
    return _redirect("/admin/hierarchy",ok="Client organization unit added")


@router.post("/hierarchy/client-units/{item_id}/toggle")
def toggle_client_unit(item_id:int, request:Request, db:Session=Depends(get_db)):
    actor=_admin(request,db); item=db.get(ClientUnit,item_id)
    if item:
        item.active=not item.active; add_audit(db,actor=actor,request=request,action="CLIENT_UNIT_STATUS_CHANGED",entity_type="ClientUnit",entity_id=item.id,summary=f"{item.code} set to {'Active' if item.active else 'Inactive'}"); db.commit()
    return RedirectResponse("/admin/hierarchy",status_code=303)


def _workflow_steps_from_lines(raw: str) -> list[dict]:
    rows=[]
    for i,line in enumerate(raw.splitlines(), start=1):
        line=line.strip()
        if not line: continue
        parts=[p.strip() for p in line.split("|")]; parts += [""]*(4-len(parts))
        flags={x.strip().lower() for x in parts[3].split(",") if x.strip()}
        rows.append({"step_order":i,"step_key":parts[0].lower().replace(" ","_"),"label":parts[1] or parts[0],"responsible_role":parts[2],"approval_required":"approval" in flags,"terminal":"terminal" in flags})
    return rows


@router.get("/workflows")
def workflows_page(request: Request, ok: str = "", error: str = "", db: Session = Depends(get_db)):
    user=_admin(request,db); sites=db.scalars(select(Site).order_by(Site.code)).all(); flows=db.scalars(select(WorkflowDefinition).order_by(WorkflowDefinition.active.desc(), WorkflowDefinition.code, WorkflowDefinition.version.desc())).all(); policies=db.scalars(select(ApprovalPolicy).order_by(ApprovalPolicy.active.desc(),ApprovalPolicy.code)).all()
    for f in flows:
        f.steps_text="\n".join(f"{x.step_key} | {x.label} | {x.responsible_role} | {','.join([v for v,b in [('approval',x.approval_required),('terminal',x.terminal)] if b])}" for x in f.steps)
    for p in policies:
        try: rows=json.loads(p.stages_json or "[]")
        except Exception: rows=[]
        p.stages_text="\n".join(f"{x.get('stage','')} | {x.get('role','')}" for x in rows if isinstance(x,dict))
    return templates.TemplateResponse("admin_workflows.html",{"request":request,"user":user,"sites":sites,"flows":flows,"policies":policies,"roles":ROLE_OPTIONS,"ok":ok,"error":error})


@router.post("/workflows")
def create_workflow(request:Request, code:str=Form(...), name:str=Form(...), sample_type:str=Form("GENERAL"), site_id:str=Form(""), steps:str=Form(""), db:Session=Depends(get_db)):
    actor=_admin(request,db); sid=int(site_id) if site_id else None; clean=code.strip().upper(); version=(db.scalar(select(func.max(WorkflowDefinition.version)).where(WorkflowDefinition.code==clean, WorkflowDefinition.site_id==sid)) or 0)+1
    rows=_workflow_steps_from_lines(steps)
    if not clean or not name.strip() or len(rows)<2: return _redirect("/admin/workflows",error="Workflow requires a code, name and at least two steps")
    for old in db.scalars(select(WorkflowDefinition).where(WorkflowDefinition.code==clean, WorkflowDefinition.site_id==sid, WorkflowDefinition.active.is_(True))).all(): old.active=False
    flow=WorkflowDefinition(site_id=sid,code=clean,name=name.strip(),sample_type=sample_type.strip().upper() or "GENERAL",version=version,active=True); db.add(flow); db.flush()
    for row in rows: db.add(WorkflowStep(workflow_id=flow.id,**row))
    add_audit(db,actor=actor,request=request,action="WORKFLOW_PUBLISHED",entity_type="WorkflowDefinition",entity_id=flow.id,summary=f"Published {flow.code} v{flow.version}",details={"steps":rows}); db.commit()
    return _redirect("/admin/workflows",ok="Workflow version published")


@router.post("/workflows/{flow_id}/toggle")
def toggle_workflow(flow_id:int,request:Request,db:Session=Depends(get_db)):
    actor=_admin(request,db); flow=db.get(WorkflowDefinition,flow_id)
    if flow:
        flow.active=not flow.active; add_audit(db,actor=actor,request=request,action="WORKFLOW_STATUS_CHANGED",entity_type="WorkflowDefinition",entity_id=flow.id,summary=f"{flow.code} v{flow.version} set to {'Active' if flow.active else 'Inactive'}"); db.commit()
    return RedirectResponse("/admin/workflows",status_code=303)


def _approval_stages_from_lines(raw: str) -> list[dict]:
    rows=[]
    for line in raw.splitlines():
        line=line.strip()
        if not line: continue
        parts=[p.strip() for p in line.split("|")]; parts += [""]*(2-len(parts)); rows.append({"stage":parts[0],"role":parts[1]})
    return rows


@router.post("/workflows/approval-policies")
def create_approval_policy(request:Request, code:str=Form(...), name:str=Form(...), entity_type:str=Form("SAMPLE_REPORT"), site_id:str=Form(""), stages:str=Form(""), db:Session=Depends(get_db)):
    actor=_admin(request,db); sid=int(site_id) if site_id else None; clean=code.strip().upper(); rows=_approval_stages_from_lines(stages)
    if not clean or not name.strip() or not rows: return _redirect("/admin/workflows",error="Approval policy requires stages")
    old=db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.code==clean,ApprovalPolicy.site_id==sid))
    if old:
        old.name=name.strip(); old.entity_type=entity_type.strip().upper(); old.stages_json=json.dumps(rows,ensure_ascii=False); old.active=True; item=old
    else:
        item=ApprovalPolicy(site_id=sid,code=clean,name=name.strip(),entity_type=entity_type.strip().upper(),stages_json=json.dumps(rows,ensure_ascii=False),active=True); db.add(item); db.flush()
    add_audit(db,actor=actor,request=request,action="APPROVAL_POLICY_SAVED",entity_type="ApprovalPolicy",entity_id=item.id,summary=f"Saved approval policy {item.code}",details={"stages":rows}); db.commit(); return _redirect("/admin/workflows",ok="Approval policy saved")


@router.get("/integrations")
def integrations_page(request:Request,ok:str="",error:str="",db:Session=Depends(get_db)):
    user=_admin(request,db); rows=db.scalars(select(IntegrationQueueItem).order_by(IntegrationQueueItem.created_at.desc()).limit(300)).all(); sync_rows=db.scalars(select(__import__('app.models',fromlist=['LmsSyncLog']).LmsSyncLog).order_by(__import__('app.models',fromlist=['LmsSyncLog']).LmsSyncLog.created_at.desc()).limit(100)).all()
    return templates.TemplateResponse("admin_integrations.html",{"request":request,"user":user,"rows":rows,"sync_rows":sync_rows,"ok":ok,"error":error})


@router.post("/integrations/{item_id}/retry")
def retry_integration(item_id:int,request:Request,db:Session=Depends(get_db)):
    actor=_admin(request,db); item=db.get(IntegrationQueueItem,item_id)
    if not item: return _redirect("/admin/integrations",error="Queue item not found")
    from ..services.integration_queue import retry_item
    success=retry_item(db,item); add_audit(db,actor=actor,request=request,action="INTEGRATION_RETRY",entity_type="IntegrationQueueItem",entity_id=item.id,summary=f"{item.integration} {item.operation} → {item.status}"); db.commit(); return _redirect("/admin/integrations",ok="Integration retry completed" if success else "",error="Integration retry failed — review error" if not success else "")
