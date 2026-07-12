from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    make_mutating_runtime_proxy,
    make_studio_static_route,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)

PROJECT_ID = f"studio-quality-feedback-browser-qa-{int(time.time())}"
NODE_ID = "node-quality-feedback-source"


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-quality-feedback-browser-")).resolve()
    report_path = Path(args.report or repo / "runs" / "studio_quality_feedback_context_overlay_browser_qa.json").resolve()
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
    parser = argparse.ArgumentParser(description="Run deterministic Studio quality-feedback context-overlay browser QA.")
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


def storage_key(project_id: str) -> str:
    return f"afs_studio_canvas_v2:{project_id}"

def prepare_project(runtime_root: Path, *, project_id: str = PROJECT_ID) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    response = client.post("/projects", json={"project_id": project_id, "goal": "Studio quality feedback browser QA"})
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {response.status_code} {response.text}")
    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": seeded_studio_state(project_id)})
    if saved.status_code != 200:
        raise AssertionError(f"studio-state setup failed: {saved.status_code} {saved.text}")
    return {"project_id": project_id, "node_id": NODE_ID}


def seeded_studio_state(project_id: str) -> dict[str, Any]:
    return {
        "meta": {"projectId": project_id, "projectName": "Quality Feedback Browser QA", "canvasName": "QA Canvas", "seq": 1, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {
            NODE_ID: {
                "id": NODE_ID,
                "type": "image",
                "title": "Feedback source",
                "x": 520,
                "y": 320,
                "w": 300,
                "h": 260,
                "prompt": "Seeded keyframe for quality feedback context-overlay QA.",
                "content": "",
                "status": "complete",
                "result": "Seeded image result with visible continuity drift for feedback recording.",
                "previewUrl": "",
                "params": {
                    "model": "local-image-fixture",
                    "spec": {"ratio": "1:1"},
                    "attachments": [],
                },
            }
        },
        "edges": {},
        "groups": {},
        "assets": [],
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
        runtime_proxy = make_mutating_runtime_proxy(runtime_root)
        page.route("**/studio/src/**", make_studio_static_route(repo))
        page.route("**/studio/styles/**", make_studio_static_route(repo))
        page.route("**/feedback", runtime_proxy)
        page.route("**/projects/**", runtime_proxy)
        try:
            page.goto(f"{base_url}/studio/?project={project_id}&qa={int(time.time())}", wait_until="commit")
            expect(page.locator("#canvas-root")).to_be_visible()
            submit_quality_feedback(page, project_id)
            summary = wait_for_quality_feedback_summary(page, project_id)
            runtime_state_summary = wait_for_runtime_state_summary(runtime_root, project_id)
            artifacts = feedback_artifacts(runtime_root, project_id)
            assert_feedback_artifacts(artifacts, summary, runtime_state_summary)
            page.screenshot(path=str(screenshot_path), full_page=True)
            actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
            serialized = json.dumps({"summary": summary, "runtime_state": runtime_state_summary, "artifacts": artifacts}, ensure_ascii=False).lower()
            if console_errors or actionable_response_errors:
                raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
            if any(marker in serialized for marker in ('"provider_raw"', '"signed_url"', "data_base64", "d:\\private", "bearer secret")):
                raise AssertionError("quality-feedback browser QA leaked unsafe fields")
            return {
                "artifact_type": "studio_quality_feedback_context_overlay_browser_qa_report",
                "schema_version": "0.1.0",
                "status": "passed",
                "project_id": project_id,
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "screenshot": str(screenshot_path),
                "feedback_artifact_id": summary["feedback_artifact_id"],
                "candidate_id": summary["candidate_id"],
                "promotion_artifact_id": summary["promotion_artifact_id"],
                "context_overlay_id": summary["context_overlay_id"],
                "context_overlay_artifact_id": summary["context_overlay_artifact_id"],
                "manifest_feedback_ref_count": artifacts["manifest_feedback_ref_count"],
                "runtime_state_context_overlay_status": runtime_state_summary["status"],
                "console_error_count": len(console_errors),
                "response_error_count": len(actionable_response_errors),
                "provider_calls_started": False,
                "writes_long_term_memory": False,
                "writes_company_kb": False,
                "browser_api_post_proxy": "fastapi_testclient",
                "non_claims": [
                    "browser/runtime verification only",
                    "not provider smoke",
                    "not generated media evidence",
                    "not human creative acceptance",
                    "not business validation",
                    "not deploy verification",
                ],
            }
        finally:
            browser.close()


def submit_quality_feedback(page: Page, project_id: str) -> None:
    open_quality_feedback_menu(page, project_id)
    pop = page.locator(".quality-feedback-popover")
    expect(pop).to_be_visible()
    pop.locator('[data-feedback-metric="identity_similarity"]').select_option("4")
    pop.locator('[data-feedback-metric="scene_continuity"]').select_option("3")
    pop.locator("[data-feedback-notes]").fill("Use https://example.test/private and D:\\private\\asset.png only as redacted drift evidence.")
    pop.locator("[data-feedback-next-context]").check()
    with page.expect_response(lambda r: "/studio-state" in r.url and r.request.method == "PUT") as state_response, page.expect_response(
        lambda r: "/feedback-candidate-context-overlays" in r.url and r.request.method == "POST"
    ) as response:
        pop.locator(".quality-feedback-submit").click()
    if response.value.status != 200:
        raise AssertionError(f"feedback context overlay failed: {response.value.status} {response.value.text()}")
    expect(pop.locator(".quality-feedback-status")).to_contain_text("已记录")
    if state_response.value.status != 200:
        raise AssertionError(f"studio-state save failed: {state_response.value.status} {state_response.value.text()}")


def open_quality_feedback_menu(page: Page, project_id: str) -> None:
    key = storage_key(project_id)
    page.wait_for_function(
        "({ key, nodeId }) => JSON.parse(window.localStorage.getItem(key) || '{}')?.nodes?.[nodeId]",
        arg={"key": key, "nodeId": NODE_ID},
    )
    page.evaluate(
        """async ({ key, nodeId }) => {
            const mod = await import('/studio/src/panels/node-menu.js');
            const node = JSON.parse(window.localStorage.getItem(key)).nodes[nodeId];
            const anchor = document.querySelector(`.node[data-node-id="${nodeId}"] [data-action="node-menu"]`);
            mod.openQualityFeedbackMenu(node, anchor);
        }""",
        {"key": key, "nodeId": NODE_ID},
    )


def wait_for_quality_feedback_summary(page: Page, project_id: str) -> dict[str, Any]:
    key = storage_key(project_id)
    page.wait_for_function(
        """({ key, nodeId }) => {
            const state = JSON.parse(window.localStorage.getItem(key) || '{}');
            const items = state?.nodes?.[nodeId]?.params?.qualityFeedbackCandidates || [];
            return items.some((item) => item.status === 'context_overlay_recorded');
        }""",
        arg={"key": key, "nodeId": NODE_ID},
    )
    return page.evaluate(
        """({ key, nodeId }) => {
            const state = JSON.parse(window.localStorage.getItem(key) || '{}');
            return state.nodes[nodeId].params.qualityFeedbackCandidates.at(-1);
        }""",
        {"key": key, "nodeId": NODE_ID},
    )


def wait_for_runtime_state_summary(runtime_root: Path, project_id: str, timeout: float = 20.0) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(f"/projects/{project_id}/studio-state").json()
        items = payload.get("state", {}).get("nodes", {}).get(NODE_ID, {}).get("params", {}).get("qualityFeedbackCandidates", [])
        if items and items[-1].get("status") == "context_overlay_recorded":
            return items[-1]
        time.sleep(0.2)
    raise AssertionError("runtime studio-state did not persist qualityFeedbackCandidates")


def feedback_artifacts(runtime_root: Path, project_id: str) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    manifest = client.get(f"/projects/{project_id}/manifest").json()["manifest"]
    files = list((runtime_root / "feedback" / project_id).glob("*/*.json"))
    payloads = {path.name: json.loads(path.read_text(encoding="utf-8-sig")) for path in files}
    return {
        "manifest_feedback_ref_count": len(manifest.get("feedback_refs", [])),
        "feedback_event": payloads["runtime_feedback_event.json"],
        "promotion_decision": payloads["runtime_feedback_candidate_promotion_decision.json"],
        "context_overlay": payloads["runtime_feedback_candidate_context_overlay.json"],
    }


def assert_feedback_artifacts(artifacts: dict[str, Any], summary: dict[str, Any], runtime_state_summary: dict[str, Any]) -> None:
    event = artifacts["feedback_event"]
    promotion = artifacts["promotion_decision"]
    overlay = artifacts["context_overlay"]
    assert summary == runtime_state_summary
    assert artifacts["manifest_feedback_ref_count"] == 3
    assert event["feedback_candidate"]["candidate_id"] == summary["candidate_id"]
    assert promotion["decision"]["decision"] == "promote_to_context_overlay"
    assert promotion["decision"]["context_overlay_allowed"] is True
    assert promotion["writes_long_term_memory"] is False
    assert promotion["writes_company_kb"] is False
    assert overlay["overlay_id"] == summary["context_overlay_id"]
    assert overlay["overlay"]["candidate_included_in_context"] is True
    assert overlay["overlay"]["provider_calls_started"] is False
    assert overlay["writes_long_term_memory"] is False
    assert overlay["writes_company_kb"] is False
    assert summary["provider_calls_started"] is False
    assert summary["writes_long_term_memory"] is False
    assert summary["writes_company_kb"] is False


if __name__ == "__main__":
    raise SystemExit(main())
