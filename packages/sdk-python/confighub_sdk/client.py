from __future__ import annotations

import json
import threading
from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from urllib import error, request

from .evaluator import evaluate_all_flags, evaluate_flag
from .types import ConfigJson, UserObject

DEFAULT_POLL_INTERVAL_SECONDS = 60
HttpResponse = Tuple[int, Mapping[str, str], bytes]
RequestFunction = Callable[[str, Mapping[str, str]], HttpResponse]


class ConfigHubClient:
    def __init__(
        self,
        sdk_key: str,
        *,
        base_url: str,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        on_config_changed: Optional[Callable[[ConfigJson], None]] = None,
        on_flag_evaluated: Optional[
            Callable[[str, Any, Optional[UserObject]], None]
        ] = None,
        request_fn: Optional[RequestFunction] = None,
    ) -> None:
        self._sdk_key = sdk_key
        self._base_url = base_url.rstrip("/")
        self._poll_interval_seconds = poll_interval_seconds
        self._on_config_changed = on_config_changed
        self._on_flag_evaluated = on_flag_evaluated
        self._request_fn = request_fn or self._default_request

        self._config: Optional[ConfigJson] = None
        self._config_etag: Optional[str] = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None

    @classmethod
    def create(
        cls,
        sdk_key: str,
        *,
        base_url: str,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        on_config_changed: Optional[Callable[[ConfigJson], None]] = None,
        on_flag_evaluated: Optional[
            Callable[[str, Any, Optional[UserObject]], None]
        ] = None,
        request_fn: Optional[RequestFunction] = None,
    ) -> "ConfigHubClient":
        client = cls(
            sdk_key,
            base_url=base_url,
            poll_interval_seconds=poll_interval_seconds,
            on_config_changed=on_config_changed,
            on_flag_evaluated=on_flag_evaluated,
            request_fn=request_fn,
        )
        client.force_refresh()
        client._start_polling()
        return client

    def get_value(
        self,
        key: str,
        default_value: Any,
        user: Optional[UserObject] = None,
    ) -> Any:
        with self._lock:
            config = self._config
        if config is None:
            return default_value

        setting = config.get("settings", {}).get(key)
        if setting is None:
            return default_value

        value = evaluate_flag(key, setting, user, config.get("segments", []))
        result = default_value if value is None else value
        if self._on_flag_evaluated is not None:
            self._on_flag_evaluated(key, result, user)
        return result

    def get_all_values(
        self,
        user: Optional[UserObject] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            config = self._config
        if config is None:
            return {}

        results = evaluate_all_flags(config, user)
        if self._on_flag_evaluated is not None:
            for key, value in results.items():
                self._on_flag_evaluated(key, value, user)
        return results

    def force_refresh(self) -> None:
        url = f"{self._base_url}/api/v1/sdk/{self._sdk_key}/config.json"
        headers: Dict[str, str] = {}
        with self._lock:
            if self._config_etag:
                headers["If-None-Match"] = self._config_etag

        status_code, response_headers, body = self._request_fn(url, headers)
        if status_code == 304:
            return
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(
                f"ConfigHub SDK: failed to fetch config (HTTP {status_code})"
            )

        new_config = json.loads(body.decode("utf-8"))
        new_etag = response_headers.get("ETag")

        with self._lock:
            changed = self._config != new_config
            self._config = new_config
            if new_etag:
                self._config_etag = new_etag

        if changed and self._on_config_changed is not None:
            self._on_config_changed(new_config)

    def get_config(self) -> Optional[ConfigJson]:
        with self._lock:
            return self._config

    def destroy(self) -> None:
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=0.2)
        with self._lock:
            self._config = None

    def _start_polling(self) -> None:
        if self._poll_interval_seconds <= 0 or self._poll_thread is not None:
            return

        def poll_loop() -> None:
            while not self._stop_event.wait(self._poll_interval_seconds):
                try:
                    self.force_refresh()
                except Exception:
                    continue

        self._poll_thread = threading.Thread(
            target=poll_loop,
            name="confighub-sdk-poller",
            daemon=True,
        )
        self._poll_thread.start()

    @staticmethod
    def _default_request(url: str, headers: Mapping[str, str]) -> HttpResponse:
        req = request.Request(url, headers=dict(headers), method="GET")
        try:
            with request.urlopen(req, timeout=10) as response:
                return response.status, dict(response.headers.items()), response.read()
        except error.HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()
