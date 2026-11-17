"""Hand-drawn vector icon set.

Emoji and font glyphs render inconsistently across Linux installations, so
every icon in OmniHub is drawn with :class:`QPainter` primitives on a 24x24
grid.  That keeps stroke weight, colour and rendering perfectly consistent
in both light and dark themes and avoids depending on optional fonts.
"""

from __future__ import annotations

import math
from typing import Callable, Dict

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen

__all__ = ["draw_icon", "icon_names", "icon_pixmap"]

Painter = QPainter


# --------------------------------------------------------------- primitives

def _circle(p: Painter, cx: float, cy: float, r: float) -> None:
    p.drawEllipse(QPointF(cx, cy), r, r)


def _poly(p: Painter, points, close: bool = True) -> None:
    path = QPainterPath()
    path.moveTo(points[0][0], points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, y)
    if close:
        path.closeSubpath()
    p.drawPath(path)


def _rrect(p: Painter, x: float, y: float, w: float, h: float, r: float) -> None:
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _gear(p: Painter) -> None:
    path = QPainterPath()
    teeth = 8
    for i in range(teeth * 2):
        angle = math.pi * i / teeth - math.pi / 2
        radius = 9.6 if i % 2 == 0 else 7.4
        x = 12 + math.cos(angle) * radius
        y = 12 + math.sin(angle) * radius
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    _circle(p, 12, 12, 3.5)


def _sparkle(p: Painter) -> None:
    path = QPainterPath()
    path.moveTo(12, 2.5)
    path.lineTo(13.9, 10.1)
    path.lineTo(21.5, 12)
    path.lineTo(13.9, 13.9)
    path.lineTo(12, 21.5)
    path.lineTo(10.1, 13.9)
    path.lineTo(2.5, 12)
    path.lineTo(10.1, 10.1)
    path.closeSubpath()
    p.drawPath(path)


def _sun(p: Painter) -> None:
    _circle(p, 12, 12, 4.4)
    for i in range(8):
        angle = math.radians(i * 45)
        inner = 7.0
        outer = 9.8
        p.drawLine(
            QPointF(12 + math.cos(angle) * inner, 12 + math.sin(angle) * inner),
            QPointF(12 + math.cos(angle) * outer, 12 + math.sin(angle) * outer),
        )


def _moon(p: Painter) -> None:
    path = QPainterPath()
    path.moveTo(18.4, 15.6)
    path.cubicTo(16.9, 16.4, 15.1, 16.8, 13.4, 16.6)
    path.cubicTo(9.0, 16.2, 5.5, 12.5, 5.6, 8.1)
    path.cubicTo(5.6, 6.4, 6.0, 4.8, 6.8, 3.4)
    path.cubicTo(5.4, 5.0, 4.6, 7.0, 4.6, 9.2)
    path.cubicTo(4.6, 14.7, 9.1, 19.2, 14.6, 19.2)
    path.cubicTo(16.4, 19.2, 18.1, 18.6, 19.5, 17.6)
    path.cubicTo(19.1, 16.9, 18.8, 16.2, 18.4, 15.6)
    p.drawPath(path)


def _monitor(p: Painter) -> None:
    _rrect(p, 3.0, 4.5, 18.0, 12.5, 2.0)
    p.drawLine(QPointF(9.0, 20.0), QPointF(15.0, 20.0))
    p.drawLine(QPointF(12.0, 17.0), QPointF(12.0, 20.0))


def _gauge(p: Painter) -> None:
    p.drawArc(QRectF(4.0, 4.5, 16.0, 16.0), 180 * 16, 180 * 16)
    p.drawLine(QPointF(12.0, 12.5), QPointF(16.6, 8.4))
    _circle(p, 12, 12.5, 1.0)


