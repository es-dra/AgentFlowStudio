from __future__ import annotations

import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class IdeaOnboardingHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/__idea_onboarding.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in {"/favicon.ico", "/favicon.svg"}:
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def test_short_idea_routes_to_text_expansion_then_refreshes_durable_revision() -> None:
    with _browser_page(viewport={"width": 1440, "height": 900}) as (page, base_url, errors):
        page.goto(
            f"{base_url}/__idea_onboarding.html?project=idea-project-a&flow=idea",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")

        assert page.get_by_text("想法已保存。", exact=True).is_visible()
        assert page.locator(".agent-primary-action").get_by_text(
            "扩写并分析故事",
            exact=True,
        ).is_visible()
        assert page.locator('.node[data-node-id="script_truth_revision_revision-1"]').is_visible()
        assert "创作想法：月光下，一只纸船逆流。" in page.locator("body").inner_text()
        assert "制作方案处理中" not in page.locator("body").inner_text()
        assert "请求参数校验失败" not in page.locator("body").inner_text()
        _capture(page, "01-short-idea-saved-real-canvas-1440x900.png")

        page.locator(".agent-primary-action").click()
        page.get_by_text("故事扩写已准备好。", exact=True).wait_for()
        assert page.locator(".agent-primary-action").get_by_text(
            "审看扩写结果",
            exact=True,
        ).is_visible()
        assert page.get_by_label("编辑剧本化预览文本").input_value() == (
            "月光下，纸船逆流而上，送回一封迟到多年的信。"
        )
        expansion_surface = page.locator(".story-expansion-entry")
        assert expansion_surface.get_by_role(
            "button",
            name="扩写并分析故事",
            exact=True,
        ).count() == 0
        review_existing = expansion_surface.get_by_role(
            "button",
            name="审看扩写结果",
            exact=True,
        )
        assert review_existing.is_visible()
        review_existing.click()
        assert page.evaluate("window.__calls.textPreview") == 1
        assert page.get_by_label("编辑剧本化预览文本").is_visible()
        _capture(page, "02-story-expansion-review-real-canvas-1440x900.png")

        page.get_by_role("button", name="应用", exact=True).click()
        page.get_by_text("剧本文本：月光下，纸船逆流而上", exact=False).wait_for()
        assert page.get_by_role("button", name="准备制作方案", exact=True).is_visible()
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("window.__contractReady === true")
        page.get_by_text("剧本文本：月光下，纸船逆流而上", exact=False).wait_for()
        assert page.get_by_role("button", name="准备制作方案", exact=True).is_visible()
        assert page.locator('.node[data-node-id="script_truth_revision_revision-2"]').is_visible()

        page.set_viewport_size({"width": 1920, "height": 1080})
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        _capture(page, "03-durable-script-refresh-real-canvas-1920x1080.png")
        assert page.evaluate("window.__calls") == {
            "textPreview": 1,
            "scriptRevision": 1,
            "recoverPreview": 0,
            "applyShotPlan": 0,
            "image": 0,
            "video": 0,
        }
        assert page.evaluate(
            "window.__studioState.production.script_core_truth_projection.current_revision_id",
        ) == "revision-2"
        assert not errors


def test_complete_script_recovers_same_preview_then_applies_one_graph_update() -> None:
    with _browser_page(viewport={"width": 1440, "height": 900}) as (page, base_url, errors):
        page.goto(
            f"{base_url}/__idea_onboarding.html?project=script-project-b&flow=script",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")

        assert page.get_by_role(
            "button",
            name="当前项目：人工测试项目 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        script_node = page.locator('.node[data-node-id="script-complete"]')
        assert script_node.is_visible()
        assert "邮差把无人认领的信放进纸船" in script_node.locator("textarea").input_value()
        assert page.get_by_role("button", name="拆分并审阅分镜", exact=True).is_visible()
        page.get_by_role("button", name="拆分并审阅分镜", exact=True).click()

        page.get_by_text("分镜候选已准备好。", exact=True).wait_for()
        assert page.get_by_text("河岸送信", exact=False).is_visible()
        assert page.get_by_text("旧邮局回响", exact=False).is_visible()
        task_panel = page.locator(".agent-current-task-review")
        assert task_panel.get_by_text("总时长约 12 秒", exact=False).is_visible()
        assert "已排队" not in task_panel.inner_text()
        assert "整理上下文" not in task_panel.inner_text()
        assert page.evaluate("window.__calls.textPreview") == 1
        assert page.evaluate("window.__calls.recoverPreview") >= 1
        assert page.evaluate("window.__calls.image") == 0
        assert page.evaluate("window.__calls.video") == 0
        _capture(page, "04-script-storyboard-recovered-review-1440x900.png")

        task_panel.get_by_role("button", name="取消", exact=True).click()
        assert page.get_by_role("button", name="拆分并审阅分镜", exact=True).is_visible()
        assert page.evaluate("window.__workspace.status") == "planning_required"

        page.get_by_role("button", name="拆分并审阅分镜", exact=True).click()
        page.get_by_text("分镜候选已准备好。", exact=True).wait_for()
        page.locator(".agent-current-task-review").get_by_role(
            "button",
            name="应用",
            exact=True,
        ).click()
        page.get_by_text("制作方案已保存：0 个角色、2 个场景、2 个镜头。", exact=True).wait_for()
        assert page.evaluate("window.__workspace.graph_version") == 1
        assert page.evaluate("window.__calls.applyShotPlan") == 1
        assert page.evaluate("window.__calls.textPreview") == 2

        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("window.__contractReady === true")
        assert page.get_by_text("制作方案已保存：0 个角色、2 个场景、2 个镜头。", exact=True).is_visible()
        page.get_by_role("tab", name="故事板", exact=True).click()
        assert page.get_by_role("button", name="镜头 1：河岸送信", exact=True).is_visible()
        second_scene = page.get_by_role("button", name=re.compile(r"^02\s+旧邮局"))
        assert second_scene.is_visible()
        second_scene.click()
        assert page.get_by_role("button", name="镜头 1：旧邮局回响", exact=True).is_visible()
        assert page.evaluate("window.__calls.applyShotPlan") == 1
        assert page.evaluate("window.__calls.image") == 0
        assert page.evaluate("window.__calls.video") == 0
        _capture(page, "05-script-storyboard-applied-refresh-1440x900.png")
        assert not errors


def test_explicit_url_projects_never_cross_project_on_switch_or_refresh() -> None:
    with _browser_page(viewport={"width": 1440, "height": 900}) as (page, base_url, errors):
        page.goto(
            f"{base_url}/__idea_onboarding.html?project=idea-project-a&flow=idea",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")
        assert page.get_by_role(
            "button",
            name="当前项目：项目甲：纸船 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        assert "月光下，一只纸船逆流" in page.locator("body").inner_text()

        page.goto(
            f"{base_url}/__idea_onboarding.html?project=script-project-b&flow=script",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")
        assert page.get_by_role(
            "button",
            name="当前项目：人工测试项目 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        body = page.locator("body").inner_text()
        script_value = page.locator(
            '.node[data-node-id="script-complete"] textarea',
        ).input_value()
        assert "邮差把无人认领的信放进纸船" in script_value
        assert "月光下，一只纸船逆流" not in body
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("window.__contractReady === true")
        body = page.locator("body").inner_text()
        assert "人工测试项目" in body
        script_value = page.locator(
            '.node[data-node-id="script-complete"] textarea',
        ).input_value()
        assert "邮差把无人认领的信放进纸船" in script_value
        assert "项目甲：纸船" not in body
        assert "月光下，一只纸船逆流" not in body
        assert page.evaluate("window.__studioState.meta.projectId") == "script-project-b"
        assert not errors


class _browser_page:
    def __init__(self, *, viewport: dict[str, int]) -> None:
        self.viewport = viewport

    def __enter__(self):
        handler = partial(IdeaOnboardingHandler, directory=str(ROOT))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.playwright_context = sync_playwright()
        self.playwright = self.playwright_context.__enter__()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        self.page = self.browser.new_page(viewport=self.viewport)
        self.errors: list[str] = []
        self.page.on(
            "console",
            lambda message: self.errors.append(message.text)
            if message.type in {"error", "warning"}
            else None,
        )
        self.page.on(
            "response",
            lambda response: self.errors.append(f"{response.status} {response.url}")
            if response.status >= 400
            else None,
        )
        base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        return self.page, base_url, self.errors

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.browser.close()
        self.playwright_context.__exit__(exc_type, exc, traceback)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _capture(page: Page, name: str) -> None:
    evidence_dir = os.environ.get("AFS_BROWSER_EVIDENCE_DIR", "").strip()
    if not evidence_dir:
        return
    path = Path(evidence_dir)
    path.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path / name), full_page=False)


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
    <link rel="stylesheet" href="/apps/studio/styles/canvas.css" />
    <link rel="stylesheet" href="/apps/studio/styles/product-shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/asset-bible.css" />
    <title>Creator text contracts</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module">
      import { mountStudioDom, createStudioProductShell } from "/apps/studio/src/studio-product-bootstrap.js";
      import { renderCanvas } from "/apps/studio/src/canvas-view.js";
      import { applyScriptCoreTruthProjection } from "/apps/studio/src/script-core-truth-projection.js";
      import { applyProductionGraphCanvasProjection } from "/apps/studio/src/production-graph-workspace-projection.js";

      const params = new URLSearchParams(window.location.search);
      const projectId = params.get("project");
      const flow = params.get("flow");
      const isIdea = flow === "idea";
      const originalIdea = "月光下，一只纸船逆流。";
      const revisedIdea = "月光下，纸船逆流而上，送回一封迟到多年的信。";
      const fullScript = "第一场\n外景，河岸，清晨。邮差把无人认领的信放进纸船，纸船逆流而上。\n第二场\n内景，旧邮局，夜。信封在空柜台上发出轻响。";
      const projectName = isIdea ? "项目甲：纸船" : "人工测试项目";
      const durableKey = `afs-contract:${projectId}`;
      const callsKey = `afs-contract-calls:${projectId}`;
      const stored = JSON.parse(localStorage.getItem(durableKey) || "null");
      window.__calls = JSON.parse(localStorage.getItem(callsKey) || "null")
        || { textPreview: 0, recoverPreview: 0, scriptRevision: 0, applyShotPlan: 0, image: 0, video: 0 };
      const persistCalls = () => localStorage.setItem(callsKey, JSON.stringify(window.__calls));
      const studioState = stored?.studioState || {
        meta: { projectId, projectName, seq: 1 },
        nodes: {},
        edges: {},
        order: [],
        selection: { nodeIds: [], edgeId: null },
        production: {},
        viewport: { x: 0, y: 0, scale: 1 },
        ui: { projectIdentity: { status: "ready" } },
      };
      studioState.meta.projectId = projectId;
      studioState.meta.projectName = projectName;
      studioState.ui = { ...(studioState.ui || {}), projectIdentity: { status: "ready" } };
      studioState.viewport = studioState.viewport || { x: 0, y: 0, scale: 1 };

      if (!stored && isIdea) {
        applyScriptCoreTruthProjection(studioState, {
          schema_version: "afs.script_core_truth.v0.1",
          project_id: projectId,
          current_revision_id: "revision-1",
          current_revision: {
            project_id: projectId,
            revision_id: "revision-1",
            source_kind: "idea",
            source_text: originalIdea,
            source_digest: "a".repeat(64),
            source_length: originalIdea.length,
            analysis_state: "analysis_required",
          },
          revision_history: [],
          assets: [],
          asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
          analysis_state: "analysis_required",
        });
      }
      if (!stored && !isIdea) {
        studioState.nodes["script-complete"] = {
          id: "script-complete",
          type: "script",
          title: "完整剧本",
          x: 80,
          y: 80,
          w: 340,
          h: 300,
          content: fullScript,
          prompt: fullScript,
          status: "complete",
          params: {},
        };
        studioState.order = ["script-complete"];
        studioState.selection = { nodeIds: ["script-complete"], edgeId: null };
      }
      window.__workspace = stored?.workspace || {
        status: "planning_required",
        project_id: projectId,
        graph_version: 0,
        graph_digest: "",
        provider_dispatch_count: 0,
      };
      if (window.__workspace.status === "ready") {
        applyProductionGraphCanvasProjection(studioState, window.__workspace);
      }

      const previewByClient = new Map();
      let clientSequence = Number(sessionStorage.getItem(`${durableKey}:clients`) || 0);
      const shotPlan = {
        total_shots: 2,
        estimated_duration_sec: 12,
        scenes: [
          {
            title: "河岸",
            purpose: "建立送信任务",
            shots: [{
              title: "河岸送信",
              duration_sec: 6,
              shot_size: "中景",
              camera_angle: "平视",
              movement: "缓慢推进",
              blocking: "邮差放下纸船",
              sound: "水声",
              transition: "切",
              narrative_purpose: "建立任务",
            }],
          },
          {
            title: "旧邮局",
            purpose: "完成情绪回响",
            shots: [{
              title: "旧邮局回响",
              duration_sec: 6,
              shot_size: "近景",
              camera_angle: "略低",
              movement: "静止",
              blocking: "信封在柜台轻响",
              sound: "纸张摩擦",
              transition: "淡出",
              narrative_purpose: "收束情绪",
            }],
          },
        ],
      };
      const graphWorkspace = () => ({
        status: "ready",
        project_id: projectId,
        graph_version: 1,
        graph_digest: "c".repeat(64),
        migration_state: "graph_backed_single_truth",
        sequence: {
          script_revisions: [{ node_id: "revision-contract", state: "active", metadata: { title: "完整剧本" } }],
          sequences: [{ node_id: "sequence-contract", state: "active", metadata: { name: "制作序列", target_duration_seconds: 12 } }],
          characters: [],
          scenes: [
            { node_id: "scene-river", state: "active", metadata: { name: "河岸", order: 1 } },
            { node_id: "scene-post", state: "active", metadata: { name: "旧邮局", order: 2 } },
          ],
          props: [],
          reference_sets: [],
          production_aids: [],
          shots: [
            { node_id: "shot-river", state: "active", metadata: { title: "河岸送信", duration_seconds: 6, order: 1 } },
            { node_id: "shot-post", state: "active", metadata: { title: "旧邮局回响", duration_seconds: 6, order: 2 } },
          ],
          approved_media: [],
          dependencies: [
            { from_id: "revision-contract", to_id: "sequence-contract", relation_type: "derived_from" },
            { from_id: "sequence-contract", to_id: "scene-river", relation_type: "contains" },
            { from_id: "sequence-contract", to_id: "scene-post", relation_type: "contains" },
            { from_id: "scene-river", to_id: "shot-river", relation_type: "contains" },
            { from_id: "scene-post", to_id: "shot-post", relation_type: "contains" },
          ],
          tasks: [
            { work_id: "work-shot-river", state: "planned" },
            { work_id: "work-shot-post", state: "planned" },
          ],
          candidates: [],
          selections: [],
          reviews: [],
          delivery_plan: [],
          version_history: [{ version: 1 }],
        },
        storyboard: {
          mode: "read_only",
          graph_version: 1,
          graph_digest: "c".repeat(64),
        },
        provider_dispatch_count: 0,
        cost_usd: 0,
      });
      const runtime = {
        projectId,
        newEmbeddedCreativeClientRequestId: () => {
          clientSequence += 1;
          sessionStorage.setItem(`${durableKey}:clients`, String(clientSequence));
          return `cli_contract_${flow}_${clientSequence}`;
        },
        previewEmbeddedCreativeAction: async (payload, options) => {
          window.__calls.textPreview += 1;
          persistCalls();
          const expectedSource = isIdea ? (
            studioState.production.script_core_truth_projection.source_kind === "idea"
              ? originalIdea
              : revisedIdea
          ) : fullScript;
          if (payload.source_text !== expectedSource) throw new Error("preview lost exact visible source");
          const response = isIdea ? {
            mode: "llm",
            provider_calls_started: true,
            preview: {
              revised_text: revisedIdea,
              change_summary: ["补充故事目标和情绪推进"],
              rationale: "保留原意并形成可继续开发的故事。",
            },
            creative_task: {},
            provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
            graph_mutation: { mutated: false, scope: "preview_only" },
            safe_manifest: { request_digest: "1".repeat(64), source_digest: "2".repeat(64), image_video_generation_enabled: false },
            cost_usd: 0,
          } : {
            mode: "llm",
            action_type: "shot_breakdown",
            provider_calls_started: true,
            preview: {
              revised_text: "剧本被拆分为河岸送信与旧邮局回响两个连续镜头。",
              change_summary: ["建立两场连续结构", "明确镜头顺序与时长"],
              rationale: "只生成分镜文本预览。",
              shot_plan: shotPlan,
            },
            creative_task: {},
            provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
            graph_mutation: { mutated: false, scope: "preview_only" },
            safe_manifest: { request_digest: "3".repeat(64), source_digest: "4".repeat(64), image_video_generation_enabled: false },
            cost_usd: 0,
          };
          previewByClient.set(options.clientRequestId, response);
          if (!isIdea && window.__calls.textPreview === 1) {
            const error = new Error("文本处理等待超时；原剧本已保留。");
            error.status = 504;
            error.clientRequestId = options.clientRequestId;
            throw error;
          }
          return response;
        },
        recoverEmbeddedCreativeActionByClient: async (clientRequestId) => {
          window.__calls.recoverPreview += 1;
          persistCalls();
          const recovered = previewByClient.get(clientRequestId);
          if (!recovered) {
            const error = new Error("still processing");
            error.status = 404;
            throw error;
          }
          return { ...recovered, recovered: true };
        },
        createScriptRevision: async (payload) => {
          window.__calls.scriptRevision += 1;
          persistCalls();
          if (payload.source_text !== revisedIdea || payload.parent_revision_id !== "revision-1") {
            throw new Error("revision apply contract mismatch");
          }
          const projection = {
            schema_version: "afs.script_core_truth.v0.1",
            project_id: projectId,
            current_revision_id: "revision-2",
            current_revision: {
              project_id: projectId,
              revision_id: "revision-2",
              parent_revision_id: "revision-1",
              source_kind: "script",
              source_text: revisedIdea,
              source_digest: "b".repeat(64),
              source_length: revisedIdea.length,
              analysis_state: "analysis_required",
            },
            revision_history: [],
            assets: [],
            asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
            analysis_state: "analysis_required",
          };
          localStorage.setItem(durableKey, JSON.stringify({ studioState, projection, workspace: window.__workspace }));
          return { revision: { revision_id: "revision-2" }, projection };
        },
        applyEmbeddedCreativeShotPlan: async (_clientRequestId, payload) => {
          if (payload.expected_graph_version !== 0 || payload.expected_request_digest !== "3".repeat(64)) {
            throw new Error("shot plan apply contract mismatch");
          }
          window.__calls.applyShotPlan += 1;
          persistCalls();
          window.__workspace = graphWorkspace();
          return {
            status: "applied",
            graph_version: 1,
            graph_digest: "c".repeat(64),
            workspace: window.__workspace,
            provider_dispatch_count: 0,
          };
        },
        sequenceWorkspace: async () => window.__workspace,
        loadVideoAdmission: async () => null,
      };

      const { editorParking, editorShell } = mountStudioDom();
      let shell = null;
      const persist = () => {
        localStorage.setItem(durableKey, JSON.stringify({ studioState, workspace: window.__workspace }));
      };
      const store = {
        get: () => studioState,
        set: (mutator) => {
          mutator(studioState);
          renderCanvas(studioState, store);
          shell?.updateStudioState(studioState);
        },
        flushRuntimeSave: async () => persist(),
        setRuntimePersistenceMode: () => {},
      };
      shell = createStudioProductShell({
        getStore: () => store,
        getRuntime: () => runtime,
        getCanvasShell: () => editorShell,
        getCanvasParking: () => editorParking,
        formatError: (error) => String(error?.message || error),
      });
      renderCanvas(studioState, store);
      shell.render({
        loading: false,
        project: { project_id: projectId, name: projectName, goal: projectName },
        workspace: { projects: [{ project_id: projectId, name: projectName }] },
        sequenceWorkspace: window.__workspace,
        studioState,
        mediaGates: { llm: true, image: false, video: false },
      });
      window.__studioState = studioState;
      window.__contractReady = true;
    </script>
  </body>
</html>
"""
