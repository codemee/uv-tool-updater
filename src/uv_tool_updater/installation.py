from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping

from packaging.version import InvalidVersion, Version

from .errors import InvalidVersionError, PackageNotInstalledError, ToolDirectoryError, UvNotFoundError
from .models import InstalledTool

Run = Callable[..., subprocess.CompletedProcess[str]]


def inspect_installation(
    package_name: str,
    command_name: str,
    *,
    uv_path: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
    python_prefix: str | os.PathLike[str] | None = None,
    runner: Run = subprocess.run,
) -> InstalledTool:
    """Inspect an installation without making application startup depend on uv."""
    try:
        raw_version = importlib.metadata.version(package_name)
        distribution = importlib.metadata.distribution(package_name)
    except importlib.metadata.PackageNotFoundError as exc:
        raise PackageNotInstalledError(f"Package {package_name!r} is not installed", cause=exc) from exc
    try:
        version = Version(raw_version)
    except InvalidVersion as exc:
        raise InvalidVersionError(f"Installed version for {package_name!r} is invalid", cause=exc) from exc

    environment = os.environ if environ is None else environ
    resolved_uv = find_uv(uv_path=uv_path, environ=environment)
    prefix = _resolved(Path(sys.prefix if python_prefix is None else python_prefix))
    command = shutil.which(command_name, path=environment.get("PATH"))
    executable = _resolved(Path(command)) if command else _resolved(Path(sys.argv[0]))
    tool_dir: Path | None = None
    managed = False
    if resolved_uv is not None:
        try:
            completed = runner(
                [str(resolved_uv), "tool", "dir"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                env=dict(environment),
            )
            output = completed.stdout.strip()
            if not output:
                raise ToolDirectoryError("uv tool dir returned an empty path")
            tool_dir = _resolved(Path(output))
            managed = (
                _is_within(prefix, tool_dir)
                and not _is_editable(distribution)
                and command is not None
                and executable.is_file()
            )
        except (OSError, subprocess.SubprocessError, ToolDirectoryError):
            tool_dir = None
            managed = False

    return InstalledTool(
        package_name=package_name,
        command_name=command_name,
        current_version=version,
        executable_path=executable,
        python_prefix=prefix,
        uv_path=resolved_uv,
        uv_tool_dir=tool_dir,
        managed_by_uv=managed,
    )


def find_uv(
    *, uv_path: str | os.PathLike[str] | None = None, environ: Mapping[str, str] | None = None
) -> Path | None:
    environment = os.environ if environ is None else environ
    candidates = [uv_path, environment.get("UV")]
    for candidate in candidates:
        if candidate:
            resolved = _executable(candidate)
            if resolved is not None:
                return resolved
    found = shutil.which("uv", path=environment.get("PATH"))
    return _resolved(Path(found)) if found else None


def require_uv(installed: InstalledTool) -> Path:
    if installed.uv_path is None:
        raise UvNotFoundError("uv executable could not be found")
    return installed.uv_path


def _executable(value: str | os.PathLike[str]) -> Path | None:
    raw = os.fspath(value)
    if os.path.dirname(raw):
        path = _resolved(Path(raw))
        return path if path.is_file() else None
    found = shutil.which(raw)
    return _resolved(Path(found)) if found else None


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path_key = os.path.normcase(str(path))
        root_key = os.path.normcase(str(root))
        return os.path.commonpath([path_key, root_key]) == root_key
    except (ValueError, OSError):
        return False


def _is_editable(distribution: importlib.metadata.Distribution) -> bool:
    try:
        raw = distribution.read_text("direct_url.json")
        if not raw:
            return False
        return bool(json.loads(raw).get("dir_info", {}).get("editable"))
    except (AttributeError, json.JSONDecodeError, TypeError):
        return False
