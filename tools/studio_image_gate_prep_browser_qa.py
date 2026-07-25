from __future__ import annotations

import argparse
import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright

from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
from apps.api.runtime_store import RuntimeStore
from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    runtime_test_client,
    stop_runtime,
    wait_for_http,
)
from studio_m6_script_plan_asset_bible_browser_qa import (
    configure,
    start_runtime,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900})
PROJECT_ID = f"image-gate-browser-{int(time.time())}"


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(
        args.runtime_root or tempfile.mkdtemp(prefix="afs-image-gate-browser-")
    ).resolve()
    stamp = int(time.time())
    report_path = Path(
        args.report or f"/tmp/afs-image-gate-browser-{stamp}.json"
    ).resolve()
    screenshot_dir = Path(
        args.screenshot_dir or f"/tmp/afs-image-gate-browser-{stamp}-screens"
    ).resolve()
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
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
    parser = argparse.ArgumentParser(description="AFS single-image gate desktop browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


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
    results: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            page = browser.new_page(viewport=VIEWPORTS[0])
            configure(page, repo, timeout_ms, console_errors, response_errors)
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
                f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=image-gate",
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(".graph-canvas-status.ready")
            results["confirmed_graph"] = {
                "status": "ready",
                "canonical_assets": 3,
                "scenes": 1,
                "shots": 3,
            }
            results["asset_edit"] = asset_edit_flow(
                page,
                runtime_root,
                base_url,
                screenshot_dir,
                screenshots,
            )
            complete_and_lock_asset_bible(base_url)
            page.reload(wait_until="domcontentloaded")
            page.get_by_role("tab", name="资产 Bible").click()
            results["image_gate"] = image_gate_flow(page, screenshot_dir, screenshots)
            page.close()
        finally:
            browser.close()
    expected_conflicts = [
        item
        for item in response_errors
        if item["status"] == 422
        and item["url"].endswith("/m6/asset-bible/commands/confirm")
    ]
    actionable = [
        item
        for item in response_errors
        if not item["url"].endswith("/favicon.ico") and item not in expected_conflicts
    ]
    expected_console_errors = [
        item
        for item in console_errors
        if "Failed to load resource" in item and "422" in item
    ]
    unexpected_console_errors = [
        item for item in console_errors if item not in expected_console_errors
    ]
    if len(expected_conflicts) != 1 or len(expected_console_errors) != 1:
        raise AssertionError(
            "browser QA did not observe exactly one expected concurrent conflict"
        )
    if unexpected_console_errors or actionable:
        raise AssertionError(
            f"console={unexpected_console_errors[:5]} responses={actionable[:5]}"
        )
    if provider_routes:
        raise AssertionError(f"provider routes were requested: {provider_routes[:5]}")
    admission = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/image-admission")
    if int(admission.get("provider_dispatch_count") or 0) != 0:
        raise AssertionError("browser QA changed provider dispatch count")
    results["evidence"] = {
        "viewports": ["1920x1080", "1440x900"],
        "unexpected_console_errors": 0,
        "expected_concurrent_conflicts": 1,
        "provider_routes": 0,
        "provider_dispatch_count": 0,
        "external_cost_usd": admission.get("external_cost_usd"),
        "screenshots": screenshots,
    }
    return results


def seed_canonical_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post(
        "/projects",
        json={"project_id": PROJECT_ID, "goal": "首张图片准入浏览器验收"},
    )
    if created.status_code not in {200, 409}:
        raise AssertionError(created.text)
    saved = client.put(
        f"/projects/{PROJECT_ID}/studio-state",
        json={
            "state": {
                "meta": {
                    "projectId": PROJECT_ID,
                    "projectName": "首张图片准入验收",
                    "canvasName": "制作画布",
                    "seq": 1,
                    "updated_at": "",
                },
                "viewport": {"x": 0, "y": 0, "scale": 1},
                "nodes": {},
                "edges": {},
                "groups": {},
                "assets": [],
                "order": [],
                "selection": {"nodeIds": [], "edgeId": None},
                "production": {},
                "ui": {},
            }
        },
    )
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    graph_store = ProductionGraphStore(RuntimeStore(runtime_root))
    nodes = [
        {
            "node_id": "revision-current",
            "category": "revision",
            "metadata": {"source_digest": "a" * 64},
        },
        {
            "node_id": "character-north",
            "category": "entity",
            "metadata": {"display_name": "巡夜人·甲", "appearance": "深灰短发"},
        },
        {
            "node_id": "scene-repair",
            "category": "location",
            "metadata": {"name": "北侧检修站", "space": "夜间检修平台"},
        },
        {
            "node_id": "prop-calibrator",
            "category": "resource",
            "metadata": {
                "name": "六角校准器",
                "kind": "prop",
                "classification": "canonical_prop",
                "style": "磨砂金属",
            },
        },
        *[
            {
                "node_id": f"shot-{index}",
                "category": "unit",
                "metadata": {
                    "title": f"镜头 {index}",
                    "intent": f"完成检修动作 {index}",
                    "duration_seconds": 6,
                    "blocking": "巡夜人使用六角校准器检查设备",
                },
            }
            for index in range(1, 4)
        ],
    ]
    graph_store.append(
        PROJECT_ID,
        expected_version=0,
        idempotency_key="seed-image-gate-browser-truth",
        semantic_digest=canonical_digest({"seed": "image-gate-browser"}),
        events=[
            *[{"type": "node_upserted", "node": node} for node in nodes],
            *[
                {
                    "type": "relation_upserted",
                    "from_id": "revision-current",
                    "to_id": node_id,
                    "relation_type": "derived_from",
                }
                for node_id in (
                    "character-north",
                    "scene-repair",
                    "prop-calibrator",
                )
            ],
            *[
                {
                    "type": "relation_upserted",
                    "from_id": "scene-repair",
                    "to_id": f"shot-{index}",
                    "relation_type": "contains",
                }
                for index in range(1, 4)
            ],
            *[
                {
                    "type": "relation_upserted",
                    "from_id": asset_id,
                    "to_id": f"shot-{index}",
                    "relation_type": "required_by",
                }
                for asset_id in ("character-north", "prop-calibrator")
                for index in range(1, 4)
            ],
        ],
    )


def asset_edit_flow(
    page,
    runtime_root: Path,
    base_url: str,
    screenshot_dir: Path,
    screenshots: dict[str, str],
) -> dict[str, Any]:
    page.get_by_role("tab", name="资产 Bible").click()
    before = http_json(f"{base_url}/projects/{PROJECT_ID}/m5/sequence-workspace")
    page.locator(".studio-asset-bible").get_by_role(
        "button", name="识别资产候选"
    ).first.click()
    review = page.locator(".asset-bible-command-review")
    expect(review).to_be_visible()
    review.get_by_role("button", name="确认应用").click()
    expect(page.locator(".asset-bible-list")).to_be_visible()
    current = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
    if int(current["graph_version"]) <= int(before["graph_version"]):
        raise AssertionError("candidate confirmation did not advance graph version")
    target = next(
        item
        for item in current["asset_bible"]["assets"]
        if item["asset_type"] == "character"
    )
    page.get_by_role("button", name=target["display_name"], exact=False).first.click()
    visual_identity = "深灰短发、蓝灰工作外套、左袖银色识别条"
    positive_traits = "眼神专注、衣料纹理清晰"
    continuity = "工作外套与左袖识别条在本场保持一致"
    page.get_by_label("视觉身份", exact=True).fill(visual_identity)
    page.get_by_label("正向特征（顿号分隔）").fill(positive_traits)
    page.get_by_label("连续性状态（顿号分隔）").fill(continuity)
    page.get_by_role("button", name="预览编辑影响").click()
    review = page.locator(".asset-bible-command-review")
    expect(review).to_contain_text("影响 1 个资产")
    review.get_by_role("button", name="确认应用").click()
    expect(page.locator(".asset-bible-failure")).to_have_count(0)
    restored = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
    persisted = next(
        item
        for item in restored["asset_bible"]["assets"]
        if item["stable_id"] == target["stable_id"]
    )
    if (
        persisted["visual_identity"] != visual_identity
        or persisted["positive_traits"] != positive_traits.split("、")
        or persisted["continuity_states"][0]["label"] != continuity
    ):
        raise AssertionError("asset visual grounding did not persist")
    page.reload(wait_until="domcontentloaded")
    page.get_by_role("tab", name="资产 Bible").click()
    page.get_by_role("button", name=target["display_name"], exact=False).first.click()
    expect(page.locator(".asset-bible-detail")).to_contain_text(visual_identity)
    expect(page.locator(".asset-bible-detail").get_by_role("button", name="批准")).to_be_enabled()
    screenshots["asset-edit-refresh-1920x1080"] = str(
        (screenshot_dir / "asset-edit-refresh-1920x1080.png").resolve()
    )
    page.screenshot(path=screenshots["asset-edit-refresh-1920x1080"], full_page=True)

    concurrent_identity = visual_identity + "，右手佩戴黑色维修手套"
    page.get_by_label("视觉身份", exact=True).fill(concurrent_identity)
    page.get_by_role("button", name="预览编辑影响").click()
    graph_store = ProductionGraphStore(RuntimeStore(runtime_root))
    graph = graph_store.load(PROJECT_ID)
    graph_store.append(
        PROJECT_ID,
        expected_version=graph["version"],
        idempotency_key="browser-qa-concurrent-change",
        semantic_digest=canonical_digest({"browser_qa": "concurrent-change"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "browser-qa-unrelated-note",
                    "category": "resource",
                    "state": "active",
                    "metadata": {"kind": "browser_qa_concurrency_marker"},
                },
            }
        ],
    )
    page.locator(".asset-bible-command-review").get_by_role(
        "button", name="确认应用"
    ).click()
    failure = page.locator(".asset-bible-failure")
    expect(failure).to_contain_text("当前资产内容已保留")
    failure.get_by_role("button", name="重新预览同一命令").click()
    page.locator(".asset-bible-command-review").get_by_role(
        "button", name="确认应用"
    ).click()
    expect(page.locator(".asset-bible-failure")).to_have_count(0)
    recovered = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
    recovered_target = next(
        item
        for item in recovered["asset_bible"]["assets"]
        if item["stable_id"] == target["stable_id"]
    )
    if recovered_target["visual_identity"] != concurrent_identity:
        raise AssertionError("concurrent edit recovery did not persist the reviewed command")
    page.set_viewport_size(VIEWPORTS[1])
    screenshots["asset-edit-concurrency-recovery-1440x900"] = str(
        (screenshot_dir / "asset-edit-concurrency-recovery-1440x900.png").resolve()
    )
    page.screenshot(
        path=screenshots["asset-edit-concurrency-recovery-1440x900"],
        full_page=True,
    )
    return {
        "stale_sequence_projection_did_not_break_confirm": True,
        "visual_grounding_persisted": True,
        "refresh_restored_visual_grounding": True,
        "approve_enabled_after_refresh": True,
        "true_concurrent_change_failed_closed": True,
        "repreview_after_conflict_succeeded": True,
    }


