from pathlib import Path
from typing import Any

from backend.app.tools.base import ToolResult


class FileReaderTool:
    name = "file_reader"
    description = "Read TXT and Markdown files from the allowed workspace file root."
    requires_approval = False
    MAX_FILE_BYTES = 1024 * 1024
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        relative_path = str(arguments.get("path", ""))
        if Path(relative_path).is_absolute():
            return ToolResult(
                ok=False,
                error="Path must be relative to the file reader root.",
            )
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents and target != self.root:
            return ToolResult(ok=False, error="Path is outside the allowed file reader root.")
        if target.suffix.lower() not in {".txt", ".md", ".markdown"}:
            return ToolResult(ok=False, error="Only TXT and Markdown files can be read.")
        if not target.exists() or not target.is_file():
            return ToolResult(ok=False, error="File does not exist.")
        try:
            size = target.stat().st_size
        except OSError:
            return ToolResult(ok=False, error="File could not be read.")
        if size > self.MAX_FILE_BYTES:
            return ToolResult(ok=False, error="File is too large to read.")
        normalized_path = target.relative_to(self.root).as_posix()
        try:
            content = target.read_text(encoding="utf-8")
        except OSError:
            return ToolResult(ok=False, error="File could not be read.")
        except UnicodeDecodeError:
            return ToolResult(ok=False, error="File could not be read.")
        return ToolResult(
            ok=True,
            output={
                "path": normalized_path,
                "content": content,
            },
        )
