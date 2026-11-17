#!/usr/bin/env python3
"""Full verification sweep for OmniHub: CLI, themes, pages, shortcuts."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, ROOT)

PASS = []
FAIL = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  — {detail}" if detail else ""))


# --------------------------------------------------------------------- CLI
def check_cli():
    launcher = os.path.expanduser("~/.local/bin/omnihub")
    if os.path.exists(launcher):
        check("launcher exists", True)
        check("launcher points at main.py", os.path.realpath(launcher) == os.path.join(ROOT, "main.py"))
        cmd_base = [launcher]
    else:
        check("launcher entrypoint exists", os.path.exists(os.path.join(ROOT, "main.py")))
        cmd_base = [sys.executable, os.path.join(ROOT, "main.py")]

    for flag in ("--version", "--help"):
        proc = subprocess.run([*cmd_base, flag], capture_output=True, text=True, timeout=60)
        check(f"CLI {flag}", proc.returncode == 0, proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else "")

    proc = subprocess.run([*cmd_base, "--version"], capture_output=True, text=True, timeout=60)
    check("version string", "OmniHub" in proc.stdout, proc.stdout.strip())


# ------------------------------------------------------------------- theme
def check_theme():
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    from omnihub.context import AppContext
    from omnihub.theme import ACCENTS, LIGHT, DARK, build_stylesheet

    ctx = AppContext()
    app.setProperty("omnihub.context", ctx)

    check("palette tokens present", len(vars(DARK)) > 30, f"{len(vars(DARK))} tokens")
    for token in ("bg", "surface", "border", "text", "accent", "success", "danger", "warning"):
        check(f"token '{token}'", hasattr(DARK, token) and hasattr(LIGHT, token))
    check("accent presets", len(ACCENTS) >= 6, ", ".join(ACCENTS))

    dark_css = build_stylesheet(DARK)
    light_css = build_stylesheet(LIGHT)
    check("stylesheet generated", len(dark_css) > 8000, f"{len(dark_css)} bytes")
    check("themes differ", dark_css != light_css)

    for mode in ("light", "dark", "system"):
        ctx.theme.set_mode(mode, persist=False)
        check(f"mode '{mode}' resolves", ctx.theme.mode == mode, ctx.theme.effective_mode())

    ctx.theme.set_mode("system", persist=False)
    check("system detection returns a theme", ctx.theme.effective_mode() in ("light", "dark"),
          ctx.theme.effective_mode())

    for key in ACCENTS:
        ctx.theme.set_accent(key, persist=False)
        check(f"accent '{key}'", ctx.theme.palette.accent == ACCENTS[key].resolve(ctx.theme.is_dark)[0])

    ctx.theme.set_density("compact", persist=False)
    check("compact density", ctx.theme.metrics.compact)
    ctx.theme.set_font_scale(1.2, persist=False)
    check("font scale", abs(ctx.theme.metrics.font_scale - 1.2) < 0.01)
    ctx.theme.set_mode("dark", persist=False)
    ctx.theme.set_accent("indigo", persist=False)
    app.quit()


# ------------------------------------------------------------------- pages
def check_pages():
    from PyQt5.QtWidgets import QApplication, QScrollArea

    app = QApplication(sys.argv[:1])
    from omnihub.context import AppContext
    from omnihub.window import MainWindow

    ctx = AppContext()
    app.setProperty("omnihub.context", ctx)
    ctx.theme.apply(app)

    win = MainWindow(ctx)
    win.resize(1360, 860)
    win.show()
    app.processEvents()

    check("six pages", win.pages.count() == 6, f"{win.pages.count()}")
    for index in range(win.pages.count()):
        win.switch_page(index)
        app.processEvents()
        page = win.pages.currentWidget()
        title = win.lbl_page_title.text()
        check(f"page {index} '{title}'", bool(title) and page is not None)

    check("command palette commands", len(win._build_commands()) >= 15,
          f"{len(win._build_commands())}")
    check("shortcuts registered", len(win.findChildren(__import__('PyQt5.QtWidgets', fromlist=['QShortcut']).QShortcut)) >= 10)

    win.toggle_sidebar()
    app.processEvents()
    check("sidebar collapses", win.sidebar.width() < 120, f"{win.sidebar.width()}px")
    win.toggle_sidebar()
    app.processEvents()
    check("sidebar expands", win.sidebar.width() > 200, f"{win.sidebar.width()}px")

    win.resize(900, 700)
    app.processEvents()
    check("responsive sidebar rail", win.sidebar.width() < 120, f"{win.sidebar.width()}px")
    win.resize(1360, 860)
    app.processEvents()

    for area in win.findChildren(QScrollArea):
        check("scroll area intact", area.widget() is not None)

    win.close()
    app.quit()


# ---------------------------------------------------------------- settings
def check_settings():
    import tempfile

    from omnihub.config import Settings

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "s.json")
        settings = Settings(path)
        settings.load()
        check("defaults applied", settings.get("theme.mode") == "system")

        settings.set("theme.mode", "dark")
        settings.save()
        reloaded = Settings(path)
        reloaded.load()
        check("round trip", reloaded.get("theme.mode") == "dark")

        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{ broken json")
        broken = Settings(path)
        broken.load()
        # A corrupt file falls back to the backup copy, and to the defaults
        # when there is no backup either.
        check("corrupt file recovers", broken.get("theme.mode") in ("system", "light", "dark"),
              str(broken.get("theme.mode")))

        settings.set("gateway.api_key", "secret-key")
        check("secret masked", "secret" not in Settings.redact("secret-key"), Settings.redact("secret-key"))

        check("atomic write leaves no temp files", sorted(os.listdir(folder)) == ["s.json"],
              str(sorted(os.listdir(folder))))


# -------------------------------------------------------------------- api
def check_api():
    from omnihub.api import OmniRouteClient

    client = OmniRouteClient("http://127.0.0.1:59998", "local", 5)
    ok, info = client.health(timeout=2)
    check("unreachable gateway handled", not ok and info.get("status") == "offline")
    check("error message is helpful", "Cannot reach" in str(info.get("error", "")),
          str(info.get("error"))[:60])

    ok, models, reason = client.models(timeout=2)
    check("models failure reported", not ok and bool(reason), reason[:60])

    ok, payload = client.chat([{"role": "user", "content": "hi"}], model="auto", timeout=3)
    check("chat failure reported", not ok and "error" in payload)

    client.configure(base_url="http://127.0.0.1:20199", api_key="test-key")
    check("client reconfigures", client.base_url == "http://127.0.0.1:20199")


def main():
    check_cli()
    check_settings()
    check_api()
    check_theme()
    check_pages()

    print("\n" + "=" * 62)
    print(f"{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
    for name, detail in FAIL:
        print(f"  FAILED: {name} ({detail})")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
