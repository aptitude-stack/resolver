"""Lock-driven local materialization of locked skills."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from aptitude_resolver.domain.errors import ContentChecksumMismatchError
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.execution.archive import extract_tar_zstd_artifact
from aptitude_resolver.execution.plan import (
    ExecutionPlan,
    build_execution_plan,
    serialize_execution_plan,
)
from aptitude_resolver.lockfile import (
    Lockfile,
    LockedSkill,
    replay_lockfile,
    serialize_lockfile,
)


class RegistryContentPort(Protocol):
    """Artifact content reads required for materialization."""

    def fetch_skill_artifact(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> bytes: ...


@dataclass(frozen=True)
class MaterializedSkill:
    """One lock-driven skill materialized to disk."""

    slug: str
    version: str
    install_path: str


@dataclass(frozen=True)
class MaterializationResult:
    """Result of materializing one lockfile locally."""

    installed_skills: list[MaterializedSkill] = field(default_factory=list)
    materialized_root: str = ""
    execution_plan: ExecutionPlan = field(default_factory=ExecutionPlan)
    trace: list[TraceEntry] = field(default_factory=list)


@dataclass(frozen=True)
class MaterializationOptions:
    """Execution-time controls for lockfile materialization."""

    concurrent_downloads: int | None = None
    concurrent_installs: int | None = None

    def __post_init__(self) -> None:
        if self.concurrent_downloads is not None and self.concurrent_downloads < 1:
            raise ValueError("concurrent_downloads must be greater than or equal to 1.")
        if self.concurrent_installs is not None and self.concurrent_installs < 1:
            raise ValueError("concurrent_installs must be greater than or equal to 1.")


@dataclass(frozen=True)
class _DownloadedArtifact:
    """One downloaded and checksum-verified locked artifact."""

    index: int
    node: LockedSkill
    artifact: bytes


@dataclass(frozen=True)
class _MaterializedSkillResult:
    """One worker result kept separate so completion order stays irrelevant."""

    index: int
    skill: MaterializedSkill
    trace: TraceEntry


def materialize_lockfile(
    *,
    target: Path,
    lockfile: Lockfile,
    registry_client: RegistryContentPort,
    execution_plan: ExecutionPlan | None = None,
    options: MaterializationOptions | None = None,
) -> MaterializationResult:
    """Materialize a local workspace from lock data only."""

    replayed = replay_lockfile(lockfile)
    execution_plan = execution_plan or build_execution_plan(lockfile)
    materialization_options = options or MaterializationOptions()
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    # Keep the staging directory under target.parent so promotion to target stays
    # on the same volume, which keeps the final replace safe on Windows.
    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}-", dir=target.parent
    ) as temp_dir:
        staging_root = Path(temp_dir)
        downloaded_artifacts = _download_locked_artifacts(
            install_order=replayed.install_order,
            registry_client=registry_client,
            options=materialization_options,
        )
        materialized_results = _materialize_locked_skills(
            downloaded_artifacts=downloaded_artifacts,
            staging_root=staging_root,
            options=materialization_options,
        )
        resolution_dir = staging_root / "resolution"
        resolution_dir.mkdir(parents=True, exist_ok=True)
        (resolution_dir / "aptitude.lock.json").write_text(
            serialize_lockfile(lockfile),
            encoding="utf-8",
        )
        (resolution_dir / "execution-plan.json").write_text(
            serialize_execution_plan(execution_plan),
            encoding="utf-8",
        )

        _promote_staging_root(staging_root=staging_root, target=target)
        installed_skills = _final_installed_skills(
            materialized_results=materialized_results,
            target=target,
        )
        trace = _final_trace_entries(
            materialized_results=materialized_results,
            target=target,
        )

    return MaterializationResult(
        installed_skills=installed_skills,
        materialized_root=str(target),
        execution_plan=execution_plan,
        trace=trace,
    )


def _promote_staging_root(*, staging_root: Path, target: Path) -> None:
    """Promote staging without destructively deleting an existing target first."""

    if not target.exists():
        staging_root.replace(target)
        return

    backup = _unique_backup_path(target)
    target.replace(backup)
    try:
        staging_root.replace(target)
    except BaseException:
        if backup.exists() and not target.exists():
            backup.replace(target)
        raise

    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def _unique_backup_path(target: Path) -> Path:
    while True:
        candidate = target.with_name(f".{target.name}.previous-{uuid.uuid4().hex}")
        if not candidate.exists():
            return candidate


def _final_installed_skills(
    *,
    materialized_results: list[_MaterializedSkillResult],
    target: Path,
) -> list[MaterializedSkill]:
    return [
        MaterializedSkill(
            slug=item.skill.slug,
            version=item.skill.version,
            install_path=str(target / "skills" / item.skill.slug / item.skill.version),
        )
        for item in materialized_results
    ]


def _final_trace_entries(
    *,
    materialized_results: list[_MaterializedSkillResult],
    target: Path,
) -> list[TraceEntry]:
    trace: list[TraceEntry] = []
    for item in materialized_results:
        data = dict(item.trace.data)
        data["install_path"] = str(target / "skills" / item.skill.slug / item.skill.version)
        trace.append(
            TraceEntry(
                stage=item.trace.stage,
                action=item.trace.action,
                message=item.trace.message,
                data=data,
            )
        )
    return trace


def _download_locked_artifacts(
    *,
    install_order: list[LockedSkill],
    registry_client: RegistryContentPort,
    options: MaterializationOptions,
) -> list[_DownloadedArtifact]:
    worker_count = _resolve_download_worker_count(options, len(install_order))
    if worker_count <= 1:
        return [
            _download_locked_artifact(
                index=index,
                node=node,
                registry_client=registry_client,
            )
            for index, node in enumerate(install_order)
        ]

    results: list[_DownloadedArtifact | None] = [None] * len(install_order)
    executor = ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="aptitude-download",
    )
    futures: list[Future[_DownloadedArtifact]] = []
    try:
        futures = [
            executor.submit(
                _download_locked_artifact,
                index=index,
                node=node,
                registry_client=registry_client,
            )
            for index, node in enumerate(install_order)
        ]
        for future in as_completed(futures):
            result = future.result()
            results[result.index] = result
    except BaseException:
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(cancel_futures=True)

    return [result for result in results if result is not None]


def _download_locked_artifact(
    *,
    index: int,
    node: LockedSkill,
    registry_client: RegistryContentPort,
) -> _DownloadedArtifact:
    artifact = registry_client.fetch_skill_artifact(
        node.slug,
        node.version,
        checksum_algorithm=node.content_checksum_algorithm,
        checksum_digest=node.content_checksum_digest,
    )
    _verify_checksum(node, artifact)
    return _DownloadedArtifact(index=index, node=node, artifact=artifact)


def _materialize_locked_skills(
    *,
    downloaded_artifacts: list[_DownloadedArtifact],
    staging_root: Path,
    options: MaterializationOptions,
) -> list[_MaterializedSkillResult]:
    worker_count = _resolve_install_worker_count(options, len(downloaded_artifacts))
    if worker_count <= 1:
        return [
            _materialize_locked_skill(
                downloaded_artifact=downloaded_artifact,
                staging_root=staging_root,
            )
            for downloaded_artifact in downloaded_artifacts
        ]

    results: list[_MaterializedSkillResult | None] = [None] * len(downloaded_artifacts)
    executor = ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="aptitude-materialize",
    )
    futures: list[Future[_MaterializedSkillResult]] = []
    try:
        futures = [
            executor.submit(
                _materialize_locked_skill,
                downloaded_artifact=downloaded_artifact,
                staging_root=staging_root,
            )
            for downloaded_artifact in downloaded_artifacts
        ]
        for future in as_completed(futures):
            result = future.result()
            results[result.index] = result
    except BaseException:
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(cancel_futures=True)

    return [result for result in results if result is not None]


def _materialize_locked_skill(
    *,
    downloaded_artifact: _DownloadedArtifact,
    staging_root: Path,
) -> _MaterializedSkillResult:
    node = downloaded_artifact.node
    skill_dir = staging_root / "skills" / node.slug / node.version
    extracted_paths = extract_tar_zstd_artifact(
        node=node,
        artifact=downloaded_artifact.artifact,
        target_dir=skill_dir,
    )
    (skill_dir / "metadata.json").write_text(
        json.dumps(_metadata_to_dict(node), indent=2),
        encoding="utf-8",
    )
    return _MaterializedSkillResult(
        index=downloaded_artifact.index,
        skill=MaterializedSkill(
            slug=node.slug,
            version=node.version,
            install_path=str(skill_dir),
        ),
        trace=TraceEntry(
            stage="execution",
            action="materialize_locked_skill",
            message=f"Materialized locked skill {node.node_id}.",
            data={
                "node_id": node.node_id,
                "install_path": str(skill_dir),
                "extracted_paths": extracted_paths,
            },
        ),
    )


def _resolve_download_worker_count(
    options: MaterializationOptions,
    artifact_count: int,
) -> int:
    if artifact_count <= 0:
        return 1
    worker_count = (
        options.concurrent_downloads
        if options.concurrent_downloads is not None
        else 8
    )
    return max(1, min(worker_count, artifact_count))


def _resolve_install_worker_count(
    options: MaterializationOptions,
    artifact_count: int,
) -> int:
    if artifact_count <= 0:
        return 1
    worker_count = (
        options.concurrent_installs
        if options.concurrent_installs is not None
        else min(os.cpu_count() or 1, 4)
    )
    return max(1, min(worker_count, artifact_count))


def _verify_checksum(node: LockedSkill, artifact: bytes) -> None:
    actual_digest = hashlib.new(
        node.content_checksum_algorithm,
        artifact,
    ).hexdigest()
    if actual_digest != node.content_checksum_digest:
        raise ContentChecksumMismatchError(
            node.slug,
            node.version,
            node.content_checksum_algorithm,
            node.content_checksum_digest,
            actual_digest,
        )


def _metadata_to_dict(node: LockedSkill) -> dict[str, object]:
    return {
        "slug": node.slug,
        "version": node.version,
        "name": node.name,
        "description": node.description,
        "tags": list(node.tags),
        "headers": dict(node.headers),
        "rendered_summary": node.rendered_summary,
        "lifecycle_status": node.lifecycle_status,
        "trust_tier": node.trust_tier,
        "published_at": node.published_at,
        "artifact_ref": node.artifact_ref,
        "content_checksum": {
            "algorithm": node.content_checksum_algorithm,
            "digest": node.content_checksum_digest,
            "size_bytes": node.content_size_bytes,
        },
    }
