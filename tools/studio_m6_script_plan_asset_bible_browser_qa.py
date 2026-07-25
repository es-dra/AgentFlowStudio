from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
STAMP = int(time.time())
PROJECT_ID = f"m6-browser-script-bible-{STAMP}"
FAILED_PROJECT_ID = f"m6-browser-failed-plan-{STAMP}"
PROCESSING_PROJECT_ID = f"m6-browser-processing-plan-{STAMP}"
VIEWPORTS = ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900})
SOURCE_TEXT = """
夏岚在海边档案馆整理一支银色录音笔。
保持角色名称“夏岚”、场景名称“海边档案馆”、道具名称“银色录音笔”不变；规划3个连续镜头，总时长约25秒。
不要新增其他人物、场景或道具；制作参考必须明确标为辅助内容。
第一镜建立档案馆窗边的工作台和录音笔原始状态。
第二镜让夏岚清理磁头并确认录音仍可读取。
第三镜以录音笔恢复播放和夏岚停止动作收束。
"""


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-browser-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-script-plan-bible-browser-{STAMP}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/afs-m6-script-plan-bible-browser-{STAMP}-screens").resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    seed_project(runtime_root)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(repo, base_url, screenshot_dir, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": str(screenshot_dir)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6 script-plan-asset-Bible Studio browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def seed_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    for project_id, goal in (
        (PROJECT_ID, "灯种黎明短片制作"),
        (FAILED_PROJECT_ID, "制作方案恢复验收"),
        (PROCESSING_PROJECT_ID, "制作方案处理中验收"),
    ):
        created = client.post("/projects", json={"project_id": project_id, "goal": goal})
        if created.status_code not in {200, 409}:
            raise AssertionError(created.text)
        saved = client.put(f"/projects/{project_id}/studio-state", json={"state": studio_state(project_id)})
        if saved.status_code != 200:
            raise AssertionError(saved.text)


