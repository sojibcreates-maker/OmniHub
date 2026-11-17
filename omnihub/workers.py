"""Background workers.

All network and process work happens off the GUI thread.  Results are
delivered back exclusively through Qt signals, which keeps the UI thread
free and avoids the classic "widget updated from a worker thread" crash.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, QRunnable, QThread, QThreadPool, pyqtSignal

__all__ = [
    "Task",
    "TaskGroup",
    "TaskSignals",
    "ServiceWorker",
    "ChatWorker",
    "SystemSampler",
    "DEFAULT_OMNIROUTE_DIR",
]

DEFAULT_OMNIROUTE_DIR = os.path.expanduser("~/.gemini/antigravity/scratch/OmniRoute")


# ------------------------------------------------------------- generic task

class TaskSignals(QObject):
    """Signals emitted by a :class:`Task`."""

    done = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class Task(QRunnable):
    """Run a callable on the global thread pool and report the result.

    Results are delivered through signals only, so receivers that live in the
    GUI thread are invoked safely via Qt's queued connection mechanism.

    Auto-deletion is disabled deliberately: the pool would otherwise destroy
    the runnable (and with it the signal object) before the queued signal has
    been delivered to the GUI thread.  :class:`TaskGroup` keeps the object
    alive until delivery instead.
    """

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.signals = TaskSignals()
        self._fn = fn
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001
            try:
                self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
            except RuntimeError:
                pass
            return
        if self._cancelled.is_set():
            return
        try:
            self.signals.done.emit(result)
        except RuntimeError:
            pass


class TaskGroup(QObject):
    """Runs background tasks and keeps them alive until their signals land."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tasks: List[Task] = []

    def run(
        self,
        fn: Callable[[], object],
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> Task:
        """Start ``fn`` on the thread pool and route its result to the GUI."""
        task = Task(fn)
        self._tasks.append(task)

        def _done(result):
            self._release(task)
            if on_done is not None:
                on_done(result)

        def _failed(message):
            self._release(task)
            if on_error is not None:
                on_error(message)

        task.signals.done.connect(_done)
        task.signals.failed.connect(_failed)
        QThreadPool.globalInstance().start(task)
        return task

    def _release(self, task: Task) -> None:
        try:
            self._tasks.remove(task)
        except ValueError:
            pass

    def cancel_all(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()


# --------------------------------------------------------- service control

class ServiceWorker(QThread):
    """Start / stop / restart the OmniRoute gateway process."""

    result = pyqtSignal(bool, str)

    def __init__(
        self,
        action: str,
        base_url: str = "http://localhost:20128",
        omniroute_dir: str = DEFAULT_OMNIROUTE_DIR,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.base_url = base_url.rstrip("/")
        self.omniroute_dir = omniroute_dir
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Ask the worker to stop waiting and return promptly."""
        self._cancel.set()

    # -- helpers -----------------------------------------------------------

    def _is_running(self) -> bool:
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/monitoring/health", timeout=1.5)
            return response.status_code < 500
        except Exception:
            return False

    def _launch_command(self) -> Optional[List[str]]:
        """Pick the best available way to boot the gateway."""
        script = os.path.join(self.omniroute_dir, "start-omniroute.sh")
        if os.path.isfile(script) and os.access(script, os.X_OK):
            return ["bash", script]
        if os.path.isfile(script):
            return ["bash", script]
        if shutil.which("omniroute"):
            return ["omniroute", "start"]
        return None

    def _kill_processes(self) -> None:
        patterns = ("run-next.mjs", "next-server", "omniroute")
        for pattern in patterns:
            subprocess.run(["pkill", "-f", pattern], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)

    # -- thread body -------------------------------------------------------

    def run(self) -> None:
        try:
            if self.action == "start":
                if self._is_running():
                    self.result.emit(True, "The gateway is already online.")
                    return
                command = self._launch_command()
                if not command:
                    self.result.emit(False, "No start script or 'omniroute' CLI was found on this machine.")
                    return
                log_path = os.path.join(
                    os.path.expanduser("~/.config/omnihub/logs"), "omniroute.log"
                )
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    handle = open(log_path, "ab", buffering=0)
                except OSError:
                    handle = subprocess.DEVNULL
                subprocess.Popen(
                    command,
                    cwd=self.omniroute_dir if os.path.isdir(self.omniroute_dir) else None,
                    stdout=handle,
                    stderr=handle,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                # Wait (bounded) for the gateway to answer.
                deadline = time.time() + 25
                while time.time() < deadline and not self._cancel.is_set():
                    if self._is_running():
                        self.result.emit(True, "Gateway started and responding.")
                        return
                    time.sleep(1.0)
                self.result.emit(True, "Start signal dispatched — the gateway is still warming up.")
                return

            if self.action == "stop":
                self._kill_processes()
                self.result.emit(True, "Gateway processes stopped.")
                return

            if self.action == "restart":
                self._kill_processes()
                command = self._launch_command()
                if not command:
                    self.result.emit(False, "No start script or 'omniroute' CLI was found on this machine.")
                    return
                log_path = os.path.join(
                    os.path.expanduser("~/.config/omnihub/logs"), "omniroute.log"
                )
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    handle = open(log_path, "ab", buffering=0)
                except OSError:
                    handle = subprocess.DEVNULL
                subprocess.Popen(
                    command,
                    cwd=self.omniroute_dir if os.path.isdir(self.omniroute_dir) else None,
                    stdout=handle,
                    stderr=handle,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                deadline = time.time() + 25
                while time.time() < deadline and not self._cancel.is_set():
                    if self._is_running():
                        self.result.emit(True, "Gateway restarted successfully.")
                        return
                    time.sleep(1.0)
                self.result.emit(True, "Restart signal dispatched — the gateway is still warming up.")
                return

            self.result.emit(False, f"Unknown action: {self.action}")
        except Exception as exc:  # noqa: BLE001
            self.result.emit(False, f"{type(exc).__name__}: {exc}")


# ------------------------------------------------------------------- chat

class ChatWorker(QThread):
    """Stream a chat completion from the gateway."""

    chunk = pyqtSignal(str)
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(
        self,
        api,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._messages = messages
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._stop_event = threading.Event()
        self._collected: List[str] = []

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        started = time.perf_counter()
        try:
            events = self._api.chat_stream(
                self._messages,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stop_event=self._stop_event,
            )
            for event in events:
                kind = event.get("type")
                if kind == "delta":
                    text = event.get("text", "")
                    self._collected.append(text)
                    self.chunk.emit(text)
                elif kind == "done":
                    payload = event.get("payload") or {}
                    elapsed = time.perf_counter() - started
                    self.completed.emit({
                        "text": "".join(self._collected),
                        "elapsed": elapsed,
                        "usage": _extract_usage(payload),
                        "model": payload.get("model") if isinstance(payload, dict) else None,
                    })
                    return
                elif kind == "stopped":
                    self.stopped.emit()
                    return
                elif kind == "error":
                    self.failed.emit(str(event.get("message", "Unknown streaming error")))
                    return
            elapsed = time.perf_counter() - started
            self.completed.emit({
                "text": "".join(self._collected),
                "elapsed": elapsed,
                "usage": {},
                "model": None,
            })
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")


def _extract_usage(payload) -> Dict:
    if not isinstance(payload, dict):
        return {}
    usage = payload.get("usage")
    if isinstance(usage, dict):
        return usage
    return {}


# ----------------------------------------------------------- system sampler

class SystemSampler:
    """Collects host telemetry.

    Holds the per-process handles needed to compute meaningful CPU
    percentages, so it must be reused rather than recreated on every tick.
    """

    def __init__(self, top_process_count: int = 5) -> None:
        self.top_process_count = top_process_count
        self._processes: Dict[int, object] = {}
        self._last_net: Optional[Tuple[int, int, float]] = None
        self._net_history: List[Tuple[float, float]] = []
        self._cpu_history: List[float] = []

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _cpu_percent() -> float:
        try:
            import psutil

            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    @staticmethod
    def _per_core() -> List[float]:
        try:
            import psutil

            return [float(value) for value in psutil.cpu_percent(interval=None, percpu=True)]
        except Exception:
            return []

    # -- public API --------------------------------------------------------

    def sample(self) -> Dict:
        """Return a complete telemetry snapshot."""
        snapshot: Dict = {
            "cpu_percent": 0.0,
            "cpu_per_core": [],
            "cpu_count": 0,
            "load_average": (0.0, 0.0, 0.0),
            "mem_percent": 0.0,
            "mem_used": 0,
            "mem_total": 0,
            "swap_percent": 0.0,
            "disks": [],
            "net_rx_rate": 0.0,
            "net_tx_rate": 0.0,
            "net_history": list(self._net_history),
            "cpu_history": list(self._cpu_history),
            "top_processes": [],
            "uptime_seconds": 0,
            "host": {},
        }
        try:
            import psutil
        except ImportError:
            return snapshot

        try:
            snapshot["cpu_percent"] = self._cpu_percent()
            snapshot["cpu_per_core"] = self._per_core()
            snapshot["cpu_count"] = psutil.cpu_count(logical=True) or 0
        except Exception:
            pass

        self._cpu_history.append(snapshot["cpu_percent"])
        if len(self._cpu_history) > 120:
            del self._cpu_history[0]

        try:
            snapshot["load_average"] = os.getloadavg()
        except (OSError, AttributeError):
            pass

        try:
            memory = psutil.virtual_memory()
            snapshot["mem_percent"] = float(memory.percent)
            snapshot["mem_used"] = int(memory.used)
            snapshot["mem_total"] = int(memory.total)
            swap = psutil.swap_memory()
            snapshot["swap_percent"] = float(swap.percent)
        except Exception:
            pass

        try:
            for partition in psutil.disk_partitions(all=False):
                if not partition.mountpoint or not os.path.exists(partition.mountpoint):
                    continue
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                except (OSError, PermissionError):
                    continue
                if usage.total < 1024 ** 3:  # ignore tiny pseudo mounts
                    continue
                snapshot["disks"].append({
                    "device": partition.device,
                    "mount": partition.mountpoint,
                    "fstype": partition.fstype,
                    "used": int(usage.used),
                    "total": int(usage.total),
                    "percent": float(usage.percent),
                })
        except Exception:
            pass

        try:
            counters = psutil.net_io_counters()
            now = time.time()
            if self._last_net:
                last_rx, last_tx, last_time = self._last_net
                delta = max(0.001, now - last_time)
                rx_rate = max(0.0, (counters.bytes_recv - last_rx) / delta)
                tx_rate = max(0.0, (counters.bytes_sent - last_tx) / delta)
                snapshot["net_rx_rate"] = rx_rate
                snapshot["net_tx_rate"] = tx_rate
                self._net_history.append((rx_rate, tx_rate))
                if len(self._net_history) > 120:
                    del self._net_history[0]
            self._last_net = (counters.bytes_recv, counters.bytes_sent, now)
        except Exception:
            pass

        snapshot["net_history"] = list(self._net_history)

        try:
            snapshot["top_processes"] = self._top_processes(psutil)
        except Exception:
            pass

        try:
            snapshot["uptime_seconds"] = int(time.time() - psutil.boot_time())
        except Exception:
            pass

        snapshot["host"] = self._host_info()
        return snapshot

    def _top_processes(self, psutil) -> List[Dict]:
        entries: List[Dict] = []
        for process in psutil.process_iter(["pid", "name", "username", "memory_info"]):
            try:
                pid = process.info.get("pid")
                if pid is None:
                    continue
                proc = self._processes.get(pid)
                if proc is None or not proc.is_running():
                    proc = psutil.Process(pid)
                    try:
                        proc.cpu_percent(None)
                    except Exception:
                        continue
                    self._processes[pid] = proc
                    continue
                cpu = proc.cpu_percent(None)
                memory = process.info.get("memory_info")
                entries.append({
                    "pid": pid,
                    "name": process.info.get("name") or "?",
                    "user": process.info.get("username") or "",
                    "cpu": float(cpu),
                    "memory": float(memory.rss) if memory else 0.0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Drop handles for dead processes so the cache cannot grow forever.
        if len(self._processes) > 400:
            for pid in list(self._processes.keys()):
                if pid not in {entry["pid"] for entry in entries}:
                    self._processes.pop(pid, None)

        entries.sort(key=lambda item: item["cpu"], reverse=True)
        return entries[: self.top_process_count]

    @staticmethod
    def _host_info() -> Dict:
        import platform

        info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "python": platform.python_version(),
            "pretty_name": f"{platform.system()} {platform.release()}",
        }
        try:
            if platform.system() == "Linux" and os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("PRETTY_NAME="):
                            info["pretty_name"] = line.split("=", 1)[1].strip().strip('"')
                            break
            elif platform.system() == "Darwin":
                import subprocess
                out = subprocess.check_output(["sw_vers", "-productVersion"], text=True, stderr=subprocess.DEVNULL).strip()
                info["pretty_name"] = f"macOS {out}"
            elif platform.system() == "Windows":
                info["pretty_name"] = f"Windows {platform.release()} ({platform.version()})"
        except Exception:
            pass
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.lower().startswith("model name"):
                        info["cpu_model"] = line.split(":", 1)[1].strip()
                        break
        except OSError:
            pass
        return info
