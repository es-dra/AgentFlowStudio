from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_idea_projection_keeps_source_visible_and_agent_reads_same_text() -> None:
    script = r'''
import assert from "node:assert/strict";
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";
import { agentChatContextSnapshot } from "./apps/studio/src/agent-chat-lifecycle.js";

const source = "海边的修表师在暴雨前听见停摆怀表重新走动。";
const state = {
  meta: { projectId: "idea-contract", projectName: "任意项目", seq: 1 },
  nodes: {},
  edges: {},
  order: [],
  production: {},
  selection: { nodeIds: [], edgeId: null },
};
applyScriptCoreTruthProjection(state, {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "idea-contract",
  current_revision_id: "revision-1",
  current_revision: {
    revision_id: "revision-1",
    source_kind: "idea",
    source_text: source,
    source_digest: "a".repeat(64),
    source_length: source.length,
    analysis_state: "analysis_required",
  },
  revision_history: [],
  assets: [],
  asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
  analysis_state: "analysis_required",
});
const node = state.nodes[state.selection.nodeIds[0]];
const context = agentChatContextSnapshot({
  project: { project_id: "idea-contract", name: "任意项目" },
  studioState: state,
  section: "canvas",
  selectedNode: node,
});
assert.match(node.content, /创作想法/);
assert.match(node.content, /海边的修表师/);
assert.equal(node.params.scriptRevision.source_text, source);
assert.equal(context.selected_node_text, source);
assert.equal(state.production.script_core_truth_projection.source_text, source);
process.stdout.write(JSON.stringify({ content: node.content, selectedText: context.selected_node_text }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert "创作想法" in payload["content"]
    assert payload["selectedText"].startswith("海边")


def test_creator_first_sources_do_not_leak_old_media_timeout_or_default_diagnostics() -> None:
    sources = "\n".join(
        (STUDIO_ROOT / "src" / name).read_text(encoding="utf-8")
        for name in (
            "runtime-client.js",
            "embedded-creative-actions.js",
            "canvas-node-body.js",
            "agent-chat-panel.js",
        )
    )
    assert "Gateway timeout while waiting for image generation" not in sources
    assert "checking saved Runtime assets" not in sources
    assert "不要触发图片或视频能力" not in sources
    assert 'details.appendChild(el("summary", "", "技术详情"))' in sources
    assert "文本处理未完成" in sources


def test_copilot_recognizes_durable_idea_revision_without_asset_bible() -> None:
    script = r'''
import assert from "node:assert/strict";
import { deriveProductionCopilotState } from "./apps/studio/src/asset-bible-workspace.js";

const result = deriveProductionCopilotState({
  studioState: {
    nodes: {},
    edges: {},
    production: {
      script_core_truth_projection: {
        current_revision_id: "revision-any",
        source_kind: "idea",
        source_text: "一只纸船逆流而上。",
        analysis_state: "analysis_required",
      },
    },
  },
  runtimeAssetBible: null,
  capabilityGates: { llm: true, image: false, video: false },
});
assert.equal(result.stage, "story_expansion_required");
assert.equal(result.ready_summary, "想法已保存。");
assert.equal(result.next_valid_action.label, "扩写并分析故事");
assert.doesNotMatch(result.ready_summary, /从一个想法开始/);
assert.doesNotMatch(result.needs_input, /输入创作想法/);
assert.equal(result.gate.image, false);
assert.equal(result.gate.video, false);

