from pathlib import Path

from packaging.version import Version

from uv_tool_updater.checker import check_for_update
from uv_tool_updater.models import InstalledTool, ReleaseInfo, UpdateStatus
from uv_tool_updater.providers import StaticProvider


def installed(version: str = "1", *, managed: bool = True) -> InstalledTool:
    return InstalledTool(
        "demo", "demo", Version(version), Path("/bin/demo"), Path("/tools/demo"),
        Path("/bin/uv"), Path("/tools"), managed,
    )


def test_update_available_and_up_to_date() -> None:
    assert check_for_update(installed(), StaticProvider(ReleaseInfo("demo", Version("2")))).status is UpdateStatus.UPDATE_AVAILABLE
    assert check_for_update(installed("2"), StaticProvider(ReleaseInfo("demo", Version("2")))).status is UpdateStatus.UP_TO_DATE
    assert check_for_update(installed("3"), StaticProvider(ReleaseInfo("demo", Version("2")))).status is UpdateStatus.UP_TO_DATE


def test_unsupported_installation_still_returns_release() -> None:
    result = check_for_update(installed(managed=False), StaticProvider(ReleaseInfo("demo", Version("2"))))
    assert result.status is UpdateStatus.UNSUPPORTED_INSTALLATION
    assert result.release and result.release.version == Version("2")
