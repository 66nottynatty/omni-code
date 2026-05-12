from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

scheduler = AsyncIOScheduler()

def start_scheduler():
    job_stores = {
        'default': SQLAlchemyJobStore(url=settings.database_url)
    }
    
    if not scheduler.running:
        scheduler.configure(jobstores=job_stores)
        scheduler.start()
        logger.info("scheduler_started")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("scheduler_stopped")
