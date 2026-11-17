"""System Radar — live host telemetry, per-core meters and process activity."""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..workers import SystemSampler
from ..widgets import Card, RingGauge, Sparkline, _Bar
from .base import Page

__all__ = ["SystemRadarPage"]


def _format_bytes(value: float) -> str:
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < step:
            return f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} PB"


class SystemRadarPage(Page):
    """Real-time hardware and runtime telemetry."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._sampler = SystemSampler(top_process_count=6)
        self._last_snapshot: Dict = {}

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

        self._build_gauges()
        self._build_cores()
        self._build_network()
        self._build_processes()
        self._build_host()
        self._layout.addStretch()

    # ------------------------------------------------------------------ UI

    def _build_gauges(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Resource utilisation")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.gauges_caption = QLabel("Live")
        self.gauges_caption.setObjectName("Muted")
        header.addWidget(self.gauges_caption)
        layout.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.gauge_cpu = RingGauge(self, 104, 9, "CPU")
        self.gauge_mem = RingGauge(self, 104, 9, "Memory")
        self.gauge_disk = RingGauge(self, 104, 9, "Storage")
        self.gauge_swap = RingGauge(self, 104, 9, "Swap")
        for gauge in (self.gauge_cpu, self.gauge_mem, self.gauge_disk, self.gauge_swap):
            row.addWidget(gauge, 1)
        layout.addLayout(row)

        self._layout.addWidget(card)

    def _build_cores(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        header = QHBoxLayout()
        title = QLabel("Processor cores")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.cores_caption = QLabel("—")
        self.cores_caption.setObjectName("Muted")
        header.addWidget(self.cores_caption)
        layout.addLayout(header)

        self.core_bars: List[_Bar] = []
        self.core_grid = QVBoxLayout()
        self.core_grid.setSpacing(6)
        layout.addLayout(self.core_grid)
        self._layout.addWidget(card)

    def _build_network(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        header = QHBoxLayout()
        title = QLabel("Network throughput")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.net_caption = QLabel("—")
        self.net_caption.setObjectName("Muted")
        header.addWidget(self.net_caption)
        layout.addLayout(header)

        self.net_spark = Sparkline(self, height=96, color="#22D3EE")
        layout.addWidget(self.net_spark)

        legend = QHBoxLayout()
        legend.setSpacing(18)
        self.lbl_rx = QLabel("▼ Download  —")
        self.lbl_rx.setObjectName("Info")
        self.lbl_tx = QLabel("▲ Upload  —")
        self.lbl_tx.setObjectName("Accent")
        legend.addWidget(self.lbl_rx)
        legend.addWidget(self.lbl_tx)
        legend.addStretch()
        layout.addLayout(legend)

        self._layout.addWidget(card)

    def _build_processes(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        header = QHBoxLayout()
        title = QLabel("Top processes")
        title.setObjectName("H2")
        header.addWidget(title)
        header.addStretch()
        self.proc_caption = QLabel("—")
        self.proc_caption.setObjectName("Muted")
        header.addWidget(self.proc_caption)
        layout.addLayout(header)

        self.table_processes = QTableWidget(0, 4)
        self.table_processes.setHorizontalHeaderLabels(["Process", "PID", "CPU", "Memory"])
        self.table_processes.verticalHeader().setVisible(False)
        self.table_processes.setAlternatingRowColors(True)
        self.table_processes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_processes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_processes.setShowGrid(False)
        header_view = self.table_processes.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table_processes.setMinimumHeight(200)
        self.table_processes.setMaximumHeight(280)
        layout.addWidget(self.table_processes)

        self._layout.addWidget(card)

    def _build_host(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        title = QLabel("Host specification")
        title.setObjectName("H2")
        layout.addWidget(title)

        self.host_grid = QHBoxLayout()
        self.host_grid.setSpacing(16)
        self.host_left = QLabel()
        self.host_left.setObjectName("Muted")
        self.host_left.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.host_right = QLabel()
        self.host_right.setObjectName("Muted")
        self.host_right.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.host_grid.addWidget(self.host_left, 1)
        self.host_grid.addWidget(self.host_right, 1)
        layout.addLayout(self.host_grid)

        self._layout.addWidget(card)

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "System Radar"

    def subtitle(self) -> str:
        return "Live processor, memory, storage and process telemetry for this machine"

    def on_activated(self) -> None:
        self.scroll_area.verticalScrollBar().setValue(0)
        self.refresh()

    def on_theme_changed(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        """Sample the host and repaint every telemetry widget."""
        snapshot = self._sampler.sample()
        self._last_snapshot = snapshot

        self.gauge_cpu.set_value(snapshot["cpu_percent"])
        self.gauge_mem.set_value(snapshot["mem_percent"])
        self.gauge_swap.set_value(snapshot["swap_percent"])

        disks = snapshot.get("disks") or []
        if disks:
            root_disk = max(disks, key=lambda item: item["total"])
            self.gauge_disk.set_value(root_disk["percent"])
        else:
            self.gauge_disk.set_value(0.0)

        self._update_cores(snapshot)
        self._update_network(snapshot)
        self._update_processes(snapshot)
        self._update_host(snapshot)

    def _update_cores(self, snapshot: Dict) -> None:
        cores: List[float] = snapshot.get("cpu_per_core") or []
        palette = self.context.theme.palette
        while len(self.core_bars) < len(cores):
            bar = _Bar(palette.accent)
            self.core_bars.append(bar)
            row = QHBoxLayout()
            row.setSpacing(8)
            label = QLabel(f"Core {len(self.core_bars)}")
            label.setObjectName("Faint")
            label.setFixedWidth(52)
            row.addWidget(label)
            row.addWidget(bar, 1)
            value = QLabel("0%")
            value.setObjectName("Faint")
            value.setFixedWidth(44)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(value)
            self.core_grid.addLayout(row)
            bar.value_label = value  # type: ignore[attr-defined]

        for index, bar in enumerate(self.core_bars):
            if index < len(cores):
                bar.set_value(cores[index])
                bar.setVisible(True)
                value_label = getattr(bar, "value_label", None)
                if value_label is not None:
                    value_label.setText(f"{cores[index]:.0f}%")
            else:
                bar.setVisible(False)

        load = snapshot.get("load_average") or (0.0, 0.0, 0.0)
        self.cores_caption.setText(
            f"{len(cores)} logical cores · load {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
        )

    def _update_network(self, snapshot: Dict) -> None:
        rx = snapshot.get("net_rx_rate", 0.0)
        tx = snapshot.get("net_tx_rate", 0.0)
        self.lbl_rx.setText(f"▼ Download  {_format_bytes(rx)}/s")
        self.lbl_tx.setText(f"▲ Upload  {_format_bytes(tx)}/s")
        history = snapshot.get("net_history") or []
        if history:
            self.net_spark.set_values([item[0] for item in history])
        self.net_caption.setText(f"{len(history)} samples")

    def _update_processes(self, snapshot: Dict) -> None:
        processes = snapshot.get("top_processes") or []
        self.table_processes.setRowCount(len(processes))
        for row, proc in enumerate(processes):
            values = (
                str(proc.get("name", "?")),
                str(proc.get("pid", "")),
                f"{proc.get('cpu', 0.0):.1f}%",
                _format_bytes(proc.get("memory", 0.0)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 2:
                    try:
                        cpu = float(proc.get("cpu", 0.0))
                    except (TypeError, ValueError):
                        cpu = 0.0
                    if cpu > 50:
                        item.setForeground(QColor(self.context.theme.palette.danger))
                    elif cpu > 20:
                        item.setForeground(QColor(self.context.theme.palette.warning))
                self.table_processes.setItem(row, column, item)
        self.proc_caption.setText(f"{len(processes)} shown")

    def _update_host(self, snapshot: Dict) -> None:
        host = snapshot.get("host") or {}
        uptime = snapshot.get("uptime_seconds", 0)
        hours, remainder = divmod(int(uptime), 3600)
        minutes = remainder // 60

        memory = snapshot.get("mem_total", 0)
        lines_left = [
            f"<b>Distribution</b><br/>{host.get('pretty_name', host.get('system', 'Unknown'))}",
            f"<b>Kernel</b><br/>{host.get('system', '')} {host.get('release', '')}",
            f"<b>Architecture</b><br/>{host.get('machine', '')}",
            f"<b>Uptime</b><br/>{hours}h {minutes}m",
        ]
        lines_right = [
            f"<b>Processor</b><br/>{host.get('cpu_model', 'Unknown')}",
            f"<b>Logical cores</b><br/>{snapshot.get('cpu_count', 0)}",
            f"<b>Memory</b><br/>{_format_bytes(memory)}",
            f"<b>Runtime</b><br/>Python {host.get('python', '')}",
        ]
        self.host_left.setText("<br/><br/>".join(lines_left))
        self.host_right.setText("<br/><br/>".join(lines_right))
