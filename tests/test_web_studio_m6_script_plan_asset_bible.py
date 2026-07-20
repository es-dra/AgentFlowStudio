from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_m6_frontend_contract_stays_in_single_shell_and_runtime_graph_path() -> None:
    files = [
        STUDIO_ROOT / "src" / "agent-chat-lifecycle.js",
        STUDIO_ROOT / "src" / "product-shell.js",
        STUDIO_ROOT / "src" / "runtime-client.js",
        STUDIO_ROOT / "src" / "production-graph-workspace-projection.js",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "m6_script_plan_asset_bible" in combined
    assert "previewM6ScriptPlanAssetBible" in combined
    assert "confirmM6ScriptPlanAssetBible" in combined
    assert "stageM6ScriptPlanCandidateCommand" in combined
    assert "/m6/script-plan-asset-bible/preview" in combined
    assert "/m6/script-plan-asset-bible/confirm" in combined
    assert "buildCanvasWorkspace" in combined
    assert "buildStoryboardWorkspace" in combined
    assert "buildAgentChat" in combined
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")
    m6_block = lifecycle[lifecycle.index("m6_script_plan_asset_bible"):]
    assert "saveStudioState" not in m6_block
    for marker in ("m6-card-stack", "m6-sequence-layout", "return buildGraphSequenceWorkspace", "4x15", "4×15", "10x6", "10×6"):
        assert marker not in combined


def test_m6_agent_chat_preview_confirms_through_runtime_production_graph() -> None:
    script = r'''
import {
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  stageM6ScriptPlanCandidateCommand,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const candidate = {
  schema_version: "afs.film_domain_pack.v0.1",
  m6_schema_version: "afs.m6.script_plan_asset_bible.v0.1",
  trusted_candidate: true,
  source_digest: "a".repeat(64),
  provider_dispatch_count: 0,
  cost_usd: 0,
  brief: { brief_id: "brief", professional_contract: {} },
  script_revision: { revision_id: "revision", script_contract: {} },
  sequence: { sequence_id: "sequence", target_duration_seconds: 12.5 },
  characters: [{ character_id: "character", display_name: "林澈", goal: "goal" }],
  scenes: [{ scene_id: "scene", name: "剪辑室", lighting: "冷光" }],
  assets: [{ asset_id: "reference", name: "参考集", kind: "reference_set", rights_boundary: "project" }],
  shots: [
    { shot_id: "shot1", scene_id: "scene", duration_seconds: 5.5, intent: "first", character_refs: ["character"], asset_refs: ["reference"], shot_size: "中景" },
    { shot_id: "shot2", scene_id: "scene", duration_seconds: 7, intent: "second", character_refs: ["character"], asset_refs: ["reference"], shot_size: "特写" },
  ],
  asset_bible: { status: "pending_confirmation", character_refs: ["character"], scene_refs: ["scene"], reference_set_refs: ["reference"] },
  knowledge_context: { items: [] },
  review_requirements: [
    "screenwriter",
    "director_storyboard",
    "cinematographer",
    "asset_continuity",
    "production_feasibility",
    "engineering_lineage_knowledge_safety",
  ].map((role) => ({ role })),
  delivery_id: "delivery",
  timeline_refs: ["timeline"],
  rights_refs: ["rights"],
};
const preview = {
  candidate,
  validation: {
    verdict: "PASS",
    P0: 0,
    P1: 0,
    review_roles: candidate.review_requirements.map((item) => item.role),
    provider_dispatch_count: 0,
    cost_usd: 0,
  },
};
const contexts = createAgentChatContextStore();
const context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "M6" },
  studioState: { meta: { projectId: "p1", seq: 1 }, nodes: {}, production: { production_graph_projection: { graph_version: 0, graph_digest: "" } } },
});
context.context_key = "p1:canvas:agent-chat";
const session = contexts.get(context.context_key);
const command = stageM6ScriptPlanCandidateCommand(session, context, preview);
let confirmPayload = null;
const runtime = {
  confirmM6ScriptPlanAssetBible: async (payload) => {
    confirmPayload = payload;
    return { graph: { version: 1, graph_digest: "b".repeat(64) } };
  },
};
const store = { set: () => { throw new Error("M6 graph command should not mutate Studio state directly"); } };
const receipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
if (command.command_type !== "m6_script_plan_asset_bible") process.exit(2);
if (!confirmPayload || confirmPayload.candidate !== candidate || confirmPayload.expected_graph_version !== 0) process.exit(3);
if (receipt.runtime_domain !== "production_graph" || receipt.graph_version !== 1 || receipt.provider_dispatch_count !== 0) process.exit(4);
console.log(JSON.stringify({ commandType: command.command_type, receiptDomain: receipt.runtime_domain, graphVersion: receipt.graph_version }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        cwd=STUDIO_ROOT.parents[1],
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["commandType"] == "m6_script_plan_asset_bible"
