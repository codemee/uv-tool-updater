from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

from uv_tool_updater.models import InstallStatus
from uv_tool_updater.result import atomic_write_json
from uv_tool_updater.updater import Updater


def test_discovers_and_consumes_latest_valid_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalid = tmp_path / "result-invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    valid = tmp_path / "result-valid.json"
    atomic_write_json(
        valid,
        {
            "schema_version": 1,
            "session_id": "valid",
            "package_name": "demo",
            "previous_version": "1",
            "requested_version": "2",
            "actual_version": None,
            "uv_exit_code": 0,
            "status": "succeeded",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "log_path": None,
            "error": None,
        },
    )
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "2")
    updater = Updater("demo", "demo", state_dir=tmp_path)
    assert updater.pending_results() == (valid,)
    result = updater.consume_latest_result()
    assert result is not None and result.status is InstallStatus.SUCCEEDED
    assert updater.pending_results() == ()
