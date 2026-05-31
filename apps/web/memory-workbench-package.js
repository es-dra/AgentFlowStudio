import { MEMORY_PACKAGE_TYPE, PACKAGE_REFS } from "./memory-workbench-package-refs.js";

export function buildMemoryWorkbenchPackageView(workspace, fallback) {
  const artifact = workspace?.memoryPackage;
  if (!isMemoryPackageArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const bundle = memoryBundleFor(workspace);
  const review = artifactByType(bundle, "agentflow_memory_video_pipeline_review")?.payload || null;
  const observation = artifactByType(bundle, "agentflow_memory_video_pipeline_human_observation")?.payload || null;
  const presentation = artifactByType(bundle, "agentflow_memory_video_pipeline_presentation_package")?.payload || null;
  const feedback = artifactByType(bundle, "agentflow_feedback_event")?.payload || null;
  const bundleSummary = buildBundleSummary(payload, bundle);
  const refs = PACKAGE_REFS.filter(([key]) => payload[key]).map(([key, label, status, artifactType]) => ({
    id: key,
    title: label,
    why_eligible: `${key} is linked by the selected package`,
    source_evidence_refs: [String(payload[key])],
    promotion_status: "reviewed",
    request_projection: projectionForRef(label, artifactType, bundle),
    feedback_effect: key === "feedback_event_draft_ref" ? "can seed the next memory candidate review" : "keeps the workbench tied to package evidence",
    status: statusForRef(status, artifactType, bundle),
  }));
  const enrichedRefs = [...refs, ...bundleSummaryRefs({ review, observation, presentation, feedback })];

  return {
    ...fallback,
    state: payload.feedback_event_draft_ref ? "feedback captured" : "review ready",
    project: {
      title: String(payload.protocol_id || artifact.fileName),
      brief: "Selected local memory video pipeline package.",
      format: MEMORY_PACKAGE_TYPE,
      route: "selected local JSON package; no bridge or provider call",
    },
    workflow_actions: (fallback.workflow_actions || []).map((item) => ({
      ...item,
      status: actionStatus(item.id, payload, bundle),
    })),
    assets: refs.map((item) => ({
      id: item.id,
      label: item.title,
      detail: item.source_evidence_refs[0],
      status: item.status,
    })),
    bundle_summary: bundleSummary,
    memory_loaded: enrichedRefs.length ? enrichedRefs : fallback.memory_loaded,
    lanes: [
      {
        id: "baseline-lane",
        title: "Baseline Run",
        status: payload.review_ref ? "review ready" : "planned",
        input: "baseline lane evidence is referenced by the package review",
        output: laneSummary(review, "baseline") || payload.review_ref || "waiting for review artifact",
      },
      {
        id: "memory-lane",
        title: "Memory-backed Run",
        status: payload.review_ref ? "review ready" : "planned",
        input: "memory-backed lane evidence is referenced by the package review",
        output: laneSummary(review, "memory_backed") || payload.observation_ref || payload.presentation_ref || "waiting for memory evidence",
      },
    ],
    protocol_summary: buildProtocolSummary({ payload, review, presentation }),
    review: {
      storyboard_adherence: storyboardSummary(review) || payload.review_ref || "review artifact not selected",
      visual_consistency: observationSummary(observation) || payload.observation_ref || "observation artifact not selected",
      boundary: claimBoundary(payload.claim_boundaries),
    },
    feedback: {
      status: payload.feedback_event_draft_ref ? "feedback captured" : "planned",
      summary: feedbackSummary(feedback) || payload.feedback_event_draft_ref || "feedback event draft not selected",
    },
    next_pass: {
      status: payload.writes_long_term_memory === false ? "memory candidate drafted" : "blocked",
      action: payload.writes_long_term_memory === false
        ? "prepare promotion decision outside this static Web slice; not durable memory"
        : "blocked: package must not write durable memory from the browser",
    },
    timeline: fallback.timeline.map((item) => timelineItem(item.label, payload, item)),
  };
}

function buildProtocolSummary({ payload, review, presentation }) {
  const parity = review?.lane_parity || {};
  const sameForBoth = Array.isArray(presentation?.experiment_setup?.same_for_both_lanes)
    ? presentation.experiment_setup.same_for_both_lanes
    : [];
  return {
    title: "Baseline parity protocol",
    status: parity.only_memory_context_differs ? "review ready" : "planned",
    controls: [
      protocolItem("same task", parity.same_user_task, sameForBoth.includes("user_task") ? "presentation setup confirms same user task" : ""),
      protocolItem("same source assets", parity.same_source_assets, sameForBoth.includes("source_keyframe") ? "same source keyframe / assets" : ""),
      protocolItem("same provider route", parity.same_provider_route, sameForBoth.includes("provider_route") ? "same provider route" : ""),
      protocolItem("same duration", parity.same_duration, sameForBoth.includes("duration_sec") ? "same duration" : ""),
      protocolItem("same script/storyboard", parity.same_script, sameForBoth.includes("storyboard_checkpoints") ? "same storyboard checkpoints" : ""),
      protocolItem("only memory context differs", parity.only_memory_context_differs, "baseline is stateless; memory lane receives context projection"),
    ],
    boundaries: claimBoundaryItems(payload.claim_boundaries || review?.claim_boundaries || presentation?.claim_boundaries),
  };
}

function protocolItem(label, passed, detail) {
  return {
    label,
    status: passed ? "review ready" : "missing",
    detail: detail || (passed ? "confirmed by selected review artifact" : "not confirmed by selected artifacts"),
  };
}

function claimBoundaryItems(boundaries) {
  const source = boundaries || {};
  return [
    boundaryItem("human acceptance", source.human_acceptance || "not_acceptance"),
    boundaryItem("business validation", source.business_validation || "not_validated"),
    boundaryItem("quality improvement claim", source.quality_improvement_claim || "bounded_visual_signal_only"),
    boundaryItem("durable memory runtime", source.durable_memory_runtime || "not_implemented"),
  ];
}

function boundaryItem(label, value) {
  const normalized = String(value);
  return {
    label,
    status: normalized.includes("not_") ? "blocked" : "review ready",
    detail: normalized,
  };
}

function actionStatus(actionId, payload, bundle) {
  if (actionId === "load_package") return "review ready";
  if (actionId === "inspect_evidence") return artifactByType(bundle, "agentflow_memory_video_pipeline_review") ? "review ready" : "missing";
  if (actionId === "compare_lanes") return artifactByType(bundle, "agentflow_memory_video_pipeline_review") ? "review ready" : "planned";
  if (actionId === "capture_feedback") return artifactByType(bundle, "agentflow_feedback_event") || payload.feedback_event_draft_ref ? "feedback captured" : "planned";
  if (actionId === "prepare_next_pass") return payload.writes_long_term_memory === false ? "memory candidate drafted" : "blocked";
  return "planned";
}

function buildBundleSummary(payload, bundle) {
  const selectedTypes = new Set(bundle.map((artifact) => artifact.artifactType));
  return PACKAGE_REFS.map(([key, label, defaultStatus, artifactType]) => {
    const ref = payload[key];
    if (!ref) {
      return {
        id: key,
        title: label,
        status: "missing",
        detail: `${key} is not linked by the selected package`,
      };
    }
    if (!artifactType) {
      return {
        id: key,
        title: label,
        status: defaultStatus,
        detail: `${ref} is package metadata only; select the plan JSON separately when review detail is needed`,
      };
    }
    const selected = selectedTypes.has(artifactType);
    return {
      id: key,
      title: label,
      status: selected ? defaultStatus : "missing",
      detail: selected ? `${artifactType} selected explicitly` : `${ref} is referenced but not selected`,
    };
  });
}

function statusForRef(defaultStatus, artifactType, bundle) {
  if (!artifactType) return defaultStatus;
  return artifactByType(bundle, artifactType) ? defaultStatus : "missing";
}

function projectionForRef(label, artifactType, bundle) {
  if (!artifactType) return `${label} reference is listed by the selected package`;
  return artifactByType(bundle, artifactType)
    ? `${label} evidence is selected for operator inspection`
    : `${label} evidence is referenced only; select the JSON to inspect it`;
}

function isMemoryPackageArtifact(artifact) {
  return artifact?.artifactType === MEMORY_PACKAGE_TYPE && artifact?.payload?.artifact_type === MEMORY_PACKAGE_TYPE;
}

function memoryBundleFor(workspace) {
  return Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle : [];
}

function artifactByType(bundle, type) {
  return bundle.find((artifact) => artifact.artifactType === type);
}

function bundleSummaryRefs({ review, observation, presentation, feedback }) {
  const refs = [];
  if (review) {
    refs.push({
      id: "review_summary",
      title: "Review summary",
      why_eligible: "explicitly selected review artifact",
      source_evidence_refs: [review.artifact_type],
      promotion_status: "reviewed",
      request_projection: storyboardSummary(review),
      feedback_effect: "review checkpoints can guide the next pass",
      status: "review ready",
    });
  }
  if (observation) {
    refs.push({
      id: "observation_summary",
      title: "Observation summary",
      why_eligible: "explicitly selected human observation artifact",
      source_evidence_refs: [observation.artifact_type],
      promotion_status: "reviewed",
      request_projection: observationSummary(observation),
      feedback_effect: "bounded visual notes can become a memory candidate",
      status: "feedback captured",
    });
  }
  if (presentation) {
    refs.push({
      id: "presentation_summary",
      title: "Presentation summary",
      why_eligible: "explicitly selected presentation package",
      source_evidence_refs: [presentation.artifact_type],
      promotion_status: "reviewed",
      request_projection: presentation.one_sentence_takeaway || "presentation package selected",
      feedback_effect: "demo explanation stays tied to evidence boundaries",
      status: "review ready",
    });
  }
  if (feedback) {
    refs.push({
      id: "feedback_summary",
      title: "Feedback draft",
      why_eligible: "explicitly selected feedback event draft",
      source_evidence_refs: [feedback.artifact_type],
      promotion_status: feedback.draft_status || "draft",
      request_projection: feedbackSummary(feedback),
      feedback_effect: "draft remains not persisted until reviewed",
      status: "feedback captured",
    });
  }
  return refs;
}

function laneSummary(review, laneId) {
  if (!review) return "";
  const artifacts = Array.isArray(review.video_artifacts) ? review.video_artifacts : [];
  const runs = artifacts.filter((artifact) => artifact.lane_id === laneId);
  if (!runs.length) return "";
  const successCount = runs.filter((artifact) => String(artifact.status).toLowerCase() === "succeeded").length;
  return `${laneId}: ${runs.length} runs, ${successCount} succeeded`;
}

function storyboardSummary(review) {
  const checkpoints = Array.isArray(review?.storyboard?.shot_checkpoints) ? review.storyboard.shot_checkpoints : [];
  if (!checkpoints.length) return "";
  return `${review.storyboard.scene_id || "storyboard"}: ${checkpoints.length} checkpoints`;
}

function observationSummary(observation) {
  if (!observation) return "";
  const observations = Array.isArray(observation.observations) ? observation.observations : [];
  const verdictCounts = {};
  for (const item of observations) {
    const verdict = item?.verdict || "unknown";
    verdictCounts[verdict] = (verdictCounts[verdict] || 0) + 1;
  }
  const summary = Object.entries(verdictCounts).map(([verdict, count]) => `${verdict}: ${count}`).join(", ");
  return summary || observation.observation_status || "";
}

function feedbackSummary(feedback) {
  if (!feedback) return "";
  const tags = Array.isArray(feedback.reason_tags) ? feedback.reason_tags.join(", ") : "no reason tags";
  return `${feedback.draft_status || feedback.decision || "feedback"} | ${tags}`;
}

function timelineItem(label, payload, fallback) {
  if (label === "Project") return { label, status: "planned", detail: payload.protocol_id || fallback.detail };
  if (label === "Assets") return { label, status: payload.observation_ref ? "review ready" : "planned", detail: payload.observation_ref || fallback.detail };
  if (label === "Memory Loaded") return { label, status: payload.presentation_ref ? "review ready" : "planned", detail: payload.presentation_ref || fallback.detail };
  if (label === "Baseline Run") return { label, status: payload.review_ref ? "review ready" : "planned", detail: payload.review_ref || fallback.detail };
  if (label === "Memory-backed Run") return { label, status: payload.review_ref ? "review ready" : "planned", detail: payload.review_ref || fallback.detail };
  if (label === "Review") return { label, status: payload.review_ref ? "review ready" : "planned", detail: payload.review_ref || fallback.detail };
  if (label === "Feedback") return { label, status: payload.feedback_event_draft_ref ? "feedback captured" : "planned", detail: payload.feedback_event_draft_ref || fallback.detail };
  return { label, status: payload.writes_long_term_memory === false ? "memory candidate drafted" : "blocked", detail: "promotion decision remains outside this static browser slice" };
}

function claimBoundary(boundaries) {
  if (!boundaries) return "not_acceptance / not_validated / not_implemented";
  return [
    boundaries.human_acceptance || "not_acceptance",
    boundaries.business_validation || "not_validated",
    boundaries.durable_memory_runtime || "not_implemented",
  ].join(" / ");
}
