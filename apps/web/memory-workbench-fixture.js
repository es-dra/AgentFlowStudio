export const memoryWorkbenchFixture = {
  contract_type: "agentflow_memory_video_pipeline_package",
  state: "review ready",
  project: {
    title: "Memory advantage storyboard demo",
    brief: "Compare baseline prompting against memory-assisted production for the same 3D anime storyboard requirement.",
    format: "keyframe to 15s I2V storyboard",
    route: "static Web fixture, no provider execution",
  },
  assets: [
    {
      id: "character_design_reference",
      label: "Character design reference",
      detail: "three-view character sheet captured as reviewed subject reference",
      status: "planned",
    },
    {
      id: "desert_scene_brief",
      label: "Desert storm scene",
      detail: "wide sandstorm setting plus fixed camera and action constraints",
      status: "planned",
    },
  ],
  bundle_summary: [
    {
      id: "static_fixture",
      title: "Static fixture",
      status: "review ready",
      detail: "No local package selected; using sanitized built-in memory workbench data.",
    },
  ],
  workflow_actions: [
    { id: "load_package", label: "Load package", focus_target: "project", status: "planned" },
    { id: "inspect_evidence", label: "Inspect evidence", focus_target: "review", status: "review ready" },
    { id: "compare_lanes", label: "Compare lanes", focus_target: "memory-backed-run", status: "review ready" },
    { id: "capture_feedback", label: "Capture feedback", focus_target: "feedback", status: "feedback captured" },
    { id: "prepare_next_pass", label: "Prepare next pass", focus_target: "next-pass", status: "memory candidate drafted" },
  ],
  artifact_inspector: [
    {
      id: "static_fixture_inspector",
      title: "Fixture summary",
      status: "review ready",
      focus_targets: ["project", "assets", "memory-loaded", "baseline-run", "memory-backed-run", "review", "feedback", "next-pass"],
      detail: "Built-in fixture only; select memory JSON artifacts to inspect live structure.",
      facts: [
        { label: "scope", value: "explicit selected files only" },
        { label: "auto_follow_refs", value: "false" },
      ],
    },
  ],
  memory_loaded: [
    {
      id: "character_design_reference",
      title: "角色定妆资产",
      why_eligible: "promoted asset memory with matching character and style scope",
      source_evidence_refs: ["review.character_sheet", "feedback_to_next_pass.character_consistency"],
      promotion_status: "promoted",
      request_projection: "keep face shape, armor silhouette, hair volume, cape behavior, and 3D anime rendering consistent",
      feedback_effect: "next pass can use shorter scene prompts while preserving the subject constraints",
    },
    {
      id: "scene_physics_note",
      title: "沙暴物理约束",
      why_eligible: "merged feedback from prior desert motion review",
      source_evidence_refs: ["review.storyboard_adherence", "human_observation.wind_and_sand"],
      promotion_status: "merged",
      request_projection: "sand, cloth, camera push, and body motion should follow one wind direction",
      feedback_effect: "new shots inherit scene continuity checks instead of restating every detail",
    },
  ],
  lanes: [
    {
      id: "baseline-lane",
      title: "Baseline Run",
      status: "review ready",
      input: "normal storyboard prompt with visible scene, subject, and camera requirements",
      output: "good local details, but motion and costume details drift between attempts",
    },
    {
      id: "memory-lane",
      title: "Memory-backed Run",
      status: "review ready",
      input: "same storyboard requirement plus reusable memory context projection",
      output: "more stable role silhouette, scene physics, and shot rhythm across attempts",
    },
  ],
  protocol_summary: {
    title: "Baseline parity protocol",
    status: "review ready",
    controls: [
      { label: "same task", status: "review ready", detail: "same storyboard requirement" },
      { label: "same source assets", status: "review ready", detail: "same character and scene inputs" },
      { label: "same provider route", status: "review ready", detail: "same I2V route in the demo setup" },
      { label: "only memory context differs", status: "review ready", detail: "memory-backed lane receives reusable context projection" },
    ],
    boundaries: [
      { label: "human acceptance", status: "blocked", detail: "not claimed in the static workbench" },
      { label: "business validation", status: "blocked", detail: "not validated by this demo evidence" },
      { label: "durable memory runtime", status: "blocked", detail: "not implemented in the browser slice" },
    ],
  },
  demo_summary: {
    title: "Demo Evidence Summary",
    status: "review ready",
    talk_track: [
      "Same task, assets, route, duration, and storyboard are held constant.",
      "Baseline stays stateless; memory-backed receives reusable context projection.",
      "Feedback becomes a next-pass draft, not durable memory or product validation.",
    ],
    evidence_cards: [
      {
        label: "Experiment setup",
        status: "review ready",
        detail: "Lane parity is reviewable from selected artifacts.",
      },
      {
        label: "Observed signal",
        status: "review ready",
        detail: "character and scene anchors remain more stable across repeated runs",
      },
      {
        label: "Reuse path",
        status: "feedback captured",
        detail: "prepare a promotion decision and reuse as context bundle after review",
      },
    ],
    comparison: [
      { label: "Baseline", status: "review ready", detail: "good local details, but motion and costume details drift between attempts" },
      { label: "Memory-backed", status: "review ready", detail: "more stable role silhouette, scene physics, and shot rhythm across attempts" },
    ],
    non_claims: [
      { label: "human acceptance", status: "blocked", detail: "not claimed in the static workbench" },
      { label: "business validation", status: "blocked", detail: "not validated by this demo evidence" },
      { label: "durable memory runtime", status: "blocked", detail: "not implemented in the browser slice" },
    ],
  },
  review: {
    storyboard_adherence: "memory lane keeps the action beat closer to the requested desert push-in",
    visual_consistency: "character and scene anchors remain more stable across repeated runs",
    boundary: "human observation candidate, not business validation",
  },
  feedback: {
    status: "feedback captured",
    summary: "tighten cape motion, keep sand direction continuous, preserve character silhouette in future shots",
  },
  feedback_draft: {
    mode: "fixture",
    status: "draft_not_persisted",
    title: "Feedback Draft Preview",
    detail: "Built-in sanitized preview; select memory JSON artifacts to generate a local draft from evidence.",
    json_text: "{\n  \"artifact_type\": \"agentflow_feedback_event\",\n  \"draft_status\": \"draft_not_persisted\",\n  \"writes_long_term_memory\": false\n}\n",
    copy_enabled: true,
  },
  next_pass: {
    status: "memory candidate drafted",
    action: "prepare a promotion decision and reuse as context bundle after review",
  },
  state_labels: [
    "no plan",
    "planned",
    "generating",
    "review ready",
    "feedback captured",
    "memory candidate drafted",
    "promotion decision ready",
    "blocked",
  ],
  timeline: [
    { label: "Project", status: "planned", detail: "script, role, and scene goal fixed" },
    { label: "Assets", status: "planned", detail: "character and scene assets selected" },
    { label: "Memory Loaded", status: "review ready", detail: "eligible memory projected into request" },
    { label: "Baseline Run", status: "review ready", detail: "stateless comparison lane" },
    { label: "Memory-backed Run", status: "review ready", detail: "memory-assisted comparison lane" },
    { label: "Review", status: "review ready", detail: "storyboard adherence and visual consistency checked" },
    { label: "Feedback", status: "feedback captured", detail: "operator note drafted for next pass" },
    { label: "Next Pass", status: "memory candidate drafted", detail: "candidate awaits promotion decision" },
  ],
};
