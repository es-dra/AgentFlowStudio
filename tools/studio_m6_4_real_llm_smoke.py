from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, start_runtime, stop_runtime, wait_for_http
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import create_blank_text_node, ensure_ai_open, fill_selected_text, selected_node_id


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_BASE = Path(
    "/home/afs-ops/.codex/afs-evidence/afs-m6-4-freeform-canvas-ai-copilot-20260722"
)
LLM_MODEL = "gpt-5.5"
LLM_REASONING_EFFORT = "medium"


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    run_root = Path(args.evidence_root or _default_run_root()).resolve()
    runtime_root = run_root / "runtime-root"
    screenshot_dir = run_root / "screenshots"
    run_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    provider_config = run_root / "provider-config.no-secrets.json"
    provider_config.write_text(json.dumps(_provider_config(), ensure_ascii=False, indent=2), encoding="utf-8")
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    previous_env = _apply_candidate_env(provider_config)
    server = start_runtime(repo, runtime_root, port, allow_live_llm=True)
    try:
        wait_for_http(f"{base_url}/health", timeout=45)
        report = run_smoke(base_url, run_root, screenshot_dir)
        report.update({
            "artifact_type": "afs_m6_4_real_runtime_llm_smoke",
            "schema_version": "afs.m6_4.real_runtime_llm_smoke.v0.1",
            "run_root": str(run_root),
            "provider_config": {
                "path_stored": "provider-config.no-secrets.json",
                "contains_secret_values": False,
                "service_id": "server_codex",
                "provider": "codex_local",
                "model": LLM_MODEL,
                "reasoning_effort": LLM_REASONING_EFFORT,
            },
            "production_provider_gates_changed": False,
            "image_video_generation_started": False,
            "external_paid_cost_usd": 0,
            "non_claims": [
                "not_owner_acceptance",
                "not_business_validation",
                "not_paid_image_video_smoke",
                "not_generated_media_qa",
                "not_public_release",
            ],
        })
        (run_root / "m6_4_real_llm_smoke_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps({
            "status": report["status"],
            "report": str(run_root / "m6_4_real_llm_smoke_report.json"),
            "provider_request_count": report["provider_request_count"],
            "browser_request_count": report["browser"]["provider_request_count"],
            "cost_usd": report["external_paid_cost_usd"],
        }, ensure_ascii=False))
        return 0 if report["status"] == "passed" else 1
    finally:
        stop_runtime(server)
        _restore_env(previous_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.4 real runtime LLM smoke for AI creative copilot")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--evidence-root", default="")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def run_smoke(base_url: str, run_root: Path, screenshot_dir: Path) -> dict[str, Any]:
    health = http_json("GET", f"{base_url}/health")
    if health["provider_gates"]["llm"] is not True:
        raise AssertionError(f"candidate runtime LLM gate not open: {health['provider_gates']}")
    for gate in ("image", "video", "audio", "vision", "asr", "external_download"):
        if health["provider_gates"].get(gate) is not False:
            raise AssertionError(f"non-LLM gate unexpectedly open: {health['provider_gates']}")
    project_id = f"m6-4-real-llm-{int(time.time())}"
    create_project(base_url, project_id)
    graph_before = graph(base_url, project_id)
    direct_started = time.perf_counter()
    direct = agent_chat(base_url, project_id, "你好", node_id="", summary={"nodes": 0, "section": "canvas"})
    direct_elapsed = round((time.perf_counter() - direct_started) * 1000, 2)
    assert_llm_response(direct, "direct_hello")
    graph_after_direct = graph(base_url, project_id)
    browser = run_browser_smoke(base_url, project_id, screenshot_dir)
    graph_after_browser = graph(base_url, project_id)
    requests = [direct, *browser["responses"]]
    graph_unchanged = (
        graph_before["graph_digest"] == graph_after_direct["graph_digest"] == graph_after_browser["graph_digest"]
        and graph_before["version"] == graph_after_direct["version"] == graph_after_browser["version"]
    )
    if not graph_unchanged:
        raise AssertionError("agent chat conversation mutated ProductionGraph")
    p0 = 0
    p1 = 0
    p2 = 0
    return {
        "status": "passed" if p0 == p1 == p2 == 0 else "failed",
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "health": {
            "status": health.get("status"),
            "provider_gates": health.get("provider_gates"),
            "local_only": health.get("local_only"),
            "auth_required": health.get("auth_required"),
        },
        "direct_http": {
            "message": "你好",
            "mode": direct["mode"],
            "provider_calls_started": direct["provider_calls_started"],
            "latency_ms": direct.get("latency_ms"),
            "wall_latency_ms": direct_elapsed,
            "reply_excerpt": direct["reply"][:180],
            "provider_lineage": _safe_lineage(direct),
        },
        "browser": browser,
        "graph_before": _graph_summary(graph_before),
        "graph_after_direct": _graph_summary(graph_after_direct),
        "graph_after_browser": _graph_summary(graph_after_browser),
        "graph_mutated": not graph_unchanged,
        "provider_request_count": sum(1 for item in requests if item.get("provider_calls_started") is True),
        "retry_count": 0,
        "timeout_count": 0,
        "request_modes": [item.get("mode") for item in requests],
        "request_latencies_ms": [item.get("latency_ms") for item in requests],
        "cost_usd": 0,
        "issue_ledger": [],
    }


