from __future__ import annotations

import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path == "/__creator_video_entry.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in {
            "/favicon.ico",
            "/favicon.svg",
            "/projects/browser-video-entry/image-assets/keyframe-approved/preview",
        }:
            body = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def _server():
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)

    class Context:
        def __enter__(self) -> str:
            thread.start()
            return f"http://127.0.0.1:{server.server_address[1]}"

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    return Context()


def test_desktop_storyboard_and_agent_use_the_same_zero_provider_video_entry() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.goto(f"{base_url}/__creator_video_entry.html", wait_until="domcontentloaded")
                page.wait_for_function("window.__videoEntryReady === true")

                _assert_storyboard_entry(page)
                _assert_two_step_confirmation(page)
                assert page.evaluate("window.__calls") == {
                    "compilePreview": 1,
                    "compileConfirm": 1,
                    "reservePreview": 1,
                    "agentConversation": 0,
                    "videoDispatch": 0,
                }
                assert not console_errors

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__videoEntryReady === true")
                composer = page.get_by_label("向 AI 创作搭档发送消息或命令")
                composer.fill(
                    "请为当前镜头准备生成视频：仅使用已批准关键帧和同项目参考图；"
                    "必须是 doubao-seedance-2-0 非 fast、720p、6 秒。先展示确认卡，不要自动发送。"
                )
                page.get_by_label("发送到 AI 创作搭档").click()
                page.get_by_text("当前镜头已有已批准关键帧和 3 张参考图", exact=False).wait_for()
                assert page.evaluate("window.__calls.agentConversation") == 1
                page.locator(".agent-primary-action").get_by_text("准备镜头视频").click()
                page.get_by_text("确认视频准备", exact=True).wait_for()
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert not console_errors
            finally:
                browser.close()


def _assert_storyboard_entry(page: Page) -> None:
    main_entry = page.locator("#product-main").get_by_role(
        "button",
        name="准备镜头视频",
        exact=True,
    )
    assert main_entry.count() == 1
    assert main_entry.is_visible()
    assert page.locator(".agent-primary-action").get_by_text("准备镜头视频").is_visible()
    assert page.get_by_text("镜头 01").first.is_visible()
    assert page.get_by_text("已生成媒体 1 / 3").is_visible()
    page.wait_for_function(
        "document.querySelector('.shot-media img')?.naturalWidth > 0"
    )
    page.evaluate("window.__deferCompilePreview = true")
    main_entry.click()
    assert page.locator(".storyboard-heading-actions").get_by_role(
        "button",
        name="正在准备…",
        exact=True,
    ).is_visible()
    assert page.locator(".video-admission-panel").is_visible()
    assert page.evaluate("window.__calls.compilePreview") == 1
    page.evaluate("window.__releaseCompilePreview()")
    page.get_by_text("确认视频准备", exact=True).wait_for()
    assert page.get_by_text("已批准关键帧").last.is_visible()
    assert page.get_by_text("角色甲、月台甲、怀表甲").is_visible()
    assert page.evaluate("window.__calls.videoDispatch") == 0


def _assert_two_step_confirmation(page: Page) -> None:
    page.get_by_role("button", name="确认", exact=True).click()
    assert page.locator("#product-main").get_by_role(
        "button",
        name="确认镜头视频",
        exact=True,
    ).is_visible()
    page.locator(".agent-primary-action").get_by_text("确认镜头视频").wait_for()
    page.get_by_role("button", name="预览并确认生成").click()
    page.get_by_text("确认发送镜头 01 视频", exact=True).wait_for()
    card = page.locator(".image-admission-review")
    for text in (
        "doubao-seedance-2-0（非 fast）",
        "720p",
        "6 秒",
        "1 次发送",
        "自动重试 0",
        "$2.00 项目停止线",
        "角色甲、月台甲、怀表甲",
    ):
        assert card.get_by_text(text, exact=False).is_visible()
    assert page.get_by_role("button", name="确认并发送").is_visible()
    assert page.evaluate("window.__calls.videoDispatch") == 0


