"""Reusable, theme-aware UI components.

Everything in this module is drawn from the active :class:`Palette`, so the
same components look correct in both light and dark mode without any
per-widget branching.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence

from PyQt5.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt5.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .context import current_theme
from .icons import draw_icon

__all__ = [
    "Card",
    "SectionLabel",
    "Divider",
    "IconButton",
    "NavItem",
    "SearchBox",
    "Sparkline",
    "RingGauge",
    "Meter",
    "ResponsiveGrid",
    "StatusDot",
    "SegmentedControl",
    "KeyValueRow",
    "EmptyState",
    "StatTile",
    "Toggle",
    "hline",
    "vline",
    "normalize_labels",
]


# ------------------------------------------------------------------ helpers

def _palette():
    theme = current_theme()
    if theme is not None:
        return theme.palette
    from .theme import DARK

    return DARK


def _metric_color(theme, token: str, fallback: str = "#6366F1") -> str:
    if theme is None:
        return fallback
    return getattr(theme.palette, token, fallback)


def hline(parent: Optional[QWidget] = None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("Divider")
    frame.setFrameShape(QFrame.HLine)
    return frame


def vline(parent: Optional[QWidget] = None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("VDivider")
    frame.setFrameShape(QFrame.VLine)
    return frame


def normalize_labels(root: QWidget) -> None:
    """Stop plain labels from stretching vertically inside their layouts.

    Word-wrapped labels keep their expanding policy (they need the room to
    show their text); every other label is pinned to its natural height so
    cards do not leave odd vertical gaps.  Labels that already carry an
    explicit vertical size (such as the chat bubble body) are left alone.
    """
    for label in root.findChildren(QLabel):
        policy = label.sizePolicy()
        if policy.verticalPolicy() in (QSizePolicy.Fixed, QSizePolicy.Maximum):
            continue
        if label.wordWrap():
            policy.setVerticalPolicy(QSizePolicy.MinimumExpanding)
        else:
            policy.setVerticalPolicy(QSizePolicy.Fixed)
        label.setSizePolicy(policy)


# ------------------------------------------------------------------ surfaces

class Card(QFrame):
    """A bordered surface used to group related content."""

    def __init__(self, parent: Optional[QWidget] = None, flat: bool = False, sunken: bool = False) -> None:
        super().__init__(parent)
        if sunken:
            self.setObjectName("CardSunken")
        elif flat:
            self.setObjectName("CardFlat")
        else:
            self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)


class SectionLabel(QLabel):
    """Small uppercase eyebrow label used above card groups."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("SectionLabel")


