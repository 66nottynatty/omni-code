from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional, Dict
import asyncio
import json
import os
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["terminal"])

class TerminalSession:
    """Manages a terminal session with bi-directional communication."""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.process: Optional[asyncio.subprocess.Process] = None
        self._output_task: Optional[asyncio.Task] = None
        self._input_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the terminal process."""
        self.process = await asyncio.create_subprocess_shell(
            "/bin/bash",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "TERM": "xterm-256color"}
        )
        
        self._output_task = asyncio.create_task(self._read_output())
        logger.info("terminal_started", session_id=self.session_id)

    async def _read_output(self):
        """Read process output and send to WebSocket."""
        while self.process and self.process.stdout:
            try:
                data = await self.process.stdout.read(1024)
                if not data:
                    break
                await self.websocket.send_text(data.decode('utf-8', errors='replace'))
            except Exception as e:
                logger.error("terminal_read_error", error=str(e))
                break

    async def send_input(self, data: str):
        """Send input to the terminal process."""
        if self.process and self.process.stdin:
            self.process.stdin.write(data.encode())
            await self.process.stdin.drain()

    async def close(self):
        """Clean up the terminal session."""
        if self._output_task:
            self._output_task.cancel()
        if self.process:
            self.process.terminate()
            try:
                await self.process.wait()
            except Exception:
                pass
        logger.info("terminal_closed", session_id=self.session_id)

# Active terminal sessions
terminal_sessions: Dict[str, TerminalSession] = {}

@router.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = TerminalSession(websocket, session_id)
    terminal_sessions[session_id] = session
    try:
        await session.start()
        while True:
            data = await websocket.receive_text()
            if data.startswith("{"):
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "resize":
                        # Resize logic would go here if supported by the shell
                        pass
                except json.JSONDecodeError:
                    await session.send_input(data)
            else:
                await session.send_input(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("terminal_error", session_id=session_id, error=str(e))
    finally:
        await session.close()
        if session_id in terminal_sessions:
            del terminal_sessions[session_id]

@router.get("/ws/terminal/{session_id}/status")
async def get_terminal_status(session_id: str):
    return {
        "session_id": session_id,
        "active": session_id in terminal_sessions
    }
