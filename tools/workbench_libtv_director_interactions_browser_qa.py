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
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/workbench_libtv_director_interactions_browser_qa")
PROVIDER_REQUEST_PATTERNS = ("api.openai.com", "replicate.com", "fal.ai", "stability.ai", "/provider", "/generate")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise LibTV-style Director Desk interactions in a real browser.")
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
                capture = _run_director_qa(page, base_url, screenshot_dir, provider_request_urls)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Director interactions QA timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Director interactions QA failed: {exc}") from exc

    report = {
        "artifact_type": "agentflow_workbench_libtv_director_interactions_browser_qa",
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
    report_path = output_dir / "workbench_libtv_director_interactions_browser_qa.json"
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(serialized, encoding="utf-8")
    _write_stdout(serialized)
    if failures:
        raise SystemExit(f"Director interactions QA found {len(failures)} failure(s). See {report_path}")
    return 0


def _run_director_qa(page: Any, base_url: str, screenshot_dir: Path, provider_urls: list[str]) -> dict[str, Any]:
    page.goto(base_url, wait_until="domcontentloaded")
    page.locator(".libtv-shell").first.wait_for(state="visible", timeout=15_000)
    page.locator("[data-view='Create']").first.click()
    page.locator(".libtv-canvas.canvas-product-v3").first.wait_for(state="visible", timeout=15_000)

    _open_add_menu(page)
    page.locator("[data-add-node-kind='director']").first.click()
    page.locator(".director-flow-v3").first.wait_for(state="visible", timeout=10_000)

    stage = page.locator(".libtv-director-stage").first
    target = page.locator("[data-director-drag-id='key-light']").first
    stage_box = stage.bounding_box()
    target_box = target.bounding_box()
    if not stage_box or not target_box:
        raise AssertionError("Director stage or draggable light has no bounding box")

    style_before_drag = target.get_attribute("style")
    page.mouse.move(target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(stage_box["x"] + stage_box["width"] * 0.68, stage_box["y"] + stage_box["height"] * 0.32, steps=8)
    page.mouse.up()
    page.wait_for_timeout(180)
    target = page.locator("[data-director-drag-id='key-light']").first
    style_after_drag = target.get_attribute("style")

    page.locator("[data-director-element-id='camera-a']").first.click()
    page.wait_for_timeout(100)
    panel_text_after_select = page.locator(".libtv-director-camera-panel").first.inner_text(timeout=5_000)

    page.locator("[data-action='apply-director-setup-to-shot']").first.click()
    page.wait_for_timeout(150)
    applied_text = page.locator(".libtv-director-camera-panel small").first.inner_text(timeout=5_000)

    page.locator("[data-action='save-director-setup']").first.click()
    page.wait_for_timeout(180)
    status_after_save = page.locator(".libtv-director-camera-panel em").first.inner_text(timeout=5_000)

    page.locator("[data-view='Assets']").first.click()
    page.locator(".asset-library-page").first.wait_for(state="visible", timeout=10_000)
    saved_asset_count = page.locator("[data-visible-asset-id^='director-setup-']").count()
    selected_saved_count = page.locator(".visible-asset-card.selected[data-visible-asset-id^='director-setup-']").count()

    screenshot_path = screenshot_dir / "director-interactions.png"
    page.screenshot(path=screenshot_path, full_page=False)
    return {
        "style_before_drag": style_before_drag,
        "style_after_drag": style_after_drag,
        "panel_text_after_select": panel_text_after_select,
        "applied_text": applied_text,
        "status_after_save": status_after_save,
        "saved_asset_count": saved_asset_count,
        "selected_saved_count": selected_saved_count,
        "viewport_overflow": _viewport_overflow(page),
        "provider_calls_started": bool(provider_urls),
        "screenshot": screenshot_path.as_posix(),
    }


def _open_add_menu(page: Any) -> None:
    menu = page.locator(".libtv-add-menu").first
    if not menu.count() or not menu.is_visible():
        page.locator("[data-studio-tool='add']").first.click()
    page.locator(".libtv-add-menu").first.wait_for(state="visible", timeout=10_000)


def _qa_failures(report: dict[str, Any]) -> list[str]:
    capture = report["capture"]
    failures: list[str] = []
    if capture["style_before_drag"] == capture["style_after_drag"]:
        failures.append("director object drag did not persist a new style position")
    if "Camera A" not in capture["panel_text_after_select"]:
        failures.append("camera object selection did not update the side panel")
    if not capture["applied_text"].strip():
        failures.append("applying director setup did not populate prompt context text")
    if not capture["status_after_save"].strip():
        failures.append("saving director setup did not show a status")
    if capture["saved_asset_count"] < 1:
        failures.append("saved director setup did not appear in visible assets")
    if capture["selected_saved_count"] < 1:
        failures.append("saved director setup was not selected in visible assets")
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
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local QA URL.
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
