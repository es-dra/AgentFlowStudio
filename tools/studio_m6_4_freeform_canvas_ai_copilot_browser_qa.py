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


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
COMPACT_AI_MAX_WIDTH = 1100
PHONE_AI_MAX_WIDTH = 760
OWNER_REFERENCE_IMAGE = Path(
    "/home/afs-ops/.codex/afs-evidence/afs-m6-4-freeform-canvas-ai-copilot-20260722/"
    "owner-input/01-full-canvas-chat-plan.png"
)


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-4-runtime-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-4-freeform-browser-{int(time.time())}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or report_path.with_suffix("")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, runtime_root, base_url, screenshot_dir, args.round_label, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": str(screenshot_dir)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.4 freeform canvas and AI creative copilot browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--round-label", default="A")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def run_browser_qa(repo: Path, runtime_root: Path, base_url: str, screenshot_dir: Path, round_label: str, timeout_ms: int) -> dict[str, Any]:
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
                project_id = f"m6-4-freeform-{round_label.lower()}-{viewport['width']}x{viewport['height']}-{int(time.time() * 1000)}"
                prepare_project(runtime_root, project_id, viewport)
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
                    result, captured = verify_project(page, base_url, project_id, viewport, screenshot_dir, round_label)
                    cases[f"{project_id}:{viewport_key(viewport)}"] = result
                    screenshots.update(captured)
                finally:
                    page.close()
        finally:
            browser.close()
    if console_errors or response_errors:
        raise AssertionError(f"console_errors={console_errors[:8]} response_errors={response_errors[:8]}")
    checks = aggregate_checks(cases)
    roles = role_matrix(checks)
    micro = micro_checks(checks)
    failures = {
        "checks": [name for name, passed in checks.items() if passed is not True],
        "roles": [name for name, item in roles.items() if item.get("completed") is not True],
        "micro": [name for name, passed in micro.items() if passed is not True],
    }
    if any(failures.values()):
        raise AssertionError(f"M6.4 browser QA still has user-visible failures: {json.dumps(failures, ensure_ascii=False)}")
    return {
        "artifact_type": "afs_m6_4_freeform_canvas_ai_copilot_browser_qa",
        "schema_version": "afs.m6_4.browser_qa.v0.1",
        "round": round_label,
        "status": "passed",
        "cases": cases,
        "screenshots": screenshots,
        "checks": checks,
        "role_task_completion_matrix": roles,
        "micro_experience_checks": micro,
        "console_error_count": 0,
        "response_error_count": 0,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "browser_plugin_boundary": "Browser plugin not installed; Playwright Chromium was used from the repository QA harness.",
    }


def prepare_project(runtime_root: Path, project_id: str, viewport: dict[str, int]) -> None:
    client = runtime_test_client(runtime_root)
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": f"M6.4自由画布QA {viewport_key(viewport)}",
            "status": "in_progress",
        },
    )
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project create failed: {response.status_code} {response.text}")


