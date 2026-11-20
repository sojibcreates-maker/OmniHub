#!/usr/bin/env python3
"""
OmniHub — AI Gateway & System Studio
A minimal, precision control surface for the OmniRoute local inference gateway.

Crafted by Md Sojib Hossain (SojibLabs).
"""

import sys
import os
import re
import time
import json
import math
import html
import base64
import subprocess
import threading
import platform
import shutil
import webbrowser
from urllib.parse import urlparse

import requests
import psutil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QUrl, QSize, QPoint, QPointF, QRectF,
    QPropertyAnimation, QEasingCurve, QVariantAnimation, pyqtProperty,
)
from PyQt5.QtGui import (
    QDesktopServices, QFont, QFontDatabase, QColor, QPainter, QPainterPath,
    QPen, QBrush, QLinearGradient, QRadialGradient, QPixmap, QPolygonF,
    QTextDocument,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox,
    QFrame, QMessageBox, QSystemTrayIcon, QMenu, QAction, QScrollArea,
    QStackedWidget, QButtonGroup, QSizePolicy, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
)

APP_NAME = "OmniHub"
APP_VERSION = "3.1.0"
APP_TAGLINE = "AI Gateway & System Studio"

OMNIROUTE_REPO = "https://github.com/cheaper-inference/OmniRoute.git"
DEFAULT_OMNIROUTE_BASE = "http://localhost:20128"
OMNIROUTE_BASE = DEFAULT_OMNIROUTE_BASE
OMNIROUTE_HEALTH = f"{OMNIROUTE_BASE}/api/monitoring/health"
OMNIROUTE_DASHBOARD = f"{OMNIROUTE_BASE}/dashboard"
OMNIROUTE_CHAT = f"{OMNIROUTE_BASE}/v1/chat/completions"


def get_default_omniroute_dir():
    custom_dev = "/home/sojiblabs/.gemini/antigravity/scratch/OmniRoute"
    if os.path.exists(custom_dev):
        return custom_dev
    env_dir = os.environ.get("OMNIROUTE_DIR")
    if env_dir:
        return env_dir
    return os.path.join(os.path.expanduser("~"), ".omniroute")


def get_default_config_dir():
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "OmniHub")
    if platform.system() == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "OmniHub")
    return os.path.expanduser("~/.config/omnihub")


OMNIROUTE_DIR = get_default_omniroute_dir()
CONFIG_DIR = get_default_config_dir()
NOTES_FILE = os.path.join(CONFIG_DIR, "notes.txt")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
os.makedirs(CONFIG_DIR, exist_ok=True)


def load_saved_gateway_url():
    """Load user-configured gateway URL from settings.json or environment."""
    env_val = os.environ.get("OMNIROUTE_BASE")
    if env_val and env_val.strip():
        return env_val.strip().rstrip("/")
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                val = data.get("gateway", {}).get("base_url")
                if val and isinstance(val, str) and val.strip():
                    return val.strip().rstrip("/")
    except Exception:
        pass
    return DEFAULT_OMNIROUTE_BASE


def set_gateway_base(url, persist=True):
    """Dynamically set the active gateway base URL and refresh all endpoint constants."""
    global OMNIROUTE_BASE, OMNIROUTE_HEALTH, OMNIROUTE_DASHBOARD, OMNIROUTE_CHAT
    url = (url or "").strip().rstrip("/")
    if not url:
        url = DEFAULT_OMNIROUTE_BASE
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    OMNIROUTE_BASE = url
    OMNIROUTE_HEALTH = f"{OMNIROUTE_BASE}/api/monitoring/health"
    OMNIROUTE_DASHBOARD = f"{OMNIROUTE_BASE}/dashboard"
    OMNIROUTE_CHAT = f"{OMNIROUTE_BASE}/v1/chat/completions"

    if persist:
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                try:
                    with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
            if "gateway" not in data or not isinstance(data["gateway"], dict):
                data["gateway"] = {}
            data["gateway"]["base_url"] = url
            tmp_cfg = SETTINGS_FILE + ".tmp"
            with open(tmp_cfg, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_cfg, SETTINGS_FILE)
        except Exception:
            pass
    return OMNIROUTE_BASE


def get_gateway_port():
    """Extract integer port from current gateway URL."""
    try:
        parsed = urlparse(OMNIROUTE_BASE)
        if parsed.port:
            return parsed.port
        if parsed.scheme == "https":
            return 443
        return 80
    except Exception:
        return 20128


def get_gateway_host_display():
    """Return compact host:port string for indicators and labels."""
    try:
        parsed = urlparse(OMNIROUTE_BASE)
        if parsed.netloc:
            return parsed.netloc
    except Exception:
        pass
    return OMNIROUTE_BASE.replace("http://", "").replace("https://", "").rstrip("/")


# Initialize active gateway base from saved settings
set_gateway_base(load_saved_gateway_url(), persist=False)


def get_app_icon_path():
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "assets", "omnihub.png"),
        os.path.join(base, "omnihub.png"),
        os.path.expanduser("~/.local/share/icons/omnihub.png"),
        "/home/sojiblabs/.local/share/icons/omnihub.png",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ""


DEV_NAME = "Md Sojib Hossain"
DEV_ORG = "SojibLabs"
DEV_FB = "https://www.facebook.com/hossain.sojibs"
DEV_KOFI = "https://ko-fi.com/sojibhossain"
DONATION_URL = "https://www.supportkori.com/sojib"
DEV_GITHUB = "https://github.com/sojibcreates-maker"


def detect_system_theme():
    """Best-effort detection of the desktop's light/dark preference."""
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "dark" if value == 0 else "light"
        except Exception:
            pass
    elif system == "Darwin":
        try:
            out = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                text=True, stderr=subprocess.DEVNULL, timeout=3,
            ).strip().lower()
            return "dark" if "dark" in out else "light"
        except Exception:
            return "light"
    else:
        for command in (
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            ["gsettings", "get", "com.deepin.dde.appearance", "gtk-theme"],
        ):
            try:
                out = subprocess.check_output(
                    command, text=True, stderr=subprocess.DEVNULL, timeout=2
                ).strip().lower()
                if "dark" in out:
                    return "dark"
                if "light" in out:
                    return "light"
            except Exception:
                continue

    app = QApplication.instance()
    if app is not None:
        return "dark" if app.palette().window().color().lightness() < 128 else "light"
    return "dark"
