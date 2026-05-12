import asyncio
from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.database.models import BackgroundTask, TaskLog
from app.graphs.workflow import workflow
import json
import redis
from app.core.config import get_settings
import httpx

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

async def _run_agent_async(task_id: int):
    db = SessionLocal()
    task = db.query(BackgroundTask).get(task_id)
    if not task:
        db.close()
        return

    task.status = "running"
    db.commit()

    payload = task.payload or {}
    initial_state = {
        "messages": payload.get("messages", []),
        "current_repo": payload.get("repo_name"),
        "github_token": settings.github_token,
        "thread_id": payload.get("thread_id"),
        "workspace_id": task.workspace_id,
        "task_id": task.id
    }

    try:
        # We need to run the ainvoke in the current event loop
        result = await workflow.ainvoke(initial_state)
        
        # Reload task as it might have been updated (e.g. blocked)
        task = db.query(BackgroundTask).get(task_id)
        if task.status != "blocked":
            task.status = "completed"
            task.result = {"messages": [m.dict() if hasattr(m, 'dict') else m for m in result["messages"]]}
            db.commit()
            
            # Notify via webhook if needed
            if payload.get("webhook_url"):
                async with httpx.AsyncClient() as client:
                    await client.post(payload["webhook_url"], json={"task_id": task_id, "status": "completed"})

    except Exception as e:
        task.status = "failed"
        task.result = {"error": str(e)}
        db.commit()
        
        log = TaskLog(task_id=task_id, content=f"Task failed: {str(e)}", level="error")
        db.add(log)
        db.commit()
        
    finally:
        db.close()

@celery_app.task(name="run_agent_task")
def run_agent_task(task_id: int):
    try:
        asyncio.run(_run_agent_async(task_id))
    except Exception as e:
        # Fallback for environments where asyncio.run might fail
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_agent_async(task_id))
        finally:
            loop.close()
