const CHARACTER_FIELDS = [
  ["identity", "身份", "28 岁左右的女性私家侦探，神情冷静"],
  ["hair", "发型/毛发/颜色", "黑色短发；或黑色短毛、虎斑纹"],
  ["face", "面部/头部特征", "瓜子脸，左眉尾一道细疤；或额头 M 字纹、眼睛和耳朵特征"],
  ["build", "体态身形", "身形瘦削，约 170cm"],
  ["wardrobe", "服装/饰品/外观", "红色及膝风衣；或不添加人类服装"],
  ["palette", "角色配色", "红黑为主，银色点缀"],
  ["demeanor", "气质神态", "寡言，惯于侧目观察"],
];

const SCENE_FIELDS = [
  ["location", "地点定位", "城市边缘的废弃天文观测站内部"],
  ["layout", "空间结构", "入口在东侧，中央是望远镜基座，西墙整面破玻璃窗"],
  ["props", "关键道具", "翻倒的金属椅，墙上褪色的星图，地面积水"],
  ["lighting_mood", "光线基调", "冷月光从西窗斜入，整体青蓝色调"],
  ["palette", "场景配色", "青蓝 + 锈橙"],
  ["time_weather", "时间天气", "深夜，雨后"],
];

const CHARACTER_LOCK_CHIPS = [
  ["保持发型/毛发", "hair"],
  ["保持服装/外观", "wardrobe"],
  ["保持面部/头部特征", "face"],
  ["不改变体型比例", null],
];

const SCENE_LOCK_CHIPS = [
  ["保持空间布局", "layout"],
  ["保持关键道具", "props"],
  ["保持光线基调", "lighting_mood"],
];

export function lockChipsForAssetType(assetType) {
  return assetType === "character" ? CHARACTER_LOCK_CHIPS : SCENE_LOCK_CHIPS;
}

export function renderVisualAssetPanel(modal, { assetType, node, imageAsset, previous, defaults, drafting = false }) {
  const fields = assetType === "character" ? CHARACTER_FIELDS : SCENE_FIELDS;
  const lockChips = lockChipsForAssetType(assetType);
  modal.innerHTML = `
    <div class="modal-head">
      <div>
        <div class="eyebrow">人工确认</div>
        <h3>固定为${assetType === "character" ? "角色" : "场景"}资产</h3>
      </div>
      <button class="icon-btn" data-action="close" title="关闭">×</button>
    </div>
    <div class="visual-asset-preview">
      ${imageAsset.preview_url ? `<img src="${escapeAttr(imageAsset.preview_url)}" alt="候选资产图">` : ""}
      <div>
        <strong>${escapeHtml(node.title || node.id)}</strong>
        <p>${escapeHtml((node.prompt || node.result || "").slice(0, 160))}</p>
        <small>${escapeHtml(imageAsset.asset_id)}</small>
      </div>
    </div>
    <div class="va-type-row">
      <button class="va-type${assetType === "character" ? " active" : ""}" data-type="character">角色资产</button>
      <button class="va-type${assetType === "scene" ? " active" : ""}" data-type="scene">场景资产</button>
    </div>
    <label class="va-row">名称<input data-field="label" data-drafting="${drafting ? "true" : "false"}" value="${escapeAttr(previous.label || defaults.label || node.title || "")}" placeholder="如：林晚 / 观测站"></label>
    <label class="va-row">一句话签名<input data-field="signature" data-drafting="${drafting ? "true" : "false"}" value="${escapeAttr(previous.signature || defaults.signature || "")}" placeholder="只写最具辨识度的 2-4 个特征，将进入优化提示词"></label>
    <div class="va-section-label">特征卡 <small>逐项填写，生成时全文注入模型；至少填一项</small></div>
    ${fields.map(([key, label, hint]) => `
      <label class="va-row va-feature">${label}<input data-card="${key}" data-drafting="${drafting ? "true" : "false"}" value="${escapeAttr(previous.card?.[key] || defaults.card?.[key] || "")}" placeholder="${escapeAttr(hint)}"></label>
    `).join("")}
    <div class="va-section-label">不可变锁定项 <small>每行一条；生成时强制遵守，可临时解除</small></div>
    <div class="va-lock-chips">
      ${lockChips.map(([label], index) => `<button class="va-chip" data-chip="${index}">+ ${label}</button>`).join("")}
    </div>
    <textarea data-field="negative_locks" data-drafting="${drafting ? "true" : "false"}" rows="3" placeholder="保持黑色短发 / 黑色短毛&#10;保持左眉尾疤痕 / 额头 M 字纹">${escapeHtml(previous.locks || defaults.locks || "")}</textarea>
    <div class="draft-status" data-role="draft-status" hidden></div>
    <div class="va-error" data-role="error" hidden></div>
    <div class="modal-actions">
      <button class="ghost-btn" data-action="draft-card">自动识别草稿</button>
      <button class="ghost-btn" data-action="reject">不采用</button>
      <button class="primary-btn" data-action="fix">确认固定</button>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value || "").replace(
    /[&<>"']/g,
    (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]),
  );
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
