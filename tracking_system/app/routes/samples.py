from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session
from app.schemas.pydantic_models import (
    SamplesToMakeResponse,
    QCResultsInput,
    SamplesToShipResponse,
    SamplesShippedInput,
    SampleStatusRequest,
    SampleTATStatusResponse,
)
from app.services.sample_service import (
    get_samples_to_process,
    log_qc_results,
    get_samples_to_ship,
    record_samples_shipped,
)

router = APIRouter()


@router.post("/sample/status", response_model=SampleTATStatusResponse)
async def get_sample_status_route(
    request: SampleStatusRequest, session: AsyncSession = Depends(get_session)
):
    return await get_sample_tat_status(
        request.sample_uuid_to_get_tat_for, session
    )


@router.get("/samples/to-process/", response_model=SamplesToMakeResponse)
async def list_samples_to_process(session: AsyncSession = Depends(get_session)):
    return await get_samples_to_process(session)


@router.post("/samples/qc-results/")
async def log_qc_results_route(
    qc_results_input: QCResultsInput, session: AsyncSession = Depends(get_session)
):
    return await log_qc_results(qc_results_input, session)


@router.get("/samples/to-ship/", response_model=SamplesToShipResponse)
async def list_samples_to_ship(session: AsyncSession = Depends(get_session)):
    return await get_samples_to_ship(session)


@router.post("/samples/shipped/")
async def record_samples_shipped_route(
    samples_shipped_input: SamplesShippedInput,
    session: AsyncSession = Depends(get_session),
):
    return await record_samples_shipped(samples_shipped_input, session)
