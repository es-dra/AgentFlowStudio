from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.studio_production_delivery_browser_qa import prepare_provider_free_delivery_qa


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


def test_production_delivery_panel_is_wired_to_quality_and_exact_export_actions() -> None:
    result_view = (STUDIO / "src" / "node-result-view.js").read_text(encoding="utf-8")
    action_handler = (STUDIO / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "node-result.css").read_text(encoding="utf-8")

    assert 'from "./production-delivery-view.js"' in result_view
    assert "productionDeliveryView(node, candidates)" in result_view
    assert 'from "./production-delivery-controller.js"' in action_handler
    assert 'action === "production-quality-approve"' in action_handler
    assert 'action === "production-export"' in action_handler
    assert ".production-delivery-panel" in styles
    assert "@media (max-width: 520px)" in styles


def test_representative_episode_binding_summary_requires_exact_authoritative_inventory() -> None:
    payload = _node_json(
        r'''
import { representativeEpisodeBindingSummary } from "./apps/studio/src/production-delivery-controller.js";

const digest = (char) => char.repeat(64);
const entityRefs = (prefix, count) => Array.from({ length: count }, (_, index) => ({
  entity_id: `${prefix}-${String(index + 1).padStart(3, "0")}`,
  current_approved_version_id: `${prefix}-${String(index + 1).padStart(3, "0")}-v1`,
}));
const assetRefs = Array.from({ length: 25 }, (_, index) => ({
  asset_id: `asset-${String(index + 1).padStart(3, "0")}`,
  current_revision_id: `asset-${String(index + 1).padStart(3, "0")}-rev-001`,
  status: "missing",
  provider_needed: true,
}));
const binding = {
  package_sha256: digest("a"),
  binding_digest: digest("b"),
  episode_id: "ep-rainlight-001",
  episode_version_id: "ep-rainlight-001-v1",
  character_refs: entityRefs("character", 3),
  scene_refs: entityRefs("scene", 3),
  shot_refs: entityRefs("shot", 15),
  asset_refs: assetRefs,
  counts: { characters: 3, scenes: 3, shots: 15, assets: 25 },
  asset_readiness: { ready_count: 0, pending_media_count: 25, provider_needed_count: 25, all_assets_ready: false },
  creator_decision_ref: "creator-decision-episode-v1",
  propagation_complete: false,
  lineage: [
    { source_ref: digest("a"), target_ref: "ep-rainlight-001-v1", relation: "package_defined_episode_version" },
    { source_ref: "creator-decision-episode-v1", target_ref: "ep-rainlight-001-v1", relation: "creator_decision_approved_episode_version" },
  ],
};
const summary = representativeEpisodeBindingSummary({ representative_episode_binding: binding });
const failures = {};
for (const [name, mutate] of Object.entries({
  incompleteShots(value) { value.shot_refs.pop(); },
  staleCounts(value) { value.counts.shots = 14; },
  readinessDrift(value) { value.asset_readiness.pending_media_count = 24; },
  missingProviderGate(value) { value.asset_refs[0].provider_needed = false; },
})) {
  const candidate = structuredClone(binding);
  mutate(candidate);
  try { representativeEpisodeBindingSummary({ representative_episode_binding: candidate }); }
  catch (error) { failures[name] = error.code; }
}
process.stdout.write(JSON.stringify({ summary, failures }));
'''
    )

    assert payload["summary"] == {
        "authoritative_source": "runtime_production_run_checkpoint",
        "package_sha256": "a" * 64,
        "binding_digest": "b" * 64,
        "episode_id": "ep-rainlight-001",
        "episode_version_id": "ep-rainlight-001-v1",
        "character_count": 3,
        "scene_count": 3,
        "shot_count": 15,
        "asset_count": 25,
        "pending_media_count": 25,
        "provider_needed_count": 25,
        "all_assets_ready": False,
        "creator_decision_ref": "creator-decision-episode-v1",
        "propagation_complete": False,
        "lineage": [
            {
                "source_ref": "a" * 64,
                "target_ref": "ep-rainlight-001-v1",
                "relation": "package_defined_episode_version",
            },
            {
                "source_ref": "creator-decision-episode-v1",
                "target_ref": "ep-rainlight-001-v1",
                "relation": "creator_decision_approved_episode_version",
            },
        ],
    }
    assert payload["failures"] == {
        "incompleteShots": "delivery_episode_shot_refs_invalid",
        "staleCounts": "delivery_episode_counts_invalid",
        "readinessDrift": "delivery_episode_readiness_invalid",
        "missingProviderGate": "delivery_episode_provider_gate_invalid",
    }


