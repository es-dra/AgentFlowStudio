import { safeError, setNodeError } from "./node-action-utils.js";
import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { updateNodeGenerationState } from "./node-generation-progress.js";
import { sleep } from "./node-generation-restore.js";
import { nodeGenerationKind } from "./node-keyframe-response.js";
const MAX_ASSET_RECOVERY_WINDOW_MS = 10 * 60 * 1000;
export function markKeyframeRecovering(store, nodeId, kind) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const label = kind === "asset" ? "正在找回资产图结果" : "正在找回图片结果";
    n.status = "generating";
    updateNodeGenerationState(n, { job: { status: "running", progress: { mode: "indeterminate" } } }, {
      kind,
      label,
      hint: "浏览器连接超时或中断，但 Runtime 可能仍在完成生成；正在从素材库补偿回填。",
    });
    n.result = `${kind === "asset" ? "资产图" : "图像"}请求连接中断，正在尝试找回已完成结果。`;
  }, { history: false });
}
export async function recoverTimedOutKeyframeFromAssets(store, runtime, nodeId, kind, submittedAtMs, originalError) {
  const deadline = Date.now() + MAX_ASSET_RECOVERY_WINDOW_MS;
  for (let attempt = 0; Date.now() < deadline; attempt += 1) {
    if (nodeAlreadyRecovered(store, nodeId)) return;
    if (attempt > 0) await sleep(attempt < 4 ? 3000 : 5000);
    const recovered = await recoverNodeFromGeneratedAssets(store, runtime, nodeId, kind, submittedAtMs);
    if (recovered) {
      await store.flushRuntimeSave?.();
      return;
    }
  }
  if (nodeAlreadyRecovered(store, nodeId)) return;
  setNodeError(store, nodeId, `图像生成请求失败: ${safeError(originalError)} 可稍后在素材库中查看是否已有候选图，或在节点菜单重试。`);
  await store.flushRuntimeSave?.();
}
async function recoverNodeFromGeneratedAssets(store, runtime, nodeId, kind, submittedAtMs) {
  if (!runtime?.listImageAssets) return false;
  let payload = null;
  try {
    payload = await runtime.listImageAssets();
  } catch {
    return false;
  }
  const assets = Array.isArray(payload?.assets) ? payload.assets : [];
  const matching = assets
    .filter((item) => String(item?.source_node_id || "") === String(nodeId) && item?.preview_url)
    .sort((a, b) => assetCreatedAtMs(b) - assetCreatedAtMs(a));
  const asset = matching.find((item) => assetCreatedAtMs(item) >= submittedAtMs - 1000) || matching.find((item) => !assetCreatedAtMs(item));
  if (!asset) return false;
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "complete";
    n.previewUrl = asset.preview_url;
    n.params.uploads = mergeImageAssets(n.params.uploads || [], recoveredAssetForNode(asset, kind)).slice(-4);
    if (asset.source_job_id) {
      n.params.lastKeyframeJobId = asset.source_job_id;
      n.params.lastKeyframeCompletedJobId = asset.source_job_id;
    }
    resizeNodeForImagePreview(n, asset, n.params?.spec?.ratio || "16:9");
    n.result = [
      `${kind === "asset" ? "资产图" : "关键帧"}已从已落盘素材找回`,
      asset.source_job_id ? `任务编号：${asset.source_job_id}` : null,
      "预览已从安全素材地址加载。",
    ].filter(Boolean).join("\n");
  }, { history: false });
  return true;
}
function nodeAlreadyRecovered(store, nodeId) {
  const node = store.get().nodes?.[nodeId];
  return node?.status === "complete" && Boolean(node.previewUrl);
}
function assetCreatedAtMs(asset) {
  const parsed = Date.parse(String(asset?.created_at || ""));
  return Number.isFinite(parsed) ? parsed : 0;
}
function recoveredAssetForNode(asset, kind) {
  const role = kind === "asset" ? asset.role || "asset_reference" : asset.role || "generated_keyframe_reference";
  return {
    asset_id: asset.asset_id,
    role,
    filename: asset.filename || `${asset.asset_id}.png`,
    preview_url: asset.preview_url,
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
  };
}
export function isRecoverableSubmitError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  const status = Number(error?.status || 0);
  return status === 0 || status === 502 || status === 503 || status === 504
    || /Gateway timeout|network connection interrupted|Failed to fetch|timed out/i.test(message);
}
export function markKeyframeStillProcessing(store, nodeId, jobId) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const kind = nodeGenerationKind(n);
    const label = kind === "asset" ? "资产图仍在生成" : "图片仍在生成";
    n.status = "generating";
    updateNodeGenerationState(n, { job: { job_id: jobId, status: "running", progress: { mode: "indeterminate" } } }, { kind, label, hint: `任务 ${jobId} 还在处理，稍后可继续刷新节点。` });
    n.result = `${kind === "asset" ? "资产图" : "图像"}生成仍在进行中。\n任务编号：${jobId}`;
    n.params.lastKeyframeJobId = jobId;
  }, { history: false });
}
