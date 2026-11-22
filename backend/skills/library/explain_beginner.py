"""ELI5 skill: explain a topic simply."""

from backend.tools import register_tool


@register_tool(
    "explain_like_im_five",
    "Explain a topic in very simple terms (ELI5 skill).",
    {"topic": "string"},
    source="skill",
)
def explain_like_im_five(topic: str) -> str:
    return (
        f"Imagine '{topic}' is like a box of toys: every part has a job, "
        f"and together they make something fun work. Start with the biggest "
        f"pieces first, then add the small ones. Keep it simple: what is it, "
        f"what does it do, why should I care about {topic}?"
    )
