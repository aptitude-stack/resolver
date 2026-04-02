"""Shared configuration helpers."""

from aptitude_client.shared.config.agent_targets import (
    AgentTargetPreset,
    detect_available_agent_targets,
    get_agent_target_preset,
    resolve_agent_install_root,
    supported_agent_targets,
)
from aptitude_client.shared.config.aptitude_config import (
    AptitudeConfig,
    PolicyConfig,
    SelectionConfig,
    discover_user_config_path,
    discover_workspace_config_path,
    load_aptitude_config,
    load_user_aptitude_config,
    load_workspace_aptitude_config,
    read_env_selection_overrides,
)
from aptitude_client.shared.config.settings import Settings

__all__ = [
    "AptitudeConfig",
    "AgentTargetPreset",
    "PolicyConfig",
    "SelectionConfig",
    "detect_available_agent_targets",
    "Settings",
    "get_agent_target_preset",
    "discover_user_config_path",
    "discover_workspace_config_path",
    "load_aptitude_config",
    "load_user_aptitude_config",
    "load_workspace_aptitude_config",
    "read_env_selection_overrides",
    "resolve_agent_install_root",
    "supported_agent_targets",
]
