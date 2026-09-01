from __future__ import annotations

import os

from .mock import MockLmsConnector


def get_lms_connector():
    mode = os.getenv("LMS_MODE", "mock").lower()
    if mode == "mock":
        return MockLmsConnector()
    raise RuntimeError(
        f"LMS_MODE={mode!r} is not implemented. Add a vendor-specific connector after receiving the official API/export specification."
    )
