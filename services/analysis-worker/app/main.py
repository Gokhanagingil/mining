import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import profiling, analysis, health
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Storage: {settings.storage_path}")
    logger.info(f"LLM configured: {bool(settings.openai_api_key)}")
    yield
    logger.info("Shutting down analysis worker")


app = FastAPI(
    title="Mining Analysis Worker",
    description="Process mining analysis engine: profiling, semantic inference, metrics, insights, LLM commentary",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profiling.router)
app.include_router(analysis.router)
