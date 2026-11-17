<div align="center">

# 🪐 OmniHub: Precision AI Gateway & System Studio

**Ultra-Modern Native Desktop Control Center & 1-Click OmniRoute Installer**  
*Seamless AI Model Routing, Real-Time Hardware Telemetry, and Developer Studio for Linux, Windows & macOS*

[![GitHub Release](https://img.shields.io/github/v/release/sojibcreates-maker/OmniHub?style=for-the-badge&logo=github&color=6366F1)](https://github.com/sojibcreates-maker/OmniHub/releases/latest)
[![Platform Support](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-10B981?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/sojibcreates-maker/OmniHub/releases)
[![Python Support](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Deepin DDE](https://img.shields.io/badge/Desktop-Deepin%20DDE%2025%20Fashion%20Dock-0078D7?style=for-the-badge)](https://www.deepin.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)
[![Sponsor on Ko-fi](https://img.shields.io/badge/Donate-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/sojibhossain)

Designed & engineered by **[Md Sojib Hossain](https://github.com/sojibcreates-maker)** ([SojibLabs](https://facebook.com/hossain.sojibs))

[📥 Download Software](#-download-ready-to-run-software) • [✨ Key Features](#-key-features) • [🚀 Quick Start](#-quick-start--installation) • [⌨️ Shortcuts](#️-global-shortcuts) • [☕ Support](#-support--donations)

<br/>

<img src="screenshot.png" alt="OmniHub Studio UI Preview - Precision AI Gateway on Deepin OS" width="900" style="border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);"/>

</div>

---

## 📑 Table of Contents

- [📥 Download Ready-to-Run Software](#-download-ready-to-run-software)
- [🌟 Overview & Architecture](#-overview--architecture)
- [✨ Key Features](#-key-features)
- [🖥️ Supported Operating Systems](#️-supported-operating-systems)
- [🚀 Quick Start & Installation](#-quick-start--installation)
  - [🐧 Linux (Debian, Deepin, Ubuntu, Arch, Fedora)](#-linux-deepin-debian-ubuntu-arch-fedora)
  - [🪟 Windows (10 & 11)](#-windows-10--11)
  - [🍎 macOS (Intel & Apple Silicon)](#-macos-apple-silicon--intel)
  - [📦 Python Package (pip)](#-universal-python-package-pip)
- [⌨️ Global Shortcuts](#️-global-shortcuts)
- [🧪 Automated Verification & Testing](#-automated-verification--testing)
- [☕ Support & Donations](#-support--donations)
- [📄 License & Authors](#-license--authors)

---

## 📥 Download Ready-to-Run Software

Pre-compiled and packaged releases ready for instant deployment without complex compilation:

| Operating System | Package Type | Download Link | Quick Installation |
| :--- | :--- | :--- | :--- |
| 🐧 **Deepin OS / Debian / Ubuntu** | **Native `.deb` Installer** | [**`omnihub_3.0.0_amd64.deb`** *(57.5 MB)*](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/omnihub_3.0.0_amd64.deb) | Double-click to install via GUI package manager, or `sudo dpkg -i omnihub_3.0.0_amd64.deb` |
| 🐧 **Linux (All Distros)** | **Standalone Binary** | [**`OmniHub-v3.0.0-Linux-Standalone-x86_64`** *(58.3 MB)*](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Linux-Standalone-x86_64) | Single self-contained binary (**Zero Python/pip setup required**). `chmod +x` & run! |
| 🪟 **Windows 10 & 11** | **Portable Archive** | [**`OmniHub-v3.0.0-Windows-Portable.zip`** *(460 KB)*](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Windows-Portable.zip) | Extract zip and double-click `run.bat` |
| 🐧 **Linux (Source + Shell)** | **Tarball Bundle** | [**`OmniHub-v3.0.0-Linux-x86_64.tar.gz`** *(450 KB)*](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Linux-x86_64.tar.gz) | Extract and execute `./install.sh` |
| 📦 **Universal Python** | **Wheel Distribution** | [**`omnihub-3.0.0-py3-none-any.whl`** *(105 KB)*](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/omnihub-3.0.0-py3-none-any.whl) | `pip install omnihub-3.0.0-py3-none-any.whl` |
| 🔒 **All Checksums** | **SHA-256** | [**`SHA256SUMS.txt`**](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/SHA256SUMS.txt) | Integrity verification hashes |

---

## 🌟 Overview & Architecture

**OmniHub** solves the complexity of running and orchestrating unified AI gateways on desktop computers. It provides a native, modern, hardware-accelerated user interface designed specifically for:

- **Local & Remote AI Inference**: Route requests across **389+ supported AI models** (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 2.0, DeepSeek R1/V3, Groq, Ollama, and local models).
- **Automated Service Management**: 1-Click setup, health heartbeat checks, latency sparklines, and auto-recovery watchdog for the [OmniRoute](https://github.com/cheaper-inference/OmniRoute) AI gateway.
- **Hardware Telemetry Radar**: Real-time inspection of CPU cores, memory allocation, storage disk utilization, and operating system specs.
- **Developer Productivity**: Integrated JSON formatter, Base64 encoder/decoder, token counter, and crash-safe auto-saving scratchpad.

---

## ✨ Key Features

### 🚀 1-Click Automated AI Gateway Installer
- Automatic cloning from GitHub repository.
- Automatic Node.js & npm environment verification and pre-flight cache configuration.
- Native build module resolution (keytar) and executable shell scripts generation.
- Real-time step progress visualizer (0% to 100%) and terminal log streaming.

### 💬 Native AI Studio & Streaming Chat
- **Real-Time Streaming**: Server-Sent Events (SSE) token-by-token streaming response.
- **Multi-Model Selector**: Dynamically populated from active gateway endpoints.
- **Customizable System Prompts**: Toggle between General Assistant, Code Specialist, Creative, and Custom modes.
- **Response Metrics**: Per-query response latency and estimated token usage.

### ⚡ System Telemetry Radar
- Multi-core CPU utilization percentage with core count.
- RAM usage gauge (Used GB / Total GB).
- Drive storage tracker and disk partition metrics.
- Host machine info: Linux kernel, desktop environment, and system uptime.

### 🛠️ Developer Utilities & Scratchpad
- **JSON Tool**: Pretty-print, minify, validate, and syntax error feedback.
- **Base64 Tool**: Instant string encoding and decoding.
- **Token Estimator**: Word count, character count, and estimated LLM token count.
- **Persistent Notes**: Auto-saving notepad with backup rotation.

### 🌗 Adaptive Theme Engine
- **Dark Mode & Light Mode**: Precision colorway with glowing accents and smooth transitions.
- **Automated Desktop Detection**:
  - 🪟 Windows: Reads Windows Personalize theme registry (`AppsUseLightTheme`).
  - 🍎 macOS: Probes `AppleInterfaceStyle` via defaults daemon.
  - 🐧 Linux: Probes GNOME `color-scheme`, Deepin DDE `gtk-theme`, KDE `kdeglobals`, and Qt application palette.
- **Desktop Dock Integration**: Custom application icons and desktop shortcut for Linux/Deepin Fashion Dock.

---

## 🖥️ Supported Operating Systems

| Operating System | Compatibility Status | Tested On |
| :--- | :--- | :--- |
| 🐧 **Linux** | ✅ **Full Native Support** | Deepin OS 25 (DDE), Ubuntu 24.04/22.04, Debian 12/13, Fedora 40, Arch Linux |
| 🪟 **Windows** | ✅ **Full Native Support** | Windows 10 (64-bit), Windows 11 (64-bit) |
| 🍎 **macOS** | ✅ **Full Native Support** | macOS Monterey, Ventura, Sonoma, Sequoia (Intel & Apple Silicon) |

---

## 🚀 Quick Start & Installation

### 🐧 Linux (Deepin, Debian, Ubuntu, Arch, Fedora)

#### Option 1: Native `.deb` Package (Recommended for Deepin/Debian/Ubuntu)
```bash
wget https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/omnihub_3.0.0_amd64.deb
sudo dpkg -i omnihub_3.0.0_amd64.deb
```

#### Option 2: Clone & Automated Shell Installer
```bash
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
chmod +x install.sh
./install.sh
```

---

### 🪟 Windows (10 & 11)

#### Option 1: Portable Release
1. Download [**`OmniHub-v3.0.0-Windows-Portable.zip`**](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Windows-Portable.zip).
2. Extract the zip archive.
3. Double-click `run.bat` to launch OmniHub.

#### Option 2: Clone from Git
```cmd
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
install.bat
```

---

### 🍎 macOS (Apple Silicon & Intel)

```bash
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
chmod +x install.sh
./install.sh
```

---

### 📦 Universal Python Package (pip)

OmniHub can be installed directly into any Python 3.10+ virtual environment:
```bash
pip install -r requirements.txt
pip install .
omnihub
```

---

## ⌨️ Global Shortcuts

| Shortcut | Action Description |
| :--- | :--- |
| `Ctrl + K` | Open Interactive Command Palette |
| `Ctrl + 1 … 6` | Switch Sections (*Start, AI Studio, System, Tools, Settings, About*) |
| `Ctrl + D` | Open OmniRoute Web Dashboard in Browser |
| `Ctrl + R` | Restart AI Gateway Background Daemon |
| `Ctrl + Shift + T` | Instant Toggle Light / Dark Theme |
| `Ctrl + Q` | Quit Application |

---

## 🧪 Automated Verification & Testing

OmniHub provides built-in automated test suites verifying CLI flags, settings durability, theme rendering, mock streaming, and layout responsiveness:

```bash
# 1. Full verification sweep (56 validation checks)
python3 verify.py

# 2. End-to-end integration suite with mock gateway (22 checks)
python3 selftest.py
```

---

## ☕ Support & Donations

If OmniHub helps streamline your AI development workflow, please consider supporting the project:

- ☕ **Ko-fi**: [ko-fi.com/sojibhossain](https://ko-fi.com/sojibhossain)
- 💖 **SupportKori**: [supportkori.com/sojib](https://www.supportkori.com/sojib)
- 🌐 **Facebook**: [facebook.com/hossain.sojibs](https://www.facebook.com/hossain.sojibs)
- 💻 **GitHub**: [github.com/sojibcreates-maker](https://github.com/sojibcreates-maker)

---

## 📄 License & Authors

- **Author**: **[Md Sojib Hossain](https://github.com/sojibcreates-maker)** ([SojibLabs](https://facebook.com/hossain.sojibs))
- **Email**: `sojib@matraki.org`
- **License**: MIT License. Free for personal, open-source, and commercial use.

---

<div align="center">
<sub>Keywords: AI Gateway, OmniRoute GUI, LLM Router, Deepin Desktop Studio, Cross-Platform AI Client, PyQt5 Desktop App, OpenAI, Anthropic, Gemini, DeepSeek, Linux Desktop Studio.</sub>
</div>
