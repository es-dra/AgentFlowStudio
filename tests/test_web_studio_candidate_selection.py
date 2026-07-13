from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


STUDIO = Path("apps/studio")


def _node_json(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_multi_candidate_generation_does_not_implicitly_choose_first_preview() -> None:
    payload = _node_json(
        r'''
import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
const digest = (char) => char.repeat(64);
const reusable = (candidateId, char, assetId) => ({
  asset_id: assetId, role: "generated_keyframe_reference", source_kind: "keyframe_candidate",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char), status: "succeeded",
});

const node = {
  id: "node-001",
  type: "image",
  status: "generating",
  previewUrl: "/projects/project-001/keyframe-generations/old-job/candidates/old/preview",
  prompt: "frame",
  params: { uploads: [], lastKeyframeJobId: "job-001" },
};
const state = { nodes: { "node-001": node }, assets: [] };
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  nextId: () => "asset-001",
};
const response = {
  job: { job_id: "job-001", project_id: "project-001", status: "succeeded" },
  candidate_previews: [
    { candidate_id: "candidate_001", sha256: digest("b"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview" },
    { candidate_id: "candidate_002", sha256: digest("c"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview" },
  ],
  reusable_image_assets: [
    reusable("candidate_001", "b", "asset-001"),
    reusable("candidate_002", "c", "asset-002"),
  ],
  safe_manifest: { output_count: 2 },
};
applyKeyframeResponse(store, node.id, response, { aspect_ratio: "9:16" });
process.stdout.write(JSON.stringify({
  previewUrl: state.nodes[node.id].previewUrl || null,
  candidates: state.nodes[node.id].params.candidatePreviewUrls,
  uploads: state.nodes[node.id].params.uploads,
  visibleAssets: state.assets,
  rawCandidates: response.candidate_previews,
}));
'''
    )

    assert payload["previewUrl"] is None
    assert [item["candidate_id"] for item in payload["candidates"]] == ["candidate_001", "candidate_002"]
    assert [item["image_asset_id"] for item in payload["candidates"]] == ["asset-001", "asset-002"]
    assert all("image_asset_id" not in item for item in payload["rawCandidates"])
    assert payload["uploads"] == []
    assert payload["visibleAssets"] == []


def test_reusable_asset_identity_requires_one_exact_successful_candidate_binding() -> None:
    payload = _node_json(
        r'''
import { candidatePreviewItems } from "./apps/studio/src/node-generation-progress.js";
const digest = (char) => char.repeat(64);
const reusable = (candidateId, char, assetId, overrides = {}) => ({
  asset_id: assetId, role: "generated_keyframe_reference", source_kind: "keyframe_candidate",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char), status: "succeeded", ...overrides,
});
const response = {
  job: { job_id: "job-001", project_id: "project-001", status: "succeeded" },
  candidate_previews: ["candidate_001", "candidate_002", "candidate_003", "candidate_004", "candidate_005"].map((candidateId, index) => ({
    candidate_id: candidateId,
    sha256: digest(String(index + 1)),
    preview_url: `/projects/project-001/keyframe-generations/job-001/candidates/${candidateId}/preview`,
  })),
  reusable_image_assets: [
    reusable("candidate_001", "1", "asset-001"),
    reusable("candidate_003", "3", "asset-003-a"),
    reusable("candidate_003", "3", "asset-003-b"),
    reusable("candidate_004", "4", "asset-004", { status: "failed" }),
    reusable("candidate_005", "5", "asset-005", { source_job_id: "job-other" }),
  ],
};
process.stdout.write(JSON.stringify(candidatePreviewItems(response)));
'''
    )

    by_id = {item["candidate_id"]: item for item in payload}
    assert by_id["candidate_001"]["image_asset_id"] == "asset-001"
    assert "image_asset_id" not in by_id["candidate_002"]
    assert "image_asset_id" not in by_id["candidate_003"]
    assert "image_asset_id" not in by_id["candidate_004"]
    assert "image_asset_id" not in by_id["candidate_005"]


def test_reusable_asset_project_envelope_and_all_preview_aliases_fail_closed() -> None:
    payload = _node_json(
        r'''
import { candidatePreviewItems } from "./apps/studio/src/node-generation-progress.js";
const sha = "a".repeat(64);
const route = "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview";
const asset = {
  asset_id: "asset-001", role: "generated_keyframe_reference", source_kind: "keyframe_candidate",
  source_job_id: "job-001", source_candidate_id: "candidate_001",
  source_candidate_digest: sha, sha256: sha, status: "succeeded",
};
function response(candidate, envelope = {}) {
  return {
    ...envelope,
    job: { job_id: "job-001", status: "succeeded", ...(envelope.job || {}) },
    candidate_previews: [{ candidate_id: "candidate_001", sha256: sha, ...candidate }],
    reusable_image_assets: [asset],
  };
}
function summary(value) {
  const candidate = candidatePreviewItems(value)[0];
  return {
    bound: candidate.image_asset_id === "asset-001",
    projectId: candidate.project_id || "",
    previewUrl: candidate.preview_url || candidate.url || "",
  };
}
const aliases = {};
for (const alias of ["preview_url", "url", "previewUrl", "image_asset_preview_url", "imageAssetPreviewUrl"]) {
  aliases[alias] = summary(response({ [alias]: route }, { job: { project_id: "project-001" } }));
}
process.stdout.write(JSON.stringify({
  aliases,
  topOnly: summary(response({ preview_url: route }, { project_id: "project-001" })),
  bothSame: summary(response({ preview_url: route }, { project_id: "project-001", job: { project_id: "project-001" } })),
  missing: summary(response({ preview_url: route })),
  conflict: summary(response({ preview_url: route }, { project_id: "project-001", job: { project_id: "project-002" } })),
}));
'''
    )

    assert all(item == {
        "bound": True,
        "projectId": "project-001",
        "previewUrl": "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
    } for item in payload["aliases"].values())
    assert payload["topOnly"]["bound"] is True
    assert payload["bothSame"]["bound"] is True
    for key in ("missing", "conflict"):
        assert payload[key] == {
            "bound": False,
            "projectId": "",
            "previewUrl": "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
        }


def test_separated_runtime_candidates_select_the_exact_reusable_asset() -> None:
    payload = _node_json(
        r'''
import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
import { submitCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const reusable = (candidateId, char, assetId) => ({
  asset_id: assetId, role: "generated_keyframe_reference", source_kind: "keyframe_candidate",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char), status: "succeeded",
});
const node = {
  id: "node-001",
  type: "image",
  status: "generating",
  params: {
    lastKeyframeJobId: "job-001",
    uploads: [],
    creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" },
  },
};
const state = { production: { active_run_id: "run-001" }, nodes: { "node-001": node }, assets: [] };
const store = { get: () => state, set: (mutator) => mutator(state), nextId: () => "visible-001", flushRuntimeSave: async () => {} };
applyKeyframeResponse(store, node.id, {
  job: { job_id: "job-001", project_id: "project-001", status: "succeeded" },
  candidate_previews: [
    { candidate_id: "candidate_001", sha256: digest("b"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview" },
    { candidate_id: "candidate_002", sha256: digest("c"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview" },
  ],
  reusable_image_assets: [
    reusable("candidate_001", "b", "asset-001"),
    reusable("candidate_002", "c", "asset-002"),
  ],
  safe_manifest: { output_count: 2 },
}, { aspect_ratio: "9:16" });
const before = {
  run_id: "run-001",
  subject_digest: digest("a"),
  candidates: [
    { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001" },
    { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001" },
  ],
  selected_revision: null,
  creator_decisions: [],
  exports: [],
  checkpoint: { version: 1, state_digest: digest("d") },
};
const after = {
  ...before,
  selected_revision: { revision_id: "revision-001", canonical_digest: digest("e"), candidate_id: "candidate_002", candidate_digest: digest("c") },
  creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
  checkpoint: { version: 2, state_digest: digest("f") },
};
let reads = 0;
const result = await submitCandidateSelection(store, {
  getProductionRun: async () => ({ production_run: ++reads === 1 ? before : after }),
  submitCreatorDecision: async () => ({ idempotent_replay: false }),
}, node, "candidate_002");
process.stdout.write(JSON.stringify({ result, state }));
'''
    )

    assert payload["result"]["ok"] is True
    selected = payload["state"]["nodes"]["node-001"]
    assert selected["params"]["creatorSelection"]["selected_asset_id"] == "asset-002"
    assert selected["params"]["uploads"][-1]["asset_id"] == "asset-002"
    assert selected["params"]["uploads"][-1]["source_candidate_id"] == "candidate_002"
    assert selected["previewUrl"].endswith("/candidate_002/preview")


def test_explicit_selection_persists_readback_and_drives_preview_fixed_asset_and_revision_lineage() -> None:
    payload = _node_json(
        r'''
import {
  buildCreatorDecisionContext,
  submitCandidateRevision,
  submitCandidateSelection,
} from "./apps/studio/src/candidate-selection-controller.js";

const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
const node = {
  id: "node-001",
  type: "image",
  status: "complete",
  previewUrl: "",
  params: {
    lastKeyframeJobId: "job-001",
    uploads: [],
    creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" },
    candidatePreviewUrls: [
      {
        candidate_id: "candidate_001",
        canonical_digest: digest("b"),
        parent_job_id: "job-001",
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_001", "b", "asset-001"),
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
        status: "succeeded",
      },
      {
        candidate_id: "candidate_002",
        canonical_digest: digest("c"),
        parent_job_id: "job-001",
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_002", "c", "asset-002"),
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
        status: "succeeded",
      },
    ],
  },
};
const state = {
  production: { active_run_id: "run-001" },
  nodes: { "node-001": node },
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
const base = {
  run_id: "run-001",
  subject_digest: digest("a"),
  candidates: [
    { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001", parent_candidate_id: null },
    { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001", parent_candidate_id: "candidate_001" },
  ],
  selected_revision: null,
  creator_decisions: [],
  exports: [],
  checkpoint: { version: 1, state_digest: digest("d") },
};
const selected = {
  ...base,
  selected_revision: {
    revision_id: "revision-001",
    revision_digest: digest("e"),
    candidate_id: "candidate_002",
    candidate_digest: digest("c"),
  },
  creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
  checkpoint: { version: 2, state_digest: digest("f") },
};
const revised = {
  ...selected,
  selected_revision: {
    revision_id: "revision-002",
    revision_digest: digest("1"),
    candidate_id: "candidate_002",
    candidate_digest: digest("c"),
  },
  creator_decisions: [
    ...selected.creator_decisions,
    { decision: "revise", candidate_id: "candidate_002", candidate_digest: digest("c") },
  ],
  exports: [{ export_id: "export-001" }],
  checkpoint: { version: 3, state_digest: digest("2") },
};
let phase = "select";
let reads = 0;
const requests = [];
const runtime = {
  getProductionRun: async () => {
    reads += 1;
    if (phase === "select") return { production_run: reads === 1 ? base : selected };
    return { production_run: reads === 3 ? selected : revised };
  },
  submitCreatorDecision: async (runId, body) => {
    requests.push({ runId, body });
    return { idempotent_replay: false };
  },
};
const selection = await submitCandidateSelection(store, runtime, node, "candidate_002", {
  idempotencyKey: "selection-idempotency-001",
  decisionId: "selection-decision-001",
});
const reselectionContext = buildCreatorDecisionContext(
  selected,
  state.nodes[node.id],
  selected.candidates[0],
  "select",
  "Switch the selected base candidate.",
  { idempotencyKey: "reselection-idempotency-001", decisionId: "reselection-decision-001" },
);
phase = "revise";
const revision = await submitCandidateRevision(
  store,
  runtime,
  state.nodes[node.id],
  "candidate_002",
  "Keep the selected composition but soften the key light.",
  { idempotencyKey: "revision-idempotency-001", decisionId: "revision-decision-001" },
);
process.stdout.write(JSON.stringify({ selection, reselectionContext, revision, requests, state }));
'''
    )

    assert payload["selection"]["ok"] is True
    context = payload["selection"]["context"]
    assert context["run_id"] == "run-001"
    assert context["node_id"] == "node-001"
    assert context["job_id"] == "job-001"
    assert context["candidate_id"] == "candidate_002"
    assert context["canonical_digest"] == "c" * 64
    assert context["parent_lineage"] == {
        "parent_job_id": "job-001",
        "parent_candidate_id": "candidate_001",
        "parent_revision_id": "",
    }
    request = payload["requests"][0]["body"]
    assert set(request) == {
        "schema_version",
        "decision_id",
        "idempotency_key",
        "expected_checkpoint_version",
        "subject_digest",
        "decision",
        "candidate_id",
        "candidate_digest",
        "parent_revision_id",
        "revision_intent",
    }
    assert request["candidate_id"] == "candidate_002"
    assert request["candidate_digest"] == "c" * 64
    assert request["expected_checkpoint_version"] == 1

    revision_request = payload["requests"][1]["body"]
    assert payload["reselectionContext"]["request"]["parent_revision_id"] == "revision-001"
    assert payload["revision"]["ok"] is True
    assert revision_request["decision"] == "revise"
    assert revision_request["parent_revision_id"] == "revision-001"
    assert revision_request["expected_checkpoint_version"] == 2
    assert revision_request["revision_intent"].startswith("Keep the selected composition")

    state = payload["state"]
    selected_node = state["nodes"]["node-001"]
    assert selected_node["previewUrl"].endswith("/candidate_002/preview")
    assert selected_node["params"]["uploads"][-1]["source_candidate_id"] == "candidate_002"
    assert state["production"]["selected_candidate_id"] == "candidate_002"
    assert state["production"]["selected_revision_id"] == "revision-002"
    assert state["production"]["last_export_id"] == "export-001"
    summary = selected_node["params"]["creatorSelection"]
    assert summary["selected_revision_id"] == "revision-002"
    assert summary["checkpoint_version"] == 3
    assert summary["selected_parent_job_id"] == "job-001"
    assert summary["selected_parent_candidate_id"] == "candidate_001"
    assert summary["selected_asset_id"] == "asset-002"


def test_stale_duplicate_and_failed_candidate_paths_remain_visible_and_fail_closed() -> None:
    payload = _node_json(
        r'''
import {
  isCandidateSelectable,
  submitCandidateSelection,
} from "./apps/studio/src/candidate-selection-controller.js";

const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
const candidate = {
  candidate_id: "candidate_002",
  canonical_digest: digest("c"),
  parent_job_id: "job-001",
};
const before = {
  run_id: "run-001",
  subject_digest: digest("a"),
  candidates: [candidate],
  selected_revision: null,
  creator_decisions: [],
  checkpoint: { version: 1, state_digest: digest("d") },
};
const after = {
  ...before,
  selected_revision: {
    revision_id: "revision-001",
    revision_digest: digest("e"),
    candidate_id: "candidate_002",
    candidate_digest: digest("c"),
  },
  creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
  checkpoint: { version: 2, state_digest: digest("f") },
};
function setup() {
  const node = {
    id: "node-001",
    previewUrl: "/projects/project-001/keyframe-generations/job-old/candidates/old/preview",
    params: {
      lastKeyframeJobId: "job-001",
      uploads: [],
      creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" },
      candidatePreviewUrls: [{
        candidate_id: "candidate_002",
        canonical_digest: digest("c"),
        parent_job_id: "job-001",
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_002", "c", "asset-002"),
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
        status: "succeeded",
      }],
    },
  };
  const state = { production: { active_run_id: "run-001" }, nodes: { "node-001": node } };
  const store = { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} };
  return { node, state, store };
}

const staleSetup = setup();
const staleRuntime = {
  getProductionRun: async () => ({ production_run: before }),
  submitCreatorDecision: async () => { const error = new Error("conflict"); error.status = 409; throw error; },
};
const stale = await submitCandidateSelection(staleSetup.store, staleRuntime, staleSetup.node, "candidate_002");

const duplicateSetup = setup();
let duplicateReads = 0;
const duplicateRuntime = {
  getProductionRun: async () => ({ production_run: ++duplicateReads === 1 ? before : after }),
  submitCreatorDecision: async () => ({ idempotent_replay: true }),
};
const duplicate = await submitCandidateSelection(duplicateSetup.store, duplicateRuntime, duplicateSetup.node, "candidate_002");

process.stdout.write(JSON.stringify({
  stale,
  stalePreview: staleSetup.state.nodes["node-001"].previewUrl,
  staleStatus: staleSetup.state.nodes["node-001"].params.creatorSelection,
  duplicate,
  duplicateStatus: duplicateSetup.state.nodes["node-001"].params.creatorSelection,
  failedSelectable: isCandidateSelectable({ candidate_id: "failed", preview_url: "/safe", status: "failed" }),
  retryableSelectable: isCandidateSelectable({ candidate_id: "retry", preview_url: "/safe", status: "retryable" }),
}));
'''
    )

    assert payload["stale"] == {
        "ok": False,
        "code": "stale_checkpoint",
        "message": "Selection was not saved because production state changed. Refresh and try again.",
    }
    assert payload["stalePreview"].endswith("/old/preview")
    assert payload["staleStatus"]["status"] == "stale_checkpoint"
    assert payload["duplicate"]["ok"] is True
    assert payload["duplicate"]["duplicate"] is True
    assert payload["duplicateStatus"]["status"] == "duplicate_replayed"
    assert payload["failedSelectable"] is False
    assert payload["retryableSelectable"] is False


def test_visible_candidate_digest_job_and_identity_mismatch_block_post_without_state_mutation() -> None:
    payload = _node_json(
        r'''
import { submitCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, candidateDigest, assetId, jobId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: jobId, source_candidate_id: candidateId,
  source_candidate_digest: candidateDigest, sha256: candidateDigest,
});
const authoritative = { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001" };
const run = {
  run_id: "run-001",
  subject_digest: digest("a"),
  candidates: [authoritative],
  selected_revision: null,
  creator_decisions: [],
  exports: [],
  checkpoint: { version: 1, state_digest: digest("d") },
};
async function attempt(overrides, studioBinding = null) {
  const visible = {
    candidate_id: "candidate_002",
    canonical_digest: digest("c"),
    parent_job_id: "job-001",
    project_id: "project-001",
    preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
    status: "succeeded",
    ...overrides,
  };
  visible.reusable_asset_authority = proof(
    visible.candidate_id,
    visible.canonical_digest,
    "asset-002",
    visible.parent_job_id,
  );
  const node = {
    id: "node-001",
    previewUrl: "/projects/project-001/keyframe-generations/job-old/candidates/old/preview",
    params: {
      lastKeyframeJobId: "job-001",
      uploads: [{ asset_id: "asset-old" }],
      creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" },
      candidatePreviewUrls: [visible],
    },
  };
  const state = { production: { active_run_id: "run-001" }, nodes: { "node-001": node } };
  const before = JSON.stringify(state);
  let posts = 0;
  const result = await submitCandidateSelection(
    { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} },
    {
      getProductionRun: async () => ({ production_run: run, ...(studioBinding ? { studio_binding: studioBinding } : {}) }),
      submitCreatorDecision: async () => { posts += 1; return {}; },
    },
    node,
    "candidate_002",
  );
  return { result, posts, unchanged: JSON.stringify(state) === before };
}
process.stdout.write(JSON.stringify({
  digestMismatch: await attempt({ canonical_digest: digest("e") }),
  jobMismatch: await attempt({ parent_job_id: "job-002" }),
  idMismatch: await attempt({ candidate_id: "candidate_003" }),
  bindingMismatch: await attempt({}, {
    schema_version: "afs_studio_production_binding.v0.1",
    authoritative_source: "runtime_production_run",
    compatibility_mode: "backend_authoritative_summary_only",
    active_run_id: "run-001",
    checkpoint_version: 1,
    checkpoint_digest: digest("d"),
    subject_digest: digest("e"),
  }),
}));
'''
    )

    for key, expected_code in (
        ("digestMismatch", "candidate_authority_mismatch"),
        ("jobMismatch", "candidate_asset_authority_mismatch"),
        ("idMismatch", "candidate_asset_authority_mismatch"),
    ):
        case = payload[key]
        assert case["result"]["ok"] is False
        assert case["result"]["code"] == expected_code
        assert "Refresh generation results" in case["result"]["message"]
        assert case["posts"] == 0
        assert case["unchanged"] is True
    assert payload["bindingMismatch"]["result"]["code"] == "binding_integrity_mismatch"
    assert payload["bindingMismatch"]["posts"] == 0
    assert payload["bindingMismatch"]["unchanged"] is True


def test_restore_rejects_visible_integrity_mismatch_without_preview_asset_or_state_relabel() -> None:
    payload = _node_json(
        r'''
import { restoreCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, candidateDigest, assetId, jobId = "job-001") => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: jobId, source_candidate_id: candidateId,
  source_candidate_digest: candidateDigest, sha256: candidateDigest,
});
const node = {
  id: "node-001",
  previewUrl: "/projects/project-001/keyframe-generations/job-old/candidates/old/preview",
  params: {
    lastKeyframeJobId: "job-001",
    uploads: [{ asset_id: "asset-old", role: "existing" }],
    candidatePreviewUrls: [{
      candidate_id: "candidate_002",
      canonical_digest: digest("e"),
      parent_job_id: "job-001",
      project_id: "project-001",
      reusable_asset_authority: proof("candidate_002", digest("e"), "asset-local"),
      preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
      status: "succeeded",
    }],
  },
};
const state = { production: { active_run_id: "run-001" }, nodes: { "node-001": node } };
const before = JSON.stringify(state);
const result = await restoreCandidateSelection(
  { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} },
  { getProductionRun: async () => ({ production_run: {
    run_id: "run-001",
    subject_digest: digest("a"),
    candidates: [{ candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001" }],
    selected_revision: { revision_id: "revision-001", canonical_digest: digest("f"), candidate_id: "candidate_002", candidate_digest: digest("c") },
    creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
    exports: [],
    checkpoint: { version: 2, state_digest: digest("d") },
  } }) },
  node,
);
process.stdout.write(JSON.stringify({ result, unchanged: JSON.stringify(state) === before, state }));
'''
    )

    assert payload["result"] == {
        "ok": False,
        "code": "candidate_authority_mismatch",
        "message": "Visible candidate integrity or lineage no longer matches production authority. Refresh generation results before selecting.",
    }
    assert payload["unchanged"] is True
    assert payload["state"]["nodes"]["node-001"]["params"]["uploads"] == [{"asset_id": "asset-old", "role": "existing"}]
    assert payload["state"]["nodes"]["node-001"]["previewUrl"].endswith("/job-old/candidates/old/preview")


def test_reload_readback_restores_backend_authoritative_selection_without_local_creator_summary() -> None:
    payload = _node_json(
        r'''
import { restoreCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
const node = {
  id: "node-001",
  type: "image",
  params: {
    candidatePreviewUrls: [
      {
        candidate_id: "candidate_001",
        canonical_digest: digest("b"),
        parent_job_id: "job-001",
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_001", "b", "asset-001"),
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
        status: "succeeded",
      },
      {
        candidate_id: "candidate_002",
        canonical_digest: digest("c"),
        parent_job_id: "job-001",
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_002", "c", "asset-002"),
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
        status: "succeeded",
      },
    ],
  },
};
const state = {
  production: {
    active_run_id: "run-001",
    selected_candidate_id: "candidate_002",
    selected_candidate_digest: digest("c"),
  },
  nodes: { "node-001": node },
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
const runtime = {
  getProductionRun: async () => ({
    studio_binding: {
      schema_version: "afs_studio_production_binding.v0.1",
      authoritative_source: "runtime_production_run",
      compatibility_mode: "backend_authoritative_summary_only",
      active_run_id: "run-001",
      checkpoint_version: 2,
      checkpoint_digest: digest("f"),
      subject_digest: digest("a"),
      selected_candidate_id: "candidate_002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-001",
      selected_revision_digest: digest("e"),
    },
    production_run: {
      run_id: "run-001",
      subject_digest: digest("a"),
      candidates: [
        { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001" },
        { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001" },
      ],
      selected_revision: {
        revision_id: "revision-001",
        canonical_digest: digest("e"),
        candidate_id: "candidate_002",
        candidate_digest: digest("c"),
      },
      creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
      exports: [],
      checkpoint: { version: 2, state_digest: digest("f") },
    },
  }),
};
const result = await restoreCandidateSelection(store, runtime, node);
process.stdout.write(JSON.stringify({ result, state }));
'''
    )

    assert payload["result"]["ok"] is True
    assert payload["state"]["production"]["authoritative_source"] == "runtime_production_run"
    assert payload["state"]["nodes"]["node-001"]["previewUrl"].endswith("candidate_002/preview")
    assert payload["state"]["nodes"]["node-001"]["params"]["creatorSelection"]["selected_candidate_id"] == "candidate_002"


def test_startup_remote_load_automatically_restores_authority_and_fail_closed_conflict_preserves_preview() -> None:
    payload = _node_json(
        r'''
import { restoreCandidateSelectionsAfterLoad } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
function setup(withRun = true) {
  const node = {
    id: "node-001",
    type: "image",
    previewUrl: "/projects/project-001/keyframe-generations/job-old/candidates/old/preview",
    params: {
      lastKeyframeJobId: "job-001",
      uploads: [],
      candidatePreviewUrls: [
        { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001", project_id: "project-001", reusable_asset_authority: proof("candidate_001", "b", "asset-001"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview", status: "succeeded" },
        { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001", project_id: "project-001", reusable_asset_authority: proof("candidate_002", "c", "asset-002"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview", status: "succeeded" },
      ],
    },
  };
  const state = { production: withRun ? { active_run_id: "run-001", selected_candidate_id: "candidate_002" } : {}, nodes: { "node-001": node } };
  return { node, state, store: { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} } };
}
const run = {
  run_id: "run-001",
  subject_digest: digest("a"),
  candidates: [
    { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001" },
    { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001", parent_candidate_id: "candidate_001" },
  ],
  selected_revision: { revision_id: "revision-001", canonical_digest: digest("e"), candidate_id: "candidate_002", candidate_digest: digest("c") },
  creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
  exports: [],
  checkpoint: { version: 2, state_digest: digest("f") },
};
const binding = {
  schema_version: "afs_studio_production_binding.v0.1",
  authoritative_source: "runtime_production_run",
  compatibility_mode: "backend_authoritative_summary_only",
  active_run_id: "run-001",
  checkpoint_version: 2,
  checkpoint_digest: digest("f"),
  subject_digest: digest("a"),
  selected_candidate_id: "candidate_002",
  selected_candidate_digest: digest("c"),
  selected_revision_id: "revision-001",
  selected_revision_digest: digest("e"),
};
let reads = 0;
const restored = setup();
const success = await restoreCandidateSelectionsAfterLoad(restored.store, {
  getProductionRun: async () => { reads += 1; return { production_run: run, studio_binding: binding }; },
});
const unbound = setup(false);
const skipped = await restoreCandidateSelectionsAfterLoad(unbound.store, {
  getProductionRun: async () => { throw new Error("must not read without a bound run"); },
});
const conflicted = setup();
const beforeConflictPreview = conflicted.node.previewUrl;
const conflict = await restoreCandidateSelectionsAfterLoad(conflicted.store, {
  getProductionRun: async () => { const error = new Error("conflict"); error.status = 409; throw error; },
});
process.stdout.write(JSON.stringify({
  success,
  reads,
  restoredPreview: restored.node.previewUrl,
  restoredSummary: restored.node.params.creatorSelection,
  skipped,
  conflict,
  conflictPreviewPreserved: conflicted.node.previewUrl === beforeConflictPreview,
  conflictStatus: conflicted.node.params.creatorSelection,
}));
'''
    )

    assert payload["success"]["ok"] is True
    assert payload["reads"] == 1
    assert payload["restoredPreview"].endswith("candidate_002/preview")
    assert payload["restoredSummary"]["selected_revision_id"] == "revision-001"
    assert payload["restoredSummary"]["selected_parent_job_id"] == "job-001"
    assert payload["restoredSummary"]["selected_asset_id"] == "asset-002"
    assert payload["skipped"] == {"ok": True, "skipped": "run_unbound"}
    assert payload["conflict"] == {
        "ok": False,
        "code": "stale_checkpoint",
        "message": "Selection was not saved because production state changed. Refresh and try again.",
    }
    assert payload["conflictPreviewPreserved"] is True
    assert payload["conflictStatus"]["status"] == "stale_checkpoint"


def test_candidate_creator_action_locks_duplicate_controls_while_authority_is_in_flight() -> None:
    payload = _node_json(
        r'''
import { handleCandidateCreatorAction } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
const candidate = { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001" };
const before = { run_id: "run-001", subject_digest: digest("a"), candidates: [candidate], selected_revision: null, creator_decisions: [], exports: [], checkpoint: { version: 1, state_digest: digest("d") } };
const after = { ...before, selected_revision: { revision_id: "revision-001", revision_digest: digest("e"), candidate_id: "candidate_002", candidate_digest: digest("c") }, creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }], checkpoint: { version: 2, state_digest: digest("f") } };
const node = { id: "node-001", params: { lastKeyframeJobId: "job-001", uploads: [], creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" }, candidatePreviewUrls: [{ candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001", project_id: "project-001", reusable_asset_authority: proof("candidate_002", "c", "asset-002"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview", status: "succeeded" }] } };
const state = { production: { active_run_id: "run-001" }, nodes: { "node-001": node } };
const store = { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} };
let releaseRead;
let reads = 0;
const runtime = {
  getProductionRun: async () => {
    reads += 1;
    if (reads === 1) return new Promise((resolve) => { releaseRead = () => resolve({ production_run: before }); });
    return { production_run: after };
  },
  submitCreatorDecision: async () => ({ idempotent_replay: false }),
};
const status = { dataset: {}, textContent: "" };
const revisionInput = { disabled: false };
const refresh = { disabled: false };
const revise = { disabled: true, dataset: {} };
const action = { disabled: false, dataset: { action: "candidate-select", candidateId: "candidate_002" } };
const controls = [action, refresh, revise, revisionInput];
const panel = {
  dataset: {},
  setAttribute: (name, value) => { panel[name] = value; },
  querySelectorAll: (selector) => selector.includes("role") ? [] : controls,
  querySelector: (selector) => selector.includes("selection-status") ? status : selector.includes("revision-intent") ? { value: "" } : selector.includes("candidate-revise") ? revise : null,
};
action.closest = () => panel;
const first = handleCandidateCreatorAction(store, runtime, node, action);
const during = { ariaBusy: panel["aria-busy"], busy: panel.dataset.busy, disabled: controls.map((item) => item.disabled), status: status.dataset.state };
const duplicate = await handleCandidateCreatorAction(store, runtime, node, action);
releaseRead();
const result = await first;
process.stdout.write(JSON.stringify({ during, duplicate, result, afterBusy: panel["aria-busy"], reads }));
'''
    )

    assert payload["during"] == {
        "ariaBusy": "true",
        "busy": "true",
        "disabled": [True, True, True, True],
        "status": "saving",
    }
    assert payload["duplicate"]["code"] == "selection_in_flight"
    assert payload["result"]["ok"] is True
    assert payload["afterBusy"] == "false"
    assert payload["reads"] == 2


def test_candidate_selection_ui_exposes_accessible_explicit_actions_and_mobile_reflow() -> None:
    result_view = (STUDIO / "src" / "node-result-view.js").read_text(encoding="utf-8")
    controller = (STUDIO / "src" / "candidate-selection-controller.js").read_text(encoding="utf-8")
    handler = (STUDIO / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "node-result.css").read_text(encoding="utf-8")
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    media_preview = (STUDIO / "src" / "media-preview-modal.js").read_text(encoding="utf-8")

    for marker in (
        'setAttribute("role", "radiogroup")',
        'setAttribute("role", "radio")',
        'setAttribute("aria-checked"',
        'dataset.action = "candidate-select"',
        'dataset.action = "candidate-revise"',
        'dataset.action = "candidate-refresh"',
        'aria-live',
        'setAttribute("aria-busy"',
        'setAttribute("aria-disabled"',
        'candidate-selection-identity',
        '"Revision"',
        '"Checkpoint"',
        '"Lineage job"',
        '"Asset source"',
        "放大查看不会改变选择",
        "不可选择",
    ):
        assert marker in result_view
    assert "handleCandidateGridKeydown" in controller
    assert '"ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"' in controller
    assert '[" ", "Spacebar", "Enter"]' in controller
    assert '["candidate-select", "candidate-revise", "candidate-refresh"]' in handler
    assert ":focus-visible" in styles
    assert "@media (max-width: 620px)" in styles
    assert ".candidate-card-shell.selected" in styles
    candidate_rule = re.search(r"\.node-result\.has-candidates:not\(\.has-preview\)\s*\{(?P<body>[^}]*)\}", styles, re.DOTALL)
    assert candidate_rule
    assert "max-height: none" in candidate_rule.group("body")
    assert "overflow-y: visible" in candidate_rule.group("body")
    assert '.candidate-selection-status[data-state="duplicate_replayed"]' in styles
    assert '.candidate-selection-status[data-state="saving"]' in styles
    assert "min-height: 44px" in styles
    assert main.count("restoreCandidateSelectionsAfterLoad(store") == 2
    assert main.index("await store.hydrateRuntime(runtime)") < main.index("await restoreCandidateSelectionsAfterLoad(store, runtime)")
    assert 'closeBtn.setAttribute("aria-label", "Close media preview")' in media_preview
    assert "showModal(modal, { initialFocus: closeBtn })" in media_preview

    def contrast(foreground: str, background: str) -> float:
        def luminance(value: str) -> float:
            channels = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

    assert contrast("#cbd2dc", "#141619") >= 4.5
    assert contrast("#ffe29a", "#141619") >= 4.5
    assert contrast("#ffd18b", "#141619") >= 4.5


def test_candidate_keyboard_space_enter_and_arrow_navigation_are_operable() -> None:
    payload = _node_json(
        r'''
import { handleCandidateGridKeydown } from "./apps/studio/src/candidate-selection-controller.js";
let clicks = 0;
let focused = "";
const choices = ["one", "two"].map((id) => ({
  id,
  disabled: false,
  tabIndex: -1,
  click: () => { clicks += 1; },
  focus: () => { focused = id; },
}));
let prevented = 0;
let stopped = 0;
const grid = { querySelectorAll: () => choices };
const space = handleCandidateGridKeydown({
  key: " ",
  target: { closest: () => choices[0] },
  currentTarget: grid,
  preventDefault: () => { prevented += 1; },
  stopPropagation: () => { stopped += 1; },
});
const arrow = handleCandidateGridKeydown({
  key: "ArrowRight",
  target: { closest: () => choices[0] },
  currentTarget: grid,
  preventDefault: () => { prevented += 1; },
  stopPropagation: () => { stopped += 1; },
});
process.stdout.write(JSON.stringify({ space, arrow, clicks, focused, prevented, stopped, tabs: choices.map((item) => item.tabIndex) }));
'''
    )

    assert payload == {
        "space": True,
        "arrow": True,
        "clicks": 1,
        "focused": "two",
        "prevented": 2,
        "stopped": 2,
        "tabs": [-1, 0],
    }


def test_unbound_selection_creates_authenticated_run_then_uses_server_binding_and_readback() -> None:
    payload = _node_json(
        r'''
import { submitCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1", asset_id: assetId,
  role: "generated_keyframe_reference", source_kind: "keyframe_candidate", status: "succeeded",
  source_job_id: "job-001", source_candidate_id: candidateId,
  source_candidate_digest: digest(char), sha256: digest(char),
});
const node = {
  id: "node-001",
  params: {
    lastKeyframeJobId: "job-001",
    uploads: [],
    candidatePreviewUrls: [
      { candidate_id: "candidate_001", canonical_digest: digest("b"), parent_job_id: "job-001", project_id: "project-001", reusable_asset_authority: proof("candidate_001", "b", "asset-001"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview", status: "succeeded" },
      { candidate_id: "candidate_002", canonical_digest: digest("c"), parent_job_id: "job-001", project_id: "project-001", reusable_asset_authority: proof("candidate_002", "c", "asset-002"), preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview", status: "succeeded" },
    ],
  },
};
const state = { meta: { projectId: "project-001" }, production: {}, nodes: { "node-001": node } };
const store = { get: () => state, set: (mutator) => mutator(state), flushRuntimeSave: async () => {} };
const createdRun = {
  run_id: "production-job-001",
  subject_digest: "",
  candidates: [],
  selected_revision: null,
  creator_decisions: [],
  exports: [],
  checkpoint: { version: 1, state_digest: digest("d") },
};
let createRequest;
let createdBinding;
let selectedRun;
let reads = 0;
const runtime = {
  projectId: "project-001",
  createProductionRun: async (request) => {
    createRequest = request;
    createdRun.subject_digest = request.subject_digest;
    createdRun.candidates = request.candidates;
    createdBinding = {
      schema_version: "afs_studio_production_binding.v0.1",
      authoritative_source: "runtime_production_run",
      compatibility_mode: "backend_authoritative_summary_only",
      active_run_id: createdRun.run_id,
      checkpoint_version: 1,
      checkpoint_digest: digest("d"),
      subject_digest: request.subject_digest,
    };
    selectedRun = {
      ...createdRun,
      selected_revision: { revision_id: "revision-001", canonical_digest: digest("e"), candidate_id: "candidate_002", candidate_digest: digest("c") },
      creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
      checkpoint: { version: 2, state_digest: digest("f") },
    };
    return { production_run: createdRun, studio_binding: createdBinding, idempotent_replay: false };
  },
  getProductionRun: async () => {
    reads += 1;
    if (reads === 1) return { production_run: createdRun, studio_binding: createdBinding };
    return {
      production_run: selectedRun,
      studio_binding: {
        ...createdBinding,
        checkpoint_version: 2,
        checkpoint_digest: digest("f"),
        selected_candidate_id: "candidate_002",
        selected_candidate_digest: digest("c"),
        selected_revision_id: "revision-001",
        selected_revision_digest: digest("e"),
      },
    };
  },
  submitCreatorDecision: async () => ({ idempotent_replay: false }),
};
const result = await submitCandidateSelection(store, runtime, node, "candidate_002", {
  idempotencyKey: "select-candidate_002",
  decisionId: "decision-candidate_002",
});
process.stdout.write(JSON.stringify({ result, createRequest, state }));
'''
    )

    assert payload["result"]["ok"] is True
    request = payload["createRequest"]
    assert request["run_id"] == "production-job-001"
    assert request["idempotency_key"] == "create-project-001-node-001-job-001"
    assert len(request["subject_digest"]) == 64
    assert [item["candidate_id"] for item in request["candidates"]] == ["candidate_001", "candidate_002"]
    assert [item["canonical_digest"] for item in request["candidates"]] == ["b" * 64, "c" * 64]
    assert all(item["parent_job_id"] == "job-001" for item in request["candidates"])
    assert "active_run_id" not in request
    assert payload["state"]["production"] == {
        "schema_version": "afs_studio_production_binding.v0.1",
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": "production-job-001",
        "checkpoint_version": 2,
        "checkpoint_digest": "f" * 64,
        "subject_digest": request["subject_digest"],
        "selected_candidate_id": "candidate_002",
        "selected_candidate_digest": "c" * 64,
        "selected_revision_id": "revision-001",
        "selected_revision_digest": "e" * 64,
        "last_export_id": "",
    }


def test_active_production_run_reuse_requires_current_node_and_parent_job_ownership() -> None:
    payload = _node_json(
        r'''
import { ensureProductionRunForCandidateSelection } from "./apps/studio/src/candidate-selection-controller.js";
const digest = (char) => char.repeat(64);
const proof = (candidateId, jobId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1",
  asset_id: `asset-${jobId}`,
  role: "generated_keyframe_reference",
  source_kind: "keyframe_candidate",
  status: "succeeded",
  source_job_id: jobId,
  source_candidate_id: candidateId,
  source_candidate_digest: digest("a"),
  sha256: digest("a"),
});
function node(nodeId, jobId, owner = null) {
  return {
    id: nodeId,
    params: {
      lastKeyframeJobId: jobId,
      uploads: [],
      candidatePreviewUrls: [{
        candidate_id: "candidate_001",
        canonical_digest: digest("a"),
        parent_job_id: jobId,
        project_id: "project-001",
        reusable_asset_authority: proof("candidate_001", jobId),
        preview_url: `/projects/project-001/keyframe-generations/${jobId}/candidates/candidate_001/preview`,
        status: "succeeded",
      }],
      ...(owner ? { creatorSelection: owner } : {}),
    },
  };
}
function storeFor(nodes, activeRunId) {
  const state = { meta: { projectId: "project-001" }, production: { active_run_id: activeRunId }, nodes };
  return {
    state,
    store: { get: () => state, set: (mutator) => mutator(state) },
  };
}
let creates = 0;
const runtime = {
  projectId: "project-001",
  createProductionRun: async (request) => {
    creates += 1;
    const checkpointDigest = digest(String(creates + 1));
    return {
      production_run: {
        run_id: request.run_id,
        subject_digest: request.subject_digest,
        candidates: request.candidates,
        selected_revision: null,
        creator_decisions: [],
        exports: [],
        checkpoint: { version: 1, state_digest: checkpointDigest },
      },
      studio_binding: {
        schema_version: "afs_studio_production_binding.v0.1",
        authoritative_source: "runtime_production_run",
        compatibility_mode: "backend_authoritative_summary_only",
        active_run_id: request.run_id,
        checkpoint_version: 1,
        checkpoint_digest: checkpointDigest,
        subject_digest: request.subject_digest,
      },
    };
  },
};

const validNode = node("node-current", "job-current", {
  run_id: "run-current",
  selected_parent_job_id: "job-current",
});
const valid = storeFor({ "node-current": validNode }, "run-current");
const validResult = await ensureProductionRunForCandidateSelection(valid.store, runtime, validNode);

const otherNode = node("node-other", "job-shared", {
  run_id: "run-other-node",
  selected_parent_job_id: "job-shared",
});
const currentNode = node("node-current", "job-shared");
const staleNode = storeFor({ "node-other": otherNode, "node-current": currentNode }, "run-other-node");
const staleNodeResult = await ensureProductionRunForCandidateSelection(staleNode.store, runtime, currentNode);

const rerunNode = node("node-current", "job-new", {
  run_id: "run-old-job",
  selected_parent_job_id: "job-old",
});
const staleParent = storeFor({ "node-current": rerunNode }, "run-old-job");
const staleParentResult = await ensureProductionRunForCandidateSelection(staleParent.store, runtime, rerunNode);

process.stdout.write(JSON.stringify({
  creates,
  validResult,
  validProduction: valid.state.production,
  staleNodeResult,
  staleNodeProduction: staleNode.state.production,
  staleNodeOwner: staleNode.state.nodes["node-current"].params.creatorSelection,
  staleParentResult,
  staleParentProduction: staleParent.state.production,
  staleParentOwner: staleParent.state.nodes["node-current"].params.creatorSelection,
}));
'''
    )

    assert payload["creates"] == 2
    assert payload["validResult"] == {"ok": True, "run_id": "run-current", "created": False}
    assert payload["validProduction"] == {"active_run_id": "run-current"}
    assert payload["staleNodeResult"]["created"] is True
    assert payload["staleNodeProduction"]["active_run_id"] == "production-job-shared"
    assert payload["staleNodeOwner"]["run_id"] == "production-job-shared"
    assert payload["staleNodeOwner"]["selected_parent_job_id"] == "job-shared"
    assert payload["staleParentResult"]["created"] is True
    assert payload["staleParentProduction"]["active_run_id"] == "production-job-new"
    assert payload["staleParentOwner"]["run_id"] == "production-job-new"
    assert payload["staleParentOwner"]["selected_parent_job_id"] == "job-new"


def test_candidate_digest_and_job_lineage_survive_preview_normalization_and_persistence() -> None:
    payload = _node_json(
        r'''
import { candidatePreviewItems } from "./apps/studio/src/node-generation-progress.js";
import { initialState, snapshotStudioState } from "./apps/studio/src/store-state.js";
const sha = "a".repeat(64);
const authority = {
  asset_id: "asset-001", role: "generated_keyframe_reference", source_kind: "keyframe_candidate",
  source_job_id: "job-001", source_candidate_id: "candidate_001",
  source_candidate_digest: sha, sha256: sha, status: "succeeded",
};
const candidates = candidatePreviewItems({
  job: { job_id: "job-001", project_id: "project-001" },
  candidate_previews: [{
    candidate_id: "candidate_001",
    preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
    sha256: sha,
  }],
  reusable_image_assets: [authority],
});
const state = initialState("project-001");
state.nodes = { node_1: { id: "node_1", type: "image", params: { candidatePreviewUrls: candidates } } };
state.order = ["node_1"];
const persisted = snapshotStudioState(state);
process.stdout.write(JSON.stringify({ candidates, persisted: persisted.nodes.node_1.params.candidatePreviewUrls }));
'''
    )

    assert payload["candidates"][0]["canonical_digest"] == "a" * 64
    assert payload["candidates"][0]["parent_job_id"] == "job-001"
    assert payload["persisted"][0]["canonical_digest"] == "a" * 64
    assert payload["persisted"][0]["parent_job_id"] == "job-001"
    assert payload["persisted"][0]["image_asset_id"] == "asset-001"
    assert payload["persisted"][0]["reusable_asset_authority"]["source_candidate_id"] == "candidate_001"


def test_reusable_asset_authority_invalid_matrix_fails_closed_across_nine_consumers() -> None:
    payload = _node_json(
        r'''
import {
  handleCandidateCreatorAction,
  isCandidateSelectable,
  restoreCandidateSelection,
  restoreCandidateSelectionsAfterLoad,
  submitCandidateRevision,
  submitCandidateSelection,
} from "./apps/studio/src/candidate-selection-controller.js";
import { candidatePreviewsFromNode } from "./apps/studio/src/node-candidate-previews.js";
import { candidatePreviewItems } from "./apps/studio/src/node-generation-progress.js";
import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
import { initialState, snapshotStudioState } from "./apps/studio/src/store-state.js";

const digest = (char) => char.repeat(64);
const candidate = {
  candidate_id: "candidate_001",
  canonical_digest: digest("a"),
  parent_job_id: "job-001",
  project_id: "project-001",
  preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
  status: "succeeded",
};
const authority = {
  schema_version: "afs_studio_reusable_asset_authority.v0.1",
  asset_id: "asset-001",
  role: "generated_keyframe_reference",
  source_kind: "keyframe_candidate",
  status: "succeeded",
  source_job_id: "job-001",
  source_candidate_id: "candidate_001",
  source_candidate_digest: digest("a"),
  sha256: digest("a"),
};
const mutate = (name, patch, options = {}) => ({ name, patch, ...options });
const variants = [
  mutate("missing_asset_id", { asset_id: undefined }),
  mutate("missing_role", { role: undefined }),
  mutate("missing_source_kind", { source_kind: undefined }),
  mutate("missing_status", { status: undefined }),
  mutate("missing_source_job_id", { source_job_id: undefined }),
  mutate("missing_source_candidate_id", { source_candidate_id: undefined }),
  mutate("missing_source_candidate_digest", { source_candidate_digest: undefined }),
  mutate("missing_sha256", { sha256: undefined }),
  mutate("failed_status", { status: "failed" }),
  mutate("retryable_status", { status: "retryable" }),
  mutate("job_mismatch", { source_job_id: "job-002" }),
  mutate("candidate_mismatch", { source_candidate_id: "candidate_002" }),
  mutate("digest_mismatch", { source_candidate_digest: digest("b"), sha256: digest("b") }),
  mutate("sha_mismatch", { sha256: digest("b") }),
  mutate("duplicate_or_ambiguous", {}, { duplicate: true }),
  mutate("asset_id_null", { asset_id: null }),
  mutate("asset_id_number", { asset_id: 7 }),
  mutate("asset_id_object", { asset_id: { value: "asset-001" } }),
  mutate("source_candidate_id_null", { source_candidate_id: null }),
  mutate("source_candidate_id_number", { source_candidate_id: 7 }),
  mutate("source_candidate_id_object", { source_candidate_id: { value: "candidate_001" } }),
  mutate("source_job_id_null", { source_job_id: null }),
  mutate("source_job_id_number", { source_job_id: 7 }),
  mutate("source_job_id_object", { source_job_id: { value: "job-001" } }),
  mutate("status_number", { status: 1 }),
  mutate("envelope_job_override", { source_job_id: "job-evil" }, {
    invalidRoute: true,
    allowStoredPreview: true,
    rawCandidatePatch: {
      parent_job_id: "job-evil",
      preview_url: "/projects/project-001/keyframe-generations/job-evil/candidates/candidate_001/preview",
    },
    nestedCandidatePatch: {
      parent_job_id: "",
      preview_url: "/projects/project-001/keyframe-generations/job-evil/candidates/candidate_001/preview",
    },
  }),
  mutate("candidate_route_identity_mismatch", {}, {
    invalidRoute: true,
    rawCandidatePatch: {
      preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
    },
    nestedCandidatePatch: {
      preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
    },
  }),
  mutate("foreign_project_route", {}, {
    invalidRoute: true,
    rawCandidatePatch: {
      preview_url: "/projects/project-evil/keyframe-generations/job-001/candidates/candidate_001/preview",
    },
    nestedCandidatePatch: {
      preview_url: "/projects/project-evil/keyframe-generations/job-001/candidates/candidate_001/preview",
    },
  }),
  mutate("camel_snake_route_conflict", {}, {
    invalidRoute: true,
    rawCandidatePatch: {
      previewUrl: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
    },
    nestedCandidatePatch: {
      previewUrl: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_002/preview",
    },
  }),
];

function mutatedAuthority(variant) {
  const value = { ...authority, ...variant.patch };
  for (const [key, field] of Object.entries(variant.patch)) {
    if (field === undefined) delete value[key];
  }
  return value;
}

function rawAssets(variant) {
  const value = mutatedAuthority(variant);
  return variant.duplicate ? [value, { ...value, asset_id: "asset-duplicate" }] : [value];
}

function nestedAuthority(variant) {
  return variant.duplicate ? [authority, { ...authority, asset_id: "asset-duplicate" }] : mutatedAuthority(variant);
}

function nodeWithAuthority(variant) {
  return {
    id: "node-001",
    type: "image",
    params: {
      lastKeyframeJobId: "job-001",
      uploads: [],
      candidatePreviewUrls: [{
        ...candidate,
        ...(variant.nestedCandidatePatch || {}),
        reusable_asset_authority: nestedAuthority(variant),
      }],
    },
  };
}

function makeStore(node) {
  const state = { production: { active_run_id: "run-001" }, nodes: { [node.id]: node }, assets: [] };
  return {
    state,
    store: {
      get: () => state,
      set: (mutator) => mutator(state),
      nextId: () => "visible-001",
      flushRuntimeSave: async () => {},
    },
  };
}

const run = {
  run_id: "run-001",
  subject_digest: digest("b"),
  candidates: [{ candidate_id: "candidate_001", canonical_digest: digest("a"), parent_job_id: "job-001" }],
  selected_revision: {
    revision_id: "revision-001",
    canonical_digest: digest("c"),
    candidate_id: "candidate_001",
    candidate_digest: digest("a"),
  },
  creator_decisions: [{ decision: "select", candidate_id: "candidate_001", candidate_digest: digest("a") }],
  exports: [],
  checkpoint: { version: 2, state_digest: digest("d") },
};

const failures = [];
let executions = 0;
function reject(variant, consumer, condition) {
  executions += 1;
  if (!condition) failures.push(`${variant.name}:${consumer}`);
}

for (const variant of variants) {
  const response = {
    job: { job_id: "job-001", project_id: "project-001", status: "succeeded" },
    candidate_previews: [{ ...candidate, sha256: digest("a"), ...(variant.rawCandidatePatch || {}) }],
    reusable_image_assets: rawAssets(variant),
    safe_manifest: { output_count: 1 },
  };
  const rawBefore = JSON.stringify(response);

  const normalized = candidatePreviewItems(response)[0];
  reject(variant, "normalize", !normalized.image_asset_id && !normalized.reusable_asset_authority
    && (!variant.invalidRoute || (!normalized.preview_url && !normalized.url))
    && JSON.stringify(response) === rawBefore);

  const keyframeNode = { id: "node-001", type: "image", params: { uploads: [], lastKeyframeJobId: "job-001" } };
  const keyframe = makeStore(keyframeNode);
  applyKeyframeResponse(keyframe.store, keyframeNode.id, response, { aspect_ratio: "9:16" });
  const applied = keyframe.state.nodes[keyframeNode.id];
  reject(variant, "keyframe", !applied.params.candidatePreviewUrls[0].image_asset_id
    && !applied.params.candidatePreviewUrls[0].reusable_asset_authority
    && applied.params.uploads.length === 0 && keyframe.state.assets.length === 0
    && (!variant.invalidRoute || !applied.previewUrl)
    && JSON.stringify(response) === rawBefore);

  const downstream = candidatePreviewsFromNode(nodeWithAuthority(variant))[0];
  reject(variant, "downstream", !downstream.image_asset_id
    && !downstream.reusable_asset_authority && !isCandidateSelectable(downstream)
    && (!variant.invalidRoute || variant.allowStoredPreview || (!downstream.preview_url && !downstream.url)));

  for (const [consumer, invoke] of [
    ["select", (store, runtime, node) => submitCandidateSelection(store, runtime, node, "candidate_001")],
    ["revision", (store, runtime, node) => submitCandidateRevision(store, runtime, node, "candidate_001", "Refine lighting.")],
  ]) {
    const node = nodeWithAuthority(variant);
    const context = makeStore(node);
    context.state.production = {};
    const before = JSON.stringify(context.state);
    let gets = 0;
    let posts = 0;
    let creates = 0;
    const result = await invoke(context.store, {
      getProductionRun: async () => { gets += 1; return { production_run: run }; },
      submitCreatorDecision: async () => { posts += 1; return {}; },
      createProductionRun: async () => { creates += 1; return {}; },
    }, node);
    reject(variant, consumer, result.ok === false && gets === 0 && posts === 0 && creates === 0
      && JSON.stringify(context.state) === before);
  }

  const restoreNode = nodeWithAuthority(variant);
  const restore = makeStore(restoreNode);
  const restoreBefore = JSON.stringify(restore.state);
  let restoreReads = 0;
  const restoreResult = await restoreCandidateSelection(restore.store, {
    getProductionRun: async () => { restoreReads += 1; return { production_run: run }; },
  }, restoreNode);
  reject(variant, "restore", restoreResult.ok === false && restoreReads === 0
    && JSON.stringify(restore.state) === restoreBefore);

  const refreshNode = nodeWithAuthority(variant);
  const refresh = makeStore(refreshNode);
  const refreshBefore = JSON.stringify(refresh.state);
  let refreshReads = 0;
  const refreshResult = await handleCandidateCreatorAction(refresh.store, {
    getProductionRun: async () => { refreshReads += 1; return { production_run: run }; },
  }, refreshNode, { dataset: { action: "candidate-refresh" }, closest: () => null });
  reject(variant, "refresh", refreshResult.ok === false && refreshReads === 0
    && JSON.stringify(refresh.state) === refreshBefore);

  const afterLoadNode = nodeWithAuthority(variant);
  const afterLoad = makeStore(afterLoadNode);
  const afterLoadBefore = JSON.stringify(afterLoad.state);
  let afterLoadReads = 0;
  const afterLoadResult = await restoreCandidateSelectionsAfterLoad(afterLoad.store, {
    getProductionRun: async () => { afterLoadReads += 1; return { production_run: run }; },
  });
  reject(variant, "after_load", afterLoadResult.skipped === "selection_target_unavailable"
    && afterLoadReads === 0 && JSON.stringify(afterLoad.state) === afterLoadBefore);

  const persistenceState = initialState("project-001");
  persistenceState.nodes = { "node-001": nodeWithAuthority(variant) };
  persistenceState.order = ["node-001"];
  const persisted = snapshotStudioState(persistenceState).nodes["node-001"].params.candidatePreviewUrls[0];
  reject(variant, "persistence", !persisted.image_asset_id && !persisted.reusable_asset_authority
    && (!variant.invalidRoute || variant.allowStoredPreview || (!persisted.preview_url && !persisted.url)));
}

const validFailures = [];
let validExecutions = 0;
function accept(consumer, condition) {
  validExecutions += 1;
  if (!condition) validFailures.push(consumer);
}
function validNode() {
  return {
    id: "node-001",
    type: "image",
    params: {
      lastKeyframeJobId: "job-001",
      uploads: [],
      creatorSelection: { run_id: "run-001", selected_parent_job_id: "job-001" },
      candidatePreviewUrls: [{ ...candidate, reusable_asset_authority: { ...authority } }],
    },
  };
}
const validResponse = {
  job: { job_id: "job-001", project_id: "project-001", status: "succeeded" },
  candidate_previews: [{ ...candidate, sha256: digest("a") }],
  reusable_image_assets: [{ ...authority }],
  safe_manifest: { output_count: 1 },
};
const selectedRun = { ...run };
const beforeRun = { ...run, selected_revision: null, creator_decisions: [], checkpoint: { version: 1, state_digest: digest("e") } };
const revisedRun = {
  ...run,
  selected_revision: {
    revision_id: "revision-002",
    canonical_digest: digest("f"),
    candidate_id: "candidate_001",
    candidate_digest: digest("a"),
  },
  creator_decisions: [...run.creator_decisions, { decision: "revise", candidate_id: "candidate_001", candidate_digest: digest("a") }],
  checkpoint: { version: 3, state_digest: digest("1") },
};

const validNormalized = candidatePreviewItems(validResponse)[0];
accept("normalize", validNormalized.image_asset_id === "asset-001"
  && validNormalized.reusable_asset_authority?.sha256 === digest("a"));

const validKeyframeNode = { id: "node-001", type: "image", params: { uploads: [], lastKeyframeJobId: "job-001" } };
const validKeyframe = makeStore(validKeyframeNode);
applyKeyframeResponse(validKeyframe.store, validKeyframeNode.id, validResponse, { aspect_ratio: "9:16" });
accept("keyframe", validKeyframeNode.params.candidatePreviewUrls[0].image_asset_id === "asset-001"
  && validKeyframeNode.params.uploads[0]?.asset_id === "asset-001"
  && validKeyframe.state.assets[0]?.asset_id === "asset-001");

const validDownstream = candidatePreviewsFromNode(validNode())[0];
accept("downstream", validDownstream.image_asset_id === "asset-001" && isCandidateSelectable(validDownstream));

const selectionNode = validNode();
const selection = makeStore(selectionNode);
let selectionReads = 0;
const selectionResult = await submitCandidateSelection(selection.store, {
  getProductionRun: async () => ({ production_run: ++selectionReads === 1 ? beforeRun : selectedRun }),
  submitCreatorDecision: async () => ({ idempotent_replay: false }),
}, selectionNode, "candidate_001");
accept("select", selectionResult.ok === true
  && selection.state.nodes[selectionNode.id].params.creatorSelection.selected_asset_id === "asset-001");

const revisionNode = validNode();
const revision = makeStore(revisionNode);
let revisionReads = 0;
const revisionResult = await submitCandidateRevision(revision.store, {
  getProductionRun: async () => ({ production_run: ++revisionReads === 1 ? selectedRun : revisedRun }),
  submitCreatorDecision: async () => ({ idempotent_replay: false }),
}, revisionNode, "candidate_001", "Refine lighting.");
accept("revision", revisionResult.ok === true
  && revision.state.nodes[revisionNode.id].params.creatorSelection.selected_revision_id === "revision-002");

const restoreNode = validNode();
const validRestore = makeStore(restoreNode);
const validRestoreResult = await restoreCandidateSelection(validRestore.store, {
  getProductionRun: async () => ({ production_run: selectedRun }),
}, restoreNode);
accept("restore", validRestoreResult.ok === true
  && validRestore.state.nodes[restoreNode.id].params.creatorSelection.selected_asset_id === "asset-001");

const refreshNode = validNode();
const validRefresh = makeStore(refreshNode);
const validRefreshResult = await handleCandidateCreatorAction(validRefresh.store, {
  getProductionRun: async () => ({ production_run: selectedRun }),
}, refreshNode, { dataset: { action: "candidate-refresh" }, closest: () => null });
accept("refresh", validRefreshResult.ok === true
  && validRefresh.state.nodes[refreshNode.id].params.creatorSelection.selected_asset_id === "asset-001");

const afterLoadNode = validNode();
const validAfterLoad = makeStore(afterLoadNode);
const validAfterLoadResult = await restoreCandidateSelectionsAfterLoad(validAfterLoad.store, {
  getProductionRun: async () => ({ production_run: selectedRun }),
});
accept("after_load", validAfterLoadResult.ok === true
  && validAfterLoad.state.nodes[afterLoadNode.id].params.creatorSelection.selected_asset_id === "asset-001");

const validPersistenceState = initialState("project-001");
validPersistenceState.nodes = { "node-001": validNode() };
validPersistenceState.order = ["node-001"];
const validPersisted = snapshotStudioState(validPersistenceState).nodes["node-001"].params.candidatePreviewUrls[0];
accept("persistence", validPersisted.image_asset_id === "asset-001"
  && validPersisted.reusable_asset_authority?.source_candidate_id === "candidate_001");

process.stdout.write(JSON.stringify({
  variants: variants.length,
  consumers: 9,
  executions,
  failures,
  validExecutions,
  validFailures,
}));
'''
    )

    assert payload == {
        "variants": 29,
        "consumers": 9,
        "executions": 261,
        "failures": [],
        "validExecutions": 9,
        "validFailures": [],
    }
