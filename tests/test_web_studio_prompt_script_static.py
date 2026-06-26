import json
import subprocess

from studio_static_helpers import STUDIO_ROOT, _styles


def test_prompt_optimization_is_inline_and_selection_safe() -> None:
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "showPopover" not in optimizer
    assert "optimizer-pop" not in optimizer
    assert "promptOptimizationState" in optimizer
    assert 'status: "running"' in optimizer
    assert 'store.get().nodes[nodeId]' in optimizer
    assert "connectNamedAssetToTarget" in optimizer
    assert "buildAssetReferenceActions" in optimizer
    assert "prompt-shimmer" in prompt_bar
    assert "syncPromptBarState" in prompt_bar
    assert "promptTextShimmer" in styles


def test_text_node_has_script_import_expand_and_breakdown_controls() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    nodes = (STUDIO_ROOT / "src" / "nodes.js").read_text(encoding="utf-8")

    assert "importScriptFileIntoTextNode" in prompt_bar
    assert "expandTextIdeaToScript" in prompt_bar
    assert "splitTextNodeToStoryboardNodes" in prompt_bar
    assert "导入剧本" in prompt_bar
    assert "扩写剧本" in prompt_bar
    assert "拆分分镜" in prompt_bar
    assert "export function splitScriptIntoShots" in script_breakdown
    assert "formal_script_before_storyboard_breakdown" in script_breakdown
    assert "storyboard_placeholder_outline" in script_breakdown
    assert "looksLikeStoryboardPlaceholder" in script_breakdown
    assert 'createNode(store, "script"' in script_breakdown
    assert "connect(store, fresh.id, shotNode.id)" in script_breakdown
    assert "剧本拆分分镜" in nodes


def test_idea_expansion_fallback_outputs_formal_script_not_storyboard_template() -> None:
    script = r'''
import { expandTextIdeaToScript } from "./apps/studio/src/script-breakdown.js";

const state = {
  nodes: {
    text_1: {
      id: "text_1",
      type: "text",
      prompt: "一个来自未来的机器人，在农村屋顶上看星星",
      content: "",
      params: {},
      status: "empty",
    },
  },
  edges: {},
  order: ["text_1"],
  assets: [],
  groups: {},
  selection: { nodeIds: ["text_1"], edgeId: null },
  ui: {},
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
};
await expandTextIdeaToScript(store, null, state.nodes.text_1);
process.stdout.write(JSON.stringify(state.nodes.text_1));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    node = json.loads(completed.stdout)

    assert node["params"]["scriptInputMode"] == "idea_expanded_script"
    assert "片名：《" in node["prompt"]
    assert "故事从一个清晰的核心画面展开" in node["prompt"]
    assert "正式短视频剧本" not in node["prompt"]
    assert "分镜 01" not in node["prompt"]
    assert "推进主体" not in node["prompt"]
    assert "展示变化" not in node["prompt"]
    assert "收束结果" not in node["prompt"]


def test_text_script_body_receives_generated_content_and_keeps_editable_surface() -> None:
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    canvas_input = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    action_handler = (STUDIO_ROOT / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "node.content = prompt" in script_breakdown
    assert "visibleText" in script_breakdown
    assert "scriptExpansionState?.status === \"running\"" in canvas_view
    assert "node-content-editor" in canvas_body
    assert "text-content-view" in canvas_body
    assert "openNodePromptEditor" in canvas_input
    assert "promptBarNodeId" in prompt_bar
    assert "content-shimmer" in canvas_body
    assert ".text-content-view.content-shimmer" in styles
    assert "node-context-toolbar" not in canvas_view
    assert "node-context-toolbar" not in styles
    assert 'node.type === "text" && action === "upload"' in action_handler


def test_storyboard_breakdown_creates_reviewable_structured_shots_without_asset_prep_nodes() -> None:
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    structured_shot = (STUDIO_ROOT / "src" / "structured-shot.js").read_text(encoding="utf-8")
    asset_nodes = (STUDIO_ROOT / "src" / "shot-asset-nodes.js").read_text(encoding="utf-8")

    assert "structuredShotFromSegment" in script_breakdown
    assert "breakdownStoryboard" in script_breakdown
    assert "createShotAssetPrepNodes" not in script_breakdown
    assert "export function structuredShotFromSegment" in structured_shot
    for field in ["镜号：", "时长：", "画面描述：", "景别：", "光影氛围：", "运镜：", "资产："]:
        assert field in structured_shot
    assert "export function extractShotAssetRefs" in structured_shot
    assert "KNOWN_CHARACTER_NAMES" in structured_shot
    assert '"孙悟空"' in structured_shot
    assert '"金刚狼"' in structured_shot
    assert '"金箍棒"' in structured_shot
    assert '"山巅"' in structured_shot
    assert '"战场"' in structured_shot
    assert '"主要场景"' in structured_shot
    assert '"路灯"' in structured_shot
    assert '"信", "照片", "灯"' not in structured_shot
    assert "shotAssetRefs" in script_breakdown
    assert "assetPrepState" in script_breakdown
    assert "pending_user_review" in script_breakdown
    assert 'createNode(store, "image"' in asset_nodes
    assert "asset_prep" in asset_nodes
    assert "connect(store, scriptNodeId, assetNode.id)" in asset_nodes


def test_storyboard_asset_cards_are_editable_candidates_before_fixed_context() -> None:
    asset_drafts = (STUDIO_ROOT / "src" / "asset-card-drafts.js").read_text(encoding="utf-8")
    asset_nodes = (STUDIO_ROOT / "src" / "shot-asset-nodes.js").read_text(encoding="utf-8")
    asset_panel = (STUDIO_ROOT / "src" / "panels" / "asset-card-panel.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")

    assert "assetCardDraftFromRef" in asset_drafts
    assert "assetCardText" in asset_drafts
    assert "asset-card-image-prompts.js" in asset_nodes
    assert "included_in_context_before_confirmation: false" in asset_drafts
    assert "node.params.assetCardDraft" in asset_nodes
    assert 'node.params.nodeRole = "asset_card_draft"' in asset_nodes
    assert "node.params.visualAssets" not in asset_nodes
    assert "openAssetCardPanel" in asset_panel
    assert "保存并局部修订生成" in asset_panel
    assert "startNodeGeneration" in asset_panel
    assert "await store.flushRuntimeSave?.();" in asset_panel
    assert "编辑资产卡" in node_menu
    assert "openAssetCardPanel(store, nodeId, runtime)" in node_menu


def test_asset_card_drafts_clean_legacy_tag_pollution_and_backfill_reference_views() -> None:
    script = r'''
