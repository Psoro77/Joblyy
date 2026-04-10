import json
import logging
from collections.abc import AsyncGenerator

from app.agents.tools import get_tool_fn, get_tool_schemas
from app.services.database import get_conversation_history
from app.services.llm import chat_completion_stream
from app.services.memory import build_context

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
HISTORY_LIMIT = 20

SYSTEM_TEMPLATE = """\
You are a job search assistant. You help the user manage their professional profile, find relevant jobs, and apply to them.

You have access to tools to manage the user's data and automate browser tasks. Use them when needed, don't ask for permission unless the action is irreversible (like submitting an application).

When the user shares their CV or experience as raw text, use parse_and_save_profile to structure and save it.
When the user describes what kind of jobs they want, use update_preferences.
When the user asks to search for jobs, use delegate_to_browser.
When the user asks about their applications, use get_application_status.

Always be concise. Summarize tool results for the user, don't dump raw data.

Current user context:
{context}
"""


_PROFILE_KEYWORDS = ("cv", "resume", "experience", "skills", "education")
_PREFERENCES_KEYWORDS = ("prefer", "looking for", "want", "salary", "location", "remote")
_JOB_SEARCH_KEYWORDS = ("search", "find", "look for job", "look for a job", "look for jobs")
_APPLY_KEYWORDS = ("apply", "submit", "candidate")
_STATUS_KEYWORDS = ("status", "applied", "application", "where")


def detect_intent(message: str) -> str:
    """Classify the user's message into one of the build_context intents."""
    lowered = message.lower()

    if any(k in lowered for k in _PROFILE_KEYWORDS):
        return "profile_edit"
    if any(k in lowered for k in _PREFERENCES_KEYWORDS):
        return "preferences_edit"
    if any(k in lowered for k in _JOB_SEARCH_KEYWORDS):
        return "job_search"
    if any(k in lowered for k in _APPLY_KEYWORDS):
        return "apply"
    if any(k in lowered for k in _STATUS_KEYWORDS):
        return "status_check"
    return "general"


def _append_tool_exchange(
    messages: list[dict],
    tool_calls: list[dict],
    results: list[str],
) -> None:
    """Append the assistant tool-call turn + tool results in Ollama-native format."""
    assistant_tool_calls = [
        {"function": {"name": tc["name"], "arguments": tc.get("arguments", {})}}
        for tc in tool_calls
    ]
    messages.append({
        "role": "assistant",
        "content": "",
        "tool_calls": assistant_tool_calls,
    })
    for tc, result in zip(tool_calls, results):
        messages.append({
            "role": "tool",
            "name": tc["name"],
            "content": result,
        })


def _coerce_arguments(args) -> dict:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {}
    return {}


class ConversationalAgent:
    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    async def _load_history(self, current_message: str) -> list[dict]:
        rows = await get_conversation_history(limit=HISTORY_LIMIT)
        history = [{"role": r["role"], "content": r["content"]} for r in rows]
        if history and history[-1]["role"] == "user" and history[-1]["content"] == current_message:
            history.pop()
        return history

    async def _execute_tool(self, name: str, arguments) -> str:
        fn = get_tool_fn(name)
        if fn is None:
            return f"Error: unknown tool '{name}'."
        kwargs = _coerce_arguments(arguments)
        try:
            result = await fn(**kwargs)
            if not isinstance(result, str):
                result = str(result)
            return result
        except TypeError as exc:
            return f"Error calling {name}: {exc}"
        except Exception as exc:
            logger.exception("Tool %s raised", name)
            return f"Error in {name}: {exc}"

    async def run(self, user_message: str) -> AsyncGenerator[str, None]:
        intent = detect_intent(user_message)
        context = build_context(self.user_id, intent)
        system_prompt = SYSTEM_TEMPLATE.format(context=context or "(none)")

        history = await self._load_history(user_message)
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        tool_schemas = get_tool_schemas()

        for iteration in range(MAX_ITERATIONS):
            tool_calls_buffer: list[dict] = []
            iter_text = ""

            async for chunk in chat_completion_stream(messages, tools=tool_schemas):
                text = chunk.get("content")
                if text:
                    iter_text += text
                    yield text
                tc = chunk.get("tool_calls")
                if tc:
                    tool_calls_buffer.extend(tc)

            if not tool_calls_buffer:
                return

            results: list[str] = []
            for call in tool_calls_buffer:
                name = call.get("name", "")
                args = call.get("arguments", {})
                result = await self._execute_tool(name, args)
                results.append(result)

            _append_tool_exchange(messages, tool_calls_buffer, results)
            yield "\n"

        yield "\n[Reached max tool iterations.]"
