from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session
from app.schemas.pydantic_models import OrderInput, OrderResponse, DuplicateSamplesResponse, OrderStatusRequest, OrderStatusResponse
from app.services.order_service import create_order, get_order_status

router = APIRouter()

@router.post("/orders/", response_model=OrderResponse | DuplicateSamplesResponse)
async def place_order(order_input: OrderInput, session: AsyncSession = Depends(get_session)):
    return await create_order(order_input, session)

@router.post("/orders/status", response_model=OrderStatusResponse)
async def get_order_status_route(request: OrderStatusRequest, session: AsyncSession = Depends(get_session)):
    return await get_order_status(request.order_uuid_to_get_sample_statuses_for, session)
