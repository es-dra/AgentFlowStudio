from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    stop_runtime,
    wait_for_http,
)
from studio_image_gate_prep_browser_qa import PROJECT_ID, seed_canonical_project
from studio_image_recovery_manifest_browser_qa import (
    fulfill_ready_image_capability,
    open_asset_bible,
    open_image_admission,
    prepare_locked_manifest,
)
from studio_m6_script_plan_asset_bible_browser_qa import configure


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(
        args.runtime_root or tempfile.mkdtemp(prefix="afs-image-candidate-media-")
    ).resolve()
    stamp = int(time.time())
    report_path = Path(
        args.report or f"/tmp/afs-image-candidate-media-{stamp}.json"
    ).resolve()
    screenshot_dir = Path(
        args.screenshot_dir or f"/tmp/afs-image-candidate-media-{stamp}-screens"
    ).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    seed_canonical_project(runtime_root)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(repo, base_url, screenshot_dir, args.timeout_ms)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "report": str(report_path),
                    "screenshots": str(screenshot_dir),
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AFS authorized candidate-media desktop browser QA"
    )
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def start_runtime(
    repo: Path,
    runtime_root: Path,
    port: int,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "AFS_RUNTIME_SERVICE_ROOT": str(runtime_root),
            "AFS_RUNTIME_ROOT": str(runtime_root),
            "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1",
            "AFS_RUNTIME_SERVICE_PORT": str(port),
            "AFS_AUTH_ENABLED": "false",
            "AFS_AUTH_ALLOW_OPEN_SIGNUP": "false",
            "AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES": "true",
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
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "runtime-service",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_qa(
    repo: Path,
    base_url: str,
    screenshot_dir: Path,
    timeout_ms: int,
) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    provider_routes: list[str] = []
    media_requests: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            configure(page, repo, timeout_ms, console_errors, response_errors)
            page.route(
                f"**/projects/{PROJECT_ID}/m6/image-admission",
                fulfill_ready_image_capability,
            )
            page.on(
                "request",
                lambda request: observe_request(
                    request, provider_routes, media_requests
                ),
            )
            page.goto(f"{base_url}/studio/", wait_until="domcontentloaded")
            page.evaluate(
                """() => localStorage.setItem(
                  "afs_auth_session_token",
                  "browser-qa-session-token"
                )"""
            )
            page.goto(
                f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=candidate-media",
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(".graph-canvas-status.ready")
            prepare_locked_manifest(page, base_url)
            panel = open_image_admission(page)
            panel.get_by_role(
                "button", name="载入零费用测试候选"
            ).first.click()
            review = panel.locator(".image-admission-review")
            expect(review).to_be_visible()
            review.get_by_role("button", name="确认").click()

            candidate = panel.locator(".image-admission-candidate-media").first
            expect(candidate).to_contain_text("图片已加载")
            image = candidate.locator("img")
            expect(image).to_be_visible()
            assert_decoded_image(image)
            approve = panel.get_by_role("button", name="批准候选").first
            expect(approve).to_be_enabled()
            expect(panel.get_by_role("button", name="拒绝候选").first).to_be_enabled()
            source = image.evaluate("(element) => element.currentSrc")
            if not source.startswith("blob:"):
                raise AssertionError("candidate media was not isolated behind a Blob URL")
            body = page.locator("body").inner_text()
            for marker in (
                "schema_version",
                "manifest_id",
                "provider_service_id",
                "/image-assets/",
                "http://",
                "https://",
            ):
                if marker in body:
                    raise AssertionError(
                        f"creator UI leaked internal media detail: {marker}"
                    )
            candidate.scroll_into_view_if_needed()
            screenshots["candidate-visible-1440x900"] = str(
                (screenshot_dir / "candidate-visible-1440x900.png").resolve()
            )
            page.screenshot(
                path=screenshots["candidate-visible-1440x900"],
            )

            panel.get_by_role("button", name="查看大图").first.click()
            viewer = page.get_by_role("dialog")
            expect(viewer).to_be_visible()
            assert_decoded_image(viewer.locator("img"))
            screenshots["candidate-viewer-1440x900"] = str(
                (screenshot_dir / "candidate-viewer-1440x900.png").resolve()
            )
            page.screenshot(path=screenshots["candidate-viewer-1440x900"])
            viewer.get_by_role("button", name="关闭大图").click()

            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            candidate = panel.locator(".image-admission-candidate-media").first
            expect(candidate).to_contain_text("图片已加载")
            assert_decoded_image(candidate.locator("img"))
            expect(panel.get_by_role("button", name="批准候选").first).to_be_enabled()
            candidate.scroll_into_view_if_needed()
            screenshots["candidate-refresh-1440x900"] = str(
                (screenshot_dir / "candidate-refresh-1440x900.png").resolve()
            )
            page.screenshot(
                path=screenshots["candidate-refresh-1440x900"],
            )

            page.evaluate(
                """() => localStorage.setItem(
                  "afs_auth_session_token",
                  "browser-qa-second-session-token"
                )"""
            )
            open_asset_bible_from_canvas(page)
            panel = open_image_admission(page)
            session_candidate = panel.locator(
                ".image-admission-candidate-media"
            ).first
            expect(session_candidate.locator("img")).to_be_visible()
            assert_decoded_image(session_candidate.locator("img"))
            if not any(item["session"] == "second" for item in media_requests):
                raise AssertionError(
                    "candidate cache was reused across authentication sessions"
                )

            request_count = len(media_requests)
            page.evaluate(
                """() => localStorage.removeItem("afs_auth_session_token")"""
            )
            open_asset_bible_from_canvas(page)
            panel = open_image_admission(page)
            expect(panel).to_contain_text("候选图片加载失败")
            expect(panel.get_by_role("button", name="批准候选").first).to_be_disabled()
            if len(media_requests) != request_count:
                raise AssertionError(
                    "candidate media made an anonymous request without a session"
                )

            page.evaluate(
                """() => localStorage.setItem(
                  "afs_auth_session_token",
                  "browser-qa-session-token"
                )"""
            )
            open_asset_bible_from_canvas(page)
            panel = open_image_admission(page)
            panel.get_by_role("button", name="重新加载图片").first.click()
            restored_candidate = panel.locator(
                ".image-admission-candidate-media"
            ).first
            expect(restored_candidate.locator("img")).to_be_visible()
            assert_decoded_image(restored_candidate.locator("img"))
            expect(panel.get_by_role("button", name="批准候选").first).to_be_enabled()

            preview_route = (
                f"**/projects/{PROJECT_ID}/image-assets/*/preview"
            )
            page.route(
                preview_route,
                lambda route: route.fulfill(
                    status=401,
                    content_type="application/json",
                    body='{"detail":{"error":"authentication_required"}}',
                ),
            )
            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            expect(panel).to_contain_text("候选图片加载失败")
            expect(panel.get_by_role("button", name="批准候选").first).to_be_disabled()
            page.unroute(preview_route)

            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            expect(panel.locator(".image-admission-candidate-media").first).to_contain_text(
                "图片已加载"
            )
            expect(panel.get_by_role("button", name="批准候选").first).to_be_enabled()
            page.close()
        finally:
            browser.close()

    actionable_responses = [
        item
        for item in response_errors
        if not item["url"].endswith("/favicon.ico") and item["status"] != 401
    ]
    expected_auth_failures = [
        item
        for item in console_errors
        if "Failed to load resource" in item and "401" in item
    ]
    unexpected_console_errors = [
        item for item in console_errors if item not in expected_auth_failures
    ]
    if len(expected_auth_failures) != 1:
        raise AssertionError(
            f"expected one fail-closed media 401, got {expected_auth_failures}"
        )
    if unexpected_console_errors or actionable_responses:
        raise AssertionError(
            f"console={unexpected_console_errors[:5]} responses={actionable_responses[:5]}"
        )
    if provider_routes:
        raise AssertionError(f"provider routes were requested: {provider_routes[:5]}")
    if not media_requests or not all(
        item["authorized"] and item["same_origin"] for item in media_requests
    ):
        raise AssertionError(
            "candidate media fetch was not same-origin bearer authorization"
        )
    return {
        "status": "passed",
        "candidate_decoded": True,
        "candidate_dimensions": "960x1280",
        "authorized_project_media_fetch": True,
        "authentication_session_cache_isolated": True,
        "no_token_media_requests": 0,
        "browser_received_blob_url": True,
        "approval_enabled_after_decode_only": True,
        "failure_kept_approval_disabled": True,
        "anonymous_fallback_requests": 0,
        "refresh_restored_candidate": True,
        "large_viewer_decoded": True,
        "provider_routes": 0,
        "viewports": ["1440x900"],
        "screenshots": screenshots,
    }


def observe_request(
    request,
    provider_routes: list[str],
    media_requests: list[dict[str, Any]],
) -> None:
    if any(
        marker in request.url
        for marker in (
            "/keyframe-generations",
            "/provider/",
            "/image-admission/dispatch",
        )
    ):
        provider_routes.append(request.url)
    if f"/projects/{PROJECT_ID}/image-assets/" in request.url:
        media_requests.append(
            {
                "authorized": request.headers.get("authorization", "").startswith(
                    "Bearer "
                ),
                "same_origin": request.url.startswith("http://127.0.0.1:"),
                "session": media_request_session(
                    request.headers.get("authorization", "")
                ),
            }
        )


def media_request_session(authorization: str) -> str:
    if authorization == "Bearer browser-qa-session-token":
        return "first"
    if authorization == "Bearer browser-qa-second-session-token":
        return "second"
    return "unknown"


def open_asset_bible_from_canvas(page) -> None:
    page.get_by_role("tab", name="画布").click()
    open_asset_bible(page)


def assert_decoded_image(locator) -> None:
    dimensions = locator.evaluate(
        """element => ({
          complete: element.complete,
          width: element.naturalWidth,
          height: element.naturalHeight
        })"""
    )
    if dimensions != {"complete": True, "width": 960, "height": 1280}:
        raise AssertionError(f"candidate image did not decode: {dimensions}")


if __name__ == "__main__":
    raise SystemExit(main())
