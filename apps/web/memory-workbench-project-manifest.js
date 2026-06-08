import { action, arrayValue, card, control, lane, step } from "./memory-workbench-production-assets-shared.js";

const PROJECT_MANIFEST_TYPE = "agentflow_project_manifest";

export function buildProjectManifestView(workspace, fallback) {
  const artifact = workspace?.agentflowProjectManifest;
  if (!artifact || artifact.payload?.artifact_type !== PROJECT_MANIFEST_TYPE) return fallback;

  const payload = artifact.payload;
  const runs = arrayValue(payload.runs);
  const packages = arrayValue(payload.packages);
  const feedbackRefs = arrayValue(payload.feedback_refs);
  const profileVersions = arrayValue(payload.profile_version_refs);
  const sourceAssets = arrayValue(payload.source_assets);
  const ready = payload.status !== "blocked";

  return {
    ...fallback,
    state: ready ? "project manifest ready" : "blocked",
    project: {
      title: payload.project_name || payload.project_id || artifact.fileName,
      brief: `${payload.project_type || "project"}: ${payload.goal || payload.project_goal || "goal not recorded"}`,
      format: PROJECT_MANIFEST_TYPE,
      route: "selected local JSON only; read-only local project workbench",
    },
    workflow_actions: [
      action("inspect_project_manifest", "Inspect project", ready ? "review ready" : "blocked", "project"),
      action("inspect_runs", "Inspect runs", runs.length ? "ready" : "missing", "memory-loaded"),
      action("inspect_packages", "Inspect packages", packages.length ? "ready" : "missing", "assets"),
      action("inspect_reusable_context", "Inspect context refs", profileVersions.length ? "ready" : "missing", "next-pass"),
    ],
    assets: [
      ...sourceAssets.map((item) => refAsset(item, "source asset")),
      ...packages.map((item) => refAsset(item, "package")),
    ],
    bundle_summary: [
      card("project_runs", "Runs", runs.length ? "review ready" : "missing", `${runs.length} run refs`),
      card("project_packages", "Packages", packages.length ? "review ready" : "missing", `${packages.length} package refs`),
      card("project_feedback", "Feedback refs", feedbackRefs.length ? "review ready" : "missing", `${feedbackRefs.length} feedback refs`),
      card("project_profile_versions", "Profile versions", profileVersions.length ? "review ready" : "missing", `${profileVersions.length} profile version refs`),
    ],
    memory_loaded: [
      ...runs.map((item) => projectMemory(item, "run")),
      ...feedbackRefs.map((item) => projectMemory(item, "feedback")),
      ...profileVersions.map((item) => projectMemory(item, "profile version")),
    ],
    lanes: [
      lane("project-runs", "Project runs", runs.length ? "review ready" : "missing", payload.project_id, `${runs.length} runs`),
      lane("project-packages", "Packages", packages.length ? "review ready" : "missing", payload.project_id, `${packages.length} packages`),
      lane("project-feedback", "Feedback refs", feedbackRefs.length ? "review ready" : "missing", payload.project_id, `${feedbackRefs.length} refs`),
      lane("project-profile-versions", "Profile versions", profileVersions.length ? "review ready" : "missing", payload.project_id, `${profileVersions.length} refs`),
    ],
    protocol_summary: {
      title: "AgentFlow project manifest v0.1",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no database", payload.does_not_create_database === true),
        control("no account", payload.does_not_create_account === true),
        control("no automatic sync", payload.does_not_auto_sync === true),
        control("no private asset bytes", payload.does_not_store_private_asset_bytes === true),
        control("no secrets", payload.does_not_store_secrets === true),
      ],
      boundaries: [
        { label: "local JSON contract only", status: "blocked", detail: "not a database or SaaS workspace" },
        { label: "does not copy run output content", status: "blocked", detail: "references artifacts by logical refs" },
        { label: "not business validation", status: "blocked", detail: "project status is local runtime status only" },
      ],
    },
    review: {
      storyboard_adherence: `${runs.length} run refs`,
      visual_consistency: `${profileVersions.length} profile version refs`,
      boundary: "project manifest only / no database / no account / no automatic sync",
    },
    feedback: {
      status: feedbackRefs.length ? "review ready" : "missing",
      summary: "Feedback refs are reusable evidence links; they do not auto-promote memory.",
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "open_referenced_package_or_next_round" : "resolve_project_manifest_blockers",
    },
    timeline: [
      step("Manifest", ready ? "ready" : "blocked", payload.project_id),
      step("Runs", runs.length ? "review ready" : "missing", `${runs.length} refs`),
      step("Packages", packages.length ? "review ready" : "missing", `${packages.length} refs`),
      step("Context reuse", profileVersions.length ? "review ready" : "missing", `${profileVersions.length} profile versions`),
    ],
  };
}

function refAsset(item, fallbackKind) {
  return {
    id: refId(item, fallbackKind),
    label: refId(item, fallbackKind),
    detail: objectValue(item).ref || fallbackKind,
    status: objectValue(item).status || "review ready",
  };
}

function projectMemory(item, kind) {
  const object = objectValue(item);
  const id = refId(item, kind);
  return {
    id,
    title: id,
    why_eligible: `${kind} referenced by project manifest`,
    source_evidence_refs: object.ref ? [object.ref] : [],
    promotion_status: object.status || "referenced",
    request_projection: object.run_id || object.profile_id || object.package_id || kind,
    feedback_effect: "project manifest links refs only; it does not copy output content or promote memory",
    status: object.status === "blocked" ? "blocked" : "review ready",
  };
}

function refId(item, fallback) {
  const object = objectValue(item);
  return String(
    object.run_id
      || object.package_id
      || object.feedback_id
      || object.profile_version_id
      || object.profile_id
      || object.asset_id
      || item
      || fallback,
  );
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export { PROJECT_MANIFEST_TYPE };
