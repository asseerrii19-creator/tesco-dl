from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LmsRegistrationResult:
    success: bool
    lms_number: str = ""
    external_reference: str = ""
    message: str = ""
    raw_response: dict | None = None


class LmsConnector(Protocol):
    def register_sample(self, payload: dict) -> LmsRegistrationResult:
        ...
