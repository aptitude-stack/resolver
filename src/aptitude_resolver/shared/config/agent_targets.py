"""Shared helpers for agent-specific skill installation targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class AgentTargetPreset:
    """One supported local agent install target preset."""

    agent: str
    display_name: str
    project_relative_root: tuple[str, ...]
    global_relative_root: tuple[str, ...]


AgentInstallScope = Literal["project", "global", "custom"]


SUPPORTED_AGENT_TARGETS: tuple[AgentTargetPreset, ...] = (
    AgentTargetPreset(
        agent="codex",
        display_name="Codex",
        project_relative_root=(".codex", "skills"),
        global_relative_root=(".codex", "skills"),
    ),
    AgentTargetPreset(
        agent="claude-code",
        display_name="Claude Code",
        project_relative_root=(".claude", "skills"),
        global_relative_root=(".claude", "skills"),
    ),
    AgentTargetPreset(
        agent="github-copilot",
        display_name="GitHub Copilot",
        project_relative_root=(".github", "skills"),
        global_relative_root=(".copilot", "skills"),
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
    AgentTargetPreset(
        agent="windsurf",
        display_name="Windsurf",
        project_relative_root=(".windsurf", "skills"),
        global_relative_root=(".codeium", "windsurf", "skills"),
    ),
    AgentTargetPreset(
        agent="universal",
        display_name="Universal",
        project_relative_root=(".agents", "skills"),
        global_relative_root=(".agents", "skills"),
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


def resolve_agent_install_roots(
    *,
    agents: list[str] | tuple[str, ...],
    scope: str,
    cwd: Path | None = None,
    home: Path | None = None,
    export_root: Path | None = None,
) -> dict[str, Path]:
    """Resolve all requested agent roots in deterministic display order."""

    normalized_scope = scope.strip().lower()
    normalized_agents = normalize_agent_list(agents, cwd=cwd, home=home)
    if normalized_scope == "custom":
        if export_root is None:
            raise ValueError("Custom install scope requires export_root.")
        root = export_root.expanduser().resolve()
        return {agent: root / agent for agent in normalized_agents}
    return {
        agent: resolve_agent_install_root(
            agent=agent,
            scope=normalized_scope,
            cwd=cwd,
            home=home,
        )
        for agent in normalized_agents
    }


def normalize_agent_list(
    agents: list[str] | tuple[str, ...],
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> list[str]:
    """Expand aliases and validate agent names in supported display order."""

    raw_agents = [item.strip().lower() for item in agents if item.strip()]
    if not raw_agents:
        raise ValueError("At least one agent target is required.")

    if "*" in raw_agents or "all" in raw_agents:
        return [preset.agent for preset in SUPPORTED_AGENT_TARGETS]

    if "detected" in raw_agents or "all-detected" in raw_agents:
        detected = detect_available_agent_targets(cwd=cwd, home=home)
        if not detected:
            raise ValueError("No supported agent skill roots were detected.")
        return detected

    supported = {preset.agent for preset in SUPPORTED_AGENT_TARGETS}
    unsupported = sorted(set(raw_agents) - supported)
    if unsupported:
        raise ValueError(
            "Unsupported agent target(s): "
            + ", ".join(unsupported)
            + ". Supported targets: "
            + ", ".join(preset.agent for preset in SUPPORTED_AGENT_TARGETS)
        )

    requested = set(raw_agents)
    return [
        preset.agent for preset in SUPPORTED_AGENT_TARGETS if preset.agent in requested
    ]


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