def studio_state(project_id: str) -> dict[str, Any]:
    return {
        "meta": {"projectId": project_id, "projectName": "灯种黎明", "canvasName": "制作画布", "seq": 1, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {
            "seed_brief": {
                "id": "seed_brief",
                "type": "text",
                "title": "创作简报",
                "x": 90,
                "y": 110,
                "w": 300,
                "h": 220,
                "prompt": "等待制作方案确认。",
                "content": "等待制作方案确认。",
                "status": "draft",
                "params": {},
                "collapsed": False,
            },
        },
        "edges": {},
        "groups": {},
        "assets": [],
        "order": ["seed_brief"],
        "selection": {"nodeIds": [], "edgeId": None},
        "production": {},
        "ui": {},
    }


def run_qa(repo: Path, base_url: str, screenshot_dir: Path, headed: bool, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    results: dict[str, Any] = {}
    before_state_version = http_json(f"{base_url}/projects/{PROJECT_ID}/studio-state")["state_version"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed, executable_path=chrome_path(), args=["--proxy-server=direct://", "--proxy-bypass-list=*"])
        try:
            recovery = browser.new_page(viewport=VIEWPORTS[0])
            configure(recovery, repo, timeout_ms, console_errors, response_errors)
            results["failed-plan-refresh-recovery-1920x1080"] = assert_failed_plan_refresh_recovery(
                recovery,
                base_url,
                screenshot_dir,
            )
            screenshots["failed-plan-refresh-recovery-1920x1080"] = str(
                (screenshot_dir / "failed-plan-refresh-recovery-1920x1080.png").resolve()
            )
            recovery.screenshot(
                path=screenshots["failed-plan-refresh-recovery-1920x1080"],
                full_page=True,
            )
            recovery.close()

            processing = browser.new_page(viewport=VIEWPORTS[0])
            configure(processing, repo, timeout_ms, console_errors, response_errors)
            results["plan-processing-1920x1080"] = assert_plan_processing_copilot(
                processing,
                base_url,
            )
            screenshots["plan-processing-1920x1080"] = str(
                (screenshot_dir / "plan-processing-1920x1080.png").resolve()
            )
            processing.screenshot(
                path=screenshots["plan-processing-1920x1080"],
                full_page=True,
            )
            processing.close()

            first = browser.new_page(viewport=VIEWPORTS[0])
            configure(first, repo, timeout_ms, console_errors, response_errors)
            first.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=m6-preview", wait_until="domcontentloaded")
            results["m6-preview-confirm-1920x1080"] = assert_m6_preview_confirm(first, base_url, screenshot_dir)
            screenshots["m6-after-confirm-1920x1080"] = str((screenshot_dir / "m6-after-confirm-1920x1080.png").resolve())
            first.screenshot(path=screenshots["m6-after-confirm-1920x1080"], full_page=True)
            first.close()

            for viewport in VIEWPORTS:
                key = f"{viewport['width']}x{viewport['height']}"
                page = browser.new_page(viewport=viewport)
                configure(page, repo, timeout_ms, console_errors, response_errors)
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=m6-graph-{viewport['width']}", wait_until="domcontentloaded")
                results[f"m6-graph-{key}"] = assert_graph_consumers(page, base_url)
                screenshots[f"m6-graph-{key}"] = str((screenshot_dir / f"m6-graph-{key}.png").resolve())
                page.screenshot(path=screenshots[f"m6-graph-{key}"], full_page=True)
                page.close()
        finally:
            browser.close()
    actionable = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable:
        raise AssertionError(f"console={console_errors[:5]} responses={actionable[:5]}")
    after_state_version = http_json(f"{base_url}/projects/{PROJECT_ID}/studio-state")["state_version"]
    workspace = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    if before_state_version != after_state_version:
        raise AssertionError("M6 graph actions wrote studio_state")
    return {
        "artifact_type": "afs_m6_script_plan_asset_bible_browser_qa",
        "status": "passed",
        "project_id": PROJECT_ID,
        "viewports": results,
        "screenshots": screenshots,
        "graph_version": workspace["graph_version"],
        "graph_digest_parity": workspace["graph_digest"] == workspace["storyboard"]["graph_digest"],
        "studio_state_unchanged_by_graph_actions": True,
        "console_error_count": 0,
        "response_error_count": 0,
        "provider_dispatch_count": workspace.get("provider_dispatch_count", 0),
        "cost_usd": workspace.get("cost_usd", 0),
    }


def assert_plan_processing_copilot(page: Page, base_url: str) -> dict[str, Any]:
    route_state = {"fake_preview_submits": 0}
    queued_run = {
        "schema_version": "afs.m6.preview_run.v0.1",
        "run_id": "processing-preview-run",
        "project_id": PROCESSING_PROJECT_ID,
        "client_request_id": "processing-preview-client",
        "phase": "queued",
        "status": "queued",
        "dispatch_count": 1,
        "candidate_digest": "",
        "cost": {
            "contract_estimated_usd": 0,
            "provider_reported_external_cost_usd": 0,
            "actual_usd": None,
        },
    }
    running_run = {**queued_run, "phase": "running", "status": "running"}

    page.route(
        f"**/projects/{PROCESSING_PROJECT_ID}/m6/script-plan-asset-bible/preview-runs/latest",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"status": "empty", "run": None}),
        ),
    )
    page.route(
        f"**/projects/{PROCESSING_PROJECT_ID}/m6/script-plan-asset-bible/preview-runs/processing-preview-run",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(running_run),
        ),
    )

    def preview_handler(route) -> None:
        route_state["fake_preview_submits"] += 1
        route.fulfill(status=200, content_type="application/json", body=json.dumps(queued_run))

    page.route(
        f"**/projects/{PROCESSING_PROJECT_ID}/m6/script-plan-asset-bible/preview",
        preview_handler,
    )
    page.goto(
        f"{base_url}/studio/?project={PROCESSING_PROJECT_ID}&stage=canvas&qa=m6-processing",
        wait_until="domcontentloaded",
    )
    page.wait_for_selector(".graph-canvas-status.planning-required")
    page.get_by_role("button", name="制作方案").click()
    page.get_by_label("输入想法或已有剧本").fill(SOURCE_TEXT)
    page.get_by_role("button", name="生成剧本制作方案").click()

    agent = page.locator(".agent-production-copilot")
    expect(agent).to_contain_text("制作方案正在准备")
    expect(agent).to_contain_text("当前无需重复提交创作想法")
    expect(agent).not_to_contain_text("项目已创建，可以从一个想法开始")
    expect(agent.get_by_role("button", name="输入创作想法")).to_have_count(0)
    progress = agent.get_by_role("button", name="查看制作进度")
    expect(progress).to_be_visible()
    progress.click()
    expect(page.locator(".m6-preview-run-status.phase-running")).to_be_visible()
    expect(page.locator(".graph-canvas-status.planning-required")).to_have_attribute("data-expanded", "true")
    if route_state["fake_preview_submits"] != 1:
        raise AssertionError("processing-state QA submitted more than one fake preview")
    return {
        "fake_preview_submit_count": 1,
        "durable_run_phase": "running",
        "copilot_processing_state_consistent": True,
        "idle_start_action_absent": True,
        "progress_action_visible": True,
        "new_provider_dispatch_count": 0,
    }


