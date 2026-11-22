import os, logging, re
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from backend.llm_chain import generate
from backend.tools import registry, execute_tool
from backend.db.database import init_db, save_conversation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(os.getenv("DATABASE_PATH", "cue.db"))
    yield

app = FastAPI(title="Cue Agent System", version="1.1.0", lifespan=lifespan)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str
    agent_id: str = "default"
    use_tools: bool = True

class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict

@app.get("/health")
async def health(): return {"status": "ok", "version": "1.1.0"}

@app.post("/api/chat/{agent_id}")
async def chat(agent_id: str, req: ChatRequest):
    try:
        if req.use_tools:
            tool_result = await execute_tool_if_needed(req.message)
            prompt = f"{req.message}\n\nTool result: {tool_result}" if tool_result else req.message
        else:
            prompt = req.message
        
        reply, provider = await generate(prompt)
        try: save_conversation(agent_id, req.message, reply, provider)
        except Exception as e: logger.warning(f"DB save failed: {e}")
        
        return {"agent_id": agent_id, "reply": reply, "provider": provider, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def list_tools():
    return {"tools": {n: {"description": i["description"], "parameters": i["parameters"]} for n, i in registry.items()}}

@app.post("/api/tools/execute")
async def exec_tool(req: ToolRequest):
    try: return {"success": True, "result": execute_tool(req.tool_name, req.arguments)}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/{agent_id}")
async def ws_endpoint(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            reply, provider = await generate(data)
            await websocket.send_json({"agent_id": agent_id, "reply": reply, "provider": provider})
    except: pass
    finally: await websocket.close()

async def execute_tool_if_needed(message: str) -> str | None:
    match = re.search(r'(?:calculate|compute|eval)\s*(.+)', message, re.IGNORECASE)
    if match:
        try: return f"The result is {execute_tool('calculate', {'expr': match.group(1).strip()})}"
        except: pass
    return None
