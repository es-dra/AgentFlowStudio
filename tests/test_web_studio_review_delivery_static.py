from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO = Path("apps/studio")


def _node_json(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_review_delivery_is_a_dedicated_authenticated_chinese_creator_surface() -> None:
    html = (STUDIO / "review.html").read_text(encoding="utf-8")
    main = (STUDIO / "src" / "review-delivery-main.js").read_text(encoding="utf-8")
    view = (STUDIO / "src" / "review-delivery-workspace.js").read_text(encoding="utf-8")
    labels_source = view + "\n" + (STUDIO / "src" / "production-delivery-view.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "review-delivery.css").read_text(encoding="utf-8")

    assert '<html lang="zh-CN">' in html
    assert 'id="secure-entry"' in html
    assert 'id="overlay-root"' in html
    for forbidden in ('id="review-delivery-root"', 'id="canvas-root"', 'id="node-layer"'):
        assert forbidden not in html
    assert main.index("await ensureAuthSession(authRuntime)") < main.index("mountReviewSurface();")
    assert "reviewState.clearIdentity();" in main
    assert "mountedRoot?.replaceChildren();" in main
    assert "clearIdentityScopedStudioState();" in main
    assert 'window.addEventListener("afs:auth-session-expired"' in main

    for label in (
        "审核与交付",
        "主创审核工作台",
        "候选对比",
        "当前版本",
        "本轮意见",
        "画面一致性",
        "叙事意图",
        "音频检查",
        "字幕检查",
        "批准当前修订",
        "退回候选",
        "要求返修",
        "交付状态",
        "查看版本沿革",
    ):
        assert label in labels_source
    for forbidden in ("runtime", "provider", "health", "json", "sha-256"):
        assert forbidden not in view.lower()
    assert 'role", "radiogroup"' in view
    assert 'role", "radio"' in view
    assert "aria-live" in view
    assert ":focus-visible" in styles
    assert "@media (max-width: 600px)" in styles
    assert "overflow-x: clip" in styles
    assert "grid-template-columns: minmax(0, 1fr)" in styles
    assert "position: fixed" not in styles


def test_review_delivery_projection_binds_exact_server_truth_and_keeps_unavailable_checks_honest() -> None:
    payload = _node_json(
        r'''
import { composeReviewDeliveryState } from "./apps/studio/src/review-delivery-state.js";
const digest = (char) => char.repeat(64);
const projectId = "project-001";
const candidates = [
  { candidate_id: "candidate-001", canonical_digest: digest("a"), parent_job_id: "job-001" },
  { candidate_id: "candidate-002", canonical_digest: digest("b"), parent_job_id: "job-001" },
];
const revision = {
  revision_id: "revision-001",
  candidate_id: "candidate-001",
  candidate_digest: digest("a"),
  canonical_digest: digest("c"),
  subject_digest: digest("d"),
  parent_job_id: "job-001",
  creator_decision_id: "decision-001",
  revision_intent: "保留构图，强化人物表情。",
};
const run = {
  run_id: "run-001",
  subject_digest: digest("e"),
  status: "creator_selected",
  candidates,
  selected_revision: revision,
  creator_decisions: [{ decision_id: "decision-001", decision: "select", candidate_id: "candidate-001" }],
  quality_reviews: [],
  exports: [],
  lineage: [],
  checkpoint: { version: 2, state_digest: digest("f") },
};
const studioPayload = { state: { production: { active_run_id: "run-001" }, nodes: {
  image_1: { id: "image_1", type: "image", params: { candidatePreviewUrls: candidates.map((item) => ({
    ...item,
    project_id: projectId,
    preview_url: `/projects/${projectId}/keyframe-generations/${item.parent_job_id}/candidates/${item.candidate_id}/preview`,
    status: "succeeded",
  })) } },
} } };
const state = composeReviewDeliveryState({
  workspace: { projects: [{ project_id: projectId, name: "雨夜灯火" }] },
  project: { project_id: projectId, name: "雨夜灯火", episode: "第 01 集" },
  runsPayload: { production_runs: [run] },
  studioPayload,
  projectId,
});
process.stdout.write(JSON.stringify({
  phase: state.phase,
  candidateCount: state.candidates.length,
  selectedCandidateId: state.selectedCandidateId,
  focusedCandidateId: state.focusedCandidateId,
  reviewCheckpoint: state.reviewSnapshot.checkpoint_version,
  deliveryCheckpoint: state.deliverySnapshot.checkpoint_version,
  narrative: state.quality.narrative,
  consistency: state.quality.consistency,
  audio: state.quality.audio,
  subtitle: state.quality.subtitle,
  exportCount: state.exports.length,
  previewAvailable: state.candidates.every((item) => item.available),
}));
'''
    )

    assert payload == {
        "phase": "ready",
        "candidateCount": 2,
        "selectedCandidateId": "candidate-001",
        "focusedCandidateId": "candidate-001",
        "reviewCheckpoint": 2,
        "deliveryCheckpoint": 2,
        "narrative": "not_checked",
        "consistency": "not_checked",
        "audio": "unavailable",
        "subtitle": "unavailable",
        "exportCount": 0,
        "previewAvailable": True,
    }


def test_dedicated_review_stale_snapshot_fails_closed_and_requires_authoritative_readback() -> None:
    payload = _node_json(
        r'''
import {
  dedicatedReviewActionSnapshot,
  submitDedicatedReviewDecision,
} from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const base = {
  run_id: "run-001",
  subject_digest: digest("a"),
  status: "candidates_ready",
  candidates: [{ candidate_id: "candidate-001", canonical_digest: digest("b"), parent_job_id: "job-001" }],
  selected_revision: null,
  creator_decisions: [],
  checkpoint: { version: 1, state_digest: digest("c") },
};
const snapshot = dedicatedReviewActionSnapshot(base, "candidate-001", "review-delivery");
const changed = { ...base, checkpoint: { version: 2, state_digest: digest("d") } };
let reads = 0;
let posts = 0;
const result = await submitDedicatedReviewDecision({
  getProductionRun: async () => { reads += 1; return { production_run: changed }; },
  submitCreatorDecision: async () => { posts += 1; return {}; },
}, snapshot, "select", "选择当前方案。", { decisionId: "decision-001", idempotencyKey: "decision-key-001" });
process.stdout.write(JSON.stringify({ result, reads, posts }));
'''
    )

    assert payload["result"]["ok"] is False
    assert payload["result"]["stale"] is True
    assert payload["result"]["code"] == "stale_review_snapshot"
    assert payload["reads"] == 2
    assert payload["posts"] == 0
