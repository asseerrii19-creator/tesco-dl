from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Role(str, Enum):
    FIELD_SAMPLER = "field_sampler"
    CLIENT_SAMPLER = "client_sampler"
    CLIENT_OPERATIONS = "client_operations"
    SAMPLING_SUPERVISOR = "sampling_supervisor"
    OPERATIONS_MANAGER = "operations_manager"
    DATA_ENTRY = "data_entry"
    SAMPLE_RECEIVING = "sample_receiving"
    LAB_TECHNICIAN = "lab_technician"
    SENIOR_CHEMIST = "senior_chemist"
    QUALITY = "quality"
    TECHNICAL_MANAGER = "technical_manager"
    MANAGEMENT = "management"
    CLIENT = "client"
    SYSTEM_ADMIN = "system_admin"


class SampleStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RETURNED = "RETURNED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    AWAITING_RECEIPT = "AWAITING_RECEIPT"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    REGISTERED = "REGISTERED"
    TESTING = "TESTING"
    TECHNICAL_REVIEW = "TECHNICAL_REVIEW"
    REPORT_APPROVED = "REPORT_APPROVED"
    REPORT_RELEASED = "REPORT_RELEASED"


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    laboratory_name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    contact_email: Mapped[str] = mapped_column(String(180), default="")
    contact_phone: Mapped[str] = mapped_column(String(60), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    site: Mapped[Site | None] = relationship()
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_department_site_code"),)


class ClientUnit(Base):
    __tablename__ = "client_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"), nullable=True, index=True)
    unit_type: Mapped[str] = mapped_column(String(40), default="SITE", index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    client: Mapped[Client] = relationship()
    parent: Mapped["ClientUnit | None"] = relationship(remote_side="ClientUnit.id")
    __table_args__ = (UniqueConstraint("client_id", "code", name="uq_client_unit_code"),)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(40), index=True)
    job_title: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped[Client | None] = relationship(foreign_keys=[client_id])
    site: Mapped[Site | None] = relationship()
    department: Mapped["Department | None"] = relationship()
    client_assignments: Mapped[list["UserClientAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserClientAssignment.user_id"
    )
    client_unit_assignments: Mapped[list["UserClientUnitAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserClientUnitAssignment.user_id"
    )


class UserClientAssignment(Base):
    __tablename__ = "user_client_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="client_assignments", foreign_keys=[user_id])
    client: Mapped[Client] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_user_client_assignment"),)




class UserClientUnitAssignment(Base):
    __tablename__ = "user_client_unit_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_unit_id: Mapped[int] = mapped_column(ForeignKey("client_units.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="client_unit_assignments", foreign_keys=[user_id])
    client_unit: Mapped[ClientUnit] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "client_unit_id", name="uq_user_client_unit_assignment"),)


