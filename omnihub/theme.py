"""Theme engine: palettes, accents, metrics and the global QSS builder.

The whole application is styled from a single generated stylesheet driven by
a :class:`Palette` value object.  Switching between light and dark is
therefore a matter of swapping the palette and re-applying the stylesheet —
there is no per-widget theming scattered through the code base.

Design language
----------------
* Minimal — hairlines instead of heavy borders, generous whitespace, no
  decorative noise.
* Premium — restrained accent usage, soft elevation, precise typography.
* Classic — a clear typographic hierarchy and conventional control shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from string import Template
from typing import Dict, List, Optional, Tuple

__all__ = [
    "Palette",
    "Accent",
    "ACCENTS",
    "ThemeManager",
    "build_stylesheet",
    "DARK",
    "LIGHT",
]

FONT_STACK = "'Inter', 'Inter Display', 'Noto Sans', 'DejaVu Sans', 'Segoe UI', sans-serif"
MONO_STACK = "'JetBrains Mono', 'Noto Sans Mono', 'DejaVu Sans Mono', 'Cascadia Code', monospace"


# --------------------------------------------------------------------- accents

@dataclass(frozen=True)
class Accent:
    """A named accent colourway."""

    key: str
    label: str
    primary: str
    secondary: str
    dark_primary: str
    dark_secondary: str

    def resolve(self, dark: bool) -> Tuple[str, str]:
        return (self.dark_primary, self.dark_secondary) if dark else (self.primary, self.secondary)


ACCENTS: Dict[str, Accent] = {
    "indigo": Accent("indigo", "Indigo", "#4F46E5", "#0891B2", "#6366F1", "#22D3EE"),
    "violet": Accent("violet", "Violet", "#7C3AED", "#C026D3", "#8B5CF6", "#E879F9"),
    "cyan": Accent("cyan", "Cyan", "#0E7490", "#4F46E5", "#06B6D4", "#6366F1"),
    "emerald": Accent("emerald", "Emerald", "#047857", "#0F766E", "#10B981", "#14B8A6"),
    "rose": Accent("rose", "Rose", "#BE123C", "#A21CAF", "#F43F5E", "#D946EF"),
    "amber": Accent("amber", "Amber", "#B45309", "#B91C1C", "#F59E0B", "#EF4444"),
}


# --------------------------------------------------------------------- palette

@dataclass
class Palette:
    """Every colour token the application needs."""

    name: str = "dark"

    bg: str = "#0A0C11"
    sidebar: str = "#0C0F16"
    surface: str = "#11141C"
    surface_alt: str = "#161A24"
    surface_hi: str = "#1C2130"
    surface_sunken: str = "#080A0F"

    border: str = "#1F2432"
    border_strong: str = "#2C3444"

    text: str = "#E9EDF5"
    text_muted: str = "#99A3B7"
    text_faint: str = "#626C7F"
    text_inverse: str = "#0B0E14"

    accent: str = "#6366F1"
    accent_hover: str = "#7C7FF3"
    accent_press: str = "#4F46E5"
    accent_soft: str = "rgba(99, 102, 241, 0.16)"
    accent_border: str = "rgba(99, 102, 241, 0.42)"
    accent_text: str = "#A5B4FC"

    accent2: str = "#22D3EE"
    accent2_soft: str = "rgba(34, 211, 238, 0.14)"

    success: str = "#34D399"
    success_soft: str = "rgba(52, 211, 153, 0.14)"
    warning: str = "#FBBF24"
    warning_soft: str = "rgba(251, 191, 36, 0.14)"
    danger: str = "#F87171"
    danger_soft: str = "rgba(248, 113, 113, 0.14)"
    info: str = "#38BDF8"
    info_soft: str = "rgba(56, 189, 248, 0.14)"

    selection: str = "#4F46E5"
    selection_text: str = "#FFFFFF"

    hover: str = "rgba(255, 255, 255, 0.05)"
    pressed: str = "rgba(255, 255, 255, 0.09)"

    shadow: str = "rgba(0, 0, 0, 0.45)"
    focus_ring: str = "#6366F1"

    def tinted(self, accent: Accent, dark: bool) -> "Palette":
        """Return a copy of this palette with the accent colours applied."""
        primary, secondary = accent.resolve(dark)
        return replace(
            self,
            accent=primary,
            accent_hover=_lighten(primary, 0.14) if dark else _lighten(primary, 0.10),
            accent_press=_darken(primary, 0.12) if dark else _darken(primary, 0.10),
            accent_soft=_rgba(primary, 0.16),
            accent_border=_rgba(primary, 0.42),
            accent_text=_lighten(primary, 0.55) if dark else _darken(primary, 0.25),
            accent2=secondary,
            accent2_soft=_rgba(secondary, 0.14),
            focus_ring=primary,
        )


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except (ValueError, IndexError):
        return 0, 0, 0


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def _lighten(hex_color: str, amount: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_color: str, amount: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02X}{g:02X}{b:02X}"


def _base_palette(dark: bool) -> Palette:
    """Return the unmodified dark or light palette."""
    if dark:
        return Palette(name="dark")
    return Palette(
        name="light",
        bg="#F2F4F8",
        sidebar="#FFFFFF",
        surface="#FFFFFF",
        surface_alt="#F7F9FC",
        surface_hi="#EDF1F7",
        surface_sunken="#F1F4F9",
        border="#E1E6EF",
        border_strong="#CBD3E0",
        text="#0F1729",
        text_muted="#59637A",
        text_faint="#8A94A8",
        text_inverse="#FFFFFF",
        accent="#4F46E5",
        accent_hover="#4338CA",
        accent_press="#3730A3",
        accent_soft="rgba(79, 70, 229, 0.10)",
        accent_border="rgba(79, 70, 229, 0.34)",
        accent_text="#4338CA",
        accent2="#0891B2",
        accent2_soft="rgba(8, 145, 178, 0.10)",
        success="#059669",
        success_soft="rgba(5, 150, 105, 0.10)",
        warning="#B45309",
        warning_soft="rgba(180, 83, 9, 0.10)",
        danger="#DC2626",
        danger_soft="rgba(220, 38, 38, 0.10)",
        info="#0284C7",
        info_soft="rgba(2, 132, 199, 0.10)",
        selection="#4F46E5",
        selection_text="#FFFFFF",
        hover="rgba(15, 23, 41, 0.045)",
        pressed="rgba(15, 23, 41, 0.085)",
        shadow="rgba(15, 23, 41, 0.14)",
        focus_ring="#4F46E5",
    )


DARK = _base_palette(True)
LIGHT = _base_palette(False)


# --------------------------------------------------------------------- metrics

@dataclass
class Metrics:
    """Density / scale knobs that feed the stylesheet."""

    font_scale: float = 1.0
    compact: bool = False

    def px(self, base: float) -> int:
        return max(8, int(round(base * self.font_scale)))


# --------------------------------------------------------------------- stylesheet

_QSS = Template(
    """
