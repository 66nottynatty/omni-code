from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from typing import Optional, List, Dict, Any
from github import Github
import structlog
from datetime import datetime
from app.database.session import get_db, SessionLocal
from app.core.config import get_settings
from app.core.security import security_manager
from app.database.models import User, Workspace, CodeChunk

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(prefix="/repos", tags=["repos"])

def get_user_github_token(user_id: int, db: Session) -> str:
    """Retrieve and decrypt user's GitHub token."""
    user = db.query(User).get(user_id)
    if not user or not user.access_token_encrypted:
        return settings.github_token
    return security_manager.decrypt_token(user.access_token_encrypted)

async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> int:
    """Extract user ID from Authorization header."""
    if not authorization:
        return 1
    user_id = security_manager.validate_bearer_token(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(user_id)

@router.get("/{owner}/{repo}/tree")
async def get_repo_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        tree = r.get_git_tree(branch, recursive=True)
        files = [
            {
                "path": item.path,
                "type": item.type,
                "size": item.size,
                "name": os.path.basename(item.path),
                "extension": os.path.splitext(item.path)[1]
            }
            for item in tree.tree
        ]
        return {
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "files": files,
            "total": len(files)
        }
    except Exception as e:
        logger.error("repo_tree_failed", owner=owner, repo=repo, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{owner}/{repo}/file")
async def get_repo_file(
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        content = r.get_contents(path, ref=branch)
        return {
            "path": path,
            "content": content.decoded_content.decode(),
            "sha": content.sha,
            "encoding": "utf-8"
        }
    except Exception as e:
        logger.error("repo_file_failed", path=path, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{owner}/{repo}/readme")
async def get_repo_readme(
    owner: str,
    repo: str,
    branch: str = "main",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    try:
        g = Github(token)
        r = g.get_repo(f"{owner}/{repo}")
        readme = r.get_readme()
        return {
            "content": readme.decoded_content.decode(),
            "name": readme.name
        }
    except Exception as e:
        return {"content": "", "name": "README.md"}

@router.post("/{owner}/{repo}/index")
async def index_repository(
    request: Request,
    owner: str,
    repo: str,
    branch: str = "main",
    incremental: bool = True,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    token = get_user_github_token(user_id, db)
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo,
        Workspace.branch == branch
    ).first()
    if not workspace:
        workspace = Workspace(owner=owner, repo=repo, branch=branch)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    from app.core.scheduler import scheduler
    
    job_id = f"index_{workspace.id}_{datetime.utcnow().timestamp()}"
    scheduler.add_job(
        _run_indexing,
        'date',
        run_date=datetime.utcnow(),
        args=[workspace.id, owner, repo, branch, incremental, token],
        id=job_id,
        replace_existing=True
    )
    logger.info("indexing_started", workspace_id=workspace.id, job_id=job_id)
    return {
        "status": "indexing_started",
        "workspace_id": workspace.id,
        "job_id": job_id
    }

async def _run_indexing(workspace_id: int, owner: str, repo: str, branch: str, incremental: bool, token: str):
    from app.intelligence.indexer import CodebaseIndexer
    db = SessionLocal()
    try:
        indexer = CodebaseIndexer(db, token)
        stats = await indexer.index_repo(workspace_id, owner, repo, branch, incremental)
        logger.info("indexing_complete", workspace_id=workspace_id, stats=stats)
    except Exception as e:
        logger.error("indexing_failed", workspace_id=workspace_id, error=str(e))
    finally:
        db.close()

@router.get("/{owner}/{repo}/index/status")
async def get_index_status(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo
    ).first()
    if not workspace:
        return {"status": "not_indexed"}
    chunk_count = db.query(CodeChunk).filter(
        CodeChunk.workspace_id == workspace.id
    ).count()
    return {
        "workspace_id": workspace.id,
        "status": "indexed",
        "chunk_count": chunk_count,
        "last_updated": workspace.created_at.isoformat()
    }

@router.post("/{owner}/{repo}/search")
async def search_code(
    owner: str,
    repo: str,
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    workspace = db.query(Workspace).filter(
        Workspace.owner == owner,
        Workspace.repo == repo
    ).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Repository not indexed")
    from app.intelligence.indexer import CodebaseIndexer
    indexer = CodebaseIndexer(db)
    results = await indexer.search_similar(workspace.id, query, limit)
    return {"results": results}
