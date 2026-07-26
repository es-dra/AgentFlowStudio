from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    stop_runtime,
    wait_for_http,
)
from studio_image_gate_prep_browser_qa import (
    PROJECT_ID,
    complete_and_lock_asset_bible,
    http_json,
    seed_canonical_project,
)
from studio_m6_script_plan_asset_bible_browser_qa import configure


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900})


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(
        args.runtime_root or tempfile.mkdtemp(prefix="afs-image-recovery-browser-")
    ).resolve()
    stamp = int(time.time())
    report_path = Path(
        args.report or f"/tmp/afs-image-recovery-browser-{stamp}.json"
    ).resolve()
    screenshot_dir = Path(
        args.screenshot_dir or f"/tmp/afs-image-recovery-browser-{stamp}-screens"
    ).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    seed_canonical_project(runtime_root)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(repo, runtime_root, base_url, screenshot_dir, args.timeout_ms)
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
        description="AFS failed-image recovery manifest desktop browser QA"
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
            "AFS_ALLOW_REMOTE_IMAGE": "true",
        }
    )
    for key in (
        "AFS_ALLOW_REMOTE_LLM",
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
    runtime_root: Path,
    base_url: str,
    screenshot_dir: Path,
    timeout_ms: int,
) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    provider_routes: list[str] = []
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            page = browser.new_page(viewport=VIEWPORTS[0])
            configure(page, repo, timeout_ms, console_errors, response_errors)
            page.route(
                f"**/projects/{PROJECT_ID}/m6/image-admission",
                fulfill_ready_image_capability,
            )
            page.on(
                "request",
                lambda request: provider_routes.append(request.url)
                if any(
                    marker in request.url
                    for marker in (
                        "/keyframe-generations",
                        "/provider/",
                        "/image-admission/dispatch",
                    )
                )
                else None,
            )
            page.goto(
                f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=image-recovery",
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(".graph-canvas-status.ready")
            prepare_locked_manifest(page, base_url)
            old_manifest = seed_exhausted_failure(runtime_root)
            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)

            expect(panel).to_contain_text("图片结果未能安全接收")
            expect(panel).to_contain_text("旧尝试与费用记录会完整保留")
            expect(panel).not_to_contain_text("预览替换")
            expect(panel).not_to_contain_text("请求参数无效")
            expect(panel).not_to_contain_text(old_manifest["manifest_id"])
            recovery_button = panel.get_by_role(
                "button", name="建立新的单次恢复清单"
            )
            if recovery_button.count() != 1:
                current = read_manifest(runtime_root)
                raise AssertionError(
                    "recovery action missing "
                    + json.dumps(
                        {
                            "status": current.get("status"),
                            "budget": current.get("budget"),
                            "budget_contract": current.get("budget_contract"),
                            "recovery_contract": current.get("recovery_contract"),
                            "panel": panel.inner_text(),
                        },
                        ensure_ascii=False,
                    )
                )
            recovery_button.click()
            review = panel.locator(".image-admission-review")
            expect(review).to_contain_text("旧清单的 1 次记录与 $0.0377 费用估算将永久保留")
            expect(review).to_contain_text("新清单只包含原失败图片")
            expect(review).to_contain_text("不会自动重试")
            expect(review).to_contain_text("确认只会建立新清单，不会生成图片")
            persisted_before_confirm = read_manifest(runtime_root)
            if persisted_before_confirm != old_manifest:
                raise AssertionError("recovery preview mutated the old manifest")
            screenshots["recovery-preview-1920x1080"] = str(
                (screenshot_dir / "recovery-preview-1920x1080.png").resolve()
            )
            page.screenshot(
                path=screenshots["recovery-preview-1920x1080"],
                full_page=True,
            )

            review.get_by_role("button", name="建立新清单").click()
            expect(panel).to_contain_text("新的单次恢复清单")
            expect(panel).to_contain_text("仍需另行预览并确认一次生成")
            expect(
                panel.get_by_role("button", name="预览生成恢复图片")
            ).to_be_visible()
            current = read_manifest(runtime_root)
            assert_recovery_manifest(runtime_root, old_manifest, current)

            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            expect(panel).to_contain_text("新的单次恢复清单")
            expect(
                panel.get_by_role("button", name="预览生成恢复图片")
            ).to_be_visible()
            body = page.locator("body").inner_text()
            for marker in (
                "schema_version",
                "manifest_id",
                "provider_service_id",
                old_manifest["manifest_id"],
                current["manifest_id"],
            ):
                if marker in body:
                    raise AssertionError(f"creator UI leaked internal identifier: {marker}")
            page.set_viewport_size(VIEWPORTS[1])
            screenshots["recovery-refresh-1440x900"] = str(
                (screenshot_dir / "recovery-refresh-1440x900.png").resolve()
            )
            page.screenshot(
                path=screenshots["recovery-refresh-1440x900"],
                full_page=True,
            )
            page.close()
        finally:
            browser.close()

    actionable_responses = [
        item
        for item in response_errors
        if not item["url"].endswith("/favicon.ico")
    ]
    if console_errors or actionable_responses:
        raise AssertionError(
            f"console={console_errors[:5]} responses={actionable_responses[:5]}"
        )
    if provider_routes:
        raise AssertionError(f"provider routes were requested: {provider_routes[:5]}")
    admission = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/image-admission")
    if int(admission.get("provider_dispatch_count") or 0) != 0:
        raise AssertionError("active recovery manifest has a provider dispatch")
    return {
        "status": "passed",
        "old_manifest_preserved": True,
        "new_manifest_single_item": True,
        "refresh_recovered_active_manifest": True,
        "separate_generate_action_visible": True,
        "provider_routes": 0,
        "new_provider_dispatch_count": 0,
        "new_external_cost_usd": admission.get("external_cost_usd"),
        "viewports": ["1920x1080", "1440x900"],
        "screenshots": screenshots,
    }


