from __future__ import annotations

from pathlib import Path

from uv_tool_updater.models import InstallStatus
from uv_tool_updater.result import atomic_write_json, consume_result, read_result


def payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "session_id": "abc",
        "package_name": "demo",
        "previous_version": "1.0",
        "requested_version": "2.0",
        "actual_version": None,
        "uv_exit_code": 0,
        "status": "succeeded",
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
        "log_path": "update.log",
        "error": None,
    }


def test_atomic_result_round_trip_and_consume(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    atomic_write_json(path, payload())
    assert read_result(path).status is InstallStatus.SUCCEEDED
    result = consume_result(path, "2.0")
    assert result.actual_version == "2.0"
    assert result.status is InstallStatus.SUCCEEDED
    assert not path.exists()
    assert path.with_suffix(".json.consumed").exists()


def test_unchanged_version_is_not_reported_as_updated(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    atomic_write_json(path, payload())
    assert consume_result(path, "1.0").status is InstallStatus.NO_CHANGE


def test_reads_windows_powershell_utf8_bom(tmp_path: Path) -> None:
    import json

    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload()), encoding="utf-8-sig")
    assert read_result(path).session_id == "abc"
