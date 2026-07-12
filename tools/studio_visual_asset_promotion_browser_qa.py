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
    chrome_path,
    fixed_visual_asset_record,
    free_port,
    make_mutating_runtime_proxy,
    make_studio_static_route,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)


PROJECT_ID = f"studio-promotion-browser-qa-{int(time.time())}"
NODE_ID = "node-promotion-source"
STUDIO_STORAGE_KEY = f"afs_studio_canvas_v2:{PROJECT_ID}"
HUMAN_GATE_ID = "runtime human gate / accepted"
ASSET_CARD_CANDIDATE_ID = "asset card candidate / main"
EXPECTED_HUMAN_GATE_ID = "runtime_human_gate_accepted"
EXPECTED_ASSET_CARD_CANDIDATE_ID = "asset_card_candidate_main"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-promotion-browser-")).resolve()
    report_path = Path(args.report or repo / "runs" / "studio_visual_asset_promotion_browser_qa.json").resolve()
    screenshot_path = resolve_screenshot_path(report_path, args.screenshot)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    seed = prepare_project(runtime_root, project_id=PROJECT_ID)
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/studio/")
        report = run_browser_qa(repo, base_url, runtime_root, seed, screenshot_path, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic AFS Studio visual-asset promotion browser QA.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args()


def resolve_screenshot_path(report_path: Path, screenshot_arg: str) -> Path:
    if screenshot_arg:
        return Path(screenshot_arg).resolve()
    return report_path.with_suffix(".png")


def prepare_project(runtime_root: Path, *, project_id: str = PROJECT_ID) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    response = client.post("/projects", json={"project_id": project_id, "goal": "Studio promotion browser QA"})
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {response.status_code} {response.text}")
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": NODE_ID,
            "filename": "promotion-source.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "character_reference",
            "generated_at": "2026-06-30T22:00:00+08:00",
        },
    )
    if upload.status_code != 200:
        raise AssertionError(f"seed image asset failed: {upload.status_code} {upload.text}")
    image_asset = upload.json()["asset"]
    state = seeded_studio_state(project_id, image_asset)
    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio-state setup failed: {saved.status_code} {saved.text}")
    return {"project_id": project_id, "image_asset": image_asset}


