"""Summarization skill: condense a topic or text into key points."""

from backend.tools import register_tool


@register_tool(
    "summarize",
    "Produce a structured summary of a topic (agent prompt skill).",
    {"topic": "string"},
    source="skill",
)
def summarize(topic: str) -> str:
    return (
        f"Summary plan for '{topic}':\n"
        f"1. Define {topic} and why it matters.\n"
        f"2. Cover core concepts and terminology.\n"
        f"3. Give practical examples and use cases.\n"
        f"4. List common pitfalls and best practices.\n"
        f"5. Suggest next steps to go deeper."
    )
