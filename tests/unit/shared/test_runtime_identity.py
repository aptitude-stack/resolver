from __future__ import annotations

import importlib


def test_runtime_package_imports_as_aptitude_resolver() -> None:
    assert importlib.import_module("aptitude_resolver") is not None
