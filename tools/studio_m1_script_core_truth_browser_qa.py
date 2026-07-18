from __future__ import annotations

import argparse
import json
import os
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

from studio_asset_context_browser_qa_support import chrome_path, free_port, stop_runtime, wait_for_http
from studio_asset_context_browser_qa_support import runtime_test_client


ANALYSIS_CANDIDATE_SCHEMA_VERSION = "afs.structured_analysis_candidate.v0.1"
PROJECT_ID = f"studio-script-core-truth-browser-qa-{int(time.time())}"
SCRIPT_TEXT = "Ari enters the Archive. Bo waits outside."


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-script-core-truth-")).resolve()
    report_path = Path(args.report or f"/tmp/{PROJECT_ID}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/{PROJECT_ID}-screens").resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    prepare_empty_project(runtime_root)

    server = start_gate_closed_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, base_url, screenshot_dir, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Studio M1 ScriptRevision and Core Asset truth browser QA.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args()


def prepare_empty_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "Script core truth browser QA"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {created.status_code} {created.text}")
    state = {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "Script Core Truth QA",
            "canvasName": "QA Canvas",
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
    }
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state setup failed: {saved.status_code} {saved.text}")


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


def run_browser_qa(repo: Path, base_url: str, screenshot_dir: Path, headed: bool, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            viewports: dict[str, Any] = {}
            for viewport in ({"width": 1440, "height": 900}, {"width": 1024, "height": 768}):
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on(
                    "response",
                    lambda response: response_errors.append({"status": response.status, "url": response.url})
                    if response.status >= 400
                    else None,
                )
                page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
                page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=script-core-{viewport['width']}", wait_until="domcontentloaded")
                expect(page.locator("#product-shell-root")).to_be_visible()
                page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
                expect(page.locator("#canvas-root")).to_be_visible()
                expect(page.locator(".studio-agent-chat")).to_be_visible()
                viewport_key = f"{viewport['width']}x{viewport['height']}"
                viewports[viewport_key] = assert_default_canvas(page, viewport)
                screenshots[viewport_key] = str((screenshot_dir / f"{viewport_key}.png").resolve())
                page.screenshot(path=screenshots[viewport_key], full_page=True)
                page.close()

            interaction_page = browser.new_page(viewport={"width": 1440, "height": 900})
            interaction_page.set_default_timeout(timeout_ms)
            expect.set_options(timeout=timeout_ms)
            interaction_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            interaction_page.on(
                "response",
                lambda response: response_errors.append({"status": response.status, "url": response.url})
                if response.status >= 400
                else None,
            )
            interaction_page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
            interaction_page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))
            interaction_page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=script-core-interaction", wait_until="domcontentloaded")
            interaction = assert_script_core_truth_interaction(interaction_page, base_url)
            screenshots["interaction"] = str((screenshot_dir / "interaction.png").resolve())
            interaction_page.screenshot(path=screenshots["interaction"], full_page=True)
            interaction_page.close()
        finally:
            browser.close()

    actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable_response_errors:
        raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
    return {
        "artifact_type": "studio_m1_script_core_truth_browser_qa_report",
        "schema_version": "0.1.0",
        "status": "passed",
        "project_id": PROJECT_ID,
        "base_url": base_url,
        "screenshots": screenshots,
        "viewports": viewports,
        "interaction": interaction,
        "console_error_count": len(console_errors),
        "response_error_count": len(actionable_response_errors),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        "non_claims": [
            "browser/runtime verification only",
            "not provider script understanding",
            "not media generation",
            "not complete auto production chain",
            "not human acceptance",
            "not business validation",
        ],
    }


def assert_default_canvas(page: Page, viewport: dict[str, int]) -> dict[str, Any]:
    snapshot = page.evaluate(
        """
        () => {
          const root = document.querySelector("#product-shell-root");
          const agent = document.querySelector(".studio-agent-chat");
          const bodyText = document.body.textContent || "";
          const rect = agent?.getBoundingClientRect();
          return {
            view: root?.dataset.view || "",
            canvasVisible: Boolean(document.querySelector("#canvas-root")),
            agentVisible: Boolean(agent && getComputedStyle(agent).display !== "none"),
            agentRightDocked: Boolean(rect && rect.width >= 48 && rect.right <= window.innerWidth + 1 && rect.left > window.innerWidth * 0.55),
            emptyFacts: bodyText.includes("0 场景") && bodyText.includes("0 镜头") && bodyText.includes("0 节点"),
            fixtureLeak: ["巷口", "雨巷", "老宅", "4x15", "4×15"].some((item) => bodyText.includes(item)),
          };
        }
        """
    )
    problems: list[str] = []
    if snapshot["view"] != "canvas":
        problems.append(f"default view is {snapshot['view']!r}")
    if not snapshot["canvasVisible"]:
        problems.append("canvas is not visible")
    if not snapshot["agentVisible"] or not snapshot["agentRightDocked"]:
        problems.append("Agent Chat is not fixed on the right")
    if not snapshot["emptyFacts"]:
        problems.append("empty canvas did not report zero facts")
    if snapshot["fixtureLeak"]:
        problems.append("fixture text leaked into empty project")
    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    readonly = page.evaluate("() => (document.body.textContent || '').includes('故事板当前只读取画布确认后的事实')")
    if not readonly:
        problems.append("storyboard did not remain read-only")
    page.get_by_role("tab", name="画布").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
    if problems:
        raise AssertionError(f"{viewport['width']}x{viewport['height']}: " + "; ".join(problems))
    return {"canvas_default": True, "agent_chat_right_panel": True, "empty_project": True, "storyboard_read_only": True}


