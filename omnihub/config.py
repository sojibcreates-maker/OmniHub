"""Durable, crash-safe settings storage for OmniHub.

The store keeps a plain JSON document on disk. Writes go through a
temp-file + ``os.replace`` dance so a crash mid-write can never leave a
truncated settings file behind, and the previous revision is always kept
as a ``.bak`` recovery copy.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from typing import Any, Dict

from .paths import SETTINGS_BACKUP, SETTINGS_FILE

__all__ = ["Settings", "DEFAULTS"]


#: Default document. Users may override any subset of these keys.
DEFAULTS: Dict[str, Any] = {
    "version": 3,
    "theme": {
        "mode": "system",  # system | light | dark
        "accent": "indigo",  # indigo | violet | cyan | emerald | rose | amber
        "density": "comfortable",  # comfortable | compact
        "font_scale": 1.0,
        "reduce_motion": False,
    },
    "gateway": {
        "base_url": "http://localhost:20128",
        "api_key": "local",
        "timeout": 60,
        "poll_interval": 2.5,
        "confirm_stop": True,
        "watchdog": False,
    },
    "behavior": {
        "start_on_launch": False,
        "minimize_to_tray": True,
        "close_to_tray": False,
        "notifications": True,
        "autostart": False,
        "check_updates": True,
    },
    "window": {
        "geometry": None,
        "page": 0,
        "sidebar_compact": None,
    },
    "scratchpad": {
        "wrap": True,
        "font_size": 13,
    },
}

_TRUTHY = {"1", "true", "yes", "on"}


class Settings:
    """Thread-safe JSON settings store with atomic persistence."""

    def __init__(self, path: os.PathLike | str = SETTINGS_FILE) -> None:
        self._path = os.fspath(path)
        self._backup_path = os.fspath(SETTINGS_BACKUP)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = copy.deepcopy(DEFAULTS)
        self._dirty = False
        self._last_error: str | None = None

    # ------------------------------------------------------------------ IO

    @property
    def path(self) -> str:
        return self._path

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def load(self) -> "Settings":
        """Read settings from disk, falling back to the backup then defaults."""
        with self._lock:
            self._last_error = None
            for candidate in (self._path, self._backup_path):
                data = self._read_json(candidate)
                if data is not None:
                    self._data = self._merge(copy.deepcopy(DEFAULTS), data)
                    if candidate == self._backup_path:
                        self._last_error = "Primary settings file unreadable; recovered from backup."
                    return self
            self._data = copy.deepcopy(DEFAULTS)
            return self

    def _read_json(self, path: str) -> Dict[str, Any] | None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return payload
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            self._last_error = f"Could not read {os.path.basename(path)}: {exc}"
        return None

    @staticmethod
    def _merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge ``overlay`` into a copy of ``base``."""
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = Settings._merge(base[key], value)
            else:
                base[key] = value
        return base

    def save(self) -> bool:
        """Atomically persist the current document. Returns success."""
        with self._lock:
            self._last_error = None
            payload = json.dumps(self._data, indent=2, ensure_ascii=False, sort_keys=True)
            directory = os.path.dirname(self._path) or "."
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as exc:
                self._last_error = f"Cannot create {directory}: {exc}"
                return False

            # Keep a recovery copy of the last known-good revision.
            try:
                if os.path.exists(self._path):
                    with open(self._path, "r", encoding="utf-8") as handle:
                        previous = handle.read()
                    with open(self._backup_path, "w", encoding="utf-8") as handle:
                        handle.write(previous)
            except OSError:
                pass

            handle = None
            tmp_path = ""
            try:
                fd, tmp_path = tempfile.mkstemp(
                    prefix=".omnihub-settings-", suffix=".tmp", dir=directory
                )
                handle = os.fdopen(fd, "w", encoding="utf-8")
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                handle.close()
                handle = None
                os.replace(tmp_path, self._path)
                tmp_path = ""
            except OSError as exc:
                self._last_error = f"Failed to save settings: {exc}"
                return False
            finally:
                if handle is not None:
                    try:
                        handle.close()
                    except OSError:
                        pass
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            self._dirty = False
            return True

    def save_debounced(self, delay: float = 0.8) -> None:
        """Schedule a save shortly after the call (coalesces rapid edits)."""
        if getattr(self, "_debounce_timer", None) is not None:
            try:
                self._debounce_timer.stop()
            except RuntimeError:
                pass
        from PyQt5.QtCore import QTimer

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(int(delay * 1000))
        timer.timeout.connect(self.save)
        self._debounce_timer = timer
        timer.start()

    # -------------------------------------------------------------- access

    def get(self, dotted: str, default: Any = None) -> Any:
        """Read a value using dotted path notation (``theme.mode``)."""
        with self._lock:
            node: Any = self._data
            for part in dotted.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return copy.deepcopy(node) if isinstance(node, (dict, list)) else node

    def set(self, dotted: str, value: Any, persist: bool = True) -> None:
        """Write a value using dotted path notation."""
        with self._lock:
            parts = dotted.split(".")
            node = self._data
            for part in parts[:-1]:
                child = node.get(part)
                if not isinstance(child, dict):
                    child = {}
                    node[part] = child
                node = child
            node[parts[-1]] = value
            self._dirty = True
        if persist:
            self.save()

    def section(self, name: str) -> Dict[str, Any]:
        with self._lock:
            value = self._data.get(name)
            return copy.deepcopy(value) if isinstance(value, dict) else {}

    def update_section(self, name: str, values: Dict[str, Any], persist: bool = True) -> None:
        with self._lock:
            current = self._data.get(name)
            if not isinstance(current, dict):
                current = {}
                self._data[name] = current
            current.update(values)
            self._dirty = True
        if persist:
            self.save()

    def reset_section(self, name: str, persist: bool = True) -> None:
        with self._lock:
            self._data[name] = copy.deepcopy(DEFAULTS.get(name, {}))
            self._dirty = True
        if persist:
            self.save()

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def replace(self, data: Dict[str, Any]) -> None:
        """Replace the whole document (used by settings import)."""
        with self._lock:
            self._data = self._merge(copy.deepcopy(DEFAULTS), data)
            self._dirty = True
        self.save()

    # -------------------------------------------------------------- helpers

    def bool_of(self, dotted: str, default: bool = False) -> bool:
        value = self.get(dotted, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in _TRUTHY
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def float_of(self, dotted: str, default: float = 0.0) -> float:
        try:
            return float(self.get(dotted, default))
        except (TypeError, ValueError):
            return default

    def int_of(self, dotted: str, default: int = 0) -> int:
        try:
            return int(float(self.get(dotted, default)))
        except (TypeError, ValueError):
            return default

    def str_of(self, dotted: str, default: str = "") -> str:
        value = self.get(dotted, default)
        return value if isinstance(value, str) else default

    @staticmethod
    def redact(value: str, keep: int = 4) -> str:
        """Mask a secret for display purposes."""
        if not value:
            return "(not set)"
        if len(value) <= keep:
            return "*" * len(value)
        return f"{value[:keep]}{'*' * 8}{value[-2:]}"
