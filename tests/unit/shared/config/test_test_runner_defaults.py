from __future__ import annotations

import sys
from pathlib import Path
import shlex
from typing import Any, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[4]


def _load_pyproject() -> dict[str, Any]:
    return cast(dict[str, Any], tomllib.loads((ROOT / "pyproject.toml").read_text()))


def test_pytest_defaults_show_test_progress_and_duration() -> None:
    pyproject = _load_pyproject()
    pytest_options = cast(dict[str, str], pyproject["tool"]["pytest"]["ini_options"])
    addopts = shlex.split(pytest_options["addopts"])

    assert "-ra" in addopts
    assert "-q" not in addopts
    assert pytest_options["console_output_style"] == "progress"


def test_makefile_test_target_does_not_force_quiet_pytest() -> None:
    makefile = (ROOT / "Makefile").read_text()

    test_block = makefile.split("test:\n", maxsplit=1)[1].split(
        "\n\ntest-cov:", maxsplit=1
    )[0]

    assert "python -m pytest" in test_block
    assert " -q" not in test_block
