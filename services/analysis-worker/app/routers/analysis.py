import logging
import traceback
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models.schemas import AnalysisRequest, AnalysisResult, InsightCandidate
from app.services.metrics_engine import MetricsEngine
from app.services.insight_engine import InsightCandidateEngine
from app.services.llm_service import LLMService
from app.core.config import settings
import httpx

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)

llm_service = LLMService()


async def _notify_api(job_id: str, status: str, result: dict = None, error: str = None):
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


def _run_analysis(request: AnalysisRequest):
    """Full analysis pipeline: metrics → insights → LLM commentary."""
    try:
        parquet_path = request.parquet_path
        if not Path(parquet_path).exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        # 1. Deterministic metrics
        logger.info(f"Computing metrics for dataset {request.dataset_id}")
        engine = MetricsEngine(parquet_path)
        try:
            metrics = engine.compute_all(request.mapping)
            row_count = engine._get_row_count()
        finally:
            engine.close()

        # 2. Insight candidates
        logger.info(f"Generating insight candidates for dataset {request.dataset_id}")
        insight_engine = InsightCandidateEngine()
        candidates = insight_engine.generate(metrics, request.mapping, row_count)

        # 3. Build evidence pack for LLM
        evidence_pack = _build_evidence_pack(
            request.dataset_id, row_count, metrics, candidates, request.mapping
        )

        # 4. LLM commentary
        logger.info(f"Generating LLM commentary for dataset {request.dataset_id}")
        llm_report = llm_service.generate_commentary(evidence_pack)

        # 5. Build result
        result = AnalysisResult(
            dataset_id=request.dataset_id,
            analysis_run_id=request.analysis_run_id,
            metrics=metrics,
            insight_candidates=candidates,
            llm_report=llm_report,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        result_dict = result.model_dump()
        asyncio.run(_notify_api(request.job_id, "completed", result=result_dict))
        return result
    except Exception as e:
        logger.error(f"Analysis failed for dataset {request.dataset_id}: {e}")
        logger.error(traceback.format_exc())
        asyncio.run(_notify_api(request.job_id, "failed", error=str(e)))
        raise


def _build_evidence_pack(
    dataset_id: str,
    row_count: int,
    metrics: dict,
    candidates: list[InsightCandidate],
    mapping,
) -> dict:
    """Build the structured evidence pack that is sent to the LLM."""
    volume_data = metrics.get("volume_over_time", [])
    date_range = None
    if volume_data:
        periods = [v["period"] for v in volume_data if v["period"] != "unknown"]
        if periods:
            date_range = f"{min(periods)} to {max(periods)}"

    domains_detected = []
    if mapping.category_column:
        domains_detected.append("categorical classification")
    if mapping.created_at_column:
        domains_detected.append("time-series")
    if mapping.assignee_column:
        domains_detected.append("actor/resource")
    if mapping.customer_column:
        domains_detected.append("customer segmentation")
    if mapping.satisfaction_column:
        domains_detected.append("satisfaction measurement")

    return {
        "dataset_summary": {
            "row_count": row_count,
            "column_count": len(mapping.model_dump()),
            "date_range": date_range,
            "domains_detected": domains_detected,
        },
        "schema_profile": [],
        "semantic_inference": [],
        "mapping_decisions": mapping.model_dump(exclude_none=True),
        "metric_summary": metrics,
        "ranked_insights": [c.model_dump() for c in candidates],
        "output_language": "en",
        "target_audience": "process_manager",
    }


@router.post("/run", response_model=dict)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Trigger analysis pipeline in background."""
    parquet_path = Path(request.parquet_path)
    if not parquet_path.exists():
        raise HTTPException(status_code=404, detail=f"Parquet file not found: {request.parquet_path}")

    background_tasks.add_task(_run_analysis, request)
    return {
        "status": "started",
        "job_id": request.job_id,
        "dataset_id": request.dataset_id,
        "analysis_run_id": request.analysis_run_id,
    }


@router.post("/run-sync", response_model=AnalysisResult)
async def run_analysis_sync(request: AnalysisRequest):
    """Synchronous analysis (for testing)."""
    try:
        result = _run_analysis(request)
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
