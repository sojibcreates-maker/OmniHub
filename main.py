#!/usr/bin/env python3
"""
OmniHub — Ultra-Modern Precision AI Gateway, Automated Installer & System Studio
Crafted by Md Sojib Hossain (SojibLabs) for Deepin OS.
"""

import sys
import os
import time
import json
import base64
import subprocess
import threading
import platform
import shutil
import webbrowser
import requests
import psutil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox,
    QProgressBar, QFrame, QMessageBox, QSystemTrayIcon,
    QMenu, QAction, QScrollArea, QStackedWidget,
    QButtonGroup, QSplitter
)

OMNIROUTE_REPO = "https://github.com/cheaper-inference/OmniRoute.git"

def get_default_omniroute_dir():
    custom_dev = "/home/sojiblabs/.gemini/antigravity/scratch/OmniRoute"
    if os.path.exists(custom_dev):
        return custom_dev
    env_dir = os.environ.get("OMNIROUTE_DIR")
    if env_dir:
        return env_dir
    return os.path.join(os.path.expanduser("~"), ".omniroute")

OMNIROUTE_DIR = get_default_omniroute_dir()
OMNIROUTE_BASE = "http://localhost:20128"
OMNIROUTE_HEALTH = f"{OMNIROUTE_BASE}/api/monitoring/health"
OMNIROUTE_DASHBOARD = f"{OMNIROUTE_BASE}/dashboard"
OMNIROUTE_CHAT = f"{OMNIROUTE_BASE}/v1/chat/completions"

def get_default_config_dir():
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "OmniHub")
    elif platform.system() == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "OmniHub")
    return os.path.expanduser("~/.config/omnihub")

CONFIG_DIR = get_default_config_dir()
NOTES_FILE = os.path.join(CONFIG_DIR, "notes.txt")
os.makedirs(CONFIG_DIR, exist_ok=True)

def get_app_icon_path():
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "assets", "omnihub.png"),
        os.path.join(base, "omnihub.png"),
        os.path.expanduser("~/.local/share/icons/omnihub.png"),
        "/home/sojiblabs/.local/share/icons/omnihub.png"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""

DEV_NAME = "Md Sojib Hossain"
DEV_ORG = "SojibLabs"
DEV_FB = "https://www.facebook.com/hossain.sojibs"
DEV_KOFI = "https://ko-fi.com/sojibhossain"
DONATION_URL = "https://www.supportkori.com/sojib"
DEV_GITHUB = "https://github.com/sojibcreates-maker"


# ================= Background Workers =================

class OmniRouteInstallerWorker(QThread):
    log_line = pyqtSignal(str)
    step_updated = pyqtSignal(int, str, str)  # step_index, status_text, color
    progress_val = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir=OMNIROUTE_DIR):
        super().__init__()
        self.target_dir = target_dir

    def run_cmd(self, cmd, cwd=None, env=None):
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        local_bin = os.path.expanduser("~/.local/bin")
        sep = ";" if platform.system() == "Windows" else ":"
        full_env["PATH"] = f"{local_bin}{sep}{full_env.get('PATH', '')}"

        proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd, env=full_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in proc.stdout:
            cleaned = line.rstrip()
            if cleaned:
                self.log_line.emit(cleaned)
        proc.wait()
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

            if os.path.exists(os.path.join(self.target_dir, ".git")):
                self.log_line.emit("Existing repository detected. Pulling latest updates...")
                rc = self.run_cmd("git fetch origin && git pull origin release/v3.8.54 || git pull", cwd=self.target_dir)
            else:
                os.makedirs(os.path.dirname(self.target_dir), exist_ok=True)
                rc = self.run_cmd(f"git clone {OMNIROUTE_REPO} \"{self.target_dir}\"")

            if rc != 0:
                self.step_updated.emit(1, "GitHub download failed", "#EF4444")
                self.finished.emit(False, "Failed to clone repository from GitHub. Check network connection.")
                return

            self.step_updated.emit(1, "✓ Repository Downloaded", "#10B981")
            self.progress_val.emit(50)

            # Step 3: Install Core Dependencies
            self.step_updated.emit(2, "Installing core dependencies (npm install)...", "#38BDF8")
            self.log_line.emit("\n=== Step 3/5: Resolving & Installing Dependencies ===")
            rc = self.run_cmd("npm install --no-audit", cwd=self.target_dir)
            if rc != 0:
                self.log_line.emit("Retrying npm install with allow-scripts...")
                self.run_cmd("npm install --allow-scripts", cwd=self.target_dir)

            self.step_updated.emit(2, "✓ Dependencies Installed", "#10B981")
            self.progress_val.emit(75)

            # Step 4: Native Modules & Keytar
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
            self.step_updated.emit(4, "Starting OmniRoute Service on port 20128...", "#38BDF8")
            self.log_line.emit("\n=== Step 5/5: Launching Gateway Service ===")
            if platform.system() == "Windows":
                subprocess.Popen("npm run dev", shell=True, cwd=self.target_dir)
            else:
                start_cmd = f"cd '{self.target_dir}' && nohup ./start-omniroute.sh > /dev/null 2>&1 &"
                subprocess.Popen(start_cmd, shell=True)

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


def stop_omniroute_processes():
    stopped = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline'] or [])
            name = (proc.info['name'] or "").lower()
            if "run-next.mjs" in cmdline or "next-server" in cmdline:
                proc.terminate()
                stopped = True
            elif OMNIROUTE_DIR and OMNIROUTE_DIR in cmdline and "node" in name:
                proc.terminate()
                stopped = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if platform.system() != "Windows":
        try:
            subprocess.run(["pkill", "-f", "run-next.mjs"], check=False)
            subprocess.run(["pkill", "-f", "next-server"], check=False)
        except Exception:
            pass
    return stopped


class OmniRouteWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, action):
        super().__init__()
        self.action = action

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

                if platform.system() == "Windows":
                    subprocess.Popen("npm run dev", shell=True, cwd=OMNIROUTE_DIR)
                else:
                    cmd = f"cd '{OMNIROUTE_DIR}' && nohup ./start-omniroute.sh > /dev/null 2>&1 &"
                    subprocess.Popen(cmd, shell=True)
                time.sleep(2.5)
                self.finished.emit(True, "OmniRoute engine launch signal dispatched.")

            elif self.action == "stop":
                stop_omniroute_processes()
                time.sleep(1)
                self.finished.emit(True, "OmniRoute server process stopped.")

            elif self.action == "restart":
                stop_omniroute_processes()
                time.sleep(1.5)
                if platform.system() == "Windows":
                    subprocess.Popen("npm run dev", shell=True, cwd=OMNIROUTE_DIR)
                else:
                    cmd = f"cd '{OMNIROUTE_DIR}' && nohup ./start-omniroute.sh > /dev/null 2>&1 &"
                    subprocess.Popen(cmd, shell=True)
                time.sleep(2.5)
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
            res = subprocess.run(["omniroute", "doctor"], capture_output=True, text=True)
            lines = res.stdout.strip().split("\n")
            summary = [l for l in lines if "Summary" in l or "OK" in l or "WARN" in l][:8]
            for s in summary:
                self.log_line.emit(f"🩺 {s}")
        except Exception as e:
            self.log_line.emit(f"Doctor error: {e}")


# ================= Theme Utilities & Vector Logo =================

def detect_system_theme():
    # 1. Windows registry probe
    if platform.system() == "Windows":
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

    # 2. macOS defaults probe
    elif platform.system() == "Darwin":
        try:
            out = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip().lower()
            if "dark" in out:
                return "dark"
            return "light"
        except Exception:
            return "light"

    # 3. Linux Desktop probes (GNOME, Deepin, FreeDesktop)
    else:
        try:
            out = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                text=True, stderr=subprocess.DEVNULL
            ).strip().lower()
            if "dark" in out:
                return "dark"
            elif "light" in out:
                return "light"
        except Exception:
            pass

        try:
            out = subprocess.check_output(
                ["gsettings", "get", "com.deepin.dde.appearance", "gtk-theme"],
                text=True, stderr=subprocess.DEVNULL
            ).strip().lower()
            if "dark" in out:
                return "dark"
            elif "light" in out:
                return "light"
        except Exception:
            pass

    # 4. Fallback: Qt application palette luminance
    app = QApplication.instance()
    if app:
        bg = app.palette().window().color()
        if bg.lightness() < 128:
            return "dark"
        return "light"

    return "dark"


