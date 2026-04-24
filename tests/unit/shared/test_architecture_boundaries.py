from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = ROOT / "src" / "aptitude_resolver"
PACKAGE_NAMES = {
    "application",
    "cache",
    "discovery",
    "domain",
    "execution",
    "governance",
    "interfaces",
    "lockfile",
    "registry",
    "resolution",
    "shared",
    "telemetry",
}
ALLOWED_IMPORTS = {
    "application": {
        "cache",
        "discovery",
        "domain",
        "execution",
        "governance",
        "lockfile",
        "registry",
        "resolution",
        "shared",
        "telemetry",
    },
    "cache": set(),
    "discovery": {"domain", "shared"},
    "domain": set(),
    "execution": {"domain", "lockfile"},
    "governance": {"domain"},
    "interfaces": {"application", "domain", "telemetry"},
    "lockfile": {"domain"},
    "registry": {"cache", "domain", "shared"},
    "resolution": {"domain", "shared"},
    "shared": set(),
    "telemetry": set(),
}


def test_package_imports_follow_documented_dependency_direction() -> None:
    violations: list[str] = []

    for path in sorted(SRC_ROOT.rglob("*.py")):
        owner = path.relative_to(SRC_ROOT).parts[0]
        if owner not in PACKAGE_NAMES:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            for module_name in _imported_modules(node):
                imported_package = _aptitude_package(module_name)
                if imported_package is None or imported_package == owner:
                    continue
                if imported_package not in ALLOWED_IMPORTS[owner]:
                    violations.append(
                        f"{path.relative_to(ROOT)} imports {module_name}"
                    )

    assert violations == []


def test_execution_does_not_depend_on_resolution_graph() -> None:
    violations: list[str] = []

    for path in sorted((SRC_ROOT / "execution").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            for imported_name in _imported_names(node):
                if imported_name == "ResolutionGraph":
                    violations.append(str(path.relative_to(ROOT)))

    assert violations == []


def _imported_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return [node.module]
    return []


def _imported_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.rsplit(".", maxsplit=1)[-1] for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [alias.name for alias in node.names]
    return []


def _aptitude_package(module_name: str) -> str | None:
    prefix = "aptitude_resolver."
    if not module_name.startswith(prefix):
        return None
    package = module_name.removeprefix(prefix).split(".", maxsplit=1)[0]
    return package if package in PACKAGE_NAMES else None