def assert_failed_plan_refresh_recovery(page: Page, base_url: str, screenshot_dir: Path) -> dict[str, Any]:
    route_state = {"failed": False, "fake_preview_submits": 0}
    failed_run = {
        "schema_version": "afs.m6.preview_run.v0.1",
        "run_id": "failed-preview-run",
        "project_id": FAILED_PROJECT_ID,
        "client_request_id": "failed-preview-client",
        "phase": "failed",
        "status": "failed",
        "dispatch_count": 1,
        "candidate_digest": "",
        "error": {
            "category": "planning_rejected",
            "message": "制作方案未通过结构校验；制作事实未改变。",
        },
        "cost": {
            "contract_estimated_usd": 0,
            "provider_reported_external_cost_usd": 0,
            "actual_usd": None,
        },
    }

    def latest_handler(route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(failed_run if route_state["failed"] else {"status": "empty", "run": None}),
        )

    def run_handler(route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(failed_run))

    def preview_handler(route) -> None:
        route_state["failed"] = True
        route_state["fake_preview_submits"] += 1
        route.fulfill(status=200, content_type="application/json", body=json.dumps(failed_run))

    page.route(
        f"**/projects/{FAILED_PROJECT_ID}/m6/script-plan-asset-bible/preview-runs/latest",
        latest_handler,
    )
    page.route(
        f"**/projects/{FAILED_PROJECT_ID}/m6/script-plan-asset-bible/preview-runs/failed-preview-run",
        run_handler,
    )
    page.route(
        f"**/projects/{FAILED_PROJECT_ID}/m6/script-plan-asset-bible/preview",
        preview_handler,
    )
    page.goto(
        f"{base_url}/studio/?project={FAILED_PROJECT_ID}&stage=canvas&qa=m6-failed-refresh",
        wait_until="domcontentloaded",
    )
    page.wait_for_selector(".graph-canvas-status.planning-required")
    page.get_by_role("button", name="制作方案").click()
    page.get_by_label("输入想法或已有剧本").fill(SOURCE_TEXT)
    page.get_by_role("button", name="生成剧本制作方案").click()
    expect(page.get_by_role("button", name="恢复同一预览")).to_be_visible()
    page.get_by_label("输入想法或已有剧本").fill("这是失败后尚未提交的新草稿。")
    page.reload(wait_until="domcontentloaded")

    expect(page.get_by_label("输入想法或已有剧本")).to_have_value(SOURCE_TEXT)
    expect(page.get_by_role("button", name="恢复同一预览")).to_be_visible()
    agent = page.locator(".agent-production-copilot")
    expect(agent).to_contain_text("制作方案未通过检查")
    expect(agent).to_contain_text("检查失败原因并恢复同一预览")
    expect(agent.get_by_role("button", name="恢复制作方案")).to_be_visible()
    expect(agent).not_to_contain_text("项目已创建，可以从一个想法开始")
    expect(agent.get_by_role("button", name="输入创作想法")).to_have_count(0)
    agent.get_by_role("button", name="恢复制作方案").click()
    expect(page.get_by_role("button", name="恢复同一预览")).to_be_visible()
    expect(page.get_by_label("输入想法或已有剧本")).to_have_value(SOURCE_TEXT)
    page.get_by_role("tab", name="故事板").click()
    screenplay = page.get_by_role("button", name="脚本与对白")
    expect(screenplay).to_be_disabled()
    expect(screenplay).to_have_attribute("title", "先完成制作方案并建立场景")
    page.get_by_role("tab", name="画布").click()
    if route_state["fake_preview_submits"] != 1:
        raise AssertionError("failed-plan recovery dispatched a new provider preview")
    return {
        "fake_preview_submit_count": 1,
        "source_draft_restored_after_refresh": True,
        "source_matches_failed_run_submission": True,
        "durable_run_recovery_visible": True,
        "copilot_recovery_action_consistent": True,
        "empty_storyboard_script_action_disabled": True,
        "new_provider_dispatch_count": 0,
    }


