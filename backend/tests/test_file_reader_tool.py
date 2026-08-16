from pathlib import Path

import pytest

from backend.app.tools.file_reader import FileReaderTool


def test_reads_markdown_inside_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    (root / "sample.md").write_text("# Sample\n\nHello", encoding="utf-8")

    result = FileReaderTool(root).execute({"path": "sample.md"})

    assert result.ok is True
    assert result.output == {"path": "sample.md", "content": "# Sample\n\nHello"}


def test_rejects_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    result = FileReaderTool(root).execute({"path": "../secret.md"})

    assert result.ok is False
    assert result.error == "Path is outside the allowed file reader root."


def test_rejects_file_exceeding_max_size(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    (root / "large.md").write_text(
        "a" * (1024 * 1024 + 1),
        encoding="utf-8",
    )

    result = FileReaderTool(root).execute({"path": "large.md"})

    assert result.ok is False
    assert result.error == "File is too large to read."


def test_invalid_utf8_markdown_returns_read_error(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    (root / "invalid.md").write_bytes(b"\xff\xfe\xfa")

    result = FileReaderTool(root).execute({"path": "invalid.md"})

    assert result.ok is False
    assert result.error == "File could not be read."


def test_rejects_unsupported_extension(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    (root / "sample.py").write_text("print('hello')", encoding="utf-8")

    result = FileReaderTool(root).execute({"path": "sample.py"})

    assert result.ok is False
    assert result.error == "Only TXT and Markdown files can be read."


def test_missing_markdown_file_returns_not_found(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()

    result = FileReaderTool(root).execute({"path": "missing.md"})

    assert result.ok is False
    assert result.error == "File does not exist."


def test_rejects_absolute_path_input(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    file_path = root / "sample.md"
    file_path.write_text("# Sample", encoding="utf-8")

    result = FileReaderTool(root).execute({"path": str(file_path)})

    assert result.ok is False
    assert result.error == "Path must be relative to the file reader root."


def test_returns_normalized_root_relative_path_for_alias(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    (root / "subdir").mkdir()
    (root / "sample.md").write_text("# Sample", encoding="utf-8")

    result = FileReaderTool(root).execute({"path": "subdir/../sample.md"})

    assert result.ok is True
    assert result.output == {"path": "sample.md", "content": "# Sample"}


def test_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace_files"
    root.mkdir()
    secret = tmp_path / "secret.md"
    secret.write_text("secret", encoding="utf-8")
    link = root / "link.md"
    try:
        link.symlink_to(secret)
    except OSError as exc:
        pytest.skip(f"Symlink creation is unavailable: {exc}")

    result = FileReaderTool(root).execute({"path": "link.md"})

    assert result.ok is False
    assert result.error == "Path is outside the allowed file reader root."
