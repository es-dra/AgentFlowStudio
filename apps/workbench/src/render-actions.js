import { badge, button, el, field, sectionTitle, selectField, textareaField } from "./dom.js";
import { PROJECT_TEMPLATES, SOURCE_PRESETS } from "./presets.js";

function projectRows(projects, currentProjectId) {
  if (!Array.isArray(projects) || !projects.length) {
    return [el("p", { className: "muted", text: "No projects loaded." })];
  }
  return projects.map((project) =>
    el("div", { className: "project-row" }, [
      el("div", {}, [
        el("strong", { text: project.project_id || "project" }),
        el("span", { text: project.status || "in_progress" }),
      ]),
      button(project.project_id === currentProjectId ? "Open" : "Load", "select-project", "ghost", {
        projectId: project.project_id,
      }),
    ]),
  );
}

function renderProjectHub(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("Project Hub", `${state.projects.length || 0} loaded`),
    el(
      "div",
      { className: "preset-row" },
      PROJECT_TEMPLATES.map((item) => button(item.label, "apply-project-template", "ghost", { templateId: item.id })),
    ),
    field("Project id", "project-id-action", state.projectId),
    field("Goal", "project-goal", state.projectGoal),
    field("Type", "project-type", state.projectType),
    el("div", { className: "connect-actions" }, [
      button("Create", "create-project", "primary"),
      button("Open", "load-project", "secondary"),
      button("Export", "export-project", "ghost"),
    ]),
    el("div", { className: "project-list" }, projectRows(state.projects, state.projectId)),
    textareaField("Import manifest JSON", "import-manifest-json", state.importManifestJson, { rows: "5" }),
    button("Import", "import-project", "secondary"),
  ]);
}

function renderRuntimeActions(state) {
  const lastRoundOne = state.latestAssetTestJobId || "pending";
  return el("section", { className: "action-group" }, [
    sectionTitle("Run Controls", lastRoundOne),
    field("Asset profile seed", "asset-profile-seed", state.assetProfileSeed),
    field("Promotion decision", "promotion-decision", state.promotionDecision),
    textareaField("Promotion rationale", "promotion-rationale", state.promotionRationale, { rows: "3" }),
    textareaField("Review note", "feedback-note", state.feedbackNote, { rows: "4" }),
    el("div", { className: "action-stack" }, [
      button("First Check", "run-asset-test", "primary"),
      button("Record Review", "record-feedback", "secondary"),
      button("Next Round", "run-two-round", "secondary"),
      button("Provider Preflight", "run-provider-preflight", "ghost"),
    ]),
  ]);
}

function renderReviewRoom(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("Decision Controls", "keep / revise / reject"),
    selectField("Decision", "review-decision", state.reviewDecision, [
      { value: "keep", label: "Keep" },
      { value: "revise", label: "Revise" },
      { value: "reject", label: "Reject" },
    ]),
    textareaField("Decision note", "review-decision-note", state.reviewDecisionNote, { rows: "3" }),
    button("Mark Selected", "record-review-decision", "secondary"),
  ]);
}

function renderAssetLibrary(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("Asset Library", "safe summaries"),
    el(
      "div",
      { className: "preset-row" },
      SOURCE_PRESETS.map((item) => button(item.label, "apply-source-preset", "ghost", { sourcePresetId: item.id })),
    ),
    field("Asset id", "source-asset-id", state.sourceAssetId),
    field("Asset type", "source-asset-type", state.sourceAssetType),
    field("Label", "source-asset-label", state.sourceAssetLabel),
    textareaField("Summary", "source-asset-summary", state.sourceAssetSummary, { rows: "3" }),
    button("Add Asset", "register-source-asset", "secondary"),
  ]);
}

function renderScenePlanner(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("Scene Planner", "content cards"),
    field("Card id", "scene-card-id", state.sceneCardId),
    field("Card type", "scene-card-type", state.sceneCardType),
    field("Title", "scene-title", state.sceneTitle),
    field("Target", "scene-target-platform", state.sceneTargetPlatform),
    textareaField("Summary", "scene-summary", state.sceneSummary, { rows: "3" }),
    el("div", { className: "connect-actions" }, [
      button("Draft Canvas", "draft-canvas", "primary"),
      button("Add Scene", "register-content-card", "secondary"),
    ]),
  ]);
}

function renderLastResult(result) {
  if (!result) return el("p", { className: "muted", text: "No action result yet." });
  const title = result.job && result.job.action ? `${result.job.action}: ${result.job.status}` : result.kind || "result";
  return el("div", { className: "result-box" }, [
    el("strong", { text: title }),
    result.job && result.job.job_id ? el("code", { text: result.job.job_id }) : null,
  ]);
}

export function renderActionPanel(state, groups = ["project", "assets", "scene", "review", "runtime", "result"]) {
  return el("aside", { className: "action-panel" }, [
    groups.includes("project") ? renderProjectHub(state) : null,
    groups.includes("assets") ? renderAssetLibrary(state) : null,
    groups.includes("scene") ? renderScenePlanner(state) : null,
    groups.includes("review") ? renderReviewRoom(state) : null,
    groups.includes("runtime") ? renderRuntimeActions(state) : null,
    groups.includes("result")
      ? el("section", { className: "action-group" }, [
          sectionTitle("Last Result", state.lastResult ? "ready" : "empty"),
          renderLastResult(state.lastResult),
          state.selectedArtifactId ? badge(`artifact ${state.selectedArtifactId}`, "ready") : null,
        ])
      : null,
  ]);
}
