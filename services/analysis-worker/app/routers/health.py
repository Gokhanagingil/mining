from fastapi import APIRouter
from app.core.config import settings
from pathlib import Path

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    storage_ok = Path(settings.storage_path).exists()
    parquet_ok = Path(settings.parquet_path).exists()
    return {
        "status": "ok",
        "storage_path": str(settings.storage_path),
        "storage_accessible": storage_ok,
        "parquet_path": str(settings.parquet_path),
        "parquet_accessible": parquet_ok,
        "llm_configured": bool(settings.openai_api_key),
    }