def _gateway(p: Painter) -> None:
    _circle(p, 12, 4.8, 2.6)
    _circle(p, 4.8, 18.6, 2.6)
    _circle(p, 19.2, 18.6, 2.6)
    p.drawLine(QPointF(11.0, 7.2), QPointF(6.2, 16.4))
    p.drawLine(QPointF(13.0, 7.2), QPointF(17.8, 16.4))
    p.drawLine(QPointF(7.4, 18.6), QPointF(16.6, 18.6))


def _sliders(p: Painter) -> None:
    for y, knob in ((7.0, 15.0), (12.0, 9.0), (17.0, 13.5)):
        p.drawLine(QPointF(3.5, y), QPointF(20.5, y))
        _circle(p, knob, y, 2.3)


def _terminal(p: Painter) -> None:
    _poly(p, [(4.5, 7.0), (9.5, 12.0), (4.5, 17.0)], close=False)
    p.drawLine(QPointF(12.0, 17.0), QPointF(19.5, 17.0))


def _bolt(p: Painter) -> None:
    _poly(p, [(13.6, 2.0), (5.0, 13.6), (10.8, 13.6), (10.0, 22.0), (19.0, 10.2), (13.0, 10.2)])


def _layers(p: Painter) -> None:
    _poly(p, [(12, 3.0), (21.0, 7.8), (12, 12.6), (3.0, 7.8)])
    p.drawLine(QPointF(3.0, 12.0), QPointF(12.0, 16.8), )
    p.drawPolyline(QPointF(3.0, 12.0), QPointF(12.0, 16.8), QPointF(21.0, 12.0))


def _activity(p: Painter) -> None:
    p.drawPolyline(
        QPointF(3.0, 12.5), QPointF(7.5, 12.5), QPointF(10.5, 5.0),
        QPointF(13.5, 19.0), QPointF(16.5, 12.5), QPointF(21.0, 12.5),
    )


def _clock(p: Painter) -> None:
    _circle(p, 12, 12, 8.4)
    p.drawPolyline(QPointF(12.0, 7.0), QPointF(12.0, 12.4), QPointF(16.0, 14.6))


def _alert(p: Painter) -> None:
    _poly(p, [(12.0, 3.4), (21.6, 20.0), (2.4, 20.0)])
    p.drawLine(QPointF(12.0, 9.4), QPointF(12.0, 14.0))
    _circle(p, 12.0, 17.0, 0.9)


def _info(p: Painter) -> None:
    _circle(p, 12, 12, 8.4)
    p.drawLine(QPointF(12.0, 11.0), QPointF(12.0, 16.4))
    _circle(p, 12.0, 7.9, 0.9)


def _refresh(p: Painter) -> None:
    p.drawArc(QRectF(4.2, 4.2, 15.6, 15.6), 55 * 16, 275 * 16)
    _poly(p, [(18.6, 3.2), (19.4, 8.4), (14.2, 8.0)], close=False)


def _external(p: Painter) -> None:
    p.drawPolyline(QPointF(13.0, 4.5), QPointF(19.5, 4.5), QPointF(19.5, 11.0))
    p.drawLine(QPointF(19.5, 4.5), QPointF(10.5, 13.5))
    p.drawPolyline(QPointF(9.5, 5.5), QPointF(4.5, 5.5), QPointF(4.5, 19.5), QPointF(18.5, 19.5), QPointF(18.5, 14.5))


def _copy(p: Painter) -> None:
    _rrect(p, 8.5, 8.5, 11.0, 11.0, 2.0)
    p.drawPolyline(QPointF(15.5, 5.5), QPointF(5.0, 5.5), QPointF(5.0, 16.0))


def _trash(p: Painter) -> None:
    p.drawLine(QPointF(4.5, 6.8), QPointF(19.5, 6.8))
    p.drawPolyline(QPointF(9.5, 6.5), QPointF(9.5, 4.5), QPointF(14.5, 4.5), QPointF(14.5, 6.5))
    p.drawPolyline(QPointF(6.5, 6.8), QPointF(7.4, 19.5), QPointF(16.6, 19.5), QPointF(17.5, 6.8))
    p.drawLine(QPointF(10.4, 10.0), QPointF(10.7, 16.4))
    p.drawLine(QPointF(13.6, 10.0), QPointF(13.3, 16.4))


