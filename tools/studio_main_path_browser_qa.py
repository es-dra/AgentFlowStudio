from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    artifact_payload,
    chrome_path,
    free_port,
    make_mutating_runtime_proxy,
    make_studio_static_route,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)
from studio_delivery_readiness_gate import build_delivery_readiness
from studio_main_path_browser_qa_support import (
    ASSET_NODE_ID,
    SCRIPT_NODE_ID,
    assert_main_path_evidence,
    make_project_id,
    prepare_project,
    storage_key,
    unsafe_marker,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    args = parse_args()
    repo = REPO_ROOT
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-main-path-browser-")).resolve()
    report_path = Path(args.report or repo / "runs" / "studio_main_path_browser_qa.json").resolve()
    screenshot_path = resolve_screenshot_path(report_path, args.screenshot)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    seed = prepare_project(runtime_root, project_id=make_project_id(), repo=repo)
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
    parser = argparse.ArgumentParser(description="Run provider-closed Studio main-path browser QA.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def resolve_screenshot_path(report_path: Path, screenshot_arg: str) -> Path:
    return Path(screenshot_arg).resolve() if screenshot_arg else report_path.with_suffix(".png")


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
        browser = p.chromium.launch(headless=not headed, executable_path=chrome_path(), args=["--proxy-server=direct://", "--proxy-bypass-list=*"])
        page = browser.new_page(viewport={"width": 1440, "height": 950})
        page.set_default_timeout(timeout_ms)
        expect.set_options(timeout=timeout_ms)
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("response", lambda response: response_errors.append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
        page.route("**/studio/src/**", make_studio_static_route(repo))
        page.route("**/studio/styles/**", make_studio_static_route(repo))
        page.route("**/projects/**", make_mutating_runtime_proxy(runtime_root))
        try:
            page.goto(f"{base_url}/studio/?project={project_id}&qa={int(time.time())}", wait_until="commit")
            expect(page.locator("#canvas-root")).to_be_visible()
            wait_for_seeded_nodes(page, project_id)
            keyframe_id = create_keyframe_layer_from_script_menu(page, project_id, seed["script_node_id"])
            keyframe_layer = keyframe_layer_summary(page, project_id, keyframe_id)
            first = submit_keyframe_generation(page, project_id, keyframe_id)
            select_feedback_overlay_for_next_context(page, project_id, keyframe_id, seed["overlay_id"])
            second = submit_keyframe_generation(page, project_id, keyframe_id)

            client = runtime_test_client(runtime_root)
            plan = artifact_payload(client, second["generation"]["artifacts"]["keyframe_request_plan"]["artifact_id"])
            final_node = node_from_storage(page, project_id, keyframe_id)
            assert_main_path_evidence(seed, keyframe_layer, first, second, plan, final_node)
            page.screenshot(path=str(screenshot_path), full_page=True)
            studio_state_recovery = studio_state_conflict_recovery_evidence(client, project_id, keyframe_id, seed["overlay_id"], response_errors)
            ignored_errors = [item for item in response_errors if is_ignored_response_error(item, studio_state_recovery)]
            actionable_errors = [item for item in response_errors if item not in ignored_errors]
            actionable_console_errors = [item for item in console_errors if not is_ignored_console_error(item, ignored_errors, studio_state_recovery)]
            if actionable_console_errors or actionable_errors:
                raise AssertionError(f"console errors: {actionable_console_errors[:5]}; response errors: {actionable_errors[:5]}")
            report = {
                "artifact_type": "studio_main_path_browser_qa_report",
                "schema_version": "0.2.0",
                "status": "passed",
                "project_id": project_id,
                "case_id": seed["case_id"],
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "screenshot": str(screenshot_path),
                "keyframe_node_id": keyframe_id,
                "fixed_asset_id": seed["fixed_asset_id"],
                "production_graph_artifact_id": seed["production_graph_artifact_id"],
                "overlay_id": seed["overlay_id"],
                "first_bridge_artifact_id": first["generation"]["artifacts"]["keyframe_generation_bridge"]["artifact_id"],
                "second_bridge_artifact_id": second["generation"]["artifacts"]["keyframe_generation_bridge"]["artifact_id"],
                "second_request_plan_artifact_id": second["generation"]["artifacts"]["keyframe_request_plan"]["artifact_id"],
                "feedback_overlay_decision_recorded": True,
                "provider_calls_started": False,
                "console_error_count": len(actionable_console_errors),
                "response_error_count": len(actionable_errors),
                "studio_state_conflict_recovery": studio_state_recovery,
                "browser_api_post_proxy": "fastapi_testclient",
                "non_claims": [
                    "browser/runtime structure verification only",
                    "not provider smoke",
                    "not generated media evidence",
                    "not human creative acceptance",
                    "not business validation",
                    "not deploy verification",
                ],
            }
            report["delivery_readiness"] = build_delivery_readiness(report, seed)
            if unsafe_marker({"plan": plan, "final_node": final_node}):
                raise AssertionError("main-path browser QA leaked unsafe fields")
            return report
        finally:
            browser.close()


def wait_for_seeded_nodes(page: Page, project_id: str) -> None:
    page.wait_for_function(
        "({ key, scriptId, assetId }) => { const s = JSON.parse(localStorage.getItem(key) || '{}'); return s.nodes?.[scriptId] && s.nodes?.[assetId]; }",
        arg={"key": storage_key(project_id), "scriptId": SCRIPT_NODE_ID, "assetId": ASSET_NODE_ID},
    )
    expect(page.locator(f'.node[data-node-id="{SCRIPT_NODE_ID}"]')).to_be_visible()
    expect(page.locator(f'.node[data-node-id="{ASSET_NODE_ID}"]')).to_be_visible()


def create_keyframe_layer_from_script_menu(page: Page, project_id: str, script_node_id: str) -> str:
    node = page.locator(f'.node[data-node-id="{script_node_id}"]')
    expect(node).to_be_visible()
    node.hover()
    node.locator('[data-action="node-menu"]').click()
    items = page.locator(".popover .menu-item")
    expect(items.first).to_be_visible()
    texts = items.all_inner_texts()
    index = menu_index(texts, ("\u5173\u952e\u5e27", "keyframe"), fallback=5)
    items.nth(index).click()
    page.wait_for_function(
        """({ key, scriptId }) => Object.values(JSON.parse(localStorage.getItem(key) || '{}').nodes || {})
          .some((node) => node?.params?.nodeRole === 'keyframe_generation' && node?.params?.keyframeLayer?.source_script_node_id === scriptId)""",
        arg={"key": storage_key(project_id), "scriptId": script_node_id},
    )
    return page.evaluate(
        """({ key, scriptId }) => Object.values(JSON.parse(localStorage.getItem(key)).nodes)
          .find((node) => node?.params?.nodeRole === 'keyframe_generation' && node?.params?.keyframeLayer?.source_script_node_id === scriptId).id""",
        {"key": storage_key(project_id), "scriptId": script_node_id},
    )


def submit_keyframe_generation(page: Page, project_id: str, keyframe_id: str) -> dict[str, Any]:
    target = page.locator(f'.node[data-node-id="{keyframe_id}"]')
    expect(target).to_be_visible()
    target.hover()
    with page.expect_response(lambda r: "/keyframe-generations/preflight" in r.url and r.request.method == "POST") as preflight_response:
        target.locator('[data-action="run"]').click()
    if preflight_response.value.status != 200:
        raise AssertionError(f"keyframe preflight failed: {preflight_response.value.status} {preflight_response.value.text()}")
    expect(page.locator(".generation-carry-modal")).to_be_visible()
    with page.expect_request(lambda r: "/keyframe-generations" in r.url and not r.url.endswith("/preflight") and r.method == "POST") as request_info:
        with page.expect_response(lambda r: "/keyframe-generations" in r.url and not r.url.endswith("/preflight") and r.request.method == "POST") as response:
            page.locator(".generation-carry-modal .primary-btn").click()
    payload = response.value.json()
    request = json.loads(request_info.value.post_data or "{}")
    page.wait_for_function(
        "({ key, nodeId }) => Boolean(JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId]?.params?.lastGenerationBridge)",
        arg={"key": storage_key(project_id), "nodeId": keyframe_id},
    )
    return {"preflight": preflight_response.value.json(), "generation": payload, "request": request}


def select_feedback_overlay_for_next_context(page: Page, project_id: str, keyframe_id: str, overlay_id: str) -> None:
    page.evaluate(
        """async ({ projectId, nodeId }) => {
          const { createStore } = await import('/studio/src/store.js');
          const { openFeedbackOverlayReviewMenu } = await import('/studio/src/feedback-overlay-review.js');
          const store = createStore(projectId);
          const node = store.get().nodes[nodeId];
          const anchor = document.querySelector(`.node[data-node-id="${nodeId}"] [data-action="node-menu"]`);
          openFeedbackOverlayReviewMenu(store, node, anchor);
        }""",
        {"projectId": project_id, "nodeId": keyframe_id},
    )
    expect(page.locator(".human-gate-submit").first).to_be_visible()
    page.locator(".human-gate-submit").first.click()
    page.wait_for_function(
        """({ key, nodeId, overlayId }) => (JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId]?.params?.feedbackOverlayDecisions || [])
          .some((item) => item.overlay_id === overlayId && item.decision === 'include_for_next_context')""",
        arg={"key": storage_key(project_id), "nodeId": keyframe_id, "overlayId": overlay_id},
    )
    page.reload(wait_until="commit")
    expect(page.locator("#canvas-root")).to_be_visible()
    expect(page.locator(f'.node[data-node-id="{keyframe_id}"]')).to_be_visible()


def keyframe_layer_summary(page: Page, project_id: str, keyframe_id: str) -> dict[str, Any]:
    return node_from_storage(page, project_id, keyframe_id)["params"]["keyframeLayer"]


def node_from_storage(page: Page, project_id: str, node_id: str) -> dict[str, Any]:
    return page.evaluate(
        "({ key, nodeId }) => JSON.parse(localStorage.getItem(key)).nodes[nodeId]",
        {"key": storage_key(project_id), "nodeId": node_id},
    )


def menu_index(texts: list[str], needles: tuple[str, ...], *, fallback: int | None = None) -> int:
    for index, text in enumerate(texts):
        if any(needle in text for needle in needles):
            return index
    if fallback is not None and len(texts) > fallback:
        return fallback
    raise AssertionError(f"menu item not found in: {texts}")


def studio_state_conflict_recovery_evidence(
    client: Any, project_id: str, keyframe_id: str, overlay_id: str, response_errors: list[dict[str, Any]], *, timeout_seconds: float = 5.0
) -> dict[str, Any]:
    conflict_count = sum(1 for item in response_errors if is_studio_state_conflict(item))
    evidence = {
        "studio_state_conflict_count": conflict_count,
        "recovery_source": "",
        "recovery_status_code": 0,
        **studio_state_conflict_recovery_from_state({}, keyframe_id, overlay_id),
    }
    deadline = time.time() + timeout_seconds
    while conflict_count and time.time() <= deadline:
        response = client.get(f"/projects/{project_id}/studio-state")
        evidence["recovery_status_code"] = response.status_code
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            evidence["recovery_source"] = str(payload.get("source", "")) if isinstance(payload, dict) else ""
            evidence.update(studio_state_conflict_recovery_from_state(payload.get("state") if isinstance(payload, dict) else None, keyframe_id, overlay_id))
            if evidence["studio_state_conflict_recovered"]:
                break
        time.sleep(0.2)
    return evidence


def studio_state_conflict_recovery_from_state(state: Any, keyframe_id: str, overlay_id: str) -> dict[str, Any]:
    nodes = state.get("nodes") if isinstance(state, dict) else {}
    node = nodes.get(keyframe_id) if isinstance(nodes, dict) else {}
    params = node.get("params") if isinstance(node, dict) and isinstance(node.get("params"), dict) else {}
    decisions = params.get("feedbackOverlayDecisions") if isinstance(params.get("feedbackOverlayDecisions"), list) else ()
    saved_decision = any(isinstance(item, dict) and item.get("overlay_id") == overlay_id and item.get("decision") == "include_for_next_context" for item in decisions)
    saved_job_id = str(params.get("lastKeyframeJobId") or "")
    saved_layer = isinstance(params.get("keyframeLayer"), dict)
    saved_node_id = str(node.get("id") or "") if isinstance(node, dict) else ""
    return {
        "studio_state_conflict_recovered": bool(saved_node_id == keyframe_id and saved_job_id and saved_decision and saved_layer),
        "saved_keyframe_node_id": saved_node_id,
        "saved_keyframe_job_id": saved_job_id,
        "saved_feedback_overlay_decision": saved_decision,
        "saved_keyframe_layer": saved_layer,
    }


def is_studio_state_conflict(item: dict[str, Any]) -> bool:
    return item.get("status") == 409 and "/studio-state" in str(item.get("url", ""))


def is_ignored_response_error(item: dict[str, Any], recovery_evidence: dict[str, Any] | None = None) -> bool:
    url = str(item.get("url", ""))
    if url.endswith("/favicon.ico"):
        return True
    return is_studio_state_conflict(item) and bool((recovery_evidence or {}).get("studio_state_conflict_recovered"))


def is_ignored_console_error(text: str, ignored_response_errors: list[dict[str, Any]], recovery_evidence: dict[str, Any] | None = None) -> bool:
    has_ignored_studio_conflict = any(is_studio_state_conflict(item) for item in ignored_response_errors)
    return bool((recovery_evidence or {}).get("studio_state_conflict_recovered")) and has_ignored_studio_conflict and "Failed to load resource" in text and "409 (Conflict)" in text


if __name__ == "__main__":
    raise SystemExit(main())
