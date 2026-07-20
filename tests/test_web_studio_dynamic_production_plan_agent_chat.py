from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_dynamic_production_plan_frontend_contract_has_no_pollution() -> None:
    production_files = [
        STUDIO_ROOT / "src" / "agent-chat-lifecycle.js",
        STUDIO_ROOT / "src" / "agent-chat-panel.js",
        STUDIO_ROOT / "src" / "production-plan-projection.js",
        STUDIO_ROOT / "src" / "product-shell.js",
        STUDIO_ROOT / "src" / "runtime-client.js",
    ]
    runtime_file = "apps/api/runtime_dynamic_production_plan.py"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in production_files)
    combined += "\n" + open(runtime_file, encoding="utf-8").read()
    for marker in ("KNOWN_", "_HINTS", "FALLBACK_SCENES", "巷口", "雨巷", "老宅", "4x15", "4×15", "fixed 4"):
        assert marker not in combined
    assert "dynamic_story_plan_candidate_contract" in combined
    assert "media_strategy_preview_confirm" in combined
    assert "chunk_continuity_plan_contract" in combined
    assert "provider_dispatch_count: 0" in combined


def test_agent_chat_dynamic_plan_projection_commands_and_undo() -> None:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  cancelAgentCommand,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";

const digest = "b".repeat(64);
const candidateDigest = "c".repeat(64);
const revision = {
  revision_id: "scrrev_dynamic_frontend",
  source_kind: "script",
  source_digest: digest,
  source_length: 90,
  analysis_state: "confirmed",
};
const character = {
  asset_id: "char_mira",
  asset_type: "character",
  source_mode: "analysis_candidate",
  status: "confirmed",
  project_id: "p1",
  revision_id: revision.revision_id,
  source_digest: digest,
  display_name: "Mira",
  name: "Mira",
  aliases: [],
  pronoun_links: [],
  evidence_spans: [{ start: 0, end: 4, quote: "Mira" }],
  confidence: 0.93,
  lineage: {},
};
const scene = {
  asset_id: "scene_observatory",
  asset_type: "main_scene",
  source_mode: "analysis_candidate",
  status: "confirmed",
  project_id: "p1",
  revision_id: revision.revision_id,
  source_digest: digest,
  display_name: "Observatory",
  name: "Observatory",
  aliases: [],
  pronoun_links: [],
  evidence_spans: [{ start: 10, end: 21, quote: "observatory" }],
  confidence: 0.91,
  lineage: {},
};
const scriptProjection = {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "p1",
  current_revision_id: revision.revision_id,
  current_revision: revision,
  revision_history: [revision],
  assets: [character, scene],
  asset_counts: { characters: 1, main_scenes: 1, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
  analysis_state: "confirmed",
  provider_dispatch_count: 0,
  remote_dispatch_count: 0,
};
function planProjection({ planId = "plan_frontend", planDigest = "d".repeat(64), durations = [2.5, 6.5], failed = false } = {}) {
  const shots = durations.map((duration, index) => ({
    shot_id: `shot_frontend_${index + 1}`,
    beat_id: index === 0 ? "beat_setup" : "beat_response",
    order: index + 1,
    intent: `Dynamic frontend shot ${index + 1}`,
    duration_seconds: duration,
    character_refs: ["char_mira"],
    scene_refs: ["scene_observatory"],
    continuity_in: index === 0 ? "opening stillness" : "placeholder_last_frame:shot_frontend_1:1",
    continuity_out: index === durations.length - 1 ? "signal holds" : "placeholder_last_frame:shot_frontend_1:1",
    source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "signal" }],
    media_strategy: {
      strategy: index === 1 ? "i2v" : "t2v",
      strategy_reason: index === 1 ? "locked keyframe lineage is available" : "text-only shot intent is sufficient",
      input_requirements: index === 1 ? ["reference_artifact_or_locked_keyframe"] : ["text_prompt_contract"],
      reference_asset_refs: index === 1 ? [{
        ref_id: "ref_frontend",
        source_kind: "locked_keyframe",
        asset_id: "char_mira",
        artifact_id: "artifact-safe-keyframe",
        lineage: {
          project_id: "p1",
          script_revision_id: revision.revision_id,
          source_digest: digest,
          asset_id: "char_mira",
          artifact_id: "artifact-safe-keyframe",
          locked_keyframe_id: "locked-keyframe-safe",
        },
      }] : [],
      user_constraints: {},
    },
    media_input_state: "ready",
    status: failed && index === 1 ? "failed" : "planned",
    chunk_ids: [`chunk_shot_frontend_${index + 1}_1`],
    attempt_history: [],
  }));
  const chunks = shots.map((shot, index) => ({
    chunk_id: `chunk_${shot.shot_id}_1`,
    shot_id: shot.shot_id,
    shot_order: shot.order,
    sequence: 1,
    target_duration_seconds: shot.duration_seconds,
    continuity_anchor_in: shot.continuity_in,
    continuity_anchor_out: shot.continuity_out,
    depends_on: index ? `chunk_${shots[index - 1].shot_id}_1` : "",
    state: failed && index === 1 ? "failed" : "ready",
    remainder_strategy: "",
    attempt_history: failed && index === 1 ? [{ state: "failed", reason: "frontend test" }] : [],
    selected_artifact_version_ref: "",
  }));
  return {
    artifact_type: "afs_dynamic_production_plan_projection",
    schema_version: "afs.dynamic_production_plan.v0.1",
    project_id: "p1",
    planning_state: failed ? "blocked" : "planned",
    current_plan: {
      plan_id: planId,
      plan_digest: planDigest,
      parent_plan_id: "",
      plan_version: 1,
      script_revision_id: revision.revision_id,
      source_digest: digest,
      candidate_digest: candidateDigest,
      created_at: "2026-07-18T00:00:00Z",
      updated_at: "2026-07-18T00:00:00Z",
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    beats: [
      { beat_id: "beat_setup", order: 1, summary: "setup", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "Mira" }], narrative_purpose: "setup" },
      { beat_id: "beat_response", order: 2, summary: "response", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "signal" }], narrative_purpose: "response" },
    ],
    shots,
    chunks,
    concat_plan: {
      concat_plan_id: "concat_frontend",
      state: "planned_not_executed",
      shot_order: shots.map((shot) => shot.shot_id),
      selected_artifact_version_refs: shots.map((shot) => ({ shot_id: shot.shot_id, artifact_version_ref: `artifact_placeholder:${shot.shot_id}`, state: "planned_placeholder" })),
      executes_media: false,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    plan_history: [{ plan_id: planId, plan_digest: planDigest, parent_plan_id: "", plan_version: 1, planning_state: failed ? "blocked" : "planned" }],
    storyboard_mode: "read_only_consumer",
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}
const candidate = {
  project_id: "p1",
  script_revision_id: revision.revision_id,
  source_digest: digest,
  schema_version: "afs.story_plan_candidate.v0.1",
  candidate_digest: candidateDigest,
  beats: [{ beat_id: "beat_setup", order: 1, summary: "setup", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "Mira" }], narrative_purpose: "setup" }],
  shots: [{ shot_id: "shot_frontend_1", beat_id: "beat_setup", order: 1, intent: "dynamic", duration_seconds: 2.5, character_refs: ["char_mira"], scene_refs: ["scene_observatory"], continuity_in: "", continuity_out: "", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "Mira" }], media_strategy: { strategy: "t2v", strategy_reason: "text-only shot intent", input_requirements: ["text_prompt_contract"], reference_asset_refs: [], user_constraints: {} } }],
  capability_contract: { schema_version: "afs.provider_capability_contract.v0.1", provider_profile_id: "offline", supports_t2v: true, supports_i2v: true, supported_clip_durations: [2.5, 3, 4], max_duration_seconds: 4, supports_start_frame: true, supports_end_frame: true, aspect_ratios: ["9:16"], fps_values: [24] },
  provider_dispatch_count: 0,
  remote_dispatch_count: 0,
};
const state = {
  meta: { projectId: "p1", projectName: "Frontend", canvasName: "Canvas", seq: 1 },
  viewport: { x: 0, y: 0, scale: 1 },
  nodes: {},
  edges: {},
  groups: {},
  order: [],
  assets: [],
  production: {},
  selection: { nodeIds: [], edgeId: null },
  ui: {},
};
const store = { get: () => state, set: (mutator) => mutator(state) };
applyScriptCoreTruthProjection(state, scriptProjection);