def _download(p: Painter) -> None:
    p.drawLine(QPointF(12.0, 3.5), QPointF(12.0, 14.5))
    p.drawPolyline(QPointF(7.0, 10.0), QPointF(12.0, 15.0), QPointF(17.0, 10.0))
    p.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 19.5))


def _save(p: Painter) -> None:
    p.drawPolyline(QPointF(4.5, 5.5), QPointF(16.5, 5.5), QPointF(19.5, 8.5), QPointF(19.5, 19.5), QPointF(4.5, 19.5))
    p.drawPolyline(QPointF(8.0, 5.5), QPointF(8.0, 11.0), QPointF(15.0, 11.0), QPointF(15.0, 5.5))
    _rrect(p, 8.0, 13.5, 8.0, 6.0, 1.2)


def _key(p: Painter) -> None:
    _circle(p, 7.8, 12.0, 4.0)
    p.drawLine(QPointF(11.0, 12.0), QPointF(20.0, 12.0))
    p.drawLine(QPointF(16.6, 12.0), QPointF(16.6, 15.4))
    p.drawLine(QPointF(19.0, 12.0), QPointF(19.0, 14.6))


def _shield(p: Painter) -> None:
    path = QPainterPath()
    path.moveTo(12.0, 3.2)
    path.lineTo(20.0, 6.2)
    path.lineTo(20.0, 12.0)
    path.cubicTo(20.0, 16.6, 16.6, 19.6, 12.0, 21.0)
    path.cubicTo(7.4, 19.6, 4.0, 16.6, 4.0, 12.0)
    path.lineTo(4.0, 6.2)
    path.closeSubpath()
    p.drawPath(path)


def _lock(p: Painter) -> None:
    _rrect(p, 5.0, 10.5, 14.0, 10.0, 2.0)
    p.drawArc(QRectF(8.0, 4.0, 8.0, 10.0), 0 * 16, 180 * 16)


def _eye(p: Painter) -> None:
    path = QPainterPath()
    path.moveTo(2.8, 12.0)
    path.cubicTo(6.0, 6.6, 18.0, 6.6, 21.2, 12.0)
    path.cubicTo(18.0, 17.4, 6.0, 17.4, 2.8, 12.0)
    p.drawPath(path)
    _circle(p, 12, 12, 3.0)


def _search(p: Painter) -> None:
    _circle(p, 10.5, 10.5, 6.0)
    p.drawLine(QPointF(15.0, 15.0), QPointF(20.0, 20.0))


def _play(p: Painter) -> None:
    _poly(p, [(8.0, 5.0), (19.0, 12.0), (8.0, 19.0)])


def _stop(p: Painter) -> None:
    _rrect(p, 7.0, 7.0, 10.0, 10.0, 1.8)


def _pause(p: Painter) -> None:
    p.drawLine(QPointF(9.5, 6.0), QPointF(9.5, 18.0))
    p.drawLine(QPointF(14.5, 6.0), QPointF(14.5, 18.0))


def _check(p: Painter) -> None:
    p.drawPolyline(QPointF(5.0, 12.6), QPointF(9.8, 17.4), QPointF(19.0, 6.8))


def _close(p: Painter) -> None:
    p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
    p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))


def _plus(p: Painter) -> None:
    p.drawLine(QPointF(12.0, 5.5), QPointF(12.0, 18.5))
    p.drawLine(QPointF(5.5, 12.0), QPointF(18.5, 12.0))


def _minus(p: Painter) -> None:
    p.drawLine(QPointF(5.5, 12.0), QPointF(18.5, 12.0))


