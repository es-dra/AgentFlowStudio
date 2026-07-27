from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class IdeaOnboardingHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path == "/__idea_onboarding.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in {"/favicon.ico", "/favicon.svg"}:
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def test_short_idea_routes_to_text_expansion_then_durable_revision_without_media() -> None:
    handler = partial(IdeaOnboardingHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                http_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type in {"error", "warning"}
                    else None,
                )
                page.on(
                    "response",
                    lambda response: http_errors.append(f"{response.status} {response.url}")
                    if response.status >= 400
                    else None,
                )
                page.goto(f"{base_url}/__idea_onboarding.html", wait_until="domcontentloaded")
                page.wait_for_function("window.__ideaReady === true")

                assert page.get_by_text("想法已保存。", exact=True).is_visible()
                assert page.locator(".agent-primary-action").get_by_text(
                    "扩写并分析故事",
                    exact=True,
                ).is_visible()
                assert "创作想法：月光下，一只纸船逆流。" in page.locator("body").inner_text()
                assert "制作方案处理中" not in page.locator("body").inner_text()
                assert "请求参数校验失败" not in page.locator("body").inner_text()
                _capture(page, "01-short-idea-saved-1440x900.png")

                page.locator(".agent-primary-action").click()
                page.get_by_text("故事扩写已准备好。", exact=True).wait_for()
                assert page.get_by_role("button", name="审看扩写结果", exact=True).is_visible()
                assert page.get_by_label("编辑剧本化预览文本").input_value() == (
                    "月光下，纸船逆流而上，送回一封迟到多年的信。"
                )
                _capture(page, "02-story-expansion-review-1440x900.png")

                page.get_by_role("button", name="应用", exact=True).click()
                page.get_by_text("剧本文本：月光下，纸船逆流而上", exact=False).wait_for()
                page.set_viewport_size({"width": 1920, "height": 1080})
                assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
                _capture(page, "03-durable-script-applied-1920x1080.png")
                assert page.evaluate("window.__calls") == {
                    "textPreview": 1,
                    "scriptRevision": 1,
                    "image": 0,
                    "video": 0,
                }
                assert page.evaluate(
                    "window.__studioState.production.script_core_truth_projection.current_revision_id",
                ) == "revision-2"
                assert not console_errors, http_errors
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _capture(page, name: str) -> None:
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
    <link rel="stylesheet" href="/apps/studio/styles/product-shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/asset-bible.css" />
    <title>Idea Onboarding Contract</title>
  </head>
  <body>
    <div id="app" class="product-mode">
      <div id="product-shell-root"></div>
      <div id="overlay-root"></div>
    </div>
    <script type="module">
      import { createProductShell } from "/apps/studio/src/product-shell.js";
      import { applyScriptCoreTruthProjection } from "/apps/studio/src/script-core-truth-projection.js";

      const projectId = "idea-browser-contract";
      const original = "月光下，一只纸船逆流。";
      const revised = "月光下，纸船逆流而上，送回一封迟到多年的信。";
      const studioState = {
        meta: { projectId, projectName: "新故事", seq: 1 },
        nodes: {},
        edges: {},
        order: [],
        selection: { nodeIds: [], edgeId: null },
        production: {},
        ui: { projectIdentity: { status: "ready" } },
      };
      applyScriptCoreTruthProjection(studioState, {
        schema_version: "afs.script_core_truth.v0.1",
        project_id: projectId,
        current_revision_id: "revision-1",
        current_revision: {
          revision_id: "revision-1",
          source_kind: "idea",
          source_text: original,
          source_digest: "a".repeat(64),
          source_length: original.length,
          analysis_state: "analysis_required",
        },
        revision_history: [],
        assets: [],
        asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
        analysis_state: "analysis_required",
      });

      window.__calls = { textPreview: 0, scriptRevision: 0, image: 0, video: 0 };
      const runtime = {
        projectId,
        newEmbeddedCreativeClientRequestId: () => "cli_idea_browser",
        previewEmbeddedCreativeAction: async (payload) => {
          window.__calls.textPreview += 1;
          if (payload.source_text !== original) throw new Error("preview lost exact source");
          return {
            mode: "llm",
            provider_calls_started: true,
            preview: {
              revised_text: revised,
              change_summary: ["补充故事目标和情绪推进"],
              rationale: "保留原意并形成可继续开发的故事。",
            },
            creative_task: {},
            provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
            graph_mutation: { mutated: false, scope: "preview_only" },
            cost_usd: 0,
          };
        },
        createScriptRevision: async (payload) => {
          window.__calls.scriptRevision += 1;
          if (payload.source_text !== revised || payload.parent_revision_id !== "revision-1") {
            throw new Error("revision apply contract mismatch");
          }
          return {
            revision: { revision_id: "revision-2" },
            projection: {
              schema_version: "afs.script_core_truth.v0.1",
              project_id: projectId,
              current_revision_id: "revision-2",
              current_revision: {
                revision_id: "revision-2",
                parent_revision_id: "revision-1",
                source_kind: "script",
                source_text: revised,
                source_digest: "b".repeat(64),
                source_length: revised.length,
                analysis_state: "analysis_required",
              },
              revision_history: [],
              assets: [],
              asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
              analysis_state: "analysis_required",
            },
          };
        },
      };
      const canvasShell = document.createElement("div");
      canvasShell.id = "studio-editor-shell";
      const syncCanvasText = () => {
        const selectedId = studioState.selection?.nodeIds?.[0] || "";
        canvasShell.textContent = String(studioState.nodes?.[selectedId]?.content || "");
      };
      syncCanvasText();
      const store = {
        get: () => studioState,
        set: (mutator) => {
          mutator(studioState);
          syncCanvasText();
        },
        flushRuntimeSave: async () => {},
      };
      const shell = createProductShell({
        getStudioState: () => studioState,
        getRuntime: () => runtime,
        getStore: () => store,
        getCanvasShell: () => canvasShell,
        formatError: (error) => String(error?.message || error),
      });
      shell.render({
        loading: false,
        project: { project_id: projectId, name: "新故事", goal: "短想法扩写" },
        workspace: { projects: [{ project_id: projectId, name: "新故事" }] },
        studioState,
        mediaGates: { llm: true, image: true, video: true },
      });
      window.__studioState = studioState;
      window.__ideaReady = true;
    </script>
  </body>
</html>
"""
