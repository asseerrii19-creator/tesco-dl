from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from ..models import AuditLog, User


def add_audit(
    db: Session,
    *,
    actor: User | None,
    request: Request | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    summary: str = "",
    details: dict[str, Any] | str | None = None,
) -> AuditLog:
    if isinstance(details, dict):
        details_text = json.dumps(details, ensure_ascii=False, default=str)
    else:
        details_text = details or ""
    ip_address = ""
    if request and request.client:
        ip_address = request.client.host or ""
    row = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        summary=summary[:260],
        details=details_text,
        ip_address=ip_address,
    )
    db.add(row)
    return row
