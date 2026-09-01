from datetime import datetime
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Client, OperationsState, PurchaseOrder, Quotation, SampleRequest


def test_field_to_client_and_integrated_lab_workflow():
    with TestClient(app) as client:
        db = SessionLocal()
        sec = db.scalar(select(Client).where(Client.code == "SEC"))
        quote = db.scalar(select(Quotation).where(Quotation.client_id == sec.id))
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.client_id == sec.id))
        asset = db.scalar(select(Asset).where(Asset.client_id == sec.id))
        db.close()

        assert client.post("/login/field", data={"email": "fieldman@tsco.local", "password": "Demo123!"}, follow_redirects=False).status_code == 303
        created = client.post(
            "/field/new",
            data={
                "client_id": sec.id, "quotation_id": str(quote.id), "purchase_order_id": str(po.id),
                "existing_asset_id": str(asset.id), "asset_code": "", "serial_number": "",
                "equipment_type": "Power Transformer", "manufacturer": "", "station_name": "",
                "asset_location_label": "", "voltage_kv": "", "rated_mva": "",
                "sample_date_time": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                "sampling_point": "Main Tank Bottom", "requested_package": "Routine Test",
                "client_sample_reference": "E2E-REFERENCE", "oil_temperature_c": "35",
                "ambient_temperature_c": "40", "ambient_humidity_pct": "35",
                "gps_latitude": "26.4207", "gps_longitude": "50.0888", "gps_accuracy_m": "3",
                "field_notes": "Automated workflow check", "container_count": "1",
            }, follow_redirects=False,
        )
        assert created.status_code == 303

        db = SessionLocal(); sample = db.scalar(select(SampleRequest).order_by(SampleRequest.id.desc())); sample_id = sample.id; request_number = sample.request_number; barcode = sample.barcode_value; db.close()

        client.post("/logout")
        client.post("/login/employee", data={"email": "intake@tsco.local", "password": "Demo123!"})
        assert client.post(f"/intake/{sample_id}/decision", data={"action": "ACCEPT_AND_REGISTER", "note": "Accepted", "issue_type": ""}, follow_redirects=False).status_code == 303

        db = SessionLocal(); sample = db.get(SampleRequest, sample_id); lms_number = sample.lms_number
        assert sample.status == "AWAITING_RECEIPT" and lms_number
        state = db.scalar(select(OperationsState).where(OperationsState.site_id == sample.site_id)); payload = json.loads(state.json_data)
        assert any(lms_number in batch.get("samples", []) for batch in payload["batches"])
        db.close()

        client.post("/logout")
        client.post("/login/employee", data={"email": "receiving@tsco.local", "password": "Demo123!"})
        assert client.post(f"/receiving/{sample_id}/receive", data={"seal_status": "Intact", "condition_note": "Good condition"}, follow_redirects=False).status_code == 303

        db = SessionLocal(); sample = db.get(SampleRequest, sample_id); assert sample.status == "RECEIVED"; db.close()

        client.post("/logout")
        client.post("/login/client", data={"email": "client@sec.local", "password": "Demo123!"})
        portal = client.get("/client")
        assert portal.status_code == 200 and request_number in portal.text and lms_number in portal.text


def test_operations_manager_to_supervisor_assignment():
    with TestClient(app) as client:
        db = SessionLocal()
        sec = db.scalar(select(Client).where(Client.code == "SEC")); quote = db.scalar(select(Quotation).where(Quotation.client_id == sec.id)); po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.client_id == sec.id)); asset = db.scalar(select(Asset).where(Asset.client_id == sec.id))
        from app.models import User
        supervisor = db.scalar(select(User).where(User.email == "supervisor@tsco.local")); sampler = db.scalar(select(User).where(User.email == "fieldman@tsco.local")); db.close()
        client.post("/login/employee", data={"email": "operations@tsco.local", "password": "Demo123!"})
        response = client.post("/operations/orders", data={"client_id": sec.id, "quotation_id": quote.id, "purchase_order_id": po.id, "supervisor_id": supervisor.id, "title": "Planned SEC sampling", "priority": "High", "due_at": "", "notes": ""}, follow_redirects=False)
        assert response.status_code == 303
        from app.models import SamplingOrder
        db = SessionLocal(); order = db.scalar(select(SamplingOrder).order_by(SamplingOrder.id.desc())); db.close()
        response = client.post(f"/operations/orders/{order.id}/assignments", data={"asset_id": asset.id, "assigned_sampler_id": sampler.id, "source_party": "TSCO", "requested_package": "SEC Routine", "sampling_point": "Main Tank Bottom", "container_count": 1, "instructions": "Take nameplate photo"}, follow_redirects=False)
        assert response.status_code == 303
        client.post("/logout"); client.post("/login/field", data={"email": "fieldman@tsco.local", "password": "Demo123!"})
        page = client.get("/field")
        assert "Planned SEC sampling" not in page.text  # compact field view uses order number/code
        assert order.order_number in page.text and "SEC Routine" in page.text


