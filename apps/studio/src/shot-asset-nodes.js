import { createNode, connect } from "./nodes.js";
import { assetRefToken, assetTypeLabel } from "./structured-shot.js";

const MAX_ASSET_PREP_NODES_PER_SHOT = 4;

export function createShotAssetPrepNodes(store, scriptNodeId, structuredShot, x, y) {
  const refs = Array.isArray(structuredShot?.asset_refs) ? structuredShot.asset_refs : [];
  const created = [];
  refs.slice(0, MAX_ASSET_PREP_NODES_PER_SHOT).forEach((asset, index) => {
    const assetNode = createNode(store, "image", x, y + index * 150);
    store.set((s) => {
      const node = s.nodes[assetNode.id];
      if (!node) return;
      node.title = `${assetTypeLabel(asset)} · ${assetRefToken(asset)}`;
      node.prompt = assetPrepPrompt(asset, structuredShot);
      node.status = "empty";
      node.params.asset_prep = {
        status: "needs_generation",
        source_script_node_id: scriptNodeId,
        source_shot_id: structuredShot.shot_id,
        asset_ref: asset,
      };
      node.params.assetPrepState = {
        status: "needs_generation",
        source_script_node_id: scriptNodeId,
        source_shot_id: structuredShot.shot_id,
      };
    });
    connect(store, scriptNodeId, assetNode.id);
    created.push(assetNode.id);
  });
  return created;
}

function assetPrepPrompt(asset, structuredShot) {
  return [
    `准备${assetTypeLabel(asset)}：${assetRefToken(asset)}`,
    `来源分镜：${String(structuredShot.index).padStart(2, "0")}`,
    `画面需求：${structuredShot.description}`,
    `景别/光影/运镜：${structuredShot.shot_size}，${structuredShot.light_atmosphere}，${structuredShot.camera_motion}`,
    "生成目标：先做可复用资产定稿，不直接推进视频。",
  ].join("\n");
}
