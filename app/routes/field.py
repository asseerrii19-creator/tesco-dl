from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Asset, Client, CustodyEvent, PurchaseOrder, Quotation, Role, SamplePhoto, SampleRequest, SampleStatus, SamplingAssignment, Site
from ..security import require_user
from ..services.barcodes import generate_assets
from ..services.identifiers import next_request_identifiers
from ..services.workflow import add_event
from ..services.audit import add_audit
from ..services.lab_operations import package_catalog
from ..services.scope import assigned_client_ids, can_access_client

router = APIRouter(prefix="/field", tags=["field"])
BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
BARCODE_DIR = BASE_DIR / "data" / "barcodes"
FIELD_ROLES = {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value, Role.SYSTEM_ADMIN.value}


def _float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, FIELD_ROLES)
    samples = db.scalars(
        select(SampleRequest).where(SampleRequest.sampler_id == user.id).order_by(SampleRequest.created_at.desc()).limit(50)
    ).all()
    assignments = db.scalars(
        select(SamplingAssignment).where(
            SamplingAssignment.assigned_sampler_id == user.id,
            SamplingAssignment.status.in_(["ASSIGNED", "IN_PROGRESS", "RETURNED"]),
        ).order_by(SamplingAssignment.created_at.desc()).limit(100)
    ).all()
    return templates.TemplateResponse("field_dashboard.html", {"request": request, "user": user, "samples": samples, "assignments": assignments})


@router.get("/new")
def new_sample(request: Request, assignment_id: int | None = None, code: str = "", db: Session = Depends(get_db)):
    user = require_user(request, db, FIELD_ROLES)
    assignment = None
    if assignment_id:
        assignment = db.get(SamplingAssignment, assignment_id)
    elif code.strip():
        assignment = db.scalar(select(SamplingAssignment).where(SamplingAssignment.assignment_code == code.strip().upper()))
    if assignment and user.role != Role.SYSTEM_ADMIN.value and assignment.assigned_sampler_id != user.id:
        assignment = None
    client_stmt = select(Client).where(Client.active.is_(True)).order_by(Client.name)
    allowed_client_ids = assigned_client_ids(db, user)
    if user.client_id:
        allowed_client_ids = {user.client_id}
    if user.role != Role.SYSTEM_ADMIN.value and allowed_client_ids:
        client_stmt = client_stmt.where(Client.id.in_(allowed_client_ids))
    clients = db.scalars(client_stmt).all()
    visible_ids = [client.id for client in clients]
    quote_stmt = select(Quotation).where(Quotation.status == "ACTIVE").order_by(Quotation.number)
    po_stmt = select(PurchaseOrder).where(PurchaseOrder.status == "ACTIVE").order_by(PurchaseOrder.number)
    asset_stmt = select(Asset).where(Asset.active.is_(True)).order_by(Asset.asset_code)
    if visible_ids:
        quote_stmt = quote_stmt.where(Quotation.client_id.in_(visible_ids))
        po_stmt = po_stmt.where(PurchaseOrder.client_id.in_(visible_ids))
        asset_stmt = asset_stmt.where(Asset.client_id.in_(visible_ids))
    elif user.role != Role.SYSTEM_ADMIN.value:
        quote_stmt = quote_stmt.where(False)
        po_stmt = po_stmt.where(False)
        asset_stmt = asset_stmt.where(False)
    quotes = db.scalars(quote_stmt).all()
    pos = db.scalars(po_stmt).all()
    assets = db.scalars(asset_stmt).all()
    return templates.TemplateResponse(
        "field_new.html",
        {"request": request, "user": user, "clients": clients, "quotes": quotes, "pos": pos, "assets": assets, "assignment": assignment, "package_names": [p["name"] for p in package_catalog()]},
    )


