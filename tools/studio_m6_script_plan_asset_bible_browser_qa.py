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
VIEWPORTS = ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900})
SOURCE_TEXT = """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：林澈手背的伤痕、时间线上的红色标记。
风格：克制写实冷暖对照。时间：夜晚到清晨。光线：剪辑室屏幕冷光与屋顶晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
目标：林澈想证明被删掉的素材能救回影片。冲突：唐予担心返工会拖垮拍摄预算。关系：两人从互相指责转为共同承担。变化：林澈从逃避失误转为主动承认。
林澈盯着屏幕里的断帧，低声说“如果这一秒还在，结尾就不是谎言”。
唐予把场记板放到桌边，要求他在十分钟内给出能拍的重做方案。
两人带着旧镜头上到屋顶，晨光压住城市噪声，林澈终于说出自己删错素材的真相。
唐予没有责备，只把红色标记改成新的拍摄任务，让林澈先拍自己的手和那支旧镜头。
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
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "M6专业剧本到资产Bible制作图"})
    if created.status_code not in {200, 409}:
        raise AssertionError(created.text)
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": studio_state(PROJECT_ID)})
    if saved.status_code != 200:
        raise AssertionError(saved.text)


def studio_state(project_id: str) -> dict[str, Any]:
    return {
        "meta": {"projectId": project_id, "projectName": "M6专业剧本项目", "canvasName": "制作画布", "seq": 1, "updated_at": ""},
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
                "prompt": "等待M6专业剧本制作方案确认。",
                "content": "等待M6专业剧本制作方案确认。",
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
        "林澈",
        "唐予",
        "夜晚旧剪辑室",
        "清晨屋顶",
        "场记板",
        "旧镜头",
        "主要道具",
        "制作参考",
        "道具清单",
        "制作参考清单",
    ):
        expect(preview).to_contain_text(token)
    expect(preview).to_contain_text("名称变化 0")
    expect(preview.locator(".agent-m6-scope-group").filter(has_text="名称变化")).to_contain_text("无")
    preview_text = preview.inner_text()
    if "制作参考" not in preview_text or "主要道具" not in preview_text:
        raise AssertionError("confirmation card does not expose creator-readable asset classifications")
    if any(token in preview_text for token in ("canonical_prop", "production_aid", "ProductionGraph", "M6")):
        raise AssertionError("confirmation card leaks internal classification or graph vocabulary")
    preview_screenshot = str((screenshot_dir / "m6-confirmation-card-1920x1080.png").resolve())
    page.screenshot(path=preview_screenshot, full_page=True)
    page.locator(".agent-command-preview").get_by_role("button", name="确认并保存").click()
    page.wait_for_selector(".graph-canvas-status.ready")
    workspace = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    if workspace["status"] != "ready" or workspace["graph_digest"] != workspace["storyboard"]["graph_digest"]:
        raise AssertionError("M6 confirmation did not produce one graph projection")
    if len(workspace["sequence"]["shots"]) < 2 or len(workspace["sequence"]["characters"]) < 2:
        raise AssertionError("M6 graph is missing shots or named characters")
    return {
        "planning_required": True,
        "agent_preview": True,
        "pc_confirmation_card_transparent": True,
        "confirmation_card_screenshot": preview_screenshot,
        "explicit_confirmation": True,
        "same_graph_projection": True,
    }


def assert_graph_consumers(page: Page, base_url: str) -> dict[str, Any]:
    page.wait_for_selector(".graph-canvas-status.ready")
    page.wait_for_selector('.node[data-node-id^="production_graph_"]')
    body = page.locator("body").inner_text()
    if any(token in body for token in ("schema_version", "graph_digest", "m6-character-", "m6-script-plan-layout")):
        raise AssertionError("raw graph internals leaked into Studio copy")
    ensure_agent_visible(page)
    expect(page.locator(".studio-agent-chat")).to_be_visible()
    page.get_by_role("tab", name="故事板").click()
    page.wait_for_selector(".storyboard-shot")
    if page.locator(".storyboard-shot").count() < 2:
        raise AssertionError("Storyboard did not consume M6 graph shots")
    page.get_by_role("tab", name="画布").click()
    page.wait_for_selector('.node[data-node-id^="production_graph_"]')
    workspace = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    return {
        "canvas_graph_nodes": True,
        "storyboard_graph_shots": True,
        "agent_chat_fixed": True,
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
