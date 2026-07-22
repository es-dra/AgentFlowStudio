from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import (
    create_blank_text_node,
    ensure_ai_open,
    graph_counts,
    has_horizontal_overflow,
    screenshot,
    select_node,
    selected_node_id,
    storage_key,
    viewport_key,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
PREVIEW_DELAY_SEC = 1.6


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-6-runtime-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-6-browser-{int(time.time())}.json").resolve()
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
            "provider_dispatch_count": report["provider_dispatch_count"],
            "cost_usd": report["cost_usd"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.6 visible creative task browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--round-label", default="A")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def run_browser_qa(runtime_root: Path, base_url: str, screenshot_dir: Path, round_label: str, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    cases: dict[str, Any] = {}
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in VIEWPORTS:
                project_id = f"m6-6-visible-task-{round_label.lower()}-{viewport_key(viewport)}-{int(time.time() * 1000)}"
                prepare_project(runtime_root, project_id)
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on(
                    "response",
                    lambda response: response_errors.append({"status": response.status, "url": response.url})
                    if response.status >= 400 and not response.url.endswith("/favicon.ico")
                    else None,
                )
                try:
                    result, captured = verify_viewport(page, base_url, project_id, viewport, screenshot_dir, round_label)
                    cases[f"{project_id}:{viewport_key(viewport)}"] = result
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
        raise AssertionError(f"M6.6 browser QA failed: {json.dumps(issues, ensure_ascii=False)}")
    return {
        "artifact_type": "afs_m6_6_visible_creative_tasks_browser_qa",
        "schema_version": "afs.m6_6.browser_qa.v0.1",
        "round": round_label,
        "status": "passed",
        "cases": cases,
        "screenshots": screenshots,
        "role_task_completion_matrix": role_matrix(cases),
        "micro_experience_checks": micro_checks(cases),
        "issue_ledger": issues,
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "console_error_count": len(console_errors),
        "response_error_count": len(response_errors),
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "real_llm_boundary": "Browser lane uses delayed safe structured preview fixtures only to prove visible task UX. Real server_codex quality is covered by the M6.6 real LLM runtime smoke.",
    }


def prepare_project(runtime_root: Path, project_id: str) -> None:
    response = runtime_test_client(runtime_root).post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": "M6.6 visible creative task browser QA",
            "status": "in_progress",
        },
    )
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project create failed: {response.status_code} {response.text}")


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
    page.goto(f"{base_url}/studio/?project={project_id}&qa=m6-6-{round_label}-{int(time.time())}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator("#canvas-root")).to_be_visible()
    screenshots[f"{key}:initial"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-01-initial.png")

    ensure_ai_open(page, viewport)
    source_node_id = create_script_node(page, project_id)
    before_counts = graph_counts(page, project_id)
    running = start_action_and_measure_running(page, project_id, source_node_id, "script_revision")
    screenshots[f"{key}:script_running"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-02-script-running.png")
    cancel_ok = cancel_and_verify_late_response_ignored(page, project_id, source_node_id, before_counts)

    running_again = start_action_and_measure_running(page, project_id, source_node_id, "script_revision")
    wait_for_embedded_status(page, project_id, source_node_id, "preview")
    screenshots[f"{key}:script_preview"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-03-script-preview.png")
    preview_geometry = task_geometry(page, source_node_id)
    script_apply = apply_script_preview(page, project_id, source_node_id, before_counts)
    screenshots[f"{key}:script_applied"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-04-script-applied.png")

    counts_after_script = graph_counts(page, project_id)
    shot_running = start_action_and_measure_running(page, project_id, source_node_id, "shot_breakdown")
    wait_for_embedded_status(page, project_id, source_node_id, "preview")
    screenshots[f"{key}:shot_preview"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-05-shot-preview.png")
    shot_apply = apply_shot_preview(page, project_id, source_node_id, counts_after_script)
    screenshots[f"{key}:shot_applied"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-06-shot-applied.png")

    timeout_isolation = verify_timeout_isolation(page, project_id, source_node_id)
    screenshots[f"{key}:timeout_isolation"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-07-timeout-isolation.png")
    final_counts = graph_counts(page, project_id)
    return (
        {
            "project_id": project_id,
            "viewport": key,
            "running_feedback_ms": max(running["feedback_ms"], running_again["feedback_ms"], shot_running["feedback_ms"]),
            "running_task_visible": running["visible"] and running_again["visible"] and shot_running["visible"],
            "cancel_late_response_ignored": cancel_ok,
            "script_preview_geometry": preview_geometry,
            "script_same_node_apply": script_apply,
            "shot_candidate_graph_apply": shot_apply,
            "timeout_error_isolation": timeout_isolation,
            "initial_counts": before_counts,
            "final_counts": final_counts,
            "request_count": int(page.evaluate("() => (window.__m66EmbeddedRequests || []).length")),
            "provider_dispatch_count": 0,
            "cost_usd": 0,
            "no_horizontal_overflow": not has_horizontal_overflow(page),
            "screenshots": [str(path) for path in screenshots.values()],
        },
        screenshots,
    )


def create_script_node(page: Page, project_id: str) -> str:
    create_blank_text_node(page, project_id)
    node_id = selected_node_id(page, project_id)
    select_node(page, project_id, node_id)
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.fill("孙悟空大战猪八戒。两人因为通关文牒和一块油饼误会升级，最后发现小妖在破庙里偷笑。")
    editor.blur()
    return node_id


def install_embedded_fetch_stub(page: Page) -> None:
    script = (
        """(() => {
          const delayMs = __DELAY_MS__;
          const screenplayPreview = __SCREENPLAY_PREVIEW__;
          const shotPreview = __SHOT_PREVIEW__;
          const originalFetch = window.fetch.bind(window);
          window.__m66EmbeddedMode = 'success';
          window.__m66EmbeddedRequests = [];
          window.fetch = (input, init = {}) => {
            const url = String(typeof input === 'string' ? input : input?.url || '');
            if (!url.includes('/embedded-creative-actions/preview')) return originalFetch(input, init);
            let payload = {};
            try { payload = JSON.parse(init.body || '{}'); } catch (_) { payload = {}; }
            window.__m66EmbeddedRequests.push({
              action_type: payload.action_type || '',
              node_id: payload.node_id || '',
              mode: payload.mode || '',
            });
            return new Promise((resolve) => {
              window.setTimeout(() => {
                if (window.__m66EmbeddedMode === 'timeout') {
                  resolve(new Response('Gateway timeout while waiting for image generation', {
                    status: 504,
                    headers: { 'content-type': 'text/plain' },
                  }));
                  return;
                }
                const actionType = payload.action_type || 'script_revision';
                const preview = actionType === 'shot_breakdown' ? shotPreview : screenplayPreview;
                const body = {
                  project_id: 'browser-qa',
                  job: { job_id: `job_${actionType}`, status: 'succeeded' },
                  mode: 'llm',
                  action_type: actionType,
                  target: {
                    node_id: payload.node_id || '',
                    node_type: payload.node_type || '',
                    action_type: actionType,
                    mode: payload.mode || '',
                    scope: actionType === 'script_revision' ? 'selected_node_only' : 'selected_node_shot_plan',
                  },
                  creative_task: {
                    schema_version: 'afs.creative_task.v0.1',
                    task_id: `task_${actionType}_${Date.now()}`,
                    node_id: payload.node_id || '',
                    node_type: payload.node_type || '',
                    action_type: actionType,
                    mode: payload.mode || '',
                    state: 'preview_ready',
                    phase: 'preview_ready',
                    completed_phases: ['queued', 'context', 'dispatching', 'validating', 'preview_ready'],
                    result_scope: actionType === 'script_revision' ? 'same_node_revision' : 'candidate_storyboard_subgraph',
                    cancel_requested: false,
                  },
                  preview,
                  provider_gate: { status: 'ready_not_run' },
                  provider_calls_started: true,
                  provider_lineage: {
                    service_id: 'server_codex',
                    provider: 'codex_local',
                    model_surface: 'server-codex-login',
                    request_id: `browser_${actionType}`,
                    structured_output_contract_id: 'afs.runtime.embedded_creative_action.v0.2',
                    structured_output_schema_digest: 'browser_schema_digest',
                    provider_calls_started: true,
                    provider_raw_response_stored: false,
                    external_paid_cost_usd: 0,
                  },
                  safe_manifest: { provider_calls_started: true, provider_raw_response_stored: false },
                  graph_mutation: {
                    before_version: 1,
                    after_version: 1,
                    before_digest: 'a'.repeat(64),
                    after_digest: 'a'.repeat(64),
                    mutated: false,
                  },
                  latency_ms: delayMs,
                  cost_usd: 0,
                  artifacts: {},
                  non_claims: ['not_canvas_mutation_until_user_apply'],
                };
                resolve(new Response(JSON.stringify(body), {
                  status: 200,
                  headers: { 'content-type': 'application/json' },
                }));
              }, delayMs);
            });
          };
        })();"""
        .replace("__DELAY_MS__", str(int(PREVIEW_DELAY_SEC * 1000)))
        .replace("__SCREENPLAY_PREVIEW__", json.dumps(fake_screenplay_preview(), ensure_ascii=False))
        .replace("__SHOT_PREVIEW__", json.dumps(fake_shot_preview(), ensure_ascii=False))
    )
    page.add_init_script(script)


def fake_preview_response(payload: dict[str, Any]) -> dict[str, Any]:
    action_type = payload.get("action_type") or "script_revision"
    preview = fake_shot_preview() if action_type == "shot_breakdown" else fake_screenplay_preview()
    return {
        "project_id": "browser-qa",
        "job": {"job_id": f"job_{action_type}", "status": "succeeded"},
        "mode": "llm",
        "action_type": action_type,
        "target": {
            "node_id": payload.get("node_id"),
            "node_type": payload.get("node_type"),
            "action_type": action_type,
            "mode": payload.get("mode"),
            "scope": "selected_node_only" if action_type == "script_revision" else "selected_node_shot_plan",
        },
        "creative_task": {
            "schema_version": "afs.creative_task.v0.1",
            "task_id": f"task_{action_type}_{int(time.time() * 1000)}",
            "node_id": payload.get("node_id"),
            "node_type": payload.get("node_type"),
            "action_type": action_type,
            "mode": payload.get("mode"),
            "state": "preview_ready",
            "phase": "preview_ready",
            "completed_phases": ["queued", "context", "dispatching", "validating", "preview_ready"],
            "result_scope": "same_node_revision" if action_type == "script_revision" else "candidate_storyboard_subgraph",
            "cancel_requested": False,
        },
        "preview": preview,
        "provider_gate": {"status": "ready_not_run"},
        "provider_calls_started": True,
        "provider_lineage": {
            "service_id": "server_codex",
            "provider": "codex_local",
            "model_surface": "server-codex-login",
            "request_id": f"browser_{action_type}",
            "structured_output_contract_id": "afs.runtime.embedded_creative_action.v0.2",
            "structured_output_schema_digest": "browser_schema_digest",
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "external_paid_cost_usd": 0,
        },
        "safe_manifest": {"provider_calls_started": True, "provider_raw_response_stored": False},
        "graph_mutation": {
            "before_version": 1,
            "after_version": 1,
            "before_digest": "a" * 64,
            "after_digest": "a" * 64,
            "mutated": False,
        },
            "latency_ms": int(PREVIEW_DELAY_SEC * 1000),
        "cost_usd": 0,
        "artifacts": {},
        "non_claims": ["not_canvas_mutation_until_user_apply"],
    }


def fake_screenplay_preview() -> dict[str, Any]:
    candidate = {
        "title": "破庙误会",
        "version_label": "M6.6 浏览器预览",
        "logline": "孙悟空误会猪八戒偷走通关文牒，两人在破庙前冲突升级，最终发现真正的小妖线索。",
        "characters": [
            {"name": "孙悟空", "goal": "夺回通关文牒", "conflict": "急躁误判八戒", "change": "从逼问转向联手追妖"},
            {"name": "猪八戒", "goal": "证明清白", "conflict": "馋嘴旧印象削弱解释", "change": "从躲闪转为指出破庙线索"},
        ],
        "scenes": [{
            "heading": "外景 - 荒山破庙 - 黄昏",
            "space_type": "外景",
            "location": "荒山破庙",
            "time_of_day": "黄昏",
            "purpose": "建立误会、动作冲突和共同目标",
            "blocks": [
                {"type": "action", "text": "通关文牒的空袋落在石阶上，油饼屑沿着脚印延伸到破庙门口。"},
                {"type": "character", "text": "孙悟空"},
                {"type": "dialogue", "text": "呆子，文牒没了，你倒先留下一路吃相。"},
                {"type": "character", "text": "猪八戒"},
                {"type": "dialogue", "text": "猴哥，我嘴馋不假，可那笑声是从庙梁上传来的。"},
                {"type": "transition", "text": "切至：庙梁黑影晃动。"},
            ],
        }],
    }
    revised_text = "\n".join([
        "《破庙误会》",
        "版本：M6.6 浏览器预览",
        "一句话梗概：孙悟空误会猪八戒偷走通关文牒，两人在破庙前冲突升级，最终发现真正的小妖线索。",
        "",
        "角色",
        "- 孙悟空：目标 夺回通关文牒；冲突 急躁误判八戒；变化 从逼问转向联手追妖",
        "- 猪八戒：目标 证明清白；冲突 馋嘴旧印象削弱解释；变化 从躲闪转为指出破庙线索",
        "",
        "外景 - 荒山破庙 - 黄昏",
        "场景目的：建立误会、动作冲突和共同目标",
        "",
        "通关文牒的空袋落在石阶上，油饼屑沿着脚印延伸到破庙门口。",
        "",
        "孙悟空",
        "呆子，文牒没了，你倒先留下一路吃相。",
        "",
        "猪八戒",
        "猴哥，我嘴馋不假，可那笑声是从庙梁上传来的。",
        "",
        "转场：切至：庙梁黑影晃动。",
    ])
    return {
        "preview_id": "browser_screenplay_preview",
        "action_type": "script_revision",
        "mode": "professional_expansion",
        "revised_text": revised_text,
        "change_summary": ["改为专业剧本格式", "保留同一节点并加入角色目标冲突变化"],
        "rationale": "剧本化预览先在右侧审阅，应用前不写入 ProductionGraph。",
        "unresolved_decisions": [],
        "quality_flags": ["screenplay_format"],
        "screenplay_candidate": candidate,
    }


def fake_shot_preview() -> dict[str, Any]:
    return {
        "preview_id": "browser_shot_preview",
        "action_type": "shot_breakdown",
        "mode": "dynamic_shot_breakdown",
        "revised_text": "这一场按误会证据、追打冲突、妖影转折拆成五个镜头，数量由动作和信息揭示决定。",
        "change_summary": ["动态 5 镜头", "每镜头保留景别、机位、运动、声音、转场和目的"],
        "rationale": "确认前只显示候选；应用后创建可见分镜候选子图。",
        "unresolved_decisions": [],
        "quality_flags": ["dynamic_count"],
        "shot_plan": {
            "total_shots": 5,
            "estimated_duration_sec": 33,
            "scenes": [
                {
                    "title": "破庙前误会",
                    "purpose": "从证据误判推进到动作冲突",
                    "shots": [
                        {"title": "空袋证据", "duration_sec": 5, "shot_size": "特写", "camera_angle": "俯拍", "movement": "轻微推进", "blocking": "悟空手指捻起油饼屑", "sound": "风声和布袋摩擦", "transition": "动作切", "narrative_purpose": "建立误会证据"},
                        {"title": "棍耙对峙", "duration_sec": 8, "shot_size": "中景", "camera_angle": "平视", "movement": "横移", "blocking": "悟空逼近，八戒护着钉耙后退", "sound": "金属轻碰", "transition": "节奏切", "narrative_purpose": "让冲突升级"},
                        {"title": "庙梁笑声", "duration_sec": 6, "shot_size": "双人中近景", "camera_angle": "仰角转摇", "movement": "从两人摇向梁上", "blocking": "两人同时停手抬头", "sound": "小妖笑声", "transition": "悬念切", "narrative_purpose": "揭示真正线索"},
                    ],
                },
                {
                    "title": "联手追妖",
                    "purpose": "把误会转成共同目标",
                    "shots": [
                        {"title": "包袱落地", "duration_sec": 5, "shot_size": "近景", "camera_angle": "低机位", "movement": "快速下摇", "blocking": "包袱落地，小妖从油饼里钻出", "sound": "布包落地和尖笑", "transition": "跳切", "narrative_purpose": "确认八戒被陷害"},
                        {"title": "师兄弟追出", "duration_sec": 9, "shot_size": "全景", "camera_angle": "侧后方", "movement": "跟拍推进", "blocking": "悟空跃上墙头，八戒抄近路追出", "sound": "脚步、风声、钉耙划地", "transition": "接下场", "narrative_purpose": "建立联手行动"},
                    ],
                },
            ],
        },
    }


def start_action_and_measure_running(page: Page, project_id: str, node_id: str, action_type: str) -> dict[str, Any]:
    select_node(page, project_id, node_id)
    role = "shot-breakdown-action" if action_type == "shot_breakdown" else "script-revision-action"
    button = page.locator(f'.node[data-node-id="{node_id}"] [data-role="{role}"]')
    expect(button).to_be_visible()
    box = button.bounding_box()
    if not box:
        raise AssertionError(f"{action_type} button has no measurable hit target")
    page.evaluate(
        """() => {
          window.__m66ActionClickAt = performance.now();
          window.__m66ActionRunningAt = 0;
          if (!window.__m66RunningListenerInstalled) {
            window.__m66RunningListenerInstalled = true;
            window.addEventListener('afs:embedded-creative-task-running', () => {
              window.__m66ActionRunningAt = performance.now();
            });
          }
        }"""
    )
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    time.sleep(0.15)
    running = page.evaluate(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return {
            status: node?.params?.embeddedCreativeAction?.status || '',
            phase: node?.params?.embeddedCreativeAction?.creative_task?.phase || '',
            message: node?.params?.embeddedCreativeAction?.message || '',
          };
        }""",
        {"key": storage_key(project_id), "nodeId": node_id},
    )
    feedback_ms = round(float(page.evaluate("() => Math.max(0, (window.__m66ActionRunningAt || 0) - (window.__m66ActionClickAt || 0))")), 2)
    if feedback_ms <= 0:
        raise AssertionError(f"{action_type} did not emit running timing event")
    visible = running.get("status") == "running"
    if not visible:
        raise AssertionError(f"{action_type} did not expose running state inside 150ms: {running}")
    if not page.locator(".agent-current-task-review.running").is_visible():
        raise AssertionError(f"{action_type} running state is not visible in the right creative sidebar")
    cancel_visible = bool(page.evaluate(
        """() => {
          const card = document.querySelector('.agent-current-task-review.running');
          const buttons = [...(card?.querySelectorAll('button') || [])];
          return buttons.some((button) => button.offsetParent !== null && button.textContent.includes('取消任务'));
        }"""
    ))
    if not cancel_visible:
        text = page.evaluate("() => document.querySelector('.agent-current-task-review')?.innerText || ''")
        raise AssertionError(f"{action_type} running state has no visible cancel action: {text!r}")
    return {"visible": True, "feedback_ms": feedback_ms, "state": running}


def cancel_and_verify_late_response_ignored(page: Page, project_id: str, node_id: str, before_counts: dict[str, int]) -> bool:
    page.get_by_role("button", name="取消任务").click()
    page.wait_for_function(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return node?.params?.embeddedCreativeAction?.status === 'cancelled';
        }""",
        arg={"key": storage_key(project_id), "nodeId": node_id},
        timeout=5_000,
    )
    time.sleep(PREVIEW_DELAY_SEC + 0.3)
    state = embedded_action_state(page, project_id, node_id)
    if state.get("status") != "cancelled":
        raise AssertionError(f"late provider response overwrote cancelled task: {state}")
    if graph_counts(page, project_id) != before_counts:
        raise AssertionError("cancelled preview mutated the graph")
    return True


def wait_for_embedded_status(page: Page, project_id: str, node_id: str, status: str) -> None:
    page.wait_for_function(
        """({ key, nodeId, status }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return node?.params?.embeddedCreativeAction?.status === status;
        }""",
        arg={"key": storage_key(project_id), "nodeId": node_id, "status": status},
        timeout=30_000,
    )


def embedded_action_state(page: Page, project_id: str, node_id: str) -> dict[str, Any]:
    return page.evaluate(
        """({ key, nodeId }) => JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId]?.params?.embeddedCreativeAction || {}""",
        {"key": storage_key(project_id), "nodeId": node_id},
    )


def task_geometry(page: Page, node_id: str) -> dict[str, Any]:
    geometry = page.evaluate(
        """nodeId => {
          const node = document.querySelector(`.node[data-node-id="${nodeId}"]`);
          const task = document.querySelector('.agent-current-task-review.preview');
          const editor = document.querySelector('.agent-current-task-editor');
          const prompt = document.querySelector('.prompt-bar');
          const outPort = node?.querySelector('.node-port.out');
          const action = node?.querySelector('[data-role="script-revision-action"]');
          const box = node?.getBoundingClientRect?.();
          const taskBox = task?.getBoundingClientRect?.();
          const editorBox = editor?.getBoundingClientRect?.();
          const promptBox = prompt?.getBoundingClientRect?.();
          const portBox = outPort?.getBoundingClientRect?.();
          const actionBox = action?.getBoundingClientRect?.();
          const overlap = (a, b) => Boolean(a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top);
          return {
            node_height: box?.height || 0,
            task_visible: Boolean(taskBox && taskBox.width > 0 && taskBox.height > 0),
            editor_scrollable: Boolean(editor && editor.scrollHeight > editor.clientHeight),
            prompt_visible: Boolean(promptBox && promptBox.width > 0 && promptBox.height > 0),
            prompt_overlaps_node: overlap(promptBox, box),
            prompt_overlaps_port: overlap(promptBox, portBox),
            prompt_overlaps_action: overlap(promptBox, actionBox),
            task_width: taskBox?.width || 0,
            editor_height: editorBox?.height || 0,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
          };
        }""",
        node_id,
    )
    if not geometry["task_visible"]:
        raise AssertionError(f"right task review is not visible: {geometry}")
    if geometry["node_height"] > 360:
        raise AssertionError(f"node expanded too tall for embedded preview: {geometry}")
    if geometry["prompt_overlaps_node"] or geometry["prompt_overlaps_port"] or geometry["prompt_overlaps_action"]:
        raise AssertionError(f"prompt bar obscures node/ports/actions: {geometry}")
    if geometry["horizontal_overflow"]:
        raise AssertionError(f"horizontal overflow after preview: {geometry}")
    return geometry


def apply_script_preview(page: Page, project_id: str, node_id: str, before_counts: dict[str, int]) -> dict[str, Any]:
    page.locator(".agent-current-task-review.preview").get_by_role("button", name="应用").click()
    page.wait_for_function(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return node?.params?.embeddedCreativeAction?.status === 'applied' && (node?.params?.revisions || []).length >= 1;
        }""",
        arg={"key": storage_key(project_id), "nodeId": node_id},
        timeout=5_000,
    )
    after_counts = graph_counts(page, project_id)
    state = page.evaluate(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return {
            node_id: node?.id,
            content: node?.content || '',
            revision_count: (node?.params?.revisions || []).length,
            current_revision_id: node?.params?.currentRevisionId || '',
            screenplay_candidate: Boolean((node?.params?.revisions || [])[0]?.screenplay_candidate),
          };
        }""",
        {"key": storage_key(project_id), "nodeId": node_id},
    )
    if after_counts != before_counts:
        raise AssertionError(f"same-node script apply changed graph counts: before={before_counts} after={after_counts}")
    if state.get("node_id") != node_id or not state.get("screenplay_candidate") or "外景 - 荒山破庙 - 黄昏" not in state.get("content", ""):
        raise AssertionError(f"script apply did not preserve node id and professional screenplay content: {state}")
    return {"before_counts": before_counts, "after_counts": after_counts, **state}


def apply_shot_preview(page: Page, project_id: str, source_node_id: str, before_counts: dict[str, int]) -> dict[str, Any]:
    page.locator(".agent-current-task-review.preview").get_by_role("button", name="应用").click()
    page.wait_for_function(
        """({ key, beforeNodes }) => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          return Object.keys(s.nodes || {}).length >= beforeNodes + 4;
        }""",
        arg={"key": storage_key(project_id), "beforeNodes": before_counts["nodes"]},
        timeout=5_000,
    )
    state = page.evaluate(
        """({ key, sourceNodeId }) => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          const nodes = Object.values(s.nodes || {});
          const edges = Object.values(s.edges || {});
          const roles = nodes.map((node) => node.params?.nodeRole).filter(Boolean);
          const source = s.nodes?.[sourceNodeId];
          const action = source?.params?.embeddedCreativeAction || {};
          return {
            node_count: nodes.length,
            edge_count: edges.length,
            roles,
            selected_node_id: s.selection?.nodeIds?.[0] || '',
            applied_status: action.status,
            subgraph: action.applied_subgraph || {},
          };
        }""",
        {"key": storage_key(project_id), "sourceNodeId": source_node_id},
    )
    required = {"m6_6_shot_sequence_candidate", "m6_6_scene_candidate", "m6_6_shot_candidate"}
    if not required.issubset(set(state.get("roles") or [])):
        raise AssertionError(f"shot preview apply did not create visible candidate roles: {state}")
    if int(state.get("node_count") or 0) <= before_counts["nodes"] or int(state.get("edge_count") or 0) <= before_counts["edges"]:
        raise AssertionError(f"shot preview apply did not add candidate nodes/edges: before={before_counts} after={state}")
    return state


def verify_timeout_isolation(page: Page, project_id: str, node_id: str) -> bool:
    page.evaluate("() => { window.__m66EmbeddedMode = 'timeout'; }")
    select_node(page, project_id, node_id)
    button = page.locator(f'.node[data-node-id="{node_id}"] [data-role="shot-breakdown-action"]')
    expect(button).to_be_visible()
    button.click()
    wait_for_embedded_status(page, project_id, node_id, "unavailable")
    state = embedded_action_state(page, project_id, node_id)
    text = page.locator(f'.node[data-node-id="{node_id}"] .embedded-creative-action').inner_text()
    if "image generation" in text or "图片" in text:
        raise AssertionError(f"shot task leaked image-generation timeout text: {text!r} state={state}")
    if "分镜拆解任务失败" not in text:
        raise AssertionError(f"shot task did not classify timeout as shot action failure: {text!r}")
    return True


def issue_ledger(
    cases: dict[str, Any],
    console_errors: list[str],
    response_errors: list[dict[str, Any]],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if console_errors:
        issues.append(issue("P0", "console_errors", str(console_errors[:6])))
    if response_errors:
        issues.append(issue("P0", "response_errors", str(response_errors[:6])))
    for key, item in cases.items():
        if item["running_feedback_ms"] > 150:
            issues.append(issue("P1", f"{key}_slow_visible_feedback", f"{item['running_feedback_ms']}ms"))
        for field in (
            "running_task_visible",
            "cancel_late_response_ignored",
            "script_same_node_apply",
            "shot_candidate_graph_apply",
            "timeout_error_isolation",
            "no_horizontal_overflow",
        ):
            if not item.get(field):
                issues.append(issue("P1", f"{key}_{field}", "browser flow did not complete"))
        if item.get("script_preview_geometry", {}).get("prompt_overlaps_node"):
            issues.append(issue("P1", f"{key}_prompt_overlap", str(item["script_preview_geometry"])))
    return issues


def role_matrix(cases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    all_ok = all(
        item.get("running_task_visible")
        and item.get("cancel_late_response_ignored")
        and item.get("script_same_node_apply")
        and item.get("shot_candidate_graph_apply")
        and item.get("timeout_error_isolation")
        for item in cases.values()
    )
    return {
        "first_time_creator": {"completed": all_ok, "task": "see immediate creative task feedback and no black-box freeze"},
        "screenwriter": {"completed": all_ok, "task": "review/apply a professional screenplay revision inside the same node"},
        "director_storyboard_artist": {"completed": all_ok, "task": "apply visible dynamic shot candidate graph"},
        "editor_recovery_operator": {"completed": all_ok, "task": "cancel/retry and verify late responses do not overwrite state"},
        "mobile_keyboard_low_vision": {"completed": all(item.get("no_horizontal_overflow") for item in cases.values()), "task": "operate task review across five viewports"},
        "owner_adversarial_tester": {"completed": all_ok, "task": "reject hidden draft, giant node preview and image timeout contamination"},
    }


def micro_checks(cases: dict[str, Any]) -> dict[str, bool]:
    return {
        "feedback_visible_within_150ms": all(item.get("running_feedback_ms", 9999) <= 150 for item in cases.values()),
        "cancel_route_available": all(item.get("cancel_late_response_ignored") for item in cases.values()),
        "right_sidebar_owns_long_review": all(item.get("script_preview_geometry", {}).get("task_visible") for item in cases.values()),
        "node_bounded_height": all(item.get("script_preview_geometry", {}).get("node_height", 9999) <= 360 for item in cases.values()),
        "prompt_not_obscuring_actions": all(not item.get("script_preview_geometry", {}).get("prompt_overlaps_node") for item in cases.values()),
        "shot_breakdown_visible_candidate_graph": all(item.get("shot_candidate_graph_apply") for item in cases.values()),
        "image_timeout_not_leaked_to_shot": all(item.get("timeout_error_isolation") for item in cases.values()),
        "provider_zero_cost_browser_lane": all(item.get("provider_dispatch_count") == 0 and item.get("cost_usd") == 0 for item in cases.values()),
    }


def issue(severity: str, issue_id: str, evidence: str) -> dict[str, str]:
    return {"severity": severity, "issue": issue_id, "evidence": evidence}


if __name__ == "__main__":
    raise SystemExit(main())
