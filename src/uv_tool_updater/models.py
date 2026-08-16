from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from packaging.version import Version


@dataclass(frozen=True)
class InstalledTool:
    package_name: str
    command_name: str
    current_version: Version
    executable_path: Path
    python_prefix: Path
    uv_path: Path | None
    uv_tool_dir: Path | None
    managed_by_uv: bool


@dataclass(frozen=True)
class ReleaseInfo:
    package_name: str
    version: Version
    release_url: str | None = None
    published_at: datetime | None = None
    yanked: bool = False
    prerelease: bool = False


class UpdateStatus(str, Enum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    UNSUPPORTED_INSTALLATION = "unsupported_installation"
    CHECK_FAILED = "check_failed"


@dataclass(frozen=True)
class UpdateCheck:
    status: UpdateStatus
    installed: InstalledTool | None
    release: ReleaseInfo | None = None
    message: str | None = None
    error_code: str | None = None


class InstallStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NO_CHANGE = "no_change"
    APP_EXIT_TIMEOUT = "app_exit_timeout"
    RESTART_FAILED = "restart_failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class UpdateResult:
    session_id: str
    status: InstallStatus
    package_name: str
    previous_version: str
    requested_version: str | None
    actual_version: str | None
    uv_exit_code: int | None
    started_at: datetime
    finished_at: datetime
    log_path: Path | None
    error: str | None = None


@dataclass(frozen=True)
class UpdatePlan:
    schema_version: int
    session_id: str
    package_name: str
    helper_path: Path
    command_path: Path
    restart_args: tuple[str, ...]
    uv_path: Path
    previous_version: str
    requested_version: str
    restart_on_failure: bool
    wait_timeout: float
    result_path: Path
    log_path: Path
    lock_path: Path
