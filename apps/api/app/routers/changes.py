from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/changes", tags=["changes"])

@router.get("/{graph_id}")
async def get_changes(graph_id: str):
    return [
        {
            "id": "c1",
            "file": "main.py",
            "hunk": "@@ -1,3 +1,4 @@\n import os\n+import sys\n print('hello')",
            "status": "pending"
        }
    ]

@router.post("/{change_id}/accept")
async def accept_change(change_id: str):
    return {"status": "accepted"}

@router.post("/{change_id}/reject")
async def reject_change(change_id: str):
    return {"status": "rejected"}