def test_studio_delivery_displays_exact_representative_episode_checkpoint_summary() -> None:
    payload = _node_json(
        r'''
import { productionDeliveryView } from "./apps/studio/src/production-delivery-view.js";

function makeElement(tagName) {
  const element = {
    tagName: String(tagName || "").toUpperCase(), children: [], dataset: {}, attributes: {}, className: "",
    title: "", disabled: false, checked: false, textContent: "",
    appendChild(child) { this.children.push(child); return child; },
    append(...children) { children.forEach((child) => this.appendChild(child)); },
    setAttribute(name, value) { this.attributes[name] = String(value); },
  };
  Object.defineProperty(element, "innerText", { get() {
    return [this.textContent, ...this.children.map((child) => child.innerText || child.textContent || "")]
      .filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }});
  return element;
}
function findBinding(element) {
  if (element?.dataset?.representativeEpisodeBinding === "true") return element;
  for (const child of element?.children || []) { const found = findBinding(child); if (found) return found; }
  return null;
}
globalThis.document = { createElement: makeElement };
const digest = (char) => char.repeat(64);
const authority = {
  run_id: "production-run-001", selected_candidate_id: "candidate-001", selected_candidate_digest: digest("c"),
  selected_revision_id: "revision-001", selected_revision_digest: digest("d"), selected_parent_job_id: "job-001",
};
const node = { id: "node-001", params: {
  creatorSelection: authority,
  productionDelivery: {
    status: "ready", run_id: authority.run_id, selected_candidate_id: authority.selected_candidate_id,
    selected_candidate_digest: authority.selected_candidate_digest, selected_revision_id: authority.selected_revision_id,
    selected_revision_digest: authority.selected_revision_digest, parent_job_id: authority.selected_parent_job_id,
    representative_episode: {
      authoritative_source: "runtime_production_run_checkpoint", package_sha256: digest("a"), binding_digest: digest("b"),
      episode_id: "ep-rainlight-001", episode_version_id: "ep-rainlight-001-v1", character_count: 3,
      scene_count: 3, shot_count: 15, asset_count: 25, pending_media_count: 25, provider_needed_count: 25,
      all_assets_ready: false, creator_decision_ref: "creator-decision-episode-v1", propagation_complete: false,
      lineage: [{}, {}],
    },
  },
}};
const panel = productionDeliveryView(node, [{ candidate_id: "candidate-001" }, { candidate_id: "candidate-002" }]);
const binding = findBinding(panel);
process.stdout.write(JSON.stringify({ text: binding?.innerText || "", titles: (binding?.children || []).map((item) => item.title).filter(Boolean) }));
'''
    )

    assert "ep-rainlight-001" in payload["text"]
    assert "ep-rainlight-001-v1" in payload["text"]
    assert "3 characters / 3 scenes / 15 shots / 25 assets" in payload["text"]
    assert "25" in payload["text"]
    assert "pending reconfirmation" in payload["text"]
    assert "2 authoritative refs" in payload["text"]
    assert "a" * 64 in payload["titles"]
    assert "b" * 64 in payload["titles"]


