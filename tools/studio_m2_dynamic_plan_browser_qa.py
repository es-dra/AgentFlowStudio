from __future__ import annotations

import argparse
import json
import os
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

from studio_asset_context_browser_qa_support import chrome_path, free_port, stop_runtime, wait_for_http
from studio_asset_context_browser_qa_support import runtime_test_client


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.runtime_dynamic_production_plan import (  # noqa: E402
    PROVIDER_CAPABILITY_SCHEMA_VERSION,
    STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
    story_plan_candidate_digest,
)


ANALYSIS_CANDIDATE_SCHEMA_VERSION = "afs.structured_analysis_candidate.v0.1"
PROJECT_ID = f"studio-dynamic-plan-browser-qa-{int(time.time())}"
SCRIPT_TEXT = "Mira calibrates the lens in the observatory. Tao opens the signal room as a distant signal arrives."


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-dynamic-plan-")).resolve()
    report_path = Path(args.report or f"/tmp/{PROJECT_ID}.json").resolve()
    screenshot_dir = Path(args.screenshot_dir or f"/tmp/{PROJECT_ID}-screens").resolve()
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}"

    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    prepare_empty_project(runtime_root)

    server = start_gate_closed_runtime(repo, runtime_root, port)
    try:
        wait_for_http(f"{base_url}/health")
        report = run_browser_qa(repo, base_url, screenshot_dir, args.headed, args.timeout_ms)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(report_path)}, ensure_ascii=False))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Studio M2 Dynamic Production Plan browser QA.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=90_000)
    return parser.parse_args()


def prepare_empty_project(runtime_root: Path) -> None:
    client = runtime_test_client(runtime_root)
    created = client.post("/projects", json={"project_id": PROJECT_ID, "goal": "Dynamic production plan browser QA"})
    if created.status_code not in {200, 409}:
        raise AssertionError(f"project setup failed: {created.status_code} {created.text}")
    state = {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "Dynamic Plan QA",
            "canvasName": "QA Canvas",
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
    }
    saved = client.put(f"/projects/{PROJECT_ID}/studio-state", json={"state": state})
    if saved.status_code != 200:
        raise AssertionError(f"studio state setup failed: {saved.status_code} {saved.text}")


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
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "runtime-service",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
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
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            viewports: dict[str, Any] = {}
            for viewport in ({"width": 1440, "height": 900}, {"width": 1024, "height": 768}):
                page = browser.new_page(viewport=viewport)
                page.set_default_timeout(timeout_ms)
                expect.set_options(timeout=timeout_ms)
                attach_error_capture(page, console_errors, response_errors)
                page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
                page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))
                page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=dynamic-plan-{viewport['width']}", wait_until="domcontentloaded")
                expect(page.locator("#product-shell-root")).to_be_visible()
                page.wait_for_function(
                    "document.querySelector('#product-shell-root')?.dataset.view === 'canvas' && document.querySelector('.studio-unified-workspace')"
                )
                viewport_key = f"{viewport['width']}x{viewport['height']}"
                viewports[viewport_key] = assert_default_canvas(page, viewport)
                screenshots[viewport_key] = str((screenshot_dir / f"{viewport_key}.png").resolve())
                page.screenshot(path=screenshots[viewport_key], full_page=True)
                page.close()

            interaction_page = browser.new_page(viewport={"width": 1440, "height": 900})
            interaction_page.set_default_timeout(timeout_ms)
            expect.set_options(timeout=timeout_ms)
            attach_error_capture(interaction_page, console_errors, response_errors)
            interaction_page.route("**/studio/src/**", make_worktree_studio_static_route(repo))
            interaction_page.route("**/studio/styles/**", make_worktree_studio_static_route(repo))
            interaction_page.goto(f"{base_url}/studio/?project={PROJECT_ID}&stage=canvas&qa=dynamic-plan-interaction", wait_until="domcontentloaded")
            interaction_page.wait_for_function(
                "document.querySelector('#product-shell-root')?.dataset.view === 'canvas' && document.querySelector('.studio-unified-workspace')"
            )
            interaction = assert_dynamic_plan_interaction(interaction_page, base_url)
            screenshots["interaction"] = str((screenshot_dir / "interaction.png").resolve())
            interaction_page.screenshot(path=screenshots["interaction"], full_page=True)
            interaction_page.close()
        finally:
            browser.close()

    actionable_response_errors = [item for item in response_errors if not item["url"].endswith("/favicon.ico")]
    if console_errors or actionable_response_errors:
        raise AssertionError(f"console errors: {console_errors[:5]}; response errors: {actionable_response_errors[:5]}")
    final_truth = http_json(f"{base_url}/projects/{PROJECT_ID}/production-plan-truth")
    return {
        "artifact_type": "studio_m2_dynamic_plan_browser_qa_report",
        "schema_version": "0.1.0",
        "status": "passed",
        "project_id": PROJECT_ID,
        "base_url": base_url,
        "screenshots": screenshots,
        "viewports": viewports,
        "interaction": interaction,
        "planning_state": final_truth["projection"]["planning_state"],
        "shot_count": len(final_truth["projection"]["shots"]),
        "chunk_count": len(final_truth["projection"]["chunks"]),
        "console_error_count": len(console_errors),
        "response_error_count": len(actionable_response_errors),
        "provider_dispatch_count": final_truth.get("provider_dispatch_count", 0),
        "remote_dispatch_count": final_truth.get("remote_dispatch_count", 0),
        "non_claims": [
            "browser/runtime verification only",
            "not provider story planning",
            "not media generation",
            "not complete auto production chain",
            "not creative quality assurance",
            "not owner acceptance",
            "not business validation",
        ],
    }