const withPreview = deriveProductionCopilotState({
  studioState: {
    nodes: {
      "script_truth_revision_revision-any": {
        params: { embeddedCreativeAction: { status: "preview" } },
      },
    },
    edges: {},
    production: {
      script_core_truth_projection: {
        current_revision_id: "revision-any",
        source_kind: "idea",
        source_text: "一只纸船逆流而上。",
        analysis_state: "analysis_required",
      },
    },
  },
  runtimeAssetBible: null,
  capabilityGates: { llm: true, image: false, video: false },
});
assert.equal(withPreview.stage, "story_expansion_review");
assert.equal(withPreview.next_valid_action.label, "审看扩写结果");
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_projected_idea_preview_uses_exact_source_and_apply_creates_durable_revision() -> None:
    script = r'''
import assert from "node:assert/strict";
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";
import {
  applyEmbeddedCreativeAction,
  startEmbeddedCreativeAction,
} from "./apps/studio/src/embedded-creative-actions.js";
import { deriveProductionCopilotState } from "./apps/studio/src/asset-bible-workspace.js";

const original = "钟楼下，修表师听见停摆怀表重新走动。";
const revised = "暴雨将至，修表师在钟楼下听见停摆多年的怀表重新走动。";
const state = {
  meta: { projectId: "durable-idea", projectName: "任意项目", seq: 1 },
  nodes: {},
  edges: {},
  order: [],
  production: {},
  selection: { nodeIds: [], edgeId: null },
};
applyScriptCoreTruthProjection(state, {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "durable-idea",
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

const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
let previewCalls = 0;
let revisionCalls = 0;
const runtime = {
  newEmbeddedCreativeClientRequestId: () => "cli_durable_idea",
  previewEmbeddedCreativeAction: async (payload) => {
    previewCalls += 1;
    assert.equal(payload.source_text, original);
    return {
      mode: "llm",
      provider_calls_started: true,
      preview: {
        revised_text: revised,
        change_summary: ["补充天气压力与故事触发点"],
        rationale: "保持原意并形成可继续开发的故事。",
      },
      creative_task: {},
      provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
      graph_mutation: { mutated: false, scope: "preview_only" },
      cost_usd: 0,
    };
  },
  createScriptRevision: async (payload) => {
    revisionCalls += 1;
    assert.equal(payload.source_text, revised);
    assert.equal(payload.parent_revision_id, "revision-1");
    return {
      revision: { revision_id: "revision-2" },
      projection: {
        schema_version: "afs.script_core_truth.v0.1",
        project_id: "durable-idea",
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

const firstNode = state.nodes[state.selection.nodeIds[0]];
await startEmbeddedCreativeAction(store, runtime, firstNode, "script_revision");
assert.equal(firstNode.params.embeddedCreativeAction.status, "preview");
const applied = await applyEmbeddedCreativeAction(store, firstNode.id, runtime);
assert.equal(applied, true);
assert.equal(previewCalls, 1);
assert.equal(revisionCalls, 1);
assert.equal(state.production.script_core_truth_projection.current_revision_id, "revision-2");
assert.equal(state.production.script_core_truth_projection.source_text, revised);
const appliedNode = state.nodes["script_truth_revision_revision-2"];
assert.equal(appliedNode.params.scriptRevision.source_text, revised);
assert.equal(appliedNode.params.embeddedCreativeAction.status, "applied");
assert.equal(state.nodes[firstNode.id], undefined);
const next = deriveProductionCopilotState({
  studioState: state,
  runtimeAssetBible: null,
  capabilityGates: { llm: true, image: false, video: false },
});
assert.equal(next.next_valid_action.action, "prepare_production_plan");
assert.equal(next.next_valid_action.label, "准备制作方案");
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_complete_script_routes_to_text_only_storyboard_review_and_recovery() -> None:
    script = r'''
import assert from "node:assert/strict";
import { deriveProductionCopilotState } from "./apps/studio/src/asset-bible-workspace.js";

const source = "第一场\n外景，河岸，清晨。邮差把一封无人认领的信放进纸船，纸船逆流而上。\n第二场\n内景，旧邮局，夜。";
const base = {
  nodes: {
    script_any: {
      id: "script_any",
      type: "script",
      title: "完整剧本",
      content: source,
      params: {},
    },
  },
  edges: {},
  production: {},
  selection: { nodeIds: ["script_any"], edgeId: null },
};
const required = deriveProductionCopilotState({
  studioState: structuredClone(base),
  capabilityGates: { llm: true, image: true, video: true },
});
assert.equal(required.stage, "storyboard_breakdown_required");
assert.equal(required.next_valid_action.action, "preview_storyboard_breakdown");
assert.equal(required.next_valid_action.label, "拆分并审阅分镜");
assert.equal(required.gate.image, false);
assert.equal(required.gate.video, false);
assert.doesNotMatch(required.ready_summary, /从一个想法开始/);

