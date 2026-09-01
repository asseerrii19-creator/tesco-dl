from __future__ import annotations

import os

from sqlalchemy import select

from .database import SessionLocal
from .models import ApprovalPolicy, Asset, Client, ClientUnit, Department, PurchaseOrder, Quotation, Role, Site, User, UserClientAssignment, UserClientUnitAssignment, WorkflowDefinition, WorkflowStep
from .security import hash_password


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def seed() -> None:
    db = SessionLocal()
    try:
        dammam = db.scalar(select(Site).where(Site.code == "DMM"))
        if not dammam:
            dammam = Site(code="DMM", name="Dammam", laboratory_name="Transformer Oil Laboratory")
            db.add(dammam)
            db.flush()
        if not db.scalar(select(Site).where(Site.code == "JBL")):
            db.add(Site(code="JBL", name="Jubail", laboratory_name="Hydrocarbon Laboratory", active=False))
        if not db.scalar(select(Site).where(Site.code == "BHR")):
            db.add(Site(code="BHR", name="Bahrain", laboratory_name="Laboratory Operations", active=False))
        db.flush()
        departments = [
            (None, "CORP", "Corporate Management"),
            (dammam.id, "OPS", "Operations"),
            (dammam.id, "RCV", "Sample Receiving"),
            (dammam.id, "LAB", "Laboratory Operations"),
            (dammam.id, "QLT", "Quality"),
        ]
        for sid, code, name in departments:
            stmt = select(Department).where(Department.code == code)
            stmt = stmt.where(Department.site_id.is_(None)) if sid is None else stmt.where(Department.site_id == sid)
            if not db.scalar(stmt): db.add(Department(site_id=sid, code=code, name=name, active=True))

        bootstrap_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@tsco.local").lower().strip()
        bootstrap_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "Demo123!")
        admin = db.scalar(select(User).where(User.email == bootstrap_email))
        if not admin:
            admin = User(
                email=bootstrap_email,
                full_name=os.getenv("BOOTSTRAP_ADMIN_NAME", "System Administrator"),
                password_hash=hash_password(bootstrap_password),
                role=Role.SYSTEM_ADMIN.value,
                site_id=dammam.id,
                must_change_password=_truthy("REQUIRE_BOOTSTRAP_PASSWORD_CHANGE", "false"),
            )
            db.add(admin)

        if not _truthy("SEED_DEMO_DATA", "true"):
            db.commit()
            return

        clients: dict[str, Client] = {}
        for code, name in [
            ("ARM", "Saudi Aramco"),
            ("SEC", "Saudi Electricity Company"),
            ("GPEL", "GPEL"),
        ]:
            client = db.scalar(select(Client).where(Client.code == code))
            if not client:
                client = Client(code=code, name=name)
                db.add(client)
                db.flush()
            clients[code] = client

        sec = clients["SEC"]
        # Client hierarchies are seeded as examples of long-term scoped access.
        hierarchy_specs = [
            ("SEC", None, "REGION", "SEC-EAST", "Eastern Region"),
            ("SEC", None, "REGION", "SEC-CENTRAL", "Central Region"),
            ("SEC", None, "REGION", "SEC-WEST", "Western Region"),
            ("SEC", None, "REGION", "SEC-SOUTH", "Southern Region"),
            ("ARM", None, "AREA", "ARM-ABQ", "Abqaiq"),
            ("ARM", None, "AREA", "ARM-HAR", "Haradh"),
            ("ARM", None, "AREA", "ARM-DHA", "Dhahran"),
        ]
        unit_map = {}
        for client_code, parent_code, unit_type, code, name in hierarchy_specs:
            c = clients[client_code]
            unit = db.scalar(select(ClientUnit).where(ClientUnit.client_id == c.id, ClientUnit.code == code))
            if not unit:
                parent = unit_map.get((client_code, parent_code)) if parent_code else None
                unit = ClientUnit(client_id=c.id, parent_id=parent.id if parent else None, unit_type=unit_type, code=code, name=name, active=True)
                db.add(unit); db.flush()
            unit_map[(client_code, code)] = unit
        child_specs = [
            ("SEC", "SEC-EAST", "SUBSTATION", "SEC-DMM-WEST", "Dammam West Substation"),
            ("ARM", "ARM-ABQ", "FACILITY", "ARM-ABQ-PLANT", "Abqaiq Plant"),
            ("ARM", "ARM-HAR", "FACILITY", "ARM-HAR-PLANT", "Haradh Gas Plant"),
            ("ARM", "ARM-DHA", "FACILITY", "ARM-DHA-HQ", "Dhahran Facilities"),
        ]
        for client_code, parent_code, unit_type, code, name in child_specs:
            c=clients[client_code]; parent=unit_map[(client_code,parent_code)]
            unit=db.scalar(select(ClientUnit).where(ClientUnit.client_id==c.id,ClientUnit.code==code))
            if not unit:
                unit=ClientUnit(client_id=c.id,parent_id=parent.id,unit_type=unit_type,code=code,name=name,active=True); db.add(unit); db.flush()
            unit_map[(client_code,code)] = unit
        quote = db.scalar(select(Quotation).where(Quotation.client_id == sec.id, Quotation.number == "QT-SEC-2026-014"))
        if not quote:
            quote = Quotation(client_id=sec.id, number="QT-SEC-2026-014", description="Transformer oil testing services")
            db.add(quote)
            db.flush()
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.client_id == sec.id, PurchaseOrder.number == "PO-SEC-2026-221"))
        if not po:
            po = PurchaseOrder(client_id=sec.id, quotation_id=quote.id, number="PO-SEC-2026-221")
            db.add(po)
        asset = db.scalar(select(Asset).where(Asset.client_id == sec.id, Asset.asset_code == "SEC-DMM-TR-001"))
        if not asset:
            asset = Asset(
                client_id=sec.id,
                client_unit_id=unit_map[("SEC","SEC-DMM-WEST")].id,
                asset_code="SEC-DMM-TR-001",
                serial_number="SN-SEC-884120",
                equipment_type="Power Transformer",
                manufacturer="Demo Manufacturer",
                voltage_kv=132,
                rated_mva=100,
                station_name="Dammam West Substation",
                asset_location_label="Bay 4 / Main Transformer",
                latitude=26.4207,
                longitude=50.0888,
            )
            db.add(asset)

        demo_password = hash_password("Demo123!")
        user_specs = [
            ("fieldman@tsco.local", "Ahmed Field Sampler", Role.FIELD_SAMPLER.value, dammam.id, None),
            ("supervisor@tsco.local", "Sampling Supervisor", Role.SAMPLING_SUPERVISOR.value, dammam.id, None),
            ("operations@tsco.local", "Operations Manager", Role.OPERATIONS_MANAGER.value, dammam.id, None),
            ("clientsampler@sec.local", "SEC Client Sampler", Role.CLIENT_SAMPLER.value, dammam.id, sec.id),
            ("clientops@sec.local", "SEC Client Operations", Role.CLIENT_OPERATIONS.value, dammam.id, sec.id),
            ("intake@tsco.local", "Data Entry User", Role.DATA_ENTRY.value, dammam.id, None),
            ("receiving@tsco.local", "Sample Receiving User", Role.SAMPLE_RECEIVING.value, dammam.id, None),
            ("chemist@tsco.local", "Laboratory Chemist", Role.LAB_TECHNICIAN.value, dammam.id, None),
            ("quality@tsco.local", "Quality Reviewer", Role.QUALITY.value, dammam.id, None),
            ("manager@tsco.local", "Dammam Laboratory Manager", Role.MANAGEMENT.value, dammam.id, None),
            ("corporate@tsco.local", "Corporate Management", Role.MANAGEMENT.value, None, None),
            ("senior@tsco.local", "Senior Chemist", Role.SENIOR_CHEMIST.value, dammam.id, None),
            ("client@sec.local", "SEC Client User", Role.CLIENT.value, None, sec.id),
            ("client@aramco.local", "Saudi Aramco Corporate User", Role.CLIENT.value, None, clients["ARM"].id),
            ("abqaiq@aramco.local", "Aramco Abqaiq User", Role.CLIENT.value, None, clients["ARM"].id),
            ("eastern@sec.local", "SEC Eastern Region User", Role.CLIENT.value, None, sec.id),
        ]
        users: dict[str, User] = {}
        for email, name, role, site_id, client_id in user_specs:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email,
                    full_name=name,
                    password_hash=demo_password,
                    role=role,
                    site_id=site_id,
                    client_id=client_id,
                )
                db.add(user)
                db.flush()
            users[email] = user

        # Scoped client accounts: corporate users have no unit assignment; regional users are constrained to a subtree.
        for email, unit_key in [
            ("abqaiq@aramco.local", ("ARM","ARM-ABQ")),
            ("eastern@sec.local", ("SEC","SEC-EAST")),
        ]:
            usr=users[email]; unit=unit_map[unit_key]
            if not db.scalar(select(UserClientUnitAssignment).where(UserClientUnitAssignment.user_id==usr.id, UserClientUnitAssignment.client_unit_id==unit.id)):
                db.add(UserClientUnitAssignment(user_id=usr.id, client_unit_id=unit.id))

        fieldman = users["fieldman@tsco.local"]
        if not db.scalar(
            select(UserClientAssignment).where(
                UserClientAssignment.user_id == fieldman.id,
                UserClientAssignment.client_id == sec.id,
            )
        ):
            db.add(UserClientAssignment(user_id=fieldman.id, client_id=sec.id))

        flow = db.scalar(select(WorkflowDefinition).where(WorkflowDefinition.site_id.is_(None), WorkflowDefinition.code=="LAB-SAMPLE-LIFECYCLE", WorkflowDefinition.active.is_(True)))
        if not flow:
            flow=WorkflowDefinition(site_id=None,code="LAB-SAMPLE-LIFECYCLE",name="Integrated Sample Lifecycle",sample_type="TRANSFORMER OIL",version=1,active=True); db.add(flow); db.flush()
            steps=[
                (1,"sampling_order","Sampling Order",Role.OPERATIONS_MANAGER.value,False,False),
                (2,"supervisor_assignment","Supervisor Assignment",Role.SAMPLING_SUPERVISOR.value,False,False),
                (3,"field_capture","Field Sampling & Capture",Role.FIELD_SAMPLER.value,False,False),
                (4,"data_entry","Data Entry Verification",Role.DATA_ENTRY.value,False,False),
                (5,"lms_registration","LMS Registration",Role.DATA_ENTRY.value,False,False),
                (6,"receiving","Physical Receiving",Role.SAMPLE_RECEIVING.value,False,False),
                (7,"laboratory","Laboratory Operations",Role.LAB_TECHNICIAN.value,False,False),
                (8,"technical_review","Technical Review",Role.SENIOR_CHEMIST.value,True,False),
                (9,"report_release","Report Release",Role.TECHNICAL_MANAGER.value,True,True),
            ]
            for order,key,label,role,approval,terminal in steps: db.add(WorkflowStep(workflow_id=flow.id,step_order=order,step_key=key,label=label,responsible_role=role,approval_required=approval,terminal=terminal))
        if not db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.site_id.is_(None),ApprovalPolicy.code=="REPORT-RELEASE")):
            db.add(ApprovalPolicy(site_id=None,code="REPORT-RELEASE",name="Technical Report Release",entity_type="SAMPLE_REPORT",stages_json='[{"stage":"Result Entry","role":"lab_technician"},{"stage":"Technical Review","role":"senior_chemist"},{"stage":"Report Release","role":"technical_manager"}]',active=True))
        db.commit()
    finally:
        db.close()
