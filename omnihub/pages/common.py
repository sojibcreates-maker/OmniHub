"""Shared building blocks used by more than one page."""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..context import current_theme
from ..icons import draw_icon
from ..widgets import Card, Toggle

__all__ = [
    "FormRow",
    "SettingSwitch",
    "AccentSwatch",
    "group_card",
    "copy_to_clipboard",
    "PageHeader",
    "InlineNotice",
]


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the clipboard. Returns success."""
    clipboard = QApplication.clipboard()
    if clipboard is None:
        return False
    clipboard.setText(text or "")
    return True


class FormRow(QWidget):
    """A labelled control row used inside settings cards."""

    def __init__(
        self,
        label: str,
        control: QWidget,
        parent: Optional[QWidget] = None,
        description: str = "",
        label_width: int = 170,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(14)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self._label = QLabel(label)
        self._label.setObjectName("H3")
        self._label.setMinimumWidth(label_width)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_box.addWidget(self._label)
        if description:
            desc = QLabel(description)
            desc.setObjectName("Faint")
            desc.setWordWrap(True)
            text_box.addWidget(desc)
        layout.addLayout(text_box)
        layout.addStretch()
        layout.addWidget(control, 0, Qt.AlignVCenter)
        self.control = control


class SettingSwitch(QWidget):
    """Title + description on the left, a toggle on the right."""

    changed = pyqtSignal(bool)

    def __init__(
        self,
        title: str,
        description: str = "",
        checked: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(16)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("H3")
        text_box.addWidget(self._title)
        if description:
            self._description = QLabel(description)
            self._description.setObjectName("Faint")
            self._description.setWordWrap(True)
            text_box.addWidget(self._description)
        layout.addLayout(text_box)
        layout.addStretch()

        self._toggle = Toggle(self, checked)
        self._toggle.setToolTip("Toggle this setting")
        self._toggle.toggled.connect(self.changed.emit)
        layout.addWidget(self._toggle, 0, Qt.AlignVCenter)

    def isChecked(self) -> bool:
        return self._toggle.isChecked()

    def setChecked(self, value: bool) -> None:
        self._toggle.setChecked(value)


class AccentSwatch(QPushButton):
    """A round colour button used to pick the accent colourway."""

    def __init__(self, color: str, tooltip: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event) -> None:
        theme = current_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        radius = 9.0
        center = self.rect().center()
        rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(rect)

        if self.isChecked():
            pen = QPen(QColor(theme.palette.text if theme else "#FFFFFF"))
            pen.setWidthF(2.0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(-3.5, -3.5, 3.5, 3.5))
        painter.end()


def group_card(title: str, description: str = "") -> Tuple[Card, QVBoxLayout]:
    """Create a titled settings card and return it with its body layout."""
    card = Card()
    outer = QVBoxLayout(card)
    outer.setContentsMargins(18, 16, 18, 16)
    outer.setSpacing(12)

    header = QVBoxLayout()
    header.setSpacing(2)
    label = QLabel(title)
    label.setObjectName("H2")
    header.addWidget(label)
    if description:
        desc = QLabel(description)
        desc.setObjectName("Faint")
        desc.setWordWrap(True)
        header.addWidget(desc)
    outer.addLayout(header)
    return card, outer


class PageHeader(QWidget):
    """The standard title block rendered at the top of every page."""

    def __init__(self, title: str, subtitle: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self._title = QLabel(title)
        self._title.setObjectName("H1")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("Muted")
        self._subtitle.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)

    def set_text(self, title: str, subtitle: str = "") -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)


class InlineNotice(QWidget):
    """A slim inline banner used for hints and warnings."""

    def __init__(self, text: str = "", icon: str = "info", tone: str = "info", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._icon_name = icon
        self._tone = tone
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(9)
        self._icon = QLabel()
        self._icon.setFixedSize(16, 16)
        self._text = QLabel(text)
        self._text.setObjectName("Muted")
        self._text.setWordWrap(True)
        layout.addWidget(self._icon)
        layout.addWidget(self._text, 1)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        theme = current_theme()
        if theme is None:
            return
        palette = theme.palette
        color = {
            "info": palette.info,
            "success": palette.success,
            "warning": palette.warning,
            "danger": palette.danger,
        }.get(tone, palette.info)
        background = {
            "info": palette.info_soft,
            "success": palette.success_soft,
            "warning": palette.warning_soft,
            "danger": palette.danger_soft,
        }.get(tone, palette.info_soft)
        self.setStyleSheet(
            f"InlineNotice {{ background-color: {background}; border: 1px solid {color};"
            f" border-radius: 10px; }}"
        )
        painter = QPainter(self._icon)
        painter.setRenderHint(QPainter.Antialiasing, True)
        draw_icon(painter, self._icon_name, QRectF(0, 0, 16, 16), color, 1.6)
        painter.end()

    def set_text(self, text: str) -> None:
        self._text.setText(text)
