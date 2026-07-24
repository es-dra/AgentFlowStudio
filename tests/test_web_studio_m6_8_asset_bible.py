from __future__ import annotations

import json
import subprocess
from pathlib import Path


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


def test_asset_bible_projection_and_copilot_follow_stage_gates() -> None:
    result = run_node_probe(
        r'''
import { assetBibleProjection, deriveProductionCopilotState } from "./apps/studio/src/asset-bible-workspace.js";

const bible = {
  schema_version: "afs.asset_bible.v0.1",
  authority_mode: "legacy_studio_adapter",
  status: "candidate_review",
  version: 2,
  current_revision_id: "asset-bible-r2",
  locked_revision_id: "",
  candidate_set: { candidate_set_id: "candidate-set", script_revision_id: "script-r1", shot_count: 17, scene_count: 3 },
  coverage: { shot_total: 17, shot_covered: 17, scene_total: 3, scene_covered: 3, unresolved_required: 1, unresolved_shot_count: 1, coverage_pass: false },
  assets: [
    { stable_id: "asset-character-1", asset_type: "character", display_name: "林晚", review_state: "approved", confidence: .9, aliases: [], occurrences: { scene_ids: ["scene_1"], shot_ids: ["shot_1"] }, positive_traits: [], negative_locks: [], pending_fields: [], source_evidence: [] },
    { stable_id: "asset-prop-1", asset_type: "prop", display_name: "红绳", review_state: "candidate", confidence: .8, aliases: [], occurrences: { scene_ids: ["scene_1"], shot_ids: ["shot_1", "shot_2"] }, positive_traits: [], negative_locks: [], pending_fields: ["visual_identity"], source_evidence: [] },
  ],
};
const state = { assetBible: bible, nodes: {}, edges: {}, assets: [] };
const view = assetBibleProjection(state, null);
const copilot = deriveProductionCopilotState({ studioState: state, capabilityGates: { llm: false, image: false }, section: "asset_bible", selectedAsset: view.assets[1] });
const canonical = assetBibleProjection(state, {
  authority_mode: "canonical_production_graph",
  asset_bible: { ...bible, authority_mode: "canonical_production_graph", status: "locked", locked_revision_id: "asset-bible-r2" },
});
console.log(JSON.stringify({ view, copilot, canonical }));
''',
    )
    assert result["view"]["counts"]["total"] == 2
    assert result["view"]["counts"]["candidate"] == 1
    assert result["copilot"]["next_valid_action"]["action"] in {"open_script", "approve_selected_asset"}
    assert result["canonical"]["authority_mode"] == "canonical_production_graph"
    assert result["canonical"]["status"] == "locked"
    assert result["canonical"]["coverage"]["coverage_pass"] is False


def test_single_shell_asset_bible_and_agent_share_runtime_preview_confirm_path() -> None:
    shell = (ROOT / "apps/studio/src/product-shell.js").read_text(encoding="utf-8")
    client = (ROOT / "apps/studio/src/runtime-client.js").read_text(encoding="utf-8")
    lifecycle = (ROOT / "apps/studio/src/agent-chat-lifecycle.js").read_text(encoding="utf-8")
    panel = (ROOT / "apps/studio/src/agent-chat-panel.js").read_text(encoding="utf-8")
    styles = (ROOT / "apps/studio/styles/asset-bible.css").read_text(encoding="utf-8")

    assert 'viewButton("asset_bible", "资产 Bible")' in shell
    assert "buildAssetBibleWorkspace()" in shell
    assert "handleCopilotAction" in shell
    assert "stageAssetBibleCommand" in shell
    assert "previewAssetBibleCommand(request)" in shell
    assert "confirmAssetBibleCommand" in shell
    assert "cancelAssetBibleCommand" in shell
    assert "取消不会改变事实" in shell
    assert "当前 Asset Bible 和 ProductionGraph 均已保留" in shell
    assert "审核与版本历史" in shell
    assert "预览重分配影响" in shell
    assert "预览标记为无需" in shell
    assert 'node("code", "", asset.stable_id)' not in shell
    assert "assetOccurrenceLabel" in shell
    assert "localizedNegativeLock" in shell
    assert 'if (view.status !== "locked" && asset.review_state !== "superseded")' in shell
    assert "if (actions.childElementCount) head.appendChild(actions)" in shell
    assert "/m6/asset-bible/commands/preview" in client
    assert "/m6/asset-bible/commands/confirm" in client
    assert 'section === "asset_bible" ? "asset_bible"' in lifecycle
    assert "selected_asset_id" in lifecycle
    assert "productionCopilot" in panel
    assert 'context?.section === "asset_bible"' in panel
    assert '当前：${currentTitle || fallbackTitle}' in panel
    assert "结构已就绪，但图片/视频媒体能力未启用" in panel
    product_styles = (ROOT / "apps/studio/styles/product-shell.css").read_text(encoding="utf-8")
    assert "grid-template-columns: auto minmax(220px, 320px) 276px" in product_styles
    assert "grid-template-columns: auto minmax(180px, 280px) 276px" in product_styles
    assert "@media (max-width: 760px)" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles
    assert "flex-direction: column" in styles
    assert "white-space: nowrap" in styles


