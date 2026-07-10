from __future__ import annotations

import subprocess
import textwrap

from studio_static_helpers import STUDIO_ROOT, _styles


def _read(path: str) -> str:
    return (STUDIO_ROOT / path).read_text(encoding="utf-8")


def test_generation_status_policy_exposes_safe_recovery_vocabulary() -> None:
    policy = _read("src/generation-status-policy.js")
    view = _read("src/generation-status-view.js")
    styles = _styles()
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")

    for marker in (
        "complete",
        "partially_complete",
        "failed",
        "retrying",
        "needs_attention",
        "Blocked reason",
        "Next action",
        "retry failed items only",
        "Partial result is preserved.",
        "provider quota may be used",
        "safeGenerationRefs",
        "safePublicText",
        "runtime_recovery",
        "safe_artifact_pointers",
        "Bearer <redacted>",
        "<local-path-redacted>",
        "<url-redacted>",
    ):
        assert marker in policy + view

    assert './styles/status-recovery.css' in index
    assert ".generation-status-card" in styles
    assert ".generation-gate-panel" in styles
    assert "preview_url" not in view
    assert "Authorization" not in view


def test_generation_modal_shows_gates_before_submit_and_blocks_local_video_gaps() -> None:
    panel = _read("src/panels/generation-panel.js")
    retry = _read("src/node-generation-retry.js")
    policy = _read("src/generation-status-policy.js")

    for marker in (
        "generationReadinessSummary",
        "generationGatePanel",
        "Auth gate",
        "Provider gate",
        "Runtime readiness",
        "Node readiness",
        "confirm.disabled = Boolean(summary.blocked)",
        "Blocked reason",
        "Next action",
        "Retry failed items",
        "shouldRetryFailedItemsOnly",
    ):
        assert marker in panel + retry + policy

    assert "First frame is required before video submit." in _read("src/generation-status-policy.js")
    assert "Video motion prompt is required before submit." in _read("src/generation-status-policy.js")