def test_integrated_lab_results_assessment_and_client_release():
    with TestClient(app) as client:
        db = SessionLocal()
        sec = db.scalar(select(Client).where(Client.code == "SEC"))
        quote = db.scalar(select(Quotation).where(Quotation.client_id == sec.id))
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.client_id == sec.id))
        asset = db.scalar(select(Asset).where(Asset.client_id == sec.id))
        db.close()

        client.post("/login/field", data={"email": "fieldman@tsco.local", "password": "Demo123!"})
        response = client.post(
            "/field/new",
            data={
                "client_id": sec.id,
                "quotation_id": str(quote.id),
                "purchase_order_id": str(po.id),
                "existing_asset_id": str(asset.id),
                "asset_code": "",
                "serial_number": "",
                "equipment_type": "Power Transformer",
                "manufacturer": "",
                "station_name": "",
                "asset_location_label": "",
                "voltage_kv": "",
                "rated_mva": "",
                "sample_date_time": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                "sampling_point": "Main Tank Bottom",
                "requested_package": "Full Test",
                "client_sample_reference": "ASSESSMENT-E2E",
                "oil_temperature_c": "42",
                "ambient_temperature_c": "34",
                "ambient_humidity_pct": "40",
                "gps_latitude": "26.4207",
                "gps_longitude": "50.0888",
                "gps_accuracy_m": "4",
                "field_notes": "Assessment integration test",
                "container_count": "2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        db = SessionLocal()
        sample = db.scalar(select(SampleRequest).where(SampleRequest.client_sample_reference == "ASSESSMENT-E2E"))
        sample_id = sample.id
        barcode = sample.barcode_value
        request_number = sample.request_number
        db.close()

        client.post("/logout")
        client.post("/login/employee", data={"email": "intake@tsco.local", "password": "Demo123!"})
        client.post(
            f"/intake/{sample_id}/decision",
            data={"action": "ACCEPT_AND_REGISTER", "note": "Verified against field submission", "issue_type": ""},
            follow_redirects=False,
        )
        db = SessionLocal()
        sample = db.get(SampleRequest, sample_id)
        lms_number = sample.lms_number
        assert sample.status == "AWAITING_RECEIPT"
        db.close()

        client.post("/logout")
        client.post("/login/employee", data={"email": "receiving@tsco.local", "password": "Demo123!"})
        client.post(
            f"/receiving/{sample_id}/receive",
            data={"seal_status": "Intact", "condition_note": "Barcode and two containers verified"},
            follow_redirects=False,
        )

        client.post("/logout")
        client.post("/login/employee", data={"email": "chemist@tsco.local", "password": "Demo123!"})
        client.post(f"/lab/{sample_id}/status", data={"action": "START_TESTING", "note": "Testing started"})
        operations = client.get("/api/lab-operations/data").json()["db"]
        now = datetime.now().isoformat()
        result_rows = [
            ("Breakdown Voltage @2.5mm- AVG", "48", "kV"),
            ("Water Content KF @RT", "18", "mg/kg"),
            ("Interfacial Tension (IFT)", "20", "mN/m"),
            ("DGA:H2", "10", "ppm"),
            ("DGA:CH4", "20", "ppm"),
            ("DGA:C2H6", "10", "ppm"),
            ("DGA:C2H4", "20", "ppm"),
            ("DGA:C2H2", "1", "ppm"),
            ("DGA:CO", "100", "ppm"),
            ("DGA:CO2", "500", "ppm"),
        ]
        for index, (test, result, unit) in enumerate(result_rows):
            operations["results"].append({
                "id": f"E2E-{sample_id}-{index}",
                "sample": lms_number,
                "test": test,
                "result": result,
                "unit": unit,
                "analyst": "Laboratory Chemist",
                "ts": now,
            })
        for batch in operations["batches"]:
            if lms_number in batch.get("samples", []):
                batch["status"] = "Technical Review"
        saved = client.put("/api/lab-operations/data", json={"db": operations})
        assert saved.status_code == 200

        db = SessionLocal()
        sample = db.get(SampleRequest, sample_id)
        assert sample.status == "TECHNICAL_REVIEW"
        db.close()

        client.post("/logout")
        client.post("/login/employee", data={"email": "senior@tsco.local", "password": "Demo123!"})
        assessment_page = client.get(f"/assessment?sample_id={sample_id}")
        assert assessment_page.status_code == 200
        assert "POOR" in assessment_page.text
        assert "T2" in assessment_page.text
        approved = client.post(
            f"/assessment/{sample_id}",
            data={"decision": "APPROVED", "recommendation": "Confirm trend and issue the reviewed report."},
            follow_redirects=False,
        )
        assert approved.status_code == 303
        db = SessionLocal()
        sample = db.get(SampleRequest, sample_id)
        assert sample.status == "REPORT_APPROVED"
        db.close()

        operations = client.get("/api/lab-operations/data").json()["db"]
        operations["reports"].append({
            "id": f"REPORT-{sample_id}",
            "sample": lms_number,
            "status": "Released",
            "released_at": datetime.now().isoformat(),
        })
        assert client.put("/api/lab-operations/data", json={"db": operations}).status_code == 200
        db = SessionLocal()
        sample = db.get(SampleRequest, sample_id)
        assert sample.status == "REPORT_RELEASED"
        db.close()

        client.post("/logout")
        client.post("/login/client", data={"email": "client@sec.local", "password": "Demo123!"})
        portal = client.get("/client")
        assert request_number in portal.text
        assert "Report released" in portal.text
        timeline = client.get(f"/track/{sample.public_token}")
        assert timeline.status_code == 200
        assert "Report released" in timeline.text
