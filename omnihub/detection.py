"""Operating-system colour-scheme detection.

OmniHub can follow the desktop environment's light/dark preference.  Deepin,
GNOME, KDE and Plasma all expose that preference differently, so several
independent probes are consulted and the first confident answer wins.

Every probe is defensive: a missing binary, a hung gsettings daemon or a
permission error must never take the app down, so all failures degrade to
``None`` (meaning "no opinion").
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

__all__ = ["detect_system_theme", "DetectionResult", "probe_sources"]

DARK = "dark"
LIGHT = "light"
UNKNOWN = None

_GSETTINGS_TIMEOUT = 2.0


class DetectionResult:
    """Outcome of a detection sweep."""

    __slots__ = ("theme", "source", "candidates")

    def __init__(self, theme: Optional[str], source: str = "none", candidates: Optional[List[str]] = None):
        self.theme = theme
        self.source = source
        self.candidates = candidates or []

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"DetectionResult(theme={self.theme!r}, source={self.source!r})"


def _run_gsettings(schema: str, key: str) -> Optional[str]:
    """Read a gsettings value, returning ``None`` on any failure."""
    if not shutil.which("gsettings"):
        return None
    try:
        proc = subprocess.run(
            ["gsettings", "get", schema, key],
            capture_output=True,
            text=True,
            timeout=_GSETTINGS_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    value = (proc.stdout or "").strip()
    if not value or value in ("'default'", "''"):
        return None
    return value.strip("'").strip()


def _gsettings_says_dark(schema: str, key: str) -> Optional[bool]:
    """Interpret a gsettings string as a dark-mode opinion."""
    value = _run_gsettings(schema, key)
    if value is None:
        return None
    lowered = value.lower()
    if "prefer-dark" in lowered or "dark" in lowered:
        return True
    if "prefer-light" in lowered or "light" in lowered:
        return False
    return None


def _kde_scheme_is_dark() -> Optional[bool]:
    """Read ``~/.config/kdeglobals`` for the active Plasma colour scheme."""
    kdeglobals = Path.home() / ".config" / "kdeglobals"
    try:
        if not kdeglobals.is_file():
            return None
        text = kdeglobals.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r"^ColorScheme\s*=\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    scheme = match.group(1).strip().lower()
    if "dark" in scheme:
        return True
    if "light" in scheme:
        return False
    return None


def _qt_palette_is_dark() -> Optional[bool]:
    """Ask the active Qt style for the background luminance."""
    try:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None
        palette = app.palette()
        color = palette.color(palette.Window)
        return color.lightness() < 128
    except Exception:
        return None


def _dde_config_is_dark() -> Optional[bool]:
    """Inspect Deepin's own appearance config for a dark preference."""
    for path in (
        Path.home() / ".config" / "dde-daemon" / "config.json",
        Path.home() / ".config" / "deepin" / "dde-daemon" / "config.json",
    ):
        try:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "dark" in text and ("theme" in text or "darkmode" in text):
            return True
    return None


def _windows_is_dark() -> Optional[bool]:
    """Read Windows personal theme registry key for dark mode."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return val == 0
    except Exception:
        return None


def _macos_is_dark() -> Optional[bool]:
    """Read macOS AppleInterfaceStyle for dark mode."""
    try:
        out = subprocess.check_output(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip().lower()
        return "dark" in out
    except Exception:
        return None


def probe_sources() -> List[Tuple[str, Optional[bool]]]:
    """Return every probe result as ``(source_name, is_dark_or_None)``."""
    probes: List[Tuple[str, Optional[bool]]] = []

    # Windows & macOS platform probes
    probes.append(("windows-registry", _windows_is_dark()))
    probes.append(("macos-defaults", _macos_is_dark()))

    # GNOME / Deepin wrap: the modern colour-scheme key.
    probes.append(("gsettings:gnome", _gsettings_says_dark("org.gnome.desktop.interface", "color-scheme")))

    # Deepin's own GTK wrapper.
    probes.append(("gsettings:deepin", _gsettings_says_dark("com.deepin.wrap.gnome.desktop.interface", "color-scheme")))

    # Deepin XSettings: theme-name flips to *-dark when the user switches.
    for schema, key in (
        ("com.deepin.xsettings", "theme-name"),
        ("com.deepin.xsettings", "gtk-theme-name"),
        ("com.deepin.dde.appearance", "gtk-theme"),
        ("com.deepin.wrap.gnome.desktop.interface", "gtk-theme"),
    ):
        value = _run_gsettings(schema, key)
        if value:
            lowered = value.lower()
            probes.append((f"gsettings:{schema}.{key}", True if "dark" in lowered else False))

    probes.append(("kdeglobals", _kde_scheme_is_dark()))
    probes.append(("dde-config", _dde_config_is_dark()))
    probes.append(("qt-palette", _qt_palette_is_dark()))
    return probes


def detect_system_theme() -> DetectionResult:
    """Detect the desktop's preferred colour scheme.

    Returns a :class:`DetectionResult` whose ``theme`` is ``"dark"``,
    ``"light"`` or ``None`` when nothing could be determined.
    """
    candidates: List[str] = []
    for source, opinion in probe_sources():
        if opinion is None:
            candidates.append(f"{source}=?")
            continue
        candidates.append(f"{source}={'dark' if opinion else 'light'}")
        if opinion:
            return DetectionResult(DARK, source, candidates)
        # An explicit light answer from a desktop-specific source is trusted,
        # but a generic "light" from the Qt palette is weaker, so keep going
        # and let any explicit dark answer override it.
        if source.startswith("gsettings:") or source == "kdeglobals":
            return DetectionResult(LIGHT, source, candidates)

    # Nothing explicit: fall back to the Qt palette, then to dark.
    palette_opinion = _qt_palette_is_dark()
    if palette_opinion is not None:
        return DetectionResult(DARK if palette_opinion else LIGHT, "qt-palette", candidates)
    return DetectionResult(None, "default", candidates)
