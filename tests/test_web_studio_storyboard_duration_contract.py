from __future__ import annotations

import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_storyboard_duration_contract_is_creator_visible_and_fail_closed() -> None:
    script = r'''
import assert from "node:assert/strict";
import {
  DEFAULT_SHORT_FILM_DURATION_SECONDS,
  isValidStoryboardDuration,
  productionBriefForSource,
  shotPlanDurationAssessment,
} from "./apps/studio/src/storyboard-duration-contract.js";
import {
  applyEmbeddedCreativeAction,
  prepareEmbeddedShotBreakdown,
  startEmbeddedCreativeAction,
  updateEmbeddedStoryboardBrief,
} from "./apps/studio/src/embedded-creative-actions.js";

assert.equal(DEFAULT_SHORT_FILM_DURATION_SECONDS, 120);
assert.equal(isValidStoryboardDuration(5), true);
assert.equal(isValidStoryboardDuration(3600), true);
assert.equal(isValidStoryboardDuration(4), false);
assert.equal(isValidStoryboardDuration(3601), false);
assert.deepEqual(
  productionBriefForSource("这是一部总时长约 90 秒的任意故事。"),
  {
    target_duration_seconds: 90,
    duration_source: "script_explicit",
    tolerance_seconds: 9,
    requires_creator_confirmation: true,
  },
);
assert.equal(
  productionBriefForSource("任意多行剧本\n没有声明成片时长。").target_duration_seconds,
  120,
);
assert.equal(
  productionBriefForSource("目标时长 2 分钟。").target_duration_seconds,
  120,
);
const sixMinuteBrief = productionBriefForSource("这是一部目标总时长约 6 分钟的完整故事。");
assert.equal(sixMinuteBrief.target_duration_seconds, 360);
assert.equal(sixMinuteBrief.duration_source, "script_explicit");
assert.equal(sixMinuteBrief.tolerance_seconds, 36);
const sixMinuteAssessment = shotPlanDurationAssessment({
  estimated_duration_sec: 360,
  scenes: [{
    title: "任意场景",
    shots: Array.from({ length: 6 }, (_, index) => ({
      title: `任意镜头 ${index + 1}`,
      duration_sec: 60,
    })),
  }],
}, sixMinuteBrief);
assert.equal(sixMinuteAssessment.target_duration_seconds, 360);
assert.equal(sixMinuteAssessment.candidate_duration_seconds, 360);
assert.equal(sixMinuteAssessment.tolerance_seconds, 36);
assert.equal(sixMinuteAssessment.apply_allowed, true);

const longPlan = {
  estimated_duration_sec: 530,
  scenes: Array.from({ length: 5 }, (_, sceneIndex) => ({
    title: `场景 ${sceneIndex + 1}`,
    shots: Array.from({ length: 6 }, (_, shotIndex) => ({
      title: `镜头 ${shotIndex + 1}`,
      duration_sec: sceneIndex === 4 && shotIndex === 5 ? 22 : 26,
    })),
  })),
};
const longAssessment = shotPlanDurationAssessment(longPlan, productionBriefForSource(""));
assert.equal(longAssessment.candidate_duration_seconds, 776);
assert.equal(longAssessment.provider_estimated_duration_seconds, 530);
assert.equal(longAssessment.target_duration_seconds, 120);
assert.equal(longAssessment.apply_allowed, false);

const source = "第一场，城市天台，清晨。人物把一封信放进纸船。";
const state = {
  meta: { projectId: "duration-contract", projectName: "任意项目" },
  nodes: {
    script: {
      id: "script",
      type: "script",
      content: source,
      params: {
        scriptRevision: {
          revision_id: "revision-any",
          source_digest: "a".repeat(64),
          source_text: source,
        },
      },
    },
  },
  edges: {},
  order: ["script"],
  selection: { nodeIds: ["script"], edgeId: null },
  production: {},
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
let previewCalls = 0;
let lastPayload = null;
const runtime = {
  newEmbeddedCreativeClientRequestId: () => "cli_duration_contract",
  previewEmbeddedCreativeAction: async (payload) => {
    previewCalls += 1;
    lastPayload = payload;
    return {
      mode: "llm",
      action_type: "shot_breakdown",
      provider_calls_started: true,
      preview: {
        revised_text: "分镜候选保留完整结构，并严格按照当前创作者确认的目标总时长进行逐镜头分配。",
        change_summary: ["拆分场景", "分配时长"],
        rationale: "只生成文字分镜预览。",
        shot_plan: {
          estimated_duration_sec: 60,
          scenes: [{
            title: "城市天台",
            purpose: "建立任务",
            shots: [
              { title: "纸船", duration_sec: 30 },
              { title: "远方", duration_sec: 30 },
            ],
          }],
        },
        production_brief: {
          target_duration_seconds: 60,
          duration_source: "creator_selected",
          tolerance_seconds: 1,
          source_revision_id: "revision-any",
          source_digest: "a".repeat(64),
        },
      },
      safe_manifest: {
        request_digest: "b".repeat(64),
        source_digest: "a".repeat(64),
      },
      provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
      graph_mutation: { mutated: false },
      creative_task: {},
    };
  },
};

prepareEmbeddedShotBreakdown(store, state.nodes.script);
assert.equal(state.nodes.script.params.embeddedCreativeAction.status, "briefing");
assert.equal(previewCalls, 0);
const selectedBrief = updateEmbeddedStoryboardBrief(store, "script", 60);
assert.equal(updateEmbeddedStoryboardBrief(store, "script", 4), null);
await startEmbeddedCreativeAction(store, runtime, state.nodes.script, "shot_breakdown", {
  mode: "dynamic_shot_breakdown",
  productionBrief: selectedBrief,
});
assert.equal(previewCalls, 1);
assert.equal(lastPayload.source_text, source);
assert.equal(lastPayload.source_revision_id, "revision-any");
assert.equal(lastPayload.source_digest, "a".repeat(64));
assert.equal(lastPayload.production_brief.target_duration_seconds, 60);
assert.equal(lastPayload.production_brief.duration_source, "creator_selected");

state.nodes.script.params.embeddedCreativeAction = {
  action_id: "historical-overlong",
  action_type: "shot_breakdown",
  status: "preview",
  source_text: source,
  preview: { shot_plan: longPlan },
};
const applied = await applyEmbeddedCreativeAction(store, "script", null);
assert.equal(applied, false);
assert.equal(state.nodes.script.params.embeddedCreativeAction.status, "preview");
assert.match(state.nodes.script.params.embeddedCreativeAction.message, /不能直接应用/);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_duration_contract_has_no_sample_specific_branch() -> None:
    source = (STUDIO_ROOT / "src" / "storyboard-duration-contract.js").read_text(encoding="utf-8")
    for sample in ("唐僧", "白骨精", "白骨成亲", "776", "5 场", "30 镜头"):
        assert sample not in source


def test_storyboard_preview_creates_and_reuses_current_script_truth_revision() -> None:
    script = r'''
