import { icon } from "../icons.js";
import { showModal, el } from "../overlay.js";
import { createManualShotAssetNode } from "../shot-asset-nodes.js";
import { structuredShotFromSegment } from "../structured-shot.js";

export function openAddAssetModal(store, scriptNode) {
  const modal = el("div", "modal compact add-asset-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "新增资产"));
  head.appendChild(el("span", "head-spacer"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(closeBtn);

  const body = el("div", "modal-body");
  const field = el("label", "modal-field");
  field.appendChild(el("span", "", "资产名称"));
  const input = document.createElement("input");
  input.placeholder = "如 金刚狼 / 金箍棒 / 山巅石台战场";
  input.maxLength = 40;
  field.appendChild(input);
  const error = el("div", "modal-error");
  error.hidden = true;
  body.append(field, error);

  const actions = el("div", "modal-actions");
  const cancel = el("button", "ghost-btn", "取消");
  const confirm = el("button", "primary-btn", "创建资产");
  actions.append(cancel, confirm);
  modal.append(head, body, actions);

  const close = showModal(modal);
  const submit = () => {
    const fresh = store.get().nodes[scriptNode.id] || scriptNode;
    const label = sanitizeAssetLabel(input.value);
    if (!fresh) {
      showError(error, "当前分镜已不存在。");
      return;
    }
    if (!label) {
      showError(error, "请输入资产名称。");
      input.focus();
      return;
    }
    const context = scriptContext(fresh);
    const structuredShot = fresh.params?.structuredShot || structuredShotFromSegment(context, Number(fresh.params?.scriptSegmentIndex || 1));
    const assetType = inferManualAssetType(label, context, structuredShot);
    createManualShotAssetNode(store, fresh, assetType, label);
    close();
  };

  closeBtn.addEventListener("click", close);
  cancel.addEventListener("click", close);
  confirm.addEventListener("click", submit);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") submit();
    if (event.key === "Escape") close();
  });
  setTimeout(() => input.focus(), 0);
}

export function inferManualAssetType(label, context = "", structuredShot = null) {
  const normalized = normalizeLabel(label);
  const refs = Array.isArray(structuredShot?.asset_refs)
    ? structuredShot.asset_refs
    : structuredShotFromSegment(context, 1).asset_refs || [];
  const matched = refs.find((ref) => normalizeLabel(ref?.label) === normalized);
  if (matched?.asset_type && ["character", "scene", "prop"].includes(matched.asset_type)) return matched.asset_type;

  const labelText = String(label || "");
  if (/(金箍棒|棒|剑|刀|枪|地图|帽|鸭舌帽|信|照片|钥匙|道具|武器|法杖|权杖|项链|戒指)/u.test(labelText)) return "prop";
  if (/(场景|战场|山巅|屋顶|街道|街区|森林|城市|房间|室内|室外|海边|天空|宫殿|山谷|平台|广场|空间|地点|背景)/u.test(labelText)) return "scene";
  if (/(孙悟空|金刚狼|主角|女孩|女生|男子|男人|女人|角色|人物|机器人|少年|少女|老人|儿童|武士|英雄|反派)/u.test(labelText)) return "character";
  return "character";
}

function scriptContext(node) {
  return [
    node.content,
    node.prompt,
    node.params?.structuredShot?.description,
    node.params?.structuredShot?.source_text,
  ].filter(Boolean).join("\n");
}

function sanitizeAssetLabel(value) {
  return String(value || "").replace(/^@+/, "").replace(/[<>]/g, "").trim().slice(0, 40);
}

function normalizeLabel(value) {
  return String(value || "").replace(/^@+/, "").trim().toLowerCase();
}

function showError(error, message) {
  error.hidden = false;
  error.textContent = message;
}