class Divider(QFrame):
    """Thin horizontal rule."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFrameShape(QFrame.HLine)


# ------------------------------------------------------------------ buttons

class IconButton(QPushButton):
    """A square, icon-only button. The icon is painted over the QSS chrome."""

    def __init__(
        self,
        icon: str = "",
        parent: Optional[QWidget] = None,
        tooltip: str = "",
        size: int = 30,
        color: Optional[str] = None,
        icon_scale: float = 0.54,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon
        self.icon_color = color
        self.icon_scale = icon_scale
        self.setObjectName("IconButton")
        self.setText("")
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        self.setFixedSize(size, size)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon(self, icon: str) -> None:
        self.icon_name = icon
        self.update()

    def set_icon_color(self, color: Optional[str]) -> None:
        self.icon_color = color
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.icon_name:
            return
        palette = _palette()
        color = self.icon_color
        if color is None:
            if not self.isEnabled():
                color = palette.text_faint
            elif self.underMouse():
                color = palette.text
            else:
                color = palette.text_muted
        side = min(self.width(), self.height()) * self.icon_scale
        rect = QRectF(
            (self.width() - side) / 2.0,
            (self.height() - side) / 2.0,
            side,
            side,
        )
        painter = QPainter(self)
        draw_icon(painter, self.icon_name, rect, color, 1.7)
        painter.end()


class NavItem(QPushButton):
    """Sidebar navigation entry: a drawn icon plus a label."""

    def __init__(
        self,
        text: str,
        icon: str = "",
        parent: Optional[QWidget] = None,
        badge: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon
        self.setObjectName("NavItem")
        self.setText("")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(38)
        self.setLayoutDirection(Qt.LeftToRight)
        self._badge = badge
        self._label = text
        self.setToolTip(text)

    def set_badge(self, badge: Optional[str]) -> None:
        self._badge = badge
        self.update()

    def set_label(self, label: str) -> None:
        """Update the visible text (used by the compact sidebar rail)."""
        self._label = label
        self.setText(label)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        palette = _palette()
        if self.isChecked():
            color = palette.accent
        elif not self.isEnabled():
            color = palette.text_faint
        elif self.underMouse():
            color = palette.text
        else:
            color = palette.text_muted

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        side = 17.0

        if self._label:
            icon_rect = QRectF(15, (self.height() - side) / 2.0, side, side)
            draw_icon(painter, self.icon_name, icon_rect, color, 1.6)
            font = painter.font()
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            text_rect = QRectF(46, 0, max(0, self.width() - 58), self.height())
            painter.setPen(QColor(palette.text if (self.isChecked() or self.underMouse()) else palette.text_muted))
            painter.drawText(
                text_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                metrics.elidedText(self._label, Qt.ElideRight, int(text_rect.width())),
            )
        elif self.icon_name:
            icon_rect = QRectF(
                (self.width() - side) / 2.0,
                (self.height() - side) / 2.0,
                side,
                side,
            )
            draw_icon(painter, self.icon_name, icon_rect, color, 1.6)
        painter.end()
        if self._badge:
            font = QFont(self.font())
            font.setPointSize(max(7, font.pointSize() - 2))
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(self._badge) + 12
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            rect = QRectF(self.width() - width - 12, (self.height() - 18) / 2.0, width, 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(palette.accent_soft))
            painter.drawRoundedRect(rect, 9, 9)
            painter.setPen(QColor(palette.accent_text))
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self._badge)
            painter.end()


class SearchBox(QLineEdit):
    """A rounded search input with a drawn magnifier glyph."""

    def __init__(self, placeholder: str = "Search…", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._icon = "search"

    def set_icon(self, icon: str) -> None:
        self._icon = icon
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        palette = _palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        side = 15.0
        rect = QRectF(11, (self.height() - side) / 2.0, side, side)
        draw_icon(painter, self._icon, rect, palette.text_faint, 1.6)
        painter.end()


# ------------------------------------------------------------------ charts

class Sparkline(QWidget):
    """A compact line chart used for latency / throughput trends."""

    def __init__(self, parent: Optional[QWidget] = None, height: int = 56, color: Optional[str] = None) -> None:
        super().__init__(parent)
        self._values: List[float] = []
        self._color = color
        self._max_points = 80
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_color(self, color: Optional[str]) -> None:
        self._color = color
        self.update()

    def set_values(self, values: Iterable[float]) -> None:
        self._values = [float(v) for v in values][-self._max_points:]
        self.update()

    def append(self, value: float) -> None:
        self._values.append(float(value))
        if len(self._values) > self._max_points:
            del self._values[0]
        self.update()

    def clear(self) -> None:
        self._values.clear()
        self.update()

    def _resolve_color(self) -> str:
        if self._color:
            return self._color
        palette = _palette()
        return palette.accent

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        palette = _palette()
        rect = QRectF(self.rect()).adjusted(1, 2, -1, -2)

        # Baseline
        pen = QPen(QColor(palette.border))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))

        if len(self._values) < 2:
            painter.setPen(QColor(palette.text_faint))
            painter.drawText(rect, Qt.AlignCenter, "Collecting samples…")
            painter.end()
            return

        values = self._values
        lo = min(values)
        hi = max(values)
        if math.isclose(hi, lo):
            hi = lo + 1.0
        span = hi - lo
        # Keep the trace away from the very top/bottom edge.
        lo -= span * 0.12
        hi += span * 0.12
        span = hi - lo

        step = rect.width() / (len(values) - 1)
        points = [
            QPointF(rect.left() + i * step, rect.bottom() - ((v - lo) / span) * rect.height())
            for i, v in enumerate(values)
        ]

        color = QColor(self._resolve_color())

        # Area fill
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 90))
        fill.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        area = QPainterPath()
        area.moveTo(points[0].x(), rect.bottom())
        for point in points:
            area.lineTo(point)
        area.lineTo(points[-1].x(), rect.bottom())
        area.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawPath(area)

        # Line
        pen = QPen(color)
        pen.setWidthF(1.9)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(*points)

        # Head dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(points[-1], 3.0, 3.0)
        painter.end()


class RingGauge(QWidget):
    """A circular progress gauge with a centred value label."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        size: int = 96,
        thickness: int = 8,
        caption: str = "",
    ) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._caption = caption
        self._size = size
        self._thickness = thickness
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_value(self, value: float) -> None:
        value = max(0.0, min(100.0, float(value)))
        if abs(value - self._value) < 0.05:
            return
        self._value = value
        self.update()

    def set_caption(self, caption: str) -> None:
        self._caption = caption
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        palette = _palette()
        inset = self._thickness / 2.0 + 1
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)

        pen = QPen(QColor(palette.surface_hi))
        pen.setWidthF(self._thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        if self._value > 0:
            color = QColor(palette.accent)
            if self._value >= 90:
                color = QColor(palette.danger)
            elif self._value >= 75:
                color = QColor(palette.warning)
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -int(self._value / 100.0 * 360 * 16))

        painter.setPen(QColor(palette.text))
        font = painter.font()
        font.setPointSizeF(max(8.0, self._size * 0.22))
        font.setBold(True)
        painter.setFont(font)
        if self._caption:
            value_rect = QRectF(
                self.rect().left(),
                self.rect().top() + self._size * 0.13,
                self.rect().width(),
                self._size * 0.34,
            )
            painter.drawText(value_rect, Qt.AlignCenter, f"{self._value:.0f}%")
            caption_font = painter.font()
            caption_font.setPointSizeF(max(6.5, self._size * 0.115))
            caption_font.setBold(False)
            painter.setFont(caption_font)
            painter.setPen(QColor(palette.text_muted))
            caption_rect = QRectF(
                self.rect().left(),
                self.rect().top() + self._size * 0.47,
                self.rect().width(),
                self._size * 0.22,
            )
            painter.drawText(caption_rect, Qt.AlignCenter, self._caption.upper())
        else:
            painter.drawText(
                QRectF(self.rect()),
                Qt.AlignCenter,
                f"{self._value:.0f}%",
            )
        painter.end()