def test_stale_delivery_authority_cannot_render_current_approval_or_enable_export() -> None:
    payload = _node_json(
        r'''
import { productionDeliveryView } from "./apps/studio/src/production-delivery-view.js";

function makeElement(tagName) {
  const element = {
    tagName: String(tagName || "").toUpperCase(),
    children: [],
    dataset: {},
    attributes: {},
    className: "",
    title: "",
    disabled: false,
    checked: false,
    textContent: "",
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    append(...children) {
      children.forEach((child) => this.appendChild(child));
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
  };
  Object.defineProperty(element, "innerText", {
    get() {
      return [this.textContent, ...this.children.map((child) => child.innerText || child.textContent || "")]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();
    },
  });
  return element;
}

function findByAction(element, action) {
  if (element?.dataset?.action === action) return element;
  for (const child of element?.children || []) {
    const found = findByAction(child, action);
    if (found) return found;
  }
  return null;
}

globalThis.document = { createElement: makeElement };
const digest = (char) => char.repeat(64);
const node = {
  id: "node-001",
  params: {
    creatorSelection: {
      run_id: "run-current",
      selected_candidate_id: "candidate-002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      selected_parent_job_id: "job-current",
    },
    productionDelivery: {
      status: "approved",
      run_id: "run-historical",
      selected_candidate_id: "candidate-002",
      selected_candidate_digest: digest("d"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      parent_job_id: "job-historical",
      quality_decision: "approve",
      message: "质量门禁已通过：这是旧审批，不得显示为当前审批。",
    },
  },
};
const panel = productionDeliveryView(node, [{ candidate_id: "candidate-001" }, { candidate_id: "candidate-002" }]);
const exportButton = findByAction(panel, "production-export");
process.stdout.write(JSON.stringify({
  exportDisabled: exportButton?.disabled,
  text: panel?.innerText || "",
}));
'''
    )

    assert payload["exportDisabled"] is True
    assert "质量门禁已通过" not in payload["text"]


def test_delivery_approval_requires_a_complete_valid_canonical_authority_tuple() -> None:
    payload = _node_json(
        r'''
import { productionDeliveryView } from "./apps/studio/src/production-delivery-view.js";

function makeElement(tagName) {
  const element = {
    tagName: String(tagName || "").toUpperCase(),
    children: [],
    dataset: {},
    attributes: {},
    disabled: false,
    checked: false,
    textContent: "",
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    append(...children) {
      children.forEach((child) => this.appendChild(child));
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
  };
  Object.defineProperty(element, "innerText", {
    get() {
      return [this.textContent, ...this.children.map((child) => child.innerText || child.textContent || "")]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();
    },
  });
  return element;
}

function findByAction(element, action) {
  if (element?.dataset?.action === action) return element;
  for (const child of element?.children || []) {
    const found = findByAction(child, action);
    if (found) return found;
  }
  return null;
}

globalThis.document = { createElement: makeElement };
const digest = (char) => char.repeat(64);
const baseNode = {
  id: "node-001",
  params: {
    creatorSelection: {
      run_id: "run-001",
      selected_candidate_id: "candidate-002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      selected_parent_job_id: "job-001",
    },
    productionDelivery: {
      status: "approved",
      run_id: "run-001",
      selected_candidate_id: "candidate-002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      parent_job_id: "job-001",
      quality_decision: "approve",
      quality_review_id: "quality-review-001",
      last_export_id: "export-001",
      delivery_sha256: digest("7"),
      message: "质量门禁已通过",
    },
  },
};
const candidates = [{ candidate_id: "candidate-001" }, { candidate_id: "candidate-002" }];

function inspect(node) {
  const panel = productionDeliveryView(node, candidates);
  return {
    approveDisabled: findByAction(panel, "production-quality-approve")?.disabled,
    exportDisabled: findByAction(panel, "production-export")?.disabled,
    showsApproval: (panel?.innerText || "").includes("质量门禁已通过"),
    showsDeliveryRecord: (panel?.innerText || "").includes("quality-review-001")
      || (panel?.innerText || "").includes("export-001"),
  };
}

const scenarios = {
  missing_run_id(selection, delivery) {
    delete selection.run_id;
    delete delivery.run_id;
  },
  missing_parent_job_id(selection, delivery) {
    delete selection.selected_parent_job_id;
    delete delivery.parent_job_id;
  },
  missing_candidate_id(selection, delivery) {
    delete selection.selected_candidate_id;
    delete delivery.selected_candidate_id;
  },
  missing_candidate_digest(selection, delivery) {
    delete selection.selected_candidate_digest;
    delete delivery.selected_candidate_digest;
  },
  missing_revision_id(selection, delivery) {
    delete selection.selected_revision_id;
    delete delivery.selected_revision_id;
  },
  missing_revision_digest(selection, delivery) {
    delete selection.selected_revision_digest;
    delete delivery.selected_revision_digest;
  },
  blank_run_id(selection, delivery) {
    selection.run_id = "   ";
    delivery.run_id = "   ";
  },
  null_parent_job_id(selection, delivery) {
    selection.selected_parent_job_id = null;
    delivery.parent_job_id = null;
  },
  non_scalar_candidate_id(selection, delivery) {
    selection.selected_candidate_id = { value: "candidate-002" };
    delivery.selected_candidate_id = { value: "candidate-002" };
  },
  invalid_revision_id(selection, delivery) {
    selection.selected_revision_id = "revision id with spaces";
    delivery.selected_revision_id = "revision id with spaces";
  },
  invalid_candidate_digest(selection, delivery) {
    selection.selected_candidate_digest = "not-a-sha256";
    delivery.selected_candidate_digest = "not-a-sha256";
  },
};

const results = {};
for (const [name, mutate] of Object.entries(scenarios)) {
  const node = structuredClone(baseNode);
  mutate(node.params.creatorSelection, node.params.productionDelivery);
  results[name] = inspect(node);
}
process.stdout.write(JSON.stringify({ baseline: inspect(baseNode), results }));
'''
    )

    assert payload["baseline"] == {
        "approveDisabled": True,
        "exportDisabled": False,
        "showsApproval": True,
        "showsDeliveryRecord": True,
    }
    assert set(payload["results"]) == {
        "missing_run_id",
        "missing_parent_job_id",
        "missing_candidate_id",
        "missing_candidate_digest",
        "missing_revision_id",
        "missing_revision_digest",
        "blank_run_id",
        "null_parent_job_id",
        "non_scalar_candidate_id",
        "invalid_revision_id",
        "invalid_candidate_digest",
    }
    for name, result in payload["results"].items():
        assert result == {
            "approveDisabled": True,
            "exportDisabled": True,
            "showsApproval": False,
            "showsDeliveryRecord": False,
        }, name


