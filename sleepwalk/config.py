from __future__ import annotations

import dataclasses
import tomllib
from pathlib import Path

from .paths import config_path


DEFAULT_INTERVAL_SECONDS = 30 * 60
DEFAULT_RESUME_TEXT = "продолжай"
DEFAULT_COOLDOWN_SECONDS = 30 * 60


@dataclasses.dataclass(frozen=True)
class SessionConfig:
    target: str
    enabled: bool = True
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS


@dataclasses.dataclass(frozen=True)
class Config:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    resume_text: str = DEFAULT_RESUME_TEXT
    tmux_socket: str | None = None
    sessions: tuple[SessionConfig, ...] = ()


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()

    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    sessions = tuple(
        SessionConfig(
            target=str(item["target"]),
            enabled=bool(item.get("enabled", True)),
            cooldown_seconds=int(item.get("cooldown_seconds", raw.get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS))),
        )
        for item in raw.get("sessions", [])
        if "target" in item
    )

    tmux_socket = raw.get("tmux_socket")
    return Config(
        interval_seconds=int(raw.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)),
        resume_text=str(raw.get("resume_text", DEFAULT_RESUME_TEXT)),
        tmux_socket=str(tmux_socket) if tmux_socket else None,
        sessions=sessions,
    )


def save_config(config: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"interval_seconds = {config.interval_seconds}",
        f"resume_text = {toml_string(config.resume_text)}",
    ]
    if config.tmux_socket:
        lines.append(f"tmux_socket = {toml_string(config.tmux_socket)}")
    lines.append("")
    for session in config.sessions:
        lines.extend(
            [
                "[[sessions]]",
                f"target = {toml_string(session.target)}",
                f"enabled = {str(session.enabled).lower()}",
                f"cooldown_seconds = {session.cooldown_seconds}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def with_sessions(config: Config, targets: list[str]) -> Config:
    return Config(
        interval_seconds=config.interval_seconds,
        resume_text=config.resume_text,
        tmux_socket=config.tmux_socket,
        sessions=tuple(SessionConfig(target=target) for target in targets),
    )


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
