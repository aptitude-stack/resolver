from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text()


def test_canonical_docs_use_resolver_identity() -> None:
    files = [
        "README.md",
        "docs/README.md",
        "docs/architecture/system-overview.md",
        "docs/architecture/decision-rules.md",
        "docs/reference/recommended-libraries.md",
        ".agents/README.md",
        ".agents/agent.md",
        ".agents/memory/meta.md",
    ]

    for relative_path in files:
        text = _read(relative_path)
        assert "Aptitude Client" not in text


def test_readme_includes_install_and_use_sections() -> None:
    readme = _read("README.md")

    assert "## How To Install" in readme
    assert "## How To Use" in readme
    assert "uv sync --extra dev" in readme
    assert "uvx aptitude-resolver" in readme
    assert 'aptitude install "Postman Primary Skill"' in readme


def test_pyproject_exposes_dual_console_scripts_and_runtime_package_name() -> None:
    pyproject = _read("pyproject.toml")

    assert 'name = "aptitude-resolver"' in pyproject
    assert (
        'aptitude-resolver = "aptitude_resolver.interfaces.cli.main:main"' in pyproject
    )
    assert 'aptitude = "aptitude_resolver.interfaces.cli.main:main"' in pyproject
    assert 'module-name = "aptitude_resolver"' in pyproject
