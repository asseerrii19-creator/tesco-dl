from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app


with TestClient(app) as client:
    checks = ["/welcome", "/login/client", "/login/employee", "/login/field", "/openapi.json"]
    for path in checks:
        response = client.get(path)
        if response.status_code != 200:
            raise SystemExit(f"FAIL {path}: {response.status_code}")
        print(f"PASS {path}")