def _chevron_down(p: Painter) -> None:
    p.drawPolyline(QPointF(6.0, 9.5), QPointF(12.0, 15.5), QPointF(18.0, 9.5))


def _chevron_right(p: Painter) -> None:
    p.drawPolyline(QPointF(9.5, 6.0), QPointF(15.5, 12.0), QPointF(9.5, 18.0))


def _chevron_left(p: Painter) -> None:
    p.drawPolyline(QPointF(14.5, 6.0), QPointF(8.5, 12.0), QPointF(14.5, 18.0))


def _filter(p: Painter) -> None:
    p.drawPolyline(QPointF(4.0, 6.0), QPointF(20.0, 6.0), QPointF(13.5, 13.0), QPointF(13.5, 19.0), QPointF(10.5, 17.0), QPointF(10.5, 13.0), QPointF(4.0, 6.0))


def _history(p: Painter) -> None:
    p.drawArc(QRectF(4.0, 4.0, 16.0, 16.0), 40 * 16, 290 * 16)
    _poly(p, [(19.2, 3.6), (19.8, 8.4), (15.0, 7.4)], close=False)
    p.drawPolyline(QPointF(12.0, 8.0), QPointF(12.0, 12.6), QPointF(15.6, 14.6))


def _cpu(p: Painter) -> None:
    _rrect(p, 6.5, 6.5, 11.0, 11.0, 1.8)
    _rrect(p, 9.5, 9.5, 5.0, 5.0, 1.0)
    for offset in (9.0, 12.0, 15.0):
        p.drawLine(QPointF(offset, 3.0), QPointF(offset, 6.5))
        p.drawLine(QPointF(offset, 17.5), QPointF(offset, 21.0))
        p.drawLine(QPointF(3.0, offset), QPointF(6.5, offset))
        p.drawLine(QPointF(17.5, offset), QPointF(21.0, offset))


def _database(p: Painter) -> None:
    p.drawEllipse(QRectF(4.0, 3.0, 16.0, 6.0))
    p.drawArc(QRectF(4.0, 8.0, 16.0, 6.0), 180 * 16, 180 * 16)
    p.drawArc(QRectF(4.0, 13.0, 16.0, 6.0), 180 * 16, 180 * 16)


def _hash(p: Painter) -> None:
    p.drawLine(QPointF(9.5, 4.0), QPointF(7.5, 20.0))
    p.drawLine(QPointF(16.5, 4.0), QPointF(14.5, 20.0))
    p.drawLine(QPointF(4.0, 9.0), QPointF(20.0, 9.0))
    p.drawLine(QPointF(3.5, 15.0), QPointF(19.5, 15.0))


def _wand(p: Painter) -> None:
    p.drawLine(QPointF(5.0, 19.0), QPointF(16.0, 8.0))
    _poly(p, [(14.0, 4.0), (15.4, 7.2), (18.6, 8.6), (15.4, 10.0), (14.0, 13.2), (12.6, 10.0), (9.4, 8.6), (12.6, 7.2)])
    p.drawLine(QPointF(6.0, 4.0), QPointF(6.0, 6.4))
    p.drawLine(QPointF(4.8, 5.2), QPointF(7.2, 5.2))


def _globe(p: Painter) -> None:
    _circle(p, 12, 12, 8.4)
    p.drawLine(QPointF(3.6, 12.0), QPointF(20.4, 12.0))
    p.drawArc(QRectF(7.6, 3.6, 8.8, 16.8), 0 * 16, 360 * 16)


def _document(p: Painter) -> None:
    p.drawPolyline(QPointF(6.0, 3.5), QPointF(14.0, 3.5), QPointF(18.5, 8.0), QPointF(18.5, 20.5), QPointF(6.0, 20.5))
    p.drawPolyline(QPointF(14.0, 3.5), QPointF(14.0, 8.0), QPointF(18.5, 8.0))
    p.drawLine(QPointF(9.0, 12.5), QPointF(16.0, 12.5))
    p.drawLine(QPointF(9.0, 16.0), QPointF(16.0, 16.0))


