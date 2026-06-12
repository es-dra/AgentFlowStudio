from __future__ import annotations

import argparse
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    artifact_payload,
    chrome_path,
    fixed_visual_asset_record,
    free_port,
    make_mutating_runtime_proxy,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)


PROJECT_ID = "studio-local-001"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PROMPT = "Lin Wan stands on a rain rooftop with red long hair, cinematic keyframe."


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-studio-s1-runtime-")).resolve()
    report_path = Path(args.report or repo / "runs" / "studio_asset_context_browser_qa_report.json").resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/studio/")
        report = run_browser_qa(repo, base_url, runtime_root, headed=args.headed)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AFS Studio asset-context S1 browser QA.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def run_browser_qa(repo: Path, base_url: str, runtime_root: Path, *, headed: bool) -> dict[str, Any]:
    upload_file = runtime_root / "qa-lin-wan.png"
    upload_file.write_bytes(PNG_BYTES)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 950})
        page.set_default_timeout(20_000)
        expect.set_options(timeout=20_000)
        page.route("**/projects/**", make_mutating_runtime_proxy(runtime_root))
        try:
            page.goto(f"{base_url}/studio/?qa={int(time.time())}", wait_until="commit")
            expect(page.locator("#starter-row")).to_be_visible()
            page.wait_for_function("() => document.readyState === 'complete'")

            create_character_asset(page, upload_file)
            create_target_node(page)

            first_opt = optimize(page)
            assert_warning(first_opt, "named_asset_not_connected")

            second_opt = click_connect_suggestion(page)
            assert_no_warning(second_opt, "named_asset_not_connected")
            assert_edge_created(page)

            click_temporary_unlock(page)
            keyframe = generate_keyframe(page)
            assert_context_indicator(page)

            comparison = run_comparison(page, keyframe_request_body(keyframe))
            api_client = runtime_test_client(runtime_root)
            plan = artifact_payload(api_client, keyframe["artifacts"]["keyframe_request_plan"]["artifact_id"])
            fixed_asset_record = fixed_visual_asset_record(runtime_root, PROJECT_ID)

            assert keyframe["provider_gate"]["status"] == "blocked"
            assert keyframe["provider_calls_started"] is False
            assert keyframe["context_bundle"]["included_assets"]
            assert keyframe["context_bundle"]["temporary_lock_overrides"]
            assert "keep black short hair" not in plan["provider_prompt"]
            assert "keep red trench coat" in plan["provider_prompt"]
            assert "keep black short hair" in fixed_asset_record["negative_locks"]
            assert comparison["report"]["provider_calls_started"] is False
            assert comparison["report"]["arms"][0]["context_path"] == "legacy_asset_refs"
            assert comparison["report"]["arms"][0]["reference_images"] == []
            assert comparison["report"]["arms"][1]["context_path"] == "context_subgraph_v0.1"
            assert comparison["report"]["arms"][2]["fixed_asset_injection"] is True

            screenshot = repo / "runs" / "studio_asset_context_browser_qa.png"
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot), full_page=True)

            return {
                "artifact_type": "studio_asset_context_browser_qa_report",
                "schema_version": "0.1.0",
                "status": "passed",
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "screenshot": str(screenshot),
                "provider_gate": keyframe["provider_gate"],
                "provider_calls_started": keyframe["provider_calls_started"],
                "included_asset_count": len(keyframe["context_bundle"]["included_assets"]),
                "temporary_lock_override_count": len(keyframe["context_bundle"]["temporary_lock_overrides"]),
                "context_indicator_visible": True,
                "comparison_status": comparison["report"]["status"],
                "comparison_provider_calls_started": comparison["report"]["provider_calls_started"],
                "browser_api_post_proxy": "fastapi_testclient",
                "non_claims": [
                    "browser/runtime verification only",
                    "not human acceptance",
                    "not business validation",
                    "not live provider smoke",
                ],
            }
        finally:
            browser.close()


def create_character_asset(page: Page, upload_file: Path) -> None:
    page.locator("#starter-row .starter-card").nth(1).click()
    node = page.locator(".node").first
    expect(node).to_be_visible()
    with page.expect_file_chooser() as chooser:
        node.locator('[data-action="upload"]').click()
    with page.expect_response(lambda r: "/image-assets" in r.url and r.request.method == "POST") as upload_response:
        chooser.value.set_files(str(upload_file))
    if upload_response.value.status != 200:
        raise AssertionError(f"image upload failed: {upload_response.value.status} {upload_response.value.text()}")
    page.wait_for_function("() => window.localStorage.getItem('afs_studio_canvas_v2')?.includes('image_reference')")

    node.locator('[data-action="fix-visual-asset"]').click()
    panel = page.locator(".visual-asset-panel")
    expect(panel).to_be_visible()
    panel.locator('[data-field="label"]').fill("Lin Wan")
    panel.locator('[data-field="signature"]').fill("black short hair, red trench coat, left brow scar")
    # Structured feature-card fields replaced the old free-text feature_card textarea.
    panel.locator('[data-card="hair"]').fill("black short hair")
    panel.locator('[data-card="face"]').fill("left brow scar")
    panel.locator('[data-card="wardrobe"]').fill("red trench coat")
    panel.locator('[data-field="negative_locks"]').fill(
        "keep black short hair\nkeep red trench coat\nkeep left brow scar"
    )
    panel.locator('[data-action="fix"]').click()
    page.wait_for_function("() => window.localStorage.getItem('afs_studio_canvas_v2')?.includes('visualAssets')")


