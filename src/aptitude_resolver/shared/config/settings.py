"""Typed runtime settings for the Aptitude aptitude."""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


_ENVIRONMENT_VARIABLES_BY_FIELD = {
    "server_base_url": "APTITUDE_SERVER_BASE_URL",
    "read_token": "APTITUDE_READ_TOKEN",
    "server_timeout_seconds": "APTITUDE_SERVER_TIMEOUT_SECONDS",
}


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


def describe_settings_validation_error(error: ValidationError) -> str:
    """Return one user-facing description for settings validation failures."""

    missing_variables: list[str] = []
    invalid_variables: list[str] = []

    for item in error.errors(include_url=False):
        location = item.get("loc", ())
        field_name = location[0] if location else None
        environment_variable = _ENVIRONMENT_VARIABLES_BY_FIELD.get(
            field_name if isinstance(field_name, str) else ""
        )
        if environment_variable is None:
            continue

        if item.get("type") == "missing":
            missing_variables.append(environment_variable)
            continue

        invalid_variables.append(
            f"{environment_variable} ({item.get('msg', 'invalid value')})"
        )

    messages: list[str] = []
    if missing_variables:
        messages.append(
            "Missing required environment variables: "
            + ", ".join(_deduplicate_preserving_order(missing_variables))
            + "."
        )
    if invalid_variables:
        messages.append(
            "Invalid environment settings: "
            + ", ".join(_deduplicate_preserving_order(invalid_variables))
            + "."
        )
    if messages:
        return " ".join(messages)
    return "Invalid Aptitude environment configuration."


def _deduplicate_preserving_order(values: list[str]) -> list[str]:
    """Return values in first-seen order without duplicates."""

    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduplicated.append(value)
    return deduplicated
