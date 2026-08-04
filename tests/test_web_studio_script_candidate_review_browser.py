from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
from threading import Thread

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]


class CandidateReviewHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path == "/__script_candidate_review.html":
            body = candidate_review_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def test_candidate_review_inspector_survives_edit_and_fits_desktop_and_mobile() -> None:
    handler = partial(CandidateReviewHandler, directory=str(REPO_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with sync_playwright() as playwright:
            browser = launch_local_chromium(playwright)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(f"{base_url}/__script_candidate_review.html", wait_until="domcontentloaded")
                page.wait_for_function("window.__candidateReviewReady === true")

                inspector = page.locator("#inspector")
                assert inspector.get_by_text("来源：Mira", exact=True).is_visible()
                name_input = inspector.get_by_label("名称", exact=True)
                assert name_input.input_value() == "Mira"
                assert_review_geometry(page)

                name_input.fill("Mira Vale")
                inspector.get_by_role("button", name="保存修改", exact=True).click()
                inspector.get_by_text("已修改，待审阅", exact=True).wait_for()
                assert page.evaluate("window.__state.selection.nodeIds[0]") == "script_truth_asset_char1"
                assert inspector.get_by_label("名称", exact=True).input_value() == "Mira Vale"
                inspector.get_by_role("button", name="确认", exact=True).click()
                inspector.get_by_text("已确认", exact=True).wait_for()
                assert inspector.get_by_role("button", name="确认", exact=True).count() == 0
                assert inspector.get_by_label("名称", exact=True).is_disabled()
                assert page.evaluate("window.__calls.reviewDecision") == "confirm"

                page.evaluate("window.__resetCandidate()")
                inspector.get_by_role("button", name="拒绝", exact=True).click()
                inspector.get_by_text("已拒绝", exact=True).wait_for()
                assert page.evaluate("window.__calls.reviewDecision") == "reject"

                page.evaluate("window.__resetCandidate()")
                page.set_viewport_size({"width": 390, "height": 844})
                assert_review_geometry(page)
                inspector.get_by_role("button", name="收起", exact=True).click()
                assert inspector.get_by_text("候选审阅", exact=True).count() == 0
                inspector.get_by_title("展开右侧状态栏").click()
                inspector.get_by_text("候选审阅", exact=True).wait_for()
                assert_review_geometry(page)
                assert not page.evaluate("window.__pageErrors")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def launch_local_chromium(playwright):
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    executable = next((Path(item) for item in candidates if item and Path(item).is_file()), None)
    options = {
        "headless": True,
        "args": ["--proxy-server=direct://", "--proxy-bypass-list=*"],
    }
    if executable:
        options["executable_path"] = str(executable)
    return playwright.chromium.launch(**options)


def assert_review_geometry(page) -> None:
    measurement = page.evaluate(
        """
        () => {
          const panel = document.querySelector("#inspector");
          const controls = [...panel.querySelectorAll(
            ".analysis-asset-review button, .analysis-asset-review input, .inspector-actions .inspector-action"
          )].filter((control) => {
            const rect = control.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          });
          const panelRect = panel.getBoundingClientRect();
          return {
            viewportWidth: window.innerWidth,
            scrollWidth: document.documentElement.scrollWidth,
            panel: { left: panelRect.left, right: panelRect.right, width: panelRect.width },
            controls: controls.map((control) => {
              const rect = control.getBoundingClientRect();
              return {
                className: control.className,
                text: control.textContent || control.value || "",
                left: rect.left,
                right: rect.right,
                width: rect.width,
                height: rect.height,
              };
            }),
          };
        }
        """
    )
    assert measurement["scrollWidth"] <= measurement["viewportWidth"]
    assert measurement["panel"]["left"] >= 0
    assert measurement["panel"]["right"] <= measurement["viewportWidth"]
    assert measurement["controls"]
    for control in measurement["controls"]:
        assert control["left"] >= measurement["panel"]["left"], (measurement["panel"], control)
        assert control["right"] <= measurement["panel"]["right"], (measurement["panel"], control)
        assert control["width"] >= 24
        assert control["height"] >= 24, control


def candidate_review_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/apps/studio/styles/tokens.css" />
    <link rel="stylesheet" href="/apps/studio/styles/base.css" />
    <link rel="stylesheet" href="/apps/studio/styles/studio-wave.css" />
    <link rel="stylesheet" href="/apps/studio/styles/studio-mature-shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/studio-inspector-declutter.css" />
    <style>
      html, body { margin: 0; min-height: 100%; background: var(--bg-canvas); }
      body { display: flex; justify-content: flex-end; min-width: 0; }
      #inspector { width: min(100%, 340px); min-height: 100vh; padding: 12px; overflow-x: hidden; }
    </style>
    <title>Script candidate review contract</title>
  </head>
  <body>
    <aside id="inspector"></aside>
    <script type="module">
      import { renderInspectorPanel } from "/apps/studio/src/panels/inspector-panel.js";
      import { applyScriptCoreTruthProjection } from "/apps/studio/src/script-core-truth-projection.js";
      import { bindScriptCandidateReviewEvents } from "/apps/studio/src/script-candidate-review.js";

      const digest = "a".repeat(64);
      let currentProjection;
      let nextDecision = "";
      window.__pageErrors = [];
      window.addEventListener("error", (event) => window.__pageErrors.push(String(event.message || event.error)));
      window.addEventListener("unhandledrejection", (event) => window.__pageErrors.push(String(event.reason)));
      window.__calls = { edits: 0, reviews: 0, reviewDecision: "" };
      window.__state = {
        meta: { projectId: "p1", projectName: "候选审阅" },
        nodes: {}, edges: {}, groups: {}, order: [], assets: [], production: {},
        selection: { nodeIds: [], edgeId: null },
        ui: { inspectorOpen: true, drawerOpen: false },
        viewport: { x: 0, y: 0, scale: 1 },
      };

      function projection(status = "candidate", version = 1, versionId = "v1", label = "Mira") {
        const revision = {
          project_id: "p1", revision_id: "rev1", source_kind: "script", source_digest: digest,
          source_length: 20, source_text: "Mira enters the hall.", analysis_state: "pending_confirmation",
        };
        return {
          schema_version: "afs.script_core_truth.v0.1", project_id: "p1", current_revision_id: "rev1",
          current_revision: revision, revision_history: [revision],
          analysis_state: status === "confirmed" ? "confirmed" : "pending_confirmation",
          asset_counts: { characters: 1, main_scenes: 0, manual_props: 0 },
          assets: [{
            asset_id: "char1", asset_type: "character", source_mode: "analysis_candidate", status,
            project_id: "p1", revision_id: "rev1", source_digest: digest, candidate_id: "candidate1",
            version, version_id: versionId, parent_version_id: version > 1 ? `v${version - 1}` : "",
            display_name: label, name: label, aliases: [], pronoun_links: [], confidence: 0.99,
            evidence_spans: [{ start: 0, end: 4, quote: "Mira" }], lineage: {},
          }],
        };
      }

      const store = {
        get: () => window.__state,
        set: (mutator) => {
          mutator(window.__state);
          renderInspectorPanel(window.__state, store);
        },
      };
      const runtime = {
        confirmCoreAssetCommand: async (payload) => {
          window.__calls.edits += 1;
          currentProjection = projection("modified", 2, "v2", payload.patch.display_name);
          return { projection: currentProjection };
        },
        loadProductionGraph: async () => ({ graph: { version: 0 } }),
        reviewAnalysisAsset: async (_revisionId, _assetId, payload) => {
          window.__calls.reviews += 1;
          window.__calls.reviewDecision = payload.decision;
          nextDecision = payload.decision;
          const truth = window.__state.nodes.script_truth_asset_char1.params.coreAssetTruth;
          currentProjection = projection(payload.decision === "confirm" ? "confirmed" : "rejected", truth.version + 1, `v${truth.version + 1}`, truth.display_name);
          return {};
        },
        loadScriptTruth: async () => ({ projection: currentProjection }),
      };

      function resetCandidate() {
        nextDecision = "";
        currentProjection = projection();
        applyScriptCoreTruthProjection(window.__state, currentProjection);
        window.__state.selection = { nodeIds: ["script_truth_asset_char1"], edgeId: null };
        document.querySelector("#inspector").dataset.signature = "";
        renderInspectorPanel(window.__state, store);
      }
      window.__resetCandidate = resetCandidate;
      bindScriptCandidateReviewEvents({ getRuntime: () => runtime, store, formatError: (error) => String(error.message || error) });
      resetCandidate();
      window.__candidateReviewReady = true;
    </script>
  </body>
</html>
"""
