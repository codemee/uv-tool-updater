from __future__ import annotations

from .errors import UpdaterError
from .models import InstalledTool, UpdateCheck, UpdateStatus
from .providers import ReleaseProvider


def check_for_update(
    installed: InstalledTool,
    provider: ReleaseProvider,
    *,
    allow_prereleases: bool = False,
    timeout: float = 5.0,
) -> UpdateCheck:
    try:
        release = provider.latest_release(
            installed.package_name,
            allow_prereleases=allow_prereleases,
            timeout=timeout,
        )
    except UpdaterError as exc:
        return UpdateCheck(
            status=UpdateStatus.CHECK_FAILED,
            installed=installed,
            message=str(exc),
            error_code=exc.code,
        )
    if not installed.managed_by_uv:
        return UpdateCheck(
            status=UpdateStatus.UNSUPPORTED_INSTALLATION,
            installed=installed,
            release=release,
            message="The current process is not running from a uv tool environment",
            error_code="unsupported_installation",
        )
    status = UpdateStatus.UPDATE_AVAILABLE if release.version > installed.current_version else UpdateStatus.UP_TO_DATE
    return UpdateCheck(status=status, installed=installed, release=release)
