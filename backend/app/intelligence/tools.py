import os
import subprocess
from typing import Optional
from github import Github
from langchain_core.tools import tool
from app.database.models import ActionHistory, CodeChunk
from app.database.session import SessionLocal
from app.core.config import get_settings
from sqlalchemy import text

settings = get_settings()

@tool
def read_file(owner: str, repo: str, file_path: str) -> str:
    """Read a file from GitHub."""
    g = Github(settings.github_token)
    repo_obj = g.get_repo(f"{owner}/{repo}")
    contents = repo_obj.get_contents(file_path)
    return contents.decoded_content.decode()

@tool
def write_file(thread_id: int, file_path: str, content: str) -> str:
    """Write a file to the local filesystem and record in ActionHistory."""
    # Snapshot to ActionHistory
    db = SessionLocal()
    try:
        content_before = None
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content_before = f.read()
        
        action = ActionHistory(
            thread_id=thread_id,
            action_type="write",
            file_path=file_path,
            content_before=content_before,
            content_after=content,
        )
        db.add(action)
        db.commit()
    finally:
        db.close()

    # Write file
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)
    
    return f"Successfully wrote to {file_path}"

@tool
def search_codebase(workspace_id: int, query_embedding: list[float]) -> list[dict]:
    """Search the codebase using vector embeddings."""
    db = SessionLocal()
    try:
        # Use pgvector to search
        results = db.query(CodeChunk).filter(
            CodeChunk.workspace_id == workspace_id
        ).order_by(
            CodeChunk.embedding.cosine_distance(query_embedding)
        ).limit(5).all()
        
        return [
            {"file_path": r.file_path, "content": r.content}
            for r in results
        ]
    finally:
        db.close()

@tool
def run_terminal(thread_id: int, command: str) -> str:
    """Execute a shell command and record in ActionHistory."""
    db = SessionLocal()
    try:
        action = ActionHistory(
            thread_id=thread_id,
            action_type="shell",
            command=command
        )
        db.add(action)
        db.commit()
    finally:
        db.close()

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        return output if output else "Command executed with no output."
    except Exception as e:
        return str(e)

@tool
def report_blocker(task_id: int, reason: str) -> str:
    """Report a blocker that prevents the agent from continuing."""
    db = SessionLocal()
    try:
        from app.database.models import BackgroundTask, BlockerNotification
        task = db.query(BackgroundTask).get(task_id)
        if task:
            task.status = "blocked"
            blocker = BlockerNotification(task_id=task_id, reason=reason)
            db.add(blocker)
            db.commit()
            
            # Webhook notification
            payload = task.payload or {}
            webhook_url = payload.get("webhook_url")
            if webhook_url:
                import httpx
                try:
                    httpx.post(webhook_url, json={
                        "task_id": task_id, 
                        "status": "blocked",
                        "reason": reason
                    }, timeout=5.0)
                except Exception as e:
                    print(f"Failed to send webhook: {e}")

            return f"Blocker reported: {reason}. Task is now paused."
        return "Task not found."
    finally:
        db.close()