class Meter(QWidget):
    """Labelled progress meter with value text."""

    def __init__(
        self,
        title: str = "",
        parent: Optional[QWidget] = None,
        color: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._title = QLabel(title)
        self._title.setObjectName("Muted")
        self._value = QLabel("—")
        self._value.setObjectName("MonoStrong")
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._value)
        layout.addLayout(header)

        self._bar = _Bar(color)
        layout.addWidget(self._bar)

    def set_value(self, percent: float, text: str = "") -> None:
        self._bar.set_value(percent)
        if text:
            self._value.setText(text)

    def set_color(self, color: Optional[str]) -> None:
        self._color = color
        self._bar.set_color(color)


class _Bar(QWidget):
    """Slim rounded progress bar."""

    def __init__(self, color: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._color = color
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_color(self, color: Optional[str]) -> None:
        self._color = color
        self.update()

    def set_value(self, percent: float) -> None:
        percent = max(0.0, min(100.0, float(percent)))
        if abs(percent - self._value) < 0.01:
            return
        self._value = percent
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        palette = _palette()
        radius = self.height() / 2.0
        rect = QRectF(self.rect())
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(palette.surface_hi))
        painter.drawRoundedRect(rect, radius, radius)
        if self._value > 0:
            color = QColor(self._color or palette.accent)
            filled = QRectF(rect.left(), rect.top(), rect.width() * self._value / 100.0, rect.height())
            painter.setBrush(color)
            painter.drawRoundedRect(filled, radius, radius)
        painter.end()


class StatusDot(QWidget):
    """A small coloured dot, optionally pulsing."""

    def __init__(self, parent: Optional[QWidget] = None, color: str = "#10B981", size: int = 8, pulse: bool = True) -> None:
        super().__init__(parent)
        self._color = color
        self._pulse = pulse
        self._phase = 0.0
        self.setFixedSize(size + 6, size + 6)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if pulse:
            self._timer.start(60)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def set_pulse(self, pulse: bool) -> None:
        self._pulse = pulse
        if pulse and not self._timer.isActive():
            self._timer.start(60)
        elif not pulse:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.08) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        color = QColor(self._color)
        if self._pulse:
            halo = QColor(color)
            halo.setAlpha(int(90 * (1.0 - self._phase)))
            painter.setPen(Qt.NoPen)
            painter.setBrush(halo)
            radius = 3.0 + 5.0 * self._phase
            painter.drawEllipse(center, radius, radius)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(center, 3.2, 3.2)
        painter.end()


# ------------------------------------------------------------------ controls

