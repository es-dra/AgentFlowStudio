import { CAMERA_BODIES, CAMERA_LENSES, CAMERA_FOCALS, CAMERA_APERTURES, defaultCameraSetup } from "../presets/cameras.js";
import { showPopover, el } from "../overlay.js";

export function openCameraPopover(store, node, anchorEl) {
  const setup = { ...(node.params.camera || defaultCameraSetup()) };
  const pop = el("div", "camera-pop");

  const title = el("div", "cam-title");
  title.appendChild(el("span", "", "摄像机"));
  pop.appendChild(title);

  const cols = el("div", "cam-cols");
  cols.appendChild(column("相机", CAMERA_BODIES, setup.body, (v) => { setup.body = v; }));
  cols.appendChild(column("镜头", CAMERA_LENSES, setup.lens, (v) => { setup.lens = v; }));
  cols.appendChild(column("焦距", CAMERA_FOCALS, setup.focal, (v) => { setup.focal = v; }, "mm"));
  cols.appendChild(column("光圈", CAMERA_APERTURES, setup.aperture, (v) => { setup.aperture = v; }));
  pop.appendChild(cols);

  const actions = el("div", "cam-actions");
  const useBtn = el("button", "cam-use-btn", "使用");
  useBtn.addEventListener("click", () => {
    store.set((s) => {
      const n = s.nodes[node.id];
      if (n) n.params.camera = setup;
    });
    close();
  });
  actions.appendChild(useBtn);
  pop.appendChild(actions);

  const close = showPopover(anchorEl, pop, { place: "top" });
}

function column(label, options, current, onPick, unit = "") {
  const col = el("div", "cam-col");
  const box = el("div", "cam-box");
  box.appendChild(el("div", "", label));
  const value = el("div", "cam-value", short(current) + unit);
  box.appendChild(value);
  col.appendChild(box);
  const select = document.createElement("select");
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt + unit;
    if (opt === current) o.selected = true;
    select.appendChild(o);
  }
  select.addEventListener("change", () => {
    onPick(select.value);
    value.textContent = short(select.value) + unit;
  });
  col.appendChild(select);
  return col;
}

function short(text) {
  return String(text).length > 12 ? `${String(text).slice(0, 11)}…` : String(text);
}
