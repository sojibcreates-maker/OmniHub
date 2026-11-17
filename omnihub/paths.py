"""XDG-compliant filesystem locations used by OmniHub.

Everything the app writes lives under standard XDG directories so the
application plays nicely with sandboxing, backups and multiple installs.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "CONFIG_DIR",
    "DATA_DIR",
    "STATE_DIR",
    "CACHE_DIR",
    "LOG_DIR",
    "SETTINGS_FILE",
    "SETTINGS_BACKUP",
    "NOTES_FILE",
    "NOTES_BACKUP",
    "HISTORY_FILE",
    "LOG_FILE",
    "ICON_CANDIDATES",
    "ensure_dirs",
]


def _xdg(env_var: str, fallback: str) -> Path:
    raw = os.environ.get(env_var, "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / fallback


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / "omnihub"
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "omnihub"
STATE_DIR = DATA_DIR
CACHE_DIR = _xdg("XDG_CACHE_HOME", ".cache") / "omnihub"
LOG_DIR = CONFIG_DIR / "logs"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
SETTINGS_BACKUP = CONFIG_DIR / "settings.json.bak"
NOTES_FILE = CONFIG_DIR / "scratchpad.txt"
NOTES_BACKUP = CONFIG_DIR / "scratchpad.bak"
HISTORY_FILE = CONFIG_DIR / "history.json"
LOG_FILE = LOG_DIR / "omnihub.log"

#: Icon locations probed at runtime (first hit wins).
ICON_CANDIDATES = (
    Path(__file__).resolve().parent.parent / "assets" / "omnihub.png",
    Path(__file__).resolve().parent.parent / "omnihub.png",
    Path.home() / ".local/share/icons" / "omnihub.png",
    Path("/usr/share/icons/hicolor/256x256/apps/omnihub.png"),
)


def ensure_dirs() -> None:
    """Create every directory OmniHub expects to write into."""
    for directory in (CONFIG_DIR, DATA_DIR, CACHE_DIR, LOG_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


def find_icon() -> Path | None:
    """Return the first existing application icon path, if any."""
    for candidate in ICON_CANDIDATES:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None
