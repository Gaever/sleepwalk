from __future__ import annotations

import subprocess


class TmuxError(RuntimeError):
    pass


def _base_cmd(socket: str | None = None) -> list[str]:
    cmd = ["tmux"]
    if socket:
        cmd.extend(["-S", socket])
    return cmd


def run_tmux(args: list[str], socket: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_base_cmd(socket), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def list_sessions(socket: str | None = None) -> list[str]:
    proc = run_tmux(["list-sessions", "-F", "#{session_name}"], socket=socket, check=False)
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def target_exists(target: str, socket: str | None = None) -> bool:
    proc = run_tmux(["has-session", "-t", target], socket=socket, check=False)
    return proc.returncode == 0


def capture_pane(target: str, socket: str | None = None, lines: int = 80) -> str:
    proc = run_tmux(["capture-pane", "-p", "-S", f"-{lines}", "-t", target], socket=socket, check=False)
    if proc.returncode != 0:
        raise TmuxError(proc.stderr.strip() or f"cannot capture {target}")
    return proc.stdout


def send_text(target: str, text: str, socket: str | None = None) -> None:
    run_tmux(["send-keys", "-t", target, "-l", text], socket=socket)
    run_tmux(["send-keys", "-t", target, "Enter"], socket=socket)
