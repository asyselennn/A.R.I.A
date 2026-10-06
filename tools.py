import platform
from datetime import datetime
from typing import Any, Callable

from memory import add_or_update_memory, delete_memory, search_memory
from security import safe_calculate

ToolFunc = Callable[[dict[str, Any]], Any]


def calculator(args: dict[str, Any]) -> dict[str, Any]:
    result = safe_calculate(str(args["expression"]))
    return {"expression": args["expression"], "result": result}


def datetime_tool(args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().astimezone()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timezone": str(now.tzinfo),
    }


def memory_search(args: dict[str, Any]) -> dict[str, Any]:
    return {"results": search_memory(str(args.get("query", "")))}


def memory_save(args: dict[str, Any]) -> dict[str, Any]:
    item = add_or_update_memory(
        str(args["key"]), str(args["value"]), str(args.get("category", "general"))
    )
    return {"saved": item}


def memory_forget(args: dict[str, Any]) -> dict[str, Any]:
    return {"removed": delete_memory(str(args["query"]))}


def system_info(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


REGISTRY: dict[str, ToolFunc] = {
    "calculator": calculator,
    "get_datetime": datetime_tool,
    "memory_search": memory_search,
    "memory_save": memory_save,
    "memory_forget": memory_forget,
    "system_info": system_info,
}

SCHEMAS = [
    {
        "type": "function", "name": "calculator",
        "description": "Safely calculate a basic arithmetic expression.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "get_datetime",
        "description": "Get the computer's current local date and time.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "memory_search",
        "description": "Search ARIA's persistent memory.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "memory_save",
        "description": "Save a non-sensitive long-term user fact or preference.",
        "parameters": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}, "category": {"type": "string"}}, "required": ["key", "value", "category"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "memory_forget",
        "description": "Forget matching persistent memories.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "system_info",
        "description": "Get basic non-sensitive information about the local computer and Python runtime.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


def execute(name: str, args: dict[str, Any]) -> Any:
    if name not in REGISTRY:
        raise ValueError(f"Unknown tool: {name}")
    return REGISTRY[name](args)
