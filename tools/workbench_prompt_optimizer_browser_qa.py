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
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_prompt_optimizer_browser_qa")
PROJECT_ID = "proj_runtime_demo"
OPTIMIZE_BUTTON_SELECTOR = "[data-action='optimize-current-prompt']"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000, "device_scale_factor": 1, "is_mobile": False},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 2, "is_mobile": True},
}
REQUIRED_LABELS = ("提示词优化", "已按影视结构优化", "已结合当前项目风格", "专业提示词")
FORBIDDEN_PATTERNS = ("api_key", "signed_url", "provider_config", "AFS_ALLOW_REMOTE", r"[A-Z]:\\")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture prompt optimizer evidence in a real browser.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Workbench URL. Defaults to the local service.")
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
    api_base_url = _api_base_url(base_url)
    _assert_url_available(base_url)
    _ensure_project(api_base_url)
    output_dir = args.output_dir
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    console_errors: list[str] = []
    page_errors: list[str] = []
    provider_request_urls: list[str] = []
    runtime_optimizer_request_urls: list[str] = []
    captures: list[dict[str, Any]] = []
    viewports = _selected_viewports(args.viewport)

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
                    page.on("request", lambda request: _record_request(request.url, provider_request_urls, runtime_optimizer_request_urls))
                    try:
                        captures.append(_capture_viewport(page, base_url, viewport_id, viewport, screenshot_dir))
                    finally:
                        page.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Prompt optimizer browser QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Prompt optimizer browser QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_prompt_optimizer_browser_qa",
        "schema_version": "0.1.0",
        "base_url": base_url,
        "captured_at_unix": int(time.time()),
        "viewports": {viewport_id: VIEWPORTS[viewport_id] for viewport_id in viewports},
        "captures": captures,
        "runtime_optimizer_request_urls": runtime_optimizer_request_urls,
        "provider_request_urls": provider_request_urls,
        "provider_calls_started": bool(provider_request_urls),
        "console_errors": console_errors,
        "page_errors": page_errors,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not human acceptance", "not business validation", "not provider smoke"],
    }
    failures = _qa_failures(report)
    report["qa_status"] = "failed" if failures else "passed"
    report["failures"] = failures
    report_path = output_dir / "workbench_prompt_optimizer_browser_qa.json"
    serialized_report = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized_report, encoding="utf-8")
    _write_stdout(serialized_report)
    if failures:
        raise SystemExit(f"Prompt optimizer browser QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _capture_viewport(page: Any, base_url: str, viewport_id: str, viewport: dict[str, Any], screenshot_dir: Path) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".app-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator("[data-view='Create']:visible").first.click()
    optimize_button = page.locator(f"{OPTIMIZE_BUTTON_SELECTOR}:visible").first
    optimize_button.wait_for(state="visible", timeout=15_000)
    optimize_button.click()
    panel = page.locator(".prompt-optimizer-panel").first
    panel.wait_for(state="visible", timeout=15_000)
    page.locator("text=已按影视结构优化").first.wait_for(state="visible", timeout=15_000)

    viewport_dir = screenshot_dir / viewport_id
    viewport_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = viewport_dir / "prompt-optimizer.png"
    panel.screenshot(path=screenshot_path)
    body_text = page.locator("body").inner_text(timeout=10_000)
    optimized_prompt_value = page.locator("#prompt-optimizer-result").input_value(timeout=10_000)
    visible_and_field_text = f"{body_text}\n{optimized_prompt_value}"
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
        "panel_visible": panel.is_visible(),
        "optimized_prompt_visible": "专业提示词" in body_text and "人物提示词" in optimized_prompt_value and "灯光提示词" in optimized_prompt_value,
        "optimized_prompt_excerpt": optimized_prompt_value[:240],
        "required_labels_missing": [label for label in REQUIRED_LABELS if label not in body_text],
        "local_optimizer_visible": "已用本地优化" in body_text,
        "forbidden_matches": _visible_forbidden_matches(visible_and_field_text),
        "viewport_overflow": viewport_overflow,
    }


def _qa_failures(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for capture in report["captures"]:
        viewport_id = capture["viewport_id"]
        if not capture["panel_visible"]:
            failures.append(f"{viewport_id}: prompt optimizer panel not visible")
        if not capture["optimized_prompt_visible"]:
            failures.append(f"{viewport_id}: optimized prompt text not visible")
        if capture["required_labels_missing"]:
            failures.append(f"{viewport_id}: missing labels {capture['required_labels_missing']}")
        if capture["forbidden_matches"]:
            failures.append(f"{viewport_id}: forbidden visible text {capture['forbidden_matches']}")
        if capture["viewport_overflow"]["x"]:
            failures.append(f"{viewport_id}: horizontal viewport overflow")
    if not report["runtime_optimizer_request_urls"]:
        failures.append("missing prompt-optimizations request")
    if report["provider_calls_started"]:
        failures.append(f"provider requests: {report['provider_request_urls']}")
    if report["console_errors"]:
        failures.append(f"console errors: {report['console_errors']}")
    if report["page_errors"]:
        failures.append(f"page errors: {report['page_errors']}")
    return failures


def _record_request(url: str, provider_urls: list[str], optimizer_urls: list[str]) -> None:
    lowered = url.lower()
    if "prompt-optimizations" in lowered:
        optimizer_urls.append(url)
    if any(pattern in lowered for pattern in PROVIDER_REQUEST_PATTERNS):
        provider_urls.append(url)


def _ensure_project(api_base_url: str) -> None:
    manifest_url = urllib.parse.urljoin(api_base_url, f"/projects/{PROJECT_ID}/manifest")
    try:
        with urllib.request.urlopen(manifest_url, timeout=10) as response:  # noqa: S310 - local QA URL.
            if response.status < 400:
                return
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    except urllib.error.URLError:
        raise
    payload = json.dumps({
        "project_id": PROJECT_ID,
        "project_type": "short_video_campaign",
        "goal": "Prompt optimizer browser QA project.",
        "status": "in_progress",
    }).encode("utf-8")
    request = urllib.request.Request(
        urllib.parse.urljoin(api_base_url, "/projects"),
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - local QA URL.
        if response.status >= 400:
            raise SystemExit(f"Could not create QA project: HTTP {response.status}")


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


def _api_base_url(workbench_url: str) -> str:
    parsed = urllib.parse.urlparse(workbench_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _assert_url_available(url: str) -> None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local QA URL.
            if response.status >= 400:
                raise SystemExit(f"Workbench URL returned HTTP {response.status}: {url}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Workbench URL is not available: {url}. Start the local service first.") from exc


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
