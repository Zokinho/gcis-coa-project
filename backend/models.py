"""SQLAlchemy ORM models and Pydantic schemas."""

import enum
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ── Enums ──────────────────────────────────────────────────────────


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    review = "review"
    published = "published"
    flagged = "flagged"
    error = "error"


class ProductStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    published = "published"
    archived = "archived"


class Confidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EmailIngestionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    review = "review"
    completed = "completed"
    error = "error"


class AttachmentType(str, enum.Enum):
    coa_pdf = "coa_pdf"
    coa_photo = "coa_photo"
    product_photo = "product_photo"


# ── SQLAlchemy Models ──────────────────────────────────────────────


def _uuid() -> str:
    return str(uuid.uuid4())


class EmailIngestion(Base):
    __tablename__ = "email_ingestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(1024), default="")
    sender: Mapped[str] = mapped_column(String(512), default="")
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[EmailIngestionStatus] = mapped_column(Enum(EmailIngestionStatus), default=EmailIngestionStatus.pending)
    suggested_client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attachments: Mapped[list["EmailAttachment"]] = relationship(back_populates="email_ingestion", cascade="all, delete-orphan")


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email_ingestion_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_ingestions.id"))
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(255))
    attachment_type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType), default=AttachmentType.product_photo)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("coa_jobs.id"), nullable=True)

    email_ingestion: Mapped["EmailIngestion"] = relationship(back_populates="attachments")
    job: Mapped["CoAJob | None"] = relationship(back_populates="email_attachment")


class CoAJob(Base):
    __tablename__ = "coa_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"), nullable=True)
    email_ingestion_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("email_ingestions.id"), nullable=True)

    product: Mapped["Product | None"] = relationship(back_populates="job")
    redaction_regions: Mapped[list["RedactionRegion"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    email_attachment: Mapped["EmailAttachment | None"] = relationship(back_populates="job")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    strain_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lot_number: Mapped[str] = mapped_column(String(100))
    producer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lab: Mapped[str] = mapped_column(String(255))
    test_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="gacp-small")
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.draft)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[dict | list] = mapped_column(JSON, default=list)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["CoAJob | None"] = relationship(back_populates="product")
    test_data: Mapped[list["ProductTestData"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductTestData(Base):
    __tablename__ = "product_test_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    test_type: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    lab: Mapped[str] = mapped_column(String(255))
    test_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overall_result: Mapped[str | None] = mapped_column(String(50), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="test_data")


class RedactionRegion(Base):
    __tablename__ = "redaction_regions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("coa_jobs.id"))
    page: Mapped[int] = mapped_column(Integer)
    x_pct: Mapped[float] = mapped_column(Float)
    y_pct: Mapped[float] = mapped_column(Float)
    w_pct: Mapped[float] = mapped_column(Float)
    h_pct: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[Confidence] = mapped_column(Enum(Confidence), default=Confidence.high)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)

    job: Mapped["CoAJob"] = relationship(back_populates="redaction_regions")


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255))
    tiers: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)


# ── Pydantic Schemas ──────────────────────────────────────────────


class JobCreate(BaseModel):
    filename: str


class JobResponse(BaseModel):
    id: str
    filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    page_count: int
    product_id: str | None = None
    email_ingestion_id: str | None = None

    model_config = {"from_attributes": True}


class RedactionRegionResponse(BaseModel):
    id: str
    page: int
    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float
    reason: str
    confidence: Confidence
    approved: bool

    model_config = {"from_attributes": True}


class RedactionToggle(BaseModel):
    approved: bool | None = None
    x_pct: float | None = None
    y_pct: float | None = None
    w_pct: float | None = None
    h_pct: float | None = None


class ProductResponse(BaseModel):
    id: str
    name: str
    strain_type: str | None = None
    lot_number: str
    producer: str | None = None
    lab: str
    test_date: date | None = None
    report_number: str | None = None
    tier: str
    status: ProductStatus
    available: bool
    tags: list[str] = []
    client_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductTestDataResponse(BaseModel):
    id: str
    test_type: str
    data: dict
    lab: str
    test_date: date | None = None
    method: str | None = None
    overall_result: str | None = None

    model_config = {"from_attributes": True}


class ProductDetailResponse(BaseModel):
    id: str
    name: str
    strain_type: str | None = None
    lot_number: str
    producer: str | None = None
    lab: str
    test_date: date | None = None
    report_number: str | None = None
    tier: str
    status: ProductStatus
    available: bool
    tags: list[str] = []
    client_name: str | None = None
    created_at: datetime
    test_data: list[ProductTestDataResponse] = []

    model_config = {"from_attributes": True}


class AccessTokenCreate(BaseModel):
    label: str
    tiers: list[str] = []


class AccessTokenResponse(BaseModel):
    id: str
    token: str
    label: str
    tiers: list[str] = []
    active: bool
    created_at: datetime
    last_used: datetime | None = None
    use_count: int = 0

    model_config = {"from_attributes": True}


class AccessTokenUpdate(BaseModel):
    label: str | None = None
    tiers: list[str] | None = None
    active: bool | None = None


class AdminLogin(BaseModel):
    username: str
    password: str


class DashboardStats(BaseModel):
    total_jobs: int = 0
    queued: int = 0
    processing: int = 0
    review: int = 0
    published: int = 0
    flagged: int = 0
    error: int = 0
    total_products: int = 0
    products_published: int = 0
    total_tokens: int = 0


class ProductUpdate(BaseModel):
    name: str | None = None
    tier: str | None = None
    tags: list[str] | None = None
    available: bool | None = None


class ExtractionResult(BaseModel):
    """Result from AI extractor for a single page."""
    page: int = 0
    product_name: str | None = None
    strain_type: str | None = None
    lot_number: str | None = None
    producer: str | None = None
    lab: str | None = None
    test_date: str | None = None
    report_number: str | None = None
    compliance_status: str | None = None

    potency: dict | None = None
    terpenes: dict | None = None
    microbial: dict | None = None
    pesticides: dict | None = None
    heavy_metals: dict | None = None
    residual_solvents: dict | None = None
    mycotoxins: dict | None = None
    moisture: dict | None = None

    methodologies: list[str] = Field(default_factory=list)
    accreditations: list[str] = Field(default_factory=list)
    lab_notes: str | None = None

    redaction_regions: list[dict] = Field(default_factory=list)


# ── Email + Evernote Schemas ─────────────────────────────────────


class EmailAttachmentResponse(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    attachment_type: AttachmentType
    file_size: int
    job_id: str | None = None

    model_config = {"from_attributes": True}


class EmailIngestionResponse(BaseModel):
    id: str
    message_id: str
    subject: str
    sender: str
    body_text: str | None = None
    received_at: datetime | None = None
    status: EmailIngestionStatus
    suggested_client: str | None = None
    confirmed_client: str | None = None
    error_message: str | None = None
    created_at: datetime
    attachments: list[EmailAttachmentResponse] = []

    model_config = {"from_attributes": True}


class EmailClientConfirm(BaseModel):
    client_name: str


class EmailAttachmentReclassify(BaseModel):
    attachment_type: AttachmentType


class EvernotePreview(BaseModel):
    note_title: str
    is_new_note: bool
    content_html: str


class EvernotePushRequest(BaseModel):
    job_id: str
    client_name: str | None = None


class EvernotePushResult(BaseModel):
    note_guid: str
    note_title: str
    note_url: str
