from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from workbench_libtv_browser_qa_common import assert_url_available
from workbench_libtv_browser_qa_common import capture_node_control_feedback
from workbench_libtv_browser_qa_common import is_provider_request
from workbench_libtv_browser_qa_common import workbench_url
from workbench_libtv_browser_qa_common import write_stdout


DEFAULT_BASE_URL = "http://127.0.0.1:8790/workbench/"
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_workflow_node_open_browser_qa")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")

NODE_CASES = [
    {"node_id": "script-input", "expected_selector": ".libtv-text-node-flow", "expected_kind": "text"},
    {"node_id": "storyboard", "expected_selector": ".libtv-script-generator-flow", "expected_kind": "script"},
    {"node_id": "character", "expected_selector": ".libtv-image-node-flow", "expected_kind": "image"},
    {"node_id": "scene", "expected_selector": ".libtv-image-node-flow", "expected_kind": "image"},
    {"node_id": "keyframe", "expected_selector": ".libtv-image-node-flow", "expected_kind": "image"},
    {"node_id": "director", "expected_selector": ".director-flow-v3", "expected_kind": "director"},
    {"node_id": "clip", "expected_selector": ".libtv-video-node-flow", "expected_kind": "video"},
    {"node_id": "compose", "expected_selector": ".libtv-video-merge-flow", "expected_kind": "video_merge"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify workflow node open transitions in a real browser.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"Playwright is required. Install with: {sys.executable} -m pip install playwright") from exc

    base_url = workbench_url(args.base_url)
    assert_url_available(base_url)
    output_dir = args.output_dir.resolve()
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_request_urls: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.on("request", lambda request: provider_request_urls.append(request.url) if is_provider_request(request.url, PROVIDER_REQUEST_PATTERNS) else None)
                capture = _run_node_open_qa(page, base_url, screenshot_dir, provider_request_urls)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Workflow node open QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Workflow node open QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_workflow_node_open_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "capture": capture,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "provider_request_urls": provider_request_urls,
        "provider_calls_started": bool(provider_request_urls),
        "non_claims": ["not human acceptance", "not business validation", "not provider smoke"],
    }
    failures = _qa_failures(report)
    report["qa_status"] = "failed" if failures else "passed"
    report["failures"] = failures
    report_path = output_dir / "workbench_libtv_workflow_node_open_browser_qa.json"
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized, encoding="utf-8")
    write_stdout(serialized)
    if failures:
        raise SystemExit(f"Workflow node open QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _run_node_open_qa(page: Any, base_url: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator("[data-view='Create']").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)

    cases: list[dict[str, Any]] = []
    for item in NODE_CASES:
        open_button = page.locator(f"[data-open-node-id='{item['node_id']}']").first
        open_button.wait_for(state="visible", timeout=10_000)
        open_kind = open_button.get_attribute("data-open-node-kind")
        open_button.click()
        expected = page.locator(item["expected_selector"]).first
        expected.wait_for(state="visible", timeout=10_000)
        context = page.locator(".node-open-context-bar").first
        context.wait_for(state="visible", timeout=10_000)
        opened_node_id = expected.get_attribute("data-opened-node-id")
        expected_visible = expected.is_visible()
        context_visible = context.is_visible()
        context_node_id = context.get_attribute("data-node-open-context")
        context_kind = context.get_attribute("data-node-open-kind")
        context_chain_count = page.locator(".node-open-context-bar .context-chain").count()
        context_return_visible = page.locator(".node-open-context-bar [data-studio-starter='close']").first.is_visible()
        node_flow_shell_visible = page.locator(".node-flow-shell").first.is_visible()
        transition = expected.get_attribute("data-node-open-transition")
        transition_animation = expected.evaluate("node => getComputedStyle(node).animationName")
        prompt_optimizer_visible = page.locator("[data-action='optimize-current-prompt']").count() > 0
        prompt_generate = _capture_prompt_generation_feedback(page, item["expected_kind"])
        node_control = capture_node_control_feedback(
            page,
            skipped=item["expected_kind"] in {"director", "video_merge"},
            reason="node has no parameter control contract",
        )
        screenshot_path = screenshot_dir / f"{item['node_id']}.png"
        page.screenshot(path=screenshot_path, full_page=False)
        context_navigation = _capture_context_navigation(page, item["node_id"])
        page.locator("[data-studio-starter='close']").first.click()
        page.locator(f"[data-node-id='{item['node_id']}']").first.wait_for(state="visible", timeout=10_000)
        return_transition = page.locator(".workflow-node-layer").first.get_attribute("data-node-open-transition")
        return_animation = page.locator(f"[data-node-id='{item['node_id']}']").first.evaluate("node => getComputedStyle(node).animationName")
        cases.append({
            **item,
            "open_kind": open_kind,
            "opened_node_id": opened_node_id,
            "expected_visible": expected_visible,
            "context_visible": context_visible,
            "context_node_id": context_node_id,
            "context_kind": context_kind,
            "context_chain_count": context_chain_count,
            "context_return_visible": context_return_visible,
            "node_flow_shell_visible": node_flow_shell_visible,
            "transition": transition,
            "transition_animation": transition_animation,
            "prompt_optimizer_visible": prompt_optimizer_visible,
            "prompt_generate": prompt_generate,
            "node_control": node_control,
            "context_navigation": context_navigation,
            "return_transition": return_transition,
            "return_animation": return_animation,
            "returned_to_canvas": page.locator(f"[data-node-id='{item['node_id']}']").first.is_visible(),
            "screenshot": screenshot_path.as_posix(),
        })

    return {
        "cases": cases,
        "viewport_overflow": _viewport_overflow(page),
        "provider_calls_started": bool(provider_urls),
    }


def _capture_prompt_generation_feedback(page: Any, expected_kind: str) -> dict[str, Any]:
    if expected_kind in {"director", "video_merge"}:
        return {"skipped": True, "reason": "node has no prompt generation control"}
    button = page.locator("[data-action='run-node-generation-preview']").first
    status = page.locator("[data-node-generation-status]").first
    if button.count() == 0 or status.count() == 0:
        return {"skipped": False, "button_visible": False, "status_visible": False}
    before_status = status.get_attribute("data-node-generation-status")
    surface = button.get_attribute("data-node-generate-surface")
    button_visible = button.is_visible()
    status_visible = status.is_visible()
    button.click()
    page.wait_for_function(
        "() => document.querySelector('[data-node-generation-status]')?.getAttribute('data-node-generation-status') === 'complete'",
        timeout=8_000,
    )
    after = page.locator("[data-node-generation-status]").first
    return {
        "skipped": False,
        "button_visible": button_visible,
        "status_visible": status_visible,
        "surface": surface,
        "before_status": before_status,
        "after_status": after.get_attribute("data-node-generation-status"),
        "status_text": after.inner_text(),
    }


def _capture_context_navigation(page: Any, node_id: str) -> dict[str, Any]:
    if node_id != "script-input":
        return {"skipped": True, "reason": "covered by script-input downstream navigation"}
    target_id = "storyboard"
    target = page.locator(f".node-open-context-bar [data-context-nav-node='{target_id}']").first
    if target.count() == 0:
        return {"skipped": False, "target_visible": False}
    target_visible = target.is_visible()
    target_kind = target.get_attribute("data-open-node-kind")
    target.click()
    page.locator(".libtv-script-generator-flow").first.wait_for(state="visible", timeout=10_000)
    context = page.locator(".node-open-context-bar").first
    return {
        "skipped": False,
        "target_visible": target_visible,
        "target_id": target_id,
        "target_kind": target_kind,
        "after_context_id": context.get_attribute("data-node-open-context"),
        "after_context_kind": context.get_attribute("data-node-open-kind"),
        "after_transition": page.locator(".libtv-script-generator-flow").first.get_attribute("data-node-open-transition"),
        "after_transition_animation": page.locator(".libtv-script-generator-flow").first.evaluate("node => getComputedStyle(node).animationName"),
        "target_panel_visible": page.locator(".libtv-script-generator-flow").first.is_visible(),
    }


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for case in report["capture"]["cases"]:
        if case["open_kind"] != case["expected_kind"]:
            failures.append(f"{case['node_id']}: expected kind {case['expected_kind']}, got {case['open_kind']}")
        if case["opened_node_id"] != case["node_id"]:
            failures.append(f"{case['node_id']}: opened node id was not preserved")
        if not case["expected_visible"]:
            failures.append(f"{case['node_id']}: expected node panel not visible")
        if not case["context_visible"]:
            failures.append(f"{case['node_id']}: node open context bar not visible")
        if case["context_node_id"] != case["node_id"]:
            failures.append(f"{case['node_id']}: node open context id was not preserved")
        if case["context_kind"] != case["expected_kind"]:
            failures.append(f"{case['node_id']}: context kind expected {case['expected_kind']}, got {case['context_kind']}")
        if case["context_chain_count"] < 3:
            failures.append(f"{case['node_id']}: context chain did not expose upstream/current/downstream")
        if not case["context_return_visible"]:
            failures.append(f"{case['node_id']}: context return button not visible")
        if not case["node_flow_shell_visible"]:
            failures.append(f"{case['node_id']}: node flow shell not visible")
        if case.get("transition") != "enter":
            failures.append(f"{case['node_id']}: node open transition was not enter")
        if "node-enter-from-canvas" not in str(case.get("transition_animation")):
            failures.append(f"{case['node_id']}: node open animation missing")
        if not case["prompt_optimizer_visible"] and case["expected_kind"] not in {"director", "video_merge"}:
            failures.append(f"{case['node_id']}: prompt optimizer trigger not visible")
        prompt_generate = case["prompt_generate"]
        if not prompt_generate["skipped"]:
            if not prompt_generate.get("button_visible"):
                failures.append(f"{case['node_id']}: node generation button not visible")
            if not prompt_generate.get("status_visible"):
                failures.append(f"{case['node_id']}: node generation status not visible")
            if prompt_generate.get("after_status") != "complete":
                failures.append(f"{case['node_id']}: local node generation did not complete")
        node_control = case["node_control"]
        if not node_control["skipped"]:
            if node_control.get("control_count", 0) < 1:
                failures.append(f"{case['node_id']}: no node parameter controls found")
            if not node_control.get("clicked"):
                failures.append(f"{case['node_id']}: no inactive node parameter control was clickable")
            if not node_control.get("after_pressed"):
                failures.append(f"{case['node_id']}: node parameter control did not become active")
        context_navigation = case["context_navigation"]
        if not context_navigation["skipped"]:
            if not context_navigation.get("target_visible"):
                failures.append(f"{case['node_id']}: downstream context navigation chip not visible")
            if context_navigation.get("target_kind") != "script":
                failures.append(f"{case['node_id']}: downstream navigation target kind was not script")
            if context_navigation.get("after_context_id") != "storyboard":
                failures.append(f"{case['node_id']}: context navigation did not open storyboard")
            if context_navigation.get("after_transition") != "chain":
                failures.append(f"{case['node_id']}: context navigation did not use chain transition")
            if "node-chain-swap" not in str(context_navigation.get("after_transition_animation")):
                failures.append(f"{case['node_id']}: context navigation animation missing")
            if not context_navigation.get("target_panel_visible"):
                failures.append(f"{case['node_id']}: context navigation target panel not visible")
        if case.get("return_transition") != "return":
            failures.append(f"{case['node_id']}: return to canvas did not mark return transition")
        if "canvas-node-return" not in str(case.get("return_animation")):
            failures.append(f"{case['node_id']}: return animation missing")
        if not case["returned_to_canvas"]:
            failures.append(f"{case['node_id']}: return to canvas did not restore workflow node")
    if report["capture"]["viewport_overflow"]["x"]:
        failures.append("horizontal viewport overflow")
    if report["console_errors"]:
        failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]:
        failures.append(f"page errors: {report['page_errors']}")
    if report["provider_calls_started"]:
        failures.append(f"provider requests: {report['provider_request_urls']}")
    return failures


def _viewport_overflow(page: Any) -> dict[str, Any]:
    return page.evaluate("""() => ({ x: document.documentElement.scrollWidth > window.innerWidth + 4, scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth })""")


if __name__ == "__main__":
    raise SystemExit(main())
