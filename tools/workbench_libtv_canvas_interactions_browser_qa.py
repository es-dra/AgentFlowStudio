from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from workbench_libtv_browser_qa_common import assert_url_available, drag_node_to_safe_bottom, is_provider_request, workbench_url, write_stdout
DEFAULT_BASE_URL = "http://127.0.0.1:8790/workbench/"
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_canvas_interactions_browser_qa")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise LibTV-style canvas interactions in a real browser.")
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
                capture = _run_canvas_qa(page, base_url, screenshot_dir, provider_request_urls)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Canvas interactions QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Canvas interactions QA failed: {exc}") from exc
    report = {
        "artifact_type": "agentflow_workbench_libtv_canvas_interactions_browser_qa",
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
    report_path = output_dir / "workbench_libtv_canvas_interactions_browser_qa.json"
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized, encoding="utf-8")
    write_stdout(serialized)
    if failures:
        raise SystemExit(f"Canvas interactions QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _run_canvas_qa(page: Any, base_url: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator(".product-nav button", has_text="创作画布").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)
    stage = page.locator("[data-canvas-surface]").first
    layer = page.locator("[data-canvas-content]").first
    stage_box = stage.bounding_box()
    if not stage_box: raise AssertionError("Canvas stage has no bounding box")
    transform_before_pan = layer.evaluate("node => getComputedStyle(node).transform")
    page.mouse.move(stage_box["x"] + 680, stage_box["y"] + 500)
    page.mouse.down()
    page.mouse.move(stage_box["x"] + 680, stage_box["y"] + 720, steps=8)
    page.mouse.up()
    page.wait_for_timeout(120)
    transform_after_pan = layer.evaluate("node => getComputedStyle(node).transform")
    page.mouse.dblclick(stage_box["x"] + 560, stage_box["y"] + 760)
    page.locator(".canvas-anchored-add-menu").first.wait_for(state="visible", timeout=5_000)
    page.locator("[data-add-node-kind='text']").first.click()
    custom_node = page.locator("[data-node-id^='text-']").first
    custom_node.wait_for(state="visible", timeout=5_000)
    custom_id = custom_node.get_attribute("data-node-id")
    created_text = custom_node.inner_text(timeout=5_000)
    x_before_drag = custom_node.get_attribute("data-node-x")
    handle = custom_node.locator("[data-node-drag-handle]").first
    handle_box = handle.bounding_box()
    if not handle_box: raise AssertionError("Custom node drag handle has no bounding box")
    page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(handle_box["x"] + 210, handle_box["y"] + 120, steps=8)
    page.mouse.up()
    page.wait_for_timeout(160)
    custom_node = page.locator(f"[data-node-id='{custom_id}']").first
    x_after_drag = custom_node.get_attribute("data-node-x")
    bottom_safe_drag = drag_node_to_safe_bottom(page, custom_id, stage_box)
    source_output_port_visible = page.locator("[data-node-id='script-input'] .output-port[data-connect-from='script-input']").first.is_visible()
    target_input_port_visible = custom_node.locator(".input-port").first.is_visible()
    connector = page.locator("[data-connect-from='script-input']").first
    connector_box = connector.bounding_box()
    target_box = custom_node.bounding_box()
    if not connector_box or not target_box: raise AssertionError("Connection endpoints have no bounding boxes")
    page.mouse.move(connector_box["x"] + connector_box["width"] / 2, connector_box["y"] + connector_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2, steps=10)
    pending_visible_during_drag = page.locator(".studio-canvas-edge.pending").count() > 0
    pending_target_locked = page.locator(".studio-canvas-edge.pending.target-locked").count() > 0
    target_highlight_during_drag = custom_node.evaluate("node => node.classList.contains('canvas-connection-target')")
    page.mouse.up()
    page.wait_for_timeout(180)
    connected_edge_count = page.locator(f"[data-linked-node-id='script-input:{custom_id}']").count()
    success_ripple_count = page.locator(f".connection-success-ripple[data-linked-node-id='script-input:{custom_id}']").count()
    connected_edge_animation = page.locator(f"[data-linked-node-id='script-input:{custom_id}']").first.evaluate("node => getComputedStyle(node).animationName")
    edge_capture = _exercise_edge_toolbar(page, f"script-input:{custom_id}")
    page.mouse.move(stage_box["x"] + 50, stage_box["y"] + 900)
    page.mouse.down()
    page.wait_for_timeout(240)
    page.mouse.move(stage_box["x"] + 1420, stage_box["y"] + 300, steps=10)
    marquee_visible_during_drag = page.locator("[data-canvas-marquee]").count() > 0
    page.mouse.up()
    page.wait_for_timeout(160)
    selected_count = page.locator(".workflow-node.selected").count()
    group_drag_capture = _drag_selected_group(page)
    selection_toolbar_capture = _exercise_selection_toolbar(page)
    screenshot_path = screenshot_dir / "canvas-interactions.png"
    page.screenshot(path=screenshot_path, full_page=False)
    return {
        "transform_before_pan": transform_before_pan,
        "transform_after_pan": transform_after_pan,
        "custom_node_id": custom_id,
        "custom_node_text": created_text,
        "x_before_drag": x_before_drag,
        "x_after_drag": x_after_drag,
        "bottom_safe_drag": bottom_safe_drag,
        "source_output_port_visible": source_output_port_visible,
        "target_input_port_visible": target_input_port_visible,
        "pending_visible_during_drag": pending_visible_during_drag,
        "pending_target_locked": pending_target_locked,
        "target_highlight_during_drag": target_highlight_during_drag,
        "connected_edge_count": connected_edge_count,
        "success_ripple_count": success_ripple_count,
        "connected_edge_animation": connected_edge_animation,
        "edge_capture": edge_capture,
        "marquee_visible_during_drag": marquee_visible_during_drag,
        "selected_count_after_marquee": selected_count,
        "group_drag_capture": group_drag_capture,
        "selection_toolbar_capture": selection_toolbar_capture,
        "viewport_overflow": _viewport_overflow(page),
        "provider_calls_started": bool(provider_urls),
        "screenshot": screenshot_path.as_posix(),
    }


def _qa_failures(report: dict[str, Any]) -> list[str]:
    capture = report["capture"]
    failures: list[str] = []
    if capture["transform_before_pan"] == capture["transform_after_pan"]:
        failures.append("canvas pan did not change transform")
    if "文本" not in capture["custom_node_text"]:
        failures.append("double-click add menu did not create a text node")
    if capture["x_before_drag"] == capture["x_after_drag"]:
        failures.append("node drag did not persist a new x coordinate")
    bottom_safe = capture["bottom_safe_drag"]
    if not bottom_safe["selected_node_clear_of_dock"]:
        failures.append(f"selected node still intersects bottom dock after bottom drag: {bottom_safe}")
    for key, message in (
        ("source_output_port_visible", "source output port was not visible before connection"),
        ("target_input_port_visible", "target input port was not visible before connection"),
        ("pending_visible_during_drag", "pending Bezier edge was not visible during connection drag"),
        ("pending_target_locked", "pending Bezier edge did not lock to the target node"),
        ("target_highlight_during_drag", "target node did not show connection highlight during drag"),
        ("marquee_visible_during_drag", "long-press marquee was not visible"),
    ):
        if not capture[key]:
            failures.append(message)
    if capture["connected_edge_count"] < 1: failures.append("connection drag did not create a connected edge")
    if capture["success_ripple_count"] < 1: failures.append("connected edge did not expose success ripple state")
    if "edge-idle-flow" not in capture["connected_edge_animation"]:
        failures.append(f"connected edge did not keep directional flow animation: {capture['connected_edge_animation']}")
    edge_capture = capture["edge_capture"]
    for key, message in (
        ("toolbar_visible", f"edge toolbar was not visible: {edge_capture}"),
        ("edge_selected", f"edge did not enter selected styling: {edge_capture}"),
        ("disconnect_removed_edge", f"edge disconnect did not remove custom edge: {edge_capture}"),
    ):
        if not edge_capture[key]: failures.append(message)
    if capture["selected_count_after_marquee"] < 2:
        failures.append("marquee did not select multiple nodes")
    group_drag = capture["group_drag_capture"]
    if not group_drag["second_selected_node_moved"]:
        failures.append(f"group drag did not move another selected node: {group_drag}")
    toolbar = capture["selection_toolbar_capture"]
    for key, message in (
        ("toolbar_visible", "selection toolbar was not visible after multi-select"),
        ("frame_visible", "selection frame was not visible after multi-select"),
        ("align_row_applied", f"selection align-row did not align y coordinates: {toolbar}"),
        ("duplicate_increased_node_count", f"selection duplicate did not increase node count: {toolbar}"),
        ("delete_restored_node_count", f"selection delete did not remove duplicated custom nodes: {toolbar}"),
    ):
        if not toolbar[key]:
            failures.append(message)
    if capture["viewport_overflow"]["x"]:
        failures.append("horizontal viewport overflow")
    if report["console_errors"]: failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]: failures.append(f"page errors: {report['page_errors']}")
    if report["provider_calls_started"]: failures.append(f"provider requests: {report['provider_request_urls']}")
    return failures