class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    number: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    description: Mapped[str] = mapped_column(String(240), default="")
    client: Mapped[Client] = relationship()
    __table_args__ = (UniqueConstraint("client_id", "number", name="uq_quote_client_number"),)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), nullable=True)
    number: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    client: Mapped[Client] = relationship()
    quotation: Mapped[Quotation | None] = relationship()
    __table_args__ = (UniqueConstraint("client_id", "number", name="uq_po_client_number"),)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    client_unit_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"), nullable=True, index=True)
    asset_code: Mapped[str] = mapped_column(String(80), index=True)
    serial_number: Mapped[str] = mapped_column(String(120), index=True)
    equipment_type: Mapped[str] = mapped_column(String(80), default="Transformer")
    manufacturer: Mapped[str] = mapped_column(String(120), default="")
    voltage_kv: Mapped[float | None] = mapped_column(Float, nullable=True)
    rated_mva: Mapped[float | None] = mapped_column(Float, nullable=True)
    station_name: Mapped[str] = mapped_column(String(160), default="")
    asset_location_label: Mapped[str] = mapped_column(String(200), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    client: Mapped[Client] = relationship()
    client_unit: Mapped["ClientUnit | None"] = relationship()
    __table_args__ = (
        UniqueConstraint("client_id", "asset_code", name="uq_asset_client_code"),
    )


class SamplingOrder(Base):
    __tablename__ = "sampling_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), nullable=True)
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="Sampling request")
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    site: Mapped[Site] = relationship()
    client: Mapped[Client] = relationship()
    quotation: Mapped[Quotation | None] = relationship()
    purchase_order: Mapped[PurchaseOrder | None] = relationship()
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    supervisor: Mapped[User | None] = relationship(foreign_keys=[supervisor_id])
    assignments: Mapped[list["SamplingAssignment"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class SamplingAssignment(Base):
    __tablename__ = "sampling_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sampling_orders.id"), index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    assigned_sampler_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assignment_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    source_party: Mapped[str] = mapped_column(String(30), default="TSCO")
    requested_package: Mapped[str] = mapped_column(String(120), default="Routine Test")
    sampling_point: Mapped[str] = mapped_column(String(100), default="Main Tank Bottom")
    container_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="UNASSIGNED", index=True)
    instructions: Mapped[str] = mapped_column(Text, default="")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_sample_id: Mapped[int | None] = mapped_column(ForeignKey("sample_requests.id", use_alter=True, name="fk_assignment_completed_sample"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped[SamplingOrder] = relationship(back_populates="assignments")
    asset: Mapped[Asset | None] = relationship()
    assigned_sampler: Mapped[User | None] = relationship(foreign_keys=[assigned_sampler_id])


class OperationsState(Base):
    __tablename__ = "operations_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), unique=True, index=True)
    json_data: Mapped[str] = mapped_column(Text, default="{}")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    site: Mapped[Site] = relationship()
    updated_by: Mapped[User | None] = relationship()


class SampleRequest(Base):
    __tablename__ = "sample_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    public_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    barcode_value: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default=SampleStatus.DRAFT.value, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), nullable=True)
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    sampler_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    sampling_assignment_id: Mapped[int | None] = mapped_column(ForeignKey("sampling_assignments.id"), nullable=True, index=True)
    submission_channel: Mapped[str] = mapped_column(String(30), default="TSCO_FIELD")

    sample_date_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    sampling_point: Mapped[str] = mapped_column(String(100))
    requested_package: Mapped[str] = mapped_column(String(120), default="Routine Test")
    oil_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    field_notes: Mapped[str] = mapped_column(Text, default="")
    container_count: Mapped[int] = mapped_column(Integer, default=1)

    lms_number: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    client_sample_reference: Mapped[str] = mapped_column(String(100), default="")
    data_entry_note: Mapped[str] = mapped_column(Text, default="")
    return_reason: Mapped[str] = mapped_column(Text, default="")
    rejection_reason: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    site: Mapped[Site] = relationship()
    client: Mapped[Client] = relationship()
    quotation: Mapped[Quotation | None] = relationship()
    purchase_order: Mapped[PurchaseOrder | None] = relationship()
    asset: Mapped[Asset] = relationship()
    sampler: Mapped[User] = relationship(foreign_keys=[sampler_id])
    sampling_assignment: Mapped[SamplingAssignment | None] = relationship(foreign_keys=[sampling_assignment_id])
    photos: Mapped[list["SamplePhoto"]] = relationship(back_populates="sample", cascade="all, delete-orphan")
    events: Mapped[list["CustodyEvent"]] = relationship(back_populates="sample", cascade="all, delete-orphan")
    issues: Mapped[list["DataQualityIssue"]] = relationship(back_populates="sample", cascade="all, delete-orphan")


class SamplePhoto(Base):
    __tablename__ = "sample_photos"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int] = mapped_column(ForeignKey("sample_requests.id"), index=True)
    kind: Mapped[str] = mapped_column(String(60), default="General")
    original_name: Mapped[str] = mapped_column(String(220))
    stored_path: Mapped[str] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sample: Mapped[SampleRequest] = relationship(back_populates="photos")


class CustodyEvent(Base):
    __tablename__ = "custody_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int] = mapped_column(ForeignKey("sample_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    sample: Mapped[SampleRequest] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship()


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int] = mapped_column(ForeignKey("sample_requests.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    description: Mapped[str] = mapped_column(Text)
    reported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sample: Mapped[SampleRequest] = relationship(back_populates="issues")
    reported_by: Mapped[User | None] = relationship()


class LmsSyncLog(Base):
    __tablename__ = "lms_sync_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int] = mapped_column(ForeignKey("sample_requests.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    operation: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    external_reference: Mapped[str] = mapped_column(String(120), default="")
    request_payload: Mapped[str] = mapped_column(Text, default="")
    response_payload: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TechnicalAssessmentRecord(Base):
    __tablename__ = "technical_assessment_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int] = mapped_column(ForeignKey("sample_requests.id"), unique=True, index=True)
    profile: Mapped[str] = mapped_column(String(80), default="IEC 60422 / IEC 60599")
    system_findings_json: Mapped[str] = mapped_column(Text, default="{}")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sample: Mapped[SampleRequest] = relationship()
    reviewed_by: Mapped[User | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    summary: Mapped[str] = mapped_column(String(260), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])


class ControlledDocument(Base):
    __tablename__ = "controlled_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    document_type: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    revision: Mapped[str] = mapped_column(String(40), default="00")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    effective_date: Mapped[str] = mapped_column(String(20), default="")
    original_filename: Mapped[str] = mapped_column(String(240))
    stored_filename: Mapped[str] = mapped_column(String(300), unique=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    site: Mapped[Site | None] = relationship()
    uploaded_by: Mapped[User | None] = relationship()


class TestPackageConfig(Base):
    __tablename__ = "test_package_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    scope: Mapped[str] = mapped_column(String(80), default="GENERAL")
    tests_json: Mapped[str] = mapped_column(Text, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    site: Mapped[Site | None] = relationship()


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    sample_type: Mapped[str] = mapped_column(String(80), default="GENERAL")
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    site: Mapped[Site | None] = relationship()
    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.step_order")
    __table_args__ = (UniqueConstraint("site_id", "code", "version", name="uq_workflow_site_code_version"),)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflow_definitions.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    step_key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(160))
    responsible_role: Mapped[str] = mapped_column(String(40), default="")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow: Mapped[WorkflowDefinition] = relationship(back_populates="steps")
    __table_args__ = (UniqueConstraint("workflow_id", "step_order", name="uq_workflow_step_order"),)


class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), default="SAMPLE_REPORT")
    stages_json: Mapped[str] = mapped_column(Text, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    site: Mapped[Site | None] = relationship()
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_approval_site_code"),)


class IntegrationQueueItem(Base):
    __tablename__ = "integration_queue"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_request_id: Mapped[int | None] = mapped_column(ForeignKey("sample_requests.id"), nullable=True, index=True)
    integration: Mapped[str] = mapped_column(String(40), default="LMS", index=True)
    direction: Mapped[str] = mapped_column(String(20), default="OUTBOUND")
    operation: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    external_reference: Mapped[str] = mapped_column(String(120), default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sample: Mapped[SampleRequest | None] = relationship()
