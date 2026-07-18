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

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.runtime_dynamic_production_plan import (  # noqa: E402
    PROVIDER_CAPABILITY_SCHEMA_VERSION,
    STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
    story_plan_candidate_digest,
)


ANALYSIS_CANDIDATE_SCHEMA_VERSION = "afs.structured_analysis_candidate.v0.1"
PROJECT_ID = f"studio-canvas-ux-m21-browser-qa-{int(time.time())}"
SCRIPT_TEXT = "Mira calibrates the lens in the observatory. Tao opens the signal room as a distant signal arrives."


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-canvas-ux-m21-")).resolve()
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
    parser = argparse.ArgumentParser(description="Run Studio Canvas UX M2.1 single-shell browser QA.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def prepare_empty_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "Canvas UX M2.1 browser QA"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {created.status_code} {created.text}")
    state = {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "Canvas UX QA",
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
        "ui": {},
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
            for viewport in ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900}, {"width": 1024, "height": 768}):
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                attach_error_capture(page, console_errors, response_errors)
                install_static_routes(page, repo)
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=ux-m21-{viewport['width']}", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
                wait_for_empty_canvas_ready(page)
                viewport_key = f"{viewport['width']}x{viewport['height']}"
                viewports[viewport_key] = assert_single_shell_default(page, viewport)
                screenshots[f"default-{viewport_key}"] = str((screenshot_dir / f"default-{viewport_key}.png").resolve())
                page.screenshot(path=screenshots[f"default-{viewport_key}"], full_page=True)
                page.close()

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(timeout_ms)
            expect.set_options(timeout=timeout_ms)
            attach_error_capture(page, console_errors, response_errors)
            install_static_routes(page, repo)
            page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=ux-m21-interaction", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
            wait_for_empty_canvas_ready(page)
            interaction = assert_interactions(page, base_url)
            screenshots["interaction-1440x900"] = str((screenshot_dir / "interaction-1440x900.png").resolve())
            page.screenshot(path=screenshots["interaction-1440x900"], full_page=True)
            page.close()
        finally:
            browser.close()

    actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable_response_errors:
        raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
    final_plan = http_json(f"{base_url}/projects/{PROJECT_ID}/production-plan-truth")
    final_script = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    return {
        "artifact_type": "studio_canvas_ux_m2_1_browser_qa_report",
        "schema_version": "0.1.0",
        "status": "passed",
        "project_id": PROJECT_ID,
        "base_url": base_url,
        "screenshots": screenshots,
        "viewports": viewports,
        "interaction": interaction,
        "script_analysis_state": final_script["projection"]["analysis_state"],
        "planning_state": final_plan["projection"]["planning_state"],
        "shot_count": len(final_plan["projection"]["shots"]),
        "chunk_count": len(final_plan["projection"]["chunks"]),
        "console_error_count": len(console_errors),
        "response_error_count": len(actionable_response_errors),
        "provider_dispatch_count": final_plan.get("provider_dispatch_count", 0) + final_script.get("provider_dispatch_count", 0),
        "remote_dispatch_count": final_plan.get("remote_dispatch_count", 0) + final_script.get("remote_dispatch_count", 0),
        "non_claims": [
            "browser/runtime verification only",
            "not provider story planning",
            "not media generation",
            "not complete auto production chain",
            "not creative quality assurance",
            "not owner acceptance",
            "not business validation",
        ],
    }


def attach_error_capture(page: Page, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on(
        "response",
        lambda response: response_errors.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )


def install_static_routes(page: Page, repo: Path) -> None:
    page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
    page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))


