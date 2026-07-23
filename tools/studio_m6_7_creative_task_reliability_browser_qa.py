from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, start_runtime, stop_runtime, wait_for_http
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import graph_counts, has_horizontal_overflow, screenshot, storage_key, viewport_key


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
PREVIEW_DELAY_SEC = 1.15


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-7-runtime-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-7-browser-{int(time.time())}.json").resolve()
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
            "max_feedback_ms": report["max_feedback_ms"],
            "provider_dispatch_count": report["provider_dispatch_count"],
            "cost_usd": report["cost_usd"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.7 creative task reliability and product shell browser QA")
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
                project_id = f"m6-7-creative-task-{round_label.lower()}-{key}-{int(time.time() * 1000)}"
                prepare_project(runtime_root, project_id)
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
        finally:
            browser.close()
    issues = issue_ledger(cases, console_errors, response_errors)
    p0 = sum(1 for item in issues if item["severity"] == "P0")
    p1 = sum(1 for item in issues if item["severity"] == "P1")
    p2 = sum(1 for item in issues if item["severity"] == "P2")
    if p0 or p1 or p2:
        raise AssertionError(f"M6.7 browser QA failed: {json.dumps(issues, ensure_ascii=False)}")
    return {
        "artifact_type": "afs_m6_7_creative_task_reliability_browser_qa",
        "schema_version": "afs.m6_7.browser_qa.v0.1",
        "round": round_label,
        "status": "passed",
        "cases": cases,
        "screenshots": screenshots,
        "role_task_completion_matrix": role_matrix(cases),
        "issue_ledger": issues,
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "max_feedback_ms": max(item["max_feedback_ms"] for item in cases.values()),
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "browser_lane_boundary": "Delayed safe structured previews prove UI state, shell and mutation contracts only; real server_codex success is covered by the M6.7 runtime LLM smoke.",
    }


def prepare_project(runtime_root: Path, project_id: str) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": project_id, "project_type": "freeform_canvas_ai_copilot", "goal": f"M6.7 QA {project_id}", "status": "in_progress"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project create failed: {created.status_code} {created.text}")
    state = seeded_studio_state(project_id)
    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state save failed: {saved.status_code} {saved.text}")


