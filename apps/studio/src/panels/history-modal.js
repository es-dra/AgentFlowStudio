import { showModal, el } from "../overlay.js";
import { coverGradient } from "../presets/galleries.js";
import { icon } from "../icons.js";

const TABS = [
  { id: "image", label: "图片历史" },
  { id: "video", label: "视频历史" },
  { id: "audio", label: "音频历史" },
];

const KIND_MAP = { image: ["image"], video: ["video", "video_merge"], audio: ["audio"] };

export function openHistoryModal(store) {
  const modal = el("div", "modal");
  let active = "image";

  const head = el("div", "modal-head");
  head.appendChild(el("span", "", "历史资产"));
  head.appendChild(el("span", "head-spacer"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(closeBtn);
  modal.appendChild(head);

  const toolbar = el("div", "history-toolbar");
  const tabsWrap = el("div", "modal-tabs");
  toolbar.appendChild(tabsWrap);
  toolbar.appendChild(el("span", "row-spacer"));
  toolbar.appendChild(el("span", "", "时间降序"));
  toolbar.appendChild(el("span", "", "批量操作"));
  modal.appendChild(toolbar);

  const body = el("div", "modal-body");
  modal.appendChild(body);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);

  function render() {
    tabsWrap.replaceChildren();
    for (const tab of TABS) {
      const assets = assetsFor(tab.id);
      const btn = el("button", `modal-tab${active === tab.id ? " active" : ""}`, `${tab.label}(${assets.length})`);
      btn.addEventListener("click", () => { active = tab.id; render(); });
      tabsWrap.appendChild(btn);
    }
    body.replaceChildren();
    const assets = assetsFor(active);
    if (!assets.length) {
      body.appendChild(el("div", "modal-empty", "暂无历史记录"));
      return;
    }
    const grid = el("div", "card-grid");
    assets.forEach((asset, i) => {
      const card = el("div", "gallery-card");
      const cover = el("div", "card-cover wide");
      const art = el("div", "cover-art");
      art.style.background = coverGradient((i * 47) % 360);
      cover.appendChild(art);
      card.appendChild(cover);
      const name = el("div", "card-name");
      name.appendChild(el("span", "", asset.title));
      card.appendChild(name);
      const meta = el("div", "card-meta");
      meta.appendChild(el("span", "", asset.summary || "（无提示词）"));
      card.appendChild(meta);
      grid.appendChild(card);
    });
    body.appendChild(grid);
  }

  function assetsFor(tabId) {
    const kinds = KIND_MAP[tabId] || [];
    return store.get().assets.filter((a) => kinds.includes(a.kind));
  }

  render();
}
