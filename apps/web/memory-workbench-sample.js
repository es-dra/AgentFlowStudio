const PROTOCOL_ID = "memory_video_pipeline_neon_rain_turnback_v1";

const SAMPLE_ARTIFACTS = [
  {
    name: "memory_video_pipeline_package.example.json",
    payload: {
      schema_version: "0.1.0",
      artifact_type: "agentflow_memory_video_pipeline_package",
      protocol_id: PROTOCOL_ID,
      provider_calls_started: false,
      writes_long_term_memory: false,
      plan_ref: "plan/run_plan.json",
      review_ref: "review/memory_video_pipeline_review.json",
      observation_ref: "observation/memory_video_pipeline_human_observation.json",
      presentation_ref: "presentation/memory_video_pipeline_presentation_package.json",
      feedback_event_draft_ref: "feedback/memory_video_pipeline_feedback_event_draft.json",
      claim_boundaries: claimBoundaries(),
    },
  },
  {
    name: "memory_video_pipeline_review.example.json",
    payload: {
      schema_version: "0.1.0",
      artifact_type: "agentflow_memory_video_pipeline_review",
      protocol_id: PROTOCOL_ID,
      provider_calls_started_by_review: false,
      writes_long_term_memory: false,
      lane_parity: {
        same_user_task: true,
        same_source_assets: true,
        same_provider_route: true,
        same_duration: true,
        same_script: true,
        only_memory_context_differs: true,
        expected_lanes_present: true,
        same_source_image_sha256: true,
        all_manifests_succeeded: true,
      },
      video_artifacts: [
        sampleVideo("recording_016_run_1", "baseline"),
        sampleVideo("recording_016_run_1", "memory_backed"),
        sampleVideo("recording_016_run_2", "baseline"),
        sampleVideo("recording_016_run_2", "memory_backed"),
      ],
      storyboard: storyboard(),
      cross_run_stability: {
        status: "ready_for_human_visual_review",
        run_count: 2,
        lane_repeat_counts: { baseline: 2, memory_backed: 2 },
        machine_judgement: "not_performed",
      },
      claim_boundaries: claimBoundaries(),
    },
  },
  {
    name: "memory_video_pipeline_human_observation.example.json",
    payload: {
      schema_version: "0.1.0",
      artifact_type: "agentflow_memory_video_pipeline_human_observation",
      protocol_id: PROTOCOL_ID,
      writes_long_term_memory: false,
      observation_status: "visual_observation_recorded",
      lane_parity: {
        same_user_task: true,
        same_source_assets: true,
        same_provider_route: true,
        same_duration: true,
        same_script: true,
        only_memory_context_differs: true,
      },
      storyboard: storyboard(),
      observations: [
        observation("shot_structure_consistency", "memory_backed_stronger", "Memory-backed repeats kept the five checkpoints closer."),
        observation("identity_anchor_retention", "memory_backed_stronger", "Memory-backed repeats recovered the same face and high ponytail more consistently."),
        observation("wardrobe_anchor_retention", "memory_backed_stronger", "Memory-backed repeats retained white top, blue jeans, and white sneakers with less drift."),
        observation("scene_anchor_retention", "mixed", "Both lanes kept neon rain; memory-backed aligned reflections more closely."),
      ],
      observed_signal_summary: {
        baseline_more_variable: true,
        memory_backed_more_stable: true,
        residual_risk: "subjective_visual_review",
      },
      claim_boundaries: claimBoundaries(),
    },
  },
  {
    name: "memory_video_pipeline_presentation_package.example.json",
    payload: {
      schema_version: "0.1.0",
      artifact_type: "agentflow_memory_video_pipeline_presentation_package",
      protocol_id: PROTOCOL_ID,
      writes_long_term_memory: false,
      one_sentence_takeaway:
        "Under the same keyframe, task, model, duration, and storyboard, the memory-backed lane showed more stable repeat behavior while remaining a bounded visual signal.",
      experiment_setup: {
        user_task: "Create a 15 second vertical 3D anime cinematic video where the same young woman crosses a neon rain street.",
        same_for_both_lanes: ["user_task", "source_keyframe", "provider_route", "duration_sec", "storyboard_checkpoints"],
        storyboard_checkpoints: storyboard().shot_checkpoints,
      },
      result_summary: {
        baseline_more_variable: true,
        memory_backed_more_stable: true,
        residual_risk: "subjective_visual_review",
        run_count: 2,
      },
      claim_boundaries: claimBoundaries(),
    },
  },
  {
    name: "memory_video_pipeline_feedback_event_draft.json",
    payload: {
      schema_version: "0.1.0",
      artifact_type: "agentflow_feedback_event",
      feedback_id: `${PROTOCOL_ID}_feedback_draft`,
      decision: "note",
      draft_status: "draft_not_persisted",
      reason_tags: ["baseline_more_variable", "memory_backed_more_stable", "bounded_visual_signal"],
      user_note: "Use this bounded observation as a next-pass review note, not as durable memory.",
      writes_long_term_memory: false,
      provider_calls_started: false,
    },
  },
];

export function memoryWorkbenchSampleFiles() {
  return SAMPLE_ARTIFACTS.map((artifact) => ({
    name: artifact.name,
    text: async () => JSON.stringify(artifact.payload),
  }));
}

function sampleVideo(runId, laneId) {
  return {
    run_id: runId,
    lane_id: laneId,
    status: "succeeded",
    task_status: "succeed",
    provider: "kling",
    api_family: "i2v",
    model: "kling-v3",
    source_image_sha256: "source_keyframe_sha256_placeholder",
    output: {
      candidate_id: "candidate_001",
      video_ref: `${laneId}_${runId}_video_ref`,
      content_type: "video/mp4",
    },
  };
}

function storyboard() {
  return {
    scene_id: "neon_rain_turnback",
    shot_checkpoints: [
      "0-3s front three-quarter readable character",
      "3-6s walking through neon rain",
      "6-10s light sweep and rain partially obscure face and torso",
      "10-13s turn back toward camera",
      "13-15s stop under flickering abstract neon sign",
    ],
  };
}

function observation(criterion, verdict, note) {
  return { criterion, verdict, note };
}

function claimBoundaries() {
  return {
    runtime_verification: "manifest_status_only",
    human_acceptance: "not_acceptance",
    business_validation: "not_validated",
    quality_improvement_claim: "bounded_visual_signal_only",
    durable_memory_runtime: "not_implemented",
  };
}
