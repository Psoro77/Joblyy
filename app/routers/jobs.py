from fastapi import APIRouter, HTTPException

from app.models.schemas import JobCreate, JobResponse, JobUpdate
from app.services.database import save_job, get_jobs, get_job, update_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
async def list_jobs(status: str | None = None):
    return await get_jobs(status=status)


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreate):
    return await save_job(
        title=job.title,
        company=job.company,
        url=job.url,
        description=job.description,
        source=job.source,
        match_score=job.match_score,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def read_job(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
async def patch_job(job_id: int, update: JobUpdate):
    existing = await get_job(job_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")

    fields = update.model_dump(exclude_none=True)
    return await update_job(job_id, **fields)
