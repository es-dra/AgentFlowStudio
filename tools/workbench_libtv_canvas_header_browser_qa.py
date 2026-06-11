from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8790/workbench/"
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_canvas_header_browser_qa")
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000, "device_scale_factor": 1, "is_mobile": False},
    "tablet": {"width": 820, "height": 1180, "device_scale_factor": 1, "is_mobile": False},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 2, "is_mobile": True},
}
TITLE_SELECTOR = "[data-studio-title-input]"
MENU_SELECTOR = "[data-studio-canvas-menu]"
CANVAS_2_SELECTOR = "[data-studio-canvas-id='canvas-2']"
NEW_CANVAS_SELECTOR = "[data-studio-canvas-action='new_canvas']"
INITIAL_SELECTORS = (
    ".libtv-shell",
    ".product-nav",
    ".product-nav button:has-text('创作画布')",
)
CANVAS_SELECTORS = (
    ".libtv-canvas.canvas-product-v3",
    ".canvas-topbar",
    "data-studio-title-input",
    "data-studio-canvas-menu",
)
MENU_SELECTORS = (
    "data-studio-canvas-id='canvas-2'",
    "data-studio-canvas-action='new_canvas'",
)
FORBIDDEN_PATTERNS = (
    "Provider",
    "Runtime",
    "CommandHub",
    "Gate",
    "api_key",
    "signed_url",
    "provider_config",
    "AFS_ALLOW_REMOTE",
    "OPENAI_API_KEY",
    r"[A-Z]:\\",
)
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture LibTV-style canvas header evidence in a real browser.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Workbench URL. Defaults to the local Runtime Service.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for manifest and screenshots.")
    parser.add_argument("--viewport", action="append", choices=["all", *VIEWPORTS.keys()], help="Viewport to capture. Defaults to all.")
    parser.add_argument("--headed", action="store_true", help="Show the browser window.")
    args = parser.parse_args()

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"Playwright is required. Install with: {sys.executable} -m pip install playwright") from exc

    base_url = _workbench_url(args.base_url)
    _assert_url_available(base_url)
    output_dir = args.output_dir
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    viewport_ids = _selected_viewports(args.viewport)
    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_request_urls: list[str] = []
    captures: list[dict[str, Any]] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                for viewport_id in viewport_ids:
                    page = browser.new_page(
                        viewport={"width": VIEWPORTS[viewport_id]["width"], "height": VIEWPORTS[viewport_id]["height"]},
                        device_scale_factor=VIEWPORTS[viewport_id]["device_scale_factor"],
                        is_mobile=VIEWPORTS[viewport_id]["is_mobile"],
                    )
                    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                    page.on("request", lambda request: provider_request_urls.append(request.url) if _is_provider_request(request.url) else None)
                    try:
                        captures.append(_capture_header(page, base_url, viewport_id, screenshot_dir, provider_request_urls))
                    finally:
                        page.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"LibTV canvas header browser QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"LibTV canvas header browser QA failed: {exc}") from exc

    report = _report(base_url, viewport_ids, captures, console_errors, page_errors, provider_request_urls)
    failures = _qa_failures(report)
    report["qa_status"] = "failed" if failures else "passed"
    report["failures"] = failures
    report_path = output_dir / "workbench_libtv_canvas_header_browser_qa.json"
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized_report, encoding="utf-8")
    _write_stdout(serialized_report)
    if failures:
        raise SystemExit(f"LibTV canvas header browser QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _capture_header(page: Any, base_url: str, viewport_id: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    initial_missing = _missing_selectors(page, INITIAL_SELECTORS)
    page.locator(".product-nav button", has_text="创作画布").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)
    canvas_missing = _missing_selectors(page, CANVAS_SELECTORS)
    page.locator(TITLE_SELECTOR).first.fill("AFS 联合验收画布")
    title_value_after_input = page.locator(TITLE_SELECTOR).first.input_value(timeout=5_000)
    page.locator(MENU_SELECTOR).first.click()
    page.locator(".libtv-canvas-menu").first.wait_for(state="visible", timeout=5_000)
    canvas_menu_visible = page.locator(".libtv-canvas-menu").first.is_visible()
    menu_missing = _missing_selectors(page, MENU_SELECTORS)
    canvas_select_clicks = [
        _click_canvas_control(page, CANVAS_2_SELECTOR, "canvas-2", provider_urls),
        _click_canvas_control(page, NEW_CANVAS_SELECTOR, "new_canvas", provider_urls),
    ]
    viewport_dir = screenshot_dir / viewport_id
    viewport_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = viewport_dir / "canvas-header.png"
    page.screenshot(path=screenshot_path, full_page=False)
    body_text = page.locator("body").inner_text(timeout=10_000)
    return {
        "viewport_id": viewport_id,
        "viewport": VIEWPORTS[viewport_id],
        "title_value_after_input": title_value_after_input,
        "canvas_menu_visible": canvas_menu_visible,
        "canvas_select_clicks": canvas_select_clicks,
        "receipt_text": _receipt_text(page),
        "missing_selectors": initial_missing + canvas_missing + menu_missing,
        "forbidden_matches": _forbidden_matches(body_text),
        "provider_calls_started": bool(provider_urls),
        "viewport_overflow": _viewport_overflow(page),
        "screenshot": screenshot_path.as_posix(),
    }


