from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class FreshBrowserProjectHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/__fresh_browser_project.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if urlparse(self.path).path in {"/favicon.ico", "/favicon.svg"}:
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def test_fresh_browser_requires_validated_project_selection_and_never_spins_forever() -> None:
    with _browser_page() as (page, base_url, errors):
        page.goto(
            f"{base_url}/__fresh_browser_project.html",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__selectionReady === true")

        assert page.get_by_role(
            "heading",
            name="选择要继续的项目",
            exact=True,
        ).is_visible()
        choices = page.locator(".product-project-choice")
        assert choices.count() == 2
        assert "项目甲" in choices.nth(0).inner_text()
        assert "第一集" in choices.nth(0).inner_text()
        assert "项目乙" in choices.nth(1).inner_text()
        assert "第二集" in choices.nth(1).inner_text()
        assert page.get_by_text("正在读取制作进度", exact=False).count() == 0
        assert page.evaluate("window.__calls.projectOverview") == 0
        assert page.evaluate("window.__calls.image") == 0
        assert page.evaluate("window.__calls.video") == 0

        choices.nth(1).click()
        page.get_by_role(
            "button",
            name="当前项目：项目乙 · 第二集。打开项目详情与切换菜单",
            exact=True,
        ).wait_for()
        assert page.evaluate("window.__selectedProjects") == ["project-b"]
        assert page.evaluate("window.__calls.projectOverview") == 1
        assert page.evaluate("window.__currentProjectId") == "project-b"
        assert page.get_by_text("正在读取制作进度", exact=False).count() == 0
        assert not errors


def test_superseded_slow_empty_refresh_cannot_replace_selected_project() -> None:
    with _browser_page() as (page, base_url, errors):
        page.goto(
            f"{base_url}/__fresh_browser_project.html#slow",
            wait_until="domcontentloaded",
        )
        page.wait_for_function("window.__slowRefreshStarted === true")
        page.evaluate("window.__selectProject('project-a')")
        page.get_by_role(
            "button",
            name="当前项目：项目甲 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).wait_for()
        page.evaluate("window.__releaseSlowRefresh()")
        page.wait_for_timeout(100)

        assert page.evaluate("window.__currentProjectId") == "project-a"
        assert page.get_by_text("正在读取制作进度", exact=False).count() == 0
        assert page.get_by_role(
            "button",
            name="当前项目：项目甲 · 第一集。打开项目详情与切换菜单",
            exact=True,
        ).is_visible()
        assert not errors


class _browser_page:
    def __enter__(self):
        handler = partial(FreshBrowserProjectHandler, directory=str(ROOT))
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
    <title>Fresh browser project selection contract</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module">
      import {
        commitProjectIdentity,
        commitProjectListIdentity,
      } from "/apps/studio/src/project-identity-gate.js";
      import {
        createStudioProductShell,
        mountStudioDom,
      } from "/apps/studio/src/studio-product-bootstrap.js";

      localStorage.clear();
      const projects = [
        { project_id: "project-a", name: "项目甲", episode: "第一集" },
        { project_id: "project-b", name: "项目乙", episode: "第二集" },
      ];
      window.__calls = { projectOverview: 0, image: 0, video: 0 };
      window.__selectedProjects = [];
      let currentRuntime = null;
      let state = projectState("studio-empty", "暂无项目");
      const store = {
        get: () => state,
        set: (mutate) => {
          mutate(state);
          shell?.updateStudioState(state);
        },
        flushRuntimeSave: async () => {},
      };
      const { editorParking, editorShell } = mountStudioDom();
      let shell = null;

      function projectState(projectId, projectName) {
        return {
          meta: { projectId, projectName, canvasName: "画布 1" },
          nodes: {},
          edges: {},
          order: [],
          assets: [],
          selection: { nodeIds: [], edgeId: null },
          ui: {
            saveState: "已保存",
            projectIdentity: { status: "ready" },
          },
          production: {},
        };
      }

      function runtimeFor(projectId, { slow = false } = {}) {
        const project = projects.find((item) => item.project_id === projectId);
        return {
          projectId,
          workspaceOverview: async () => {
            if (slow) await new Promise((resolve) => {
              window.__releaseSlowRefresh = resolve;
              window.__slowRefreshStarted = true;
            });
            return { projects };
          },
          projectOverview: async () => {
            window.__calls.projectOverview += 1;
            return { project };
          },
          sequenceWorkspace: async () => null,
          loadAssetBible: async () => null,
          loadImageAdmission: async () => null,
          loadVideoAdmission: async () => null,
          health: async () => ({
            provider_gates: { llm: true, image: false, video: false },
          }),
        };
      }

      async function selectProject(projectId) {
        window.__selectedProjects.push(projectId);
        const project = projects.find((item) => item.project_id === projectId);
        currentRuntime = runtimeFor(projectId);
        state = projectState(projectId, project.name);
        commitProjectIdentity({ projectId, accountId: "account-a" });
        shell.updateStudioState(state);
        await shell.refresh(currentRuntime, { user_id: "account-a" });
        window.__currentProjectId = currentRuntime.projectId;
      }
      window.__selectProject = selectProject;

      shell = createStudioProductShell({
        getStore: () => store,
        getRuntime: () => currentRuntime,
        getCanvasShell: () => editorShell,
        getCanvasParking: () => editorParking,
        isRuntimeCurrent: (candidate) => candidate === currentRuntime,
        onSwitchProject: selectProject,
        onCreateProject: () => {},
        formatError: (error) => String(error?.message || error),
      });
      commitProjectListIdentity("account-a");
      shell.render({ authUser: { user_id: "account-a", display_name: "创作者" } });

      const slow = window.location.hash === "#slow";
      currentRuntime = runtimeFor("studio-empty", { slow });
      const refresh = shell.refresh(currentRuntime, { user_id: "account-a" });
      if (!slow) {
        await refresh;
        window.__selectionReady = true;
      }
    </script>
  </body>
</html>
"""
