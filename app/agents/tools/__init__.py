from typing import Dict, List, Callable, Optional

from app.agents.tools.job_tools import JOB_TOOLS
from app.agents.tools.memory_tools import MEMORY_TOOLS

TOOLS: Dict[str, dict] = {**MEMORY_TOOLS, **JOB_TOOLS}


def get_tool_schemas() -> List[dict]:
    return [entry["schema"] for entry in TOOLS.values()]


def get_tool_fn(name: str) -> Optional[Callable]:
    entry = TOOLS.get(name)
    if entry is None:
        return None
    return entry["fn"]
