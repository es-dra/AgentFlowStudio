from __future__ import annotations

import json
import subprocess


def test_web_memory_workbench_renders_loulan_decision_template_and_context_projection() -> None:
    script = """
import { readFile } from "node:fs/promises";
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";

const files = await Promise.all([
  "loulan_memory_package.example.json",
  "loulan_api_workbench_plan.example.json",
  "loulan_human_review_pack.example.json",
  "loulan_promotion_decisions_template.example.json",
  "loulan_context_bundle_projection.example.json",
].map(async (name) => ({
  name,
  text: async () => readFile(`examples/agentflow/${name}`, "utf8"),
})));
const workspace = normalizeWorkspace(await parseFiles(files));
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({
  decisionTemplate: workspace.loulanDecisionTemplate?.payload?.artifact_type,
  contextProjection: workspace.loulanContextBundleProjection?.payload?.artifact_type,
  bundle: view.bundle_summary,
  controls: view.protocol_summary.controls,
  nextPass: view.next_pass,
  inspectorTitles: view.artifact_inspector.map((item) => item.title),
  timelineLabels: view.timeline.map((node) => node.label),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["decisionTemplate"] == "agentflow_loulan_promotion_decisions"
    assert payload["contextProjection"] == "agentflow_loulan_context_bundle_projection"
    assert any(item["title"] == "Decision template" for item in payload["bundle"])
    assert any(item["title"] == "Context bundle projection" for item in payload["bundle"])
    assert any(item["label"] == "decision template" for item in payload["controls"])
    assert any(item["label"] == "context bundle" for item in payload["controls"])
    assert payload["nextPass"]["status"] == "partial_ready"
    assert "Decision audit: partial_ready" in payload["nextPass"]["action"]
    assert "Loulan decision template" in payload["inspectorTitles"]
    assert "Loulan context bundle projection" in payload["inspectorTitles"]
    assert "Decision Template" in payload["timelineLabels"]
    assert "Context Bundle" in payload["timelineLabels"]
