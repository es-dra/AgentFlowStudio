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
        "redactUnsafeText",
    ):
        assert marker in policy + view

    script = textwrap.dedent(
        """
        import { safePublicText } from "./apps/studio/src/generation-status-policy.js";

        const text = safePublicText("Bearer abc /home/owner/private.png https://signed.example/private token=abc api_key=def Authorization=ghi", 260);
        for (const forbidden of ["Bearer abc", "/home/owner", "signed.example", "token=abc", "api_key", "Authorization=ghi"]) {
          if (text.includes(forbidden)) throw new Error(`safePublicText leaked ${forbidden}: ${text}`);
        }
        if (!text.includes("<local-path-redacted>") || !text.includes("<url-redacted>")) {
          throw new Error(`safePublicText did not apply canonical redactions: ${text}`);
        }
        """
    )
    subprocess.run(["node", "--input-type=module", "-e", script], check=True)

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


def test_studio_preserves_multi_image_candidate_lists_across_result_and_restore() -> None:
    script = textwrap.dedent(
        """
        import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
        import { candidatePreviews as canvasCandidatePreviews } from "./apps/studio/src/canvas-node-body.js";
        import { candidatePreviewItems } from "./apps/studio/src/node-generation-progress.js";
        import { normalizeSnapshot } from "./apps/studio/src/store-state.js";

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

        const projectId = "studio-multi-candidates";
        const firstUrl = `/projects/${projectId}/keyframe-generations/job_multi_001/candidates/candidate_001/preview`;
        const secondUrl = `/projects/${projectId}/keyframe-generations/job_multi_001/candidates/candidate_002/preview`;

        const twoSuccess = {
          job: { status: "succeeded", job_id: "job_multi_001" },
          safe_manifest: { batch_status: "complete", output_count: 2 },
          candidate_previews: [
            { candidate_id: "candidate_001", preview_url: firstUrl, width: 1024, height: 576, aspect_ratio: "16:9" },
            { candidate_id: "candidate_002", preview_url: secondUrl, width: 1024, height: 576, aspect_ratio: "16:9" },
          ],
        };

        const successItems = candidatePreviewItems(twoSuccess);
        if (successItems.length !== 2 || successItems[1].candidate_id !== "candidate_002") {
          throw new Error(`expected both successful candidates, got ${JSON.stringify(successItems)}`);
        }

        const successNode = makeNode();
        applyKeyframeResponse(makeStore(successNode), "node_1", twoSuccess, { aspect_ratio: "16:9" });
        if (successNode.status !== "complete" || successNode.previewUrl) {
          throw new Error(`two-success response implicitly selected a primary preview: ${JSON.stringify(successNode)}`);
        }
        if (successNode.params.candidatePreviewUrls?.length !== 2) {
          throw new Error(`two-success node degraded candidate list: ${JSON.stringify(successNode.params.candidatePreviewUrls)}`);
        }

        const partialResponse = {
          job: { status: "failed", job_id: "job_multi_001" },
          safe_manifest: {
            batch_status: "partially_complete",
            output_count: 1,
            blocks: [{ candidate_id: "candidate_002", reason: "provider temporarily unavailable", failure_class: "provider_timeout" }],
          },
          candidate_previews: [
            { candidate_id: "candidate_001", preview_url: firstUrl, width: 1024, height: 576, aspect_ratio: "16:9" },
          ],
          runtime_recovery: {
            status: "partially_complete",
            outputs: [
              { item_id: "candidate_001", state: "complete", preserved: true, preview_url: firstUrl },
              { item_id: "candidate_002", state: "failed", preserved: false, failure_class: "provider_timeout" },
            ],
          },
        };

        const partialNode = makeNode();
        applyKeyframeResponse(makeStore(partialNode), "node_1", partialResponse, { aspect_ratio: "16:9" });
        const partialItems = partialNode.params.candidatePreviewUrls || [];
        if (partialNode.status !== "partial" || partialNode.params.generationPolicyStatus !== "partially_complete") {
          throw new Error(`partial response did not expose partial state: ${JSON.stringify(partialNode)}`);
        }
        if (partialItems.length !== 2) {
          throw new Error(`partial response lost failed candidate evidence: ${JSON.stringify(partialItems)}`);
        }
        if (partialItems[0].candidate_id !== "candidate_001" || partialItems[0].status !== "succeeded") {
          throw new Error(`partial response lost successful candidate identity: ${JSON.stringify(partialItems)}`);
        }
        if (partialItems[1].candidate_id !== "candidate_002" || partialItems[1].status !== "failed") {
          throw new Error(`partial response lost failed candidate slot: ${JSON.stringify(partialItems)}`);
        }

        const restored = normalizeSnapshot({
          meta: { projectId },
          nodes: {
            node_1: {
              id: "node_1",
              type: "image",
              previewUrl: firstUrl,
              status: "partial",
              params: { candidatePreviewUrls: partialItems },
            },
          },
          order: ["node_1"],
        });
        const restoredItems = restored.nodes.node_1.params.candidatePreviewUrls || [];
        if (restoredItems.length !== 2 || restoredItems[1].status !== "failed") {
          throw new Error(`persistence restore degraded candidate list: ${JSON.stringify(restoredItems)}`);
        }

        const runtimeSanitizedRestore = normalizeSnapshot({
          meta: { projectId },
          nodes: {
            node_1: {
              id: "node_1",
              type: "image",
              previewUrl: firstUrl,
              status: "partial",
              params: {
                candidatePreviewUrls: [{ url: firstUrl, preview_url: firstUrl }],
                lastGenerationManifest: partialNode.params.lastGenerationManifest,
              },
            },
          },
          order: ["node_1"],
        });
        const rebuiltItems = canvasCandidatePreviews(runtimeSanitizedRestore.nodes.node_1);
        if (rebuiltItems.length !== 2 || rebuiltItems[0].candidate_id !== "candidate_001" || rebuiltItems[1].status !== "failed") {
          throw new Error(`runtime-style restore did not rebuild candidate evidence: ${JSON.stringify(rebuiltItems)}`);
        }
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_candidate_failure_reasons_are_redacted_before_state_restore_and_dom() -> None:
    script = textwrap.dedent(
        """
        import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";
        import { candidatePreviewsFromNode } from "./apps/studio/src/node-candidate-previews.js";
        import { resultView } from "./apps/studio/src/node-result-view.js";
        import { normalizeSnapshot } from "./apps/studio/src/store-state.js";

        function makeStore(node) {
          const state = { nodes: { node_1: node }, assets: [] };
          return {
            get: () => state,
            set: (mutator) => mutator(state),
            nextId: (prefix) => `${prefix}_001`,
          };
        }

        function makeElement(tagName) {
          const element = {
            tagName: String(tagName || "").toUpperCase(),
            children: [],
            dataset: {},
            style: {},
            attributes: {},
            className: "",
            title: "",
            disabled: false,
            textContent: "",
            innerHTML: "",
            appendChild(child) {
              this.children.push(child);
              return child;
            },
            append(...children) {
              children.forEach((child) => this.appendChild(child));
            },
            addEventListener() {},
            setAttribute(name, value) {
              this.attributes[name] = String(value);
              this[name] = String(value);
            },
          };
          element.classList = {
            add(...names) {
              const current = new Set(String(element.className || "").split(/\\s+/).filter(Boolean));
              names.forEach((name) => current.add(name));
              element.className = [...current].join(" ");
            },
          };
          Object.defineProperty(element, "innerText", {
            get() {
              const own = [this.textContent, String(this.innerHTML || "").replace(/<[^>]+>/g, " ")]
                .filter(Boolean)
                .join(" ");
              return [own, ...this.children.map((child) => child.innerText || child.textContent || "")]
                .filter(Boolean)
                .join(" ")
                .replace(/\\s+/g, " ")
                .trim();
            },
          });
          return element;
        }

        function titles(element) {
          return [
            element.title || "",
            ...element.children.flatMap((child) => titles(child)),
          ].filter(Boolean);
        }

        function assertNoUnsafe(label, value) {
          const text = JSON.stringify(value);
          const forbidden = [
            "Authorization=TOPSECRET",
            "TOPSECRET",
            "token=MYTOKEN",
            "MYTOKEN",
            "secret=MYSECRET",
            "MYSECRET",
            "api_key=APIKEY",
            "APIKEY",
          ];
          for (const item of forbidden) {
            if (text.includes(item)) {
              throw new Error(`${label} leaked ${item}: ${text}`);
            }
          }
          if (text.toLowerCase().includes("api_key")) {
            throw new Error(`${label} leaked api_key marker: ${text}`);
          }
        }

        globalThis.document = { createElement: makeElement };

        const projectId = "studio-redaction-candidates";
        const firstUrl = `/projects/${projectId}/keyframe-generations/job_redact_001/candidates/candidate_001/preview`;
        const unsafe = "Authorization=TOPSECRET token=MYTOKEN secret=MYSECRET api_key=APIKEY";
        const response = {
          job: { status: "failed", job_id: "job_redact_001" },
          safe_manifest: {
            batch_status: "partially_complete",
            output_count: 1,
            stage: unsafe,
            failure_class: "provider_timeout",
            blocks: [{ candidate_id: "candidate_002", reason: unsafe, message: unsafe, error: unsafe, failure_class: "provider_timeout" }],
            provider_diagnostics: { reason: unsafe, error_type: unsafe, provider_stage: unsafe },
            batch_summary: unsafe,
          },
          candidate_previews: [
            { candidate_id: "candidate_001", preview_url: firstUrl, width: 1024, height: 576, aspect_ratio: "16:9" },
          ],
          runtime_recovery: {
            status: "partially_complete",
            outputs: [
              { item_id: "candidate_001", state: "complete", preserved: true, preview_url: firstUrl },
              { item_id: "candidate_002", state: "failed", preserved: false, reason: unsafe },
            ],
          },
        };

        const node = { id: "node_1", type: "image", title: "Keyframe", prompt: "prompt", params: {} };
        applyKeyframeResponse(makeStore(node), "node_1", response, { aspect_ratio: "16:9" });
        assertNoUnsafe("immediate lastGenerationManifest", node.params.lastGenerationManifest);
        assertNoUnsafe("immediate provider diagnostics", node.params.lastGenerationManifest.provider_diagnostics);
        assertNoUnsafe("immediate manifest blocks", node.params.lastGenerationManifest.blocks);
        assertNoUnsafe("immediate params", node.params);
        assertNoUnsafe("immediate result", node.result);
        const candidates = candidatePreviewsFromNode(node);
        assertNoUnsafe("candidate objects", candidates);

        const restored = normalizeSnapshot({
          meta: { projectId },
          nodes: {
            node_1: {
              id: "node_1",
              type: "image",
              previewUrl: firstUrl,
              status: "partial",
              result: node.result,
              params: {
                candidatePreviewUrls: node.params.candidatePreviewUrls,
                lastGenerationManifest: {
                  blocks: [{ candidate_id: "candidate_002", reason: unsafe, failure_class: "provider_timeout" }],
                },
              },
            },
          },
          order: ["node_1"],
        });
        assertNoUnsafe("normalized persistence state", restored.nodes.node_1.params);

        const view = resultView(restored.nodes.node_1);
        assertNoUnsafe("DOM text", view.innerText);
        assertNoUnsafe("DOM titles", titles(view));
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_candidate_preview_items_sanitize_adversarial_immediate_state() -> None:
    script = textwrap.dedent(
        """
        import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";

        function makeStore(node) {
          const state = { nodes: { node_1: node }, assets: [] };
          return {
            get: () => state,
            set: (mutator) => mutator(state),
            nextId: (prefix) => `${prefix}_001`,
          };
        }

        function assertNoUnsafe(label, value) {
          const text = JSON.stringify(value);
          const forbidden = [
            "Authorization=TOPSECRET",
            "TOPSECRET",
            "token=MYTOKEN",
            "MYTOKEN",
            "secret=MYSECRET",
            "MYSECRET",
            "api_key=APIKEY",
            "APIKEY",
          ];
          for (const item of forbidden) {
            if (text.includes(item)) {
              throw new Error(`${label} leaked ${item}: ${text}`);
            }
          }
          if (text.toLowerCase().includes("api_key")) {
            throw new Error(`${label} leaked api_key marker: ${text}`);
          }
        }

        const allowedStatus = new Set(["succeeded", "failed", "blocked", "needs_attention", "cancelled", "retryable", "partial"]);
        const allowedState = new Set(["complete", ...allowedStatus]);
        const safePreviewRoute = /^\\/projects\\/[a-zA-Z0-9_.-]+\\/(?:image-assets\\/[a-zA-Z0-9_.-]+\\/preview|keyframe-generations\\/[a-zA-Z0-9_.-]+\\/candidates\\/[a-zA-Z0-9_.-]+\\/preview|video-generations\\/[a-zA-Z0-9_.-]+\\/candidates\\/[a-zA-Z0-9_.-]+\\/preview)$/;
        const safeIdentifier = /^[a-zA-Z0-9_.:-]{1,160}$/;

        function assertCandidateAllowlist(candidate, index) {
          if (candidate.status && !allowedStatus.has(candidate.status)) {
            throw new Error(`candidate ${index} kept unsafe status: ${JSON.stringify(candidate)}`);
          }
          if (candidate.state && !allowedState.has(candidate.state)) {
            throw new Error(`candidate ${index} kept unsafe state: ${JSON.stringify(candidate)}`);
          }
          for (const field of ["candidate_id", "artifact_id", "image_asset_id"]) {
            if (candidate[field] && !safeIdentifier.test(candidate[field])) {
              throw new Error(`candidate ${index} kept unsafe ${field}: ${JSON.stringify(candidate)}`);
            }
          }
          for (const field of ["url", "preview_url"]) {
            if (candidate[field] && !safePreviewRoute.test(candidate[field])) {
              throw new Error(`candidate ${index} kept unsafe ${field}: ${JSON.stringify(candidate)}`);
            }
          }
          if (candidate.aspect_ratio && !/^\\d{1,2}:\\d{1,2}$/.test(candidate.aspect_ratio)) {
            throw new Error(`candidate ${index} kept unsafe aspect ratio: ${JSON.stringify(candidate)}`);
          }
          for (const field of ["attempt_index", "requested_count", "returned_count"]) {
            if (field in candidate && (!Number.isInteger(candidate[field]) || candidate[field] < 0 || candidate[field] > 9999)) {
              throw new Error(`candidate ${index} kept unsafe ${field}: ${JSON.stringify(candidate)}`);
            }
          }
        }

        const unsafe = "Authorization=TOPSECRET token=MYTOKEN secret=MYSECRET api_key=APIKEY";
        const projectId = "studio-candidate-allowlist";
        const safeUrl = `/projects/${projectId}/keyframe-generations/job_matrix_001/candidates/candidate_001/preview`;
        const unsafeUrl = `https://signed.example/private.png?api_key=APIKEY&token=MYTOKEN`;
        const response = {
          job: { status: "failed", job_id: "job_matrix_001" },
          safe_manifest: {
            batch_status: "partially_complete",
            output_count: 1,
            blocks: [
              {
                candidate_id: `candidate_002 ${unsafe}`,
                item_id: `item_${unsafe}`,
                id: `id_${unsafe}`,
                block_id: `block_${unsafe}`,
                reason: unsafe,
                message: unsafe,
                error: unsafe,
                failure_class: `provider_timeout ${unsafe}`,
                provider_stage: `provider_request ${unsafe}`,
                required_gate: `gate_${unsafe}`,
                attempt_index: `2 ${unsafe}`,
                requested_count: `2 ${unsafe}`,
                returned_count: `1 ${unsafe}`,
              },
            ],
            provider_diagnostics: {
              reason: unsafe,
              failure_class: `provider_timeout ${unsafe}`,
              provider_stage: `provider_request ${unsafe}`,
            },
          },
          candidate_previews: [
            {
              candidate_id: `candidate_001 ${unsafe}`,
              item_id: `item_${unsafe}`,
              id: `id_${unsafe}`,
              preview_url: unsafeUrl,
              url: unsafeUrl,
              artifact_id: `artifact_${unsafe}`,
              image_asset_id: `image_${unsafe}`,
              width: "1024",
              height: "576",
              aspect_ratio: `16:9 ${unsafe}`,
              attempt_index: `1 ${unsafe}`,
              requested_count: `2 ${unsafe}`,
              returned_count: `1 ${unsafe}`,
            },
          ],
          runtime_recovery: {
            status: "partially_complete",
            outputs: [
              {
                item_id: `candidate_001 ${unsafe}`,
                state: `complete ${unsafe}`,
                status: `succeeded ${unsafe}`,
                preserved: true,
                preview_url: safeUrl,
                image_asset_preview_url: unsafeUrl,
                url: `javascript:alert("${unsafe}")`,
                artifact_id: `artifact_${unsafe}`,
                image_asset_id: `image_${unsafe}`,
                width: "1024",
                height: "576",
                aspect_ratio: `16:9 ${unsafe}`,
                attempt_index: `1 ${unsafe}`,
                requested_count: `2 ${unsafe}`,
                returned_count: `1 ${unsafe}`,
              },
              {
                item_id: "candidate_002",
                state: `failed ${unsafe}`,
                status: `failed ${unsafe}`,
                preserved: false,
                preview_url: unsafeUrl,
                image_asset_preview_url: unsafeUrl,
                url: unsafeUrl,
                artifact_id: `artifact_${unsafe}`,
                image_asset_id: `image_${unsafe}`,
                failure_class: `provider_timeout ${unsafe}`,
                reason: unsafe,
                aspect_ratio: `1:1 ${unsafe}`,
                attempt_index: `2 ${unsafe}`,
                requested_count: `2 ${unsafe}`,
                returned_count: `1 ${unsafe}`,
              },
            ],
          },
        };

        const node = { id: "node_1", type: "image", title: "Keyframe", prompt: "prompt", params: {} };
        applyKeyframeResponse(makeStore(node), "node_1", response, { aspect_ratio: "16:9" });
        assertNoUnsafe("immediate params", node.params);
        assertNoUnsafe("immediate result", node.result);
        assertNoUnsafe("immediate manifest", node.params.lastGenerationManifest);
        assertNoUnsafe("immediate candidates", node.params.candidatePreviewUrls);
        for (const [index, candidate] of (node.params.candidatePreviewUrls || []).entries()) {
          assertCandidateAllowlist(candidate, index);
        }
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_reusable_asset_authority_has_one_validator_and_a_frozen_consumer_inventory() -> None:
    helper = _read("src/reusable-asset-authority.js")
    progress = _read("src/node-generation-progress.js")
    response = _read("src/node-keyframe-response.js")
    previews = _read("src/node-candidate-previews.js")
    controller = _read("src/candidate-selection-controller.js")
    store = _read("src/store-state.js")

    assert helper.count("export function selectReusableAssetAuthority") == 1
    for marker in (
        'asset.status !== "succeeded"',
        'asset.role !== "generated_keyframe_reference"',
        'asset.source_kind !== "keyframe_candidate"',
        "matching.length !== 1",
        "sourceJobId !== candidate.parentJobId",
        "sourceCandidateId !== candidate.candidateId",
        "sourceCandidateDigest !== candidate.canonicalDigest",
        "sha256 !== sourceCandidateDigest",
        "validatedCandidatePreviewRoute(candidate)",
        "CANDIDATE_PREVIEW_ROUTE_RE",
        "parentJobId && first.job_id !== parentJobId",
        "candidateId && first.candidate_id !== candidateId",
        "projectId !== first.project_id",
        "item.route !== first.route",
    ):
        assert marker in helper

    consumers = {
        "node-generation-progress.js": progress,
        "node-keyframe-response.js": response,
        "node-candidate-previews.js": previews,
        "candidate-selection-controller.js": controller,
        "store-state.js": store,
    }
    for name, source in consumers.items():
        assert 'from "./reusable-asset-authority.js"' in source, name
        assert "selectReusableAssetAuthority(" in source, name

    raw_authority_readers = {
        path.name
        for path in (STUDIO_ROOT / "src").glob("*.js")
        if "reusable_image_assets" in path.read_text(encoding="utf-8")
    }
    assert raw_authority_readers == {
        "generation-status-policy.js",  # availability signal only
        "node-generation-progress.js",  # sole authority binding handoff
        "node-generation-results.js",  # informational asset id text only
        "node-keyframe-response.js",  # compatibility marker; no raw payload access
    }
    assert progress.count("response?.reusable_image_assets") == 1
    assert "response?.reusable_image_assets" not in response
    assert "reusable_image_assets" not in previews + controller + store

    for source in (progress, response, previews, controller, store):
        assert "source_candidate_id ||" not in source
        assert "image_asset_id || item.asset_id" not in source
        assert "image_asset_id || asset_id" not in source

    submit_start = controller.index("async function submitCreatorDecision")
    submit_end = controller.index("function assertVisibleCandidateAuthority", submit_start)
    submit_body = controller[submit_start:submit_end]
    assert submit_body.index("requireReusableAssetAuthority(preflightCandidate)") < submit_body.index(
        "ensureProductionRunForCandidateSelection"
    )
    assert submit_body.index("requireReusableAssetAuthority(preflightCandidate)") < submit_body.index(
        "runtime.submitCreatorDecision"
    )
    assert submit_body.index("requireReusableAssetAuthority(preflightCandidate)") < submit_body.index(
        "runtime.getProductionRun"
    )

    restore_start = controller.index("export async function restoreCandidateSelection")
    restore_end = controller.index("function preflightRestorableCandidate", restore_start)
    restore_body = controller[restore_start:restore_end]
    assert restore_body.index("requireReusableAssetAuthority(preflightRestorableCandidate") < restore_body.index(
        "runtime.getProductionRun"
    )

    assert "item.parent_job_id || parentJobId" not in progress
    assert "itemJobMatchesEnvelope" in progress
    assert "normalizedParentJobId" in progress
    assert "validatedCandidatePreviewRoute" in progress
    assert "trustedEnvelopeProjectId(response)" in progress
    assert "response?.job?.project_id" in progress
    assert "projectId && jobProjectId && projectId !== jobProjectId" in progress
    assert "projectId: envelopeProjectId" in progress
    assert "project_id: safeToken(projectId, 160)" in store

    url_aliases = (
        "preview_url",
        "url",
        "previewUrl",
        "image_asset_preview_url",
        "imageAssetPreviewUrl",
    )
    for alias in url_aliases:
        assert f"candidate.{alias}" in helper
        assert f"item.{alias}" in progress
        assert f"item.{alias}" in previews
        assert f"source.{alias}" in store


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
