from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.database import save_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    await save_message("user", request.message)

    reply = f"Echo: {request.message} (LLM not connected yet)"

    await save_message("assistant", reply)

    return ChatResponse(reply=reply)
