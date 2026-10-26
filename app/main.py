import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.db import init_db
from app.api.routes import router
from app.scheduler.runner import start_scheduler, stop_scheduler, run_daily_pipeline
from scripts.generate_synthetic_data import create_snapshots

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database initialized, seed snapshots created and ingested
    init_db()
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    snapshots_dir = os.path.join(base_dir, "data", "snapshots")
    outbox_dir = os.path.join(base_dir, "outbox")
    
    os.makedirs(snapshots_dir, exist_ok=True)
    os.makedirs(outbox_dir, exist_ok=True)
    
    today_csv = os.path.join(snapshots_dir, "snapshot_2025-05-15.csv")
    if not os.path.exists(today_csv):
        create_snapshots(count=2000, output_dir=snapshots_dir)
        
    # Run initial pipeline pass to prime DB and outbox
    run_daily_pipeline(snapshot_date="2025-05-15", outbox_dir=outbox_dir)
    
    # Start APScheduler
    start_scheduler()
    
    yield
    
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title="Sales Forecast Automator",
    description="Automated Sales Forecast Pipeline, Quality Checks & System of Record Reconciliation for ATX Fall Co-Ops Bobathon",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router)

# Mount static files for dashboard UI
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