/* ============================ base ============================ */
QWidget {
    color: ${text};
    font-family: ${font};
    font-size: ${fs_body}px;
}
QMainWindow, QDialog, #Root {
    background-color: ${bg};
}
QWidget:disabled {
    color: ${text_faint};
}
QToolTip {
    background-color: ${surface_hi};
    color: ${text};
    border: 1px solid ${border_strong};
    border-radius: 6px;
    padding: 5px 9px;
    font-size: ${fs_small}px;
}

/* ============================ labels ============================ */
QLabel {
    background: transparent;
    color: ${text};
}
QLabel#H1 {
    font-size: ${fs_h1}px;
    font-weight: 700;
    letter-spacing: -0.4px;
}
QLabel#H2 {
    font-size: ${fs_h2}px;
    font-weight: 650;
    letter-spacing: -0.2px;
}
QLabel#H3 {
    font-size: ${fs_h3}px;
    font-weight: 600;
}
QLabel#SectionLabel {
    color: ${text_faint};
    font-size: ${fs_micro}px;
    font-weight: 700;
    letter-spacing: 1.1px;
    text-transform: uppercase;
}
QLabel#Muted {
    color: ${text_muted};
    font-size: ${fs_small}px;
}
QLabel#Faint {
    color: ${text_faint};
    font-size: ${fs_small}px;
}
QLabel#Metric {
    font-size: ${fs_metric}px;
    font-weight: 700;
    letter-spacing: -0.6px;
}
QLabel#MetricSmall {
    font-size: ${fs_h3}px;
    font-weight: 650;
}
QLabel#Mono {
    font-family: ${mono};
    font-size: ${fs_small}px;
    color: ${text_muted};
}
QLabel#MonoStrong {
    font-family: ${mono};
    font-size: ${fs_small}px;
    color: ${text};
}
QLabel#Success { color: ${success}; font-size: ${fs_small}px; font-weight: 600; }
QLabel#Warning { color: ${warning}; font-size: ${fs_small}px; font-weight: 600; }
QLabel#Danger  { color: ${danger};  font-size: ${fs_small}px; font-weight: 600; }
QLabel#Info    { color: ${info};    font-size: ${fs_small}px; font-weight: 600; }
QLabel#Accent  { color: ${accent_text}; font-size: ${fs_small}px; font-weight: 600; }
QLabel#Badge {
    color: ${accent_text};
    background-color: ${accent_soft};
    border: 1px solid ${accent_border};
    border-radius: ${radius_pill}px;
    padding: 2px 9px;
    font-size: ${fs_micro}px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#BadgeSuccess {
    color: ${success}; background-color: ${success_soft};
    border: 1px solid ${success}; border-radius: ${radius_pill}px;
    padding: 2px 9px; font-size: ${fs_micro}px; font-weight: 700;
}
QLabel#BadgeWarning {
    color: ${warning}; background-color: ${warning_soft};
    border: 1px solid ${warning}; border-radius: ${radius_pill}px;
    padding: 2px 9px; font-size: ${fs_micro}px; font-weight: 700;
}
QLabel#BadgeDanger {
    color: ${danger}; background-color: ${danger_soft};
    border: 1px solid ${danger}; border-radius: ${radius_pill}px;
    padding: 2px 9px; font-size: ${fs_micro}px; font-weight: 700;
}

