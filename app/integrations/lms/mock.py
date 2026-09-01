from __future__ import annotations

from datetime import datetime

from .base import LmsRegistrationResult


class MockLmsConnector:
    def register_sample(self, payload: dict) -> LmsRegistrationResult:
        site = payload.get("site_code", "DMM")
        year = datetime.utcnow().strftime("%y")
        internal_id = int(payload["portal_sample_id"])
        lms_number = f"{site}{year}-{internal_id:06d}"
        return LmsRegistrationResult(
            success=True,
            lms_number=lms_number,
            external_reference=f"MOCK-{internal_id}",
            message="Registered through mock LMS adapter",
            raw_response={"sampleNumber": lms_number, "mode": "mock"},
        )
