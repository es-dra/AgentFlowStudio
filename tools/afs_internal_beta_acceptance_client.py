from __future__ import annotations

from typing import Any

import httpx


class HttpAcceptanceClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds, follow_redirects=True, trust_env=False)

    def get(self, path: str, *, headers: dict[str, str] | None = None):
        return self._client.get(path, headers=headers)

    def post(self, path: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        return self._client.post(path, json=json, headers=headers)

    def put(self, path: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        return self._client.put(path, json=json, headers=headers)

    def close(self) -> None:
        self._client.close()


class RuntimeTestClientAdapter:
    def __init__(self, client) -> None:
        self._client = client

    def get(self, path: str, *, headers: dict[str, str] | None = None):
        return self._client.get(path, headers=headers)

    def post(self, path: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        return self._client.post(path, json=json, headers=headers)

    def put(self, path: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        return self._client.put(path, json=json, headers=headers)

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
