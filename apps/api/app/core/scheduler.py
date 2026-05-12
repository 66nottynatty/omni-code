from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.core.config import get_settings

settings = get_settings()

scheduler = AsyncIOScheduler(
    jobstores={
        'default': SQLAlchemyJobStore(url=settings.database_url)
    }
)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()

async def run_scheduled_task(instruction: str, workspace_id: int):
    from app.orchestrator.engine import OrchestratorEngine
    from app.database.session import AsyncSessionLocal
    from app.core.cache import get_cache
    
    async with AsyncSessionLocal() as db:
        engine = OrchestratorEngine(db_session=db, redis_client=get_cache().client)
        await engine.execute_workflow(instruction, workspace_id)

def schedule_task(instruction: str, workspace_id: int, cron: str, timezone: str = "UTC"):
    from app.utils.cron_parser import parse_cron
    scheduler.add_job(
        run_scheduled_task,
        'cron',
        **parse_cron(cron),
        timezone=timezone,
        args=[instruction, workspace_id]
    )