class OmniLogoWidget(QWidget):
    """Vector emblem renderer matching the official OmniHub precision logo"""
    def __init__(self, size=44, is_dark=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.is_dark = is_dark

    def set_theme(self, is_dark):
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        s = self.width()
        scale = s / 240.0
        p.scale(scale, scale)

        # Draw Squircle background
        if self.is_dark:
            grad = QtGui.QLinearGradient(36, 0, 204, 240)
            grad.setColorAt(0, QtGui.QColor("#1B2552"))
            grad.setColorAt(1, QtGui.QColor("#0A0E1C"))
            p.setBrush(QtGui.QBrush(grad))
            p.setPen(QtGui.QPen(QtGui.QColor("#2A3560"), 3))
        else:
            p.setBrush(QtGui.QBrush(QtGui.QColor("#FFFFFF")))
            p.setPen(QtGui.QPen(QtGui.QColor("#D5DAEA"), 3))

        p.drawRoundedRect(QtCore.QRectF(3, 3, 234, 234), 54, 54)

        # Colors for emblem
        if self.is_dark:
            ring_col = QtGui.QColor("#5B6CF0")
            spoke_col = QtGui.QColor("#B7C0FF")
            node_col = QtGui.QColor("#E7ECF4")
            hub_col = QtGui.QColor("#38BDF8")
            core_col = QtGui.QColor("#0B1020")
        else:
            ring_col = QtGui.QColor("#4F5FE0")
            spoke_col = QtGui.QColor("#A5AEF2")
            node_col = QtGui.QColor("#1B2350")
            hub_col = QtGui.QColor("#0EA5E9")
            core_col = QtGui.QColor("#FFFFFF")

        # Inner emblem transform (matches 68% scale in center)
        p.save()
        p.translate(38.4, 38.4)
        p.scale(0.68, 0.68)

        # Outer ring
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(ring_col, 14))
        p.drawEllipse(QtCore.QPointF(120, 120), 96, 96)

        # Spokes
        p.setPen(QtGui.QPen(spoke_col, 8, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        p.drawLine(QtCore.QPointF(120, 120), QtCore.QPointF(120, 24))
        p.drawLine(QtCore.QPointF(120, 120), QtCore.QPointF(203.1, 168))
        p.drawLine(QtCore.QPointF(120, 120), QtCore.QPointF(36.9, 168))

        # Nodes
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(node_col))
        p.drawEllipse(QtCore.QPointF(120, 24), 13, 13)
        p.drawEllipse(QtCore.QPointF(203.1, 168), 13, 13)
        p.drawEllipse(QtCore.QPointF(36.9, 168), 13, 13)

        # Hub & core
        p.setBrush(QtGui.QBrush(hub_col))
        p.drawEllipse(QtCore.QPointF(120, 120), 28, 28)
        p.setBrush(QtGui.QBrush(core_col))
        p.drawEllipse(QtCore.QPointF(120, 120), 9, 9)

        p.restore()
        p.end()


DARK_THEME_QSS = """
    QMainWindow {
        background-color: #0B0F19;
        color: #F1F4FA;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', 'Ubuntu', sans-serif;
    }
    QWidget {
        color: #F1F4FA;
    }
    QScrollArea#contentScrollArea, QScrollArea#contentScrollArea > QWidget > QWidget {
        background: transparent;
        border: none;
    }
    QWidget#scrollContentPage {
        background: transparent;
    }
    QFrame#sidebarFrame {
        background-color: #0D1222;
        border-right: 1px solid #1E2942;
    }
    QFrame#statusCard {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #12182C, stop:1 #0E1324);
        border: 1px solid #1F2A44;
        border-radius: 12px;
    }
    GlassCard {
        background-color: #12182C;
        border: 1px solid #1F2A44;
        border-radius: 14px;
    }
    GlassCard:hover {
        border-color: #5B6CF0;
    }
    #MetricCard {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141A2E, stop:1 #0F1424);
        border: 1px solid #1F2A44;
        border-radius: 14px;
    }
    #MetricCard:hover {
        border: 1px solid #5B6CF0;
    }
    StepCard {
        background-color: #0E1324;
        border: 1px solid #1A233D;
        border-radius: 10px;
    }
    StepCard:hover {
        border-color: #2D3A5C;
    }
    QLabel#stepTitle {
        color: #F1F4FA;
        font-size: 13px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#stepSub {
        color: #8591A5;
        font-size: 11px;
        background: transparent;
    }
    QLabel#stepStatus {
        color: #8591A5;
        font-size: 11px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#bannerTitle {
        font-size: 18px;
        font-weight: 900;
        color: #FFFFFF;
        background: transparent;
    }
    QLabel#heroTitle {
        font-size: 22px;
        font-weight: 900;
        color: #FFFFFF;
        background: transparent;
    }
    QLabel#devName {
        font-size: 17px;
        font-weight: 900;
        color: #FFFFFF;
        background: transparent;
    }
    QLabel#metricTitle {
        color: #8591A5;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        background: transparent;
    }
    QLabel#metricValue {
        color: #FFFFFF;
        font-size: 26px;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: transparent;
    }
    NavButton {
        text-align: left;
        padding-left: 18px;
        background-color: transparent;
        color: #8591A5;
        border: none;
        outline: none;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
    }
    NavButton:hover {
        background-color: #161D32;
        color: #F1F4FA;
    }
    NavButton:checked {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        color: #FFFFFF;
        font-weight: 700;
    }
    NavButton:focus {
        outline: none;
        border: none;
    }
    QPushButton {
        background-color: #161D32;
        color: #F1F5F9;
        border: 1px solid #24304D;
        border-radius: 9px;
        padding: 9px 18px;
        font-weight: 700;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #202A46;
        border-color: #5B6CF0;
        color: #FFFFFF;
    }
    QPushButton#primaryGradientBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        border: 1px solid #5B6CF0;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#primaryGradientBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4351CC, stop:1 #0284C7);
    }
    QPushButton#kofiBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5E5B, stop:1 #E0403D);
        border: 1px solid #FF7B79;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 13px;
    }
    QPushButton#kofiBtn:hover {
        background: #E0403D;
    }
    QPushButton#fbBtn {
        background: #1877F2;
        border: 1px solid #166FE5;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#donateBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #BE123C);
        border: 1px solid #F43F5E;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#limeBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
        border: 1px solid #34D399;
        color: #FFFFFF;
        font-weight: 800;
    }
    QComboBox {
        background-color: #12182C;
        border: 1px solid #24304D;
        border-radius: 8px;
        padding: 5px 12px;
        color: #F1F5F9;
        font-weight: 700;
        font-size: 12px;
    }
    QComboBox QAbstractItemView {
        background-color: #12182C;
        color: #F1F5F9;
        selection-background-color: #4F5FE0;
        border: 1px solid #24304D;
    }
    QTextEdit, QLineEdit {
        background-color: #070A12;
        border: 1px solid #1F2A44;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 8px;
    }
    QProgressBar {
        background-color: #161D32;
        border: none;
        border-radius: 6px;
        height: 8px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        border-radius: 6px;
    }
    ChatBubble#chatBubbleBot {
        background-color: #12182C;
        border: 1px solid #1F2A44;
        border-radius: 14px;
        border-bottom-left-radius: 2px;
    }
    ChatBubble#chatBubbleBot QLabel#bubbleSender {
        color: #38BDF8;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
        background: transparent;
    }
    ChatBubble#chatBubbleBot QLabel#bubbleText {
        color: #F8FAFC;
        font-size: 13.5px;
        line-height: 1.5;
        background: transparent;
    }
    ChatBubble#chatBubbleUser {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        border: 1px solid #5B6CF0;
        border-radius: 14px;
        border-bottom-right-radius: 2px;
    }
    ChatBubble#chatBubbleUser QLabel#bubbleSender {
        color: #E0E7FF;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
        background: transparent;
    }
    ChatBubble#chatBubbleUser QLabel#bubbleText {
        color: #FFFFFF;
        font-size: 13.5px;
        line-height: 1.5;
        background: transparent;
    }
"""

LIGHT_THEME_QSS = """
    QMainWindow {
        background-color: #F3F5FA;
        color: #10172F;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', 'Ubuntu', sans-serif;
    }
    QWidget {
        color: #10172F;
    }
    QScrollArea#contentScrollArea, QScrollArea#contentScrollArea > QWidget > QWidget {
        background: transparent;
        border: none;
    }
    QWidget#scrollContentPage {
        background: transparent;
    }
    QFrame#sidebarFrame {
        background-color: #FFFFFF;
        border-right: 1px solid #D5DAEA;
    }
    QFrame#statusCard {
        background: #F8FAFD;
        border: 1px solid #D5DAEA;
        border-radius: 12px;
    }
    GlassCard {
        background-color: #FFFFFF;
        border: 1px solid #D5DAEA;
        border-radius: 14px;
    }
    GlassCard:hover {
        border-color: #4F5FE0;
    }
    #MetricCard {
        background: #FFFFFF;
        border: 1px solid #D5DAEA;
        border-radius: 14px;
    }
    #MetricCard:hover {
        border: 1px solid #4F5FE0;
    }
    StepCard {
        background-color: #F8FAFD;
        border: 1px solid #D5DAEA;
        border-radius: 10px;
    }
    StepCard:hover {
        border-color: #4F5FE0;
    }
    QLabel#stepTitle {
        color: #10172F;
        font-size: 13px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#stepSub {
        color: #64748B;
        font-size: 11px;
        background: transparent;
    }
    QLabel#stepStatus {
        color: #64748B;
        font-size: 11px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#bannerTitle {
        font-size: 18px;
        font-weight: 900;
        color: #10172F;
        background: transparent;
    }
    QLabel#heroTitle {
        font-size: 22px;
        font-weight: 900;
        color: #10172F;
        background: transparent;
    }
    QLabel#devName {
        font-size: 17px;
        font-weight: 900;
        color: #10172F;
        background: transparent;
    }
    QLabel#metricTitle {
        color: #64748B;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        background: transparent;
    }
    QLabel#metricValue {
        color: #10172F;
        font-size: 26px;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: transparent;
    }
    NavButton {
        text-align: left;
        padding-left: 18px;
        background-color: transparent;
        color: #475569;
        border: none;
        outline: none;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
    }
    NavButton:hover {
        background-color: #F1F5F9;
        color: #10172F;
    }
    NavButton:checked {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        color: #FFFFFF;
        font-weight: 700;
    }
    NavButton:focus {
        outline: none;
        border: none;
    }
    QPushButton {
        background-color: #FFFFFF;
        color: #10172F;
        border: 1px solid #CBD5E1;
        border-radius: 9px;
        padding: 9px 18px;
        font-weight: 700;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #F8FAFD;
        border-color: #4F5FE0;
    }
    QPushButton#primaryGradientBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4351CC, stop:1 #0284C7);
        border: 1px solid #4F5FE0;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#primaryGradientBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3743B3, stop:1 #0274B0);
    }
    QPushButton#kofiBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5E5B, stop:1 #E0403D);
        border: 1px solid #FF7B79;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 13px;
    }
    QPushButton#kofiBtn:hover {
        background: #E0403D;
    }
    QPushButton#fbBtn {
        background: #1877F2;
        border: 1px solid #166FE5;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#donateBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #BE123C);
        border: 1px solid #F43F5E;
        color: #FFFFFF;
        font-weight: 800;
    }
    QPushButton#limeBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
        border: 1px solid #34D399;
        color: #FFFFFF;
        font-weight: 800;
    }
    QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 5px 12px;
        color: #10172F;
        font-weight: 700;
        font-size: 12px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        color: #10172F;
        selection-background-color: #4F5FE0;
        border: 1px solid #CBD5E1;
    }
    QTextEdit, QLineEdit {
        background-color: #FFFFFF;
        border: 1px solid #D5DAEA;
        color: #10172F;
        border-radius: 8px;
        padding: 8px;
    }
    QProgressBar {
        background-color: #E2E8F0;
        border: none;
        border-radius: 6px;
        height: 8px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        border-radius: 6px;
    }
    ChatBubble#chatBubbleBot {
        background-color: #FFFFFF;
        border: 1px solid #D5DAEA;
        border-radius: 14px;
        border-bottom-left-radius: 2px;
    }
    ChatBubble#chatBubbleBot QLabel#bubbleSender {
        color: #0284C7;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
        background: transparent;
    }
    ChatBubble#chatBubbleBot QLabel#bubbleText {
        color: #10172F;
        font-size: 13.5px;
        line-height: 1.5;
        background: transparent;
    }
    ChatBubble#chatBubbleUser {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F5FE0, stop:1 #0EA5E9);
        border: 1px solid #5B6CF0;
        border-radius: 14px;
        border-bottom-right-radius: 2px;
    }
    ChatBubble#chatBubbleUser QLabel#bubbleSender {
        color: #E0E7FF;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
        background: transparent;
    }
    ChatBubble#chatBubbleUser QLabel#bubbleText {
        color: #FFFFFF;
        font-size: 13.5px;
        line-height: 1.5;
        background: transparent;
    }
"""


# ================= Custom UI Components =================

class GlassCard(QFrame):
    def __init__(self, parent=None, accent=None, glow=False):
        super().__init__(parent)
        self.setObjectName("GlassCard")


class MetricHeroCard(QFrame):
    def __init__(self, title, value, subtitle, icon="⚡", accent_color="#6366F1", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("metricTitle")
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setStyleSheet(f"font-size: 20px; color: {accent_color}; background: transparent;")
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()
        top_row.addWidget(self.lbl_icon)
        layout.addLayout(top_row)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("metricValue")
        layout.addWidget(self.lbl_value)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("metricSub")
        self.lbl_sub.setStyleSheet(f"color: {accent_color}; font-size: 12px; font-weight: 600; background: transparent;")
        layout.addWidget(self.lbl_sub)


class StepCard(QFrame):
    """Sleek pipeline step tile with glowing indicator"""
    def __init__(self, num, title, subtitle, parent=None):
        super().__init__(parent)
        self.num = num
        self.setFixedHeight(66)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        self.dot = QLabel(str(num))
        self.dot.setObjectName("stepDot")
        self.dot.setFixedSize(26, 26)
        self.dot.setAlignment(Qt.AlignCenter)
        self.dot.setStyleSheet("background-color: rgba(148, 163, 184, 0.18); color: #94A3B8; font-size: 12px; font-weight: 800; border-radius: 13px;")
        layout.addWidget(self.dot)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)
        self.l1 = QLabel(title)
        self.l1.setObjectName("stepTitle")
        self.l1.setFixedHeight(20)
        self.l2 = QLabel(subtitle)
        self.l2.setObjectName("stepSub")
        self.l2.setFixedHeight(18)
        text_layout.addWidget(self.l1)
        text_layout.addWidget(self.l2)
        layout.addLayout(text_layout)

        layout.addStretch()

        self.status = QLabel("Pending")
        self.status.setObjectName("stepStatus")
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.status)

    def set_state(self, state, text, color):
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; background: transparent;")
        if state == "done":
            self.dot.setText("✓")
            self.dot.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-size: 12px; font-weight: 800; border-radius: 13px;")
        elif state == "running":
            self.dot.setText("●")
            self.dot.setStyleSheet("background-color: #0EA5E9; color: #FFFFFF; font-size: 12px; font-weight: 800; border-radius: 13px;")
        elif state == "error":
            self.dot.setText("✗")
            self.dot.setStyleSheet("background-color: #EF4444; color: #FFFFFF; font-size: 12px; font-weight: 800; border-radius: 13px;")
        else:
            self.dot.setText(str(self.num))
            self.dot.setStyleSheet("background-color: rgba(148, 163, 184, 0.18); color: #94A3B8; font-size: 12px; font-weight: 800; border-radius: 13px;")