/* ============================ frames ============================ */
QFrame#Card {
    background-color: ${surface};
    border: 1px solid ${border};
    border-radius: ${radius}px;
}
QFrame#CardFlat {
    background-color: ${surface};
    border: 1px solid ${border};
    border-radius: ${radius}px;
}
QFrame#CardSunken {
    background-color: ${surface_sunken};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
}
QFrame#CardInteractive:hover {
    border: 1px solid ${border_strong};
    background-color: ${surface};
}
QFrame#Divider {
    background-color: ${border};
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QFrame#VDivider {
    background-color: ${border};
    border: none;
    max-width: 1px;
    min-width: 1px;
}
QFrame#Sidebar {
    background-color: ${sidebar};
    border-right: 1px solid ${border};
}
QFrame#TopBar {
    background-color: ${bg};
    border-bottom: 1px solid ${border};
}
QFrame#Hover {
    background-color: ${hover};
    border: none;
    border-radius: ${radius_sm}px;
}

/* ============================ buttons ============================ */
QPushButton {
    background-color: ${surface_alt};
    color: ${text};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    padding: ${pad_v}px ${pad_h}px;
    font-size: ${fs_body}px;
    font-weight: 550;
    min-height: ${btn_h}px;
}
QPushButton:hover {
    background-color: ${surface_hi};
    border-color: ${border_strong};
}
QPushButton:pressed {
    background-color: ${pressed};
}
QPushButton:focus {
    border-color: ${focus_ring};
}
QPushButton:disabled {
    background-color: ${surface_alt};
    color: ${text_faint};
    border-color: ${border};
}

QPushButton#Primary {
    background-color: ${accent};
    color: #FFFFFF;
    border: 1px solid ${accent};
    font-weight: 650;
}
QPushButton#Primary:hover {
    background-color: ${accent_hover};
    border-color: ${accent_hover};
}
QPushButton#Primary:pressed {
    background-color: ${accent_press};
}
QPushButton#Primary:disabled {
    background-color: ${accent_soft};
    color: ${text_faint};
    border-color: transparent;
}

