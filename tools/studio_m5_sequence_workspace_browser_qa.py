from __future__ import annotations

import argparse
import hashlib
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
LEGACY_PROJECT = f"m5-browser-legacy-{STAMP}"
GRAPH_PROJECT = f"m5-browser-graph-{STAMP}"
PLANNING_PROJECT = f"m5-browser-planning-{STAMP}"
VIEWPORTS = ({"width": 1440, "height": 900}, {"width": 1024, "height": 768}, {"width": 800, "height": 900})


def main() -> int:
    args = parse_args(); repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m5-browser-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m5-sequence-browser-{STAMP}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/afs-m5-sequence-browser-{STAMP}-screens").resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True); report_path.parent.mkdir(parents=True, exist_ok=True)
    seed_projects(runtime_root)
    port = args.port or free_port(); base_url = f"http://127.0.0.1:{port}"
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
    parser = argparse.ArgumentParser(description="M5 graph-backed single-shell browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT)); parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default=""); parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0); parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def seed_projects(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    for project_id, goal in ((LEGACY_PROJECT, "未迁移画布可达性核验"), (GRAPH_PROJECT, "专业制作序列核验"),
                             (PLANNING_PROJECT, "待确认制作方案核验")):
        response = client.post("/projects", json={"project_id": project_id, "goal": goal})
        if response.status_code not in {200, 409}: raise AssertionError(response.text)
        saved = client.put(f"/projects/{project_id}/studio-state", json={"state": studio_state(project_id)})
        if saved.status_code != 200: raise AssertionError(saved.text)

    candidate = film_candidate()
    confirmed = client.post(f"/projects/{GRAPH_PROJECT}/m4/film-candidates/confirm", json={
        "expected_graph_version": 0, "idempotency_key": "browser-confirm", "candidate": candidate})
    if confirmed.status_code != 200: raise AssertionError(confirmed.text)
    executed = client.post(f"/projects/{GRAPH_PROJECT}/m4/work/work-browser-shot-1/fake-execute", json={
        "candidate_payload": {"media_version": "离线候选一", "review_state": "draft"}, "semantic_digest": digest("browser-artifact")})
    if executed.status_code != 200: raise AssertionError(executed.text)


def studio_state(project_id: str) -> dict[str, Any]:
    nodes = {
        "legacy_text": {"id": "legacy_text", "type": "text", "title": "创作简报", "x": 70, "y": 100, "w": 280, "h": 240,
            "prompt": "从可编辑文本进入制作。", "content": "从可编辑文本进入制作。", "status": "complete", "params": {}, "collapsed": False},
        "legacy_script": {"id": "legacy_script", "type": "script", "title": "剧本工作稿", "x": 470, "y": 260, "w": 280, "h": 240,
            "prompt": "保持原画布编辑能力。", "content": "保持原画布编辑能力。", "status": "complete", "params": {}, "collapsed": False},
    }
    return {"meta": {"projectId": project_id, "projectName": "专业序列工作区", "canvasName": "制作画布", "seq": 1, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1}, "nodes": nodes,
        "edges": {"legacy_edge": {"id": "legacy_edge", "from": "legacy_text", "to": "legacy_script", "relation_type": "generation"}},
        "groups": {}, "assets": [], "order": ["legacy_text", "legacy_script"],
        "selection": {"nodeIds": [], "edgeId": None}, "production": {}, "ui": {}}


