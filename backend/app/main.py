from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import time

from app.core.config import get_settings
from app.database.database import engine, Base
from app.api import api_router
from app.agents.scheduler import start_scheduler, stop_scheduler, scheduler_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

VERSION = "0.5.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")
    start_scheduler()
    logger.info("Cloud agent scheduler started — agents run independently of the desktop client")
    yield
    stop_scheduler()
    logger.info("Shutdown complete")


app = FastAPI(
    title="RainMoal Workspace",
    description="RainMoal Workspace — Give AI a job. Cloud agents run independently of the desktop client.",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.time() - start, 4))
    response.headers["X-RainMoal-Version"] = VERSION
    return response


app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": "RainMoal Workspace",
        "tagline": "Give AI a job.",
        "version": VERSION,
        "status": "running",
        "env": settings.APP_ENV,
        "agents": "cloud-scheduled",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": VERSION,
        "env": settings.APP_ENV,
        "scheduler": scheduler_status(),
    }


@app.get("/api/status")
async def api_status():
    return {
        "status": "ok",
        "version": VERSION,
        "env": settings.APP_ENV,
        "name": "RainMoal Workspace",
        "timestamp": time.time(),
    }
