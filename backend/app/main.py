from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routers import subscribers, reports, pipeline

app = FastAPI(title="Econ Briefing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = None


@app.on_event("startup")
async def startup():
    global scheduler
    models.Base.metadata.create_all(bind=engine)

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from app.pipeline.orchestrator import Orchestrator

    scheduler = AsyncIOScheduler()

    async def scheduled_run():
        import app.routers.pipeline as _pipeline_router
        if not _pipeline_router._is_running:
            _pipeline_router._is_running = True
            await _pipeline_router._run_pipeline()

    scheduler.add_job(scheduled_run, CronTrigger(hour=6, minute=0), id="daily_pipeline")
    scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(subscribers.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
