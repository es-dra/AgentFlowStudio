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


def test_identity_switch_logout_and_expiry_invalidate_visible_and_pending_review_state() -> None:
    payload = _node_json(
        r'''
import { createReviewDeliveryState } from "./apps/studio/src/review-delivery-state.js";
const events = [];
const store = createReviewDeliveryState((state) => events.push({
  phase: state.phase,
  identity: state.identity,
  projectId: state.projectId,
  candidateCount: state.candidates.length,
  busy: state.busy,
}));
store.setIdentity({ user_id: "owner-alpha", display_name: "Alpha" });
store.publish({
  phase: "ready",
  projectId: "alpha-project",
  candidates: [{ candidate_id: "candidate-alpha", preview_url: "/alpha.png" }],
  busy: "",
});
const pending = store.beginAction("select");
store.setIdentity({ user_id: "owner-beta", display_name: "Beta" });
const afterSwitch = store.get();
const oldResultAccepted = store.finishAction(pending, { notice: "stale alpha result" });
store.publish({ phase: "ready", projectId: "beta-project", candidates: [{ candidate_id: "candidate-beta" }] });
store.clearIdentity();
const afterLogout = store.get();
process.stdout.write(JSON.stringify({
  afterSwitch: {
    identity: afterSwitch.identity,
    phase: afterSwitch.phase,
    projectId: afterSwitch.projectId,
    candidateCount: afterSwitch.candidates.length,
    busy: afterSwitch.busy,
  },
  oldResultAccepted,
  afterLogout: {
    identity: afterLogout.identity,
    phase: afterLogout.phase,
    projectId: afterLogout.projectId,
    candidateCount: afterLogout.candidates.length,
    run: afterLogout.run,
  },
  eventCount: events.length,
}));
'''
    )

    assert payload["afterSwitch"] == {
        "identity": "owner-beta",
        "phase": "secure",
        "projectId": "",
        "candidateCount": 0,
        "busy": "",
    }
    assert payload["oldResultAccepted"] is False
    assert payload["afterLogout"] == {
        "identity": "",
        "phase": "secure",
        "projectId": "",
        "candidateCount": 0,
        "run": None,
    }
    assert payload["eventCount"] >= 6


def test_review_delivery_declares_recovery_mobile_and_no_overlap_browser_contracts() -> None:
    main = (STUDIO / "src" / "review-delivery-main.js").read_text(encoding="utf-8")
    view = (STUDIO / "src" / "review-delivery-workspace.js").read_text(encoding="utf-8")
    state = (STUDIO / "src" / "review-delivery-state.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "review-delivery.css").read_text(encoding="utf-8")

    for marker in ('phase: "loading"', 'phase: "empty"', 'phase: "read_error"'):
        assert marker in main or marker in state
    for marker in ("writeError", "stale", 'action === "retry"', 'action === "refresh"', 'action === "reload"'):
        assert marker in main
    assert "if (state.busy || state.stale) return;" in main
    assert "if (value.busy) return null;" in state
    assert 'headers: { Authorization: `Bearer ${sessionToken}` }' in main
    assert "URL.createObjectURL(blob)" in main
    assert "URL.revokeObjectURL(url)" in main
    assert main.index("revokePreviewMedia();") < main.index("reviewState.beginLoad(requestedId)")
    assert "preview temporarily" not in view.lower()
    assert "预览暂不可用" in view
    assert "不可用不会被显示为通过" in view
    assert "position: fixed" not in styles
    assert "max-height: calc(100dvh - 108px)" in styles
    assert "@media (max-width: 600px)" in styles
    mobile = styles[styles.index("@media (max-width: 600px)") :]
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert "overflow-x: clip" in styles
    assert "min-height: 310px" in mobile


def test_stale_delivery_snapshot_posts_neither_quality_review_nor_export() -> None:
    payload = _node_json(
        r'''
import {
  dedicatedDeliveryActionSnapshot,
  submitDedicatedProductionExport,
  submitDedicatedQualityApproval,
} from "./apps/studio/src/production-delivery-controller.js";
const digest = (char) => char.repeat(64);
const candidate = { candidate_id: "candidate-001", canonical_digest: digest("a"), parent_job_id: "job-001" };
const other = { candidate_id: "candidate-002", canonical_digest: digest("b"), parent_job_id: "job-001" };
const revision = {
  revision_id: "revision-001", candidate_id: "candidate-001", candidate_digest: digest("a"),
  canonical_digest: digest("c"), subject_digest: digest("d"), parent_job_id: "job-001",
};
const base = {
  run_id: "run-001", subject_digest: digest("e"), status: "creator_selected",
  candidates: [candidate, other], selected_revision: revision,
  creator_decisions: [{ decision: "select" }], quality_reviews: [], exports: [],
  checkpoint: { version: 2, state_digest: digest("f") },
};
const node = { id: "review-delivery", params: {
  lastKeyframeJobId: "job-001",
  creatorSelection: {
    run_id: "run-001", selected_candidate_id: "candidate-001", selected_candidate_digest: digest("a"),
    selected_revision_id: "revision-001", selected_revision_digest: digest("c"), selected_parent_job_id: "job-001",
  },
  reviewDeliveryCandidates: [candidate, other],
  candidatePreviewUrls: [candidate, other].map((item) => ({
    ...item, project_id: "project-001", status: "succeeded",
    preview_url: `/projects/project-001/keyframe-generations/job-001/candidates/${item.candidate_id}/preview`,
  })),
} };
const snapshot = dedicatedDeliveryActionSnapshot(base, node);
const changed = { ...base, checkpoint: { version: 3, state_digest: digest("9") } };
let qualityPosts = 0;
let exportPosts = 0;
let reads = 0;
const runtime = {
  getProductionRun: async () => { reads += 1; return { production_run: changed }; },
  recordProductionQualityReview: async () => { qualityPosts += 1; return {}; },
  exportProductionRun: async () => { exportPosts += 1; return {}; },
};
const checklist = {
  story_intent_preserved: true,
  character_continuity_checked: true,
  shot_coverage_checked: true,
  revision_addressed: true,
};
const quality = await submitDedicatedQualityApproval(runtime, snapshot, node, checklist);
const exported = await submitDedicatedProductionExport(runtime, snapshot, node);
process.stdout.write(JSON.stringify({ quality, exported, qualityPosts, exportPosts, reads }));
'''
    )

    assert payload["quality"]["stale"] is True
    assert payload["exported"]["stale"] is True
    assert payload["qualityPosts"] == 0
    assert payload["exportPosts"] == 0
    assert payload["reads"] == 4
