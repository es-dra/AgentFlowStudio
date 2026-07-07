import { el, showPopover } from "../overlay.js";
import { icon } from "../icons.js";
import { duplicateNode, deleteNodes } from "../nodes.js";
import { qualityFeedbackView } from "../quality-feedback.js";
import {
  cancelNodeVideoGeneration,
  enableVideoRevisionDraft,
  fixNodeVisualAsset,
  createStoryboardKeyframeLayer,
  pollNodeVideoGeneration,
  identifyScriptAssets,
  setNodeVideoFrame,
  startNodeGeneration,
  uploadNodeImage,
} from "../node-actions.js";
import { canContinueKeyframeToVideo, createVideoNodeFromKeyframe } from "../keyframe-video-continuation.js";
import {
  ASSET_REFERENCE_MODES,
  assetReferenceMode,
  canUseAssetReferenceMode,
} from "../asset-revision-references.js";
import {
  expandTextIdeaToScript,
  importScriptFileIntoTextNode,
  splitTextNodeToStoryboardNodes,
} from "../script-breakdown.js";
import { openAddAssetModal } from "./add-asset-modal.js";
import { openAssetCardPanel } from "./asset-card-panel.js";
import { openRetireAssetModal } from "./drawer-asset-actions.js";

const VIDEO_REVISION_DRAFT_MARKER = "video-revision-draft";

export function openNodeMenu(store, runtime, nodeId, anchorOrPoint) {
  const node = store.get().nodes[nodeId];
  if (!node) return;
  const pop = el("div");
  pop.style.minWidth = "188px";
  const anchor = resolveAnchor(anchorOrPoint);

  addItem("pencil", "重命名", () => renameNode(store, nodeId, anchor.point || anchor.el));
  addItem("copy", "复制节点", () => duplicateNode(store, nodeId));
  addItem(node.collapsed ? "chevronDown" : "chevronUp", node.collapsed ? "展开" : "折叠", () =>
    store.set((s) => { const n = s.nodes[nodeId]; if (n) n.collapsed = !n.collapsed; }));
  addItem("retry", "重试生成", () => {
    const fresh = store.get().nodes[nodeId];
    if (fresh) startNodeGeneration(store, runtime, fresh);
  });
  if (node.type === "text") {
    addItem("upload", "导入/替换剧本", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) importScriptFileIntoTextNode(store, fresh);
    });
    addItem("sparkles", "扩写当前文本", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) expandTextIdeaToScript(store, runtime, fresh);
    });
    addItem("frames", "拆分为分镜", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) splitTextNodeToStoryboardNodes(store, fresh, runtime);
    });
  }
  if (node.type === "image") {
    if (node.params?.assetCardDraft) {
      addItem("pencil", "编辑资产卡", () => openAssetCardPanel(store, nodeId, runtime));
      addItem("bolt", "生成资产图", () => {
        const fresh = store.get().nodes[nodeId];
        if (fresh) startNodeGeneration(store, runtime, fresh);
      });
    }
    if (node.params?.nodeRole === "keyframe_generation" && node.params?.keyframeAssetPlan) {
      addItem("pencil", "编辑关键帧资产约束", () => {
        const fresh = store.get().nodes[nodeId];
        if (!fresh) return;
        store.set((s) => {
          s.selection = { nodeIds: [fresh.id], edgeId: null };
          s.ui.promptBarNodeId = fresh.id;
        }, { history: false, persist: false });
        window.dispatchEvent(new CustomEvent("afs:studio-open-generation-panel", { detail: { node_id: fresh.id, node: fresh } }));
      });
    }
    addItem("upload", "上传/替换参考图", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) uploadNodeImage(store, runtime, fresh);
    });
    if (canUseAssetReferenceMode(node)) {
      addItem("wand", referenceModeMenuLabel(node), () => toggleReferenceMode(store, nodeId));
    }
    addItem("bookmark", "标记为角色/场景/道具资产", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) fixNodeVisualAsset(store, runtime, fresh);
    });
    const fixedAsset = activeFixedVisualAsset(node);
    if (fixedAsset) {
      addItem("x", "取消固定资产", () => openRetireAssetModal(store, runtime, fixedAsset));
    }
    if (canContinueKeyframeToVideo(node)) {
      addItem("video", "接续视频节点", () => {
        const fresh = store.get().nodes[nodeId];
        if (fresh) createVideoNodeFromKeyframe(store, fresh);
      });
    }
    if (node.status === "complete" && (node.previewUrl || node.result)) {
      addItem("sparkles", "反馈图片质量", () => {
        const fresh = store.get().nodes[nodeId];
        if (fresh) openQualityFeedbackMenu(fresh, anchor.point || anchor.el);
      });
    }
  }
  if (node.type === "video") {
    addItem("upload", "上传首帧/尾帧图片", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) uploadNodeImage(store, runtime, fresh);
    });
    addItem("frames", "设最近上传图为首帧", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) setNodeVideoFrame(store, fresh, "first");
    });
    addItem("frames", "设最近上传图为尾帧", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) setNodeVideoFrame(store, fresh, "last");
    });
    addItem("frames", "识别视频资产卡", () => requestVideoAssetCardDraft(store, nodeId));
    if (node.params?.lastVideoJobId) {
      addItem("pencil", "创建视频修改草稿", () => {
        void VIDEO_REVISION_DRAFT_MARKER;
        const fresh = store.get().nodes[nodeId];
        if (fresh) enableVideoRevisionDraft(store, fresh);
      });
      addItem("retry", "继续轮询视频任务", () => {
        const fresh = store.get().nodes[nodeId];
        if (fresh) pollNodeVideoGeneration(store, runtime, fresh);
      });
      if (node.status === "generating") {
        addItem("x", "本地取消轮询", () => {
          const fresh = store.get().nodes[nodeId];
          if (fresh) cancelNodeVideoGeneration(store, runtime, fresh);
        });
      }
    }
    if (node.status === "complete" && (node.previewUrl || node.result)) {
      addItem("sparkles", "反馈视频质量", () => {
        const fresh = store.get().nodes[nodeId];
        if (fresh) openQualityFeedbackMenu(fresh, anchor.point || anchor.el);
      });
    }
  }
  if (node.type === "script") {
    addItem("sparkles", "识别资产", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) identifyScriptAssets(store, runtime, fresh);
    });
    addItem("plus", "新增资产", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) openAddAssetModal(store, fresh);
    });
    addItem("image", "生成关键帧层", () => {
      const fresh = store.get().nodes[nodeId];
      if (fresh) createStoryboardKeyframeLayer(store, fresh);
    });
  }
  addItem("bookmark", node.params?.isReference ? "取消参考" : "设为参考", () =>
    store.set((s) => { const n = s.nodes[nodeId]; if (n) n.params.isReference = !n.params.isReference; }));
  addItem("trash", "删除节点", () => deleteNodes(store, [nodeId]), true);

  const close = showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });

  function addItem(iconName, label, onClick, danger = false) {
    const item = el("button", `menu-item${danger ? " danger" : ""}`);
    item.innerHTML = `<span class="mi-icon">${icon(iconName, 13)}</span><span>${label}</span>`;
    item.addEventListener("click", () => { close(); onClick(); });
    pop.appendChild(item);
  }
}