def test_quality_approval_and_export_bind_exact_selected_revision_and_fail_closed() -> None:
    payload = _node_json(
        r'''
import {
  buildProductionExportRequest,
  buildQualityApprovalRequest,
  productionDeliveryAuthority,
} from "./apps/studio/src/production-delivery-controller.js";

const digest = (char) => char.repeat(64);
const candidate = (id, char) => ({
  candidate_id: id,
  canonical_digest: digest(char),
  parent_job_id: "job-001",
  preview_url: `/projects/project-001/keyframe-generations/job-001/candidates/${id}/preview`,
  status: "succeeded",
});
const node = {
  id: "node-001",
  type: "image",
  params: {
    lastKeyframeJobId: "job-001",
    candidatePreviewUrls: [candidate("candidate-001", "b"), candidate("candidate-002", "c")],
    creatorSelection: {
      status: "persisted",
      run_id: "run-001",
      selected_candidate_id: "candidate-002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      selected_parent_job_id: "job-001",
      checkpoint_version: 2,
    },
  },
};
const run = {
  run_id: "run-001",
  subject_digest: digest("a"),
  checkpoint: { version: 2, state_digest: digest("f") },
  candidates: [candidate("candidate-001", "b"), candidate("candidate-002", "c")],
  selected_revision: {
    revision_id: "revision-002",
    canonical_digest: digest("e"),
    candidate_id: "candidate-002",
    candidate_digest: digest("c"),
    parent_job_id: "job-001",
    subject_digest: digest("a"),
  },
  quality_reviews: [],
  exports: [],
};
const authority = productionDeliveryAuthority(run, node);
const quality = buildQualityApprovalRequest(run, node, {
  reviewId: "quality-review-001",
  idempotencyKey: "quality-review-001",
  checklist: {
    story_intent_preserved: true,
    character_continuity_checked: true,
    shot_coverage_checked: true,
    revision_addressed: true,
  },
});
const reviewed = {
  ...run,
  checkpoint: { version: 3, state_digest: digest("9") },
  quality_reviews: [{
    review_id: "quality-review-001",
    selected_revision_id: "revision-002",
    selected_revision_digest: digest("e"),
    decision: "approve",
    human_acceptance_claimed: false,
  }],
};
const exported = buildProductionExportRequest(reviewed, node, {
  exportId: "export-001",
  idempotencyKey: "export-001",
});
const failures = {};
for (const [name, mutate] of Object.entries({
  unselected: (value) => { delete value.params.creatorSelection.selected_candidate_id; },
  stale_candidate: (value) => { value.params.creatorSelection.selected_candidate_id = "candidate-001"; },
  stale_revision: (value) => { value.params.creatorSelection.selected_revision_id = "revision-old"; },
  stale_lineage: (value) => { value.params.lastKeyframeJobId = "job-new"; },
})) {
  const changed = structuredClone(node);
  mutate(changed);
  try {
    productionDeliveryAuthority(reviewed, changed);
    failures[name] = null;
  } catch (error) {
    failures[name] = error.code;
  }
}
const unreviewed = (() => {
  try {
    buildProductionExportRequest(run, node, { exportId: "export-blocked", idempotencyKey: "export-blocked" });
    return null;
  } catch (error) {
    return error.code;
  }
})();
process.stdout.write(JSON.stringify({ authority, quality, exported, failures, unreviewed }));
'''
    )

    assert payload["authority"] == {
        "run_id": "run-001",
        "candidate_id": "candidate-002",
        "candidate_digest": "c" * 64,
        "revision_id": "revision-002",
        "revision_digest": "e" * 64,
        "parent_job_id": "job-001",
        "checkpoint_version": 2,
    }
    assert payload["quality"]["expected_checkpoint_version"] == 2
    assert payload["quality"]["reviewed_subject_digest"] == "a" * 64
    assert payload["quality"]["selected_revision_id"] == "revision-002"
    assert payload["quality"]["selected_revision_digest"] == "e" * 64
    assert payload["quality"]["decision"] == "approve"
    assert payload["quality"]["checklist"] == {
        "story_intent_preserved": True,
        "character_continuity_checked": True,
        "shot_coverage_checked": True,
        "revision_addressed": True,
    }
    assert payload["exported"] == {
        "schema_version": "afs_production_export.v0.1",
        "export_id": "export-001",
        "idempotency_key": "export-001",
        "expected_checkpoint_version": 3,
        "selected_revision_id": "revision-002",
        "selected_revision_digest": "e" * 64,
    }
    assert payload["failures"] == {
        "unselected": "delivery_selection_missing",
        "stale_candidate": "delivery_candidate_stale",
        "stale_revision": "delivery_revision_stale",
        "stale_lineage": "delivery_lineage_stale",
    }
    assert payload["unreviewed"] == "delivery_quality_required"


