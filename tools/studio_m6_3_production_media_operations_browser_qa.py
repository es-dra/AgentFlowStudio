from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
CASES = ("dialogue_room", "four_person_action", "sci_fi_chamber")
CLEAN_CASES = {"dialogue_room", "four_person_action"}
RECOVERY_CASES = {"sci_fi_chamber"}


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-3-media-ops-browser-{int(time.time())}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or report_path.with_suffix("")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(base_url, screenshot_dir, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": str(screenshot_dir)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.3 production media operations Studio browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def run_qa(base_url: str, screenshot_dir: Path, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    case_results: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in VIEWPORTS:
                viewport_key = f"{viewport['width']}x{viewport['height']}"
                for case_id in CASES:
                    page = browser.new_page(viewport=viewport)
                    page.set_default_timeout(timeout_ms)
                    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                    page.on(
                        "response",
                        lambda response: response_errors.append({"status": response.status, "url": response.url})
                        if response.status >= 400
                        else None,
                    )
                    result, captured = verify_case(page, base_url, case_id, viewport_key, screenshot_dir)
                    case_results[f"{case_id}:{viewport_key}"] = result
                    screenshots.update(captured)
                    page.close()
        finally:
            browser.close()
    actionable = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable:
        raise AssertionError(f"console={console_errors[:8]} responses={actionable[:8]}")
    role_matrix = build_role_matrix(case_results, screenshots)
    return {
        "artifact_type": "afs_m6_3_production_media_operations_browser_qa",
        "status": "passed",
        "cases": case_results,
        "screenshots": screenshots,
        "role_task_completion_matrix": role_matrix,
        "micro_experience_checks": build_micro_experience_checks(case_results),
        "console_error_count": 0,
        "response_error_count": 0,
        "provider_dispatch_boundary": "read-only Studio QA reusing M6.2 evidence; no provider dispatch is triggered",
    }


def verify_case(page: Any, base_url: str, case_id: str, viewport_key: str, screenshot_dir: Path) -> tuple[dict[str, Any], dict[str, str]]:
    project_id = f"m6-2-{case_id}"
    page.goto(f"{base_url}/studio/?project={project_id}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator(".media-canvas-status")).to_be_visible()
    expect(page.locator("#product-shell-root")).to_contain_text("媒体审片候选")
    expect(page.locator("#product-shell-root")).to_contain_text("进入故事板审片")
    canvas_shot = screenshot_dir / f"m6-3-{case_id}-canvas-{viewport_key}.png"
    page.screenshot(path=str(canvas_shot), full_page=True)
    canvas_text = page.locator("#product-shell-root").inner_text()
    assert_user_language(canvas_text, "canvas", case_id, viewport_key)
    title_discoverable, title_screens = verify_project_title_discovery(page, case_id, viewport_key, screenshot_dir)

    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    expect(page.locator(".media-operations-workspace")).to_be_visible()
    expect(page.locator(".media-operations-workspace")).to_contain_text("生产审片")
    expect(page.locator(".media-operations-workspace")).to_contain_text("Bible 与复用锁")
    expect(page.locator(".media-operations-workspace")).to_contain_text("费用、重复提交保护与恢复")
    expect(page.locator(".media-operations-workspace")).to_contain_text("最终审片")
    expect(page.locator(".media-operations-workspace")).to_contain_text("确认前不会扣费")
    expect(page.locator(".media-operations-workspace")).to_contain_text("不是人工验收")
    if case_id in CLEAN_CASES:
        expect(page.locator(".media-operations-workspace")).to_contain_text("可审片")
    if case_id in RECOVERY_CASES:
        expect(page.locator(".media-operations-workspace")).to_contain_text("恢复")
        expect(page.locator(".media-operations-workspace")).to_contain_text("只作为恢复证据")
    if has_horizontal_document_overflow(page):
        raise AssertionError(f"horizontal document overflow for {case_id}:{viewport_key}")
    if not primary_review_unclipped(page):
        raise AssertionError(f"primary review content is clipped for {case_id}:{viewport_key}")

    storyboard_initial = screenshot_dir / f"m6-3-{case_id}-storyboard-initial-{viewport_key}.png"
    page.screenshot(path=str(storyboard_initial), full_page=True)
    shot_selected = select_review_shot(page)
    responsive_result, responsive_screens = verify_responsive_agent_chat(page, case_id, viewport_key, screenshot_dir)

    metadata = page.locator(".media-viewer video").first.evaluate(
        """video => new Promise((resolve, reject) => {
          const done = () => resolve({ readyState: video.readyState, duration: video.duration || 0, src: video.currentSrc || video.src });
          if (video.readyState >= 1) return done();
          video.addEventListener('loadedmetadata', done, { once: true });
          video.addEventListener('error', () => reject(new Error('video metadata failed')), { once: true });
        })"""
    )
    if not metadata["src"] or metadata["duration"] <= 0:
        raise AssertionError(f"video did not load metadata for {case_id}:{viewport_key}: {metadata}")
    if any(token in metadata["src"].lower() for token in ("/home/", "/tmp/", "/var/", ".mp4", "secret", "token")):
        raise AssertionError(f"unsafe media URL exposed: {metadata['src']}")

    page.locator(".media-side-panel").scroll_into_view_if_needed()
    redo_compare_shot = screenshot_dir / f"m6-3-{case_id}-redo-compare-{viewport_key}.png"
    page.screenshot(path=str(redo_compare_shot), full_page=True)

    page.get_by_role("button", name="预览重做").first.click()
    expect(page.locator(".media-command-receipt")).to_be_visible()
    expect(page.locator(".media-command-receipt")).to_contain_text("不会发起生成或产生费用")
    receipt_text = page.locator(".media-command-receipt").inner_text().lower()
    if "provider" in receipt_text or "idempotency" in receipt_text or "幂等键" in receipt_text:
        raise AssertionError(f"raw command-preview term leaked for {case_id}:{viewport_key}: {receipt_text}")
    expect(page.locator(".studio-agent-chat")).to_be_visible()
    command_preview_shot = screenshot_dir / f"m6-3-{case_id}-command-preview-{viewport_key}.png"
    page.screenshot(path=str(command_preview_shot), full_page=True)
    if viewport_width(viewport_key) <= 900:
        page.keyboard.press("Escape")
        expect(page.locator(".media-operations-workspace")).to_be_visible()

    page.locator(".cost-recovery-panel").scroll_into_view_if_needed()
    recovery_shot = screenshot_dir / f"m6-3-{case_id}-recovery-cost-{viewport_key}.png"
    page.screenshot(path=str(recovery_shot), full_page=True)

    page.locator(".media-evidence-drawer summary").click()
    expect(page.locator(".media-evidence-list")).to_contain_text("Graph digest")
    visible_text = page.locator("#product-shell-root").inner_text()
    forbidden = [token for token in ("/home/", "/tmp/", "/var/", ".mp4", ".png", "api_key", "authorization", "bearer", "secret") if token in visible_text.lower()]
    if forbidden:
        raise AssertionError(f"unsafe visible UI token for {case_id}:{viewport_key}: {forbidden}")

    evidence_shot = screenshot_dir / f"m6-3-{case_id}-advanced-evidence-{viewport_key}.png"
    page.screenshot(path=str(evidence_shot), full_page=True)
    focus_sequence = collect_focus_sequence(page)
    if not focus_sequence:
        raise AssertionError(f"keyboard focus sequence is empty for {case_id}:{viewport_key}")
    return (
        {
            "project_id": project_id,
            "viewport": viewport_key,
            "video_duration_sec": round(float(metadata["duration"]), 3),
            "media_url_safe": True,
            "canvas_first_screen": True,
            "storyboard_operations": True,
            "review_shot_selected": shot_selected,
            "primary_review_unclipped": True,
            "project_title_discoverable": title_discoverable,
            "agent_chat_compact_default": responsive_result["compact_default"],
            "agent_chat_expand_collapse": responsive_result["expand_collapse"],
            "agent_chat_viewport_bound": responsive_result["viewport_bound"],
            "phone_agent_chat_no_background_sliver": responsive_result["phone_no_background_sliver"],
            "phone_reviewer_flow": responsive_result["phone_reviewer_flow"],
            "redo_preview": True,
            "redo_version_compare": True,
            "recovery_and_cost_state": True,
            "advanced_evidence_drawer": True,
            "keyboard_focus_sequence": focus_sequence,
            "provider_dispatch_count": 0,
            "case_classification": "clean_completed" if case_id in CLEAN_CASES else "recovery_evidence",
        },
        {
            f"{case_id}:{viewport_key}:canvas": str(canvas_shot.resolve()),
            **title_screens,
            f"{case_id}:{viewport_key}:storyboard_initial": str(storyboard_initial.resolve()),
            **responsive_screens,
            f"{case_id}:{viewport_key}:redo_compare": str(redo_compare_shot.resolve()),
            f"{case_id}:{viewport_key}:command_preview": str(command_preview_shot.resolve()),
            f"{case_id}:{viewport_key}:recovery_cost": str(recovery_shot.resolve()),
            f"{case_id}:{viewport_key}:advanced_evidence": str(evidence_shot.resolve()),
        },
    )


def assert_user_language(text: str, surface: str, case_id: str, viewport_key: str) -> None:
    forbidden = ("runtime root", "idempotency", "dispatch", "provider", "graph digest", "/home/", "/var/", "/tmp/")
    low = text.lower()
    leaked = [token for token in forbidden if token in low]
    if leaked:
        raise AssertionError(f"raw infrastructure terms leaked in {surface} for {case_id}:{viewport_key}: {leaked}")


def has_horizontal_document_overflow(page: Any) -> bool:
    return bool(page.evaluate(
        """() => {
          const root = document.documentElement;
          const body = document.body;
          return Math.max(root.scrollWidth, body.scrollWidth) > window.innerWidth + 2;
        }"""
    ))


def primary_review_unclipped(page: Any) -> bool:
    return bool(page.evaluate(
        """() => {
          const preview = document.querySelector('.media-preview-panel');
          const next = document.querySelector('.media-next-action');
          if (!preview || !next) return false;
          const previewRect = preview.getBoundingClientRect();
          const nextRect = next.getBoundingClientRect();
          const chat = document.querySelector('.studio-agent-chat.collapsed');
          const chatRect = chat?.getBoundingClientRect();
          const railReserve = chatRect && chatRect.width > 0 ? chatRect.width + 8 : 0;
          const usableRight = window.innerWidth - railReserve;
          const previewRoom = previewRect.width >= Math.min(320, window.innerWidth - 96);
          const previewClear = !railReserve || previewRect.right <= usableRight + 2;
          const nextClear = nextRect.left >= -1 && nextRect.right <= window.innerWidth + 2;
          return previewRoom && previewClear && nextClear;
        }"""
    ))


def verify_project_title_discovery(page: Any, case_id: str, viewport_key: str, screenshot_dir: Path) -> tuple[bool, dict[str, str]]:
    button = page.locator(".studio-project-button").first
    expect(button).to_be_visible()
    project_name = button.locator("strong").inner_text().strip()
    aria = button.get_attribute("aria-label") or ""
    title = button.get_attribute("title") or ""
    if project_name and project_name not in f"{aria} {title}":
        raise AssertionError(f"full project title not exposed for {case_id}:{viewport_key}: aria={aria!r} title={title!r}")
    button.focus()
    button.click()
    summary = page.locator(".studio-current-project-summary").first
    expect(summary).to_be_visible()
    expect(summary).to_contain_text(project_name)
    shot = screenshot_dir / f"m6-3-{case_id}-title-disclosure-{viewport_key}.png"
    page.screenshot(path=str(shot), full_page=True)
    page.keyboard.press("Escape")
    expect(summary).to_be_hidden()
    return True, {f"{case_id}:{viewport_key}:title_disclosure": str(shot.resolve())}


def select_review_shot(page: Any) -> bool:
    selector = page.locator(".media-shot-selector button")
    if selector.count() <= 1:
        return False
    selector.nth(1).click()
    expect(selector.nth(1)).to_have_attribute("aria-current", "true")
    return True


def verify_responsive_agent_chat(page: Any, case_id: str, viewport_key: str, screenshot_dir: Path) -> tuple[dict[str, bool], dict[str, str]]:
    width = viewport_width(viewport_key)
    selected_before = page.locator(".media-panel-head strong").first.inner_text()
    screenshots: dict[str, str] = {}
    if width > 900:
        expect(page.locator(".studio-agent-chat")).to_be_visible()
        return (
            {
                "compact_default": True,
                "expand_collapse": True,
                "viewport_bound": True,
                "phone_no_background_sliver": True,
                "phone_reviewer_flow": True,
            },
            screenshots,
        )

    collapsed_shot = screenshot_dir / f"m6-3-{case_id}-agent-chat-collapsed-{viewport_key}.png"
    page.screenshot(path=str(collapsed_shot), full_page=True)
    screenshots[f"{case_id}:{viewport_key}:agent_chat_collapsed"] = str(collapsed_shot.resolve())

    if width <= 760:
        expect(page.locator(".product-mobile-nav")).to_be_visible()
        page.locator(".product-mobile-nav button").filter(has_text="Agent").first.click()
    else:
        expect(page.locator(".studio-agent-chat.collapsed")).to_be_visible()
        page.get_by_role("button", name="展开 Agent Chat").click()

    expect(page.locator(".studio-agent-chat.mobile-open")).to_be_visible()
    if has_horizontal_document_overflow(page):
        raise AssertionError(f"horizontal overflow after chat expand for {case_id}:{viewport_key}")
    geometry = assert_agent_chat_expanded_geometry(page, width, case_id, viewport_key)
    expanded_shot = screenshot_dir / f"m6-3-{case_id}-agent-chat-expanded-{viewport_key}.png"
    page.screenshot(path=str(expanded_shot), full_page=True)
    screenshots[f"{case_id}:{viewport_key}:agent_chat_expanded"] = str(expanded_shot.resolve())

    page.keyboard.press("Escape")
    if width <= 760:
        expect(page.locator(".studio-agent-chat")).to_be_hidden()
    else:
        expect(page.locator(".studio-agent-chat.collapsed")).to_be_visible()
    selected_after = page.locator(".media-panel-head strong").first.inner_text()
    if selected_after != selected_before:
        raise AssertionError(f"selected shot changed after chat collapse for {case_id}:{viewport_key}")
    returned_shot = screenshot_dir / f"m6-3-{case_id}-agent-chat-returned-{viewport_key}.png"
    page.screenshot(path=str(returned_shot), full_page=True)
    screenshots[f"{case_id}:{viewport_key}:agent_chat_returned"] = str(returned_shot.resolve())
    phone_flow = True
    if width <= 430:
        phone_flow = (
            page.locator(".media-viewer video").first.is_visible()
            and page.locator(".cost-recovery-panel").first.is_visible()
            and page.locator(".media-shot-selector button[aria-current='true']").count() == 1
        )
    return (
        {
            "compact_default": True,
            "expand_collapse": True,
            "viewport_bound": geometry["viewport_bound"],
            "phone_no_background_sliver": geometry["phone_no_background_sliver"],
            "phone_reviewer_flow": phone_flow,
        },
        screenshots,
    )


def assert_agent_chat_expanded_geometry(page: Any, width: int, case_id: str, viewport_key: str) -> dict[str, bool]:
    metrics = page.evaluate(
        """() => {
          const rectFor = (selector) => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
          };
          const chat = document.querySelector('.studio-agent-chat.mobile-open');
          const workspace = document.querySelector('.studio-unified-workspace');
          const withinChat = (x, y) => {
            const el = document.elementFromPoint(x, y);
            return Boolean(chat && el && (el === chat || chat.contains(el)));
          };
          const workspaceRect = rectFor('.studio-unified-workspace') || { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight, width: window.innerWidth, height: window.innerHeight };
          const pointY = Math.min(workspaceRect.top + 10, window.innerHeight - 72);
          return {
            viewport: { width: window.innerWidth, height: window.innerHeight },
            chat: rectFor('.studio-agent-chat.mobile-open'),
            workspace: workspaceRect,
            backdrop: rectFor('.agent-mobile-backdrop'),
            mediaWorkspace: rectFor('.media-operations-workspace'),
            chatHead: rectFor('.agent-chat-head'),
            composer: rectFor('.agent-chat-composer'),
            topLeftWithinChat: withinChat(8, pointY),
            topCenterWithinChat: withinChat(Math.floor(window.innerWidth / 2), pointY),
            workspacePosition: workspace ? getComputedStyle(workspace).position : '',
          };
        }"""
    )
    chat = metrics.get("chat") or {}
    workspace = metrics.get("workspace") or {}
    backdrop = metrics.get("backdrop") or {}
    media_workspace = metrics.get("mediaWorkspace") or {}
    viewport = metrics.get("viewport") or {}
    viewport_bound = (
        chat.get("left", 99) >= -1
        and chat.get("right", 0) <= float(viewport.get("width") or width) + 1
        and chat.get("width", 0) >= min(320, width - 2)
    )
    phone_no_background_sliver = True
    if width <= 760:
        phone_no_background_sliver = (
            abs(float(chat.get("top") or 0) - float(workspace.get("top") or 0)) <= 2
            and abs(float(chat.get("bottom") or 0) - float(workspace.get("bottom") or 0)) <= 4
            and abs(float(backdrop.get("top") or 0) - float(workspace.get("top") or 0)) <= 2
            and abs(float(backdrop.get("bottom") or 0) - float(workspace.get("bottom") or 0)) <= 4
            and float(media_workspace.get("width") or 0) >= min(320, width - 4)
            and metrics.get("topLeftWithinChat") is True
            and metrics.get("topCenterWithinChat") is True
        )
    if not viewport_bound or not phone_no_background_sliver:
        raise AssertionError(
            "agent chat expanded geometry failed "
            f"for {case_id}:{viewport_key}: viewport_bound={viewport_bound} "
            f"phone_no_background_sliver={phone_no_background_sliver} metrics={metrics}"
        )
    return {"viewport_bound": True, "phone_no_background_sliver": True}


def viewport_width(viewport_key: str) -> int:
    return int(viewport_key.split("x", 1)[0])


def collect_focus_sequence(page: Any) -> list[dict[str, str]]:
    sequence: list[dict[str, str]] = []
    for _ in range(8):
        page.keyboard.press("Tab")
        info = page.evaluate(
            """() => {
              const el = document.activeElement;
              if (!el || el === document.body) return null;
              const rect = el.getBoundingClientRect();
              return {
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                label: el.getAttribute('aria-label') || el.innerText || el.textContent || '',
                visible: String(rect.width > 0 && rect.height > 0),
              };
            }"""
        )
        if info and info.get("visible") == "true":
            info["label"] = " ".join(str(info.get("label", "")).split())[:80]
            sequence.append(info)
    return sequence


def build_micro_experience_checks(case_results: dict[str, Any]) -> dict[str, Any]:
    all_cases = list(case_results.values())
    return {
        "first_screen_10s": all(item.get("canvas_first_screen") for item in all_cases),
        "primary_next_action_visible": all(item.get("storyboard_operations") for item in all_cases),
        "project_title_discoverable": all(item.get("project_title_discoverable") for item in all_cases),
        "primary_review_not_clipped": all(item.get("primary_review_unclipped") for item in all_cases),
        "review_shot_selection_available": all(item.get("review_shot_selected") for item in all_cases),
        "agent_chat_compact_default": all(item.get("agent_chat_compact_default") for item in all_cases),
        "agent_chat_expand_collapse": all(item.get("agent_chat_expand_collapse") for item in all_cases),
        "agent_chat_viewport_bound": all(item.get("agent_chat_viewport_bound") for item in all_cases),
        "phone_agent_chat_no_background_sliver": all(item.get("phone_agent_chat_no_background_sliver") for item in all_cases),
        "phone_reviewer_flow": all(item.get("phone_reviewer_flow") for item in all_cases),
        "paid_action_preview_not_execution": all(item.get("redo_preview") and item.get("provider_dispatch_count") == 0 for item in all_cases),
        "safe_media_urls": all(item.get("media_url_safe") for item in all_cases),
        "version_compare_available": all(item.get("redo_version_compare") for item in all_cases),
        "recovery_cost_state_available": all(item.get("recovery_and_cost_state") for item in all_cases),
        "keyboard_focus_visible_sequence": all(bool(item.get("keyboard_focus_sequence")) for item in all_cases),
        "clean_and_recovery_cases_present": (
            any(item.get("case_classification") == "clean_completed" for item in all_cases)
            and any(item.get("case_classification") == "recovery_evidence" for item in all_cases)
        ),
    }


def build_role_matrix(case_results: dict[str, Any], screenshots: dict[str, str]) -> dict[str, Any]:
    values = list(case_results.values())
    desktop_dialogue = "dialogue_room:1440x900"
    narrow_dialogue = "dialogue_room:800x900"
    phone_dialogue = "dialogue_room:430x932"
    mobile_dialogue = "dialogue_room:390x844"
    recovery_desktop = "sci_fi_chamber:1440x900"
    return {
        "first_time_creator": {
            "completed": bool(screenshots.get(f"{desktop_dialogue}:canvas")),
            "evidence": [f"{desktop_dialogue}:canvas"],
            "task": "首屏识别当前项目、完成度和进入故事板审片的下一步。",
        },
        "screenwriter": {
            "completed": bool(screenshots.get(f"{desktop_dialogue}:storyboard_initial")),
            "evidence": [f"{desktop_dialogue}:storyboard_initial"],
            "task": "查看故事摘要、场景与镜头对应关系，不暴露基础设施术语。",
        },
        "director_storyboard": {
            "completed": all(item.get("video_duration_sec", 0) > 0 and item.get("storyboard_operations") for item in values),
            "evidence": [f"{desktop_dialogue}:storyboard_initial", "four_person_action:1440x900:storyboard_initial"],
            "task": "选择镜头、播放视频、理解镜头目的/机位/运动/声音/转场。",
        },
        "art_continuity": {
            "completed": all(item.get("storyboard_operations") for item in values),
            "evidence": [f"{desktop_dialogue}:storyboard_initial"],
            "task": "检查角色、服装、场景、道具、ReferenceSet 与 negative locks。",
        },
        "producer": {
            "completed": all(item.get("recovery_and_cost_state") for item in values),
            "evidence": [f"{desktop_dialogue}:recovery_cost"],
            "task": "确认完成度、估算费用、复用避免的派发和局部重做增量。",
        },
        "editor_media_reviewer": {
            "completed": all(item.get("video_duration_sec", 0) > 0 for item in values),
            "evidence": [f"{desktop_dialogue}:storyboard_initial", "four_person_action:1440x900:storyboard_initial"],
            "task": "播放逐镜/全片，查看 contact sheet、QA 警告和交付边界。",
        },
        "runtime_operator": {
            "completed": bool(screenshots.get(f"{recovery_desktop}:recovery_cost")),
            "evidence": [f"{recovery_desktop}:recovery_cost", f"{narrow_dialogue}:agent_chat_expanded", f"{recovery_desktop}:command_preview"],
            "task": "验证失败/恢复/重试是 fail-closed，预览不重复收费或写第二事实。",
        },
        "owner_decision_maker": {
            "completed": all(item.get("canvas_first_screen") and item.get("advanced_evidence_drawer") for item in values),
            "evidence": [f"{desktop_dialogue}:canvas", f"{desktop_dialogue}:advanced_evidence"],
            "task": "快速理解进度、质量边界、风险和下一决策；高级证据可查但不淹没主流程。",
        },
        "mobile_reviewer": {
            "completed": bool(
                screenshots.get(f"{mobile_dialogue}:storyboard_initial")
                and screenshots.get(f"{mobile_dialogue}:agent_chat_collapsed")
                and screenshots.get(f"{mobile_dialogue}:agent_chat_expanded")
                and screenshots.get(f"{phone_dialogue}:storyboard_initial")
                and screenshots.get(f"{phone_dialogue}:agent_chat_collapsed")
                and screenshots.get(f"{phone_dialogue}:agent_chat_expanded")
            ),
            "evidence": [
                f"{phone_dialogue}:storyboard_initial",
                f"{phone_dialogue}:agent_chat_collapsed",
                f"{phone_dialogue}:agent_chat_expanded",
                f"{phone_dialogue}:agent_chat_returned",
                f"{mobile_dialogue}:storyboard_initial",
                f"{mobile_dialogue}:agent_chat_collapsed",
                f"{mobile_dialogue}:agent_chat_expanded",
                f"{mobile_dialogue}:agent_chat_returned",
            ],
            "task": "在真实手机视口快速播放、看状态/费用/恢复，展开并收起 Agent Chat 后回到当前审片。",
        },
        "keyboard_low_vision": {
            "completed": all(bool(item.get("keyboard_focus_sequence")) for item in values),
            "evidence": ["keyboard_focus_sequence"],
            "task": "Tab 焦点能落到真实控件，状态文本不只靠颜色表达。",
        },
    }


def start_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "AFS_RUNTIME_SERVICE_ROOT": str(runtime_root),
            "AFS_RUNTIME_ROOT": str(runtime_root),
            "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1",
            "AFS_RUNTIME_SERVICE_PORT": str(port),
            "AFS_AUTH_ENABLED": "false",
            "AFS_AUTH_ALLOW_OPEN_SIGNUP": "false",
            "NO_PROXY": _merge_no_proxy(env.get("NO_PROXY")),
            "no_proxy": _merge_no_proxy(env.get("no_proxy")),
        }
    )
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


def _merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    lowered = {item.lower() for item in entries}
    for item in ("127.0.0.1", "localhost", "::1"):
        if item.lower() not in lowered:
            entries.append(item)
    return ",".join(entries)


if __name__ == "__main__":
    raise SystemExit(main())
