import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter()

_is_running = False
_last_run: Optional[datetime] = None


async def _run_pipeline():
    global _is_running, _last_run
    from app.pipeline.orchestrator import Orchestrator
    try:
        await Orchestrator().run(sectors=["macro", "finance", "tech", "ai", "energy", "realestate", "politics", "startup"])
    finally:
        _last_run = datetime.utcnow()
        _is_running = False


@router.post("/pipeline/run")
async def run_pipeline(background_tasks: BackgroundTasks):
    global _is_running
    if _is_running:
        raise HTTPException(status_code=409, detail="already_running")
    _is_running = True
    background_tasks.add_task(_run_pipeline)
    return {"status": "started", "message": "Pipeline execution started"}


@router.get("/pipeline/status")
async def pipeline_status():
    from app.main import scheduler

    next_run = None
    if scheduler is not None:
        job = scheduler.get_job("daily_pipeline")
        if job and job.next_run_time:
            next_run = job.next_run_time

    return {
        "status": "running" if _is_running else "idle",
        "last_run": _last_run,
        "next_run": next_run,
    }
