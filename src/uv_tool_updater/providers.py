from __future__ import annotations

import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from .errors import InvalidResponseError, NetworkError, ReleaseNotFoundError
from .models import ReleaseInfo


class ReleaseProvider(Protocol):
    def latest_release(
        self,
        package_name: str,
        *,
        allow_prereleases: bool = False,
        timeout: float = 5.0,
    ) -> ReleaseInfo: ...


class StaticProvider:
    def __init__(self, release: ReleaseInfo) -> None:
        self.release = release

    def latest_release(
        self,
        package_name: str,
        *,
        allow_prereleases: bool = False,
        timeout: float = 5.0,
    ) -> ReleaseInfo:
        del timeout
        if canonicalize_name(package_name) != canonicalize_name(self.release.package_name):
            raise ReleaseNotFoundError(f"Static provider has no release for {package_name!r}")
        if self.release.yanked or (self.release.version.is_prerelease and not allow_prereleases):
            raise ReleaseNotFoundError(f"No eligible release for {package_name!r}")
        return self.release


class PyPIJsonProvider:
    def __init__(self, base_url: str = "https://pypi.org", *, user_agent: str = "uv-tool-updater/0.1.0") -> None:
        base_url = base_url.rstrip("/")
        if not base_url.startswith("https://"):
            raise ValueError("Provider base_url must use HTTPS")
        self.base_url = base_url
        self.user_agent = user_agent

    def latest_release(
        self,
        package_name: str,
        *,
        allow_prereleases: bool = False,
        timeout: float = 5.0,
    ) -> ReleaseInfo:
        url = f"{self.base_url}/pypi/{quote(package_name, safe='')}/json"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is HTTPS-validated
                payload = json.load(response)
        except HTTPError as exc:
            if exc.code == 404:
                raise ReleaseNotFoundError(f"Package {package_name!r} was not found") from exc
            raise NetworkError(f"PyPI returned HTTP {exc.code}", cause=exc) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise NetworkError("Could not reach the release provider", cause=exc) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidResponseError("Release provider returned invalid JSON", cause=exc) from exc
        return self._parse(payload, package_name, allow_prereleases=allow_prereleases)

    @staticmethod
    def _parse(payload: Any, package_name: str, *, allow_prereleases: bool) -> ReleaseInfo:
        try:
            returned_name = payload["info"]["name"]
            releases = payload["releases"]
            if not isinstance(returned_name, str) or not isinstance(releases, dict):
                raise TypeError
        except (KeyError, TypeError) as exc:
            raise InvalidResponseError("Release response is missing required fields", cause=exc) from exc
        if canonicalize_name(returned_name) != canonicalize_name(package_name):
            raise InvalidResponseError("Release response package name does not match the request")

        candidates: list[tuple[Version, list[dict[str, Any]]]] = []
        for raw_version, files in releases.items():
            if not isinstance(files, list) or not files:
                continue
            try:
                version = Version(raw_version)
            except InvalidVersion:
                continue
            usable = [item for item in files if isinstance(item, dict) and not bool(item.get("yanked"))]
            if not usable or (version.is_prerelease and not allow_prereleases):
                continue
            candidates.append((version, usable))
        if not candidates:
            raise ReleaseNotFoundError(f"No eligible release found for {package_name!r}")

        version, files = max(candidates, key=lambda item: item[0])
        published_at = _published_at(files)
        project_url = payload.get("info", {}).get("project_url") or payload.get("info", {}).get("package_url")
        return ReleaseInfo(
            package_name=returned_name,
            version=version,
            release_url=project_url if isinstance(project_url, str) else None,
            published_at=published_at,
            prerelease=version.is_prerelease,
        )


def _published_at(files: list[dict[str, Any]]) -> datetime | None:
    values: list[datetime] = []
    for item in files:
        raw = item.get("upload_time_iso_8601")
        if not isinstance(raw, str):
            continue
        try:
            values.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            try:
                values.append(parsedate_to_datetime(raw))
            except (TypeError, ValueError):
                pass
    return min(values) if values else None
