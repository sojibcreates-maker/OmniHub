"""AI Studio — a streaming chat workbench wired to the local gateway."""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

from PyQt5.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFontMetrics

from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..workers import ChatWorker, TaskGroup
from .base import Page


__all__ = ["AIStudioPage"]


SYSTEM_PRESETS: Dict[str, str] = {
    "Balanced assistant": "",
    "Senior Python engineer": "You are a senior Python engineer. Write precise, production-quality code with clear explanations.",
    "Technical writer": "You are a concise technical writer. Prefer short sentences, structured output and concrete examples.",
    "SQL analyst": "You are an SQL expert. Always answer with runnable queries and explain indexing implications.",
    "Product strategist": "You are a pragmatic product strategist. Challenge assumptions and prioritise ruthlessly.",
}

#: Offered when the gateway catalogue cannot be read (it needs a registered
#: access key).  The model field stays editable, so any id can still be used.
FALLBACK_MODELS: List[str] = [
    "auto",
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet",
    "claude-3-5-haiku",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "deepseek-chat",
    "deepseek-coder",
    "llama-3.3-70b",
    "qwen-max",
    "mistral-large",
]


class ChatBubble(QFrame):
    """A single message bubble."""

    def __init__(
        self,
        sender: str,
        text: str = "",
        is_user: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._is_user = is_user
        self._sizing = False
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(5)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        self._sender = QLabel(sender)
        self._sender.setObjectName("SectionLabel")
        meta_row.addWidget(self._sender)
        self._meta = QLabel("")
        self._meta.setObjectName("Faint")
        meta_row.addWidget(self._meta)
        meta_row.addStretch()
        layout.addLayout(meta_row)

        self._body = QLabel(text)
        self._body.setTextFormat(Qt.PlainText)
        self._body.setWordWrap(True)
        self._body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._body.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(self._body)
        self.set_text(text)

    def set_text(self, text: str) -> None:
        self._body.setText(text or "")
        self._resize_body()

    def append_text(self, text: str) -> None:
        self._body.setText(self._body.text() + text)
        self._resize_body()

    def set_meta(self, text: str) -> None:
        self._meta.setText(text)

    def set_sender(self, text: str) -> None:
        self._sender.setText(text)

    def _resize_body(self) -> None:
        """Size the bubble to hug its text, wrapping at 78 % of the column.

        The width and height are pinned explicitly because a word-wrapped
        label cannot report a sensible height to a layout on its own.  The
        wrapped height is computed from the font metrics (not from
        ``heightForWidth``) so that re-running this method is idempotent and
        cannot feed back into an ever-growing bubble.
        """
        if self._sizing:
            return
        parent = self.parentWidget()
        available = parent.width() if parent is not None else 760
        if available <= 0:
            return

        self._sizing = True
        try:
            max_width = int(available * 0.78)
            metrics = QFontMetrics(self._body.font())
            text = self._body.text()
            natural = metrics.horizontalAdvance(text) + 6
            width = max(140, min(natural, max_width))

            bounds = metrics.boundingRect(
                QRect(0, 0, width, 10000), Qt.TextWordWrap, text
            )
            height = max(metrics.height(), bounds.height())

            if self._body.width() != width:
                self._body.setFixedWidth(width)
            target_height = int(height) + 2
            if self._body.height() != target_height:
                self._body.setFixedHeight(target_height)
            if self.maximumWidth() != max_width:
                self.setMaximumWidth(max_width)
            self.updateGeometry()
        finally:
            self._sizing = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Defer the relayout so it never runs inside the resize notification.
        QTimer.singleShot(0, self._resize_body)

    def text(self) -> str:
        return self._body.text()


class AIStudioPage(Page):
    """Interactive prompt tester with streaming responses."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._client = context.api
        self._worker: Optional[ChatWorker] = None
        self._history: List[Dict[str, str]] = []
        self._bubble: Optional[ChatBubble] = None
        self._started_at = 0.0
        self._models: List[str] = []
        self._total_tokens = 0
        self._tasks = TaskGroup(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        root.addWidget(self._build_controls())

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.chat_layout = QVBoxLayout(self.container)
        self.chat_layout.setContentsMargins(4, 4, 10, 4)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(self.container)
        root.addWidget(self.scroll_area, 1)

        root.addWidget(self._build_composer())

        self._add_system_bubble(
            "OmniHub assistant",
            "Connected to the local OmniRoute router. Ask anything — responses stream in "
            "as the model produces them.",
        )

    # ------------------------------------------------------------------ UI

    def _build_controls(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(10)

        model_label = QLabel("Model")
        model_label.setObjectName("Muted")
        layout.addWidget(model_label)
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setInsertPolicy(QComboBox.NoInsert)
        self.cb_model.addItems(FALLBACK_MODELS)
        self.cb_model.setFixedWidth(190)
        self.cb_model.setToolTip("Type a model id or pick one from the discovered catalogue.")
        self.cb_model.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.cb_model)

        sys_label = QLabel("System")
        sys_label.setObjectName("Muted")
        layout.addWidget(sys_label)
        self.cb_preset = QComboBox()
        self.cb_preset.addItems(list(SYSTEM_PRESETS.keys()))
        self.cb_preset.setFixedWidth(190)
        self.cb_preset.currentTextChanged.connect(self._apply_preset)
        layout.addWidget(self.cb_preset)

        self.txt_system = QLineEdit()
        self.txt_system.setPlaceholderText("Optional system instruction…")
        self.txt_system.textChanged.connect(self._on_system_changed)
        layout.addWidget(self.txt_system, 1)

        temp_label = QLabel("Temp")
        temp_label.setObjectName("Muted")
        layout.addWidget(temp_label)
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.1)
        self.spin_temp.setValue(0.7)
        self.spin_temp.setFixedWidth(72)
        self.spin_temp.setToolTip("Sampling temperature")
        layout.addWidget(self.spin_temp)

        return card

    def _build_composer(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText(
            "Ask the gateway anything…   (Enter to send, Shift+Enter for a new line)"
        )
        self.txt_prompt.setFixedHeight(74)
        self.txt_prompt.setAcceptRichText(False)
        self.txt_prompt.installEventFilter(self)
        row.addWidget(self.txt_prompt, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(7)
        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("Primary")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setFixedHeight(34)
        self.btn_send.clicked.connect(self.send)
        buttons.addWidget(self.btn_send)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("Danger")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setFixedHeight(31)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop)
        buttons.addWidget(self.btn_stop)
        row.addLayout(buttons)
        layout.addLayout(row)

        status = QHBoxLayout()
        status.setSpacing(12)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("Muted")
        status.addWidget(self.lbl_status)
        status.addStretch()

        self.lbl_counter = QLabel("0 tokens")
        self.lbl_counter.setObjectName("Faint")
        status.addWidget(self.lbl_counter)

        btn_clear = QPushButton("New chat")
        btn_clear.setObjectName("Ghost")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_chat)
        status.addWidget(btn_clear)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("Ghost")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self.export_chat)
        status.addWidget(btn_export)
        layout.addLayout(status)

        return card

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "AI Studio"

    def subtitle(self) -> str:
        return "Streaming chat against the OmniRoute auto-fallback matrix"

    def header_actions(self) -> Optional[QWidget]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        btn = QPushButton("Reload models")
        btn.setObjectName("Ghost")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.refresh_models)
        layout.addWidget(btn)
        return widget

    def on_activated(self) -> None:
        if not self._models:
            self.refresh_models()

    def _on_model_changed(self, text: str) -> None:
        self.lbl_status.setText(f"Model: {text or 'auto'}")

    def _on_system_changed(self, text: str) -> None:
        # Keep the preset dropdown in sync when the field is edited manually.
        for name, value in SYSTEM_PRESETS.items():
            if value == text:
                if self.cb_preset.currentText() != name:
                    self.cb_preset.blockSignals(True)
                    self.cb_preset.setCurrentText(name)
                    self.cb_preset.blockSignals(False)
                break

    def _apply_preset(self, name: str) -> None:
        self.txt_system.setText(SYSTEM_PRESETS.get(name, ""))

    # -- models ------------------------------------------------------------

    def refresh_models(self) -> None:
        client = self._client

        def fetch():
            return client.models(timeout=12.0)

        self._tasks.run(fetch, self._on_models, lambda _msg: self.notify.emit("Could not load models.", "danger"))

    def _on_models(self, result) -> None:
        ok, models, reason = result
        if not ok:
            self.notify.emit(
                reason or "The model catalogue is unavailable; type a model id instead.",
                "warning",
            )
            self._populate_models([])
            return
        self._populate_models([str(model.get("id")) for model in models if model.get("id")])

    def _populate_models(self, models: List[str]) -> None:
        current = self.cb_model.currentText().strip()
        self.cb_model.blockSignals(True)
        self.cb_model.clear()
        self.cb_model.addItem("auto")
        for model in models or FALLBACK_MODELS:
            self.cb_model.addItem(model)
        self.cb_model.setCurrentText(current or "auto")
        self.cb_model.blockSignals(False)
        self.lbl_status.setText(f"{len(models)} models available")

    # -- chat --------------------------------------------------------------

    def _add_system_bubble(self, sender: str, text: str) -> None:
        self._insert_bubble(ChatBubble(sender, text, is_user=False))

    def _insert_bubble(self, bubble: ChatBubble) -> None:
        """Insert a bubble, aligning user messages to the right."""
        self._style_bubble(bubble)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        if bubble._is_user:
            row.addStretch(1)
            row.addWidget(bubble, 0, Qt.AlignTop | Qt.AlignRight)
        else:
            row.addWidget(bubble, 0, Qt.AlignTop | Qt.AlignLeft)
            row.addStretch(1)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _style_bubble(self, bubble: ChatBubble) -> None:
        palette = self.context.theme.palette
        if bubble._is_user:
            bubble.setStyleSheet(
                "ChatBubble {"
                f" background-color: {palette.accent_soft};"
                f" border: 1px solid {palette.accent_border};"
                " border-radius: 14px;"
                " border-bottom-right-radius: 4px;"
                "}"
            )
            bubble._sender.setStyleSheet(f"color: {palette.accent_text};")
        else:
            bubble.setStyleSheet(
                "ChatBubble {"
                f" background-color: {palette.surface_alt};"
                f" border: 1px solid {palette.border};"
                " border-radius: 14px;"
                " border-bottom-left-radius: 4px;"
                "}"
            )
            bubble._sender.setStyleSheet(f"color: {palette.text_muted};")

    def _scroll_to_bottom(self) -> None:
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(30, self._scroll_to_bottom_now)

    def _scroll_to_bottom_now(self) -> None:
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def send(self) -> None:
        prompt = self.txt_prompt.toPlainText().strip()
        if not prompt:
            return
        if self._worker is not None and self._worker.isRunning():
            self.notify.emit("A response is already streaming.", "warning")
            return

        model = self.cb_model.currentText().strip() or "auto"
        system_prompt = self.txt_system.text().strip()

        user_bubble = ChatBubble("You", prompt, is_user=True)
        self._insert_bubble(user_bubble)

        self._history.append({"role": "user", "content": prompt})
        self.txt_prompt.clear()

        assistant = ChatBubble(f"OmniRoute · {model}", "", is_user=False)
        self._insert_bubble(assistant)
        self._bubble = assistant
        self._started_at = time.time()
        self._scroll_to_bottom()

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self._history)

        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText(f"Streaming from {model}…")

        self._worker = ChatWorker(
            self._client,
            messages,
            model=model,
            temperature=self.spin_temp.value(),
        )
        self._worker.chunk.connect(self._on_chunk)
        self._worker.completed.connect(self._on_complete)
        self._worker.failed.connect(self._on_failed)
        self._worker.stopped.connect(self._on_stopped)
        self._worker.start()

    def stop(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self.lbl_status.setText("Stopping…")

    def _on_chunk(self, text: str) -> None:
        if self._bubble is not None:
            self._bubble.append_text(text)
            self._scroll_to_bottom()

    def _on_complete(self, payload: Dict) -> None:
        elapsed = float(payload.get("elapsed", 0.0))
        text = payload.get("text", "")
        usage = payload.get("usage") or {}
        tokens = 0
        if isinstance(usage, dict):
            tokens = int(usage.get("total_tokens") or usage.get("completion_tokens") or 0)
        self._total_tokens += tokens

        if self._bubble is not None:
            self._bubble.set_meta(f"{elapsed:.2f}s" + (f" · {tokens} tokens" if tokens else ""))
            self._bubble.set_text(text)
            self._history.append({"role": "assistant", "content": text})

        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._worker = None
        self.lbl_status.setText(f"Completed in {elapsed:.2f}s")
        self.lbl_counter.setText(f"~{self._total_tokens} tokens")
        self._scroll_to_bottom()
        self.log.emit(f"AI request completed in {elapsed:.2f}s ({len(text)} chars).")

    def _on_failed(self, message: str) -> None:
        if self._bubble is not None and not self._bubble.text().strip():
            self._bubble.set_text(f"⚠ {message}")
            self._bubble.set_meta("failed")
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._worker = None
        self.lbl_status.setText("Request failed")
        self.notify.emit(message, "danger")
        self.log.emit(f"AI request failed: {message}")

    def _on_stopped(self) -> None:
        if self._bubble is not None:
            text = self._bubble.text()
            if text.strip():
                self._history.append({"role": "assistant", "content": text})
            self._bubble.set_meta("stopped")
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._worker = None
        self.lbl_status.setText("Stopped")

    # -- conversation management ------------------------------------------

    def clear_chat(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.stop()
        self._history.clear()
        self._total_tokens = 0
        self._bubble = None
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
                continue
            row = item.layout()
            if row is not None:
                for index in reversed(range(row.count())):
                    child = row.itemAt(index).widget()
                    if child is not None:
                        child.setParent(None)
                        child.deleteLater()
        self._add_system_bubble(
            "OmniHub assistant",
            "Fresh conversation. The router will pick the best available provider for each turn.",
        )
        self.lbl_status.setText("Ready")
        self.lbl_counter.setText("0 tokens")
        self.notify.emit("Started a new conversation.", "success")

    def export_chat(self) -> None:
        from ..paths import DATA_DIR

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            target = DATA_DIR / f"conversation-{time.strftime('%Y%m%d-%H%M%S')}.json"
            target.write_text(
                json.dumps(
                    {"exported_at": time.time(), "model": self.cb_model.currentText(), "messages": self._history},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.notify.emit(f"Conversation exported to {target.name}.", "success")
        except OSError as exc:
            self.notify.emit(f"Export failed: {exc}", "danger")

    # -- events ------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        from PyQt5.QtCore import QEvent

        if obj is self.txt_prompt and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self.send()
                    return True
        return super().eventFilter(obj, event)

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