import assert from "node:assert/strict";
import {
  prepareEmbeddedShotBreakdown,
  startEmbeddedCreativeAction,
  updateEmbeddedStoryboardBrief,
} from "./apps/studio/src/embedded-creative-actions.js";

const source = "《海边的信》\n第一场 海边，清晨。苏晴把一封旧信放进漂流瓶。\n第二场 灯塔，夜。她读完迟到多年的回信。";
const digest = "a".repeat(64);
const editedSource = `${source}\n第三场 苏晴的房间，深夜。她开始写第十八封信。`;
const editedDigest = "c".repeat(64);
const rapidSource = `${editedSource}\n尾声 海面恢复平静。`;
const rapidDigest = "d".repeat(64);
const state = {
  meta: { projectId: "seaside-letter", projectName: "海边的信", seq: 1 },
  nodes: {
    pasted: {
      id: "pasted",
      type: "text",
      title: "粘贴的剧本",
      content: source,
      prompt: source,
      params: {},
      status: "draft",
    },
  },
  edges: {},
  order: ["pasted"],
  selection: { nodeIds: ["pasted"], edgeId: null },
  production: {},
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
const calls = [];
const runtime = {
  newEmbeddedCreativeClientRequestId: () => `cli_${calls.length}`,
  createScriptRevision: async (payload) => {
    calls.push({ type: "revision", payload });
    const revisionId = payload.source_text === rapidSource
      ? "scrrev-seaside-3"
      : payload.provenance.node_id === "mismatch"
        ? "scrrev-seaside-4"
        : payload.source_text === editedSource
          ? "scrrev-seaside-2"
          : "scrrev-seaside-1";
    const revisionDigest = payload.source_text === rapidSource
      ? rapidDigest
      : payload.source_text === editedSource
        ? editedDigest
        : digest;
    return {
      revision: {
        project_id: "seaside-letter",
        revision_id: revisionId,
        source_kind: "script",
        source_text: payload.source_text,
        source_digest: revisionDigest,
        source_length: payload.source_text.length,
        analysis_state: "analysis_required",
      },
      projection: {
        schema_version: "afs.script_core_truth.v0.1",
        project_id: "seaside-letter",
        current_revision_id: revisionId,
        current_revision: {
          project_id: "seaside-letter",
          revision_id: revisionId,
          source_kind: "script",
          source_text: payload.source_text,
          source_digest: revisionDigest,
          source_length: payload.source_text.length,
          analysis_state: "analysis_required",
        },
        assets: [],
        asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
        analysis_state: "analysis_required",
      },
    };
  },
  previewEmbeddedCreativeAction: async (payload) => {
    calls.push({ type: "preview", payload });
    return {
      mode: "llm",
      action_type: "shot_breakdown",
      provider_calls_started: true,
      preview: {
        revised_text: source,
        shot_plan: { estimated_duration_sec: 60, scenes: [] },
        production_brief: payload.production_brief,
      },
      safe_manifest: { request_digest: "b".repeat(64), source_digest: digest },
      provider_lineage: { provider_calls_started: true, provider_dispatch_count: 1 },
      graph_mutation: { mutated: false },
      creative_task: {},
    };
  },
};

prepareEmbeddedShotBreakdown(store, state.nodes.pasted);
const firstBrief = updateEmbeddedStoryboardBrief(store, "pasted", 60);
await startEmbeddedCreativeAction(store, runtime, state.nodes.pasted, "shot_breakdown", {
  productionBrief: firstBrief,
});
assert.deepEqual(calls.map((call) => call.type), ["revision", "preview"]);
assert.equal(calls[0].payload.source_text, source);
assert.equal(calls[0].payload.parent_revision_id, null);
assert.equal(calls[1].payload.source_revision_id, "scrrev-seaside-1");
assert.equal(calls[1].payload.source_digest, digest);
assert.equal(calls[1].payload.production_brief.source_revision_id, "scrrev-seaside-1");
assert.equal(calls[1].payload.production_brief.source_digest, digest);

const canonical = state.nodes["script_truth_revision_scrrev-seaside-1"];
assert.ok(canonical);
assert.equal(state.selection.nodeIds[0], canonical.id);
assert.equal(canonical.params.embeddedCreativeAction.status, "preview");
assert.equal(state.nodes.pasted.params.embeddedCreativeAction, undefined);

prepareEmbeddedShotBreakdown(store, canonical);
const secondBrief = updateEmbeddedStoryboardBrief(store, canonical.id, 60);
await startEmbeddedCreativeAction(store, runtime, canonical, "shot_breakdown", {
  productionBrief: secondBrief,
});
assert.deepEqual(calls.map((call) => call.type), ["revision", "preview", "preview"]);
assert.equal(calls[2].payload.source_revision_id, "scrrev-seaside-1");
assert.equal(calls[2].payload.production_brief.source_revision_id, "scrrev-seaside-1");

state.nodes.edited = {
  id: "edited",
  type: "text",
  title: "编辑后的剧本",
  content: editedSource,
  prompt: editedSource,
  params: { scriptRevision: { ...canonical.params.scriptRevision } },
  status: "draft",
};
state.order.push("edited");
state.selection = { nodeIds: ["edited"], edgeId: null };
prepareEmbeddedShotBreakdown(store, state.nodes.edited);
const editedBrief = updateEmbeddedStoryboardBrief(store, "edited", 75);
await startEmbeddedCreativeAction(store, runtime, state.nodes.edited, "shot_breakdown", {
  productionBrief: editedBrief,
});
assert.deepEqual(
  calls.map((call) => call.type),
  ["revision", "preview", "preview", "revision", "preview"],
);
assert.equal(calls[3].payload.source_text, editedSource);
assert.equal(calls[3].payload.parent_revision_id, "scrrev-seaside-1");
assert.equal(calls[4].payload.source_revision_id, "scrrev-seaside-2");
assert.equal(calls[4].payload.source_digest, editedDigest);
assert.equal(calls[4].payload.production_brief.source_revision_id, "scrrev-seaside-2");
assert.equal(calls[4].payload.production_brief.source_digest, editedDigest);

state.nodes.rapid = {
  id: "rapid",
  type: "text",
  title: "快速确认的剧本",
  content: rapidSource,
  prompt: rapidSource,
  params: {},
  status: "draft",
};
state.order.push("rapid");
state.selection = { nodeIds: ["rapid"], edgeId: null };
prepareEmbeddedShotBreakdown(store, state.nodes.rapid);
const rapidBrief = updateEmbeddedStoryboardBrief(store, "rapid", 80);
await Promise.all([
  startEmbeddedCreativeAction(store, runtime, state.nodes.rapid, "shot_breakdown", {
    productionBrief: rapidBrief,
  }),
  startEmbeddedCreativeAction(store, runtime, state.nodes.rapid, "shot_breakdown", {
    productionBrief: rapidBrief,
  }),
]);
assert.deepEqual(
  calls.map((call) => call.type),
  ["revision", "preview", "preview", "revision", "preview", "revision", "preview"],
);
assert.equal(calls[5].payload.parent_revision_id, "scrrev-seaside-2");
assert.equal(calls[6].payload.source_revision_id, "scrrev-seaside-3");
assert.equal(calls[6].payload.production_brief.source_revision_id, "scrrev-seaside-3");

const offlineSource = `${source}\n尾声 她把最后一封信收进抽屉。`;
const offlineState = {
  meta: { projectId: "seaside-letter", projectName: "海边的信", seq: 1 },
  nodes: {
    offline: {
      id: "offline",
      type: "text",
      title: "离线剧本",
      content: offlineSource,
      prompt: offlineSource,
      params: {},
      status: "draft",
    },
  },
  edges: {},
  order: ["offline"],
  selection: { nodeIds: ["offline"], edgeId: null },
  production: {},
};
const offlineStore = {
  get: () => offlineState,
  set: (mutator) => mutator(offlineState),
  flushRuntimeSave: async () => {},
};
const offlineRuntime = { ...runtime };
delete offlineRuntime.previewEmbeddedCreativeAction;
prepareEmbeddedShotBreakdown(offlineStore, offlineState.nodes.offline);
const offlineBrief = updateEmbeddedStoryboardBrief(offlineStore, "offline", 60);
await startEmbeddedCreativeAction(offlineStore, offlineRuntime, offlineState.nodes.offline, "shot_breakdown", {
  productionBrief: offlineBrief,
});
const offlineCanonical = offlineState.nodes["script_truth_revision_scrrev-seaside-1"];
assert.equal(offlineCanonical.params.embeddedCreativeAction.status, "unavailable");
assert.equal(offlineState.nodes.offline.params.embeddedCreativeAction, undefined);

function corruptedProjectionState(nodeId, bindingDigest = digest, projectionSource = source) {
  return {
    meta: { projectId: "seaside-letter", projectName: "海边的信", seq: 1 },
    nodes: {
      [nodeId]: {
        id: nodeId,
        type: "script",
        title: "损坏的本地投影",
        content: "本地摘要",
        prompt: "",
        params: {
          scriptCoreProjection: "script_core_truth_projection",
          scriptRevision: {
            revision_id: "scrrev-corrupt-current",
            source_digest: bindingDigest,
            source_text: source,
          },
        },
        status: "draft",
      },
    },
    edges: {},
    order: [nodeId],
    selection: { nodeIds: [nodeId], edgeId: null },
    production: {
      script_core_truth_projection: {
        current_revision_id: "scrrev-corrupt-current",
        source_digest: digest,
        source_text: projectionSource,
      },
    },
  };
}

const mismatchState = corruptedProjectionState("mismatch", "e".repeat(64));
const mismatchStore = {
  get: () => mismatchState,
  set: (mutator) => mutator(mismatchState),
  flushRuntimeSave: async () => {},
};
const mismatchNode = mismatchState.nodes.mismatch;
prepareEmbeddedShotBreakdown(mismatchStore, mismatchNode);
const mismatchBrief = updateEmbeddedStoryboardBrief(mismatchStore, mismatchNode.id, 60);
await startEmbeddedCreativeAction(mismatchStore, runtime, mismatchNode, "shot_breakdown", {
  productionBrief: mismatchBrief,
});
assert.deepEqual(calls.slice(-2).map((call) => call.type), ["revision", "preview"]);
assert.equal(calls.at(-2).payload.parent_revision_id, "scrrev-corrupt-current");
assert.equal(calls.at(-1).payload.source_revision_id, "scrrev-seaside-4");
assert.equal(calls.at(-1).payload.source_digest, digest);

const sourceMismatchState = corruptedProjectionState("source-mismatch", digest, "陈旧的顶层文本");
const sourceMismatchStore = {
  get: () => sourceMismatchState,
  set: (mutator) => mutator(sourceMismatchState),
  flushRuntimeSave: async () => {},
};
const sourceMismatchNode = sourceMismatchState.nodes["source-mismatch"];
prepareEmbeddedShotBreakdown(sourceMismatchStore, sourceMismatchNode);
const sourceMismatchBrief = updateEmbeddedStoryboardBrief(sourceMismatchStore, sourceMismatchNode.id, 60);
await startEmbeddedCreativeAction(sourceMismatchStore, runtime, sourceMismatchNode, "shot_breakdown", {
  productionBrief: sourceMismatchBrief,
});
assert.deepEqual(calls.slice(-2).map((call) => call.type), ["revision", "preview"]);
assert.equal(calls.at(-2).payload.parent_revision_id, "scrrev-corrupt-current");

const malformedState = corruptedProjectionState("malformed", "e".repeat(64));
const malformedStore = {
  get: () => malformedState,
  set: (mutator) => mutator(malformedState),
  flushRuntimeSave: async () => {},
};
const malformedRuntime = {
  ...runtime,
  createScriptRevision: async (payload) => ({
    revision: {
      revision_id: "scrrev-response",
      source_text: payload.source_text,
      source_digest: digest,
    },
    projection: {
      schema_version: "afs.script_core_truth.v0.1",
      project_id: "seaside-letter",
      current_revision_id: "scrrev-projection",
      current_revision: {
        project_id: "seaside-letter",
        revision_id: "scrrev-projection",
        source_kind: "script",
        source_text: payload.source_text,
        source_digest: digest,
      },
      assets: [],
      asset_counts: { characters: 0, main_scenes: 0, manual_props: 0 },
      analysis_state: "analysis_required",
    },
  }),
};
const malformedNode = malformedState.nodes.malformed;
prepareEmbeddedShotBreakdown(malformedStore, malformedNode);
const malformedBrief = updateEmbeddedStoryboardBrief(malformedStore, malformedNode.id, 60);
const previewCallsBeforeMalformedResponse = calls.filter((call) => call.type === "preview").length;
await startEmbeddedCreativeAction(malformedStore, malformedRuntime, malformedNode, "shot_breakdown", {
  productionBrief: malformedBrief,
});
assert.ok(malformedState.nodes.malformed);
assert.equal(malformedState.production.script_core_truth_projection.current_revision_id, "scrrev-corrupt-current");
assert.equal(malformedState.nodes.malformed.params.embeddedCreativeAction.status, "unavailable");
assert.equal(
  calls.filter((call) => call.type === "preview").length,
  previewCallsBeforeMalformedResponse,
);
'''
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=STUDIO_ROOT.parents[1],
        check=True,
    )


def test_plan_entry_uses_only_the_current_script_revision_binding() -> None:
    source = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert 'textarea.setAttribute("aria-label", "当前已应用剧本")' in source
    assert "textarea.readOnly = true" in source
    assert 'source_kind: "script"' in source
    assert "source_revision_id: sourceBinding.revision_id" in source
    assert "source_revision_digest: sourceBinding.source_digest" in source
    assert "previewM6ScriptPlan(textarea.value)" not in source
    assert "|| currentReadyScriptNode()?.id" not in source
    assert "|| currentReadyScriptNode()," not in source
