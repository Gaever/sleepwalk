from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "sleepwalk"


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def state_path() -> Path:
    return state_dir() / "state.json"


def log_path() -> Path:
    return state_dir() / "sleepwalk.log"
