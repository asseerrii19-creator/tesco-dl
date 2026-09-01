from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import SampleRequest, SamplingOrder, Site


def next_request_identifiers(db: Session, site: Site) -> tuple[str, str, str]:
    year = datetime.utcnow().strftime("%y")
    prefix = f"FS-{site.code}-{year}-"
    count = db.scalar(select(func.count(SampleRequest.id)).where(SampleRequest.request_number.like(f"{prefix}%"))) or 0
    sequence = count + 1
    request_number = f"{prefix}{sequence:06d}"
    barcode_value = f"TSCO-{site.code}-{year}-{sequence:08d}"
    public_token = secrets.token_urlsafe(24)
    return request_number, barcode_value, public_token


def next_sampling_order_identifiers(db: Session, site: Site) -> tuple[str, str]:
    year = datetime.utcnow().strftime("%y")
    prefix = f"SO-{site.code}-{year}-"
    count = db.scalar(select(func.count(SamplingOrder.id)).where(SamplingOrder.order_number.like(f"{prefix}%"))) or 0
    order_number = f"{prefix}{count + 1:05d}"
    assignment_code = f"{site.code}-{secrets.token_hex(4).upper()}"
    return order_number, assignment_code


def next_assignment_code(site: Site) -> str:
    return f"{site.code}-{secrets.token_hex(5).upper()}"