class OmniRouteInstallerWorker(QThread):
    log_line = pyqtSignal(str)
    step_updated = pyqtSignal(int, str, str)  # step_index, status_text, color
    progress_val = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir=OMNIROUTE_DIR):
        super().__init__()
        self.target_dir = target_dir
        self._proc = None
        self._cancelled = False

    def cancel(self):
        """Stop the current child process and abort the pipeline."""
        self._cancelled = True
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def _aborted(self):
        if self._cancelled:
            self.log_line.emit("Installation cancelled by user.")
            self.finished.emit(False, "Installation cancelled.")
            return True
        return False

    def run_cmd(self, cmd, cwd=None, env=None, shell=True):
        if self._cancelled:
            return 130
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        local_bin = os.path.expanduser("~/.local/bin")
        sep = ";" if platform.system() == "Windows" else ":"
        full_env["PATH"] = f"{local_bin}{sep}{full_env.get('PATH', '')}"

        try:
            proc = subprocess.Popen(
                cmd, shell=shell, cwd=cwd, env=full_env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
        except Exception as exc:
            self.log_line.emit(f"Command failed to start: {exc}")
            return 1
        self._proc = proc
        if proc.stdout is not None:
            for line in proc.stdout:
                if self._cancelled:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
                cleaned = line.rstrip()
                if cleaned:
                    self.log_line.emit(cleaned)
        proc.wait()
        self._proc = None
        return proc.returncode

    def run(self):
        try:
            self.progress_val.emit(8)
            self.step_updated.emit(0, "Checking environment & cache permissions...", "#38BDF8")
            self.log_line.emit("=== Step 1/5: System Environment & Pre-flight ===")

            if platform.system() != "Windows":
                cache_dir = os.path.expanduser("~/.cache")
                try:
                    os.makedirs(cache_dir, exist_ok=True)
                    os.chmod(cache_dir, 0o700)
                    self.log_line.emit(f"✓ Cache permissions verified: chmod 700 {cache_dir}")
                except Exception as e:
                    self.log_line.emit(f"! Note on cache permission: {e}")

            if self._aborted():
                return
            rc = self.run_cmd("node -v && git --version && npm -v")
            if rc != 0:
                self.step_updated.emit(0, "Node.js or Git not ready", "#EF4444")
                self.finished.emit(False, "Node.js (v18+) or Git is missing from standard PATH.")
                return
            self.step_updated.emit(0, "✓ Environment Ready (Node + Git)", "#10B981")
            self.progress_val.emit(25)

            # Step 2: Download / Clone
            self.step_updated.emit(1, "Downloading repository from GitHub...", "#38BDF8")
            self.log_line.emit("\n=== Step 2/5: Fetching OmniRoute from GitHub ===")
            self.log_line.emit(f"Source URL: {OMNIROUTE_REPO}")
            self.log_line.emit(f"Destination: {self.target_dir}")

            if self._aborted():
                return
            if os.path.exists(os.path.join(self.target_dir, ".git")):
                self.log_line.emit("Existing repository detected. Pulling latest updates...")
                rc = self.run_cmd("git fetch origin && git pull origin release/v3.8.54 || git pull", cwd=self.target_dir)
            else:
                os.makedirs(os.path.dirname(self.target_dir), exist_ok=True)
                rc = self.run_cmd(["git", "clone", OMNIROUTE_REPO, self.target_dir], shell=False)

            if rc != 0:
                self.step_updated.emit(1, "GitHub download failed", "#EF4444")
                self.finished.emit(False, "Failed to clone repository from GitHub. Check network connection.")
                return

            self.step_updated.emit(1, "✓ Repository Downloaded", "#10B981")
            self.progress_val.emit(50)

            # Step 3: Install Core Dependencies
            if self._aborted():
                return
            self.step_updated.emit(2, "Installing core dependencies (npm install)...", "#38BDF8")
            self.log_line.emit("\n=== Step 3/5: Resolving & Installing Dependencies ===")
            rc = self.run_cmd("npm install --no-audit", cwd=self.target_dir)
            if rc != 0:
                self.log_line.emit("Retrying npm install with allow-scripts...")
                rc = self.run_cmd("npm install --allow-scripts", cwd=self.target_dir)
            if rc != 0 and not self._cancelled:
                self.step_updated.emit(2, "Dependency install failed", "#EF4444")
                self.finished.emit(False, "npm install failed. Check the log for details.")
                return

            self.step_updated.emit(2, "✓ Dependencies Installed", "#10B981")
            self.progress_val.emit(75)

            # Step 4: Native Modules & Keytar
            if self._aborted():
                return
            self.step_updated.emit(3, "Configuring native modules & launcher script...", "#38BDF8")
            self.log_line.emit("\n=== Step 4/5: Native Module Configuration ===")

            env_file = os.path.join(self.target_dir, ".env")
            env_example = os.path.join(self.target_dir, ".env.example")
            if not os.path.exists(env_file) and os.path.exists(env_example):
                try:
                    shutil.copyfile(env_example, env_file)
                    self.log_line.emit("✓ Created default .env from .env.example")
                except Exception as e:
                    self.log_line.emit(f"! Note on creating .env: {e}")

            self.run_cmd("npm install keytar --no-save --foreground-scripts", cwd=self.target_dir)

            cli_bin = os.path.join(self.target_dir, "bin", "omniroute.mjs")
            target_link = os.path.expanduser("~/.local/bin/omniroute")
            if os.path.exists(cli_bin) and platform.system() != "Windows":
                try:
                    os.chmod(cli_bin, 0o755)
                    if os.path.islink(target_link) or os.path.exists(target_link):
                        os.remove(target_link)
                    os.symlink(cli_bin, target_link)
                    self.log_line.emit("✓ Linked 'omniroute' CLI to ~/.local/bin/omniroute")
                except Exception as e:
                    self.log_line.emit(f"! Note linking CLI: {e}")

            if platform.system() == "Windows":
                start_bat = os.path.join(self.target_dir, "start-omniroute.bat")
                with open(start_bat, "w", encoding="utf-8") as f:
                    f.write("@echo off\r\ncd /d \"%~dp0\"\r\nnpm run dev\r\n")
                self.log_line.emit("✓ Generated start-omniroute.bat launcher script")
            else:
                start_script = os.path.join(self.target_dir, "start-omniroute.sh")
                with open(start_script, "w", encoding="utf-8") as f:
                    f.write("""#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
export NVM_DIR="$HOME/.config/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
export PATH="$HOME/.local/bin:$PATH"
exec npm run dev
""")
                try:
                    os.chmod(start_script, 0o755)
                except Exception:
                    pass
                self.log_line.emit("✓ Generated start-omniroute.sh executable script")

            self.step_updated.emit(3, "✓ Native Modules & Environment Configured", "#10B981")
            self.progress_val.emit(90)

            # Step 5: Start Service & Verify
            if self._aborted():
                return
            self.step_updated.emit(4, "Starting OmniRoute Service on port 20128...", "#38BDF8")
            self.log_line.emit("\n=== Step 5/5: Launching Gateway Service ===")
            start_script = os.path.join(self.target_dir, "start-omniroute.sh")
            if platform.system() == "Windows":
                subprocess.Popen("npm run dev", shell=True, cwd=self.target_dir)
            elif os.path.exists(start_script):
                subprocess.Popen([start_script], cwd=self.target_dir,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            else:
                self.log_line.emit("! Launcher script missing; starting with npm directly.")
                subprocess.Popen(["npm", "run", "dev"], cwd=self.target_dir,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)

            self.log_line.emit("Awaiting health check on http://localhost:20128/api/monitoring/health...")
            healthy = False
            for i in range(15):
                time.sleep(1.5)
                try:
                    r = requests.get(OMNIROUTE_HEALTH, timeout=1.5)
                    if r.status_code == 200:
                        healthy = True
                        break
                except Exception:
                    pass
                self.log_line.emit(f"Checking server response... ({i+1}/15)")

            if healthy:
                self.step_updated.emit(4, "✓ Service Online & Healthy (Port 20128)", "#10B981")
                self.progress_val.emit(100)
                self.finished.emit(True, "OmniRoute successfully installed and running!")
            else:
                self.step_updated.emit(4, "✓ Installed (Launch starting in background)", "#F59E0B")
                self.progress_val.emit(100)
                self.finished.emit(True, "OmniRoute installed. Initial startup may take a few more seconds to warm up.")

        except Exception as e:
            self.log_line.emit(f"CRITICAL ERROR: {e}")
            self.finished.emit(False, str(e))


def stop_omniroute_processes(target_dir=None, port=None):
    """
    Terminates OmniRoute and all associated background node/next.js/turbopack processes.
    Uses multi-stage teardown:
    1. By port: Kills any process (and descendants) listening on gateway port or default 20128.
    2. By working directory: Kills any process running inside target_dir.
    3. By cmdline patterns: 'run-next.mjs', 'next-server', 'omniroute', 'start-omniroute.sh'.
    4. Escalation: SIGTERM followed by SIGKILL for clean port release.
    5. Native OS fallback: fuser / lsof on Linux/macOS, taskkill on Windows.
    """
    if target_dir is None:
        target_dir = OMNIROUTE_DIR
    if port is None:
        port = get_gateway_port()

    stopped = False
    my_pid = os.getpid()
    my_ppid = os.getppid()
    pids_to_kill = set()

    ports_to_check = {20128}
    if port and isinstance(port, int):
        ports_to_check.add(port)

    # 1. Check network listeners on the gateway port(s)
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port in ports_to_check and conn.pid:
                if conn.pid not in (my_pid, my_ppid):
                    pids_to_kill.add(conn.pid)
    except Exception:
        pass

    # 2. Check process working directories and cmdline
    target_real = os.path.realpath(target_dir) if target_dir and os.path.exists(target_dir) else None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid in (my_pid, my_ppid):
                continue
            name = (proc.info['name'] or "").lower()
            cmdline = " ".join(proc.info['cmdline'] or [])

            cwd = ""
            try:
                cwd = proc.cwd()
            except Exception:
                pass

            is_in_target_dir = False
            if target_real and cwd:
                try:
                    if os.path.realpath(cwd) == target_real:
                        is_in_target_dir = True
                except Exception:
                    pass

            if is_in_target_dir and any(k in name for k in ("node", "npm", "bun", "next", "esbuild", "sh", "bash")):
                pids_to_kill.add(pid)
            elif any(pat in cmdline for pat in ("run-next.mjs", "next-server", "omniroute", "start-omniroute.sh")):
                pids_to_kill.add(pid)
            elif target_dir and target_dir in cmdline and any(k in name for k in ("node", "npm", "bun", "next")):
                pids_to_kill.add(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 3. Include all child and descendant processes
    all_pids = set(pids_to_kill)
    for pid in list(pids_to_kill):
        try:
            p = psutil.Process(pid)
            for child in p.children(recursive=True):
                if child.pid not in (my_pid, my_ppid):
                    all_pids.add(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 4. First pass: terminate gracefully
    for pid in all_pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            stopped = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 5. Wait up to 1.2s and force kill any stubborn processes
    if all_pids:
        alive_procs = []
        for pid in all_pids:
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    alive_procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if alive_procs:
            _, still_alive = psutil.wait_procs(alive_procs, timeout=1.2)
            for p in still_alive:
                try:
                    p.kill()
                    stopped = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    # 6. Fallback platform commands
    if platform.system() == "Windows":
        for pid in all_pids:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass
    else:
        for p in ports_to_check:
            try:
                subprocess.run(["fuser", "-k", "-9", f"{p}/tcp"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass
            try:
                subprocess.run(f"lsof -ti :{p} | xargs -r kill -9",
                               shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass
        try:
            subprocess.run(["pkill", "-9", "-f", "run-next.mjs"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-9", "-f", "next-server"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    return stopped


class OmniRouteWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, action):
        super().__init__()
        self.action = action

    def _launch(self):
        script = os.path.join(OMNIROUTE_DIR, "start-omniroute.sh")
        env = os.environ.copy()
        port = get_gateway_port()
        if port:
            env["PORT"] = str(port)
        try:
            if platform.system() == "Windows":
                subprocess.Popen("npm run dev", shell=True, cwd=OMNIROUTE_DIR, env=env)
            elif os.path.exists(script):
                subprocess.Popen([script], cwd=OMNIROUTE_DIR, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            else:
                return False
        except Exception as exc:
            self.finished.emit(False, f"Launch failed: {exc}")
            return None
        return True

    def run(self):
        try:
            if self.action == "start":
                try:
                    r = requests.get(OMNIROUTE_HEALTH, timeout=1.5)
                    if r.status_code == 200:
                        self.finished.emit(True, "OmniRoute Gateway is already online!")
                        return
                except Exception:
                    pass

                launched = self._launch()
                if launched is None:
                    return
                if not launched:
                    self.finished.emit(False, "Launcher not found — run the installer first.")
                    return
                time.sleep(2.5)
                self.finished.emit(True, "OmniRoute engine launch signal dispatched.")

            elif self.action == "stop":
                stop_omniroute_processes()
                time.sleep(0.5)
                self.finished.emit(True, "OmniRoute server process stopped.")

            elif self.action == "restart":
                stop_omniroute_processes()
                time.sleep(1.0)
                launched = self._launch()
                if launched is None:
                    return
                if not launched:
                    self.finished.emit(False, "Launcher not found — run the installer first.")
                    return
                time.sleep(2.0)
                self.finished.emit(True, "OmniRoute server restarted successfully.")

        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class AIChatWorker(QThread):
    finished = pyqtSignal(bool, str, float)

    def __init__(self, model, prompt, system_prompt=""):
        super().__init__()
        self.model = model
        self.prompt = prompt
        self.system_prompt = system_prompt

    def run(self):
        start_t = time.time()
        messages = []
        if self.system_prompt.strip():
            messages.append({"role": "system", "content": self.system_prompt.strip()})
        messages.append({"role": "user", "content": self.prompt.strip()})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer local"
        }

        try:
            res = requests.post(OMNIROUTE_CHAT, json=payload, headers=headers, timeout=50)
            elapsed = time.time() - start_t
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                self.finished.emit(True, content, elapsed)
            else:
                self.finished.emit(False, f"HTTP {res.status_code}: {res.text}", elapsed)
        except Exception as e:
            elapsed = time.time() - start_t
            self.finished.emit(False, f"Connection Failed: {e}\n(Ensure OmniRoute server is active)", elapsed)


class HealthCheckWorker(QThread):
    result = pyqtSignal(bool, int)

    def run(self):
        try:
            t0 = time.time()
            res = requests.get(OMNIROUTE_HEALTH, timeout=1.8)
            latency = int((time.time() - t0) * 1000)
            if res.status_code == 200:
                self.result.emit(True, latency)
                return
            self.result.emit(False, latency)
        except Exception:
            self.result.emit(False, 0)


class DoctorWorker(QThread):
    log_line = pyqtSignal(str)

    def run(self):
        try:
            if shutil.which("omniroute") is None:
                self.log_line.emit("Doctor unavailable — the omniroute CLI is not linked.")
                return
            res = subprocess.run(["omniroute", "doctor"], capture_output=True,
                                 text=True, timeout=45)
            lines = res.stdout.strip().split("\n")
            summary = [l for l in lines if "Summary" in l or "OK" in l or "WARN" in l][:8]
            for s in summary:
                self.log_line.emit(f"🩺 {s}")
        except Exception as e:
            self.log_line.emit(f"Doctor error: {e}")




# =============================================================================
#  Design tokens
# =============================================================================

TOKENS = {
    "dark": {
        "bg": "#08090D",
        "sidebar": "#0B0D12",
        "surface": "#101319",
        "surface2": "#151922",
        "surfaceHover": "#1A1F2A",
        "border": "#1D222D",
        "borderStrong": "#2B3240",
        "accent": "#7B8CFF",
        "accentHover": "#93A1FF",
        "accentPress": "#6373E8",
        "accentSoft": "rgba(123, 140, 255, 0.12)",
        "accentBorder": "rgba(123, 140, 255, 0.34)",
        "text": "#EDF0F6",
        "dim": "#98A1B3",
        "faint": "#626C7E",
        "success": "#4ADE80",
        "successSoft": "rgba(74, 222, 128, 0.12)",
        "successBorder": "rgba(74, 222, 128, 0.38)",
        "warn": "#FBBF24",
        "danger": "#FB7185",
        "dangerSoft": "rgba(251, 113, 133, 0.12)",
        "dangerBorder": "rgba(251, 113, 133, 0.36)",
        "monoText": "#8FE3CB",
        "consoleBg": "#06080C",
        "consoleBorder": "#171C25",
        "chipBg": "#151922",
        "inputBg": "#0C0F15",
        "grid": "rgba(255, 255, 255, 0.030)",
        "glow": "rgba(123, 140, 255, 0.10)",
        "white": "#FFFFFF",
    },
    "light": {
        "bg": "#F5F6F9",
        "sidebar": "#FFFFFF",
        "surface": "#FFFFFF",
        "surface2": "#F4F6FA",
        "surfaceHover": "#EEF1F6",
        "border": "#E4E7EE",
        "borderStrong": "#D2D8E3",
        "accent": "#4F5FE0",
        "accentHover": "#4351CC",
        "accentPress": "#3A47B8",
        "accentSoft": "rgba(79, 95, 224, 0.10)",
        "accentBorder": "rgba(79, 95, 224, 0.30)",
        "text": "#101319",
        "dim": "#5D6676",
        "faint": "#8A92A2",
        "success": "#0F9D58",
        "successSoft": "rgba(15, 157, 88, 0.10)",
        "successBorder": "rgba(15, 157, 88, 0.30)",
        "warn": "#B45309",
        "danger": "#DC2626",
        "dangerSoft": "rgba(220, 38, 38, 0.09)",
        "dangerBorder": "rgba(220, 38, 38, 0.28)",
        "monoText": "#0E7C66",
        "consoleBg": "#0A0D13",
        "consoleBorder": "#1A202B",
        "chipBg": "#F4F6FA",
        "inputBg": "#FBFCFE",
        "grid": "rgba(16, 20, 32, 0.045)",
        "glow": "rgba(79, 95, 224, 0.07)",
        "white": "#FFFFFF",
    },
}


def qcolor(value):
    """QColor does not parse CSS ``rgba(...)`` strings, so do it here."""
    if isinstance(value, QColor):
        return QColor(value)
    text = str(value).strip()
    match = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)",
                     text)
    if match:
        r, g, b = (int(float(match.group(i))) for i in (1, 2, 3))
        alpha = float(match.group(4)) if match.group(4) is not None else 1.0
        return QColor(r, g, b, int(round(alpha * 255)))
    return QColor(text)


def build_qss(t):
    from string import Template

    tpl = Template("""
    QWidget {
        color: $text;
        font-family: "$font";
        font-size: 13px;
    }
    QMainWindow, QWidget#root { background: $bg; }
    QLabel { background: transparent; }
    QToolTip {
        background: $surface2; color: $text; border: 1px solid $borderStrong;
        padding: 6px 8px; border-radius: 6px; font-size: 11px;
    }

    /* ---------- scaffolding ---------- */
    QFrame#sidebar { background: $sidebar; border-right: 1px solid $border; }
    QWidget#content { background: transparent; }
    QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
    QWidget#scrollPage { background: transparent; }
    QWidget#chatBody { background: transparent; }

    /* ---------- typography ---------- */
    QLabel#brandName { font-size: 16px; font-weight: 700; color: $text; }
    QLabel#brandTag { font-size: 10px; color: $faint; }
    QLabel#navSection { color: $faint; font-size: 10px; }
    QLabel#sectionLabel { color: $faint; font-size: 10px; }
    QLabel#eyebrow { color: $accent; font-size: 10px; font-weight: 700; }
    QLabel#pageTitle { font-size: 22px; font-weight: 700; color: $text; }
    QLabel#pageDesc { font-size: 12px; color: $dim; }
    QLabel#heroTitle { font-size: 20px; font-weight: 700; color: $text; }
    QLabel#heroDesc { font-size: 12px; color: $dim; }
    QLabel#kpiTitle { color: $faint; font-size: 10px; }
    QLabel#kpiValue { font-size: 25px; font-weight: 700; color: $text; }
    QLabel#kpiSub { color: $dim; font-size: 11px; }
    QLabel#hint { color: $faint; font-size: 11px; }
    QLabel#mono { font-family: "$mono"; font-size: 11px; color: $dim; }
    QLabel#monoAccent { font-family: "$mono"; font-size: 11px; color: $accent; }
    QLabel#keyLabel { color: $faint; font-size: 11px; }
    QLabel#valLabel { color: $text; font-size: 12px; }
    QLabel#devName { font-size: 16px; font-weight: 700; color: $text; }
    QLabel#devRole { font-size: 11px; color: $accent; }
    QLabel#accentValue { color: $accent; font-size: 12px; }
    QLabel#kpiSubOk { color: $success; font-size: 11px; }
    QLabel#kpiSubErr { color: $faint; font-size: 11px; }
    QLabel#avatar {
        background: $accentSoft; color: $accent; border: 1px solid $accentBorder;
        border-radius: 22px; font-size: 15px; font-weight: 700;
    }

    /* ---------- surfaces ---------- */
    QFrame#card {
        background: $surface;
        border: 1px solid $border;
        border-radius: 14px;
    }
    QFrame#cardAccent {
        background: $surface;
        border: 1px solid $accentBorder;
        border-radius: 14px;
    }
    QFrame#inset {
        background: $surface2;
        border: 1px solid $border;
        border-radius: 10px;
    }
    QFrame#statusCard {
        background: $surface;
        border: 1px solid $border;
        border-radius: 12px;
    }
    QFrame#stepRow {
        background: transparent;
        border: none;
        border-radius: 8px;
    }
    QFrame#stepRow:hover { background: $surface2; }

    /* ---------- pills / chips ---------- */
    QLabel#chip {
        background: $chipBg; border: 1px solid $border; border-radius: 9px;
        color: $dim; padding: 4px 10px; font-size: 11px;
    }
    QLabel#chipAccent {
        background: $accentSoft; border: 1px solid $accentBorder; border-radius: 9px;
        color: $accent; padding: 4px 10px; font-size: 11px;
    }
    QLabel#chipOk {
        background: $successSoft; border: 1px solid $successBorder; border-radius: 9px;
        color: $success; padding: 4px 10px; font-size: 11px;
    }
    QLabel#chipErr {
        background: $dangerSoft; border: 1px solid $dangerBorder; border-radius: 9px;
        color: $danger; padding: 4px 10px; font-size: 11px;
    }

    /* ---------- buttons ---------- */
    QPushButton {
        background: transparent;
        border: 1px solid $borderStrong;
        border-radius: 9px;
        padding: 0 14px;
        min-height: 34px;
        color: $text;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton:hover { background: $surfaceHover; border-color: $borderStrong; }
    QPushButton:pressed { background: $surface2; }
    QPushButton:disabled { color: $faint; border-color: $border; }
    QPushButton:focus { outline: none; }

    QPushButton#primaryBtn {
        background: $accent; border: 1px solid $accent; color: #FFFFFF; font-weight: 600;
    }
    QPushButton#primaryBtn:hover { background: $accentHover; border-color: $accentHover; }
    QPushButton#primaryBtn:pressed { background: $accentPress; border-color: $accentPress; }
    QPushButton#primaryBtn:disabled { background: $surface2; border-color: $border; color: $faint; }

    QPushButton#successBtn {
        background: $successSoft; border: 1px solid $successBorder; color: $success;
    }
    QPushButton#successBtn:hover { background: $successSoft; border-color: $success; }
    QPushButton#dangerBtn {
        background: transparent; border: 1px solid $dangerBorder; color: $danger;
    }
    QPushButton#dangerBtn:hover { background: $dangerSoft; border-color: $danger; }

    QPushButton#iconBtn {
        min-height: 28px; max-height: 28px; min-width: 28px; max-width: 28px;
        padding: 0; border-radius: 7px; border: 1px solid transparent;
        background: transparent; color: $dim;
    }
    QPushButton#iconBtn:hover { background: $surfaceHover; color: $text; }

    QPushButton#chipBtn {
        background: $chipBg; border: 1px solid $border; border-radius: 11px;
        min-height: 26px; max-height: 26px; padding: 0 11px;
        color: $dim; font-size: 11px; font-weight: 500;
    }
    QPushButton#chipBtn:hover { color: $text; border-color: $accentBorder; background: $accentSoft; }

    QPushButton#linkBtn {
        border: none; background: transparent; color: $accent; padding: 0;
        min-height: 24px; font-weight: 600;
    }
    QPushButton#linkBtn:hover { color: $accentHover; }

    /* ---------- segmented theme control ---------- */
    QFrame#segment {
        background: $surface2;
        border: 1px solid $border;
        border-radius: 9px;
    }
    QPushButton#segBtn {
        background: transparent; border: 1px solid transparent; border-radius: 7px;
        min-height: 24px; max-height: 24px; padding: 0 9px;
        color: $faint; font-size: 10px; font-weight: 600;
    }
    QPushButton#segBtn:hover { color: $text; }
    QPushButton#segBtn:checked {
        background: $surface; border-color: $borderStrong; color: $text;
    }

    /* ---------- inputs ---------- */
    QLineEdit, QTextEdit, QComboBox {
        background: $inputBg;
        border: 1px solid $border;
        border-radius: 9px;
        padding: 8px 10px;
        color: $text;
        selection-background-color: $accent;
        selection-color: #FFFFFF;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: $accent; }
    QLineEdit:disabled, QLineEdit[readOnly="true"] { color: $dim; }
    QComboBox { padding: 5px 10px; min-height: 22px; font-size: 12px; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView {
        background: $surface; border: 1px solid $borderStrong; border-radius: 8px;
        padding: 4px; outline: none;
        selection-background-color: $accentSoft; selection-color: $text;
    }
    QComboBox QAbstractItemView::item { min-height: 26px; padding: 2px 8px; border-radius: 5px; }

    QTextEdit#composer {
        font-size: 13px; padding: 10px 12px; border-radius: 10px;
    }
    QTextEdit#editor {
        font-family: "$mono"; font-size: 12.5px; padding: 14px;
        background: $inputBg; border: 1px solid $border; border-radius: 12px;
        selection-background-color: $accent;
    }
    QTextEdit#console, QTextEdit#installLog {
        background: $consoleBg; border: 1px solid $consoleBorder; border-radius: 10px;
        color: $monoText; font-family: "$mono"; font-size: 11.5px; padding: 12px;
        selection-background-color: rgba(123, 140, 255, 0.35);
    }

    /* ---------- chat ---------- */
    QScrollArea#chatArea {
        background: $surface; border: 1px solid $border; border-radius: 14px;
    }
    QFrame#bubbleUser {
        background: $accentSoft; border: 1px solid $accentBorder; border-radius: 12px;
        border-top-right-radius: 4px;
    }
    QFrame#bubbleBot {
        background: $surface2; border: 1px solid $border; border-radius: 12px;
        border-top-left-radius: 4px;
    }
    QLabel#bubbleSender { font-size: 10px; font-weight: 700; color: $faint; }
    QLabel#bubbleText { font-size: 13px; color: $text; }
    QFrame#bubbleUser QLabel#bubbleSender { color: $accent; }

    /* ---------- logs / separators ---------- */
    QFrame#hline { background: $border; border: none; max-height: 1px; min-height: 1px; }

    /* ---------- scrollbars ---------- */
    QScrollBar:vertical {
        background: transparent; width: 10px; margin: 2px;
    }
    QScrollBar::handle:vertical {
        background: $borderStrong; min-height: 30px; border-radius: 3px;
    }
    QScrollBar::handle:vertical:hover { background: $faint; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
    QScrollBar::handle:horizontal {
        background: $borderStrong; min-width: 30px; border-radius: 3px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

    /* ---------- misc ---------- */
    QMessageBox { background: $surface; }
    QMessageBox QLabel { color: $text; font-size: 13px; }
    QMenu {
        background: $surface; border: 1px solid $borderStrong; border-radius: 8px; padding: 5px;
    }
    QMenu::item { padding: 6px 18px; border-radius: 6px; color: $text; }
    QMenu::item:selected { background: $accentSoft; color: $text; }
    QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }
    """.replace("$font", FONT_UI).replace("$mono", FONT_MONO))
    return tpl.substitute(t)


# =============================================================================
#  Fonts
# =============================================================================

FONT_UI = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"


def init_fonts():
    global FONT_UI, FONT_MONO
    families = set(QFontDatabase().families())
    for candidate in ("Inter", "Noto Sans", "Cantarell", "DejaVu Sans"):
        if candidate in families:
            FONT_UI = candidate
            break
    for candidate in ("JetBrains Mono", "Cascadia Code", "Source Han Mono",
                      "DejaVu Sans Mono", "Noto Sans Mono"):
        if candidate in families:
            FONT_MONO = candidate
            break


def font(size, weight=QFont.Normal, family=None, spacing=None):
    f = QFont(family or FONT_UI)
    f.setPixelSize(int(round(size)))
    f.setWeight(weight)
    if spacing is not None:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


# =============================================================================
#  Vector icon set
# =============================================================================

ICON_NAMES = {
    "spark", "gauge", "chat", "cpu", "code", "info", "play", "stop", "restart",
    "copy", "globe", "folder", "terminal", "bolt", "check", "close", "trash",
    "send", "external", "sun", "moon", "auto", "shield", "layers", "download",
    "heart", "pulse", "plus", "clock", "monitor",
}


def draw_icon(painter, name, rect, color, stroke=1.7):
    """Paint a 24x24 line icon into ``rect``."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 24.0, rect.height() / 24.0)
    pen = QPen(QColor(color), stroke)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    def line(x1, y1, x2, y2):
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def poly(points, close=False):
        path = QPainterPath()
        path.moveTo(*points[0])
        for pt in points[1:]:
            path.lineTo(*pt)
        if close:
            path.closeSubpath()
        painter.drawPath(path)

    if name == "spark":
        path = QPainterPath()
        path.moveTo(12, 2.5)
        path.quadTo(13.2, 9.4, 21.5, 12)
        path.quadTo(13.2, 14.6, 12, 21.5)
        path.quadTo(10.8, 14.6, 2.5, 12)
        path.quadTo(10.8, 9.4, 12, 2.5)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
    elif name == "gauge":
        painter.drawArc(QRectF(3, 5, 18, 18), 200 * 16, 140 * 16)
        line(12, 14, 16.5, 8.5)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(12, 14), 1.5, 1.5)
    elif name == "chat":
        path = QPainterPath()
        path.addRoundedRect(QRectF(3, 4.5, 18, 12.5), 3.2, 3.2)
        painter.drawPath(path)
        poly([(8.5, 17), (8.5, 21), (13, 17)])
    elif name == "cpu":
        painter.drawRoundedRect(QRectF(6.5, 6.5, 11, 11), 2, 2)
        painter.drawRoundedRect(QRectF(10, 10, 4, 4), 1, 1)
        for v in (9.5, 12, 14.5):
            line(v, 3, v, 6.5)
            line(v, 17.5, v, 21)
            line(3, v, 6.5, v)
            line(17.5, v, 21, v)
    elif name == "code":
        poly([(9, 7), (4, 12), (9, 17)])
        poly([(15, 7), (20, 12), (15, 17)])
    elif name == "info":
        painter.drawEllipse(QPointF(12, 12), 8.7, 8.7)
        line(12, 11, 12, 16.5)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(12, 7.8), 1.05, 1.05)
    elif name == "play":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        poly([(8, 5.5), (18.5, 12), (8, 18.5)], close=True)
    elif name == "stop":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(7, 7, 10, 10), 2, 2)
    elif name == "restart":
        painter.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 280 * 16)
        poly([(18.6, 3.6), (19.8, 9.2), (14.2, 8.2)])
    elif name == "copy":
        painter.drawRoundedRect(QRectF(9, 9, 10.5, 10.5), 2, 2)
        poly([(15, 9), (15, 6), (6, 6), (6, 15), (9, 15)])
    elif name == "globe":
        painter.drawEllipse(QPointF(12, 12), 8.7, 8.7)
        painter.drawEllipse(QPointF(12, 12), 3.9, 8.7)
        line(3.3, 12, 20.7, 12)
    elif name == "folder":
        poly([(3.5, 18.5), (3.5, 6), (9.5, 6), (11.5, 8.5), (20.5, 8.5), (20.5, 18.5)],
             close=True)
    elif name == "terminal":
        painter.drawRoundedRect(QRectF(3, 4.5, 18, 15), 2.4, 2.4)
        poly([(7, 9.5), (10, 12.3), (7, 15)])
        line(12.5, 15.3, 16.5, 15.3)
    elif name == "bolt":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        poly([(13, 2.5), (5, 13.5), (11, 13.5), (10.4, 21.5), (19, 10.5), (13, 10.5)],
             close=True)
    elif name == "check":
        poly([(5, 12.5), (9.8, 17.2), (19, 7)])
    elif name == "close":
        line(6.5, 6.5, 17.5, 17.5)
        line(17.5, 6.5, 6.5, 17.5)
    elif name == "trash":
        line(4, 7, 20, 7)
        poly([(6, 7), (6.8, 19.2), (17.2, 19.2), (18, 7)])
        line(9.5, 7, 9.5, 4.6)
        line(14.5, 7, 14.5, 4.6)
        line(9.5, 4.6, 14.5, 4.6)
        line(10.5, 11, 10.5, 16.5)
        line(13.5, 11, 13.5, 16.5)
    elif name == "send":
        line(12, 20, 12, 5)
        poly([(5.5, 11.5), (12, 5), (18.5, 11.5)])
    elif name == "external":
        poly([(13.5, 4.5), (19.5, 4.5), (19.5, 10.5)])
        line(19.5, 4.5, 11, 13)
        poly([(17.5, 14), (17.5, 18.7), (5.3, 18.7), (5.3, 6.5), (10, 6.5)])
    elif name == "sun":
        painter.drawEllipse(QPointF(12, 12), 4.2, 4.2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            line(12 + 7 * math.cos(rad), 12 + 7 * math.sin(rad),
                 12 + 9.2 * math.cos(rad), 12 + 9.2 * math.sin(rad))
    elif name == "moon":
        outer = QPainterPath()
        outer.addEllipse(QRectF(3.2, 2.6, 18, 18))
        cut = QPainterPath()
        cut.addEllipse(QRectF(8.6, 0.6, 16, 16))
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(outer.subtracted(cut))
    elif name == "auto":
        painter.drawEllipse(QPointF(12, 12), 8.6, 8.6)
        path = QPainterPath()
        path.moveTo(12, 3.4)
        path.arcTo(QRectF(3.4, 3.4, 17.2, 17.2), 90, -180)
        path.closeSubpath()
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(12, 12), 8.6, 8.6)
    elif name == "shield":
        poly([(12, 3), (19.5, 6), (19.5, 11.5), (12, 21), (4.5, 11.5), (4.5, 6)],
             close=True)
        poly([(8.8, 11.6), (11.2, 14), (15.6, 9.4)])
    elif name == "layers":
        poly([(12, 3), (20.5, 7.6), (12, 12.2), (3.5, 7.6)], close=True)
        poly([(3.5, 12), (12, 16.6), (20.5, 12)])
        poly([(3.5, 16.2), (12, 20.8), (20.5, 16.2)])
    elif name == "download":
        line(12, 3.5, 12, 15)
        poly([(7.2, 10.4), (12, 15.2), (16.8, 10.4)])
        poly([(4, 19.5), (20, 19.5)])
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(12, 20)
        path.cubicTo(3, 14.4, 4.4, 6.4, 8.6, 6.4)
        path.cubicTo(10.6, 6.4, 11.6, 7.8, 12, 9)
        path.cubicTo(12.4, 7.8, 13.4, 6.4, 15.4, 6.4)
        path.cubicTo(19.6, 6.4, 21, 14.4, 12, 20)
        painter.drawPath(path)
    elif name == "pulse":
        poly([(2.5, 12), (6, 12), (8.4, 5.5), (12.4, 18.5), (15, 12), (21.5, 12)])
    elif name == "plus":
        line(12, 5.5, 12, 18.5)
        line(5.5, 12, 18.5, 12)
    elif name == "monitor":
        painter.drawRoundedRect(QRectF(3, 4.5, 18, 12.5), 2.2, 2.2)
        line(12, 17, 12, 20)
        line(8.5, 20, 15.5, 20)
    elif name == "clock":
        painter.drawEllipse(QPointF(12, 12), 8.6, 8.6)
        poly([(12, 7), (12, 12.3), (15.7, 14.3)])

    painter.restore()


class Icon(QWidget):
    def __init__(self, name, size=18, color=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._color = color
        self._tokens = TOKENS["dark"]

    def set_color(self, color):
        self._color = color
        self.update()

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        draw_icon(p, self.name, QRectF(0, 0, self.width(), self.height()),
                  self._color or self._tokens["dim"])
        p.end()


class LogoMark(QWidget):
    """The OmniHub emblem: an orbital hub with three routed nodes."""

    def __init__(self, size=40, is_dark=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.is_dark = is_dark

    def set_theme(self, is_dark):
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        p.scale(s / 240.0, s / 240.0)

        if self.is_dark:
            grad = QLinearGradient(36, 0, 204, 240)
            grad.setColorAt(0, QColor("#171D33"))
            grad.setColorAt(1, QColor("#0A0D16"))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor("#2A3350"), 3))
        else:
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.setPen(QPen(QColor("#D8DEEA"), 3))
        p.drawRoundedRect(QRectF(3, 3, 234, 234), 60, 60)

        if self.is_dark:
            ring, spoke, node = QColor("#7B8CFF"), QColor("#AEB8FF"), QColor("#E7ECF4")
            hub, core = QColor("#5EEAD4"), QColor("#0B1020")
        else:
            ring, spoke, node = QColor("#4F5FE0"), QColor("#9AA6F0"), QColor("#1B2350")
            hub, core = QColor("#0D9488"), QColor("#FFFFFF")

        p.save()
        p.translate(38.4, 38.4)
        p.scale(0.68, 0.68)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(ring, 13))
        p.drawEllipse(QPointF(120, 120), 96, 96)

        p.setPen(QPen(spoke, 7, Qt.SolidLine, Qt.RoundCap))
        for pt in (QPointF(120, 24), QPointF(203.1, 168), QPointF(36.9, 168)):
            p.drawLine(QPointF(120, 120), pt)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(node))
        for pt in (QPointF(120, 24), QPointF(203.1, 168), QPointF(36.9, 168)):
            p.drawEllipse(pt, 13, 13)

        p.setBrush(QBrush(hub))
        p.drawEllipse(QPointF(120, 120), 28, 28)
        p.setBrush(QBrush(core))
        p.drawEllipse(QPointF(120, 120), 9, 9)
        p.restore()
        p.end()


# =============================================================================
#  Animation helpers
# =============================================================================

def fade_in(widget, duration=220, start=0.0):
    previous = getattr(widget, "_fade_anim", None)
    if previous is not None and previous.state() == QPropertyAnimation.Running:
        previous.stop()
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def _cleanup():
        anim.stop()
        if getattr(widget, "_fade_anim", None) is not anim:
            anim.deleteLater()
            return
        try:
            widget.setGraphicsEffect(None)
        except (RuntimeError, TypeError):
            pass
        widget._fade_anim = None
        anim.deleteLater()

    anim.finished.connect(_cleanup)
    widget._fade_anim = anim
    anim.start()
    return anim


def grow_in(widget, duration=210):
    """Fade + height reveal, used for chat bubbles and toasts."""
    target = max(widget.sizeHint().height(), 10)
    widget.setMaximumHeight(0)
    fade_in(widget, duration)
    anim = QPropertyAnimation(widget, b"maximumHeight", widget)
    anim.setDuration(duration)
    anim.setStartValue(0)
    anim.setEndValue(target + 4)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(lambda: widget.setMaximumHeight(16777215))
    anim.start()
    return anim


def animate_number(label, value, suffix="", prefix="", duration=450, fmt="{:,}"):
    try:
        value = int(round(value))
    except Exception:
        label.setText(f"{prefix}{value}{suffix}")
        return None
    anim = QVariantAnimation(label)
    anim.setDuration(duration)
    anim.setStartValue(0)
    anim.setEndValue(value)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def _set(v):
        try:
            label.setText(f"{prefix}{fmt.format(int(v))}{suffix}")
        except Exception:
            pass

    anim.valueChanged.connect(_set)
    anim.start(QVariantAnimation.DeleteWhenStopped)
    return anim


# =============================================================================
#  Widget kit
# =============================================================================

def label(text, object_name=None, size=None, weight=None, color=None,
          spacing=None, mono=False, wrap=False):
    lbl = QLabel(text)
    if object_name:
        lbl.setObjectName(object_name)
    if wrap:
        lbl.setWordWrap(True)
    if size is not None or weight is not None or spacing is not None or mono:
        lbl.setFont(font(size or 13, weight if weight is not None else QFont.Normal,
                        FONT_MONO if mono else None, spacing))
    if color:
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
    return lbl


def section_label(text):
    return label(text, "sectionLabel", 10, QFont.DemiBold, spacing=1.1)


def hline():
    line = QFrame()
    line.setObjectName("hline")
    line.setFixedHeight(1)
    return line


class Card(QFrame):
    def __init__(self, accent=False, parent=None):
        super().__init__(parent)
        self.setObjectName("cardAccent" if accent else "card")


class IconButton(QPushButton):
    def __init__(self, icon_name, tooltip="", size=28, icon_size=15, parent=None):
        super().__init__(parent)
        self.setObjectName("iconBtn")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self._icon = Icon(icon_name, icon_size, parent=self)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._icon)
        self._tokens = TOKENS["dark"]

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self._icon.apply_tokens(tokens)

    def enterEvent(self, event):
        self._icon.set_color(self._tokens["text"])
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._icon.set_color(self._tokens["dim"])
        super().leaveEvent(event)


class NavButton(QPushButton):
    """Sidebar item with animated hover and active indicator."""

    def __init__(self, text, icon_name, parent=None):
        super().__init__(text, parent)
        self.label_text = text
        self.icon_name = icon_name
        self._hover = 0.0
        self._active = 0.0
        self._tokens = TOKENS["dark"]
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFont(font(12.5, QFont.Medium))

        self._hover_anim = QPropertyAnimation(self, b"hoverP", self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._active_anim = QPropertyAnimation(self, b"activeP", self)
        self._active_anim.setDuration(180)
        self._active_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate_active)

    # animated properties -------------------------------------------------
    def get_hover(self):
        return self._hover

    def set_hover(self, value):
        self._hover = float(value)
        self.update()

    hoverP = pyqtProperty(float, get_hover, set_hover)

    def get_active(self):
        return self._active

    def set_active(self, value):
        self._active = float(value)
        self.update()

    activeP = pyqtProperty(float, get_active, set_active)

    def _animate_active(self, checked):
        self._active_anim.stop()
        self._active_anim.setStartValue(self._active)
        self._active_anim.setEndValue(1.0 if checked else 0.0)
        self._active_anim.start()

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        if self._hover > 0.01:
            bg = QColor(t["text"])
            bg.setAlphaF(0.055 * self._hover * (1 - self._active))
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 8, 8)

        if self._active > 0.01:
            bg = QColor(t["accent"])
            bg.setAlphaF(0.13 * self._active)
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 8, 8)
            bar = QColor(t["accent"])
            bar.setAlphaF(self._active)
            p.setBrush(bar)
            p.drawRoundedRect(QRectF(0, (self.height() - 16) / 2, 2.5, 16), 1.25, 1.25)

        base = QColor(t["dim"])
        if self._active > 0.01:
            target = QColor(t["text"])
            base = QColor(
                int(base.red() + (target.red() - base.red()) * self._active),
                int(base.green() + (target.green() - base.green()) * self._active),
                int(base.blue() + (target.blue() - base.blue()) * self._active),
            )
        if self._hover > 0.01:
            target = QColor(t["text"])
            base = QColor(
                int(base.red() + (target.red() - base.red()) * self._hover),
                int(base.green() + (target.green() - base.green()) * self._hover),
                int(base.blue() + (target.blue() - base.blue()) * self._hover),
            )

        icon_color = t["accent"] if self._active > 0.5 else base.name()
        draw_icon(p, self.icon_name, QRectF(13, (self.height() - 16) / 2, 16, 16), icon_color, 1.65)

        p.setPen(base)
        p.setFont(self.font())
        p.drawText(QRectF(40, 0, self.width() - 48, self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.label_text)
        p.end()


class StatusDot(QWidget):
    def __init__(self, size=9, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 8, size + 8)
        self.size_ = size
        self.state = "off"
        self._tokens = TOKENS["dark"]
        self._phase = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(2200)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, v):
        self._phase = float(v)
        self.update()

    def set_state(self, state):
        self.state = state
        if state == "on":
            if self._anim.state() != QVariantAnimation.Running:
                self._anim.start()
        else:
            self._anim.stop()
            self._phase = 0.0
        self.update()

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        t = self._tokens
        if self.state == "on":
            color = QColor(t["success"])
            halo = QColor(color)
            halo.setAlphaF(0.30 * (1 - self._phase))
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            radius = self.size_ / 2 + 6 * self._phase
            p.drawEllipse(QPointF(cx, cy), radius, radius)
        elif self.state == "warn":
            color = QColor(t["warn"])
        else:
            color = QColor(t["danger"])
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx, cy), self.size_ / 2, self.size_ / 2)
        p.end()


class ProgressBar(QWidget):
    """Painted progress bar with an eased value transition."""

    def __init__(self, height=6, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._value = 0.0
        self._target = 0.0
        self._tokens = TOKENS["dark"]
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(420)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

    def _on_value(self, v):
        self._value = float(v)
        self.update()

    def setValue(self, value):
        value = max(0.0, min(100.0, float(value)))
        self._target = value
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(value)
        self._anim.start()

    def value(self):
        return int(round(self._target))

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t["surface2"]))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        if self._value > 0:
            fill_w = max(h, w * (self._value / 100.0))
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0, QColor(t["accent"]))
            grad.setColorAt(1, QColor(t["success"]) if self._value >= 100 else QColor(t["accentHover"]))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(0, 0, fill_w, h), h / 2, h / 2)
        p.end()


class Sparkline(QWidget):
    def __init__(self, height=34, max_points=36, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setMinimumWidth(60)
        self.values = []
        self.max_points = max_points
        self._tokens = TOKENS["dark"]
        self._accent = None

    def push(self, value):
        try:
            self.values.append(float(value))
        except (TypeError, ValueError):
            return
        self.values = self.values[-self.max_points:]
        self.update()

    def apply_tokens(self, tokens, accent=None):
        self._tokens = tokens
        self._accent = accent
        self.update()

    def paintEvent(self, event):
        if len(self.values) < 2:
            return
        t = self._tokens
        accent = QColor(self._accent or t["accent"])
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = 2
        lo, hi = min(self.values), max(self.values)
        span = max(hi - lo, 1e-6)
        pts = []
        n = len(self.values)
        for i, v in enumerate(self.values):
            x = pad + (w - 2 * pad) * (i / max(n - 1, 1))
            y = h - pad - (h - 2 * pad) * ((v - lo) / span if span > 1e-6 else 0.5)
            pts.append(QPointF(x, y))

        path = QPainterPath()
        path.moveTo(pts[0])
        for i in range(1, len(pts)):
            prev, cur = pts[i - 1], pts[i]
            mid = QPointF((prev.x() + cur.x()) / 2, (prev.y() + cur.y()) / 2)
            path.quadTo(prev, mid)
            if i == len(pts) - 1:
                path.lineTo(cur)

        area = QPainterPath(path)
        area.lineTo(w - pad, h)
        area.lineTo(pad, h)
        area.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        top = QColor(accent)
        top.setAlphaF(0.22)
        bottom = QColor(accent)
        bottom.setAlphaF(0.0)
        grad.setColorAt(0, top)
        grad.setColorAt(1, bottom)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(area)

        pen = QPen(accent, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.setBrush(accent)
        p.setPen(Qt.NoPen)
        p.drawEllipse(pts[-1], 2.1, 2.1)
        p.end()


class StepDot(QWidget):
    def __init__(self, number, size=22, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.number = number
        self.state = "pending"
        self._tokens = TOKENS["dark"]

    def set_state(self, state):
        self.state = state
        self.update()

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6)
        if self.state == "done":
            bg, fg, border = t["success"], t["white"], t["success"]
            text = None
        elif self.state == "running":
            bg, fg, border = t["accent"], t["white"], t["accent"]
            text = None
        elif self.state == "error":
            bg, fg, border = t["danger"], t["white"], t["danger"]
            text = None
        else:
            bg, fg, border = "transparent", t["faint"], t["border"]
            text = str(self.number)

        if bg != "transparent":
            p.setBrush(QColor(bg))
        else:
            p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(border), 1.2))
        p.drawEllipse(r)
        if self.state == "done":
            draw_icon(p, "check", QRectF(5, 5, self.width() - 10, self.height() - 10), fg, 2.0)
        elif self.state == "error":
            draw_icon(p, "close", QRectF(5.5, 5.5, self.width() - 11, self.height() - 11), fg, 2.0)
        elif self.state == "running":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(fg))
            p.drawEllipse(QPointF(self.width() / 2, self.height() / 2), 2.2, 2.2)
        else:
            p.setPen(QColor(fg))
            p.setFont(font(9.5, QFont.DemiBold, FONT_MONO))
            p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignCenter, text)
        p.end()


class StepRow(QFrame):
    def __init__(self, number, title, subtitle, parent=None):
        super().__init__(parent)
        self.setObjectName("stepRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 7, 8, 7)
        lay.setSpacing(12)

        self.dot = StepDot(number)
        lay.addWidget(self.dot)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.l1 = QLabel(title)
        self.l1.setFont(font(12.5, QFont.DemiBold))
        self.l2 = QLabel(subtitle)
        self.l2.setObjectName("hint")
        text_box.addWidget(self.l1)
        text_box.addWidget(self.l2)
        lay.addLayout(text_box, 1)

        self.status = QLabel("Pending")
        self.status.setObjectName("hint")
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.status)

    def set_state(self, state, text, color):
        self._state = state
        self._state_text = text
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; background: transparent; font-size: 11px;")
        self.dot.set_state(state)

    def apply_tokens(self, tokens):
        self.dot.apply_tokens(tokens)
        state = getattr(self, "_state", "pending")
        text = getattr(self, "_state_text", "Pending")
        color = {
            "done": tokens["success"],
            "running": tokens["accent"],
            "error": tokens["danger"],
        }.get(state, tokens["faint"])
        self.status.setStyleSheet(f"color: {color}; background: transparent; font-size: 11px;")


class ChatBubble(QFrame):
    def __init__(self, sender, text, is_user=False, parent=None, tokens=None):
        super().__init__(parent)
        self.setObjectName("bubbleUser" if is_user else "bubbleBot")
        self.setMaximumWidth(640)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 11)
        lay.setSpacing(3)

        self.sender_label = QLabel(sender)
        self.sender_label.setObjectName("bubbleSender")
        lay.addWidget(self.sender_label)

        self.text_label = QLabel()
        self.text_label.setObjectName("bubbleText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tokens = tokens or TOKENS["dark"]
        self.text_label.setText(render_chat_text(text, self.tokens))
        self.text_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        lay.addWidget(self.text_label)

        plain = re.sub(r"```", "", str(text))
        metrics = QFontMetrics(font(13))
        natural = metrics.boundingRect(
            QtCore.QRect(0, 0, 540, 10000), Qt.TextWordWrap, plain).width()
        width = max(240, min(600, natural + 34))
        self.setFixedWidth(width)

        # QLabel inside a fixed-width frame does not always report its wrapped
        # height to the layout, so measure the rich document explicitly.
        document = QTextDocument()
        document.setDefaultFont(font(13))
        document.setHtml(render_chat_text(text, self.tokens))
        document.setTextWidth(width - 30)
        self.text_label.setMinimumHeight(int(math.ceil(document.size().height())) + 2)


def render_chat_text(text, tokens=None):
    """Escape untrusted model output and render fences/inline code safely."""
    t = tokens or TOKENS["dark"]
    raw = str(text)
    blocks = re.split(r"```", raw)
    out = []
    for index, block in enumerate(blocks):
        if index % 2 == 1:
            code = block.strip("\n")
            lines = code.split("\n")
            if lines and re.match(r"^[A-Za-z0-9_+.#-]{1,16}$", lines[0].strip()):
                lines = lines[1:]
            code = "\n".join(lines)
            out.append(
                '<table width="100%%" cellpadding="8" cellspacing="0" bgcolor="%s">'
                '<tr><td><pre style="font-family:\'%s\'; font-size:11.5px; '
                'color:%s; margin:0;">%s</pre></td></tr></table>'
                % (t["surfaceHover"], FONT_MONO, t["text"], html.escape(code))
            )
        else:
            escaped = html.escape(block)
            escaped = re.sub(
                r"`([^`\n]+)`",
                r"<code style=\"font-family:'%s'; color:%s\">\1</code>" % (FONT_MONO, t["accent"]),
                escaped,
            )
            escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
            escaped = escaped.replace("\n", "<br/>")
            out.append(escaped)
    return "".join(out)


class TypingDots(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 18)
        self._phase = 0.0
        self._tokens = TOKENS["dark"]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(110)

    def _tick(self):
        self._phase = (self._phase + 0.16) % 1.0
        self.update()

    def apply_tokens(self, tokens):
        self._tokens = tokens

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(self._tokens["dim"])
        for i in range(3):
            alpha = 0.35 + 0.65 * (0.5 + 0.5 * math.sin((self._phase * 2 * math.pi) - i * 0.7))
            c = QColor(color)
            c.setAlphaF(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(7 + i * 13, 9), 2.6, 2.6)
        p.end()


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("card")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._tokens = TOKENS["dark"]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 14, 9)
        lay.setSpacing(9)
        self.icon = Icon("check", 15, parent=self)
        lay.addWidget(self.icon)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(300)
        self.label.setFont(font(12, QFont.Medium))
        lay.addWidget(self.label)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide_anim)
        self._anim = None

    def show_message(self, text, kind="ok"):
        t = self._tokens
        color = {"ok": t["success"], "error": t["danger"], "info": t["accent"]}.get(kind, t["accent"])
        icon = {"ok": "check", "error": "close", "info": "info"}.get(kind, "info")
        self.icon.name = icon
        self.icon.set_color(color)
        self.label.setStyleSheet(f"color: {t['text']};")
        self.label.setText(text)
        self.label.setFixedWidth(300)
        self.setFixedWidth(382)
        self.layout().activate()
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move(parent.width() - self.width() - 26,
                      parent.height() - self.height() - 104)
        self.show()
        self.raise_()
        self._slide_in()
        self._timer.start(2600)

    def _slide_in(self):
        if self._anim:
            self._anim.stop()
        start = QPoint(self.x(), self.y() + 10)
        end = QPoint(self.x(), self.y())
        self.move(start)
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(200)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()
        fade_in(self, 180)

    def _hide_anim(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self._finish_hide)
        anim.start()
        self._hide_anim_ref = anim

    def _finish_hide(self):
        self.setGraphicsEffect(None)
        self.hide()

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.icon.apply_tokens(tokens)


def restyle(widget, object_name):
    widget.setObjectName(object_name)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class Backdrop(QWidget):
    """Content surface with a faint dot-grid and a soft accent glow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens = TOKENS["dark"]
        self._pattern = None
        self._pattern_bg = None

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self._pattern = None
        self._pattern_bg = None
        self.update()

    def _build_pattern(self):
        dot = QPixmap(26, 26)
        dot.fill(Qt.transparent)
        p = QPainter(dot)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(qcolor(self._tokens["grid"]))
        p.drawEllipse(QPointF(13, 13), 1.0, 1.0)
        p.end()
        self._pattern = dot

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(t["bg"]))

        glow = QRadialGradient(QPointF(self.width() * 0.78, -self.height() * 0.15),
                              max(self.width(), self.height()) * 0.95)
        c0 = QColor(123, 140, 255)
        c0.setAlphaF(0.0)
        glow.setColorAt(0.0, qcolor(t["glow"]))
        glow.setColorAt(1.0, c0)
        p.fillRect(self.rect(), QBrush(glow))

        if self._pattern is None:
            self._build_pattern()
        p.drawTiledPixmap(self.rect(), self._pattern)
        p.end()


class ThemeSwitch(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("segment")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for index, (key, icon_name, tip) in enumerate((
            ("system", "monitor", "Follow system theme"),
            ("dark", "moon", "Dark theme"),
            ("light", "sun", "Light theme"),
        )):
            btn = QPushButton()
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setFixedSize(34, 24)
            icon = Icon(icon_name, 13, parent=btn)
            icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            icon.move(10, 5)
            btn._icon = icon
            self.group.addButton(btn, index)
            self.buttons.append(btn)
            lay.addWidget(btn)
        self.buttons[0].setChecked(True)
        self._tokens = TOKENS["dark"]

    def apply_tokens(self, tokens):
        self._tokens = tokens
        for btn in self.buttons:
            btn._icon.apply_tokens(tokens)

    def set_index(self, index):
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)


class MetricCard(QFrame):
    def __init__(self, title, value, subtitle, icon_name="pulse", accent=None,
                 dot=False, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.accent = accent
        self._tokens = TOKENS["dark"]
        self.dot = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 15, 18, 15)
        lay.setSpacing(7)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("kpiTitle")
        self.title_label.setFont(font(9.5, QFont.DemiBold, spacing=1.0))
        head.addWidget(self.title_label)
        head.addStretch()
        self.icon = Icon(icon_name, 16, accent, parent=self) if icon_name else None
        if self.icon is not None:
            head.addWidget(self.icon)
        if dot:
            self.dot = StatusDot(7, parent=self)
            head.addWidget(self.dot)
        lay.addLayout(head)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("kpiValue")
        self.value_label.setFont(font(25, QFont.DemiBold, FONT_UI, spacing=-0.4))
        bottom.addWidget(self.value_label)
        bottom.addStretch()
        self.spark = None
        lay.addLayout(bottom)

        self.sub_label = QLabel(subtitle)
        self.sub_label.setObjectName("kpiSub")
        lay.addWidget(self.sub_label)

    def add_sparkline(self):
        self.spark = Sparkline(30, parent=self)
        self.layout().addWidget(self.spark)
        return self.spark

    def apply_tokens(self, tokens):
        self._tokens = tokens
        if self.icon is not None:
            self.icon.apply_tokens(tokens)
        if self.dot:
            self.dot.apply_tokens(tokens)
        if self.spark:
            self.spark.apply_tokens(tokens, self.accent)


from PyQt5.QtGui import QFontMetrics, QKeySequence
from PyQt5.QtWidgets import QShortcut


# =============================================================================
#  Buttons with painted icons (consistent colours across states)
# =============================================================================

class ActionButton(QPushButton):
    def __init__(self, text, icon_name=None, kind="secondary", height=36, parent=None):
        super().__init__(parent)
        self._text = text
        self._icon_name = icon_name
        self._kind = kind
        self._hover = 0.0
        self._down = False
        self._tokens = TOKENS["dark"]
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(font(12, QFont.Medium))
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.NoFocus)
        self._anim = QPropertyAnimation(self, b"hoverP", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def setText(self, text):
        self._text = text
        self.updateGeometry()
        self.update()

    def text(self):
        return self._text

    def get_hover(self):
        return self._hover

    def set_hover(self, value):
        self._hover = float(value)
        self.update()

    hoverP = pyqtProperty(float, get_hover, set_hover)

    def apply_tokens(self, tokens):
        self._tokens = tokens
        self.update()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        extra = 24 if self._icon_name else 10
        return QSize(fm.horizontalAdvance(self._text) + 32 + extra, self.height())

    def enterEvent(self, event):
        if self.isEnabled():
            self._anim.stop()
            self._anim.setStartValue(self._hover)
            self._anim.setEndValue(1.0)
            self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(0.0)
        self._anim.start()
        self._down = False
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._down = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._down = False
        self.update()
        super().mouseReleaseEvent(event)

    def _colors(self):
        t = self._tokens
        kind = self._kind
        if not self.isEnabled():
            return t["surface2"], t["border"], t["faint"]
        if kind == "primary":
            bg = {"n": t["accent"], "h": t["accentHover"], "d": t["accentPress"]}
            return self._pick(bg), t["accent"], t["white"]
        if kind == "success":
            border = t["success"] if self._hover > 0.4 else t["successBorder"]
            return t["successSoft"], border, t["success"]
        if kind == "danger":
            border = t["danger"] if self._hover > 0.4 else t["dangerBorder"]
            return t["dangerSoft"] if self._hover > 0.4 else "transparent", border, t["danger"]
        if kind == "ghost":
            return (t["surfaceHover"] if self._hover > 0.05 else "transparent",
                    "transparent", t["text"] if self._hover > 0.4 else t["dim"])
        bg = t["surfaceHover"] if self._hover > 0.05 else "transparent"
        border = t["borderStrong"]
        return bg, border, t["text"]

    def _pick(self, mapping):
        if self._down:
            return mapping["d"]
        if self._hover > 0.3:
            return mapping["h"]
        return mapping["n"]

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        bg, border, fg = self._colors()
        p.setBrush(qcolor(bg) if bg != "transparent" else Qt.NoBrush)
        p.setPen(QPen(qcolor(border), 1) if border != "transparent" else Qt.NoPen)
        p.drawRoundedRect(r, 9, 9)

        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self._text)
        total = text_w + (23 if self._icon_name else 0)
        x = (self.width() - total) / 2
        if self._icon_name:
            draw_icon(p, self._icon_name, QRectF(x, (self.height() - 15) / 2, 15, 15), fg, 1.6)
            x += 23
        p.setPen(QColor(fg))
        p.setFont(self.font())
        p.drawText(QRectF(x, 0, text_w + 2, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self._text)
        p.end()


def make_button(text, icon_name=None, kind="secondary", height=36, slot=None, tooltip=None):
    btn = ActionButton(text, icon_name, kind, height)
    if slot:
        btn.clicked.connect(slot)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


# =============================================================================
#  Main window
# =============================================================================

PAGE_META = [
    ("Setup", "Install and operate the OmniRoute gateway"),
    ("Gateway", "Traffic, routing and service health"),
    ("AI Studio", "Direct inference against the local gateway"),
    ("System", "Host telemetry and runtime details"),
    ("Scratchpad", "Notes, payloads and quick utilities"),
    ("About", "Project, credits and support"),
]

PAGE_KEYS = {
    "start": 0, "setup": 0, "install": 0,
    "gateway": 1, "overview": 1,
    "ai": 2, "chat": 2, "studio": 2,
    "system": 3, "radar": 3,
    "tools": 4, "scratchpad": 4, "code": 4,
    "about": 5, "support": 5,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        self.setMinimumSize(1040, 700)
        self.resize(1240, 820)

        icon_path = get_app_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        self.theme_mode = "system"
        self.active_theme = detect_system_theme()
        self.tokens = TOKENS[self.active_theme]
        self._themed = []
        self._first_show = True

        self.init_layout()
        self.apply_theme(self.active_theme)
        self.setup_tray()

        self.health_worker = HealthCheckWorker(self)
        self.health_worker.result.connect(self.on_health_result)

        self.doctor_worker = DoctorWorker(self)
        self.doctor_worker.log_line.connect(lambda line: self.log_msg(line, "ok"))

        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self.check_omniroute_health)
        self.health_timer.start(3000)

        self.sys_timer = QTimer(self)
        self.sys_timer.timeout.connect(self.update_system_stats)
        self.sys_timer.start(2000)

        # Theme probing spawns gsettings subprocesses, so keep it inexpensive.
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_auto_theme)
        self.theme_timer.start(20000)

        self._install_timer = QTimer(self)
        self._install_timer.timeout.connect(self._tick_install_clock)

        self._setup_shortcuts()
        self.check_omniroute_health()
        self.update_system_stats()

    # ------------------------------------------------------------------ utils
    def _setup_shortcuts(self):
        for index in range(len(PAGE_META)):
            QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self,
                      activated=lambda i=index: self.switch_page(i))
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._focus_ai_prompt)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self,
                  activated=lambda: self.run_gateway_action("restart"))

    def _focus_ai_prompt(self):
        self.switch_page(2)
        self.txt_ai_prompt.setFocus()

    def _register(self, widget):
        self._themed.append(widget)
        return widget

    def show_toast(self, message, kind="ok"):
        self.toast.show_message(message, kind)

    def closeEvent(self, event):
        try:
            self.health_timer.stop()
            self.sys_timer.stop()
            self.theme_timer.stop()
            self.save_notes()
            for worker_name in ("health_worker", "doctor_worker"):
                worker = getattr(self, worker_name, None)
                if worker is not None and worker.isRunning():
                    worker.quit()
                    worker.wait(700)
            installer = getattr(self, "installer_worker", None)
            if installer is not None and installer.isRunning():
                installer.cancel()
                installer.wait(2500)
            for worker_name in ("ai_worker", "gw_worker", "doctor_worker"):
                worker = getattr(self, worker_name, None)
                if worker is not None and worker.isRunning():
                    worker.terminate()
                    worker.wait(400)
        except Exception:
            pass
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            fade_in(self.centralWidget(), 260)
            self.switch_page(0, animate=False)

    # ------------------------------------------------------------------ theme
    def on_theme_selection_changed(self, index):
        self.theme_mode = ("system", "dark", "light")[index] if 0 <= index <= 2 else "system"
        self.apply_theme(detect_system_theme() if self.theme_mode == "system" else self.theme_mode)

    def check_auto_theme(self):
        if self.theme_mode == "system":
            detected = detect_system_theme()
            if detected != self.active_theme:
                self.apply_theme(detected)

    def apply_theme(self, theme_name):
        theme_name = theme_name if theme_name in TOKENS else "dark"
        self.active_theme = theme_name
        is_dark = theme_name == "dark"
        self.tokens = TOKENS[theme_name]

        self.setStyleSheet(build_qss(self.tokens))

        for widget in [self] + self.findChildren(QWidget):
            apply_tokens = getattr(widget, "apply_tokens", None)
            if callable(apply_tokens):
                try:
                    apply_tokens(self.tokens)
                except Exception:
                    pass

        if hasattr(self, "sidebar_logo"):
            self.sidebar_logo.set_theme(is_dark)
        if hasattr(self, "about_logo"):
            self.about_logo.set_theme(is_dark)
        if hasattr(self, "chip_latency"):
            self._render_latency_chip(self._last_latency, self._is_online)
        if hasattr(self, "chat_scroll"):
            self.chat_scroll.setStyleSheet("")

    def _render_latency_chip(self, latency, online):
        self._last_latency = latency
        self._is_online = online
        chip = self.chip_latency
        if online:
            chip.setObjectName("chipOk")
            chip.setText(f"● Online · {latency} ms")
        else:
            chip.setObjectName("chipErr")
            chip.setText("● Offline")
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        chip.adjustSize()

    # ------------------------------------------------------------------ layout
    def init_layout(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        content = Backdrop()
        content.setObjectName("content")
        self.content = self._register(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 20, 26, 22)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_topbar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self.create_start_page())
        self.pages.addWidget(self.create_gateway_page())
        self.pages.addWidget(self.create_ai_page())
        self.pages.addWidget(self.create_system_page())
        self.pages.addWidget(self.create_tools_page())
        self.pages.addWidget(self.create_about_page())
        content_layout.addWidget(self.pages, 1)

        root_layout.addWidget(content, 1)

        self.toast = Toast(content)
        self.toast.apply_tokens(self.tokens)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.move(self.toast.parentWidget().width() - self.toast.width() - 26,
                            self.toast.parentWidget().height() - self.toast.height() - 104)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 16, 12, 14)
        lay.setSpacing(4)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        self.sidebar_logo = LogoMark(34, self.active_theme == "dark")
        brand.addWidget(self.sidebar_logo)

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setObjectName("brandName")
        name.setFont(font(16, QFont.Bold, spacing=-0.2))
        tag = QLabel("AI GATEWAY STUDIO")
        tag.setObjectName("brandTag")
        tag.setFont(font(9, QFont.DemiBold, spacing=1.0))
        text_box.addWidget(name)
        text_box.addWidget(tag)
        brand.addLayout(text_box)
        brand.addStretch()
        lay.addLayout(brand)
        lay.addSpacing(18)

        nav_label = QLabel("WORKSPACE")
        nav_label.setObjectName("navSection")
        nav_label.setFont(font(9, QFont.DemiBold, spacing=1.2))
        nav_label.setContentsMargins(10, 0, 0, 4)
        lay.addWidget(nav_label)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        entries = [
            ("Setup", "spark"),
            ("Gateway", "gauge"),
            ("AI Studio", "chat"),
            ("System", "cpu"),
            ("Scratchpad", "code"),
            ("About", "info"),
        ]
        self.nav_buttons = []
        for index, (text, icon_name) in enumerate(entries):
            btn = self._register(NavButton(text, icon_name))
            btn.setToolTip(f"{text}  (Ctrl+{index + 1})")
            self.nav_group.addButton(btn, index)
            lay.addWidget(btn)
            self.nav_buttons.append(btn)
        self.nav_buttons[0].setChecked(True)
        self.nav_group.buttonClicked[int].connect(self.switch_page)

        lay.addStretch()

        # gateway status
        card = QFrame()
        card.setObjectName("statusCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        self.sb_dot = self._register(StatusDot(8))
        head.addWidget(self.sb_dot)
        head.addWidget(label("GATEWAY", "sectionLabel", 9, QFont.DemiBold, spacing=1.0))
        head.addStretch()
        card_layout.addLayout(head)

        self.lbl_sb_status = QLabel("Offline")
        self.lbl_sb_status.setFont(font(12, QFont.DemiBold))
        card_layout.addWidget(self.lbl_sb_status)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.lbl_sb_info = QLabel(get_gateway_host_display())
        self.lbl_sb_info.setObjectName("mono")
        bottom.addWidget(self.lbl_sb_info)
        bottom.addStretch()
        restart = IconButton("restart", "Restart gateway", 26, 14)
        restart.clicked.connect(lambda: self.run_gateway_action("restart"))
        self._register(restart)
        bottom.addWidget(restart)
        card_layout.addLayout(bottom)
        lay.addWidget(card)

        version = QLabel(f"v{APP_VERSION} · GPL-3.0")
        version.setObjectName("hint")
        version.setAlignment(Qt.AlignCenter)
        version.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(version)
        return sidebar

    def _build_topbar(self):
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_eyebrow = QLabel("WORKSPACE / 01")
        self.lbl_eyebrow.setObjectName("eyebrow")
        self.lbl_eyebrow.setFont(font(9.5, QFont.DemiBold, spacing=1.1))
        self.lbl_header_title = QLabel("Setup")
        self.lbl_header_title.setObjectName("pageTitle")
        self.lbl_header_title.setFont(font(22, QFont.Bold, spacing=-0.4))
        self.lbl_header_desc = QLabel(PAGE_META[0][1])
        self.lbl_header_desc.setObjectName("pageDesc")
        title_box.addWidget(self.lbl_eyebrow)
        title_box.addWidget(self.lbl_header_title)
        title_box.addWidget(self.lbl_header_desc)
        lay.addLayout(title_box)
        lay.addStretch()

        self.chip_latency = QLabel("● Offline")
        self.chip_latency.setObjectName("chipErr")
        self.chip_latency.setFont(font(11, QFont.Medium))
        self.chip_latency.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.chip_latency, 0, Qt.AlignVCenter)
        self._last_latency = 0
        self._is_online = False

        self.theme_switch = self._register(ThemeSwitch())
        self.theme_switch.group.idClicked.connect(self.on_theme_selection_changed)
        lay.addWidget(self.theme_switch, 0, Qt.AlignVCenter)

        self.btn_dashboard = make_button("Dashboard", "external", "primary", 34,
                                         self.open_dashboard, "Open the OmniRoute web dashboard")
        lay.addWidget(self.btn_dashboard, 0, Qt.AlignVCenter)
        return bar

    def switch_page(self, index, animate=True):
        if not (0 <= index < len(PAGE_META)):
            return
        self.pages.setCurrentIndex(index)
        title, desc = PAGE_META[index]
        self.lbl_header_title.setText(title)
        self.lbl_header_desc.setText(desc)
        self.lbl_eyebrow.setText(f"WORKSPACE / {index + 1:02d}")
        btn = self.nav_group.button(index)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)
        if animate:
            fade_in(self.pages.currentWidget(), 200, 0.35)

    # ------------------------------------------------------------------ cards
    def _card(self, accent=False, margins=(18, 16, 18, 16), spacing=10):
        card = Card(accent=accent)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(*margins)
        lay.setSpacing(spacing)
        return card, lay

    def _card_head(self, lay, title, right=None):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(section_label(title))
        row.addStretch()
        if right is not None:
            row.addWidget(right)
        lay.addLayout(row)
        return row

    def _scroll_page(self):
        scroll = QScrollArea()
        scroll.setObjectName("contentScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        page = QWidget()
        page.setObjectName("scrollPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 8, 6)
        lay.setSpacing(16)
        scroll.setWidget(page)
        return scroll, lay

    def _mono_field(self, text):
        field = QLineEdit(text)
        field.setReadOnly(True)
        field.setFont(font(11.5, QFont.Normal, FONT_MONO))
        return field

    def _log_console(self, height=180):
        box = QTextEdit()
        box.setObjectName("console")
        box.setReadOnly(True)
        if height is None:
            box.setMinimumHeight(140)
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            box.setFixedHeight(height)
        box.setFont(font(11.5, QFont.Normal, FONT_MONO))
        return box

    # ------------------------------------------------------------------ page 0
    def create_start_page(self):
        page, lay = self._scroll_page()

        hero, hero_lay = self._card(accent=True, margins=(22, 20, 22, 20), spacing=12)
        head = QHBoxLayout()
        head.setSpacing(10)
        eyebrow = label("AUTOMATED SETUP", "eyebrow", 9.5, QFont.DemiBold, spacing=1.2)
        head.addWidget(eyebrow)
        head.addStretch()
        head.addWidget(label(f"github.com/cheaper-inference/OmniRoute", "chip", 10.5))
        hero_lay.addLayout(head)

        title = label("A local AI gateway, ready in one click.", "heroTitle", 20, QFont.Bold, spacing=-0.3)
        hero_lay.addWidget(title)
        desc = label(
            "OmniHub fetches the latest OmniRoute release, prepares the Node runtime, installs "
            "dependencies and brings the gateway up on port 20128 — then keeps it healthy.",
            "heroDesc", 12, wrap=True,
        )
        hero_lay.addWidget(desc)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        for text in ("Node 18+", "Port 20128", "389 providers", "Auto-fallback"):
            meta.addWidget(label(text, "chip", 10.5))
        meta.addStretch()
        hero_lay.addLayout(meta)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        self.btn_run_install = make_button("Install / Update", "download", "primary", 38,
                                           self.start_installation)
        self.btn_fast_start = make_button("Start service", "play", "success", 38,
                                          lambda: self.run_gateway_action("start"))
        btn_gateway = make_button("Open gateway", "gauge", "secondary", 38,
                                  lambda: self.switch_page(1))
        actions.addWidget(self.btn_run_install)
        actions.addWidget(self.btn_fast_start)
        actions.addWidget(btn_gateway)
        actions.addStretch()
        hero_lay.addLayout(actions)
        lay.addWidget(hero)

        pipeline, pipe_lay = self._card()
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        progress_row.addWidget(section_label("INSTALLATION PIPELINE"))
        progress_row.addStretch()
        self.lbl_install_pct = label("0%", "monoAccent", 11, QFont.DemiBold, mono=True)
        self.lbl_install_elapsed = label("", "hint", 10.5)
        progress_row.addWidget(self.lbl_install_elapsed)
        progress_row.addWidget(self.lbl_install_pct)
        pipe_lay.addLayout(progress_row)

        self.install_progress = ProgressBar(6)
        self._register(self.install_progress)
        pipe_lay.addWidget(self.install_progress)

        self.step_widgets = []
        definitions = [
            ("Pre-flight checks", "Verify Node.js, npm, Git and cache permissions"),
            ("Fetch source", "Clone or pull the latest OmniRoute release"),
            ("Install dependencies", "Resolve npm packages and native bindings"),
            ("Configure environment", "Create .env, link the CLI and launcher"),
            ("Launch and verify", "Start the daemon and confirm /api/monitoring/health"),
        ]
        for index, (title_text, subtitle) in enumerate(definitions, start=1):
            row = self._register(StepRow(index, title_text, subtitle))
            pipe_lay.addWidget(row)
            self.step_widgets.append(row)
        lay.addWidget(pipeline)

        console_card, console_lay = self._card(margins=(16, 14, 16, 14), spacing=8)
        clear_btn = IconButton("trash", "Clear output", 26, 13)
        clear_btn.clicked.connect(lambda: self.txt_install_log.clear())
        self._register(clear_btn)
        self._card_head(console_lay, "ACTIVITY LOG", clear_btn)
        self.txt_install_log = self._log_console(170)
        self.txt_install_log.setText("Idle — run the installer to begin.")
        console_lay.addWidget(self.txt_install_log)
        lay.addWidget(console_card)
        lay.addStretch()
        return page

    # --------------------------------------------------------------- installer
    def start_installation(self):
        self.btn_run_install.setEnabled(False)
        self.btn_run_install.setText("Installing…")
        self.install_progress.setValue(4)
        self.lbl_install_pct.setText("4%")
        self.txt_install_log.clear()
        for row in self.step_widgets:
            row.set_state("pending", "Pending", self.tokens["faint"])

        self._install_started_at = time.time()
        self._install_timer.start(1000)
        self.log_install_msg("Starting automated OmniRoute installation", "accent")

        self.installer_worker = OmniRouteInstallerWorker(OMNIROUTE_DIR)
        self.installer_worker.log_line.connect(self.log_install_msg)
        self.installer_worker.step_updated.connect(self.on_installer_step)
        self.installer_worker.progress_val.connect(self._set_install_progress)
        self.installer_worker.finished.connect(self.on_install_finished)
        self.installer_worker.start()
        self.show_toast("Installation started", "info")

    def _tick_install_clock(self):
        if hasattr(self, "_install_started_at"):
            elapsed = int(time.time() - self._install_started_at)
            self.lbl_install_elapsed.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def _set_install_progress(self, value):
        self.install_progress.setValue(value)
        self.lbl_install_pct.setText(f"{value}%")

    def log_install_msg(self, message, kind="info"):
        if not hasattr(self, "txt_install_log"):
            return
        stamp = time.strftime("%H:%M:%S")
        color = {"info": "#A9B7C9", "ok": "#8FE3CB", "warn": "#FBBF24",
                 "error": "#FB7185", "accent": "#A5B0FF"}.get(kind, "#A9B7C9")
        self.txt_install_log.append(
            f'<span style="color:#4B5568">{stamp}</span> '
            f'<span style="color:{color}">{html.escape(str(message))}</span>'
        )
        bar = self.txt_install_log.verticalScrollBar()
        bar.setValue(bar.maximum())

    def on_installer_step(self, step_index, status_text, color):
        if 0 <= step_index < len(self.step_widgets):
            row = self.step_widgets[step_index]
            if "#10B981" in color or "#4ADE80" in color:
                row.set_state("done", status_text, self.tokens["success"])
            elif "#EF4444" in color or "#FB7185" in color:
                row.set_state("error", status_text, self.tokens["danger"])
            else:
                row.set_state("running", status_text, self.tokens["accent"])

    def on_install_finished(self, success, message):
        self._install_timer.stop()
        self.btn_run_install.setEnabled(True)
        self.btn_run_install.setText("Install / Update")
        if success:
            self._set_install_progress(100)
            self.show_toast("OmniRoute is ready", "ok")
            QMessageBox.information(self, "Installation complete", message)
            self.check_omniroute_health()
        else:
            self.show_toast(message, "error")
            QMessageBox.warning(self, "Installation", message)

    # ------------------------------------------------------------------ page 1
    def create_gateway_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self.kpi_status = self._register(MetricCard(
            "Engine status", "Offline", get_gateway_host_display(), None,
            self.tokens["danger"], dot=True))
        self.kpi_providers = self._register(MetricCard(
            "Provider matrix", "389", "auto-fallback routing", "layers", self.tokens["accent"]))
        self.kpi_speed = self._register(MetricCard(
            "Edge latency", "—", "local intercept", "bolt", self.tokens["success"]))
        self.latency_spark = self.kpi_speed.add_sparkline()
        kpi_row.addWidget(self.kpi_status)
        kpi_row.addWidget(self.kpi_providers)
        kpi_row.addWidget(self.kpi_speed)
        lay.addLayout(kpi_row)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        service_card, service_lay = self._card()
        self._card_head(service_lay, "SERVICE CONTROL")
        hint = label("Control the background OmniRoute daemon.", "hint", 11, wrap=True)
        service_lay.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.btn_gw_start = make_button("Start", "play", "success", 34,
                                        lambda: self.run_gateway_action("start"))
        self.btn_gw_restart = make_button("Restart", "restart", "secondary", 34,
                                          lambda: self.run_gateway_action("restart"))
        self.btn_gw_stop = make_button("Stop", "stop", "danger", 34,
                                       lambda: self.run_gateway_action("stop"))
        buttons.addWidget(self.btn_gw_start)
        buttons.addWidget(self.btn_gw_restart)
        buttons.addWidget(self.btn_gw_stop)
        buttons.addStretch()
        service_lay.addLayout(buttons)
        service_lay.addSpacing(2)
        service_lay.addWidget(hline())
        service_lay.addSpacing(2)

        doctor = make_button("Run doctor diagnostics", "shield", "ghost", 30,
                             self.run_doctor_check)
        service_lay.addWidget(doctor, 0, Qt.AlignLeft)
        service_lay.addStretch()
        mid_row.addWidget(service_card, 4)

        cred_card, cred_lay = self._card()
        copy_btn = IconButton("copy", "Copy endpoint", 26, 14)
        copy_btn.clicked.connect(self.copy_api_url)
        self._register(copy_btn)
        self._card_head(cred_lay, "CONNECTION & ENDPOINTS", copy_btn)

        cred_lay.addWidget(label("GATEWAY BASE URL / HOST", "keyLabel", 9.5, QFont.DemiBold, spacing=0.8))
        gw_url_row = QHBoxLayout()
        gw_url_row.setSpacing(6)
        self.txt_gateway_url = QLineEdit(OMNIROUTE_BASE)
        self.txt_gateway_url.setPlaceholderText("http://localhost:20128")
        self.txt_gateway_url.setFont(font(11, QFont.Normal, FONT_MONO))
        self.txt_gateway_url.returnPressed.connect(self.on_save_gateway_url)
        gw_url_row.addWidget(self.txt_gateway_url, 1)

        self.btn_apply_url = make_button("Save", "check", "secondary", 28, self.on_save_gateway_url)
        self.btn_reset_url = make_button("Default", "restart", "ghost", 28, self.on_reset_gateway_url)
        gw_url_row.addWidget(self.btn_apply_url)
        gw_url_row.addWidget(self.btn_reset_url)
        cred_lay.addLayout(gw_url_row)

        cred_lay.addSpacing(4)
        cred_lay.addWidget(label("OPENAI-COMPATIBLE API (LOCAL INFERENCE)", "keyLabel", 9.5, QFont.DemiBold, spacing=0.8))

        endpoint_row = QHBoxLayout()
        endpoint_row.setSpacing(6)
        self.txt_api_base = self._mono_field(f"{OMNIROUTE_BASE}/v1")
        endpoint_row.addWidget(self.txt_api_base, 1)
        endpoint_row.addWidget(make_button("Copy", None, "secondary", 28, self.copy_api_url))
        endpoint_row.addWidget(make_button("Dashboard", "globe", "secondary", 28, self.open_dashboard))
        cred_lay.addLayout(endpoint_row)

        auth_row = QHBoxLayout()
        auth_row.setSpacing(8)
        auth_row.addWidget(label("AUTH", "keyLabel", 10, QFont.DemiBold, spacing=0.8))
        auth_row.addWidget(label("Bearer local", "mono", 11, mono=True))
        auth_row.addSpacing(10)
        auth_row.addWidget(label("MANAGEMENT", "keyLabel", 10, QFont.DemiBold, spacing=0.8))
        auth_row.addWidget(label("CHANGEME", "mono", 11, mono=True))
        auth_row.addStretch()
        cred_lay.addLayout(auth_row)
        cred_lay.addWidget(label("Supports localhost:20128, 127.0.0.1, custom ports, or remote gateways.", "hint", 10))
        cred_lay.addStretch()
        mid_row.addWidget(cred_card, 5)
        lay.addLayout(mid_row)

        console_card, console_lay = self._card(margins=(16, 14, 16, 14), spacing=8)
        clear_btn = IconButton("trash", "Clear console", 26, 13)
        clear_btn.clicked.connect(lambda: self.txt_console.clear())
        self._register(clear_btn)
        self._card_head(console_lay, "SYSTEM CONSOLE", clear_btn)
        self.txt_console = self._log_console(None)
        console_lay.addWidget(self.txt_console)
        lay.addWidget(console_card, 1)
        self.log_msg("Console ready.", "ok")
        return page

    # ------------------------------------------------------------------ page 2
    def create_ai_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        config, config_lay = self._card(margins=(14, 10, 14, 10), spacing=10)
        row = QHBoxLayout()
        row.setSpacing(9)
        row.addWidget(label("MODEL", "keyLabel", 10, QFont.DemiBold, spacing=0.8))
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setInsertPolicy(QComboBox.NoInsert)
        self.cb_model.addItems(["auto", "gpt-4o", "claude-3-5-sonnet", "gemini-1.5-flash",
                                "deepseek-coder", "llama-3.3-70b"])
        self.cb_model.setFixedWidth(190)
        row.addWidget(self.cb_model)
        row.addSpacing(6)
        row.addWidget(label("SYSTEM", "keyLabel", 10, QFont.DemiBold, spacing=0.8))
        self.txt_ai_sys = QLineEdit()
        self.txt_ai_sys.setPlaceholderText("Optional system role — e.g. senior Python engineer")
        row.addWidget(self.txt_ai_sys, 1)
        self.lbl_ai_status = label("Ready", "hint", 11)
        row.addWidget(self.lbl_ai_status)
        config_lay.addLayout(row)
        lay.addWidget(config)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatArea")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_cast = QWidget()
        self.chat_cast.setObjectName("chatBody")
        self.chat_layout = QVBoxLayout(self.chat_cast)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_cast)
        lay.addWidget(self.chat_scroll, 1)

        self.add_chat_bubble(
            "OmniRoute",
            "Connected to the local gateway. Ask anything — requests route through the "
            "auto-fallback matrix across configured providers.",
            is_user=False,
        )

        composer, composer_lay = self._card(margins=(14, 12, 14, 12), spacing=9)
        chips_row = QHBoxLayout()
        chips_row.setSpacing(7)
        for chip_text, prompt in (
            ("Ping", "Respond with 'PONG' and report your configured model identity."),
            ("QuickSort", "Write an optimized Python implementation of QuickSort with comments and time complexity."),
            ("Explain routing", "Briefly explain how OmniRoute routes AI requests with automatic fallback across providers."),
        ):
            chip = QPushButton(chip_text)
            chip.setObjectName("chipBtn")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _, p=prompt: self.apply_chip(p))
            chips_row.addWidget(chip)
        chips_row.addStretch()
        chips_row.addWidget(label("Enter to send · Shift+Enter for newline", "hint", 10.5))
        composer_lay.addLayout(chips_row)

        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(10)
        self.txt_ai_prompt = QTextEdit()
        self.txt_ai_prompt.setObjectName("composer")
        self.txt_ai_prompt.setPlaceholderText("Ask the gateway…")
        self.txt_ai_prompt.setFixedHeight(64)
        self.txt_ai_prompt.installEventFilter(self)
        prompt_row.addWidget(self.txt_ai_prompt, 1)
        self.btn_ai_send = make_button("Send", "send", "primary", 64, self.send_ai_prompt)
        self.btn_ai_send.setFixedWidth(104)
        prompt_row.addWidget(self.btn_ai_send)
        composer_lay.addLayout(prompt_row)
        lay.addWidget(composer)
        return page

    def apply_chip(self, prompt):
        self.txt_ai_prompt.setPlainText(prompt)
        self.txt_ai_prompt.setFocus()

    def _scroll_chat_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def add_chat_bubble(self, sender, text, is_user=False):
        bubble = ChatBubble(sender, text, is_user=is_user, tokens=self.tokens)
        align = (Qt.AlignRight if is_user else Qt.AlignLeft) | Qt.AlignTop
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble, 0, align)
        grow_in(bubble)
        QTimer.singleShot(240, self._scroll_chat_bottom)
        return bubble

    def _show_typing(self):
        frame = QFrame()
        frame.setObjectName("bubbleBot")
        frame.setMaximumWidth(200)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 9, 14, 10)
        lay.setSpacing(3)
        lay.addWidget(label("OmniRoute", "bubbleSender", 10, QFont.DemiBold))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._typing_dots = self._register(TypingDots())
        row.addWidget(self._typing_dots)
        row.addWidget(label("thinking", "hint", 10.5))
        row.addStretch()
        lay.addLayout(row)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, frame, 0,
                                      Qt.AlignLeft | Qt.AlignTop)
        grow_in(frame, 160)
        self._typing = frame
        QTimer.singleShot(200, self._scroll_chat_bottom)

    def _clear_typing(self):
        frame = getattr(self, "_typing", None)
        if frame is not None:
            self.chat_layout.removeWidget(frame)
            frame.deleteLater()
            self._typing = None

    def send_ai_prompt(self):
        if getattr(self, "_ai_pending", False):
            return
        prompt = self.txt_ai_prompt.toPlainText().strip()
        if not prompt:
            return
        model = self.cb_model.currentText().strip() or "auto"
        system_prompt = self.txt_ai_sys.text().strip()

        self.add_chat_bubble("You", prompt, is_user=True)
        self.txt_ai_prompt.clear()

        self._ai_pending = True
        self.btn_ai_send.setEnabled(False)
        self.btn_ai_send.setText("Sending…")
        self.lbl_ai_status.setText(f"routing · {model}")
        self._show_typing()

        self.ai_worker = AIChatWorker(model, prompt, system_prompt)
        self.ai_worker.finished.connect(self.on_ai_finish)
        self.ai_worker.start()

    def on_ai_finish(self, success, response, elapsed):
        self._ai_pending = False
        self._clear_typing()
        self.btn_ai_send.setEnabled(True)
        self.btn_ai_send.setText("Send")
        if success:
            words = len(response.split())
            self.lbl_ai_status.setText(f"{elapsed:.2f}s · {words} words")
            self.add_chat_bubble(f"OmniRoute · {self.cb_model.currentText()}",
                                 response, is_user=False)
        else:
            self.lbl_ai_status.setText(f"failed · {elapsed:.2f}s")
            self.add_chat_bubble("Request failed", response, is_user=False)
            self.show_toast("Model request failed", "error")
            self.log_msg(f"AI request failed: {response}", "error")

    def eventFilter(self, obj, event):
        if obj is getattr(self, "txt_ai_prompt", None) and event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self.send_ai_prompt()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------ page 3
    def create_system_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        res_card, res_lay = self._card(margins=(20, 18, 20, 18), spacing=14)
        self._card_head(res_lay, "RESOURCE UTILIZATION")
        res_lay.addSpacing(2)

        self.bar_cpu, self.lbl_cpu_val = self._gauge_row(res_lay, "CPU load")
        self.bar_ram, self.lbl_ram_val = self._gauge_row(res_lay, "Memory")
        self.bar_disk, self.lbl_disk_val = self._gauge_row(res_lay, "Root storage")
        lay.addWidget(res_card)

        env_card, env_lay = self._card(margins=(20, 18, 20, 18), spacing=12)
        self._card_head(env_lay, "ENVIRONMENT")
        grid = QGridLayout()
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(10)
        self.env_labels = {}
        rows = [
            ("os", "Operating system"), ("desktop", "Desktop"),
            ("uptime", "Uptime"), ("python", "Python runtime"),
            ("engine", "OmniRoute engine"), ("cpu", "Processor"),
            ("memory", "Installed memory"), ("storage", "Storage"),
        ]
        for index, (key, title_text) in enumerate(rows):
            grid.addWidget(label(title_text, "keyLabel", 11), index // 2, (index % 2) * 2)
            value = label("—", "valLabel", 12)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(value, index // 2, (index % 2) * 2 + 1)
            self.env_labels[key] = value
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        env_lay.addLayout(grid)
        lay.addWidget(env_card)
        lay.addStretch()
        return page

    def _gauge_row(self, parent_lay, title_text):
        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(label(title_text, None, 12, QFont.Medium))
        head.addStretch()
        value = label("—", "accentValue", 12, QFont.DemiBold)
        head.addWidget(value)
        parent_lay.addLayout(head)
        bar = self._register(ProgressBar(6))
        parent_lay.addWidget(bar)
        return bar, value

    # ------------------------------------------------------------------ page 4
    def create_tools_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        bar, bar_lay = self._card(margins=(14, 10, 14, 10), spacing=10)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(section_label("SCRATCHPAD"))
        row.addSpacing(6)
        for text, slot in (
            ("Format JSON", self.format_json),
            ("Base64 encode", self.b64_encode),
            ("Base64 decode", self.b64_decode),
            ("Count tokens", self.count_tokens),
        ):
            row.addWidget(make_button(text, None, "secondary", 30, slot))
        row.addStretch()
        clear_btn = IconButton("trash", "Clear scratchpad", 28, 14)
        clear_btn.clicked.connect(self.clear_notes)
        self._register(clear_btn)
        row.addWidget(clear_btn)
        bar_lay.addLayout(row)
        lay.addWidget(bar)

        self.txt_notes = QTextEdit()
        self.txt_notes.setObjectName("editor")
        self.txt_notes.setPlaceholderText(
            "Paste prompts, JSON payloads, API keys or temporary notes — saved automatically.")
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as handle:
                    self.txt_notes.setText(handle.read())
            except Exception:
                pass
        self._notes_timer = QTimer(self)
        self._notes_timer.setSingleShot(True)
        self._notes_timer.timeout.connect(self.save_notes)
        self.txt_notes.textChanged.connect(lambda: self._notes_timer.start(400))
        lay.addWidget(self.txt_notes, 1)

        quick, quick_lay = self._card(margins=(14, 10, 14, 10), spacing=10)
        qrow = QHBoxLayout()
        qrow.setSpacing(8)
        qrow.addWidget(section_label("QUICK LAUNCH"))
        qrow.addSpacing(6)
        for text, icon_name, slot in (
            ("Terminal", "terminal", self.open_terminal),
            ("Files", "folder", self.open_file_manager),
            ("Browser", "globe", self.open_browser),
            ("Dashboard", "external", self.open_dashboard),
        ):
            qrow.addWidget(make_button(text, icon_name, "secondary", 30, slot))
        qrow.addStretch()
        quick_lay.addLayout(qrow)
        lay.addWidget(quick)
        return page

    # ------------------------------------------------------------------ page 5
    def create_about_page(self):
        page, lay = self._scroll_page()

        hero, hero_lay = self._card(accent=True, margins=(22, 20, 22, 20), spacing=10)
        head = QHBoxLayout()
        head.setSpacing(14)
        self.about_logo = LogoMark(54, self.active_theme == "dark")
        head.addWidget(self.about_logo)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(label("OmniHub", "heroTitle", 20, QFont.Bold, spacing=-0.3))
        title_box.addWidget(label(f"v{APP_VERSION} · {APP_TAGLINE}", "devRole", 11, QFont.Medium))
        head.addLayout(title_box)
        head.addStretch()
        head.addWidget(label("GPL-3.0 · OPEN SOURCE", "chipAccent", 10))
        hero_lay.addLayout(head)
        hero_lay.addWidget(label(
            "A precision desktop control surface for OmniRoute: one-click setup, multi-provider "
            "model routing, live host telemetry and developer utilities — built for Linux, "
            "Windows and macOS.",
            "heroDesc", 12, wrap=True))
        lay.addWidget(hero)

        row = QHBoxLayout()
        row.setSpacing(14)

        dev, dev_lay = self._card(margins=(20, 17, 20, 17), spacing=10)
        self._card_head(dev_lay, "DEVELOPER")
        profile = QHBoxLayout()
        profile.setSpacing(12)
        avatar = QLabel("SH")
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFont(font(15, QFont.Bold))
        avatar.setObjectName("avatar")
        profile.addWidget(avatar)
        info = QVBoxLayout()
        info.setSpacing(1)
        info.addWidget(label(DEV_NAME, "devName", 16, QFont.DemiBold))
        info.addWidget(label(f"{DEV_ORG} · creator & Linux developer", "hint", 11))
        profile.addLayout(info)
        profile.addStretch()
        dev_lay.addLayout(profile)
        dev_lay.addWidget(hline())
        dev_lay.addWidget(make_button("Facebook", "globe", "secondary", 32,
                                      lambda: QDesktopServices.openUrl(QUrl(DEV_FB))))
        dev_lay.addWidget(make_button("GitHub", "code", "secondary", 32,
                                      lambda: QDesktopServices.openUrl(QUrl(DEV_GITHUB))))
        dev_lay.addStretch()
        row.addWidget(dev, 5)

        support, support_lay = self._card(margins=(20, 17, 20, 17), spacing=10)
        self._card_head(support_lay, "SUPPORT THE PROJECT")
        support_lay.addWidget(label(
            "OmniHub stays free and open source. If it saves you time, you can support "
            "ongoing development and Linux desktop maintenance.",
            "hint", 11.5, wrap=True))
        support_lay.addWidget(make_button("Buy me a coffee", "heart", "primary", 34,
                                          lambda: QDesktopServices.openUrl(QUrl(DEV_KOFI))))
        support_lay.addWidget(make_button("Support via SupportKori", "external", "secondary", 32,
                                          lambda: QDesktopServices.openUrl(QUrl(DONATION_URL))))
        support_lay.addStretch()
        row.addWidget(support, 6)
        lay.addLayout(row)

        credits, credits_lay = self._card()
        self._card_head(credits_lay, "ACKNOWLEDGEMENTS")
        credits_lay.addWidget(label(
            "OmniRoute engine — Diego Souza and the open-source community "
            "(github.com/cheaper-inference/OmniRoute). "
            "Built with Python 3, PyQt5 and Qt 5.15. "
            "Thanks to contributors and supporters in Bangladesh and worldwide.",
            "hint", 11.5, wrap=True))
        lay.addWidget(credits)
        lay.addStretch()
        return page

    # ------------------------------------------------------------------ logic
    def log_msg(self, message, kind="info"):
        if not hasattr(self, "txt_console"):
            return
        stamp = time.strftime("%H:%M:%S")
        color = {"info": "#A9B7C9", "ok": "#8FE3CB", "warn": "#FBBF24",
                 "error": "#FB7185", "accent": "#A5B0FF"}.get(kind, "#A9B7C9")
        self.txt_console.append(
            f'<span style="color:#4B5568">{stamp}</span> '
            f'<span style="color:{color}">{html.escape(str(message))}</span>'
        )
        bar = self.txt_console.verticalScrollBar()
        bar.setValue(bar.maximum())

    def check_omniroute_health(self):
        if not self.health_worker.isRunning():
            self.health_worker.start()

    def on_save_gateway_url(self):
        raw = self.txt_gateway_url.text().strip() if hasattr(self, "txt_gateway_url") else ""
        if not raw:
            raw = DEFAULT_OMNIROUTE_BASE
        new_url = set_gateway_base(raw, persist=True)
        if hasattr(self, "txt_gateway_url"):
            self.txt_gateway_url.setText(new_url)
        if hasattr(self, "txt_api_base"):
            self.txt_api_base.setText(f"{new_url}/v1")
        host_disp = get_gateway_host_display()
        if hasattr(self, "kpi_status"):
            self.kpi_status.sub_label.setText(host_disp)
        if hasattr(self, "lbl_sb_info"):
            self.lbl_sb_info.setText(host_disp)
        self.log_msg(f"Gateway URL configured: {new_url}", "ok")
        self.show_toast(f"Gateway URL: {new_url}", "ok")
        self.check_omniroute_health()

    def on_reset_gateway_url(self):
        new_url = set_gateway_base(DEFAULT_OMNIROUTE_BASE, persist=True)
        if hasattr(self, "txt_gateway_url"):
            self.txt_gateway_url.setText(new_url)
        if hasattr(self, "txt_api_base"):
            self.txt_api_base.setText(f"{new_url}/v1")
        host_disp = get_gateway_host_display()
        if hasattr(self, "kpi_status"):
            self.kpi_status.sub_label.setText(host_disp)
        if hasattr(self, "lbl_sb_info"):
            self.lbl_sb_info.setText(host_disp)
        self.log_msg(f"Gateway URL reset to default: {new_url}", "info")
        self.show_toast("Gateway URL reset to default", "info")
        self.check_omniroute_health()

    def on_health_result(self, is_ok, latency):
        try:
            host_disp = get_gateway_host_display()
            if is_ok:
                self.kpi_status.value_label.setText("Online")
                self.kpi_status.sub_label.setText(host_disp)
                restyle(self.kpi_status.sub_label, "kpiSubOk")
                if self.kpi_status.dot:
                    self.kpi_status.dot.set_state("on")
                animate_number(self.kpi_speed.value_label, latency, " ms")
                self.latency_spark.push(latency)
                self._render_latency_chip(latency, True)
                self.sb_dot.set_state("on")
                self.lbl_sb_status.setText("Online")
                self.lbl_sb_info.setText(f"{host_disp} · {latency} ms")
            else:
                self.kpi_status.value_label.setText("Offline")
                self.kpi_status.sub_label.setText(f"{host_disp} (offline)")
                restyle(self.kpi_status.sub_label, "kpiSubErr")
                if self.kpi_status.dot:
                    self.kpi_status.dot.set_state("off")
                self.kpi_speed.value_label.setText("—")
                self._render_latency_chip(0, False)
                self.sb_dot.set_state("off")
                self.lbl_sb_status.setText("Offline")
                self.lbl_sb_info.setText(host_disp)
        except Exception:
            pass

    def update_system_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            cores = psutil.cpu_count(logical=True) or 0
            self.bar_cpu.setValue(cpu)
            self.lbl_cpu_val.setText(f"{cpu:.0f}% · {cores} threads")

            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            self.bar_ram.setValue(mem.percent)
            self.lbl_ram_val.setText(f"{used_gb:.1f} / {total_gb:.1f} GB")

            mount = "/" if platform.system() != "Windows" else os.path.abspath(os.sep)
            disk = psutil.disk_usage(mount)
            self.bar_disk.setValue(disk.percent)
            self.lbl_disk_val.setText(f"{disk.used / (1024 ** 3):.0f} / {disk.total / (1024 ** 3):.0f} GB")

            uptime = int(time.time() - psutil.boot_time())
            days, rem = divmod(uptime, 86400)
            hours, rem = divmod(rem, 3600)
            minutes = rem // 60
            uptime_text = (f"{days}d " if days else "") + f"{hours}h {minutes}m"

            sys_os = f"{platform.system()} {platform.release()}"
            if platform.system() == "Linux":
                try:
                    with open("/etc/os-release") as handle:
                        for line in handle:
                            if line.startswith("PRETTY_NAME="):
                                sys_os = line.split("=", 1)[1].strip().strip('"')
                                break
                except Exception:
                    pass
            desktop = os.environ.get("XDG_CURRENT_DESKTOP") or "Linux desktop"
            if platform.system() == "Windows":
                desktop = "Windows shell"
            elif platform.system() == "Darwin":
                desktop = "Aqua"

            self.env_labels["os"].setText(sys_os)
            self.env_labels["desktop"].setText(desktop)
            self.env_labels["uptime"].setText(uptime_text)
            self.env_labels["python"].setText(f"{platform.python_version()} · {platform.machine()}")
            self.env_labels["engine"].setText(os.path.basename(OMNIROUTE_DIR.rstrip("/")) or OMNIROUTE_DIR)
            self.env_labels["cpu"].setText(f"{cores} logical cores")
            self.env_labels["memory"].setText(f"{total_gb:.1f} GB")
            self.env_labels["storage"].setText(f"{disk.total / (1024 ** 3):.0f} GB · {disk.percent:.0f}% used")
        except Exception:
            pass

    def run_gateway_action(self, action):
        self.log_msg(f"Service action: {action}", "accent")
        if action == "stop":
            self.on_health_result(False, 0)
            if hasattr(self, "btn_gw_stop"):
                self.btn_gw_stop.setEnabled(False)
        elif action in ("start", "restart"):
            if hasattr(self, "btn_gw_start"):
                self.btn_gw_start.setEnabled(False)
            if hasattr(self, "btn_gw_restart"):
                self.btn_gw_restart.setEnabled(False)

        self.gw_worker = OmniRouteWorker(action)
        self.gw_worker.finished.connect(self._on_gateway_action_done)
        self.gw_worker.start()
        delay = 800 if action == "stop" else 2600
        QTimer.singleShot(delay, self.check_omniroute_health)

    def _on_gateway_action_done(self, ok, message):
        if hasattr(self, "btn_gw_start"):
            self.btn_gw_start.setEnabled(True)
        if hasattr(self, "btn_gw_restart"):
            self.btn_gw_restart.setEnabled(True)
        if hasattr(self, "btn_gw_stop"):
            self.btn_gw_stop.setEnabled(True)
        self.log_msg(message, "ok" if ok else "error")
        self.show_toast(message, "ok" if ok else "error")
        self.check_omniroute_health()

    def run_doctor_check(self):
        if self.doctor_worker.isRunning():
            return
        self.log_msg("Running omniRoute doctor…", "accent")
        self.doctor_worker.start()

    def open_dashboard(self):
        QDesktopServices.openUrl(QUrl(OMNIROUTE_DASHBOARD))
        self.log_msg(f"Opened {OMNIROUTE_DASHBOARD}", "ok")
        self.show_toast("Opening web dashboard", "info")

    def open_terminal(self):
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe"])
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
        else:
            for term in ("deepin-terminal", "gnome-terminal", "konsole",
                         "xfce4-terminal", "alacritty", "xterm"):
                if shutil.which(term):
                    subprocess.Popen([term])
                    return
            subprocess.Popen(["x-terminal-emulator"])

    def open_browser(self):
        webbrowser.open("https://google.com")

    def open_file_manager(self):
        system = platform.system()
        target = os.path.expanduser("~")
        if system == "Windows":
            subprocess.Popen(["explorer.exe", target])
        elif system == "Darwin":
            subprocess.Popen(["open", target])
        else:
            for fm in ("dde-file-manager", "nautilus", "dolphin", "thunar", "nemo"):
                if shutil.which(fm):
                    subprocess.Popen([fm, target])
                    return
            subprocess.Popen(["xdg-open", target])

    def copy_api_url(self):
        QApplication.clipboard().setText(f"{OMNIROUTE_BASE}/v1")
        self.log_msg("Endpoint copied to clipboard", "ok")
        self.show_toast("Endpoint copied", "ok")

    # ---- scratchpad -------------------------------------------------------
    def save_notes(self):
        if not hasattr(self, "txt_notes"):
            return
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as handle:
                handle.write(self.txt_notes.toPlainText())
        except Exception:
            pass

    def clear_notes(self):
        if QMessageBox.question(self, "Clear scratchpad", "Delete all scratchpad contents?") == QMessageBox.Yes:
            self.txt_notes.clear()
            self.save_notes()
            self.show_toast("Scratchpad cleared", "info")

    def format_json(self):
        raw = self.txt_notes.toPlainText().strip()
        try:
            data = json.loads(raw)
            self.txt_notes.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            self.show_toast("JSON formatted", "ok")
        except Exception as exc:
            self.show_toast(f"Invalid JSON: {exc}", "error")

    def b64_encode(self):
        raw = self.txt_notes.toPlainText()
        self.txt_notes.setPlainText(base64.b64encode(raw.encode("utf-8")).decode("utf-8"))
        self.show_toast("Base64 encoded", "ok")

    def b64_decode(self):
        raw = self.txt_notes.toPlainText().strip()
        try:
            self.txt_notes.setPlainText(base64.b64decode(raw.encode("utf-8")).decode("utf-8"))
            self.show_toast("Base64 decoded", "ok")
        except Exception as exc:
            self.show_toast(f"Decode failed: {exc}", "error")

    def count_tokens(self):
        raw = self.txt_notes.toPlainText()
        chars = len(raw)
        words = len(raw.split())
        tokens = int(chars / 4)
        self.show_toast(f"{chars:,} chars · {words:,} words · ~{tokens:,} tokens", "info")
        self.log_msg(f"Token estimate: {chars:,} chars, {words:,} words, ~{tokens:,} tokens", "ok")

    # ---- tray -------------------------------------------------------------
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = get_app_icon_path()
        icon = QtGui.QIcon(icon_path) if icon_path and os.path.exists(icon_path) else self.windowIcon()
        if icon.isNull():
            return
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip(f"{APP_NAME} — {APP_TAGLINE}")
        menu = QMenu(self)
        actions = [
            ("Open OmniHub", self.showNormal),
            ("Open dashboard", self.open_dashboard),
            ("Restart gateway", lambda: self.run_gateway_action("restart")),
        ]
        for text, slot in actions:
            action = QAction(text, self)
            action.triggered.connect(slot)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.showNormal() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()


# =============================================================================
#  Entry point
# =============================================================================

def _cli_restart():
    stop_omniroute_processes()
    script = os.path.join(OMNIROUTE_DIR, "start-omniroute.sh")
    env = os.environ.copy()
    port = get_gateway_port()
    if port:
        env["PORT"] = str(port)
    if platform.system() == "Windows":
        subprocess.Popen(["cmd.exe", "/c", "start", "npm run dev"], cwd=OMNIROUTE_DIR, env=env)
    elif os.path.exists(script):
        subprocess.Popen([script], cwd=OMNIROUTE_DIR, env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    else:
        print(f"Launcher not found: {script}")
        return 1
    print("OmniRoute restart signal sent.")
    return 0


def main():
    argv = sys.argv[1:]

    if "--version" in argv or "-v" in argv:
        print(f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(f"""{APP_NAME} {APP_VERSION} — {APP_TAGLINE}

Usage:
  omnihub [options]

Options:
  -h, --help        Show this help and exit
  -v, --version     Show version and exit
  --page <name>     Open a page: setup, gateway, ai, system, tools, about
  --restart         Restart the OmniRoute background service and exit
""")
        return 0
    if "--restart" in argv:
        return _cli_restart()

    page_index = 0
    if "--page" in argv:
        try:
            page_index = PAGE_KEYS.get(argv[argv.index("--page") + 1].lower(), 0)
        except (IndexError, ValueError):
            page_index = 0

    if platform.system() == "Linux" and "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "xcb"

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("omnihub")
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName("omnihub.desktop")

    init_fonts()
    app.setFont(font(13))

    window = MainWindow()
    window.switch_page(page_index, animate=False)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
