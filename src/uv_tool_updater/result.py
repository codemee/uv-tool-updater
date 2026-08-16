from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from .errors import InvalidSessionError
from .models import InstallStatus, UpdateResult

SCHEMA_VERSION = 1


def read_result(path: Path) -> UpdateResult:
    try:
        # Windows PowerShell 5.1 emits a UTF-8 BOM with Set-Content -Encoding utf8.
        data: Any = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise InvalidSessionError("Unsupported result schema")
        return UpdateResult(
            session_id=str(data["session_id"]),
            status=InstallStatus(data["status"]),
            package_name=str(data["package_name"]),
            previous_version=str(data["previous_version"]),
            requested_version=_optional_string(data.get("requested_version")),
            actual_version=_optional_string(data.get("actual_version")),
            uv_exit_code=data.get("uv_exit_code"),
            started_at=_datetime(data["started_at"]),
            finished_at=_datetime(data["finished_at"]),
            log_path=Path(data["log_path"]) if data.get("log_path") else None,
            error=_optional_string(data.get("error")),
        )
    except InvalidSessionError:
        raise
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise InvalidSessionError("Invalid update result", cause=exc) from exc


def confirm_actual_version(result: UpdateResult, actual_version: str) -> UpdateResult:
    """Turn the helper's provisional success into a metadata-confirmed result."""
    try:
        actual = Version(actual_version)
        previous = Version(result.previous_version)
    except InvalidVersion as exc:
        raise InvalidSessionError("Result contains an invalid version", cause=exc) from exc
    status = result.status
    if status is InstallStatus.SUCCEEDED:
        status = InstallStatus.NO_CHANGE if actual == previous else InstallStatus.SUCCEEDED
    return replace(result, status=status, actual_version=str(actual))


def consume_result(path: Path, actual_version: str) -> UpdateResult:
    result = confirm_actual_version(read_result(path), actual_version)
    consumed = path.with_suffix(path.suffix + ".consumed")
    try:
        os.replace(path, consumed)
    except OSError as exc:
        raise InvalidSessionError("Could not mark update result as consumed", cause=exc) from exc
    return result


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            temporary_path.chmod(0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
