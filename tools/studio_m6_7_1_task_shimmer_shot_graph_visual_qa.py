from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, start_runtime, stop_runtime, wait_for_http
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import has_horizontal_overflow, screenshot, storage_key, viewport_key
from studio_m6_7_creative_task_reliability_browser_qa import fake_script_preview, graph_counts, reveal_node_actions, viewport_probe


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
PREVIEW_DELAY_SEC = 1.05


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-7-1-runtime-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-7-1-browser-{int(time.time())}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or report_path.with_suffix("")).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(runtime_root, base_url, screenshot_dir, args.round_label, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "report": str(report_path),
            "screenshots": str(screenshot_dir),
            "P0": report["P0"],
            "P1": report["P1"],
            "P2": report["P2"],
            "max_shimmer_extension_px": report["max_shimmer_extension_px"],
            "min_shot_apply_zoom": report["min_shot_apply_zoom"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.7.1 visual correction browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--round-label", default="A")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args()


def run_browser_qa(runtime_root: Path, base_url: str, screenshot_dir: Path, round_label: str, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    cases: dict[str, Any] = {}
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=chrome_path(), args=["--proxy-server=direct://", "--proxy-bypass-list=*"])
        try:
            for viewport in VIEWPORTS:
                key = viewport_key(viewport)
                project_id = f"m6-7-1-visual-{round_label.lower()}-{key}-{int(time.time() * 1000)}"
                prepare_project(runtime_root, project_id, with_node=True)
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("response", lambda response: response_errors.append({"status": response.status, "url": response.url}) if response.status >= 400 and not response.url.endswith("/favicon.ico") else None)
                try:
                    result, captured = verify_viewport(page, base_url, project_id, viewport, screenshot_dir, round_label)
                    cases[f"{project_id}:{key}"] = result
                    screenshots.update(captured)
                finally:
                    page.close()
            empty_project_id = f"m6-7-1-empty-{round_label.lower()}-{int(time.time() * 1000)}"
            prepare_project(runtime_root, empty_project_id, with_node=False)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_default_timeout(timeout_ms)
            try:
                page.goto(f"{base_url}/studio/?project={empty_project_id}&qa=m6-7-1-empty-{round_label}", wait_until="networkidle")
                expect(page.locator("#product-shell-root")).to_be_visible()
                expect(page.locator(".graph-canvas-status.planning-required.compact")).to_be_visible()
                screenshots["empty:compact_onboarding"] = screenshot(page, screenshot_dir, f"{round_label}-390x844-empty-compact-onboarding.png")
            finally:
                page.close()
        finally:
            browser.close()
    issues = issue_ledger(cases, console_errors, response_errors)
    p0 = sum(1 for item in issues if item["severity"] == "P0")
    p1 = sum(1 for item in issues if item["severity"] == "P1")
    p2 = sum(1 for item in issues if item["severity"] == "P2")
    if p0 or p1 or p2:
        raise AssertionError(f"M6.7.1 visual QA failed: {json.dumps(issues, ensure_ascii=False)}")
    return {
        "artifact_type": "afs_m6_7_1_task_shimmer_shot_graph_visual_qa",
        "schema_version": "afs.m6_7_1.visual_browser_qa.v0.1",
        "round": round_label,
        "status": "passed",
        "cases": cases,
        "screenshots": screenshots,
        "visual_mismatch_ledger": visual_mismatch_ledger(cases, screenshots),
        "issue_ledger": issues,
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "max_shimmer_extension_px": max(item["max_shimmer_extension_px"] for item in cases.values()),
        "min_shot_apply_zoom": min(item["shot_apply_zoom"] for item in cases.values()),
        "provider_dispatch_count": 0,
        "cost_usd": 0,
    }


def prepare_project(runtime_root: Path, project_id: str, with_node: bool) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": project_id, "project_type": "freeform_canvas_ai_copilot", "goal": f"M6.7.1 QA {project_id}", "status": "in_progress"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project create failed: {created.status_code} {created.text}")
    state = seeded_studio_state(project_id) if with_node else empty_studio_state(project_id)
    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state save failed: {saved.status_code} {saved.text}")


def empty_studio_state(project_id: str) -> dict[str, Any]:
    return {
        "meta": {"projectId": project_id, "projectName": "M6.7.1 空项目入口", "canvasName": "自由创作画布", "seq": 1},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "order": [],
        "nodes": {},
        "edges": {},
        "selection": {"nodeIds": [], "edgeId": None},
        "ui": {"saveState": "已保存"},
    }


def seeded_studio_state(project_id: str) -> dict[str, Any]:
    story = "孙悟空大战猪八戒。两人因为一块油饼和通关文牒误会升级，在破庙门口棍耙相向，最后发现小妖躲在梁上偷笑。"
    return {
        "meta": {"projectId": project_id, "projectName": "M6.7.1 分镜视觉修正", "canvasName": "自由创作画布", "seq": 6},
        "viewport": {"x": 118, "y": 86, "scale": 1},
        "order": ["story_text"],
        "nodes": {
            "story_text": {
                "id": "story_text",
                "type": "text",
                "title": "孙悟空大战猪八戒",
                "x": 260,
                "y": 210,
                "w": 310,
                "h": 260,
                "status": "draft",
                "content": story,
                "prompt": story,
                "params": {},
            }
        },
        "edges": {},
        "selection": {"nodeIds": ["story_text"], "edgeId": None},
        "ui": {"saveState": "已保存"},
    }


def verify_viewport(
    page: Page,
    base_url: str,
    project_id: str,
    viewport: dict[str, int],
    screenshot_dir: Path,
    round_label: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    key = viewport_key(viewport)
    screenshots: dict[str, str] = {}
    install_visual_fetch_stub(page)
    page.goto(f"{base_url}/studio/?project={project_id}&qa=m6-7-1-{round_label}-{int(time.time())}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator('.node[data-node-id="story_text"]')).to_be_visible()
    expect(page.locator(".graph-canvas-status.planning-required.expanded")).to_have_count(0)
    expect(page.locator(".studio-header-notice")).to_have_count(0)
    menu_checks = verify_menus(page, project_id, screenshot_dir, round_label, key)
    screenshots.update(menu_checks.pop("screenshots"))
    script_running = verify_running_shimmer(page, project_id, screenshot_dir, round_label, key, "script_revision")
    screenshots.update({f"{key}:script_running_t0": script_running["t0"], f"{key}:script_running_t1": script_running["t1"]})
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'preview'""", arg=storage_key(project_id))
    preview_summary = page.locator(".agent-current-task-head small").inner_text()
    phase_labels = page.locator(".agent-task-phases li").all_inner_texts()
    screenshots[f"{key}:script_preview"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-05-script-preview.png")
    cancel_task(page)
    shot_running = verify_running_shimmer(page, project_id, screenshot_dir, round_label, key, "shot_breakdown")
    screenshots.update({f"{key}:shot_running_t0": shot_running["t0"], f"{key}:shot_running_t1": shot_running["t1"]})
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'preview'""", arg=storage_key(project_id))
    before = graph_counts(page, project_id)
    page.get_by_role("button", name="应用").click()
    page.wait_for_function("""({ key, beforeNodes }) => Object.keys(JSON.parse(localStorage.getItem(key) || '{}').nodes || {}).length > beforeNodes""", arg={"key": storage_key(project_id), "beforeNodes": before["nodes"]})
    page.wait_for_selector(".node.selected[data-node-id]")
    applied = shot_layout_probe(page, project_id, viewport)
    screenshots[f"{key}:shot_applied"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-07-shot-applied.png")
    delete_screenshot = verify_delete_confirm(page, screenshot_dir, round_label, key)
    screenshots[f"{key}:delete_confirm"] = delete_screenshot
    return (
        {
            "viewport": key,
            "project_id": project_id,
            "project_switcher_no_viewport_change": menu_checks["project_switcher_no_viewport_change"],
            "account_menu_visible": menu_checks["account_menu_visible"],
            "script_shimmer": script_running,
            "shot_shimmer": shot_running,
            "max_shimmer_extension_px": max(script_running["extension_px"], shot_running["extension_px"]),
            "preview_status_deduped": preview_summary.count("预览可审") <= 1 and phase_labels.count("预览可审") <= 1,
            "shot_apply_zoom": applied["viewport_scale"],
            "shot_layout": applied,
            "nonempty_banner_absent": compact_planning_surface_ok(page),
            "no_horizontal_overflow": not has_horizontal_overflow(page),
        },
        screenshots,
    )


def compact_planning_surface_ok(page: Page) -> bool:
    return bool(page.evaluate("""() => {
      const expanded = document.querySelector('.graph-canvas-status.planning-required.expanded');
      const status = document.querySelector('.graph-canvas-status.planning-required');
      const box = status?.getBoundingClientRect?.();
      return !expanded && (!box || box.height <= 96);
    }"""))


def install_visual_fetch_stub(page: Page) -> None:
    payload = json.dumps(
        {
            "delayMs": int(PREVIEW_DELAY_SEC * 1000),
            "scriptPreview": fake_script_preview(),
            "shotPreview": fake_shot_preview_nine(),
        },
        ensure_ascii=False,
    )
    page.add_init_script("""(() => {
      const config = __M671_STUB_CONFIG__;
      const originalFetch = window.fetch.bind(window);
      window.fetch = async (input, init = {}) => {
        const url = typeof input === 'string' ? input : input?.url || '';
        if (!String(url).includes('/embedded-creative-actions/preview')) return originalFetch(input, init);
        const payload = JSON.parse(init?.body || '{}');
        const actionType = payload.action_type || 'script_revision';
        await new Promise((resolve) => setTimeout(resolve, config.delayMs));
        const preview = JSON.parse(JSON.stringify(actionType === 'shot_breakdown' ? config.shotPreview : config.scriptPreview));
        const now = Date.now();
        const body = {
          mode: 'llm',
          action_type: actionType,
          creative_task: {
            schema_version: 'afs.creative_task.v0.1',
            task_id: `visual_task_${actionType}_${now}`,
            action_type: actionType,
            state: 'preview_ready',
            phase: 'preview_ready',
            completed_phases: ['queued', 'context', 'dispatching', 'validating', 'preview_ready'],
          },
          preview,
          provider_calls_started: true,
          provider_lineage: { service_id: 'server_codex', provider: 'codex_local', provider_calls_started: true, request_id: `visual_${actionType}_${now}` },
          latency_ms: config.delayMs,
          cost_usd: 0,
        };
        return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
      };
    })()""".replace("__M671_STUB_CONFIG__", payload))


def verify_menus(page: Page, project_id: str, screenshot_dir: Path, round_label: str, key: str) -> dict[str, bool]:
    before = viewport_probe(page, project_id)
    project_button = page.locator(".studio-project-button")
    project_button.click()
    expect(page.locator(".studio-project-menu")).to_be_visible()
    project_menu = screenshot(page, screenshot_dir, f"{round_label}-{key}-01-project-menu-open.png")
    after = viewport_probe(page, project_id)
    page.keyboard.press("Escape")
    expect(page.locator(".studio-project-menu")).to_have_count(0)
    account = page.locator(".studio-account-button")
    account.click()
    expect(page.locator(".studio-account-menu")).to_be_visible()
    account_menu = screenshot(page, screenshot_dir, f"{round_label}-{key}-02-account-menu-open.png")
    account_visible = page.locator(".studio-account-menu").bounding_box() is not None
    page.keyboard.press("Escape")
    expect(page.locator(".studio-account-menu")).to_have_count(0)
    return {
        "project_switcher_no_viewport_change": equivalent_viewport_probe(before, after),
        "account_menu_visible": account_visible,
        "screenshots": {
            f"{key}:project_menu": project_menu,
            f"{key}:account_menu": account_menu,
        },
    }


def verify_running_shimmer(page: Page, project_id: str, screenshot_dir: Path, round_label: str, key: str, action_type: str) -> dict[str, Any]:
    reveal_node_actions(page)
    role = "shot-breakdown-action" if action_type == "shot_breakdown" else "script-revision-action"
    button = page.locator(f'.node[data-node-id="story_text"] [data-role="{role}"]')
    expect(button).to_be_visible()
    page.evaluate("() => { window.__m671ClickAt = performance.now(); window.__m671RunningAt = 0; window.addEventListener('afs:embedded-creative-task-running', () => { window.__m671RunningAt = performance.now(); }, { once: true }); }")
    button.click()
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'running'""", arg=storage_key(project_id), timeout=5_000)
    page.wait_for_timeout(140)
    first = shimmer_probe(page)
    t0_path = screenshot(page, screenshot_dir, f"{round_label}-{key}-03-{action_type}-running-t0.png")
    page.wait_for_timeout(420)
    second = shimmer_probe(page)
    t1_path = screenshot(page, screenshot_dir, f"{round_label}-{key}-04-{action_type}-running-t1.png")
    feedback_ms = round(float(page.evaluate("() => Math.max(0, (window.__m671RunningAt || 0) - (window.__m671ClickAt || 0))")), 2)
    if feedback_ms <= 0 or feedback_ms > 150:
        raise AssertionError(f"{action_type} feedback exceeded 150ms: {feedback_ms}ms")
    for probe in (first, second):
        if not probe["class_running"] or probe["extension_px"] > 3.1 or probe["transform"] not in {"none", ""}:
            raise AssertionError(f"{action_type} shimmer geometry failed: {probe}")
        if "embeddedTaskPerimeterSweep" not in probe["animation_name"] and probe["animation_name"] != "none":
            raise AssertionError(f"{action_type} shimmer animation missing: {probe}")
    return {
        "feedback_ms": feedback_ms,
        "extension_px": max(first["extension_px"], second["extension_px"]),
        "animation_t0": first["animation_name"],
        "animation_t1": second["animation_name"],
        "transform_t0": first["transform"],
        "t0": t0_path,
        "t1": t1_path,
    }


def shimmer_probe(page: Page) -> dict[str, Any]:
    return page.evaluate("""() => {
      const node = document.querySelector('.node[data-node-id="story_text"]');
      const style = node ? getComputedStyle(node, '::after') : null;
      const toPx = (value) => Math.abs(Number.parseFloat(String(value || '0')) || 0);
      const extensions = [style?.top, style?.right, style?.bottom, style?.left].map(toPx);
      return {
        class_running: Boolean(node?.classList.contains('embedded-task-running')),
        pointer_events: style?.pointerEvents || '',
        transform: style?.transform || '',
        animation_name: style?.animationName || '',
        extension_px: Math.max(...extensions),
      };
    }""")


def cancel_task(page: Page) -> None:
    page.locator(".agent-current-task-review.preview").get_by_role("button", name="取消").click()
    page.wait_for_timeout(100)


def shot_layout_probe(page: Page, project_id: str, viewport: dict[str, int]) -> dict[str, Any]:
    state = page.evaluate("""key => {
      const state = JSON.parse(localStorage.getItem(key) || '{}');
      const nodes = Object.values(state.nodes || {});
      const selectedId = document.querySelector('.node.selected[data-node-id]')?.dataset?.nodeId || (state.selection?.nodeIds || [])[0] || '';
      const roles = nodes.map((node) => node.params?.nodeRole).filter(Boolean);
      const shots = nodes.filter((node) => node.params?.nodeRole === 'm6_6_shot_candidate');
      return {
        viewport_scale: Number(state.viewport?.scale || 0),
        roles,
        shot_count: shots.length,
        max_column: Math.max(...shots.map((node) => Number(node.params?.layout_column || 0))),
        max_row: Math.max(...shots.map((node) => Number(node.params?.layout_row || 0))),
        selected_id: selectedId,
        selected_role: nodes.find((node) => node.id === selectedId)?.params?.nodeRole || '',
        sequence_selected: selectedId && nodes.find((node) => node.id === selectedId)?.params?.nodeRole === 'm6_6_shot_sequence_candidate',
      };
    }""", storage_key(project_id))
    min_zoom = 0.5 if int(viewport["width"]) <= 560 else 0.7
    if state["viewport_scale"] < min_zoom:
      raise AssertionError(f"shot graph zoom is unreadable: {state}")
    if state["shot_count"] != 9:
      raise AssertionError(f"shot graph did not materialize nine shots: {state}")
    expected_max_column = 1 if int(viewport["width"]) <= 560 else 2
    if state["max_column"] > expected_max_column:
      raise AssertionError(f"shot grid columns exceeded layout contract: {state}")
    if not state["sequence_selected"]:
      raise AssertionError(f"new sequence group was not selected: {state}")
    return state


def verify_delete_confirm(page: Page, screenshot_dir: Path, round_label: str, key: str) -> str:
    page.locator(".studio-project-button").click()
    expect(page.locator(".studio-project-menu")).to_be_visible()
    page.locator(".studio-project-delete").click()
    expect(page.locator(".project-delete-modal")).to_be_visible()
    path = screenshot(page, screenshot_dir, f"{round_label}-{key}-08-delete-confirm.png")
    page.get_by_role("button", name="取消").click()
    return path


def fake_shot_preview_nine() -> dict[str, Any]:
    shots = []
    for index, title in enumerate([
        "油屑证据", "棍耙对峙", "八戒辩解", "梁上笑声", "半块油饼", "误会反转", "小妖逃窜", "联手追出", "破庙余响",
    ], start=1):
        shots.append({
            "title": title,
            "duration_sec": 4 + index % 4,
            "shot_size": ["特写", "中景", "全景"][index % 3],
            "camera_angle": ["俯拍", "平视", "低机位"][index % 3],
            "movement": ["轻推", "横移", "跟拍"][index % 3],
            "blocking": f"镜头 {index} 围绕误会升级与反转调度人物和道具。",
            "sound": "风声、脚步、金属碰撞与小妖偷笑",
            "transition": "动作切" if index < 9 else "接下场",
            "narrative_purpose": f"推进第 {index} 个叙事节拍，保持动作与关系变化连续。",
        })
    return {
        "preview_id": "m671_browser_shot_preview",
        "action_type": "shot_breakdown",
        "mode": "dynamic_shot_breakdown",
        "revised_text": "按证据、对峙、反转、追逐和余响拆成九个内容驱动镜头。",
        "change_summary": ["动态九镜头", "验证场景分组与镜头网格布局"],
        "rationale": "预览完成后应用为可见分镜候选子图。",
        "unresolved_decisions": [],
        "quality_flags": ["dynamic_count"],
        "shot_plan": {
            "total_shots": 9,
            "estimated_duration_sec": 48,
            "scenes": [{
                "title": "破庙前误会",
                "purpose": "从证据误判转向共同发现小妖",
                "shots": shots,
            }],
        },
    }


def equivalent_viewport_probe(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if before.get("selected") != after.get("selected"):
        return False
    for key in ("x", "y", "scale"):
        if abs(float((before.get("viewport") or {}).get(key, 0)) - float((after.get("viewport") or {}).get(key, 0))) > 0.01:
            return False
    before_box = before.get("box") or {}
    after_box = after.get("box") or {}
    return all(abs(float(before_box.get(key, 0)) - float(after_box.get(key, 0))) <= 1 for key in ("x", "y", "width", "height"))


def issue_ledger(cases: dict[str, Any], console_errors: list[str], response_errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if console_errors:
        issues.append(issue("P0", "console_errors", str(console_errors[:6])))
    if response_errors:
        issues.append(issue("P0", "response_errors", str(response_errors[:6])))
    for key, item in cases.items():
        checks = {
            "project_switcher_no_viewport_change": item.get("project_switcher_no_viewport_change"),
            "account_menu_visible": item.get("account_menu_visible"),
            "preview_status_deduped": item.get("preview_status_deduped"),
            "nonempty_banner_absent": item.get("nonempty_banner_absent"),
            "no_horizontal_overflow": item.get("no_horizontal_overflow"),
            "script_shimmer_geometry": item.get("script_shimmer", {}).get("extension_px", 99) <= 3.1,
            "shot_shimmer_geometry": item.get("shot_shimmer", {}).get("extension_px", 99) <= 3.1,
            "shot_graph_readable_zoom": item.get("shot_apply_zoom", 0) >= (0.5 if "390x" in key or "430x" in key else 0.7),
            "shot_graph_nine_items": item.get("shot_layout", {}).get("shot_count") == 9,
        }
        for field, ok in checks.items():
            if not ok:
                issues.append(issue("P1" if "geometry" in field or "zoom" in field else "P2", f"{key}_{field}", json.dumps(item, ensure_ascii=False)[:900]))
    return issues


def visual_mismatch_ledger(cases: dict[str, Any], screenshots: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "issue": "running_shimmer_escape",
            "design_intent": "节点运行态只显示贴边 2-3px 顺时针光，不覆盖内容或端口。",
            "status": "closed",
            "evidence": {
                "max_extension_px": max(item["max_shimmer_extension_px"] for item in cases.values()),
                "script_t0": screenshots.get("1440x900:script_running_t0", ""),
                "shot_t0": screenshots.get("1440x900:shot_running_t0", ""),
            },
        },
        {
            "issue": "nine_shot_vertical_stack_unreadable_zoom",
            "design_intent": "9 镜头候选按场景 lane 和镜头 grid 呈现，应用后 zoom floor 保持可读。",
            "status": "closed",
            "evidence": {
                "min_zoom": min(item["shot_apply_zoom"] for item in cases.values()),
                "desktop": screenshots.get("1440x900:shot_applied", ""),
                "phone": screenshots.get("390x844:shot_applied", ""),
            },
        },
        {
            "issue": "duplicate_preview_status",
            "design_intent": "同一语义阶段在任务头与阶段 chip 中各只出现一次。",
            "status": "closed",
            "evidence": all(item["preview_status_deduped"] for item in cases.values()),
        },
        {
            "issue": "nonempty_amber_onboarding",
            "design_intent": "已有节点/候选的项目不显示大面积 planning/onboarding banner。",
            "status": "closed",
            "evidence": all(item["nonempty_banner_absent"] for item in cases.values()),
        },
        {
            "issue": "topbar_task_notice_clutter",
            "design_intent": "任务反馈只在节点和右侧当前任务区显示；topbar 保留保存/账户等简洁状态。",
            "status": "closed",
            "evidence": "studio-header-notice count is zero in accepted paths",
        },
        {
            "issue": "desktop_account_menu_not_captured",
            "design_intent": "账户菜单位于 shell overlay 层，截图中明确可见，并可 Escape 关闭。",
            "status": "closed",
            "evidence": screenshots.get("1440x900:account_menu", ""),
        },
    ]


def issue(severity: str, issue_id: str, evidence: str) -> dict[str, str]:
    return {"severity": severity, "issue": issue_id, "evidence": evidence}


if __name__ == "__main__":
    raise SystemExit(main())
