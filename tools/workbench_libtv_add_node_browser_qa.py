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
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_add_node_state_browser_qa")
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000, "device_scale_factor": 1, "is_mobile": False},
    "tablet": {"width": 820, "height": 1180, "device_scale_factor": 1, "is_mobile": False},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 2, "is_mobile": True},
}
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
STATE_CASES = [
    {"case_id": "node_text", "group": "node", "kind": "text", "expected_selector": ".libtv-text-node-flow"},
    {"case_id": "node_image", "group": "node", "kind": "image", "expected_selector": ".libtv-image-node-flow"},
    {"case_id": "node_video", "group": "node", "kind": "video", "expected_selector": ".libtv-video-node-flow"},
    {"case_id": "node_audio", "group": "node", "kind": "audio", "expected_selector": ".libtv-audio-node-flow"},
    {"case_id": "node_script", "group": "node", "kind": "script", "expected_selector": ".libtv-script-generator-flow"},
    {"case_id": "node_director", "group": "node", "kind": "director", "expected_selector": ".libtv-director-flow"},
    {"case_id": "node_video_merge", "group": "node", "kind": "video_merge", "expected_selector": ".libtv-video-merge-flow"},
    {"case_id": "resource_upload", "group": "resource", "kind": "upload", "expected_selector": ".libtv-upload-dropzone"},
    {"case_id": "resource_history", "group": "resource", "kind": "history", "expected_selector": ".libtv-history-resource-picker"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture LibTV add-node/resource state evidence in a real browser.")
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
    viewport_ids = _selected_viewports(args.viewport)

    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_request_urls: list[str] = []
    cases: list[dict[str, Any]] = []

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
                        _open_workbench(page, base_url)
                        viewport_dir = screenshot_dir / viewport_id
                        viewport_dir.mkdir(parents=True, exist_ok=True)
                        for item in STATE_CASES:
                            cases.append(_capture_case(page, item, viewport_id, viewport, viewport_dir, console_errors, page_errors, provider_request_urls))
                    finally:
                        page.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"LibTV browser QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"LibTV browser QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_add_node_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "viewports": {viewport_id: VIEWPORTS[viewport_id] for viewport_id in viewport_ids},
        "cases": cases,
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
    report_path = output_dir / "workbench_libtv_add_node_browser_qa.json"
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized_report, encoding="utf-8")
    _write_stdout(serialized_report)
    if failures:
        raise SystemExit(f"LibTV browser QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _open_workbench(page: Any, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".app-shell").first.wait_for(state="visible", timeout=15_000)
    create_entry = page.locator("[data-view='Create']:visible").first
    create_entry.wait_for(state="visible", timeout=20_000)
    create_entry.click()
    page.locator(".studio-workspace").first.wait_for(state="visible", timeout=15_000)


def _capture_case(
    page: Any,
    item: dict[str, str],
    viewport_id: str,
    viewport: dict[str, Any],
    screenshot_dir: Path,
    console_errors: list[str],
    page_errors: list[str],
    provider_request_urls: list[str],
) -> dict[str, Any]:
    _open_add_menu(page)
    if item["group"] == "node":
        page.locator(f"button[data-add-node-kind='{item['kind']}']").first.click()
    else:
        page.locator(f"button[data-add-resource-kind='{item['kind']}']").first.click()
    expected = page.locator(item["expected_selector"]).first
    expected.wait_for(state="visible", timeout=10_000)
    page.wait_for_timeout(150)

    screenshot_path = screenshot_dir / f"{item['case_id']}.png"
    page.screenshot(path=screenshot_path, full_page=True)
    forbidden_matches = _visible_forbidden_matches(page)
    overflow_nodes = _overflow_nodes(page)
    viewport_overflow = page.evaluate(
        """() => ({
            x: document.documentElement.scrollWidth > window.innerWidth + 4,
            y: document.documentElement.scrollHeight > window.innerHeight + 4,
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight
        })"""
    )
    return {
        **item,
        "viewport_id": viewport_id,
        "viewport": viewport,
        "expected_visible": expected.is_visible(),
        "screenshot": screenshot_path.as_posix(),
        "console_errors": list(console_errors),
        "page_errors": list(page_errors),
        "forbidden_matches": forbidden_matches,
        "provider_calls_started": bool(provider_request_urls),
        "overflow_nodes": overflow_nodes,
        "overflow_node_count": len(overflow_nodes),
        "viewport_overflow": viewport_overflow,
    }


def _open_add_menu(page: Any) -> None:
    menu = page.locator(".libtv-add-menu").first
    if not menu.count() or not menu.is_visible():
        page.locator("[data-studio-tool='add']").first.click()
    page.locator(".libtv-add-menu").first.wait_for(state="visible", timeout=10_000)


def _visible_forbidden_matches(page: Any) -> list[str]:
    body_text = page.locator("body").inner_text(timeout=10_000)
    matches: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, body_text, flags=re.IGNORECASE):
            matches.append(pattern)
    return sorted(set(matches))


def _overflow_nodes(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('body *')).filter((node) => {
            const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const rect = node.getBoundingClientRect();
            if (rect.width < 2 || rect.height < 2) return false;
            const text = (node.innerText || node.textContent || '').trim();
            if (!text) return false;
            return node.scrollWidth > node.clientWidth + 2 || node.scrollHeight > node.clientHeight + 2;
        }).slice(0, 20).map((node) => ({
            tag: node.tagName.toLowerCase(),
            className: String(node.className || ''),
            text: String((node.innerText || node.textContent || '').trim()).slice(0, 120),
            clientWidth: node.clientWidth,
            scrollWidth: node.scrollWidth,
            clientHeight: node.clientHeight,
            scrollHeight: node.scrollHeight
        }))"""
    )


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for case in report["cases"]:
        if not case["expected_visible"]:
            failures.append(f"{case['case_id']}: expected selector not visible")
        if case["forbidden_matches"]:
            failures.append(f"{case['case_id']}: forbidden visible text {case['forbidden_matches']}")
        if case["provider_calls_started"]:
            failures.append(f"{case['case_id']}: provider request started")
    if report["console_errors"]:
        failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]:
        failures.append(f"page errors: {report['page_errors']}")
    if report["provider_calls_started"]:
        failures.append(f"provider requests: {report['provider_request_urls']}")
    return failures


def _workbench_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.path.rstrip("/").endswith("/workbench"):
        return raw_url if raw_url.endswith("/") else f"{raw_url}/"
    return urllib.parse.urljoin(raw_url.rstrip("/") + "/", "workbench/")


def _assert_url_available(url: str) -> None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local QA URL.
            if response.status >= 400:
                raise RuntimeError(f"{url} returned HTTP {response.status}")
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(f"Workbench URL is not available: {url} ({exc})") from exc


def _is_provider_request(url: str) -> bool:
    return any(pattern in url for pattern in PROVIDER_REQUEST_PATTERNS)


def _selected_viewports(raw_values: list[str] | None) -> list[str]:
    if not raw_values or "all" in raw_values:
        return list(VIEWPORTS.keys())
    return list(dict.fromkeys(raw_values))


def _write_stdout(text: str) -> None:
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    raise SystemExit(main())
