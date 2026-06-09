from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_ROOT = Path("data/processed/runs/workbench_browser_smoke")
LEGACY_FIRST_SCREEN_PATTERNS = (
    "Demo brief",
    "Safe campaign brief summary",
    "Reference library",
    "Project readiness",
    "Run provider preflight",
    "Operations workspace",
    "Job center",
    "Command hub",
    "Production board",
    "First generation check",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Workbench vertical flow in a real browser.")
    parser.add_argument("--port", type=int, default=0, help="Runtime Service port. Defaults to an available local port.")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT, help="Ignored runtime output root.")
    parser.add_argument("--headed", action="store_true", help="Show the browser window.")
    args = parser.parse_args()

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for browser smoke. Install locally with: "
            f"{sys.executable} -m pip install playwright && {sys.executable} -m playwright install chromium"
        ) from exc

    port = args.port or _free_port()
    runtime_root = args.runtime_root.resolve()
    output_dir = runtime_root / "browser_evidence"
    output_dir.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{port}"
    project_id = f"proj_browser_vertical_{int(time.time())}"
    server = _start_runtime_service(port=port, runtime_root=runtime_root)
    console_errors: list[str] = []
    final_state: dict[str, Any] | None = None
    first_screen: dict[str, Any] | None = None
    try:
        _wait_for_health(base_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            try:
                first_screen = _run_browser_flow(page, base_url=base_url, project_id=project_id)
                screenshot_path = output_dir / "workbench-ready-for-next-round.png"
                page.screenshot(path=screenshot_path, full_page=True)
            finally:
                browser.close()
        final_state = _json_get(f"{base_url}/projects/{project_id}/workbench-state")
    except PlaywrightTimeoutError as exc:
        raise SystemExit(f"Browser smoke timed out: {exc}") from exc
    except PlaywrightError as exc:
        raise SystemExit(f"Browser smoke failed: {exc}") from exc
    finally:
        _stop_server(server)

    if final_state is None:
        raise SystemExit("Browser smoke did not produce final Workbench state.")
    if first_screen is None:
        raise SystemExit("Browser smoke did not inspect the acceptance first screen.")
    _assert_final_state(final_state, console_errors)
    report = {
        "artifact_type": "agentflow_workbench_vertical_flow_browser_smoke",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "runtime_root": runtime_root.as_posix(),
        "screenshot": (output_dir / "workbench-ready-for-next-round.png").as_posix(),
        "project_status": final_state["project"]["status"],
        "readiness_status": final_state["project_readiness"]["status"],
        "current_action": final_state["project_readiness"]["current_action"],
        "acceptance_first_screen": first_screen,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not human acceptance", "not business validation", "not durable memory"],
    }
    report_path = output_dir / "workbench_vertical_flow_browser_smoke.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def _run_browser_flow(page: Any, *, base_url: str, project_id: str) -> dict[str, Any]:
    page.goto(f"{base_url}/workbench/", wait_until="networkidle")
    first_screen = _capture_acceptance_first_screen(page)
    _assert_acceptance_first_screen(first_screen)
    _open_diagnostics(page)
    _fill_if_present(page, "#runtime-url", base_url)
    _fill_if_present(page, "#project-id", project_id)
    _fill_if_present(page, "#project-id-action", project_id)
    _fill_if_present(page, "#project-goal", "通过浏览器点击完成确定性工作台主路径。")
    _click_action(page, "create-project")
    _click_view(page, "Create")
    page.locator(".studio-workspace").wait_for(state="visible", timeout=10_000)

    _click_view(page, "Assets")
    _fill_if_present(page, "#source-asset-id", "brief-browser")
    _fill_if_present(page, "#source-asset-type", "brief")
    _fill_if_present(page, "#source-asset-label", "浏览器主路径需求")
    _fill_if_present(page, "#source-asset-summary", "通过浏览器录入的安全需求摘要，用于确定性内容制作主路径。")
    _click_action(page, "register-source-asset")
    _wait_for_action(page, "draft-canvas")

    _click_action(page, "draft-canvas")
    _wait_for_action(page, "run-asset-test")

    _click_action(page, "run-asset-test", timeout=30_000)
    _wait_for_action(page, "run-two-round")

    _click_view(page, "Review")
    _click_action(page, "record-review-decision")
    _wait_for_action(page, "run-two-round")

    _click_action(page, "run-two-round", timeout=30_000)
    _wait_for_project_status(base_url, project_id, "ready_for_next_round")

    if page.locator(".toast.error").count():
        raise AssertionError(page.locator(".toast.error").first.text_content() or "Workbench showed an error toast.")
    return first_screen


def _capture_acceptance_first_screen(page: Any) -> dict[str, Any]:
    page.locator(".app-shell").first.wait_for(state="visible", timeout=10_000)
    page.wait_for_function(
        "() => document.querySelector('.project-row') || document.querySelector('.empty-workspace') || document.querySelector('.workspace')",
        timeout=10_000,
    )
    visible_text = page.locator("body").inner_text(timeout=10_000)
    project_list_text = page.evaluate("() => Array.from(document.querySelectorAll('.project-row')).map((node) => node.innerText).join('\\n')")
    old_ids = sorted(set(re.findall(r"\bproj_[a-z0-9_]+\b", project_list_text, flags=re.IGNORECASE)))
    english_matches = [text for text in LEGACY_FIRST_SCREEN_PATTERNS if re.search(re.escape(text), visible_text, flags=re.IGNORECASE)]
    return {
        "old_project_ids_visible": bool(old_ids),
        "old_project_ids": old_ids[:10],
        "question_mark_runs": len(re.findall(r"\?{6,}", project_list_text)),
        "stage_rc_visible": bool(re.search(r"Stage\s*7|stage7", project_list_text, flags=re.IGNORECASE)),
        "visible_english_matches": english_matches,
        "toast_errors": [text for text in page.locator(".toast.error").all_text_contents() if text.strip()],
    }


def _assert_acceptance_first_screen(first_screen: dict[str, Any]) -> None:
    assert not first_screen["old_project_ids_visible"], first_screen
    assert first_screen["question_mark_runs"] == 0, first_screen
    assert first_screen["stage_rc_visible"] is False, first_screen
    assert first_screen["visible_english_matches"] == [], first_screen
    assert first_screen["toast_errors"] == [], first_screen


def _open_diagnostics(page: Any) -> None:
    panel = page.locator(".diagnostic-panel").first
    if not panel.count():
        return
    if not panel.evaluate("node => node.open"):
        page.locator(".diagnostic-panel summary").first.click()
        page.locator("#runtime-url").first.wait_for(state="visible", timeout=10_000)


def _wait_for_action(page: Any, action: str, *, timeout: int = 20_000) -> None:
    page.locator(f"[data-action='{action}']").first.wait_for(state="visible", timeout=timeout)


def _click_action(page: Any, action: str, *, timeout: int = 10_000) -> None:
    locator = page.locator(f"[data-action='{action}']").first
    locator.wait_for(state="visible", timeout=timeout)
    locator.click(timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)
    page.wait_for_timeout(100)
    if page.locator(".toast.error").count():
        raise AssertionError(page.locator(".toast.error").first.text_content() or f"{action} failed")


def _click_view(page: Any, view: str) -> None:
    locator = page.locator(f"[data-view='{view}']").first
    locator.wait_for(state="visible", timeout=10_000)
    locator.click()
    page.wait_for_timeout(50)


def _fill_if_present(page: Any, selector: str, value: str) -> None:
    locator = page.locator(selector)
    if locator.count():
        locator.first.fill(value)


def _wait_for_project_status(base_url: str, project_id: str, status: str) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        state = _json_get(f"{base_url}/projects/{project_id}/workbench-state")
        if state.get("project", {}).get("status") == status:
            return
        time.sleep(0.2)
    raise AssertionError(f"Project did not reach {status}.")


def _assert_final_state(state: dict[str, Any], console_errors: list[str]) -> None:
    serialized = json.dumps(state, ensure_ascii=False).lower()
    assert state["project"]["status"] == "ready_for_next_round"
    assert state["project_readiness"]["status"] == "ready_for_provider_preflight"
    assert state["project_readiness"]["current_action"] == "run_provider_preflight"
    assert state["review_room"]["decision_counts"]["keep"] == 1
    assert state["project_hub"]["counts"]["runs"] >= 2
    assert state["project_hub"]["counts"]["profile_versions"] == 1
    assert state["provider_gate"]["status"] == "ready_not_run"
    assert not console_errors, console_errors
    for forbidden in ("api_key", "signed_url", "provider_config"):
        assert forbidden not in serialized


def _start_runtime_service(*, port: int, runtime_root: Path) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "apps.cli.main",
        "runtime-service",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--runtime-root",
        str(runtime_root),
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _stop_server(server: subprocess.Popen[str]) -> None:
    if server.poll() is not None:
        return
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)


def _wait_for_health(base_url: str) -> None:
    deadline = time.time() + 20
    last_error = ""
    while time.time() < deadline:
        try:
            payload = _json_get(f"{base_url}/health")
            if payload.get("status") in {"ok", "ready"}:
                return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"Runtime Service did not become healthy: {last_error}")


def _json_get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local smoke URL.
        return json.loads(response.read().decode("utf-8"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    raise SystemExit(main())
