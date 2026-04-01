"""Typed runtime settings for the Aptitude aptitude."""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="APTITUDE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_base_url: str
    read_token: str
    server_timeout_seconds: float = Field(default=5.0, gt=0)

    def __init__(self, **values: Any) -> None:
        super().__init__(**cast(dict[str, Any], values))
