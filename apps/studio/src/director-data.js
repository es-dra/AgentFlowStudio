export const DIRECTOR_OBJECTS = [
  { kind: "camera", label: "镜头/机位" },
  { kind: "subject", label: "人物/主体" },
  { kind: "key_light", label: "Key Light" },
  { kind: "fill_light", label: "Fill Light" },
  { kind: "back_light", label: "Back Light" },
  { kind: "practical_light", label: "Practical Light" },
  { kind: "reflector", label: "反光板" },
  { kind: "diffusion", label: "柔光布" },
  { kind: "flag", label: "遮光旗" },
  { kind: "window_light", label: "窗户光" },
  { kind: "bed", label: "床" },
  { kind: "table", label: "桌" },
  { kind: "door", label: "门" },
  { kind: "window", label: "窗" },
  { kind: "wall", label: "墙" },
  { kind: "poster", label: "海报" },
];

export function createDefaultDirectorSetup() {
  return {
    view: "top_down_2d",
    selectedId: "camera_main",
    activeCameraId: "camera_main",
    activeSubjectIds: ["subject_a"],
    cameras: [{
      id: "camera_main",
      name: "机位1",
      x: 22,
      y: 78,
      angle: -38,
      fov: 50,
      focalLength: 35,
      height: "平视",
      shot: "中景",
      composition: "三分构图",
      lookAt: "主体A",
    }],
    subjects: [{
      id: "subject_a",
      name: "主体A",
      x: 53,
      y: 55,
      angle: 210,
      action: "",
      emotion: "",
      visual_asset_id: "",
    }],
    lights: [],
    modifiers: [],
    props: [],
    composition: "",
    notes: "",
  };
}

function light(kind, name, x, y, angle, intensity, colorTemp, softness, motivated) {
  return { id: kind, kind, name, x, y, angle, intensity, colorTemp, softness, distance: 3.2, motivated };
}

function modifier(kind, name, x, y, angle, influence) {
  return { id: kind, kind, name, x, y, angle, width: 16, influence };
}

function prop(kind, name, x, y, width, height, narrative) {
  return { id: kind, kind, name, x, y, width, height, visible: true, narrative };
}

export function normalizeDirectorSetup(value) {
  const base = createDefaultDirectorSetup();
  if (!value || typeof value !== "object") return base;
  const setup = {
    ...base,
    ...clone(value),
    cameras: normalizeList(value.cameras, base.cameras),
    subjects: normalizeList(value.subjects || value.characters, base.subjects),
    lights: normalizeList(value.lights, base.lights),
    modifiers: normalizeList(value.modifiers, base.modifiers),
    props: normalizeList(value.props, base.props),
  };
  setup.view = "top_down_2d";
  setup.selectedId = setup.selectedId || setup.cameras[0]?.id || "camera_main";
  setup.activeCameraId = setup.activeCameraId || setup.cameras[0]?.id || null;
  setup.activeSubjectIds = Array.isArray(setup.activeSubjectIds)
    ? setup.activeSubjectIds.filter(Boolean)
    : setup.subjects.map((item) => item.id).filter(Boolean);
  return setup;
}

function normalizeList(value, fallback) {
  return Array.isArray(value) ? clone(value) : clone(fallback);
}

export function selectedDirectorObject(setup) {
  const id = setup.selectedId;
  return allDirectorObjects(setup).find((item) => item.object.id === id) || allDirectorObjects(setup)[0];
}

export function allDirectorObjects(setup) {
  return [
    ...setup.cameras.map((object) => ({ group: "camera", object })),
    ...setup.subjects.map((object) => ({ group: "subject", object })),
    ...setup.lights.map((object) => ({ group: "light", object })),
    ...setup.modifiers.map((object) => ({ group: "modifier", object })),
    ...setup.props.map((object) => ({ group: "prop", object })),
  ];
}

export function updateDirectorObjectPosition(setup, id, x, y) {
  const item = allDirectorObjects(setup).find((entry) => entry.object.id === id);
  if (!item) return;
  item.object.x = clamp(Math.round(x), 4, 96);
  item.object.y = clamp(Math.round(y), 4, 96);
}

export function directorCounts(setup) {
  return {
    cameras: setup.cameras.length,
    subjects: setup.subjects.length,
    lights: setup.lights.length,
  };
}

export function directorSummary(setup) {
  const counts = directorCounts(setup);
  return `${counts.cameras} 个机位 / ${counts.subjects} 个主体 / ${counts.lights} 盏灯`;
}

export function directorPromptSummary(setup) {
  const camera = setup.cameras.find((item) => item.id === setup.activeCameraId) || setup.cameras[0];
  const active = new Set(setup.activeSubjectIds || []);
  const subjects = setup.subjects.filter((item) => !active.size || active.has(item.id));
  const lights = setup.lights.map((item) => item.name).filter(Boolean).slice(0, 3).join("、");
  const props = setup.props.filter((item) => item.visible !== false).map((item) => item.name).filter(Boolean).slice(0, 4).join("、");
  return [
    camera ? `生效机位 ${camera.name || camera.id}，${camera.shot || "未设景别"}，${camera.height || "未设高度"}` : "未指定生效机位",
    subjects.length ? `生效主体 ${subjects.map((item) => item.name || item.id).join("、")}` : "未指定生效主体",
    lights ? `灯光 ${lights}` : "",
    props ? `道具 ${props}` : "",
    setup.composition ? `构图意图 ${setup.composition}` : "",
    setup.notes ? `导演备注 ${setup.notes}` : "",
  ].filter(Boolean).join("；");
}

export function safeDirectorSetup(setup) {
  const normalized = normalizeDirectorSetup(setup);
  return {
    view: "top_down_2d",
    activeCameraId: normalized.activeCameraId || null,
    activeSubjectIds: normalized.activeSubjectIds || [],
    characters: normalized.subjects.map(({ id, name, x, y, angle, action, emotion, visual_asset_id }) => ({ id, name, x, y, angle, action, emotion, visual_asset_id })),
    subjects: normalized.subjects.map(({ id, name, x, y, angle, action, emotion, visual_asset_id }) => ({ id, name, x, y, angle, action, emotion, visual_asset_id })),
    lights: normalized.lights.map(({ id, kind, name, x, y, angle, intensity, colorTemp, softness, distance, motivated }) => ({ id, kind, name, x, y, angle, intensity, colorTemp, softness, distance, motivated })),
    cameras: normalized.cameras.map(({ id, name, x, y, angle, fov, focalLength, height, shot, composition, lookAt }) => ({ id, name, x, y, angle, fov, focalLength, height, shot, composition, lookAt })),
    modifiers: normalized.modifiers.map(({ id, kind, name, x, y, angle, width, influence }) => ({ id, kind, name, x, y, angle, width, influence })),
    props: normalized.props.map(({ id, kind, name, x, y, width, height, visible, narrative }) => ({ id, kind, name, x, y, width, height, visible, narrative })),
    composition: normalized.composition || "",
    notes: normalized.notes || "",
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
