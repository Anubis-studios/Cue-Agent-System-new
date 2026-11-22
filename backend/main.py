"""FastAPI application for the Cue Agent System.

Endpoints:
  POST /api/chat/{agent_id}      chat (auto-detects topic-expansion requests)
  POST /api/agent/explore        explicit topic -> skills + tools + MCP + memories
  GET  /api/tools                all usable functions (builtin, skill, mcp)
  POST /api/tools/execute        run any function by name
  GET  /api/providers            every free provider/model in the catalog
  GET  /api/memories/{agent_id}  list stored memories
  POST /api/memories/{agent_id}  store a memory
  DELETE /api/memories/{id}      forget a memory
  GET  /api/history/{agent_id}   conversation history from the database
  POST /api/jobs                 enqueue a background job (worker service)
  GET  /api/jobs/{job_id}        poll job status
  GET  /api/capabilities         one-shot overview of the whole system
  WS   /ws/{agent_id}            websocket chat
"""

import logging
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import agent as topic_agent
from backend.config import ALLOWED_ORIGINS, DATABASE_PATH, SKILLS_DIR
from backend.db import database
from backend.llm_chain import LLMUnavailableError, catalog, generate
from backend.mcp_client import discover_and_register, mcp_manager
from backend.skills import load_builtin_skills, load_user_skills
from backend.tools import execute_tool_async, registry

logger = logging.getLogger(__name__)

APP_VERSION = "1.2.0"

# Matches messages like "calculate 2+2" / "compute sqrt..." / "eval 3*4".
_TOOL_TRIGGER = re.compile(r"(?:calculate|compute|eval)\s*(.+)", re.IGNORECASE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(database.init_db)
    logger.info("Database ready (%s)", database.db_backend())
    loaded = load_builtin_skills()
    if SKILLS_DIR:
        loaded += load_user_skills(SKILLS_DIR)
    logger.info("Loaded %d skills: %s", len(loaded), ", ".join(loaded) or "-")
    try:
        summary = await discover_and_register(force=True)
        logger.info("MCP discovery: %s", summary.get("servers") or "no servers configured")
    except Exception as exc:  # noqa: BLE001 - MCP is optional
        logger.warning("MCP discovery failed: %s", exc)
    yield
    await mcp_manager.shutdown()


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
    expand_topic: Optional[bool] = None  # None = auto-detect phrasing


class ExploreRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=500)
    agent_id: str = "default"
    functions: Optional[list[str]] = None  # subset of usable functions
    use_mcp: bool = True


class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    kind: str = "fact"
    tags: list[str] = Field(default_factory=list)


class JobRequest(BaseModel):
    job_type: str = "video_processing"
    payload: dict = Field(default_factory=dict)


def _registry_public() -> dict:
    return {
        name: {
            "description": info["description"],
            "parameters": info["parameters"],
            "source": info.get("source", "builtin"),
        }
        for name, info in registry.items()
    }


def _run_tool_if_requested(message: str):
    """Detect a calculation request and schedule the ``calculate`` tool."""
    match = _TOOL_TRIGGER.search(message)
    if not match:
        return None
    try:
        result = execute_tool_sync_safe("calculate", {"expr": match.group(1).strip()})
        return f"The result is {result}"
    except Exception as exc:  # noqa: BLE001 - tool failure is non-fatal
        logger.info("Tool execution failed: %s", exc)
        return None


def execute_tool_sync_safe(name: str, args: dict):
    import asyncio

    return asyncio.run(execute_tool_async(name, args))


async def _answer(message: str, use_tools: bool) -> tuple[str, str]:
    prompt = message
    if use_tools:
        tool_result = _run_tool_if_requested(message)
        if tool_result:
            prompt = f"{message}\n\nTool result: {tool_result}"
    return await generate(prompt)


@app.get("/health")
async def health() -> dict:
    try:
        db = await run_in_threadpool(database.stats)
        backend = database.db_backend()
    except Exception as exc:  # noqa: BLE001
        db, backend = {"error": str(exc)}, "unavailable"
    return {
        "status": "ok",
        "version": APP_VERSION,
        "database": backend,
        "db_counts": db,
        "tools": len(registry),
        "mcp_servers": mcp_manager.status,
    }


