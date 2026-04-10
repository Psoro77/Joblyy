from fastapi import APIRouter

from app.config import get_settings, update_settings
from app.models.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def read_settings() -> SettingsResponse:
    s = get_settings()
    model = s.ollama_model if s.llm_provider == "ollama" else s.cloud_model
    return SettingsResponse(
        provider=s.llm_provider,
        model=model,
        ollama_base_url=s.ollama_base_url,
    )


@router.post("", response_model=SettingsResponse)
async def save_settings(body: SettingsUpdate) -> SettingsResponse:
    mapping: dict[str, str | None] = {}

    if body.provider is not None:
        mapping["llm_provider"] = body.provider
    if body.ollama_base_url is not None:
        mapping["ollama_base_url"] = body.ollama_base_url
    if body.api_key is not None:
        mapping["cloud_api_key"] = body.api_key

    provider = body.provider or get_settings().llm_provider
    if body.model is not None:
        if provider == "ollama":
            mapping["ollama_model"] = body.model
        else:
            mapping["cloud_model"] = body.model

    s = update_settings(**mapping)

    active_model = s.ollama_model if s.llm_provider == "ollama" else s.cloud_model
    return SettingsResponse(
        provider=s.llm_provider,
        model=active_model,
        ollama_base_url=s.ollama_base_url,
    )