@router.post("/new")
def create_sample(
    request: Request,
    assignment_id: str = Form(""),
    client_id: int = Form(...),
    quotation_id: str = Form(""),
    purchase_order_id: str = Form(""),
    existing_asset_id: str = Form(""),
    asset_code: str = Form(""),
    serial_number: str = Form(""),
    equipment_type: str = Form("Transformer"),
    manufacturer: str = Form(""),
    station_name: str = Form(""),
    asset_location_label: str = Form(""),
    voltage_kv: str = Form(""),
    rated_mva: str = Form(""),
    sample_date_time: str = Form(...),
    sampling_point: str = Form(...),
    requested_package: str = Form(...),
    client_sample_reference: str = Form(""),
    oil_temperature_c: str = Form(""),
    ambient_temperature_c: str = Form(""),
    ambient_humidity_pct: str = Form(""),
    gps_latitude: str = Form(""),
    gps_longitude: str = Form(""),
    gps_accuracy_m: str = Form(""),
    field_notes: str = Form(""),
    container_count: int = Form(1),
    photo_kind: list[str] = Form(default=[]),
    photos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    user = require_user(request, db, FIELD_ROLES)
    assignment = db.get(SamplingAssignment, int(assignment_id)) if assignment_id else None
    if assignment and user.role != Role.SYSTEM_ADMIN.value and assignment.assigned_sampler_id != user.id:
        raise ValueError("Assignment is not allocated to this sampler")
    if assignment:
        client_id = assignment.order.client_id
        quotation_id = str(assignment.order.quotation_id or "")
        purchase_order_id = str(assignment.order.purchase_order_id or "")
        if assignment.asset_id:
            existing_asset_id = str(assignment.asset_id)
        requested_package = assignment.requested_package
        sampling_point = assignment.sampling_point
        container_count = assignment.container_count
    site = db.get(Site, user.site_id) if user.site_id else (assignment.order.site if assignment else db.scalar(select(Site).where(Site.code == "DMM")))
    client = db.get(Client, client_id)
    if not site or not client or not client.active:
        raise ValueError("Site or client missing")
    if not can_access_client(db, user, client_id):
        raise ValueError("Sampler is not assigned to this client")
    quote = db.get(Quotation, int(quotation_id)) if quotation_id else None
    po = db.get(PurchaseOrder, int(purchase_order_id)) if purchase_order_id else None
    if quote and quote.client_id != client_id:
        raise ValueError("Quotation does not belong to selected client")
    if po and po.client_id != client_id:
        raise ValueError("Purchase order does not belong to selected client")

    if existing_asset_id:
        asset = db.get(Asset, int(existing_asset_id))
        if not asset or asset.client_id != client_id:
            raise ValueError("Asset does not belong to selected client")
    else:
        if not asset_code.strip() or not serial_number.strip():
            raise ValueError("Asset code and serial number are required for a new asset")
        asset = Asset(
            client_id=client_id,
            asset_code=asset_code.strip(),
            serial_number=serial_number.strip(),
            equipment_type=equipment_type.strip(),
            manufacturer=manufacturer.strip(),
            station_name=station_name.strip(),
            asset_location_label=asset_location_label.strip(),
            voltage_kv=_float(voltage_kv),
            rated_mva=_float(rated_mva),
            latitude=_float(gps_latitude),
            longitude=_float(gps_longitude),
        )
        db.add(asset)
        db.flush()

    request_number, barcode_value, public_token = next_request_identifiers(db, site)
    sample = SampleRequest(
        request_number=request_number,
        public_token=public_token,
        barcode_value=barcode_value,
        status=SampleStatus.SUBMITTED.value,
        site_id=site.id,
        client_id=client_id,
        quotation_id=quote.id if quote else None,
        purchase_order_id=po.id if po else None,
        asset_id=asset.id,
        sampler_id=user.id,
        sampling_assignment_id=assignment.id if assignment else None,
        submission_channel="CLIENT_FIELD" if user.role in {Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} else "TSCO_FIELD",
        sample_date_time=datetime.fromisoformat(sample_date_time),
        sampling_point=sampling_point.strip(),
        requested_package=requested_package.strip(),
        client_sample_reference=client_sample_reference.strip(),
        oil_temperature_c=_float(oil_temperature_c),
        ambient_temperature_c=_float(ambient_temperature_c),
        ambient_humidity_pct=_float(ambient_humidity_pct),
        gps_latitude=_float(gps_latitude),
        gps_longitude=_float(gps_longitude),
        gps_accuracy_m=_float(gps_accuracy_m),
        field_notes=field_notes.strip(),
        container_count=max(1, container_count),
        submitted_at=datetime.utcnow(),
    )
    db.add(sample)
    db.flush()
    if assignment:
        assignment.status = "COMPLETED"
        assignment.completed_at = datetime.utcnow()
        assignment.completed_sample_id = sample.id
    add_event(
        db,
        sample,
        user,
        "FIELD_SUBMISSION",
        sample.status,
        "Sample captured and submitted from field",
        sample.gps_latitude,
        sample.gps_longitude,
    )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for idx, upload in enumerate(photos):
        if not upload.filename:
            continue
        ext = Path(upload.filename).suffix.lower()[:10]
        stored = UPLOAD_DIR / f"sample_{sample.id}_{idx}_{datetime.utcnow().timestamp():.0f}{ext}"
        with stored.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        kind = photo_kind[idx] if idx < len(photo_kind) and photo_kind[idx].strip() else "General"
        db.add(SamplePhoto(sample_request_id=sample.id, kind=kind, original_name=upload.filename, stored_path=str(stored)))

    generate_assets(barcode_value, request_number, client.name, asset.asset_code, BARCODE_DIR)
    add_audit(
        db,
        actor=user,
        request=request,
        action="FIELD_SAMPLE_SUBMITTED",
        entity_type="SampleRequest",
        entity_id=sample.id,
        summary=f"Submitted {sample.request_number} for {client.code}",
        details={"barcode": barcode_value, "asset": asset.asset_code, "photo_count": len(sample.photos)},
    )
    db.commit()
    return RedirectResponse(f"/field/sample/{sample.id}", status_code=303)


@router.get("/sample/{sample_id}")
def sample_detail(sample_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, FIELD_ROLES)
    sample = db.get(SampleRequest, sample_id)
    if not sample or (user.role != Role.SYSTEM_ADMIN.value and sample.sampler_id != user.id):
        return RedirectResponse("/field", status_code=303)
    return templates.TemplateResponse("field_detail.html", {"request": request, "user": user, "sample": sample})


@router.get("/sample/{sample_id}/label")
def label(sample_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value, Role.DATA_ENTRY.value, Role.SAMPLE_RECEIVING.value, Role.SYSTEM_ADMIN.value})
    sample = db.get(SampleRequest, sample_id)
    if not sample:
        raise ValueError("Sample not found")
    if user.role in {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} and sample.sampler_id != user.id:
        return RedirectResponse("/field", status_code=303)
    if user.role in {Role.DATA_ENTRY.value, Role.SAMPLE_RECEIVING.value} and user.site_id and sample.site_id != user.site_id:
        return RedirectResponse("/", status_code=303)
    path = BARCODE_DIR / f"{sample.barcode_value}_label.pdf"
    return FileResponse(path, media_type="application/pdf", filename=f"{sample.request_number}_tag.pdf")