def run_browser_smoke(base_url: str, project_id: str, screenshot_dir: Path) -> dict[str, Any]:
    responses: list[dict[str, Any]] = []
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(180_000)
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on(
                "response",
                lambda response: _capture_response(response, responses, response_errors),
            )
            page.goto(f"{base_url}/studio/?project={project_id}&qa=real-llm-{int(time.time())}", wait_until="networkidle")
            expect(page.locator("#product-shell-root")).to_be_visible()
            expect(page.locator("#canvas-root")).to_be_visible()
            ensure_ai_open(page, {"width": 1440, "height": 900})
            send_ai_real(page, "你好", responses, expected_count=1)
            expect(page.locator(".agent-chat-log")).not_to_contain_text("不会用本地固定回答冒充理解")
            screenshots["hello"] = screenshot(page, screenshot_dir, "browser-01-hello.png")
            create_blank_text_node(page, project_id)
            first_id = selected_node_id(page, project_id)
            fill_selected_text(page, "女孩在雨夜天台寻找失踪的哥哥，她必须在灯牌熄灭前找到线索。")
            ensure_ai_open(page, {"width": 1440, "height": 900})
            send_ai_real(page, "这个节点是什么", responses, expected_count=2)
            send_ai_real(page, "下一步建议是什么", responses, expected_count=3)
            screenshots["context_followup"] = screenshot(page, screenshot_dir, "browser-02-context-followup.png")
            if console_errors or response_errors:
                raise AssertionError(f"browser errors: console={console_errors[:4]} responses={response_errors[:4]}")
        finally:
            browser.close()
    if len(responses) < 3:
        raise AssertionError(f"expected at least 3 browser LLM responses, got {len(responses)}")
    for index, response in enumerate(responses[:3], start=1):
        assert_llm_response(response, f"browser_{index}")
        if response["graph_mutation"]["mutated"] is True:
            raise AssertionError(f"browser request mutated ProductionGraph: {response['graph_mutation']}")
    return {
        "messages": ["你好", "这个节点是什么", "下一步建议是什么"],
        "provider_request_count": sum(1 for item in responses[:3] if item.get("provider_calls_started") is True),
        "responses": responses[:3],
        "screenshots": screenshots,
        "console_error_count": 0,
        "response_error_count": 0,
        "selected_node_created_for_context": True,
    }


def send_ai_real(page: Page, text: str, responses: list[dict[str, Any]], *, expected_count: int) -> None:
    if not page.locator(".studio-agent-chat:not(.collapsed) .agent-chat-composer textarea").is_visible():
        ensure_ai_open(page, page.viewport_size or {"width": 1440, "height": 900})
    form = page.locator(".studio-agent-chat:not(.collapsed) .agent-chat-composer").last
    textarea = form.locator("textarea")
    button = form.get_by_role("button", name="发送到 AI 创作搭档")
    expect(textarea).to_be_visible()
    before_messages = page.locator(".agent-chat-log .agent-message").count()
    textarea.click()
    textarea.fill(text)
    expect(button).to_be_visible()
    button.click()
    page.wait_for_function(
        """before => {
          const messages = document.querySelectorAll('.agent-chat-log .agent-message').length;
          const loading = document.querySelector('.agent-conversation-status.loading');
          return messages >= before + 2 && !loading;
        }""",
        arg=before_messages,
        timeout=180_000,
    )
    deadline = time.time() + 180
    while len(responses) < expected_count and time.time() < deadline:
        page.wait_for_timeout(250)
    if len(responses) < expected_count:
        raise AssertionError(f"browser did not capture agent-chat/conversation response for {text!r}")


def _capture_response(response: Any, responses: list[dict[str, Any]], response_errors: list[dict[str, Any]]) -> None:
    url = response.url
    if response.status >= 400 and not url.endswith("/favicon.ico"):
        response_errors.append({"status": response.status, "url": _safe_url(url)})
    if not urlparse(url).path.endswith("/agent-chat/conversation"):
        return
    try:
        payload = response.json()
    except Exception:
        return
    responses.append(_safe_response_summary(payload))


