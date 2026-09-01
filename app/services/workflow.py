from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from ..integrations.lms.factory import get_lms_connector
from ..models import CustodyEvent, LmsSyncLog, SampleRequest, SampleStatus, User
from .lab_operations import sync_sample_to_operations


STATUS_LABELS = {
    SampleStatus.DRAFT.value: "Draft",
    SampleStatus.SUBMITTED.value: "Submitted from field",
    SampleStatus.RETURNED.value: "Returned for correction",
    SampleStatus.REJECTED.value: "Rejected",
    SampleStatus.ACCEPTED.value: "Data accepted",
    SampleStatus.AWAITING_RECEIPT.value: "Registered in LMS — awaiting physical receipt",
    SampleStatus.IN_TRANSIT.value: "In transit",
    SampleStatus.RECEIVED.value: "Received at laboratory",
    SampleStatus.REGISTERED.value: "Registered in LMS",
    SampleStatus.TESTING.value: "Testing in progress",
    SampleStatus.TECHNICAL_REVIEW.value: "Technical review",
    SampleStatus.REPORT_APPROVED.value: "Report approved",
    SampleStatus.REPORT_RELEASED.value: "Report released",
}

STATUS_ORDER = [
    SampleStatus.SUBMITTED.value,
    SampleStatus.ACCEPTED.value,
    SampleStatus.AWAITING_RECEIPT.value,
    SampleStatus.IN_TRANSIT.value,
    SampleStatus.RECEIVED.value,
    SampleStatus.REGISTERED.value,
    SampleStatus.TESTING.value,
    SampleStatus.TECHNICAL_REVIEW.value,
    SampleStatus.REPORT_APPROVED.value,
    SampleStatus.REPORT_RELEASED.value,
]


def add_event(
    db: Session,
    sample: SampleRequest,
    actor: User | None,
    event_type: str,
    status_value: str,
    note: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> CustodyEvent:
    event = CustodyEvent(
        sample_request_id=sample.id,
        event_type=event_type,
        status=status_value,
        actor_id=actor.id if actor else None,
        note=note,
        latitude=latitude,
        longitude=longitude,
        event_at=datetime.utcnow(),
    )
    db.add(event)
    return event


def register_in_lms(db: Session, sample: SampleRequest, actor: User) -> str:
    connector = get_lms_connector()
    payload = {
        "portal_sample_id": sample.id,
        "portal_request_number": sample.request_number,
        "barcode": sample.barcode_value,
        "site_code": sample.site.code,
        "client_code": sample.client.code,
        "quotation": sample.quotation.number if sample.quotation else "",
        "purchase_order": sample.purchase_order.number if sample.purchase_order else "",
        "asset_code": sample.asset.asset_code,
        "serial_number": sample.asset.serial_number,
        "sampling_point": sample.sampling_point,
        "requested_package": sample.requested_package,
    }
    result = connector.register_sample(payload)
    log = LmsSyncLog(
        sample_request_id=sample.id,
        direction="OUTBOUND",
        operation="REGISTER_SAMPLE",
        status="SUCCESS" if result.success else "FAILED",
        external_reference=result.external_reference,
        request_payload=json.dumps(payload, ensure_ascii=False),
        response_payload=json.dumps(result.raw_response or {}, ensure_ascii=False),
        error_message="" if result.success else result.message,
    )
    db.add(log)
    if not result.success:
        raise RuntimeError(result.message or "LMS registration failed")
    sample.lms_number = result.lms_number
    sample.registered_at = datetime.utcnow()
    sample.status = SampleStatus.AWAITING_RECEIPT.value
    add_event(db, sample, actor, "LMS_REGISTRATION", sample.status, f"LMS number {result.lms_number}; awaiting physical receipt")
    sync_sample_to_operations(db, sample, actor, phase="REGISTERED")
    return result.lms_number
