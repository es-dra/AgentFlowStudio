export function buildDemoReadyChecklist(view) {
  const bundle = Array.isArray(view.bundle_summary) ? view.bundle_summary : [];
  const protocol = view.protocol_summary || {};
  const controls = Array.isArray(protocol.controls) ? protocol.controls : [];
  const boundaries = Array.isArray(protocol.boundaries) ? protocol.boundaries : [];
  const feedback = view.feedback_draft || {};
  const source = checklistItem("source loaded", sourceReady(view.source_status), view.source_status?.detail || "fixture only");
  const selectedPackage = checklistItem("package selected", Boolean(view.project?.title), view.project?.title || "no package");
  const reviewEvidence = checklistItem("review evidence", itemReady(bundle, "review_ref"), detailFor(bundle, "review_ref"));
  const observationNotes = checklistItem("observation notes", itemReady(bundle, "observation_ref"), detailFor(bundle, "observation_ref"));
  const presentationSummary = checklistItem("presentation summary", itemReady(bundle, "presentation_ref"), detailFor(bundle, "presentation_ref"));
  const laneParity = checklistItem("lane parity", parityReady(controls), parityDetail(controls));
  const feedbackDraft = checklistItem("feedback draft", feedbackReady(feedback), feedback.detail || "no feedback draft");
  const claimBoundaries = checklistItem("claim boundaries visible", boundaries.length >= 3, `${boundaries.length} boundaries shown`);
  const items = [
    source,
    selectedPackage,
    reviewEvidence,
    observationNotes,
    presentationSummary,
    laneParity,
    feedbackDraft,
    claimBoundaries,
  ];
  const requiredItems = [source, reviewEvidence, observationNotes, presentationSummary, laneParity, feedbackDraft];
  const readyCount = requiredItems.filter((item) => isReady(item.status)).length;
  const boundaryItems = boundaries.map((item) => ({
    label: item.label,
    status: item.status || "blocked",
    detail: item.detail,
  }));

  return {
    title: "Demo-ready checklist",
    status: checklistStatus(requiredItems.map((item) => isReady(item.status))),
    summary: {
      ready_count: readyCount,
      total_count: requiredItems.length,
      gap_count: requiredItems.length - readyCount,
      boundary_count: boundaryItems.length,
      headline: readyCount === requiredItems.length ? "Demo can be rehearsed" : "Evidence gaps remain",
    },
    items,
    groups: [
      {
        id: "speakable",
        title: "可讲内容",
        detail: "用于路演时直接解释当前 demo 依据。",
        status: checklistStatus([isReady(source.status), isReady(laneParity.status), isReady(feedbackDraft.status)]),
        items: [source, selectedPackage, laneParity, feedbackDraft],
      },
      {
        id: "gaps",
        title: "待补缺口",
        detail: "决定这次演示是否有足够证据支撑。",
        status: checklistStatus([isReady(reviewEvidence.status), isReady(observationNotes.status), isReady(presentationSummary.status)]),
        items: [reviewEvidence, observationNotes, presentationSummary],
      },
      {
        id: "non-claims",
        title: "禁止宣称",
        detail: "这些边界必须一直可见，避免把 demo 说成验收或商业验证。",
        status: boundaries.length >= 3 ? "blocked" : "missing",
        items: boundaryItems.length ? boundaryItems : [claimBoundaries],
      },
    ],
  };
}

function checklistStatus(items) {
  return items.every(Boolean) ? "review ready" : "planned";
}

function checklistItem(label, ready, detail) {
  return {
    label,
    status: ready ? "review ready" : "planned",
    detail,
  };
}

function isReady(status) {
  return status === "review ready" || status === "feedback captured";
}

function sourceReady(source) {
  return ["review ready", "feedback captured"].includes(source?.status);
}

function itemReady(bundle, id) {
  return bundle.some((item) => item.id === id && !["missing", "blocked"].includes(item.status));
}

function detailFor(bundle, id) {
  return bundle.find((item) => item.id === id)?.detail || `${id} not loaded`;
}

function parityReady(controls) {
  return controls.some((item) => item.label === "only memory context differs" && item.status === "review ready");
}

function parityDetail(controls) {
  const ready = controls.filter((item) => item.status === "review ready").length;
  return `${ready}/${controls.length} parity controls ready`;
}

function feedbackReady(feedback) {
  return feedback.copy_enabled === true && feedback.status === "draft_not_persisted";
}
