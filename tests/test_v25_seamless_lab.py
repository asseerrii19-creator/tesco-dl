from fastapi.testclient import TestClient

from app.main import app


def test_seamless_lab_shell():
    with TestClient(app) as client:
        client.post("/login/employee", data={"email":"admin@tsco.local","password":"Demo123!"})
        page = client.get("/lab/operations?section=workstations")
        assert page.status_code == 200
        text = page.text
        assert 'id="labOperationsFrame"' in text
        assert 'lab-frame-seamless' in text
        assert 'TSCO_LAB_HEIGHT' in text
        assert 'TSCO_LAB_SECTION_CHANGE' in text
        assert 'Open Full Laboratory Operations' not in text


def test_embedded_lab_hides_duplicate_shell():
    with TestClient(app) as client:
        client.post("/login/employee", data={"email":"admin@tsco.local","password":"Demo123!"})
        page = client.get("/lab/operations/app?embed=1&section=quality")
        assert page.status_code == 200
        text = page.text
        assert 'body.platform-embed>header,body.platform-embed>nav{display:none!important}' in text
        assert 'window.TSCO_PLATFORM_EMBED=true' in text
        assert 'Unified Platform Session • v2.6' in text


def test_lab_settings_visible_for_admin():
    with TestClient(app) as client:
        client.post("/login/employee", data={"email":"admin@tsco.local","password":"Demo123!"})
        page = client.get("/lab/operations?section=general")
        assert page.status_code == 200
        assert 'Laboratory Settings' in page.text
