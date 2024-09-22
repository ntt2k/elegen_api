import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Order, Sample, SampleStatus
from app.schemas.pydantic_models import (
    OrderInput,
    OrderResponse,
    OrderStatusResponse,
    SampleStatusResponse,
)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)


async def create_order(order_input: OrderInput, session: AsyncSession):
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


async def get_order_status(order_uuid: UUID, session: AsyncSession):
    # Fetch the order
    order_stmt = select(Order).where(Order.order_uuid == order_uuid)
    order_result = await session.execute(order_stmt)
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404, detail=f"Order with UUID {order_uuid} not found"
        )

    # Fetch all samples for this order
    samples_stmt = select(Sample).where(Sample.order_id == order.order_id)
    samples_result = await session.execute(samples_stmt)
    samples = samples_result.scalars().all()

    # Prepare the response
    sample_statuses = [
        SampleStatusResponse(sample_uuid=sample.sample_uuid, status=sample.status)
        for sample in samples
    ]

    return OrderStatusResponse(sample_statuses=sample_statuses)
