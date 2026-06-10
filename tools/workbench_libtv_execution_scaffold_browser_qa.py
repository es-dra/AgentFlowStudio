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
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_execution_scaffold_browser_qa")
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000, "device_scale_factor": 1, "is_mobile": False},
    "tablet": {"width": 820, "height": 1180, "device_scale_factor": 1, "is_mobile": False},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 2, "is_mobile": True},
}
REQUIRED_LABELS = (
    "节点连接",
    "参数抽屉",
    "待执行动作",
    "生成预检",
    "登记执行意图",
    "等待能力授权",
    "只登记本地执行意图，不启动真实生成。",
)
FORBIDDEN_PATTERNS = (
    "api_key",
    "signed_url",
    "provider_config",
    "AFS_ALLOW_REMOTE",
    "OPENAI_API_KEY",
    r"[A-Z]:\\",
)
PROVIDER_REQUEST_PATTERNS = (
    "api.openai.com",
    "replicate.com",
    "fal.ai",
    "stability.ai",
    "/provider",
    "/generate",
)
INTENT_SELECTORS = {
    "preflight": "[data-execution-intent='preflight']",
    "register": "[data-execution-intent='register']",
    "wait_gate": "[data-execution-intent='wait_gate']",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture LibTV execution scaffold evidence in a real browser.")
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
        raise SystemExit(
            "Playwright is required. Install with: "
            f"{sys.executable} -m pip install playwright && {sys.executable} -m playwright install chromium"
        ) from exc

    base_url = _workbench_url(args.base_url)
    _assert_url_available(base_url)
    output_dir = args.output_dir.resolve()
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_request_urls: list[str] = []
    viewports = _selected_viewports(args.viewport)
    captures: list[dict[str, Any]] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                for viewport_id in viewports:
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
                        captures.append(_capture_viewport(page, base_url, viewport_id, viewport, screenshot_dir, provider_request_urls))
                    finally:
                        page.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"LibTV execution scaffold QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"LibTV execution scaffold QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_execution_scaffold_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "viewports": {viewport_id: VIEWPORTS[viewport_id] for viewport_id in viewports},
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
    report_path = output_dir / "workbench_libtv_execution_scaffold_browser_qa.json"
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized_report, encoding="utf-8")
    _write_stdout(serialized_report)
    if failures:
        raise SystemExit(f"LibTV execution scaffold QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _capture_viewport(page: Any, base_url: str, viewport_id: str, viewport: dict[str, Any], screenshot_dir: Path, provider_request_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".app-shell").first.wait_for(state="visible", timeout=15_000)
    create_entry = page.locator("[data-view='Create']:visible").first
    create_entry.wait_for(state="visible", timeout=20_000)
    create_entry.click()
    scaffold = page.locator(".libtv-execution-scaffold").first
    scaffold.wait_for(state="visible", timeout=15_000)
    parameter_drawer = page.locator(".libtv-parameter-drawer").first
    action_queue = page.locator(".libtv-action-queue").first
    parameter_drawer.wait_for(state="visible", timeout=10_000)
    action_queue.wait_for(state="visible", timeout=10_000)
    scaffold.scroll_into_view_if_needed()
    page.wait_for_timeout(150)

    viewport_dir = screenshot_dir / viewport_id
    viewport_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = viewport_dir / "execution-scaffold.png"
    scaffold.screenshot(path=screenshot_path)
    body_text = page.locator("body").inner_text(timeout=10_000)
    required_labels_missing = [label for label in REQUIRED_LABELS if label not in body_text]
    action_count = page.locator("[data-execution-intent]").count()
    edge_count = page.locator(".libtv-canvas-edge").count()
    parameter_count = page.locator(".libtv-parameter-grid article").count()
    intent_clicks = _click_intents(page, viewport_dir, provider_request_urls)
    viewport_overflow = page.evaluate(
        """() => ({
            x: document.documentElement.scrollWidth > window.innerWidth + 4,
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth
        })"""
    )
    return {
        "viewport_id": viewport_id,
        "viewport": viewport,
        "screenshot": screenshot_path.as_posix(),
        "scaffold_visible": scaffold.is_visible(),
        "parameter_drawer_visible": parameter_drawer.is_visible(),
        "action_queue_visible": action_queue.is_visible(),
        "required_labels_missing": required_labels_missing,
        "action_count": action_count,
        "edge_count": edge_count,
        "parameter_count": parameter_count,
        "intent_clicks": intent_clicks,
        "forbidden_matches": _visible_forbidden_matches(body_text),
        "provider_calls_started": bool(provider_request_urls),
        "viewport_overflow": viewport_overflow,
    }


def _click_intents(page: Any, viewport_dir: Path, provider_request_urls: list[str]) -> list[dict[str, Any]]:
    clicks: list[dict[str, Any]] = []
    for intent, selector in INTENT_SELECTORS.items():
        button = page.locator(selector).first
        button.click()
        page.wait_for_timeout(100)
        status = page.locator(".libtv-execution-status").first
        active_button = page.locator(f"{selector}.active").first
        status.wait_for(state="visible", timeout=5_000)
        screenshot_path = viewport_dir / f"execution-intent-{intent}.png"
        status.screenshot(path=screenshot_path)
        clicks.append({
            "intent": intent,
            "selector": selector,
            "active_button_visible": active_button.is_visible(),
            "receipt_text": status.inner_text(timeout=5_000),
            "screenshot": screenshot_path.as_posix(),
            "provider_calls_started": bool(provider_request_urls),
        })
    return clicks


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for capture in report["captures"]:
        viewport_id = capture["viewport_id"]
        if not capture["scaffold_visible"]:
            failures.append(f"{viewport_id}: scaffold not visible")
        if capture["required_labels_missing"]:
            failures.append(f"{viewport_id}: missing labels {capture['required_labels_missing']}")
        if capture["action_count"] < 3:
            failures.append(f"{viewport_id}: expected at least 3 execution actions")
        if capture["edge_count"] < 1:
            failures.append(f"{viewport_id}: expected at least 1 edge row")
        if capture["parameter_count"] < 6:
            failures.append(f"{viewport_id}: expected at least 6 parameter rows")
        for click in capture["intent_clicks"]:
            missing = [
                label for label in ("本地意图已登记", "未创建真实任务", "未启动 provider")
                if label not in click["receipt_text"]
            ]
            if not click["active_button_visible"]:
                failures.append(f"{viewport_id}: intent {click['intent']} active button not visible")
            if missing:
                failures.append(f"{viewport_id}: intent {click['intent']} missing receipt labels {missing}")
            if click["provider_calls_started"]:
                failures.append(f"{viewport_id}: intent {click['intent']} started provider request")
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


def _visible_forbidden_matches(body_text: str) -> list[str]:
    matches: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, body_text, flags=re.IGNORECASE):
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


def _selected_viewports(raw: list[str] | None) -> list[str]:
    if not raw or "all" in raw:
        return list(VIEWPORTS)
    return raw


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
