"""A fuzzy-search command palette (Ctrl + K)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from PyQt5.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QKeyEvent, QPainter
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .icons import draw_icon

__all__ = ["CommandPalette", "Command"]


def _fallback_palette():
    from .theme import DARK

    return DARK


@dataclass
class Command:
    """A single palette entry."""

    title: str
    subtitle: str = ""
    icon: str = "activity"
    identifier: str = ""
    payload: object = None
    shortcut: str = ""
    keywords: str = ""

    def search_text(self) -> str:
        return " ".join((self.title, self.subtitle, self.keywords)).lower()


class _PaletteList(QListWidget):
    """A flat, styled list of palette results."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PaletteList")
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setFrameShape(QFrame.NoFrame)
        self.setSpacing(2)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)


class _PaletteDelegate(QStyledItemDelegate):
    """Draws each result as an icon, a title, a hint and a shortcut."""

    ROW_HEIGHT = 50

    def sizeHint(self, option, index) -> QSize:
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        command = index.data(Qt.UserRole + 1)
        if not isinstance(command, Command):
            super().paint(painter, option, index)
            return

        from .context import current_theme

        theme = current_theme()
        palette = theme.palette if theme else _fallback_palette()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect.adjusted(8, 2, -8, -2)
        selected = bool(option.state & QStyle.State_Selected) or index.row() == self._active_row(index)

        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(palette.accent_soft))
            painter.drawRoundedRect(rect, 8, 8)

        text_color = palette.text if selected else palette.text_muted
        muted_color = palette.text_faint

        # Icon
        icon_rect = QRectF(rect.left() + 11, rect.center().y() - 9, 18, 18)
        draw_icon(
            painter,
            command.icon,
            icon_rect,
            palette.accent if selected else palette.text_muted,
            1.6,
        )

        # Title
        title_font = painter.font()
        title_font.setPointSizeF(max(9.0, title_font.pointSizeF()))
        title_font.setWeight(QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(text_color))
        text_left = rect.left() + 40
        text_right = rect.right() - 70
        title_rect = QRectF(text_left, rect.top() + 7, max(10, text_right - text_left), 18)
        metrics = QFontMetrics(title_font)
        painter.drawText(
            title_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            metrics.elidedText(command.title, Qt.ElideRight, int(title_rect.width())),
        )

        # Subtitle
        if command.subtitle:
            sub_font = painter.font()
            sub_font.setPointSizeF(max(7.5, sub_font.pointSizeF() - 1.5))
            sub_font.setWeight(QFont.Normal)
            painter.setFont(sub_font)
            painter.setPen(QColor(muted_color))
            sub_rect = QRectF(text_left, rect.top() + 24, max(10, text_right - text_left), 16)
            sub_metrics = QFontMetrics(sub_font)
            painter.drawText(
                sub_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                sub_metrics.elidedText(command.subtitle, Qt.ElideRight, int(sub_rect.width())),
            )

        # Shortcut
        if command.shortcut:
            key_font = painter.font()
            key_font.setPointSizeF(max(7.5, key_font.pointSizeF() - 1.0))
            painter.setFont(key_font)
            painter.setPen(QColor(muted_color))
            key_rect = QRectF(rect.right() - 72, rect.center().y() - 9, 66, 18)
            painter.drawText(key_rect, Qt.AlignRight | Qt.AlignVCenter, command.shortcut)

        painter.restore()

    @staticmethod
    def _active_row(index) -> int:
        return -1