def attach_error_capture(page: Page, console_errors: list[str], response_errors: list[dict[str, Any]]) -> None:
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on(
        "response",
        lambda response: response_errors.append({"status": response.status, "url": response.url})
        if response.status >= 400
        else None,
    )


def assert_default_canvas(page: Page, viewport: dict[str, int]) -> dict[str, Any]:
    snapshot = page.evaluate(
        """
        () => {
          const root = document.querySelector("#product-shell-root");
          const workspace = document.querySelector(".studio-unified-workspace");
          const agent = document.querySelector(".studio-agent-chat");
          const bodyText = document.body.textContent || "";
          const rect = agent?.getBoundingClientRect();
          const shellRect = workspace?.getBoundingClientRect();
          return {
            view: root?.dataset.view || "",
            rootClass: root?.className || "",
            workspaceClass: workspace?.className || "",
            agentClass: agent?.className || "",
            bodyExcerpt: bodyText.replace(/\\s+/g, " ").slice(0, 300),
            canvasVisible: Boolean(document.querySelector("#canvas-root")),
            agentVisible: Boolean(agent && getComputedStyle(agent).display !== "none"),
            agentRightDocked: Boolean(
              agent
              && workspace
              && workspace.lastElementChild === agent
              && rect
              && shellRect
              && rect.width >= 48
              && Math.abs(rect.right - shellRect.right) <= 2
            ),
            emptyFacts: bodyText.includes("0 场景") && bodyText.includes("0 镜头") && bodyText.includes("尚未创建故事事实"),
            fixtureLeak: ["巷口", "雨巷", "老宅", "4x15", "4×15"].some((item) => bodyText.includes(item)),
          };
        }
        """
    )
    problems: list[str] = []
    if snapshot["view"] != "canvas":
        problems.append(f"default view is {snapshot['view']!r}")
    if not snapshot["canvasVisible"]:
        problems.append("canvas is not visible")
    if not snapshot["agentVisible"] or not snapshot["agentRightDocked"]:
        problems.append("Agent Chat is not fixed on the right")
    if not snapshot["emptyFacts"]:
        problems.append("empty canvas did not report zero facts")
    if snapshot["fixtureLeak"]:
        problems.append("fixture text leaked into empty project")
    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    readonly = page.evaluate("() => (document.body.textContent || '').includes('故事板当前只读取画布确认后的事实')")
    if not readonly:
        problems.append("storyboard did not remain read-only")
    page.get_by_role("tab", name="画布").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'canvas'")
    if problems:
        raise AssertionError(f"{viewport['width']}x{viewport['height']}: " + "; ".join(problems) + f"; snapshot={json.dumps(snapshot, ensure_ascii=False)}")
    return {"canvas_default": True, "agent_chat_right_panel": True, "empty_project": True, "storyboard_read_only": True}


