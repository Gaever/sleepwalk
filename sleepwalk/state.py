from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path

from .paths import log_path, state_path


@dataclasses.dataclass
class SessionState:
    last_resume_sent_at: str | None = None
    last_limited_hash: str | None = None
    expected_reset_at: str | None = None


def utcnow() -> datetime:
    return datetime.now(UTC)


def load_state(path: Path | None = None) -> dict[str, SessionState]:
    path = path or state_path()
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {target: SessionState(**value) for target, value in raw.items()}


def save_state(state: dict[str, SessionState], path: Path | None = None) -> None:
    path = path or state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {target: dataclasses.asdict(value) for target, value in state.items()}
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def append_log(message: str) -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = utcnow().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {message}\n")
