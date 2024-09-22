from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID, uuid4
from typing import List, Union
from pydantic import BaseModel
import json

from app.db import get_session, init_db
from app.models import Order, Sample, SampleStatus, QCResults


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("Starting up...")
    await init_db()
    yield
    # Shutdown code
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)


@app.get("/health-check/")
def health_check():
    return {"message": "OK"}


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)


@app.post("/orders/", response_model=Union[OrderResponse, DuplicateSamplesResponse])
async def place_order(
    order_input: OrderInput, session: AsyncSession = Depends(get_session)
):
    # Check for duplicate sample UUIDs within the input
    input_sample_uuids = [sample.sample_uuid for sample in order_input.order]
    if len(input_sample_uuids) != len(set(input_sample_uuids)):
        raise HTTPException(status_code=400, detail="Duplicate sample UUIDs in input")

    # Check for existing sample UUIDs in the database
    stmt = select(Sample).where(Sample.sample_uuid.in_(input_sample_uuids))
    result = await session.execute(stmt)
    existing_samples = result.scalars().all()

    if existing_samples:
        repeat_uuids = [sample.sample_uuid for sample in existing_samples]
        return JSONResponse(
            status_code=409,  # Using 409 Conflict for duplicate samples
            content=json.loads(
                json.dumps({"repeat_sample_uuids": repeat_uuids}, cls=UUIDEncoder)
            ),
        )

    # Create new order
    new_order = Order(order_uuid=uuid4())
    session.add(new_order)
    await session.flush()  # This will assign an order_id to new_order

    # Create samples
    for sample_input in order_input.order:
        new_sample = Sample(
            sample_uuid=sample_input.sample_uuid,
            order_id=new_order.order_id,
            sequence=sample_input.sequence,
            status=SampleStatus.ORDERED,
        )
        session.add(new_sample)

    await session.commit()

    return OrderResponse(order_uuid=new_order.order_uuid)


@app.get("/samples/to-process/", response_model=SamplesToMakeResponse)
async def list_samples_to_process(session: AsyncSession = Depends(get_session)):
    # Query for samples that are in ORDERED status and don't have QC results
    samples_query = (
        select(Sample)
        .where(Sample.status == SampleStatus.ORDERED)
        .outerjoin(QCResults)
        .where(QCResults.qc_id == None)
        .limit(96)
    )
    result = await session.execute(samples_query)
    samples = result.scalars().all()

    samples_to_make = [
        SampleToMake(sample_uuid=sample.sample_uuid, sequence=sample.sequence)
        for sample in samples
    ]

    return SamplesToMakeResponse(samples_to_make=samples_to_make)
