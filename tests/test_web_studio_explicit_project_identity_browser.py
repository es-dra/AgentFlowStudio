from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class ExplicitProjectIdentityHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/__explicit_project_identity.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/projects/project-a/studio-state":
            self._json({
                "project_id": "project-a",
                "source": "runtime",
                "state_version": "studio_state:v1",
                "state": {
                    "meta": {
                        "projectId": "project-a",
                        "projectName": "项目甲",
                        "canvasName": "第一集",
                        "seq": 1,
                    },
                    "nodes": {
                        "script_truth_revision_revision-a": {
                            "id": "script_truth_revision_revision-a",
                            "type": "script",
                            "title": "甲项目剧本",
                            "content": "甲项目原始故事：纸船逆流而上。",
                            "prompt": "甲项目原始故事：纸船逆流而上。",
                            "status": "complete",
                            "params": {
                                "scriptCoreProjection": "script_core_truth_projection",
                                "scriptRevision": {
                                    "project_id": "project-a",
                                    "revision_id": "revision-a",
                                    "source_kind": "script",
                                    "source_digest": "a" * 64,
                                    "source_text": "甲项目原始故事：纸船逆流而上。",
                                    "analysis_state": "ready",
                                },
                            },
                        },
                    },
                    "edges": {},
                    "order": ["script_truth_revision_revision-a"],
                    "assets": [],
                    "assetBible": {},
                    "production": {
                        "script_core_truth_projection": {
                            "project_id": "project-a",
                            "current_revision_id": "revision-a",
                            "source_digest": "a" * 64,
                            "source_text": "甲项目原始故事：纸船逆流而上。",
                            "source_kind": "script",
                            "analysis_state": "ready",
                        },
                    },
                },
            })
            return
        if path == "/projects/project-a/product-overview":
            self._json({
                "project": {
                    "project_id": "project-a",
                    "name": "项目甲",
                    "episode": "第一集",
                },
            })
            return
        if path == "/projects/project-a/m5/sequence-workspace":
            self._json({
                "status": "planning_required",
                "project_id": "project-b",
                "graph_version": 0,
                "graph_digest": "0" * 64,
                "provider_dispatch_count": 0,
            })
            return
        if path in {
            "/projects/project-a/image-assets",
            "/projects/project-a/visual-assets",
        }:
            self._json({"assets": []})
            return
        if path == "/projects":
            self._json({
                "projects": [{
                    "project_id": "project-a",
                    "name": "项目甲",
                    "episode": "第一集",
                }],
            })
            return
        if path == "/product/workspace-overview":
            self._json({
                "projects": [{
                    "project_id": "project-a",
                    "name": "项目甲",
                    "episode": "第一集",
                }],
            })
            return
        if path in {"/favicon.ico", "/favicon.svg"}:
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def do_PUT(self) -> None:
        if urlparse(self.path).path == "/projects/project-a/studio-state":
            self._json({"state_version": "studio_state:v2"})
            return
        self.send_response(404)
        self.end_headers()

    def _json(self, payload: dict[str, object]) -> None:
        import json

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_explicit_project_url_replaces_stale_store_and_survives_refresh() -> None:
    with _browser_page() as (page, base_url, errors):
        url = (
            f"{base_url}/__explicit_project_identity.html"
            "?project=project-a&episode=episode-a"
        )
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_function("window.__contractReady === true")

        assert page.get_by_role(
            "button",
            name="当前项目：项目甲 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        body = page.locator("body").inner_text()
        assert page.evaluate(
            'window.__studioState.nodes["script_truth_revision_revision-a"].params.scriptRevision.source_text',
        ) == "甲项目原始故事：纸船逆流而上。"
        assert "完整剧本已保存。" in body
        assert "乙项目不应出现" not in body
        assert page.evaluate("window.__studioState.meta.projectId") == "project-a"
        assert page.evaluate("window.__runtimeProjectId") == "project-a"
        assert page.get_by_text("Runtime returned a different project identity").count() == 0

        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("window.__contractReady === true")
        assert page.evaluate("window.__studioState.meta.projectId") == "project-a"
        assert page.get_by_role(
            "button",
            name="当前项目：项目甲 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        body = page.locator("body").inner_text()
        assert "项目甲" in body
        assert page.evaluate(
            'window.__studioState.nodes["script_truth_revision_revision-a"].params.scriptRevision.source_text',
        ) == "甲项目原始故事：纸船逆流而上。"
        assert "完整剧本已保存。" in body
        assert "乙项目不应出现" not in body
        assert not errors


def test_invalid_explicit_project_is_terminal_chinese_fail_closed() -> None:
    with _browser_page() as (page, base_url, errors):
        page.goto(
            f"{base_url}/__explicit_project_identity.html"
            "?project=missing-project&episode=episode-missing&invalid=1",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")

        assert page.get_by_role("heading", name="项目不存在", exact=True).is_visible()
        assert page.get_by_text(
            "项目不存在或已被移除。没有加载其他项目，也未发送任何修改请求。",
            exact=True,
        ).is_visible()
        assert page.get_by_role("button", name="重新加载当前项目", exact=True).count() == 0
        assert page.get_by_role("button", name="选择其他项目", exact=True).is_visible()
        body = page.locator("body").inner_text()
        assert "Runtime returned a different project identity" not in body
        assert "project_not_found" not in body
        assert "乙项目不应出现" not in body
        assert page.evaluate("window.__calls.mutations") == 0
        assert page.evaluate("window.__calls.image") == 0
        assert page.evaluate("window.__calls.video") == 0
        assert not errors


def test_identity_mismatch_allows_one_reload_then_stops_the_loop() -> None:
    with _browser_page() as (page, base_url, errors):
        page.goto(
            f"{base_url}/__explicit_project_identity.html"
            "?project=project-a&episode=episode-a&mismatch=1",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__contractReady === true")

        retry = page.get_by_role("button", name="重新加载当前项目", exact=True)
        assert retry.is_visible()
        retry.click()
        page.get_by_text(
            "重新加载后仍无法验证此项目。为保护项目内容，已停止继续重试；"
            "请选择其他项目或稍后再打开此链接。",
            exact=True,
        ).wait_for()
        assert page.get_by_role(
            "button",
            name="重新加载当前项目",
            exact=True,
        ).count() == 0
        assert page.get_by_role("button", name="选择其他项目", exact=True).is_visible()
        body = page.locator("body").inner_text()
        assert "Runtime returned a different project identity" not in body
        assert "乙项目不应出现" not in body
        assert page.evaluate("window.__calls.image") == 0
        assert page.evaluate("window.__calls.video") == 0
        assert not errors


class _browser_page:
    def __enter__(self):
        handler = partial(ExplicitProjectIdentityHandler, directory=str(ROOT))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.playwright_context = sync_playwright()
        self.playwright = self.playwright_context.__enter__()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
        )
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("console", lambda message: (
            self.errors.append(message.text)
            if message.type in {"error", "warning"}
            else None
        ))
        self.page.on("response", lambda response: (
            self.errors.append(f"HTTP {response.status} {response.url}")
            if response.status >= 400
            else None
        ))
        return self.page, f"http://127.0.0.1:{self.server.server_port}", self.errors

    def __exit__(self, exc_type, exc, traceback):
        self.context.close()
        self.browser.close()
        self.playwright_context.__exit__(exc_type, exc, traceback)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


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
    <title>Explicit project identity contract</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module">
      import { renderCanvas } from "/apps/studio/src/canvas-view.js";
      import { beginProjectIdentityLoad } from "/apps/studio/src/project-identity-gate.js";
      import { createStore } from "/apps/studio/src/store.js";
      import { createProjectController } from "/apps/studio/src/studio-project-controller.js";
      import { applyScriptCoreTruthProjection } from "/apps/studio/src/script-core-truth-projection.js";
      import {
        createStudioProductShell,
        mountStudioDom,
      } from "/apps/studio/src/studio-product-bootstrap.js";

      const params = new URLSearchParams(window.location.search);
      const requestedProjectId = params.get("project");
      const requestedEpisodeId = params.get("episode");
      const invalid = params.get("invalid") === "1";
      const mismatch = params.get("mismatch") === "1";
      const staleProjectId = "project-b";
      window.__calls = { mutations: 0, image: 0, video: 0 };

      const store = createStore(staleProjectId);
      store.set((state) => {
        state.meta.projectId = staleProjectId;
        state.meta.projectName = "项目乙";
        state.meta.episodeId = "episode-b";
        state.nodes = {
          "script-b": {
            id: "script-b",
            type: "script",
            title: "乙项目剧本",
            content: "乙项目不应出现",
            prompt: "乙项目不应出现",
            x: 80,
            y: 80,
            w: 340,
            h: 220,
            status: "complete",
            params: {},
          },
        };
        state.order = ["script-b"];
        state.selection = { nodeIds: ["script-b"], edgeId: null };
      }, { history: false });

      const stateA = {
        meta: {
          projectId: requestedProjectId,
          projectName: "项目甲",
          episodeId: requestedEpisodeId,
          canvasName: "第一集",
          seq: 1,
        },
        nodes: {
          "script_truth_revision_revision-a": {
            id: "script_truth_revision_revision-a",
            type: "script",
            title: "甲项目剧本",
            content: "甲项目原始故事：纸船逆流而上。",
            prompt: "甲项目原始故事：纸船逆流而上。",
            x: 80,
            y: 80,
            w: 360,
            h: 240,
            status: "complete",
            params: {
              scriptCoreProjection: "script_core_truth_projection",
              scriptRevision: {
                project_id: requestedProjectId,
                revision_id: "revision-a",
                source_kind: "script",
                source_digest: "a".repeat(64),
                source_text: "甲项目原始故事：纸船逆流而上。",
                analysis_state: "ready",
              },
            },
          },
        },
        edges: {},
        order: ["script_truth_revision_revision-a"],
        assets: [],
        assetBible: {},
        production: {
          script_core_truth_projection: {
            project_id: requestedProjectId,
            current_revision_id: "revision-a",
            source_digest: "a".repeat(64),
            source_text: "甲项目原始故事：纸船逆流而上。",
            source_kind: "script",
            analysis_state: "ready",
          },
        },
        viewport: { x: 0, y: 0, scale: 1 },
        selection: { nodeIds: ["script_truth_revision_revision-a"], edgeId: null },
      };
      const planningWorkspace = {
        status: "planning_required",
        project_id: requestedProjectId,
        graph_version: 0,
        graph_digest: "0".repeat(64),
        provider_dispatch_count: 0,
      };
      const runtimeA = {
        projectId: requestedProjectId,
        listProjects: async () => ({
          projects: invalid ? [] : [{
            project_id: requestedProjectId,
            name: "项目甲",
            episode: "第一集",
            studio_state_meta: {
              projectName: "项目甲",
              canvasName: "第一集",
            },
          }],
        }),
        loadStudioState: async () => {
          if (invalid) {
            const error = new Error("Runtime project not found");
            error.status = 404;
            error.errorCode = "project_not_found";
            throw error;
          }
          return {
            project_id: requestedProjectId,
            source: "runtime",
            state_version: "studio_state:v1",
            state: structuredClone(stateA),
          };
        },
        saveStudioState: async () => {
          window.__calls.mutations += 1;
          return { state_version: "studio_state:v1" };
        },
        listImageAssets: async () => ({ assets: [] }),
        listVisualAssets: async () => ({ assets: [] }),
        workspaceOverview: async () => ({
          projects: invalid ? [] : [{
            project_id: requestedProjectId,
            name: "项目甲",
            episode: "第一集",
          }],
        }),
        projectOverview: async () => ({
          project: {
            project_id: requestedProjectId,
            name: "项目甲",
            episode: "第一集",
          },
        }),
        sequenceWorkspace: async () => mismatch
          ? { ...planningWorkspace, project_id: "project-b" }
          : planningWorkspace,
        loadAssetBible: async () => null,
        loadImageAdmission: async () => null,
        loadVideoAdmission: async () => null,
        health: async () => ({
          provider_gates: { llm: true, image: false, video: false },
        }),
      };

      let runtime = runtimeA;
      beginProjectIdentityLoad(requestedProjectId, "");
      const { editorParking, editorShell } = mountStudioDom();
      let shell = null;
      const render = () => {
        renderCanvas(store.get(), store);
        shell?.updateStudioState(store.get());
      };
      const controller = createProjectController({
        store,
        getRuntime: () => runtime,
        setRuntime: (nextRuntime) => { runtime = nextRuntime; },
        render,
        onProjectReady: async () => {},
      });
      shell = createStudioProductShell({
        getStore: () => store,
        getRuntime: () => runtime,
        getCanvasShell: () => editorShell,
        getCanvasParking: () => editorParking,
        createRuntime: () => runtimeA,
        isRuntimeCurrent: (candidate) => candidate === runtime,
        formatError: (error) => String(error?.message || error),
        onRetry: async () => {
          await controller.retryCurrentProject();
          await shell.refresh(runtime);
        },
        onProjectIdentityInvalid: (error) => controller.recoverProjectAccessDenied(error),
        onProjectSurfaceReady: (projectId) => controller.markProjectSurfaceReady(projectId),
      });
      render();
      await controller.ensureAccessibleStartupProject();
      store.set((state) => {
        applyScriptCoreTruthProjection(state, {
          schema_version: "afs.script_core_truth.v0.1",
          project_id: requestedProjectId,
          current_revision_id: "revision-a",
          current_revision: {
            project_id: requestedProjectId,
            revision_id: "revision-a",
            source_kind: "script",
            source_text: "甲项目原始故事：纸船逆流而上。",
            source_digest: "a".repeat(64),
            source_length: 16,
            analysis_state: "ready",
          },
          revision_history: [],
          assets: [],
          asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
          analysis_state: "ready",
        });
      }, { history: false });
      render();
      await shell.refresh(runtime);
      window.__studioState = store.get();
      window.__runtimeProjectId = runtime.projectId;
      window.__contractReady = true;
    </script>
  </body>
</html>
"""