def assert_m6_preview_confirm(page: Page, base_url: str, screenshot_dir: Path) -> dict[str, Any]:
    page.wait_for_selector(".graph-canvas-status.planning-required")
    plan_status = page.locator(".graph-canvas-status.planning-required")
    if page.get_by_role("button", name="展开制作方案").count():
        expect(plan_status).to_contain_text("可自由开始")
        page.get_by_role("button", name="展开制作方案").click()
    else:
        expect(plan_status).to_contain_text("制作方案")
        page.get_by_role("button", name="制作方案").click()
    page.get_by_label("输入想法或已有剧本").fill(SOURCE_TEXT)
    page.get_by_role("button", name="生成剧本制作方案").click()
    preview = page.locator(".agent-command-preview")
    expect(preview).to_contain_text("确认制作方案")
    expect(preview).to_contain_text("动态镜头")
    for token in (
        "本次方案包含",
        "新建内容",
        "名称变化",
        "内容补充",
        "资产用途",
        "影响的镜头与引用",
        "夏岚",
        "海边档案馆",
        "银色录音笔",
        "主要道具",
        "制作参考",
        "道具清单",
        "制作参考清单",
        "创作目标",
        "关系变化",
        "镜头时长",
        "人物调度",
    ):
        expect(preview).to_contain_text(token)
    expect(preview).to_contain_text("名称变化 0")
    expect(preview.locator(".agent-m6-scope-group").filter(has_text="名称变化")).to_contain_text("无")
    preview_text = preview.inner_text()
    if "制作参考" not in preview_text or "主要道具" not in preview_text:
        raise AssertionError("confirmation card does not expose creator-readable asset classifications")
    if any(token in preview_text for token in (
        "canonical_prop", "production_aid", "ProductionGraph", "M6",
        "relationship_arc", "duration_seconds", "camera_movement", "rights_boundary",
    )):
        raise AssertionError("confirmation card leaks internal classification or graph vocabulary")
    preview_screenshot = str((screenshot_dir / "m6-confirmation-card-1920x1080.png").resolve())
    page.screenshot(path=preview_screenshot, full_page=True)
    expansions = preview.locator(".agent-m6-scope-group").filter(has_text="内容补充")
    expansions.scroll_into_view_if_needed()
    expansion_screenshot = str((screenshot_dir / "m6-confirmation-expansions-1920x1080.png").resolve())
    page.screenshot(path=expansion_screenshot, full_page=True)
    page.locator(".agent-command-preview").get_by_role("button", name="确认并保存").click()
    page.wait_for_selector(".graph-canvas-status.ready")
    workspace = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    if workspace["status"] != "ready" or workspace["graph_digest"] != workspace["storyboard"]["graph_digest"]:
        raise AssertionError("M6 confirmation did not produce one graph projection")
    if len(workspace["sequence"]["shots"]) < 2 or len(workspace["sequence"]["characters"]) < 1:
        raise AssertionError("M6 graph is missing shots or named characters")
    return {
        "planning_required": True,
        "agent_preview": True,
        "pc_confirmation_card_transparent": True,
        "confirmation_card_screenshot": preview_screenshot,
        "confirmation_expansions_screenshot": expansion_screenshot,
        "explicit_confirmation": True,
        "same_graph_projection": True,
    }


