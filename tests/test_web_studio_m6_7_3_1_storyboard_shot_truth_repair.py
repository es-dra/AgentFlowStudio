from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


ROOT = Path(__file__).resolve().parents[1]


def run_node_probe(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


STATE_BUILDER = r'''
function shotPlan() {
  const counts = [6, 6, 5];
  let shotIndex = 0;
  return {
    schema_version: "afs.shot_plan.v0.1",
    candidate_id: "candidate_m6731",
    source_revision_id: "rev_m6731",
    total_shots: 17,
    estimated_duration_sec: 126,
    scenes: counts.map((count, sceneIndex) => ({
      scene_id: `scene_${sceneIndex + 1}`,
      title: `场景 ${sceneIndex + 1}`,
      purpose: `场景目的 ${sceneIndex + 1}`,
      shots: Array.from({ length: count }, () => {
        shotIndex += 1;
        return {
          shot_id: `shot_${shotIndex}`,
          title: `镜头 ${shotIndex}`,
          duration_sec: shotIndex === 17 ? 17 : 9,
          shot_size: "中景",
          camera_angle: "平视",
          movement: "轻微推轨",
          blocking: `调度 ${shotIndex}`,
          sound: "环境声",
          transition: "切",
          narrative_purpose: `目的 ${shotIndex}`,
        };
      }),
    })),
  };
}

function appliedState(options = {}) {
  const status = options.status || "applied";
  const includeEdges = options.includeEdges !== false;
  const includeAction = options.includeAction !== false;
  const plan = shotPlan();
  const state = {
    meta: { seq: 100 },
    selection: { nodeIds: ["sequence_1"], edgeId: null },
    nodes: {
      story: {
        id: "story",
        type: "text",
        title: "故事文本",
        content: "INT. 控制室 - 夜\n主角确认最后一次广播。",
        prompt: "INT. 控制室 - 夜\n主角确认最后一次广播。",
        params: {
          currentRevisionId: "rev_m6731",
          revisions: [{ revision_id: "rev_m6731", action_type: "shot_breakdown", shot_plan: plan }],
          shotPlanDraft: {
            ...plan,
            estimated_duration_sec: 161,
            provider_estimated_duration_sec: 126,
            duration_source: "per_shot_sum",
          },
        },
      },
      sequence_1: {
        id: "sequence_1",
        type: "sequence",
        title: "分镜序列候选",
        groupId: "candidate_m6731",
        params: {
          candidate_id: "candidate_m6731",
          nodeRole: "m6_6_shot_sequence_candidate",
          source_node_id: "story",
          source_revision_id: "rev_m6731",
          creative_task_id: "task_m6731",
          scene_count: 3,
          shot_count: 17,
          estimated_duration_sec: 161,
        },
      },
    },
    edges: {},
    order: ["story", "sequence_1"],
  };
  if (includeAction) {
    state.nodes.story.params.embeddedCreativeAction = {
      action_id: "task_m6731",
      action_type: "shot_breakdown",
      mode: "dynamic_shot_breakdown",
      status,
      message: "optimistic stale copy",
      requested_at: "2026-07-23T20:00:00Z",
      applied_at: "2026-07-23T20:10:00Z",
      applied_revision_id: "rev_m6731",
      provider_lineage: {
        service_id: "server_codex",
        provider: "codex_local",
        model_surface: "server-codex-login",
        provider_dispatch_count: 1,
        external_paid_cost_usd: 0,
      },
      preview: {
        revised_text: state.nodes.story.content,
        shot_plan: plan,
      },
      applied_subgraph: {
        candidate_id: "candidate_m6731",
        source_revision_id: "rev_m6731",
        scene_count: 3,
        shot_count: 17,
        estimated_duration_sec: 161,
        shot_plan: {
          ...plan,
          estimated_duration_sec: 161,
          provider_estimated_duration_sec: 126,
          duration_source: "per_shot_sum",
        },
      },
    };
  }
  if (includeEdges) state.edges.edge_story_sequence = { id: "edge_story_sequence", from: "story", to: "sequence_1", relation_type: "proposed" };
  let shotNumber = 0;
  for (const [sceneIndex, count] of [6, 6, 5].entries()) {
    const sceneId = `scene_${sceneIndex + 1}`;
    state.nodes[sceneId] = {
      id: sceneId,
      type: "scene",
      title: `场景 ${sceneIndex + 1}`,
      groupId: "candidate_m6731",
      params: {
        candidate_id: "candidate_m6731",
        nodeRole: "m6_6_scene_candidate",
        source_sequence_node_id: "sequence_1",
        source_revision_id: "rev_m6731",
        scene_index: sceneIndex,
      },
    };
    state.order.push(sceneId);
    if (includeEdges) state.edges[`edge_sequence_${sceneId}`] = { id: `edge_sequence_${sceneId}`, from: "sequence_1", to: sceneId, relation_type: "sequence" };
    for (let index = 0; index < count; index += 1) {
      shotNumber += 1;
      const shotId = `shot_${shotNumber}`;
      state.nodes[shotId] = {
        id: shotId,
        type: "shot",
        title: `镜头 ${shotNumber}`,
        content: `目的 ${shotNumber}`,
        groupId: "candidate_m6731",
        params: {
          candidate_id: "candidate_m6731",
          nodeRole: "m6_6_shot_candidate",
          source_scene_node_id: sceneId,
          source_revision_id: "rev_m6731",
          scene_index: sceneIndex,
          shot_index: index,
          duration_sec: shotNumber === 17 ? 17 : 9,
          narrative_purpose: `目的 ${shotNumber}`,
        },
      };
      state.order.push(shotId);
      if (includeEdges) state.edges[`edge_${sceneId}_${shotId}`] = { id: `edge_${sceneId}_${shotId}`, from: sceneId, to: shotId, relation_type: "sequence", suppress_label: true };
    }
  }
  return state;
}
'''


def test_legacy_applied_candidate_projects_to_storyboard_and_duration_sum() -> None:
    payload = run_node_probe(
        STATE_BUILDER
        + r'''
import assert from "node:assert/strict";
import { shotPlanSummary } from "./apps/studio/src/creative-task-contract.js";
import { legacyAppliedStoryboardProjection } from "./apps/studio/src/shot-truth-projection.js";

const projection = legacyAppliedStoryboardProjection(appliedState());
const summary = shotPlanSummary(shotPlan());
assert.equal(projection.status, "ready");
assert.equal(projection.source, "legacy_applied_candidate_subgraph");
assert.equal(projection.scene_count, 3);
assert.equal(projection.shot_count, 17);
assert.equal(projection.duration_sec, 161);
assert.equal(projection.scenes.length, 3);
assert.equal(projection.scenes[2].shots.length, 5);
assert.equal(summary.estimated_duration_sec, 161);
assert.equal(summary.provider_estimated_duration_sec, 126);
assert.equal(summary.duration_source, "per_shot_sum");
process.stdout.write(JSON.stringify({ projection, summary }));
'''
    )
    assert payload["projection"]["shot_count"] == 17
    assert payload["summary"]["estimated_duration_sec"] == 161


def test_storyboard_projection_excludes_preview_failed_cancelled_and_orphaned_candidates() -> None:
    payload = run_node_probe(
        STATE_BUILDER
        + r'''
import assert from "node:assert/strict";
import { legacyAppliedStoryboardProjection } from "./apps/studio/src/shot-truth-projection.js";

const statuses = ["preview", "unavailable", "cancelled", "running"];
const statusCounts = Object.fromEntries(statuses.map((status) => [status, legacyAppliedStoryboardProjection(appliedState({ status })).shot_count]));
const noAction = legacyAppliedStoryboardProjection(appliedState({ includeAction: false })).shot_count;
const noEdges = legacyAppliedStoryboardProjection(appliedState({ includeEdges: false })).shot_count;
const mixed = appliedState();
mixed.nodes.orphan_shot = {
  id: "orphan_shot",
  type: "shot",
  title: "孤立镜头",
  groupId: "candidate_m6731",
  params: {
    candidate_id: "candidate_m6731",
    nodeRole: "m6_6_shot_candidate",
    source_revision_id: "rev_m6731",
    duration_sec: 99,
  },
};
const mixedProjection = legacyAppliedStoryboardProjection(mixed);
for (const count of Object.values(statusCounts)) assert.equal(count, 0);
assert.equal(noAction, 0);
assert.equal(noEdges, 0);
assert.equal(mixedProjection.shot_count, 17);
assert.equal(mixedProjection.duration_sec, 161);
process.stdout.write(JSON.stringify({ statusCounts, noAction, noEdges, mixedShotCount: mixedProjection.shot_count }));
'''
    )
    assert all(count == 0 for count in payload["statusCounts"].values())
    assert payload["noAction"] == 0
    assert payload["noEdges"] == 0
    assert payload["mixedShotCount"] == 17


def test_product_shell_keeps_production_graph_authority_ahead_of_legacy_projection() -> None:
    shell = (ROOT / "apps/studio/src/product-shell.js").read_text(encoding="utf-8")
    scene_model = shell.split("function sceneModel()", 1)[1].split("function shotModel()", 1)[0]
    shot_model = shell.split("function shotModel()", 1)[1].split("function graphView()", 1)[0]
    assert scene_model.index("if (graphWorkspaceReady()) return graphSceneModel();") < scene_model.index("legacyAppliedStoryboardProjection")
    assert shot_model.index("if (graphWorkspaceReady()) return graphShotModel();") < shot_model.index("legacyAppliedStoryboardProjection")


def test_applied_terminal_assistant_receipt_replaces_optimistic_message_and_reconstructs_after_reload() -> None:
    payload = run_node_probe(
        STATE_BUILDER
        + r'''
import assert from "node:assert/strict";
import {
  AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID,
  EMBEDDED_CREATIVE_TASK_OPEN_PLACEHOLDER_ID,
} from "./apps/studio/src/agent-chat-lifecycle.js";
import { syncEmbeddedCreativeAssistantMessages } from "./apps/studio/src/agent-chat-panel.js";

const state = appliedState();
const session = {
  context_key: "m6731:canvas:agent-chat",
  messages: [
    {
      role: "assistant",
      text: "我会基于当前画布上下文生成命令预览；确认前不改变事实。",
      placeholder_id: AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID,
      context_key: "m6731:canvas:agent-chat",
    },
    { role: "user", text: "保留这个用户问题。" },
    {
      role: "assistant",
      text: "已在「故事文本」打开分镜拆解任务；结果会在当前任务区审阅，确认前不改动画布。",
      placeholder_id: EMBEDDED_CREATIVE_TASK_OPEN_PLACEHOLDER_ID,
      embedded_node_id: "story",
      embedded_action_type: "shot_breakdown",
    },
    { role: "assistant", text: "保留这个无关回复。" },
  ],
};
syncEmbeddedCreativeAssistantMessages(session, state);
const terminalReceipts = session.messages.filter((message) => message.embedded_terminal_key);
assert.equal(session.messages.length, 3);
assert.equal(terminalReceipts.length, 1);
assert.equal(terminalReceipts[0].tone, "success");
assert.match(terminalReceipts[0].text, /动态分镜已应用/);
assert.match(terminalReceipts[0].text, /17 镜头/);
assert.match(terminalReceipts[0].text, /161 秒/);
assert.match(terminalReceipts[0].text, /故事板/);
assert.ok(!session.messages.some((message) => message.placeholder_id === AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID));
assert.ok(!session.messages.some((message) => message.placeholder_id === EMBEDDED_CREATIVE_TASK_OPEN_PLACEHOLDER_ID));
assert.ok(!session.messages.some((message) => String(message.text || "").includes("结果会在当前任务区审阅")));
assert.ok(!session.messages.some((message) => String(message.text || "").includes("我会基于当前画布上下文生成命令预览")));
assert.ok(session.messages.some((message) => message.text === "保留这个用户问题。"));
assert.ok(session.messages.some((message) => message.text === "保留这个无关回复。"));

const restoredSession = { messages: [] };
syncEmbeddedCreativeAssistantMessages(restoredSession, state);
assert.equal(restoredSession.messages.length, 1);
assert.match(restoredSession.messages[0].text, /可重载候选分镜子图/);
process.stdout.write(JSON.stringify({ messages: session.messages, terminal: terminalReceipts[0], restored: restoredSession.messages[0] }));
'''
    )
    assert payload["terminal"]["tone"] == "success"
    assert "结果会在当前任务区审阅" not in payload["terminal"]["text"]
    assert len(payload["messages"]) == 3


def test_apply_is_idempotent_and_persists_canonical_duration_and_lineage() -> None:
    payload = run_node_probe(
        STATE_BUILDER
        + r'''
import assert from "node:assert/strict";
import { applyEmbeddedCreativeAction } from "./apps/studio/src/embedded-creative-actions.js";

const plan = shotPlan();
let state = {
  meta: { seq: 1 },
  selection: { nodeIds: ["story"], edgeId: null },
  nodes: {
    story: {
      id: "story",
      type: "text",
      title: "故事文本",
      x: 0,
      y: 0,
      w: 320,
      h: 260,
      content: "INT. 控制室 - 夜\n主角确认最后一次广播。",
      prompt: "INT. 控制室 - 夜\n主角确认最后一次广播。",
      params: {
        embeddedCreativeAction: {
          action_id: "task_m6731",
          action_type: "shot_breakdown",
          mode: "dynamic_shot_breakdown",
          status: "preview",
          source_text: "INT. 控制室 - 夜\n主角确认最后一次广播。",
          source_node_version: "",
          creative_task: { task_id: "task_m6731", state: "preview_ready", phase: "preview_ready", action_type: "shot_breakdown", mode: "dynamic_shot_breakdown" },
          provider_lineage: { service_id: "server_codex", provider: "codex_local", provider_dispatch_count: 1, external_paid_cost_usd: 0 },
          production_brief: {
            target_duration_seconds: 161,
            duration_source: "creator_selected",
            tolerance_seconds: 1,
          },
          preview: {
            revised_text: "INT. 控制室 - 夜\n主角确认最后一次广播。",
            shot_plan: plan,
            production_brief: {
              target_duration_seconds: 161,
              duration_source: "creator_selected",
              tolerance_seconds: 1,
            },
          },
          graph_mutation: { mutated: false, scope: "preview_only" },
          cost_usd: 0,
        },
      },
      status: "draft",
    },
  },
  edges: {},
  order: ["story"],
};
let flushes = 0;
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: () => {
    flushes += 1;
    return Promise.resolve();
  },
};
applyEmbeddedCreativeAction(store, "story");
applyEmbeddedCreativeAction(store, "story");
await Promise.resolve();
const nodes = Object.values(state.nodes);
const action = state.nodes.story.params.embeddedCreativeAction;
const typeCounts = Object.fromEntries(["sequence", "scene", "shot"].map((type) => [type, nodes.filter((node) => node.type === type).length]));
assert.equal(typeCounts.sequence, 1);
assert.equal(typeCounts.scene, 3);
assert.equal(typeCounts.shot, 17);
assert.equal(Object.keys(state.edges).length, 21);
assert.equal(state.nodes.story.params.revisions.length, 1);
assert.equal(action.status, "applied");
assert.equal(action.provider_lineage.provider_dispatch_count, 1);
assert.equal(action.applied_subgraph.shot_count, 17);
assert.equal(action.applied_subgraph.estimated_duration_sec, 161);
assert.equal(action.applied_subgraph.shot_plan.estimated_duration_sec, 161);
assert.equal(action.applied_subgraph.shot_plan.provider_estimated_duration_sec, 126);
assert.equal(action.applied_subgraph.shot_plan.duration_source, "per_shot_sum");
assert.equal(state.nodes.story.params.shotPlanDraft.estimated_duration_sec, 161);
assert.equal(state.nodes.story.params.shotPlanDraft.provider_estimated_duration_sec, 126);
assert.match(action.message, /故事板/);
assert.match(action.message, /161 秒/);
assert.equal(flushes, 1);
process.stdout.write(JSON.stringify({ typeCounts, edgeCount: Object.keys(state.edges).length, message: action.message, flushes }));
'''
    )
    assert payload["typeCounts"] == {"sequence": 1, "scene": 3, "shot": 17}
    assert payload["edgeCount"] == 21
    assert payload["flushes"] == 1


def test_applied_candidate_state_roundtrips_safe_lineage_fields(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-m6731-applied-shot-truth"
    client.post("/projects", json={"project_id": project_id, "goal": "Applied shot truth roundtrip"})
    state = run_node_probe(
        STATE_BUILDER
        + r'''
process.stdout.write(JSON.stringify(appliedState()));
'''
    )
    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert response.status_code == 200, response.text
    restored = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    params = restored["nodes"]["story"]["params"]
    action = params["embeddedCreativeAction"]
    assert action["status"] == "applied"
    assert action["provider_lineage"]["provider_dispatch_count"] == 1
    assert action["provider_lineage"]["external_paid_cost_usd"] == 0
    assert params["currentRevisionId"] == "rev_m6731"
    assert params["shotPlanDraft"]["candidate_id"] == "candidate_m6731"
    assert params["shotPlanDraft"]["estimated_duration_sec"] == 161
    assert params["shotPlanDraft"]["provider_estimated_duration_sec"] == 126
    assert params["shotPlanDraft"]["duration_source"] == "per_shot_sum"
    assert action["applied_subgraph"]["candidate_id"] == "candidate_m6731"
    assert action["applied_subgraph"]["shot_count"] == 17
    assert restored["edges"]["edge_story_sequence"]["relation_type"] == "proposed"
    assert restored["edges"]["edge_scene_3_shot_17"]["relation_type"] == "sequence"