def assert_single_shell_default(page: Page, viewport: dict[str, int]) -> dict[str, Any]:
    expect(page.locator("#canvas-root")).to_be_visible()
    snapshot = page.evaluate(
        """
        () => {
          const text = document.body.textContent || "";
          const root = document.querySelector("#product-shell-root");
          const workspace = document.querySelector(".studio-unified-workspace");
          const agent = document.querySelector(".studio-agent-chat");
          const canvas = document.querySelector("#canvas-root");
          const stage = document.querySelector(".canvas-workspace-stage");
          const agentRect = agent?.getBoundingClientRect();
          const canvasRect = canvas?.getBoundingClientRect();
          const stageRect = stage?.getBoundingClientRect();
          const rail = document.querySelector(".studio-scene-rail");
          return {
            view: root?.dataset.view || "",
            legacyShellCount: document.querySelectorAll("#topbar,#drawer,#inspector,#dock,#starter-row,#sprite-root").length,
            agentCount: document.querySelectorAll(".studio-agent-chat").length,
            sceneRailVisible: Boolean(rail && getComputedStyle(rail).display !== "none"),
            canvasVisible: Boolean(canvas && getComputedStyle(canvas).display !== "none"),
            emptyVisible: Boolean(document.querySelector("#canvas-empty-hint:not([hidden])")),
            nodeCount: document.querySelectorAll(".node").length,
            zoomText: document.querySelector("#corner-controls .zoom-label")?.textContent || "",
            agentVisible: Boolean(agent && getComputedStyle(agent).display !== "none"),
            agentRight: agentRect ? Math.round(agentRect.right) : 0,
            viewportRight: window.innerWidth,
            canvasWidth: canvasRect ? Math.round(canvasRect.width) : 0,
            stageWithinViewport: Boolean(stageRect && stageRect.left >= -1 && stageRect.right <= window.innerWidth + 1),
            noHorizontalScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
            noDuplicateOpenButton: !text.includes("打开 Agent Chat"),
            fakeCardLeak: ["故事到关键帧", "角色设定卡", "首帧到视频", "视频片段复用"].some((item) => text.includes(item)),
            rawDefaultLeak: ["studio-state-", "planning_required", "{json}", "Story Plan Candidate JSON"].some((item) => text.includes(item)),
            counts: ["节点", "场景", "镜头"].every((item) => text.includes(item)) && text.includes("0"),
          };
        }
        """
    )
    problems: list[str] = []
    if snapshot["view"] != "canvas":
        problems.append(f"default view is {snapshot['view']!r}")
    if snapshot["legacyShellCount"]:
        problems.append(f"legacy shell nodes present: {snapshot['legacyShellCount']}")
    if snapshot["agentCount"] != 1 or not snapshot["agentVisible"]:
        problems.append("Agent Chat is not the single visible dock")
    if viewport["width"] >= 1180 and abs(snapshot["agentRight"] - snapshot["viewportRight"]) > 2:
        problems.append("Agent Chat is not docked at the right edge")
    if snapshot["sceneRailVisible"]:
        problems.append("canvas view shows a permanent scene rail")
    if not snapshot["canvasVisible"] or snapshot["canvasWidth"] < 520:
        problems.append("canvas does not own the remaining workspace")
    if not snapshot["emptyVisible"] or snapshot["nodeCount"] != 0 or not snapshot["counts"]:
        problems.append("zero-node empty state is not true empty")
    if snapshot["zoomText"] != "100%":
        problems.append(f"empty canvas zoom was {snapshot['zoomText']!r}")
    if not snapshot["noDuplicateOpenButton"]:
        problems.append("duplicate Agent Chat opener is visible")
    if snapshot["fakeCardLeak"]:
        problems.append("workflow starter card leaked into empty state")
    if snapshot["rawDefaultLeak"]:
        problems.append("raw state or command syntax leaked into default UI")
    if not snapshot["stageWithinViewport"] or not snapshot["noHorizontalScroll"]:
        problems.append("workspace overflows viewport")
    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    expect(page.locator("#product-shell-root")).to_contain_text("故事板当前只读取画布确认后的事实")
    page.get_by_role("tab", name="画布").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
    if problems:
        raise AssertionError(f"{viewport['width']}x{viewport['height']}: " + "; ".join(problems) + f"; snapshot={json.dumps(snapshot, ensure_ascii=False)}")
    return {
        "canvas_default": True,
        "single_agent_chat": True,
        "no_double_left_rail": True,
        "true_zero_node_empty_state": True,
        "storyboard_read_only": True,
        "no_horizontal_scroll": True,
    }


def wait_for_empty_canvas_ready(page: Page) -> None:
    page.wait_for_function(
        """
        () => {
          const stage = document.querySelector(".canvas-workspace-stage");
          const root = stage?.querySelector("#canvas-root");
          const form = stage?.querySelector(".canvas-empty-onboarding");
          const rect = form?.getBoundingClientRect();
          return Boolean(
            root
            && form
            && !document.querySelector(".product-state-loading")
            && rect
            && rect.width > 220
            && rect.height > 160
            && rect.right > 0
            && rect.bottom > 56
            && rect.left < window.innerWidth
            && rect.top < window.innerHeight
          );
        }
        """
    )


