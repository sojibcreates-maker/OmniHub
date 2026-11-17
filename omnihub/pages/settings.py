"""Settings — appearance, gateway, behaviour and data management."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..paths import CONFIG_DIR, LOG_DIR, SETTINGS_FILE
from ..theme import ACCENTS
from .base import Page
from .common import AccentSwatch, FormRow, SettingSwitch, group_card

__all__ = ["SettingsPage"]

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "omnihub.desktop")


class SettingsPage(Page):
    """Everything the user can tune about OmniHub."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)
    theme_changed = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.settings = context.settings
        self._loading = True

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(0, 0, 6, 0)
        self._layout.setSpacing(16)
        scroll_area.setWidget(content)
        self.scroll_area = scroll_area
        root.addWidget(scroll_area)

        self._build_appearance()
        self._build_gateway()
        self._build_behaviour()
        self._build_data()
        self._layout.addStretch()
        self._loading = False

    # ------------------------------------------------------------------ UI

    def _build_appearance(self) -> None:
        card, layout = group_card(
            "Appearance",
            "OmniHub follows your desktop's light or dark preference by default and can override it.",
        )

        # -- theme mode ------------------------------------------------------
        from ..widgets import SegmentedControl

        self.seg_theme = SegmentedControl(["System", "Light", "Dark"], self)
        self.seg_theme.setFixedWidth(230)
        mode = self.settings.get("theme.mode", "system")
        self.seg_theme.select({"system": "System", "light": "Light", "dark": "Dark"}.get(mode, "System"))
        self.seg_theme.changed.connect(self._on_theme_mode)
        layout.addWidget(FormRow("Colour scheme", self.seg_theme, description="Automatically detect the desktop theme."))

        # -- accent ----------------------------------------------------------
        accent_widget = QWidget()
        accent_layout = QHBoxLayout(accent_widget)
        accent_layout.setContentsMargins(0, 0, 0, 0)
        accent_layout.setSpacing(9)
        self._accent_swatches: list = []
        for key, accent in ACCENTS.items():
            swatch = AccentSwatch(accent.primary, accent.label, accent_widget)
            swatch.clicked.connect(lambda _checked, name=key: self._on_accent(name))
            accent_layout.addWidget(swatch)
            self._accent_swatches.append((key, swatch))
        accent_layout.addStretch()
        current_accent = self.settings.get("theme.accent", "indigo")
        for key, swatch in self._accent_swatches:
            swatch.setChecked(key == current_accent)
        layout.addWidget(FormRow("Accent colour", accent_widget, description="Used for highlights, charts and primary actions."))

        # -- density ---------------------------------------------------------
        from ..widgets import SegmentedControl

        self.seg_density = SegmentedControl(["Comfortable", "Compact"], self)
        self.seg_density.setFixedWidth(230)
        density = self.settings.get("theme.density", "comfortable")
        self.seg_density.select("Compact" if density == "compact" else "Comfortable")
        self.seg_density.changed.connect(self._on_density)
        layout.addWidget(FormRow("Density", self.seg_density, description="Compact reduces padding and control heights."))

        # -- font scale ------------------------------------------------------
        self.spin_scale = QSlider(Qt.Horizontal)
        self.spin_scale.setRange(85, 130)
        self.spin_scale.setSingleStep(5)
        self.spin_scale.setValue(int(float(self.settings.get("theme.font_scale", 1.0)) * 100))
        self.spin_scale.setFixedWidth(230)
        self.spin_scale.setToolTip("Interface font scale, in percent")
        self.spin_scale.valueChanged.connect(self._on_font_scale)
        self.lbl_scale = QLabel(f"{self.spin_scale.value()}%")
        self.lbl_scale.setObjectName("Muted")
        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(10)
        scale_layout.addWidget(self.spin_scale)
        scale_layout.addWidget(self.lbl_scale)
        scale_layout.addStretch()
        layout.addWidget(FormRow("Font scale", scale_row, description="Scale every text size in the interface."))

        # -- reduce motion ----------------------------------------------------
        self.switch_motion = SettingSwitch(
            "Reduce motion",
            "Disable pulsing indicators and animated transitions.",
            checked=self.settings.bool_of("theme.reduce_motion", False),
        )
        self.switch_motion.changed.connect(self._on_reduce_motion)
        layout.addWidget(self.switch_motion)

        self._layout.addWidget(card)

    def _build_gateway(self) -> None:
        card, layout = group_card(
            "Gateway",
            "Where OmniHub connects and how often it checks the engine's health.",
        )

        self.txt_base = QLineEdit(self.settings.str_of("gateway.base_url", "http://localhost:20128"))
        self.txt_base.setObjectName("Mono")
        self.txt_base.editingFinished.connect(self._on_base_url)
        layout.addWidget(FormRow("Base URL", self.txt_base, description="The OmniRoute HTTP endpoint."))

        self.txt_key = QLineEdit(self.settings.str_of("gateway.api_key", "local"))
        self.txt_key.setObjectName("Mono")
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.txt_key.editingFinished.connect(self._on_api_key)
        layout.addWidget(FormRow("API key", self.txt_key, description="Sent as a Bearer token on every request."))

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 600)
        self.spin_timeout.setValue(self.settings.int_of("gateway.timeout", 60))
        self.spin_timeout.setSuffix(" s")
        self.spin_timeout.setFixedWidth(110)
        self.spin_timeout.valueChanged.connect(self._on_timeout)
        layout.addWidget(FormRow("Request timeout", self.spin_timeout, description="How long to wait for a model response."))

        self.spin_poll = QSpinBox()
        self.spin_poll.setRange(1, 60)
        self.spin_poll.setValue(int(self.settings.float_of("gateway.poll_interval", 2.5)))
        self.spin_poll.setSuffix(" s")
        self.spin_poll.setFixedWidth(110)
        self.spin_poll.valueChanged.connect(self._on_poll_interval)
        layout.addWidget(FormRow("Health poll interval", self.spin_poll, description="How often the gateway is probed."))

        self.switch_watchdog = SettingSwitch(
            "Auto-restart watchdog",
            "Restart the gateway automatically if it stops responding while OmniHub is open.",
            checked=self.settings.bool_of("gateway.watchdog", False),
        )
        self.switch_watchdog.changed.connect(self._on_watchdog)
        layout.addWidget(self.switch_watchdog)

        self.switch_confirm = SettingSwitch(
            "Confirm before stopping",
            "Ask for confirmation before terminating the gateway processes.",
            checked=self.settings.bool_of("gateway.confirm_stop", True),
        )
        self.switch_confirm.changed.connect(self._on_confirm_stop)
        layout.addWidget(self.switch_confirm)

        self._layout.addWidget(card)

    def _build_behaviour(self) -> None:
        card, layout = group_card("Behaviour", "How OmniHub behaves on launch and shutdown.")

        self.switch_start = SettingSwitch(
            "Start the gateway on launch",
            "Boot the OmniRoute engine as soon as OmniHub opens.",
            checked=self.settings.bool_of("behavior.start_on_launch", False),
        )
        self.switch_start.changed.connect(self._on_start_on_launch)
        layout.addWidget(self.switch_start)

        self.switch_tray = SettingSwitch(
            "Minimize to the system tray",
            "Closing the window keeps OmniHub running in the background.",
            checked=self.settings.bool_of("behavior.minimize_to_tray", True),
        )
        self.switch_tray.changed.connect(self._on_minimize_tray)
        layout.addWidget(self.switch_tray)

        self.switch_close_tray = SettingSwitch(
            "Close to tray",
            "The close button hides the window instead of quitting.",
            checked=self.settings.bool_of("behavior.close_to_tray", False),
        )
        self.switch_close_tray.changed.connect(self._on_close_to_tray)
        layout.addWidget(self.switch_close_tray)

        self.switch_notify = SettingSwitch(
            "Desktop notifications",
            "Show a notification when the gateway goes up or down.",
            checked=self.settings.bool_of("behavior.notifications", True),
        )
        self.switch_notify.changed.connect(self._on_notifications)
        layout.addWidget(self.switch_notify)

        self.switch_autostart = SettingSwitch(
            "Launch OmniHub at login",
            "Add an autostart entry for your desktop session.",
            checked=self._autostart_enabled(),
        )
        self.switch_autostart.changed.connect(self._on_autostart)
        layout.addWidget(self.switch_autostart)

        self._layout.addWidget(card)

    def _build_data(self) -> None:
        card, layout = group_card("Data", "Your settings and scratchpad live in the OmniHub config folder.")

        buttons = QHBoxLayout()
        buttons.setSpacing(9)

        btn_export = QPushButton("Export settings")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_settings)
        buttons.addWidget(btn_export)

        btn_import = QPushButton("Import settings")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self._import_settings)
        buttons.addWidget(btn_import)

        btn_folder = QPushButton("Open config folder")
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.clicked.connect(self._open_folder)
        buttons.addWidget(btn_folder)

        btn_logs = QPushButton("Clear logs")
        btn_logs.setObjectName("Danger")
        btn_logs.setCursor(Qt.PointingHandCursor)
        btn_logs.clicked.connect(self._clear_logs)
        buttons.addWidget(btn_logs)

        buttons.addStretch()
        layout.addLayout(buttons)

        path_label = QLabel(str(SETTINGS_FILE))
        path_label.setObjectName("Faint")
        layout.addWidget(path_label)

        self._layout.addWidget(card)

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "Settings"

    def subtitle(self) -> str:
        return "Tune the interface, the connection and the way OmniHub behaves"

    def on_activated(self) -> None:
        self.scroll_area.verticalScrollBar().setValue(0)

    # -- appearance --------------------------------------------------------

    def _on_theme_mode(self, value: str) -> None:
        if self._loading:
            return
        mode = {"System": "system", "Light": "light", "Dark": "dark"}.get(value, "system")
        self.context.theme.set_mode(mode, persist=True)
        self.theme_changed.emit()
        self.log.emit(f"Colour scheme set to {mode}.")

    def _on_accent(self, key: str) -> None:
        if self._loading:
            return
        for name, swatch in self._accent_swatches:
            swatch.setChecked(name == key)
        self.context.theme.set_accent(key, persist=True)
        self.theme_changed.emit()
        self.log.emit(f"Accent colour set to {key}.")

    def _on_density(self, value: str) -> None:
        if self._loading:
            return
        density = "compact" if value == "Compact" else "comfortable"
        self.context.theme.set_density(density, persist=True)
        self.theme_changed.emit()
        self.log.emit(f"Interface density set to {density}.")

    def _on_font_scale(self, value: int) -> None:
        self.lbl_scale.setText(f"{value}%")
        if self._loading:
            return
        self.context.theme.set_font_scale(value / 100.0, persist=True)
        self.theme_changed.emit()

    def _on_reduce_motion(self, enabled: bool) -> None:
        self.settings.set("theme.reduce_motion", bool(enabled))
        self.context.theme.resolve()
        self.theme_changed.emit()

    # -- gateway -----------------------------------------------------------

    def _on_base_url(self) -> None:
        value = self.txt_base.text().strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            value = "http://" + value
        self.txt_base.setText(value)
        self.settings.set("gateway.base_url", value)
        self.context.api.configure(base_url=value)
        self.notify.emit("Gateway address updated.", "success")

    def _on_api_key(self) -> None:
        value = self.txt_key.text().strip() or "local"
        self.settings.set("gateway.api_key", value)
        self.context.api.configure(api_key=value)
        self.notify.emit("API key updated.", "success")

    def _on_timeout(self, value: int) -> None:
        self.settings.set("gateway.timeout", int(value))
        self.context.api.configure(timeout=int(value))

    def _on_poll_interval(self, value: int) -> None:
        self.settings.set("gateway.poll_interval", int(value))
        self.settings_changed.emit()

    def _on_watchdog(self, enabled: bool) -> None:
        self.settings.set("gateway.watchdog", bool(enabled))

    def _on_confirm_stop(self, enabled: bool) -> None:
        self.settings.set("gateway.confirm_stop", bool(enabled))

    # -- behaviour ---------------------------------------------------------

    def _on_start_on_launch(self, enabled: bool) -> None:
        self.settings.set("behavior.start_on_launch", bool(enabled))

    def _on_minimize_tray(self, enabled: bool) -> None:
        self.settings.set("behavior.minimize_to_tray", bool(enabled))

    def _on_close_to_tray(self, enabled: bool) -> None:
        self.settings.set("behavior.close_to_tray", bool(enabled))

    def _on_notifications(self, enabled: bool) -> None:
        self.settings.set("behavior.notifications", bool(enabled))

    def _on_autostart(self, enabled: bool) -> None:
        if enabled:
            ok = self._write_autostart()
        else:
            ok = self._remove_autostart()
        if ok:
            self.notify.emit(
                "OmniHub will now launch at login." if enabled else "Login autostart removed.",
                "success",
            )
        else:
            self.notify.emit("Could not update the autostart entry.", "danger")
            self.switch_autostart.setChecked(self._autostart_enabled())

    @staticmethod
    def _autostart_enabled() -> bool:
        return os.path.isfile(AUTOSTART_FILE)

    @staticmethod
    def _write_autostart() -> bool:
        try:
            os.makedirs(AUTOSTART_DIR, exist_ok=True)
            executable = os.path.expanduser("~/.local/bin/omnihub")
            if not os.path.exists(executable):
                executable = os.path.expanduser("~/.gemini/antigravity/scratch/omnihub/main.py")
            entry = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=OmniHub\n"
                "Comment=Precision AI & System Studio\n"
                f"Exec=python3 {executable}\n"
                "Icon=omnihub\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as handle:
                handle.write(entry)
            return True
        except OSError:
            return False

    @staticmethod
    def _remove_autostart() -> bool:
        try:
            if os.path.isfile(AUTOSTART_FILE):
                os.unlink(AUTOSTART_FILE)
            return True
        except OSError:
            return False

    # -- data --------------------------------------------------------------

    def _export_settings(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Export settings",
            os.path.expanduser("~/omnihub-settings.json"),
            "JSON files (*.json)",
        )
        if not target:
            return
        try:
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(self.settings.as_dict(), handle, indent=2, ensure_ascii=False)
            self.notify.emit(f"Settings exported to {target}.", "success")
        except OSError as exc:
            self.notify.emit(f"Export failed: {exc}", "danger")

    def _import_settings(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Import settings",
            os.path.expanduser("~"),
            "JSON files (*.json)",
        )
        if not source:
            return
        try:
            with open(source, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("The file does not contain a settings object.")
        except (OSError, ValueError) as exc:
            self.notify.emit(f"Import failed: {exc}", "danger")
            return

        self.settings.replace(payload)
        self.context.theme.resolve()
        self.theme_changed.emit()
        self.settings_changed.emit()
        self._reload_from_settings()
        self.notify.emit("Settings imported and applied.", "success")

    def _reload_from_settings(self) -> None:
        self._loading = True
        self.txt_base.setText(self.settings.str_of("gateway.base_url"))
        self.txt_key.setText(self.settings.str_of("gateway.api_key"))
        self.spin_timeout.setValue(self.settings.int_of("gateway.timeout", 60))
        self.spin_poll.setValue(int(self.settings.float_of("gateway.poll_interval", 2.5)))
        self.switch_watchdog.setChecked(self.settings.bool_of("gateway.watchdog"))
        self.switch_confirm.setChecked(self.settings.bool_of("gateway.confirm_stop", True))
        self.switch_start.setChecked(self.settings.bool_of("behavior.start_on_launch"))
        self.switch_tray.setChecked(self.settings.bool_of("behavior.minimize_to_tray"))
        self.switch_close_tray.setChecked(self.settings.bool_of("behavior.close_to_tray"))
        self.switch_notify.setChecked(self.settings.bool_of("behavior.notifications"))
        self.switch_autostart.setChecked(self._autostart_enabled())
        self.switch_motion.setChecked(self.settings.bool_of("theme.reduce_motion"))
        mode = {"system": "System", "light": "Light", "dark": "Dark"}.get(
            self.settings.get("theme.mode", "system"), "System"
        )
        self.seg_theme.select(mode)
        density = self.settings.get("theme.density", "comfortable")
        self.seg_density.select("Compact" if density == "compact" else "Comfortable")
        self.spin_scale.setValue(int(float(self.settings.get("theme.font_scale", 1.0)) * 100))
        for name, swatch in self._accent_swatches:
            swatch.setChecked(name == self.settings.get("theme.accent", "indigo"))
        self._loading = False

    def _open_folder(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["xdg-open", str(CONFIG_DIR)])
        except Exception as exc:  # noqa: BLE001
            self.notify.emit(f"Could not open the folder: {exc}", "danger")

    def _clear_logs(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear logs",
            "Delete every OmniHub log file? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        removed = 0
        try:
            for entry in LOG_DIR.glob("*"):
                if entry.is_file():
                    entry.unlink()
                    removed += 1
        except OSError as exc:
            self.notify.emit(f"Could not clear logs: {exc}", "danger")
            return
        self.notify.emit(f"Cleared {removed} log file(s).", "success")
