from __future__ import annotations

import argparse
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, make_mutating_runtime_proxy, make_studio_static_route
from studio_asset_context_browser_qa_support import runtime_test_client, start_runtime, stop_runtime, wait_for_http
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import ensure_ai_open, graph_counts, send_ai
from studio_m6_5_embedded_creative_action_browser_qa import (
    attach_real_reference_image,
    create_global_image_node,
    uploaded_reference_ok,
)


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

            asset_result = assert_reference_image_entry(page)
            companion_result = assert_ai_companion_provider_closed_state(page)
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
                    "reference_image_entry": asset_result,
                    "ai_companion_provider_closed": companion_result,
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


def assert_reference_image_entry(page: Page) -> dict[str, Any]:
    image_id = create_global_image_node(page, PROJECT_ID, {"width": 1366, "height": 900})
    attach_real_reference_image(page, PROJECT_ID, image_id)
    if not uploaded_reference_ok(page, PROJECT_ID, image_id):
        raise AssertionError("reference image node did not retain preview URL and upload asset id")
    img = page.locator(f'.node[data-node-id="{image_id}"] img').first
    expect(img).to_be_visible()
    loaded = img.evaluate("(node) => Boolean(node.complete && node.naturalWidth > 0)")
    if not loaded:
        raise AssertionError("reference image preview did not load")
    return {"image_node_id": image_id, "preview_loaded": True, "upload_asset_bound": True}


def assert_ai_companion_provider_closed_state(page: Page) -> dict[str, Any]:
    before = graph_counts(page, PROJECT_ID)
    ensure_ai_open(page, {"width": 1366, "height": 900})
    send_ai(page, "这个节点是什么")
    expect(page.locator(".agent-chat-log")).to_contain_text("不会用本地固定回答冒充理解")
    after = graph_counts(page, PROJECT_ID)
    if after != before:
        raise AssertionError(f"AI companion provider-closed conversation mutated graph: before={before} after={after}")
    return {"provider_closed_honest": True, "zero_mutation": True}


def assert_save_restore_and_small_viewport(page: Page, base_url: str) -> dict[str, Any]:
    before_count = page.locator(".node").count()
    page.locator('#corner-controls button[aria-label="添加节点"]').first.click()
    page.locator(".popover button").filter(has_text="场景与镜头").first.click()
    expected_count = before_count + 1
    expect(page.locator(".node")).to_have_count(expected_count)
    page.wait_for_timeout(1200)
    expect(page.locator(".studio-save-status")).to_contain_text("已保存", timeout=15_000)
    page.reload(wait_until="networkidle")
    expect(page.locator(".node")).to_have_count(expected_count)
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
    page.goto(f"{base_url}/studio/?project={PROJECT_ID}&qa=restore-{int(time.time())}", wait_until="networkidle")
    expect(page.locator(".node")).to_have_count(expected_count)
    return {"node_restored_after_reload": True, "expected_node_count": expected_count, "small_viewport": overflow}


if __name__ == "__main__":
    raise SystemExit(main())
