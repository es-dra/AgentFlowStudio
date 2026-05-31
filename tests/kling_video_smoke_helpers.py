from __future__ import annotations

import json

import httpx

from narratocut.model_gateway.company_secrets import load_company_provider_secrets
from tests.provider_smoke_helpers import provider_config


class Completed:
    def __init__(self, *, stdout: bytes, stderr: bytes = b"", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def json_response(payload: dict) -> httpx.Response:
    return httpx.Response(
        200,
        content=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("GET", "https://api-beijing.klingai.com"),
    )


def curl_response(payload: dict) -> bytes:
    return b"HTTP/1.1 200 OK\r\nContent-Type: application/json;charset=UTF-8\r\n\r\n" + json.dumps(payload).encode(
        "utf-8"
    )


def store(tmp_path):
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")
    return load_company_provider_secrets(config_path)
