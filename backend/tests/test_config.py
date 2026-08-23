from backend.app.config import Settings


def test_settings_accept_deepseek_values() -> None:
    settings = Settings(
        _env_file=None,
        deepseek_api_key="key",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-v4-flash",
        agent_max_steps=8,
        file_reader_root="workspace_files",
        web_search_mode="stub",
        database_url="sqlite:///workspace_files/agent_runs.sqlite3",
    )

    assert settings.deepseek_api_key == "key"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.agent_max_steps == 8
    assert settings.file_reader_root == "workspace_files"
    assert settings.web_search_mode == "stub"
    assert settings.database_url == "sqlite:///workspace_files/agent_runs.sqlite3"
