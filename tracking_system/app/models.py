from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class SampleStatus(str, Enum):
    ORDERED = "ORDERED"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    PASSED_QC = "PASSED_QC"
    SHIPPED = "SHIPPED"

class QCResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class Order(SQLModel, table=True):
    order_id: Optional[int] = Field(default=None, primary_key=True)
    order_uuid: UUID = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    samples: List["Sample"] = Relationship(back_populates="order")

class Sample(SQLModel, table=True):
    sample_id: Optional[int] = Field(default=None, primary_key=True)
    sample_uuid: UUID = Field(unique=True, index=True)
    order_id: int = Field(foreign_key="order.order_id", index=True)
    sequence: str
    status: SampleStatus = Field(default=SampleStatus.ORDERED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    order: Order = Relationship(back_populates="samples")
    qc_result: Optional["QCResults"] = Relationship(back_populates="sample")
    shipment: Optional["Shipment"] = Relationship(back_populates="sample")

class QCResults(SQLModel, table=True):
    qc_id: Optional[int] = Field(default=None, primary_key=True)
    sample_id: int = Field(foreign_key="sample.sample_id", index=True)
    plate_id: int
    well: str
    qc_1: float
    qc_2: float
    qc_3: QCResult
    created_at: datetime = Field(default_factory=datetime.utcnow)

    sample: Sample = Relationship(back_populates="qc_result")

class Shipment(SQLModel, table=True):
    shipment_id: Optional[int] = Field(default=None, primary_key=True)
    sample_id: int = Field(foreign_key="sample.sample_id", index=True)
    shipped_at: datetime = Field(default_factory=datetime.utcnow)

    sample: Sample = Relationship(back_populates="shipment")
    