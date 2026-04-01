from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NoReturn

import httpx
import pytest

from aptitude.shared.config import Settings


@dataclass(frozen=True)
class IntegrationConfig:
    """Runtime configuration for live server integration tests."""

    base_url: str
    read_token: str
    publish_token: str | None
    timeout_seconds: float


def _env_value(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _load_integration_config() -> IntegrationConfig:
    timeout_raw = _env_value(
        "APTITUDE_INTEGRATION_TIMEOUT_SECONDS",
        "APTITUDE_SERVER_TIMEOUT_SECONDS",
        default="5.0",
    )
    try:
        timeout_seconds = float(timeout_raw or "5.0")
    except ValueError as exc:
        pytest.skip(
            "Integration timeout configuration is invalid. "
            "Set APTITUDE_INTEGRATION_TIMEOUT_SECONDS or "
            "APTITUDE_SERVER_TIMEOUT_SECONDS to a numeric value."
        )
        raise AssertionError("unreachable") from exc

    return IntegrationConfig(
        base_url=_env_value(
            "APTITUDE_INTEGRATION_BASE_URL",
            "APTITUDE_SERVER_BASE_URL",
            default="http://localhost:8000",
        )
        or "http://localhost:8000",
        read_token=_env_value(
            "APTITUDE_INTEGRATION_READ_TOKEN",
            "APTITUDE_READ_TOKEN",
            default="reader-token",
        )
        or "reader-token",
        publish_token=_env_value(
            "APTITUDE_INTEGRATION_PUBLISH_TOKEN",
            "APTITUDE_PUBLISH_TOKEN",
        ),
        timeout_seconds=timeout_seconds,
    )


def _ensure_registry_ready(config: IntegrationConfig) -> None:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.read_token}",
    }
    payload = {
        "name": "aptitude integration readiness probe",
        "description": "Probe the live discovery endpoint before running integration tests.",
        "tags": ["integration", "readiness"],
    }

    try:
        with httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        ) as client:
            response = client.post("/discovery", headers=headers, json=payload)
    except httpx.HTTPError as exc:
        pytest.skip(
            f"Live integration server is not reachable at {config.base_url}: {exc}"
        )

    if response.status_code in {401, 403}:
        pytest.skip(
            "Live integration server rejected the read token. "
            "Set APTITUDE_INTEGRATION_READ_TOKEN or APTITUDE_READ_TOKEN."
        )

    if response.status_code >= 500:
        pytest.skip(
            f"Live integration server is not ready yet: discovery returned {response.status_code}."
        )

    if response.status_code != 200:
        pytest.skip(
            "Live integration server readiness probe failed: "
            f"discovery returned {response.status_code} with body {response.text!r}."
        )


@pytest.fixture(scope="session")
def integration_config() -> IntegrationConfig:
    config = _load_integration_config()
    _ensure_registry_ready(config)
    return config


@pytest.fixture(scope="session")
def integration_settings(integration_config: IntegrationConfig) -> Settings:
    return Settings(
        server_base_url=integration_config.base_url,
        read_token=integration_config.read_token,
        server_timeout_seconds=integration_config.timeout_seconds,
        _env_file=None,
    )


@pytest.fixture(scope="session")
def publish_token(integration_config: IntegrationConfig) -> str:
    if integration_config.publish_token:
        return integration_config.publish_token

    _skip_missing_publish_token()


def _skip_missing_publish_token() -> NoReturn:
    pytest.skip(
        "Live integration publish token is not configured. "
        "Set APTITUDE_INTEGRATION_PUBLISH_TOKEN or APTITUDE_PUBLISH_TOKEN."
    )
    raise AssertionError("unreachable")