def assert_graph_consumers(page: Page, base_url: str) -> dict[str, Any]:
    page.wait_for_selector(".graph-canvas-status.ready")
    page.wait_for_selector('.node[data-node-id^="production_graph_"]')
    body = page.locator("body").inner_text()
    if any(token in body for token in ("schema_version", "graph_digest", "m6-character-", "m6-script-plan-layout")):
        raise AssertionError("raw graph internals leaked into Studio copy")
    projected_layout = page.locator('.node[data-node-id^="production_graph_"]').evaluate_all(
        """
        nodes => nodes.map((node) => {
          const rect = node.getBoundingClientRect();
          const title = node.querySelector(".node-title");
          const titleRect = title?.getBoundingClientRect();
          return {
            id: node.dataset.nodeId,
            left: rect.left,
            right: rect.right,
            top: rect.top,
            bottom: rect.bottom,
            titleWithinNode: !titleRect || titleRect.right <= rect.right + 1,
            text: node.innerText,
          };
        })
        """
    )
    for index, node in enumerate(projected_layout):
        if not node["titleWithinNode"]:
            raise AssertionError(f"projected node title overflows its card: {node['id']}")
        if any(token in node["text"] for token in ("输入故事", "上传或连接")):
            raise AssertionError(f"projected node leaks an editor placeholder: {node['id']}")
        for other in projected_layout[index + 1 :]:
            overlap_width = min(node["right"], other["right"]) - max(node["left"], other["left"])
            overlap_height = min(node["bottom"], other["bottom"]) - max(node["top"], other["top"])
            if overlap_width > 1 and overlap_height > 1:
                raise AssertionError(f"projected nodes overlap: {node['id']} and {other['id']}")
    ensure_agent_visible(page)
    agent = page.locator(".studio-agent-chat")
    expect(agent).to_be_visible()
    expect(agent).to_contain_text("制作方案已保存")
    expect(agent.get_by_role("button", name="查看故事板")).to_be_visible()
    page.get_by_role("tab", name="故事板").click()
    page.wait_for_selector(".storyboard-shot")
    if page.locator(".storyboard-shot").count() < 2:
        raise AssertionError("Storyboard did not consume M6 graph shots")
    workspace = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    graph_version = workspace["graph_version"]
    canonical_names = [
        *[
            item.get("metadata", {}).get("display_name", "")
            for item in workspace["sequence"]["characters"]
        ],
        *[
            item.get("metadata", {}).get("name", "")
            for item in workspace["sequence"]["scenes"]
        ],
        *[
            item.get("metadata", {}).get("name", "")
            for item in workspace["sequence"]["props"]
        ],
    ]
    page.get_by_role("tab", name="资产 Bible").click()
    bible = page.locator(".studio-asset-bible")
    expect(bible).to_be_visible()
    expect(bible.locator(".asset-bible-status-bar")).to_contain_text("已选择")
    expect(bible.locator(".asset-bible-status-bar")).to_contain_text(
        f"{len(workspace['sequence']['scenes'])} 场 · {len(workspace['sequence']['shots'])} 镜头"
    )
    expect(bible.locator(".asset-bible-status-bar")).to_contain_text(
        f"{len(canonical_names)} 项来源已确认"
    )
    for name in canonical_names:
        if name:
            expect(bible).to_contain_text(name)
    agent = page.locator(".agent-production-copilot")
    expect(agent.get_by_role("button", name="识别资产候选")).to_be_visible()
    identify = bible.get_by_role("button", name="识别资产候选")
    expect(identify).to_be_enabled()
    identify.click()
    review = bible.locator(".asset-bible-command-review")
    expect(review).to_be_visible()
    expect(review).to_contain_text(
        f"影响 {len(canonical_names)} 个资产 · {len(workspace['sequence']['scenes'])} 场 · {len(workspace['sequence']['shots'])} 镜头"
    )
    review.get_by_role("button", name="取消").click()
    expect(bible.locator(".asset-bible-command-review")).to_have_count(0)
    after_preview = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    if after_preview["graph_version"] != graph_version:
        raise AssertionError("Asset Bible preview mutated the confirmed graph")
    if any(token in bible.inner_text() for token in ("graph_digest", "ProductionGraph", "source_graph_asset_ids")):
        raise AssertionError("Asset Bible leaked graph internals into the creator surface")
    return {
        "canvas_graph_nodes": True,
        "canvas_graph_nodes_do_not_overlap": True,
        "canvas_graph_titles_contained": True,
        "canvas_graph_placeholders_absent": True,
        "storyboard_graph_shots": True,
        "asset_bible_graph_source_ready": True,
        "asset_bible_canonical_assets_visible": True,
        "asset_bible_identify_action_enabled": True,
        "asset_bible_preview_cancel_preserved_graph": True,
        "agent_chat_fixed": True,
        "agent_next_action_matches_graph": True,
        "graph_digest_parity": workspace["graph_digest"] == workspace["storyboard"]["graph_digest"],
        "provider_dispatch_count": workspace.get("provider_dispatch_count", 0),
        "cost_usd": workspace.get("cost_usd", 0),
    }


