from __future__ import annotations

import os
import getpass
import subprocess
import sys
from pathlib import Path

from .config import Config


SERVICE_NAME = "sleepwalk.service"
TIMER_NAME = "sleepwalk.timer"


def user_systemd_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def install_units(config: Config, project_dir: Path) -> tuple[Path, Path]:
    systemd_dir = user_systemd_dir()
    systemd_dir.mkdir(parents=True, exist_ok=True)
    service_path = systemd_dir / SERVICE_NAME
    timer_path = systemd_dir / TIMER_NAME

    python = sys.executable
    env_path = f"PYTHONPATH={pythonpath_with_project(project_dir)}"
    service_path.write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Resume tmux-hosted AI agent sessions after usage limits reset",
                "",
                "[Service]",
                "Type=oneshot",
                f"WorkingDirectory={project_dir}",
                f"Environment={env_path}",
                f"ExecStart={python} -m sleepwalk run-scheduled",
                "",
            ]
        ),
        encoding="utf-8",
    )
    timer_path.write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Run sleepwalk periodically",
                "",
                "[Timer]",
                "OnBootSec=2min",
                f"OnUnitActiveSec={config.interval_seconds}s",
                "AccuracySec=30s",
                "Persistent=true",
                "",
                "[Install]",
                "WantedBy=timers.target",
                "",
            ]
        ),
        encoding="utf-8",
    )
    enable_linger()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", TIMER_NAME], check=True)
    return service_path, timer_path


def uninstall_units() -> None:
    subprocess.run(["systemctl", "--user", "disable", "--now", TIMER_NAME], check=False)
    for path in (user_systemd_dir() / SERVICE_NAME, user_systemd_dir() / TIMER_NAME):
        if path.exists():
            path.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)


def enable_linger() -> None:
    user = getpass.getuser()
    direct = subprocess.run(["loginctl", "enable-linger", user], check=False)
    if direct.returncode == 0:
        return
    subprocess.run(["sudo", "-n", "loginctl", "enable-linger", user], check=True)


def pythonpath_with_project(project_dir: Path) -> str:
    parts = [str(project_dir)]
    for item in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if item and item not in parts:
            parts.append(item)
    return os.pathsep.join(parts)
