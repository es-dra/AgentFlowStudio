from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_m6_frontend_contract_stays_in_single_shell_and_runtime_graph_path() -> None:
    files = [
        STUDIO_ROOT / "src" / "agent-chat-lifecycle.js",
        STUDIO_ROOT / "src" / "agent-chat-panel.js",
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
    assert "/m6/script-plan-asset-bible/preview-runs/" in combined
    assert "/m6/script-plan-asset-bible/confirm" in combined
    assert "恢复同一预览" in combined
    assert "candidate_digest" in combined
    assert "scope_impact" in combined
    assert "agent-m6-scope-impact" in combined
    assert "loadLatestM6ScriptPlanPreviewRun" in combined
    assert "cancelM6ScriptPlanPreviewRun" in combined
    assert "confirmPayload.candidate" not in combined
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    restore = shell.split("async function restoreLatestM6PreviewRun", 1)[1].split("function currentPlanningPanelPreferenceKey", 1)[0]
    assert "isM6RuntimeCurrent(runtime, expectedProjectId)" in restore
    assert restore.index("await runtime?.loadLatestM6ScriptPlanPreviewRun?.()") < restore.index(
        "if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;"
    ) < restore.index("m6PreviewRun = run")
    permanent_error = shell.split("if (error?.status && error.status !== 0) {", 1)[1].split("}", 1)[0]
    assert "m6PreviewRecovering = false;" in permanent_error
    assert "return;" in permanent_error
    assert "String(run.project_id || \"\") === expectedProjectId" in shell
    panel = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    assert 'if (run?.phase !== "cancelled")' in panel
    cancelled = panel.split('if (run?.phase !== "cancelled")', 1)[1].split("} catch", 1)[0]
    assert "session.pendingCommand = null;" in cancelled
    assert "cancelAgentCommand(session)" not in cancelled
    for field, label in (
        ("goal", "创作目标"),
        ("relationship_arc", "关系变化"),
        ("duration_seconds", "镜头时长"),
        ("camera_movement", "镜头运动"),
        ("rights_boundary", "使用边界"),
    ):
        assert f'{field}: "{label}"' in panel
    assert "item.fields.map(m6FieldLabel)" in panel
    styles = (STUDIO_ROOT / "styles" / "product-shell.css").read_text(encoding="utf-8")
    assert ".studio-unified-workspace.agent-collapsed .canvas-workspace-stage .graph-canvas-status," in styles
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
  assets: [
    { asset_id: "prop", name: "场记板", kind: "prop", classification: "canonical_prop", canonical_asset_type: "prop", production_aid_type: "", rights_boundary: "project" },
    { asset_id: "closeup", name: "手背伤痕特写", kind: "closeup", classification: "production_aid", canonical_asset_type: "", production_aid_type: "closeup", rights_boundary: "project" },
    { asset_id: "reference", name: "参考集", kind: "reference_set", classification: "production_aid", canonical_asset_type: "", production_aid_type: "reference_set", rights_boundary: "project" },
  ],
  shots: [
    { shot_id: "shot1", scene_id: "scene", duration_seconds: 5.5, intent: "first", character_refs: ["character"], asset_refs: ["prop", "reference"], shot_size: "中景" },
    { shot_id: "shot2", scene_id: "scene", duration_seconds: 7, intent: "second", character_refs: ["character"], asset_refs: ["closeup", "reference"], shot_size: "特写" },
  ],
  asset_bible: { status: "pending_confirmation", character_refs: ["character"], scene_refs: ["scene"], prop_refs: ["prop"], closeup_refs: ["closeup"], reference_set_refs: ["reference"], production_aid_refs: ["closeup", "reference"] },
  m6_scope_review: {
    schema_version: "afs.m6.canonical_scope_review.v0.1",
    source_authority: "user_supplied_canonical_scope",
    canonical: { characters: ["林澈"], scenes: ["剪辑室"], props: ["场记板"] },
    production_aids: [{ name: "手背伤痕特写", kind: "closeup", classification: "production_aid", production_aid_type: "closeup" }],
    proposed_additions: [
      { item_type: "character", name: "林澈", classification: "canonical_character" },
      { item_type: "scene", name: "剪辑室", classification: "canonical_scene" },
      { item_type: "asset", name: "场记板", kind: "prop", classification: "canonical_prop" },
      { item_type: "asset", name: "手背伤痕特写", kind: "closeup", classification: "production_aid", production_aid_type: "closeup" },
    ],
    proposed_renames: [],
    proposed_expansions: [{ item_type: "scene", name: "剪辑室", fields: ["lighting", "continuity"] }],
    proposed_classifications: [
      { item_type: "asset", name: "场记板", kind: "prop", classification: "canonical_prop" },
      { item_type: "asset", name: "手背伤痕特写", kind: "closeup", classification: "production_aid", production_aid_type: "closeup" },
    ],
    affected_associations: [
      { association_type: "asset_bible.prop_refs", names: ["场记板"], classification: "canonical_prop_refs_only" },
      { association_type: "asset_bible.production_aid_refs", names: ["手背伤痕特写", "参考集"], classification: "production_aid_refs_not_canonical_props" },
      { association_type: "shot.references", name: "镜头1", scene: "剪辑室", characters: ["林澈"], canonical_props: ["场记板"], production_aids: ["参考集"], duration_seconds: 5.5 },
    ],
    fail_closed: { status: "pass", reasons: [], extra_canonical_entities: [], missing_canonical_entities: [], renamed_canonical_entities: [] },
  },
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
  run_id: "m6-preview-run",
  candidate_digest: "c".repeat(64),
  phase: "succeeded",
  dispatch_count: 1,
  preview: {
    candidate,
    candidate_digest: "c".repeat(64),
    validation: {
      verdict: "PASS",
      P0: 0,
      P1: 0,
      review_roles: candidate.review_requirements.map((item) => item.role),
      provider_dispatch_count: 1,
      cost_usd: 0,
    },
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
if (!confirmPayload || confirmPayload.run_id !== "m6-preview-run" || confirmPayload.candidate_digest !== "c".repeat(64) || confirmPayload.expected_graph_version !== 0 || confirmPayload.candidate) process.exit(3);
if (receipt.runtime_domain !== "production_graph" || receipt.graph_version !== 1 || receipt.provider_dispatch_count !== 1) process.exit(4);
if (!command.scope_impact || command.scope_impact.summary.additions !== 4 || command.scope_impact.summary.renames !== 0) process.exit(5);
if (!command.summary.includes("所有新建、改名、补充、用途和关联都会逐项列出")) process.exit(6);
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


def test_m6_run_reconciliation_keeps_one_task_message_and_unrelated_chat() -> None:
    script = r'''
import {
  createAgentChatContextStore,
  syncM6PreviewRunSession,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const session = createAgentChatContextStore().get("project:canvas");
session.messages.push({ role: "assistant", text: "保留这条无关对话", created_at: "before" });
const context = { context_key: "project:canvas" };
syncM6PreviewRunSession(session, context, { run_id: "run-1", phase: "queued" });
syncM6PreviewRunSession(session, context, { run_id: "run-1", phase: "running" });
syncM6PreviewRunSession(session, context, {
  run_id: "run-1",
  phase: "failed",
  error: { message: "制作方案任务失败；制作事实未改变。" },
});
const matching = session.messages.filter((item) => item.m6_preview_run_id === "run-1" && item.role === "assistant");
if (matching.length !== 1) process.exit(2);
if (!matching[0].text.includes("制作事实未改变")) process.exit(3);
if (!session.messages.some((item) => item.text === "保留这条无关对话")) process.exit(4);
if (session.messages.some((item) => item.text.includes("重新生成"))) process.exit(5);
if (session.messages.some((item) => item.text.includes("我会基于当前画布上下文生成命令预览"))) process.exit(6);
console.log(JSON.stringify({ matching: matching.length, messages: session.messages.length }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        cwd=STUDIO_ROOT.parents[1],
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["matching"] == 1
