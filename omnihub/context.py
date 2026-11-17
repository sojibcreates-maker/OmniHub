"""Application-wide shared context (settings, theme, API client).

A single :class:`AppContext` instance is created during bootstrap and stored
on the QApplication so any widget can reach it without import cycles.
"""

from __future__ import annotations

import time
from typing import Optional

from .config import Settings
from .paths import ensure_dirs
from .theme import ThemeManager

__all__ = ["AppContext", "current_context", "current_theme"]


class AppContext:
    """Holds the long-lived services shared across the UI."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        ensure_dirs()
        self.settings = settings or Settings().load()
        self.theme = ThemeManager(self.settings)
        self.started_at = time.time()
        self._api = None

    @property
    def api(self):
        """Lazily-built OmniRoute HTTP client (keeps import cost off boot)."""
        if self._api is None:
            from .api import OmniRouteClient

            self._api = OmniRouteClient(
                base_url=self.settings.str_of("gateway.base_url", "http://localhost:20128"),
                api_key=self.settings.str_of("gateway.api_key", "local"),
                timeout=self.settings.int_of("gateway.timeout", 60),
            )
        return self._api

    def refresh_api(self) -> None:
        """Rebuild the API client after settings changed."""
        self._api = None


def current_context(app=None) -> Optional[AppContext]:
    """Return the active :class:`AppContext`, if the app is running."""
    if app is None:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
    if app is None:
        return None
    try:
        return app.property("omnihub.context")
    except Exception:
        return None


def current_theme(app=None):
    """Return the active :class:`ThemeManager`, if available."""
    context = current_context(app)
    if context is not None:
        return context.theme
    return None
