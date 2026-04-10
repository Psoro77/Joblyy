from collections.abc import Callable

from app.agents.tools.job_tools import JOB_TOOLS
from app.agents.tools.memory_tools import MEMORY_TOOLS

TOOLS: dict[str, dict] = {**MEMORY_TOOLS, **JOB_TOOLS}


def get_tool_schemas() -> list[dict]:
    return [entry["schema"] for entry in TOOLS.values()]


def get_tool_fn(name: str) -> Callable | None:
    entry = TOOLS.get(name)
    if entry is None:
        return None
    return entry["fn"]