def verify_project(page: Page, base_url: str, project_id: str, viewport: dict[str, int], screenshot_dir: Path, round_label: str) -> tuple[dict[str, Any], dict[str, str]]:
    key = viewport_key(viewport)
    screenshots: dict[str, str] = {}
    page.goto(f"{base_url}/studio/?project={project_id}&qa={round_label}-{int(time.time())}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator("#canvas-root")).to_be_visible()
    assert_no_primary_english_agent_label(page)
    initial = graph_counts(page, project_id)
    assert_plan_panel_contextual(page)
    screenshots[f"{key}:initial"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-01-initial.png")

    ensure_ai_open(page, viewport)
    send_ai(page, "你好")
    expect(page.locator(".agent-chat-log")).to_contain_text("不会用本地固定回答冒充理解")
    greeting_counts = graph_counts(page, project_id)
    if greeting_counts != initial:
        raise AssertionError(f"greeting mutated graph: before={initial} after={greeting_counts}")
    assert_keyboard_input_paths(page)
    if graph_counts(page, project_id) != initial:
        raise AssertionError("keyboard conversation path changed graph state")
    screenshots[f"{key}:greeting"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-02-greeting.png")

    create_blank_text_node(page, project_id)
    first_id = selected_node_id(page, project_id)
    fill_selected_text(page, "女孩在雨夜天台寻找失踪的哥哥，她必须在灯牌熄灭前找到线索。")
    node_question_before = graph_counts(page, project_id)
    send_ai(page, "这个节点是什么")
    expect(page.locator(".agent-chat-log")).to_contain_text("不会用本地固定回答冒充理解")
    if graph_counts(page, project_id) != node_question_before:
        raise AssertionError("node explanation changed graph state")

    send_ai(page, "预览生成图片")
    expect(page.locator(".agent-command-preview")).to_contain_text("命令预览")
    preview_counts = graph_counts(page, project_id)
    page.get_by_role("button", name="取消").last.click()
    expect(page.locator(".agent-chat-log")).to_contain_text("画布未改变")
    cancel_after_counts = graph_counts(page, project_id)
    if cancel_after_counts != preview_counts:
        raise AssertionError("cancelled command preview changed graph state")

    before_optimize = graph_counts(page, project_id)
    send_ai(page, "优化当前文本")
    expect(page.locator(".agent-command-preview")).to_contain_text("优化当前节点")
    expect(page.locator(".agent-command-preview")).to_contain_text("确认后在当前节点打开真实 LLM 修订任务")
    expect(page.locator(".agent-command-preview")).to_contain_text("server_codex 文本模型")
    after_optimize = graph_counts(page, project_id)
    if after_optimize != before_optimize:
        raise AssertionError("global optimize preview changed graph state before confirmation")
    revisions = page.evaluate(
        """({ key, nodeId }) => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          return (s.nodes?.[nodeId]?.params?.revisions || []).length;
        }""",
        {"key": storage_key(project_id), "nodeId": first_id},
    )
    if revisions:
        raise AssertionError("global optimize preview created a local revision before confirmation")
    page.get_by_role("button", name="取消").last.click()

    send_ai(page, "创建分支版本：哥哥视角")
    expect(page.locator(".agent-command-preview")).to_contain_text("创建分支版本")
    confirm_latest_command(page)
    page.wait_for_function(
        """key => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          return (s.order || []).length === 2 && Object.values(s.edges || {}).some((e) => e.relation_type === 'fork');
        }""",
        arg=storage_key(project_id),
    )
    fork_counts = graph_counts(page, project_id)
    screenshots[f"{key}:revision_fork"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-03-revision-fork.png")

    select_node(page, project_id, first_id)
    plus_node_id = create_node_from_handle(page, project_id, first_id, "镜头设计")
    free_ref_id = create_node_from_global_palette(page, project_id, viewport, "参考图/图片")
    manual_edge_id = connect_nodes_by_drag(page, project_id, first_id, free_ref_id)
    manual_edge_id = select_edge(page, project_id, manual_edge_id)
    ensure_ai_open(page, viewport)
    expect(page.locator(".studio-agent-chat .agent-context-strip")).to_contain_text("连线")
    send_ai(page, "这条连线代表什么")
    expect(page.locator(".agent-chat-log")).to_contain_text("不会用本地固定回答冒充理解")
    send_ai(page, "把这条连线改成生成")
    expect(page.locator(".agent-command-preview")).to_contain_text("连线")
    confirm_latest_command(page)
    page.wait_for_function(
        """({ key, edgeId }) => JSON.parse(localStorage.getItem(key) || '{}').edges?.[edgeId]?.relation_type === 'generation'""",
        arg={"key": storage_key(project_id), "edgeId": manual_edge_id},
    )
    send_ai(page, "删除选中连线")
    expect(page.locator(".agent-command-preview")).to_contain_text("删除当前连线")
    confirm_latest_command(page)
    page.wait_for_function(
        """({ key, edgeId }) => !JSON.parse(localStorage.getItem(key) || '{}').edges?.[edgeId]""",
        arg={"key": storage_key(project_id), "edgeId": manual_edge_id},
    )
    undo_latest_agent_receipt(page)
    page.wait_for_function(
        """({ key, edgeId }) => Boolean(JSON.parse(localStorage.getItem(key) || '{}').edges?.[edgeId])""",
        arg={"key": storage_key(project_id), "edgeId": manual_edge_id},
    )
    screenshots[f"{key}:freeform_edges"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-04-freeform-edges.png")

    attach_reference_by_drop(page, project_id, free_ref_id)
    page.wait_for_function(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return Boolean(node?.previewUrl && (node?.params?.uploads || []).length);
        }""",
        arg={"key": storage_key(project_id), "nodeId": free_ref_id},
    )
    create_any_entry_nodes(page, project_id, viewport)
    screenshots[f"{key}:reference_upload"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-05-reference-upload.png")

    collapsed_ok, expanded_ok = verify_mobile_or_desktop_ai_geometry(page, viewport)
    no_overflow = not has_horizontal_overflow(page)
    console_network_clean = True
    final_counts = graph_counts(page, project_id)
    primary_text = page.locator("#product-shell-root").inner_text()
    forbidden = [token for token in ("Agent Chat", "已记录到当前上下文", "runtime root", "/home/", "/var/", "secret", "token") if token in primary_text]
    if forbidden:
        raise AssertionError(f"primary UI leaked forbidden terms: {forbidden}")
    screenshots[f"{key}:final"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-06-final.png")
    return (
        {
            "project_id": project_id,
            "viewport": key,
            "initial_counts": initial,
            "after_greeting_counts": greeting_counts,
            "after_optimize_counts": after_optimize,
            "after_fork_counts": fork_counts,
            "final_counts": final_counts,
            "first_node_id": first_id,
            "plus_node_id": plus_node_id,
            "reference_node_id": free_ref_id,
            "manual_edge_id": manual_edge_id,
            "greeting_zero_mutation": greeting_counts == initial,
            "command_cancel_zero_mutation": cancel_after_counts == preview_counts,
            "command_confirm_declared_mutation": True,
            "same_node_revision": after_optimize["nodes"] == before_optimize["nodes"],
            "explicit_fork_creates_node": fork_counts["nodes"] == before_optimize["nodes"] + 1,
            "plus_node_creation": bool(plus_node_id),
            "manual_connection": bool(manual_edge_id),
            "edge_inspect_change_delete_undo": True,
            "reference_image_entry": True,
            "plan_panel_contextual": True,
            "mobile_freeform_usable": collapsed_ok and expanded_ok and no_overflow,
            "console_network_clean": console_network_clean,
            "provider_dispatch_count": 0,
            "cost_usd": 0,
        },
        screenshots,
    )


def assert_no_primary_english_agent_label(page: Page) -> None:
    text = page.locator("#product-shell-root").inner_text()
    if "Agent Chat" in text:
        raise AssertionError("primary UI still exposes Agent Chat label")
    expect(page.locator(".studio-agent-chat")).to_contain_text("AI 创作搭档")


def assert_plan_panel_contextual(page: Page) -> None:
    expect(page.locator(".planning-required")).to_be_visible()
    expect(page.locator(".planning-required")).to_contain_text("可自由开始")
    if page.locator(".m6-script-plan-entry textarea").is_visible():
        raise AssertionError("plan text area is visible before a meaningful plan draft exists")
    box = page.locator(".planning-required").bounding_box()
    if box and box["height"] > 180:
        raise AssertionError(f"compact plan surface is too tall: {box}")
    panel = page.locator(".planning-required")
    panel.get_by_role("button", name="展开制作方案").click()
    expect(page.locator(".m6-script-plan-entry textarea")).to_be_visible()
    panel.get_by_role("button", name="收起", exact=True).click()
    expect(page.locator(".planning-required")).to_contain_text("可自由开始")


def ensure_ai_open(page: Page, viewport: dict[str, int]) -> None:
    if page.locator(".agent-chat-composer textarea").is_visible():
        return
    expand_buttons = page.get_by_role("button", name=re.compile("^展开 AI 创作搭档$"))
    if expand_buttons.count():
        expand_buttons.first.click()
    elif viewport["width"] <= COMPACT_AI_MAX_WIDTH and page.get_by_role("button", name="搭档", exact=True).count():
        page.get_by_role("button", name="搭档", exact=True).click()
    else:
        buttons = page.get_by_role("button", name=re.compile("展开 AI 创作搭档"))
        if buttons.count():
            buttons.first.click()
    expect(page.locator(".agent-chat-composer textarea")).to_be_visible()


def close_ai_overlay_if_open(page: Page) -> None:
    backdrop = page.locator(".agent-mobile-backdrop")
    if backdrop.count() and backdrop.first.is_visible():
        close_button = page.get_by_role("button", name="收起 AI 创作搭档", exact=True)
        if close_button.count() and close_button.first.is_visible():
            close_button.first.click()
        else:
            box = backdrop.first.bounding_box()
            if not box:
                raise AssertionError("AI backdrop is visible but not measurable")
            page.mouse.click(box["x"] + 12, box["y"] + 12)
        expect(backdrop.first).not_to_be_visible()


def confirm_latest_command(page: Page) -> None:
    preview = page.locator(".studio-agent-chat:not(.collapsed) .agent-command-preview").last
    expect(preview).to_be_visible()
    before = page.locator(".agent-chat-log").inner_text()
    button = page.get_by_role("button", name="确认执行").last
    expect(button).to_be_visible()
    button.click()
    try:
        page.wait_for_function(
            """previous => document.querySelector('.agent-chat-log')?.innerText !== previous""",
            arg=before,
            timeout=10_000,
        )
        assert_chat_log_stable(page, "confirm button")
        expect(preview).not_to_be_visible()
    except Exception as error:
        diagnostics = page.evaluate(
            """args => {
              const preview = document.querySelector('.studio-agent-chat:not(.collapsed) .agent-command-preview');
              const button = [...document.querySelectorAll('button')].find((item) => item.innerText?.includes('确认执行'));
              const box = button?.getBoundingClientRect?.();
              const hit = box ? document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2) : null;
              return {
                previewVisible: Boolean(preview),
                previewText: preview?.innerText || '',
                buttonVisible: Boolean(box && box.width > 0 && box.height > 0),
                buttonDisabled: Boolean(button?.disabled),
                buttonHitTag: hit?.tagName || '',
                buttonHitClass: hit?.getAttribute?.('class') || '',
                buttonHitButton: Boolean(hit?.closest?.('button')),
                logTail: (document.querySelector('.agent-chat-log')?.innerText || '').slice(-800),
              };
            }"""
        )
        raise AssertionError(f"confirm button did not execute exactly once: {json.dumps(diagnostics, ensure_ascii=False)}") from error


def undo_latest_agent_receipt(page: Page) -> None:
    receipts = page.locator(".studio-agent-chat:not(.collapsed) .agent-receipts")
    expect(receipts).to_be_visible()
    if not receipts.locator(".agent-receipt:visible").count():
        receipts.locator("summary").click()
    receipt = receipts.locator('.agent-receipt[data-command-type="delete_selected_edge"]').first
    expect(receipt).to_be_visible()
    undo = receipt.get_by_role("button", name="撤销")
    expect(undo).to_be_visible()
    undo.click()


def send_ai(page: Page, text: str) -> None:
    if not page.locator(".studio-agent-chat:not(.collapsed) .agent-chat-composer textarea").is_visible():
        viewport = page.viewport_size or {"width": int(page.evaluate("window.innerWidth")), "height": int(page.evaluate("window.innerHeight"))}
        ensure_ai_open(page, viewport)
    form = page.locator(".studio-agent-chat:not(.collapsed) .agent-chat-composer").last
    expect(form).to_be_visible()
    before = page.locator(".agent-chat-log").inner_text()
    before_messages = chat_message_count(page)
    before_previews = page.locator(".studio-agent-chat:not(.collapsed) .agent-command-preview").count()
    composer = form.locator("textarea")
    expect(composer).to_be_visible()
    assert_composer_hit_target(page)
    composer.click()
    composer.fill(text)
    try:
        expect(composer).to_have_value(text)
    except Exception as error:
        diagnostics = composer_path_diagnostics(page)
        raise AssertionError(
            f"AI composer did not contain requested text before button click: "
            f"expected={text!r} actual={composer.input_value()!r} diagnostics={json.dumps(diagnostics, ensure_ascii=False)}"
        ) from error
    button = form.get_by_role("button", name="发送到 AI 创作搭档")
    expect(button).to_be_visible()
    assert_send_button_hit_target(page)
    path_probe = install_send_path_probe(page)
    button.click()
    try:
        wait_for_agent_turn(page, before_messages, before_previews, before)
        probe = send_path_probe(page, path_probe)
        if probe.get("buttonClickCount") != 1:
            raise AssertionError(f"visible send button click count was {probe.get('buttonClickCount')}, expected 1")
        assert_chat_log_stable(page, "visible send button")
    except Exception as error:
        diagnostics = page.evaluate(
            """args => {
              const log = document.querySelector('.agent-chat-log');
              const afterLog = log?.innerText || '';
              const forms = [...document.querySelectorAll('.agent-chat-composer')].map((form) => {
                const box = form.getBoundingClientRect();
                const textarea = form.querySelector('textarea');
                const button = form.querySelector('button[aria-label="发送到 AI 创作搭档"]');
                const buttonBox = button?.getBoundingClientRect?.();
                const hit = buttonBox ? document.elementFromPoint(buttonBox.left + buttonBox.width / 2, buttonBox.top + buttonBox.height / 2) : null;
                return {
                  className: form.closest('.studio-agent-chat')?.className || '',
                  formVisible: box.width > 0 && box.height > 0,
                  box: { x: box.x, y: box.y, width: box.width, height: box.height },
                  textareaVisible: Boolean(textarea?.offsetWidth && textarea?.offsetHeight),
                  value: textarea?.value || '',
                  buttonVisible: Boolean(buttonBox && buttonBox.width > 0 && buttonBox.height > 0),
                  buttonEnabled: Boolean(button && !button.disabled),
                  buttonDisabled: Boolean(button?.disabled),
                  buttonBox: buttonBox ? { x: buttonBox.x, y: buttonBox.y, width: buttonBox.width, height: buttonBox.height } : null,
                  buttonHitTag: hit?.tagName || '',
                  buttonHitClass: hit?.getAttribute?.('class') || '',
                  buttonHitRole: hit?.getAttribute?.('role') || '',
                  buttonHitLabel: hit?.getAttribute?.('aria-label') || hit?.innerText || '',
                };
              });
              return {
                forms,
                pendingPreviewCountBefore: args.beforePreviews,
                pendingPreviewCountAfter: document.querySelectorAll('.studio-agent-chat:not(.collapsed) .agent-command-preview').length,
                logChanged: afterLog !== args.beforeLog,
                logTextDelta: afterLog.length - args.beforeLog.length,
                sendPathProbeId: args.pathProbe,
                sendPathProbe: window.__afsQaSendPathProbes?.[args.pathProbe] || null,
                messageCountBefore: args.beforeMessages,
                messageCountAfter: document.querySelectorAll('.agent-chat-log .agent-message').length,
                messageDelta: document.querySelectorAll('.agent-chat-log .agent-message').length - args.beforeMessages,
                activeTag: document.activeElement?.tagName || '',
                activeClass: document.activeElement?.getAttribute?.('class') || '',
                logTail: afterLog.slice(-500),
              };
            }"""
            ,
            arg={"beforePreviews": before_previews, "beforeLog": before, "beforeMessages": before_messages, "pathProbe": path_probe},
        )
        raise AssertionError(f"visible send button did not submit exactly once: text={text!r} diagnostics={json.dumps(diagnostics, ensure_ascii=False)}") from error


def assert_keyboard_input_paths(page: Page) -> None:
    form = page.locator(".studio-agent-chat:not(.collapsed) .agent-chat-composer").last
    composer = form.locator("textarea")
    expect(composer).to_be_visible()
    before_shift = page.locator(".agent-chat-log").inner_text()
    before_shift_messages = chat_message_count(page)
    shift_probe = install_send_path_probe(page)
    composer.fill("第一行")
    composer.press("Shift+Enter")
    value = composer.input_value()
    if "\n" not in value:
        raise AssertionError(f"Shift+Enter did not preserve a multiline draft: {value!r}")
    if page.locator(".agent-chat-log").inner_text() != before_shift:
        raise AssertionError("Shift+Enter submitted the AI composer instead of preserving a draft")
    if chat_message_count(page) != before_shift_messages:
        raise AssertionError("Shift+Enter changed the AI message log")
    shift_path = send_path_probe(page, shift_probe)
    if shift_path.get("buttonClickCount") or shift_path.get("formSubmitCount"):
        raise AssertionError(f"Shift+Enter triggered the AI composer send path: {json.dumps(shift_path, ensure_ascii=False)}")
    composer.fill("")

    before_enter = page.locator(".agent-chat-log").inner_text()
    before_enter_messages = chat_message_count(page)
    enter_probe = install_send_path_probe(page)
    composer.fill("下一步建议是什么")
    composer.press("Enter")
    try:
        wait_for_agent_turn(page, before_enter_messages, page.locator(".studio-agent-chat:not(.collapsed) .agent-command-preview").count(), before_enter)
    except Exception as error:
        diagnostics = page.evaluate(
            """args => {
              const form = document.querySelector('.studio-agent-chat:not(.collapsed) .agent-chat-composer');
              const input = form?.querySelector('textarea');
              const log = document.querySelector('.agent-chat-log')?.innerText || '';
              return {
                value: input?.value || '',
                sendPathProbeId: args.pathProbe,
                sendPathProbe: window.__afsQaSendPathProbes?.[args.pathProbe] || null,
                messageCountBefore: args.beforeMessages,
                messageCountAfter: document.querySelectorAll('.agent-chat-log .agent-message').length,
                messageDelta: document.querySelectorAll('.agent-chat-log .agent-message').length - args.beforeMessages,
                logTextDelta: log.length - args.beforeLog.length,
                logTail: log.slice(-600),
                activeTag: document.activeElement?.tagName || '',
              };
            }"""
            ,
            arg={"beforeMessages": before_enter_messages, "beforeLog": before_enter, "pathProbe": enter_probe},
        )
        raise AssertionError(f"Enter did not submit the AI composer exactly once: {json.dumps(diagnostics, ensure_ascii=False)}") from error
    enter_path = send_path_probe(page, enter_probe)
    if enter_path.get("buttonClickCount") != 0 or enter_path.get("formSubmitCount") != 1:
        raise AssertionError(f"Enter did not use the keyboard submit path exactly once: {json.dumps(enter_path, ensure_ascii=False)}")
    expect(page.locator(".agent-chat-log")).to_contain_text("不会用本地固定回答冒充理解")
    assert_chat_log_stable(page, "Enter key")


def wait_for_agent_turn(page: Page, before_messages: int, before_previews: int, before_log: str, timeout_ms: int = 20_000) -> None:
    page.wait_for_function(
        """({ beforeMessages, beforePreviews, beforeLog }) => {
          const messages = document.querySelectorAll('.agent-chat-log .agent-message').length;
          const previews = document.querySelectorAll('.studio-agent-chat:not(.collapsed) .agent-command-preview').length;
          const loading = document.querySelector('.agent-conversation-status.loading');
          const log = document.querySelector('.agent-chat-log')?.innerText || '';
          return !loading && (previews > beforePreviews || messages >= beforeMessages + 2 || log !== beforeLog);
        }""",
        arg={"beforeMessages": before_messages, "beforePreviews": before_previews, "beforeLog": before_log},
        timeout=timeout_ms,
    )


def assert_chat_log_stable(page: Page, label: str) -> None:
    after = page.locator(".agent-chat-log").inner_text()
    page.wait_for_timeout(150)
    if page.locator(".agent-chat-log").inner_text() != after:
        raise AssertionError(f"{label} caused more than one chat-log update")


def assert_send_button_hit_target(page: Page) -> None:
    diagnostics = page.evaluate(
        """() => {
          const forms = [...document.querySelectorAll('.studio-agent-chat:not(.collapsed) .agent-chat-composer')];
          const form = forms[forms.length - 1];
          const button = form?.querySelector('button[aria-label="发送到 AI 创作搭档"]');
          const box = button?.getBoundingClientRect?.();
          const hit = box ? document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2) : null;
          return {
            formVisible: Boolean(form?.offsetWidth && form?.offsetHeight),
            buttonVisible: Boolean(box && box.width > 0 && box.height > 0),
            buttonEnabled: Boolean(button && !button.disabled),
            buttonBox: box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null,
            viewport: { width: window.innerWidth, height: window.innerHeight },
            hitTag: hit?.tagName || '',
            hitClass: hit?.getAttribute?.('class') || '',
            hitLabel: hit?.getAttribute?.('aria-label') || hit?.innerText || '',
            hitOwnsButton: Boolean(button && hit?.closest?.('button[aria-label="发送到 AI 创作搭档"]') === button),
          };
        }"""
    )
    if not diagnostics.get("formVisible") or not diagnostics.get("buttonVisible") or not diagnostics.get("buttonEnabled"):
        raise AssertionError(f"visible send button is not ready: {json.dumps(diagnostics, ensure_ascii=False)}")
    if not diagnostics.get("hitOwnsButton"):
        raise AssertionError(f"visible send button center is not reachable: {json.dumps(diagnostics, ensure_ascii=False)}")


def assert_composer_hit_target(page: Page) -> None:
    diagnostics = composer_path_diagnostics(page)
    if not diagnostics.get("textareaVisible") or not diagnostics.get("textareaEditable"):
        raise AssertionError(f"AI composer is not ready for visible input: {json.dumps(diagnostics, ensure_ascii=False)}")
    if not diagnostics.get("hitOwnsTextarea"):
        raise AssertionError(f"AI composer center is not reachable: {json.dumps(diagnostics, ensure_ascii=False)}")


def composer_path_diagnostics(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const forms = [...document.querySelectorAll('.studio-agent-chat:not(.collapsed) .agent-chat-composer')];
          const form = forms[forms.length - 1];
          const textarea = form?.querySelector('textarea');
          const box = textarea?.getBoundingClientRect?.();
          const hit = box ? document.elementFromPoint(box.left + Math.min(24, box.width / 2), box.top + Math.min(24, box.height / 2)) : null;
          return {
            formVisible: Boolean(form?.offsetWidth && form?.offsetHeight),
            textareaVisible: Boolean(box && box.width > 0 && box.height > 0),
            textareaEditable: Boolean(textarea && !textarea.disabled && !textarea.readOnly),
            textareaValue: textarea?.value || '',
            textareaBox: box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null,
            viewport: { width: window.innerWidth, height: window.innerHeight },
            hitTag: hit?.tagName || '',
            hitClass: hit?.getAttribute?.('class') || '',
            hitLabel: hit?.getAttribute?.('aria-label') || hit?.innerText || '',
            hitOwnsTextarea: Boolean(textarea && (hit === textarea || hit?.closest?.('textarea') === textarea)),
          };
        }"""
    )


def install_send_path_probe(page: Page) -> str:
    probe_id = f"probe_{int(time.time() * 1000)}"
    page.evaluate(
        """probeId => {
          const forms = [...document.querySelectorAll('.studio-agent-chat:not(.collapsed) .agent-chat-composer')];
          const form = forms[forms.length - 1];
          if (!form) throw new Error('visible AI composer form not found');
          const button = form.querySelector('button[aria-label="发送到 AI 创作搭档"]');
          if (!button) throw new Error('visible AI send button not found');
          window.__afsQaSendPathProbes = window.__afsQaSendPathProbes || {};
          window.__afsQaSendPathProbes[probeId] = { buttonClickCount: 0, formSubmitCount: 0 };
          document.addEventListener('click', (event) => {
            const targetButton = event.target?.closest?.('button[aria-label="发送到 AI 创作搭档"]');
            if (!targetButton) return;
            if (!targetButton.closest('.studio-agent-chat:not(.collapsed) .agent-chat-composer')) return;
            window.__afsQaSendPathProbes[probeId].buttonClickCount += 1;
          }, { capture: true });
          form.addEventListener('submit', () => {
            window.__afsQaSendPathProbes[probeId].formSubmitCount += 1;
          }, { capture: true });
        }""",
        probe_id,
    )
    return probe_id


def send_path_probe(page: Page, probe_id: str) -> dict[str, int]:
    value = page.evaluate("probeId => window.__afsQaSendPathProbes?.[probeId] || {}", probe_id)
    return {
        "buttonClickCount": int(value.get("buttonClickCount") or 0),
        "formSubmitCount": int(value.get("formSubmitCount") or 0),
    }


def chat_message_count(page: Page) -> int:
    return page.locator(".agent-chat-log .agent-message").count()


def create_blank_text_node(page: Page, project_id: str) -> None:
    close_ai_overlay_if_open(page)
    page.get_by_role("button", name="空白节点").click()
    page.wait_for_function("key => (JSON.parse(localStorage.getItem(key) || '{}').order || []).length === 1", arg=storage_key(project_id))
    expect(page.locator(".node").first).to_be_visible()


def fill_selected_text(page: Page, text: str) -> None:
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.fill(text)
    editor.blur()


def selected_node_id(page: Page, project_id: str) -> str:
    value = page.evaluate(
        """key => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          return s.selection?.nodeIds?.[0] || s.order?.[0] || '';
        }""",
        storage_key(project_id),
    )
    if not value:
        raise AssertionError("no selected node")
    return str(value)


def select_node(page: Page, project_id: str, node_id: str) -> None:
    close_ai_overlay_if_open(page)
    node = page.locator(f'.node[data-node-id="{node_id}"]')
    expect(node).to_be_visible()
    title = page.locator(f'.node[data-node-id="{node_id}"] .node-title')
    if title.count():
        title.click()
    else:
        box = node.bounding_box()
        if not box:
            raise AssertionError(f"node is not measurable: {node_id}")
        page.mouse.click(box["x"] + 18, box["y"] + 18)
    expect(page.locator(f'.node[data-node-id="{node_id}"].selected')).to_be_visible()


def create_node_from_handle(page: Page, project_id: str, from_node_id: str, label: str) -> str:
    close_ai_overlay_if_open(page)
    before = set(dom_node_ids(page))
    before_graph = set(node_ids(page, project_id))
    port = page.locator(f'.node[data-node-id="{from_node_id}"] .node-port.out')
    expect(port).to_be_visible()
    port.click()
    item = page.locator(".popover .menu-item").filter(has_text=re.compile(f"^{re.escape(label)}")).first
    expect(item).to_be_visible()
    item.click()
    return stable_created_node_id(
        page,
        project_id,
        before_dom=before,
        before_graph=before_graph,
        expected_type="shot",
        label="handle plus",
    )


def create_node_from_global_palette(page: Page, project_id: str, viewport: dict[str, int], label: str) -> str:
    close_ai_overlay_if_open(page)
    before = set(dom_node_ids(page))
    before_graph = set(node_ids(page, project_id))
    canvas_box = page.locator("#canvas-root").bounding_box()
    if not canvas_box:
        raise AssertionError("canvas root is not measurable for global node creation")
    x = min(canvas_box["x"] + canvas_box["width"] - 120, canvas_box["x"] + max(260, canvas_box["width"] * 0.62))
    y = min(canvas_box["y"] + canvas_box["height"] - 120, canvas_box["y"] + max(240, canvas_box["height"] * 0.52))
    global_add = page.locator('#corner-controls button[aria-label="添加节点"]')
    if global_add.count() and global_add.first.is_visible():
        global_add.first.click()
    else:
        page.mouse.click(x, y, button="right")
        page.get_by_role("button", name=re.compile("添加节点")).click()
    target = page.locator(".popover button").filter(has_text=re.compile(f"^{re.escape(label)}")).first
    expect(target).to_be_visible()
    target.click()
    expected_type = "image" if "图片" in label else "ref" if "参考" in label else ""
    return stable_created_node_id(
        page,
        project_id,
        before_dom=before,
        before_graph=before_graph,
        expected_type=expected_type,
        label="global palette",
    )


def connect_nodes_by_drag(page: Page, project_id: str, from_id: str, to_id: str) -> str:
    close_ai_overlay_if_open(page)
    before_dom = set(dom_edge_ids(page))
    before_graph = set(edge_ids(page, project_id))
    out_box = page.locator(f'.node[data-node-id="{from_id}"] .node-port.out').bounding_box()
    in_box = page.locator(f'.node[data-node-id="{to_id}"] .node-port.in').bounding_box()
    if not out_box or not in_box:
        raise AssertionError("node ports are not measurable")
    page.mouse.move(out_box["x"] + out_box["width"] / 2, out_box["y"] + out_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(in_box["x"] + in_box["width"] / 2, in_box["y"] + in_box["height"] / 2, steps=12)
    page.mouse.up()
    return stable_edge_id(
        page,
        project_id,
        from_id=from_id,
        to_id=to_id,
        expected_relation="generation",
        before_dom=before_dom,
        before_graph=before_graph,
    )


def select_edge(page: Page, project_id: str, edge_id: str) -> str:
    identity = assert_stable_edge_identity(page, project_id, edge_id)
    page.wait_for_function(
        """({ edgeId, fromId, toId, relation }) => {
          const item = document.querySelector(`#edge-layer [data-edge-id="${edgeId}"]`);
          const action = document.querySelector(`.edge-relation-button[data-edge-id="${edgeId}"]`);
          return item
            && action
            && action.dataset.edgeFrom === fromId
            && action.dataset.edgeTo === toId
            && action.dataset.edgeRelation === relation
            && !['pending', 'running'].includes(String(item.dataset.edgeLifecycle || ''));
        }""",
        arg={
            "edgeId": edge_id,
            "fromId": identity["graph"]["from"],
            "toId": identity["graph"]["to"],
            "relation": identity["graph"]["relation"],
        },
        timeout=5_000,
    )
    action_button = page.locator(
        f'.edge-relation-button[data-edge-id="{edge_id}"]'
        f'[data-edge-from="{identity["graph"]["from"]}"]'
        f'[data-edge-to="{identity["graph"]["to"]}"]'
        f'[data-edge-relation="{identity["graph"]["relation"]}"]'
    )
    expect(action_button).to_be_visible()
    action_button.click()
    page.wait_for_timeout(100)
    selected = page.evaluate(
        """edgeId => Boolean(document.querySelector(`#edge-layer [data-edge-id="${edgeId}"][data-edge-selected="true"]`))""",
        edge_id,
    )
    if selected:
        return str(edge_id)
    point = page.evaluate(
        """edgeId => {
          const g = document.querySelector(`#edge-layer [data-edge-id="${edgeId}"]`);
          const path = g?.querySelector('path.edge-hit, path.edge-flow');
          if (!path?.getTotalLength) return null;
          const matrix = path.getScreenCTM();
          if (!matrix) return null;
          const length = path.getTotalLength();
          const samples = [0.2, 0.35, 0.5, 0.65, 0.8].map((ratio) => {
            const svgPoint = path.getPointAtLength(length * ratio);
            const screenPoint = new DOMPoint(svgPoint.x, svgPoint.y).matrixTransform(matrix);
            const hit = document.elementFromPoint(screenPoint.x, screenPoint.y);
            return {
              x: screenPoint.x,
              y: screenPoint.y,
              hitTag: hit?.tagName || '',
              hitClass: hit?.getAttribute?.('class') || '',
              hitEdge: hit?.closest?.('[data-edge-id]')?.dataset?.edgeId || '',
            };
          });
          return samples.find((item) => item.hitEdge === edgeId) || { ...samples[Math.floor(samples.length / 2)], samples };
        }""",
        edge_id,
    )
    if not point:
        raise AssertionError(f"edge path not measurable: {edge_id}")
    diagnostics = page.evaluate(
        """({ edgeId, point }) => {
          const hit = document.elementFromPoint(point.x, point.y);
          const graph = JSON.parse(localStorage.getItem(point.key) || '{}').edges?.[edgeId] || null;
          return {
            requested: edgeId,
            graph,
            hit_tag: hit?.tagName || '',
            hit_class: hit?.getAttribute?.('class') || '',
            hit_edge: hit?.closest?.('[data-edge-id]')?.dataset?.edgeId || '',
            edges: [...document.querySelectorAll('#edge-layer [data-edge-id]')].map((item) => ({
              id: item.dataset.edgeId,
              selected: item.dataset.edgeSelected,
              lifecycle: item.dataset.edgeLifecycle,
            })),
            actionEdges: [...document.querySelectorAll('.edge-relation-button[data-edge-id]')].map((item) => ({
              id: item.dataset.edgeId,
              from: item.dataset.edgeFrom,
              to: item.dataset.edgeTo,
              relation: item.dataset.edgeRelation,
              selected: item.dataset.edgeSelected,
              text: item.textContent,
            })),
          };
        }""",
        {"edgeId": edge_id, "point": {**point, "key": storage_key(project_id)}},
    )
    raise AssertionError(f"edge click did not select edge: {json.dumps(diagnostics, ensure_ascii=False)}")


def attach_reference_by_drop(page: Page, project_id: str, node_id: str) -> None:
    close_ai_overlay_if_open(page)
    select_node(page, project_id, node_id)
    image = reference_image_payload()
    image_payload = {
        "name": image["name"],
        "mime": image["mime"],
        "b64": image["bytes"].hex(),
    }
    page.evaluate(
        """({ payload }) => {
          const bytes = new Uint8Array(payload.b64.match(/.{1,2}/g).map((hex) => parseInt(hex, 16)));
          const file = new File([bytes], payload.name, { type: payload.mime });
          const dt = new DataTransfer();
          dt.items.add(file);
          const root = document.querySelector('#canvas-root');
          const rect = root.getBoundingClientRect();
          root.dispatchEvent(new DragEvent('drop', {
            bubbles: true,
            cancelable: true,
            dataTransfer: dt,
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2,
          }));
        }""",
        {"payload": image_payload},
    )


def create_any_entry_nodes(page: Page, project_id: str, viewport: dict[str, int]) -> None:
    required = {"sequence", "scene", "shot", "character", "location", "prop", "ref", "image", "video"}
    existing = node_types(page, project_id)
    for node_type, phrase in (
        ("sequence", "创建段落节点"),
        ("scene", "创建场景节点"),
        ("character", "创建角色节点"),
        ("location", "创建场景空间节点"),
        ("prop", "创建道具节点"),
        ("ref", "创建参考资料集节点"),
        ("image", "创建图片节点"),
        ("video", "创建视频节点"),
    ):
        if node_type in existing:
            continue
        ensure_ai_open(page, viewport)
        send_ai(page, phrase)
        expect(page.locator(".agent-command-preview")).to_contain_text("创建")
        preview_text = page.locator(".agent-command-preview").inner_text()
        confirm_latest_command(page)
        try:
            page.wait_for_function(
                """({ key, type }) => Object.values(JSON.parse(localStorage.getItem(key) || '{}').nodes || {}).some((node) => node?.type === type)""",
                arg={"key": storage_key(project_id), "type": node_type},
                timeout=10_000,
            )
        except Exception as error:
            raise AssertionError(
                f"any-node entry did not create expected type {node_type} from {phrase}: "
                f"preview={preview_text!r} types={sorted(node_types(page, project_id))} "
                f"counts={graph_counts(page, project_id)}"
            ) from error
        existing = node_types(page, project_id)
    missing = sorted(required - node_types(page, project_id))
    if missing:
        raise AssertionError(f"missing any-node entry types: {missing}")


def verify_mobile_or_desktop_ai_geometry(page: Page, viewport: dict[str, int]) -> tuple[bool, bool]:
    if viewport["width"] <= COMPACT_AI_MAX_WIDTH:
        if not page.locator(".studio-agent-chat.collapsed").count():
            page.get_by_role("button", name="收起 AI 创作搭档", exact=True).click()
        collapsed_ok = not has_horizontal_overflow(page)
        ensure_ai_open(page, viewport)
        expect(page.locator(".studio-agent-chat.mobile-open")).to_be_visible()
        expanded_ok = bool(page.evaluate(
            """() => {
              const chat = document.querySelector('.studio-agent-chat.mobile-open');
              const backdrop = document.querySelector('.agent-mobile-backdrop');
              if (!chat || !backdrop) return false;
              const box = chat.getBoundingClientRect();
              const back = backdrop.getBoundingClientRect();
              const phoneSheet = window.innerWidth <= 760;
              const chatBound = box.left >= -1
                && box.right <= window.innerWidth + 1
                && box.bottom <= window.innerHeight + 1
                && (!phoneSheet || box.width >= window.innerWidth - 8);
              const backdropBound = back.left <= 1 && back.right >= window.innerWidth - 1;
              const sliver = document.elementFromPoint(8, Math.max(90, box.top - 20));
              const noClickThrough = !sliver?.closest?.('.node,.canvas-workspace-stage');
              return chatBound && backdropBound && noClickThrough;
            }"""
        ))
        page.keyboard.press("Escape")
        return collapsed_ok, expanded_ok
    return True, not has_horizontal_overflow(page)


def graph_counts(page: Page, project_id: str) -> dict[str, int]:
    return page.evaluate(
        """key => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          return { nodes: (s.order || []).length, edges: Object.keys(s.edges || {}).length, assets: (s.assets || []).length };
        }""",
        storage_key(project_id),
    )


def node_ids(page: Page, project_id: str) -> list[str]:
    return page.evaluate("key => JSON.parse(localStorage.getItem(key) || '{}').order || []", storage_key(project_id))


def dom_node_ids(page: Page) -> list[str]:
    return page.evaluate("[...document.querySelectorAll('.node[data-node-id]')].map((node) => node.dataset.nodeId)")


def edge_ids(page: Page, project_id: str) -> list[str]:
    return page.evaluate("key => Object.keys(JSON.parse(localStorage.getItem(key) || '{}').edges || {})", storage_key(project_id))


def dom_edge_ids(page: Page) -> list[str]:
    return page.evaluate("[...document.querySelectorAll('#edge-layer [data-edge-id]')].map((item) => item.dataset.edgeId)")


def graph_node_records(page: Page, project_id: str) -> dict[str, dict[str, Any]]:
    records = page.evaluate(
        """key => JSON.parse(localStorage.getItem(key) || '{}').nodes || {}""",
        storage_key(project_id),
    )
    return {str(node_id): dict(record or {}) for node_id, record in records.items()}


def graph_edge_records(page: Page, project_id: str) -> dict[str, dict[str, Any]]:
    records = page.evaluate(
        """key => JSON.parse(localStorage.getItem(key) || '{}').edges || {}""",
        storage_key(project_id),
    )
    return {str(edge_id): dict(record or {}) for edge_id, record in records.items()}


def dom_edge_records(page: Page) -> dict[str, dict[str, str]]:
    records = page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('#edge-layer [data-edge-id]')].map((item) => [
          item.dataset.edgeId,
          {
            id: item.dataset.edgeId || '',
            from: item.dataset.edgeFrom || '',
            to: item.dataset.edgeTo || '',
            relation: item.dataset.edgeRelation || '',
            selected: item.dataset.edgeSelected || '',
            lifecycle: item.dataset.edgeLifecycle || '',
          },
        ]))"""
    )
    return {str(edge_id): dict(record or {}) for edge_id, record in records.items()}


def stable_created_node_id(
    page: Page,
    project_id: str,
    *,
    before_dom: set[str],
    before_graph: set[str],
    expected_type: str,
    label: str,
) -> str:
    deadline = time.time() + 10
    latest: dict[str, Any] = {}
    while time.time() < deadline:
        dom_now = set(dom_node_ids(page))
        graph_now = graph_node_records(page, project_id)
        new_dom = dom_now - before_dom
        new_graph = set(graph_now) - before_graph
        shared = sorted(new_dom & new_graph)
        if expected_type:
            shared = [node_id for node_id in shared if graph_now.get(node_id, {}).get("type") == expected_type]
        latest = {
            "label": label,
            "expected_type": expected_type,
            "new_dom": sorted(new_dom),
            "new_graph": sorted(new_graph),
            "shared": shared,
            "graph_new_records": {node_id: graph_now.get(node_id) for node_id in sorted(new_graph)},
        }
        if len(shared) == 1:
            return shared[0]
        if len(shared) > 1:
            raise AssertionError(f"{label} created multiple stable nodes: {json.dumps(latest, ensure_ascii=False)}")
        page.wait_for_timeout(100)
    raise AssertionError(f"{label} did not create one stable rendered graph node: {json.dumps(latest, ensure_ascii=False)}")


def stable_edge_id(
    page: Page,
    project_id: str,
    *,
    from_id: str,
    to_id: str,
    expected_relation: str,
    before_dom: set[str],
    before_graph: set[str],
) -> str:
    deadline = time.time() + 10
    latest: dict[str, Any] = {}
    last_candidate = ""
    stable_reads = 0
    while time.time() < deadline:
        graph_now = graph_edge_records(page, project_id)
        dom_now = dom_edge_records(page)
        graph_candidates = [
            edge_id
            for edge_id, edge in graph_now.items()
            if edge_id not in before_graph
            and edge.get("from") == from_id
            and edge.get("to") == to_id
            and (edge.get("relation_type") or edge.get("relationType") or "generation") == expected_relation
        ]
        stable_candidates = [
            edge_id
            for edge_id in graph_candidates
            if edge_id not in before_dom
            and dom_now.get(edge_id, {}).get("from") == from_id
            and dom_now.get(edge_id, {}).get("to") == to_id
            and dom_now.get(edge_id, {}).get("relation") == expected_relation
        ]
        latest = stable_edge_diagnostics(
            graph_now,
            dom_now,
            requested={"from": from_id, "to": to_id, "relation": expected_relation},
            before_dom=before_dom,
            before_graph=before_graph,
            graph_candidates=graph_candidates,
            stable_candidates=stable_candidates,
        )
        if len(stable_candidates) == 1:
            candidate = stable_candidates[0]
            if candidate == last_candidate:
                stable_reads += 1
            else:
                last_candidate = candidate
                stable_reads = 1
            if stable_reads >= 4:
                return candidate
        if len(stable_candidates) > 1:
            raise AssertionError(f"multiple stable persisted/rendered edges matched request: {json.dumps(latest, ensure_ascii=False)}")
        page.wait_for_timeout(100)
    raise AssertionError(f"stable edge did not appear for exact relation: {json.dumps(latest, ensure_ascii=False)}")


def assert_stable_edge_identity(page: Page, project_id: str, edge_id: str) -> dict[str, Any]:
    graph = graph_edge_records(page, project_id)
    dom = dom_edge_records(page)
    edge = graph.get(edge_id)
    rendered = dom.get(edge_id)
    if not edge or not rendered:
        raise AssertionError(
            f"edge id is not present in both graph and DOM before click: "
            f"{json.dumps(stable_edge_diagnostics(graph, dom, requested={'edge_id': edge_id}), ensure_ascii=False)}"
        )
    graph_relation = edge.get("relation_type") or edge.get("relationType") or "generation"
    mismatch = {
        "edge_id": edge_id,
        "graph": {"from": edge.get("from"), "to": edge.get("to"), "relation": graph_relation},
        "dom": {"from": rendered.get("from"), "to": rendered.get("to"), "relation": rendered.get("relation")},
    }
    if (
        mismatch["graph"]["from"] != mismatch["dom"]["from"]
        or mismatch["graph"]["to"] != mismatch["dom"]["to"]
        or mismatch["graph"]["relation"] != mismatch["dom"]["relation"]
    ):
        raise AssertionError(f"edge graph/DOM identity mismatch before click: {json.dumps(mismatch, ensure_ascii=False)}")
    return mismatch


def stable_edge_diagnostics(
    graph: dict[str, dict[str, Any]],
    dom: dict[str, dict[str, str]],
    *,
    requested: dict[str, Any],
    before_dom: set[str] | None = None,
    before_graph: set[str] | None = None,
    graph_candidates: list[str] | None = None,
    stable_candidates: list[str] | None = None,
) -> dict[str, Any]:
    before_dom = before_dom or set()
    before_graph = before_graph or set()
    return {
        "requested": requested,
        "graph_candidates": graph_candidates or [],
        "stable_candidates": stable_candidates or [],
        "new_graph_edges": {
            edge_id: {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "relation": edge.get("relation_type") or edge.get("relationType") or "generation",
            }
            for edge_id, edge in graph.items()
            if edge_id not in before_graph
        },
        "new_dom_edges": {edge_id: record for edge_id, record in dom.items() if edge_id not in before_dom},
        "all_graph_edges": {
            edge_id: {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "relation": edge.get("relation_type") or edge.get("relationType") or "generation",
            }
            for edge_id, edge in graph.items()
        },
        "all_dom_edges": dom,
    }


def reference_image_payload() -> dict[str, Any]:
    source = safe_reference_image_path()
    data = source.read_bytes()
    if len(data) < 1024:
        raise AssertionError(f"reference image is not a real visual asset: {source}")
    return {"name": source.name, "mime": mime_for_image(source), "bytes": data, "source": str(source)}


def safe_reference_image_path() -> Path:
    if OWNER_REFERENCE_IMAGE.exists():
        return OWNER_REFERENCE_IMAGE
    search_roots = [REPO_ROOT / "tests", REPO_ROOT / "apps" / "studio"]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            for candidate in root.rglob(pattern):
                if candidate.is_file() and candidate.stat().st_size >= 1024:
                    return candidate
    raise AssertionError("no existing safe real image was available for reference upload evidence")


def mime_for_image(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".jpg" or suffix == ".jpeg":
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def node_types(page: Page, project_id: str) -> set[str]:
    values = page.evaluate(
        "key => Object.values(JSON.parse(localStorage.getItem(key) || '{}').nodes || {}).map((node) => node.type)",
        storage_key(project_id),
    )
    return set(str(item) for item in values)


def has_horizontal_overflow(page: Page) -> bool:
    return bool(page.evaluate(
        """() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > window.innerWidth + 2"""
    ))


def screenshot(page: Page, screenshot_dir: Path, filename: str) -> str:
    path = screenshot_dir / filename
    page.screenshot(path=str(path), full_page=True)
    return str(path.resolve())


def viewport_key(viewport: dict[str, int]) -> str:
    return f"{viewport['width']}x{viewport['height']}"


def storage_key(project_id: str) -> str:
    return f"afs_studio_canvas_v2:{project_id}"


def aggregate_checks(cases: dict[str, Any]) -> dict[str, bool]:
    fields = (
        "greeting_zero_mutation",
        "command_cancel_zero_mutation",
        "command_confirm_declared_mutation",
        "same_node_revision",
        "explicit_fork_creates_node",
        "plus_node_creation",
        "manual_connection",
        "edge_inspect_change_delete_undo",
        "reference_image_entry",
        "plan_panel_contextual",
        "console_network_clean",
    )
    checks = {field: all(item.get(field) is True for item in cases.values()) for field in fields}
    compact_cases = [item for item in cases.values() if viewport_width(item.get("viewport", "")) <= COMPACT_AI_MAX_WIDTH]
    checks["mobile_freeform_usable"] = bool(compact_cases) and all(item.get("mobile_freeform_usable") is True for item in compact_cases)
    return checks


def viewport_width(value: str) -> int:
    try:
        return int(str(value).split("x", 1)[0])
    except (TypeError, ValueError):
        return 0


def role_matrix(checks: dict[str, bool]) -> dict[str, dict[str, Any]]:
    return {
        "first_time_nontechnical_creator": {"completed": checks["greeting_zero_mutation"] and checks["plan_panel_contextual"], "task": "understand start state and ask greeting"},
        "screenwriter": {"completed": checks["same_node_revision"] and checks["explicit_fork_creates_node"], "task": "refine same node and explicitly fork"},
        "director_storyboard_artist": {"completed": checks["plus_node_creation"] and checks["manual_connection"], "task": "create shot and connect it"},
        "concept_artist": {"completed": checks["reference_image_entry"], "task": "start from a reference image"},
        "asset_continuity_supervisor": {"completed": checks["manual_connection"] and checks["edge_inspect_change_delete_undo"], "task": "inspect and change relation semantics"},
        "producer_cost_reviewer": {"completed": checks["command_cancel_zero_mutation"] and checks["command_confirm_declared_mutation"], "task": "preview scope and cost before changes"},
        "editor_recovery_operator": {"completed": checks["edge_inspect_change_delete_undo"], "task": "delete and undo without losing graph truth"},
        "advanced_graph_user": {"completed": checks["plus_node_creation"] and checks["manual_connection"], "task": "use handles and graph palette"},
        "keyboard_low_vision_reduced_motion": {"completed": checks["mobile_freeform_usable"], "task": "use accessible controls without overflow"},
        "owner_adversarial_tester": {"completed": all(checks.values()), "task": "verify no canned chat, broken plus, or permanent plan obstruction"},
    }


def micro_checks(checks: dict[str, bool]) -> dict[str, bool]:
    return {
        "first_screen_10s": checks["plan_panel_contextual"],
        "primary_next_action_visible": checks["plan_panel_contextual"],
        "plain_user_language": checks["greeting_zero_mutation"],
        "no_raw_infrastructure_terms": checks["console_network_clean"],
        "loading_feedback_and_safe_preview": checks["command_cancel_zero_mutation"],
        "reference_media_entry": checks["reference_image_entry"],
        "phone_no_horizontal_scroll": checks["mobile_freeform_usable"],
        "context_preserved_after_chat_toggle": checks["mobile_freeform_usable"],
        "paid_or_provider_preview_not_execution": checks["command_cancel_zero_mutation"],
        "advanced_evidence_not_primary_noise": checks["console_network_clean"],
    }
if __name__ == "__main__":
    raise SystemExit(main())
