from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from backend.app.api.tools import build_registry
from backend.app.config import get_settings
from backend.app.llm.deepseek import DeepSeekProvider
from backend.app.schemas.agent import AgentRunResponse, CreateRunRequest, RunListResponse
from backend.app.services.run_service import PUBLIC_RUN_FAILURE_ERROR, RunService
from backend.app.services.run_store import InMemoryRunStore

router = APIRouter(prefix="/api/agent", tags=["agent"])
RUN_STORE = InMemoryRunStore()


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
    service = RunService(
        store=RUN_STORE,
        provider=provider,
        registry=build_registry(),
        max_steps=request.max_steps or settings.agent_max_steps,
        public_failure_error=PUBLIC_RUN_FAILURE_ERROR,
    )
    try:
        run = service.create_run(request.task)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=PUBLIC_RUN_FAILURE_ERROR) from exc
    return AgentRunResponse.model_validate(run)


@router.get("/runs", response_model=RunListResponse)
def list_runs() -> RunListResponse:
    return RunListResponse(items=RUN_STORE.list_runs())


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_run(run_id: str) -> AgentRunResponse:
    run = RUN_STORE.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    run["steps"] = [event.as_dict() for event in RUN_STORE.list_events(run_id)]
    return AgentRunResponse.model_validate(run)


@router.get("/runs/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
    if RUN_STORE.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return StreamingResponse(
        (event.to_sse() for event in RUN_STORE.list_events(run_id)),
        media_type="text/event-stream",
    )