def _viewport_overflow(page: Any) -> dict[str, Any]:
    return page.evaluate("""() => ({ x: document.documentElement.scrollWidth > window.innerWidth + 4, scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth })""")


def _drag_selected_group(page: Any) -> dict[str, Any]:
    selected = page.locator(".workflow-node.selected")
    if selected.count() < 2:
        return {"selected_count": selected.count(), "second_selected_node_moved": False}
    first_id = selected.nth(0).get_attribute("data-node-id")
    second_id = selected.nth(1).get_attribute("data-node-id")
    if not first_id or not second_id:
        return {"selected_count": selected.count(), "first_id": first_id, "second_id": second_id, "second_selected_node_moved": False}
    second = page.locator(f"[data-node-id='{second_id}']").first
    second_x_before = second.get_attribute("data-node-x")
    handle = page.locator(f"[data-node-id='{first_id}'] [data-node-drag-handle]").first
    handle_box = handle.bounding_box()
    if not handle_box:
        return {"selected_count": selected.count(), "first_id": first_id, "second_id": second_id, "second_selected_node_moved": False}
    page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(handle_box["x"] + 110, handle_box["y"] + 72, steps=8)
    page.mouse.up()
    page.wait_for_timeout(180)
    second_x_after = page.locator(f"[data-node-id='{second_id}']").first.get_attribute("data-node-x")
    return {
        "selected_count": selected.count(),
        "first_id": first_id,
        "second_id": second_id,
        "second_x_before": second_x_before,
        "second_x_after": second_x_after,
        "second_selected_node_moved": second_x_before != second_x_after,
    }


