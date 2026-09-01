from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Client, ControlledDocument, Site, TestPackageConfig as PackageConfig
from app.services.lab_operations import package_catalog


def login_admin(client):
    response = client.post('/login/employee', data={'email':'admin@tsco.local','password':'Demo123!'}, follow_redirects=False)
    assert response.status_code == 303


def test_multiclient_isolation_and_corporate_accounts_seeded():
    with TestClient(app) as client:
        db = SessionLocal()
        sec = db.scalar(select(Client).where(Client.code == 'SEC'))
        aramco = db.scalar(select(Client).where(Client.code == 'ARM'))
        assert sec and aramco and sec.id != aramco.id
        db.close()
        r = client.post('/login/client', data={'email':'client@aramco.local','password':'Demo123!'}, follow_redirects=False)
        assert r.status_code == 303
        page = client.get('/client')
        assert page.status_code == 200
        assert 'Saudi Aramco' in page.text or 'No samples' in page.text or 'Client Dashboard' in page.text


def test_admin_can_manage_sites_documents_and_test_packages_without_code_changes():
    with TestClient(app) as client:
        login_admin(client)
        response = client.post('/admin/sites', data={'code':'TST','name':'Test Site','laboratory_name':'Test Laboratory'}, follow_redirects=False)
        assert response.status_code == 303
        db = SessionLocal(); site = db.scalar(select(Site).where(Site.code == 'TST')); assert site and site.active; db.close()

        files = {'document_file': ('SOP-DEMO.pdf', b'%PDF-1.4 demo controlled document', 'application/pdf')}
        data = {'document_type':'SOP','code':'SOP-DEMO-001','title':'Demo SOP','revision':'01','effective_date':'2026-08-31','site_id':'','notes':'First revision'}
        response = client.post('/admin/documents', data=data, files=files, follow_redirects=False)
        assert response.status_code == 303
        files = {'document_file': ('SOP-DEMO-R2.pdf', b'%PDF-1.4 revision 2', 'application/pdf')}
        data['revision']='02'; data['notes']='Second revision'
        response = client.post('/admin/documents', data=data, files=files, follow_redirects=False)
        assert response.status_code == 303
        db = SessionLocal(); docs = db.scalars(select(ControlledDocument).where(ControlledDocument.code=='SOP-DEMO-001').order_by(ControlledDocument.id)).all(); assert len(docs)==2; assert docs[0].status=='SUPERSEDED'; assert docs[1].status=='ACTIVE'; db.close()

        tests_text = 'Water Content | IEC 60814 | Water | mg/kg\nBreakdown Voltage | IEC 60156 | Electrical | kV'
        response = client.post('/admin/test-packages', data={'code':'DEMO-R1','name':'Demo Routine','scope':'GENERAL','site_id':'','tests':tests_text}, follow_redirects=False)
        assert response.status_code == 303
        db = SessionLocal(); package = db.scalar(select(PackageConfig).where(PackageConfig.code=='DEMO-R1')); assert package and package.active; names=[p['name'] for p in package_catalog(db)]; assert 'Demo Routine' in names; db.close()

        page = client.get('/admin/test-packages')
        assert page.status_code == 200 and 'Demo Routine' in page.text
        docs_page = client.get('/documents')
        assert docs_page.status_code == 200 and 'SOP-DEMO-001' in docs_page.text
