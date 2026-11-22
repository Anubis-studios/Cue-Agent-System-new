"""Topic agent: orchestrates skills, tools, MCP integrations and memories.

Given a user-provided topic, the agent:
  1. recalls relevant long-term memories (DB + optional ChromaDB vectors),
  2. picks the usable skill/tool functions for the topic (all of them by
     default, or a named subset),
  3. runs each selected function against the topic (including any tools
     discovered from connected MCP servers),
  4. asks the free-LLM chain to synthesize everything into a final answer,
  5. stores the exchange and the extracted memories back in the database.
"""

import asyncio
import inspect
import json
import logging
import re
from typing import Any, Optional

from backend.db.database import (
    get_recent_memories,
    recall_memories,
    save_conversation,
    store_memory,
)
from backend.llm_chain import LLMUnavailableError, generate
from backend.tools import execute_tool_async, registry

logger = logging.getLogger(__name__)

# "explore quantum computing", "deep dive on X", "tell me about X", "topic: X"
_TOPIC_TRIGGER = re.compile(
    r"^\s*(?:explore|deep\s+dive\s+(?:on|into)?|learn\s+about|tell\s+me\s+about|topic)\s*[:\-]?\s+(?P<topic>.{2,})",
    re.IGNORECASE,
)

MAX_MCP_TOOLS_PER_RUN = 6


def is_explicit_topic_request(message: str) -> bool:
    return bool(_TOPIC_TRIGGER.match(message))


def extract_topic(message: str) -> Optional[str]:
    match = _TOPIC_TRIGGER.match(message)
    return match.group("topic").strip() if match else None


def usable_functions(names: Optional[list[str]] = None) -> dict[str, dict]:
    """All registered functions usable with a single ``topic`` argument."""
    candidates = {
        name: info
        for name, info in registry.items()
        if "topic" in inspect.signature(info["fn"]).parameters
    }
    if names:
        wanted = set(names)
        candidates = {n: i for n, i in candidates.items() if n in wanted}
    return candidates


async def _run_function(name: str, topic: str) -> Optional[str]:
    try:
        result = await execute_tool_async(name, {"topic": topic})
        return str(result)
    except Exception as exc:  # noqa: BLE001 - one failing skill shouldn't abort
        logger.warning("Function %s failed for topic %r: %s", name, topic, exc)
        return None


def _memories_block(agent_id: str, topic: str) -> tuple[str, list[dict]]:
    rows = recall_memories(agent_id, topic, limit=5)
    if not rows:
        rows = get_recent_memories(agent_id, limit=5)
    if not rows:
        return "", []
    lines = [f"- [{r['kind']}] {r['content']}" for r in rows]
    return "Relevant memories:\n" + "\n".join(lines), rows


def _store_topic_memory(agent_id: str, topic: str, reply: str, provider: str) -> None:
    summary = reply.strip().replace("\n", " ")[:280]
    store_memory(
        agent_id=agent_id,
        kind="conversation",
        content=f"Topic '{topic}' via {provider}: {summary}",
        tags=json.dumps([topic.lower()]),
    )


async def explore_topic(
    agent_id: str,
    topic: str,
    function_names: Optional[list[str]] = None,
    use_mcp: bool = True,
) -> dict[str, Any]:
    """Run the full agent pipeline for a topic and return structured results."""
    functions = usable_functions(function_names)
    mcp_tools = {
        n: i for n, i in registry.items() if i.get("source") == "mcp"
    } if use_mcp else {}
    mcp_tools = dict(list(mcp_tools.items())[:MAX_MCP_TOOLS_PER_RUN])

    memories_text, memory_rows = _memories_block(agent_id, topic)

    skill_results: dict[str, str] = {}
    tasks = [_run_function(n, topic) for n in functions]
    for name, outcome in zip(functions, await asyncio.gather(*tasks)):
        if outcome is not None:
            skill_results[name] = outcome

    mcp_results: dict[str, str] = {}
    if mcp_tools:
        tasks = [_run_function(n, topic) for n in mcp_tools]
        for name, outcome in zip(mcp_tools, await asyncio.gather(*tasks)):
            if outcome is not None:
                mcp_results[name] = outcome

    context_parts = [f"User topic: {topic}"]
    if memories_text:
        context_parts.append(memories_text)
    if skill_results:
        context_parts.append(
            "Agent skill outputs:\n"
            + "\n\n".join(f"[{k}]\n{v}" for k, v in skill_results.items())
        )
    if mcp_results:
        context_parts.append(
            "MCP tool outputs:\n"
            + "\n\n".join(f"[{k}]\n{v}" for k, v in mcp_results.items())
        )
    context_parts.append(
        f"Write a comprehensive, well-structured exploration of the topic "
        f"'{topic}', using the material above where helpful."
    )
    prompt = "\n\n".join(context_parts)

    reply, provider = await generate(prompt)
    _store_topic_memory(agent_id, topic, reply, provider)
    try:
        save_conversation(agent_id, f"explore: {topic}", reply, provider)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB save failed: %s", exc)

    return {
        "topic": topic,
        "reply": reply,
        "provider": provider,
        "skills_used": sorted(skill_results),
        "mcp_tools_used": sorted(mcp_results),
        "memories_recalled": len(memory_rows),
    }
