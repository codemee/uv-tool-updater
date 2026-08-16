from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .result import atomic_write_json


@dataclass(frozen=True)
class UpdateState:
    last_checked_at: str | None = None
    skipped_version: str | None = None
    pending_session_id: str | None = None
    last_result_id: str | None = None


class UpdateStateStore(Protocol):
    def load(self) -> UpdateState: ...
    def save(self, state: UpdateState) -> None: ...


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> UpdateState:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return UpdateState(**{key: data.get(key) for key in UpdateState.__dataclass_fields__})
        except FileNotFoundError:
            return UpdateState()

    def save(self, state: UpdateState) -> None:
        atomic_write_json(self.path, asdict(state))


def check_is_due(last_checked_at: str | None, *, now: datetime, interval_seconds: float = 86400) -> bool:
    if last_checked_at is None:
        return True
    try:
        previous = datetime.fromisoformat(last_checked_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (now - previous).total_seconds() >= interval_seconds
