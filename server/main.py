import os
import sys
import asyncio

# Ensure server package directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from api.ingest_api import router as ingest_router
from api.timelines import router as timelines_router
from api.flags import router as flags_router
from api.projects import router as projects_router
from api.day_end import router as day_end_router
from api.punches import router as punches_router
from api.metrics import router as metrics_router
from mcp.server import router as mcp_router
from db.connection import init_db_pool, close_db_pool
from workers.scheduler import BackgroundIntelligenceWorker

worker = BackgroundIntelligenceWorker(interval_seconds=30)
worker_task = None

app = FastAPI(
    title="Enterprise ActivityWatch & AI Intelligence Platform",
    description="Stage A (Platform, Capture & Intelligence) and Stage B (Experience & Work Surfaces)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(ingest_router)
app.include_router(timelines_router)
app.include_router(flags_router)
app.include_router(projects_router)
app.include_router(day_end_router)
app.include_router(punches_router)
app.include_router(metrics_router)
app.include_router(mcp_router)

# Mount static files if present
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def on_startup():
    global worker_task
    await init_db_pool()
    worker_task = asyncio.create_task(worker.start())

@app.on_event("shutdown")
async def on_shutdown():
    if worker:
        worker.stop()
    if worker_task:
        worker_task.cancel()
    await close_db_pool()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Enterprise ActivityWatch & AI Intelligence Platform API</h1><p>Visit /docs for OpenAPI specs.</p>")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "activitywatch-enterprise-backend"}

