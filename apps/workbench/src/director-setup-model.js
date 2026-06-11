export const DIRECTOR_STAGE_ELEMENTS = [
  { id: "camera-a", label: "Camera A", kind: "camera", className: "libtv-director-camera", x: 18, y: 62, summary: "35mm / 低机位 / 中近景", props: { lens: "35mm", height: "1.2m", fov: "50°", target: "角色 A" } },
  { id: "subject-a", label: "角色 A", kind: "subject", className: "libtv-director-role", x: 58, y: 48, summary: "坐姿 / 面向窗户 / 情绪低落", props: { pose: "坐姿", facing: "窗户冷光", action: "低头停顿" } },
  { id: "key-light", label: "Key Light", kind: "light", className: "libtv-director-light key-light", x: 42, y: 18, summary: "强度 70 / 色温 4300K / 柔硬 60", props: { intensity: "70%", color: "4300K", softness: "Soft 60", angle: "45°" } },
  { id: "fill-light", label: "Fill Light", kind: "light", className: "libtv-director-light fill-light", x: 22, y: 58, summary: "强度 25 / 色温 5000K / 柔硬 80", props: { intensity: "25%", color: "5000K", softness: "Soft 80", angle: "30°" } },
  { id: "back-light", label: "Back Light", kind: "light", className: "libtv-director-light back-light", x: 74, y: 24, summary: "强度 35 / 色温 5600K / 柔硬 45", props: { intensity: "35%", color: "5600K", softness: "Soft 45", angle: "120°" } },
  { id: "practical-light", label: "Practical", kind: "light", className: "libtv-director-light practical-light", x: 80, y: 70, summary: "暖色台灯 / 20% / 动机光", props: { intensity: "20%", color: "3000K", softness: "Hard 35", angle: "床头灯" } },
  { id: "reflector-a", label: "反光板", kind: "modifier", className: "libtv-director-modifier reflector", x: 34, y: 36, summary: "左侧弱反射，保留眼神光", props: { type: "银白反光", distance: "1.6m" } },
  { id: "flag-a", label: "遮光旗", kind: "modifier", className: "libtv-director-modifier flag", x: 10, y: 44, summary: "压暗床尾和背景左侧", props: { type: "黑旗", distance: "1.1m" } },
  { id: "bed-a", label: "床", kind: "prop", className: "libtv-director-prop bed", x: 68, y: 40, summary: "主体坐在床边，形成三角构图", props: { type: "单人床", material: "浅色床品" } },
  { id: "window-a", label: "窗户光", kind: "prop", className: "libtv-director-prop window", x: 12, y: 18, summary: "冷色环境光来源", props: { type: "窗户", color: "冷蓝" } },
  { id: "poster-a", label: "海报", kind: "prop", className: "libtv-director-prop poster", x: 82, y: 16, summary: "墙面识别点，辅助角色记忆", props: { type: "墙面海报", color: "低饱和" } },
];

export function directorElements(state = {}) {
  const saved = state.directorElementOverrides || {};
  return DIRECTOR_STAGE_ELEMENTS.map((item) => ({ ...item, ...(saved[item.id] || {}) }));
}

export function selectedDirectorElement(state = {}) {
  const selectedId = state.directorSelectedElementId || "camera-a";
  return directorElements(state).find((item) => item.id === selectedId) || directorElements(state)[0];
}

export function directorSetupAsset(state = {}) {
  const elements = directorElements(state);
  const selected = selectedDirectorElement(state);
  return {
    asset_id: state.directorSavedSetupId || "director-setup-live",
    asset_type: "director_setup",
    title: "导演台布光图",
    thumbnail_ref: "director_setup_live_thumbnail_ref",
    linked_shot_id: "镜头 01",
    status: state.directorSaveStatus || "本地预览",
    created_at: "2026-06-11",
    safe_summary: `${selected.label} 已调整；${lightSummary(elements)}；机位 ${cameraSummary(elements)}`,
  };
}

export function directorPromptContext(state = {}) {
  const elements = directorElements(state);
  return [
    "二维导演台布置：",
    ...elements.map((item) => `${item.label}(${Math.round(item.x)}%, ${Math.round(item.y)}%): ${item.summary}`),
  ].join("\n");
}

function lightSummary(elements) {
  return elements.filter((item) => item.kind === "light").map((item) => item.label).join(" / ");
}

function cameraSummary(elements) {
  const camera = elements.find((item) => item.kind === "camera");
  return camera ? `${Math.round(camera.x)}%, ${Math.round(camera.y)}%` : "已设置";
}
