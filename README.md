# 🪐 OmniHub

**Ultra-Modern Precision AI Gateway, 1-Click OmniRoute Installer & System Studio**  
*Cross-Platform Desktop Control Center for Linux, Windows & macOS*

Designed and engineered by **[Md Sojib Hossain](https://github.com/sojibcreates-maker)** ([SojibLabs](https://facebook.com/hossain.sojibs)).

![OmniHub Desktop Studio](screenshot.png)

---

## 📥 Download Software Packages (v3.0.0)

| OS / Package | Download Link | Installation |
| :--- | :--- | :--- |
| 🐧 **Deepin / Debian / Ubuntu** | [**omnihub_3.0.0_amd64.deb** (57.5 MB)](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/omnihub_3.0.0_amd64.deb) | Native `.deb` Installer (Double-click to install) |
| 🐧 **Linux Standalone Executable** | [**OmniHub-v3.0.0-Linux-Standalone-x86_64** (58.3 MB)](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Linux-Standalone-x86_64) | Single Binary (No Python required) |
| 🪟 **Windows 10 & 11** | [**OmniHub-v3.0.0-Windows-Portable.zip** (460 KB)](https://github.com/sojibcreates-maker/OmniHub/releases/download/v3.0.0/OmniHub-v3.0.0-Windows-Portable.zip) | Portable Package (Run `run.bat`) |
| 🌐 **Release Hub** | [**Browse All Releases & Checksums**](https://github.com/sojibcreates-maker/OmniHub/releases/tag/v3.0.0) | Full Assets & Changelog |

---

## 🌟 Platforms Supported

| Platform | Supported Versions | Launcher / Installer |
| :--- | :--- | :--- |
| 🐧 **Linux** | Deepin OS (DDE), Ubuntu, Debian, Fedora, Arch Linux, etc. | `./install.sh` or `python3 main.py` |
| 🪟 **Windows** | Windows 10 & Windows 11 (64-bit) | `install.bat` or `run.bat` |
| 🍎 **macOS** | macOS Monterey, Ventura, Sonoma, Sequoia (Intel & Apple Silicon) | `./install.sh` or `python3 main.py` |

---

## 🌟 What is OmniHub?

**OmniHub** is a native cross-platform desktop control studio for AI routing, model experimentation, and hardware telemetry:

1. **🚀 1-Click OmniRoute Gateway Installer**: Automatically clones, resolves dependencies, compiles native modules, and launches the OmniRoute AI gateway daemon right from GitHub.
2. **💬 AI Studio & Chat**: Stream live responses across **389+ AI models** (OpenAI, Anthropic Claude, Google Gemini, Groq, DeepSeek, Ollama, local LLMs) via Server-Sent Events (SSE).
3. **⚡ System Radar**: Real-time hardware telemetry: CPU utilisation, per-core load, RAM allocation, storage capacity, and host specs.
4. **🛠️ Developer Scratchpad & Utilities**: Rapid JSON validation & pretty-printer, Base64 encoder/decoder, token estimator, and persistent crash-safe notes.
5. **🌗 Native Adaptive Theme Engine**: Supports both Dark Mode and Light Mode with custom vector icons and automatic desktop appearance detection (Windows Registry, macOS defaults, GNOME/Deepin/KDE).

---

## 🚀 Installation & Setup

### Requirements
- **Python**: Version 3.10 or newer
- **Node.js**: Version 18+ (required for OmniRoute gateway service)
- **Git**: Installed and available in PATH

---

### 🐧 Linux (Deepin, Ubuntu, Debian, Fedora, Arch)

```bash
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
chmod +x install.sh
./install.sh
```
*To run anytime*: type `omnihub` in your terminal or launch from your application menu/dock.

---

### 🪟 Windows (10 & 11)

1. Open PowerShell or Command Prompt:
```cmd
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
install.bat
```
2. Double-click `run.bat` or run:
```cmd
python main.py
```

---

### 🍎 macOS (Apple Silicon & Intel)

```bash
git clone https://github.com/sojibcreates-maker/OmniHub.git
cd OmniHub
chmod +x install.sh
./install.sh
```
*To run anytime*:
```bash
python3 main.py
```

---

### 📦 Pip Package Install (All Platforms)

You can also install OmniHub directly via pip:
```bash
pip install -r requirements.txt
pip install .
omnihub
```

---

## ⌨️ Global Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl + K` | Open Fuzzy Command Palette |
| `Ctrl + 1 … 6` | Switch Sections (Start, AI Studio, System, Tools, Settings, About) |
| `Ctrl + D` | Open OmniRoute Web Dashboard |
| `Ctrl + R` | Restart AI Gateway Service |
| `Ctrl + Shift + T` | Toggle Light / Dark Theme |
| `Ctrl + Q` | Quit Application |

---

## 🧪 Automated Testing

OmniHub includes two headless automated test suites covering CLI arguments, settings durability, theme rendering, and mock streaming:

```bash
# 1. Full verification sweep (CLI, storage, theme tokens, page layout)
python3 verify.py

# 2. End-to-end headless integration suite (Mock gateway, SSE streaming, telemetry)
python3 selftest.py
```

---

## ☕ Support & Donations

If you enjoy using OmniHub, please consider supporting ongoing development:

- ☕ **Ko-fi**: [ko-fi.com/sojibhossain](https://ko-fi.com/sojibhossain)
- 💖 **SupportKori**: [supportkori.com/sojib](https://www.supportkori.com/sojib)
- 🌐 **Facebook**: [facebook.com/hossain.sojibs](https://www.facebook.com/hossain.sojibs)
- 💻 **GitHub**: [github.com/sojibcreates-maker](https://github.com/sojibcreates-maker)

---

## 📄 License

Created by **Md Sojib Hossain (SojibLabs)**. Distributed for personal and community use.
