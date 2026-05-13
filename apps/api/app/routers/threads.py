from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/threads", tags=["threads"])

@router.get("/{graph_id}/actions")
async def get_thread_actions(graph_id: str):
    return [
        {"id": "a1", "type": "tool_call", "tool": "read_file", "status": "success"},
        {"id": "a2", "type": "thought", "content": "I should fix the import error."}
    ]

@router.get("/{graph_id}/logs")
async def get_thread_logs(graph_id: str):
    return ["Initialized graph", "Started task: Fix imports", "Tool call: read_file"]