def film_candidate() -> dict[str, Any]:
    return {"schema_version": "afs.film_domain_pack.v0.1", "trusted_candidate": True, "source_digest": digest("browser-script"),
        "brief": {"brief_id": "browser-brief"}, "script_revision": {"revision_id": "browser-revision"},
        "sequence": {"sequence_id": "browser-sequence", "name": "主制作序列", "target_duration_seconds": 14.75},
        "characters": [
            {"character_id": "browser-character-1", "display_name": "顾青", "aliases": ["摄影师"]},
            {"character_id": "browser-character-2", "display_name": "唐予", "aliases": ["制片人"]},
        ],
        "scenes": [
            {"scene_id": "browser-scene-1", "name": "室内摄影棚", "lineage": ["browser-revision"]},
            {"scene_id": "browser-scene-2", "name": "剪辑室", "lineage": ["browser-revision"]},
        ],
        "assets": [
            {"asset_id": "browser-reference-1", "name": "摄影棚光位参考", "kind": "reference_set"},
            {"asset_id": "browser-prop-1", "name": "场记板", "kind": "prop"},
        ],
        "shots": [
            {"shot_id": "browser-shot-1", "scene_id": "browser-scene-1", "duration_seconds": 4.5, "intent": "顾青调整主光，唐予确认场记。", "character_refs": ["browser-character-1", "browser-character-2"], "asset_refs": ["browser-reference-1", "browser-prop-1"]},
            {"shot_id": "browser-shot-2", "scene_id": "browser-scene-1", "duration_seconds": 7, "intent": "镜头沿灯架移动，交代空间关系。", "character_refs": ["browser-character-1"], "asset_refs": ["browser-reference-1"]},
            {"shot_id": "browser-shot-3", "scene_id": "browser-scene-2", "duration_seconds": 3.25, "intent": "唐予在时间线上标记需要返工的段落。", "character_refs": ["browser-character-2"], "asset_refs": ["browser-prop-1"]},
        ], "delivery_id": "browser-delivery", "timeline_refs": ["sequence-main"], "rights_refs": ["internal-original"]}


