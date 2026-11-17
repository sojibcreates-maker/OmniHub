#!/usr/bin/env python3
"""End-to-end smoke test of the OmniHub UI.

Runs entirely offline: a miniature OpenAI-compatible server is started on a
loopback port so the health checks, the model catalogue and the streaming
chat path can all be exercised without touching the real gateway.
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

OUT = "/tmp/opencode/omnihub-e2e"
os.makedirs(OUT, exist_ok=True)

MOCK_PORT = 20199
MOCK_URL = f"http://127.0.0.1:{MOCK_PORT}"
MOCK_KEY = "test-key"

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(("PASS  " if condition else "FAIL  ") + name + (f"  — {detail}" if detail else ""))


# --------------------------------------------------------------- mock server

class _MockHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/monitoring/health"):
            self._json({"status": "healthy", "version": "3.8.54", "setupComplete": True})
        elif self.path.startswith("/v1/models"):
            if self.headers.get("Authorization") != f"Bearer {MOCK_KEY}":
                self._json({"error": {"message": "Invalid API key", "code": "invalid_api_key"}}, 401)
                return
            self._json({
                "object": "list",
                "data": [
                    {"id": "gpt-4o", "owned_by": "openai", "context_window": 128000},
                    {"id": "claude-3-5-sonnet", "owned_by": "anthropic", "context_window": 200000},
                    {"id": "gemini-1.5-flash", "owned_by": "google", "context_window": 1000000},
                    {"id": "llama-3.3-70b", "owned_by": "meta", "context_window": 131072},
                ],
            })
        else:
            self._json({"error": {"message": "not found"}}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except ValueError:
            payload = {}

        if not self.path.startswith("/v1/chat/completions"):
            self._json({"error": {"message": "not found"}}, 404)
            return

        if not payload.get("stream"):
            self._json({
                "id": "chatcmpl-mock",
                "model": payload.get("model", "auto"),
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "PONG (buffered)"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
            })
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        def send(obj):
            self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode())
            self.wfile.flush()

        send({"id": "chatcmpl-keepalive", "object": "chat.completion.chunk",
              "created": 0, "model": "keepalive", "choices": []})
        time.sleep(0.2)

        text = "PONG — streaming works. OmniHub is talking to the mock gateway."
        for word in text.split(" "):
            send({
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": payload.get("model", "auto"),
                "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}],
            })
            time.sleep(0.03)

        send({
            "id": "chatcmpl-mock",
            "object": "chat.completion.chunk",
            "created": 2,
            "model": payload.get("model", "auto"),
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 14, "total_tokens": 26},
        })
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def start_mock_server():
    """Start the mock gateway on a background thread."""
    server = ThreadingHTTPServer(("127.0.0.1", MOCK_PORT), _MockHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main():
    mock = start_mock_server()
    app = QApplication(sys.argv[:1])
    from omnihub.config import Settings
    from omnihub.context import AppContext

    # Use an isolated settings file so the real user configuration is never
    # touched by the test run.
    tmp_settings = "/tmp/opencode/omnihub-e2e-settings.json"
    if os.path.exists(tmp_settings):
        os.unlink(tmp_settings)

    settings = Settings(tmp_settings)
    settings.load()
    settings.set("gateway.base_url", MOCK_URL)
    settings.set("gateway.api_key", MOCK_KEY)
    settings.set("gateway.poll_interval", 1)
    settings.save()

    ctx = AppContext(settings)
    app.setProperty("omnihub.context", ctx)
    ctx.theme.set_mode("dark", persist=False)
    ctx.theme.apply(app)

    from omnihub.window import MainWindow

    win = MainWindow(ctx)
    win.resize(1360, 860)
    win.show()

    def step1():
        page = win.gateway_page
        page.poll_health()
        page.refresh_models()

    def step2():
        page = win.gateway_page
        check("gateway reports online", page.tile_status._value.text() == "Online",
              page.tile_status._value.text())
        check("latency measured", "ms" in page.tile_latency._value.text(),
              page.tile_latency._value.text())
        check("model catalogue loaded", page.tile_models._value.text() == "4",
              page.tile_models._value.text())
        check("model table populated", page.table_models.rowCount() == 4,
              f"rows={page.table_models.rowCount()}")
        check("availability tracked", page.tile_uptime._value.text() != "—",
              page.tile_uptime._value.text())
        check("sparkline has samples", len(page._latencies) >= 1,
              f"n={len(page._latencies)}")

        # model filtering
        page._filter_models("claude")
        check("model filter works", page.table_models.rowCount() == 1,
              f"rows={page.table_models.rowCount()}")
        page._filter_models("")

        # AI studio streaming
        win.switch_page(1)
        page = win.ai_page
        page.refresh_models()
        app.processEvents()
        check("model dropdown populated", page.cb_model.count() >= 4,
              f"count={page.cb_model.count()}")
        page.txt_prompt.setPlainText("Say PONG")
        page.send()

    def step3():
        page = win.ai_page
        text = page._bubble.text() if page._bubble else ""
        check("assistant streamed a response", "PONG" in text, text[:80])
        check("bubble meta shows timing", "s" in page._bubble._meta.text(),
              page._bubble._meta.text())
        check("send button re-enabled", page.btn_send.isEnabled())
        check("history recorded", len(page._history) == 2, f"n={len(page._history)}")
        win.grab().save(f"{OUT}/ai-studio.png")

        # system radar
        win.switch_page(2)
        app.processEvents()
        snap = win.system_page._last_snapshot
        check("cpu sampled", snap.get("cpu_percent", 0) > 0, str(snap.get("cpu_percent")))
        check("memory sampled", snap.get("mem_total", 0) > 0, str(snap.get("mem_total")))
        check("processes listed", len(snap.get("top_processes", [])) > 0,
              f"n={len(snap.get('top_processes', []))}")

        # scratchpad
        win.switch_page(3)
        app.processEvents()
        tools = win.tools_page
        tools.json_input.setPlainText('{"b":2,"a":1}')
        tools._json_pretty()
        check("json pretty print", '"a": 1' in tools.json_input.toPlainText(),
              tools.json_input.toPlainText()[:50].replace("\n", " "))
        tools.enc_input.setPlainText("OmniHub")
        tools.enc_mode.setCurrentText("Base64 encode")
        tools._encode_run()
        check("base64 encode", tools.enc_output.toPlainText() == "T21uaUh1Yg==",
              tools.enc_output.toPlainText())
        tools.hash_input.setPlainText("OmniHub")
        tools.hash_algo.setCurrentText("sha256")
        tools._hash_run()
        check("sha256 hash", len(tools.hash_output.toPlainText()) == 64,
              tools.hash_output.toPlainText()[:16])
        tools.text_input.setPlainText("Hello World")
        tools.text_action.setCurrentText("Slugify")
        tools._text_run()
        check("slugify", tools.text_output.toPlainText() == "hello-world",
              tools.text_output.toPlainText())

        # settings round trip
        win.switch_page(4)
        app.processEvents()
        sp = win.settings_page
        sp.seg_theme.select("Light")
        app.processEvents()
        check("theme switched to light", ctx.theme.palette.name == "light",
              ctx.theme.palette.name)
        sp.seg_theme.select("Dark")
        app.processEvents()
        check("theme switched back to dark", ctx.theme.palette.name == "dark",
              ctx.theme.palette.name)

        # command palette
        commands = win._build_commands()
        check("command palette populated", len(commands) >= 15, f"n={len(commands)}")

        win.grab().save(f"{OUT}/e2e-final.png")

        app.quit()

    QTimer.singleShot(600, step1)
    QTimer.singleShot(2200, step2)
    QTimer.singleShot(5200, step3)
    app.exec_()

    try:
        mock.shutdown()
    except Exception:
        pass
    mock.server_close()

    failures = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 60)
    print(f"{len(RESULTS) - len(failures)}/{len(RESULTS)} checks passed")
    for name, _ok, detail in failures:
        print(f"  FAILED: {name} ({detail})")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--serve-mock" in sys.argv:
        server = start_mock_server()
        print(f"mock gateway listening on {MOCK_URL}", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            server.server_close()
        raise SystemExit(0)
    raise SystemExit(main())