QPushButton#Secondary {
    background-color: transparent;
    color: ${text_muted};
    border: 1px solid transparent;
}
QPushButton#Secondary:hover {
    background-color: ${hover};
    color: ${text};
    border-color: ${border};
}

QPushButton#Ghost {
    background-color: transparent;
    color: ${text_muted};
    border: 1px solid ${border};
}
QPushButton#Ghost:hover {
    background-color: ${surface_alt};
    color: ${text};
    border-color: ${border_strong};
}

QPushButton#Success {
    background-color: ${success_soft};
    color: ${success};
    border: 1px solid ${success};
}
QPushButton#Success:hover {
    background-color: ${success};
    color: #FFFFFF;
}
QPushButton#Success:disabled {
    background-color: ${surface_alt};
    color: ${text_faint};
    border-color: ${border};
}

QPushButton#Danger {
    background-color: ${danger_soft};
    color: ${danger};
    border: 1px solid ${danger};
}
QPushButton#Danger:hover {
    background-color: ${danger};
    color: #FFFFFF;
}
QPushButton#Danger:disabled {
    background-color: ${surface_alt};
    color: ${text_faint};
    border-color: ${border};
}

QPushButton#Warning {
    background-color: ${warning_soft};
    color: ${warning};
    border: 1px solid ${warning};
}
QPushButton#Warning:hover {
    background-color: ${warning};
    color: #0B0E14;
}
QPushButton#Warning:disabled {
    background-color: ${surface_alt};
    color: ${text_faint};
    border-color: ${border};
}

QPushButton#Ghost:disabled {
    background-color: transparent;
    color: ${text_faint};
    border-color: ${border};
}

QPushButton#Secondary:disabled {
    background-color: transparent;
    color: ${text_faint};
    border-color: transparent;
}

QPushButton#IconButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: ${radius_sm}px;
    padding: 0px;
    min-width: ${icon_btn}px;
    max-width: ${icon_btn}px;
    min-height: ${icon_btn}px;
    max-height: ${icon_btn}px;
}
QPushButton#IconButton:hover {
    background-color: ${hover};
    border-color: ${border};
}
QPushButton#IconButton:pressed {
    background-color: ${pressed};
}

/* ============================ navigation ============================ */
QPushButton#NavItem {
    background-color: transparent;
    color: ${text_muted};
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 0px 12px 0px 42px;
    font-size: ${fs_body}px;
    font-weight: 600;
    text-align: left;
    min-height: 0px;
}
QPushButton#NavItem:hover {
    background-color: ${hover};
    color: ${text};
}
QPushButton#NavItem:checked {
    background-color: ${accent_soft};
    color: ${accent_text};
    border-color: ${accent_border};
    font-weight: 650;
}

/* ============================ toggles ============================ */
QCheckBox#Toggle {
    spacing: 0px;
}
QCheckBox#Toggle::indicator {
    width: 38px;
    height: 21px;
    border-radius: 11px;
    border: 1px solid ${border_strong};
    background-color: ${surface_hi};
}
QCheckBox#Toggle::indicator:hover {
    border-color: ${accent};
}
QCheckBox#Toggle::indicator:checked {
    background-color: ${accent};
    border-color: ${accent};
}
QCheckBox#Toggle::indicator:disabled {
    background-color: ${surface};
    border-color: ${border};
}

QPushButton#Chip {
    background-color: ${surface_alt};
    color: ${text_muted};
    border: 1px solid ${border};
    border-radius: ${radius_pill}px;
    padding: 4px 12px;
    font-size: ${fs_small}px;
    font-weight: 550;
    min-height: 0px;
}
QPushButton#Chip:hover {
    color: ${text};
    border-color: ${accent_border};
    background-color: ${accent_soft};
}
QPushButton#Chip:checked {
    color: ${accent_text};
    border-color: ${accent};
    background-color: ${accent_soft};
}