def seeded_studio_state(project_id: str) -> dict[str, Any]:
    story = "孙悟空大战猪八戒。两人因为一块油饼和通关文牒误会升级，在破庙门口棍耙相向，最后发现小妖躲在梁上偷笑。"
    return {
        "meta": {"projectId": project_id, "projectName": "M6.7 创作任务可靠性测试", "canvasName": "自由创作画布", "seq": 6},
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
    install_embedded_fetch_stub(page)
    page.goto(f"{base_url}/studio/?project={project_id}&qa=m6-7-{round_label}-{int(time.time())}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator('.node[data-node-id="story_text"]')).to_be_visible()
    reveal_node_actions(page)
    expect(page.locator('.node[data-node-id="story_text"] [data-role="shot-breakdown-action"]')).to_be_visible()
    expect(page.locator(".studio-unified-header")).not_to_contain_text("项目导航")
    expect(page.locator("#product-shell-root")).not_to_contain_text("自动拆分分镜")
    expect(page.locator(".studio-live-notice")).to_have_count(0)
    screenshots[f"{key}:initial"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-01-initial.png")

    shell_checks = verify_shell_menus(page, project_id, screenshot_dir, round_label, key)
    script_cancel = verify_running_then_cancel(page, project_id, "script_revision")
    script_apply = verify_preview_apply(page, project_id, "script_revision")
    screenshots[f"{key}:script_applied"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-04-script-applied.png")
    shot_apply = verify_preview_apply(page, project_id, "shot_breakdown")
    screenshots[f"{key}:shot_applied"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-06-shot-applied.png")
    delete_ok = verify_project_delete(page, base_url, project_id, screenshot_dir, round_label, key)
    return (
        {
            "viewport": key,
            "project_id": project_id,
            "max_feedback_ms": max(script_cancel["feedback_ms"], script_apply["feedback_ms"], shot_apply["feedback_ms"]),
            "script_cancel_late_response_ignored": script_cancel["late_response_ignored"],
            "script_same_node_apply": script_apply["script_same_node_apply"],
            "shot_candidate_graph_apply": shot_apply["shot_candidate_graph_apply"],
            "project_switcher_no_viewport_change": shell_checks["project_switcher_no_viewport_change"],
            "project_menu_outside_escape_close": shell_checks["project_menu_outside_escape_close"],
            "account_menu_real": shell_checks["account_menu_real"],
            "delete_project_supported": delete_ok,
            "running_visual": script_apply["running_visual"] and shot_apply["running_visual"],
            "no_horizontal_overflow": not has_horizontal_overflow(page),
            "provider_dispatch_count": 0,
            "cost_usd": 0,
        },
        screenshots,
    )


def install_embedded_fetch_stub(page: Page) -> None:
    payload = json.dumps(
        {
            "delayMs": int(PREVIEW_DELAY_SEC * 1000),
            "scriptPreview": fake_script_preview(),
            "shotPreview": fake_shot_preview(),
        },
        ensure_ascii=False,
    )
    script = """(() => {
          const config = __M67_STUB_CONFIG__;
          const delayMs = config.delayMs;
          const scriptPreview = config.scriptPreview;
          const shotPreview = config.shotPreview;
          const originalFetch = window.fetch.bind(window);
          window.__m67EmbeddedRequests = [];
          window.fetch = async (input, init = {}) => {
            const url = typeof input === 'string' ? input : input?.url || '';
            if (!String(url).includes('/embedded-creative-actions/preview')) {
              return originalFetch(input, init);
            }
            const payload = JSON.parse(init?.body || '{}');
            const actionType = payload.action_type || 'script_revision';
            window.__m67EmbeddedRequests.push({ action_type: actionType, at: performance.now() });
            await new Promise((resolve) => setTimeout(resolve, delayMs));
            const projectId = String(url).split('/projects/')[1]?.split('/')[0] || '';
            const preview = JSON.parse(JSON.stringify(actionType === 'shot_breakdown' ? shotPreview : scriptPreview));
            const now = Date.now();
            const body = {
              project_id: projectId,
              job: { job_id: `browser_${actionType}_${now}`, status: 'succeeded' },
              mode: 'llm',
              action_type: actionType,
              target: { node_id: 'story_text', node_type: 'text', action_type: actionType, mode: preview.mode },
              creative_task: {
                schema_version: 'afs.creative_task.v0.1',
                task_id: `browser_task_${now}`,
                project_id: projectId,
                node_id: 'story_text',
                node_type: 'text',
                action_type: actionType,
                mode: preview.mode,
                state: 'preview_ready',
                phase: 'preview_ready',
                completed_phases: ['queued', 'context', 'dispatching', 'validating', 'preview_ready'],
                result_scope: actionType === 'shot_breakdown' ? 'candidate_storyboard_subgraph' : 'same_node_revision',
              },
              preview,
              provider_gate: { status: 'browser_fixture_no_provider' },
              provider_calls_started: true,
              provider_lineage: {
                service_id: 'server_codex',
                provider: 'codex_local',
                model_surface: 'browser-structured-preview',
                request_id: `browser_${actionType}_${now}`,
                structured_output_contract_id: 'afs.runtime.embedded_creative_action.v0.2',
                provider_calls_started: true,
                external_paid_cost_usd: 0,
              },
              safe_manifest: { provider_calls_started: true, provider_raw_response_stored: false, canvas_mutation_enabled: false },
              graph_mutation: { before_version: 0, after_version: 0, before_digest: '', after_digest: '', mutated: false },
              latency_ms: delayMs,
              cost_usd: 0,
              artifacts: {},
              non_claims: ['browser_fixture_not_provider_quality'],
            };
            return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
          };
        })()""".replace("__M67_STUB_CONFIG__", payload)
    page.add_init_script(script)


def fake_embedded_response(project_id: str, action_type: str) -> dict[str, Any]:
    preview = fake_shot_preview() if action_type == "shot_breakdown" else fake_script_preview()
    now = int(time.time() * 1000)
    return {
        "project_id": project_id,
        "job": {"job_id": f"browser_{action_type}_{now}", "status": "succeeded"},
        "mode": "llm",
        "action_type": action_type,
        "target": {"node_id": "story_text", "node_type": "text", "action_type": action_type, "mode": preview["mode"]},
        "creative_task": {
            "schema_version": "afs.creative_task.v0.1",
            "task_id": f"browser_task_{now}",
            "project_id": project_id,
            "node_id": "story_text",
            "node_type": "text",
            "action_type": action_type,
            "mode": preview["mode"],
            "state": "preview_ready",
            "phase": "preview_ready",
            "completed_phases": ["queued", "context", "dispatching", "validating", "preview_ready"],
            "result_scope": "candidate_storyboard_subgraph" if action_type == "shot_breakdown" else "same_node_revision",
        },
        "preview": preview,
        "provider_gate": {"status": "browser_fixture_no_provider"},
        "provider_calls_started": True,
        "provider_lineage": {
            "service_id": "server_codex",
            "provider": "codex_local",
            "model_surface": "browser-structured-preview",
            "request_id": f"browser_{action_type}_{now}",
            "structured_output_contract_id": "afs.runtime.embedded_creative_action.v0.2",
            "provider_calls_started": True,
            "external_paid_cost_usd": 0,
        },
        "safe_manifest": {"provider_calls_started": True, "provider_raw_response_stored": False, "canvas_mutation_enabled": False},
        "graph_mutation": {"before_version": 0, "after_version": 0, "before_digest": "", "after_digest": "", "mutated": False},
        "latency_ms": PREVIEW_DELAY_SEC * 1000,
        "cost_usd": 0,
        "artifacts": {},
        "non_claims": ["browser_fixture_not_provider_quality"],
    }


def fake_script_preview() -> dict[str, Any]:
    candidate = {
        "title": "破庙误会",
        "version_label": "v1",
        "logline": "悟空误会八戒偷吃油饼，两人在破庙前冲突升级，并一起发现真正捣乱的小妖。",
        "characters": [
            {"name": "孙悟空", "goal": "查清通关文牒和油饼被动过的真相", "conflict": "急躁误判八戒，差点错过小妖线索", "change": "从逼问转为联手追查"},
            {"name": "猪八戒", "goal": "证明自己清白并保住队伍信任", "conflict": "馋嘴名声让解释缺乏可信度", "change": "从躲闪辩解转为指出屋梁上的动静"},
        ],
        "scenes": [{
            "heading": "外景 - 荒山破庙 - 黄昏",
            "space_type": "外景",
            "location": "荒山破庙",
            "time_of_day": "黄昏",
            "purpose": "把油饼误会推进成师兄弟冲突，并转向共同目标",
            "blocks": [
                {"type": "action", "text": "破庙门口风沙卷起，油饼屑粘在通关文牒边角。孙悟空捻起碎屑，金箍棒在地上划出火星。"},
                {"type": "character", "text": "孙悟空"},
                {"type": "dialogue", "text": "呆子，文牒边上都是油，你还说没碰？"},
                {"type": "character", "text": "猪八戒"},
                {"type": "dialogue", "text": "猴哥，我馋归馋，可这回真不是我。你听，梁上有人笑。"},
                {"type": "action", "text": "两人同时停手，屋梁暗处一只小妖捂着半块油饼缩回阴影。悟空与八戒对视，怒气转成默契。"},
            ],
        }],
    }
    return {
        "preview_id": "m67_browser_script_preview",
        "action_type": "script_revision",
        "mode": "professional_expansion",
        "revised_text": "《破庙误会》\n外景 - 荒山破庙 - 黄昏\n孙悟空与猪八戒围绕油饼和通关文牒发生冲突，最后发现小妖线索。",
        "change_summary": ["改成专业剧本格式", "强化角色目标、冲突、变化与对白"],
        "rationale": "预览保留同一节点身份；应用前不创建新剧本节点。",
        "unresolved_decisions": [],
        "quality_flags": ["screenplay_format"],
        "screenplay_candidate": candidate,
    }


def fake_shot_preview() -> dict[str, Any]:
    return {
        "preview_id": "m67_browser_shot_preview",
        "action_type": "shot_breakdown",
        "mode": "dynamic_shot_breakdown",
        "revised_text": "按证据、对峙、梁上笑声、发现小妖、联手追出拆成五个内容驱动镜头。",
        "change_summary": ["动态五镜头", "每镜头记录景别、机位、运动、声音、转场和目的"],
        "rationale": "预览完成后应用为可见分镜候选子图。",
        "unresolved_decisions": [],
        "quality_flags": ["dynamic_count"],
        "shot_plan": {
            "total_shots": 5,
            "estimated_duration_sec": 34,
            "scenes": [{
                "title": "破庙前误会",
                "purpose": "从证据误判转向共同发现小妖",
                "shots": [
                    {"title": "油屑证据", "duration_sec": 5, "shot_size": "特写", "camera_angle": "俯拍", "movement": "轻推", "blocking": "悟空捻起文牒边的油饼屑", "sound": "风沙和纸张摩擦", "transition": "动作切", "narrative_purpose": "建立误会证据"},
                    {"title": "棍耙对峙", "duration_sec": 8, "shot_size": "中景", "camera_angle": "平视", "movement": "横移", "blocking": "悟空逼近，八戒后退护住钉耙", "sound": "金属轻碰和急促呼吸", "transition": "节奏切", "narrative_purpose": "升级冲突"},
                    {"title": "梁上笑声", "duration_sec": 6, "shot_size": "双人中近景", "camera_angle": "仰角转摇", "movement": "从二人摇向梁上", "blocking": "两人同时停手抬头", "sound": "小妖偷笑", "transition": "悬念切", "narrative_purpose": "揭示真正线索"},
                    {"title": "半块油饼", "duration_sec": 6, "shot_size": "近景", "camera_angle": "低机位", "movement": "快速上摇", "blocking": "小妖露出半块油饼又缩回暗处", "sound": "木梁吱呀", "transition": "反应切", "narrative_purpose": "证明八戒被陷害"},
                    {"title": "联手追出", "duration_sec": 9, "shot_size": "全景", "camera_angle": "侧后方", "movement": "跟拍推进", "blocking": "悟空跃上墙头，八戒抄近路追出", "sound": "脚步、风声、钉耙划地", "transition": "接下场", "narrative_purpose": "把误会转为共同目标"},
                ],
            }],
        },
    }


def verify_shell_menus(page: Page, project_id: str, screenshot_dir: Path, round_label: str, key: str) -> dict[str, bool]:
    before = viewport_probe(page, project_id)
    project_button = page.locator(".studio-project-button")
    project_button.click()
    expect(page.locator(".studio-project-menu")).to_be_visible()
    screenshot(page, screenshot_dir, f"{round_label}-{key}-02-project-menu.png")
    after_open = viewport_probe(page, project_id)
    page.mouse.click(20, 20)
    expect(page.locator(".studio-project-menu")).to_have_count(0)
    project_button.click()
    expect(page.locator(".studio-project-menu")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator(".studio-project-menu")).to_have_count(0)
    account = page.locator(".studio-account-button")
    account.click()
    expect(page.locator(".studio-account-menu")).to_be_visible()
    expect(page.locator(".studio-account-menu")).to_contain_text("账户与工作区")
    screenshot(page, screenshot_dir, f"{round_label}-{key}-03-account-menu.png")
    page.keyboard.press("Escape")
    return {
        "project_switcher_no_viewport_change": equivalent_viewport_probe(before, after_open),
        "project_menu_outside_escape_close": page.locator(".studio-project-menu").count() == 0,
        "account_menu_real": page.locator(".studio-account-menu").count() == 0,
    }


def verify_running_then_cancel(page: Page, project_id: str, action_type: str) -> dict[str, Any]:
    before = graph_counts(page, project_id)
    feedback = start_action(page, project_id, action_type)
    expect(page.locator(".agent-current-task-review.running")).to_be_visible()
    page.get_by_role("button", name="取消任务").click()
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'cancelled'""", arg=storage_key(project_id))
    time.sleep(PREVIEW_DELAY_SEC + 0.35)
    after = graph_counts(page, project_id)
    state = embedded_state(page, project_id)
    return {"feedback_ms": feedback["feedback_ms"], "late_response_ignored": state.get("status") == "cancelled" and after == before}


def verify_preview_apply(page: Page, project_id: str, action_type: str) -> dict[str, Any]:
    before = graph_counts(page, project_id)
    feedback = start_action(page, project_id, action_type)
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'preview'""", arg=storage_key(project_id))
    expect(page.locator(".agent-current-task-review.preview")).to_be_visible()
    page.locator(".agent-current-task-review.preview").get_by_role("button", name="应用").click()
    if action_type == "script_revision":
        page.wait_for_function("""key => (JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.revisions || []).length >= 1""", arg=storage_key(project_id))
        after = graph_counts(page, project_id)
        content = page.evaluate("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.content || ''""", storage_key(project_id))
        return {
            "feedback_ms": feedback["feedback_ms"],
            "running_visual": feedback["running_visual"],
            "script_same_node_apply": after == before and "外景 - 荒山破庙 - 黄昏" in content,
            "shot_candidate_graph_apply": True,
        }
    page.wait_for_function("""({ key, beforeNodes }) => Object.keys(JSON.parse(localStorage.getItem(key) || '{}').nodes || {}).length > beforeNodes""", arg={"key": storage_key(project_id), "beforeNodes": before["nodes"]})
    after = graph_counts(page, project_id)
    roles = page.evaluate("""key => Object.values(JSON.parse(localStorage.getItem(key) || '{}').nodes || {}).map((node) => node.params?.nodeRole).filter(Boolean)""", storage_key(project_id))
    return {
        "feedback_ms": feedback["feedback_ms"],
        "running_visual": feedback["running_visual"],
        "script_same_node_apply": True,
        "shot_candidate_graph_apply": after["nodes"] > before["nodes"] and {"m6_6_shot_sequence_candidate", "m6_6_scene_candidate", "m6_6_shot_candidate"}.issubset(set(roles)),
    }


def start_action(page: Page, project_id: str, action_type: str) -> dict[str, Any]:
    reveal_node_actions(page)
    role = "shot-breakdown-action" if action_type == "shot_breakdown" else "script-revision-action"
    button = page.locator(f'.node[data-node-id="story_text"] [data-role="{role}"]')
    expect(button).to_be_visible()
    page.evaluate("""() => {
      window.__m67ActionClickAt = performance.now();
      window.__m67ActionRunningAt = 0;
      window.__m67RunningEvents = 0;
      if (!window.__m67RunningListenerInstalled) {
        window.__m67RunningListenerInstalled = true;
        window.addEventListener('afs:embedded-creative-task-running', () => {
          window.__m67RunningEvents += 1;
          window.__m67ActionRunningAt = performance.now();
        });
      }
    }""")
    button.click()
    page.wait_for_function("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction?.status === 'running'""", arg=storage_key(project_id), timeout=5_000)
    page.wait_for_timeout(140)
    visual = page.evaluate("""() => {
      const node = document.querySelector('.node[data-node-id="story_text"]');
      const button = node?.querySelector('.na-btn.is-busy');
      const style = node ? getComputedStyle(node, '::after') : null;
      return {
        classRunning: Boolean(node?.classList.contains('embedded-task-running')),
        animationName: style?.animationName || '',
        busyButton: Boolean(button),
        sidebarRunning: Boolean(document.querySelector('.agent-current-task-review.running')),
      };
    }""")
    feedback_ms = round(float(page.evaluate("() => Math.max(0, (window.__m67ActionRunningAt || 0) - (window.__m67ActionClickAt || 0))")), 2)
    if feedback_ms <= 0 or feedback_ms > 150:
        raise AssertionError(f"{action_type} feedback exceeded 150ms: {feedback_ms}ms")
    if not all([visual.get("classRunning"), visual.get("busyButton"), visual.get("sidebarRunning")]):
        raise AssertionError(f"{action_type} running visual incomplete: {visual}")
    if "embeddedTaskPerimeterRotate" not in str(visual.get("animationName")) and visual.get("animationName") != "none":
        raise AssertionError(f"{action_type} missing perimeter animation: {visual}")
    return {"feedback_ms": feedback_ms, "running_visual": True, "visual": visual}


def reveal_node_actions(page: Page) -> None:
    node = page.locator('.node[data-node-id="story_text"]')
    expect(node).to_be_visible()
    box = node.bounding_box()
    if not box:
        raise AssertionError("story_text node has no measurable box")
    page.mouse.move(box["x"] + 24, box["y"] + 20)
    node.locator(".node-title").click()


def verify_project_delete(page: Page, base_url: str, project_id: str, screenshot_dir: Path, round_label: str, key: str) -> bool:
    page.locator(".studio-project-button").click()
    expect(page.locator(".studio-project-menu")).to_be_visible()
    page.locator(".studio-project-delete").click()
    expect(page.locator(".project-delete-modal")).to_be_visible()
    screenshot(page, screenshot_dir, f"{round_label}-{key}-07-delete-confirm.png")
    page.get_by_role("button", name="取消").click()
    page.locator(".studio-project-button").click()
    page.locator(".studio-project-delete").click()
    expect(page.locator(".project-delete-modal")).to_be_visible()
    page.get_by_role("button", name="确认删除").click()
    page.wait_for_timeout(400)
    response = page.request.get(f"{base_url}/projects")
    projects = response.json().get("projects") or []
    return all(item.get("project_id") != project_id for item in projects)


def viewport_probe(page: Page, project_id: str) -> dict[str, Any]:
    return page.evaluate(
        """key => {
          const state = JSON.parse(localStorage.getItem(key) || '{}');
          const node = document.querySelector('.node[data-node-id="story_text"]');
          const box = node?.getBoundingClientRect?.();
          return {
            viewport: state.viewport || {},
            selected: state.selection?.nodeIds?.[0] || '',
            box: box ? { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) } : null,
          };
        }""",
        storage_key(project_id),
    )


def equivalent_viewport_probe(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if before.get("selected") != after.get("selected"):
        return False
    for key in ("x", "y", "scale"):
        if abs(float((before.get("viewport") or {}).get(key, 0)) - float((after.get("viewport") or {}).get(key, 0))) > 0.01:
            return False
    before_box = before.get("box") or {}
    after_box = after.get("box") or {}
    return all(abs(float(before_box.get(key, 0)) - float(after_box.get(key, 0))) <= 1 for key in ("x", "y", "width", "height"))


def graph_counts_safe(page: Page, project_id: str) -> dict[str, int]:
    try:
        return graph_counts(page, project_id)
    except Exception:
        return {"nodes": 0, "edges": 0}


def embedded_state(page: Page, project_id: str) -> dict[str, Any]:
    return page.evaluate("""key => JSON.parse(localStorage.getItem(key) || '{}').nodes?.story_text?.params?.embeddedCreativeAction || {}""", storage_key(project_id))


def project_id_from_url(url: str) -> str:
    marker = "/projects/"
    if marker not in url:
        return ""
    return url.split(marker, 1)[1].split("/", 1)[0]


def issue_ledger(cases: dict[str, Any], console_errors: list[str], response_errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if console_errors:
        issues.append(issue("P0", "console_errors", str(console_errors[:6])))
    if response_errors:
        issues.append(issue("P0", "response_errors", str(response_errors[:6])))
    for key, item in cases.items():
        if item.get("max_feedback_ms", 9999) > 150:
            issues.append(issue("P1", f"{key}_slow_feedback", f"{item.get('max_feedback_ms')}ms"))
        for field in (
            "script_cancel_late_response_ignored",
            "script_same_node_apply",
            "shot_candidate_graph_apply",
            "project_switcher_no_viewport_change",
            "project_menu_outside_escape_close",
            "account_menu_real",
            "delete_project_supported",
            "running_visual",
            "no_horizontal_overflow",
        ):
            if not item.get(field):
                issues.append(issue("P1", f"{key}_{field}", "browser contract failed"))
    return issues


def role_matrix(cases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    all_ok = all(
        item.get("running_visual")
        and item.get("script_same_node_apply")
        and item.get("shot_candidate_graph_apply")
        and item.get("project_switcher_no_viewport_change")
        and item.get("delete_project_supported")
        for item in cases.values()
    )
    return {
        "first_time_creator": {"completed": all_ok, "task": "see concise shell and immediate task feedback"},
        "screenwriter": {"completed": all(item.get("script_same_node_apply") for item in cases.values()), "task": "apply screenplay revision to the same node"},
        "director_storyboard_artist": {"completed": all(item.get("shot_candidate_graph_apply") for item in cases.values()), "task": "turn script into visible shot candidate graph"},
        "producer_operator": {"completed": all(item.get("delete_project_supported") for item in cases.values()), "task": "manage projects without accidental viewport changes"},
        "mobile_reviewer": {"completed": all(item.get("no_horizontal_overflow") for item in cases.values()), "task": "operate shell and task review across phone viewports"},
    }


def issue(severity: str, issue_id: str, evidence: str) -> dict[str, str]:
    return {"severity": severity, "issue": issue_id, "evidence": evidence}


if __name__ == "__main__":
    raise SystemExit(main())
