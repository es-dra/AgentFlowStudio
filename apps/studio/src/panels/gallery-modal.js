import { MOTION_PRESETS, STYLE_PRESETS, STYLE_CATEGORIES, EFFECT_PRESETS, TOOLBOX_PRESETS, coverGradient } from "../presets/galleries.js";
import { showModal, el } from "../overlay.js";
import { icon } from "../icons.js";

const GALLERIES = {
  styles: {
    title: "风格广场",
    tabs: ["风格广场", "我的收藏", "最近使用"],
    filters: STYLE_CATEGORIES,
    items: STYLE_PRESETS,
    wide: false,
    apply(store, nodeId, item) {
      store.set((s) => {
        const n = s.nodes[nodeId];
        if (n) n.params.styleRef = item.name;
      });
    },
  },
  motions: {
    title: "运镜广场",
    tabs: ["运镜广场", "我的收藏", "我的运镜"],
    filters: [],
    items: MOTION_PRESETS,
    wide: false,
    apply(store, nodeId, item) {
      store.set((s) => {
        const n = s.nodes[nodeId];
        if (n) n.params.motion = item.name;
      });
    },
  },
  effects: {
    title: "特效广场",
    tabs: ["特效广场", "我的收藏", "最近使用"],
    filters: ["推荐"],
    items: EFFECT_PRESETS,
    wide: false,
    apply(store, nodeId, item) {
      store.set((s) => {
        const n = s.nodes[nodeId];
        if (n) n.params.effect = item.name;
      });
    },
  },
  toolbox: {
    title: "我的工具箱",
    tabs: ["我的工具箱"],
    filters: [],
    items: TOOLBOX_PRESETS,
    wide: true,
    apply() { /* 工具箱预设在后续里程碑展开为节点组 */ },
  },
};

export function openGalleryModal(store, kind, nodeId) {
  const def = GALLERIES[kind];
  if (!def) return;

  const modal = el("div", "modal");

  const head = el("div", "modal-head");
  const tabs = el("div", "modal-tabs");
  def.tabs.forEach((t, i) => tabs.appendChild(el("button", `modal-tab${i === 0 ? " active" : ""}`, t)));
  head.appendChild(tabs);
  const search = el("div", "modal-search");
  search.innerHTML = icon("search", 13);
  const input = document.createElement("input");
  input.placeholder = `搜索${def.title.replace("广场", "")}名称`;
  search.appendChild(input);
  head.appendChild(search);
  head.appendChild(el("span", "head-spacer"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(closeBtn);
  modal.appendChild(head);

  if (def.filters.length) {
    const filters = el("div", "modal-filters");
    def.filters.forEach((f, i) => filters.appendChild(el("button", `chip${i === 0 ? " active" : ""}`, f)));
    modal.appendChild(filters);
  }

  const body = el("div", "modal-body");
  const grid = el("div", "card-grid");
  body.appendChild(grid);
  modal.appendChild(body);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);

  function renderGrid(keyword = "") {
    grid.replaceChildren();
    const items = def.items.filter((it) => !keyword || it.name.includes(keyword));
    if (!items.length) {
      grid.appendChild(el("div", "modal-empty", "暂无匹配结果"));
      return;
    }
    for (const item of items) {
      const card = el("button", "gallery-card");
      const cover = el("div", `card-cover${def.wide ? " wide" : ""}`);
      const art = el("div", "cover-art");
      art.style.background = coverGradient(item.hue);
      cover.appendChild(art);
      if (item.meta) cover.appendChild(el("span", "cover-tag", item.meta));
      card.appendChild(cover);
      const name = el("div", "card-name");
      name.appendChild(el("span", "", item.name));
      card.appendChild(name);
      if (item.category || item.likes) {
        const meta = el("div", "card-meta");
        meta.appendChild(el("span", "", item.category || ""));
        if (item.likes) meta.appendChild(el("span", "", `收藏 ${item.likes}`));
        card.appendChild(meta);
      }
      card.addEventListener("click", () => {
        def.apply(store, nodeId, item);
        close();
      });
      grid.appendChild(card);
    }
  }

  input.addEventListener("input", () => renderGrid(input.value.trim()));
  renderGrid();
}