let lastPlanPreview = null;
let lastPlanConfirm = null;
let lastUndo = null;
const runtime = {
  submitStoryPlanCandidate: async (payload) => {
    if (payload.candidate_digest !== candidateDigest) throw new Error("candidate digest was not sent");
    return { candidate: { candidate_digest: candidateDigest }, projection: planProjection() };
  },
  confirmStoryPlanCandidate: async (_digest, payload) => {
    if (payload.schema_version !== "afs.story_plan_candidate.v0.1") throw new Error("confirm schema mismatch");
    return {
      receipt: {
        receipt_id: "receipt_plan_confirm",
        command_type: "confirm_story_plan_candidate",
        status: "executed",
        summary: "plan confirmed",
        script_revision_id: revision.revision_id,
        source_digest: digest,
        before_plan_id: "",
        after_plan_id: "plan_frontend",
        before_plan_digest: "",
        after_plan_digest: "d".repeat(64),
        undo_available: true,
      },
      projection: planProjection(),
    };
  },
  loadProductionPlanTruth: async () => ({ projection: planProjection() }),
  previewProductionPlanCommand: async (payload) => {
    lastPlanPreview = payload;
    return { command: { status: "preview", command_type: payload.command_type }, projection: planProjection() };
  },
  confirmProductionPlanCommand: async (payload) => {
    lastPlanConfirm = payload;
    return {
      receipt: {
        receipt_id: "receipt_plan_edit",
        command_type: payload.command_type,
        status: "executed",
        summary: "plan command confirmed",
        script_revision_id: revision.revision_id,
        source_digest: digest,
        before_plan_id: "plan_frontend",
        after_plan_id: "plan_frontend_v2",
        before_plan_digest: "d".repeat(64),
        after_plan_digest: "e".repeat(64),
        undo_available: true,
      },
      projection: planProjection({ planId: "plan_frontend_v2", planDigest: "e".repeat(64), durations: [2.5, payload.patch.duration_seconds || 6.25] }),
    };
  },
  undoProductionPlanCommand: async (payload) => {
    lastUndo = payload;
    return {
      receipt: { receipt_id: "receipt_plan_undo", command_type: "undo", status: "undone", summary: "plan undo", after_plan_digest: "d".repeat(64) },
      projection: planProjection(),
    };
  },
};