def _contract_html() -> str:
    return r"""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/apps/studio/styles/tokens.css" />
    <link rel="stylesheet" href="/apps/studio/styles/base.css" />
    <link rel="stylesheet" href="/apps/studio/styles/shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/product-shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/asset-bible.css" />
    <title>Creator Video Entry Contract</title>
  </head>
  <body>
    <div id="app" class="product-mode">
      <div id="product-shell-root"></div>
      <div id="overlay-root"></div>
    </div>
    <script type="module">
      import { createProductShell } from "/apps/studio/src/product-shell.js";

      localStorage.setItem("afs_auth_session_token", "browser-contract-token");
      window.__calls = {
        compilePreview: 0,
        compileConfirm: 0,
        reservePreview: 0,
        agentConversation: 0,
        videoDispatch: 0,
      };
      const projectId = "browser-video-entry";
      const bible = {
        schema_version: "afs.asset_bible.v0.1",
        status: "locked",
        version: 9,
        current_revision_id: "asset-bible-r9",
        locked_revision_id: "asset-bible-r9",
        candidate_set: {
          script_revision_id: "script-r1",
          scene_count: 1,
          shot_count: 3,
        },
        art_direction: {
          visual_style: "写实电影",
          medium: "电影摄影",
          palette: "冷暖对比",
          lighting: "月台侧光",
          confirmed_at: "2026-07-26T00:00:00Z",
        },
        recognition_quality: { status: "pass", issues: [] },
        coverage: {
          coverage_pass: true,
          quality_pass: true,
          scene_total: 1,
          scene_covered: 1,
          shot_total: 3,
          shot_covered: 3,
          unresolved_required: 0,
        },
        assets: [
          {
            stable_id: "character-01", asset_type: "character", display_name: "角色甲", review_state: "approved",
            visual_identity: "稳定面部轮廓", positive_traits: ["深灰外套"], pending_fields: [],
            continuity_states: [{ label: "造型连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
          {
            stable_id: "scene-01", asset_type: "scene", display_name: "月台甲", review_state: "approved",
            visual_identity: "旧站月台空间", positive_traits: ["黄昏侧光"], pending_fields: [],
            continuity_states: [{ label: "空间连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
          {
            stable_id: "prop-01", asset_type: "prop", display_name: "怀表甲", review_state: "approved",
            visual_identity: "蓝铜表壳", positive_traits: ["明确氧化纹理"], pending_fields: [],
            continuity_states: [{ label: "道具连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
        ],
      };
      const workspace = {
        status: "ready",
        project_id: projectId,
        graph_version: 14,
        graph_digest: "graph-v14",
        storyboard: { graph_version: 14, graph_digest: "graph-v14" },
        sequence: {
          script_revisions: [{ node_id: "script-r1", state: "active", metadata: { source_digest: "source" } }],
          sequences: [{ node_id: "sequence-01", state: "active", metadata: { name: "制作序列" } }],
          characters: [{ node_id: "character-01", state: "active", metadata: { display_name: "角色甲" } }],
          scenes: [{ node_id: "scene-01", state: "active", metadata: { name: "月台甲" } }],
          props: [{ node_id: "prop-01", state: "active", metadata: { display_name: "怀表甲" } }],
          reference_sets: [],
          production_aids: [],
          shots: [
            { node_id: "shot-01", state: "active", metadata: { title: "镜头 01", duration_seconds: 6, intent: "推进到怀表" } },
            { node_id: "shot-02", state: "active", metadata: { title: "镜头 02", duration_seconds: 7, intent: "修复过程" } },
            { node_id: "shot-03", state: "active", metadata: { title: "镜头 03", duration_seconds: 5, intent: "完成修复" } },
          ],
          approved_media: [{
            media_node_id: "approved-shot-01",
            media_kind: "image",
            preview_url: "/projects/browser-video-entry/image-assets/keyframe-approved/preview",
            target_node_ids: ["shot-01"],
          }],
          dependencies: [
            { from_id: "scene-01", to_id: "shot-01", relation_type: "contains" },
            { from_id: "scene-01", to_id: "shot-02", relation_type: "contains" },
            { from_id: "scene-01", to_id: "shot-03", relation_type: "contains" },
          ],
          tasks: [],
          candidates: [],
          selections: [],
          reviews: [],
          delivery_plan: [],
          version_history: [],
        },
      };
      const source = {
        shot: { shot_id: "shot-01", label: "镜头 01" },
        keyframe: {
          image_asset_id: "keyframe-approved",
          label: "已批准关键帧",
          aspect_ratio: "16:9",
        },
        references: [
          { image_asset_id: "character-image", label: "角色甲" },
          { image_asset_id: "scene-image", label: "月台甲" },
          { image_asset_id: "prop-image", label: "怀表甲" },
        ],
        prompt_contract: {
          provider_prompt: "角色甲在月台甲修复怀表甲，镜头缓慢推进。",
          camera_movement: "缓慢推进",
        },
      };
      const providerContract = {
        service_id: "seedance_i2v",
        model: "doubao-seedance-2-0",
        model_variant: "non_fast",
        create_endpoint: "/volc/v1/contents/generations/tasks",
        query_endpoint: "/volc/v1/contents/generations/tasks/{id}",
        resolution: "720p",
        duration_sec: 6,
        candidate_count: 1,
        max_dispatches: 1,
        auto_retry: 0,
      };
      const budgetContract = {
        hard_ceiling_usd: "2.00",
        classification: "program_stop_ceiling_not_provider_enforced_estimate_or_actual",
      };
      const compiledManifest = {
        status: "locked",
        manifest_id: "video-manifest",
        manifest_hash: "a".repeat(64),
        source,
        provider_contract: providerContract,
        budget_contract: budgetContract,
        budget: { dispatches_reserved: 0, remaining_dispatches: 1 },
        item: { item_id: "video-shot-01", state: "planned" },
        provider_dispatch_count: 0,
      };
      const preview = (command) => ({
        preview_digest: `${command.type}-digest`,
        command,
        result: {
          manifest: command.type === "compile"
            ? { ...compiledManifest, status: "draft" }
            : {
                ...compiledManifest,
                item: { ...compiledManifest.item, state: "reserved", reservation_token: "reservation" },
                budget: { dispatches_reserved: 1, remaining_dispatches: 0 },
              },
        },
      });
      const runtime = {
        previewVideoAdmissionCommand(request) {
          if (request.command.type === "compile") window.__calls.compilePreview += 1;
          if (request.command.type === "reserve_dispatch") window.__calls.reservePreview += 1;
          if (request.command.type === "compile" && window.__deferCompilePreview) {
            return new Promise((resolve) => {
              window.__releaseCompilePreview = () => {
                window.__deferCompilePreview = false;
                resolve(preview(request.command));
              };
            });
          }
          return Promise.resolve(preview(request.command));
        },
        confirmVideoAdmissionCommand(request) {
          if (request.command.type === "compile") window.__calls.compileConfirm += 1;
          return Promise.resolve({
            result: { manifest: compiledManifest },
            provider_dispatch_count: 0,
          });
        },
        agentChatConversation(payload) {
          window.__calls.agentConversation += 1;
          if (
            payload.canvas_summary.video_readiness_status !== "ready"
            || payload.canvas_summary.video_selected_shot_ready !== 1
            || payload.canvas_summary.video_reference_count !== 3
          ) {
            throw new Error("agent conversation did not receive same-graph video readiness");
          }
          return Promise.resolve({
            mode: "llm",
            provider_calls_started: true,
            reply: "当前镜头已有已批准关键帧和 3 张参考图。请使用页面上的“准备镜头视频”入口审核真实确认卡；我没有创建清单或发送任务。",
            suggested_actions: ["准备镜头视频"],
            provider_lineage: { service_id: "server_codex" },
          });
        },
      };
      const studioState = {
        meta: { projectId, projectName: "视频入口验收" },
        nodes: {},
        edges: {},
        selection: { nodeIds: [], edgeId: null },
        production: {},
        assetBible: bible,
        ui: { projectIdentity: { status: "ready" } },
      };
      const imageAdmission = {
        status: "locked",
        manifest: {
          status: "locked",
          provider_dispatch_count: 1,
          budget: { dispatches_reserved: 0 },
          items: [{ item_id: "approved-keyframe", state: "approved" }],
        },
      };
      const videoAdmission = {
        status: "empty",
        manifest: null,
        readiness: {
          status: "ready",
          shot_id: "shot-01",
          shot_label: "镜头 01",
          first_frame_label: "已批准关键帧",
          reference_count: 3,
          next_action: "预览视频生成确认卡。",
        },
        capability: { configured: true },
        provider_dispatch_count: 0,
      };
      const shell = createProductShell({
        getStudioState: () => studioState,
        getRuntime: () => runtime,
        getStore: () => ({ get: () => studioState }),
        formatError: (error) => String(error?.message || error),
      });
      shell.render({
        loading: false,
        project: { project_id: projectId, name: "视频入口验收", status: "in_progress" },
        studioState,
        sequenceWorkspace: workspace,
        runtimeAssetBible: { authority_mode: "canonical_production_graph", asset_bible: bible },
        imageAdmission,
        videoAdmission,
        mediaGates: { llm: true, image: true, video: true },
        authUser: { user_id: "browser-owner", display_name: "Owner" },
      });
      shell.setSection("storyboard");
      window.__videoEntryReady = true;
    </script>
  </body>
</html>
"""