def assert_script_core_truth_interaction(page: Page, base_url: str) -> dict[str, Any]:
    expect(page.locator("#canvas-root")).to_be_visible()
    composer = page.locator(".agent-chat-composer textarea")
    expect(composer).to_be_visible()
    composer.fill(f"/script-revision {SCRIPT_TEXT}")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    expect(page.locator(".agent-command-preview").filter(has_text="ScriptRevision")).to_be_visible()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").filter(has_text="ScriptRevision 已创建")).to_be_visible()
    page.wait_for_function("document.querySelectorAll('.node').length >= 1")
    expect(page.locator(".node").filter(has_text="分析：待分析")).to_be_visible()

    truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    revision = truth["projection"]["current_revision"]
    submit_candidate(base_url, revision)

    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/refresh-script-truth")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    expect(page.locator(".agent-command-preview").filter(has_text="Script/Core Asset Truth")).to_be_visible()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".node").filter(has_text="Ari")).to_be_visible()
    expect(page.locator(".node").filter(has_text="Archive")).to_be_visible()
    expect(page.locator(".node").filter(has_text="pending_confirmation").first).to_be_visible()

    character = page.locator(".node").filter(has_text="Ari").first
    character.click()
    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/merge-alias A")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    expect(page.locator(".agent-command-preview").filter(has_text="合并角色别名")).to_be_visible()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".node").filter(has_text="aliases: A")).to_be_visible()
    page.get_by_role("button", name="撤销").click()
    page.wait_for_function(
        "() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('aliases: A'))"
    )

    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/manual-prop brass key")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    expect(page.locator(".agent-command-preview").filter(has_text="手动 Prop")).to_be_visible()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".node").filter(has_text="brass key")).to_be_visible()
    page.get_by_role("button", name="撤销").click()
    page.wait_for_function(
        "() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('brass key'))"
    )

    character = page.locator(".node").filter(has_text="Ari").first
    character.click()
    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/retire-selected-asset")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".node").filter(has_text="status: retired")).to_be_visible()
    page.locator(".node").filter(has_text="Ari").first.click()
    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/restore-selected-asset")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    page.get_by_role("button", name="确认执行").click()
    expect(page.locator(".node").filter(has_text="status: confirmed")).to_be_visible()

    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    composer = page.locator(".agent-chat-composer textarea")
    composer.fill("/manual-prop storyboard blocked")
    page.get_by_role("button", name="发送到 Agent Chat").click()
    expect(page.locator(".agent-command-preview.blocked").filter(has_text="故事板是只读投影")).to_be_visible()

    final_truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    projection = final_truth["projection"]
    return {
        "script_revision_created": True,
        "analysis_required_visible": True,
        "confirmed_and_pending_assets_visible": True,
        "manual_prop_confirm_and_undo": True,
        "edit_retire_restore_alias_command_lifecycle": True,
        "storyboard_read_only_blocks_write": True,
        "asset_counts": projection["asset_counts"],
        "provider_dispatch_count": final_truth["provider_dispatch_count"],
        "remote_dispatch_count": final_truth["remote_dispatch_count"],
    }


def submit_candidate(base_url: str, revision: dict[str, Any]) -> None:
    body = {
        "project_id": PROJECT_ID,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
        "named_characters": [
            {"display_name": "Ari", "aliases": [], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Ari")], "confidence": 0.94, "status": "candidate"},
            {"display_name": "Bo", "aliases": [], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Bo")], "confidence": 0.72, "status": "candidate"},
        ],
        "main_scenes": [
            {"name": "Archive", "evidence_spans": [span(SCRIPT_TEXT, "Archive")], "confidence": 0.74, "status": "candidate"},
        ],
        "style": "observational",
        "genre": "short drama",
        "tone": "curious",
        "actions": ["enters"],
        "events": ["meeting delayed"],
        "beats": [{"summary": "arrival"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    http_json(
        f"{base_url}/projects/{PROJECT_ID}/script-revisions/{revision['revision_id']}/analysis-candidates",
        method="POST",
        payload=body,
    )


def span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {exc.code} from {url}: {body}") from exc


def make_worktree_studio_static_route(repo: Path):
    studio_root = (repo / "apps" / "studio").resolve()

    def route_studio_static(route: Any) -> None:
        parsed = urlsplit(route.request.url)
        relative = unquote(parsed.path.removeprefix("/studio/"))
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


def merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    lowered = {item.lower() for item in entries}
    for item in ("127.0.0.1", "localhost", "::1"):
        if item.lower() not in lowered:
            entries.append(item)
    return ",".join(entries)


if __name__ == "__main__":
    raise SystemExit(main())
