from fastapi import APIRouter

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/runs")
def create_run() -> dict[str, str]:
    return {"status": "not_implemented"}
