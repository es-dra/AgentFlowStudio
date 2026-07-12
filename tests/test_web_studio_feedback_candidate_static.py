from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_studio_runtime_client_exposes_feedback_candidate_promotion_contract() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "recordFeedbackCandidatePromotion(payload)" in runtime_client
    assert "/feedback-candidate-promotions" in runtime_client
    assert "record_feedback_candidate_promotion" in runtime_client
    assert "recordFeedbackCandidateContextOverlay(payload)" in runtime_client
    assert "/feedback-candidate-context-overlays" in runtime_client
    assert "record_feedback_candidate_context_overlay" in runtime_client


def test_studio_quality_feedback_can_request_reviewed_context_overlay() -> None:
    quality_feedback = (STUDIO_ROOT / "src" / "quality-feedback.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    runtime_flow = (STUDIO_ROOT / "src" / "quality-feedback-runtime-flow.js").read_text(encoding="utf-8")
    candidate_flow = (STUDIO_ROOT / "src" / "feedback-candidate-flow.js").read_text(encoding="utf-8")

    assert "data-feedback-next-context" in quality_feedback
    assert "context_overlay" in quality_feedback
    assert "include_next_context" in quality_feedback
    assert "feedbackResultText" in quality_feedback
    assert "handleQualityFeedbackRuntime" in main
    assert "async function handleQualityFeedback" not in main
    assert "recordFeedbackCandidatePromotion" in runtime_flow + candidate_flow
    assert "recordFeedbackCandidateContextOverlay" in runtime_flow + candidate_flow
    assert "qualityFeedbackCandidates" in runtime_flow
    assert "provider_calls_started: false" in candidate_flow
    assert "writes_long_term_memory: false" in candidate_flow
    assert "writes_company_kb: false" in candidate_flow
    assert "fetch(" not in candidate_flow + runtime_flow
    assert "AFS_ALLOW_REMOTE" not in candidate_flow + runtime_flow


def test_studio_feedback_candidate_flow_is_explicit_and_safe() -> None:
    script = r'''
import {
  feedbackCandidateFlowSummary,
  promoteFeedbackCandidateToContextOverlay,
} from "./apps/studio/src/feedback-candidate-flow.js";

const feedbackResponse = {
  artifact: { artifact_id: "artifact_feedback_001" },
  feedback_event: {
    feedback_id: "runtime-feedback:project:001",
    feedback_candidate: {
      candidate_id: "runtime-feedback-candidate:001",
      candidate_scope: "quality_feedback_candidate",
    },
  },
};
const calls = [];
const runtime = {
  async recordFeedbackCandidatePromotion(payload) {
    calls.push({ kind: "promotion", payload });
    return {
      artifact: { artifact_id: "artifact_promotion_001" },
      feedback_candidate_promotion_decision: { decision_id: "promotion_decision_001" },
    };
  },
  async recordFeedbackCandidateContextOverlay(payload) {
    calls.push({ kind: "overlay", payload });
    return {
      artifact: { artifact_id: "artifact_overlay_001" },
      feedback_candidate_context_overlay: { overlay_id: "runtime-feedback-overlay:001" },
    };
  },
};

const skipped = await promoteFeedbackCandidateToContextOverlay(runtime, feedbackResponse, { requested: false });
const promoted = await promoteFeedbackCandidateToContextOverlay(runtime, feedbackResponse, {
  requested: true,
  rationale: "Use https://example.test/token and D:\\private\\asset.png",
  overlay_intent: "Use Bearer secret and D:\\private\\context.png",
});
const summary = feedbackCandidateFlowSummary(feedbackResponse, promoted);
process.stdout.write(JSON.stringify({ skipped, calls, summary }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["skipped"] == {"requested": False, "status": "not_requested"}
    assert [call["kind"] for call in payload["calls"]] == ["promotion", "overlay"]
    assert payload["calls"][0]["payload"]["decision"] == "promote_to_context_overlay"
    assert payload["calls"][0]["payload"]["feedback_artifact_id"] == "artifact_feedback_001"
    assert payload["calls"][0]["payload"]["candidate_id"] == "runtime-feedback-candidate:001"
    assert payload["calls"][1]["payload"]["promotion_decision_artifact_id"] == "artifact_promotion_001"
    assert payload["summary"]["context_overlay_requested"] is True
    assert payload["summary"]["context_overlay_id"] == "runtime-feedback-overlay:001"
    assert payload["summary"]["provider_calls_started"] is False
    assert payload["summary"]["writes_long_term_memory"] is False
    assert payload["summary"]["writes_company_kb"] is False
    assert "https://example.test" not in serialized
    assert "bearer secret" not in serialized
    assert "d:\\private" not in serialized


def test_studio_feedback_overlay_review_surface_reads_context_bundle_only() -> None:
    overlay_helper = STUDIO_ROOT / "src" / "feedback-context-overlays.js"
    inspector_summary = (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")

    assert overlay_helper.is_file()
    overlay_source = overlay_helper.read_text(encoding="utf-8")
    assert "feedback_context_overlays" in overlay_source
    assert "feedbackContextOverlaysFromBundle" in overlay_source
    assert "provider_calls_started" in overlay_source
    assert "writes_long_term_memory" in overlay_source
    assert "writes_company_kb" in overlay_source
    assert "fetch(" not in overlay_source
    assert "recordFeedbackCandidateContextOverlay" not in overlay_source
    assert "AFS_ALLOW_REMOTE" not in overlay_source

    assert "feedbackContextOverlaysFromBundle" in inspector_summary
    assert "反馈上下文" in inspector_summary
    assert "feedbackOverlaySummaryText" in inspector_summary
    assert "反馈" in algorithm_panel


def test_studio_feedback_overlay_prompt_policy_review_surface_is_local() -> None:
    overlay_helper = STUDIO_ROOT / "src" / "feedback-context-overlays.js"
    inspector_summary = (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")

    overlay_source = overlay_helper.read_text(encoding="utf-8")
    assert "feedbackOverlayPromptPolicyFromBundle" in overlay_source
    assert "feedbackOverlayPromptPolicySummaryText" in overlay_source
    assert "feedback_context_overlay_prompt_policy" in overlay_source
    assert "provider_prompt_includes_context_overlays" in overlay_source
    assert "prompt_provider_gate" in overlay_source
    assert "provider_prompt_inclusion_allowed" in overlay_source
    assert "fetch(" not in overlay_source
    assert "recordFeedbackCandidateContextOverlay" not in overlay_source
    assert "AFS_ALLOW_REMOTE" not in overlay_source

    assert "feedbackOverlayPromptPolicyFromBundle" in inspector_summary
    assert "反馈提示词策略" in inspector_summary
    assert "feedbackOverlayPromptPolicyFromBundle" in algorithm_panel
    assert "反馈策略" in algorithm_panel


def test_feedback_overlay_prompt_policy_summary_is_bounded() -> None:
    script = r'''
import {
  feedbackOverlayPromptPolicyFromBundle,
  feedbackOverlayPromptPolicySummaryText,
} from "./apps/studio/src/feedback-context-overlays.js";

const bundle = {
  feedback_context_overlay_prompt_policy: {
    policy_id: "feedback_overlay_context_evidence_only_v0",
    default_action: "context_evidence_only",
    provider_prompt_includes_context_overlays: false,
    overlay_text_channel: "disabled_by_default",
    requires_explicit_prompt_policy_gate: true,
    prompt_provider_gate: {
      gate_id: "feedback_overlay_provider_prompt_gate_v0",
      status: "blocked_by_default",
      provider_prompt_inclusion_allowed: false,
      requires_human_approval: true,
      requires_provider_gate: true,
      requires_prompt_budget_review: true,
      requires_safety_filter: true,
      gate_record_ref: "not_approved",
      provider_raw: { unsafe: true },
      local_path: "D:\\private\\gate.txt",
    },
    context_overlay_count: 1,
    selected_overlay_ids: ["runtime-feedback-overlay:abc123"],
    provider_raw: { unsafe: true },
    local_path: "D:\\private\\feedback.png",
  },
};
const policy = feedbackOverlayPromptPolicyFromBundle(bundle);
process.stdout.write(JSON.stringify({ policy, text: feedbackOverlayPromptPolicySummaryText(policy) }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)
    serialized = json.dumps(result, ensure_ascii=False).lower()

    assert result["policy"]["policy_id"] == "feedback_overlay_context_evidence_only_v0"
    assert result["policy"]["provider_prompt_includes_context_overlays"] is False
    assert result["policy"]["prompt_provider_gate"]["provider_prompt_inclusion_allowed"] is False
    assert result["policy"]["prompt_provider_gate"]["requires_human_approval"] is True
    assert result["text"] == "本地上下文，不注入生成提示词"
    assert "provider_raw" not in serialized
    assert "local_path" not in serialized
    assert "d:\\private" not in serialized


def test_studio_feedback_overlay_selection_ui_is_local_and_provider_closed() -> None:
    review_ui = STUDIO_ROOT / "src" / "feedback-overlay-review.js"
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")

    assert review_ui.is_file()
    review_source = review_ui.read_text(encoding="utf-8")
    assert "feedbackOverlayReviewTargets" in review_source
    assert "openFeedbackOverlayReviewMenu" in review_source
    assert "include_for_next_context" in review_source
    assert "reject_for_next_context" in review_source
    assert "provider_calls_started: false" in review_source
    assert "writes_long_term_memory: false" in review_source
    assert "writes_company_kb: false" in review_source
    assert "fetch(" not in review_source
    assert "recordFeedbackCandidateContextOverlay" not in review_source
    assert "AFS_ALLOW_REMOTE" not in review_source

    assert "feedbackOverlayReviewTargets" in node_menu
    assert "openFeedbackOverlayReviewMenu" in node_menu
    assert "选择反馈上下文" in node_menu


def test_keyframe_generation_request_carries_feedback_overlay_decisions() -> None:
    script = r'''
import { buildKeyframeGenerationRequest } from "./apps/studio/src/optimizer-contract.js";
const node = {
  id: "keyframe_01",
  type: "image",
  title: "关键帧 01",
  prompt: "生成下一帧",
  params: {
    model: "image2-keyframe",
    nodeRole: "keyframe_generation",
    lastOptimizedPromptPlain: "生成下一帧",
    feedbackOverlayDecisions: [
      {
        overlay_id: "runtime-feedback-overlay:abc123",
        candidate_id: "runtime-feedback-candidate:feedback001",
        decision: "reject_for_next_context",
        reviewed_at: "2026-06-30T20:01:00+08:00",
        provider_calls_started: false,
        writes_long_term_memory: false,
        writes_company_kb: false,
      },
    ],
  },
};
const state = { nodes: { keyframe_01: node }, edges: {} };
const request = buildKeyframeGenerationRequest(state, node);
const params = request.context_subgraph.nodes.find((item) => item.id === "keyframe_01").node_parameters;
process.stdout.write(JSON.stringify(params.feedback_context_overlay_decisions));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    decisions = json.loads(completed.stdout)

    assert decisions == [
        {
            "overlay_id": "runtime-feedback-overlay:abc123",
            "candidate_id": "runtime-feedback-candidate:feedback001",
            "decision": "reject_for_next_context",
            "reviewed_at": "2026-06-30T20:01:00+08:00",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
    ]