def complete_and_lock_asset_bible(base_url: str) -> None:
    state = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
    for asset in state["asset_bible"]["assets"]:
        if asset.get("pending_fields"):
            confirm_asset_command(
                base_url,
                {
                    "type": "edit",
                    "target_id": asset["stable_id"],
                    "patch": {
                        "visual_identity": asset.get("visual_identity")
                        or f"{asset['display_name']} 的轮廓、材质与主色已确认",
                        "positive_traits": asset.get("positive_traits")
                        or [f"保持 {asset['display_name']} 的稳定辨识特征"],
                        "continuity_states": [
                            item.get("label")
                            for item in asset.get("continuity_states", [])
                            if item.get("label")
                        ]
                        or ["当前场次外观与持有物保持一致"],
                    },
                },
            )
        current = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
        refreshed = next(
            item
            for item in current["asset_bible"]["assets"]
            if item["stable_id"] == asset["stable_id"]
        )
        if refreshed["review_state"] != "approved":
            confirm_asset_command(
                base_url,
                {"type": "approve", "target_id": asset["stable_id"]},
            )
    confirm_asset_command(
        base_url,
        {
            "type": "set_art_direction",
            "art_direction": {
                "visual_style": "写实电影叙事",
                "medium": "电影摄影，真实皮肤、织物与金属质感",
                "palette": "低饱和蓝灰与暖色工作灯",
                "lighting": "柔和侧逆光，主体面部与关键道具清晰",
            },
        },
    )
    confirm_asset_command(base_url, {"type": "lock"})