def prepare_locked_manifest(page, base_url: str) -> None:
    open_asset_bible(page)
    page.locator(".studio-asset-bible").get_by_role(
        "button", name="识别资产候选"
    ).first.click()
    review = page.locator(".asset-bible-command-review")
    expect(review).to_be_visible()
    review.get_by_role("button", name="确认应用").click()
    expect(review).to_have_count(0)
    complete_and_lock_asset_bible(base_url)
    page.reload(wait_until="domcontentloaded")
    open_asset_bible(page)
    panel = open_image_admission(page)
    panel.get_by_role("button", name="预览准入清单").click()
    panel.locator(".image-admission-review").get_by_role(
        "button", name="确认"
    ).click()
    expect(panel.locator(".image-admission-review")).to_have_count(0)
    panel.get_by_role("button", name="预览锁定清单").click()
    panel.locator(".image-admission-review").get_by_role(
        "button", name="确认"
    ).click()
    expect(panel.locator(".image-admission-review")).to_have_count(0)
    if http_json(f"{base_url}/projects/{PROJECT_ID}/m6/image-admission")["status"] != "locked":
        raise AssertionError("image admission manifest did not finish locking")


def fulfill_ready_image_capability(route) -> None:
    response = route.fetch()
    payload = response.json()
    payload["capability"] = {
        **payload.get("capability", {}),
        "configured": True,
        "exact_model": True,
        "image_gate_open": True,
        "keyframe_continuity_ready": True,
        "reference_image_slots": 4,
        "blocker": "",
    }
    route.fulfill(response=response, json=payload)


def open_asset_bible(page) -> None:
    page.wait_for_selector(".graph-canvas-status.ready")
    page.get_by_role("tab", name="资产 Bible").click()
    expect(page.locator(".studio-asset-bible")).to_be_visible()


def open_image_admission(page):
    page.locator(".studio-asset-bible").get_by_role(
        "button", name="图片准入", exact=True
    ).click()
    panel = page.locator(".image-admission-panel")
    expect(panel).to_be_visible()
    return panel


def seed_exhausted_failure(runtime_root: Path) -> dict[str, Any]:
    manifest = read_manifest(runtime_root)
    failed = next(
        item for item in manifest["items"] if item["item_type"] == "character_design"
    )
    failed["state"] = "failed"
    failed["dispatch_ordinal"] = 1
    failed["error_category"] = "blocked"
    manifest["budget"].update(
        {
            "dispatches_reserved": 1,
            "estimated_reserved_usd": "0.0377",
            "remaining_dispatches": 0,
            "remaining_estimated_usd": "0.0000",
        }
    )
    manifest["provider_dispatch_count"] = 1
    manifest["receipts"].extend(
        [
            {
                "receipt_id": "deterministic-reserved",
                "manifest_id": manifest["manifest_id"],
                "manifest_hash": manifest["manifest_hash"],
                "item_id": failed["item_id"],
                "idempotency_key": "deterministic-reserve",
                "state": "reserved",
                "dispatch_ordinal": 1,
                "estimated_usd": "0.0377",
                "actual_usd": None,
                "provider_raw_response_stored": False,
            },
            {
                "receipt_id": "deterministic-failed",
                "manifest_id": manifest["manifest_id"],
                "manifest_hash": manifest["manifest_hash"],
                "item_id": failed["item_id"],
                "idempotency_key": "deterministic-failure",
                "state": "failed",
                "dispatch_ordinal": 1,
                "estimated_usd": "0.0377",
                "actual_usd": None,
                "error_category": "blocked",
                "provider_raw_response_stored": False,
            },
        ]
    )
    path = manifest_path(runtime_root)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return deepcopy(manifest)


def assert_recovery_manifest(
    runtime_root: Path,
    old_manifest: dict[str, Any],
    current: dict[str, Any],
) -> None:
    if current["manifest_id"] == old_manifest["manifest_id"]:
        raise AssertionError("recovery did not activate a new manifest")
    if (
        current["status"] != "locked"
        or len(current["items"]) != 1
        or current["items"][0]["state"] != "planned"
        or current["budget"]["dispatches_reserved"] != 0
        or current["budget"]["remaining_dispatches"] != 1
        or current["provider_dispatch_count"] != 0
        or current["budget_contract"]["auto_retry"] != 0
    ):
        raise AssertionError("active recovery manifest violates the single-image contract")
    archive = (
        manifest_path(runtime_root).parent
        / "history"
        / f"{old_manifest['manifest_id']}.json"
    )
    if json.loads(archive.read_text(encoding="utf-8")) != old_manifest:
        raise AssertionError("old manifest archive changed")


def read_manifest(runtime_root: Path) -> dict[str, Any]:
    return json.loads(manifest_path(runtime_root).read_text(encoding="utf-8"))


def manifest_path(runtime_root: Path) -> Path:
    return (
        runtime_root
        / "projects"
        / PROJECT_ID
        / "image_admission"
        / "manifest.json"
    )


if __name__ == "__main__":
    raise SystemExit(main())
