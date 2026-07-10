from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from .config import Config, load_config, save_config, with_sessions
from .detector import Detection, detect, format_duration
from .interactive import run_wizard
from .paths import config_path, log_path
from .state import SessionState, append_log, load_state, parse_dt, save_state, utcnow
from .systemd import install_units, uninstall_units
from .tmux import capture_pane, list_sessions, send_text


RESET_GRACE = timedelta(minutes=2)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sleepwalk")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")
    sub.add_parser("tick")
    add_parser = sub.add_parser("add")
    add_parser.add_argument("targets", nargs="+")
    remove_parser = sub.add_parser("remove")
    remove_parser.add_argument("targets", nargs="+")
    sub.add_parser("list")
    sub.add_parser("install-systemd")
    sub.add_parser("uninstall-systemd")
    sub.add_parser("paths")

    args = parser.parse_args(argv)
    config = load_config()

    if args.command is None:
        return run_wizard(config)
    if args.command == "status":
        return print_status(config)
    if args.command == "tick":
        return tick(config)
    if args.command == "add":
        targets = sorted({*(session.target for session in config.sessions), *args.targets})
        save_config(with_sessions(config, targets))
        print(f"watching {len(targets)} session(s)")
        return 0
    if args.command == "remove":
        remove = set(args.targets)
        targets = [session.target for session in config.sessions if session.target not in remove]
        save_config(with_sessions(config, targets))
        print(f"watching {len(targets)} session(s)")
        return 0
    if args.command == "list":
        for session in config.sessions:
            print(session.target)
        return 0
    if args.command == "install-systemd":
        service, timer = install_units(config, PROJECT_ROOT)
        print(f"installed {service}")
        print(f"installed {timer}")
        return 0
    if args.command == "uninstall-systemd":
        uninstall_units()
        print("uninstalled sleepwalk user systemd units")
        return 0
    if args.command == "paths":
        print(f"config: {config_path()}")
        print(f"log:    {log_path()}")
        return 0
    parser.print_help()
    return 2


def print_status(config: Config) -> int:
    rows = inspect_sessions(config)
    if not rows:
        print("No watched sessions. Run `sleepwalk` to choose tmux sessions.")
        return 0
    for target, detection in rows:
        state = public_state(detection.state)
        print(f"{target}: {state} reset={format_duration(detection.reset_in)}")
    return 0


def inspect_sessions(config: Config) -> list[tuple[str, Detection]]:
    rows: list[tuple[str, Detection]] = []
    for session in config.sessions:
        if not session.enabled:
            continue
        try:
            rows.append((session.target, detect(capture_pane(session.target, config.tmux_socket))))
        except Exception as exc:
            rows.append((session.target, Detection("missing", str(exc))))
    return rows


def public_state(state: str) -> str:
    if state == "limited":
        return "limited"
    if state == "missing":
        return "missing"
    return "ok"


def tick(config: Config) -> int:
    state = load_state()
    changed = False
    watched = [session for session in config.sessions if session.enabled]
    if not watched:
        append_log("no watched sessions")
        return 0

    now = utcnow()
    for session in watched:
        try:
            text = capture_pane(session.target, config.tmux_socket)
            detection = detect(text)
        except Exception as exc:
            append_log(f"{session.target}: missing: {exc}")
            continue

        if detection.state != "limited":
            append_log(f"{session.target}: {detection.state}")
            continue

        session_state = state.setdefault(session.target, SessionState())
        last_sent = parse_dt(session_state.last_resume_sent_at)
        cooldown_left = None
        if last_sent:
            cooldown_left = timedelta(seconds=session.cooldown_seconds) - (now - last_sent)
        if cooldown_left and cooldown_left.total_seconds() > 0:
            append_log(f"{session.target}: limited, cooldown {format_duration(cooldown_left)}")
            continue

        if detection.reset_in is None:
            append_log(f"{session.target}: limited, reset unknown")
            continue

        if detection.reset_in and detection.reset_in > RESET_GRACE:
            append_log(f"{session.target}: limited, reset in {format_duration(detection.reset_in)}")
            continue

        append_log(f"{session.target}: limited, sent resume")
        print(f"{session.target}: sent `{config.resume_text}`")
        send_text(session.target, config.resume_text, config.tmux_socket)
        session_state.last_resume_sent_at = now.isoformat()
        session_state.last_limited_hash = detection.pane_hash
        changed = True

    if changed:
        save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
