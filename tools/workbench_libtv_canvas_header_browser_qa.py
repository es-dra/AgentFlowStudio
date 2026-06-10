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
PROJECT_TITLE_LABEL = "项目名称"
REQUIRED_LABELS = ("画布 1", "画布 2", "新建画布")
FORBIDDEN_PATTERNS = ("api_key", "signed_url", "provider_config", "AFS_ALLOW_REMOTE", "OPENAI_API_KEY", r"[A-Z]:\\")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")
TITLE_SELECTOR = "[data-studio-title-input]"
MENU_SELECTOR = "[data-studio-canvas-menu]"
CANVAS_SELECTORS = {
    "canvas_2": "[data-studio-canvas-id='canvas-2']",
    "new_canvas": "[data-studio-canvas-action='new_canvas']",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture LibTV canvas header evidence in a real browser.")
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
    output_dir = args.output_dir.resolve()
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
                    viewport = VIEWPORTS[viewport_id]
                    page = browser.new_page(
                        viewport={"width": viewport["width"], "height": viewport["height"]},
                        device_scale_factor=viewport["device_scale_factor"],
                        is_mobile=viewport["is_mobile"],
                    )
                    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                    page.on("request", lambda request: provider_request_urls.append(request.url) if _is_provider_request(request.url) else None)
                    try:
                        captures.append(_capture_header(page, base_url, viewport_id, viewport, screenshot_dir, provider_request_urls))
                    finally:
                        page.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"LibTV canvas header browser QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"LibTV canvas header browser QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_canvas_header_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "viewports": {viewport_id: VIEWPORTS[viewport_id] for viewport_id in viewport_ids},
        "captures": captures,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "provider_request_urls": provider_request_urls,
        "provider_calls_started": bool(provider_request_urls),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not human acceptance", "not business validation", "not provider smoke"],
    }
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


def _capture_header(page: Any, base_url: str, viewport_id: str, viewport: dict[str, Any], screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".app-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator("[data-view='Create']:visible").first.click()
    page.locator(".libtv-topbar").first.wait_for(state="visible", timeout=15_000)
    title = page.locator(TITLE_SELECTOR).first
    title.fill("本地画布验收", timeout=5_000)
    page.locator(MENU_SELECTOR).first.click()
    page.locator(".libtv-canvas-menu").first.wait_for(state="visible", timeout=5_000)
    menu_visible = page.locator(".libtv-canvas-menu").first.is_visible()
    body_text = page.locator("body").inner_text(timeout=10_000)

    viewport_dir = screenshot_dir / viewport_id
    viewport_dir.mkdir(parents=True, exist_ok=True)
    menu_screenshot = viewport_dir / "canvas-menu.png"
    page.locator(".libtv-canvas-menu").first.screenshot(path=menu_screenshot)
    clicks = _click_canvas_selectors(page, viewport_dir, provider_urls)
    return {
        "viewport_id": viewport_id,
        "viewport": viewport,
        "title_value_after_input": title.input_value(timeout=5_000),
        "title_aria_label": title.get_attribute("aria-label", timeout=5_000),
        "canvas_menu_visible": menu_visible,
        "required_labels_missing": [label for label in REQUIRED_LABELS if label not in body_text],
        "canvas_select_clicks": clicks,
        "forbidden_matches": _forbidden_matches(body_text),
        "provider_calls_started": bool(provider_urls),
        "viewport_overflow": _viewport_overflow(page),
        "screenshot": menu_screenshot.as_posix(),
    }


def _click_canvas_selectors(page: Any, screenshot_dir: Path, provider_urls: list[str]) -> list[dict[str, Any]]:
    clicks: list[dict[str, Any]] = []
    for intent, selector in CANVAS_SELECTORS.items():
        if page.locator(".libtv-canvas-menu").count() == 0:
            page.locator(MENU_SELECTOR).first.click()
            page.locator(".libtv-canvas-menu").first.wait_for(state="visible", timeout=5_000)
        page.locator(selector).first.click()
        page.wait_for_timeout(100)
        status = page.locator(".libtv-canvas-intent-status").first
        status.wait_for(state="visible", timeout=5_000)
        screenshot_path = screenshot_dir / f"canvas-header-{intent}.png"
        status.screenshot(path=screenshot_path)
        clicks.append({
            "intent": intent,
            "selector": selector,
            "receipt_text": status.inner_text(timeout=5_000),
            "screenshot": screenshot_path.as_posix(),
            "provider_calls_started": bool(provider_urls),
        })
    return clicks


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for capture in report["captures"]:
        viewport_id = capture["viewport_id"]
        if capture["title_value_after_input"] != "本地画布验收":
            failures.append(f"{viewport_id}: title input did not retain local value")
        if capture["title_aria_label"] != PROJECT_TITLE_LABEL:
            failures.append(f"{viewport_id}: title input aria label is not 项目名称")
        if not capture["canvas_menu_visible"]:
            failures.append(f"{viewport_id}: canvas menu was not visible")
        if capture["required_labels_missing"]:
            failures.append(f"{viewport_id}: missing labels {capture['required_labels_missing']}")
        for click in capture["canvas_select_clicks"]:
            missing = [label for label in ("本地画布意图已登记", "未创建真实画布", "未启动 provider") if label not in click["receipt_text"]]
            if missing:
                failures.append(f"{viewport_id}: {click['intent']} missing receipt labels {missing}")
            if click["provider_calls_started"]:
                failures.append(f"{viewport_id}: {click['intent']} started provider request")
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


def _viewport_overflow(page: Any) -> dict[str, Any]:
    return page.evaluate("""() => ({ x: document.documentElement.scrollWidth > window.innerWidth + 4, scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth })""")


def _forbidden_matches(text: str) -> list[str]:
    matches: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(pattern)
    return sorted(set(matches))


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


def _is_provider_request(url: str) -> bool:
    lowered = url.lower()
    return any(pattern in lowered for pattern in PROVIDER_REQUEST_PATTERNS)


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
