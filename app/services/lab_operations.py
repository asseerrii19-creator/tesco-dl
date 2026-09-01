from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import OperationsState, SampleRequest, Site, TestPackageConfig, User

BASE_DIR = Path(__file__).resolve().parents[1]
PACKAGE_FILE = BASE_DIR / "data" / "lab_packages.json"


def package_catalog(db: Session | None = None, site_id: int | None = None) -> list[dict[str, Any]]:
    try:
        base = json.loads(PACKAGE_FILE.read_text(encoding="utf-8"))["packages"]
    except Exception:
        base = []
    if db is None:
        return base
    stmt = select(TestPackageConfig).where(TestPackageConfig.active.is_(True))
    if site_id is not None:
        stmt = stmt.where((TestPackageConfig.site_id.is_(None)) | (TestPackageConfig.site_id == site_id))
    rows = db.scalars(stmt.order_by(TestPackageConfig.name)).all()
    dynamic = []
    for row in rows:
        try:
            tests = json.loads(row.tests_json or "[]")
        except Exception:
            tests = []
        dynamic.append({
            "id": row.code, "name": row.name, "scope": row.scope, "kind": "configured",
            "site_id": row.site_id, "tests": tests if isinstance(tests, list) else [],
        })
    names = {item.get("name", "").strip().lower() for item in dynamic}
    return dynamic + [item for item in base if item.get("name", "").strip().lower() not in names]


def blank_operations_db(site: Site) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    return {
        "batches": [], "results": [], "qc": [], "qualifiedQcProfiles": [], "reports": [],
        "retained": [], "retests": [], "storageAssignments": [], "batchHistory": [],
        "cancelledSamples": [], "supervisorNotes": [], "standards": [], "dgaAttachments": [],
        "clients": [], "customPackages": [], "formulaDefinitions": [], "calculationDrafts": {},
        "staff": [], "samplePoints": ["Bottom", "Top", "Main Tank", "OLTC", "Bushing", "Drum / Tote", "Other"],
        "testUnits": {}, "drafts": {},
        "settings": {
            "labCode": "DM" if site.code == "DMM" else site.code,
            "yearCode": datetime.utcnow().strftime("%y"), "prefixPadding": "00",
            "normalRetentionDays": 15, "urgentRetentionDays": 15,
            "currentSite": site.code, "enabledSites": [site.code],
            "qcProfileSelections": {}, "activeSeniorChemist": "",
        },
        "meta": {"schema": 3, "site": site.code, "revision": 0, "updatedAt": now, "platformIntegrated": True},
    }


def get_operations_state(db: Session, site: Site) -> tuple[OperationsState, dict[str, Any]]:
    state = db.scalar(select(OperationsState).where(OperationsState.site_id == site.id))
    if not state:
        payload = blank_operations_db(site)
        state = OperationsState(site_id=site.id, json_data=json.dumps(payload, ensure_ascii=False), revision=0)
        db.add(state)
        db.flush()
        return state, payload
    try:
        payload = json.loads(state.json_data or "{}")
    except json.JSONDecodeError:
        payload = blank_operations_db(site)
    if not isinstance(payload, dict) or "batches" not in payload:
        payload = blank_operations_db(site)
    return state, payload


def save_operations_state(db: Session, state: OperationsState, payload: dict[str, Any], actor: User | None = None) -> None:
    payload.setdefault("meta", {})
    payload["meta"]["revision"] = int(payload["meta"].get("revision", 0)) + 1
    payload["meta"]["updatedAt"] = datetime.utcnow().isoformat()
    payload["meta"]["platformIntegrated"] = True
    state.json_data = json.dumps(payload, ensure_ascii=False)
    state.revision = int(payload["meta"]["revision"])
    state.updated_by_id = actor.id if actor else None
    state.updated_at = datetime.utcnow()


def _select_package(db: Session, sample: SampleRequest) -> dict[str, Any]:
    packages = package_catalog(db, sample.site_id)
    wanted = (sample.requested_package or "Routine Test").strip().lower()
    aliases = {
        "sec package": "sec routine",
        "aramco package": "aramco routine",
        "gpel package": "gpel package",
        "routine": "routine test",
        "full": "full test",
    }
    wanted = aliases.get(wanted, wanted)
    for package in packages:
        if package.get("name", "").strip().lower() == wanted:
            return package
    for package in packages:
        if wanted in package.get("name", "").strip().lower():
            return package
    return next((p for p in packages if p.get("name") == "Routine Test"), {"id": "GEN_ROUTINE", "name": "Routine Test", "tests": []})