def test_content_coverage_blocks_media_admission_before_runtime_capability() -> None:
    result = run_node_probe(
        r'''
import { assetBibleProjection, deriveProductionCopilotState, localizedNegativeLock, assetOccurrenceLabel } from "./apps/studio/src/asset-bible-workspace.js";

const bible = {
  schema_version: "afs.asset_bible.v0.1",
  status: "locked",
  version: 8,
  current_revision_id: "asset-bible-r8",
  locked_revision_id: "asset-bible-r8",
  candidate_set: {
    script_revision_id: "script-r8",
    scene_count: 3,
    shot_count: 17,
    scene_index: [{ scene_id: "scene-1", name: "雨夜天台", number: 1 }],
    shot_index: [{ shot_id: "shot-1", scene_id: "scene-1", title: "悟空发现湿泥", number: 2 }],
  },
  assets: [
    { stable_id: "asset-character-wukong", asset_type: "character", display_name: "孙悟空", review_state: "approved", aliases: ["悟空"], occurrences: { scene_ids: ["scene-1"], shot_ids: ["shot-1"] } },
    { stable_id: "asset-character-bajie", asset_type: "character", display_name: "猪八戒", review_state: "rejected", aliases: ["八戒"], occurrences: { scene_ids: ["scene-1"], shot_ids: ["shot-1"] } },
  ],
  resolution_ledger: [{ requirement_id: "req-1", source_asset_id: "asset-character-bajie", assigned_asset_id: "asset-character-bajie", occurrence_kind: "shot", occurrence_id: "shot-1", status: "rejected", resolved: false }],
  coverage: { scene_total: 3, scene_covered: 3, shot_total: 17, shot_covered: 17, unresolved_required: 1, unresolved_shot_count: 1, coverage_pass: false },
};
const state = { assetBible: bible, nodes: {}, edges: {}, assets: [] };
const view = assetBibleProjection(state);
const copilot = deriveProductionCopilotState({ studioState: state, capabilityGates: { image: false }, section: "asset_bible" });
console.log(JSON.stringify({
  view,
  copilot,
  lock: localizedNegativeLock("do not change character identity"),
  occurrence: assetOccurrenceLabel(bible.candidate_set, "shot", "shot-1"),
}));
''',
    )
    assert result["view"]["counts"]["rejected"] == 1
    assert len(result["view"]["history_assets"]) == 1
    assert result["copilot"]["gate"]["admission"] == "blocked"
    assert result["copilot"]["next_valid_action"]["action"] == "resolve_required_occurrences"
    assert "必要出现范围" in result["copilot"]["blockers"][0]
    assert result["lock"] == "禁止改变角色身份"
    assert result["occurrence"] == "镜头 02 · 悟空发现湿泥"


