from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, stop_runtime, wait_for_http
from studio_image_gate_prep_browser_qa import (
    PROJECT_ID,
    http_json,
    http_post_json,
    seed_canonical_project,
)
from studio_image_recovery_manifest_browser_qa import (
    fulfill_ready_image_capability,
    open_asset_bible,
    open_image_admission,
    prepare_locked_manifest,
    read_manifest,
    start_runtime,
)
from studio_m6_script_plan_asset_bible_browser_qa import configure


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="AFS next image batch desktop browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-next-image-batch-")).resolve()
    stamp = int(time.time())
    report_path = Path(args.report or f"/tmp/afs-next-image-batch-{stamp}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/afs-next-image-batch-{stamp}-screens").resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    seed_canonical_project(runtime_root)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    os.environ["AFS_ALLOW_DETERMINISTIC_MEDIA_FIXTURES"] = "true"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_qa(repo, runtime_root, base_url, screenshot_dir)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": report["screenshots"]}))
        return 0
    finally:
        stop_runtime(server)


def run_qa(repo: Path, runtime_root: Path, base_url: str, screenshot_dir: Path) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    provider_routes: list[str] = []
    screenshots: dict[str, str] = {}
    source_capture: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            configure(page, repo, 120_000, console_errors, response_errors)
            page.on("request", lambda request: capture_admission_source(request, source_capture))
            page.route(f"**/projects/{PROJECT_ID}/m6/image-admission", fulfill_ready_image_capability)
            page.on(
                "request",
                lambda request: provider_routes.append(request.url)
                if any(marker in request.url for marker in ("/keyframe-generations", "/provider/", "/dispatch"))
                else None,
            )
            page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=next-image-batch")
            page.wait_for_selector(".graph-canvas-status.ready")
            prepare_locked_manifest(page, base_url)
            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            character = panel.locator(".image-admission-item").filter(has_text="角色设定").first
            character.get_by_role("button", name="载入零费用测试候选").click()
            panel.locator(".image-admission-review").get_by_role("button", name="确认").click()
            expect(character).to_contain_text("待审核")
            approve_admission_item(base_url, source_capture["source"], read_manifest(runtime_root), "character_design")
            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            character = panel.locator(".image-admission-item").filter(has_text="角色设定").first
            expect(character).to_contain_text("已批准")
            panel.get_by_role("button", name="停止未发送项目").click()
            panel.locator(".image-admission-review").get_by_role("button", name="确认").click()
            expect(panel.get_by_role("button", name="准备下一批图片")).to_be_visible()

            old_manifest = read_manifest(runtime_root)
            panel.get_by_role("button", name="准备下一批图片").click()
            selector = panel.locator(".image-admission-next-batch")
            expect(selector).to_contain_text("选择本批内容")
            scene = selector.locator("label").filter(has_text="场景净板")
            prop = selector.locator("label").filter(has_text="核心道具")
            scene.locator("input").check()
            prop.locator("input").check()
            expect(selector).to_contain_text("已选 2 项")
            expect(selector).to_contain_text("下一步按当前服务合同核验费用")
            expect(selector).not_to_contain_text("$0.0754")
            selector.scroll_into_view_if_needed()
            screenshots["selection_1920x1080"] = str((screenshot_dir / "selection-1920x1080.png").resolve())
            page.screenshot(path=screenshots["selection_1920x1080"])

            selector.get_by_role("button", name="预览费用").click()
            review = panel.locator(".image-admission-review")
            expect(review).to_contain_text("确认下一批图片")
            expect(review).to_contain_text("硬上限 2 次 / $0.0754")
            expect(review).to_contain_text("场景净板")
            expect(review).to_contain_text("核心道具")
            expect(review).to_contain_text("每张图片仍需另行预览并确认生成")
            screenshots["review_1920x1080"] = str((screenshot_dir / "review-1920x1080.png").resolve())
            page.screenshot(path=screenshots["review_1920x1080"])
            if read_manifest(runtime_root) != old_manifest:
                raise AssertionError("next-batch preview mutated the active manifest")
            review.get_by_role("button", name="建立本批清单").click()
            expect(panel).to_contain_text("本轮硬上限")
            expect(panel).to_contain_text("$0.0754 · 2 次")
            current = read_manifest(runtime_root)
            if len(current["items"]) != 2 or current["provider_dispatch_count"] != 0:
                raise AssertionError("next batch did not persist exactly two zero-dispatch items")
            history_path = (
                runtime_root
                / "projects"
                / PROJECT_ID
                / "image_admission"
                / "history"
                / f"{old_manifest['manifest_id']}.json"
            )
            if json.loads(history_path.read_text(encoding="utf-8")) != old_manifest:
                raise AssertionError("previous image manifest was not preserved immutably")

            page.reload(wait_until="domcontentloaded")
            open_asset_bible(page)
            panel = open_image_admission(page)
            expect(panel).to_contain_text("$0.0754 · 2 次")
            expect(panel.locator(".image-admission-item")).to_have_count(2)
            page.set_viewport_size({"width": 1440, "height": 900})
            screenshots["refresh_1440x900"] = str((screenshot_dir / "refresh-1440x900.png").resolve())
            page.screenshot(path=screenshots["refresh_1440x900"], full_page=True)
            body = page.locator("body").inner_text()
            for marker in ("schema_version", "manifest_id", "provider_service_id"):
                if marker in body:
                    raise AssertionError(f"creator UI leaked internal marker: {marker}")
        finally:
            browser.close()
    actionable = [
        item for item in response_errors if not item["url"].endswith("/favicon.ico")
    ]
    if console_errors or actionable or provider_routes:
        raise AssertionError(
            f"console={console_errors[:3]} responses={actionable[:3]} provider={provider_routes[:3]}"
        )
    admission = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/image-admission")
    return {
        "selected_items": 2,
        "max_dispatches": admission["manifest"]["budget_contract"]["max_dispatches"],
        "max_estimated_usd": admission["manifest"]["budget_contract"]["max_estimated_usd"],
        "provider_dispatch_count": admission["provider_dispatch_count"],
        "external_cost_usd": admission["external_cost_usd"],
        "screenshots": screenshots,
    }


def capture_admission_source(request, target: dict[str, Any]) -> None:
    if not request.url.endswith("/m6/image-admission/commands/preview") or not request.post_data:
        return
    payload = json.loads(request.post_data)
    if isinstance(payload.get("source"), dict):
        target["source"] = payload["source"]


def approve_admission_item(
    base_url: str,
    source: dict[str, Any],
    manifest: dict[str, Any],
    item_type: str,
) -> None:
    item = next(item for item in manifest["items"] if item["item_type"] == item_type)
    command = {
        "type": "approve",
        "item_id": item["item_id"],
        "idempotency_key": f"browser-approve-{item['item_id']}",
    }
    request = {
        "command": command,
        "source": source,
        "requested_at": "2026-07-26T00:00:00Z",
    }
    preview = http_post_json(
        f"{base_url}/projects/{PROJECT_ID}/m6/image-admission/commands/preview",
        request,
    )
    http_post_json(
        f"{base_url}/projects/{PROJECT_ID}/m6/image-admission/commands/confirm",
        {**request, "preview_digest": preview["preview_digest"]},
    )


if __name__ == "__main__":
    raise SystemExit(main())
