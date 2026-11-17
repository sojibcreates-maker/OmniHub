"""The OmniHub main window."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCloseEvent, QIcon, QKeySequence, QPixmap, QResizeEvent
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_TAGLINE, APP_VERSION
from .command_palette import Command, CommandPalette
from .context import AppContext
from .icons import icon_pixmap
from .pages.about import AboutPage
from .pages.ai import AIStudioPage
from .pages.gateway import GatewayPage
from .pages.settings import SettingsPage
from .pages.system import SystemRadarPage
from .pages.tools import ToolsPage
from .paths import find_icon
from .widgets import IconButton, NavItem, StatusDot, normalize_labels

__all__ = ["MainWindow"]

SIDEBAR_WIDTH = 238
SIDEBAR_RAIL_WIDTH = 68
COMPACT_BREAKPOINT = 1080


class MainWindow(QMainWindow):
    """The application shell: sidebar, header, page stack and status bar."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.settings = context.settings
        self._sidebar_collapsed = False
        self._health_ok: Optional[bool] = None
        self._consecutive_failures = 0
        self._watchdog_triggered = False
        self._tray: Optional[QSystemTrayIcon] = None
        self._quitting = False

        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.setMinimumSize(860, 600)
        self.resize(1360, 860)

        icon_path = find_icon()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._build_tray()
        self._build_shortcuts()
        self._restore_geometry()

        self._connect_context()

        # Timers
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._poll_health)
        self._health_timer.start(2500)

        self._system_timer = QTimer(self)
        self._system_timer.timeout.connect(self._update_system)
        self._system_timer.start(2200)

        self._theme_timer = QTimer(self)
        self._theme_timer.timeout.connect(self._detect_system_theme)
        self._theme_timer.start(20000)

        self._poll_health()
        self._update_system()
        self._detect_system_theme()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_topbar())
        right_layout.addWidget(self._build_header())

        # --- page stack ---
        self.pages = QStackedWidget()
        self.gateway_page = GatewayPage(self.context)
        self.ai_page = AIStudioPage(self.context)
        self.system_page = SystemRadarPage(self.context)
        self.tools_page = ToolsPage(self.context)
        self.settings_page = SettingsPage(self.context)
        self.about_page = AboutPage(self.context)
        self._page_list = [
            self.gateway_page,
            self.ai_page,
            self.system_page,
            self.tools_page,
            self.settings_page,
            self.about_page,
        ]
        for page in self._page_list:
            self.pages.addWidget(page)
        right_layout.addWidget(self.pages, 1)

        right_layout.addWidget(self._build_statusbar())
        root.addWidget(right, 1)

        normalize_labels(self)
        self.switch_page(int(self.settings.int_of("window.page", 0)))
        self._apply_theme()

    def _build_sidebar(self) -> QWidget:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(6)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(11)
        self.brand_icon = QLabel()
        self.brand_icon.setFixedSize(34, 34)
        icon_path = find_icon()
        if icon_path is not None:
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                self.brand_icon.setPixmap(
                    pixmap.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        brand.addWidget(self.brand_icon)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        self.lbl_brand = QLabel(APP_NAME.upper())
        self.lbl_brand.setStyleSheet("font-size: 15px; font-weight: 700; letter-spacing: 1.2px;")
        self.lbl_brand_tag = QLabel("PRO GATEWAY")
        self.lbl_brand_tag.setStyleSheet("font-size: 9px; font-weight: 700; letter-spacing: 1.6px;")
        brand_text.addWidget(self.lbl_brand)
        brand_text.addWidget(self.lbl_brand_tag)
        brand.addLayout(brand_text)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(14)

        # Palette launcher
        self.btn_palette = QPushButton("Search commands")
        self.btn_palette.setObjectName("Ghost")
        self.btn_palette.setCursor(Qt.PointingHandCursor)
        self.btn_palette.setToolTip("Open the command palette  (Ctrl + K)")
        self.btn_palette.clicked.connect(self.open_palette)
        layout.addWidget(self.btn_palette)
        layout.addSpacing(12)

        nav_label = QLabel("WORKSPACE")
        nav_label.setObjectName("SectionLabel")
        nav_label.setContentsMargins(6, 0, 0, 0)
        self.nav_label = nav_label
        layout.addWidget(nav_label)

        self.nav_items: List[NavItem] = []
        definitions = [
            ("Gateway", "gateway"),
            ("AI Studio", "sparkle"),
            ("System Radar", "gauge"),
            ("Scratchpad", "document"),
            ("Settings", "sliders"),
            ("About", "info"),
        ]
        for index, (text, icon) in enumerate(definitions):
            item = NavItem(text, icon)
            item.clicked.connect(lambda _checked, position=index: self.switch_page(position))
            layout.addWidget(item)
            self.nav_items.append(item)

        layout.addStretch()

        # Gateway status card
        self.status_card = QFrame()
        self.status_card.setObjectName("CardSunken")
        card_layout = QVBoxLayout(self.status_card)
        card_layout.setContentsMargins(12, 11, 12, 11)
        card_layout.setSpacing(7)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.sidebar_dot = StatusDot(self, "#F87171", 8, pulse=True)
        status_row.addWidget(self.sidebar_dot)
        self.lbl_sidebar_status = QLabel("Connecting…")
        self.lbl_sidebar_status.setStyleSheet("font-size: 12px; font-weight: 600;")
        status_row.addWidget(self.lbl_sidebar_status)
        status_row.addStretch()
        card_layout.addLayout(status_row)

        self.lbl_sidebar_meta = QLabel("—")
        self.lbl_sidebar_meta.setObjectName("Faint")
        card_layout.addWidget(self.lbl_sidebar_meta)

        layout.addWidget(self.status_card)

        # Theme quick toggle
        self.btn_theme = IconButton("sun", self, "Toggle light / dark mode  (Ctrl + Shift + T)", 30)
        self.btn_theme.clicked.connect(self.toggle_theme)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(7)
        theme_row.addWidget(self.btn_theme)
        self.lbl_version = QLabel(f"v{APP_VERSION}")
        self.lbl_version.setObjectName("Faint")
        theme_row.addWidget(self.lbl_version)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        return self.sidebar

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(46)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(10)

        self.btn_toggle_sidebar = IconButton("chevron-left", self, "Collapse the sidebar  (Ctrl + B)", 28)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.btn_toggle_sidebar)

        crumb = QLabel("OmniRoute")
        crumb.setObjectName("Muted")
        layout.addWidget(crumb)
        self.lbl_crumbs = crumb

        layout.addStretch()

        self.chip_latency = QLabel("— ms")
        self.chip_latency.setObjectName("Badge")
        layout.addWidget(self.chip_latency)

        btn_dashboard = IconButton("globe", self, "Open the web dashboard  (Ctrl + D)", 28)
        btn_dashboard.clicked.connect(self.open_dashboard)
        layout.addWidget(btn_dashboard)

        return bar

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 16, 24, 14)
        layout.setSpacing(16)

        text = QVBoxLayout()
        text.setSpacing(3)
        self.lbl_page_title = QLabel("Gateway Overview")
        self.lbl_page_title.setObjectName("H1")
        self.lbl_page_desc = QLabel("")
        self.lbl_page_desc.setObjectName("Muted")
        self.lbl_page_desc.setWordWrap(True)
        self.lbl_page_desc.setMinimumWidth(460)
        text.addWidget(self.lbl_page_title)
        text.addWidget(self.lbl_page_desc)
        layout.addLayout(text)
        layout.addStretch()

        self.header_actions_host = QWidget()
        self.header_actions_layout = QHBoxLayout(self.header_actions_host)
        self.header_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.header_actions_layout.setSpacing(8)
        layout.addWidget(self.header_actions_host, 0, Qt.AlignVCenter)

        return header

    def _build_statusbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(26)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("Faint")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

        self.lbl_status_right = QLabel(f"{APP_NAME} {APP_VERSION}")
        self.lbl_status_right.setObjectName("Faint")
        layout.addWidget(self.lbl_status_right)
        return bar

    # ------------------------------------------------------------- plumbing

    def _connect_context(self) -> None:
        for page in self._page_list:
            if hasattr(page, "log"):
                page.log.connect(self._on_page_log)
            if hasattr(page, "notify"):
                page.notify.connect(self.notify)

        self.gateway_page.health_changed.connect(self._on_health_changed)
        self.settings_page.theme_changed.connect(self._apply_theme)
        self.settings_page.settings_changed.connect(self._on_settings_changed)

    def _on_health_changed(self, online: bool, payload: dict) -> None:
        """Mirror the gateway state into the sidebar and the top bar."""
        palette = self.context.theme.palette
        latency = int(payload.get("latency_ms", 0) or 0)

        if online:
            self._health_ok = True
            self._consecutive_failures = 0
            self._watchdog_triggered = False
            self.sidebar_dot.set_color(palette.success)
            self.lbl_sidebar_status.setText("Gateway online")
            self.lbl_sidebar_meta.setText(f"{self.context.api.base_url.replace('http://', '')} · {latency} ms")
            self.chip_latency.setText(f"{latency} ms")
            self.chip_latency.setObjectName("BadgeSuccess")
            self._polish_chip()
        else:
            was_online = self._health_ok is True
            self._health_ok = False
            self._consecutive_failures += 1
            self.sidebar_dot.set_color(palette.danger)
            self.lbl_sidebar_status.setText("Gateway offline")
            self.lbl_sidebar_meta.setText("No response")
            self.chip_latency.setText("Offline")
            self.chip_latency.setObjectName("BadgeDanger")
            self._polish_chip()

            if was_online and self.settings.bool_of("behavior.notifications", True):
                self.notify("The OmniRoute gateway stopped responding.", "danger")
            self._maybe_watchdog()

    def _maybe_watchdog(self) -> None:
        """Restart the gateway automatically after repeated failures."""
        if not self.settings.bool_of("gateway.watchdog", False):
            return
        if self._watchdog_triggered or self._consecutive_failures < 3:
            return
        self._watchdog_triggered = True
        self.notify("Watchdog: restarting the gateway…", "warning")
        QTimer.singleShot(500, self.gateway_page.restart_service)

    def _polish_chip(self) -> None:
        self.chip_latency.style().unpolish(self.chip_latency)
        self.chip_latency.style().polish(self.chip_latency)

    def _build_shortcuts(self) -> None:
        def bind(sequence: str, handler) -> None:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.WindowShortcut)
            shortcut.activated.connect(handler)

        bind("Ctrl+K", self.open_palette)
        bind("Ctrl+,", lambda: self.switch_page(4))
        bind("Ctrl+D", self.open_dashboard)
        bind("Ctrl+R", self.restart_gateway)
        bind("Ctrl+B", self.toggle_sidebar)
        bind("Ctrl+Q", self.quit_app)
        bind("Ctrl+Shift+T", self.toggle_theme)
        bind("Ctrl+F", self.focus_find)
        bind("F5", self._poll_health)
        for index in range(1, 7):
            bind(f"Ctrl+{index}", lambda _=None, i=index - 1: self.switch_page(i))

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = find_icon()
        if icon_path is not None:
            icon = QIcon(str(icon_path))
        else:
            icon = QIcon(icon_pixmap("gateway", 64, "#6366F1"))
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip(f"{APP_NAME} — {APP_TAGLINE}")

        menu = QMenu()
        act_show = menu.addAction("Open OmniHub")
        act_show.triggered.connect(self._show_from_tray)
        act_dash = menu.addAction("Open web dashboard")
        act_dash.triggered.connect(self.open_dashboard)
        act_restart = menu.addAction("Restart gateway")
        act_restart.triggered.connect(self.restart_gateway)
        menu.addSeparator()
        act_quit = menu.addAction("Quit OmniHub")
        act_quit.triggered.connect(self.quit_app)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.Trigger else None
        )
        self._tray.show()

    def _restore_geometry(self) -> None:
        geometry = self.settings.get("window.geometry")
        if isinstance(geometry, dict):
            try:
                self.setGeometry(
                    int(geometry["x"]),
                    int(geometry["y"]),
                    int(geometry["width"]),
                    int(geometry["height"]),
                )
                return
            except (KeyError, TypeError, ValueError):
                pass
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width = min(1360, int(area.width() * 0.86))
        height = min(880, int(area.height() * 0.88))
        self.setGeometry(
            area.x() + (area.width() - width) // 2,
            area.y() + (area.height() - height) // 2,
            width,
            height,
        )

    # ----------------------------------------------------------- navigation

    def switch_page(self, index: int) -> None:
        if index < 0 or index >= len(self._page_list):
            return
        previous = self.pages.currentIndex()
        if previous >= 0 and previous != index:
            page = self._page_list[previous]
            if hasattr(page, "on_deactivated"):
                page.on_deactivated()

        self.pages.setCurrentIndex(index)
        page = self._page_list[index]
        self.lbl_page_title.setText(page.title())
        self.lbl_page_desc.setText(page.subtitle())

        for position, item in enumerate(self.nav_items):
            item.setChecked(position == index)

        self._refresh_header_actions(page)
        self.settings.set("window.page", index)

        if hasattr(page, "on_activated"):
            page.on_activated()

    def open_page(self, name: str) -> None:
        """Switch to a page by its short name (used by the CLI and desktop actions)."""
        names = {
            "gateway": 0,
            "ai": 1,
            "studio": 1,
            "system": 2,
            "radar": 2,
            "tools": 3,
            "scratchpad": 3,
            "settings": 4,
            "about": 5,
        }
        index = names.get(str(name).lower())
        if index is not None:
            self.switch_page(index)
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _refresh_header_actions(self, page) -> None:
        while self.header_actions_layout.count():
            item = self.header_actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        actions = page.header_actions() if hasattr(page, "header_actions") else None
        if actions is not None:
            self.header_actions_layout.addWidget(actions)

    # --------------------------------------------------------------- theme

    def _apply_theme(self) -> None:
        theme = self.context.theme
        theme.resolve()
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.stylesheet())
        self._refresh_sidebar_theme()
        for page in self._page_list:
            if hasattr(page, "on_theme_changed"):
                page.on_theme_changed()

    def _refresh_sidebar_theme(self) -> None:
        palette = self.context.theme.palette
        self.lbl_brand.setStyleSheet("font-size: 15px; font-weight: 700; letter-spacing: 1.2px;")
        self.lbl_brand_tag.setStyleSheet(
            f"font-size: 9px; font-weight: 700; letter-spacing: 1.6px; color: {palette.accent_text};"
        )
        self.btn_theme.set_icon("moon" if self.context.theme.is_dark else "sun")

    def _detect_system_theme(self) -> None:
        """Re-resolve the theme when following the operating system."""
        if self.context.theme.mode != "system":
            return
        before = self.context.theme.palette.name
        after = self.context.theme.resolve().name
        if before != after:
            self._apply_theme()
            self.notify(
                f"Switched to {after} mode to match your desktop.",
                "info",
            )

    def toggle_theme(self) -> None:
        current = self.context.theme.mode
        if current == "system":
            resolved = self.context.theme.effective_mode()
            new_mode = "light" if resolved == "dark" else "dark"
        else:
            new_mode = "light" if current == "dark" else "dark"
        self.context.theme.set_mode(new_mode)
        self._apply_theme()
        self.notify(f"Switched to {new_mode} mode.", "info")

    def toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self._apply_sidebar_mode()
        self.settings.set("window.sidebar_compact", self._sidebar_collapsed)

    def _apply_sidebar_mode(self) -> None:
        collapsed = self._sidebar_collapsed or self.width() < COMPACT_BREAKPOINT
        self.sidebar.setFixedWidth(SIDEBAR_RAIL_WIDTH if collapsed else SIDEBAR_WIDTH)
        self.lbl_brand.setVisible(not collapsed)
        self.lbl_brand_tag.setVisible(not collapsed)
        self.nav_label.setVisible(not collapsed)
        self.status_card.setVisible(not collapsed)
        self.btn_palette.setText("" if collapsed else "Search commands")
        self.lbl_version.setVisible(not collapsed)
        for item in self.nav_items:
            item.set_label("" if collapsed else item._label)
        self.btn_toggle_sidebar.set_icon("chevron-right" if collapsed else "chevron-left")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_sidebar_mode()

    # -------------------------------------------------------------- timers

    def _poll_health(self) -> None:
        self.gateway_page.poll_health()

    def _update_system(self) -> None:
        if self.pages.currentIndex() == 2:
            self.system_page.refresh()

    def _on_settings_changed(self) -> None:
        interval = int(self.settings.float_of("gateway.poll_interval", 2.5))
        self._health_timer.setInterval(max(1, interval) * 1000)
        self.context.api.configure(
            base_url=self.settings.str_of("gateway.base_url"),
            api_key=self.settings.str_of("gateway.api_key"),
            timeout=self.settings.int_of("gateway.timeout", 60),
        )

    # -------------------------------------------------------------- actions

    def open_palette(self) -> None:
        palette = CommandPalette(self)
        palette.set_commands(self._build_commands())
        palette.chosen.connect(self._run_command)
        palette.show_centered()

    def _build_commands(self) -> List[Command]:
        commands: List[Command] = []
        for index, page in enumerate(self._page_list):
            commands.append(
                Command(
                    title=f"Go to {page.title()}",
                    subtitle=page.subtitle(),
                    icon=("gateway", "sparkle", "gauge", "document", "sliders", "info")[index],
                    identifier=f"page:{index}",
                    shortcut=f"Ctrl+{index + 1}",
                    keywords=page.title(),
                )
            )
        commands.extend(
            [
                Command("Start the gateway", "Launch the OmniRoute engine", "play", "action:start", keywords="service up"),
                Command("Restart the gateway", "Stop and start the engine", "refresh", "action:restart", keywords="service reload"),
                Command("Stop the gateway", "Terminate the engine", "stop", "action:stop", keywords="service down"),
                Command("Open the web dashboard", "Open localhost:20128/dashboard", "globe", "action:dashboard", keywords="browser web"),
                Command("Reload the model catalogue", "Fetch the available models", "layers", "action:models", keywords="providers"),
                Command("Toggle light / dark mode", "Switch the colour scheme", "sun", "action:theme", keywords="appearance dark light"),
                Command("Follow the system theme", "Automatically match the desktop", "monitor", "action:theme-system", keywords="appearance auto"),
                Command("Copy the API endpoint", "Copy the base URL to the clipboard", "copy", "action:copy-url", keywords="endpoint url"),
                Command("Copy the API key", "Copy the bearer token", "key", "action:copy-key", keywords="secret token"),
                Command("Export the audit trail", "Save the console output to a file", "download", "action:export-log", keywords="save log"),
                Command("New chat", "Clear the AI Studio conversation", "sparkles", "action:new-chat", keywords="clear conversation"),
                Command("Find in the scratchpad", "Search the notepad", "search", "action:find", shortcut="Ctrl+F", keywords="search notepad"),
                Command("Restart OmniHub", "Reload the application", "refresh", "action:restart-app", keywords="reload reboot"),
                Command("Quit OmniHub", "Close the application", "close", "action:quit", shortcut="Ctrl+Q", keywords="exit"),
            ]
        )
        return commands

    def _run_command(self, identifier: str, payload: object) -> None:
        if identifier.startswith("page:"):
            try:
                self.switch_page(int(identifier.split(":", 1)[1]))
            except ValueError:
                pass
            return

        action = identifier.split(":", 1)[1] if ":" in identifier else identifier
        if action == "start":
            self.gateway_page.start_service()
        elif action == "restart":
            self.restart_gateway()
        elif action == "stop":
            self.gateway_page.stop_service()
        elif action == "dashboard":
            self.open_dashboard()
        elif action == "models":
            self.gateway_page.refresh_models()
        elif action == "theme":
            self.toggle_theme()
        elif action == "theme-system":
            self.context.theme.set_mode("system")
            self._apply_theme()
            self.notify("Now following the system colour scheme.", "info")
        elif action == "copy-url":
            from .pages.common import copy_to_clipboard

            copy_to_clipboard(self.context.api.base_url)
            self.notify("Endpoint copied to the clipboard.", "success")
        elif action == "copy-key":
            from .pages.common import copy_to_clipboard

            copy_to_clipboard(self.context.api.api_key)
            self.notify("API key copied to the clipboard.", "success")
        elif action == "export-log":
            self.gateway_page._export_console()
        elif action == "new-chat":
            self.switch_page(1)
            self.ai_page.clear_chat()
        elif action == "find":
            self.switch_page(3)
            self.focus_find()
        elif action == "restart-app":
            self.restart_app()
        elif action == "quit":
            self.quit_app()

    def open_dashboard(self) -> None:
        url = f"{self.context.api.base_url}/dashboard"
        try:
            subprocess.Popen(["xdg-open", url])
            self.notify(f"Opened {url}", "info")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Could not open the dashboard: {exc}", "danger")

    def restart_gateway(self) -> None:
        self.switch_page(0)
        self.gateway_page._service_action("restart")

    def focus_find(self) -> None:
        self.switch_page(3)
        self.tools_page.txt_find.setFocus()
        self.tools_page.txt_find.selectAll()

    def restart_app(self) -> None:
        self.notify("Restarting OmniHub…", "info")
        QTimer.singleShot(350, self._do_restart)

    def _do_restart(self) -> None:
        try:
            os.execv(sys.executable, [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:])
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Could not restart: {exc}", "danger")

    def quit_app(self) -> None:
        self._quitting = True
        self.close()

    # -------------------------------------------------------------- notices

    def notify(self, message: str, tone: str = "info") -> None:
        """Show a transient message in the status bar and optionally as a tray notification."""
        self.lbl_status.setText(message)
        QTimer.singleShot(6000, lambda: self.lbl_status.setText("Ready"))

        if not self.settings.bool_of("behavior.notifications", True):
            return
        if self._tray is None or not self._tray.isVisible():
            return
        if tone not in ("success", "danger", "warning"):
            return
        self._tray.showMessage(
            APP_NAME,
            message,
            QSystemTrayIcon.Information if tone == "success" else QSystemTrayIcon.Warning,
            4000,
        )

    def _on_page_log(self, message: str) -> None:
        self.gateway_page.log_message(_strip_tags(message), "muted")

    # -------------------------------------------------------------- closing

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._quitting and self.settings.bool_of("behavior.close_to_tray", False):
            if self._tray is not None and self._tray.isVisible():
                self.hide()
                event.ignore()
                return

        logger = logging.getLogger("omnihub")
        logger.info("Window closing (quit flag=%s)", self._quitting)
        self._save_state()
        self._shutdown_pages()

        if self._tray is not None:
            self._tray.hide()
        event.accept()

    def _save_state(self) -> None:
        geometry = self.geometry()
        self.settings.set(
            "window.geometry",
            {
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
            },
        )
        self.settings.set("window.page", self.pages.currentIndex())

    def _shutdown_pages(self) -> None:
        for page in self._page_list:
            if hasattr(page, "shutdown"):
                try:
                    page.shutdown()
                except Exception:
                    pass


def _strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text or "")
