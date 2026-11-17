"""Gateway Overview — live health, routing matrix and audit trail."""

from __future__ import annotations

import html
import logging
import re
import traceback
import time
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..api import OmniRouteClient
from ..context import AppContext
from ..workers import ServiceWorker, TaskGroup
from ..widgets import (
    Card,
    IconButton,
    ResponsiveGrid,
    SearchBox,
    Sparkline,
    StatTile,
    StatusDot,
)
from .base import Page
from .common import copy_to_clipboard

__all__ = ["GatewayPage"]


class GatewayPage(Page):
    """Control surface for the local OmniRoute gateway."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)
    health_changed = pyqtSignal(bool, dict)

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._client: OmniRouteClient = context.api

        self._latencies: List[float] = []
        self._health_payload: Dict = {}
        self._models: List[Dict] = []
        self._model_filter: str = ""
        self._poll_pending = False
        self._busy = False
        self._models_loaded = False
        self._session_start = time.time()
        self._uptime_samples: List[bool] = []
        self._console_lines: List[str] = []
        self._tasks = TaskGroup(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(0, 0, 6, 0)
        self._layout.setSpacing(16)
        scroll.setWidget(content)
        self.scroll_area = scroll
        root.addWidget(scroll)

        self._build_metrics()
        self._build_service_row()
        self._build_performance()
        self._build_models()
        self._build_console()
        self._layout.addStretch()

    # ------------------------------------------------------------------ UI

    def _build_metrics(self) -> None:
        self._grid = ResponsiveGrid(self, spacing=14, min_item_width=210, max_columns=4)
        self.tile_status = StatTile("Engine liveness", "Checking…", "Probing the local gateway", "gateway")
        self.tile_latency = StatTile("Edge latency", "—", "Awaiting first sample", "bolt")
        self.tile_models = StatTile("Routing matrix", "—", "Models in the catalogue", "layers")
        self.tile_uptime = StatTile("Availability", "—", "Since this session started", "activity")
        for tile in (self.tile_status, self.tile_latency, self.tile_models, self.tile_uptime):
            self._grid.add(tile)
        self._layout.addWidget(self._grid)

    def _build_service_row(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(14)

        # -- service control ------------------------------------------------
        service_card = Card()
        service_layout = QVBoxLayout(service_card)
        service_layout.setContentsMargins(18, 16, 18, 16)
        service_layout.setSpacing(13)

        header = QHBoxLayout()
        header.setSpacing(9)
        self._status_dot = StatusDot(self, "#F87171", 8, pulse=True)
        header.addWidget(self._status_dot)
        service_title = QLabel("Service management")
        service_title.setObjectName("H2")
        header.addWidget(service_title)
        header.addStretch()
        self.service_state_badge = QLabel("Offline")
        self.service_state_badge.setObjectName("BadgeDanger")
        header.addWidget(self.service_state_badge)
        service_layout.addLayout(header)

        self.service_summary = QLabel("The gateway is not responding on the configured port.")
        self.service_summary.setObjectName("Muted")
        self.service_summary.setWordWrap(True)
        service_layout.addWidget(self.service_summary)
        service_layout.addSpacing(6)

        details = QFrame()
        details.setObjectName("CardSunken")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(13, 11, 13, 11)
        details_layout.setSpacing(4)

        self.lbl_detail_status = self._detail_row(details_layout, "Engine status", "Offline")
        self.lbl_detail_endpoint = self._detail_row(details_layout, "Endpoint", self._client.base_url)
        self.lbl_detail_version = self._detail_row(details_layout, "Engine build", "—")
        self.lbl_detail_check = self._detail_row(details_layout, "Last check", "—")
        service_layout.addWidget(details)
        service_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        self.btn_start = QPushButton("Start")
        self.btn_start.setObjectName("Success")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(lambda: self._service_action("start"))
        actions.addWidget(self.btn_start)

        self.btn_restart = QPushButton("Restart")
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.clicked.connect(lambda: self._service_action("restart"))
        actions.addWidget(self.btn_restart)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("Danger")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(lambda: self._service_action("stop"))
        actions.addWidget(self.btn_stop)

        actions.addStretch()
        self.btn_open_dashboard = QPushButton("Open dashboard")
        self.btn_open_dashboard.setObjectName("Ghost")
        self.btn_open_dashboard.setCursor(Qt.PointingHandCursor)
        self.btn_open_dashboard.clicked.connect(self._open_dashboard)
        actions.addWidget(self.btn_open_dashboard)
        service_layout.addLayout(actions)

        watchdog_row = QHBoxLayout()
        watchdog_row.setSpacing(8)
        self.watchdog_label = QLabel("Auto-restart if the gateway drops")
        self.watchdog_label.setObjectName("Muted")
        watchdog_row.addWidget(self.watchdog_label)
        watchdog_row.addStretch()
        self.btn_watchdog = QPushButton("Enabled" if self.context.settings.bool_of("gateway.watchdog") else "Disabled")
        self.btn_watchdog.setObjectName("Chip")
        self.btn_watchdog.setCheckable(True)
        self.btn_watchdog.setChecked(self.context.settings.bool_of("gateway.watchdog"))
        self.btn_watchdog.setCursor(Qt.PointingHandCursor)
        self.btn_watchdog.toggled.connect(self._toggle_watchdog)
        watchdog_row.addWidget(self.btn_watchdog)
        service_layout.addLayout(watchdog_row)

        row.addWidget(service_card, 6)

        # -- connection -----------------------------------------------------
        conn_card = Card()
        conn_layout = QVBoxLayout(conn_card)
        conn_layout.setContentsMargins(18, 16, 18, 16)
        conn_layout.setSpacing(12)

        conn_title = QLabel("Connection")
        conn_title.setObjectName("H2")
        conn_layout.addWidget(conn_title)

        base_row = QHBoxLayout()
        base_row.setSpacing(8)
        base_caption = QLabel("Base URL")
        base_caption.setObjectName("Muted")
        base_caption.setFixedWidth(76)
        base_row.addWidget(base_caption)
        self.txt_base_url = QLineEdit(self._client.base_url)
        self.txt_base_url.setReadOnly(True)
        self.txt_base_url.setObjectName("Mono")
        base_row.addWidget(self.txt_base_url, 1)
        btn_copy_base = IconButton("copy", self, "Copy base URL")
        btn_copy_base.clicked.connect(lambda: self._copy(self._client.base_url, "Base URL"))
        base_row.addWidget(btn_copy_base)
        conn_layout.addLayout(base_row)

        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        key_caption = QLabel("API key")
        key_caption.setObjectName("Muted")
        key_caption.setFixedWidth(76)
        key_row.addWidget(key_caption)
        self.txt_api_key = QLineEdit(self._client.api_key)
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        self.txt_api_key.setObjectName("Mono")
        key_row.addWidget(self.txt_api_key, 1)
        btn_reveal = IconButton("eye", self, "Show / hide key")
        btn_reveal.clicked.connect(self._toggle_reveal)
        key_row.addWidget(btn_reveal)
        btn_copy_key = IconButton("copy", self, "Copy API key")
        btn_copy_key.clicked.connect(lambda: self._copy(self._client.api_key, "API key"))
        key_row.addWidget(btn_copy_key)
        conn_layout.addLayout(key_row)

        self.snippet_tabs = QTabWidget()
        self.snippet_tabs.setDocumentMode(True)
        self.snippet_tabs.setFixedHeight(152)
        self._snippets: Dict[str, QPlainTextEdit] = {}
        for name, snippet in self._build_snippets().items():
            view = QPlainTextEdit(snippet)
            view.setReadOnly(True)
            view.setObjectName("Mono")
            view.setFixedHeight(96)
            view.setLineWrapMode(QPlainTextEdit.NoWrap)
            self._snippets[name] = view
            self.snippet_tabs.addTab(view, name)
        conn_layout.addWidget(self.snippet_tabs)

        snippet_actions = QHBoxLayout()
        snippet_actions.addStretch()
        btn_copy_snippet = QPushButton("Copy snippet")
        btn_copy_snippet.setObjectName("Ghost")
        btn_copy_snippet.setCursor(Qt.PointingHandCursor)
        btn_copy_snippet.clicked.connect(self._copy_snippet)
        snippet_actions.addWidget(btn_copy_snippet)
        conn_layout.addLayout(snippet_actions)
        conn_layout.addStretch(1)

        row.addWidget(conn_card, 7)
        self._layout.addLayout(row)

    @staticmethod
    def _detail_row(layout: QVBoxLayout, key: str, value: str) -> QLabel:
        """Add a compact key/value row inside the engine details panel."""
        row = QHBoxLayout()
        row.setSpacing(10)
        name = QLabel(key)
        name.setObjectName("Muted")
        name.setFixedWidth(96)
        row.addWidget(name)
        label = QLabel(value)
        label.setObjectName("MonoStrong")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(label, 1)
        layout.addLayout(row)
        return label

    def _build_performance(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Latency trend")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.perf_summary = QLabel("No samples yet")
        self.perf_summary.setObjectName("Muted")
        header.addWidget(self.perf_summary)
        layout.addLayout(header)

        self.sparkline = Sparkline(self, height=110)
        layout.addWidget(self.sparkline)

        stats = QHBoxLayout()
        stats.setSpacing(18)
        self.stat_min = StatTile("Minimum", "—", "Fastest response", "bolt")
        self.stat_avg = StatTile("Average", "—", "Across samples", "activity")
        self.stat_max = StatTile("Maximum", "—", "Slowest response", "alert")
        for tile in (self.stat_min, self.stat_avg, self.stat_max):
            tile.setMinimumHeight(92)
            stats.addWidget(tile)
        layout.addLayout(stats)

        self._layout.addWidget(card)

    def _build_models(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel("Routing matrix")
        title.setObjectName("H2")
        header.addWidget(title)
        self.models_caption = QLabel("Not loaded")
        self.models_caption.setObjectName("Muted")
        header.addWidget(self.models_caption)
        header.addStretch()
        self.model_search = SearchBox("Filter models…", self)
        self.model_search.setFixedWidth(220)
        self.model_search.textChanged.connect(self._filter_models)
        header.addWidget(self.model_search)
        btn_refresh_models = IconButton("refresh", self, "Reload the model catalogue")
        btn_refresh_models.clicked.connect(self.refresh_models)
        header.addWidget(btn_refresh_models)
        layout.addLayout(header)

        self.table_models = QTableWidget(0, 3)
        self.table_models.setHorizontalHeaderLabels(["Model", "Provider", "Context"])
        self.table_models.verticalHeader().setVisible(False)
        self.table_models.setAlternatingRowColors(True)
        self.table_models.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_models.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_models.setShowGrid(False)
        header_view = self.table_models.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_models.setMinimumHeight(220)
        self.table_models.setMaximumHeight(320)
        layout.addWidget(self.table_models)

        self._model_hint = QLabel("")
        self._model_hint.setObjectName("Muted")
        self._model_hint.setWordWrap(True)
        self._model_hint.setVisible(False)
        layout.addWidget(self._model_hint)

        self._layout.addWidget(card)

    def _build_console(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Audit trail")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.console_filter = SearchBox("Filter output…", self)
        self.console_filter.setFixedWidth(200)
        self.console_filter.textChanged.connect(self._render_console)
        header.addWidget(self.console_filter)
        btn_export = QPushButton("Export")
        btn_export.setObjectName("Ghost")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_console)
        header.addWidget(btn_export)
        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("Ghost")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_console)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setLineWrapMode(QTextEdit.NoWrap)
        self.txt_console.setStyleSheet("font-family: 'JetBrains Mono', 'Noto Sans Mono', monospace; font-size: 12px;")
        self.txt_console.setMinimumHeight(180)
        layout.addWidget(self.txt_console)

        self._layout.addWidget(card)
        self.log_message("OmniHub Engine v3.0 initialised — ready.", "success")

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "Gateway Overview"

    def subtitle(self) -> str:
        return "Live health, routing matrix and audit trail for your local AI gateway"

    def header_actions(self) -> Optional[QWidget]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        btn = QPushButton("Refresh")
        btn.setObjectName("Ghost")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.refresh_models)
        layout.addWidget(btn)
        btn_dash = QPushButton("Dashboard")
        btn_dash.setObjectName("Primary")
        btn_dash.setCursor(Qt.PointingHandCursor)
        btn_dash.clicked.connect(self._open_dashboard)
        layout.addWidget(btn_dash)
        return widget

    def on_activated(self) -> None:
        self.txt_base_url.setText(self._client.base_url)
        self.txt_api_key.setText(self._client.api_key)
        self.scroll_area.verticalScrollBar().setValue(0)
        if not self._models_loaded:
            self._models_loaded = True
            self.refresh_models()

    def on_theme_changed(self) -> None:
        self._render_console()

    # -- polling -----------------------------------------------------------

    def poll_health(self) -> None:
        """Kick off a health probe (never overlapping with the previous one)."""
        if self._poll_pending:
            return
        self._poll_pending = True
        client = self._client

        def probe():
            return client.health(timeout=2.5)

        self._tasks.run(probe, self._on_health, self._on_health_error)

    def _on_health(self, result) -> None:
        self._poll_pending = False
        ok, info = result
        self._health_payload = info if isinstance(info, dict) else {}
        self._uptime_samples.append(bool(ok))
        if len(self._uptime_samples) > 400:
            del self._uptime_samples[0]

        latency = float(self._health_payload.get("latency_ms", 0) or 0)
        if ok:
            self._latencies.append(latency)
            if len(self._latencies) > 120:
                del self._latencies[0]
            self.sparkline.set_values(self._latencies)
            self.tile_latency.set_value(f"{int(latency)} ms")
            self.tile_latency.set_caption("Local fast intercept", "info")
            self.tile_status.set_value("Online")
            self.tile_status.set_caption("Gateway is accepting requests", "success")
            self.service_state_badge.setText("Online")
            self.service_state_badge.setObjectName("BadgeSuccess")
            self._status_dot.set_color("#34D399")
            self.service_summary.setText(
                f"Responding on {self._client.base_url} — health status: "
                f"{self._health_payload.get('status', 'ok')}."
            )
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_restart.setEnabled(True)
        else:
            self.tile_latency.set_value("— ms")
            self.tile_latency.set_caption("Gateway unreachable", "danger")
            self.tile_status.set_value("Offline")
            self.tile_status.set_caption("No response from the gateway", "danger")
            self.service_state_badge.setText("Offline")
            self.service_state_badge.setObjectName("BadgeDanger")
            self._status_dot.set_color("#F87171")
            reason = self._health_payload.get("error") or "The gateway is not responding."
            self.service_summary.setText(str(reason))
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_restart.setEnabled(True)

        self._polish_badge(self.service_state_badge)
        self._update_perf_stats()
        self._update_availability()
        self._update_details(ok)
        self.health_changed.emit(bool(ok), dict(self._health_payload))

    def _update_details(self, ok: bool) -> None:
        payload = self._health_payload or {}
        self.lbl_detail_status.setText(
            "Online" if ok else "Offline"
        )
        version = (
            payload.get("version")
            or payload.get("build")
            or payload.get("appVersion")
            or "—"
        )
        self.lbl_detail_version.setText(str(version))
        self.lbl_detail_check.setText(time.strftime("%H:%M:%S"))
        self.lbl_detail_endpoint.setText(self._client.base_url)

    def _on_health_error(self, message: str) -> None:
        self._poll_pending = False
        self.tile_status.set_value("Offline")
        self.tile_status.set_caption("Health probe failed", "danger")
        self.service_state_badge.setText("Offline")
        self.service_state_badge.setObjectName("BadgeDanger")
        self._polish_badge(self.service_state_badge)
        self._update_availability()

    def _update_perf_stats(self) -> None:
        if not self._latencies:
            self.perf_summary.setText("No samples yet")
            return
        values = self._latencies
        low, high = min(values), max(values)
        average = sum(values) / len(values)
        self.stat_min.set_value(f"{int(low)} ms")
        self.stat_avg.set_value(f"{int(average)} ms")
        self.stat_max.set_value(f"{int(high)} ms")
        self.perf_summary.setText(f"{len(values)} samples · last {int(values[-1])} ms")

    def _update_availability(self) -> None:
        if not self._uptime_samples:
            return
        ratio = sum(1 for value in self._uptime_samples if value) / len(self._uptime_samples) * 100
        self.tile_uptime.set_value(f"{ratio:.0f}%")
        self.tile_uptime.set_caption(f"{len(self._uptime_samples)} health probes", "success" if ratio > 95 else "warning")

    @staticmethod
    def _polish_badge(label: QLabel) -> None:
        label.style().unpolish(label)
        label.style().polish(label)

    # -- models ------------------------------------------------------------

    def refresh_models(self) -> None:
        """Fetch the model catalogue in the background."""
        client = self._client
        self.models_caption.setText("Loading…")

        def fetch():
            return client.models(timeout=12.0)

        self._tasks.run(fetch, self._on_models, self._on_models_error)

    def _on_models(self, result) -> None:
        ok, models, reason = result
        if not ok:
            self.models_caption.setText("Catalogue unavailable")
            self.tile_models.set_value("—")
            self.tile_models.set_caption("A registered access key is required", "warning")
            self.model_search.setEnabled(False)
            self._model_hint.setText(reason or "The model catalogue could not be read.")
            self._model_hint.setVisible(True)
            return
        self._model_hint.setVisible(False)
        self.model_search.setEnabled(True)
        self._models = models
        self._filter_models(self._model_filter)
        self.tile_models.set_value(str(len(models)))
        self.tile_models.set_caption("Models exposed by the gateway", "info")

    def _on_models_error(self, message: str) -> None:
        self.models_caption.setText("Catalogue unavailable")

    def _filter_models(self, text: str) -> None:
        self._model_filter = text or ""
        needle = self._model_filter.strip().lower()
        rows = self._models
        if needle:
            rows = [
                model
                for model in self._models
                if needle in str(model.get("id", "")).lower()
                or needle in str(model.get("owned_by", "")).lower()
            ]
        self.table_models.setRowCount(len(rows))
        for row, model in enumerate(rows):
            identifier = str(model.get("id", "—"))
            provider = str(model.get("owned_by") or model.get("provider") or "—")
            context = model.get("context_window") or model.get("context_length") or "—"
            for column, value in enumerate((identifier, provider, context)):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setToolTip(identifier)
                self.table_models.setItem(row, column, item)
        self.models_caption.setText(
            f"{len(rows)} of {len(self._models)} models" if self._models else "No models returned"
        )

    # -- service actions ---------------------------------------------------

    # -- public service API ------------------------------------------------

    def start_service(self) -> None:
        """Start the gateway."""
        self._service_action("start")

    def stop_service(self) -> None:
        """Stop the gateway."""
        self._service_action("stop")

    def restart_service(self) -> None:
        """Restart the gateway."""
        self._service_action("restart")

    def _service_action(self, action: str) -> None:
        logging.getLogger("omnihub").debug(
            "Service action requested: %s\n%s", action, traceback.format_stack()
        )
        if self._busy:
            self.notify.emit("A service action is already running.", "warning")
            return
        if action == "stop" and self.context.settings.bool_of("gateway.confirm_stop", True):
            from PyQt5.QtWidgets import QMessageBox

            answer = QMessageBox.question(
                self,
                "Stop the gateway?",
                "This will terminate the running OmniRoute processes.\n"
                "Any in-flight AI requests will be dropped.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self._set_busy(True)
        self.log.emit(f"Dispatching <b>{action}</b> to the OmniRoute engine…")
        worker = ServiceWorker(
            action,
            base_url=self._client.base_url,
            omniroute_dir=_default_omniroute_dir(),
        )
        worker.result.connect(self._on_service_result)
        self._worker = worker
        worker.start()

    def _on_service_result(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        level = "success" if ok else "danger"
        self.log.emit(f"<span style='color:{self._tone_color(level)}'>{html.escape(message)}</span>")
        self.notify.emit(message, level)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for button in (self.btn_start, self.btn_restart, self.btn_stop):
            button.setEnabled(not busy)
        if busy:
            self.service_state_badge.setText("Working")
            self.service_state_badge.setObjectName("BadgeWarning")
            self._polish_badge(self.service_state_badge)

    def _toggle_watchdog(self, enabled: bool) -> None:
        self.context.settings.set("gateway.watchdog", bool(enabled))
        self.btn_watchdog.setText("Enabled" if enabled else "Disabled")
        self.log.emit(f"Watchdog auto-restart {'enabled' if enabled else 'disabled'}.")

    # -- misc --------------------------------------------------------------

    def _toggle_reveal(self) -> None:
        current = self.txt_api_key.echoMode()
        self.txt_api_key.setEchoMode(
            QLineEdit.Normal if current == QLineEdit.Password else QLineEdit.Password
        )

    def _copy(self, text: str, what: str) -> None:
        if copy_to_clipboard(text):
            self.notify.emit(f"{what} copied to the clipboard.", "success")
            self.log.emit(f"Copied {html.escape(what.lower())} to the clipboard.")
        else:
            self.notify.emit("Could not access the clipboard.", "danger")

    def _copy_snippet(self) -> None:
        widget = self.snippet_tabs.currentWidget()
        if widget is None:
            return
        if copy_to_clipboard(widget.toPlainText()):
            self.notify.emit("Snippet copied to the clipboard.", "success")

    def _build_snippets(self) -> Dict[str, str]:
        base = self._client.base_url
        key = self._client.api_key or "local"
        return {
            "cURL": (
                f"curl {base}/v1/chat/completions \\\n"
                f"  -H 'Content-Type: application/json' \\\n"
                f"  -H 'Authorization: Bearer {key}' \\\n"
                f"  -d '{{\"model\":\"auto\",\"messages\":[{{\"role\":\"user\",\"content\":\"Hello\"}}]}}'"
            ),
            "Python": (
                "import requests\n\n"
                f"response = requests.post(\n"
                f"    \"{base}/v1/chat/completions\",\n"
                f"    headers={{\"Authorization\": \"Bearer {key}\"}},\n"
                f"    json={{\"model\": \"auto\", \"messages\": [{{\"role\": \"user\", \"content\": \"Hello\"}}]}},\n"
                f"    timeout=60,\n"
                f")\n"
                f"print(response.json()[\"choices\"][0][\"message\"][\"content\"])"
            ),
            "JavaScript": (
                "const res = await fetch(\n"
                f"  \"{base}/v1/chat/completions\",\n"
                "  {\n"
                "    method: \"POST\",\n"
                "    headers: {\n"
                "      \"Content-Type\": \"application/json\",\n"
                f"      \"Authorization\": \"Bearer {key}\",\n"
                "    },\n"
                "    body: JSON.stringify({\n"
                "      model: \"auto\",\n"
                "      messages: [{ role: \"user\", content: \"Hello\" }],\n"
                "    }),\n"
                "  }\n"
                ");\n"
                "const data = await res.json();\n"
                "console.log(data.choices[0].message.content);"
            ),
        }

    def _open_dashboard(self) -> None:
        import subprocess

        url = f"{self._client.base_url}/dashboard"
        try:
            subprocess.Popen(["xdg-open", url])
            self.log.emit(f"Opened <code>{html.escape(url)}</code> in the default browser.")
        except Exception as exc:  # noqa: BLE001
            self.notify.emit(f"Could not open the dashboard: {exc}", "danger")

    # -- console -----------------------------------------------------------

    def append_log(self, message: str) -> None:
        """Append a raw (already formatted) line to the audit trail."""
        self._console_lines.append(message)
        if len(self._console_lines) > 2000:
            del self._console_lines[0]
        self._render_console()

    def log_message(self, message: str, tone: str = "info") -> None:
        stamp = time.strftime("%H:%M:%S")
        color = self._tone_color(tone)
        self.append_log(
            f"<span style='color:#5A6478'>[{stamp}]</span> "
            f"<span style='color:{color}'>{html.escape(message)}</span>"
        )

    def _tone_color(self, tone: str) -> str:
        theme = self.context.theme
        palette = theme.palette
        return {
            "success": palette.success,
            "warning": palette.warning,
            "danger": palette.danger,
            "info": palette.accent_text,
            "muted": palette.text_muted,
        }.get(tone, palette.text)

    def _render_console(self) -> None:
        needle = (self.console_filter.text() or "").strip().lower()
        lines = self._console_lines
        if needle:
            stripped = [re.sub(r"<[^>]+>", "", line).lower() for line in lines]
            lines = [line for line, text in zip(lines, stripped) if needle in text]
        self.txt_console.setHtml("<br>".join(lines) if lines else
                                 "<span style='color:#5A6478'>No console output yet.</span>")
        scrollbar = self.txt_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_console(self) -> None:
        self._console_lines.clear()
        self._render_console()

    def _export_console(self) -> None:
        import os

        from ..paths import LOG_DIR

        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            target = LOG_DIR / f"audit-{time.strftime('%Y%m%d-%H%M%S')}.txt"
            plain = "\n".join(re.sub(r"<[^>]+>", "", line) for line in self._console_lines)
            target.write_text(plain, encoding="utf-8")
            self.notify.emit(f"Audit trail exported to {target.name}.", "success")
        except OSError as exc:
            self.notify.emit(f"Export failed: {exc}", "danger")

    def shutdown(self) -> None:
        """Stop any running service worker so the app can exit cleanly."""
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            try:
                worker.cancel()
            except Exception:
                pass
            worker.wait(3000)


def _default_omniroute_dir() -> str:
    from ..workers import DEFAULT_OMNIROUTE_DIR

    return DEFAULT_OMNIROUTE_DIR
