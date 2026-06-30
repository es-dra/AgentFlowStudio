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
from urllib.request import ProxyHandler, build_opener

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
    env["AFS_RUNTIME_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_RUNTIME_SERVICE_PORT"] = str(port)
    env["NO_PROXY"] = _merge_no_proxy(env.get("NO_PROXY"))
    env["no_proxy"] = _merge_no_proxy(env.get("no_proxy"))
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
    opener = build_opener(ProxyHandler({}))
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with opener.open(url, timeout=1.5) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic only
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Runtime did not become ready at {url}: {last_error}")


def _merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    required = ("127.0.0.1", "localhost", "::1")
    lowered = {item.lower() for item in entries}
    for item in required:
        if item.lower() not in lowered:
            entries.append(item)
    return ",".join(entries)


def make_mutating_runtime_proxy(runtime_root: Path, *, allow_live_llm: bool = False):
    client = runtime_test_client(runtime_root)

    def proxy_mutating_runtime_request(route: Any) -> None:
        request = route.request
        if request.method not in {"POST", "PUT"}:
            route.continue_()
            return
        parsed = urlsplit(request.url)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        with browser_qa_provider_context(allow_live_llm=allow_live_llm):
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


def make_studio_static_route(repo: Path):
    studio_root = (repo / "apps" / "studio").resolve()

    def route_studio_static(route: Any) -> None:
        parsed = urlsplit(route.request.url)
        relative = parsed.path.removeprefix("/studio/").replace("/", "\\")
        path = (studio_root / relative).resolve()
        try:
            path.relative_to(studio_root)
        except ValueError:
            route.fulfill(status=404, body=b"")
            return
        if not path.is_file():
            route.fulfill(status=404, body=b"")
            return
        content_type = "text/javascript; charset=utf-8" if path.suffix.lower() == ".js" else "text/css; charset=utf-8"
        route.fulfill(status=200, content_type=content_type, body=path.read_bytes())

    return route_studio_static


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


@contextmanager
def browser_qa_provider_context(*, allow_live_llm: bool = False):
    stub_llm = os.environ.get("AFS_BROWSER_QA_STUB_LLM", "").strip().lower() in {"1", "true", "yes", "on"}
    if not stub_llm:
        with remote_provider_gates_closed(allow_live_llm=allow_live_llm):
            yield
        return

    import apps.api.runtime_llm_enhancement as llm_enhancement

    previous_loader = llm_enhancement.load_provider_registry
    previous_gates = {key: os.environ.get(key) for key in REMOTE_PROVIDER_GATES}
    try:
        os.environ["AFS_ALLOW_REMOTE_LLM"] = "true"
        for key in MEDIA_PROVIDER_GATES:
            os.environ.pop(key, None)
        llm_enhancement.load_provider_registry = lambda: BrowserQaFakeLLMRegistry()  # type: ignore[assignment]
        yield
    finally:
        llm_enhancement.load_provider_registry = previous_loader  # type: ignore[assignment]
        for key, value in previous_gates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class BrowserQaFakeLLMRegistry:
    def __init__(self) -> None:
        self._descriptors = {"prompt_optimizer": _FakeDescriptor("llm")}

    def dispatch(self, capability: str, service_id: str, request: Any) -> dict[str, str]:
        if capability != "llm" or service_id != "prompt_optimizer":
            from agentflow_studio.model_gateway.errors import ModelGatewayError

            raise ModelGatewayError(f"Provider service not found: {service_id}")
        return {
            "text": "\n".join(
                [
                    "意图：生成一张用于短视频故事推进的电影感关键帧。",
                    "角色/主体：保持 Lin Wan 的角色身份、黑色短发、红色风衣和左眉疤痕清晰稳定。",
                    "场景/美术：雨夜天台、湿润地面和城市霓虹反光，环境信息服务人物状态。",
                    "动作/情节：人物站在天台边缘短暂停顿，准备进入下一段行动。",
                    "镜头/构图：竖构图中景，主体居中偏下，保留头肩和服装识别信息。",
                    "灯光：冷色雨夜环境光叠加红蓝霓虹边缘光，面部保持可读。",
                    "运动/时间推进：静态关键帧，暗示风雨和缓慢推进，不制造明显运动模糊。",
                    "连续性：延续上游固定角色资产的发型、服装、疤痕和色彩关系。",
                    "负面约束：不要水印，不要文字，不要身份漂移，不要多余人物。",
                ]
            )
        }


class _FakeDescriptor:
    def __init__(self, modality: str) -> None:
        self.modality = modality


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
