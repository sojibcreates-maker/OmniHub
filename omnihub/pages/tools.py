"""Scratchpad & Utilities — a persistent notepad with developer tool drawers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..paths import NOTES_BACKUP, NOTES_FILE
from .base import Page
from .common import copy_to_clipboard

__all__ = ["ToolsPage"]


class ToolsPage(Page):
    """Notepad plus a drawer of common developer utilities."""

    log = pyqtSignal(str)
    notify = pyqtSignal(str, str)

    def __init__(self, context: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._saving = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        root.addWidget(self._build_utilities())
        root.addWidget(self._build_editor(), 1)
        root.addWidget(self._build_launchers())

    # ------------------------------------------------------------------ UI

    def _build_utilities(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setFixedHeight(288)

        tabs.addTab(self._build_json_tab(), "JSON")
        tabs.addTab(self._build_encode_tab(), "Encode")
        tabs.addTab(self._build_hash_tab(), "Hash")
        tabs.addTab(self._build_text_tab(), "Text")
        return tabs

    def _build_json_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(8)
        btn_format = QPushButton("Pretty print")
        btn_format.setObjectName("Primary")
        btn_format.setCursor(Qt.PointingHandCursor)
        btn_format.clicked.connect(self._json_pretty)
        row.addWidget(btn_format)

        btn_minify = QPushButton("Minify")
        btn_minify.setCursor(Qt.PointingHandCursor)
        btn_minify.clicked.connect(self._json_minify)
        row.addWidget(btn_minify)

        btn_sort = QPushButton("Sort keys")
        btn_sort.setCursor(Qt.PointingHandCursor)
        btn_sort.clicked.connect(self._json_sort)
        row.addWidget(btn_sort)

        btn_validate = QPushButton("Validate")
        btn_validate.setCursor(Qt.PointingHandCursor)
        btn_validate.clicked.connect(self._json_validate)
        row.addWidget(btn_validate)
        row.addStretch()

        self.json_status = QLabel("Ready")
        self.json_status.setObjectName("Muted")
        row.addWidget(self.json_status)
        layout.addLayout(row)

        self.json_input = QPlainTextEdit()
        self.json_input.setPlaceholderText(
            'Paste a JSON document here, e.g. {"model": "auto", "stream": true}'
        )
        self.json_input.setObjectName("Mono")
        layout.addWidget(self.json_input, 1)

        btn_apply = QPushButton("Send to scratchpad")
        btn_apply.setObjectName("Ghost")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.clicked.connect(self._json_to_scratchpad)
        layout.addWidget(btn_apply, 0, Qt.AlignLeft)
        return widget

    def _build_encode_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.enc_mode = QComboBox()
        self.enc_mode.addItems(
            ["Base64 encode", "Base64 decode", "URL encode", "URL decode", "Hex encode", "Escape unicode"]
        )
        self.enc_mode.setFixedWidth(180)
        row.addWidget(self.enc_mode)

        btn_run = QPushButton("Run")
        btn_run.setObjectName("Primary")
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.clicked.connect(self._encode_run)
        row.addWidget(btn_run)

        btn_swap = QPushButton("Swap")
        btn_swap.setObjectName("Ghost")
        btn_swap.setCursor(Qt.PointingHandCursor)
        btn_swap.clicked.connect(self._encode_swap)
        row.addWidget(btn_swap)
        row.addStretch()

        self.enc_status = QLabel("Ready")
        self.enc_status.setObjectName("Muted")
        row.addWidget(self.enc_status)
        layout.addLayout(row)

        self.enc_input = QPlainTextEdit()
        self.enc_input.setPlaceholderText("Input…")
        self.enc_input.setObjectName("Mono")
        layout.addWidget(self.enc_input, 1)

        self.enc_output = QPlainTextEdit()
        self.enc_output.setPlaceholderText("Output…")
        self.enc_output.setObjectName("Mono")
        self.enc_output.setReadOnly(True)
        layout.addWidget(self.enc_output, 1)
        return widget

    def _build_hash_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.hash_algo = QComboBox()
        self.hash_algo.addItems(["sha256", "sha1", "md5", "sha512"])
        self.hash_algo.setFixedWidth(140)
        row.addWidget(self.hash_algo)

        btn_run = QPushButton("Hash input")
        btn_run.setObjectName("Primary")
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.clicked.connect(self._hash_run)
        row.addWidget(btn_run)
        row.addStretch()

        self.hash_status = QLabel("Ready")
        self.hash_status.setObjectName("Muted")
        row.addWidget(self.hash_status)
        layout.addLayout(row)

        self.hash_input = QPlainTextEdit()
        self.hash_input.setPlaceholderText("Input…")
        self.hash_input.setObjectName("Mono")
        layout.addWidget(self.hash_input, 1)

        self.hash_output = QPlainTextEdit()
        self.hash_output.setPlaceholderText("Digest…")
        self.hash_output.setObjectName("Mono")
        self.hash_output.setReadOnly(True)
        layout.addWidget(self.hash_output, 1)
        return widget

    def _build_text_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.text_action = QComboBox()
        self.text_action.addItems(
            [
                "Uppercase",
                "Lowercase",
                "Title case",
                "Slugify",
                "Strip whitespace",
                "Remove duplicates",
                "Sort lines",
                "Escape regex",
                "Escape quotes",
            ]
        )
        self.text_action.setFixedWidth(190)
        row.addWidget(self.text_action)

        btn_run = QPushButton("Run")
        btn_run.setObjectName("Primary")
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.clicked.connect(self._text_run)
        row.addWidget(btn_run)
        row.addStretch()

        self.text_status = QLabel("Ready")
        self.text_status.setObjectName("Muted")
        row.addWidget(self.text_status)
        layout.addLayout(row)

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Input…")
        self.text_input.setObjectName("Mono")
        layout.addWidget(self.text_input, 1)

        self.text_output = QPlainTextEdit()
        self.text_output.setPlaceholderText("Output…")
        self.text_output.setObjectName("Mono")
        self.text_output.setReadOnly(True)
        layout.addWidget(self.text_output, 1)
        return widget

    def _build_editor(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(9)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        title = QLabel("Scratchpad")
        title.setObjectName("H2")
        toolbar.addWidget(title)

        self.lbl_saved = QLabel("")
        self.lbl_saved.setObjectName("Faint")
        toolbar.addWidget(self.lbl_saved)
        toolbar.addStretch()

        self.chk_wrap = QCheckBox("Wrap")
        self.chk_wrap.setChecked(self.context.settings.bool_of("scratchpad.wrap", True))
        self.chk_wrap.setToolTip("Soft-wrap long lines")
        self.chk_wrap.toggled.connect(self._toggle_wrap)
        toolbar.addWidget(self.chk_wrap)

        lbl_size = QLabel("Size")
        lbl_size.setObjectName("Muted")
        toolbar.addWidget(lbl_size)
        self.spin_font = QSpinBox()
        self.spin_font.setRange(9, 24)
        self.spin_font.setValue(self.context.settings.int_of("scratchpad.font_size", 13))
        self.spin_font.setFixedWidth(62)
        self.spin_font.setToolTip("Editor font size")
        self.spin_font.valueChanged.connect(self._font_size_changed)
        toolbar.addWidget(self.spin_font)

        self.txt_find = QLineEdit()
        self.txt_find.setPlaceholderText("Find in scratchpad…")
        self.txt_find.setFixedWidth(200)
        self.txt_find.setClearButtonEnabled(True)
        self.txt_find.textChanged.connect(self._find)
        toolbar.addWidget(self.txt_find)

        btn_next = QPushButton("Next")
        btn_next.setObjectName("Ghost")
        btn_next.setCursor(Qt.PointingHandCursor)
        btn_next.clicked.connect(lambda: self._find(direction=True))
        toolbar.addWidget(btn_next)

        btn_copy = QPushButton("Copy")
        btn_copy.setObjectName("Ghost")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.clicked.connect(self._copy_scratchpad)
        toolbar.addWidget(btn_copy)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("Ghost")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_scratchpad)
        toolbar.addWidget(btn_clear)
        layout.addLayout(toolbar)

        self.txt_notes = QTextEdit()
        self.txt_notes.setObjectName("Mono")
        self.txt_notes.setAcceptRichText(False)
        self.txt_notes.setPlaceholderText(
            "Paste prompts, JSON payloads, API secrets or temporary notes. "
            "Everything is saved automatically to your OmniHub config folder."
        )
        self.txt_notes.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.txt_notes, 1)

        footer = QHBoxLayout()
        footer.setSpacing(16)
        self.lbl_stats = QLabel("0 characters")
        self.lbl_stats.setObjectName("Faint")
        footer.addWidget(self.lbl_stats)
        footer.addStretch()
        self.lbl_path = QLabel(str(NOTES_FILE))
        self.lbl_path.setObjectName("Faint")
        footer.addWidget(self.lbl_path)
        layout.addLayout(footer)

        self._load_notes()
        self._apply_wrap()
        self._apply_font_size()
        self._update_stats()
        return card

    def _build_launchers(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(9)

        title = QLabel("Launch")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        for label, command, args in (
            ("Terminal", "deepin-terminal", []),
            ("Files", "dde-file-manager", []),
            ("Antigravity", "antigravity", []),
            ("Chrome", "google-chrome", []),
            ("System monitor", "deepin-system-monitor", []),
        ):
            button = QPushButton(label)
            button.setObjectName("Ghost")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, cmd=command, a=list(args): self._launch(cmd, a))
            layout.addWidget(button)
        layout.addStretch()
        return card

    # ------------------------------------------------------------ behaviour

    def title(self) -> str:
        return "Scratchpad & Utilities"

    def subtitle(self) -> str:
        return "A persistent developer notepad with encoding, hashing and JSON tooling"

    def on_activated(self) -> None:
        self.txt_notes.setFocus()

    def shutdown(self) -> None:
        self._save_notes()

    # -- persistence -------------------------------------------------------

    def _load_notes(self) -> None:
        for candidate in (NOTES_FILE, NOTES_BACKUP):
            try:
                if candidate.is_file():
                    self.txt_notes.setPlainText(candidate.read_text(encoding="utf-8", errors="replace"))
                    self.lbl_saved.setText("Loaded from disk")
                    return
            except OSError:
                continue
        self.lbl_saved.setText("New document")

    def _on_text_changed(self) -> None:
        self._update_stats()
        timer = getattr(self, "_save_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(700)
            timer.timeout.connect(self._save_notes)
            self._save_timer = timer
        timer.start()

    def _save_notes(self) -> None:
        if self._saving:
            return
        self._saving = True
        try:
            content = self.txt_notes.toPlainText()
            NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
            if NOTES_FILE.exists():
                try:
                    NOTES_BACKUP.write_text(NOTES_FILE.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                except OSError:
                    pass
            tmp = NOTES_FILE.with_suffix(".tmp")
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, NOTES_FILE)
            stamp = time.strftime("%H:%M:%S")
            self.lbl_saved.setText(f"Saved {stamp}")
        except OSError as exc:
            self.lbl_saved.setText("Save failed")
            self.notify.emit(f"Could not save the scratchpad: {exc}", "danger")
        finally:
            self._saving = False

    def _update_stats(self) -> None:
        text = self.txt_notes.toPlainText()
        chars = len(text)
        words = len(text.split())
        lines = text.count("\n") + 1 if text else 0
        tokens = int(chars / 4)
        self.lbl_stats.setText(
            f"{chars:,} characters · {words:,} words · {lines:,} lines · ~{tokens:,} tokens"
        )

    # -- editor helpers ----------------------------------------------------

    def _toggle_wrap(self, enabled: bool) -> None:
        self.txt_notes.setLineWrapMode(QTextEdit.WidgetWidth if enabled else QTextEdit.NoWrap)
        self.context.settings.set("scratchpad.wrap", bool(enabled))

    def _font_size_changed(self, size: int) -> None:
        self._apply_font_size()
        self.context.settings.set("scratchpad.font_size", int(size))

    def _apply_font_size(self) -> None:
        font = QFont("JetBrains Mono")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(self.spin_font.value())
        self.txt_notes.setFont(font)

    def _apply_wrap(self) -> None:
        self.txt_notes.setLineWrapMode(
            QTextEdit.WidgetWidth if self.chk_wrap.isChecked() else QTextEdit.NoWrap
        )

    def _find(self, text: Optional[str] = None, direction: bool = False) -> None:
        needle = self.txt_find.text() if text is None else text
        if not needle:
            return
        if not self.txt_notes.find(needle):
            # Wrap around to the top of the document.
            cursor = self.txt_notes.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.txt_notes.setTextCursor(cursor)
            self.txt_notes.find(needle)

    def _copy_scratchpad(self) -> None:
        if copy_to_clipboard(self.txt_notes.toPlainText()):
            self.notify.emit("Scratchpad copied to the clipboard.", "success")

    def _clear_scratchpad(self) -> None:
        from PyQt5.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            self,
            "Clear scratchpad",
            "Wipe the scratchpad contents? A backup of the previous text is kept on disk.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.txt_notes.clear()
            self._save_notes()
            self.notify.emit("Scratchpad cleared.", "success")

    # -- utilities ---------------------------------------------------------

    def _json_pretty(self) -> None:
        self._json_action(pretty=True, sort_keys=False)

    def _json_minify(self) -> None:
        self._json_action(pretty=False, sort_keys=False)

    def _json_sort(self) -> None:
        self._json_action(pretty=True, sort_keys=True)

    def _json_action(self, pretty: bool, sort_keys: bool) -> None:
        raw = self.json_input.toPlainText().strip()
        if not raw:
            self.json_status.setText("Nothing to process")
            return
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.json_status.setText(f"Invalid JSON · line {exc.lineno} column {exc.colno}")
            self.notify.emit(f"Invalid JSON: {exc.msg}", "danger")
            return
        if pretty:
            output = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=sort_keys)
        else:
            output = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        self.json_input.setPlainText(output)
        self.json_status.setText("Formatted successfully")

    def _json_validate(self) -> None:
        raw = self.json_input.toPlainText().strip()
        if not raw:
            self.json_status.setText("Nothing to validate")
            return
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.json_status.setText(f"Invalid · {exc.msg}")
            self.notify.emit(f"Invalid JSON: {exc.msg}", "danger")
            return
        kind = type(data).__name__
        size = len(raw)
        self.json_status.setText(f"Valid {kind} · {size:,} bytes")
        self.notify.emit("The document is valid JSON.", "success")

    def _json_to_scratchpad(self) -> None:
        content = self.json_input.toPlainText()
        if not content:
            return
        self.txt_notes.setPlainText(content)
        self.notify.emit("JSON copied into the scratchpad.", "success")

    def _encode_run(self) -> None:
        raw = self.enc_input.toPlainText()
        mode = self.enc_mode.currentText()
        try:
            if mode == "Base64 encode":
                output = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            elif mode == "Base64 decode":
                padded = raw.strip()
                padded += "=" * (-len(padded) % 4)
                output = base64.b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")
            elif mode == "URL encode":
                output = urllib.parse.quote_plus(raw)
            elif mode == "URL decode":
                output = urllib.parse.unquote_plus(raw)
            elif mode == "Hex encode":
                output = raw.encode("utf-8").hex(" ")
            else:
                output = raw.encode("unicode_escape").decode("ascii")
        except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
            self.enc_status.setText(f"Failed · {exc}")
            self.notify.emit(f"Conversion failed: {exc}", "danger")
            return
        self.enc_output.setPlainText(output)
        self.enc_status.setText(f"{len(output):,} characters")

    def _encode_swap(self) -> None:
        self.enc_input.setPlainText(self.enc_output.toPlainText())
        self.enc_output.clear()

    def _hash_run(self) -> None:
        raw = self.hash_input.toPlainText().encode("utf-8")
        algo = self.hash_algo.currentText()
        digest = hashlib.new(algo, raw).hexdigest()
        self.hash_output.setPlainText(digest)
        self.hash_status.setText(f"{algo} · {len(digest)} hex characters")

    def _text_run(self) -> None:
        raw = self.text_input.toPlainText()
        action = self.text_action.currentText()
        try:
            if action == "Uppercase":
                output = raw.upper()
            elif action == "Lowercase":
                output = raw.lower()
            elif action == "Title case":
                output = raw.title()
            elif action == "Slugify":
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw.lower()).strip("-")
                output = slug
            elif action == "Strip whitespace":
                output = re.sub(r"[ \t]+", " ", raw).strip()
            elif action == "Remove duplicates":
                seen = set()
                kept = []
                for line in raw.splitlines():
                    if line not in seen:
                        seen.add(line)
                        kept.append(line)
                output = "\n".join(kept)
            elif action == "Sort lines":
                output = "\n".join(sorted(raw.splitlines()))
            elif action == "Escape regex":
                output = re.escape(raw)
            else:
                output = raw.replace("\\", "\\\\").replace('"', '\\"')
        except Exception as exc:  # noqa: BLE001
            self.text_status.setText(f"Failed · {exc}")
            return
        self.text_output.setPlainText(output)
        self.text_status.setText(f"{len(output):,} characters")

    def _launch(self, command: str, args: list) -> None:
        import platform
        import shutil

        candidates = [command]
        if command == "deepin-terminal":
            if platform.system() == "Windows":
                candidates = ["cmd.exe", "powershell.exe", "wt.exe"]
            elif platform.system() == "Darwin":
                try:
                    subprocess.Popen(["open", "-a", "Terminal"])
                    self.notify.emit("Launched Terminal.", "success")
                    return
                except Exception:
                    pass
            else:
                candidates = ["deepin-terminal", "gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "xterm", "x-terminal-emulator"]

        elif command == "dde-file-manager":
            if platform.system() == "Windows":
                candidates = ["explorer.exe"]
            elif platform.system() == "Darwin":
                try:
                    subprocess.Popen(["open", os.path.expanduser("~")])
                    self.notify.emit("Opened Files.", "success")
                    return
                except Exception:
                    pass
            else:
                candidates = ["dde-file-manager", "nautilus", "dolphin", "thunar", "nemo", "xdg-open"]

        elif command == "deepin-system-monitor":
            if platform.system() == "Windows":
                candidates = ["taskmgr.exe"]
            elif platform.system() == "Darwin":
                try:
                    subprocess.Popen(["open", "-a", "Activity Monitor"])
                    self.notify.emit("Launched Activity Monitor.", "success")
                    return
                except Exception:
                    pass
            else:
                candidates = ["deepin-system-monitor", "gnome-system-monitor", "plasma-systemmonitor", "htop", "top"]

        elif command == "google-chrome":
            if platform.system() == "Windows":
                candidates = ["chrome.exe", "msedge.exe", "firefox.exe"]
            elif platform.system() == "Darwin":
                candidates = ["google-chrome", "firefox", "safari"]
            else:
                candidates = ["google-chrome", "google-chrome-stable", "chromium", "firefox", "xdg-open"]

        for cand in candidates:
            if shutil.which(cand):
                try:
                    subprocess.Popen([cand, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.notify.emit(f"Launched {cand}.", "success")
                    return
                except Exception:
                    continue

        self.notify.emit(f"Could not find an application for {command} on this system.", "warning")