def _arrow_right(p: Painter) -> None:
    p.drawLine(QPointF(4.5, 12.0), QPointF(18.5, 12.0))
    p.drawPolyline(QPointF(13.5, 7.0), QPointF(18.5, 12.0), QPointF(13.5, 17.0))


def _arrow_up(p: Painter) -> None:
    p.drawLine(QPointF(12.0, 19.5), QPointF(12.0, 5.5))
    p.drawPolyline(QPointF(7.0, 10.5), QPointF(12.0, 5.5), QPointF(17.0, 10.5))


def _minimize(p: Painter) -> None:
    p.drawLine(QPointF(5.0, 12.0), QPointF(19.0, 12.0))


def _maximize(p: Painter) -> None:
    _rrect(p, 5.0, 5.0, 14.0, 14.0, 2.0)


def _sparkles(p: Painter) -> None:
    _sparkle(p)
    _poly(p, [(19.0, 15.5), (20.2, 18.3), (23.0, 19.5), (20.2, 20.7), (19.0, 23.5), (17.8, 20.7), (15.0, 19.5), (17.8, 18.3)])


def _webhook(p: Painter) -> None:
    _circle(p, 8.5, 7.5, 3.2)
    _circle(p, 15.5, 7.5, 3.2)
    p.drawArc(QRectF(5.5, 11.0, 13.0, 11.0), 180 * 16, 180 * 16)
    p.drawLine(QPointF(12.0, 17.0), QPointF(12.0, 21.0))


_ICONS: Dict[str, Callable[[Painter], None]] = {
    "alert": _alert,
    "arrow-right": _arrow_right,
    "arrow-up": _arrow_up,
    "bolt": _bolt,
    "check": _check,
    "chevron-down": _chevron_down,
    "chevron-left": _chevron_left,
    "chevron-right": _chevron_right,
    "clock": _clock,
    "close": _close,
    "copy": _copy,
    "cpu": _cpu,
    "database": _database,
    "document": _document,
    "download": _download,
    "eye": _eye,
    "filter": _filter,
    "gauge": _gauge,
    "gateway": _gateway,
    "globe": _globe,
    "hash": _hash,
    "history": _history,
    "info": _info,
    "key": _key,
    "layers": _layers,
    "lock": _lock,
    "maximize": _maximize,
    "minimize": _minimize,
    "minus": _minus,
    "monitor": _monitor,
    "moon": _moon,
    "pause": _pause,
    "play": _play,
    "plus": _plus,
    "refresh": _refresh,
    "save": _save,
    "search": _search,
    "shield": _shield,
    "sliders": _sliders,
    "sparkle": _sparkle,
    "sparkles": _sparkles,
    "stop": _stop,
    "sun": _sun,
    "terminal": _terminal,
    "trash": _trash,
    "wand": _wand,
    "webhook": _webhook,
    "activity": _activity,
}


def icon_names() -> list:
    """Return every available icon name."""
    return sorted(_ICONS.keys())


def draw_icon(
    painter: Painter,
    name: str,
    rect,
    color: str = "#FFFFFF",
    width: float = 1.7,
) -> bool:
    """Draw ``name`` inside ``rect`` (a QRect or QRectF). Returns success."""
    fn = _ICONS.get(name)
    if fn is None:
        return False
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    size = min(rect.width(), rect.height())
    scale = size / 24.0
    painter.translate(rect.x(), rect.y())
    painter.scale(scale, scale)
    try:
        fn(painter)
    finally:
        painter.restore()
    return True


def icon_pixmap(name: str, size: int = 20, color: str = "#FFFFFF", width: float = 1.7):
    """Render an icon into a QPixmap (useful for window/taskbar use)."""
    from PyQt5.QtGui import QPixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    draw_icon(painter, name, pixmap.rect(), color, width)
    painter.end()
    return pixmap
