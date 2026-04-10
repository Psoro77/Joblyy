from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.models.schemas import MarkdownContent
from app.services.memory import read_markdown, write_markdown

router = APIRouter(prefix="/profile", tags=["profile"])

USER_ID = 1


@router.get("", response_class=PlainTextResponse)
async def get_profile():
    return read_markdown(USER_ID, "profile.md")


@router.post("", response_class=PlainTextResponse)
async def update_profile(body: MarkdownContent):
    write_markdown(USER_ID, "profile.md", body.content)
    return read_markdown(USER_ID, "profile.md")


@router.get("/preferences", response_class=PlainTextResponse)
async def get_preferences():
    return read_markdown(USER_ID, "preferences.md")


@router.post("/preferences", response_class=PlainTextResponse)
async def update_preferences(body: MarkdownContent):
    write_markdown(USER_ID, "preferences.md", body.content)
    return read_markdown(USER_ID, "preferences.md")
