from __future__ import annotations

import re
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version

_PACKAGE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_SAFE_OPTIONS = frozenset({"--offline", "--no-cache", "--native-tls", "--refresh"})


def upgrade_command(
    uv_path: Path,
    package_name: str,
    target_version: Version,
    *,
    options: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if not _PACKAGE_RE.fullmatch(package_name) or not canonicalize_name(package_name):
        raise ValueError("Invalid Python distribution name")
    unsupported = set(options) - _SAFE_OPTIONS
    if unsupported:
        raise ValueError(f"Unsupported uv option: {sorted(unsupported)[0]}")
    if not uv_path.is_absolute():
        raise ValueError("uv path must be absolute")
    # An installation created with ``uv tool install package==version`` keeps
    # that exact requirement in uv's receipt.  Upgrading by bare package name
    # therefore succeeds without changing anything.  Supplying the release
    # selected by the provider replaces that stale constraint while retaining
    # uv's recorded source and index configuration.
    requirement = f"{package_name}=={target_version}"
    return (str(uv_path), "tool", "upgrade", *options, requirement)
