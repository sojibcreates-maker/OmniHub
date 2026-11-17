"""HTTP client for the local OmniRoute gateway.

The client is intentionally defensive: every call has a short timeout, returns
structured results instead of raising, and never assumes a particular payload
shape (the gateway evolves).  Chat completions support both buffered and
Server-Sent-Events streaming responses.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - dependency guard
    requests = None  # type: ignore

__all__ = ["OmniRouteClient", "ApiError"]


class ApiError(RuntimeError):
    """Raised for unrecoverable client problems (missing dependency)."""


DEFAULT_BASE_URL = "http://localhost:20128"


class OmniRouteClient:
    """Small, thread-safe façade over the OmniRoute HTTP API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "local",
        timeout: int = 60,
    ) -> None:
        if requests is None:  # pragma: no cover
            raise ApiError("The 'requests' package is required by OmniHub.")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or "local"
        self.timeout = max(3, int(timeout or 60))
        self._local = threading.local()
        self._generation = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------ internals

    @property
    def _session(self):
        """A per-thread HTTP session.

        ``requests.Session`` is not thread-safe, and OmniHub talks to the
        gateway from the health poller, the model loader and the streaming
        chat worker at the same time.  Each thread therefore gets its own
        session, all sharing one connection pool so connections are still
        reused across the app.
        """
        session = getattr(self._local, "session", None)
        generation = getattr(self._local, "generation", -1)
        if session is None or generation != self._generation:
            session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=8,
                pool_maxsize=8,
                max_retries=0,
                pool_block=False,
            )
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            self._local.session = session
            self._local.generation = self._generation
        return session

    def configure(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[int] = None) -> None:
        if base_url is not None:
            new_base = (base_url or DEFAULT_BASE_URL).rstrip("/")
            if new_base != self.base_url:
                self.base_url = new_base
                self._reset_sessions()
        if api_key is not None:
            self.api_key = api_key or "local"
        if timeout is not None:
            self.timeout = max(3, int(timeout))

    def _reset_sessions(self) -> None:
        """Invalidate every thread's session after a base-URL change."""
        with self._lock:
            self._generation += 1
        session = getattr(self._local, "session", None)
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        self._local.session = None

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OmniHub/3.0",
        }
        if extra:
            headers.update(extra)
        return headers

    def url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    # ------------------------------------------------------------- requests

    def get(self, path: str, timeout: Optional[float] = None, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        """Perform a GET request. Returns ``(ok, payload)``."""
        try:
            response = self._session.get(
                self.url(path),
                headers=self._headers(),
                params=params,
                timeout=timeout or min(self.timeout, 10),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            return False, _describe_exception(exc)
        return _interpret(response)

    def post(self, path: str, payload: Dict[str, Any], timeout: Optional[float] = None) -> Tuple[bool, Any]:
        """Perform a JSON POST request. Returns ``(ok, payload)``."""
        try:
            response = self._session.post(
                self.url(path),
                headers=self._headers(),
                json=payload,
                timeout=timeout or self.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            return False, _describe_exception(exc)
        return _interpret(response)

    # --------------------------------------------------------------- health

    def health(self, timeout: float = 2.5) -> Tuple[bool, Dict[str, Any]]:
        """Probe the gateway health endpoint.

        Returns ``(ok, info)`` where ``info`` always carries a ``latency_ms``
        and ``status`` key so the UI never has to special-case failures.
        """
        started = time.perf_counter()
        try:
            response = self._session.get(
                self.url("/api/monitoring/health"),
                headers=self._headers({"Accept": "application/json"}),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - started) * 1000
            return False, {
                "status": "offline",
                "latency_ms": 0,
                "error": _describe_exception(exc, self.base_url),
            }

        elapsed = (time.perf_counter() - started) * 1000
        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:400]}
        if not isinstance(payload, dict):
            payload = {"data": payload}

        info = dict(payload)
        info["latency_ms"] = int(elapsed)
        info["http_status"] = response.status_code
        ok = response.status_code < 400
        status = str(info.get("status", "ok" if ok else "error")).lower()
        info["status"] = status
        if ok and status in ("ok", "healthy", "pass", "degraded", "unknown"):
            # 'degraded' still means the gateway is reachable.
            info["reachable"] = True
        else:
            info["reachable"] = ok and status not in ("down", "unhealthy", "critical", "failed")
            if not info["reachable"]:
                ok = False
        return ok, info

    # --------------------------------------------------------------- models

    def models(self, timeout: float = 12.0) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Fetch the catalogue of available models.

        Returns ``(ok, models, reason)``.  The catalogue endpoint requires a
        registered gateway key, so a clear reason is returned when it cannot
        be read rather than a bare failure.
        """
        ok, payload = self.get("/v1/models", timeout=timeout)
        if not ok:
            reason = str(payload)
            if "invalid_api_key" in reason or "Invalid API key" in reason:
                reason = (
                    "This gateway requires a registered access key for the model "
                    "catalogue. Add one in Settings, or create one in the OmniRoute dashboard."
                )
            elif "Authentication required" in reason:
                reason = "The model catalogue requires authentication."
            return False, [], reason

        models: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            raw = payload.get("data") or payload.get("models") or []
            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, str):
                        models.append({"id": entry})
                    elif isinstance(entry, dict) and entry.get("id"):
                        models.append(entry)
        return True, models, ""

    def providers(self, timeout: float = 12.0) -> Tuple[bool, List[Dict[str, Any]]]:
        """Fetch provider connectivity information when exposed by the API."""
        ok, payload = self.get("/v1/providers", timeout=timeout)
        if not ok:
            return False, []
        providers: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            raw = payload.get("data") or payload.get("providers") or []
            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict):
                        providers.append(entry)
        return True, providers

    # ----------------------------------------------------------------- chat

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run a buffered chat completion."""
        payload: Dict[str, Any] = {"model": model or "auto", "messages": messages, "stream": False}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        ok, response = self.post("/v1/chat/completions", payload, timeout=timeout)
        if not ok:
            return False, {"error": response}
        if isinstance(response, dict) and response.get("error"):
            error = response["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            return False, {"error": str(message)}
        return True, response if isinstance(response, dict) else {"content": str(response)}

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield streaming chat events.

        Each yielded item is a dict with a ``type`` key:
        ``delta`` (incremental text), ``done`` (final payload) or
        ``error`` (failure description).
        """
        payload: Dict[str, Any] = {"model": model or "auto", "messages": messages, "stream": True}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = None
        try:
            response = self._session.post(
                self.url("/v1/chat/completions"),
                headers=self._headers({"Accept": "text/event-stream"}),
                json=payload,
                timeout=timeout or self.timeout,
                stream=True,
            )
            if response.status_code >= 400:
                detail = response.text[:500]
                yield {"type": "error", "message": f"HTTP {response.status_code}: {detail}"}
                return

            saw_event = False
            for raw_line in response.iter_lines(decode_unicode=True):
                if stop_event is not None and stop_event.is_set():
                    yield {"type": "stopped"}
                    return
                if raw_line is None:
                    continue
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue

                if isinstance(chunk, dict):
                    error = chunk.get("error")
                    if error:
                        message = error.get("message") if isinstance(error, dict) else str(error)
                        yield {"type": "error", "message": str(message)}
                        return
                    if chunk.get("id") == "chatcmpl-keepalive":
                        # Gateway keep-alive while a provider is being chosen.
                        continue

                saw_event = True
                delta = _extract_delta(chunk)
                if delta:
                    yield {"type": "delta", "text": delta}
                else:
                    yield {"type": "raw", "payload": chunk}

            if not saw_event:
                # The gateway ignored `stream: true` and replied with one body.
                try:
                    body = response.json()
                except Exception:
                    body = None
                if isinstance(body, dict):
                    content = _extract_content(body)
                    if content:
                        yield {"type": "delta", "text": content}
                        yield {"type": "done", "payload": body}
                        return
            yield {"type": "done", "payload": {}}
        except Exception as exc:  # noqa: BLE001
            if stop_event is not None and stop_event.is_set():
                yield {"type": "stopped"}
                return
            yield {"type": "error", "message": _describe_exception(exc)}
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass


# ------------------------------------------------------------------ helpers

def _describe_exception(exc: Exception, base_url: str = DEFAULT_BASE_URL) -> str:
    """Turn an exception into a friendly one-line message."""
    name = type(exc).__name__
    if name == "ConnectionError":
        return f"Cannot reach the gateway at {base_url}. Is OmniRoute running?"
    if name == "Timeout":
        return f"The gateway at {base_url} did not respond in time."
    if name == "TooManyRedirects":
        return "The gateway redirected too many times."
    text = str(exc).strip()
    if not text:
        return name
    return text


def _interpret(response) -> Tuple[bool, Any]:
    """Turn an HTTP response into ``(ok, payload)``."""
    status = response.status_code
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:600]}
    if status >= 400:
        message = payload
        if isinstance(payload, dict):
            message = payload.get("error") or payload.get("message") or payload
        if isinstance(message, dict):
            message = message.get("message") or str(message)
        return False, f"HTTP {status}: {message}"
    return True, payload


def _extract_delta(chunk: Any) -> str:
    """Pull incremental text out of an SSE chunk.

    Handles the OpenAI chat-completion shape, the Anthropic message shape
    and plain text deltas, so the studio works with whichever provider the
    router picked.
    """
    if not isinstance(chunk, dict):
        return ""

    choices = chunk.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            delta = first.get("delta")
            if isinstance(delta, dict):
                content = delta.get("content")
                if isinstance(content, str):
                    return content
                reasoning = delta.get("reasoning_content")
                if isinstance(reasoning, str):
                    return reasoning
                text = delta.get("text")
                if isinstance(text, str):
                    return text
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
            text = first.get("text")
            if isinstance(text, str):
                return text

    # Anthropic-style events.
    delta = chunk.get("delta")
    if isinstance(delta, dict):
        text = delta.get("text")
        if isinstance(text, str):
            return text

    content_block = chunk.get("content_block")
    if isinstance(content_block, dict):
        text = content_block.get("text")
        if isinstance(text, str):
            return text

    return ""


def _extract_content(body: Dict[str, Any]) -> str:
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
            text = first.get("text")
            if isinstance(text, str):
                return text
    return ""
