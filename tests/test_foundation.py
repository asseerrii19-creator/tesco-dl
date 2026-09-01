from fastapi.testclient import TestClient

from app.main import app


def test_public_welcome_separates_portals():
    with TestClient(app) as client:
        response = client.get("/welcome")
        assert response.status_code == 200
        assert "Client Portal" in response.text
        assert "Employee Portal" in response.text
        assert "Field Sampling" in response.text
        assert "fieldman@tsco.local" not in response.text


def test_api_openapi():
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "TSCO Digital Laboratory Platform"
        assert response.json()["info"]["version"] == "2.6.0"


def test_admin_console_and_company_creation():
    with TestClient(app) as client:
        login = client.post(
            "/login/employee",
            data={"email": "admin@tsco.local", "password": "Demo123!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        page = client.get("/admin")
        assert page.status_code == 200
        assert "Platform Overview" in page.text
        assert "Operational Modules" in page.text
        assert "UAT ENVIRONMENT" not in page.text
        response = client.post(
            "/admin/clients",
            data={"code": "TST", "name": "Test Client Company", "contact_email": "qa@example.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "Test Client Company" in response.text


def test_client_cannot_enter_employee_portal_or_admin():
    with TestClient(app) as client:
        wrong_portal = client.post(
            "/login/employee",
            data={"email": "client@sec.local", "password": "Demo123!"},
        )
        assert wrong_portal.status_code == 401
        login = client.post(
            "/login/client",
            data={"email": "client@sec.local", "password": "Demo123!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        denied = client.get("/admin")
        assert denied.status_code == 403


def test_field_sampler_sees_only_assigned_company():
    with TestClient(app) as client:
        login = client.post(
            "/login/field",
            data={"email": "fieldman@tsco.local", "password": "Demo123!"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        page = client.get("/field/new")
        assert page.status_code == 200
        assert "Saudi Electricity Company" in page.text
        assert "Saudi Aramco" not in page.text
        assert ">GPEL<" not in page.text


def test_lab_operations_is_role_protected_and_integrated():
    with TestClient(app) as client:
        client.post("/login/employee", data={"email": "chemist@tsco.local", "password": "Demo123!"})
        page = client.get("/lab/operations")
        assert page.status_code == 200
        assert "Integrated transformer oil laboratory operations" in page.text
        app_page = client.get("/lab/operations/app?section=retained")
        assert app_page.status_code == 200 and "TSCO Transformer Oil Laboratory" in app_page.text
        assert "/api/lab-operations/data" in app_page.text
        client.post("/logout")
        client.post("/login/client", data={"email": "client@sec.local", "password": "Demo123!"})
        assert client.get("/lab/operations").status_code == 403
