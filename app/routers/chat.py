from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.database import save_message
from app.services.llm import chat_completion
from app.services.memory import build_context

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_BASE = (
    "You are Joblyy, an AI assistant that helps users find and apply for jobs. "
    "Be concise and helpful."
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    await save_message("user", request.message)

    user_context = build_context(user_id=1, intent="general")
    system_prompt = SYSTEM_BASE
    if user_context:
        system_prompt += "\n\n" + user_context

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.message},
    ]

    result = await chat_completion(messages)
    reply = result.get("content") or "No response from the LLM."

    await save_message("assistant", reply)

    return ChatResponse(reply=reply)