def test_delivery_actions_use_authoritative_readback_and_never_post_stale_export() -> None:
    payload = _node_json(
        r'''
import { handleProductionDeliveryAction } from "./apps/studio/src/production-delivery-controller.js";

const digest = (char) => char.repeat(64);
const proof = (id, char, assetId) => ({
  schema_version: "afs_studio_reusable_asset_authority.v0.1",
  asset_id: assetId,
  role: "generated_keyframe_reference",
  source_kind: "keyframe_candidate",
  source_job_id: "job-001",
  source_candidate_id: id,
  source_candidate_digest: digest(char),
  sha256: digest(char),
  status: "succeeded",
});
const visible = (id, char, assetId) => ({
  candidate_id: id,
  canonical_digest: digest(char),
  parent_job_id: "job-001",
  project_id: "project-001",
  preview_url: `/projects/project-001/keyframe-generations/job-001/candidates/${id}/preview`,
  status: "succeeded",
  reusable_asset_authority: proof(id, char, assetId),
});
const runCandidate = (id, char) => ({
  candidate_id: id,
  canonical_digest: digest(char),
  parent_job_id: "job-001",
  status: "succeeded",
});
const makeNode = () => ({
  id: "node-001",
  type: "image",
  params: {
    lastKeyframeJobId: "job-001",
    uploads: [],
    candidatePreviewUrls: [visible("candidate_001", "b", "asset-001"), visible("candidate_002", "c", "asset-002")],
    creatorSelection: {
      status: "persisted",
      run_id: "run-001",
      selected_candidate_id: "candidate_002",
      selected_candidate_digest: digest("c"),
      selected_revision_id: "revision-002",
      selected_revision_digest: digest("e"),
      selected_parent_job_id: "job-001",
      checkpoint_version: 2,
    },
  },
});
const revision = {
  revision_id: "revision-002",
  canonical_digest: digest("e"),
  candidate_id: "candidate_002",
  candidate_digest: digest("c"),
  parent_job_id: "job-001",
  subject_digest: digest("a"),
};
const base = {
  run_id: "run-001",
  subject_digest: digest("a"),
  checkpoint: { version: 2, state_digest: digest("f") },
  candidates: [runCandidate("candidate_001", "b"), runCandidate("candidate_002", "c")],
  selected_revision: revision,
  creator_decisions: [{ decision: "select", candidate_id: "candidate_002", candidate_digest: digest("c") }],
  quality_reviews: [],
  exports: [],
};
const review = {
  review_id: "quality-review-001",
  selected_revision_id: "revision-002",
  selected_revision_digest: digest("e"),
  decision: "approve",
  human_acceptance_claimed: false,
};
const reviewed = { ...base, checkpoint: { version: 3, state_digest: digest("9") }, quality_reviews: [review] };
const exportRecord = {
  export_id: "export-001",
  selected_revision_id: "revision-002",
  selected_revision_digest: digest("e"),
  delivery_sha256: digest("7"),
};
const exported = { ...reviewed, status: "exported", checkpoint: { version: 4, state_digest: digest("8") }, exports: [exportRecord] };

function makeStore(node) {
  const state = { production: { active_run_id: "run-001" }, nodes: { [node.id]: node }, assets: [] };
  return {
    state,
    store: {
      get: () => state,
      set: (mutator) => mutator(state),
      flushRuntimeSave: async () => {},
    },
  };
}
function panel() {
  const status = { dataset: {}, textContent: "" };
  const checks = new Map([
    ["story_intent_preserved", { checked: true }],
    ["character_continuity_checked", { checked: true }],
    ["shot_coverage_checked", { checked: true }],
    ["revision_addressed", { checked: true }],
  ]);
  return {
    dataset: {},
    status,
    setAttribute: () => {},
    querySelectorAll: () => [],
    querySelector: (selector) => {
      if (selector === "[data-production-delivery-status]") return status;
      const match = selector.match(/data-delivery-check="([^"]+)"/);
      return match ? checks.get(match[1]) : null;
    },
  };
}
function action(name, value) {
  return { dataset: { action: name }, closest: () => value };
}

const happy = makeStore(makeNode());
const qualityPanel = panel();
let qualityReads = 0;
let qualityRequest = null;
const qualityResult = await handleProductionDeliveryAction(happy.store, {
  getProductionRun: async () => ({ production_run: ++qualityReads === 1 ? base : reviewed }),
  recordProductionQualityReview: async (_runId, request) => { qualityRequest = request; return {}; },
}, happy.state.nodes["node-001"], action("production-quality-approve", qualityPanel));

const exportPanel = panel();
let exportReads = 0;
let exportRequest = null;
const exportResult = await handleProductionDeliveryAction(happy.store, {
  getProductionRun: async () => ({ production_run: ++exportReads === 1 ? reviewed : exported }),
  exportProductionRun: async (_runId, request) => { exportRequest = request; return { export: exportRecord }; },
}, happy.state.nodes["node-001"], action("production-export", exportPanel));

const stale = makeStore(makeNode());
stale.state.nodes["node-001"].params.lastKeyframeJobId = "job-new";
let stalePosts = 0;
const staleResult = await handleProductionDeliveryAction(stale.store, {
  getProductionRun: async () => ({ production_run: reviewed }),
  exportProductionRun: async () => { stalePosts += 1; return {}; },
}, stale.state.nodes["node-001"], action("production-export", panel()));

const unselected = makeStore(makeNode());
delete unselected.state.nodes["node-001"].params.creatorSelection.run_id;
let unselectedReads = 0;
let unselectedPosts = 0;
const unselectedResult = await handleProductionDeliveryAction(unselected.store, {
  getProductionRun: async () => { unselectedReads += 1; return { production_run: reviewed }; },
  exportProductionRun: async () => { unselectedPosts += 1; return {}; },
}, unselected.state.nodes["node-001"], action("production-export", panel()));

process.stdout.write(JSON.stringify({
  qualityResult,
  qualityRequest,
  exportResult,
  exportRequest,
  delivery: happy.state.nodes["node-001"].params.productionDelivery,
  production: happy.state.production,
  staleResult,
  stalePosts,
  unselectedResult,
  unselectedReads,
  unselectedPosts,
}));
'''
    )

    assert payload["qualityResult"]["ok"] is True, payload
    assert payload["qualityRequest"]["decision"] == "approve"
    assert payload["qualityRequest"]["selected_revision_id"] == "revision-002"
    assert payload["exportResult"]["ok"] is True
    assert payload["exportRequest"]["expected_checkpoint_version"] == 3
    assert payload["exportRequest"]["selected_revision_id"] == "revision-002"
    assert payload["delivery"]["status"] == "exported"
    assert payload["delivery"]["last_export_id"] == "export-001"
    assert payload["delivery"]["delivery_sha256"] == "7" * 64
    assert payload["production"]["selected_candidate_id"] == "candidate_002"
    assert payload["production"]["selected_revision_id"] == "revision-002"
    assert payload["production"]["last_export_id"] == "export-001"
    assert payload["staleResult"]["code"] == "delivery_lineage_stale"
    assert payload["stalePosts"] == 0
    assert payload["unselectedResult"]["code"] == "delivery_selection_missing"
    assert payload["unselectedReads"] == 0
    assert payload["unselectedPosts"] == 0