import {
  assetCardDraftFromRef,
  normalizeAssetCardDraft,
} from "./apps/studio/src/asset-card-drafts.js";
import { assetImagePrompt } from "./apps/studio/src/asset-card-image-prompts.js";
import { structuredShotFromSegment } from "./apps/studio/src/structured-shot.js";

const shot = {
  shot_id: "shot_01",
  description: "@主角 @主要场景。描绘一个来自未来的机器人在城市屋顶静静仰望星空的孤独、沉静、诗意的科幻瞬间。夜晚的高层城市屋顶，远处高楼灯火与天际线微弱闪烁，头顶星空清澈深远，冷蓝月光与星光主导。",
};
const structured = structuredShotFromSegment(shot.description, 1);
const character = assetCardDraftFromRef({ label: "主角", asset_type: "character" }, shot);
const scene = assetCardDraftFromRef({ label: "主要场景", asset_type: "scene" }, shot);
const legacyCharacter = normalizeAssetCardDraft({
  asset_type: "character",
  label: "主角",
  signature: "主角：@主角 @主要场景",
  feature_card: {
    identity: "来自未来的机器人主角",
    appearance: "金属机身，精密发光纹路",
    demeanor: "@主角 @主要场景",
  },
  evidence_text: shot.description,
});
const legacyScene = normalizeAssetCardDraft({
  asset_type: "scene",
  label: "主要场景",
  signature: "主要场景：@主角 @主要场景",
  feature_card: {
    location: "夜晚城市屋顶/楼顶平台",
    lighting_mood: "@主角 @主要场景",
  },
  evidence_text: shot.description,
});

