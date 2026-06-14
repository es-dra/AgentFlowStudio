from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


REMOTE_PROVIDER_GATES = ("AFS_ALLOW_REMOTE_IMAGE", "AFS_ALLOW_REMOTE_LLM", "AFS_ALLOW_REMOTE_ASR", "AFS_ALLOW_REMOTE_VIDEO")
MEDIA_PROVIDER_GATES = ("AFS_ALLOW_REMOTE_IMAGE", "AFS_ALLOW_REMOTE_ASR", "AFS_ALLOW_REMOTE_VIDEO")


def gates_to_close(*, allow_live_llm: bool = False) -> tuple[str, ...]:
    return MEDIA_PROVIDER_GATES if allow_live_llm else REMOTE_PROVIDER_GATES


def start_runtime(repo: Path, runtime_root: Path, port: int, *, allow_live_llm: bool = False) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_RUNTIME_SERVICE_PORT"] = str(port)
    for key in gates_to_close(allow_live_llm=allow_live_llm):
        env.pop(key, None)
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "runtime-service",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def stop_runtime(server: subprocess.Popen[str]) -> None:
    if server.poll() is not None:
        return
    server.terminate()
    try:
        server.wait(timeout=8)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=8)


def wait_for_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic only
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Runtime did not become ready at {url}: {last_error}")


def make_mutating_runtime_proxy(runtime_root: Path, *, allow_live_llm: bool = False):
    client = runtime_test_client(runtime_root)

    def proxy_mutating_runtime_request(route: Any) -> None:
        request = route.request
        if request.method not in {"POST", "PUT"}:
            route.continue_()
            return
        parsed = urlsplit(request.url)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        with remote_provider_gates_closed(allow_live_llm=allow_live_llm):
            response = client.request(
                request.method,
                path,
                content=(request.post_data or "").encode("utf-8"),
                headers={
                    "Content-Type": request.headers.get("content-type", "application/json"),
                    "Accept": request.headers.get("accept", "application/json"),
                },
            )
        route.fulfill(
            status=response.status_code,
            headers={"content-type": response.headers.get("content-type", "application/json")},
            body=response.content,
        )

    return proxy_mutating_runtime_request


@contextmanager
def remote_provider_gates_closed(*, allow_live_llm: bool = False):
    previous = {key: os.environ.get(key) for key in REMOTE_PROVIDER_GATES}
    try:
        for key in gates_to_close(allow_live_llm=allow_live_llm):
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def runtime_test_client(runtime_root: Path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=runtime_root))


def artifact_payload(client: TestClient, artifact_id: str) -> dict[str, Any]:
    response = client.get(f"/artifacts/{artifact_id}")
    assert response.status_code == 200
    return response.json()["payload"]


def fixed_visual_asset_record(runtime_root: Path, project_id: str) -> dict[str, Any]:
    records = list((runtime_root / "projects" / project_id / "visual_assets").glob("*/visual_asset.json"))
    assert len(records) == 1
    return json.loads(records[0].read_text(encoding="utf-8-sig"))


def chrome_path() -> str | None:
    configured = os.environ.get("CHROME_PATH")
    if configured:
        return configured
    for candidate in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    if shutil.which("chrome"):
        return shutil.which("chrome")
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
