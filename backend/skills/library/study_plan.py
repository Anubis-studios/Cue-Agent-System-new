"""Study-plan skill: 4-week roadmap for learning a topic."""

from backend.tools import register_tool


@register_tool(
    "study_plan",
    "Build a 4-week study roadmap for a topic (planning skill).",
    {"topic": "string"},
    source="skill",
)
def study_plan(topic: str) -> str:
    return (
        f"4-week study plan for '{topic}':\n"
        f"Week 1 — Basics: overview, vocabulary, 1 intro video/article daily.\n"
        f"Week 2 — Core concepts: worked examples, flashcards, mini-exercises.\n"
        f"Week 3 — Practice: build a small project or solve problem sets.\n"
        f"Week 4 — Deepen & review: advanced topics, teach-back, gap analysis."
    )