def agent_chat(base_url: str, project_id: str, message: str, *, node_id: str, summary: dict[str, Any]) -> dict[str, Any]:
    return http_json(
        "POST",
        f"{base_url}/projects/{project_id}/agent-chat/conversation",
        {
            "message": message,
            "node_id": node_id,
            "canvas_summary": summary,
            "provider_service_id": "server_codex",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def create_project(base_url: str, project_id: str) -> None:
    response = http_json(
        "POST",
        f"{base_url}/projects",
        {
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": "M6.4 real LLM smoke",
            "status": "in_progress",
        },
    )
    if response.get("project", {}).get("project_id") not in {project_id, None}:
        raise AssertionError(f"unexpected project create response: {response}")


def graph(base_url: str, project_id: str) -> dict[str, Any]:
    return http_json("GET", f"{base_url}/projects/{project_id}/m4/production-graph")["graph"]


def http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    opener = build_opener(ProxyHandler({}))
    data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with opener.open(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {method} {_safe_url(url)} failed: {exc.code} {body[:600]}") from exc


def assert_llm_response(payload: dict[str, Any], label: str) -> None:
    if payload.get("mode") != "llm":
        raise AssertionError(f"{label} did not return llm mode: {payload.get('mode')} {payload.get('safe_manifest')}")
    if payload.get("provider_calls_started") is not True:
        raise AssertionError(f"{label} did not start provider")
    lineage = payload.get("provider_lineage") or {}
    if lineage.get("service_id") != "server_codex" or lineage.get("provider") != "codex_local":
        raise AssertionError(f"{label} used unexpected provider lineage: {lineage}")
    if not str(payload.get("reply") or "").strip():
        raise AssertionError(f"{label} returned empty reply")
    if payload.get("graph_mutation", {}).get("mutated") is True:
        raise AssertionError(f"{label} mutated graph")


def _safe_response_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": payload.get("mode"),
        "reply": str(payload.get("reply") or "")[:240],
        "provider_calls_started": payload.get("provider_calls_started") is True,
        "provider_lineage": _safe_lineage(payload),
        "graph_mutation": payload.get("graph_mutation") if isinstance(payload.get("graph_mutation"), dict) else {},
        "latency_ms": payload.get("latency_ms"),
        "cost_usd": payload.get("cost_usd", 0),
    }


def _safe_lineage(payload: dict[str, Any]) -> dict[str, Any]:
    lineage = payload.get("provider_lineage") if isinstance(payload.get("provider_lineage"), dict) else {}
    allowed = (
        "service_id",
        "provider",
        "model_surface",
        "request_id",
        "structured_output_contract_id",
        "structured_output_schema_digest",
        "provider_calls_started",
        "provider_raw_response_stored",
        "external_paid_cost_usd",
    )
    return {key: lineage.get(key) for key in allowed if key in lineage}


def _graph_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": payload.get("version"),
        "graph_digest": payload.get("graph_digest"),
        "node_count": len(payload.get("nodes") or {}),
        "relation_count": len(payload.get("relations") or []),
    }


def screenshot(page: Page, screenshot_dir: Path, filename: str) -> str:
    path = screenshot_dir / filename
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def _safe_url(value: str) -> str:
    parsed = urlparse(value)
    return parsed.path


def _provider_config() -> dict[str, Any]:
    descriptor = {
        "schema_version": "provider_descriptor.v0.1",
        "modality": "llm",
        "execution_mode": "sync",
        "capabilities": ["llm"],
        "account_pool_id": "server_codex_pool",
        "reference_image_slots": 0,
        "supported_aspect_ratios": ["1:1"],
        "prompt_char_limit": 12000,
        "seed_supported": False,
        "required_gate": "AFS_ALLOW_REMOTE_LLM",
    }
    return {
        "schema_version": "company_provider_secrets.v0.1",
        "accounts": {
            "server_codex_login": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "default_models": {"llm": "server-codex-login"},
                "cli_model": LLM_MODEL,
                "cli_reasoning_effort": LLM_REASONING_EFFORT,
                "timeout_sec": 120,
            }
        },
        "account_pools": {
            "server_codex_pool": {
                "accounts": [{
                    "account_id": "server_codex_login",
                    "service_id": "server_codex",
                    "enabled_capabilities": ["llm"],
                    "enabled": True,
                    "priority": 1,
                    "weight": 1,
                    "concurrency_limit": 1,
                    "health_state": "unknown",
                }]
            }
        },
        "services": {
            "server_codex": {
                "provider": "codex_local",
                "account_ref": "server_codex_login",
                "capability": "llm",
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "descriptor": descriptor,
            }
        },
    }


def _apply_candidate_env(provider_config: Path) -> dict[str, str | None]:
    keys = (
        "AFS_PROVIDER_CONFIG",
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
        "AFS_EXTERNAL_DOWNLOAD",
        "AFS_AUTH_ENABLED",
    )
    previous = {key: os.environ.get(key) for key in keys}
    os.environ["AFS_PROVIDER_CONFIG"] = str(provider_config)
    os.environ["AFS_ALLOW_REMOTE_LLM"] = "true"
    os.environ["AFS_AUTH_ENABLED"] = "false"
    for key in keys:
        if key not in {"AFS_PROVIDER_CONFIG", "AFS_ALLOW_REMOTE_LLM", "AFS_AUTH_ENABLED"}:
            os.environ.pop(key, None)
    return previous


def _restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _default_run_root() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(DEFAULT_EVIDENCE_BASE / f"{stamp}-real-runtime-llm-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
