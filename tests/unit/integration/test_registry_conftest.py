from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import httpx
import pytest
from integration.registry.support import build_publish_payload, ensure_publish_ready


def _load_registry_conftest():
    module_path = (
        Path(__file__).resolve().parents[2] / "integration" / "registry" / "conftest.py"
    )
    spec = spec_from_file_location("registry_integration_conftest", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_integration_config_uses_read_token_for_publish_fallback(
    monkeypatch,
    tmp_path,
) -> None:
    registry_conftest = _load_registry_conftest()
    monkeypatch.setattr(registry_conftest, "REPO_ROOT", tmp_path)

    monkeypatch.setenv("APTITUDE_SERVER_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("APTITUDE_READ_TOKEN", "reader-token")
    monkeypatch.delenv("APTITUDE_INTEGRATION_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("APTITUDE_PUBLISH_TOKEN", raising=False)

    config = registry_conftest._load_integration_config()

    assert config.read_token == "reader-token"
    assert config.publish_token == "reader-token"


def test_load_integration_config_reads_tokens_from_repo_env_file(
    monkeypatch,
    tmp_path,
) -> None:
    registry_conftest = _load_registry_conftest()
    monkeypatch.setattr(registry_conftest, "REPO_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "APTITUDE_SERVER_BASE_URL=http://env-file.test\n"
        "APTITUDE_READ_TOKEN=env-reader-token\n"
    )

    monkeypatch.delenv("APTITUDE_SERVER_BASE_URL", raising=False)
    monkeypatch.delenv("APTITUDE_READ_TOKEN", raising=False)
    monkeypatch.delenv("APTITUDE_INTEGRATION_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("APTITUDE_PUBLISH_TOKEN", raising=False)

    config = registry_conftest._load_integration_config()

    assert config.base_url == "http://env-file.test"
    assert config.read_token == "env-reader-token"
    assert config.publish_token == "env-reader-token"


def test_load_integration_config_prefers_publish_token_over_read_fallback(
    monkeypatch,
    tmp_path,
) -> None:
    registry_conftest = _load_registry_conftest()
    monkeypatch.setattr(registry_conftest, "REPO_ROOT", tmp_path)

    monkeypatch.setenv("APTITUDE_READ_TOKEN", "reader-token")
    monkeypatch.setenv("APTITUDE_PUBLISH_TOKEN", "publisher-token")
    monkeypatch.delenv("APTITUDE_INTEGRATION_PUBLISH_TOKEN", raising=False)

    config = registry_conftest._load_integration_config()

    assert config.read_token == "reader-token"
    assert config.publish_token == "publisher-token"


def test_ensure_publish_ready_skips_when_write_endpoint_is_unavailable() -> None:
    response = httpx.Response(404, text='{"detail":"Not Found"}')

    with pytest.raises(pytest.skip.Exception):
        ensure_publish_ready(response)


def test_ensure_publish_ready_accepts_created_response() -> None:
    response = httpx.Response(201, text='{"ok":true}')

    ensure_publish_ready(response)


def test_build_publish_payload_matches_current_live_publish_shape() -> None:
    payload = build_publish_payload(
        version="1.2.3",
        raw_markdown="# Demo\n",
        name="Demo Skill",
        description="Demo description",
        tags=["demo"],
        token_estimate=42,
        maturity_score=0.8,
        security_score=0.9,
    )

    assert payload["intent"] == "create_skill"
    assert payload["content"] == {"raw_markdown": "# Demo\n"}
    assert "rendered_summary" not in payload["content"]
    assert "headers" not in payload["metadata"]
    assert payload["governance"] == {"trust_tier": "untrusted"}
    assert "lifecycle_status" not in payload["governance"]