def assert_dynamic_plan_interaction(page: Page, base_url: str) -> dict[str, Any]:
    expect(page.locator("#canvas-root")).to_be_visible()
    send_agent_command(page, f"/script-revision {SCRIPT_TEXT}", "ScriptRevision")
    expect(page.locator(".node").filter(has_text="analysis_state: analysis_required")).to_be_visible()

    truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    revision = truth["projection"]["current_revision"]
    submit_analysis_candidate(base_url, revision)
    send_agent_command(page, "/refresh-script-truth", "Script/Core Asset Truth")
    expect(page.locator(".node").filter(has_text="Mira")).to_be_visible()
    expect(page.locator(".node").filter(has_text="Observatory")).to_be_visible()

    truth = http_json(f"{base_url}/projects/{PROJECT_ID}/script-truth")
    candidate = story_plan_candidate(revision, truth["projection"])
    send_agent_command(page, f"/submit-story-plan {json.dumps(candidate, ensure_ascii=False, separators=(',', ':'))}", "Story Plan Candidate")
    expect(page.locator(".node").filter(has_text="Production Plan")).to_be_visible()
    expect(page.locator(".node").filter(has_text="Dynamic shot 3")).to_be_visible()
    expect(page.locator(".node").filter(has_text="Concat Plan")).to_be_visible()

    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/edit-shot-duration 7.25", "编辑镜头时长")
    expect(page.locator(".node").filter(has_text="7.25s")).to_be_visible()
    page.get_by_role("button", name="撤销").first.click()
    page.wait_for_function(
        "() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('7.25s'))"
    )

    select_plan_node(page, "production_plan_shot_shot_dynamic_1", "Shot 1")
    send_agent_command(page, "/set-shot-strategy t2v reason=creator keeps this shot text-only", "设置镜头媒体策略")
    expect(page.locator(".node").filter(has_text="creator keeps this shot text-only")).to_be_visible()

    select_plan_node(page, "production_plan_shot_shot_dynamic_2", "Shot 2")
    send_agent_command(page, "/split-shot 3 3.5", "拆分当前镜头")
    expect(page.locator(".node").filter(has_text="part 2")).to_be_visible()
    select_plan_node(page, "production_plan_shot_shot_dynamic_2a", "Shot 2")
    send_agent_command(page, "/merge-shot-next", "合并下一镜头")
    page.wait_for_function(
        "() => !document.getElementById('production_plan_shot_shot_dynamic_2b') && !document.querySelector('[data-node-id=\"production_plan_shot_shot_dynamic_2b\"]')"
    )

    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/mark-failed", "标记失败")
    expect(page.locator(".node").filter(has_text="state: failed")).to_be_visible()
    send_agent_command(page, "/retry-failed", "重试失败项")
    page.wait_for_function(
        "() => !Array.from(document.querySelectorAll('.node')).some((node) => (node.textContent || '').includes('state: failed'))"
    )
    select_plan_node(page, "production_plan_shot_shot_dynamic_3", "Shot 3")
    send_agent_command(page, "/replan-affected", "重算受影响计划")

    page.get_by_role("tab", name="故事板").click()
    page.wait_for_function("document.querySelector('#product-shell-root')?.dataset.view === 'storyboard'")
    expect(page.locator("#product-shell-root")).to_contain_text("Shot 1")
    expect(page.locator("#product-shell-root")).to_contain_text("Shot 2")
    submit_agent_text(page, "/edit-shot-duration 8")
    expect(page.locator(".agent-command-preview.blocked").filter(has_text="故事板是只读投影")).to_be_visible()

    final_plan = http_json(f"{base_url}/projects/{PROJECT_ID}/production-plan-truth")["projection"]
    return {
        "script_revision_created": True,
        "analysis_candidate_seeded": True,
        "plan_created_from_agent_chat": True,
        "shot_count": len(final_plan["shots"]),
        "chunk_count": len(final_plan["chunks"]),
        "planning_state": final_plan["planning_state"],
        "storyboard_read_only_blocks_write": True,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def send_agent_command(page: Page, command: str, preview_text: str) -> None:
    preview = page.locator(".agent-command-preview").filter(has_text=preview_text).first
    last_error: AssertionError | None = None
    for attempt in range(2):
        submit_agent_text(page, command)
        try:
            expect(preview).to_be_visible(timeout=8_000)
            last_error = None
            break
        except AssertionError as exc:
            last_error = exc
            page.wait_for_timeout(250 + attempt * 250)
    if last_error is not None:
        details = page.evaluate(
            """
            () => {
              const agent = document.querySelector('.studio-agent-chat');
              return {
                agentText: (agent?.textContent || '').replace(/\\s+/g, ' ').slice(0, 1200),
                previewCount: document.querySelectorAll('.agent-command-preview').length,
                composerValue: document.querySelector('.agent-chat-composer textarea')?.value || '',
              };
            }
            """
        )
        raise AssertionError(f"Agent command preview not visible for {preview_text}: {json.dumps(details, ensure_ascii=False)}") from last_error
    confirm = preview.get_by_role("button", name="确认执行")
    expect(confirm).to_be_visible()
    confirm.click()
    expect(page.locator(".agent-receipt").first).to_be_visible()


def submit_agent_text(page: Page, command: str) -> None:
    composer = page.locator(".agent-chat-composer textarea")
    expect(composer).to_be_visible()
    composer.fill(command)
    composer.evaluate("(input) => input.form.requestSubmit()")


def select_plan_node(page: Page, node_id: str, context_label: str) -> None:
    exists = page.evaluate(
        "(nodeId) => Boolean(document.getElementById(nodeId) || document.querySelector(`[data-node-id=\"${nodeId}\"]`))",
        node_id,
    )
    if not exists:
        raise AssertionError(f"projection node is missing: {node_id}")
    page.evaluate(
        """
        (nodeId) => window.dispatchEvent(new CustomEvent('afs:studio-select-node', { detail: { node_id: nodeId } }))
        """,
        node_id,
    )
    expect(page.locator(".studio-agent-chat .agent-context-strip")).to_contain_text(context_label)


def submit_analysis_candidate(base_url: str, revision: dict[str, Any]) -> None:
    body = {
        "project_id": PROJECT_ID,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
        "named_characters": [
            {"display_name": "Mira", "aliases": ["she"], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Mira")], "confidence": 0.94, "status": "candidate"},
            {"display_name": "Tao", "aliases": [], "pronoun_links": [], "evidence_spans": [span(SCRIPT_TEXT, "Tao")], "confidence": 0.9, "status": "candidate"},
        ],
        "main_scenes": [
            {"name": "Observatory", "evidence_spans": [span(SCRIPT_TEXT, "observatory")], "confidence": 0.92, "status": "candidate"},
            {"name": "Signal Room", "evidence_spans": [span(SCRIPT_TEXT, "signal room")], "confidence": 0.91, "status": "candidate"},
        ],
        "style": "precise luminous animation",
        "genre": "short science drama",
        "tone": "focused",
        "actions": ["calibrates the lens", "opens the signal room"],
        "events": ["a distant signal arrives"],
        "beats": [{"summary": "signal setup"}, {"summary": "response"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    http_json(
        f"{base_url}/projects/{PROJECT_ID}/script-revisions/{revision['revision_id']}/analysis-candidates",
        method="POST",
        payload=body,
    )


def story_plan_candidate(revision: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    characters = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "character"]
    scenes = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "main_scene"]
    beats = [
        {
            "beat_id": "beat_lens_setup",
            "order": 1,
            "summary": "Mira prepares the lens as the signal arrives.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Mira calibrates the lens"}],
            "narrative_purpose": "establish the signal source",
        },
        {
            "beat_id": "beat_signal_response",
            "order": 2,
            "summary": "Tao opens the signal room and the response path.",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Tao opens the signal room"}],
            "narrative_purpose": "move the scene into response",
        },
    ]
    shots = [
        shot(revision["revision_id"], "shot_dynamic_1", beats[0]["beat_id"], 1, 2.5, "Dynamic shot 1 follows Mira setting the lens.", characters[:1], scenes[:1], "opening stillness", "lens rotates", t2v("text prompt is sufficient because no visual reference is locked")),
        shot(revision["revision_id"], "shot_dynamic_2", beats[0]["beat_id"], 2, 6.5, "Dynamic shot 2 moves through the calibrated lens.", characters[:1], scenes[:1], "lens rotates", "signal line continues", i2v(PROJECT_ID, revision, characters[0])),
        shot(revision["revision_id"], "shot_dynamic_3", beats[1]["beat_id"], 3, 3.0, "Dynamic shot 3 tracks Tao opening the signal room.", characters[:2], scenes[-1:], "signal line continues", "response path holds", t2v("creator intent names action without a reference artifact")),
    ]
    payload = {
        "project_id": PROJECT_ID,
        "script_revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
        "candidate_digest": "",
        "beats": beats,
        "shots": shots,
        "capability_contract": {
            "schema_version": PROVIDER_CAPABILITY_SCHEMA_VERSION,
            "provider_profile_id": "offline-contract-capability",
            "supports_t2v": True,
            "supports_i2v": True,
            "supported_clip_durations": [2.5, 3.0, 4.0],
            "max_duration_seconds": 4.0,
            "supports_start_frame": True,
            "supports_end_frame": True,
            "aspect_ratios": ["9:16"],
            "fps_values": [24],
        },
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload["candidate_digest"] = story_plan_candidate_digest(payload)
    return payload


def shot(
    revision_id: str,
    shot_id: str,
    beat_id: str,
    order: int,
    duration: float,
    intent: str,
    character_refs: list[str],
    scene_refs: list[str],
    continuity_in: str,
    continuity_out: str,
    media_strategy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "shot_id": shot_id,
        "beat_id": beat_id,
        "order": order,
        "intent": intent,
        "duration_seconds": duration,
        "character_refs": character_refs,
        "scene_refs": scene_refs,
        "continuity_in": continuity_in,
        "continuity_out": continuity_out,
        "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision_id, "quote": "distant signal arrives"}],
        "media_strategy": {key: value for key, value in media_strategy.items() if key != "revision_id"},
    }


def t2v(reason: str) -> dict[str, Any]:
    return {
        "revision_id": "",
        "strategy": "t2v",
        "strategy_reason": reason,
        "input_requirements": ["text_prompt_contract"],
        "reference_asset_refs": [],
        "user_constraints": {"explicit_reference_available": False},
    }


def i2v(project_id: str, revision: dict[str, Any], asset_id: str) -> dict[str, Any]:
    return {
        "revision_id": revision["revision_id"],
        "strategy": "i2v",
        "strategy_reason": "locked keyframe lineage is available for the lens move",
        "input_requirements": ["reference_artifact_or_locked_keyframe"],
        "reference_asset_refs": [
            {
                "ref_id": "ref_lens_keyframe",
                "source_kind": "locked_keyframe",
                "asset_id": asset_id,
                "artifact_id": "artifact-lens-keyframe",
                "lineage": {
                    "project_id": project_id,
                    "script_revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "asset_id": asset_id,
                    "artifact_id": "artifact-lens-keyframe",
                    "locked_keyframe_id": "locked-keyframe-lens",
                },
            }
        ],
        "user_constraints": {"explicit_reference_available": True},
    }


def span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


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
