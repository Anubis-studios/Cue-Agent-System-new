"""Tool registry with a safe AST-based calculator."""

import ast
import operator
from typing import Any, Callable, Optional

registry: dict[str, dict] = {}


def register_tool(
    name: str, description: str = "", parameters: Optional[dict] = None
) -> Callable:
    """Decorator that registers a function as an executable tool."""

    def decorator(fn: Callable) -> Callable:
        registry[name] = {
            "fn": fn,
            "description": description,
            "parameters": parameters or {},
        }
        return fn

    return decorator


def execute_tool(tool_name: str, arguments: dict) -> Any:
    if tool_name not in registry:
        raise ValueError(f"Unknown tool: {tool_name}")
    return registry[tool_name]["fn"](**arguments)


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        return _ALLOWED_OPERATORS[op_type](
            _eval_node(node.left), _eval_node(node.right)
        )

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _ALLOWED_OPERATORS[op_type](_eval_node(node.operand))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name not in _ALLOWED_FUNCTIONS:
            raise ValueError(f"Function not allowed: {name}")
        return _ALLOWED_FUNCTIONS[name](*[_eval_node(a) for a in node.args])

    raise ValueError(f"Unsupported expression: {type(node).__name__}")


def safe_eval_expression(expr: str) -> float:
    """Evaluate an arithmetic expression safely (no eval, AST whitelist)."""
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval_node(tree.body)
    except Exception as exc:
        raise ValueError(f"Invalid expression: {exc}") from exc

    if isinstance(result, (int, float)):
        return float(result)
    return float("nan")


@register_tool("calculate", "Evaluate math safely", {"expr": "string"})
def calculate(expr: str) -> float:
    return safe_eval_expression(expr)


@register_tool("weather", "Get weather (stub)", {"location": "string"})
def get_weather(location: str) -> str:
    return f"Weather data for {location} would be fetched here"