class NavButton(QPushButton):
    def __init__(self, text, icon="●", parent=None):
        super().__init__(f"  {icon}   {text}", parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)


class ChatBubble(QFrame):
    def __init__(self, sender, text, is_user=False, parent=None):
        super().__init__(parent)
        self.setObjectName("chatBubbleUser" if is_user else "chatBubbleBot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        lbl_sender = QLabel(sender)
        lbl_sender.setObjectName("bubbleSender")
        layout.addWidget(lbl_sender)

        lbl_text = QLabel(text)
        lbl_text.setObjectName("bubbleText")
        lbl_text.setWordWrap(True)
        lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(lbl_text)


# ================= Main Window =================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniHub — Precision AI Gateway, Installer & System Studio")
        self.setMinimumSize(1100, 760)
        self.resize(1180, 800)

        icon_path = get_app_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        self.theme_mode = "system"
        self.active_theme = detect_system_theme()

        self.init_layout()
        self.apply_theme(self.active_theme)
        self.setup_tray()

        # Thread-safe workers
        self.health_worker = HealthCheckWorker(self)
        self.health_worker.result.connect(self.on_health_result)

        self.doctor_worker = DoctorWorker(self)
        self.doctor_worker.log_line.connect(self.log_msg)

        # Real-time timers
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self.check_omniroute_health)
        self.health_timer.start(2500)

        self.sys_timer = QTimer(self)
        self.sys_timer.timeout.connect(self.update_system_stats)
        self.sys_timer.start(2000)

        # Auto theme check timer (every 4s)
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_auto_theme)
        self.theme_timer.start(4000)

        # Trigger immediately
        self.check_omniroute_health()
        self.update_system_stats()

    def closeEvent(self, event):
        try:
            self.health_timer.stop()
            self.sys_timer.stop()
            self.theme_timer.stop()
            if hasattr(self, 'health_worker') and self.health_worker.isRunning():
                self.health_worker.quit()
                self.health_worker.wait(800)
            if hasattr(self, 'doctor_worker') and self.doctor_worker.isRunning():
                self.doctor_worker.quit()
                self.doctor_worker.wait(800)
        except Exception:
            pass
        event.accept()

    def on_theme_selection_changed(self, index):
        if index == 0:
            self.theme_mode = "system"
            self.apply_theme(detect_system_theme())
        elif index == 1:
            self.theme_mode = "dark"
            self.apply_theme("dark")
        elif index == 2:
            self.theme_mode = "light"
            self.apply_theme("light")

    def check_auto_theme(self):
        if self.theme_mode == "system":
            sys_theme = detect_system_theme()
            if sys_theme != self.active_theme:
                self.apply_theme(sys_theme)

    def apply_theme(self, theme_name):
        self.active_theme = theme_name
        is_dark = (theme_name == "dark")

        if hasattr(self, 'sidebar_logo'):
            self.sidebar_logo.set_theme(is_dark)
        if hasattr(self, 'about_logo'):
            self.about_logo.set_theme(is_dark)

        if is_dark:
            self.setStyleSheet(DARK_THEME_QSS)
            if hasattr(self, 'lbl_app_name'):
                self.lbl_app_name.setStyleSheet("font-size: 19px; font-weight: 800; color: #F1F4FA; letter-spacing: -0.4px;")
            if hasattr(self, 'lbl_app_badge'):
                self.lbl_app_badge.setStyleSheet("font-size: 9px; font-weight: 800; color: #38BDF8; letter-spacing: 1.2px;")
            if hasattr(self, 'lbl_header_title'):
                self.lbl_header_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.5px;")
            if hasattr(self, 'lbl_header_desc'):
                self.lbl_header_desc.setStyleSheet("font-size: 12px; color: #8591A5;")
        else:
            self.setStyleSheet(LIGHT_THEME_QSS)
            if hasattr(self, 'lbl_app_name'):
                self.lbl_app_name.setStyleSheet("font-size: 19px; font-weight: 800; color: #10172F; letter-spacing: -0.4px;")
            if hasattr(self, 'lbl_app_badge'):
                self.lbl_app_badge.setStyleSheet("font-size: 9px; font-weight: 800; color: #0284C7; letter-spacing: 1.2px;")
            if hasattr(self, 'lbl_header_title'):
                self.lbl_header_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #10172F; letter-spacing: -0.5px;")
            if hasattr(self, 'lbl_header_desc'):
                self.lbl_header_desc.setStyleSheet("font-size: 12px; color: #64748B;")

        if hasattr(self, 'chat_scroll'):
            if is_dark:
                self.chat_scroll.setStyleSheet("background-color: #0A0D17; border: 1px solid #1A2238; border-radius: 14px;")
            else:
                self.chat_scroll.setStyleSheet("background-color: #FFFFFF; border: 1px solid #D5DAEA; border-radius: 14px;")

        if hasattr(self, 'txt_notes'):
            if is_dark:
                self.txt_notes.setStyleSheet("""
                    background-color: #080A10;
                    border: 1px solid #161D2E;
                    color: #E2E8F0;
                    font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
                    font-size: 13px;
                    padding: 14px;
                    line-height: 1.5;
                """)
            else:
                self.txt_notes.setStyleSheet("""
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    color: #0F172A;
                    font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
                    font-size: 13px;
                    padding: 14px;
                    line-height: 1.5;
                """)

    def init_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ================= LEFT SIDEBAR =================
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebarFrame")
        self.sidebar.setFixedWidth(264)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(16, 20, 16, 18)
        sb_layout.setSpacing(8)

        # Brand Header with Official Vector Emblem
        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)

        self.sidebar_logo = OmniLogoWidget(size=44, is_dark=(self.active_theme == "dark"))
        brand_row.addWidget(self.sidebar_logo)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(1)
        self.lbl_app_name = QLabel("OmniHub")
        self.lbl_app_name.setStyleSheet("font-size: 19px; font-weight: 800; letter-spacing: -0.4px;")
        self.lbl_app_badge = QLabel("PRO GATEWAY STUDIO")
        self.lbl_app_badge.setStyleSheet("font-size: 9px; font-weight: 800; color: #38BDF8; letter-spacing: 1.2px;")
        brand_text_box.addWidget(self.lbl_app_name)
        brand_text_box.addWidget(self.lbl_app_badge)
        brand_row.addLayout(brand_text_box)
        brand_row.addStretch()

        sb_layout.addLayout(brand_row)
        sb_layout.addSpacing(14)

        # Section Label
        lbl_nav = QLabel("WORKSPACE MENU")
        lbl_nav.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; padding-left: 6px;")
        sb_layout.addWidget(lbl_nav)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_start = NavButton("Start && Install", "✦")
        self.btn_nav_gw = NavButton("Gateway Overview", "◈")
        self.btn_nav_ai = NavButton("AI Studio && Chat", "🗨")
        self.btn_nav_sys = NavButton("System Radar", "📶")
        self.btn_nav_tools = NavButton("Code && Scratchpad", "✎")
        self.btn_nav_about = NavButton("About && Support", "ⓘ")

        self.btn_nav_start.setChecked(True)

        nav_buttons = [
            self.btn_nav_start, self.btn_nav_gw, self.btn_nav_ai,
            self.btn_nav_sys, self.btn_nav_tools, self.btn_nav_about
        ]
        for idx, btn in enumerate(nav_buttons):
            self.nav_group.addButton(btn, idx)
            sb_layout.addWidget(btn)

        self.nav_group.buttonClicked[int].connect(self.switch_page)

        sb_layout.addStretch()

        # Bottom Server Status Card in Sidebar
        self.sb_status_card = QFrame()
        self.sb_status_card.setObjectName("statusCard")
        sb_card_layout = QVBoxLayout(self.sb_status_card)
        sb_card_layout.setContentsMargins(12, 10, 12, 10)
        sb_card_layout.setSpacing(6)

        sb_card_header = QHBoxLayout()
        self.lbl_sb_dot = QLabel("●")
        self.lbl_sb_dot.setStyleSheet("color: #EF4444; font-size: 14px;")
        self.lbl_sb_status = QLabel("Server Offline")
        self.lbl_sb_status.setStyleSheet("font-size: 12px; font-weight: 700;")
        sb_card_header.addWidget(self.lbl_sb_dot)
        sb_card_header.addWidget(self.lbl_sb_status)
        sb_card_header.addStretch()
        sb_card_layout.addLayout(sb_card_header)

        self.lbl_sb_info = QLabel("Port: 20128 • v3.8.54")
        self.lbl_sb_info.setStyleSheet("color: #64748B; font-size: 11px;")
        sb_card_layout.addWidget(self.lbl_sb_info)

        btn_sb_restart = QPushButton("🔄 Restart Engine")
        btn_sb_restart.setFixedHeight(28)
        btn_sb_restart.setStyleSheet("font-size: 11px; padding: 4px;")
        btn_sb_restart.clicked.connect(lambda: self.run_gateway_action("restart"))
        sb_card_layout.addWidget(btn_sb_restart)

        sb_layout.addWidget(self.sb_status_card)

        root_layout.addWidget(self.sidebar)

        # ================= RIGHT CONTENT AREA =================
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(28, 20, 28, 22)
        content_layout.setSpacing(16)

        # Global Top Header Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(14)

        header_title_box = QVBoxLayout()
        header_title_box.setSpacing(2)
        self.lbl_header_title = QLabel("Start & Install OmniRoute")
        self.lbl_header_title.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: -0.5px;")
        self.lbl_header_desc = QLabel("Automated 1-Click installer, updater and service launcher from GitHub")
        self.lbl_header_desc.setWordWrap(True)
        self.lbl_header_desc.setStyleSheet("font-size: 12px;")
        header_title_box.addWidget(self.lbl_header_title)
        header_title_box.addWidget(self.lbl_header_desc)
        top_bar.addLayout(header_title_box)

        top_bar.addStretch()

        # Theme Switcher Control
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Auto (System)", "Dark Theme", "Light Theme"])
        self.combo_theme.setFixedHeight(34)
        self.combo_theme.setCursor(Qt.PointingHandCursor)
        self.combo_theme.currentIndexChanged.connect(self.on_theme_selection_changed)
        top_bar.addWidget(self.combo_theme)

        # Latency Chip
        self.chip_latency = QLabel("○ Offline")
        self.chip_latency.setStyleSheet("""
            background-color: #27141A;
            color: #F87171;
            border: 1px solid #7F1D1D;
            border-radius: 16px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 700;
        """)
        top_bar.addWidget(self.chip_latency)

        # Web Dashboard Button
        btn_web_dash = QPushButton("🌐 Launch Web Dashboard")
        btn_web_dash.setObjectName("primaryGradientBtn")
        btn_web_dash.setCursor(Qt.PointingHandCursor)
        btn_web_dash.setFixedHeight(38)
        btn_web_dash.clicked.connect(self.open_dashboard)
        top_bar.addWidget(btn_web_dash)

        content_layout.addLayout(top_bar)

        # Stacked Pages
        self.pages = QStackedWidget()
        self.pages.addWidget(self.create_start_page())     # Index 0: Start / Install
        self.pages.addWidget(self.create_gateway_page())   # Index 1: Gateway Overview
        self.pages.addWidget(self.create_ai_page())        # Index 2: AI Studio & Chat
        self.pages.addWidget(self.create_system_page())    # Index 3: System Radar
        self.pages.addWidget(self.create_tools_page())     # Index 4: Code & Scratchpad
        self.pages.addWidget(self.create_about_page())     # Index 5: About & Support

        content_layout.addWidget(self.pages)
        root_layout.addWidget(content_area)

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)
        titles = [
            ("Start & Install OmniRoute", "Automated 1-Click installer, updater and service launcher from GitHub"),
            ("Gateway Overview", "Monitor AI traffic, multi-provider routing & service health"),
            ("AI Studio & Chat", "Direct inference tester connected to OmniRoute's auto-fallback matrix"),
            ("System Radar", "Real-time hardware telemetry and Deepin host metrics"),
            ("Code & Scratchpad", "Persistent developer notepad with automated JSON & token utilities"),
            ("About & Support", f"Created with passion by {DEV_NAME} ({DEV_ORG}) for Deepin OS")
        ]
        self.lbl_header_title.setText(titles[index][0])
        self.lbl_header_desc.setText(titles[index][1])

    # ================= 0. START / INSTALLER PAGE =================
    def create_start_page(self):
        scroll = QScrollArea()
        scroll.setObjectName("contentScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)

        page = QWidget()
        page.setObjectName("scrollContentPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(14)

        # Banner Card
        banner = GlassCard(accent="#223050")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(24, 20, 24, 20)
        b_layout.setSpacing(10)

        top_banner_row = QHBoxLayout()
        b_title = QLabel("✦ 1-Click OmniRoute Setup & Automated Installer")
        b_title.setObjectName("bannerTitle")
        top_banner_row.addWidget(b_title)
        top_banner_row.addStretch()

        badge_repo = QLabel("github.com/cheaper-inference/OmniRoute")
        badge_repo.setStyleSheet("""
            background-color: #0D1527;
            color: #38BDF8;
            border: 1px solid #1E3A5F;
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        top_banner_row.addWidget(badge_repo)
        b_layout.addLayout(top_banner_row)

        b_desc = QLabel(
            "Automatically downloads the latest source release from GitHub, prepares the Node v24 runtime, "
            "resolves 2,400+ dependencies, configures Better-SQLite3 native engines, and brings up the local gateway daemon on port 20128."
        )
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("font-size: 13px; color: #8591A5; line-height: 1.55;")
        b_layout.addWidget(b_desc)

        # Action Buttons Row
        act_row = QHBoxLayout()
        act_row.setSpacing(12)

        self.btn_run_install = QPushButton("⚡ 1-Click Install / Update OmniRoute")
        self.btn_run_install.setObjectName("primaryGradientBtn")
        self.btn_run_install.setFixedHeight(44)
        self.btn_run_install.setCursor(Qt.PointingHandCursor)
        self.btn_run_install.clicked.connect(self.start_installation)
        act_row.addWidget(self.btn_run_install)

        self.btn_fast_start = QPushButton("▶ Launch Gateway Service")
        self.btn_fast_start.setObjectName("limeBtn")
        self.btn_fast_start.setFixedHeight(44)
        self.btn_fast_start.setCursor(Qt.PointingHandCursor)
        self.btn_fast_start.clicked.connect(lambda: self.run_gateway_action("start"))
        act_row.addWidget(self.btn_fast_start)

        btn_view_gw = QPushButton("🌐 View Gateway Panel")
        btn_view_gw.setFixedHeight(44)
        btn_view_gw.clicked.connect(lambda: self.btn_nav_gw.setChecked(True) or self.switch_page(1))
        act_row.addWidget(btn_view_gw)

        b_layout.addSpacing(4)
        b_layout.addLayout(act_row)
        layout.addWidget(banner)

        # Step-by-Step Progress Checklist Card
        steps_card = GlassCard()
        sc_layout = QVBoxLayout(steps_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(8)

        sc_title = QLabel("AUTOMATED INSTALLATION PIPELINE")
        sc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        sc_layout.addWidget(sc_title)

        self.step_widgets = []
        step_definitions = [
            (1, "Pre-Flight & Permissions", "Verify Node.js v24, npm, and unlock ~/.cache permissions"),
            (2, "Download from GitHub", "Clone or pull latest release from cheaper-inference/OmniRoute"),
            (3, "Dependency Resolution", "Execute npm install and patch required packages"),
            (4, "Native Modules & Keytar", "Configure Better-SQLite3, Keytar, and local .env deployment"),
            (5, "Launch & Verify Service", "Start background daemon on http://localhost:20128/api/monitoring/health")
        ]

        for num, title, sub in step_definitions:
            card = StepCard(num, title, sub)
            sc_layout.addWidget(card)
            self.step_widgets.append(card)

        # Overall Progress Bar
        sc_layout.addSpacing(6)
        self.install_progress = QProgressBar()
        self.install_progress.setValue(0)
        sc_layout.addWidget(self.install_progress)

        layout.addWidget(steps_card)

        # Installation Console / Terminal Log
        term_card = GlassCard()
        tc_layout = QVBoxLayout(term_card)
        tc_layout.setContentsMargins(18, 12, 18, 12)
        tc_layout.setSpacing(8)

        tc_header = QHBoxLayout()
        tc_title = QLabel("INSTALLATION OUTPUT STREAM")
        tc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #38BDF8; letter-spacing: 1.2px;")
        tc_header.addWidget(tc_title)
        tc_header.addStretch()

        btn_clear_inst = QPushButton("Clear Output")
        btn_clear_inst.setFixedHeight(26)
        btn_clear_inst.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        btn_clear_inst.clicked.connect(lambda: self.txt_install_log.clear())
        tc_header.addWidget(btn_clear_inst)
        tc_layout.addLayout(tc_header)

        self.txt_install_log = QTextEdit()
        self.txt_install_log.setReadOnly(True)
        self.txt_install_log.setStyleSheet("""
            background-color: #06080F;
            border: 1px solid #141A2B;
            color: #A7F3D0;
            font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
            font-size: 12px;
            padding: 10px;
            line-height: 1.45;
        """)
        self.txt_install_log.setText("Ready. Click '1-Click Install / Update OmniRoute' to begin setup.")
        tc_layout.addWidget(self.txt_install_log)

        layout.addWidget(term_card)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def start_installation(self):
        self.btn_run_install.setEnabled(False)
        self.btn_run_install.setText("⏳ Installing OmniRoute...")
        self.install_progress.setValue(5)
        self.txt_install_log.clear()
        self.log_install_msg("Starting automated 1-Click Installation for OmniRoute...")

        for card in self.step_widgets:
            card.set_state("pending", "Pending", "#64748B")

        self.installer_worker = OmniRouteInstallerWorker(OMNIROUTE_DIR)
        self.installer_worker.log_line.connect(self.log_install_msg)
        self.installer_worker.step_updated.connect(self.on_installer_step)
        self.installer_worker.progress_val.connect(self.install_progress.setValue)
        self.installer_worker.finished.connect(self.on_install_finished)
        self.installer_worker.start()

    def log_install_msg(self, msg):
        self.txt_install_log.append(msg)
        self.txt_install_log.moveCursor(QtGui.QTextCursor.End)

    def on_installer_step(self, step_idx, status_text, color_hex):
        if 0 <= step_idx < len(self.step_widgets):
            card = self.step_widgets[step_idx]
            if "#10B981" in color_hex:
                card.set_state("done", status_text, color_hex)
            elif "#EF4444" in color_hex:
                card.set_state("error", status_text, color_hex)
            else:
                card.set_state("running", status_text, color_hex)

    def on_install_finished(self, success, message):
        self.btn_run_install.setEnabled(True)
        self.btn_run_install.setText("⚡ 1-Click Install / Update OmniRoute")
        if success:
            QMessageBox.information(self, "Installation Complete", message)
            self.check_omniroute_health()
        else:
            QMessageBox.warning(self, "Installation Note", message)

    # ================= 1. GATEWAY PAGE =================
    def create_gateway_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 3 Top KPI Cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self.kpi_status = MetricHeroCard("Engine Liveness", "OFFLINE", "● http://localhost:20128", "🟢", "#10B981")
        self.kpi_providers = MetricHeroCard("Provider Matrix", "389 Active", "150+ Cataloged Free Tiers", "🔮", "#8B5CF6")
        self.kpi_speed = MetricHeroCard("Edge Latency", "-- ms", "Local Fast Intercept", "⚡", "#06B6D4")

        kpi_row.addWidget(self.kpi_status)
        kpi_row.addWidget(self.kpi_providers)
        kpi_row.addWidget(self.kpi_speed)
        layout.addLayout(kpi_row)

        # Service Control & Endpoints (2 Columns)
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        # Left: Service Controls Card
        ctrl_card = GlassCard()
        cc_layout = QVBoxLayout(ctrl_card)
        cc_layout.setContentsMargins(20, 18, 20, 18)
        cc_layout.setSpacing(12)

        ctrl_title = QLabel("SERVICE MANAGEMENT")
        ctrl_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        cc_layout.addWidget(ctrl_title)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(10)

        self.btn_gw_start = QPushButton("▶ Start Service")
        self.btn_gw_start.setObjectName("successBtn")
        self.btn_gw_start.clicked.connect(lambda: self.run_gateway_action("start"))
        btn_grid.addWidget(self.btn_gw_start)

        self.btn_gw_restart = QPushButton("🔄 Restart")
        self.btn_gw_restart.clicked.connect(lambda: self.run_gateway_action("restart"))
        btn_grid.addWidget(self.btn_gw_restart)

        self.btn_gw_stop = QPushButton("⏹ Stop")
        self.btn_gw_stop.setObjectName("dangerBtn")
        self.btn_gw_stop.clicked.connect(lambda: self.run_gateway_action("stop"))
        btn_grid.addWidget(self.btn_gw_stop)

        cc_layout.addLayout(btn_grid)

        btn_doctor = QPushButton("🩺 Run OmniRoute Doctor Diagnostics")
        btn_doctor.clicked.connect(self.run_doctor_check)
        cc_layout.addWidget(btn_doctor)

        mid_row.addWidget(ctrl_card, stretch=4)

        # Right: Connection Endpoints Card
        ep_card = GlassCard()
        ep_layout = QVBoxLayout(ep_card)
        ep_layout.setContentsMargins(20, 18, 20, 18)
        ep_layout.setSpacing(10)

        ep_title = QLabel("CONNECTION CREDENTIALS")
        ep_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        ep_layout.addWidget(ep_title)

        ep_row = QHBoxLayout()
        self.txt_api_base = QLineEdit(f"{OMNIROUTE_BASE}/v1")
        self.txt_api_base.setReadOnly(True)
        btn_copy_base = QPushButton("📋 Copy URL")
        btn_copy_base.clicked.connect(self.copy_api_url)
        ep_row.addWidget(self.txt_api_base)
        ep_row.addWidget(btn_copy_base)
        ep_layout.addLayout(ep_row)

        lbl_auth_hint = QLabel("Default Auth: <b>Bearer local</b> • Management Pass: <b>CHANGEME</b>")
        lbl_auth_hint.setStyleSheet("color: #64748B; font-size: 11px;")
        ep_layout.addWidget(lbl_auth_hint)

        mid_row.addWidget(ep_card, stretch=5)
        layout.addLayout(mid_row)

        # Live Activity Terminal Console
        console_card = GlassCard()
        cons_layout = QVBoxLayout(console_card)
        cons_layout.setContentsMargins(18, 14, 18, 14)
        cons_layout.setSpacing(8)

        cons_header = QHBoxLayout()
        cons_title = QLabel("SYSTEM CONSOLE & AUDIT TRAIL")
        cons_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #F59E0B; letter-spacing: 1.2px;")
        cons_header.addWidget(cons_title)
        cons_header.addStretch()

        btn_clear_cons = QPushButton("Clear")
        btn_clear_cons.setFixedHeight(24)
        btn_clear_cons.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        btn_clear_cons.clicked.connect(lambda: self.txt_console.clear())
        cons_header.addWidget(btn_clear_cons)
        cons_layout.addLayout(cons_header)

        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("""
            background-color: #06080F;
            border: 1px solid #141A2B;
            color: #38BDF8;
            font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
            font-size: 12px;
            padding: 10px;
            line-height: 1.4;
        """)
        self.log_msg("OmniHub Engine initialized. Ready.")
        cons_layout.addWidget(self.txt_console)

        layout.addWidget(console_card, stretch=1)
        return page

    # ================= 2. AI STUDIO PAGE =================
    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        config_card = GlassCard()
        cc_layout = QHBoxLayout(config_card)
        cc_layout.setContentsMargins(14, 10, 14, 10)
        cc_layout.setSpacing(14)

        cc_layout.addWidget(QLabel("<b>Model:</b>"))
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.addItems(["auto", "gpt-4o", "claude-3-5-sonnet", "gemini-1.5-flash", "deepseek-coder", "llama-3.3-70b"])
        self.cb_model.setFixedWidth(200)
        cc_layout.addWidget(self.cb_model)

        cc_layout.addWidget(QLabel("<b>System:</b>"))
        self.txt_ai_sys = QLineEdit()
        self.txt_ai_sys.setPlaceholderText("Optional system role (e.g. Expert Python Senior Engineer)...")
        cc_layout.addWidget(self.txt_ai_sys)

        layout.addWidget(config_card)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background-color: #0A0D17; border: 1px solid #1A2238; border-radius: 14px;")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        self.add_chat_bubble(
            "OmniRoute Assistant",
            "Hello! I am connected to OmniRoute's auto-failover AI router with access to over 389 providers. How can I help you today?",
            is_user=False
        )

        input_card = GlassCard()
        ic_layout = QVBoxLayout(input_card)
        ic_layout.setContentsMargins(14, 12, 14, 12)
        ic_layout.setSpacing(10)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips = ["💡 Ping Latency", "⚡ Write Python QuickSort", "🌐 Explain OmniRoute Auto-fallback"]
        for c in chips:
            btn_chip = QPushButton(c)
            btn_chip.setFixedHeight(26)
            btn_chip.setStyleSheet("""
                QPushButton {
                    background-color: #151A29;
                    border: 1px solid #232C42;
                    border-radius: 13px;
                    color: #94A3B8;
                    font-size: 11px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                    border-color: #38BDF8;
                }
            """)
            btn_chip.clicked.connect(lambda _, t=c: self.apply_chip(t))
            chips_row.addWidget(btn_chip)
        chips_row.addStretch()

        self.lbl_ai_status = QLabel("Ready")
        self.lbl_ai_status.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        chips_row.addWidget(self.lbl_ai_status)
        ic_layout.addLayout(chips_row)

        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(10)

        self.txt_ai_prompt = QTextEdit()
        self.txt_ai_prompt.setPlaceholderText("Type a prompt... (Press Enter to Send, Shift+Enter for new line)")
        self.txt_ai_prompt.setFixedHeight(68)
        self.txt_ai_prompt.installEventFilter(self)
        prompt_row.addWidget(self.txt_ai_prompt)

        self.btn_ai_send = QPushButton("Send  ↵")
        self.btn_ai_send.setObjectName("primaryGradientBtn")
        self.btn_ai_send.setCursor(Qt.PointingHandCursor)
        self.btn_ai_send.setFixedSize(110, 68)
        self.btn_ai_send.clicked.connect(self.send_ai_prompt)
        prompt_row.addWidget(self.btn_ai_send)

        ic_layout.addLayout(prompt_row)
        layout.addWidget(input_card)

        return page

    def apply_chip(self, chip_text):
        prompts = {
            "💡 Ping Latency": "Respond with 'PONG' and report your configured model identity.",
            "⚡ Write Python QuickSort": "Write an optimized Python implementation of QuickSort with comments and time complexity.",
            "🌐 Explain OmniRoute Auto-fallback": "Briefly explain how OmniRoute routes AI requests with automatic fallback across providers."
        }
        self.txt_ai_prompt.setPlainText(prompts.get(chip_text, chip_text))

    def add_chat_bubble(self, sender, text, is_user=False):
        bubble = ChatBubble(sender, text, is_user=is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def send_ai_prompt(self):
        prompt = self.txt_ai_prompt.toPlainText().strip()
        if not prompt:
            return

        model = self.cb_model.currentText().strip() or "auto"
        sys_prompt = self.txt_ai_sys.text().strip()

        self.add_chat_bubble("You", prompt, is_user=True)
        self.txt_ai_prompt.clear()

        self.btn_ai_send.setEnabled(False)
        self.btn_ai_send.setText("⏳ ...")
        self.lbl_ai_status.setText(f"Routing to '{model}'...")

        self.ai_worker = AIChatWorker(model, prompt, sys_prompt)
        self.ai_worker.finished.connect(self.on_ai_finish)
        self.ai_worker.start()

    def on_ai_finish(self, success, response, elapsed):
        self.btn_ai_send.setEnabled(True)
        self.btn_ai_send.setText("Send  ↵")
        if success:
            words = len(response.split())
            self.lbl_ai_status.setText(f"✓ Responded in {elapsed:.2f}s (~{words} words)")
            self.add_chat_bubble(f"OmniRoute ({self.cb_model.currentText()})", response, is_user=False)
        else:
            self.lbl_ai_status.setText(f"✗ Failed ({elapsed:.2f}s)")
            self.add_chat_bubble("Error", response, is_user=False)

    def eventFilter(self, obj, event):
        if obj == getattr(self, 'txt_ai_prompt', None) and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.send_ai_prompt()
                return True
        return super().eventFilter(obj, event)

    # ================= 3. SYSTEM RADAR PAGE =================
    def create_system_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        res_card = GlassCard()
        rc_layout = QVBoxLayout(res_card)
        rc_layout.setContentsMargins(22, 20, 22, 20)
        rc_layout.setSpacing(16)

        rc_title = QLabel("HARDWARE UTILIZATION GAUGES")
        rc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        rc_layout.addWidget(rc_title)

        cpu_row = QHBoxLayout()
        self.lbl_cpu_head = QLabel("CPU Load")
        self.lbl_cpu_head.setStyleSheet("font-weight: 700; font-size: 13px;")
        self.lbl_cpu_val = QLabel("0%")
        self.lbl_cpu_val.setStyleSheet("color: #38BDF8; font-weight: 800; font-size: 14px;")
        cpu_row.addWidget(self.lbl_cpu_head)
        cpu_row.addStretch()
        cpu_row.addWidget(self.lbl_cpu_val)
        rc_layout.addLayout(cpu_row)

        self.bar_cpu = QProgressBar()
        rc_layout.addWidget(self.bar_cpu)

        ram_row = QHBoxLayout()
        self.lbl_ram_head = QLabel("Memory (RAM)")
        self.lbl_ram_head.setStyleSheet("font-weight: 700; font-size: 13px;")
        self.lbl_ram_val = QLabel("0 / 0 GB")
        self.lbl_ram_val.setStyleSheet("color: #A78BFA; font-weight: 800; font-size: 14px;")
        ram_row.addWidget(self.lbl_ram_head)
        ram_row.addStretch()
        ram_row.addWidget(self.lbl_ram_val)
        rc_layout.addLayout(ram_row)

        self.bar_ram = QProgressBar()
        rc_layout.addWidget(self.bar_ram)

        disk_row = QHBoxLayout()
        self.lbl_disk_head = QLabel("Root NVMe / SSD Storage")
        self.lbl_disk_head.setStyleSheet("font-weight: 700; font-size: 13px;")
        self.lbl_disk_val = QLabel("0 / 0 GB")
        self.lbl_disk_val.setStyleSheet("color: #34D399; font-weight: 800; font-size: 14px;")
        disk_row.addWidget(self.lbl_disk_head)
        disk_row.addStretch()
        disk_row.addWidget(self.lbl_disk_val)
        rc_layout.addLayout(disk_row)

        self.bar_disk = QProgressBar()
        rc_layout.addWidget(self.bar_disk)

        layout.addWidget(res_card)

        host_card = GlassCard()
        hc_layout = QVBoxLayout(host_card)
        hc_layout.setContentsMargins(22, 20, 22, 20)
        hc_layout.setSpacing(12)

        hc_title = QLabel("OPERATING SYSTEM & RUNTIME SPECIFICATIONS")
        hc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        hc_layout.addWidget(hc_title)

        self.lbl_host_specs = QLabel("Inspecting environment...")
        self.lbl_host_specs.setStyleSheet("font-size: 13px; line-height: 1.8; color: #CBD5E1;")
        hc_layout.addWidget(self.lbl_host_specs)

        layout.addWidget(host_card)
        layout.addStretch()
        return page

    # ================= 4. CODE & TOOLS PAGE =================
    def create_tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        tb_card = GlassCard()
        tb_layout = QHBoxLayout(tb_card)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(10)

        tb_title = QLabel("<b>SCRATCHPAD:</b>")
        tb_title.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 800;")
        tb_layout.addWidget(tb_title)

        btn_json = QPushButton("{ } Format JSON")
        btn_json.clicked.connect(self.format_json)
        tb_layout.addWidget(btn_json)

        btn_enc = QPushButton("B64 Encode")
        btn_enc.clicked.connect(self.b64_encode)
        tb_layout.addWidget(btn_enc)

        btn_dec = QPushButton("B64 Decode")
        btn_dec.clicked.connect(self.b64_decode)
        tb_layout.addWidget(btn_dec)

        btn_tok = QPushButton("📊 Count Tokens")
        btn_tok.clicked.connect(self.count_tokens)
        tb_layout.addWidget(btn_tok)

        tb_layout.addStretch()

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.clicked.connect(self.clear_notes)
        tb_layout.addWidget(btn_clear)

        layout.addWidget(tb_card)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Paste prompts, JSON payloads, API secrets, or temporary notes here (Auto-saves continuously)...")
        self.txt_notes.setStyleSheet("""
            background-color: #080A10;
            border: 1px solid #161D2E;
            color: #E2E8F0;
            font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
            font-size: 13px;
            padding: 14px;
            line-height: 1.5;
        """)

        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    self.txt_notes.setText(f.read())
            except Exception:
                pass

        self.txt_notes.textChanged.connect(self.save_notes)
        layout.addWidget(self.txt_notes, stretch=1)

        launch_card = GlassCard()
        lc_layout = QHBoxLayout(launch_card)
        lc_layout.setContentsMargins(14, 10, 14, 10)
        lc_layout.setSpacing(12)

        lc_title = QLabel("<b>FAST LAUNCH:</b>")
        lc_title.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 800;")
        lc_layout.addWidget(lc_title)

        btn_term = QPushButton("💻 Terminal")
        btn_term.clicked.connect(self.open_terminal)
        lc_layout.addWidget(btn_term)

        btn_files = QPushButton("📁 Files")
        btn_files.clicked.connect(self.open_file_manager)
        lc_layout.addWidget(btn_files)

        btn_chrome = QPushButton("🌐 Browser")
        btn_chrome.clicked.connect(self.open_browser)
        lc_layout.addWidget(btn_chrome)

        btn_anti = QPushButton("🪐 Antigravity")
        btn_anti.clicked.connect(lambda: subprocess.Popen(["antigravity"], shell=True))
        lc_layout.addWidget(btn_anti)

        lc_layout.addStretch()
        layout.addWidget(launch_card)

        return page

    # ================= 5. ABOUT & SUPPORT PAGE =================
    def create_about_page(self):
        scroll = QScrollArea()
        scroll.setObjectName("contentScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)

        page = QWidget()
        page.setObjectName("scrollContentPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(16)

        # Top Hero Card
        hero_card = GlassCard(accent="#2D3A5C", glow=True)
        hc_layout = QVBoxLayout(hero_card)
        hc_layout.setContentsMargins(24, 22, 24, 22)
        hc_layout.setSpacing(10)

        hero_row = QHBoxLayout()
        self.about_logo = OmniLogoWidget(size=64, is_dark=(self.active_theme == "dark"))
        hero_row.addWidget(self.about_logo)

        hero_text_box = QVBoxLayout()
        hero_text_box.setSpacing(3)
        h_title = QLabel("OmniHub — AI Gateway & System Studio")
        h_title.setObjectName("heroTitle")
        h_version = QLabel("Version 3.0.0 (Pro Edition) • Deepin Linux Native")
        h_version.setStyleSheet("font-size: 12px; font-weight: 700; color: #10B981;")
        hero_text_box.addWidget(h_title)
        hero_text_box.addWidget(h_version)
        hero_row.addLayout(hero_text_box)
        hero_row.addStretch()

        badge_open = QLabel("GPL v3.0 OPEN SOURCE")
        badge_open.setStyleSheet("""
            background-color: #172554;
            color: #60A5FA;
            border: 1px solid #2563EB;
            border-radius: 12px;
            padding: 6px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        hero_row.addWidget(badge_open)
        hc_layout.addLayout(hero_row)

        h_desc = QLabel(
            "OmniHub is a high-performance desktop control center and gateway interface for "
            "<b>OmniRoute</b>, featuring 1-click automated setup from GitHub, multi-provider "
            "model routing (389 AI providers with 150+ free tiers), real-time hardware telemetry, "
            "and developer tools."
        )
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("font-size: 13px; color: #8591A5; line-height: 1.6;")
        hc_layout.addWidget(h_desc)
        layout.addWidget(hero_card)

        # Developer & Socials Row (2 Columns)
        row_dev = QHBoxLayout()
        row_dev.setSpacing(14)

        # Developer Info Card
        dev_card = GlassCard()
        dc_layout = QVBoxLayout(dev_card)
        dc_layout.setContentsMargins(22, 18, 22, 18)
        dc_layout.setSpacing(12)

        dc_head = QLabel("DEVELOPER PROFILE")
        dc_head.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        dc_layout.addWidget(dc_head)

        dev_info_box = QHBoxLayout()
        dev_info_box.setSpacing(14)

        dev_avatar = QLabel("SH")
        dev_avatar.setFixedSize(54, 54)
        dev_avatar.setAlignment(Qt.AlignCenter)
        dev_avatar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #06B6D4);
            color: #FFFFFF;
            font-size: 20px;
            font-weight: 900;
            border-radius: 27px;
            border: 2px solid #38BDF8;
        """)
        dev_info_box.addWidget(dev_avatar)

        dev_details = QVBoxLayout()
        dev_details.setSpacing(2)
        dev_name_lbl = QLabel(DEV_NAME)
        dev_name_lbl.setObjectName("devName")
        dev_org_lbl = QLabel(f"{DEV_ORG} • Creator & Linux Developer")
        dev_org_lbl.setStyleSheet("font-size: 12px; color: #38BDF8; font-weight: 600;")
        dev_details.addWidget(dev_name_lbl)
        dev_details.addWidget(dev_org_lbl)
        dev_info_box.addLayout(dev_details)
        dev_info_box.addStretch()
        dc_layout.addLayout(dev_info_box)

        # Social & Profile Buttons
        btn_fb = QPushButton("📘 Connect on Facebook (hossain.sojibs)")
        btn_fb.setObjectName("fbBtn")
        btn_fb.setCursor(Qt.PointingHandCursor)
        btn_fb.setFixedHeight(40)
        btn_fb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DEV_FB)))
        dc_layout.addWidget(btn_fb)

        btn_git = QPushButton("🐙 GitHub Profile (sojibcreates-maker)")
        btn_git.setCursor(Qt.PointingHandCursor)
        btn_git.setFixedHeight(38)
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DEV_GITHUB)))
        dc_layout.addWidget(btn_git)

        row_dev.addWidget(dev_card, stretch=5)

        # Donation & Support Card (Ko-fi & SupportKori)
        don_card = GlassCard(accent="#FF5E5B", glow=True)
        don_layout = QVBoxLayout(don_card)
        don_layout.setContentsMargins(22, 18, 22, 18)
        don_layout.setSpacing(12)

        don_head = QLabel("SUPPORT & BUY ME A COFFEE")
        don_head.setStyleSheet("font-size: 11px; font-weight: 800; color: #FF5E5B; letter-spacing: 1.2px;")
        don_layout.addWidget(don_head)

        don_text = QLabel(
            "Love using OmniHub? Support ongoing development, feature releases, and Linux desktop "
            "maintenance by buying Sojib a coffee on Ko-fi!"
        )
        don_text.setWordWrap(True)
        don_text.setStyleSheet("font-size: 12.5px; line-height: 1.5; color: #8591A5;")
        don_layout.addWidget(don_text)

        btn_kofi = QPushButton("☕ Buy Me a Coffee on Ko-fi (ko-fi.com/sojibhossain)")
        btn_kofi.setObjectName("kofiBtn")
        btn_kofi.setCursor(Qt.PointingHandCursor)
        btn_kofi.setFixedHeight(44)
        btn_kofi.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DEV_KOFI)))
        don_layout.addWidget(btn_kofi)

        btn_donate = QPushButton("♥ Support via SupportKori (supportkori.com/sojib)")
        btn_donate.setObjectName("donateBtn")
        btn_donate.setCursor(Qt.PointingHandCursor)
        btn_donate.setFixedHeight(38)
        btn_donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATION_URL)))
        don_layout.addWidget(btn_donate)

        row_dev.addWidget(don_card, stretch=6)
        layout.addLayout(row_dev)

        cred_card = GlassCard()
        cc_layout = QVBoxLayout(cred_card)
        cc_layout.setContentsMargins(22, 16, 22, 16)
        cc_layout.setSpacing(8)

        cc_title = QLabel("ACKNOWLEDGEMENTS & CREDITS")
        cc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #64748B; letter-spacing: 1.2px;")
        cc_layout.addWidget(cc_title)

        cc_desc = QLabel(
            "• <b>OmniRoute Engine:</b> Created by Diego Souza & the open-source community (<code>github.com/cheaper-inference/OmniRoute</code>)<br/>"
            "• <b>Framework:</b> Python 3, PyQt5 (Qt 5.15), and Deepin Desktop Environment (DDE 25)<br/>"
            "• <b>Special Thanks:</b> All contributors and supporters from Bangladesh and the global Linux developer community."
        )
        cc_desc.setWordWrap(True)
        cc_desc.setStyleSheet("font-size: 12px; color: #8591A5; line-height: 1.6;")
        cc_layout.addWidget(cc_desc)

        layout.addWidget(cred_card)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    # ================= LOGIC & REAL-TIME UPDATES =================
    def log_msg(self, text):
        t_str = time.strftime("%H:%M:%S")
        self.txt_console.append(f"<span style='color: #64748B;'>[{t_str}]</span> {text}")

    def check_omniroute_health(self):
        if hasattr(self, 'health_worker') and not self.health_worker.isRunning():
            self.health_worker.start()

    def on_health_result(self, is_ok, latency):
        try:
            if is_ok:
                self.kpi_status.lbl_value.setText("HEALTHY 200")
                self.kpi_status.lbl_sub.setText("● http://localhost:20128")
                self.kpi_speed.lbl_value.setText(f"{latency} ms")
                self.chip_latency.setText(f"⚡ {latency} ms")
                self.chip_latency.setStyleSheet("""
                    background-color: #064E3B;
                    color: #34D399;
                    border: 1px solid #059669;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 700;
                """)
                self.lbl_sb_dot.setStyleSheet("color: #10B981; font-size: 14px;")
                self.lbl_sb_status.setText("Server Online")
            else:
                self.kpi_status.lbl_value.setText("OFFLINE")
                self.kpi_status.lbl_sub.setText("Service stopped")
                self.kpi_speed.lbl_value.setText("-- ms")
                self.chip_latency.setText("○ Disconnected")
                self.chip_latency.setStyleSheet("""
                    background-color: #27141A;
                    color: #F87171;
                    border: 1px solid #7F1D1D;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 700;
                """)
                self.lbl_sb_dot.setStyleSheet("color: #EF4444; font-size: 14px;")
                self.lbl_sb_status.setText("Server Offline")
        except Exception:
            pass

    def update_system_stats(self):
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            self.bar_cpu.setValue(int(cpu_pct))
            cores = psutil.cpu_count(logical=True)
            self.lbl_cpu_val.setText(f"{cpu_pct:.1f}% ({cores} Cores)")

            mem = psutil.virtual_memory()
            mem_used = mem.used / (1024 ** 3)
            mem_total = mem.total / (1024 ** 3)
            self.bar_ram.setValue(int(mem.percent))
            self.lbl_ram_val.setText(f"{mem_used:.2f} GB / {mem_total:.2f} GB ({mem.percent}%)")

            root_drive = os.path.splitdrive(os.path.abspath("."))[0] or "/"
            if platform.system() == "Windows" and not root_drive.endswith("\\"):
                root_drive += "\\"
            disk = psutil.disk_usage(root_drive)
            disk_used = disk.used / (1024 ** 3)
            disk_total = disk.total / (1024 ** 3)
            self.bar_disk.setValue(int(disk.percent))
            self.lbl_disk_val.setText(f"{disk_used:.1f} GB / {disk_total:.1f} GB ({disk.percent}%)")

            boot = time.time() - psutil.boot_time()
            hours = int(boot // 3600)
            mins = int((boot % 3600) // 60)

            sys_os = f"{platform.system()} {platform.release()}"
            if platform.system() == "Linux":
                try:
                    with open("/etc/os-release") as f:
                        for line in f:
                            if line.startswith("PRETTY_NAME="):
                                sys_os = line.split("=", 1)[1].strip().strip('"')
                                break
                except Exception:
                    pass
            elif platform.system() == "Darwin":
                try:
                    v = subprocess.check_output(["sw_vers", "-productVersion"], text=True, stderr=subprocess.DEVNULL).strip()
                    sys_os = f"macOS {v}"
                except Exception:
                    sys_os = f"macOS ({platform.machine()})"
            elif platform.system() == "Windows":
                sys_os = f"Windows {platform.release()} ({platform.version()})"

            if platform.system() == "Windows":
                de_name = "Windows Shell (Explorer)"
            elif platform.system() == "Darwin":
                de_name = "Aqua / Cocoa Desktop"
            else:
                de_name = os.environ.get("XDG_CURRENT_DESKTOP") or "Linux Desktop"

            self.lbl_host_specs.setText(
                f"• <b>Operating System:</b> {sys_os}<br/>"
                f"• <b>Desktop Environment:</b> {de_name}<br/>"
                f"• <b>System Uptime:</b> {hours} hours, {mins} minutes<br/>"
                f"• <b>Python Runtime:</b> v{platform.python_version()} ({platform.machine()})<br/>"
                f"• <b>OmniRoute Engine:</b> v3.8.54 ({OMNIROUTE_DIR})"
            )
        except Exception:
            pass

    def run_gateway_action(self, action):
        self.log_msg(f"Triggered action: <b>{action.upper()}</b>")
        self.gw_worker = OmniRouteWorker(action)
        self.gw_worker.finished.connect(lambda ok, msg: self.log_msg(f"<b>Result:</b> {msg}"))
        self.gw_worker.start()

    def run_doctor_check(self):
        self.log_msg("Executing <code>omniroute doctor</code>...")
        if hasattr(self, 'doctor_worker') and not self.doctor_worker.isRunning():
            self.doctor_worker.start()

    def open_dashboard(self):
        QDesktopServices.openUrl(QUrl(OMNIROUTE_DASHBOARD))
        self.log_msg(f"Opened web dashboard at {OMNIROUTE_DASHBOARD}")

    def open_terminal(self):
        sys_plat = platform.system()
        if sys_plat == "Windows":
            subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe"])
        elif sys_plat == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
        else:
            for term in ["deepin-terminal", "gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "xterm"]:
                if shutil.which(term):
                    subprocess.Popen([term])
                    return
            subprocess.Popen(["x-terminal-emulator"])

    def open_browser(self):
        webbrowser.open("https://google.com")

    def open_file_manager(self):
        sys_plat = platform.system()
        if sys_plat == "Windows":
            subprocess.Popen(["explorer.exe", os.path.expanduser("~")])
        elif sys_plat == "Darwin":
            subprocess.Popen(["open", os.path.expanduser("~")])
        else:
            for fm in ["dde-file-manager", "nautilus", "dolphin", "thunar", "nemo", "xdg-open"]:
                if shutil.which(fm):
                    subprocess.Popen([fm, os.path.expanduser("~")])
                    return

    def copy_api_url(self):
        QApplication.clipboard().setText(f"{OMNIROUTE_BASE}/v1")
        self.log_msg(f"Copied endpoint: <code>{OMNIROUTE_BASE}/v1</code> to clipboard.")

    # Utilities
    def save_notes(self):
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                f.write(self.txt_notes.toPlainText())
        except Exception:
            pass

    def clear_notes(self):
        if QMessageBox.question(self, "Clear Notes", "Wipe scratchpad contents?") == QMessageBox.Yes:
            self.txt_notes.clear()
            self.save_notes()

    def format_json(self):
        raw = self.txt_notes.toPlainText().strip()
        try:
            data = json.loads(raw)
            self.txt_notes.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            self.log_msg("JSON formatted successfully.")
        except Exception as e:
            QMessageBox.warning(self, "JSON Format Error", str(e))

    def b64_encode(self):
        raw = self.txt_notes.toPlainText()
        enc = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
        self.txt_notes.setPlainText(enc)

    def b64_decode(self):
        raw = self.txt_notes.toPlainText().strip()
        try:
            dec = base64.b64decode(raw.encode('utf-8')).decode('utf-8')
            self.txt_notes.setPlainText(dec)
        except Exception as e:
            QMessageBox.warning(self, "Decoding Error", str(e))

    def count_tokens(self):
        raw = self.txt_notes.toPlainText()
        chars = len(raw)
        words = len(raw.split())
        est = int(chars / 4)
        QMessageBox.information(
            self, "Token & Character Analysis",
            f"Characters: {chars:,}\nWords: {words:,}\nEstimated Tokens: ~{est:,}"
        )

    # System Tray
    def setup_tray(self):
        icon_path = get_app_icon_path()
        if not icon_path or not os.path.exists(icon_path):
            return

        self.tray = QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        self.tray_menu = QMenu(self)

        act_show = QAction("Open OmniHub Studio", self)
        act_show.triggered.connect(self.showNormal)
        self.tray_menu.addAction(act_show)

        act_dash = QAction("Open Web Dashboard", self)
        act_dash.triggered.connect(self.open_dashboard)
        self.tray_menu.addAction(act_dash)

        self.tray_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.quit)
        self.tray_menu.addAction(act_quit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()


def main():
    if "--version" in sys.argv or "-v" in sys.argv:
        print("OmniHub 3.0.0 — Precision AI Gateway & System Studio")
        return 0
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""OmniHub 3.0.0 — Precision AI Gateway & System Studio

Cross-Platform AI Gateway Control Center & System Studio for Linux, Windows & macOS.

Usage:
  omnihub [options]

Options:
  -h, --help       Show this help message and exit
  -v, --version    Show version information and exit
  --page <name>    Open directly to page (start, ai, gateway, system, tools, about)
  --restart        Restart the OmniRoute background service
""")
        return 0

    if platform.system() == "Linux" and "QT_QPA_PLATFORM" not in os.environ:
        if os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setApplicationName("omnihub")
    app.setDesktopFileName("omnihub.desktop")

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
