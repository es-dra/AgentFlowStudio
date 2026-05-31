from __future__ import annotations

import json
import subprocess


def test_web_memory_workbench_renders_loulan_human_review_pack() -> None:
    script = """
import { readFile } from "node:fs/promises";
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView } from "./apps/web/memory-workbench-controller.js";

const packageText = await readFile("examples/agentflow/loulan_memory_package.example.json", "utf8");
const apiPlanText = await readFile("examples/agentflow/loulan_api_workbench_plan.example.json", "utf8");
const reviewPackText = await readFile("examples/agentflow/loulan_human_review_pack.example.json", "utf8");
const workspace = normalizeWorkspace(await parseFiles([
  { name: "loulan_memory_package.example.json", text: async () => packageText },
  { name: "loulan_api_workbench_plan.example.json", text: async () => apiPlanText },
  { name: "loulan_human_review_pack.example.json", text: async () => reviewPackText },
]));
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({
  hasReviewPack: workspace.loulanHumanReviewPack?.payload?.artifact_type,
  bundle: view.bundle_summary,
  review: view.review,
  feedbackDraft: view.feedback_draft,
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

    assert payload["hasReviewPack"] == "agentflow_loulan_human_review_pack"
    assert any(item["title"] == "Human review pack" and item["status"] == "blocked" for item in payload["bundle"])
    assert "2 B01 shots queued" in payload["review"]["storyboard_adherence"]
    assert payload["feedbackDraft"]["mode"] == "loulan_human_review_pack"
    assert '"source": "human_review_pending_draft"' in payload["feedbackDraft"]["json_text"]
    assert payload["nextPass"]["status"] == "blocked_until_human_review"
    assert "Loulan human review pack" in payload["inspectorTitles"]
    assert "Human Review" in payload["timelineLabels"]