def ensure_agent_visible(page: Page) -> None:
    if page.locator(".studio-agent-chat:visible").count():
        return
    if page.get_by_role("button", name="Agent").count():
        page.get_by_role("button", name="Agent").click()
    elif page.get_by_role("button", name="搭档").count():
        page.get_by_role("button", name="搭档").click()
    expect(page.locator(".studio-agent-chat")).to_be_visible()


def configure(page: Page, repo: Path, timeout_ms: int, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.set_default_timeout(timeout_ms)
    expect.set_options(timeout=timeout_ms)
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("response", lambda response: response_errors.append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
    page.route("**/studio/src/**", static_route(repo))
    page.route("**/studio/styles/**", static_route(repo))


def start_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update({
        "AFS_RUNTIME_SERVICE_ROOT": str(runtime_root),
        "AFS_RUNTIME_ROOT": str(runtime_root),
        "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1",
        "AFS_RUNTIME_SERVICE_PORT": str(port),
        "AFS_AUTH_ENABLED": "false",
        "AFS_AUTH_ALLOW_OPEN_SIGNUP": "false",
    })
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


def static_route(repo: Path):
    studio_root = (repo / "apps/studio").resolve()

    def handler(route) -> None:
        relative = urlsplit(route.request.url).path.removeprefix("/studio/")
        path = (studio_root / relative).resolve()
        try:
            path.relative_to(studio_root)
        except ValueError:
            route.fulfill(status=404, body=b"")
            return
        if not path.is_file():
            route.fulfill(status=404, body=b"")
            return
        content_type = "text/javascript; charset=utf-8" if path.suffix == ".js" else "text/css; charset=utf-8"
        route.fulfill(status=200, content_type=content_type, body=path.read_bytes())

    return handler


def http_json(url: str) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