def seeded_studio_state(project_id: str, image_asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "meta": {"projectId": project_id, "projectName": "Promotion Browser QA", "canvasName": "QA Canvas", "seq": 1, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {
            NODE_ID: {
                "id": NODE_ID,
                "type": "image",
                "title": "Promotion source",
                "x": 520,
                "y": 320,
                "w": 280,
                "h": 280,
                "prompt": "Lin Wan character reference for fixed asset promotion.",
                "content": "",
                "status": "complete",
                "result": "Seeded image reference with accepted asset-card gate evidence.",
                "previewUrl": image_asset.get("preview_url", ""),
                "params": {
                    "model": "local-image-fixture",
                    "attachments": [],
                    "styleRef": None,
                    "isReference": False,
                    "spec": {"ratio": "1:1"},
                    "uploads": [image_asset],
                    "assetCardDraft": {"asset_type": "character", "label": "Lin Wan", "status": "draft"},
                    "humanGateDecisions": [
                        {
                            "human_gate_id": HUMAN_GATE_ID,
                            "target_type": "asset_card_candidate",
                            "target_id": ASSET_CARD_CANDIDATE_ID,
                            "decision": "accepted_for_next_step",
                            "status": "succeeded",
                            "recorded_at": "2026-06-30T22:05:00+08:00",
                            "writes_long_term_memory": False,
                        }
                    ],
                },
            }
        },
        "edges": {},
        "groups": {},
        "assets": [
            {
                "id": "asset_seed_image",
                "kind": "image_reference",
                "title": "Promotion source",
                "safe_summary": "promotion-source.png",
                "thumbnail_ref": "keyframe",
                "source_node_id": NODE_ID,
                "status": "ready",
                "asset_id": image_asset.get("asset_id"),
                "preview_url": image_asset.get("preview_url", ""),
                "created_at": "2026-06-30T22:00:00+08:00",
            }
        ],
        "order": [NODE_ID],
    }


def run_browser_qa(
    repo: Path,
    base_url: str,
    runtime_root: Path,
    seed: dict[str, Any],
    screenshot_path: Path,
    headed: bool,
    timeout_ms: int,
) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    project_id = str(seed["project_id"])
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(timeout_ms)
        expect.set_options(timeout=timeout_ms)
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on(
            "response",
            lambda response: response_errors.append({"status": response.status, "url": response.url})
            if response.status >= 400
            else None,
        )
        page.route("**/studio/src/**", make_studio_static_route(repo))
        page.route("**/studio/styles/**", make_studio_static_route(repo))
        page.route("**/projects/**", make_mutating_runtime_proxy(runtime_root))
        try:
            page.goto(f"{base_url}/studio/?project={project_id}&qa={int(time.time())}", wait_until="commit")
            expect(page.locator("#canvas-root")).to_be_visible()
            promote_seeded_node(page)

            client = runtime_test_client(runtime_root)
            record = fixed_visual_asset_record(runtime_root, project_id)
            detail = client.get(f"/projects/{project_id}/visual-assets/{record['asset_id']}")
            if detail.status_code != 200:
                raise AssertionError(f"visual asset detail failed: {detail.status_code} {detail.text}")
            public_asset = detail.json()["asset"]
            gate = assert_promotion_gate(record)
            serialized = json.dumps({"record": record, "public_asset": public_asset}, ensure_ascii=False).lower()
            if any(marker in serialized for marker in ("data_base64", "signed_url", "c:\\", "d:\\")):
                raise AssertionError("promotion browser QA leaked unsafe fields")
            page.wait_for_function("(key) => window.localStorage.getItem(key)?.includes('promotion_gate')", arg=STUDIO_STORAGE_KEY)
            page.screenshot(path=str(screenshot_path), full_page=True)
            actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
            if console_errors or actionable_response_errors:
                raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
            return {
                "artifact_type": "studio_visual_asset_promotion_browser_qa_report",
                "schema_version": "0.1.0",
                "status": "passed",
                "project_id": project_id,
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "screenshot": str(screenshot_path),
                "source_image_asset_id": seed["image_asset"]["asset_id"],
                "visual_asset_id": record["asset_id"],
                "promotion_gate": gate,
                "console_error_count": len(console_errors),
                "response_error_count": len(actionable_response_errors),
                "provider_calls_started": False,
                "browser_api_post_proxy": "fastapi_testclient",
                "non_claims": [
                    "browser/runtime verification only",
                    "not human creative acceptance",
                    "not business validation",
                    "not image/video live provider smoke",
                    "not deploy verification",
                ],
            }
        finally:
            browser.close()


def promote_seeded_node(page: Page) -> None:
    node = page.locator(f'.node[data-node-id="{NODE_ID}"]')
    expect(node).to_be_visible()
    node.hover()
    node.locator('[data-action="fix-visual-asset"]').click()
    panel = page.locator(".visual-asset-panel")
    expect(panel).to_be_visible()
    panel.locator('[data-field="label"]').fill("Lin Wan")
    panel.locator('[data-field="signature"]').fill("black short hair, red trench coat, left brow scar")
    panel.locator('[data-card="identity"]').fill("private investigator")
    panel.locator('[data-card="hair"]').fill("black short hair")
    panel.locator('[data-card="face"]').fill("left brow scar")
    panel.locator('[data-card="wardrobe"]').fill("red trench coat")
    panel.locator('[data-field="negative_locks"]').fill("keep black short hair\nkeep red trench coat\nkeep left brow scar")
    with page.expect_response(lambda r: "/visual-assets/promote" in r.url and r.request.method == "POST") as response:
        panel.locator('[data-action="fix"]').click()
    if response.value.status != 200:
        raise AssertionError(f"visual asset promote failed: {response.value.status} {response.value.text()}")
    expect(page.locator(".visual-asset-panel")).to_have_count(0)


def assert_promotion_gate(record: dict[str, Any]) -> dict[str, Any]:
    gate = record.get("promotion_gate")
    if not isinstance(gate, dict):
        raise AssertionError("visual asset record missing promotion_gate")
    expected = {
        "scope": "manual_fixed_asset_promotion",
        "source_contract": "runtime_human_gate_decision",
        "source_human_gate_id": EXPECTED_HUMAN_GATE_ID,
        "source_asset_card_candidate_id": EXPECTED_ASSET_CARD_CANDIDATE_ID,
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
    }
    if gate != expected:
        raise AssertionError(f"unexpected promotion gate: {gate}")
    for key in ("media_bytes_returned_by_api", "provider_raw_response_stored", "writes_long_term_memory", "writes_company_kb"):
        if record.get(key) is not False:
            raise AssertionError(f"visual asset record has unsafe {key}={record.get(key)!r}")
    return gate


if __name__ == "__main__":
    raise SystemExit(main())
