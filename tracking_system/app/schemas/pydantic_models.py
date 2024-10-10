from pydantic import BaseModel
from uuid import UUID
from app.models import SampleStatus, QCResult


class SampleInput(BaseModel):
    sample_uuid: UUID
    sequence: str


class OrderInput(BaseModel):
    order: list[SampleInput]


class OrderResponse(BaseModel):
    order_uuid: UUID


class DuplicateSamplesResponse(BaseModel):
    repeat_sample_uuids: list[UUID]


class SampleToMake(BaseModel):
    sample_uuid: UUID
    sequence: str


class SamplesToMakeResponse(BaseModel):
    samples_to_make: list[SampleToMake]


class QCResultInput(BaseModel):
    sample_uuid: UUID
    plate_id: int
    well: str
    qc_1: float
    qc_2: float
    qc_3: QCResult


class QCResultsInput(BaseModel):
    samples_made: list[QCResultInput]


class SampleToShip(BaseModel):
    sample_uuid: UUID
    plate_id: int
    well: str


class SamplesToShipResponse(BaseModel):
    samples_to_ship: list[SampleToShip]


class SamplesShippedInput(BaseModel):
    samples_shipped: list[UUID]


class SampleStatusResponse(BaseModel):
    sample_uuid: UUID
    status: SampleStatus


class OrderStatusResponse(BaseModel):
    sample_statuses: list[SampleStatusResponse]


class OrderStatusRequest(BaseModel):
    order_uuid_to_get_sample_statuses_for: UUID

class SampleStatusRequest(BaseModel):
    sample_uuid_to_get_tat_for: UUID


class SampleTATStatusResponse(BaseModel):
    sample_uuid: UUID
    order_placed: str
    sample_shipped: str | None