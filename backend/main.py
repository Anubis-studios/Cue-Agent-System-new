"""FastAPI application for the Cue Agent System."""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import ALLOWED_ORIGINS, DATABASE_PATH
from backend.db.database import init_db, save_conversation
from backend.llm_chain import LLMUnavailableError, generate
from backend.tools import execute_tool, registry

logger = logging.getLogger(__name__)

APP_VERSION = "1.1.0"

# Matches messages like "calculate 2+2" / "compute sqrt..." / "eval 3*4".
_TOOL_TRIGGER = re.compile(r"(?:calculate|compute|eval)\s*(.+)", re.IGNORECASE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DATABASE_PATH)
    yield


app = FastAPI(
    title="Cue Agent System",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    agent_id: str = "default"
    use_tools: bool = True


class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


def _run_tool_if_requested(message: str) -> str | None:
    """Detect a calculation request and run the ``calculate`` tool."""
    match = _TOOL_TRIGGER.search(message)
    if not match:
        return None
    try:
        result = execute_tool("calculate", {"expr": match.group(1).strip()})
        return f"The result is {result}"
    except Exception as exc:  # noqa: BLE001 - tool failure is non-fatal
        logger.info("Tool execution failed: %s", exc)
        return None


async def _answer(message: str, use_tools: bool) -> tuple[str, str]:
    prompt = message
    if use_tools:
        tool_result = _run_tool_if_requested(message)
        if tool_result:
            prompt = f"{message}\n\nTool result: {tool_result}"
    return await generate(prompt)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


@app.post("/api/chat/{agent_id}")
async def chat(agent_id: str, req: ChatRequest) -> dict:
    try:
        reply, provider = await _answer(req.message, req.use_tools)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - map unexpected errors to 500
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        save_conversation(agent_id, req.message, reply, provider)
    except Exception as exc:  # noqa: BLE001 - persistence failure is non-fatal
        logger.warning("DB save failed: %s", exc)

    return {
        "agent_id": agent_id,
        "reply": reply,
        "provider": provider,
        "success": True,
    }


@app.get("/api/tools")
async def list_tools() -> dict:
    tools = {
        name: {"description": info["description"], "parameters": info["parameters"]}
        for name, info in registry.items()
    }
    return {"tools": tools}


@app.post("/api/tools/execute")
async def exec_tool(req: ToolRequest) -> dict:
    try:
        result = execute_tool(req.tool_name, req.arguments)
    except Exception as exc:  # noqa: BLE001 - bad tool call from client
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "result": result}


@app.websocket("/ws/{agent_id}")
async def ws_endpoint(websocket: WebSocket, agent_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            reply, provider = await generate(data)
            await websocket.send_json(
                {"agent_id": agent_id, "reply": reply, "provider": provider}
            )
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
