from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = f"studio-m3-zero-cost-browser-qa-{int(time.time())}"
SCRIPT_TEXT = "林夏在旧剧场排练最后一场独白，周澈带来一张被雨水打湿的票根，两人决定把沉默改成告别。"


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root_auto = not args.runtime_root
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m3-zero-cost-browser-")).resolve()
    report_path = Path(args.report or f"/tmp/{PROJECT_ID}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/{PROJECT_ID}-screens").resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    revision = prepare_project(runtime_root)

    server = start_gate_closed_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, base_url, screenshot_dir, revision, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)
        if runtime_root_auto:
            shutil.rmtree(runtime_root, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Studio M3.0 zero-cost knowledge/context browser QA.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def prepare_project(runtime_root: Path) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "M3 零付费上下文浏览器核验"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {created.status_code} {created.text}")
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": empty_studio_state()})
    if saved.status_code != 200:
        raise AssertionError(f"studio state setup failed: {saved.status_code} {saved.text}")
    revision = client.post(
        f"/projects/{PROJECT_ID}/script-revisions",
        json={"source_kind": "script", "source_text": SCRIPT_TEXT, "provenance": {"qa": "m3_zero_cost_browser"}},
    )
    if revision.status_code != 200:
        raise AssertionError(f"script revision setup failed: {revision.status_code} {revision.text}")
    return revision.json()["revision"]


def empty_studio_state() -> dict[str, Any]:
    return {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "M3 零付费核验",
            "canvasName": "制作画布",
            "seq": 1,
            "updated_at": "",
        },
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {},
        "edges": {},
        "groups": {},
        "assets": [],
        "order": [],
        "selection": {"nodeIds": [], "edgeId": None},
        "production": {},
        "ui": {},
    }


