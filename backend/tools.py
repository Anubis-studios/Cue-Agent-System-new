from typing import Callable, Any
import ast
import operator

registry: dict[str, dict] = {}

def register_tool(name: str, description: str = "", parameters: dict | None = None):
    def deco(fn: Callable):
        registry[name] = {"fn": fn, "description": description, "parameters": parameters or {}}
        return fn
    return deco

def execute_tool(tool_name: str, arguments: dict) -> Any:
    if tool_name not in registry:
        raise ValueError(f"Unknown tool: {tool_name}")
    return registry[tool_name]["fn"](**arguments)

def safe_eval_expression(expr: str) -> float:
    allowed_ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, 
                   ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}
    allowed_funcs = {'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum}
    
    def _eval(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.BinOp):
            l, r = _eval(node.left), _eval(node.right)
            op = type(node.op)
            if op in allowed_ops: return allowed_ops[op](l, r)
            raise ValueError(f"Unsupported operator: {op}")
        if isinstance(node, ast.UnaryOp):
            o = _eval(node.operand)
            op = type(node.op)
            if op in allowed_ops: return allowed_ops[op](o)
            raise ValueError(f"Unsupported unary op: {op}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fname = node.func.id
            if fname in allowed_funcs: return allowed_funcs[fname](*[_eval(a) for a in node.args])
            raise ValueError(f"Function not allowed: {fname}")
        raise ValueError(f"Unsupported expression: {type(node)}")
    
    try:
        tree = ast.parse(expr, mode='eval')
        res = _eval(tree.body)
        return float(res) if isinstance(res, (int, float)) else float('nan')
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")

@register_tool("calculate", "Evaluate math safely", {"expr": "string"})
def calculate(expr: str) -> float:
    return safe_eval_expression(expr)

@register_tool("weather", "Get weather (stub)", {"location": "string"})
def get_weather(location: str) -> str:
    return f"Weather data for {location} would be fetched here"
