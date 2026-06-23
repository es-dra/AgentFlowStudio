import { setNodeError } from "./node-action-utils.js";
import { ensureShotAssetPrepNodesForScriptNode } from "./shot-asset-nodes.js";
import { createKeyframeNodesForStoryboard } from "./storyboard-keyframes.js";

export async function identifyScriptAssets(store, runtime, node) {
  const fresh = store.get().nodes[node.id] || node;
  const structuredShot = await plannedStructuredShot(store, runtime, fresh);
  const created = ensureShotAssetPrepNodesForScriptNode(store, fresh, { structuredShot });
  if (!created.length) {
    setNodeError(store, fresh.id, "当前分镜没有识别到可拆出的角色、场景或道具资产。");
  }
  return created;
}

export function createStoryboardKeyframeLayer(store, node) {
  const fresh = store.get().nodes[node.id] || node;
  return createKeyframeNodesForStoryboard(store, fresh);
}

async function plannedStructuredShot(store, runtime, node) {
  const fresh = store.get().nodes[node.id] || node;
  const localShot = fresh.params?.structuredShot || null;
  if (!runtime?.planShotAssets) return localShot;
  try {
    store.set((s) => {
      const target = s.nodes[fresh.id];
      if (!target) return;
      target.params.assetPrepState = { status: "planning", updated_at: new Date().toISOString() };
    }, { history: false });
    const payload = await runtime.planShotAssets({
      node_id: fresh.id,
      shot: localShot || {},
      script_text: fresh.content || fresh.prompt || "",
      generated_at: new Date().toISOString(),
    });
    const assetRefs = Array.isArray(payload?.asset_refs) ? payload.asset_refs : [];
    if (!assetRefs.length) return localShot;
    return {
      ...(localShot || {}),
      shot_id: localShot?.shot_id || `shot_${String(fresh.params?.scriptSegmentIndex || 1).padStart(2, "0")}`,
      index: localShot?.index || Number(fresh.params?.scriptSegmentIndex || 1),
      description: localShot?.description || fresh.content || fresh.prompt || "",
      source_text: localShot?.source_text || fresh.content || fresh.prompt || "",
      asset_refs: assetRefs,
    };
  } catch (error) {
    setNodeError(store, fresh.id, `${error.message || "Runtime 资产规划失败"}，已回退为本地识别。`);
    return localShot;
  }
}
