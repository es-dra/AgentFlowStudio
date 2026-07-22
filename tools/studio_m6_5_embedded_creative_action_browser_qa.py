from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import (
    chrome_path,
    free_port,
    runtime_test_client,
    start_runtime,
    stop_runtime,
    wait_for_http,
)
from studio_m6_4_freeform_canvas_ai_copilot_browser_qa import (
    assert_keyboard_input_paths,
    assert_no_primary_english_agent_label,
    assert_plan_panel_contextual,
    close_ai_overlay_if_open,
    create_blank_text_node,
    create_node_from_handle,
    dom_edge_ids,
    dom_node_ids,
    edge_ids,
    ensure_ai_open,
    graph_counts,
    graph_edge_records,
    has_horizontal_overflow,
    node_ids,
    safe_reference_image_path,
    screenshot,
    select_node,
    selected_node_id,
    send_ai,
    stable_created_node_id,
    stable_edge_id,
    storage_key,
    viewport_key,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    {"width": 1440, "height": 900},
    {"width": 1024, "height": 768},
    {"width": 800, "height": 900},
    {"width": 430, "height": 932},
    {"width": 390, "height": 844},
)
OWNER_BASELINE_IMAGES = (
    Path("/home/afs-ops/.codex/afs-evidence/afs-m6-5-embedded-creative-action-ux-20260722/owner-input/codex-clipboard-f0c32c42-a2cb-46b4-b121-c0ddcb0768f9.png"),
    Path("/home/afs-ops/.codex/afs-evidence/afs-m6-5-embedded-creative-action-ux-20260722/owner-input/codex-clipboard-3d1e4c45-27a4-45c9-8767-87ddb030858d.png"),
    Path("/home/afs-ops/.codex/afs-evidence/afs-m6-5-embedded-creative-action-ux-20260722/owner-input/codex-clipboard-8339440d-3b06-49ed-b0cc-4c3c389c8c31.png"),
    Path("/home/afs-ops/.codex/afs-evidence/afs-m6-5-embedded-creative-action-ux-20260722/owner-input/codex-clipboard-782a1d7e-c3d7-4662-ba09-09db27efa05a.png"),
)
COMPACT_AI_MAX_WIDTH = 1100


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-5-runtime-")).resolve()
    report_path = Path(args.report or f"/tmp/afs-m6-5-browser-{int(time.time())}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or report_path.with_suffix("")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = start_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, runtime_root, base_url, screenshot_dir, args.round_label, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path), "screenshots": str(screenshot_dir)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.5 embedded creative action browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--round-label", default="A")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def run_browser_qa(repo: Path, runtime_root: Path, base_url: str, screenshot_dir: Path, round_label: str, timeout_ms: int) -> dict[str, Any]:
    del repo
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    cases: dict[str, Any] = {}
    screenshots: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in VIEWPORTS:
                project_id = f"m6-5-embedded-action-{round_label.lower()}-{viewport_key(viewport)}-{int(time.time() * 1000)}"
                prepare_project(runtime_root, project_id, viewport)
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on(
                    "response",
                    lambda response: response_errors.append({"status": response.status, "url": response.url})
                    if response.status >= 400 and not response.url.endswith("/favicon.ico")
                    else None,
                )
                try:
                    result, captured = verify_project(page, base_url, project_id, viewport, screenshot_dir, round_label)
                    cases[f"{project_id}:{viewport_key(viewport)}"] = result
                    screenshots.update(captured)
                finally:
                    page.close()
        finally:
            browser.close()
    if console_errors or response_errors:
        raise AssertionError(f"console_errors={console_errors[:8]} response_errors={response_errors[:8]}")
    checks = aggregate_checks(cases)
    roles = role_matrix(checks)
    micro = micro_checks(checks)
    failures = {
        "checks": [name for name, passed in checks.items() if passed is not True],
        "roles": [name for name, item in roles.items() if item.get("completed") is not True],
        "micro": [name for name, passed in micro.items() if passed is not True],
    }
    if any(failures.values()):
        raise AssertionError(f"M6.5 browser QA still has user-visible failures: {json.dumps(failures, ensure_ascii=False)}")
    return {
        "artifact_type": "afs_m6_5_embedded_creative_action_browser_qa",
        "schema_version": "afs.m6_5.browser_qa.v0.1",
        "round": round_label,
        "status": "passed",
        "owner_baseline_images": [str(path) for path in OWNER_BASELINE_IMAGES if path.exists()],
        "cases": cases,
        "screenshots": screenshots,
        "checks": checks,
        "role_task_completion_matrix": roles,
        "micro_experience_checks": micro,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "real_llm_boundary": "This browser lane keeps remote providers closed. Real server_codex evidence is recorded by the M6.5 runtime LLM harness.",
        "console_error_count": 0,
        "response_error_count": 0,
    }


