from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8790/workbench/"
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_relation_focus_browser_qa")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")

def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise LibTV-style node relation focus in a real browser.")
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

    base_url = _workbench_url(args.base_url)
    _assert_url_available(base_url)
    output_dir = args.output_dir.resolve()
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_urls: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.on("request", lambda request: provider_urls.append(request.url) if _is_provider_request(request.url) else None)
                capture = _run_relation_focus_qa(page, base_url, screenshot_dir, provider_urls)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Relation focus QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Relation focus QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_relation_focus_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "capture": capture,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "provider_request_urls": provider_urls,
        "provider_calls_started": bool(provider_urls),
        "non_claims": ["not human acceptance", "not business validation", "not provider smoke"],
    }
    failures = _qa_failures(report)
    report["qa_status"] = "failed" if failures else "passed"
    report["failures"] = failures
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "workbench_libtv_relation_focus_browser_qa.json"
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized, encoding="utf-8")
    _write_stdout(serialized)
    if failures:
        raise SystemExit(f"Relation focus QA found {len(failures)} failure(s). See {report_path}")
    return 0

def _run_relation_focus_qa(page: Any, base_url: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator(".product-nav button", has_text="创作画布").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)
    _create_unrelated_custom_branch(page)
    page.locator("[data-node-id='keyframe']").first.click()
    page.wait_for_timeout(180)
    capture = {
        "selected_relation": page.locator("[data-node-id='keyframe']").first.get_attribute("data-relation-role"),
        "direct_upstream_count": page.locator(".workflow-node.relation-upstream.relation-direct").count(),
        "direct_downstream_count": page.locator(".workflow-node.relation-downstream.relation-direct").count(),
        "upstream_edge_count": page.locator(".studio-canvas-edge.edge-upstream.active").count(),
        "downstream_edge_count": page.locator(".studio-canvas-edge.edge-downstream.active").count(),
        "dimmed_node_count": page.locator(".workflow-node.is-dimmed").count(),
        "dimmed_edge_count": page.locator(".studio-canvas-edge.edge-dimmed").count(),
        "viewport_overflow": _viewport_overflow(page),
        "provider_calls_started": bool(provider_urls),
    }
    screenshot_path = screenshot_dir / "relation-focus-keyframe.png"
    page.screenshot(path=screenshot_path, full_page=False)
    capture["screenshot"] = screenshot_path.as_posix()
    return capture

def _create_unrelated_custom_branch(page: Any) -> None:
    stage = page.locator("[data-canvas-surface]").first
    stage_box = stage.bounding_box()
    if not stage_box:
        raise AssertionError("Canvas stage has no bounding box")
    page.mouse.dblclick(stage_box["x"] + 560, stage_box["y"] + 760)
    page.locator(".canvas-anchored-add-menu").first.wait_for(state="visible", timeout=5_000)
    page.locator("[data-add-node-kind='text']").first.click()
    custom_node = page.locator("[data-node-id^='text-']").first
    custom_node.wait_for(state="visible", timeout=5_000)
    connector = page.locator("[data-connect-from='script-input']").first
    connector_box = connector.bounding_box()
    target_box = custom_node.bounding_box()
    if not connector_box or not target_box:
        raise AssertionError("Connection endpoints have no bounding boxes")
    page.mouse.move(connector_box["x"] + connector_box["width"] / 2, connector_box["y"] + connector_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2, steps=10)
    page.mouse.up()
    page.wait_for_timeout(180)

def _qa_failures(report: dict[str, Any]) -> list[str]:
    capture = report["capture"]
    failures: list[str] = []
    if capture["selected_relation"] != "selected":
        failures.append(f"selected node relation role mismatch: {capture['selected_relation']}")
    for key in ["direct_upstream_count", "direct_downstream_count", "upstream_edge_count", "downstream_edge_count", "dimmed_node_count", "dimmed_edge_count"]:
        if capture[key] < 1:
            failures.append(f"{key} was not visible")
    if capture["viewport_overflow"]["x"]:
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

def _workbench_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.path.rstrip("/").endswith("/workbench"):
        return raw_url if raw_url.endswith("/") else f"{raw_url}/"
    return urllib.parse.urljoin(raw_url.rstrip("/") + "/", "workbench/")

def _assert_url_available(url: str) -> None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status >= 400:
                raise SystemExit(f"Workbench URL returned HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Workbench URL is not available: {url}. Start the Runtime Service first.") from exc

def _is_provider_request(url: str) -> bool:
    lowered = url.lower()
    return any(pattern in lowered for pattern in PROVIDER_REQUEST_PATTERNS)

def _write_stdout(value: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(value)

if __name__ == "__main__":
    raise SystemExit(main())
