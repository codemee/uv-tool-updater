from __future__ import annotations

import pytest
from packaging.version import Version

from uv_tool_updater.errors import InvalidResponseError, ReleaseNotFoundError
from uv_tool_updater.models import ReleaseInfo
from uv_tool_updater.providers import PyPIJsonProvider, StaticProvider


def file(*, yanked: bool = False, uploaded: str = "2026-01-01T00:00:00Z") -> dict[str, object]:
    return {"yanked": yanked, "upload_time_iso_8601": uploaded}


def test_pypi_selects_latest_non_yanked_stable() -> None:
    payload = {
        "info": {"name": "Demo_Tool", "package_url": "https://pypi.org/project/demo-tool/"},
        "releases": {
            "1.0": [file()],
            "1.1rc1": [file()],
            "1.0.post1": [file()],
            "2.0": [file(yanked=True)],
        },
    }
    release = PyPIJsonProvider._parse(payload, "demo-tool", allow_prereleases=False)
    assert release.version == Version("1.0.post1")
    assert release.published_at is not None


def test_pypi_can_select_prerelease() -> None:
    payload = {"info": {"name": "demo"}, "releases": {"1.0": [file()], "2.0rc1": [file()]}}
    assert PyPIJsonProvider._parse(payload, "demo", allow_prereleases=True).version == Version("2.0rc1")


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"info": {}, "releases": {}}, InvalidResponseError),
        ({"info": {"name": "other"}, "releases": {"1": [file()]}}, InvalidResponseError),
        ({"info": {"name": "demo"}, "releases": {"1": [file(yanked=True)]}}, ReleaseNotFoundError),
    ],
)
def test_pypi_rejects_invalid_or_ineligible_data(payload: dict, error: type[Exception]) -> None:
    with pytest.raises(error):
        PyPIJsonProvider._parse(payload, "demo", allow_prereleases=False)


def test_provider_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        PyPIJsonProvider("http://example.test")


def test_static_provider_checks_name_and_channel() -> None:
    provider = StaticProvider(ReleaseInfo("demo", Version("2.0rc1")))
    with pytest.raises(ReleaseNotFoundError):
        provider.latest_release("other")
    with pytest.raises(ReleaseNotFoundError):
        provider.latest_release("demo")
    assert provider.latest_release("demo", allow_prereleases=True).version == Version("2.0rc1")