class CommandPalette(QDialog):
    """A Spotlight-style launcher for pages and actions."""

    chosen = pyqtSignal(str, object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._commands: List[Command] = []
        self._filtered: List[Command] = []
        self._active = 0

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(620, 420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._frame = QFrame(self)
        self._frame.setObjectName("PaletteFrame")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(16, 14, 16, 12)
        search_row.setSpacing(10)

        self._icon = QLabel()
        self._icon.setFixedSize(18, 18)
        search_row.addWidget(self._icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search commands, pages and settings…")
        self._search.setObjectName("PaletteSearch")
        self._search.setStyleSheet(
            "QLineEdit#PaletteSearch {"
            " background: transparent; border: none; padding: 2px 0px;"
            " font-size: 15px; font-weight: 500;"
            "}"
        )
        self._search.textChanged.connect(self._filter)
        self._search.returnPressed.connect(self._run_active)
        search_row.addWidget(self._search, 1)

        hint = QLabel("Esc")
        hint.setObjectName("Faint")
        search_row.addWidget(hint)
        frame_layout.addLayout(search_row)

        divider = QFrame()
        divider.setObjectName("Divider")
        frame_layout.addWidget(divider)

        self._list = _PaletteList()
        self._delegate = _PaletteDelegate(self._list)
        self._list.setItemDelegate(self._delegate)
        self._list.itemClicked.connect(self._on_item_clicked)
        frame_layout.addWidget(self._list, 1)

        self._footer = QLabel("")
        self._footer.setObjectName("Faint")
        self._footer.setContentsMargins(16, 8, 16, 10)
        frame_layout.addWidget(self._footer)

        outer.addWidget(self._frame)

    # ------------------------------------------------------------------ api

    def set_commands(self, commands: Sequence[Command]) -> None:
        self._commands = list(commands)
        self._filter(self._search.text())

    def show_centered(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            geometry = parent.geometry()
            self.setGeometry(
                geometry.x() + max(0, (geometry.width() - self.width()) // 2),
                geometry.y() + max(40, (geometry.height() - self.height()) // 3),
                self.width(),
                self.height(),
            )
        self.refresh_theme()
        self._search.clear()
        self._filter("")
        self._search.setFocus()
        self.show()
        self.raise_()
        self.activateWindow()

    def refresh_theme(self) -> None:
        """Re-apply the palette colours to the palette chrome."""
        from .context import current_theme

        theme = current_theme()
        palette = theme.palette if theme else _fallback_palette()
        self._frame.setStyleSheet(
            f"QFrame#PaletteFrame {{"
            f" background-color: {palette.surface};"
            f" border: 1px solid {palette.border_strong};"
            " border-radius: 14px;"
            "}"
        )
        self._list.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; }"
            "QListWidget::item { border: none; }"
            "QListWidget::item:selected { background: transparent; }"
        )
        from .icons import icon_pixmap

        self._icon.setPixmap(icon_pixmap("search", 18, palette.text_faint, 1.6))
    # ------------------------------------------------------------ internals

    def _filter(self, text: str) -> None:
        needle = (text or "").strip().lower()
        if needle:
            scored = []
            for command in self._commands:
                score = _fuzzy_score(command, needle)
                if score > 0:
                    scored.append((score, command))
            scored.sort(key=lambda item: item[0], reverse=True)
            self._filtered = [command for _score, command in scored]
        else:
            self._filtered = list(self._commands)

        self._list.clear()
        for command in self._filtered:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, command.identifier or command.title)
            item.setData(Qt.UserRole + 1, command)
            item.setSizeHint(QSize(0, _PaletteDelegate.ROW_HEIGHT))
            item.setToolTip(command.subtitle or command.title)
            self._list.addItem(item)
        if self._filtered:
            self._active = 0
            self._list.setCurrentRow(0)
        self._footer.setText(
            f"{len(self._filtered)} result{'s' if len(self._filtered) != 1 else ''}"
            + ("  ·  ↑↓ to move, ↵ to run" if self._filtered else "")
        )

    def _run_active(self) -> None:
        if not self._filtered:
            return
        command = self._filtered[max(0, min(self._active, len(self._filtered) - 1))]
        self.chosen.emit(command.identifier or command.title, command.payload)
        self.accept()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        identifier = item.data(Qt.UserRole)
        for command in self._filtered:
            if (command.identifier or command.title) == identifier:
                self.chosen.emit(command.identifier or command.title, command.payload)
                break
        self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() == Qt.Key_Down:
            self._move(1)
            return
        if event.key() == Qt.Key_Up:
            self._move(-1)
            return
        super().keyPressEvent(event)

    def _move(self, delta: int) -> None:
        if not self._filtered:
            return
        self._active = (self._active + delta) % len(self._filtered)
        self._list.setCurrentRow(self._active)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        shadow = QRectF(self._frame.geometry()).adjusted(-6, -4, 6, 10)
        painter.drawRoundedRect(shadow, 16, 16)
        painter.end()


def _fuzzy_score(command: Command, needle: str) -> int:
    """Score a command against a needle. Higher is better; 0 means no match."""
    haystack = command.search_text()
    if not needle:
        return 1

    title = command.title.lower()
    if title == needle:
        return 1000
    if title.startswith(needle):
        return 800
    if needle in title:
        return 600
    if needle in haystack:
        return 400

    # Subsequence match with a bonus for consecutive characters.
    position = 0
    score = 0
    previous = -2
    for char in needle:
        found = haystack.find(char, position)
        if found == -1:
            return 0
        score += 10
        if found == previous + 1:
            score += 12
        previous = found
        position = found + 1
    return score
