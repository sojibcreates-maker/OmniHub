"""Application bootstrap: single instance, logging, crash handling and CLI."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
import traceback
from typing import List, Optional

from PyQt5.QtCore import QObject, Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import QApplication, QMessageBox

from . import APP_ID, APP_NAME, APP_TAGLINE, APP_VERSION
from .context import AppContext
from .paths import LOG_FILE, ensure_dirs

__all__ = ["main", "run"]

LOGGER_NAME = "omnihub"
_UID = os.getuid() if hasattr(os, "getuid") else os.environ.get("USERNAME", "user")
_IPC_SERVER_NAME = f"{APP_ID}-single-instance-{_UID}"


# --------------------------------------------------------------------- setup

def _configure_logging() -> logging.Logger:
    """Configure rotating file logging for the application."""
    ensure_dirs()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if logger.handlers:
        return logger

    try:
        handler = logging.handlers.RotatingFileHandler(
            str(LOG_FILE), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")
        )
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())

    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(console)
    return logger


def _install_excepthook(logger: logging.Logger) -> None:
    """Route unhandled exceptions to the log and show a friendly dialog."""

    def handler(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Unhandled exception:\n%s", details)
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle(f"{APP_NAME} — unexpected error")
            box.setText(
                "Something went wrong, but OmniHub is still running.\n"
                "The details were written to the log file."
            )
            box.setInformativeText(f"{exc_type.__name__}: {exc_value}")
            box.setDetailedText(details)
            box.exec_()
        except Exception:
            pass

    sys.excepthook = handler


def _apply_app_font(app: QApplication) -> None:
    """Prefer the Inter typeface, falling back to the system sans-serif."""
    font = QFont("Inter")
    if font.family().lower() not in ("inter", "inter display"):
        font = QFont()
        font.setStyleHint(QFont.SansSerif)
    font.setPointSize(10)
    app.setFont(font)


class _IpcProbe(QObject):
    """Raises the already-running instance when a second copy is started."""

    def __init__(self) -> None:
        super().__init__()
        self.already_running = False
        socket = QLocalSocket()
        socket.connectToServer(_IPC_SERVER_NAME)
        if socket.waitForConnected(400):
            socket.write(b"show")
            socket.flush()
            socket.waitForBytesWritten(400)
            socket.disconnectFromServer()
            self.already_running = True
        else:
            socket.abort()


def _claim_instance() -> Optional[QLocalServer]:
    """Become the single running instance, cleaning up a stale socket."""
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.UserAccessOption)
    if server.listen(_IPC_SERVER_NAME):
        return server

    # Remove a stale socket file left behind by a crash and retry once.
    QLocalServer.removeServer(_IPC_SERVER_NAME)
    if server.listen(_IPC_SERVER_NAME):
        return server
    return None


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=APP_ID, description=f"{APP_NAME} — {APP_TAGLINE}")
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--restart", action="store_true", help="restart the OmniRoute gateway and exit")
    parser.add_argument("--reset-settings", action="store_true", help="restore default settings and exit")
    parser.add_argument("--reset-all", action="store_true", help="reset settings and delete the scratchpad")
    parser.add_argument(
        "--page",
        default="",
        choices=["", "gateway", "ai", "system", "tools", "settings", "about"],
        help="open a specific page on launch",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------- main

def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns the process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0

    logger = _configure_logging()

    # Qt high-DPI attributes must be set before the QApplication exists.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_ID)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("SojibLabs")
    app.setDesktopFileName(f"{APP_ID}.desktop")
    app.setQuitOnLastWindowClosed(True)
    try:
        app.setStyle("Fusion")
    except Exception:
        pass
    _apply_app_font(app)

    if args.reset_settings or args.reset_all:
        from .config import Settings

        settings = Settings()
        settings.load()
        settings.reset_section("theme")
        settings.reset_section("gateway")
        settings.reset_section("behavior")
        settings.reset_section("window")
        settings.save()
        print("Settings restored to defaults.")
        if args.reset_all:
            from .paths import NOTES_FILE

            try:
                NOTES_FILE.unlink()
                print("Scratchpad deleted.")
            except OSError:
                pass
        return 0

    if args.restart:
        from .workers import ServiceWorker

        logger.info("Restarting the gateway from the command line")
        context = AppContext()
        worker = ServiceWorker("restart", base_url=context.settings.str_of("gateway.base_url"))
        worker.result.connect(lambda ok, message: (print(message), sys.exit(0 if ok else 1)))
        worker.start()
        app.exec_()
        return 0

    probe = _IpcProbe()
    if probe.already_running:
        print(f"{APP_NAME} is already running — the existing window was raised.")
        return 0

    ipc_server = _claim_instance()

    context = AppContext()
    app.setProperty("omnihub.context", context)

    theme = context.theme
    theme.apply(app)

    if context.settings.get("theme.mode", "system") == "system":
        logger.info(
            "Resolved system theme to %s", theme.effective_mode()
        )

    _install_excepthook(logger)

    from .window import MainWindow

    window = MainWindow(context)
    window.show()

    if args.page:
        window.open_page(args.page)

    if context.settings.bool_of("behavior.start_on_launch", False):
        QTimer.singleShot(1200, window.gateway_page.start_service)

    logger.info("%s %s started", APP_NAME, APP_VERSION)
    code = app.exec_()
    logger.info("%s exiting", APP_NAME)
    if ipc_server is not None:
        ipc_server.close()
    return code


def run() -> None:
    """Console entry point."""
    sys.exit(main())
