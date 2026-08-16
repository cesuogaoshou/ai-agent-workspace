from fastapi import APIRouter

from backend.app.config import get_settings
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.file_reader import FileReaderTool
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.web_search import StubWebSearchTool

router = APIRouter(prefix="/api/tools", tags=["tools"])


def build_registry() -> ToolRegistry:
    settings = get_settings()
    return ToolRegistry(
        [
            CalculatorTool(),
            FileReaderTool(settings.file_reader_root),
            StubWebSearchTool(),
        ]
    )


@router.get("")
def list_tools() -> dict[str, list[dict[str, object]]]:
    registry = build_registry()
    return {"items": registry.metadata()}
