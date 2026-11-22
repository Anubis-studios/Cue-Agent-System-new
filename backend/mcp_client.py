"""Minimal Model Context Protocol (MCP) client + server registry.

Speaks JSON-RPC 2.0 over two transports:
  * ``stdio``   — spawns a local MCP server process (e.g. ``npx @modelcontextprotocol/server-*``)
  * ``http``    — posts JSON-RPC to a streamable-HTTP MCP endpoint

Discovered server tools are exposed to the agent through the standard tool
registry (``source="mcp"``), so everything downstream (chat pipeline, REST API,
frontend capability panel) treats them like any other usable tool function.

Reference: https://modelcontextprotocol.io
"""

import asyncio
import json
import logging
import os
import shlex
import time
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "cue-agent", "version": "1.2.0"}


class MCPError(RuntimeError):
    pass


class MCPServerConfig:
    def __init__(self, name: str, command: Optional[str] = None,
                 url: Optional[str] = None, env: Optional[dict] = None) -> None:
        self.name = name
        self.command = command
        self.url = url
        self.env = env or {}

    @property
    def transport(self) -> str:
        return "stdio" if self.command else "http"


def servers_from_env() -> dict[str, MCPServerConfig]:
    """Parse ``MCP_SERVERS`` env var: JSON object of name -> {command|url, env}.

    Example::

        MCP_SERVERS='{"fetch": {"command": "npx -y @modelcontextprotocol/server-fetch"}}'
    """
    raw = os.getenv("MCP_SERVERS", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Ignoring malformed MCP_SERVERS: %s", exc)
        return {}
    servers: dict[str, MCPServerConfig] = {}
    for name, cfg in data.items():
        servers[name] = MCPServerConfig(
            name=name,
            command=cfg.get("command"),
            url=cfg.get("url"),
            env=cfg.get("env"),
        )
    return servers


class StdioMCPSession:
    """JSON-RPC 2.0 over a subprocess's stdin/stdout (newline-delimited)."""

    def __init__(self, command: str, env: Optional[dict] = None) -> None:
        self._argv = shlex.split(command)
        self._env = env or {}
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._id = 0

    async def start(self) -> None:
        merged_env = {**os.environ, **self._env}
        self._proc = await asyncio.create_subprocess_exec(
            *self._argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=merged_env,
        )
        await self.request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })
        await self.notify("notifications/initialized", {})

    async def stop(self) -> None:
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()

    async def request(self, method: str, params: dict, timeout: float = 30.0) -> Any:
        assert self._proc and self._proc.stdin and self._proc.stdout
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        self._proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self._proc.stdin.drain()
        raw = await asyncio.wait_for(self._proc.stdout.readline(), timeout=timeout)
        if not raw:
            raise MCPError(f"Server closed while awaiting {method}")
        reply = json.loads(raw)
        if "error" in reply:
            raise MCPError(f"{method}: {reply['error']}")
        return reply.get("result")

    async def notify(self, method: str, params: dict) -> None:
        assert self._proc and self._proc.stdin
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self._proc.stdin.drain()


class HttpMCPSession:
    """JSON-RPC 2.0 over a streamable-HTTP MCP endpoint."""

    def __init__(self, url: str, env: Optional[dict] = None) -> None:
        self._url = url
        self._headers = {"Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"}
        for key, value in (env or {}).items():
            self._headers[key] = os.getenv(value, value)
        self._id = 0

    async def start(self) -> None:
        await self.request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        })

    async def stop(self) -> None:
        return None

    async def request(self, method: str, params: dict, timeout: float = 30.0) -> Any:
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
        try:
            async with client.post(self._url, json=msg, headers=self._headers) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MCPError(f"HTTP {resp.status}: {body[:200]}")
                payload = _parse_jsonrpc_body(body)
                if payload is None:
                    raise MCPError(f"No JSON-RPC payload for {method}")
                if "error" in payload:
                    raise MCPError(f"{method}: {payload['error']}")
                return payload.get("result")
        finally:
            await client.close()

    async def notify(self, method: str, params: dict) -> None:
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        try:
            async with client.post(self._url, json=msg, headers=self._headers):
                pass
        finally:
            await client.close()


def _parse_jsonrpc_body(body: str) -> Optional[dict]:
    body = body.strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass
    for line in body.splitlines():  # SSE framing: "data: {...}"
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
    return None


def _make_session(cfg: MCPServerConfig):
    if cfg.transport == "stdio":
        return StdioMCPSession(cfg.command or "", cfg.env)
    return HttpMCPSession(cfg.url or "", cfg.env)


class MCPManager:
    """Connects configured MCP servers, lists and proxies their tools."""

    def __init__(self) -> None:
        self.sessions: dict[str, Any] = {}
        self.server_tools: dict[str, list[dict]] = {}
        self.status: dict[str, str] = {}

    @property
    def connected(self) -> bool:
        return bool(self.sessions)

    async def connect(self, servers: dict[str, MCPServerConfig]) -> None:
        for name, cfg in servers.items():
            session = _make_session(cfg)
            try:
                await session.start()
                result = await session.request("tools/list", {})
                tools = result.get("tools", []) if isinstance(result, dict) else []
                self.sessions[name] = session
                self.server_tools[name] = tools
                self.status[name] = f"connected ({len(tools)} tools)"
                logger.info("MCP server '%s' connected with %d tools", name, len(tools))
            except Exception as exc:  # noqa: BLE001 - optional integration
                self.status[name] = f"failed: {exc}"
                logger.warning("MCP server '%s' failed to connect: %s", name, exc)
                await session.stop()

    async def call_tool(self, server: str, tool: str, arguments: dict) -> Any:
        session = self.sessions.get(server)
        if session is None:
            raise MCPError(f"MCP server '{server}' is not connected")
        result = await session.request(
            "tools/call", {"name": tool, "arguments": arguments}
        )
        if isinstance(result, dict) and "content" in result:
            parts = [c.get("text", "") for c in result["content"] if c.get("type") == "text"]
            return "\n".join(parts) if parts else result
        return result

    async def shutdown(self) -> None:
        for session in self.sessions.values():
            await session.stop()
        self.sessions.clear()


mcp_manager = MCPManager()

_last_discovery = 0.0


async def discover_and_register(force: bool = False) -> dict[str, Any]:
    """Connect to env-configured MCP servers and register their tools.

    Returns a summary dict.  Discovery is throttled to once per 60s unless
    ``force`` is set.
    """
    global _last_discovery
    from backend.tools import register_external_tool

    now = time.monotonic()
    if not force and now - _last_discovery < 60:
        return {"skipped": True, "servers": mcp_manager.status}
    _last_discovery = now

    servers = servers_from_env()
    if servers:
        await mcp_manager.connect(servers)

    for server_name, tools in mcp_manager.server_tools.items():
        for tool in tools:
            tool_name = tool.get("name", "")
            if not tool_name:
                continue

            async def _call(_server: str = server_name, _tool: str = tool_name, **kwargs: Any) -> Any:
                return await mcp_manager.call_tool(_server, _tool, kwargs)

            register_external_tool(
                name=f"mcp_{server_name}_{tool_name}",
                description=tool.get("description", f"MCP tool {tool_name} on {server_name}"),
                parameters=tool.get("inputSchema", {}).get("properties", {}),
                source="mcp",
                fn=_call,
                coroutine=True,
            )

    return {
        "servers": {k: v for k, v in mcp_manager.status.items()},
        "tools": {k: [t.get("name") for t in v] for k, v in mcp_manager.server_tools.items()},
    }
