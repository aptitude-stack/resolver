"""Shared helpers for agent-specific skill installation targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentTargetPreset:
    """One supported local agent install target preset."""

    agent: str
    display_name: str
    project_relative_root: tuple[str, ...]
    global_relative_root: tuple[str, ...]


SUPPORTED_AGENT_TARGETS: tuple[AgentTargetPreset, ...] = (
    AgentTargetPreset(
        agent="codex",
        display_name="Codex",
        project_relative_root=(".agents", "skills"),
        global_relative_root=(".codex", "skills"),
    ),
    AgentTargetPreset(
        agent="claude-code",
        display_name="Claude Code",
        project_relative_root=(".claude", "skills"),
        global_relative_root=(".claude", "skills"),
    ),
    AgentTargetPreset(
        agent="cursor",
        display_name="Cursor",
        project_relative_root=(".agents", "skills"),
        global_relative_root=(".cursor", "skills"),
    ),
    AgentTargetPreset(
        agent="gemini-cli",
        display_name="Gemini CLI",
        project_relative_root=(".agents", "skills"),
        global_relative_root=(".gemini", "skills"),
    ),
    AgentTargetPreset(
        agent="opencode",
        display_name="OpenCode",
        project_relative_root=(".agents", "skills"),
        global_relative_root=(".config", "opencode", "skills"),
    ),
)


def supported_agent_targets() -> tuple[AgentTargetPreset, ...]:
    """Return the supported agent install presets in CLI display order."""

    return SUPPORTED_AGENT_TARGETS


def get_agent_target_preset(agent: str) -> AgentTargetPreset:
    """Return one supported preset by its stable machine name."""

    normalized = agent.strip().lower()
    for preset in SUPPORTED_AGENT_TARGETS:
        if preset.agent == normalized:
            return preset
    raise ValueError(f"Unsupported agent preset: {agent}")


def resolve_agent_install_root(
    *,
    agent: str,
    scope: str,
    cwd: Path | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the root folder where exported skills should be written."""

    preset = get_agent_target_preset(agent)
    normalized_scope = scope.strip().lower()
    if normalized_scope == "project":
        base = (cwd or Path.cwd()).resolve()
        return base.joinpath(*preset.project_relative_root)
    if normalized_scope == "global":
        base = (home or Path.home()).resolve()
        return base.joinpath(*preset.global_relative_root)
    raise ValueError(f"Unsupported agent scope: {scope}")


def detect_available_agent_targets(
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> list[str]:
    """Return supported presets with likely existing local roots first."""

    detected: list[str] = []
    current_workdir = (cwd or Path.cwd()).resolve()
    current_home = (home or Path.home()).resolve()

    for preset in SUPPORTED_AGENT_TARGETS:
        project_root = current_workdir.joinpath(*preset.project_relative_root)
        global_root = current_home.joinpath(*preset.global_relative_root)
        if project_root.exists() or global_root.exists():
            detected.append(preset.agent)

    return detected