def test_provider_free_authenticated_browser_fixture_restores_candidate_authority(tmp_path: Path) -> None:
    seed = prepare_provider_free_delivery_qa(tmp_path)

    assert seed["candidate_count"] == 2
    assert seed["selected_candidate_id"] == "candidate_002"
    assert str(seed["selected_revision_id"]).startswith("revision-")
    assert seed["provider_calls_started"] is False
    assert seed["evidence_boundary"] == "provider-free deterministic UI/runtime verification only"
    assert seed["browser_preflight"] == {
        "ready": True,
        "missing_candidate_authority_fields": [],
        "persisted_candidate_count": 2,
        "stop_reason": "",
    }

    from apps.api.runtime_service import create_runtime_app
    from fastapi.testclient import TestClient

    with _seed_auth_environment(), TestClient(create_runtime_app(runtime_root=tmp_path)) as client:
        login = client.post(
            "/auth/login",
            json={"email": seed["email"], "password": seed["password"]},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['session_token']}"}
        run = client.get(
            f"/projects/{seed['project_id']}/production-runs/{seed['run_id']}",
            headers=headers,
        )
        state = client.get(f"/projects/{seed['project_id']}/studio-state", headers=headers)

    assert run.status_code == 200
    assert run.json()["production_run"]["selected_revision"]["candidate_id"] == "candidate_002"
    assert run.json()["production_run"]["quality_reviews"] == []
    candidates = state.json()["state"]["nodes"][seed["node_id"]]["params"]["candidatePreviewUrls"]
    assert len(candidates) == 2
    assert all(item["preview_url"].endswith("/preview") for item in candidates)
    assert all(len(item["canonical_digest"]) == 64 for item in candidates)
    assert all(item["parent_job_id"] == seed["job_id"] for item in candidates)
    assert all(item["project_id"] == seed["project_id"] for item in candidates)
    assert all(
        item["reusable_asset_authority"]["source_candidate_id"] == item["candidate_id"]
        and item["reusable_asset_authority"]["source_candidate_digest"] == item["canonical_digest"]
        for item in candidates
    )


class _seed_auth_environment:
    def __enter__(self):
        import os

        self.before = {key: os.environ.get(key) for key in ("AFS_AUTH_ENABLED", "AFS_INVITE_CODES")}
        os.environ["AFS_AUTH_ENABLED"] = "true"
        os.environ["AFS_INVITE_CODES"] = "delivery-qa-invite"
        return self

    def __exit__(self, *_args):
        import os

        for key, value in self.before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