def _exercise_selection_toolbar(page: Any) -> dict[str, Any]:
    toolbar = page.locator(".canvas-selection-toolbar").first
    frame = page.locator(".canvas-selection-frame").first
    toolbar_visible = toolbar.count() > 0 and toolbar.is_visible()
    frame_visible = frame.count() > 0 and frame.is_visible()
    node_count_before = page.locator(".workflow-node").count()
    page.locator("[data-canvas-selection-action='align-row']").first.click()
    page.wait_for_timeout(160)
    selected_y = page.locator(".workflow-node.selected").evaluate_all("nodes => nodes.map(node => node.getAttribute('data-node-y'))")
    align_row_applied = len(set(selected_y)) == 1 if selected_y else False
    page.locator("[data-canvas-selection-action='duplicate']").first.click()
    page.wait_for_timeout(220)
    node_count_after_duplicate = page.locator(".workflow-node").count()
    page.locator("[data-canvas-selection-action='delete']").first.click()
    page.wait_for_timeout(220)
    node_count_after_delete = page.locator(".workflow-node").count()
    return {
        "toolbar_visible": toolbar_visible,
        "frame_visible": frame_visible,
        "node_count_before": node_count_before,
        "selected_y_after_align_row": selected_y,
        "align_row_applied": align_row_applied,
        "node_count_after_duplicate": node_count_after_duplicate,
        "duplicate_increased_node_count": node_count_after_duplicate > node_count_before,
        "node_count_after_delete": node_count_after_delete,
        "delete_restored_node_count": node_count_after_delete == node_count_before,
    }
def _exercise_edge_toolbar(page: Any, edge_key: str) -> dict[str, Any]:
    edge = page.locator(f"[data-linked-node-id='{edge_key}']").first
    edge.evaluate("node => node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))")
    page.wait_for_timeout(120)
    toolbar = page.locator(f"[data-selected-edge-key='{edge_key}']").first
    edge_selected = page.locator(f".edge-selected[data-linked-node-id='{edge_key}']").count() > 0
    toolbar_visible = toolbar.count() > 0 and toolbar.is_visible()
    page.locator("[data-canvas-edge-action='disconnect-edge']").first.click()
    page.wait_for_timeout(160)
    return {"toolbar_visible": toolbar_visible, "edge_selected": edge_selected, "disconnect_removed_edge": page.locator(f"[data-linked-node-id='{edge_key}']").count() == 0}


if __name__ == "__main__":
    raise SystemExit(main())
