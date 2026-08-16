from fastapi import APIRouter

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def list_tools() -> dict[str, list[dict[str, str]]]:
    return {"items": []}
