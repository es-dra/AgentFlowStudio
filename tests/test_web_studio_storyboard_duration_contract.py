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
