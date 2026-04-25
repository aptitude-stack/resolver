"""Safe helpers for reading and extracting skill archive artifacts."""

from __future__ import annotations

from contextlib import closing
import importlib
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from typing import BinaryIO, cast

from aptitude_resolver.domain.errors import InvalidArtifactError
from aptitude_resolver.lockfile import LockedSkill

PREVIEW_FILENAMES = ("SKILL.md", "content.md", "README.md", "readme.md")


def extract_tar_zstd_artifact(
    *,
    node: LockedSkill,
    artifact: bytes,
    target_dir: Path,
) -> list[str]:
    """Extract one locked tar.zst artifact into target_dir safely."""

    target_dir.mkdir(parents=True, exist_ok=True)
    extracted_paths: list[str] = []
    try:
        with closing(_open_zstd_reader(artifact)) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                for member in archive:
                    destination = _safe_member_destination(
                        node=node,
                        target_dir=target_dir,
                        member=member,
                    )
                    if member.isdir():
                        destination.mkdir(parents=True, exist_ok=True)
                        extracted_paths.append(
                            _relative_output_path(target_dir, destination)
                        )
                        continue
                    source = archive.extractfile(member)
                    if source is None:
                        raise InvalidArtifactError(
                            node.slug,
                            node.version,
                            f"Archive file '{member.name}' has no readable payload.",
                        )
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    _apply_safe_file_mode(destination, member.mode)
                    extracted_paths.append(_relative_output_path(target_dir, destination))
    except InvalidArtifactError:
        raise
    except Exception as exc:
        raise InvalidArtifactError(
            node.slug,
            node.version,
            "Artifact is not a readable tar.zst archive.",
        ) from exc

    return extracted_paths


def preview_tar_zstd_artifact(
    *,
    slug: str,
    version: str,
    artifact: bytes,
    limit: int,
) -> tuple[str, bool]:
    """Return a bounded text preview from a tar.zst artifact."""

    try:
        with closing(_open_zstd_reader(artifact)) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    member_path = _safe_member_path(slug, version, member.name)
                    if member_path.name not in PREVIEW_FILENAMES:
                        continue
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    with source:
                        payload = source.read(max(limit + 1, 1))
                    text = payload.decode("utf-8", errors="replace")
                    if len(text) <= limit:
                        return text, False
                    if limit <= 3:
                        return text[:limit], True
                    return text[: limit - 3].rstrip() + "...", True
    except InvalidArtifactError:
        raise
    except Exception as exc:
        raise InvalidArtifactError(
            slug,
            version,
            "Artifact is not a readable tar.zst archive.",
        ) from exc

    return "", False


def _open_zstd_reader(artifact: bytes) -> BinaryIO:
    try:
        zstd_module = importlib.import_module("compression.zstd")
    except ImportError:
        import zstandard

        decompressor = zstandard.ZstdDecompressor()
        return cast(BinaryIO, decompressor.stream_reader(io.BytesIO(artifact)))

    return cast(BinaryIO, zstd_module.open(io.BytesIO(artifact), "rb"))


def _safe_member_destination(
    *,
    node: LockedSkill,
    target_dir: Path,
    member: tarfile.TarInfo,
) -> Path:
    if not member.isdir() and not member.isfile():
        raise InvalidArtifactError(
            node.slug,
            node.version,
            f"Archive member '{member.name}' is not a regular file or directory.",
        )
    member_path = _safe_member_path(node.slug, node.version, member.name)
    destination = target_dir.joinpath(*member_path.parts)
    _ensure_within_directory(
        slug=node.slug,
        version=node.version,
        root=target_dir,
        destination=destination,
    )
    return destination


def _safe_member_path(slug: str, version: str, raw_name: str) -> PurePosixPath:
    if "\\" in raw_name:
        raise InvalidArtifactError(
            slug,
            version,
            f"Archive member '{raw_name}' uses an unsafe path separator.",
        )
    member_path = PurePosixPath(raw_name)
    if member_path.is_absolute():
        raise InvalidArtifactError(
            slug,
            version,
            f"Archive member '{raw_name}' uses an absolute path.",
        )
    if not member_path.parts or any(
        part in {"", ".", ".."} for part in member_path.parts
    ):
        raise InvalidArtifactError(
            slug,
            version,
            f"Archive member '{raw_name}' contains an unsafe path segment.",
        )
    if ":" in member_path.parts[0]:
        raise InvalidArtifactError(
            slug,
            version,
            f"Archive member '{raw_name}' looks like a drive-qualified path.",
        )
    return member_path


def _ensure_within_directory(
    *,
    slug: str,
    version: str,
    root: Path,
    destination: Path,
) -> None:
    resolved_root = root.resolve()
    resolved_destination = destination.resolve(strict=False)
    if (
        resolved_root != resolved_destination
        and resolved_root not in resolved_destination.parents
    ):
        raise InvalidArtifactError(
            slug,
            version,
            f"Archive member would escape target directory: {destination}",
        )


def _relative_output_path(root: Path, destination: Path) -> str:
    return destination.relative_to(root).as_posix()


def _apply_safe_file_mode(destination: Path, mode: int) -> None:
    if os.name == "nt":
        return
    destination.chmod(mode & 0o777)
