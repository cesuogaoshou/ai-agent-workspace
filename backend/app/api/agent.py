from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from backend.app.agent.loop import AgentLoop
from backend.app.api.tools import build_registry
from backend.app.config import get_settings
from backend.app.llm.deepseek import DeepSeekProvider
from backend.app.schemas.agent import AgentRunResponse, CreateRunRequest

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/runs", response_model=AgentRunResponse)
def create_run(request: CreateRunRequest) -> AgentRunResponse:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY is not configured.")

    provider = DeepSeekProvider(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    loop = AgentLoop(provider, build_registry(), max_steps=request.max_steps or settings.agent_max_steps)
    return AgentRunResponse.model_validate(asdict(loop.run(request.task)))
