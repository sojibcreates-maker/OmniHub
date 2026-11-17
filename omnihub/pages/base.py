"""Base class shared by every OmniHub page."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import QWidget

__all__ = ["Page"]


class Page(QWidget):
    """A page in the main stack.

    Subclasses provide their own title/subtitle and may contribute widgets to
    the window's header bar.
    """

    def title(self) -> str:
        return "Page"

    def subtitle(self) -> str:
        return ""

    def header_actions(self) -> Optional[QWidget]:
        """Optional widget injected into the window header, right-aligned."""
        return None

    def on_activated(self) -> None:
        """Called each time the page becomes visible."""

    def on_deactivated(self) -> None:
        """Called when the page is hidden."""

    def on_theme_changed(self) -> None:
        """Called after the palette changes so custom-painted widgets refresh."""
