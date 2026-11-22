"""Quiz skill: generate practice questions about a topic."""

from backend.tools import register_tool


@register_tool(
    "generate_quiz",
    "Create a short quiz about a topic (assessment skill).",
    {"topic": "string"},
    source="skill",
)
def generate_quiz(topic: str) -> str:
    return (
        f"Quiz on '{topic}':\n"
        f"Q1. What is {topic}, in one sentence?\n"
        f"Q2. Name two real-world applications of {topic}.\n"
        f"Q3. What is a common misconception about {topic}?\n"
        f"Q4. How would you explain {topic} to a beginner?\n"
        f"Q5. What future development excites you most about {topic}?"
    )
