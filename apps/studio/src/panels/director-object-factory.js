export function addDirectorObject(setup, def) {
  const kind = def.kind;
  const id = `${kind}_${Date.now().toString(36)}`;
  let object;
  let group;

  if (kind === "camera") {
    group = "camera";
    object = { id, kind: "camera", name: "机位", x: 22, y: 78, angle: -35, fov: 50, focalLength: 35, height: "平视", shot: "中景", composition: "", lookAt: "" };
    setup.cameras.push(object);
    setup.activeCameraId = setup.activeCameraId || id;
  } else if (kind === "subject") {
    group = "subject";
    object = { id, kind: "subject", name: "主体", x: 53, y: 55, angle: 210, action: "", emotion: "", visual_asset_id: "" };
    setup.subjects.push(object);
    setup.activeSubjectIds = [...new Set([...(setup.activeSubjectIds || []), id])];
  } else if (kind.includes("light")) {
    group = "light";
    object = { id, kind, name: def.label, x: 36, y: 30, angle: 45, intensity: 60, colorTemp: 4300, softness: 60, distance: 3, motivated: false };
    setup.lights.push(object);
  } else if (["reflector", "diffusion", "flag", "window_light"].includes(kind)) {
    group = "modifier";
    object = { id, kind, name: def.label, x: 45, y: 45, angle: 90, width: 16, influence: "" };
    setup.modifiers.push(object);
  } else {
    group = "prop";
    object = { id, kind, name: def.label, x: 58, y: 58, width: 14, height: 10, visible: true, narrative: "" };
    setup.props.push(object);
  }

  return { group, object };
}