/* ============================ inputs ============================ */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: ${surface_sunken};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    padding: ${pad_v}px ${pad_h}px;
    color: ${text};
    font-size: ${fs_body}px;
    selection-background-color: ${selection};
    selection-color: ${selection_text};
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: ${focus_ring};
    background-color: ${surface_alt};
}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QSpinBox:disabled, QComboBox:disabled {
    color: ${text_faint};
    background-color: ${surface};
}
QLineEdit#Search {
    border-radius: ${radius_pill}px;
    padding-left: 32px;
    background-color: ${surface_alt};
}
QLineEdit#Mono {
    font-family: ${mono};
    font-size: ${fs_small}px;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: ${surface};
    border: 1px solid ${border_strong};
    border-radius: ${radius_sm}px;
    selection-background-color: ${accent_soft};
    selection-color: ${text};
    outline: none;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 22px;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: ${surface_hi};
    border: none;
    width: 16px;
    border-radius: 3px;
}
QCheckBox, QRadioButton {
    spacing: 8px;
    color: ${text};
    font-size: ${fs_body}px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator {
    border: 1px solid ${border_strong};
    border-radius: 4px;
    background-color: ${surface_sunken};
    image: url(${check_unchecked});
}
QCheckBox::indicator:hover {
    border-color: ${accent};
}
QCheckBox::indicator:checked {
    background-color: ${accent};
    border-color: ${accent};
    image: url(${check_checked});
}
QRadioButton::indicator {
    border: 1px solid ${border_strong};
    border-radius: 8px;
    background-color: ${surface_sunken};
}
QRadioButton::indicator:checked {
    border: 5px solid ${accent};
    background-color: ${surface_sunken};
}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    border-color: ${border};
    background-color: ${surface};
}