def run_qa(repo: Path, base_url: str, screenshot_dir: Path, headed: bool, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []; response_errors: list[dict[str, Any]] = []; screenshots: dict[str, str] = {}; results: dict[str, Any] = {}
    initial_state_version = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/studio-state")["state_version"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed, executable_path=chrome_path(), args=["--proxy-server=direct://", "--proxy-bypass-list=*"])
        try:
            planning = browser.new_page(viewport={"width": 1440, "height": 900})
            configure(planning, repo, timeout_ms, console_errors, response_errors)
            planning.goto(f"{base_url}/studio/?project={PLANNING_PROJECT}&stage=canvas&qa=m5-planning", wait_until="domcontentloaded")
            results["planning-import-1440x900"] = assert_planning_import(planning, base_url)
            screenshots["planning-import-1440x900"] = str((screenshot_dir / "planning-import-1440x900.png").resolve())
            planning.screenshot(path=screenshots["planning-import-1440x900"], full_page=True); planning.close()
            for viewport in VIEWPORTS:
                key = f"{viewport['width']}x{viewport['height']}"
                baseline = browser.new_page(viewport=viewport); configure(baseline, repo, timeout_ms, console_errors, response_errors)
                baseline.goto(f"{base_url}/studio/?project={LEGACY_PROJECT}&stage=canvas&qa=m5-baseline-{viewport['width']}", wait_until="domcontentloaded")
                results[f"baseline-{key}"] = assert_legacy_parity(baseline)
                screenshots[f"baseline-{key}"] = str((screenshot_dir / f"baseline-{key}.png").resolve()); baseline.screenshot(path=screenshots[f"baseline-{key}"], full_page=True); baseline.close()

                page = browser.new_page(viewport=viewport); configure(page, repo, timeout_ms, console_errors, response_errors)
                page.goto(f"{base_url}/studio/?project={GRAPH_PROJECT}&stage=canvas&qa=m5-graph-{viewport['width']}", wait_until="domcontentloaded")
                results[f"graph-{key}"] = assert_graph_workspace(page)
                screenshots[f"graph-{key}"] = str((screenshot_dir / f"graph-{key}.png").resolve()); page.screenshot(path=screenshots[f"graph-{key}"], full_page=True)
                if viewport["width"] == 1440:
                    page.get_by_role("button", name="打开项目导航").click()
                    screenshots["production-details-1440x900"] = str((screenshot_dir / "production-details-1440x900.png").resolve())
                    page.screenshot(path=screenshots["production-details-1440x900"], full_page=True)
                    page.keyboard.press("Escape")
                    results["lifecycle-1440x900"] = assert_graph_lifecycle(page, base_url)
                    after_graph_actions = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/studio-state")["state_version"]
                    if after_graph_actions != initial_state_version: raise AssertionError("graph actions wrote studio_state")
                    results["lifecycle-1440x900"]["projection_pruned_on_user_save"] = assert_projection_pruned_on_user_save(page, base_url)
                    screenshots["lifecycle-1440x900"] = str((screenshot_dir / "lifecycle-1440x900.png").resolve()); page.screenshot(path=screenshots["lifecycle-1440x900"], full_page=True)
                page.close()
        finally:
            browser.close()
    actionable = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable: raise AssertionError(f"console={console_errors[:5]} responses={actionable[:5]}")
    final_workspace = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/m5/sequence-workspace")
    if final_workspace["graph_digest"] != final_workspace["storyboard"]["graph_digest"]: raise AssertionError("Canvas and Storyboard digest diverged")
    return {"artifact_type": "afs_m5_sequence_workspace_browser_qa", "status": "passed", "viewports": results,
        "screenshots": screenshots, "graph_version": final_workspace["graph_version"], "graph_digest_parity": True,
        "studio_state_unchanged_by_graph_actions": True, "graph_projection_pruned_from_user_save": True, "console_error_count": 0, "response_error_count": 0,
        "provider_dispatch_count": final_workspace.get("provider_dispatch_count", 0), "cost_usd": final_workspace.get("cost_usd", 0)}


def configure(page: Page, repo: Path, timeout_ms: int, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.set_default_timeout(timeout_ms); expect.set_options(timeout=timeout_ms)
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("response", lambda response: response_errors.append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
    page.route("**/studio/src/**", static_route(repo)); page.route("**/studio/styles/**", static_route(repo))


def assert_legacy_parity(page: Page) -> dict[str, Any]:
    page.wait_for_selector('.node[data-node-id="legacy_text"]'); page.wait_for_selector('[data-edge-id="legacy_edge"] path.edge-flow')
    editor = page.locator('.node[data-node-id="legacy_text"] .node-content-editor'); editor.click(); editor.press("Control+A"); editor.type("y"); editor.type("y")
    if editor.input_value() != "yy" or not editor.evaluate("element => element === document.activeElement"): raise AssertionError("legacy text editing lost focus")
    page.locator('.node[data-node-id="legacy_text"] .node-title').click(); expect(page.locator('.node[data-node-id="legacy_text"].selected')).to_have_count(1)
    ensure_agent_visible(page); expect(page.locator(".studio-agent-chat")).to_be_visible()
    page.get_by_role("tab", name="故事板").click(); page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    page.get_by_role("tab", name="画布").click(); page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
    return {"text_editing": True, "selection": True, "connection": True, "agent_chat": True, "storyboard_switch": True}


def assert_graph_workspace(page: Page) -> dict[str, Any]:
    page.wait_for_selector(".graph-canvas-status.ready"); page.wait_for_selector('.node[data-node-id^="production_graph_"]')
    if page.locator('[data-edge-id^="production_graph_edge_"] path.edge-flow').count() < 1: raise AssertionError("graph dependency edges are not rendered")
    text = page.locator("body").inner_text()
    if any(token in text for token in ("schema_version", "graph_digest", "browser-character-1", "m5-sequence-layout")): raise AssertionError("raw graph details leaked")
    page.get_by_role("button", name="打开项目导航").click()
    expect(page.locator(".graph-production-summary")).to_contain_text("序列")
    expect(page.locator(".graph-production-summary")).to_contain_text("制作任务")
    expect(page.locator(".graph-production-summary")).to_contain_text("交付清单")
    page.keyboard.press("Escape"); ensure_agent_visible(page)
    page.get_by_role("tab", name="故事板").click(); page.wait_for_selector(".storyboard-shot")
    if page.locator(".storyboard-shot").count() != 2 or page.locator(".scene-list button").count() != 2:
        raise AssertionError("Storyboard did not project the graph scene hierarchy")
    page.get_by_role("tab", name="画布").click(); page.wait_for_selector('.node[data-node-id^="production_graph_"]')
    projected = page.locator('.node[data-node-id^="production_graph_"]').first
    projected.locator(".node-title").click()
    if page.locator(".prompt-bar").count(): raise AssertionError("read-only graph node exposed legacy prompt actions")
    boxes = page.evaluate("""() => { const node = document.querySelector('.node[data-node-id^="production_graph_"].selected')?.getBoundingClientRect();
      const agent = document.querySelector('.studio-agent-chat')?.getBoundingClientRect();
      return { selected: Boolean(node), intersects: Boolean(node && agent && node.left < agent.right && node.right > agent.left && node.top < agent.bottom && node.bottom > agent.top),
        horizontalScroll: document.documentElement.scrollWidth > window.innerWidth + 1 }; }""")
    if not boxes["selected"] or boxes["intersects"] or boxes["horizontalScroll"]: raise AssertionError(f"graph Canvas safe-area failed: {boxes}")
    return {"single_shell": True, "canvas_graph_nodes": True, "dependency_edges": True, "professional_summary": True,
        "storyboard_same_projection": True, "raw_ids_hidden": True, "selected_node_safe_area": True, "legacy_prompt_actions_hidden": True}


def assert_graph_lifecycle(page: Page, base_url: str) -> dict[str, Any]:
    page.get_by_role("tab", name="画布").click()
    page.locator('.node[data-node-id="production_graph_browser-character-1"] .node-title').click()
    page.get_by_role("button", name="预览所选对象影响").click()
    expect(page.locator(".agent-command-preview")).to_contain_text("确认修订顾青")
    page.locator(".agent-command-preview").get_by_role("button", name="确认执行").click()
    page.wait_for_function("!document.querySelector('.agent-command-preview')")
    run_drawer_action(page, "选择最新候选"); run_drawer_action(page, "退回修改"); run_drawer_action(page, "安排返工"); run_drawer_action(page, "提交交付核验")
    page.get_by_role("tab", name="故事板").click(); page.get_by_role("button", name="预览修改影响").click()
    expect(page.locator(".agent-command-preview")).to_contain_text("确认镜头局部修改")
    page.locator(".agent-command-preview").get_by_role("button", name="确认执行").click(); page.wait_for_selector(".agent-receipt")
    expect(page.locator(".agent-recovery-hint").first).to_contain_text("安全重试")
    page.wait_for_function("document.body.innerText.includes('制作图已更新到版本')")
    workspace = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/m5/sequence-workspace")
    review_states = {item["state"] for item in workspace["sequence"]["reviews"]}
    delivery_states = {item["state"] for item in workspace["sequence"]["delivery_plan"]}
    if "redo_planned" not in review_states or "review_ready" not in delivery_states: raise AssertionError("review/redo/delivery lifecycle did not persist")
    return {"canvas_character_impact": True, "candidate_selection": True, "review_reject": True, "redo": True, "delivery_plan": True,
        "impact_preview": True, "explicit_agent_confirmation": True, "receipt_recovery": True}


def assert_planning_import(page: Page, base_url: str) -> dict[str, Any]:
    page.wait_for_selector(".graph-canvas-status.planning_required")
    expect(page.get_by_role("button", name="导入结构化制作方案")).to_be_visible()
    payload = {"name": "typed-film-plan.json", "mimeType": "application/json",
               "buffer": json.dumps(film_candidate(), ensure_ascii=False).encode("utf-8")}
    page.locator('input[aria-label="选择结构化制作方案文件"]').set_input_files(payload)
    expect(page.locator(".agent-command-preview")).to_contain_text("确认导入制作方案")
    expect(page.locator(".agent-command-preview")).to_contain_text("2 个角色、2 个场景和 3 个镜头")
    page.locator(".agent-command-preview").get_by_role("button", name="确认执行").click()
    page.wait_for_selector(".graph-canvas-status.ready")
    workspace = http_json(f"{base_url}/projects/{PLANNING_PROJECT}/m5/sequence-workspace")
    if workspace["graph_version"] != workspace["storyboard"]["graph_version"]:
        raise AssertionError("imported candidate projections diverged")
    return {"planning_required": True, "typed_file_import": True, "agent_preview": True,
            "explicit_confirmation": True, "same_graph_projection": True}


def assert_projection_pruned_on_user_save(page: Page, base_url: str) -> bool:
    page.get_by_role("tab", name="画布").click()
    before = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/studio-state")
    legacy = page.locator('.node[data-node-id="legacy_text"]')
    if legacy.locator(".node-content-editor").count(): raise AssertionError("legacy Studio node remained writable after graph migration")
    page.wait_for_timeout(900)
    after = http_json(f"{base_url}/projects/{GRAPH_PROJECT}/studio-state")
    if before["state_version"] != after["state_version"]: raise AssertionError("graph project wrote studio_state")
    persisted = after["state"]
    if any(str(node_id).startswith("production_graph_") for node_id in persisted.get("nodes", {})): raise AssertionError("graph nodes persisted to studio_state")
    if any(str(edge.get("relation_type", "")).startswith("production_graph_") for edge in persisted.get("edges", {}).values()): raise AssertionError("graph edges persisted to studio_state")
    if "production_graph_projection" in persisted.get("production", {}): raise AssertionError("graph summary persisted to studio_state")
    return True


def run_drawer_action(page: Page, label: str) -> None:
    if page.locator("#studio-context-drawer").count() == 0: page.get_by_role("button", name="打开项目导航").click()
    page.get_by_role("button", name=label).click(); expect(page.locator(".agent-command-preview")).to_be_visible()
    page.locator(".agent-command-preview").get_by_role("button", name="确认执行").click()
    page.wait_for_function("!document.querySelector('.agent-command-preview')")
    page.wait_for_timeout(100)


def ensure_agent_visible(page: Page) -> None:
    if page.locator(".studio-agent-chat:visible").count(): return
    page.get_by_role("button", name="Agent").click(); expect(page.locator(".studio-agent-chat")).to_be_visible()


def start_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy(); env.update({"AFS_RUNTIME_SERVICE_ROOT": str(runtime_root), "AFS_RUNTIME_ROOT": str(runtime_root),
        "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1", "AFS_RUNTIME_SERVICE_PORT": str(port), "AFS_AUTH_ENABLED": "false", "AFS_AUTH_ALLOW_OPEN_SIGNUP": "false"})
    for key in ("AFS_ALLOW_REMOTE_LLM", "AFS_ALLOW_REMOTE_IMAGE", "AFS_ALLOW_REMOTE_VIDEO", "AFS_ALLOW_REMOTE_AUDIO", "AFS_ALLOW_REMOTE_ASR", "AFS_ALLOW_REMOTE_VISION", "AFS_ALLOW_EXTERNAL_DOWNLOAD"): env.pop(key, None)
    return subprocess.Popen([sys.executable, "-m", "apps.cli.main", "runtime-service", "--host", "127.0.0.1", "--port", str(port)], cwd=repo, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def static_route(repo: Path):
    studio_root = (repo / "apps/studio").resolve()
    def handler(route) -> None:
        relative = urlsplit(route.request.url).path.removeprefix("/studio/")
        path = (studio_root / relative).resolve()
        try: path.relative_to(studio_root)
        except ValueError: route.fulfill(status=404, body=b""); return
        if not path.is_file(): route.fulfill(status=404, body=b""); return
        content_type = "text/javascript; charset=utf-8" if path.suffix == ".js" else "text/css; charset=utf-8"
        route.fulfill(status=200, content_type=content_type, body=path.read_bytes())
    return handler


def http_json(url: str) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=20) as response: return json.loads(response.read().decode("utf-8"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__": raise SystemExit(main())