def start_gate_closed_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_RUNTIME_SERVICE_PORT"] = str(port)
    env["AFS_AUTH_ENABLED"] = "false"
    env["AFS_AUTH_ALLOW_OPEN_SIGNUP"] = "false"
    env["NO_PROXY"] = merge_no_proxy(env.get("NO_PROXY"))
    env["no_proxy"] = merge_no_proxy(env.get("no_proxy"))
    for key in (
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        env.pop(key, None)
    return subprocess.Popen(
        [sys.executable, "-m", "apps.cli.main", "runtime-service", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_browser_qa(repo: Path, base_url: str, screenshot_dir: Path, revision: dict[str, Any], headed: bool, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    viewports: dict[str, Any] = {}
    interaction: dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900}, {"width": 1024, "height": 768}):
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                attach_error_capture(page, console_errors, response_errors)
                install_static_routes(page, repo)
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=m3-zero-cost-{viewport['width']}", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
                expect(page.locator(".studio-agent-chat")).to_have_count(1)
                expect(page.locator(".agent-chat-composer textarea")).to_be_visible()
                key = f"{viewport['width']}x{viewport['height']}"
                viewports[key] = {
                    "canvas_view": page.locator("#product-shell-root").get_attribute("data-view"),
                    "agent_chat_count": page.locator(".studio-agent-chat").count(),
                    "composer_visible": page.locator(".agent-chat-composer textarea").is_visible(),
                }
                screenshots[f"default-{key}"] = str((screenshot_dir / f"default-{key}.png").resolve())
                page.screenshot(path=screenshots[f"default-{key}"], full_page=True)
                page.close()

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(timeout_ms)
            expect.set_options(timeout=timeout_ms)
            attach_error_capture(page, console_errors, response_errors)
            install_static_routes(page, repo)
            page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=m3-zero-cost-interaction", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
            interaction = assert_m3_context_pack_lifecycle(page, base_url, revision)
            screenshots["interaction-1440x900"] = str((screenshot_dir / "interaction-1440x900.png").resolve())
            page.screenshot(path=screenshots["interaction-1440x900"], full_page=True)
            page.close()
        finally:
            browser.close()

    actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable_response_errors:
        raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
    audit_truth = http_json(f"{base_url}/projects/{PROJECT_ID}/m3-zero-cost/audit-truth")
    return {
        "artifact_type": "studio_m3_zero_cost_browser_qa_report",
        "schema_version": "0.1.0",
        "status": "passed",
        "project_id": PROJECT_ID,
        "base_url": base_url,
        "browser_path": "Playwright fallback; Browser plugin not available in this session",
        "screenshots": screenshots,
        "viewports": viewports,
        "interaction": interaction,
        "context_pack_count": audit_truth["projection"]["context_pack_count"],
        "current_context_pack_id": audit_truth["projection"]["current_context_pack_id"],
        "pending_feedback_not_memory": audit_truth["projection"]["pending_feedback_not_memory"],
        "console_error_count": len(console_errors),
        "response_error_count": len(actionable_response_errors),
        "provider_dispatch_count": audit_truth.get("provider_dispatch_count", 0),
        "remote_dispatch_count": audit_truth.get("remote_dispatch_count", 0),
        "non_claims": [
            "browser/runtime verification only",
            "not provider story planning",
            "not provider script understanding",
            "not media generation",
            "not owner acceptance",
            "not business validation",
        ],
    }


def assert_m3_context_pack_lifecycle(page: Page, base_url: str, revision: dict[str, Any]) -> dict[str, Any]:
    expect(page.locator(".studio-agent-chat")).to_have_count(1)
    composer = page.locator(".agent-chat-composer textarea").first
    expect(composer).to_be_visible()
    composer.fill("构建精准上下文包：专业审查当前剧本、分镜、资产和风险")
    page.locator(".agent-chat-composer button[aria-label='发送到 Agent Chat']").click()
    preview = page.locator(".agent-command-preview").first
    expect(preview).to_be_visible()
    expect(preview).to_contain_text("构建精准上下文包")
    visible_text = page.locator(".studio-agent-chat").inner_text()
    for forbidden in ("schema_version", "raw_command_text", "/m3-context-pack", "provider_dispatch_count"):
        if forbidden in visible_text:
            raise AssertionError(f"default Agent Chat leaked internal term: {forbidden}")
    page.locator(".agent-command-preview button", has_text="确认执行").click()
    expect(page.locator(".agent-receipt").first).to_contain_text("精准上下文包")
    audit_after_confirm = http_json(f"{base_url}/projects/{PROJECT_ID}/m3-zero-cost/audit-truth")
    if audit_after_confirm["projection"]["context_pack_count"] != 1:
        raise AssertionError("context pack did not persist after confirm")
    context_pack = audit_after_confirm["context_packs"][0]
    if context_pack["script_revision_id"] != revision["revision_id"] or context_pack["source_digest"] != revision["source_digest"]:
        raise AssertionError("context pack lost ScriptRevision/digest lineage")
    if len(context_pack["relevant_knowledge_refs"]) >= audit_after_confirm["knowledge_pack"]["entry_count"]:
        raise AssertionError("context pack injected the full knowledge pack")
    if any(context_pack["provider_gates"].values()):
        raise AssertionError("provider gate opened during browser QA")
    page.locator(".agent-receipt button", has_text="撤销").click()
    expect(page.locator(".agent-receipt").first).to_contain_text("已撤销")
    audit_after_undo = http_json(f"{base_url}/projects/{PROJECT_ID}/m3-zero-cost/audit-truth")
    if audit_after_undo["projection"]["current_context_pack_id"]:
        raise AssertionError("context pack undo did not clear current selection")
    return {
        "command_preview": "passed",
        "confirm_receipt": "passed",
        "undo": "passed",
        "context_pack_id": context_pack["context_pack_id"],
        "knowledge_refs": context_pack["relevant_knowledge_refs"],
        "knowledge_pack_entry_count": audit_after_confirm["knowledge_pack"]["entry_count"],
        "script_revision_id": context_pack["script_revision_id"],
        "provider_dispatch_count": audit_after_undo.get("provider_dispatch_count", 0),
        "remote_dispatch_count": audit_after_undo.get("remote_dispatch_count", 0),
    }


def attach_error_capture(page: Page, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    def on_response(response) -> None:
        if response.status >= 400:
            response_errors.append({"status": response.status, "url": response.url})

    page.on("response", on_response)


def install_static_routes(page: Page, repo: Path) -> None:
    page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
    page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))


def make_worktree_studio_static_route(repo: Path):
    def handler(route) -> None:
        request_path = unquote(urlsplit(route.request.url).path)
        if request_path.startswith("/studio/src/"):
            file_path = repo / "apps" / "studio" / "src" / request_path.removeprefix("/studio/src/")
        elif request_path.startswith("/studio/styles/"):
            file_path = repo / "apps" / "studio" / "styles" / request_path.removeprefix("/studio/styles/")
        else:
            route.fallback()
            return
        if not file_path.exists() or not file_path.is_file():
            route.abort()
            return
        content_type = "text/css" if file_path.suffix == ".css" else "application/javascript"
        route.fulfill(status=200, body=file_path.read_bytes(), content_type=content_type)

    return handler


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {url} failed: {exc.code} {body}") from exc


def merge_no_proxy(value: str | None) -> str:
    values = {part.strip() for part in (value or "").split(",") if part.strip()}
    values.update({"127.0.0.1", "localhost"})
    return ",".join(sorted(values))


if __name__ == "__main__":
    raise SystemExit(main())