function activeFixedVisualAsset(node) {
  const assets = Array.isArray(node.params?.visualAssets) ? node.params.visualAssets : [];
  return [...assets].reverse().find((asset) => {
    const status = String(asset?.status || asset?.asset_status || "fixed");
    return status !== "retired" && status !== "excluded";
  }) || null;
}

function referenceModeMenuLabel(node) {
  return assetReferenceMode(node) === ASSET_REFERENCE_MODES.ORIGINALIZE_IP_SAFE
    ? "参考图模式：原创重生"
    : "参考图模式：局部修订";
}

function toggleReferenceMode(store, nodeId) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    const current = assetReferenceMode(node);
    node.params.assetReferenceMode = current === ASSET_REFERENCE_MODES.ORIGINALIZE_IP_SAFE
      ? ASSET_REFERENCE_MODES.LOCALIZED_EDIT
      : ASSET_REFERENCE_MODES.ORIGINALIZE_IP_SAFE;
    if (node.params.assetCardRevision) node.params.assetCardRevision.mode = node.params.assetReferenceMode;
    delete node.params.lastOptimizedPromptPlain;
    s.selection = { nodeIds: [node.id], edgeId: null };
    s.ui.promptBarNodeId = node.id;
  }, { history: false });
}

function requestVideoAssetCardDraft(store, nodeId) {
  const fresh = store.get().nodes[nodeId];
  if (!fresh) return;
  const sourceVideoArtifactId = String(
    fresh.params?.lastVideoArtifactId || fresh.params?.lastVideoJobId || "",
  ).trim();
  if (!sourceVideoArtifactId) {
    store.set((s) => {
      const node = s.nodes[nodeId];
      if (!node) return;
      node.result = [
        node.result || "",
        "请先生成视频，再识别视频资产卡。",
      ].filter(Boolean).join("\n");
    });
    return;
  }
  window.dispatchEvent(new CustomEvent("afs:video-asset-card-draft", {
    detail: { node_id: fresh.id, node: fresh },
  }));
}

export function openQualityFeedbackMenu(node, anchorOrPoint) {
  const feedback = qualityFeedbackView(node);
  if (!feedback) return;
  const pop = el("div", "quality-feedback-popover");
  pop.appendChild(feedback);
  const anchor = resolveAnchor(anchorOrPoint);
  showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });
}

export function renameNode(store, nodeId, anchorOrPoint) {
  const node = store.get().nodes[nodeId];
  if (!node) return;
  const pop = el("div", "rename-pop");
  const input = document.createElement("input");
  input.className = "rename-input";
  input.value = node.title;
  input.maxLength = 40;
  pop.appendChild(input);
  const anchor = resolveAnchor(anchorOrPoint);
  const close = showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });
  input.focus();
  input.select();
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const title = input.value.trim();
      if (title) store.set((s) => { const n = s.nodes[nodeId]; if (n) n.title = title; });
      close();
    }
    if (e.key === "Escape") close();
  });
}

function resolveAnchor(anchorOrPoint) {
  if (anchorOrPoint instanceof Element) return { el: anchorOrPoint, cleanup: undefined, point: null };
  const ghost = el("div");
  ghost.style.cssText = `position:fixed;left:${anchorOrPoint.x}px;top:${anchorOrPoint.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(ghost);
  return { el: ghost, cleanup: () => ghost.remove(), point: { x: anchorOrPoint.x, y: anchorOrPoint.y } };
}
