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
      action: "坐姿",
      emotion: "低落",
    }],
    lights: [
      light("key_light", "Key Light", 34, 30, 45, 78, 4300, 68, true),
      light("fill_light", "Fill Light", 74, 42, 190, 38, 5600, 82, false),
      light("back_light", "Back Light", 56, 22, 120, 48, 5200, 42, false),
    ],
    modifiers: [
      modifier("reflector", "反光板", 68, 52, 180, "回收面部暗部"),
      modifier("flag", "遮光旗", 26, 50, 90, "压暗背景墙"),
    ],
    props: [
      prop("bed", "床", 58, 68, 28, 14, "主体坐位"),
      prop("window", "窗", 82, 28, 18, 8, "冷色窗外光"),
      prop("poster", "海报", 76, 46, 12, 8, "角色身份线索"),
      prop("door", "门", 18, 40, 10, 20, "入画方向"),
      prop("wall", "墙", 50, 18, 74, 5, "背景边界"),
    ],
    composition: "主体偏左，窗户光和海报形成右侧叙事信息",
    notes: "暗调房间，主光来自床侧，保留墙上海报作为情绪线索。",
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
  return setup;
}

function normalizeList(value, fallback) {
  return Array.isArray(value) && value.length ? clone(value) : clone(fallback);
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
  const camera = setup.cameras[0];
  const subject = setup.subjects[0];
  const lights = setup.lights.map((item) => `${item.name} ${item.intensity}% ${item.colorTemp}K`).join("；");
  const props = setup.props.filter((item) => item.visible !== false).map((item) => `${item.name}:${item.narrative || "可见"}`).join("；");
  return [
    camera ? `机位 ${camera.name}，${camera.shot}，${camera.height}，FOV ${camera.fov}，构图 ${camera.composition}` : "",
    subject ? `主体 ${subject.name} 位于画面 ${subject.x}/${subject.y}，朝向 ${subject.angle}°，动作 ${subject.action}，情绪 ${subject.emotion}` : "",
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
    characters: normalized.subjects.map(({ id, name, x, y, angle, action, emotion }) => ({ id, name, x, y, angle, action, emotion })),
    subjects: normalized.subjects.map(({ id, name, x, y, angle, action, emotion }) => ({ id, name, x, y, angle, action, emotion })),
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