let context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "canvas" });
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const submitPreview = submitAgentChatMessage(session, `/submit-story-plan ${JSON.stringify(candidate)}`, context);
const confirmReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const planNodeCount = state.order.filter((id) => id.startsWith("production_plan_")).length;
const shotNodeId = state.order.find((id) => id === "production_plan_shot_shot_frontend_2");
state.selection = { nodeIds: [shotNodeId], edgeId: null };
context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "canvas", selectedNode: state.nodes[shotNodeId] });
const editPreview = submitAgentChatMessage(session, "/edit-shot-duration 6.25", context);
const editReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const undoReceipt = await undoAgentReceiptWithRuntime(session, editReceipt, store, runtime);

const previewedTypes = {};
for (const commandText of [
  "/set-shot-strategy i2v reason=explicit visual reference requested by creator",
  "/split-shot 2.5 4",
  "/merge-shot-next",
  "/mark-failed",
  "/retry-failed",
  "/replan-affected",
]) {
  const result = submitAgentChatMessage(session, commandText, context);
  previewedTypes[commandText] = { status: result.status, type: result.command.command_type, storyboardWrite: result.command.impact?.storyboard_write };
  cancelAgentCommand(session);
}
const storyboardContext = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "storyboard" });
const storyboardBlocked = submitAgentChatMessage(session, "/edit-shot-duration 7", storyboardContext);

process.stdout.write(JSON.stringify({
  submitStatus: submitPreview.status,
  submitType: submitPreview.command.command_type,
  confirmStatus: confirmReceipt.status,
  confirmRuntimeDomain: confirmReceipt.runtime_domain,
  confirmUndoAvailable: confirmReceipt.undo_available,
  planNodeCount,
  planState: state.production.dynamic_production_plan_projection.planning_state,
  storyboardShotCount: state.production.dynamic_production_plan_projection.storyboard_shots.length,
  selectedEntityType: context.selected_plan_entity_type,
  editStatus: editPreview.status,
  previewCommandType: lastPlanPreview.command_type,
  previewPlanDigest: lastPlanPreview.plan_digest,
  confirmCommandType: lastPlanConfirm.command_type,
  editReceiptPlanDigest: editReceipt.plan_digest,
  undoStatus: undoReceipt.status,
  undoPlanDigest: lastUndo.plan_digest,
  previewedTypes,
  storyboardBlockedStatus: storyboardBlocked.status,
  storyboardRequiresConfirmation: storyboardBlocked.command.requires_confirmation,
  providerDispatchCount: confirmReceipt.provider_dispatch_count + editReceipt.provider_dispatch_count + undoReceipt.provider_dispatch_count,
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert payload["submitStatus"] == "preview"
    assert payload["submitType"] == "submit_story_plan_candidate"
    assert payload["confirmStatus"] == "executed"
    assert payload["confirmRuntimeDomain"] == "production_plan"
    assert payload["confirmUndoAvailable"] is True
    assert payload["planNodeCount"] >= 7
    assert payload["planState"] == "planned"
    assert payload["storyboardShotCount"] == 2
    assert payload["selectedEntityType"] == "shot"
    assert payload["editStatus"] == "preview"
    assert payload["previewCommandType"] == "edit_shot_duration"
    assert payload["previewPlanDigest"] == "d" * 64
    assert payload["confirmCommandType"] == "edit_shot_duration"
    assert payload["editReceiptPlanDigest"] == "e" * 64
    assert payload["undoStatus"] == "undone"
    assert payload["undoPlanDigest"] == "e" * 64
    assert payload["storyboardBlockedStatus"] == "blocked"
    assert payload["storyboardRequiresConfirmation"] is False
    assert payload["providerDispatchCount"] == 0
    assert {item["status"] for item in payload["previewedTypes"].values()} == {"preview"}
    assert {item["storyboardWrite"] for item in payload["previewedTypes"].values()} == {False}
    assert {item["type"] for item in payload["previewedTypes"].values()} == {
        "set_shot_strategy",
        "split_shot",
        "merge_shot_next",
        "mark_failed",
        "retry_failed",
        "replan_affected",
    }