@router.post("/offline-sync")
async def offline_sync(request: Request, db: Session = Depends(get_db)):
    """Synchronize a field record captured while the device was offline.

    The device creates a globally unique Code 39-compatible barcode. The server preserves
    that barcode, issues the official portal request number and creates the normal custody trail.
    Replaying the same payload is idempotent.
    """
    import base64
    import re

    user = require_user(request, db, FIELD_ROLES)
    body = await request.json()
    fields = body.get("fields") or {}
    offline_barcode = str(body.get("offline_barcode") or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9.-]{12,80}", offline_barcode):
        return JSONResponse({"error": "Invalid offline barcode"}, status_code=400)
    existing = db.scalar(select(SampleRequest).where(SampleRequest.barcode_value == offline_barcode))
    if existing:
        return {
            "ok": True,
            "idempotent": True,
            "sample_id": existing.id,
            "request_number": existing.request_number,
            "barcode": existing.barcode_value,
            "status": existing.status,
        }

    assignment_id = str(fields.get("assignment_id") or "")
    client_id = int(fields.get("client_id") or 0)
    quotation_id = str(fields.get("quotation_id") or "")
    purchase_order_id = str(fields.get("purchase_order_id") or "")
    existing_asset_id = str(fields.get("existing_asset_id") or "")
    assignment = db.get(SamplingAssignment, int(assignment_id)) if assignment_id else None
    if assignment and user.role != Role.SYSTEM_ADMIN.value and assignment.assigned_sampler_id != user.id:
        return JSONResponse({"error": "Assignment is not allocated to this sampler"}, status_code=403)
    if assignment:
        client_id = assignment.order.client_id
        quotation_id = str(assignment.order.quotation_id or "")
        purchase_order_id = str(assignment.order.purchase_order_id or "")
        if assignment.asset_id:
            existing_asset_id = str(assignment.asset_id)

    site = db.get(Site, user.site_id) if user.site_id else (assignment.order.site if assignment else db.scalar(select(Site).where(Site.code == "DMM")))
    client = db.get(Client, client_id)
    if not site or not client or not client.active:
        return JSONResponse({"error": "Site or client missing"}, status_code=400)
    if not can_access_client(db, user, client_id):
        return JSONResponse({"error": "Sampler is not assigned to this client"}, status_code=403)
    quote = db.get(Quotation, int(quotation_id)) if quotation_id else None
    po = db.get(PurchaseOrder, int(purchase_order_id)) if purchase_order_id else None
    if quote and quote.client_id != client_id:
        return JSONResponse({"error": "Quotation does not belong to selected client"}, status_code=400)
    if po and po.client_id != client_id:
        return JSONResponse({"error": "Purchase order does not belong to selected client"}, status_code=400)

    if existing_asset_id:
        asset = db.get(Asset, int(existing_asset_id))
        if not asset or asset.client_id != client_id:
            return JSONResponse({"error": "Asset does not belong to selected client"}, status_code=400)
    else:
        asset_code = str(fields.get("asset_code") or "").strip()
        serial_number = str(fields.get("serial_number") or "").strip()
        if not asset_code or not serial_number:
            return JSONResponse({"error": "Asset code and serial number are required"}, status_code=400)
        asset = Asset(
            client_id=client_id,
            asset_code=asset_code,
            serial_number=serial_number,
            equipment_type=str(fields.get("equipment_type") or "Transformer").strip(),
            manufacturer=str(fields.get("manufacturer") or "").strip(),
            station_name=str(fields.get("station_name") or "").strip(),
            asset_location_label=str(fields.get("asset_location_label") or "").strip(),
            voltage_kv=_float(str(fields.get("voltage_kv") or "")),
            rated_mva=_float(str(fields.get("rated_mva") or "")),
            latitude=_float(str(fields.get("gps_latitude") or "")),
            longitude=_float(str(fields.get("gps_longitude") or "")),
        )
        db.add(asset)
        db.flush()

    request_number, _, public_token = next_request_identifiers(db, site)
    try:
        sample_dt = datetime.fromisoformat(str(fields.get("sample_date_time") or ""))
    except ValueError:
        return JSONResponse({"error": "Invalid sample date and time"}, status_code=400)
    sample = SampleRequest(
        request_number=request_number,
        public_token=public_token,
        barcode_value=offline_barcode,
        status=SampleStatus.SUBMITTED.value,
        site_id=site.id,
        client_id=client_id,
        quotation_id=quote.id if quote else None,
        purchase_order_id=po.id if po else None,
        asset_id=asset.id,
        sampler_id=user.id,
        sampling_assignment_id=assignment.id if assignment else None,
        submission_channel="CLIENT_FIELD_OFFLINE" if user.role in {Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value} else "TSCO_FIELD_OFFLINE",
        sample_date_time=sample_dt,
        sampling_point=(assignment.sampling_point if assignment else str(fields.get("sampling_point") or "")).strip(),
        requested_package=(assignment.requested_package if assignment else str(fields.get("requested_package") or "Routine Test")).strip(),
        client_sample_reference=str(fields.get("client_sample_reference") or "").strip(),
        oil_temperature_c=_float(str(fields.get("oil_temperature_c") or "")),
        ambient_temperature_c=_float(str(fields.get("ambient_temperature_c") or "")),
        ambient_humidity_pct=_float(str(fields.get("ambient_humidity_pct") or "")),
        gps_latitude=_float(str(fields.get("gps_latitude") or "")),
        gps_longitude=_float(str(fields.get("gps_longitude") or "")),
        gps_accuracy_m=_float(str(fields.get("gps_accuracy_m") or "")),
        field_notes=str(fields.get("field_notes") or "").strip(),
        container_count=max(1, int(assignment.container_count if assignment else fields.get("container_count") or 1)),
        submitted_at=datetime.utcnow(),
    )
    db.add(sample)
    db.flush()
    if assignment:
        assignment.status = "COMPLETED"
        assignment.completed_at = datetime.utcnow()
        assignment.completed_sample_id = sample.id
    add_event(db, sample, user, "OFFLINE_FIELD_SYNC", sample.status, "Offline field record synchronized to server", sample.gps_latitude, sample.gps_longitude)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    accepted_photos = 0
    for idx, photo in enumerate(body.get("photos") or []):
        data_url = str(photo.get("data") or "")
        if not data_url.startswith("data:image/") or "," not in data_url:
            continue
        header, encoded = data_url.split(",", 1)
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception:
            continue
        total_bytes += len(raw)
        if total_bytes > 25_000_000:
            return JSONResponse({"error": "Offline photo payload exceeds 25 MB"}, status_code=413)
        subtype = header.split(";")[0].split("/")[-1].lower()
        ext = ".jpg" if subtype in {"jpeg", "jpg"} else f".{re.sub(r'[^a-z0-9]', '', subtype)[:8]}"
        stored = UPLOAD_DIR / f"sample_{sample.id}_offline_{idx}_{datetime.utcnow().timestamp():.0f}{ext}"
        stored.write_bytes(raw)
        db.add(SamplePhoto(
            sample_request_id=sample.id,
            kind=str(photo.get("kind") or "General")[:80],
            original_name=str(photo.get("name") or f"offline_{idx}{ext}")[:240],
            stored_path=str(stored),
        ))
        accepted_photos += 1

    generate_assets(offline_barcode, request_number, client.name, asset.asset_code, BARCODE_DIR)
    add_audit(
        db,
        actor=user,
        request=request,
        action="OFFLINE_FIELD_SAMPLE_SYNCHRONIZED",
        entity_type="SampleRequest",
        entity_id=sample.id,
        summary=f"Synchronized {sample.request_number} for {client.code}",
        details={"barcode": offline_barcode, "asset": asset.asset_code, "photo_count": accepted_photos, "local_id": body.get("id")},
    )
    db.commit()
    return {
        "ok": True,
        "sample_id": sample.id,
        "request_number": sample.request_number,
        "barcode": sample.barcode_value,
        "status": sample.status,
        "photo_count": accepted_photos,
    }
