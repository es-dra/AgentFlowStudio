import { badge, button, el, field, sectionTitle, selectField, textareaField } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";
import { PROJECT_TEMPLATES, SOURCE_PRESETS } from "./presets.js";

function projectRows(projects, currentProjectId) {
  if (!Array.isArray(projects) || !projects.length) {
    return [el("p", { className: "muted", text: "还没有从运行服务读取到项目。" })];
  }
  return projects.map((project) =>
    el("div", { className: "project-row" }, [
      el("div", {}, [
        el("strong", { text: projectTitle(project) }),
        el("span", { text: displayStatus(project.status || "in_progress") }),
        el("span", { className: "muted", text: projectMeta(project) }),
      ]),
      button(project.project_id === currentProjectId ? "已选中" : "打开", "select-project", "ghost", {
        projectId: project.project_id,
      }),
    ]),
  );
}

function projectTitle(project) {
  const title = displayText(project.goal || project.project_type || "内容项目");
  const questionMarks = (title.match(/\?/g) || []).length;
  if (questionMarks >= 6) return "历史演练项目";
  return title.includes("Stage 7 RC") ? "验收演练项目" : title;
}

function projectMeta(project) {
  const type = displayText(project.project_type || "short_video_campaign");
  const runs = Number(project.run_count || 0);
  const feedback = Number(project.feedback_count || 0);
  const memory = Number(project.profile_version_count || 0);
  return `${type} · ${runs} 次运行 · ${feedback} 条审片 · ${memory} 个记忆版本`;
}

function renderProjectHub(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("项目设置向导", `${state.projects.length || 0} 个已加载项目`),
    el("ol", { className: "wizard-steps" }, [
      el("li", { text: "选择内容项目类型" }),
      el("li", { text: "确认本轮制作目标" }),
      el("li", { text: "创建项目并进入创作画布" }),
    ]),
    el(
      "div",
      { className: "preset-row" },
      PROJECT_TEMPLATES.map((item) => button(item.label, "apply-project-template", "ghost", { templateId: item.id })),
    ),
    field("项目 ID", "project-id-action", state.projectId),
    field("本轮目标", "project-goal", state.projectGoal),
    field("项目类型", "project-type", state.projectType),
    el("div", { className: "connect-actions" }, [
      button("创建项目", "create-project", "primary"),
      button("打开项目", "load-project", "secondary"),
      button("导出档案", "export-project", "ghost"),
    ]),
    el("div", { className: "project-list" }, projectRows(state.projects, state.projectId)),
  ]);
}

function renderProjectImport(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("导入项目档案", "诊断入口"),
    textareaField("Manifest JSON", "import-manifest-json", state.importManifestJson, { rows: "5" }),
    button("导入", "import-project", "secondary"),
  ]);
}

function renderRuntimeActions(state) {
  const lastRoundOne = state.latestAssetTestJobId ? "首轮证据已记录" : "待运行";
  return el("section", { className: "action-group" }, [
    sectionTitle("制作运行控制", lastRoundOne),
    el("div", { className: "action-stack" }, [
      button("首轮检查", "run-asset-test", "primary"),
      button("记录反馈", "record-feedback", "secondary"),
      button("进入下一轮", "run-two-round", "secondary"),
      button("Provider 预检", "run-provider-preflight", "ghost"),
    ]),
    el("details", { className: "advanced" }, [
      el("summary", { text: "高级运行参数" }),
      field("资产档案种子", "asset-profile-seed", state.assetProfileSeed),
      field("晋升决定", "promotion-decision", state.promotionDecision),
      textareaField("晋升理由", "promotion-rationale", state.promotionRationale, { rows: "3" }),
      textareaField("审片反馈", "feedback-note", state.feedbackNote, { rows: "4" }),
    ]),
  ]);
}

function renderReviewRoom(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("审片决定", "保留 / 修改 / 拒绝"),
    selectField("决定", "review-decision", state.reviewDecision, [
      { value: "keep", label: "保留" },
      { value: "revise", label: "修改" },
      { value: "reject", label: "拒绝" },
    ]),
    textareaField("决定说明", "review-decision-note", state.reviewDecisionNote, { rows: "3" }),
    button("标记当前候选", "record-review-decision", "secondary"),
  ]);
}

function renderAssetLibrary(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("素材摘要", "安全摘要"),
    el(
      "div",
      { className: "preset-row" },
      SOURCE_PRESETS.map((item) => button(item.label, "apply-source-preset", "ghost", { sourcePresetId: item.id })),
    ),
    field("素材 ID", "source-asset-id", state.sourceAssetId),
    field("素材类型", "source-asset-type", state.sourceAssetType),
    field("素材名称", "source-asset-label", state.sourceAssetLabel),
    textareaField("摘要", "source-asset-summary", state.sourceAssetSummary, { rows: "3" }),
    button("添加素材摘要", "register-source-asset", "secondary"),
  ]);
}

function renderScenePlanner(state) {
  return el("section", { className: "action-group" }, [
    sectionTitle("分镜草稿", "内容卡片"),
    field("卡片 ID", "scene-card-id", state.sceneCardId),
    field("卡片类型", "scene-card-type", state.sceneCardType),
    field("标题", "scene-title", state.sceneTitle),
    field("目标平台", "scene-target-platform", state.sceneTargetPlatform),
    textareaField("摘要", "scene-summary", state.sceneSummary, { rows: "3" }),
    el("div", { className: "connect-actions" }, [
      button("生成画布草稿", "draft-canvas", "primary"),
      button("添加分镜卡", "register-content-card", "secondary"),
    ]),
  ]);
}

function renderLastResult(result) {
  if (!result) return el("p", { className: "muted", text: "还没有操作结果。" });
  const title = result.job && result.job.action
    ? `${displayText(result.job.action)}：${displayStatus(result.job.status)}`
    : displayText(result.kind || "result");
  const flow = result.flow || null;
  return el("div", { className: "result-box" }, [
    el("strong", { text: title }),
    result.job && result.job.job_id ? badge("运行证据已记录", "ready") : null,
    flow
      ? el("div", { className: "result-flow" }, [
          badge(displayStatus(flow.project_status || "in_progress"), flow.target_achieved ? "ready" : "quiet"),
          badge(`下一步：${displayText(flow.current_action_label || flow.current_action, "继续")}`, "active"),
        ])
      : null,
  ]);
}

export function renderActionPanel(state, groups = ["project", "assets", "scene", "review", "runtime", "result"]) {
  return el("aside", { className: "action-panel" }, [
    groups.includes("project") ? renderProjectHub(state) : null,
    groups.includes("import") ? renderProjectImport(state) : null,
    groups.includes("assets") ? renderAssetLibrary(state) : null,
    groups.includes("scene") ? renderScenePlanner(state) : null,
    groups.includes("review") ? renderReviewRoom(state) : null,
    groups.includes("runtime") ? renderRuntimeActions(state) : null,
    groups.includes("result")
      ? el("section", { className: "action-group" }, [
          sectionTitle("最近结果", state.lastResult ? displayStatus("ready") : "empty"),
          renderLastResult(state.lastResult),
          state.selectedArtifactId ? badge("已选择安全产物", "ready") : null,
        ])
      : null,
  ]);
}
