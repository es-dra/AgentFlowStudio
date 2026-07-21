from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ({"width": 1440, "height": 900}, {"width": 1024, "height": 768}, {"width": 800, "height": 900})
COUNTED_CASES = ("dialogue_room", "four_person_action")


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-2-paid-media-browser-{int(time.time())}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or report_path.with_suffix("")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(base_url, screenshot_dir, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": str(screenshot_dir)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.2 paid media adaptive workspace browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--run-id", default="paid-media-v2")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def run_qa(base_url: str, screenshot_dir: Path, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in VIEWPORTS:
                viewport_key = f"{viewport['width']}x{viewport['height']}"
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on(
                    "response",
                    lambda response: response_errors.append({"status": response.status, "url": response.url})
                    if response.status >= 400
                    else None,
                )
                summaries = {}
                for case_id in COUNTED_CASES:
                    payload = _load_workspace(page, base_url, case_id)
                    summaries[case_id] = _assert_workspace(case_id, payload)
                screenshot_path = screenshot_dir / f"m6-2-paid-media-{viewport_key}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshots[viewport_key] = str(screenshot_path.resolve())
                results[viewport_key] = summaries
                page.close()
        finally:
            browser.close()
    actionable = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable:
        raise AssertionError(f"console={console_errors[:5]} responses={actionable[:5]}")
    return {
        "artifact_type": "afs_m6_2_paid_media_browser_qa",
        "status": "passed",
        "viewports": results,
        "screenshots": screenshots,
        "console_error_count": 0,
        "response_error_count": 0,
        "provider_dispatch_boundary": "read-only browser QA; no provider dispatch is triggered",
    }


def _load_workspace(page: Any, base_url: str, case_id: str) -> dict[str, Any]:
    url = f"{base_url}/projects/m6-2-{case_id}/adaptive-canvas-v2/workspace?run_id=paid-media-v2"
    page.goto(url, wait_until="networkidle")
    text = page.locator("body").inner_text()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise AssertionError(f"workspace did not return an object: {case_id}")
    return payload


def _assert_workspace(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_tokens = ("/home/", "/tmp/", "/var/", ".mp4", ".png", "api_key", "authorization", "bearer", "secret")
    leaked = [token for token in forbidden_tokens if token.lower() in serialized.lower()]
    if leaked:
        raise AssertionError(f"unsafe adaptive workspace leak for {case_id}: {leaked}")
    if payload.get("schema_version") != "afs.adaptive_canvas_v2.workspace.v0.1":
        raise AssertionError(f"unexpected workspace schema for {case_id}")
    shots = payload.get("shots") if isinstance(payload.get("shots"), list) else []
    assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
    timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else {}
    final_demo = payload.get("final_demo") if isinstance(payload.get("final_demo"), dict) else {}
    qa = payload.get("qa") if isinstance(payload.get("qa"), dict) else {}
    if len(shots) < 2 or len(timeline.get("order") or []) != len(shots):
        raise AssertionError(f"workspace shot/timeline mismatch for {case_id}")
    if not assets.get("characters") or not assets.get("scenes") or not assets.get("style_bible"):
        raise AssertionError(f"workspace missing asset Bible projection for {case_id}")
    if final_demo.get("status") != "silent_video_ready_for_owner_review":
        raise AssertionError(f"workspace missing final demo status for {case_id}")
    if qa.get("status") != "pass":
        raise AssertionError(f"workspace QA did not pass for {case_id}")
    provider_dispatch_count = int(payload.get("provider_dispatch_count") or 0)
    if provider_dispatch_count <= 0:
        raise AssertionError(f"workspace did not preserve paid provider dispatch lineage for {case_id}")
    non_claims = payload.get("non_claims") if isinstance(payload.get("non_claims"), list) else []
    if "not_human_creative_acceptance" not in non_claims:
        raise AssertionError(f"workspace lost non-claim boundary for {case_id}")
    return {
        "schema": payload["schema_version"],
        "shot_count": len(shots),
        "timeline_duration_sec": timeline.get("duration_sec"),
        "final_duration_sec": final_demo.get("duration_sec"),
        "provider_dispatch_count": provider_dispatch_count,
        "qa_status": qa.get("status"),
        "safe_projection_no_private_paths": True,
    }


def start_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "AFS_RUNTIME_SERVICE_ROOT": str(runtime_root),
            "AFS_RUNTIME_ROOT": str(runtime_root),
            "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1",
            "AFS_RUNTIME_SERVICE_PORT": str(port),
            "AFS_AUTH_ENABLED": "false",
            "AFS_AUTH_ALLOW_OPEN_SIGNUP": "false",
            "NO_PROXY": _merge_no_proxy(env.get("NO_PROXY")),
            "no_proxy": _merge_no_proxy(env.get("no_proxy")),
        }
    )
    for key in (
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        env.pop(key, None)
    return subprocess.Popen(
        [sys.executable, "-m", "apps.cli.main", "runtime-service", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    lowered = {item.lower() for item in entries}
    for item in ("127.0.0.1", "localhost", "::1"):
        if item.lower() not in lowered:
            entries.append(item)
    return ",".join(entries)


if __name__ == "__main__":
    raise SystemExit(main())
