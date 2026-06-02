export function assetFromIncluded(item) {
  return {
    id: item.ref_id,
    label: item.ref_id,
    detail: item.summary || item.profile_kind || "included asset profile",
    status: "review ready",
  };
}

export function assetFromBlocked(item) {
  return {
    id: item.ref_id,
    label: item.ref_id,
    detail: item.reason || "blocked asset profile",
    status: "blocked",
  };
}

export function memoryFromIncluded(item) {
  return {
    id: item.ref_id,
    title: item.summary || item.ref_id,
    why_eligible: `explicit profile version ${item.source_version_id || "unknown"}`,
    source_evidence_refs: arrayValue(item.evidence_refs),
    promotion_status: item.profile_version || "included",
    request_projection: [
      ...arrayValue(item.allowed_variations).map((value) => `allow: ${value}`),
      ...arrayValue(item.negative_constraints).map((value) => `avoid: ${value}`),
    ].join(" / ") || "asset profile constraints available",
    feedback_effect: "included by profile version context projection; no durable memory or Company KB write",
    status: "review ready",
  };
}

export function controlsFromPayload(controls, labels) {
  const result = arrayValue(controls).map((item) => {
    const controlId = String(item?.control_id || "unknown_control");
    return {
      label: labels[controlId] || controlId.replaceAll("_", " "),
      status: item?.status === "passed" ? "review ready" : "blocked",
      detail: item?.status === "passed" ? "confirmed by selected artifact" : "requires operator attention",
    };
  });
  for (const [controlId, label] of Object.entries(labels)) {
    if (!result.some((item) => item.label === label)) {
      result.push({ label, status: "blocked", detail: `missing control ${controlId}` });
    }
  }
  return result;
}

export function boundaryItems(payload) {
  return arrayValue(payload.non_claims).map((item) => ({
    label: item,
    status: "blocked",
    detail: "non-claim boundary",
  }));
}

export function genericStatus(payload) {
  return payload.review_status
    || payload.projection_status
    || payload.candidate_generation_status
    || payload.decision_effect
    || payload.parse_status
    || payload.readiness_status
    || payload.package_status
    || payload.profile_status
    || "review ready";
}

export function action(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

export function card(id, title, status, detail) {
  return { id, title, status, detail };
}

export function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

export function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by selected artifact" : "not confirmed" };
}

export function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

export function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
