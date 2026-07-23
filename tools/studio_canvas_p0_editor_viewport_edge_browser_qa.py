from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, free_port, runtime_test_client, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PROJECT_ID = f"studio-canvas-p0-browser-qa-{int(time.time())}"
SCRIPT_TEXT = "林夏在雨后的车站拾到一只旧录音笔。她听见未来的自己提醒她不要登上末班车。"


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root_auto = not args.runtime_root
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-canvas-p0-")).resolve()
    report_path = Path(args.report or f"/tmp/{PROJECT_ID}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/{PROJECT_ID}-screens").resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    prepare_project(runtime_root, empty_studio_state())

    server = start_gate_closed_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, base_url, screenshot_dir, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)
        if runtime_root_auto:
            shutil.rmtree(runtime_root, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Studio Canvas P0 editor/viewport/edge browser QA.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    return parser.parse_args()


def prepare_project(runtime_root: Path, state: dict[str, Any]) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "画布 P0 输入与连线核验"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {created.status_code} {created.text}")
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state setup failed: {saved.status_code} {saved.text}")


def empty_studio_state() -> dict[str, Any]:
    return {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "P0 输入与连线核验",
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


def edge_studio_state() -> dict[str, Any]:
    state = empty_studio_state()
    state["meta"]["seq"] = 3
    state["viewport"] = {"x": 0, "y": 0, "scale": 1}
    state["nodes"] = {
        "node_text_a": {
            "id": "node_text_a",
            "type": "text",
            "title": "起点文本",
            "x": 80,
            "y": 120,
            "w": 280,
            "h": 260,
            "prompt": "林夏听见录音笔里的提醒。",
            "content": "林夏听见录音笔里的提醒。",
            "status": "complete",
            "params": {},
            "collapsed": False,
        },
        "node_text_b": {
            "id": "node_text_b",
            "type": "script",
            "title": "分镜准备",
            "x": 520,
            "y": 290,
            "w": 280,
            "h": 260,
            "prompt": "准备进入专业分镜。",
            "content": "准备进入专业分镜。",
            "status": "complete",
            "params": {},
            "collapsed": False,
        },
    }
    state["edges"] = {"edge_a_b": {"id": "edge_a_b", "from": "node_text_a", "to": "node_text_b", "relation_type": "generation"}}
    state["order"] = ["node_text_a", "node_text_b"]
    return state


def start_gate_closed_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_RUNTIME_SERVICE_PORT"] = str(port)
    env["AFS_AUTH_ENABLED"] = "false"
    env["AFS_AUTH_ALLOW_OPEN_SIGNUP"] = "false"
    env["NO_PROXY"] = merge_no_proxy(env.get("NO_PROXY"))
    env["no_proxy"] = merge_no_proxy(env.get("no_proxy"))
    for key in (
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        env.pop(key, None)
    return subprocess.Popen(
        [sys.executable, "-m", "apps.cli.main", "runtime-service", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_browser_qa(repo: Path, base_url: str, screenshot_dir: Path, headed: bool, timeout_ms: int) -> dict[str, Any]:
    console_errors: list[str] = []
    response_errors: list[dict[str, Any]] = []
    screenshots: dict[str, str] = {}
    viewports: dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            for viewport in ({"width": 1920, "height": 1080}, {"width": 1440, "height": 900}, {"width": 1024, "height": 768}):
                context = browser.new_context(viewport=viewport)
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                attach_error_capture(page, console_errors, response_errors)
                install_static_routes(page, repo)
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=p0-empty-{viewport['width']}", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
                wait_for_empty_canvas_ready(page)
                key = f"{viewport['width']}x{viewport['height']}"
                viewports[key] = {
                    "empty": assert_empty_input_and_viewport(page),
                    "node_input": assert_node_text_input_lifecycle(page),
                    "prompt_bar": assert_prompt_bar_input_lifecycle(page),
                    "agent_chat": assert_agent_chat_input_lifecycle(page),
                }
                screenshots[f"p0-editor-{key}"] = str((screenshot_dir / f"p0-editor-{key}.png").resolve())
                page.screenshot(path=screenshots[f"p0-editor-{key}"], full_page=True)
                context.close()

                reset_project_state(base_url, edge_studio_state())
                edge_context = browser.new_context(viewport=viewport)
                edge_page = edge_context.new_page()
                edge_page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                attach_error_capture(edge_page, console_errors, response_errors)
                install_static_routes(edge_page, repo)
                edge_page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=p0-edge-{viewport['width']}", wait_until="domcontentloaded")
                edge_page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
                edge_page.wait_for_selector('[data-edge-id="edge_a_b"] path.edge-flow')
                viewports[key]["edge_geometry"] = assert_edge_geometry(edge_page)
                screenshots[f"p0-edge-{key}"] = str((screenshot_dir / f"p0-edge-{key}.png").resolve())
                edge_page.screenshot(path=screenshots[f"p0-edge-{key}"], full_page=True)
                edge_context.close()

                reset_project_state(base_url, empty_studio_state())

            reset_project_state(base_url, empty_studio_state())
            split_context = browser.new_context(viewport={"width": 1440, "height": 900})
            split_page = split_context.new_page()
            split_page.set_default_timeout(timeout_ms)
            expect.set_options(timeout=timeout_ms)
            attach_error_capture(split_page, console_errors, response_errors)
            install_static_routes(split_page, repo)
            split_page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=p0-auto-split", wait_until="domcontentloaded")
            split_page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
            wait_for_empty_canvas_ready(split_page)
            viewports["1440x900"]["auto_split"] = assert_auto_split_entry(split_page)
            screenshots["p0-auto-split-1440x900"] = str((screenshot_dir / "p0-auto-split-1440x900.png").resolve())
            split_page.screenshot(path=screenshots["p0-auto-split-1440x900"], full_page=True)
            split_context.close()
        finally:
            browser.close()

    actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable_response_errors:
        raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
    script_truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    plan_truth = http_json(f"{base_url}/projects/{PROJECT_ID}/production-plan-truth")
    return {
        "artifact_type": "studio_canvas_p0_editor_viewport_edge_browser_qa_report",
        "schema_version": "0.1.0",
        "status": "passed",
        "project_id": PROJECT_ID,
        "screenshots": screenshots,
        "viewports": viewports,
        "console_error_count": len(console_errors),
        "response_error_count": len(actionable_response_errors),
        "provider_dispatch_count": script_truth.get("provider_dispatch_count", 0) + plan_truth.get("provider_dispatch_count", 0),
        "remote_dispatch_count": script_truth.get("remote_dispatch_count", 0) + plan_truth.get("remote_dispatch_count", 0),
        "non_claims": [
            "browser/runtime verification only",
            "not provider story planning",
            "not media generation",
            "not creative quality assurance",
            "not owner acceptance",
            "not business validation",
        ],
    }


def assert_empty_input_and_viewport(page: Page) -> dict[str, Any]:
    expect(page.locator("#canvas-empty-hint:not([hidden])")).to_be_visible()
    textarea = page.locator('.canvas-empty-onboarding [data-empty-action="idea-text"]').first
    textarea.click()
    page.keyboard.type("yy")
    snapshot = page.evaluate(
        """
        () => {
          const input = document.querySelector('.canvas-empty-onboarding [data-empty-action="idea-text"]');
          return {
            focused: document.activeElement === input,
            value: input?.value || "",
            nodeCount: document.querySelectorAll(".node").length,
            zoom: document.querySelector("#corner-controls .zoom-label")?.textContent || "",
          };
        }
        """
    )
    if snapshot != {"focused": True, "value": "yy", "nodeCount": 0, "zoom": "100%"}:
        raise AssertionError(f"empty input/viewport failed: {json.dumps(snapshot, ensure_ascii=False)}")
    return snapshot


def assert_node_text_input_lifecycle(page: Page) -> dict[str, Any]:
    page.locator('.canvas-workspace-stage [data-empty-action="blank-node"]').click()
    expect(page.locator(".node")).to_have_count(1)
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.click()
    page.keyboard.type("y")
    page.wait_for_timeout(850)
    first = editor_snapshot(page)
    page.keyboard.type("y")
    second = editor_snapshot(page)
    page.keyboard.type(" long text stays focused")
    long_text = editor_snapshot(page)
    page.evaluate(
        """
        () => {
          const el = document.querySelector(".node-content-editor");
          el.focus();
          el.setRangeText("\\n粘贴段落", el.selectionStart, el.selectionEnd, "end");
          el.dispatchEvent(new ClipboardEvent("paste", { bubbles: true }));
          el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertFromPaste" }));
        }
        """
    )
    pasted = editor_snapshot(page)
    page.evaluate(
        """
        () => {
          const el = document.querySelector(".node-content-editor");
          el.focus();
          el.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true, data: "" }));
          el.setRangeText("中", el.selectionStart, el.selectionEnd, "end");
          el.dispatchEvent(new InputEvent("beforeinput", { bubbles: true, inputType: "insertCompositionText", data: "中" }));
          el.dispatchEvent(new CompositionEvent("compositionupdate", { bubbles: true, data: "中" }));
          el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertCompositionText", data: "中" }));
          el.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true, data: "中" }));
        }
        """
    )
    page.wait_for_timeout(50)
    composed = editor_snapshot(page)
    page.keyboard.press("Control+Z")
    undo = editor_snapshot(page)
    page.keyboard.press("Control+Y")
    redo = editor_snapshot(page)
    checks = [first, second, long_text, pasted, composed, undo, redo]
    if any(not item["focused"] for item in checks):
        raise AssertionError(f"node editor lost focus: {json.dumps(checks, ensure_ascii=False)}")
    if first["value"] != "y" or second["value"] != "yy" or "long text" not in long_text["value"] or "粘贴段落" not in pasted["value"] or "中" not in composed["value"]:
        raise AssertionError(f"node editor values failed: {json.dumps(checks, ensure_ascii=False)}")
    if composed["nodeCount"] != 1 or undo["nodeCount"] != 1 or redo["nodeCount"] != 1:
        raise AssertionError(f"editor undo/redo leaked to canvas history: {json.dumps(checks, ensure_ascii=False)}")
    return {"focused_after_yy": True, "paste": True, "composition": True, "undo_redo_kept_node": True}


def assert_prompt_bar_input_lifecycle(page: Page) -> dict[str, Any]:
    prompt = page.locator(".prompt-bar textarea").first
    expect(prompt).to_be_visible()
    prompt.click()
    page.keyboard.type(" prompt")
    page.wait_for_timeout(850)
    snapshot = page.evaluate(
        """
        () => {
          const el = document.querySelector(".prompt-bar textarea");
          return {
            focused: document.activeElement === el,
            value: el?.value || "",
            nodeCount: document.querySelectorAll(".node").length,
          };
        }
        """
    )
    if not snapshot["focused"] or "prompt" not in snapshot["value"] or snapshot["nodeCount"] != 1:
        raise AssertionError(f"prompt bar input failed: {json.dumps(snapshot, ensure_ascii=False)}")
    return snapshot


def assert_agent_chat_input_lifecycle(page: Page) -> dict[str, Any]:
    input_box = page.locator(".agent-chat-composer textarea").first
    expect(input_box).to_be_visible()
    input_box.click()
    page.keyboard.type("yy")
    snapshot = page.evaluate(
        """
        () => {
          const el = document.querySelector(".agent-chat-composer textarea");
          return { focused: document.activeElement === el, value: el?.value || "" };
        }
        """
    )
    if snapshot != {"focused": True, "value": "yy"}:
        raise AssertionError(f"agent chat input failed: {json.dumps(snapshot, ensure_ascii=False)}")
    input_box.fill("")
    return snapshot


def assert_auto_split_entry(page: Page) -> dict[str, Any]:
    page.locator('.canvas-workspace-stage [data-empty-action="blank-node"]').click()
    expect(page.locator(".node")).to_have_count(1)
    editor = page.locator(".node-content-editor").first
    expect(editor).to_be_visible()
    editor.fill(SCRIPT_TEXT)
    node_id = page.locator(".node").first.get_attribute("data-node-id")
    if not node_id:
        raise AssertionError("text node missing before auto split")
    send_agent_command(page, f"/script-revision {SCRIPT_TEXT}", "创建剧本版本")
    select_canvas_node(page, node_id)
    split = page.get_by_title("从当前剧本版本规划专业分镜")
    expect(split).to_be_visible()
    split.click()
    preview = page.locator(".agent-command-preview").filter(has_text="拆分分镜").first
    expect(preview).to_be_visible()
    preview.get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").filter(has_text="需要智能规划器")).to_be_visible()
    snapshot = page.evaluate(
        """
        () => {
          const visible = document.body.innerText;
          return {
            hasSplitAction: visible.includes("拆分分镜"),
            planningRequiredReceipt: visible.includes("需要智能规划器"),
            rawLeak: visible.includes("/plan-selected-script-shots") || visible.includes("structuredShotFromSegment"),
            fixedPlanLeak: visible.includes("4×15") || visible.includes("15秒"),
          };
        }
        """
    )
    if not snapshot["hasSplitAction"] or not snapshot["planningRequiredReceipt"] or snapshot["rawLeak"] or snapshot["fixedPlanLeak"]:
        raise AssertionError(f"auto split entry failed: {json.dumps(snapshot, ensure_ascii=False)}")
    return snapshot


def assert_edge_geometry(page: Page) -> dict[str, Any]:
    page.emulate_media(reduced_motion="reduce")
    default = edge_snapshot(page)
    page.keyboard.press("Control+=")
    page.keyboard.press("Control+=")
    zoomed = edge_snapshot(page)
    page.mouse.move(320, 320)
    page.mouse.wheel(120, 80)
    panned = edge_snapshot(page)
    select_canvas_node(page, "node_text_a")
    selected = edge_snapshot(page)
    if any(item["startDelta"] > 1.75 or item["endDelta"] > 1.75 for item in [default, zoomed, panned, selected]):
        raise AssertionError(f"edge endpoint drift: {json.dumps([default, zoomed, panned, selected], ensure_ascii=False)}")
    if selected["sparkActive"]:
        raise AssertionError(f"selected edge/node activated runtime spark: {json.dumps(selected, ensure_ascii=False)}")
    if selected["sparkAnimation"] not in {"none", ""}:
        raise AssertionError(f"reduced-motion did not suppress spark animation: {json.dumps(selected, ensure_ascii=False)}")
    return {"default": default, "zoomed": zoomed, "panned": panned, "selection_static": selected}


def editor_snapshot(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const el = document.querySelector(".node-content-editor");
          return {
            focused: document.activeElement === el,
            value: el?.value || "",
            selectionStart: el?.selectionStart || 0,
            selectionEnd: el?.selectionEnd || 0,
            composing: el?.dataset.afsComposing || "",
            nodeCount: document.querySelectorAll(".node").length,
          };
        }
        """
    )


def edge_snapshot(page: Page) -> dict[str, Any]:
    page.wait_for_timeout(80)
    return page.evaluate(
        """
        () => {
          const parse = (d) => {
            const numbers = String(d || "").match(/-?\\d+(?:\\.\\d+)?/g)?.map(Number) || [];
            return { x1: numbers[0], y1: numbers[1], x2: numbers[numbers.length - 2], y2: numbers[numbers.length - 1] };
          };
          const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
          const matrix = new DOMMatrixReadOnly(getComputedStyle(document.querySelector("#world")).transform);
          const root = document.querySelector("#canvas-root").getBoundingClientRect();
          const path = document.querySelector('[data-edge-id="edge_a_b"] path.edge-flow');
          const spark = document.querySelector('[data-edge-id="edge_a_b"] path.edge-spark');
          const d = parse(path.getAttribute("d"));
          const toClient = (x, y) => ({ x: root.left + matrix.a * x + matrix.e, y: root.top + matrix.d * y + matrix.f });
          const startPath = toClient(d.x1, d.y1);
          const endPath = toClient(d.x2, d.y2);
          const out = document.querySelector('[data-node-id="node_text_a"] .node-port.out').getBoundingClientRect();
          const input = document.querySelector('[data-node-id="node_text_b"] .node-port.in').getBoundingClientRect();
          const startPort = { x: out.left + out.width / 2, y: out.top + out.height / 2 };
          const endPort = { x: input.left + input.width / 2, y: input.top + input.height / 2 };
          return {
            zoom: document.querySelector("#corner-controls .zoom-label")?.textContent || "",
            startDelta: dist(startPath, startPort),
            endDelta: dist(endPath, endPort),
            sparkActive: spark.classList.contains("active"),
            sparkAnimation: getComputedStyle(spark).animationName,
            edgeLifecycle: spark.dataset.lifecycle || "",
            noHorizontalScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
          };
        }
        """
    )


def wait_for_empty_canvas_ready(page: Page) -> None:
    page.wait_for_function(
        """
        () => {
          const root = document.querySelector("#canvas-root");
          const form = document.querySelector(".canvas-empty-onboarding");
          const rect = form?.getBoundingClientRect();
          return Boolean(root && form && !document.querySelector(".product-state-loading") && rect && rect.width > 220 && rect.height > 160);
        }
        """
    )


def reset_project_state(base_url: str, state: dict[str, Any]) -> None:
    current = http_json(f"{base_url}/projects/{PROJECT_ID}/studio-state")
    http_json(
        f"{base_url}/projects/{PROJECT_ID}/studio-state",
        method="PUT",
        payload={"state": state, "expected_version": current.get("state_version", "")},
    )


def send_agent_command(page: Page, command: str, preview_text: str) -> None:
    composer = page.locator(".agent-chat-composer textarea").first
    expect(composer).to_be_visible()
    composer.fill(command)
    composer.evaluate("(input) => input.form.requestSubmit()")
    preview = page.locator(".agent-command-preview").filter(has_text=preview_text).first
    expect(preview).to_be_visible()
    preview.get_by_role("button", name="确认执行").click()
    expect(page.locator(".agent-receipt").first).to_be_visible()


def select_canvas_node(page: Page, node_id: str) -> None:
    page.evaluate(
        "(nodeId) => window.dispatchEvent(new CustomEvent('afs:studio-select-node', { detail: { node_id: nodeId } }))",
        node_id,
    )


def attach_error_capture(page: Page, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on(
        "response",
        lambda response: response_errors.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )


def install_static_routes(page: Page, repo: Path) -> None:
    page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
    page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {exc.code} from {url}: {body}") from exc


def make_worktree_studio_static_route(repo: Path):
    studio_root = (repo / "apps" / "studio").resolve()

    def route_studio_static(route: Any) -> None:
        parsed = urlsplit(route.request.url)
        relative = unquote(parsed.path.removeprefix("/studio/"))
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


def merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    lowered = {item.lower() for item in entries}
    for item in ("127.0.0.1", "localhost", "::1"):
        if item.lower() not in lowered:
            entries.append(item)
    return ",".join(entries)


if __name__ == "__main__":
    raise SystemExit(main())
