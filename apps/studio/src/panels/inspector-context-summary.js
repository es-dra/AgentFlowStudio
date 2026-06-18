import {
  assetIdFromRef,
  assetLabel,
  assetTypeLabel,
  assetsFromNode,
} from "../asset-reference-summary.js";
import { assetLifecycleSummary } from "../asset-lifecycle.js";

export function projectReferenceSummaryText(state) {
  const summary = assetLifecycleSummary(state.assets || []);
  const edgeCount = Object.keys(state.edges || {}).length;
  const nodeCount = state.order.length;
  if (!nodeCount) {
    return "还没有项目参考。创建节点并确认素材后，系统会在生成前整理本次参考摘要。";
  }
  return [
    `画布节点：${nodeCount}`,
    `可进入下次调用：${summary.fixed} 个已确认素材`,
    `待确认候选：${summary.draft + summary.rejected} 个`,
    summary.retired ? `已停用：${summary.retired} 个` : "",
    `连线关系：${edgeCount}`,
  ].filter(Boolean).join("\n");
}

export function projectAssetDecisionText(state) {
  const summary = assetLifecycleSummary(state.assets || []);
  if (!summary.total) return "当前还没有确认素材。视觉识别和生成结果会先成为候选，确认后才进入后续上下文。";
  return [
    `已确认素材会默认参与下一次调度：${summary.fixed}`,
    `候选/待确认不会自动污染后续调用：${summary.draft + summary.rejected}`,
    summary.retired ? `停用素材仅保留记录：${summary.retired}` : "",
  ].filter(Boolean).join("\n");
}

export function nodeContextSummaryText(node) {
  const bundle = node.params?.lastContextBundle || null;
  const includedAssets = Array.isArray(bundle?.included_assets) ? bundle.included_assets : [];
  const excludedAssets = Array.isArray(bundle?.excluded_assets) ? bundle.excluded_assets : [];
  const includedNodes = Array.isArray(bundle?.included_nodes) ? bundle.included_nodes : [];
  const localAssets = assetsFromNode(node);

  if (!bundle && !localAssets.length) {
    return "还没有引用内容。优化或生成后会显示本次携带的节点、素材和排除原因。";
  }

  const lines = [];
  if (includedNodes.length || includedAssets.length) {
    lines.push(`本次纳入：${includedNodes.length} 个节点 / ${includedAssets.length} 个素材`);
  } else {
    lines.push("本次纳入：等待下一次调度");
  }
  if (includedAssets.length) lines.push(`已确认参考：${assetList(includedAssets)}`);
  if (excludedAssets.length) lines.push(`本次排除：${assetList(excludedAssets)}`);
  if (!includedAssets.length && localAssets.length) lines.push(`当前节点候选：${assetList(localAssets)}`);
  const warnings = warningList(bundle);
  if (warnings.length) lines.push(`提醒：${warnings.join("；")}`);
  return lines.join("\n");
}

export function nodeAssetDecisionText(node) {
  const localAssets = assetsFromNode(node);
  const bundle = node.params?.lastContextBundle || {};
  const included = Array.isArray(bundle.included_assets) ? bundle.included_assets.length : 0;
  const excluded = Array.isArray(bundle.excluded_assets) ? bundle.excluded_assets.length : 0;
  if (!localAssets.length && !included && !excluded) {
    return "当前节点还没有绑定素材；生成或上传后先作为候选，用户确认后才会成为固定资产。";
  }
  return [
    included ? `已随本次调用携带：${included}` : "",
    excluded ? `本次被排除：${excluded}` : "",
    localAssets.length ? `节点绑定候选：${localAssets.length}` : "",
  ].filter(Boolean).join("\n");
}

function assetList(items) {
  return items.slice(0, 3).map((item) => {
    const label = compactText(assetLabel(item), 36);
    const type = assetTypeLabel(item);
    const id = assetIdFromRef(item);
    return id && label === id ? `${type} ${shortId(id)}` : `${type} ${label}`;
  }).join("、");
}

function warningList(bundle) {
  const warnings = [];
  if (Array.isArray(bundle?.warnings)) warnings.push(...bundle.warnings);
  if (Array.isArray(bundle?.asset_conflicts)) warnings.push(...bundle.asset_conflicts.map((item) => item?.reason || item));
  return warnings.map(warningText).filter(Boolean).slice(0, 2);
}

function warningText(item) {
  if (!item || typeof item !== "object") return compactText(item, 80);
  return compactText(item.reason || item.warning_id || item.label || item.attribute || "context warning", 80);
}

function shortId(id) {
  const value = String(id || "");
  return value.length > 10 ? `${value.slice(0, 6)}…${value.slice(-3)}` : value;
}

function compactText(value, maxLength) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}
