import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Ollama can be slow to produce the first token, especially with tool schemas
# and long inputs. Use a short connect timeout (fail fast if Ollama is down)
# and a generous read timeout for the actual model response.
_OLLAMA_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=5.0)


# ── Normalisation helpers ──

def _normalize_ollama_response(data: dict) -> dict:
    """Convert Ollama /api/chat response into our standard format."""
    message = data.get("message", {})
    content = message.get("content", "")
    raw_tool_calls = message.get("tool_calls")
    tool_calls = _normalize_tool_call_list(raw_tool_calls) if raw_tool_calls else None
    return {"content": content, "tool_calls": tool_calls}


def _normalize_litellm_response(response) -> dict:
    """Convert a LiteLLM ModelResponse into our standard format."""
    choice = response.choices[0]
    content = choice.message.content or ""
    raw_tool_calls = choice.message.tool_calls
    tool_calls = None
    if raw_tool_calls:
        tool_calls = [
            {
                "name": tc.function.name,
                "arguments": (
                    json.loads(tc.function.arguments)
                    if isinstance(tc.function.arguments, str)
                    else tc.function.arguments
                ),
            }
            for tc in raw_tool_calls
        ]
    return {"content": content, "tool_calls": tool_calls}


def _normalize_tool_call_list(raw: list[dict]) -> list[dict]:
    """Normalise a list of Ollama-style tool call dicts."""
    results = []
    for tc in raw:
        func = tc.get("function", {})
        args = func.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        results.append({"name": func.get("name", ""), "arguments": args})
    return results


# ── Public API ──

def parse_tool_calls(response: dict) -> list[dict]:
    """Extract tool calls from our normalised response dict.

    Returns a list of ``{"name": str, "arguments": dict}`` or an empty list.
    """
    return response.get("tool_calls") or []


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    """Send messages to the configured LLM and return a normalised response.

    Returns ``{"content": str, "tool_calls": list[dict] | None}``.
    On connection/provider errors the content field carries the error message.
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        return await _ollama_chat(messages, tools)
    return await _cloud_chat(messages, tools)


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Yield chunks from the configured LLM.

    Text chunks: ``{"content": str}``.
    After the stream ends, if tool calls were present, a final chunk
    ``{"tool_calls": list[dict]}`` is yielded.
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        async for chunk in _ollama_stream(messages, tools):
            yield chunk
    else:
        async for chunk in _cloud_stream(messages, tools):
            yield chunk


# ── Ollama backend ──

async def _ollama_chat(
    messages: list[dict],
    tools: list[dict] | None,
) -> dict:
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/chat"
    body: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return _normalize_ollama_response(resp.json())
    except httpx.ConnectError:
        msg = f"Cannot connect to Ollama at {settings.ollama_base_url}. Is it running?"
        logger.error(msg)
        return {"content": f"Error: {msg}", "tool_calls": None}
    except httpx.HTTPStatusError as exc:
        msg = f"Ollama returned {exc.response.status_code}: {exc.response.text}"
        logger.error(msg)
        return {"content": f"Error: {msg}", "tool_calls": None}
    except Exception as exc:
        logger.exception("Ollama chat failed")
        return {"content": f"LLM error: {exc}", "tool_calls": None}


async def _ollama_stream(
    messages: list[dict],
    tools: list[dict] | None,
) -> AsyncGenerator[dict, None]:
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/chat"
    body: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        body["tools"] = tools

    buffered_tool_calls: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    message = data.get("message", {})

                    content = message.get("content", "")
                    if content:
                        yield {"content": content}

                    raw_tc = message.get("tool_calls")
                    if raw_tc:
                        buffered_tool_calls.extend(_normalize_tool_call_list(raw_tc))

        if buffered_tool_calls:
            yield {"tool_calls": buffered_tool_calls}

    except httpx.ConnectError:
        yield {"content": f"Error: Cannot connect to Ollama at {settings.ollama_base_url}. Is it running?"}
    except Exception as exc:
        logger.exception("Ollama stream failed")
        yield {"content": f"LLM error: {exc}"}


# ── Cloud (LiteLLM) backend ──

async def _cloud_chat(
    messages: list[dict],
    tools: list[dict] | None,
) -> dict:
    settings = get_settings()

    if not settings.cloud_api_key:
        return {
            "content": "Error: No cloud API key configured. Set one via POST /settings or in .env.",
            "tool_calls": None,
        }

    try:
        import litellm  # noqa: local import — only llm.py touches this

        kwargs: dict = {
            "model": settings.cloud_model,
            "messages": messages,
            "api_key": settings.cloud_api_key,
        }
        if tools:
            kwargs["tools"] = tools

        response = await litellm.acompletion(**kwargs)
        return _normalize_litellm_response(response)

    except Exception as exc:
        logger.exception("Cloud LLM chat failed")
        return {"content": f"LLM error: {exc}", "tool_calls": None}


async def _cloud_stream(
    messages: list[dict],
    tools: list[dict] | None,
) -> AsyncGenerator[dict, None]:
    settings = get_settings()

    if not settings.cloud_api_key:
        yield {"content": "Error: No cloud API key configured. Set one via POST /settings or in .env."}
        return

    try:
        import litellm

        kwargs: dict = {
            "model": settings.cloud_model,
            "messages": messages,
            "api_key": settings.cloud_api_key,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        response = await litellm.acompletion(**kwargs)

        buffered_tool_calls: list[dict] = []

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"content": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function and tc.function.name:
                        args = tc.function.arguments or "{}"
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                pass
                        buffered_tool_calls.append({
                            "name": tc.function.name,
                            "arguments": args,
                        })

        if buffered_tool_calls:
            yield {"tool_calls": buffered_tool_calls}

    except Exception as exc:
        logger.exception("Cloud LLM stream failed")
        yield {"content": f"LLM error: {exc}"}