def sync_sample_to_operations(db: Session, sample: SampleRequest, actor: User | None = None, phase: str = "REGISTERED") -> None:
    site = sample.site
    state, payload = get_operations_state(db, site)
    sample_key = (sample.lms_number or sample.request_number).upper()
    existing = next((batch for batch in payload.get("batches", []) if sample_key in batch.get("samples", [])), None)
    package = _select_package(db, sample)
    client_entry = {"id": str(sample.client.id), "code": sample.client.code, "name": sample.client.name, "active": True}
    clients = payload.setdefault("clients", [])
    if not any(str(item.get("id")) == client_entry["id"] or item.get("code") == client_entry["code"] for item in clients):
        clients.append(client_entry)
    room_temp = "" if sample.ambient_temperature_c is None else str(sample.ambient_temperature_c)
    room_humidity = "" if sample.ambient_humidity_pct is None else str(sample.ambient_humidity_pct)
    oil_temp = "" if sample.oil_temperature_c is None else str(sample.oil_temperature_c)
    metadata = {
        "point": sample.sampling_point,
        "temp": oil_temp,
        "roomTemp": room_temp,
        "roomHumidity": room_humidity,
        "portalRequest": sample.request_number,
        "lmsNumber": sample.lms_number or "",
        "assetCode": sample.asset.asset_code,
        "serialNumber": sample.asset.serial_number,
        "stationName": sample.asset.station_name,
        "exactLocation": sample.asset.asset_location_label,
        "quotation": sample.quotation.number if sample.quotation else "",
        "purchaseOrder": sample.purchase_order.number if sample.purchase_order else "",
        "barcode": sample.barcode_value,
        "sourceChannel": sample.submission_channel,
    }
    status_map = {"REGISTERED": "Waiting Receipt", "RECEIVED": "Received", "TESTING": "Testing", "TECHNICAL_REVIEW": "Technical Review"}
    if existing:
        existing["status"] = status_map.get(phase, existing.get("status", "Received"))
        existing.setdefault("sample_meta", {})[sample_key] = metadata
        existing["roomTemp"] = room_temp
        existing["roomHumidity"] = room_humidity
        existing["platform_updated_at"] = datetime.utcnow().isoformat()
    else:
        batch = {
            "id": f"PLATFORM-{sample.id}",
            "template": package.get("name", sample.requested_package),
            "package_id": package.get("id", "PLATFORM"),
            "client_id": str(sample.client.id), "client_name": sample.client.name, "client_code": sample.client.code,
            "priority": sample.sampling_assignment.order.priority if sample.sampling_assignment else "Normal",
            "site": site.code, "samples": [sample_key], "sample_meta": {sample_key: metadata},
            "roomTemp": room_temp, "roomHumidity": room_humidity,
            "note": f"Imported from platform {sample.request_number}. LMS: {sample.lms_number or 'pending'}",
            "tests": package.get("tests", []), "status": status_map.get(phase, "Waiting Receipt"),
            "created_at": datetime.utcnow().isoformat(), "platform_sample_id": sample.id,
        }
        payload.setdefault("batches", []).append(batch)
        payload.setdefault("batchHistory", []).insert(0, {
            "id": f"BH-PLATFORM-{sample.id}", "action": "Platform Sample Imported", "sample": sample_key,
            "from_batch": "Field / Intake", "to_batch": batch["id"],
            "reason": f"{sample.request_number} accepted and registered in LMS", "details": sample.submission_channel,
            "by": actor.full_name if actor else "TSCO Platform", "ts": datetime.utcnow().isoformat(),
        })
    save_operations_state(db, state, payload, actor)


def reconcile_operations_to_platform(db: Session, payload: dict[str, Any], site_id: int, actor: User | None = None) -> int:
    """Propagate laboratory progress/report release back to the platform/client timeline."""
    from ..models import CustodyEvent, SampleStatus

    samples = db.scalars(select(SampleRequest).where(SampleRequest.site_id == site_id)).all()
    results_keys = {str(row.get("sample", "")).upper() for row in payload.get("results", [])}
    reports = {str(row.get("sample", "")).upper(): row for row in payload.get("reports", [])}
    batch_status: dict[str, str] = {}
    for batch in payload.get("batches", []):
        for key in batch.get("samples", []):
            batch_status[str(key).upper()] = str(batch.get("status", ""))

    rank = {
        SampleStatus.SUBMITTED.value: 1,
        SampleStatus.ACCEPTED.value: 2,
        SampleStatus.AWAITING_RECEIPT.value: 3,
        SampleStatus.RECEIVED.value: 4,
        SampleStatus.REGISTERED.value: 4,
        SampleStatus.TESTING.value: 5,
        SampleStatus.TECHNICAL_REVIEW.value: 6,
        SampleStatus.REPORT_APPROVED.value: 7,
        SampleStatus.REPORT_RELEASED.value: 8,
    }
    changed = 0
    for sample in samples:
        keys = {sample.request_number.upper()}
        if sample.lms_number:
            keys.add(sample.lms_number.upper())
        target = sample.status
        report = next((reports[key] for key in keys if key in reports), None)
        statuses = [batch_status.get(key, "").lower() for key in keys]
        has_technical = any("technical" in value or "review" in value for value in statuses)
        has_testing = bool(keys & results_keys) or any("testing" in value for value in statuses)

        if report and str(report.get("status", "")).lower() == "released":
            target = SampleStatus.REPORT_RELEASED.value
            released = report.get("released_at")
            if released:
                try:
                    sample.released_at = datetime.fromisoformat(str(released).replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    sample.released_at = datetime.utcnow()
        elif has_technical:
            target = SampleStatus.TECHNICAL_REVIEW.value
        elif has_testing:
            target = SampleStatus.TESTING.value

        if rank.get(target, 0) > rank.get(sample.status, 0):
            sample.status = target
            event_type = {
                SampleStatus.TESTING.value: "LAB_RESULTS_IN_PROGRESS",
                SampleStatus.TECHNICAL_REVIEW.value: "TECHNICAL_REVIEW_STARTED",
                SampleStatus.REPORT_RELEASED.value: "REPORT_RELEASED",
            }.get(target, "LAB_STATUS_SYNC")
            exists = db.scalar(
                select(CustodyEvent.id).where(
                    CustodyEvent.sample_request_id == sample.id,
                    CustodyEvent.event_type == event_type,
                )
            )
            if not exists:
                db.add(
                    CustodyEvent(
                        sample_request_id=sample.id,
                        event_type=event_type,
                        status=target,
                        actor_id=actor.id if actor else None,
                        note="Synchronized from Full Laboratory Operations",
                        event_at=datetime.utcnow(),
                    )
                )
            changed += 1
    return changed
