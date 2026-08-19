"""Lockfile package."""

from aptitude_resolver.lockfile.model import (
    GovernanceSnapshotEntry,
    LockRoot,
    Lockfile,
    LockedEdge,
    LockedSkill,
    PolicySnapshot,
    SelectionSnapshot,
)
from aptitude_resolver.lockfile.parser import load_lockfile, parse_lockfile
from aptitude_resolver.lockfile.merge import merge_lockfiles
from aptitude_resolver.lockfile.replay import ReplayedLock, replay_lockfile
from aptitude_resolver.lockfile.serializer import (
    build_lockfile,
    lockfile_to_dict,
    serialize_lockfile,
)

__all__ = [
    "GovernanceSnapshotEntry",
    "LockRoot",
    "Lockfile",
    "LockedEdge",
    "LockedSkill",
    "PolicySnapshot",
    "SelectionSnapshot",
    "ReplayedLock",
    "build_lockfile",
    "load_lockfile",
    "merge_lockfiles",
    "lockfile_to_dict",
    "parse_lockfile",
    "replay_lockfile",
    "serialize_lockfile",
]
