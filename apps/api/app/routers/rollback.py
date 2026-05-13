from fastapi import APIRouter

router = APIRouter(prefix="/rollback", tags=["rollback"])

@router.post("/{graph_id}")
async def rollback_graph(graph_id: str):
    return {"status": "success", "reverted_files": ["main.py", "utils.py"]}
