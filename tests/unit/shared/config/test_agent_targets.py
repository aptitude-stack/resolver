from __future__ import annotations

from pathlib import Path

from aptitude_resolver.shared.config import (
    detect_available_agent_targets,
    get_agent_target_preset,
    resolve_agent_install_root,
    supported_agent_targets,
)


def test_supported_agent_targets_contains_the_phase_one_presets() -> None:
    assert [preset.agent for preset in supported_agent_targets()] == [
        "codex",
        "claude-code",
        "cursor",
        "gemini-cli",
        "opencode",
    ]


def test_resolve_agent_install_root_supports_project_and_global_scopes(tmp_path) -> None:
    cwd = tmp_path / "workspace"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()

    assert resolve_agent_install_root(
        agent="codex",
        scope="project",
        cwd=cwd,
        home=home,
    ) == cwd / ".agents" / "skills"
    assert resolve_agent_install_root(
        agent="opencode",
        scope="global",
        cwd=cwd,
        home=home,
    ) == home / ".config" / "opencode" / "skills"


def test_detect_available_agent_targets_prefers_existing_roots(tmp_path) -> None:
    cwd = tmp_path / "workspace"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    (cwd / ".claude" / "skills").mkdir(parents=True)
    (home / ".cursor" / "skills").mkdir(parents=True)

    detected = detect_available_agent_targets(cwd=cwd, home=home)

    assert detected == ["claude-code", "cursor"]


def test_get_agent_target_preset_returns_display_metadata() -> None:
    preset = get_agent_target_preset("gemini-cli")

    assert preset.display_name == "Gemini CLI"
    assert Path(*preset.project_relative_root) == Path(".agents") / "skills"
