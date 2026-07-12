from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        return


def test_save_retry_control_is_visible_actionable_and_unclipped_across_viewports() -> None:
    with static_server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"{base_url}/__topbar_retry_layout_contract.html", wait_until="domcontentloaded")
                page.wait_for_function("window.__topbarReady === true")

                failures: list[str] = []
                for viewport in ({"width": 1280, "height": 800}, {"width": 390, "height": 844}):
                    page.set_viewport_size(viewport)
                    page.wait_for_timeout(80)
                    measurement = page.evaluate("window.__measureRetryControl()")
                    failures.extend(retry_control_geometry_failures(measurement, viewport))
                    try:
                        page.locator(".save-pill-button").click(timeout=1_000)
                    except Exception as exc:  # pragma: no cover - failure message is the contract evidence
                        failures.append(f"{viewport['width']}px retry click failed: {exc}")

                clicks = page.evaluate("window.__retryClicks")
                if clicks != 2:
                    failures.append(f"retry control should be clickable at both widths, clicks={clicks}")
                assert not failures, "\n".join(failures)
            finally:
                browser.close()


def static_server():
    handler = partial(TopbarContractHandler, directory=str(REPO_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)

    class ServerContext:
        def __enter__(self) -> str:
            thread.start()
            return f"http://127.0.0.1:{server.server_address[1]}"

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    return ServerContext()


class TopbarContractHandler(QuietStaticHandler):
    def do_GET(self) -> None:
        if self.path == "/__topbar_retry_layout_contract.html":
            body = topbar_contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def topbar_contract_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/apps/studio/styles/tokens.css" />
    <link rel="stylesheet" href="/apps/studio/styles/base.css" />
    <link rel="stylesheet" href="/apps/studio/styles/shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/studio-mature-shell.css" />
    <title>Topbar Retry Layout Contract</title>
  </head>
  <body>
    <div id="app"><header id="topbar"></header></div>
    <script type="module">
      import { renderTopbar } from "/apps/studio/src/studio-topbar.js";
      window.__retryClicks = 0;
      const state = {
        meta: {
          projectId: "project-save-recovery-layout-contract",
          projectName: "Authenticated Studio Project Save Recovery Contract With Long Title",
          canvasName: "画布 1",
        },
        ui: {
          drawerOpen: true,
          saveState: "保存失败",
          saveMessage: "运行服务保存失败，当前修改已保留在本地；请检查连接后重试保存。",
        },
      };
      renderTopbar({
        state,
        store: { set: () => {} },
        runtime: { projectId: state.meta.projectId },
        projectSummaries: [],
        projectOptions: [{ project_id: state.meta.projectId, goal: state.meta.projectName }],
        hiddenProjectCount: 0,
        showAllProjects: false,
        onToggleProjectFilter: () => {},
        onSwitchProject: () => {},
        onCreateProject: () => {},
        onOpenHome: () => {},
        onBeforeSiteHome: () => {},
        authUser: {
          user_id: "layout-user",
          display_name: "Authenticated Layout Reviewer With Long Name",
        },
        runtimeSurfaceStatus: {
          state: "ready",
          label: "Runtime service ready",
          authLabel: "Signed in",
          providerGateLabel: "Provider gates closed",
          boundaryLabel: "Health only",
        },
        onSignOut: () => {},
        onRetrySave: () => { window.__retryClicks += 1; },
      });
      window.__measureRetryControl = () => {
        const button = document.querySelector(".save-pill-button");
        const topbar = document.querySelector("#topbar");
        const rect = button ? button.getBoundingClientRect() : null;
        const topbarRect = topbar ? topbar.getBoundingClientRect() : null;
        const style = button ? getComputedStyle(button) : null;
        return {
          exists: Boolean(button),
          tagName: button?.tagName || "",
          text: button?.textContent || "",
          ariaLabel: button?.getAttribute("aria-label") || "",
          display: style?.display || "",
          visibility: style?.visibility || "",
          pointerEvents: style?.pointerEvents || "",
          rect: rect ? { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height } : null,
          topbarRect: topbarRect ? { left: topbarRect.left, right: topbarRect.right, width: topbarRect.width } : null,
          scrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
        };
      };
      window.__topbarReady = true;
    </script>
  </body>
</html>
"""


def retry_control_geometry_failures(measurement: dict[str, Any], viewport: dict[str, int]) -> list[str]:
    width = viewport["width"]
    rect = measurement.get("rect") or {}
    failures: list[str] = []
    if not measurement.get("exists"):
      failures.append(f"{width}px retry control missing")
      return failures
    if measurement.get("tagName") != "BUTTON":
      failures.append(f"{width}px retry control is not a button: {measurement.get('tagName')}")
    if "重试" not in str(measurement.get("text")):
      failures.append(f"{width}px retry control missing retry label: {measurement.get('text')}")
    if "重试保存" not in str(measurement.get("ariaLabel")):
      failures.append(f"{width}px retry control missing accessible retry name")
    if measurement.get("display") == "none" or measurement.get("visibility") == "hidden":
      failures.append(f"{width}px retry control hidden: display={measurement.get('display')} visibility={measurement.get('visibility')}")
    if float(rect.get("width") or 0) < 32 or float(rect.get("height") or 0) < 24:
      failures.append(f"{width}px retry control has no real clickable box: {rect}")
    if float(rect.get("left") or -1) < 0 or float(rect.get("right") or (width + 1)) > width:
      failures.append(f"{width}px retry control clipped by viewport: {rect}")
    overflow = max(int(measurement.get("scrollWidth") or 0), int(measurement.get("bodyScrollWidth") or 0)) - width
    if overflow > 1:
      failures.append(f"{width}px topbar creates horizontal overflow: {overflow}px")
    return failures
