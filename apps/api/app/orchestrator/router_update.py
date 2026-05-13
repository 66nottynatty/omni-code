@router.post("/{graph_id}/pause")
async def pause_graph(graph_id: str):
    from app.core.cache import get_cache
    cache = get_cache()
    if cache.client:
        cache.client.set(f"graph_signal_{graph_id}", "pause")
    return {"status": "pausing", "graph_id": graph_id}


@router.post("/{graph_id}/resume")
async def resume_graph(graph_id: str):
    from app.core.cache import get_cache
    cache = get_cache()
    if cache.client:
        cache.client.delete(f"graph_signal_{graph_id}")
    return {"status": "resuming", "graph_id": graph_id}
