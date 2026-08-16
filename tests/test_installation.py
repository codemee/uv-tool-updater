from __future__ import annotations

import importlib.metadata
import subprocess
from pathlib import Path

import pytest

from uv_tool_updater.errors import PackageNotInstalledError
from uv_tool_updater.installation import inspect_installation


class Distribution:
    def __init__(self, editable: bool = False) -> None:
        self.editable = editable

    def read_text(self, name: str) -> str | None:
        if name == "direct_url.json" and self.editable:
            return '{"dir_info":{"editable":true}}'
        return None


def test_detects_prefix_below_uv_tool_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uv = tmp_path / "uv.exe"
    uv.touch()
    root = tmp_path / "Tools With Space"
    prefix = root / "demo"
    command = tmp_path / "demo.exe"
    command.touch()
    monkeypatch.setattr("uv_tool_updater.installation.shutil.which", lambda name, path=None: str(command))
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.2.3")
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Distribution())

    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=str(root) + "\n", stderr="")

    result = inspect_installation("demo", "missing-demo", uv_path=uv, python_prefix=prefix, runner=run)
    assert result.managed_by_uv
    assert str(result.current_version) == "1.2.3"


def test_editable_install_is_not_managed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uv = tmp_path / "uv.exe"
    uv.touch()
    command = tmp_path / "demo.exe"
    command.touch()
    monkeypatch.setattr("uv_tool_updater.installation.shutil.which", lambda name, path=None: str(command))
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Distribution(editable=True))
    run = lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout=str(tmp_path), stderr="")
    result = inspect_installation("demo", "demo", uv_path=uv, python_prefix=tmp_path / "demo", runner=run)
    assert not result.managed_by_uv


def test_missing_command_is_not_safe_to_restart(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uv = tmp_path / "uv.exe"
    uv.touch()
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Distribution())
    monkeypatch.setattr("uv_tool_updater.installation.shutil.which", lambda name, path=None: None)
    run = lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout=str(tmp_path), stderr="")
    result = inspect_installation("demo", "demo", uv_path=uv, python_prefix=tmp_path / "demo", runner=run)
    assert not result.managed_by_uv


def test_missing_package_has_typed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(name: str):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(PackageNotInstalledError) as caught:
        inspect_installation("missing", "missing")
    assert caught.value.code == "package_not_installed"
