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
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_canvas_viewport_browser_qa")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise LibTV-style canvas viewport controls in a real browser.")
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
    provider_request_urls: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                page.on("request", lambda request: provider_request_urls.append(request.url) if _is_provider_request(request.url) else None)
                capture = _run_viewport_qa(page, base_url, screenshot_dir, provider_request_urls)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Canvas viewport QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Canvas viewport QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_canvas_viewport_browser_qa",
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
    report_path = output_dir / "workbench_libtv_canvas_viewport_browser_qa.json"
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized, encoding="utf-8")
    _write_stdout(serialized)
    if failures:
        raise SystemExit(f"Canvas viewport QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _run_viewport_qa(page: Any, base_url: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator("[data-view='Create']").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)
    layer = page.locator("[data-canvas-content]").first
    stage = page.locator("[data-canvas-surface]").first
    stage_box = stage.bounding_box()
    if not stage_box:
        raise AssertionError("Canvas stage has no bounding box")

    page.locator("[data-studio-tool='map']").first.click()
    page.locator(".canvas-navigator-panel").first.wait_for(state="visible", timeout=5_000)
    mini_map_visible = page.locator(".canvas-mini-map").first.is_visible()
    mini_node_count = page.locator(".canvas-mini-node").count()
    mini_viewport_visible = page.locator(".canvas-mini-viewport").first.is_visible()
    transform_before_fit = layer.evaluate("node => getComputedStyle(node).transform")
    page.locator("[data-canvas-action='fit-view']").first.click()
    page.wait_for_timeout(180)
    transform_after_fit = layer.evaluate("node => getComputedStyle(node).transform")

    page.mouse.move(stage_box["x"] + 720, stage_box["y"] + 500)
    page.mouse.down()
    page.mouse.move(stage_box["x"] + 1040, stage_box["y"] + 760, steps=8)
    page.mouse.up()
    page.wait_for_timeout(120)
    page.locator("[data-canvas-action='center-selection']").first.click()
    page.wait_for_timeout(180)
    selected_box = page.locator(".workflow-node.selected").first.bounding_box()
    selected_node_centered = _is_centered(selected_box)
    page.locator("[data-canvas-action='zoom-reset']").first.click()
    page.wait_for_timeout(120)
    transform_after_reset = layer.evaluate("node => getComputedStyle(node).transform")

    screenshot_path = screenshot_dir / "canvas-viewport.png"
    page.screenshot(path=screenshot_path, full_page=False)
    return {
        "mini_map_visible": mini_map_visible,
        "mini_node_count": mini_node_count,
        "mini_viewport_visible": mini_viewport_visible,
        "transform_before_fit": transform_before_fit,
        "transform_after_fit": transform_after_fit,
        "transform_after_reset": transform_after_reset,
        "selected_node_centered": selected_node_centered,
        "viewport_overflow": _viewport_overflow(page),
        "provider_calls_started": bool(provider_urls),
        "screenshot": screenshot_path.as_posix(),
    }


def _qa_failures(report: dict[str, Any]) -> list[str]:
    capture = report["capture"]
    failures: list[str] = []
    if not capture["mini_map_visible"]:
        failures.append("canvas navigator panel did not show mini map")
    if capture["mini_node_count"] < 4:
        failures.append(f"mini map did not render enough node marks: {capture['mini_node_count']}")
    if not capture["mini_viewport_visible"]:
        failures.append("mini map did not render viewport rectangle")
    if capture["transform_before_fit"] == capture["transform_after_fit"]:
        failures.append("fit-view did not change canvas transform")
    if not capture["selected_node_centered"]:
        failures.append("center-selection did not bring selected node near viewport center")
    if capture["viewport_overflow"]["x"]:
        failures.append("horizontal viewport overflow")
    if report["console_errors"]:
        failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]:
        failures.append(f"page errors: {report['page_errors']}")
    if report["provider_calls_started"]:
        failures.append(f"provider requests: {report['provider_request_urls']}")
    return failures


def _is_centered(box: dict[str, float] | None) -> bool:
    if not box:
        return False
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    return abs(center_x - 720) < 180 and abs(center_y - 470) < 180


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