/* ============================ scrollbars ============================ */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px 2px 2px 0px;
}
QScrollBar::handle:vertical {
    background: ${border_strong};
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: ${text_faint};
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0px 2px 2px 2px;
}
QScrollBar::handle:horizontal {
    background: ${border_strong};
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: ${text_faint};
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
    border: none;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ============================ tables & lists ============================ */
QTableWidget, QTableView, QListWidget, QTreeWidget {
    background-color: ${surface};
    alternate-background-color: ${surface_alt};
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    gridline-color: ${border};
    outline: none;
    selection-background-color: ${accent_soft};
    selection-color: ${text};
}
QTableWidget::item, QTableView::item {
    padding: 7px 8px;
    border: none;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: ${accent_soft};
}
QHeaderView::section {
    background-color: ${surface_alt};
    color: ${text_faint};
    border: none;
    border-bottom: 1px solid ${border};
    padding: 8px 8px;
    font-size: ${fs_micro}px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
QTableCornerButton::section {
    background-color: ${surface_alt};
    border: none;
}

/* ============================ tabs ============================ */
QTabWidget::pane {
    border: 1px solid ${border};
    border-radius: ${radius_sm}px;
    background-color: ${surface};
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: ${text_muted};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    margin-right: 2px;
    font-size: ${fs_small}px;
    font-weight: 600;
}
QTabBar::tab:hover {
    color: ${text};
}
QTabBar::tab:selected {
    color: ${accent_text};
    border-bottom-color: ${accent};
}

/* ============================ misc ============================ */
QProgressBar {
    background-color: ${surface_sunken};
    border: none;
    border-radius: ${radius_xs}px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: ${accent};
    border-radius: ${radius_xs}px;
}
QSplitter::handle {
    background-color: ${border};
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QMenu {
    background-color: ${surface};
    border: 1px solid ${border_strong};
    border-radius: ${radius_sm}px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 26px 7px 14px;
    border-radius: 5px;
    color: ${text};
    font-size: ${fs_small}px;
}
QMenu::item:selected {
    background-color: ${accent_soft};
    color: ${text};
}
QMenu::separator {
    height: 1px;
    background: ${border};
    margin: 5px 8px;
}
QStatusBar {
    background-color: ${surface_alt};
    border-top: 1px solid ${border};
    color: ${text_muted};
}
QStatusBar::item { border: none; }
QMessageBox {
    background-color: ${surface};
}
QMessageBox QLabel {
    color: ${text};
    font-size: ${fs_body}px;
}
QCalendarWidget QToolButton { color: ${text}; background: transparent; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid ${text_muted};
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid ${text_muted};
}
"""
)


def _checkbox_assets(palette: Palette) -> Tuple[str, str]:
    """Write (and cache) the checkmark SVGs used by the stylesheet.

    Qt's stylesheet language cannot draw a tick, so the indicator is painted
    from a tiny generated SVG that matches the active palette.
    """
    from .paths import CACHE_DIR

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ("", "")

    stamp = f"{palette.name}-{palette.accent.lstrip('#')}-{palette.border_strong.lstrip('#')}"
    checked_path = CACHE_DIR / f"checkbox-checked-{stamp}.svg"
    unchecked_path = CACHE_DIR / f"checkbox-unchecked-{stamp}.svg"

    checked_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        f'<rect x="0.5" y="0.5" width="15" height="15" rx="4" fill="{palette.accent}"/>'
        '<path d="M4.4 8.3 L6.9 10.8 L11.6 5.7" fill="none" stroke="#FFFFFF" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )
    unchecked_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        f'<rect x="0.5" y="0.5" width="15" height="15" rx="4" fill="{palette.surface_sunken}" '
        f'stroke="{palette.border_strong}" stroke-width="1"/>'
        "</svg>"
    )

    for path, content in ((checked_path, checked_svg), (unchecked_path, unchecked_svg)):
        try:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                path.write_text(content, encoding="utf-8")
        except OSError:
            return ("", "")
    return (str(checked_path), str(unchecked_path))


def build_stylesheet(palette: Palette, metrics: Optional[Metrics] = None) -> str:
    """Render the complete application stylesheet for a palette."""
    metrics = metrics or Metrics()
    compact = metrics.compact

    fs_micro = metrics.px(11)
    fs_small = metrics.px(12)
    fs_body = metrics.px(13)
    fs_h3 = metrics.px(15)
    fs_h2 = metrics.px(19)
    fs_h1 = metrics.px(23)
    fs_metric = metrics.px(27)

    radius = 12 if not compact else 10
    radius_sm = 8 if not compact else 7
    radius_xs = 5
    radius_pill = 11

    pad_h = 12 if not compact else 9
    pad_v = 7 if not compact else 5
    btn_h = 18 if not compact else 14
    icon_btn = 30 if not compact else 27

    check_checked, check_unchecked = _checkbox_assets(palette)

    values = {
        "text": palette.text,        "text_muted": palette.text_muted,
        "text_faint": palette.text_faint,
        "bg": palette.bg,
        "sidebar": palette.sidebar,
        "surface": palette.surface,
        "surface_alt": palette.surface_alt,
        "surface_hi": palette.surface_hi,
        "surface_sunken": palette.surface_sunken,
        "border": palette.border,
        "border_strong": palette.border_strong,
        "accent": palette.accent,
        "accent_hover": palette.accent_hover,
        "accent_press": palette.accent_press,
        "accent_soft": palette.accent_soft,
        "accent_border": palette.accent_border,
        "accent_text": palette.accent_text,
        "accent2": palette.accent2,
        "success": palette.success,
        "success_soft": palette.success_soft,
        "warning": palette.warning,
        "warning_soft": palette.warning_soft,
        "danger": palette.danger,
        "danger_soft": palette.danger_soft,
        "info": palette.info,
        "info_soft": palette.info_soft,
        "selection": palette.selection,
        "selection_text": palette.selection_text,
        "hover": palette.hover,
        "pressed": palette.pressed,
        "focus_ring": palette.focus_ring,
        "font": FONT_STACK,
        "mono": MONO_STACK,
        "fs_micro": fs_micro,
        "fs_small": fs_small,
        "fs_body": fs_body,
        "fs_h3": fs_h3,
        "fs_h2": fs_h2,
        "fs_h1": fs_h1,
        "fs_metric": fs_metric,
        "radius": radius,
        "radius_sm": radius_sm,
        "radius_xs": radius_xs,
        "radius_pill": radius_pill,
        "pad_h": pad_h,
        "pad_v": pad_v,
        "btn_h": btn_h,
        "icon_btn": icon_btn,
        "check_checked": check_checked,
        "check_unchecked": check_unchecked,
    }
    return _QSS.substitute(**values)


# --------------------------------------------------------------------- manager

class ThemeManager:
    """Owns the resolved theme and notifies listeners when it changes.

    Theme attributes are held in memory so they can be previewed live
    (without touching the settings file) and are seeded from the stored
    settings on first use.
    """

    def __init__(self, settings=None) -> None:
        from .config import Settings

        self._settings = settings or Settings()
        self._palette: Palette = DARK
        self._mode: Optional[str] = None
        self._accent_key: Optional[str] = None
        self._font_scale: Optional[float] = None
        self._density: Optional[str] = None
        self._listeners: List = []
        self._system_theme: Optional[str] = None
        self.resolve(force=True)

    # -- listeners ---------------------------------------------------------

    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback(self._palette)
            except Exception:
                pass

    # -- state -------------------------------------------------------------

    @property
    def palette(self) -> Palette:
        return self._palette

    @property
    def mode(self) -> str:
        return self._mode or "system"

    @property
    def is_dark(self) -> bool:
        return self._palette.name == "dark"

    def _seed_from_settings(self) -> None:
        theme = self._settings.section("theme")
        if self._mode is None:
            mode = str(theme.get("mode", "system"))
            self._mode = mode if mode in ("system", "light", "dark") else "system"
        if self._accent_key is None:
            accent = str(theme.get("accent", "indigo"))
            self._accent_key = accent if accent in ACCENTS else "indigo"
        if self._font_scale is None:
            try:
                self._font_scale = float(theme.get("font_scale", 1.0))
            except (TypeError, ValueError):
                self._font_scale = 1.0
            self._font_scale = max(0.8, min(1.4, self._font_scale))
        if self._density is None:
            density = str(theme.get("density", "comfortable"))
            self._density = density if density in ("comfortable", "compact") else "comfortable"

    @property
    def metrics(self) -> Metrics:
        self._seed_from_settings()
        return Metrics(
            font_scale=float(self._font_scale or 1.0),
            compact=str(self._density).lower() == "compact",
        )

    @property
    def accent_key(self) -> str:
        self._seed_from_settings()
        return str(self._accent_key)

    def effective_mode(self) -> str:
        """Resolve ``system`` into a concrete light/dark answer."""
        if self.mode == "system":
            from .detection import detect_system_theme

            result = detect_system_theme()
            self._system_theme = result.theme
            return result.theme or "dark"
        return self.mode

    def set_mode(self, mode: str, persist: bool = True) -> None:
        mode = mode if mode in ("system", "light", "dark") else "system"
        self._mode = mode
        if persist:
            self._settings.set("theme.mode", mode)
        self.resolve()

    def set_accent(self, accent: str, persist: bool = True) -> None:
        if accent not in ACCENTS:
            return
        self._accent_key = accent
        if persist:
            self._settings.set("theme.accent", accent)
        self.resolve()

    def set_density(self, density: str, persist: bool = True) -> None:
        self._density = density
        if persist:
            self._settings.set("theme.density", density)
        self.resolve()

    def set_font_scale(self, scale: float, persist: bool = True) -> None:
        self._font_scale = max(0.8, min(1.4, float(scale)))
        if persist:
            self._settings.set("theme.font_scale", round(self._font_scale, 2))
        self.resolve()

    def resolve(self, force: bool = False) -> Palette:
        """Recompute the active palette and notify listeners if it changed."""
        self._seed_from_settings()

        dark = self.effective_mode() == "dark"
        accent = ACCENTS.get(str(self._accent_key), ACCENTS["indigo"])

        new_palette = _base_palette(dark).tinted(accent, dark)
        if force or new_palette != self._palette:
            self._palette = new_palette
            self._notify()
        return self._palette

    def stylesheet(self) -> str:
        return build_stylesheet(self._palette, self.metrics)

    def apply(self, app) -> None:
        """Apply the current theme to a QApplication."""
        app.setStyleSheet(self.stylesheet())

    def color(self, token: str, default: str = "#000000") -> str:
        """Look up a palette token by name."""
        return getattr(self._palette, token, default)