def assert_interactions(page: Page, base_url: str) -> dict[str, Any]:
    assert_project_drawer(page)
    assert_agent_chat_resize_and_collapse(page)
    assert_text_revision_and_optimization(page)
    submit_analysis_candidate(base_url)
    assert_dynamic_plan_flow(page, base_url)
    final_snapshot = page.evaluate(
        """
        () => ({
          noHorizontalScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
          rawLeak: ["studio-state-", "planning_required", "{json}"].some((item) => (document.body.textContent || "").includes(item)),
          nodeCount: document.querySelectorAll(".node").length,
        })
        """
    )
    if not final_snapshot["noHorizontalScroll"] or final_snapshot["rawLeak"]:
        raise AssertionError(f"final workspace snapshot failed: {json.dumps(final_snapshot, ensure_ascii=False)}")
    return {
        "project_drawer_escape": True,
        "agent_chat_collapse_resize": True,
        "default_optimize_preview_confirm_receipt_undo": True,
        "instructed_optimize_preview_confirm_receipt_undo": True,
        "dynamic_plan_create_edit_split_merge_retry_replan": True,
        "storyboard_read_only": True,
        "node_count": final_snapshot["nodeCount"],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def assert_project_drawer(page: Page) -> None:
    page.get_by_role("button", name="打开项目导航").click()
    expect(page.locator("#studio-context-drawer")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#studio-context-drawer")).to_have_count(0)


def assert_agent_chat_resize_and_collapse(page: Page) -> None:
    agent = page.locator(".studio-agent-chat").first
    expect(agent).to_be_visible()
    before = agent.bounding_box()["width"]
    handle = page.locator(".agent-resize-handle").first
    box = handle.bounding_box()
    if box:
        page.mouse.move(box["x"] + 4, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] - 44, box["y"] + box["height"] / 2)
        page.mouse.up()
        after = agent.bounding_box()["width"]
        if after <= before:
            raise AssertionError(f"Agent Chat resize did not increase width: before={before} after={after}")
    page.get_by_role("button", name="收起 Agent Chat").click()
    expect(page.locator(".studio-unified-workspace.agent-collapsed")).to_be_visible()
    page.get_by_role("button", name="展开 Agent Chat").click()
    expect(page.locator(".studio-unified-workspace.agent-collapsed")).to_have_count(0)


def assert_text_revision_and_optimization(page: Page) -> None:
    page.locator('.canvas-workspace-stage [data-empty-action="blank-node"]').click()
    expect(page.locator(".node")).to_have_count(1)
    expect(page.locator("#canvas-empty-hint:not([hidden])")).to_have_count(0)
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.fill(SCRIPT_TEXT)
    send_agent_command(page, f"/script-revision {SCRIPT_TEXT}", "创建 ScriptRevision")
    expect(page.locator(".node").filter(has_text="分析：待分析")).to_be_visible()
    select_node_by_title(page, "故事文本")
    page.get_by_title("默认优化文本").click()
    expect(page.locator(".agent-command-preview").filter(has_text="默认优化文本")).to_be_visible()
    page.locator(".agent-command-preview").filter(has_text="默认优化文本").get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").filter(has_text="优化后的 ScriptRevision 已创建")).to_be_visible()
    page.get_by_role("button", name="撤销").first.click()
    expect(page.locator(".agent-receipt").filter(has_text="已恢复上一 ScriptRevision")).to_be_visible()
    select_node_by_title(page, "故事文本")
    submit_agent_text(page, "/optimize-selected 按用户要求压缩节奏并保留结尾")
    expect(page.locator(".agent-command-preview").filter(has_text="按要求优化文本")).to_be_visible()
    page.locator(".agent-command-preview").filter(has_text="按要求优化文本").get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").filter(has_text="优化后的 ScriptRevision 已创建")).to_be_visible()
    page.get_by_role("button", name="撤销").first.click()
    expect(page.locator(".agent-receipt").filter(has_text="已恢复上一 ScriptRevision")).to_be_visible()


def assert_dynamic_plan_flow(page: Page, base_url: str) -> None:
    send_agent_command(page, "/refresh-script-truth", "刷新 Script/Core Asset Truth")
    truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    revision = truth["projection"]["current_revision"]
    candidate = story_plan_candidate(revision, truth["projection"])
    send_agent_command(page, f"/submit-story-plan {json.dumps(candidate, ensure_ascii=False, separators=(',', ':'))}", "提交 Story Plan Candidate")
    expect(page.locator(".node").filter(has_text="Production Plan")).to_be_visible()
    expect(page.locator(".node").filter(has_text="Dynamic shot 3")).to_be_visible()
    assert_canvas_content_fits(page)

    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/edit-shot-duration 7.25", "编辑镜头时长")
    expect(page.locator(".node").filter(has_text="7.25s")).to_be_visible()
    page.get_by_role("button", name="撤销").first.click()
    page.wait_for_function("() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('7.25s'))")

    select_plan_node(page, "production_plan_shot_shot_dynamic_2", "Shot 2")
    send_agent_command(page, "/split-shot 3 3.5", "拆分当前镜头")
    expect(page.locator(".node").filter(has_text="part 2")).to_be_visible()
    select_plan_node(page, "production_plan_shot_shot_dynamic_2a", "Shot 2")
    send_agent_command(page, "/merge-shot-next", "合并下一镜头")
    page.wait_for_function("() => !document.querySelector('[data-node-id=\"production_plan_shot_shot_dynamic_2b\"]')")

    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/mark-failed", "标记失败")
    expect(page.locator(".node").filter(has_text="state: failed")).to_be_visible()
    send_agent_command(page, "/retry-failed", "重试失败项")
    page.wait_for_function("() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('state: failed'))")
    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/replan-affected", "重算受影响计划")

    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    expect(page.locator("#product-shell-root")).to_contain_text("Shot 1")
    expect(page.locator("#product-shell-root")).to_contain_text("Shot 2")
    submit_agent_text(page, "/edit-shot-duration 8")
    expect(page.locator(".agent-command-preview.blocked").filter(has_text="故事板是只读投影")).to_be_visible()
    page.get_by_role("tab", name="画布").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")


def send_agent_command(page: Page, command: str, preview_text: str) -> None:
    submit_agent_text(page, command)
    preview = page.locator(".agent-command-preview").filter(has_text=preview_text).first
    expect(preview).to_be_visible()
    preview.get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").first).to_be_visible()


def submit_agent_text(page: Page, command: str) -> None:
    composer = page.locator(".agent-chat-composer textarea").first
    expect(composer).to_be_visible()
    composer.fill(command)
    composer.evaluate("(input) => input.form.requestSubmit()")


def select_node_by_title(page: Page, title: str) -> None:
    node_id = page.locator(".node").filter(has_text=title).first.get_attribute("data-node-id")
    if not node_id:
        raise AssertionError(f"node with title {title!r} is missing")
    select_canvas_node(page, node_id)


def select_plan_node(page: Page, node_id: str, context_label: str) -> None:
    if not page.evaluate("(nodeId) => Boolean(document.querySelector(`[data-node-id=\"${nodeId}\"]`))", node_id):
        raise AssertionError(f"projection node is missing: {node_id}")
    select_canvas_node(page, node_id)
    expect(page.locator(".studio-agent-chat .agent-context-strip")).to_contain_text(context_label)


def select_canvas_node(page: Page, node_id: str) -> None:
    page.evaluate(
        "(nodeId) => window.dispatchEvent(new CustomEvent('afs:studio-select-node', { detail: { node_id: nodeId } }))",
        node_id,
    )


def assert_canvas_content_fits(page: Page) -> None:
    snapshot = page.evaluate(
        """
        () => {
          const canvas = document.querySelector("#canvas-root")?.getBoundingClientRect();
          const nodes = Array.from(document.querySelectorAll(".node")).map((node) => node.getBoundingClientRect());
          const visible = nodes.filter((rect) => rect.right >= 0 && rect.left <= window.innerWidth && rect.bottom >= 56 && rect.top <= window.innerHeight);
          return {
            nodeCount: nodes.length,
            visibleCount: visible.length,
            scale: Number((document.querySelector("#world")?.style.transform || "").match(/scale\\(([^)]+)\\)/)?.[1] || 1),
            canvasWidth: canvas?.width || 0,
            noHorizontalScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
          };
        }
        """
    )
    if snapshot["nodeCount"] < 4 or snapshot["visibleCount"] < 4 or not snapshot["noHorizontalScroll"]:
        raise AssertionError(f"canvas projection did not fit content: {json.dumps(snapshot, ensure_ascii=False)}")


def submit_analysis_candidate(base_url: str) -> None:
    truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    revision = truth["projection"]["current_revision"]
    body = {
        "project_id": PROJECT_ID,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
        "named_characters": [
            {"display_name": "Mira", "aliases": ["she"], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Mira")], "confidence": 0.94, "status": "candidate"},
            {"display_name": "Tao", "aliases": [], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Tao")], "confidence": 0.9, "status": "candidate"},
        ],
        "main_scenes": [
            {"name": "Observatory", "evidence_spans": [span(SCRIPT_TEXT, "observatory")], "confidence": 0.92, "status": "candidate"},
            {"name": "Signal Room", "evidence_spans": [span(SCRIPT_TEXT, "signal room")], "confidence": 0.91, "status": "candidate"},
        ],
        "style": "precise luminous animation",
        "genre": "short science drama",
        "tone": "focused",
        "actions": ["calibrates the lens", "opens the signal room"],
        "events": ["a distant signal arrives"],
        "beats": [{"summary": "signal setup"}, {"summary": "response"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    http_json(
        f"{base_url}/projects/{PROJECT_ID}/script-revisions/{revision['revision_id']}/analysis-candidates",
        method="POST",
        payload=body,
    )


def story_plan_candidate(revision: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    characters = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "character"]
    scenes = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "main_scene"]
    beats = [
        {
            "beat_id": "beat_lens_setup",
            "order": 1,
            "summary": "Mira prepares the lens as the signal arrives.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Mira calibrates the lens"}],
            "narrative_purpose": "establish the signal source",
        },
        {
            "beat_id": "beat_signal_response",
            "order": 2,
            "summary": "Tao opens the signal room and the response path.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Tao opens the signal room"}],
            "narrative_purpose": "move the scene into response",
        },
    ]
    shots = [
        shot(revision["revision_id"], "shot_dynamic_1", beats[0]["beat_id"], 1, 2.5, "Dynamic shot 1 follows Mira setting the lens.", characters[:1], scenes[:1], "opening stillness", "lens rotates", t2v("text prompt is sufficient because no visual reference is locked")),
        shot(revision["revision_id"], "shot_dynamic_2", beats[0]["beat_id"], 2, 6.5, "Dynamic shot 2 moves through the calibrated lens.", characters[:1], scenes[:1], "lens rotates", "signal line continues", i2v(PROJECT_ID, revision, characters[0])),
        shot(revision["revision_id"], "shot_dynamic_3", beats[1]["beat_id"], 3, 3.0, "Dynamic shot 3 tracks Tao opening the signal room.", characters[:2], scenes[-1:], "signal line continues", "response path holds", t2v("creator intent names action without a reference artifact")),
    ]
    payload = {
        "project_id": PROJECT_ID,
        "script_revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
        "candidate_digest": "",
        "beats": beats,
        "shots": shots,
        "capability_contract": {
            "schema_version": PROVIDER_CAPABILITY_SCHEMA_VERSION,
            "provider_profile_id": "offline-contract-capability",
            "supports_t2v": True,
            "supports_i2v": True,
            "supported_clip_durations": [2.5, 3.0, 4.0],
            "max_duration_seconds": 4.0,
            "supports_start_frame": True,
            "supports_end_frame": True,
            "aspect_ratios": ["9:16"],
            "fps_values": [24],
        },
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload["candidate_digest"] = story_plan_candidate_digest(payload)
    return payload


def shot(
    revision_id: str,
    shot_id: str,
    beat_id: str,
    order: int,
    duration: float,
    intent: str,
    character_refs: list[str],
    scene_refs: list[str],
    continuity_in: str,
    continuity_out: str,
    media_strategy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "shot_id": shot_id,
        "beat_id": beat_id,
        "order": order,
        "intent": intent,
        "duration_seconds": duration,
        "character_refs": character_refs,
        "scene_refs": scene_refs,
        "continuity_in": continuity_in,
        "continuity_out": continuity_out,
        "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision_id, "quote": "distant signal arrives"}],
        "media_strategy": media_strategy,
    }


def t2v(reason: str) -> dict[str, Any]:
    return {
        "strategy": "t2v",
        "strategy_reason": reason,
        "input_requirements": ["text_prompt_contract"],
        "reference_asset_refs": [],
        "user_constraints": {"explicit_reference_available": False},
    }


def i2v(project_id: str, revision: dict[str, Any], asset_id: str) -> dict[str, Any]:
    return {
        "strategy": "i2v",
        "strategy_reason": "locked keyframe lineage is available for the lens move",
        "input_requirements": ["reference_artifact_or_locked_keyframe"],
        "reference_asset_refs": [
            {
                "ref_id": "ref_lens_keyframe",
                "source_kind": "locked_keyframe",
                "asset_id": asset_id,
                "artifact_id": "artifact-lens-keyframe",
                "lineage": {
                    "project_id": project_id,
                    "script_revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "asset_id": asset_id,
                    "artifact_id": "artifact-lens-keyframe",
                    "locked_keyframe_id": "locked-keyframe-lens",
                },
            }
        ],
        "user_constraints": {"explicit_reference_available": True},
    }


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
