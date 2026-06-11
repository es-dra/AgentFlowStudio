export const DEFAULT_WORKSPACE_ID = "Projects";

export const WORKSPACES = [
  {
    id: "Projects",
    label: "首页",
    kicker: "创作门户",
    summary: "浏览最近项目、灵感案例和创作模板。",
  },
  {
    id: "Create",
    label: "创作画布",
    kicker: "无限画布",
    summary: "用节点组织剧本、角色、关键帧、导演台和视频片段。",
  },
  {
    id: "Assets",
    label: "资产库",
    kicker: "显性资产",
    summary: "查看可复用的人物、场景、关键帧、视频和导演台资产。",
  },
];

export function workspaceItems() {
  return WORKSPACES;
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
    Create: ["scene", "result"],
    Assets: ["assets", "scene", "result"],
  }[activeView] || ["scene", "result"];
}