process.stdout.write(JSON.stringify({
  structured,
  character,
  scene,
  legacyCharacter,
  legacyScene,
  legacyCharacterPrompt: assetImagePrompt(legacyCharacter),
  legacyScenePrompt: assetImagePrompt(legacyScene),
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
    labels = [item["label"] for item in payload["structured"]["asset_refs"]]

    generated_surface = json.dumps(
        {
            "legacyCharacterSignature": payload["legacyCharacter"]["signature"],
            "legacyCharacterFeatureCard": payload["legacyCharacter"]["feature_card"],
            "legacySceneSignature": payload["legacyScene"]["signature"],
            "legacySceneFeatureCard": payload["legacyScene"]["feature_card"],
            "legacyCharacterPrompt": payload["legacyCharacterPrompt"],
            "legacyScenePrompt": payload["legacyScenePrompt"],
        },
        ensure_ascii=False,
    )
    assert labels[:2] == ["未来机器人", "夜晚城市屋顶"]
    assert "@主角" not in payload["structured"]["description"]
    assert "@主要场景" not in payload["structured"]["description"]
    assert "@主角 @主要场景" not in generated_surface
    assert payload["character"]["feature_card"]["reference_views"]
    assert payload["scene"]["feature_card"]["view_set"]
    assert payload["legacyCharacter"]["feature_card"]["reference_views"]
    assert payload["legacyScene"]["feature_card"]["view_set"]
    assert "Character reference sheet" in payload["legacyCharacterPrompt"]
    assert "front half-body close-up" in payload["legacyCharacterPrompt"]
    assert "Environment reference" in payload["legacyScenePrompt"]
    for polluted in ("多视图角色设定表", "多视角场景设定图", "设定板", "软件界面"):
        assert polluted not in payload["legacyCharacterPrompt"] + payload["legacyScenePrompt"]
    assert "Forbidden: software dashboard, app interface, data chart" in payload["legacyCharacterPrompt"]


def test_prompt_bar_canvas_double_click_and_node_motion_are_stable() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    canvas_input = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    event_targets = (STUDIO_ROOT / "src" / "dom-event-targets.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "s.ui.promptBarNodeId = node.id;" in prompt_bar
    assert "isBlankCanvasDoubleClick" in canvas_input
    assert "closestFromEvent(e, \".node\")" in canvas_input
    assert "event?.composedPath?.()" in event_targets
    assert "document.elementFromPoint" in event_targets
    assert "#canvas-empty-hint" in canvas_input
    assert 'new Set(["canvas-root", "canvas-viewport", "world", "node-layer"])' in canvas_input
    assert "Math.abs(dx) + Math.abs(dy) <= 2 && !session.moved" in canvas_input
    assert "node-land" not in styles
    assert "scale: 1.012" not in styles
    assert ".node:hover { transform" not in styles


def test_script_nodes_identify_assets_and_create_keyframe_layer_without_candidate_pollution() -> None:
    nodes = (STUDIO_ROOT / "src" / "nodes.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    storyboard_actions = (STUDIO_ROOT / "src" / "storyboard-node-actions.js").read_text(encoding="utf-8")
    keyframes = (STUDIO_ROOT / "src" / "storyboard-keyframes.js").read_text(encoding="utf-8")
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    visible_assets = (STUDIO_ROOT / "src" / "node-visible-assets.js").read_text(encoding="utf-8")
    lifecycle = (STUDIO_ROOT / "src" / "asset-lifecycle.js").read_text(encoding="utf-8")

    assert "识别资产" in nodes
    assert "生成关键帧层" in nodes
    assert "identifyScriptAssets" in node_actions
    assert "createStoryboardKeyframeLayer" in node_actions
    assert "识别资产" in node_menu
    assert "生成关键帧层" in node_menu
    assert "createKeyframeNodesForStoryboard" in keyframes
    assert "ensureShotAssetPrepNodesForScriptNode(store, fresh)" not in storyboard_actions
    assert "existingShotAssetCardNodeIds" not in storyboard_actions
    assert "fixed_visual_asset_ids" in keyframes
    assert "missing_asset_card_node_ids" in keyframes
    assert "candidate_asset_card_node_ids" in keyframes
    assert "ready_without_fixed_assets" in keyframes
    assert "asset.params?.visualAssets" in keyframes
    assert "needs_fixed_assets" not in node_actions
    assert "shouldCollectConnectedUploads" in optimizer_contract
    assert '["keyframe_generation", "asset_card_draft"].includes(node?.params?.nodeRole)' in optimizer_contract
    assert "asset_card_draft" in optimizer_contract
    assert "character_asset_candidate" in visible_assets
    assert "prop_asset_candidate" in visible_assets
    assert 'kind.endsWith("_candidate")' in lifecycle
    assert 'kind === "prop_asset"' in lifecycle
    assert "connect(store, scriptNode.id, keyframeNode.id)" in keyframes


def test_keyframe_generation_carries_connected_asset_card_images_as_local_refs() -> None:
    script = r'''
import { buildKeyframeGenerationRequest } from "./apps/studio/src/optimizer-contract.js";

const keyframe = {
  id: "keyframe_01",
  type: "image",
  title: "关键帧 · 分镜01",
  prompt: "根据分镜生成关键帧：@孙悟空 @金刚狼 @金箍棒",
  params: {
    nodeRole: "keyframe_generation",
    visualAssets: [{
      asset_id: "vas_swk",
      label: "孙悟空",
      status: "fixed",
      image_asset_refs: ["img_swk_fixed"],
    }],
    spec: { ratio: "16:9", count: 1 },
  },
};
const wolverine = {
  id: "asset_wolverine",
  type: "image",
  title: "角色资产 · @金刚狼",
  params: {
    nodeRole: "asset_card_draft",
    assetCardDraft: { label: "金刚狼", asset_type: "character", status: "draft" },
    uploads: [
      { asset_id: "img_wolverine_candidate", role: "character_reference" },
      { asset_id: "img_old_keyframe_history", role: "generated_keyframe_reference" },
    ],
  },
};
const scene = {
  id: "asset_scene",
  type: "image",
  title: "场景资产 · @雨夜码头",
  params: {
    nodeRole: "asset_card_draft",
    assetCardDraft: { label: "雨夜码头", asset_type: "scene", status: "draft" },
    uploads: [{ asset_id: "img_scene_candidate", role: "scene_reference" }],
  },
};
const unrelated = {
  id: "unrelated_image",
  type: "image",
  params: { uploads: [{ asset_id: "img_unrelated_history", role: "generated_keyframe_reference" }] },
};
const state = {
  nodes: { keyframe_01: keyframe, asset_wolverine: wolverine, asset_scene: scene, unrelated_image: unrelated },
  edges: {
    e1: { id: "e1", from: "asset_wolverine", to: "keyframe_01" },
    e2: { id: "e2", from: "asset_scene", to: "keyframe_01" },
    e3: { id: "e3", from: "unrelated_image", to: "keyframe_01" },
  },
};
const request = buildKeyframeGenerationRequest(state, keyframe);
process.stdout.write(JSON.stringify({
  refs: request.asset_refs,
  contextRefs: request.context_subgraph.nodes.find((node) => node.id === "keyframe_01").image_asset_refs,
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

    assert payload["refs"] == ["img_swk_fixed", "img_wolverine_candidate", "img_scene_candidate"]
    assert "img_old_keyframe_history" not in payload["refs"]
    assert "img_unrelated_history" not in payload["refs"]
    assert payload["contextRefs"] == ["img_swk_fixed"]


def test_storyboard_asset_identification_uses_runtime_plan_and_allows_manual_asset_nodes() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    storyboard_actions = (STUDIO_ROOT / "src" / "storyboard-node-actions.js").read_text(encoding="utf-8")
    asset_nodes = (STUDIO_ROOT / "src" / "shot-asset-nodes.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    add_asset_modal = (STUDIO_ROOT / "src" / "panels" / "add-asset-modal.js").read_text(encoding="utf-8")

    assert "planShotAssets(payload)" in runtime_client
    assert "shot-asset-plans" in runtime_client
    assert "identifyScriptAssets(store, runtime, node)" in storyboard_actions
    assert "runtime?.planShotAssets" in storyboard_actions
    assert "createManualShotAssetNode" in asset_nodes
    assert "openAddAssetModal" in node_menu
    assert "新增资产" in node_menu
    assert "添加角色资产" not in node_menu
    assert "添加场景资产" not in node_menu
    assert "添加道具资产" not in node_menu
    assert "inferManualAssetType" in add_asset_modal
    assert "createManualShotAssetNode(store, fresh, assetType, label)" in add_asset_modal
    assert "金刚狼" in add_asset_modal


def test_asset_mentions_scope_fixed_project_assets_and_tree_candidates() -> None:
    candidates = (STUDIO_ROOT / "src" / "asset-reference-candidates.js").read_text(encoding="utf-8")
    mentions = (STUDIO_ROOT / "src" / "mention-suggestions.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")

    assert "assetReferenceCandidates" in candidates
    assert "fixedProjectAssets" in candidates
    assert "treeCandidateAssets" in candidates
    assert "connectedNodeIds" in candidates
    assert '"project_fixed"' in candidates
    assert '"shot_tree_candidate"' in candidates
    assert "isRetired(asset)" in candidates
    assert "bindAssetMentionSuggestions" in mentions
    assert "assetReferenceCandidates(store.get(), nodeId, match.query)" in mentions
    assert "MENTION_QUERY_RE" in mentions
    assert "bindAssetMentionSuggestions(textarea, store, node.id)" in prompt_bar
    assert "bindAssetMentionSuggestions(textarea, store, node.id)" in canvas_body
    assert "取消固定资产" in node_menu
    assert "openRetireAssetModal" in node_menu


def test_asset_mentions_exclude_generated_history_from_unconnected_nodes() -> None:
    script = r'''
import { assetReferenceCandidates } from "./apps/studio/src/asset-reference-candidates.js";

const state = {
  nodes: {
    isolated: { id: "isolated", type: "image", params: {} },
    shot_01: { id: "shot_01", type: "script", params: {} },
    wolverine_asset: {
      id: "wolverine_asset",
      type: "image",
      title: "角色资产 · @金刚狼",
      params: { assetCardDraft: { card_id: "card_wolverine", label: "金刚狼", asset_type: "character", status: "draft" } },
    },
    staff_asset: {
      id: "staff_asset",
      type: "image",
      title: "道具资产 · @金箍棒",
      params: { assetCardDraft: { card_id: "card_staff", label: "金箍棒", asset_type: "prop", status: "draft" } },
    },
  },
  edges: {
    e1: { from: "shot_01", to: "wolverine_asset" },
  },
  assets: [
    { kind: "visual_asset", asset_id: "visual_swk", visual_asset_id: "visual_swk", label: "孙悟空", asset_type: "character", status: "fixed" },
    { kind: "image_reference", asset_id: "img_old", title: "candidate_001.png", role: "generated_keyframe_reference", status: "ready", source_node_id: "shot_01" },
  ],
};

process.stdout.write(JSON.stringify({
  isolated: assetReferenceCandidates(state, "isolated").map((item) => item.label),
  connected: assetReferenceCandidates(state, "shot_01").map((item) => item.label),
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

    assert payload["isolated"] == ["孙悟空"]
    assert payload["connected"] == ["孙悟空", "金刚狼"]
    assert "candidate_001.png" not in payload["isolated"] + payload["connected"]
    assert "金箍棒" not in payload["connected"]


def test_visual_asset_cards_support_prop_assets_across_frontend_and_runtime_contract() -> None:
    visual_render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    visual_defaults = (STUDIO_ROOT / "src" / "panels" / "visual-asset-defaults.js").read_text(encoding="utf-8")
    asset_summary = (STUDIO_ROOT / "src" / "asset-reference-summary.js").read_text(encoding="utf-8")
    runtime_models = (STUDIO_ROOT.parent / "api" / "runtime_models.py").read_text(encoding="utf-8")
    algorithm = (STUDIO_ROOT.parent.parent / "agentflow" / "algorithms" / "asset_card_drafting" / "__init__.py").read_text(encoding="utf-8")

    assert "PROP_FIELDS" in visual_render
    assert "道具资产" in visual_render
    assert "propDefaults" in visual_defaults
    assert 'if (type === "prop") return "道具";' in asset_summary
    assert 'Literal["character", "scene", "prop", "video"]' in runtime_models
    assert 'Literal["character", "scene", "prop"]' in runtime_models
    assert '"prop"' in algorithm


def test_visual_asset_draft_and_existing_asset_edit_show_inline_loading() -> None:
    visual_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    visual_render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    asset_detail = (STUDIO_ROOT / "src" / "panels" / "asset-detail-popover.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "existingAsset" in visual_panel
    assert "supersedes_asset_id" in visual_panel
    assert "image_asset_refs" in visual_panel
    assert "seedFromExistingAsset" in visual_panel
    assert "is-drafting" in visual_panel
    assert "visualAssetFieldShimmer" in styles
    assert "data-drafting" in visual_render
    assert "lastFixedVisualAsset" in node_actions
    assert "imageAssetFromVisualAsset" in node_actions
    assert "调整资产" in asset_detail
    assert "openVisualAssetPanel" in asset_detail
    assert "existingAsset" in asset_detail
    assert "cancelFixedAsset" in asset_detail
    assert "retireVisualAsset" in asset_detail
    assert "applyRetiredVisualAssetToStore" in asset_detail
