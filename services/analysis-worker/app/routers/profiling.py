import logging
import traceback
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.schemas import ProfilingRequest, ProfilingResult
from app.services.profiler import CSVProfiler
from app.core.config import settings
import httpx

router = APIRouter(prefix="/profiling", tags=["profiling"])
logger = logging.getLogger(__name__)


async def _notify_api(job_id: str, status: str, result: dict = None, error: str = None):
    """Notify the NestJS API of job completion."""
    api_url = f"http://api:3001/internal/jobs/{job_id}/complete"
    payload = {"status": status}
    if result:
        payload["result"] = result
    if error:
        payload["error"] = error
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(api_url, json=payload)
    except Exception as e:
        logger.warning(f"Failed to notify API for job {job_id}: {e}")


def _run_profiling(request: ProfilingRequest):
    """Synchronous profiling execution (called in background)."""
    import asyncio
    try:
        profiler = CSVProfiler(
            storage_path=settings.storage_path,
            parquet_base=settings.parquet_path,
            sample_size=settings.sample_size_rows,
        )
        result = profiler.profile(request.file_path, request.dataset_id)
        result_dict = result.model_dump()
        asyncio.run(_notify_api(request.job_id, "completed", result=result_dict))
        return result
    except Exception as e:
        logger.error(f"Profiling failed for dataset {request.dataset_id}: {e}")
        logger.error(traceback.format_exc())
        asyncio.run(_notify_api(request.job_id, "failed", error=str(e)))
        raise


@router.post("/run", response_model=dict)
async def start_profiling(request: ProfilingRequest, background_tasks: BackgroundTasks):
    """
    Trigger profiling for a dataset. Runs in background and notifies API when done.
    """
    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    background_tasks.add_task(_run_profiling, request)
    return {"status": "started", "job_id": request.job_id, "dataset_id": request.dataset_id}


@router.post("/run-sync", response_model=ProfilingResult)
async def run_profiling_sync(request: ProfilingRequest):
    """
    Synchronous profiling (for testing/small files).
    """
    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    try:
        profiler = CSVProfiler(
            storage_path=settings.storage_path,
            parquet_base=settings.parquet_path,
            sample_size=settings.sample_size_rows,
        )
        result = profiler.profile(request.file_path, request.dataset_id)
        return result
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