def test_runtime_recovery_envelope_feeds_studio_status_policy() -> None:
    script = textwrap.dedent(
        """
        import { responseStatusSummary } from "./apps/studio/src/generation-status-policy.js";

        const summary = responseStatusSummary({
          job: { job_id: "job_123", status: "failed" },
          safe_manifest: { batch_status: "failed", blocks: [{ reason: "one requested image failed" }] },
          runtime_recovery: {
            status: "partially_complete",
            job_id: "job_123",
            outputs: [
              { item_id: "candidate_001", state: "complete", preserved: true },
              { item_id: "candidate_002", state: "failed", preserved: false },
            ],
            safe_artifact_pointers: [
              { role: "safe_manifest", artifact_id: "artifact_safe_123" },
            ],
          },
        });

        if (summary.policyStatus !== "partially_complete") {
          throw new Error(`unexpected policyStatus ${summary.policyStatus}`);
        }
        if (!summary.hasPartialOutput) {
          throw new Error("expected partial output detection from runtime_recovery.outputs");
        }
        if (!summary.safeRefs.some((item) => item.value === "artifact_safe_123")) {
          throw new Error("expected safe artifact pointer from runtime_recovery");
        }
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_active_multi_candidate_retry_keeps_retrying_job_state_until_terminal_response() -> None:
    actions = _read("src/node-keyframe-actions.js")
    response_path = _read("src/node-keyframe-response.js")
    policy = _read("src/generation-status-policy.js")

    assert "retrying: retryPlan.retrying" in actions
    assert "retrying: Boolean(fresh?.params?.retryFailedItemsOnly)" in actions
    assert "retrying: Boolean(options.retrying)" in response_path
    assert "options.retrying && isActiveRuntimeStatus(runtimeStatus)" in policy

    script = textwrap.dedent(
        """
        import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
        import { responseStatusSummary } from "./apps/studio/src/generation-status-policy.js";
        import { setSubmittingGenerationState, updateNodeGenerationState } from "./apps/studio/src/node-generation-progress.js";

        function makeStore(node) {
          const state = { nodes: { node_1: node }, assets: [] };
          return {
            get: () => state,
            set: (mutator) => mutator(state),
            nextId: (prefix) => `${prefix}_001`,
          };
        }

        function makeNode() {
          return { id: "node_1", type: "image", title: "Keyframe", prompt: "prompt", params: {} };
        }

        const submitted = responseStatusSummary({ job: { status: "submitted" } }, { retrying: true });
        if (submitted.policyStatus !== "retrying") {
          throw new Error(`expected retrying active policy, got ${submitted.policyStatus}`);
        }

        const terminal = responseStatusSummary({
          job: { status: "succeeded" },
          safe_manifest: { batch_status: "complete", output_count: 2 },
        }, { retrying: true });
        if (terminal.policyStatus !== "complete") {
          throw new Error(`expected terminal complete policy, got ${terminal.policyStatus}`);
        }

        const node = { params: {} };
        setSubmittingGenerationState(node, "keyframe", { retrying: true, clearPreview: false });
        updateNodeGenerationState(node, { job: { status: "submitted" } }, { kind: "keyframe", retrying: true });
        if (node.params.generationPolicyStatus !== "retrying" || node.params.retryFailedItemsOnly !== true) {
          throw new Error("active retry submit lost failed-items-only job state");
        }
        updateNodeGenerationState(node, { job: { status: "running", progress: { mode: "indeterminate" } } }, { kind: "keyframe" });
        if (node.params.progressPercent !== null || node.params.jobProgress.mode !== "indeterminate") {
          throw new Error(`indeterminate progress should not expose a fake percent, got ${node.params.progressPercent}`);
        }

        updateNodeGenerationState(node, {
          job: { status: "succeeded" },
          safe_manifest: { batch_status: "complete", output_count: 2 },
        }, { kind: "keyframe", retrying: true });
        if (node.params.generationPolicyStatus !== "complete" || node.params.retryFailedItemsOnly) {
          throw new Error("terminal retry response did not clear retrying job state");
        }

        for (const status of ["submitted", "pending", "running"]) {
          const actualNode = makeNode();
          const store = makeStore(actualNode);
          applyKeyframeResponse(
            store,
            "node_1",
            { job: { status, job_id: `job_${status}` } },
            { aspect_ratio: "9:16" },
            { kind: "keyframe", retrying: true },
          );
          if (actualNode.params.generationPolicyStatus !== "retrying" || actualNode.params.retryFailedItemsOnly !== true) {
            throw new Error(`actual applyKeyframeResponse path lost retrying for ${status}`);
          }
        }

        const terminalCases = [
          {
            label: "complete",
            response: { job: { status: "succeeded" }, safe_manifest: { batch_status: "complete", output_count: 2 } },
            expected: "complete",
          },
          {
            label: "partially_complete",
            response: { job: { status: "failed" }, safe_manifest: { batch_status: "partially_complete", output_count: 1, blocks: [{ reason: "one failed" }] } },
            expected: "partially_complete",
          },
          {
            label: "failed",
            response: { job: { status: "failed" }, safe_manifest: { batch_status: "failed", output_count: 0, blocks: [{ reason: "provider failed" }] } },
            expected: "failed",
          },
          {
            label: "needs_attention",
            response: { job: { status: "blocked" }, safe_manifest: { batch_status: "needs_attention", output_count: 0, blocks: [{ reason: "gate closed" }] } },
            expected: "needs_attention",
          },
        ];
        for (const item of terminalCases) {
          const actualNode = makeNode();
          const store = makeStore(actualNode);
          applyKeyframeResponse(store, "node_1", item.response, { aspect_ratio: "9:16" }, { kind: "keyframe", retrying: true });
          if (actualNode.params.generationPolicyStatus !== item.expected || actualNode.params.retryFailedItemsOnly) {
            throw new Error(`actual terminal ${item.label} did not clear retrying; got ${actualNode.params.generationPolicyStatus}`);
          }
        }
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_partial_outputs_are_preserved_and_retry_targets_failed_items_only() -> None:
    keyframe_response = _read("src/node-keyframe-response.js")
    keyframe_actions = _read("src/node-keyframe-actions.js")
    video_actions = _read("src/node-video-actions.js")
    results = _read("src/node-generation-results.js")
    retry = _read("src/node-generation-retry.js")

    assert 'partial ? "partial" : "error"' in keyframe_response
    assert 'status === "succeeded";' in keyframe_response
    assert "appendPreservedOutput" in keyframe_actions
    assert "appendPreservedOutput" in video_actions
    assert "retryFailedItemsPlan" in keyframe_actions + video_actions
    assert "retryResultText" in video_actions
    assert "Preserved outputs remain visible" in retry
    assert "retry targets failed items only" in retry
    assert "partially_complete" in results
    assert "retry failed items only" in results
    assert "safePublicText(reason)" in results


def test_normal_workflow_surfaces_show_recovery_and_review() -> None:
    body = _read("src/canvas-node-body.js")
    canvas = _read("src/canvas-view.js")
    job_center = _read("src/panels/job-center.js")
    inspector = _read("src/panels/inspector-panel.js")
    process_panel = _read("src/panels/creation-process-panel.js")
    result_view = _read("src/node-result-view.js")
    feedback = _read("src/quality-feedback.js")
    menu = _read("src/panels/node-menu.js")

    for marker in (
        "partialBody",
        "generationStatusCard",
        "partially_complete",
        "Retry failed items",
        "blockedReasonForNode",
        "nextActionForNode",
        "statusLineForNode",
        "qualityFeedbackView(node)",
        '["complete", "partial"].includes(node.status)',
    ):
        assert marker in body + canvas + job_center + inspector + process_panel + result_view + feedback + menu

    assert "node.status === \"partial\"" in result_view
    assert '["error", "partial"].includes(node.status)' in canvas + inspector + menu
    assert "stateText(" not in job_center


def test_job_center_keeps_blocked_reason_and_next_action_together() -> None:
    job_center = _read("src/panels/job-center.js")
    styles = _styles()

    for marker in (
        "const suffixParts = [];",
        'suffixParts.push(`blocked reason: ${summary.blockedReason}`)',
        'suffixParts.push(`next action: ${summary.nextAction}`)',
        'suffixParts.join(" · ")',
    ):
        assert marker in job_center

    for marker in (
        ".job-center.jobs .job-center-card.partial .job-main",
        ".job-center.jobs .job-center-card.failed .job-main",
        ".job-center.jobs .job-center-card.attention .job-main",
        "flex: 1 0 100%;",
        "overflow-wrap: anywhere;",
        "text-overflow: clip;",
        "white-space: normal;",
    ):
        assert marker in styles


def test_narrow_studio_workflow_has_canvas_lane_and_collapsed_inspector() -> None:
    styles = _styles()

    for marker in (
        "#drawer:not(.collapsed) ~ #canvas-root #canvas-viewport",
        "width: calc(100vw - var(--mobile-drawer-w));",
        "#drawer:not(.collapsed) ~ #canvas-root .node",
        "width: calc(100vw - var(--mobile-drawer-w, var(--drawer-w)) - 24px) !important;",
        "#inspector > :not(.inspector-collapse-toggle)",
        ".generation-status-row,\n  .generation-gate-row",
    ):
        assert marker in styles
