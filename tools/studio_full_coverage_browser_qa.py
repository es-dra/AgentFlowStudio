from __future__ import annotations

import argparse
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, make_mutating_runtime_proxy
from studio_asset_context_browser_qa_support import runtime_test_client, start_runtime, stop_runtime, wait_for_http


PROJECT_ID = f"studio-full-browser-qa-{int(time.time())}"
PNG_BYTES = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-studio-full-qa-")).resolve()
    report_path = Path(args.report or repo / "runs" / "studio_full_coverage_browser_qa.json").resolve()
    screenshot_path = Path(args.screenshot or report_path.with_suffix(".png")).resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    prepare_project(runtime_root)
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/studio/")
        report = run_browser_scenarios(repo, base_url, runtime_root, screenshot_path, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run broader AFS Studio browser QA scenarios.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args()


def prepare_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    response = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "Studio full coverage browser QA"})
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {response.status_code} {response.text}")
    state = {
        "meta": {"projectId": PROJECT_ID, "projectName": "Full Coverage QA", "canvasName": "QA Canvas", "seq": 1, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {},
        "edges": {},
        "groups": {},
        "assets": [],
        "order": [],
    }
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state setup failed: {saved.status_code} {saved.text}")
    upload = client.post(
        f"/projects/{PROJECT_ID}/image-assets",
        json={
            "node_id": "seed-image-node",
            "filename": "qa-reference.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": "2026-06-21T00:00:00+08:00",
        },
    )
    if upload.status_code != 200:
        raise AssertionError(f"seed image asset failed: {upload.status_code} {upload.text}")


def make_studio_static_route(repo: Path):
    studio_root = (repo / "apps" / "studio").resolve()

    def route_studio_static(route: Any) -> None:
        parsed = urlsplit(route.request.url)
        relative = parsed.path.removeprefix("/studio/").replace("/", "\\")
        path = (studio_root / relative).resolve()
        try:
            path.relative_to(studio_root)
        except ValueError:
            route.fulfill(status=404, body=b"")
            return
        if not path.is_file():
            route.fulfill(status=404, body=b"")
            return
        content_type = "text/javascript; charset=utf-8" if path.suffix.lower() == ".js" else "text/css; charset=utf-8"
        route.fulfill(status=200, content_type=content_type, body=path.read_bytes())

    return route_studio_static


def run_browser_scenarios(
    repo: Path, base_url: str, runtime_root: Path, screenshot_path: Path, headed: bool, timeout_ms: int
) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(timeout_ms)
        expect.set_options(timeout=timeout_ms)
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in {"error"} else None)
        page.on(
            "response",
            lambda response: response_errors.append({"status": response.status, "url": response.url})
            if response.status >= 400
            else None,
        )
        page.route("**/studio/src/**", make_studio_static_route(repo))
        page.route("**/studio/styles/**", make_studio_static_route(repo))
        page.route("**/projects/**", make_mutating_runtime_proxy(runtime_root))
        inject_delayed_sprite_reply(page)
        try:
            page.goto(f"{base_url}/studio/?project={PROJECT_ID}&qa={int(time.time())}", wait_until="commit")
            expect(page.locator("#canvas-root")).to_be_visible()

            asset_result = assert_asset_drawer_preview_and_delete(page, runtime_root)
            sprite_result = assert_sprite_pending_state(page)
            save_result = assert_save_restore_and_small_viewport(page, base_url)

            page.screenshot(path=str(screenshot_path), full_page=True)
            actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
            if console_errors or actionable_response_errors:
                raise AssertionError(
                    f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}"
                )
            return {
                "artifact_type": "studio_full_coverage_browser_qa_report",
                "schema_version": "0.1.0",
                "status": "passed",
                "project_id": PROJECT_ID,
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "screenshot": str(screenshot_path),
                "scenarios": {
                    "asset_librarian_delete": asset_result,
                    "sprite_pending": sprite_result,
                    "returning_creator_small_viewport": save_result,
                },
                "console_error_count": len(console_errors),
                "response_error_count": len(response_errors),
                "provider_calls_started": False,
                "non_claims": ["browser/runtime verification only", "not human acceptance", "not business validation", "not video provider smoke"],
            }
        finally:
            browser.close()


def inject_delayed_sprite_reply(page: Page) -> None:
    page.add_init_script(
        """
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.__afsSpriteFetchCalls = 0;
          window.fetch = (input, init) => {
            const url = typeof input === "string" ? input : String(input?.url || "");
            if (url.includes("/sprite/chat")) {
              window.__afsSpriteFetchCalls += 1;
              return new Promise((resolve) => {
                setTimeout(() => resolve(new Response(JSON.stringify({
                  reply: "我看到了当前画布，可以继续从素材开始调整。",
                  provider_calls_started: true,
                  mode: "llm"
                }), { status: 200, headers: { "Content-Type": "application/json" } })), 3200);
              });
            }
            return originalFetch(input, init);
          };
        })();
        """
    )