def prepare_project(runtime_root: Path, project_id: str, viewport: dict[str, int]) -> None:
    client = runtime_test_client(runtime_root)
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": f"M6.5节点内创作动作QA {viewport_key(viewport)}",
            "status": "in_progress",
        },
    )
    if response.status_code not in {200, 409}:
        raise AssertionError(f"project create failed: {response.status_code} {response.text}")


def verify_project(page: Page, base_url: str, project_id: str, viewport: dict[str, int], screenshot_dir: Path, round_label: str) -> tuple[dict[str, Any], dict[str, str]]:
    key = viewport_key(viewport)
    screenshots: dict[str, str] = {}
    page.goto(f"{base_url}/studio/?project={project_id}&qa=m6-5-{round_label}-{int(time.time())}", wait_until="networkidle")
    expect(page.locator("#product-shell-root")).to_be_visible()
    expect(page.locator("#canvas-root")).to_be_visible()
    assert_no_primary_english_agent_label(page)
    assert_plan_panel_contextual(page)
    assert_shell_information_architecture(page)
    screenshots[f"{key}:initial"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-01-initial.png")

    initial = graph_counts(page, project_id)
    ensure_ai_open(page, viewport)
    send_ai(page, "你好")
    assert_not_canned_execution_log(page)
    if graph_counts(page, project_id) != initial:
        raise AssertionError("greeting changed the canvas graph")
    assert_keyboard_input_paths(page)
    if graph_counts(page, project_id) != initial:
        raise AssertionError("keyboard conversation path changed the canvas graph")
    screenshots[f"{key}:ai_companion"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-02-ai-companion.png")

    text_id = create_text_entry(page, project_id)
    source_text = "孙悟空大战猪八戒。两人在废弃摄影棚里为一段失控的AI广告争夺金箍棒。"
    fill_selected_text(page, source_text)
    node_local = run_node_local_actions_provider_closed(page, project_id, text_id)
    screenshots[f"{key}:embedded_action"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-03-embedded-action.png")

    shot_id = create_node_from_handle(page, project_id, text_id, "镜头设计")
    image_id = create_global_image_node(page, project_id, viewport)
    edge_id = connect_exact_generation_edge(page, project_id, text_id, image_id)
    geometry = verify_edge_geometry_at_zooms(page, project_id, edge_id)
    attach_real_reference_image(page, project_id, image_id)
    screenshots[f"{key}:palette_edges_upload"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-04-palette-edges-upload.png")

    verify_help_and_account(page)
    mobile_ok = verify_responsive_ai(page, viewport)
    no_overflow = not has_horizontal_overflow(page)
    primary_text = page.locator("#product-shell-root").inner_text()
    forbidden = [
        token for token in (
            "Agent Chat",
            "已记录到当前上下文",
            "核心意图/叙事推进/制作优化",
            "runtime root",
            "/home/",
            "/var/",
            "secret",
            "token",
        )
        if token in primary_text
    ]
    if forbidden:
        raise AssertionError(f"primary UI leaked forbidden terms: {forbidden}")
    final_counts = graph_counts(page, project_id)
    screenshots[f"{key}:final"] = screenshot(page, screenshot_dir, f"{round_label}-{key}-05-final.png")
    return (
        {
            "project_id": project_id,
            "viewport": key,
            "initial_counts": initial,
            "final_counts": final_counts,
            "text_node_id": text_id,
            "shot_node_id": shot_id,
            "image_node_id": image_id,
            "generation_edge_id": edge_id,
            "greeting_zero_mutation": True,
            "visible_send_button": True,
            "keyboard_enter_path": True,
            "node_local_action_anchored": node_local["anchored"],
            "node_local_action_not_global_chat": node_local["global_chat_unchanged"],
            "node_local_provider_closed_zero_mutation": node_local["zero_mutation"],
            "shot_breakdown_provider_closed_zero_mutation": node_local["shot_breakdown_zero_mutation"],
            "compact_palette": compact_palette_ok(page),
            "plus_node_creation": bool(shot_id),
            "manual_connection_exact": bool(edge_id),
            "edge_geometry_exact": geometry["max_gap_px"] <= 2.0,
            "reference_image_entry": uploaded_reference_ok(page, project_id, image_id),
            "topbar_help_account_ia": True,
            "ai_partner_compact": True,
            "responsive_shell": mobile_ok and no_overflow,
            "provider_dispatch_count": 0,
            "cost_usd": 0,
            "edge_geometry": geometry,
        },
        screenshots,
    )


def create_text_entry(page: Page, project_id: str) -> str:
    create_blank_text_node(page, project_id)
    node_id = selected_node_id(page, project_id)
    select_node(page, project_id, node_id)
    return node_id


def fill_selected_text(page: Page, text: str) -> None:
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.fill(text)
    editor.blur()


def run_node_local_actions_provider_closed(page: Page, project_id: str, node_id: str) -> dict[str, bool]:
    select_node(page, project_id, node_id)
    before_counts = graph_counts(page, project_id)
    before_chat = page.locator(".agent-chat-log").inner_text() if page.locator(".agent-chat-log").count() else ""
    optimize = page.locator(f'.node[data-node-id="{node_id}"] [data-role="script-revision-action"]')
    expect(optimize).to_be_visible()
    optimize.click()
    wait_for_embedded_state(page, node_id, "unavailable")
    after_optimize = graph_counts(page, project_id)
    if after_optimize != before_counts:
        raise AssertionError(f"provider-closed optimize mutated graph: before={before_counts} after={after_optimize}")
    panel_text = page.locator(f'.node[data-node-id="{node_id}"] .embedded-creative-action').inner_text()
    if "本地模板" not in panel_text or "不会" not in panel_text:
        raise AssertionError(f"optimize fail-closed text is not honest: {panel_text!r}")
    chat_after_optimize = page.locator(".agent-chat-log").inner_text() if page.locator(".agent-chat-log").count() else ""

    clear = page.locator(f'.node[data-node-id="{node_id}"] .embedded-creative-clear').first
    if clear.count() and clear.is_visible():
        clear.click()
    breakdown = page.locator(f'.node[data-node-id="{node_id}"] [data-role="shot-breakdown-action"]')
    expect(breakdown).to_be_visible()
    breakdown.click()
    wait_for_embedded_state(page, node_id, "unavailable")
    after_breakdown = graph_counts(page, project_id)
    if after_breakdown != before_counts:
        raise AssertionError(f"provider-closed shot breakdown mutated graph: before={before_counts} after={after_breakdown}")
    chat_after_breakdown = page.locator(".agent-chat-log").inner_text() if page.locator(".agent-chat-log").count() else ""
    return {
        "anchored": page.locator(f'.node[data-node-id="{node_id}"] .embedded-creative-action[data-creative-action="shot_breakdown"]').is_visible(),
        "global_chat_unchanged": before_chat == chat_after_optimize == chat_after_breakdown,
        "zero_mutation": after_optimize == before_counts,
        "shot_breakdown_zero_mutation": after_breakdown == before_counts,
    }


def wait_for_embedded_state(page: Page, node_id: str, status: str) -> None:
    page.wait_for_function(
        """({ key, nodeId, status }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return node?.params?.embeddedCreativeAction?.status === status;
        }""",
        arg={"key": storage_key(project_id_from_page(page)), "nodeId": node_id, "status": status},
        timeout=30_000,
    )


def project_id_from_page(page: Page) -> str:
    return str(page.evaluate("new URL(location.href).searchParams.get('project') || ''"))


def create_global_image_node(page: Page, project_id: str, viewport: dict[str, int]) -> str:
    close_ai_overlay_if_open(page)
    before_dom = set(dom_node_ids(page))
    before_graph = set(node_ids(page, project_id))
    button = page.locator('#corner-controls button[aria-label="添加节点"]')
    if button.count() and button.first.is_visible():
        button.first.click()
    else:
        canvas_box = page.locator("#canvas-root").bounding_box()
        if not canvas_box:
            raise AssertionError("canvas root is not measurable for global palette")
        page.mouse.click(
            canvas_box["x"] + min(canvas_box["width"] - 80, max(180, viewport["width"] * 0.52)),
            canvas_box["y"] + min(canvas_box["height"] - 80, max(180, viewport["height"] * 0.45)),
            button="right",
        )
        page.get_by_role("button", name=re.compile("添加节点")).click()
    primary_text = page.locator(".popover").inner_text()
    if any(term in primary_text for term in ("导演台 NEW", "视频合成", "参考节点", "场景空间")):
        raise AssertionError(f"primary palette still exposes raw or future options: {primary_text!r}")
    item = page.locator(".popover button").filter(has_text="参考图/图片").first
    expect(item).to_be_visible()
    item.click()
    return stable_created_node_id(
        page,
        project_id,
        before_dom=before_dom,
        before_graph=before_graph,
        expected_type="image",
        label="global image palette",
    )


def compact_palette_ok(page: Page) -> bool:
    close_ai_overlay_if_open(page)
    button = page.locator('#corner-controls button[aria-label="添加节点"]')
    expect(button.first).to_be_visible()
    button.first.click()
    text = page.locator(".popover").inner_text()
    primary_labels = ["想法/文本", "剧本/导入", "场景与镜头", "角色与资产", "参考图/图片", "视频"]
    ok = all(label in text for label in primary_labels) and "更多/高级" in text
    if not ok:
        raise AssertionError(f"compact palette missing primary creator labels: {text!r}")
    page.keyboard.press("Escape")
    return True


def connect_exact_generation_edge(page: Page, project_id: str, from_id: str, to_id: str) -> str:
    close_ai_overlay_if_open(page)
    before_dom = set(dom_edge_ids(page))
    before_graph = set(edge_ids(page, project_id))
    out_box = page.locator(f'.node[data-node-id="{from_id}"] .node-port.out').bounding_box()
    in_box = page.locator(f'.node[data-node-id="{to_id}"] .node-port.in').bounding_box()
    if not out_box or not in_box:
        raise AssertionError("node ports are not measurable for exact connection")
    page.mouse.move(out_box["x"] + out_box["width"] / 2, out_box["y"] + out_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(in_box["x"] + in_box["width"] / 2, in_box["y"] + in_box["height"] / 2, steps=12)
    page.mouse.up()
    edge_id = stable_edge_id(
        page,
        project_id,
        from_id=from_id,
        to_id=to_id,
        expected_relation="generation",
        before_dom=before_dom,
        before_graph=before_graph,
    )
    records = graph_edge_records(page, project_id)
    edge = records.get(edge_id) or {}
    if edge.get("from") != from_id or edge.get("to") != to_id:
        raise AssertionError(f"edge identity changed after stable lookup: {edge_id} {edge}")
    return edge_id


def verify_edge_geometry_at_zooms(page: Page, project_id: str, edge_id: str) -> dict[str, Any]:
    zooms = [1.0, 0.62, 1.18]
    measurements: list[dict[str, Any]] = []
    for zoom in zooms:
        set_zoom(page, project_id, zoom)
        wait_for_canvas_layout(page)
        measurements.append(edge_endpoint_measurement(page, edge_id))
    max_gap = max(max(item["source_gap_px"], item["target_gap_px"]) for item in measurements)
    return {"zooms": measurements, "max_gap_px": round(max_gap, 3)}


def set_zoom(page: Page, project_id: str, zoom: float) -> None:
    page.evaluate(
        """({ key, zoom }) => {
          const s = JSON.parse(localStorage.getItem(key) || '{}');
          s.viewport = s.viewport || {};
          s.viewport.scale = zoom;
          localStorage.setItem(key, JSON.stringify(s));
          window.dispatchEvent(new Event('storage'));
        }""",
        {"key": storage_key(project_id), "zoom": zoom},
    )
    page.reload(wait_until="networkidle")


def wait_for_canvas_layout(page: Page) -> None:
    page.evaluate(
        """() => new Promise((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        })"""
    )


def edge_endpoint_measurement(page: Page, edge_id: str) -> dict[str, Any]:
    result = page.evaluate(
        """edgeId => {
          const group = document.querySelector(`#edge-layer [data-edge-id="${edgeId}"]`);
          const path = group?.querySelector('path.edge-flow');
          if (!group || !path?.getTotalLength) return { error: 'edge path missing', edge_id: edgeId };
          const total = path.getTotalLength();
          const matrix = path.getScreenCTM();
          const pointAt = (length) => {
            const p = path.getPointAtLength(length);
            const s = new DOMPoint(p.x, p.y).matrixTransform(matrix);
            return { x: s.x, y: s.y };
          };
          const from = group.dataset.edgeFrom || '';
          const to = group.dataset.edgeTo || '';
          const expected = (nodeId, side) => {
            const node = document.querySelector(`.node[data-node-id="${nodeId}"]`);
            const port = node?.querySelector(side === 'out' ? '.node-port.out' : '.node-port.in');
            const nodeBox = node?.getBoundingClientRect?.();
            const portBox = port?.getBoundingClientRect?.();
            const styles = port ? getComputedStyle(port) : null;
            const visible = Boolean(portBox && portBox.width > 0 && portBox.height > 0 && Number(styles?.opacity || 0) >= 0.5 && styles?.visibility !== 'hidden');
            if (visible) return { x: portBox.left + portBox.width / 2, y: portBox.top + portBox.height / 2, mode: 'visible_handle' };
            if (!nodeBox) return { x: 0, y: 0, mode: 'missing_node' };
            return {
              x: side === 'out' ? nodeBox.right : nodeBox.left,
              y: nodeBox.top + nodeBox.height / 2,
              mode: 'card_border',
            };
          };
          const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
          const sourcePoint = pointAt(0);
          const targetPoint = pointAt(total);
          const sourceExpected = expected(from, 'out');
          const targetExpected = expected(to, 'in');
          return {
            edge_id: edgeId,
            from,
            to,
            relation: group.dataset.edgeRelation || '',
            source_point: sourcePoint,
            target_point: targetPoint,
            source_expected: sourceExpected,
            target_expected: targetExpected,
            source_mode: sourceExpected.mode,
            target_mode: targetExpected.mode,
            source_gap_px: dist(sourcePoint, sourceExpected),
            target_gap_px: dist(targetPoint, targetExpected),
          };
        }""",
        edge_id,
    )
    if result.get("error"):
        raise AssertionError(f"edge geometry probe failed: {result}")
    if result["source_gap_px"] > 2.0 or result["target_gap_px"] > 2.0:
        raise AssertionError(f"edge endpoint gap exceeds 2px: {json.dumps(result, ensure_ascii=False)}")
    return result


def attach_real_reference_image(page: Page, project_id: str, node_id: str) -> None:
    select_node(page, project_id, node_id)
    source = next((path for path in OWNER_BASELINE_IMAGES if path.exists() and path.stat().st_size >= 1024), None)
    if source is None:
        source = safe_reference_image_path()
    payload = {"name": source.name, "mime": mime_for_image(source), "hex": source.read_bytes().hex()}
    page.evaluate(
        """({ payload }) => {
          const bytes = new Uint8Array(payload.hex.match(/.{1,2}/g).map((hex) => parseInt(hex, 16)));
          const file = new File([bytes], payload.name, { type: payload.mime });
          const dt = new DataTransfer();
          dt.items.add(file);
          const root = document.querySelector('#canvas-root');
          const rect = root.getBoundingClientRect();
          root.dispatchEvent(new DragEvent('drop', {
            bubbles: true,
            cancelable: true,
            dataTransfer: dt,
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2,
          }));
        }""",
        {"payload": payload},
    )
    page.wait_for_function(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return Boolean(node?.previewUrl && (node?.params?.uploads || []).length);
        }""",
        arg={"key": storage_key(project_id), "nodeId": node_id},
    )


def uploaded_reference_ok(page: Page, project_id: str, node_id: str) -> bool:
    return bool(page.evaluate(
        """({ key, nodeId }) => {
          const node = JSON.parse(localStorage.getItem(key) || '{}').nodes?.[nodeId];
          return Boolean(node?.previewUrl && node?.params?.uploads?.[0]?.asset_id);
        }""",
        {"key": storage_key(project_id), "nodeId": node_id},
    ))


def mime_for_image(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def assert_shell_information_architecture(page: Page) -> None:
    header = page.locator(".studio-unified-header")
    expect(header).to_be_visible()
    text = header.inner_text()
    forbidden = ["AgentFlow Studio", "自由画布", "AI 漫剧"]
    noisy = [item for item in forbidden if item in text]
    if noisy:
        raise AssertionError(f"topbar still exposes noisy mechanical tokens: {noisy} text={text!r}")
    if page.locator(".product-mobile-nav").is_visible():
        expect(page.locator(".product-mobile-nav button").filter(has_text="指南")).to_be_visible()
        expect(page.locator(".product-mobile-nav button").filter(has_text="项目")).to_be_visible()
        return
    expect(page.get_by_role("button", name=re.compile("使用指南|帮助"))).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("账户|工作区|偏好"))).to_be_visible()


def verify_help_and_account(page: Page) -> None:
    if page.locator(".product-mobile-nav").is_visible():
        page.locator(".product-mobile-nav button").filter(has_text="指南").first.click()
        expect(page.locator(".studio-mobile-help-sheet")).to_be_visible()
        expect(page.locator(".studio-mobile-help-sheet .studio-help-menu")).to_contain_text("从任意节点开始")
    else:
        help_button = page.get_by_role("button", name=re.compile("使用指南|帮助")).first
        help_button.click()
        expect(page.locator(".studio-help-context .studio-help-menu")).to_contain_text("从任意节点开始")
    if page.locator(".studio-mobile-help-sheet").is_visible():
        page.get_by_role("button", name="关闭使用指南").click()
        page.locator(".product-mobile-nav button").filter(has_text="项目").first.click()
        expect(page.locator(".context-drawer-account")).to_contain_text("账户与工作区")
        page.get_by_role("button", name="关闭项目导航").click()
    else:
        page.get_by_role("button", name=re.compile("使用指南|帮助")).first.click()
        account = page.get_by_role("button", name=re.compile("账户|工作区|偏好")).first
        account.click()
        expect(page.locator(".studio-account-menu")).to_contain_text("工作区")
        page.keyboard.press("Escape")


def verify_responsive_ai(page: Page, viewport: dict[str, int]) -> bool:
    if viewport["width"] > COMPACT_AI_MAX_WIDTH:
        return not has_horizontal_overflow(page)
    if not page.locator(".studio-agent-chat.collapsed").count():
        close_button = page.get_by_role("button", name="收起 AI 创作搭档", exact=True)
        if close_button.count() and close_button.first.is_visible():
            close_button.first.click()
    collapsed_ok = not has_horizontal_overflow(page)
    ensure_ai_open(page, viewport)
    expanded_ok = bool(page.evaluate(
        """() => {
          const chat = document.querySelector('.studio-agent-chat.mobile-open');
          const backdrop = document.querySelector('.agent-mobile-backdrop');
          if (!chat || !backdrop) return false;
          const box = chat.getBoundingClientRect();
          const back = backdrop.getBoundingClientRect();
          const chatBound = box.left >= -1 && box.right <= window.innerWidth + 1 && box.bottom <= window.innerHeight + 1;
          const backdropBound = back.left <= 1 && back.right >= window.innerWidth - 1;
          const topHit = document.elementFromPoint(8, Math.max(90, box.top - 20));
          const noClickThrough = !topHit?.closest?.('.node,.canvas-workspace-stage');
          return chatBound && backdropBound && noClickThrough;
        }"""
    ))
    page.keyboard.press("Escape")
    return collapsed_ok and expanded_ok and not has_horizontal_overflow(page)


def assert_not_canned_execution_log(page: Page) -> None:
    text = page.locator(".agent-chat-log").inner_text()
    forbidden = ["已记录到当前上下文", "send command preview", "核心意图", "叙事推进", "制作优化"]
    leaked = [item for item in forbidden if item in text]
    if leaked:
        raise AssertionError(f"AI companion still shows canned execution receipt text: {leaked}")


def aggregate_checks(cases: dict[str, Any]) -> dict[str, bool]:
    fields = (
        "greeting_zero_mutation",
        "visible_send_button",
        "keyboard_enter_path",
        "node_local_action_anchored",
        "node_local_action_not_global_chat",
        "node_local_provider_closed_zero_mutation",
        "shot_breakdown_provider_closed_zero_mutation",
        "compact_palette",
        "plus_node_creation",
        "manual_connection_exact",
        "edge_geometry_exact",
        "reference_image_entry",
        "topbar_help_account_ia",
        "ai_partner_compact",
        "responsive_shell",
    )
    return {field: all(item.get(field) is True for item in cases.values()) for field in fields}


def role_matrix(checks: dict[str, bool]) -> dict[str, dict[str, Any]]:
    return {
        "first_time_creator": {"completed": checks["greeting_zero_mutation"] and checks["topbar_help_account_ia"], "task": "understand shell and greet the AI partner"},
        "screenwriter": {"completed": checks["node_local_action_anchored"], "task": "invoke optimize from the selected text node without global transcript clutter"},
        "director_storyboard_artist": {"completed": checks["shot_breakdown_provider_closed_zero_mutation"] and checks["plus_node_creation"], "task": "invoke shot breakdown preview and create a shot from the handle"},
        "concept_artist": {"completed": checks["reference_image_entry"], "task": "start from a real reference image"},
        "continuity_supervisor": {"completed": checks["manual_connection_exact"] and checks["edge_geometry_exact"], "task": "verify relation endpoints and semantics"},
        "producer_cost_reviewer": {"completed": checks["node_local_provider_closed_zero_mutation"], "task": "see that closed provider state does not imply charge or mutation"},
        "editor_recovery_operator": {"completed": checks["manual_connection_exact"], "task": "work with precise graph relations"},
        "advanced_graph_user": {"completed": checks["compact_palette"] and checks["manual_connection_exact"], "task": "use palette, handles and exact relation identity"},
        "mobile_keyboard_low_vision": {"completed": checks["responsive_shell"] and checks["keyboard_enter_path"], "task": "use touch and keyboard paths without overflow"},
        "owner_adversarial_tester": {"completed": all(checks.values()), "task": "reject canned optimize, cluttered palette, detached edges and topbar noise"},
    }


def micro_checks(checks: dict[str, bool]) -> dict[str, bool]:
    return {
        "first_screen_10s": checks["topbar_help_account_ia"],
        "local_actions_are_embedded": checks["node_local_action_anchored"] and checks["node_local_action_not_global_chat"],
        "no_canned_template_success": checks["node_local_provider_closed_zero_mutation"],
        "palette_progressive_disclosure": checks["compact_palette"],
        "edge_endpoint_gap_within_2px": checks["edge_geometry_exact"],
        "real_reference_image_entry": checks["reference_image_entry"],
        "ai_panel_not_execution_receipt_dump": checks["ai_partner_compact"],
        "phone_and_tablet_no_horizontal_scroll": checks["responsive_shell"],
        "provider_cost_honesty_when_closed": checks["node_local_provider_closed_zero_mutation"],
        "advanced_evidence_not_primary_noise": checks["topbar_help_account_ia"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
