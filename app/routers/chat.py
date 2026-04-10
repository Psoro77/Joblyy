import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.database import save_message
from app.services.llm import chat_completion, chat_completion_stream
from app.services.memory import build_context

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_BASE = (
    "You are Joblyy, an AI assistant that helps users find and apply for jobs. "
    "Be concise and helpful."
)

# region agent log
_LOG_PATH = "debug-f1df32.log"

def _dbg(msg: str, data: dict, hypothesis: str):
    entry = json.dumps({
        "sessionId": "f1df32", "timestamp": int(time.time() * 1000),
        "location": "chat.py", "message": msg, "data": data, "hypothesisId": hypothesis,
    })
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
# endregion


def _build_messages(user_message: str) -> list[dict]:
    # region agent log
    try:
        user_context = build_context(user_id=1, intent="general")
        _dbg("build_context OK", {"context_len": len(user_context) if user_context else 0}, "H-C")
    except Exception as exc:
        _dbg("build_context FAILED", {"error": str(exc)}, "H-C")
        raise
    # endregion
    system_prompt = SYSTEM_BASE
    if user_context:
        system_prompt += "\n\n" + user_context
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    await save_message("user", request.message)

    messages = _build_messages(request.message)
    result = await chat_completion(messages)
    reply = result.get("content") or "No response from the LLM."

    await save_message("assistant", reply)
    return ChatResponse(reply=reply)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    # region agent log
    _dbg("chat_stream entered", {"message_preview": request.message[:60]}, "H-B")
    # endregion
    try:
        await save_message("user", request.message)
    except Exception as exc:
        # region agent log
        _dbg("save_message(user) FAILED", {"error": str(exc)}, "H-C")
        # endregion
        raise
    messages = _build_messages(request.message)

    async def event_generator():
        # region agent log
        _dbg("event_generator started", {}, "H-C")
        # endregion
        full_reply = ""
        chunk_count = 0
        try:
            async for chunk in chat_completion_stream(messages):
                text = chunk.get("content", "")
                if text:
                    full_reply += text
                    chunk_count += 1
                    # region agent log
                    if chunk_count == 1:
                        _dbg("first chunk received from LLM", {"text_preview": text[:40]}, "H-D")
                    # endregion
                    yield f"data: {text}\n\n"
        except Exception as exc:
            # region agent log
            _dbg("event_generator stream EXCEPTION", {"error": str(exc)}, "H-C")
            # endregion
            yield f"data: [ERROR] {exc}\n\n"
        # region agent log
        _dbg("event_generator done", {"chunk_count": chunk_count, "reply_len": len(full_reply)}, "H-D")
        # endregion
        await save_message("assistant", full_reply)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
