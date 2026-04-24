"""Shared configuration helpers."""

from aptitude_resolver.shared.config.agent_targets import (
    AgentTargetPreset,
    detect_available_agent_targets,
    get_agent_target_preset,
    resolve_agent_install_root,
    supported_agent_targets,
)
from aptitude_resolver.shared.config.aptitude_config import (
    AptitudeConfig,
    ExecutionConfig,
    PolicyConfig,
    SelectionConfig,
    discover_system_config_path,
    discover_user_config_path,
    discover_workspace_config_path,
    load_aptitude_config,
    load_system_aptitude_config,
    load_user_aptitude_config,
    load_workspace_aptitude_config,
    read_env_execution_overrides,
    read_env_selection_overrides,
    resolve_system_config_path,
    resolve_user_config_path,
)
from aptitude_resolver.shared.config.settings import (
    Settings,
    describe_settings_validation_error,
)

__all__ = [
    "AptitudeConfig",
    "AgentTargetPreset",
    "ExecutionConfig",
    "PolicyConfig",
    "SelectionConfig",
    "detect_available_agent_targets",
    "Settings",
    "describe_settings_validation_error",
    "discover_system_config_path",
    "get_agent_target_preset",
    "discover_user_config_path",
    "discover_workspace_config_path",
    "load_aptitude_config",
    "load_system_aptitude_config",
    "load_user_aptitude_config",
    "load_workspace_aptitude_config",
    "read_env_execution_overrides",
    "read_env_selection_overrides",
    "resolve_system_config_path",
    "resolve_user_config_path",
    "resolve_agent_install_root",
    "supported_agent_targets",
]