def create_target_node(page: Page) -> None:
    page.locator("#canvas-root").click(position={"x": 900, "y": 440})
    page.keyboard.press("Tab")
    page.locator(".popover .menu-item").nth(1).click()
    page.wait_for_function("() => JSON.parse(window.localStorage.getItem('afs_studio_canvas_v2')).order.length >= 2")
    page.locator(".prompt-bar textarea").fill(PROMPT)


def optimize(page: Page) -> dict[str, Any]:
    with page.expect_response(lambda r: "/prompt-optimizations" in r.url and r.request.method == "POST") as response:
        page.locator('.prompt-bar [data-action="optimize-prompt"]').click()
    payload = response.value.json()
    expect(page.locator(".optimizer-pop")).to_be_visible()
    return payload


def click_connect_suggestion(page: Page) -> dict[str, Any]:
    with page.expect_response(lambda r: "/prompt-optimizations" in r.url and r.request.method == "POST") as response:
        page.locator('.optimizer-pop [data-action="connect-named-asset"]').click()
    return response.value.json()


def click_temporary_unlock(page: Page) -> None:
    page.locator('.optimizer-pop [data-action="temporary-unlock"]').first.click()
    page.wait_for_function(
        "() => window.localStorage.getItem('afs_studio_canvas_v2')?.includes('one-off-ui-unlock')"
    )
    page.locator(".optimizer-pop .opt-close").click()


def generate_keyframe(page: Page) -> dict[str, Any]:
    target_id = target_node_id(page)
    target = page.locator(f'.node[data-node-id="{target_id}"]')
    with page.expect_request(lambda r: "/keyframe-generations" in r.url and r.method == "POST") as request_info:
        with page.expect_response(lambda r: "/keyframe-generations" in r.url and r.request.method == "POST") as response:
            target.locator('[data-action="run"]').click()
    payload = response.value.json()
    payload["_request_body"] = json.loads(request_info.value.post_data or "{}")
    return payload


def run_comparison(page: Page, request: dict[str, Any]) -> dict[str, Any]:
    body = {
        "node_id": request["node_id"],
        "prompt_text": request["prompt_text"],
        "optimized_prompt": request["optimized_prompt"],
        "target_platform": request["target_platform"],
        "style": request["style"],
        "aspect_ratio": request["aspect_ratio"],
        "candidate_count": request["candidate_count"],
        "provider_service_id": request["provider_service_id"],
        "context_subgraph": request["context_subgraph"],
        "manual_scores": {"A": {"identity": 1}, "B": {"identity": 2}, "C": {"identity": 3}},
        "generated_at": request["generated_at"],
    }
    return page.evaluate(
        """async ({ projectId, body }) => {
          const response = await fetch(`/projects/${projectId}/generation-comparisons`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify(body),
          });
          if (!response.ok) throw new Error(`comparison failed: ${response.status}`);
          return await response.json();
        }""",
        {"projectId": PROJECT_ID, "body": body},
    )


def assert_context_indicator(page: Page) -> None:
    target = page.locator(f'.node[data-node-id="{target_node_id(page)}"]')
    expect(target.locator(".context-bundle-summary")).to_be_visible()


def assert_warning(payload: dict[str, Any], warning_id: str) -> None:
    warnings = payload["context_bundle"]["warnings"]
    assert any(item.get("warning_id") == warning_id for item in warnings), warnings


def assert_no_warning(payload: dict[str, Any], warning_id: str) -> None:
    warnings = payload["context_bundle"]["warnings"]
    assert not any(item.get("warning_id") == warning_id for item in warnings), warnings


def assert_edge_created(page: Page) -> None:
    state = studio_state(page)
    assert len(state["edges"]) == 1


def keyframe_request_body(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("_request_body") or {}
    assert body.get("context_subgraph")
    assert body.get("temporary_lock_overrides")
    return body


def target_node_id(page: Page) -> str:
    state = studio_state(page)
    return state["order"][-1]


def studio_state(page: Page) -> dict[str, Any]:
    raw = page.evaluate("window.localStorage.getItem('afs_studio_canvas_v2')")
    assert raw
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
