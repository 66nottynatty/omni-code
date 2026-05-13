"""
Real MCP (Model Context Protocol) Manager.
Implements stdio transport per the MCP 2024-11-05 spec.
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()


class MCPManager:
    def __init__(self):
        self.servers: Dict[str, dict] = {}
        self.tools: Dict[str, dict] = {}
        self._request_id = 0
        self._locks: Dict[str, asyncio.Lock] = {}

    async def register_server(self, name: str, config: Dict[str, Any]):
        """Register and handshake with an MCP server over stdio."""
        logger.info("registering_mcp_server", name=name)

        process = await asyncio.create_subprocess_exec(
            config["command"],
            *config.get("args", []),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**config.get("env", {})}
        )

        self.servers[name] = {"process": process, "type": "stdio"}
        self._locks[name] = asyncio.Lock()

        # MCP initialization handshake
        await self._send_request(name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "omnicode", "version": "1.0.0"}
        })
        await self._send_notification(name, "notifications/initialized", {})

        # Discover tools
        response = await self._send_request(name, "tools/list", {})
        for tool in response.get("tools", []):
            self.tools[tool["name"]] = {
                "server": name,
                "schema": tool.get("inputSchema", {}),
                "description": tool.get("description", "")
            }
            logger.info("mcp_tool_discovered", server=name, tool=tool["name"])

    async def _send_request(self, server_name: str, method: str, params: dict) -> dict:
        """Send a JSON-RPC request and await the response."""
        async with self._locks[server_name]:
            self._request_id += 1
            req_id = self._request_id

            message = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params
            }) + "\n"

            proc = self.servers[server_name]["process"]
            proc.stdin.write(message.encode())
            await proc.stdin.drain()

            # Read response
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=30.0)
            response = json.loads(line.decode().strip())

            if "error" in response:
                raise RuntimeError(f"MCP error: {response['error']}")

            return response.get("result", {})

    async def _send_notification(self, server_name: str, method: str, params: dict):
        """Send a JSON-RPC notification (no response expected)."""
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }) + "\n"
        proc = self.servers[server_name]["process"]
        proc.stdin.write(message.encode())
        await proc.stdin.drain()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on its registered MCP server."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available: {list(self.tools.keys())}")

        server_name = self.tools[tool_name]["server"]
        logger.info("calling_mcp_tool", server=server_name, tool=tool_name)

        result = await self._send_request(server_name, "tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        content = result.get("content", [])
        if content and isinstance(content, list):
            return "\n".join(
                item.get("text", "") for item in content if item.get("type") == "text"
            )
        return str(result)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, "description": info["description"], "server": info["server"]}
            for name, info in self.tools.items()
        ]

    async def close_all(self):
        """Gracefully terminate all MCP server processes."""
        for name, server in self.servers.items():
            try:
                server["process"].terminate()
                await server["process"].wait()
                logger.info("mcp_server_closed", name=name)
            except Exception as e:
                logger.warning("mcp_server_close_failed", name=name, error=str(e))
