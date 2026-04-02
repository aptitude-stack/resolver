"""Shared orchestration helpers for CLI and wizard flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

from aptitude.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude.application.dto import (
    InstallRequestDto,
    InstallResultDto,
    ResolveQueryRequestDto,
    ResolveQueryResultDto,
    SyncRequestDto,
    SyncResultDto,
)

InteractionMode = Literal["auto", "always", "never"]


class ResolveWorkflowUseCase(Protocol):
    def execute(self, request: ResolveQueryRequestDto) -> ResolveQueryResultDto: ...


class InstallWorkflowUseCase(Protocol):
    def execute(self, request: InstallRequestDto) -> InstallResultDto: ...


class SyncWorkflowUseCase(Protocol):
    def execute(self, request: SyncRequestDto) -> SyncResultDto: ...


ResolveBuilder = Callable[..., tuple[ResolveWorkflowUseCase, Callable[[], None]]]
InstallBuilder = Callable[..., tuple[InstallWorkflowUseCase, Callable[[], None]]]
SyncBuilder = Callable[[], tuple[SyncWorkflowUseCase, Callable[[], None]]]


@dataclass(frozen=True)
class InstallWorkflowOptions:
    """Optional CLI and wizard overrides for planning and install use cases."""

    selection_profile: str | None = None
    interaction_mode: InteractionMode | None = None
    allowed_trust_tiers: list[str] | None = None
    allowed_lifecycle_statuses: list[str] | None = None
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None

    def build_kwargs(self) -> dict[str, object]:
        """Return composition kwargs for the configured overrides."""

        kwargs: dict[str, object] = {}
        if self.selection_profile is not None:
            kwargs["selection_profile_override"] = self.selection_profile
        if self.interaction_mode is not None:
            kwargs["interaction_mode_override"] = self.interaction_mode
        if self.allowed_trust_tiers is not None:
            kwargs["allowed_trust_tiers_override"] = self.allowed_trust_tiers
        if self.allowed_lifecycle_statuses is not None:
            kwargs["allowed_lifecycle_statuses_override"] = (
                self.allowed_lifecycle_statuses
            )
        if self.max_token_estimate is not None:
            kwargs["max_token_estimate_override"] = self.max_token_estimate
        if self.max_content_size_bytes is not None:
            kwargs["max_content_size_bytes_override"] = self.max_content_size_bytes
        return kwargs


class InstallWorkflowService:
    """Run resolve/install/sync workflows with shared builder cleanup."""

    def __init__(
        self,
        *,
        resolve_builder: ResolveBuilder = build_resolve_use_case,
        install_builder: InstallBuilder = build_install_use_case,
        sync_builder: SyncBuilder = build_sync_use_case,
    ) -> None:
        self._resolve_builder = resolve_builder
        self._install_builder = install_builder
        self._sync_builder = sync_builder

    def resolve_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
        options: InstallWorkflowOptions | None = None,
    ) -> ResolveQueryResultDto:
        """Execute resolve with shared override handling and cleanup."""

        use_case, close = self.prepare_resolve(options=options)
        try:
            return self.execute_resolve(
                use_case,
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        finally:
            close()

    def install_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        target: Path,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
        options: InstallWorkflowOptions | None = None,
    ) -> InstallResultDto:
        """Execute install with shared override handling and cleanup."""

        use_case, close = self.prepare_install(options=options)
        try:
            return self.execute_install(
                use_case,
                query=query,
                version=version,
                select_slug=select_slug,
                target=target,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        finally:
            close()

    def sync_lock(
        self,
        *,
        lock_path: Path,
        target: Path,
    ) -> SyncResultDto:
        """Execute lock replay with builder cleanup."""

        use_case, close = self._sync_builder()
        try:
            return use_case.execute(SyncRequestDto(lock_path=lock_path, target=target))
        finally:
            close()

    def prepare_resolve(
        self,
        *,
        options: InstallWorkflowOptions | None = None,
    ) -> tuple[ResolveWorkflowUseCase, Callable[[], None]]:
        """Build one reusable resolve use case with the provided overrides."""

        return self._resolve_builder(**self._build_kwargs(options))

    def execute_resolve(
        self,
        use_case: ResolveWorkflowUseCase,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
    ) -> ResolveQueryResultDto:
        """Execute one prepared resolve use case."""

        return use_case.execute(
            ResolveQueryRequestDto(
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        )

    def prepare_install(
        self,
        *,
        options: InstallWorkflowOptions | None = None,
    ) -> tuple[InstallWorkflowUseCase, Callable[[], None]]:
        """Build one reusable install use case with the provided overrides."""

        return self._install_builder(**self._build_kwargs(options))

    def execute_install(
        self,
        use_case: InstallWorkflowUseCase,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        target: Path,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
    ) -> InstallResultDto:
        """Execute one prepared install use case."""

        return use_case.execute(
            InstallRequestDto(
                query=query,
                version=version,
                select_slug=select_slug,
                target=target,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        )

    @staticmethod
    def _build_kwargs(options: InstallWorkflowOptions | None) -> dict[str, object]:
        """Return composition kwargs for the provided overrides."""

        if options is None:
            return {}
        return options.build_kwargs()