class Toggle(QAbstractButton):
    """A pill-shaped switch with an animated knob."""

    def __init__(self, parent: Optional[QWidget] = None, checked: bool = False) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(40, 22)
        self._position = 1.0 if checked else 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._on_value)
        self._animation.finished.connect(self.update)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()
        self.update()

    def _on_value(self, value) -> None:
        self._position = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        palette = _palette()

        track = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = track.height() / 2.0
        if self.isChecked():
            track_color = QColor(palette.accent)
        else:
            track_color = QColor(palette.surface_hi)

        painter.setPen(QPen(QColor(palette.border_strong if not self.isChecked() else palette.accent), 1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, radius, radius)

        knob_radius = track.height() / 2.0 - 3.0
        centre_x = track.left() + knob_radius + 3.0 + self._position * (
            track.width() - 2 * knob_radius - 6.0
        )
        centre_y = track.center().y()
        knob_color = QColor("#FFFFFF")
        painter.setPen(Qt.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(QPointF(centre_x, centre_y), knob_radius, knob_radius)
        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(40, 22)


class SegmentedControl(QWidget):
    """A compact segmented selector used for view switching."""

    changed = pyqtSignal(str)

    def __init__(self, items: Sequence[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._buttons: List[QPushButton] = []
        self._current = ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for item in items:
            button = QPushButton(item)
            button.setCheckable(True)
            button.setObjectName("Chip")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, value=item: self.select(value))
            layout.addWidget(button)
            self._buttons.append(button)
        if items:
            self.select(items[0])

    def select(self, value: str) -> None:
        self._current = value
        for button in self._buttons:
            button.setChecked(button.text() == value)
        self.changed.emit(value)

    def current(self) -> str:
        return self._current


class KeyValueRow(QWidget):
    """A two-column label/value row."""

    def __init__(self, key: str, value: str = "—", parent: Optional[QWidget] = None, mono: bool = False) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(12)
        self._key = QLabel(key)
        self._key.setObjectName("Muted")
        self._value = QLabel(value)
        self._value.setObjectName("MonoStrong" if mono else "")
        self._value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._value.setWordWrap(True)
        layout.addWidget(self._key)
        layout.addStretch()
        layout.addWidget(self._value, 0, Qt.AlignRight)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class EmptyState(QWidget):
    """Friendly placeholder shown when a panel has nothing to display."""

    def __init__(
        self,
        title: str = "Nothing here yet",
        message: str = "",
        icon: str = "info",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(24, 32, 24, 32)

        self._icon = IconButton(icon, self, "", 44, icon_scale=0.62)
        self._icon.setEnabled(False)
        layout.addWidget(self._icon, 0, Qt.AlignCenter)

        self._title = QLabel(title)
        self._title.setObjectName("H3")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)

        self._message = QLabel(message)
        self._message.setObjectName("Muted")
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

    def set_text(self, title: str, message: str = "") -> None:
        self._title.setText(title)
        self._message.setText(message)


class StatTile(Card):
    """A compact metric tile: label, value, caption and optional trend."""

    def __init__(
        self,
        label: str,
        value: str = "—",
        caption: str = "",
        icon: str = "",
        parent: Optional[QWidget] = None,
        accent: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(104)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._label = QLabel(label.upper())
        self._label.setObjectName("SectionLabel")
        header.addWidget(self._label)
        header.addStretch()
        self._icon = IconButton(icon, self, "", 26, icon_scale=0.56) if icon else None
        if self._icon is not None:
            self._icon.setEnabled(False)
            header.addWidget(self._icon)
        layout.addLayout(header)

        self._value = QLabel(value)
        self._value.setObjectName("Metric")
        layout.addWidget(self._value)

        self._caption = QLabel(caption)
        self._caption.setObjectName("Muted")
        self._caption.setWordWrap(True)
        layout.addWidget(self._caption)
        layout.addStretch()

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_caption(self, caption: str, tone: str = "") -> None:
        """Update the caption; ``tone`` may be ``success``/``warning``/``danger``/``info``."""
        self._caption.setText(caption)
        if tone:
            self._caption.setObjectName(tone.capitalize())
        else:
            self._caption.setObjectName("Muted")
        # Re-apply the object-name style by forcing a style re-polish.
        self._caption.style().unpolish(self._caption)
        self._caption.style().polish(self._caption)


class ResponsiveGrid(QWidget):
    """A grid that reflows its children based on the available width."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        spacing: int = 14,
        min_item_width: int = 250,
        max_columns: int = 4,
    ) -> None:
        super().__init__(parent)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
        self._items: List[QWidget] = []
        self._spacing = spacing
        self._min_item_width = max(120, min_item_width)
        self._max_columns = max(1, max_columns)
        self._columns = 0

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self._items.append(widget)
        self._relayout()
        return widget

    def clear(self) -> None:
        for item in self._items:
            self._layout.removeWidget(item)
            item.setParent(None)
        self._items.clear()
        self._relayout()

    def _column_count(self) -> int:
        width = max(1, self.width() - self._spacing)
        columns = int(width // (self._min_item_width + self._spacing))
        return max(1, min(self._max_columns, columns))

    def _relayout(self) -> None:
        columns = self._columns or self._column_count()
        for item in self._items:
            self._layout.removeWidget(item)
        for index, item in enumerate(self._items):
            row, column = divmod(index, columns)
            self._layout.addWidget(item, row, column)
        for column in range(columns):
            self._layout.setColumnStretch(column, 1)
        rows = (len(self._items) + columns - 1) // columns
        for row in range(rows + 1):
            self._layout.setRowStretch(row, 0)
        self._layout.setRowStretch(rows, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = self._column_count()
        if columns != self._columns:
            self._columns = columns
            self._relayout()