const failedState = structuredClone(base);
failedState.nodes.script_any.params.embeddedCreativeAction = {
  action_type: "shot_breakdown",
  status: "unavailable",
  provider_lineage: { provider_dispatch_count: 1 },
};
const failed = deriveProductionCopilotState({
  studioState: failedState,
  capabilityGates: { llm: true, image: true, video: true },
});
assert.equal(failed.stage, "storyboard_breakdown_recovery");
assert.equal(failed.next_valid_action.label, "重新预览分镜");
assert.equal(failed.gate.image, false);
assert.equal(failed.gate.video, false);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_fastapi_array_validation_error_is_creator_safe_chinese() -> None:
    script = r'''
import assert from "node:assert/strict";

globalThis.window = {
  location: { origin: "https://afstudio.art", search: "?project=validation-project" },
  localStorage: {
    getItem: () => "",
    setItem: () => {},
    removeItem: () => {},
  },
  dispatchEvent: () => {},
};
globalThis.localStorage = window.localStorage;
globalThis.fetch = async () => ({
  ok: false,
  status: 422,
  statusText: "Unprocessable Entity",
  headers: { get: () => "" },
  text: async () => JSON.stringify({
    detail: [{
      type: "string_too_short",
      loc: ["body", "source_text"],
      msg: "Value error, creator input is required",
    }],
  }),
});
const { commitProjectIdentity } = await import("./apps/studio/src/project-identity-gate.js");
commitProjectIdentity({ projectId: "validation-project" });
const { createRuntimeClient } = await import("./apps/studio/src/runtime-client.js");
const runtime = createRuntimeClient("validation-project");
await assert.rejects(
  runtime.previewEmbeddedCreativeAction({
    action_type: "script_revision",
    node_id: "script",
    node_type: "script",
    source_text: "",
    generated_at: "2026-07-27T00:00:00Z",
  }, { clientRequestId: "cli_validation_array" }),
  (error) => {
    assert.equal(error.message, "请先输入创作想法或剧本文本。");
    assert.doesNotMatch(error.message, /Value error|source_text|字段|schema/i);
    return true;
  },
);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_explicit_project_url_never_falls_back_to_cached_project() -> None:
    script = r'''
import assert from "node:assert/strict";
const values = new Map([["afs_studio_active_project_id", "cached-project"]]);
globalThis.localStorage = { getItem: (key) => values.get(key) || "" };
globalThis.window = {
  location: { search: "?project=exact-project" },
  localStorage: globalThis.localStorage,
};
const { initialProjectId } = await import("./apps/studio/src/studio-project-session.js");
assert.equal(initialProjectId(), "exact-project");
window.location.search = "?project=";
assert.equal(initialProjectId(), "studio-invalid-project");
window.location.search = "?project=bad/project";
assert.equal(initialProjectId(), "studio-invalid-project");
window.location.search = "";
assert.equal(initialProjectId(), "cached-project");
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_refresh_sanitizes_legacy_text_failure_without_replaying_it() -> None:
    script = r'''
import assert from "node:assert/strict";
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";

const source = "荒原上的邮差追逐一封会飞的信。";
const nodeId = "script_truth_revision_revision-legacy";
const state = {
  meta: { projectId: "legacy-recovery" },
  nodes: {
    [nodeId]: {
      id: nodeId,
      type: "script",
      params: {
        projectionFlags: ["script_core_truth_projection"],
        scriptRevision: { revision_id: "revision-legacy", source_text: source },
        embeddedCreativeAction: {
          action_id: "embedded-legacy",
          action_type: "script_revision",
          status: "unavailable",
          message: "Gateway timeout while waiting for image generation; checking saved Runtime assets may recover the result.",
          error: "Gateway timeout while waiting for image generation",
          error_detail: "Runtime assets",
        },
      },
    },
  },
  edges: {},
  order: [nodeId],
  production: {},
  selection: { nodeIds: [nodeId], edgeId: null },
};
applyScriptCoreTruthProjection(state, {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "legacy-recovery",
  current_revision_id: "revision-legacy",
  current_revision: {
    revision_id: "revision-legacy",
    source_kind: "idea",
    source_text: source,
    source_digest: "c".repeat(64),
    source_length: source.length,
    analysis_state: "analysis_required",
  },
  revision_history: [],
  assets: [],
  asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
  analysis_state: "analysis_required",
});
const action = state.nodes[nodeId].params.embeddedCreativeAction;
assert.equal(action.status, "unavailable");
assert.equal(action.message, "文本优化未完成；原始想法已保留。");
assert.equal(action.error_detail, "");
assert.doesNotMatch(JSON.stringify(action), /Gateway|image generation|Runtime assets/);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )
