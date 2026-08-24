from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")
    agent_max_steps: int = Field(default=8, ge=1, le=20, alias="AGENT_MAX_STEPS")
    file_reader_root: str = Field(default="workspace_files", alias="FILE_READER_ROOT")
    web_search_mode: str = Field(default="stub", alias="WEB_SEARCH_MODE")
    calculator_tool_mode: Literal["local", "mcp"] = Field(
        default="local",
        alias="CALCULATOR_TOOL_MODE",
    )
    database_url: str = Field(default="sqlite:///workspace_files/agent_runs.sqlite3", alias="DATABASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