def _click_canvas_control(page: Any, selector: str, action: str, provider_urls: list[str]) -> dict[str, Any]:
    if page.locator(".libtv-canvas-menu").count() == 0 or not page.locator(".libtv-canvas-menu").first.is_visible():
        page.locator(MENU_SELECTOR).first.click()
        page.locator(".libtv-canvas-menu").first.wait_for(state="visible", timeout=5_000)
    page.locator(selector).first.click()
    page.locator(".libtv-canvas-intent-status").first.wait_for(state="visible", timeout=5_000)
    return {
        "action": action,
        "selector": selector,
        "receipt_text": _receipt_text(page),
        "provider_calls_started": bool(provider_urls),
    }


def _report(base_url: str, viewport_ids: list[str], captures: list[dict[str, Any]], console_errors: list[str], page_errors: list[str], provider_urls: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_workbench_libtv_canvas_header_browser_qa",
        "schema_version": "0.3.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "viewports": {viewport_id: VIEWPORTS[viewport_id] for viewport_id in viewport_ids},
        "captures": captures,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "provider_request_urls": provider_urls,
        "provider_calls_started": bool(provider_urls),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not human acceptance", "not business validation", "not provider smoke"],
    }


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for capture in report["captures"]:
        viewport_id = capture["viewport_id"]
        if capture["title_value_after_input"] != "AFS 联合验收画布":
            failures.append(f"{viewport_id}: title input did not persist")
        if not capture["canvas_menu_visible"]:
            failures.append(f"{viewport_id}: canvas menu did not open")
        if any(click["provider_calls_started"] for click in capture["canvas_select_clicks"]):
            failures.append(f"{viewport_id}: canvas action started provider request")
        if capture["missing_selectors"]:
            failures.append(f"{viewport_id}: missing selectors {capture['missing_selectors']}")
        if capture["forbidden_matches"]:
            failures.append(f"{viewport_id}: forbidden visible text {capture['forbidden_matches']}")
        if capture["provider_calls_started"]:
            failures.append(f"{viewport_id}: provider request started")
        if capture["viewport_overflow"]["x"]:
            failures.append(f"{viewport_id}: horizontal viewport overflow")
    if report["console_errors"]:
        failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]:
        failures.append(f"page errors: {report['page_errors']}")
    if report["provider_calls_started"]:
        failures.append(f"provider requests: {report['provider_request_urls']}")
    return failures


def _missing_selectors(page: Any, selectors: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for selector in selectors:
        locator_selector = f"[{selector}]" if selector.startswith("data-") else selector
        if page.locator(locator_selector).count() == 0:
            missing.append(selector)
    return missing


def _receipt_text(page: Any) -> str:
    if page.locator(".libtv-canvas-intent-status").count() == 0:
        return ""
    return page.locator(".libtv-canvas-intent-status").first.inner_text(timeout=5_000)


def _viewport_overflow(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => ({
            x: document.documentElement.scrollWidth > window.innerWidth + 4,
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth
        })"""
    )


def _forbidden_matches(text: str) -> list[str]:
    matches = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, text, flags=re.IGNORECASE)]
    return sorted(set(matches))


def _is_provider_request(url: str) -> bool:
    lowered = url.lower()
    return any(pattern in lowered for pattern in PROVIDER_REQUEST_PATTERNS)


def _workbench_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.path.rstrip("/").endswith("/workbench"):
        return raw_url if raw_url.endswith("/") else f"{raw_url}/"
    return urllib.parse.urljoin(raw_url.rstrip("/") + "/", "workbench/")


def _assert_url_available(url: str) -> None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local QA URL.
            if response.status >= 400:
                raise SystemExit(f"Workbench URL returned HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Workbench URL is not available: {url}. Start the Runtime Service first.") from exc


def _selected_viewports(raw: list[str] | None) -> list[str]:
    if not raw or "all" in raw:
        return list(VIEWPORTS)
    return raw


def _write_stdout(value: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(value)


if __name__ == "__main__":
    raise SystemExit(main())
