from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import structlog
import json
import asyncio

logger = structlog.get_logger()
router = APIRouter(prefix="/stream", tags=["stream"])

@router.get("/{graph_id}")
async def stream_activity(
    graph_id: str,
    request: Request
) -> StreamingResponse:
    """
    Server-Sent Events stream for real-time activity updates.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = request.app.state.redis
        
        if not redis_client:
            yield "data: {\"type\": \"connected\", \"graph_id\": \"" + graph_id + "\"}\n\n"
            while True:
                if await request.is_disconnected(): break
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                await asyncio.sleep(5)
            return
        
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(
                f"graph_updates_{graph_id}", 
                f"agent_logs_{graph_id}",
                f"agent_tokens_{graph_id}"
            )
            
            yield f"data: {json.dumps({'type': 'connected', 'graph_id': graph_id})}\n\n"
            
            while True:
                if await request.is_disconnected(): break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data", b"").decode()
                    yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error("sse_stream_error", error=str(e))
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"
        finally:
            if redis_client:
                await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/agent/{task_id}")
async def stream_agent_logs(
    task_id: str,
    request: Request
) -> StreamingResponse:
    """Stream logs for a specific agent/task."""
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = request.app.state.redis
        
        if not redis_client:
            yield "data: {\"type\": \"connected\", \"task_id\": \"" + task_id + "\"}\n\n"
            while True:
                if await request.is_disconnected(): break
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                await asyncio.sleep(5)
            return
        
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"agent_logs_{task_id}", f"agent_tokens_{task_id}")
            
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"
            
            while True:
                if await request.is_disconnected(): break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data", b"").decode()
                    yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error("agent_log_stream_error", error=str(e))
        finally:
            if redis_client:
                await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/workspace/{workspace_id}")
async def stream_workspace_activity(
    workspace_id: int,
    request: Request
) -> StreamingResponse:
    """Stream all activity for a specific workspace."""
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = request.app.state.redis
        
        if not redis_client:
            yield "data: {\"type\": \"connected\", \"workspace_id\": " + str(workspace_id) + "}\n\n"
            while True:
                if await request.is_disconnected(): break
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                await asyncio.sleep(5)
            return
        
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(f"workspace_updates_{workspace_id}")
            
            yield f"data: {json.dumps({'type': 'connected', 'workspace_id': workspace_id})}\n\n"
            
            while True:
                if await request.is_disconnected(): break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data", b"").decode()
                    yield f"data: {data}\n\n"
                else:
                    yield ": keepalive\n\n"
                    
        except Exception as e:
            logger.error("workspace_sse_error", error=str(e))
        finally:
            if redis_client:
                await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
