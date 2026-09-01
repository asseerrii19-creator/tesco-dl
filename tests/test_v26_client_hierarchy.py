from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Asset, Client, ClientUnit, Role, SampleRequest, Site, User, UserClientUnitAssignment
from app.security import hash_password
from app.services.scope import allowed_client_unit_ids


def test_client_unit_assignment_inherits_descendants_and_filters_portal():
    with TestClient(app) as client:
        db=SessionLocal()
        arm=db.scalar(select(Client).where(Client.code=='ARM')); dmm=db.scalar(select(Site).where(Site.code=='DMM')); sampler=db.scalar(select(User).where(User.email=='fieldman@tsco.local'))
        abq=db.scalar(select(ClientUnit).where(ClientUnit.client_id==arm.id, ClientUnit.code=='ARM-ABQ'))
        abq_plant=db.scalar(select(ClientUnit).where(ClientUnit.client_id==arm.id, ClientUnit.code=='ARM-ABQ-PLANT'))
        har=db.scalar(select(ClientUnit).where(ClientUnit.client_id==arm.id, ClientUnit.code=='ARM-HAR'))
        user=db.scalar(select(User).where(User.email=='scope-test@aramco.local'))
        if not user:
            user=User(email='scope-test@aramco.local',full_name='Scope Test',password_hash=hash_password('Demo123!'),role=Role.CLIENT.value,client_id=arm.id); db.add(user); db.flush(); db.add(UserClientUnitAssignment(user_id=user.id,client_unit_id=abq.id))
        a1=db.scalar(select(Asset).where(Asset.asset_code=='ARM-ABQ-TEST'))
        if not a1:
            a1=Asset(client_id=arm.id,client_unit_id=abq_plant.id,asset_code='ARM-ABQ-TEST',serial_number='ABQ-SN',equipment_type='Transformer'); db.add(a1); db.flush()
        a2=db.scalar(select(Asset).where(Asset.asset_code=='ARM-HAR-TEST'))
        if not a2:
            a2=Asset(client_id=arm.id,client_unit_id=har.id,asset_code='ARM-HAR-TEST',serial_number='HAR-SN',equipment_type='Transformer'); db.add(a2); db.flush()
        for req,asset in [('REQ-ABQ-SCOPE',a1),('REQ-HAR-SCOPE',a2)]:
            if not db.scalar(select(SampleRequest).where(SampleRequest.request_number==req)):
                db.add(SampleRequest(request_number=req,public_token=req+'-TOKEN',barcode_value=req+'-BAR',status='TESTING',site_id=dmm.id,client_id=arm.id,asset_id=asset.id,sampler_id=sampler.id,sample_date_time=datetime.utcnow(),sampling_point='Bottom'))
        db.commit(); allowed=allowed_client_unit_ids(db,user,arm.id); assert abq.id in allowed and abq_plant.id in allowed and har.id not in allowed; db.close()
        r=client.post('/login/client',data={'email':'scope-test@aramco.local','password':'Demo123!'},follow_redirects=False); assert r.status_code==303
        page=client.get('/client'); assert page.status_code==200; assert 'REQ-ABQ-SCOPE' in page.text; assert 'REQ-HAR-SCOPE' not in page.text; assert 'Area: Abqaiq' in page.text


def test_admin_can_change_client_unit_scope_without_code_changes():
    with TestClient(app) as client:
        r=client.post('/login/employee',data={'email':'admin@tsco.local','password':'Demo123!'},follow_redirects=False); assert r.status_code==303
        db=SessionLocal(); arm=db.scalar(select(Client).where(Client.code=='ARM')); har=db.scalar(select(ClientUnit).where(ClientUnit.client_id==arm.id,ClientUnit.code=='ARM-HAR')); target=db.scalar(select(User).where(User.email=='client@aramco.local')); db.close()
        r=client.post(f'/admin/users/{target.id}/client-unit-scope',data={'assigned_client_unit_ids':str(har.id)},follow_redirects=False); assert r.status_code==303
        db=SessionLocal(); ids={x.client_unit_id for x in db.scalars(select(UserClientUnitAssignment).where(UserClientUnitAssignment.user_id==target.id)).all()}; assert ids=={har.id}; db.close()
