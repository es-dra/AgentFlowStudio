export function buildDemoEvidenceSummary(view) {
  if (isOperatorReadinessView(view)) return buildOperatorReadinessSummary(view);

  const protocol = view.protocol_summary || {};
  const controls = Array.isArray(protocol.controls) ? protocol.controls : [];
  const boundaries = Array.isArray(protocol.boundaries) ? protocol.boundaries : [];
  const lanes = Array.isArray(view.lanes) ? view.lanes : [];
  const memoryLane = lanes.find((lane) => lane.id === "memory-lane") || lanes[1] || {};
  const baselineLane = lanes.find((lane) => lane.id === "baseline-lane") || lanes[0] || {};
  const parityReady = controls.some((item) => item.label === "only memory context differs" && item.status === "review ready");

  return {
    title: "Demo Evidence Summary",
    status: parityReady ? "review ready" : "planned",
    talk_track: [
      "Same task, assets, route, duration, and storyboard are held constant.",
      "Baseline stays stateless; memory-backed receives reusable context projection.",
      "Feedback becomes a next-pass draft, not durable memory or product validation.",
    ],
    evidence_cards: [
      {
        label: "Experiment setup",
        status: protocol.status || "planned",
        detail: parityReady ? "Lane parity is reviewable from selected artifacts." : "Select review and presentation artifacts for parity evidence.",
      },
      {
        label: "Observed signal",
        status: view.review?.storyboard_adherence ? "review ready" : "planned",
        detail: view.review?.visual_consistency || memoryLane.output || "Memory-backed lane signal not loaded.",
      },
      {
        label: "Reuse path",
        status: view.feedback?.status || "planned",
        detail: view.next_pass?.action || "Feedback draft not loaded.",
      },
    ],
    comparison: [
      {
        label: "Baseline",
        status: baselineLane.status || "planned",
        detail: baselineLane.output || baselineLane.input || "Baseline lane not loaded.",
      },
      {
        label: "Memory-backed",
        status: memoryLane.status || "planned",
        detail: memoryLane.output || memoryLane.input || "Memory-backed lane not loaded.",
      },
    ],
    non_claims: boundaries.map((item) => ({
      label: item.label,
      status: item.status,
      detail: item.detail,
    })),
  };
}

function buildOperatorReadinessSummary(view) {
  const protocol = view.protocol_summary || {};
  const controls = Array.isArray(protocol.controls) ? protocol.controls : [];
  const boundaries = Array.isArray(protocol.boundaries) ? protocol.boundaries : [];
  const readyControls = controls.filter((item) => item.status === "review ready").length;
  return {
    title: "Operator Readiness Summary",
    status: view.next_pass?.status === "ready" ? "review ready" : "blocked",
    talk_track: [
      "Start packet is ready for the recorded next operator action.",
      "Post-check artifacts are visible from the selected operator-loop manifest.",
      "Provider calls, durable memory writes, and Company KB writes remain disabled.",
    ],
    evidence_cards: [
      {
        label: "Start packet",
        status: view.next_pass?.status === "ready" ? "review ready" : "blocked",
        detail: view.next_pass?.action || "next operator action not recorded",
      },
      {
        label: "Readiness controls",
        status: readyControls ? "review ready" : "planned",
        detail: `${readyControls}/${controls.length} controls ready`,
      },
      {
        label: "Claim boundaries",
        status: "blocked",
        detail: `${boundaries.length} boundaries remain visible`,
      },
    ],
    comparison: [],
    non_claims: boundaries.map((item) => ({
      label: item.label,
      status: item.status,
      detail: item.detail,
    })),
  };
}

function isOperatorReadinessView(view) {
  return view?.project?.format === "agentflow_production_memory_operator_loop_run"
    && Array.isArray(view?.bundle_summary)
    && view.bundle_summary.some((item) => item.id === "next_operator_start_packet");
}
