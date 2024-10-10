from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Sample, SampleStatus, QCResult, QCResults, Shipment
from app.schemas.pydantic_models import (
    QCResultsInput,
    SampleToMake,
    SamplesToMakeResponse,
    SampleToShip,
    SamplesToShipResponse,
    SamplesShippedInput,
    SampleTATStatusResponse,
)


async def get_sample_tat_status(sample_uuid: UUID, session: AsyncSession):
    # Fetch the order
    sample_stmt = select(Sample).where(Sample.sample_uuid == sample_uuid)
    smaple_result = await session.execute(sample_stmt)
    sample = smaple_result.scalar_one()

    if not sample:
        raise HTTPException(
            status_code=404, detail=f"Sample with UUID {sample_uuid} not found"
        )

    response = SampleTATStatusResponse(
        sample_uuid=sample.sample_uuid,
        order_placed=sample.created_at.isoformat(),
        sample_shipped=(
            sample.updated_at.isoformat()
            if sample.status == SampleStatus.SHIPPED
            else None
        ),
    )

    return response


async def get_samples_to_process(session: AsyncSession):
    # Query for samples that are in ORDERED status and don't have QC results
    samples_query = (
        select(Sample)
        .where(Sample.status == SampleStatus.ORDERED)
        .outerjoin(QCResults)
        .where(QCResults.qc_id == None)
        .order_by(Sample.created_at)
        .order_by(Sample.sample_uuid)
        .limit(96)
    )
    result = await session.execute(samples_query)
    samples = result.scalars().all()

    samples_to_make = [
        SampleToMake(
            sample_uuid=sample.sample_uuid,
            sequence=sample.sequence,
            created_at=sample.created_at.isoformat(),
        )
        for sample in samples
    ]

    return SamplesToMakeResponse(samples_to_make=samples_to_make)


async def log_qc_results(qc_results_input: QCResultsInput, session: AsyncSession):
    # Get all sample UUIDs from the input
    sample_uuids = [result.sample_uuid for result in qc_results_input.samples_made]

    # Fetch all samples with the given UUIDs
    stmt = select(Sample).where(Sample.sample_uuid.in_(sample_uuids))
    result = await session.execute(stmt)
    samples = {sample.sample_uuid: sample for sample in result.scalars().all()}

    # Check if all samples exist
    missing_samples = set(sample_uuids) - set(samples.keys())
    if missing_samples:
        raise HTTPException(
            status_code=400, detail=f"Samples not found: {missing_samples}"
        )

    # Fetch existing QC results for these samples
    qc_stmt = select(QCResults).where(
        QCResults.sample_id.in_([sample.sample_id for sample in samples.values()])
    )
    qc_result = await session.execute(qc_stmt)
    existing_qc_results = {qc.sample_id: qc for qc in qc_result.scalars().all()}

    # Process QC results
    for qc_result in qc_results_input.samples_made:
        sample = samples[qc_result.sample_uuid]

        # Check if QC results already exist for this sample
        if sample.sample_id in existing_qc_results:
            raise HTTPException(
                status_code=400,
                detail=f"QC results already exist for sample: {sample.sample_uuid}",
            )

        # Create new QC result
        new_qc_result = QCResults(
            sample_id=sample.sample_id,
            plate_id=qc_result.plate_id,
            well=qc_result.well,
            qc_1=qc_result.qc_1,
            qc_2=qc_result.qc_2,
            qc_3=qc_result.qc_3,
        )
        session.add(new_qc_result)

        # Update sample status based on QC results
        if (
            qc_result.qc_1 >= 10.0
            and qc_result.qc_2 >= 5.0
            and qc_result.qc_3 == QCResult.PASS
        ):
            sample.status = SampleStatus.PASSED_QC
        else:
            sample.status = SampleStatus.FAILED

    await session.commit()

    return {"message": "QC results logged successfully"}


async def get_samples_to_ship(session: AsyncSession):
    # Query for samples that have passed QC and are not shipped
    samples_query = (
        select(Sample, QCResults)
        .join(QCResults)
        .where(Sample.status == SampleStatus.PASSED_QC)
    )
    result = await session.execute(samples_query)
    samples_and_qc = result.all()

    samples_to_ship = [
        SampleToShip(
            sample_uuid=sample.sample_uuid,
            plate_id=qc_result.plate_id,
            well=qc_result.well,
        )
        for sample, qc_result in samples_and_qc
    ]

    return SamplesToShipResponse(samples_to_ship=samples_to_ship)


async def record_samples_shipped(
    samples_shipped_input: SamplesShippedInput, session: AsyncSession
):
    # Get all sample UUIDs from the input
    sample_uuids = samples_shipped_input.samples_shipped

    # Fetch all samples with the given UUIDs
    stmt = select(Sample).where(Sample.sample_uuid.in_(sample_uuids))
    result = await session.execute(stmt)
    samples = result.scalars().all()

    # Check if all samples exist and are in the correct state
    found_uuids = set(sample.sample_uuid for sample in samples)
    missing_uuids = set(sample_uuids) - found_uuids
    if missing_uuids:
        raise HTTPException(
            status_code=400, detail=f"Samples not found: {missing_uuids}"
        )

    shipped_samples = []
    for sample in samples:
        if sample.status != SampleStatus.PASSED_QC:
            raise HTTPException(
                status_code=400,
                detail=f"Sample {sample.sample_uuid} is not ready to be shipped. Current status: {sample.status}",
            )

        # Create shipment record
        new_shipment = Shipment(sample_id=sample.sample_id)
        session.add(new_shipment)

        # Update sample status
        sample.status = SampleStatus.SHIPPED
        sample.updated_at = datetime.utcnow()

        shipped_samples.append(sample.sample_uuid)

    await session.commit()

    return {"message": f"Successfully shipped samples: {shipped_samples}"}