@app.post("/api/chat/{agent_id}")
async def chat(agent_id: str, req: ChatRequest) -> dict:
    try:
        # Topic-expansion path: run all usable functions over the topic.
        should_expand = req.expand_topic
        topic = topic_agent.extract_topic(req.message) if should_expand is not False else None
        if should_expand is True and not topic:
            topic = req.message.strip()
        if topic and len(topic) >= 2:
            result = await topic_agent.explore_topic(agent_id, topic)
            return {"agent_id": agent_id, "success": True, **result}

        reply, provider = await _answer(req.message, req.use_tools)
        await run_in_threadpool(
            database.save_conversation, agent_id, req.message, reply, provider
        )
        return {
            "agent_id": agent_id,
            "reply": reply,
            "provider": provider,
            "success": True,
        }
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - map unexpected errors to 500
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/agent/explore")
async def explore(req: ExploreRequest) -> dict:
    try:
        return await topic_agent.explore_topic(
            req.agent_id, req.topic, req.functions, req.use_mcp
        )
    except ValueError as exc:  # unknown function names etc.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/tools")
async def list_tools() -> dict:
    return {"tools": _registry_public()}


@app.post("/api/tools/execute")
async def exec_tool(req: ToolRequest) -> dict:
    try:
        result = await execute_tool_async(req.tool_name, req.arguments)
    except Exception as exc:  # noqa: BLE001 - bad tool call from client
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "result": result}


@app.get("/api/providers")
async def providers() -> dict:
    return {"providers": catalog()}


@app.get("/api/memories/{agent_id}")
async def list_memories(agent_id: str, q: str = "", limit: int = 20) -> dict:
    rows = await run_in_threadpool(database.recall_memories, agent_id, q, limit)
    return {"memories": rows}


@app.post("/api/memories/{agent_id}")
async def add_memory(agent_id: str, req: MemoryRequest) -> dict:
    import json as _json

    memory_id = await run_in_threadpool(
        database.store_memory,
        agent_id,
        req.content,
        req.kind,
        _json.dumps(req.tags) if req.tags else None,
    )
    return {"success": True, "id": memory_id}


@app.delete("/api/memories/{memory_id}")
async def remove_memory(memory_id: int) -> dict:
    deleted = await run_in_threadpool(database.delete_memory, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}


@app.get("/api/history/{agent_id}")
async def history(agent_id: str, limit: int = 50) -> dict:
    rows = await run_in_threadpool(database.get_conversations, agent_id, limit)
    return {"history": rows}


@app.post("/api/jobs")
async def create_job(req: JobRequest) -> dict:
    job_id = await run_in_threadpool(database.enqueue_job, req.job_type, req.payload)
    return {"success": True, "job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: int) -> dict:
    job = await run_in_threadpool(database.get_job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/mcp/discover")
async def rediscover_mcp() -> dict:
    summary = await discover_and_register(force=True)
    return {"success": True, **summary}


@app.get("/api/capabilities")
async def capabilities() -> dict:
    usable = topic_agent.usable_functions()
    skills = [n for n, i in registry.items() if i.get("source") == "skill"]
    mcp_tools = [n for n, i in registry.items() if i.get("source") == "mcp"]
    provs = catalog()
    return {
        "usable_functions": sorted(usable),
        "tools": _registry_public(),
        "skills": sorted(skills),
        "mcp": {"servers": mcp_manager.status, "tools": sorted(mcp_tools)},
        "providers": {
            name: {"models": p["models"], "key_configured": p["key_configured"]}
            for name, p in provs.items()
        },
        "total_free_models": sum(len(p["models"]) for p in provs.values()),
        "database": database.db_backend(),
    }


@app.websocket("/ws/{agent_id}")
async def ws_endpoint(websocket: WebSocket, agent_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            topic = topic_agent.extract_topic(data)
            if topic:
                result = await topic_agent.explore_topic(agent_id, topic)
                await websocket.send_json({"agent_id": agent_id, **result})
            else:
                reply, provider = await generate(data)
                await websocket.send_json(
                    {"agent_id": agent_id, "reply": reply, "provider": provider}
                )
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
