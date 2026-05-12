"""
Tools for agents - GitHub integration, file operations, shell commands, and skill access.
"""
import os
import re
import subprocess
import json
from typing import Optional, List, Dict, Any
from github import Github, GithubException
from langchain_core.tools import tool
from app.database.models import ActionHistory, CodeChunk
from app.database.session import SessionLocal
from app.core.config import get_settings
from app.core.embedding import get_embedding_model
from app.core.cache import get_cache

settings = get_settings()


def get_github_client() -> Github:
    """Get authenticated GitHub client."""
    return Github(settings.github_token)


# ===== File Operations =====

@tool
def read_file(file_path: str) -> str:
    """Read content from a local file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(thread_id: int, file_path: str, content: str) -> str:
    """Write content to a local file and record in ActionHistory."""
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
        
        # Publish change to Redis for Live Coding View
        cache = get_cache()
        if cache and cache.client:
            cache.client.publish(f"file_changes_thread_{thread_id}", json.dumps({
                "type": "file_change",
                "path": file_path,
                "content": content
            }))
            
    finally:
        db.close()

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return f"Successfully wrote to {file_path}"


@tool
def read_multiple_files(file_paths: List[str]) -> Dict[str, str]:
    """Read multiple files at once."""
    results = {}
    for path in file_paths:
        results[path] = read_file(path)
    return results


# ===== GitHub Operations =====

@tool
def get_repo_file(owner: str, repo: str, file_path: str, branch: str = "main") -> str:
    """Read a file from a GitHub repository."""
    try:
        g = get_github_client()
        repo_obj = g.get_repo(f"{owner}/{repo}")
        contents = repo_obj.get_contents(file_path, ref=branch)
        return contents.decoded_content.decode()
    except GithubException as e:
        return f"GitHub error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def create_or_update_file(
    owner: str,
    repo: str,
    file_path: str,
    content: str,
    message: str = "Update file",
    branch: str = "main"
) -> str:
    """Create or update a file in a GitHub repository."""
    try:
        g = get_github_client()
        repo_obj = g.get_repo(f"{owner}/{repo}")
        
        try:
            contents = repo_obj.get_contents(file_path, ref=branch)
            repo_obj.update_file(
                contents.path,
                message,
                content,
                contents.sha,
                branch=branch
            )
            return f"Updated {file_path} on {branch}"
        except GithubException as e:
            if e.status == 404:
                repo_obj.create_file(
                    file_path,
                    message,
                    content,
                    branch=branch
                )
                return f"Created {file_path} on {branch}"
    except GithubException as e:
        return f"GitHub error: {str(e)}"


@tool
def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main"
) -> str:
    """Create a pull request in a GitHub repository."""
    try:
        g = get_github_client()
        repo_obj = g.get_repo(f"{owner}/{repo}")
        
        pr = repo_obj.create_pull(
            title=title,
            body=body,
            head=head,
            base=base
        )
        
        return f"Created PR: {pr.html_url}"
    except GithubException as e:
        return f"GitHub error: {str(e)}"


# ===== Codebase Search =====

@tool
def search_codebase(workspace_id: int, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search the codebase using vector embeddings."""
    db = SessionLocal()
    try:
        embedding_model = get_embedding_model()
        query_embedding = embedding_model.embed_query(query)
        
        results = db.query(CodeChunk).filter(
            CodeChunk.workspace_id == workspace_id
        ).order_by(
            CodeChunk.embedding.cosine_distance(query_embedding)
        ).limit(max_results).all()
        
        return [
            {
                "file_path": r.file_path,
                "name": r.name,
                "chunk_type": r.chunk_type,
                "content": r.content,
                "signature": r.signature,
                "start_line": r.start_line,
                "end_line": r.end_line
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


# ===== Shell Operations =====

@tool
def run_terminal(thread_id: int, command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
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
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        
        # Publish output to Redis
        cache = get_cache()
        if cache and cache.client:
            cache.client.publish(f"agent_logs_thread_{thread_id}", json.dumps({
                "type": "shell_output",
                "command": command,
                "output": output
            }))
            
        return output if output else "Command executed with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


# ===== Skill Access =====

@tool
def read_skill(skill_name: str, workspace_id: Optional[int] = None) -> str:
    """Read the full content of a skill from the skills library."""
    db = SessionLocal()
    try:
        from app.intelligence.skill_registry import SkillRegistry
        
        registry = SkillRegistry(db)
        skill = registry.get_skill_by_name(skill_name, workspace_id)
        
        if not skill:
            available_skills = registry.list_skills(workspace_id=workspace_id)
            skill_names = [s.name for s in available_skills]
            return f"Skill '{skill_name}' not found. Available skills: {', '.join(skill_names)}"
        
        return f"# {skill.name}\n\n{skill.content}"
    finally:
        db.close()
