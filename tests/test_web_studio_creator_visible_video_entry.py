from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "apps" / "studio"


def _run_node(source: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_video_preparation_conversation_receives_same_graph_readiness_context() -> None:
    result = _run_node(
        r'''
import { submitAgentChatMessageWithRuntime } from "./apps/studio/src/agent-chat-lifecycle.js";

const session = { context_key: "project:shot-01", messages: [], receipts: [] };
const calls = [];
const runtime = {
  agentChatConversation(payload) {
    calls.push(payload);
    return Promise.resolve({
      mode: "llm",
      provider_calls_started: true,
      reply: "当前镜头已有已批准关键帧和 3 张参考图。请使用页面上的“准备镜头视频”入口审核真实确认卡；我没有创建清单或发送任务。",
      suggested_actions: ["准备镜头视频"],
      provider_lineage: { service_id: "server_codex" },
    });
  },
};
const outcome = await submitAgentChatMessageWithRuntime(
  session,
  "请为当前镜头准备生成视频，先展示完整确认卡，不要自动发送。",
  {
    project_id: "project",
    selected_node_id: "shot-01",
    section: "storyboard_read_only",
    counts: { nodes: 8, edges: 7, assets: 4 },
    video_readiness_status: "ready",
    video_selected_shot_ready: true,
    video_shot_label: "镜头 01",
    video_keyframe_label: "已批准关键帧",
    video_reference_count: 3,
    video_model: "doubao-seedance-2-0",
    video_resolution: "720p",
    video_duration_sec: 6,
  },
  runtime,
);
process.stdout.write(JSON.stringify({
  outcome,
  calls,
  messages: session.messages,
}));
'''
    )

    assert result["outcome"]["status"] == "answered"
    assert len(result["calls"]) == 1
    summary = result["calls"][0]["canvas_summary"]
    assert summary["video_readiness_status"] == "ready"
    assert summary["video_selected_shot_ready"] == 1
    assert summary["video_shot_label"] == "镜头 01"
    assert summary["video_keyframe_label"] == "已批准关键帧"
    assert summary["video_reference_count"] == 3
    assert summary["video_model"] == "doubao-seedance-2-0"
    assert summary["video_resolution"] == "720p"
    assert summary["video_duration_sec"] == 6
    assert [item["role"] for item in result["messages"]] == ["user", "assistant"]
    assert "已有已批准关键帧和 3 张参考图" in result["messages"][1]["text"]
    assert "没有创建清单或发送任务" in result["messages"][1]["text"]


def test_copilot_prioritizes_ready_selected_shot_video_over_next_image_batch() -> None:
    result = _run_node(
        r'''
import { deriveProductionCopilotState } from "./apps/studio/src/asset-bible-workspace.js";

const bible = {
  schema_version: "afs.asset_bible.v0.1",
  status: "locked",
  locked_revision_id: "asset-bible-r9",
  candidate_set: { script_revision_id: "script-r1", shot_count: 3, scene_count: 1 },
  coverage: {
    coverage_pass: true,
    quality_pass: true,
    shot_total: 3,
    shot_covered: 3,
    unresolved_required: 0,
  },
  recognition_quality: { status: "pass", issues: [] },
  art_direction: {
    visual_style: "写实电影",
    medium: "电影摄影",
    palette: "冷暖对比",
    lighting: "月台侧光",
    confirmed_at: "2026-07-26T00:00:00Z",
  },
  assets: [{
    stable_id: "asset-character",
    asset_type: "character",
    display_name: "角色甲",
    review_state: "approved",
    visual_identity: "稳定面部轮廓与服装",
    positive_traits: ["清晰身份特征"],
    pending_fields: [],
    continuity_states: [{ label: "造型连续", status: "confirmed" }],
    occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01"] },
  }],
};
const common = {
  studioState: { assetBible: bible, nodes: {} },
  capabilityGates: { image: true, video: true },
  section: "storyboard",
  imageAdmission: {
    status: "locked",
    counts: {
      approved: 1,
      rejected: 0,
      planned: 0,
      reserved: 0,
      processing: 0,
      candidate: 0,
      failed: 0,
    },
    budget: { dispatches_reserved: 0 },
    provider_dispatch_count: 1,
  },
};
const ready = deriveProductionCopilotState({
  ...common,
  videoAdmission: {
    status: "empty",
    readiness: { status: "ready", shot_id: "shot-01", reference_count: 3 },
    selected_shot_ready: true,
  },
});
const otherShot = deriveProductionCopilotState({
  ...common,
  videoAdmission: {
    status: "empty",
    readiness: { status: "ready", shot_id: "shot-01", reference_count: 3 },
    selected_shot_ready: false,
  },
});
const planned = deriveProductionCopilotState({
  ...common,
  videoAdmission: {
    status: "locked",
    readiness: { status: "ready", shot_id: "shot-01", reference_count: 3 },
    selected_shot_ready: true,
    item: { state: "planned" },
  },
});
const newRound = deriveProductionCopilotState({
  ...common,
  videoAdmission: {
    status: "locked",
    readiness: {
      status: "new_round_ready",
      shot_id: "shot-01",
      reference_count: 3,
      new_round_allowed: true,
    },
    selected_shot_ready: true,
    item: { state: "reconcile_required" },
  },
});
process.stdout.write(JSON.stringify({ ready, otherShot, planned, newRound }));
'''
    )

    assert result["ready"]["next_valid_action"] == {
        "action": "prepare_shot_video",
        "label": "准备镜头视频",
        "reason": "当前镜头的已批准关键帧和参考组已就绪；先审核视频准备清单，不会发送外部任务。",
        "enabled": True,
    }
    assert result["ready"]["provider_dispatch_count"] == 1
    assert result["otherShot"]["next_valid_action"]["action"] == "image_admission_ready"
    assert result["otherShot"]["next_valid_action"]["label"] == "准备下一批图片"
    assert result["planned"]["next_valid_action"] == {
        "action": "review_video_admission",
        "label": "确认镜头视频",
        "reason": "视频准备清单已保存；下一步审核最终模型、参考组、时长和费用停止线，再决定是否发送。",
        "enabled": True,
    }
    assert result["newRound"]["next_valid_action"] == {
        "action": "prepare_shot_video",
        "label": "建立新视频清单",
        "reason": "上一次发送已安全归档；可建立新的单次视频清单，不会重放旧任务。",
        "enabled": True,
    }


def test_safe_video_new_round_readiness_is_creator_visible() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    bible = (STUDIO / "src" / "asset-bible-workspace.js").read_text(encoding="utf-8")
    workspace = (STUDIO / "src" / "video-admission-workspace.js").read_text(encoding="utf-8")

    assert '"new_round_ready"' in workspace
    assert "videoAdmissionCanEnterPanel(videoAdmissionView().readiness)" in shell
    assert "videoAdmissionCanPrepare(videoAdmissionView().readiness)" in shell
    assert "safeNewRoundVideo" in shell
    assert "建立新视频清单" in shell
    assert "videoAdmissionCanPrepare(videoAdmission?.readiness)" in bible


def test_storyboard_copilot_and_chat_share_real_video_admission_preview() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    panel = (STUDIO / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    workspace = (STUDIO / "src" / "video-admission-workspace.js").read_text(encoding="utf-8")
    runtime = (STUDIO / "src" / "runtime-client.js").read_text(encoding="utf-8")

    storyboard = shell.split("function buildStoryboardContent()", 1)[1].split(
        "function buildMediaOperationsContent()", 1
    )[0]
    assert '"准备镜头视频"' in storyboard
    assert "currentShotVideoAdmissionReady()" in storyboard
    assert "openCurrentShotVideoPreparation()" in storyboard
    assert "shot_id: view.source?.shot?.shot_id || currentShot().graphNodeId || \"\"" in shell
    assert "loadCurrentShotVideoAdmission" in shell
    assert "previewVideoAdmissionRuntimeCommand" in shell
    assert "confirmVideoAdmissionRuntimeCommand" in shell
    assert "selectedShotId !== (currentShot().graphNodeId || \"\")" in shell
    assert "loadVideoAdmissionLane(shotId)" in runtime
    assert "previewVideoAdmissionLaneCommand(shotId, payload)" in runtime
    assert "confirmVideoAdmissionLaneCommand(shotId, payload)" in runtime

    open_flow = shell.split("async function openCurrentShotVideoPreparation()", 1)[1].split(
        "function handleAgentVideoPreparation()", 1
    )[0]
    assert "focusVideoAdmissionPanel()" in open_flow
    assert 'stageVideoAdmissionCommand({ type: "compile" })' not in open_flow
    assert 'section = "storyboard"' in open_flow

    assert 'action.action === "prepare_shot_video"' in shell
    assert "submitAgentChatMessageWithRuntime" in panel
    for field in (
        "video_readiness_status",
        "video_selected_shot_ready",
        "video_keyframe_label",
        "video_reference_count",
        "video_model",
        "video_resolution",
        "video_duration_sec",
    ):
        assert field in shell
    assert "isVideoPreparationIntent" not in workspace


def test_video_confirmation_remains_two_step_and_never_auto_dispatches_from_entry() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    entry = shell.split("async function openCurrentShotVideoPreparation()", 1)[1].split(
        "async function confirmVideoAdmissionCommand()", 1
    )[0]
    assert "dispatchVideoAdmissionItem" not in entry

    confirm = shell.split("async function confirmVideoAdmissionCommand()", 1)[1].split(
        "async function commitVideoAdmissionCommand", 1
    )[0]
    assert 'if (commandType === "reserve_dispatch")' in confirm
    assert "await dispatchVideoAdmissionItem()" in confirm
    assert 'commandType === "reserve_dispatch" ? "确认并发送" : "确认"' in shell
