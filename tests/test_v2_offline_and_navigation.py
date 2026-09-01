from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Client, PurchaseOrder, Quotation, SampleRequest


def test_offline_field_sync_is_idempotent_and_preserves_barcode():
    with TestClient(app) as client:
        db = SessionLocal()
        sec = db.scalar(select(Client).where(Client.code == "SEC"))
        quote = db.scalar(select(Quotation).where(Quotation.client_id == sec.id))
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.client_id == sec.id))
        asset = db.scalar(select(Asset).where(Asset.client_id == sec.id))
        db.close()
        client.post("/login/field", data={"email": "fieldman@tsco.local", "password": "Demo123!"})
        payload = {
            "id": "offline-test-001",
            "offline_barcode": "DMM-OFF-20260805-A1B2C3",
            "created_at": datetime.now().isoformat(),
            "fields": {
                "assignment_id": "", "client_id": str(sec.id), "quotation_id": str(quote.id),
                "purchase_order_id": str(po.id), "existing_asset_id": str(asset.id),
                "sample_date_time": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                "sampling_point": "Main Tank Bottom", "requested_package": "Routine Test",
                "client_sample_reference": "OFFLINE-UAT", "oil_temperature_c": "31",
                "ambient_temperature_c": "38", "ambient_humidity_pct": "43",
                "gps_latitude": "26.4207", "gps_longitude": "50.0888", "gps_accuracy_m": "5",
                "field_notes": "Captured offline", "container_count": "1",
            },
            "photos": [],
        }
        first = client.post("/field/offline-sync", json=payload)
        assert first.status_code == 200
        assert first.json()["barcode"] == payload["offline_barcode"]
        second = client.post("/field/offline-sync", json=payload)
        assert second.status_code == 200 and second.json()["idempotent"] is True
        db = SessionLocal()
        rows = db.scalars(select(SampleRequest).where(SampleRequest.barcode_value == payload["offline_barcode"])).all()
        db.close()
        assert len(rows) == 1


def test_unified_role_navigation_keeps_retained_samples_and_hides_supervision_from_chemist():
    with TestClient(app) as client:
        client.post("/login/employee", data={"email": "chemist@tsco.local", "password": "Demo123!"})
        page = client.get("/lab/operations?section=retained")
        assert page.status_code == 200
        assert "Retained Samples" in page.text
        assert "Technical Supervision" not in page.text
        client.post("/logout")
        client.post("/login/employee", data={"email": "senior@tsco.local", "password": "Demo123!"})
        senior = client.get("/lab/operations?section=supervisor")
        assert "Technical Supervision" in senior.text
        assert "Retained Samples" in senior.text