def assert_asset_drawer_preview_and_delete(page: Page, runtime_root: Path) -> dict[str, Any]:
    page.locator(".drawer-tabs .drawer-tab").filter(has_text="素材").click()
    card = page.locator(".asset-card").first
    expect(card).to_be_visible()
    img = card.locator("img").first
    expect(img).to_be_visible()
    loaded = img.evaluate("(node) => Boolean(node.complete && node.naturalWidth > 0)")
    if not loaded:
        raise AssertionError("asset preview image did not load")
    card.click()
    expect(page.locator(".asset-detail-popover")).to_be_visible()
    page.keyboard.press("Escape")
    card.click(button="right")
    menu = page.locator(".asset-context-menu")
    expect(menu).to_be_visible()
    if not menu.locator("text=删除图片素材").count():
        raise AssertionError("asset context menu does not expose image delete")
    menu.locator("text=删除图片素材").click()
    expect(page.locator(".asset-card")).to_have_count(0)
    assets = runtime_test_client(runtime_root).get(f"/projects/{PROJECT_ID}/image-assets").json()["assets"]
    if assets:
        raise AssertionError("runtime image asset still exists after drawer delete")
    return {"preview_loaded": True, "context_menu_delete": True, "runtime_asset_count_after_delete": 0}


def assert_sprite_pending_state(page: Page) -> dict[str, Any]:
    orb = page.locator(".afs-sprite-orb")
    expect(orb).to_be_visible()
    orb.click()
    input_box = page.locator(".afs-sprite-form input")
    expect(input_box).to_be_visible()
    input_box.fill("目前画布是什么状态")
    input_box.press("Enter")
    pending = page.locator(".afs-sprite-msg.pending")
    expect(pending).to_be_visible()
    first_text = pending.inner_text()
    if "团团正在" not in first_text:
        raise AssertionError(f"unexpected pending text: {first_text}")
    has_shimmer = pending.evaluate("(node) => getComputedStyle(node).animationName.includes('generating-text-shimmer')")
    if not has_shimmer:
        raise AssertionError("pending text shimmer animation is missing")
    page.wait_for_timeout(2900)
    second_text = page.locator(".afs-sprite-msg.pending").inner_text()
    if second_text == first_text:
        raise AssertionError("pending text did not rotate")
    expect(page.locator(".afs-sprite-msg.pending")).to_have_count(0, timeout=10_000)
    expect(page.locator(".afs-sprite-msg.sprite").last).to_contain_text("我看到了当前画布")
    calls = page.evaluate("() => window.__afsSpriteFetchCalls || 0")
    return {"pending_rotated": True, "shimmer": True, "sprite_fetch_calls": calls}


def assert_save_restore_and_small_viewport(page: Page, base_url: str) -> dict[str, Any]:
    page.locator("#canvas-root").click(position={"x": 780, "y": 360})
    page.locator("#dock .dock-btn.primary").click()
    page.locator(".popover .quick-create-grid .quick-create-card[data-tone='scene']").click()
    expect(page.locator(".node")).to_have_count(1)
    page.wait_for_timeout(1200)
    expect(page.locator(".save-pill")).to_contain_text("已保存", timeout=15_000)
    page.reload(wait_until="commit")
    expect(page.locator(".node")).to_have_count(1)
    page.locator(".node").first.click()
    page.set_viewport_size({"width": 390, "height": 820})
    expect(page.locator("#canvas-root")).to_be_visible()
    prompt_box = page.locator(".prompt-bar")
    expect(prompt_box).to_be_visible()
    overflow = page.evaluate(
        "() => ({width: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,"
        " promptVisible: !!document.querySelector('.prompt-bar'),"
        " spriteHidden: document.querySelector('#sprite-root')?.dataset.spriteHidden || ''})"
    )
    if overflow["scrollWidth"] > overflow["width"] + 4:
        raise AssertionError(f"small viewport has horizontal overflow: {overflow}")
    page.goto(f"{base_url}/studio/?project={PROJECT_ID}&qa=restore-{int(time.time())}", wait_until="commit")
    expect(page.locator(".node")).to_have_count(1)
    return {"node_restored_after_reload": True, "small_viewport": overflow}


if __name__ == "__main__":
    raise SystemExit(main())
