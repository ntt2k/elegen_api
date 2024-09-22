from pydantic import BaseModel
from typing import List
from uuid import UUID
from app.models import SampleStatus, QCResult


class SampleInput(BaseModel):
    sample_uuid: UUID
    sequence: str


class OrderInput(BaseModel):
    order: List[SampleInput]


class OrderResponse(BaseModel):
    order_uuid: UUID


class DuplicateSamplesResponse(BaseModel):
    repeat_sample_uuids: List[UUID]


class SampleToMake(BaseModel):
    sample_uuid: UUID
    sequence: str


class SamplesToMakeResponse(BaseModel):
    samples_to_make: List[SampleToMake]


class QCResultInput(BaseModel):
    sample_uuid: UUID
    plate_id: int
    well: str
    qc_1: float
    qc_2: float
    qc_3: QCResult


class QCResultsInput(BaseModel):
    samples_made: List[QCResultInput]


class SampleToShip(BaseModel):
    sample_uuid: UUID
    plate_id: int
    well: str


class SamplesToShipResponse(BaseModel):
    samples_to_ship: List[SampleToShip]


class SamplesShippedInput(BaseModel):
    samples_shipped: List[UUID]


class SampleStatusResponse(BaseModel):
    sample_uuid: UUID
    status: SampleStatus


class OrderStatusResponse(BaseModel):
    sample_statuses: List[SampleStatusResponse]


class OrderStatusRequest(BaseModel):
    order_uuid_to_get_sample_statuses_for: UUID
