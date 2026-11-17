"""About — identity, runtime information and dependency health."""

from __future__ import annotations

import os
import platform
import time
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_TAGLINE, APP_VERSION, ORG_NAME
from ..context import AppContext
from ..paths import CONFIG_DIR, find_icon
from ..widgets import Card
from .base import Page

__all__ = ["AboutPage"]


class AboutPage(Page):
    """Product information and a quick health check of the environment."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(16)
        scroll_area.setWidget(content)
        self.scroll_area = scroll_area
        root.addWidget(scroll_area)

        layout.addWidget(self._build_identity())
        layout.addWidget(self._build_dependencies())
        layout.addWidget(self._build_links())
        layout.addStretch()

    # ------------------------------------------------------------------ UI

    def _build_identity(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(16)

        icon = QLabel()
        path = find_icon()
        if path is not None:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                icon.setPixmap(
                    pixmap.scaled(
                        68, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
        icon.setFixedSize(68, 68)
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(3)
        name = QLabel(APP_NAME)
        name.setObjectName("H1")
        text.addWidget(name)
        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("Muted")
        text.addWidget(tagline)
        meta = QLabel(f"Version {APP_VERSION} · {ORG_NAME}")
        meta.setObjectName("Faint")
        text.addWidget(meta)
        row.addLayout(text)
        row.addStretch()
        layout.addLayout(row)

        description = QLabel(
            "OmniHub is a native desktop control centre for the OmniRoute AI gateway. "
            "It manages the engine, streams chat completions, charts live system telemetry "
            "and keeps a persistent developer scratchpad — all on your machine, with no "
            "telemetry leaving the device."
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)
        layout.addWidget(description)
        return card

    def _build_dependencies(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Runtime environment")
        title.setObjectName("H2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self._dep_labels: dict = {}
        for row, (key, value) in enumerate(self._dependency_rows()):
            name = QLabel(key)
            name.setObjectName("Muted")
            value_label = QLabel(value)
            value_label.setObjectName("MonoStrong")
            grid.addWidget(name, row, 0)
            grid.addWidget(value_label, row, 1)
            self._dep_labels[key] = value_label
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        return card

    def _dependency_rows(self):
        import psutil
        import requests

        started = self.context.started_at
        rows = [
            ("Python", platform.python_version()),
            ("PyQt5", _qt_version()),
            ("requests", requests.__version__),
            ("psutil", psutil.__version__),
            ("Platform", f"{platform.system()} {platform.release()} ({platform.machine()})"),
            ("Desktop", os.environ.get("XDG_CURRENT_DESKTOP", "unknown")),
            ("Config folder", str(CONFIG_DIR)),
            ("Started", time.strftime("%d %b %Y, %H:%M", time.localtime(started))),
        ]
        return rows

    def _build_links(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Shortcuts")
        title.setObjectName("H2")
        layout.addWidget(title)

        shortcuts = [
            ("Ctrl + K", "Open the command palette"),
            ("Ctrl + 1 … 5", "Jump to a page"),
            ("Ctrl + ,", "Open settings"),
            ("Ctrl + D", "Open the web dashboard"),
            ("Ctrl + R", "Restart the gateway"),
            ("Ctrl + B", "Collapse the sidebar"),
            ("Ctrl + F", "Find in the scratchpad"),
            ("Ctrl + Shift + T", "Toggle light / dark mode"),
            ("Ctrl + Q", "Quit OmniHub"),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        for row, (keys, description) in enumerate(shortcuts):
            key_label = QLabel(keys)
            key_label.setObjectName("MonoStrong")
            description_label = QLabel(description)
            description_label.setObjectName("Muted")
            grid.addWidget(key_label, row, 0)
            grid.addWidget(description_label, row, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        return card

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "About"

    def subtitle(self) -> str:
        return f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}"

    def on_activated(self) -> None:
        self.scroll_area.verticalScrollBar().setValue(0)


def _qt_version() -> str:
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR

        return f"Qt {QT_VERSION_STR} / PyQt {PYQT_VERSION_STR}"
    except Exception:  # pragma: no cover
        return "unknown"
