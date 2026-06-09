export const DEFAULT_WORKSPACE_ID = "Projects";

export const WORKSPACES = [
  {
    id: "Projects",
    label: "项目",
    kicker: "项目",
    summary: "创建、打开和确认当前项目状态。",
  },
  {
    id: "Create",
    label: "创作画布",
    kicker: "画布",
    summary: "组织需求、素材、分镜、审片和记忆复用。",
  },
  {
    id: "Assets",
    label: "素材库",
    kicker: "素材",
    summary: "录入安全素材摘要和参考约束。",
  },
  {
    id: "Storyboard",
    label: "分镜台",
    kicker: "分镜",
    summary: "查看镜头序列、当前卡片和分镜阻塞项。",
  },
  {
    id: "Review",
    label: "审片室",
    kicker: "审片",
    summary: "对候选结果做保留、修改或拒绝。",
  },
  {
    id: "Style Memory",
    label: "项目记忆",
    kicker: "记忆",
    summary: "查看候选记忆、风格约束和下一轮复用。",
  },
  {
    id: "Jobs",
    label: "任务中心",
    kicker: "任务",
    summary: "查看运行任务、阻塞原因和生成能力预检。",
  },
  {
    id: "Settings",
    label: "诊断",
    kicker: "诊断",
    summary: "连接运行服务，查看内部引用和安全边界。",
  },
];

export function workspaceItems(runtimeItems = []) {
  const allowed = new Set(Array.isArray(runtimeItems) && runtimeItems.length ? runtimeItems : WORKSPACES.map((item) => item.id));
  const canonical = WORKSPACES.filter((item) => allowed.has(item.id) || item.id === "Storyboard");
  return canonical.length ? canonical : WORKSPACES;
}

export function workspaceMeta(viewId) {
  return WORKSPACES.find((item) => item.id === viewId) || WORKSPACES[0];
}

export function workspaceLabel(viewId) {
  return workspaceMeta(viewId).label;
}

export function viewActionGroups(activeView) {
  return {
    Projects: ["project", "result"],
    Create: ["scene", "runtime", "result"],
    Assets: ["assets", "scene", "result"],
    Storyboard: ["scene", "runtime", "result"],
    Review: ["review", "runtime", "result"],
    "Style Memory": ["review", "runtime", "result"],
    Jobs: ["runtime", "result"],
    Settings: ["project", "import", "assets", "scene", "review", "runtime", "result"],
  }[activeView] || ["scene", "runtime", "result"];
}
