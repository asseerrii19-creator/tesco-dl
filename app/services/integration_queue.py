from __future__ import annotations

import json
from sqlalchemy.orm import Session

from ..integrations.lms.factory import get_lms_connector
from ..models import IntegrationQueueItem, SampleRequest

def retry_item(db: Session, item: IntegrationQueueItem) -> bool:
    item.attempts += 1
    item.status = "PROCESSING"
    item.last_error = ""
    try:
        payload = json.loads(item.payload_json or "{}")
        if item.integration == "LMS" and item.operation == "REGISTER_SAMPLE":
            result = get_lms_connector().register_sample(payload)
            if not result.success:
                raise RuntimeError(result.message or "LMS operation failed")
            item.status = "SUCCESS"
            item.external_reference = result.external_reference or result.lms_number or ""
        else:
            raise RuntimeError(f"No runtime adapter configured for {item.integration}:{item.operation}")
    except Exception as exc:
        item.status = "FAILED"
        item.last_error = str(exc)
        return False
    return True