def test_storyboard_context_prefers_current_shot_and_media_progress_is_unambiguous() -> None:
    shell = (ROOT / "apps/studio/src/product-shell.js").read_text(encoding="utf-8")
    lifecycle = (ROOT / "apps/studio/src/agent-chat-lifecycle.js").read_text(encoding="utf-8")

    assert 'const selectedId = section === "storyboard"' in shell
    assert "currentShot().nodeId || state.selection?.nodeIds?.[0]" in shell
    assert "currentShot().title" in shell
    assert 'const asset = section === "asset_bible" ? selectedAsset() : null' in shell
    assert 'context?.section === "storyboard_read_only"' in (ROOT / "apps/studio/src/agent-chat-panel.js").read_text(encoding="utf-8")
    assert "已生成媒体 ${generatedMediaCount()} / ${totalShots()}" in shell
    assert "projectDisplayName()" in shell
    assert "preferredProjectName(project?.name, meta.projectName)" in lifecycle


def test_agent_context_fingerprint_tracks_selected_object_and_revision() -> None:
    result = run_node_probe(
        r'''
import { agentChatContextSnapshot } from "./apps/studio/src/agent-chat-lifecycle.js";

const state = {
  meta: { projectId: "project-1", seq: 4 },
  nodes: { source: { id: "source", type: "story_text", title: "剧本" } },
  edges: {},
  production: {
    script_core_truth_projection: { current_revision_id: "script-r2" },
    production_graph_projection: { graph_version: 7, graph_digest: "graph-digest" },
  },
};
const project = { project_id: "project-1", name: "项目一" };
const shot1 = agentChatContextSnapshot({ project, studioState: state, section: "storyboard", currentShot: { nodeId: "shot-1", title: "镜头 1" } });
const shot2 = agentChatContextSnapshot({ project, studioState: state, section: "storyboard", currentShot: { nodeId: "shot-2", title: "镜头 2" } });
const asset = agentChatContextSnapshot({
  project,
  studioState: state,
  section: "asset_bible",
  selectedAsset: { stable_id: "asset-character-1", asset_type: "character", display_name: "林晚" },
  assetBible: { current_revision_id: "asset-bible-r3" },
});
console.log(JSON.stringify({ shot1, shot2, asset }));
''',
    )
    assert result["shot1"]["object_kind"] == "shot"
    assert result["shot1"]["object_id"] == "shot-1"
    assert result["shot1"]["context_fingerprint"] != result["shot2"]["context_fingerprint"]
    assert result["asset"]["object_kind"] == "asset"
    assert result["asset"]["object_id"] == "asset-character-1"
    assert result["asset"]["asset_bible_revision_id"] == "asset-bible-r3"
    assert result["asset"]["context_fingerprint"] != result["shot1"]["context_fingerprint"]


def test_legacy_sequence_duration_labels_shot_sum_and_plan_estimate() -> None:
    result = run_node_probe(
        r'''
import { shotSequenceDurationSummary } from "./apps/studio/src/canvas-node-body.js";

const sequence = {
  id: "sequence-1",
  groupId: "candidate-1",
  params: {
    nodeRole: "m6_6_shot_sequence_candidate",
    candidate_id: "candidate-1",
    scene_count: 3,
    shot_count: 3,
    estimated_duration_sec: 21,
  },
};
const state = {
  nodes: {
    sequence: sequence,
    shot1: { groupId: "candidate-1", params: { nodeRole: "m6_6_shot_candidate", duration_sec: 8 } },
    shot2: { groupId: "candidate-1", params: { nodeRole: "m6_6_shot_candidate", duration_sec: 9 } },
    shot3: { groupId: "candidate-1", params: { nodeRole: "m6_6_shot_candidate", duration_sec: 10 } },
  },
};
console.log(JSON.stringify(shotSequenceDurationSummary(sequence, state)));
''',
    )
    assert result["duration_source"] == "per_shot_sum"
    assert result["shot_duration_sec"] == 27
    assert result["planned_duration_sec"] == 21
    assert "镜头合计 27 秒" in result["text"]
    assert "计划估算 21 秒" in result["text"]
