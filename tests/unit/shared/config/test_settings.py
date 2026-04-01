from __future__ import annotations

import pytest
from pydantic import ValidationError

from aptitude_resolver.shared.config.settings import Settings


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APTITUDE_SERVER_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("APTITUDE_READ_TOKEN", "reader-token")
    monkeypatch.delenv("APTITUDE_SERVER_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.server_base_url == "http://localhost:8000"
    assert settings.read_token == "reader-token"
    assert settings.server_timeout_seconds == 5.0


def test_settings_require_server_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APTITUDE_SERVER_BASE_URL", raising=False)
    monkeypatch.setenv("APTITUDE_READ_TOKEN", "reader-token")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "server_base_url" in str(exc_info.value)


def test_settings_require_read_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APTITUDE_SERVER_BASE_URL", "http://localhost:8000")
    monkeypatch.delenv("APTITUDE_READ_TOKEN", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "read_token" in str(exc_info.value)
