"""Mind-map skill: expand a topic into branches."""

from backend.tools import register_tool


@register_tool(
    "mind_map",
    "Break a topic into a branching outline (mind-map skill).",
    {"topic": "string"},
    source="skill",
)
def mind_map(topic: str) -> str:
    branches = ["Foundations", "Tools & Techniques", "Real-world Applications",
                "History & Context", "Future Trends", "Open Questions"]
    lines = [f"{topic}"]
    lines += [f"├── {b}" for b in branches[:-1]]
    lines.append(f"└── {branches[-1]}")
    return "\n".join(lines)
