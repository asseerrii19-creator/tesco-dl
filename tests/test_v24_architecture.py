import json
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.database import SessionLocal
from app.main import app
from app.models import ApprovalPolicy, Client, ClientUnit, Department, IntegrationQueueItem, Site, WorkflowDefinition, WorkflowStep

def login_admin(client):
    r=client.post('/login/employee',data={'email':'admin@tsco.local','password':'Demo123!'},follow_redirects=False); assert r.status_code==303

def test_enterprise_hierarchy_and_master_data_are_runtime_configurable():
    with TestClient(app) as client:
        login_admin(client)
        db=SessionLocal(); dmm=db.scalar(select(Site).where(Site.code=='DMM')); arm=db.scalar(select(Client).where(Client.code=='ARM')); db.close()
        r=client.post('/admin/hierarchy/departments',data={'site_id':str(dmm.id),'code':'ENG','name':'Engineering'},follow_redirects=False); assert r.status_code==303
        r=client.post('/admin/hierarchy/client-units',data={'client_id':arm.id,'unit_type':'PLANT','code':'PLANT-1','name':'Plant 1','parent_id':''},follow_redirects=False); assert r.status_code==303
        db=SessionLocal(); assert db.scalar(select(Department).where(Department.code=='ENG')); assert db.scalar(select(ClientUnit).where(ClientUnit.client_id==arm.id,ClientUnit.code=='PLANT-1')); db.close()
        page=client.get('/admin/master-data'); assert page.status_code==200 and 'Master Data Center' in page.text

def test_workflow_versions_and_approval_policy_can_be_published_without_code_change():
    with TestClient(app) as client:
        login_admin(client)
        steps='order | Order | operations_manager |\nreceive | Receive | sample_receiving |\nreview | Review | senior_chemist | approval\nrelease | Release | technical_manager | approval,terminal'
        r=client.post('/admin/workflows',data={'code':'UAT-FLOW','name':'UAT Flow','sample_type':'OIL','site_id':'','steps':steps},follow_redirects=False); assert r.status_code==303
        r=client.post('/admin/workflows/approval-policies',data={'code':'UAT-APPROVAL','name':'UAT Approval','entity_type':'SAMPLE_REPORT','site_id':'','stages':'Entry | lab_technician\nReview | senior_chemist\nRelease | technical_manager'},follow_redirects=False); assert r.status_code==303
        db=SessionLocal(); flow=db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.code=='UAT-FLOW',WorkflowDefinition.active.is_(True))); assert flow; assert len(db.scalars(select(WorkflowStep).where(WorkflowStep.workflow_id==flow.id)).all())==4; policy=db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.code=='UAT-APPROVAL')); assert policy and len(json.loads(policy.stages_json))==3; db.close()

def test_integration_queue_control_page_is_available():
    with TestClient(app) as client:
        login_admin(client)
        db=SessionLocal(); item=IntegrationQueueItem(integration='LMS',direction='OUTBOUND',operation='UNSUPPORTED_TEST',status='FAILED',payload_json='{}',attempts=1,last_error='demo'); db.add(item); db.commit(); iid=item.id; db.close()
        page=client.get('/admin/integrations'); assert page.status_code==200 and 'Integration Control' in page.text
        r=client.post(f'/admin/integrations/{iid}/retry',follow_redirects=False); assert r.status_code==303
        db=SessionLocal(); item=db.get(IntegrationQueueItem,iid); assert item.status=='FAILED' and item.attempts==2; db.close()