def confirm_asset_command(base_url: str, command: dict[str, Any]) -> dict[str, Any]:
    current = http_json(f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible")
    request = {
        "asset_bible": current["asset_bible"],
        "authority_mode": current["authority_mode"],
        "command": command,
        "requested_at": "2026-07-26T00:00:00Z",
    }
    preview = http_post_json(
        f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible/commands/preview",
        request,
    )
    return http_post_json(
        f"{base_url}/projects/{PROJECT_ID}/m6/asset-bible/commands/confirm",
        {
            **request,
            "preview_digest": preview["preview_digest"],
            "command_id": preview["command_id"],
            "expected_graph_version": preview["expected_graph_version"],
        },
    )


def image_gate_flow(
    page,
    screenshot_dir: Path,
    screenshots: dict[str, str],
) -> dict[str, Any]:
    page.locator(".studio-asset-bible").get_by_role(
        "button", name="图片准入", exact=True
    ).click()
    panel = page.locator(".image-admission-panel")
    expect(panel).to_contain_text("准备首张图片")
    expect(panel).to_contain_text("创建首张图片清单")
    expect(panel).not_to_contain_text("九项代表集")
    panel.get_by_role("button", name="预览准入清单").click()
    review = panel.locator(".image-admission-review")
    expect(review).to_contain_text("现在仅供预览，确认后才会保存")
    review.get_by_role("button", name="确认").click()
    expect(panel).to_contain_text("本轮硬上限")
    expect(panel).to_contain_text("$0.0377 · 1 次")
    panel.get_by_role("button", name="预览锁定清单").click()
    panel.locator(".image-admission-review").get_by_role(
        "button", name="确认"
    ).click()
    expect(panel).to_contain_text("图片能力尚未开启")
    body = page.locator("body").inner_text()
    if any(
        marker in body
        for marker in (
            "schema_version",
            "manifest_id",
            "provider_service_id",
            "ProductionGraph",
        )
    ):
        raise AssertionError("image gate leaked internal identifiers into creator UI")
    screenshots["image-gate-locked-1440x900"] = str(
        (screenshot_dir / "image-gate-locked-1440x900.png").resolve()
    )
    page.screenshot(path=screenshots["image-gate-locked-1440x900"], full_page=True)
    return {
        "dynamic_first_image_list_visible": True,
        "single_dispatch_budget_visible": True,
        "preview_confirm_before_persistence": True,
        "image_gate_closed_without_dispatch": True,
        "internal_identifiers_absent": True,
    }


def http_json(url: str) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AssertionError(exc.read().decode("utf-8")) from exc


if __name__ == "__main__":
    raise SystemExit(main())
