const READY = "ready";

export function productionGraphWorkspaceProjection(workspace = null) {
  if (!workspace || workspace.status !== READY) {
    return {
      status: workspace?.status || "unavailable",
      planningRequired: workspace?.status === "planning_required",
      graphVersion: Number(workspace?.graph_version || 0),
      graphDigest: String(workspace?.graph_digest || ""),
      scenes: [],
      shots: [],
      approvedMedia: [],
      approvedMediaByTarget: {},
      videoCandidates: [],
      videoCandidatesByTarget: {},
      mediaSummary: { approvedImages: 0, approvedAssetImages: 0, approvedShotImages: 0, approvedVideos: 0, pendingVideoCandidates: 0, generatedVideos: 0, readyShots: 0 },
      summary: emptySummary(),
    };
  }

  const graphVersion = Number(workspace.graph_version || 0);
  const graphDigest = String(workspace.graph_digest || "");
  if (
    Number(workspace.storyboard?.graph_version || 0) !== graphVersion
    || String(workspace.storyboard?.graph_digest || "") !== graphDigest
  ) {
    return {
      status: "projection_conflict",
      planningRequired: false,
      graphVersion,
      graphDigest,
      scenes: [],
      shots: [],
      approvedMedia: [],
      approvedMediaByTarget: {},
      videoCandidates: [],
      videoCandidatesByTarget: {},
      mediaSummary: { approvedImages: 0, approvedAssetImages: 0, approvedShotImages: 0, approvedVideos: 0, pendingVideoCandidates: 0, generatedVideos: 0, readyShots: 0 },
      summary: emptySummary(),
    };
  }

  const sequence = workspace.sequence || {};
  const relations = array(sequence.dependencies);
  const approvedMedia = approvedMediaProjection(
    sequence.approved_media,
    workspace.project_id,
  );
  const videoCandidates = pendingVideoCandidateProjection(
    sequence.video_candidates,
    workspace.project_id,
  );
  const approvedMediaByTarget = Object.fromEntries(approvedMedia.byTarget.entries());
  const videoCandidatesByTarget = Object.fromEntries(videoCandidates.byTarget.entries());
  const shots = array(sequence.shots).map((shot) => {
    const media = approvedMediaByTarget[String(shot.node_id || "")] || {};
    const candidate = videoCandidatesByTarget[String(shot.node_id || "")] || null;
    return {
      nodeId: canvasNodeId(shot.node_id),
      graphNodeId: String(shot.node_id || ""),
      sceneNodeId: sceneForShot(relations, shot.node_id),
      title: String(shot.metadata?.title || shot.metadata?.intent || ""),
      description: String(shot.metadata?.intent || ""),
      durationSeconds: Number(shot.metadata?.duration_seconds || 0),
      state: shot.state === "invalidated"
        ? "blocked"
        : shot.metadata?.review_state === "approved" || media.image || media.video
          ? "ready"
          : candidate
            ? "candidate"
          : "draft",
      preview: media.image?.previewUrl || "",
      video: media.video || null,
      videoCandidate: candidate,
    };
  });
  const scenes = array(sequence.scenes).map((scene) => ({
    nodeId: canvasNodeId(scene.node_id),
    graphNodeId: String(scene.node_id || ""),
    name: String(scene.metadata?.name || ""),
    shots: shots.filter((shot) => shot.sceneNodeId === scene.node_id),
  }));
  const shotTargetIds = new Set(shots.map((shot) => shot.graphNodeId));
  const approvedImages = approvedMedia.items.filter((item) => item.mediaKind === "image");

  return {
    status: READY,
    planningRequired: false,
    graphVersion,
    graphDigest,
    scenes,
    shots,
    approvedMedia: approvedMedia.items,
    approvedMediaByTarget,
    videoCandidates: videoCandidates.items,
    videoCandidatesByTarget,
    mediaSummary: {
      approvedImages: approvedImages.length,
      approvedAssetImages: approvedImages.filter(
        (item) => item.targetNodeIds.some((targetId) => !shotTargetIds.has(targetId)),
      ).length,
      approvedShotImages: approvedImages.filter(
        (item) => item.targetNodeIds.some((targetId) => shotTargetIds.has(targetId)),
      ).length,
      approvedVideos: approvedMedia.items.filter((item) => item.mediaKind === "video").length,
      pendingVideoCandidates: videoCandidates.items.length,
      generatedVideos: approvedMedia.items.filter((item) => item.mediaKind === "video").length + videoCandidates.items.length,
      readyShots: shots.filter((shot) => shot.preview || shot.video || shot.videoCandidate).length,
    },
    summary: {
      scriptRevisions: array(sequence.script_revisions).filter(
        (item) => item?.state !== "invalidated",
      ).length,
      sequences: array(sequence.sequences).length,
      characters: array(sequence.characters).length,
      locations: array(sequence.scenes).length,
      props: array(sequence.props).length,
      referenceSets: array(sequence.reference_sets).length,
      productionAids: array(sequence.production_aids).length,
      tasks: array(sequence.tasks).length,
      candidates: array(sequence.candidates).length,
      selections: array(sequence.selections).length,
      reviews: array(sequence.reviews).length,
      pendingReviews: array(sequence.reviews).filter((item) => item.state === "pending").length,
      rejectedReviews: array(sequence.reviews).filter((item) => item.state === "rejected").length,
      deliveries: array(sequence.delivery_plan).length,
      versionHistory: array(sequence.version_history),
    },
    lifecycle: {
      tasks: array(sequence.tasks),
      candidates: array(sequence.candidates),
      selections: array(sequence.selections),
      reviews: array(sequence.reviews),
      deliveries: array(sequence.delivery_plan),
    },
  };
}

export function applyProductionGraphCanvasProjection(state, workspace) {
  const workspaceProjectId = String(workspace?.project_id || "");
  const stateProjectId = String(state?.meta?.projectId || "");
  if (stateProjectId && (!workspaceProjectId || workspaceProjectId !== stateProjectId)) {
    throw new Error("production graph project does not match the active canvas");
  }
  const projection = productionGraphWorkspaceProjection(workspace);
  removeCanvasProjection(state);
  state.production = state.production || {};
  if (projection.status !== READY) {
    delete state.production.production_graph_projection;
    return projection;
  }
  for (const node of Object.values(state.nodes || {})) {
    node.params = { ...(node.params || {}), productionGraphLegacyProjection: "read_only_legacy_projection" };
  }
  state.production.production_graph_projection = {
    graph_version: projection.graphVersion,
    graph_digest: projection.graphDigest,
    scene_count: projection.scenes.length,
    shot_count: projection.shots.length,
    task_count: projection.summary.tasks,
    pending_review_count: projection.summary.pendingReviews,
    migration_state: "read_only_projection",
    provider_dispatch_count: 0,
  };

  const sequence = workspace.sequence || {};
  const groups = [
    [array(sequence.script_revisions), "script", "剧本版本"],
    [array(sequence.sequences), "text", "制作序列"],
    [array(sequence.characters), "character", "角色"],
    [array(sequence.scenes), "scene", "场景"],
    [array(sequence.props), "asset", "道具"],
    [array(sequence.reference_sets), "asset", "参考集"],
    [array(sequence.shots), "shot", "镜头"],
  ];
  const nodeMap = new Map();
  const legacyBottom = Object.values(state.nodes || {}).reduce(
    (bottom, node) => Math.max(bottom, Number(node?.y || 0) + Number(node?.h || 0)),
    0,
  );
  const originY = legacyBottom > 0 ? legacyBottom + 80 : 80;
  let slot = 0;
  for (const [records, type, fallbackTitle] of groups) {
    if (!records.length) continue;
    records.forEach((record) => {
      const graphNodeId = String(record.node_id || "");
      const id = canvasNodeId(graphNodeId);
      nodeMap.set(graphNodeId, id);
      state.nodes[id] = canvasNode(record, id, graphNodeId, type, fallbackTitle, slot, originY, projection);
      pushOrder(state, id);
      slot += 1;
    });
  }
  for (const media of projection.approvedMedia.filter((item) => item.mediaKind === "video")) {
    const graphNodeId = media.mediaNodeId;
    const id = canvasNodeId(graphNodeId);
    nodeMap.set(graphNodeId, id);
    state.nodes[id] = mediaCanvasNode(
      media,
      id,
      graphNodeId,
      slot,
      originY,
      projection,
    );
    pushOrder(state, id);
    slot += 1;
  }
  for (const relation of array(sequence.dependencies)) {
    const from = nodeMap.get(String(relation.from_id || ""));
    const to = nodeMap.get(String(relation.to_id || ""));
    if (!from || !to) continue;
    const edgeId = `production_graph_edge_${from}__${to}`;
    state.edges[edgeId] = { id: edgeId, from, to, relation_type: `production_graph_${String(relation.relation_type || "dependency")}` };
  }
  return projection;
}

export function productionGraphAgentContext(studioState, workspace) {
  const projection = productionGraphWorkspaceProjection(workspace);
  if (projection.status !== READY) return studioState;
  return {
    ...(studioState || {}),
    production: {
      ...(studioState?.production || {}),
      production_graph_projection: {
        graph_version: projection.graphVersion,
        graph_digest: projection.graphDigest,
        scene_count: projection.scenes.length,
        shot_count: projection.shots.length,
        task_count: projection.summary.tasks,
        pending_review_count: projection.summary.pendingReviews,
        migration_state: "read_only_projection",
      },
    },
  };
}

function sceneForShot(relations, shotId) {
  return String(relations.find((item) => item.to_id === shotId && item.relation_type === "contains")?.from_id || "");
}

function approvedMediaProjection(value, projectId) {
  const expectedProject = String(projectId || "");
  const routePatterns = {
    image: /^\/projects\/([A-Za-z0-9_.-]+)\/image-assets\/[A-Za-z0-9_.-]+\/preview$/,
    video: /^\/projects\/([A-Za-z0-9_.-]+)\/approved-video-assets\/[A-Za-z0-9_.-]+\/preview$/,
  };
  const byKindTarget = new Map();
  const ambiguousTargets = new Set();
  const accepted = [];
  for (const media of array(value)) {
    const mediaKind = String(media?.media_kind || "");
    const previewUrl = String(media?.preview_url || "");
    const routePattern = routePatterns[mediaKind];
    const match = routePattern ? previewUrl.match(routePattern) : null;
    if (
      !["image", "video"].includes(mediaKind)
      || !match
      || !expectedProject
      || match[1] !== expectedProject
    ) {
      continue;
    }
    const record = {
      mediaNodeId: String(media?.media_node_id || ""),
      mediaKind,
      previewUrl,
      mimeType: String(media?.mime_type || (mediaKind === "image" ? "image/*" : "video/*")),
      container: String(media?.container || ""),
      width: Number(media?.width || 0),
      height: Number(media?.height || 0),
      durationSeconds: Number(media?.duration_sec || 0),
      codec: String(media?.codec || ""),
      model: String(media?.model || ""),
      resolution: String(media?.resolution || ""),
      generationMode: String(media?.generation_mode || ""),
      approvalGraphVersion: Number(media?.approval_graph_version || 0),
      targetNodeIds: array(media?.target_node_ids).map((item) => String(item || "")).filter(Boolean),
      lineage: media?.lineage && typeof media.lineage === "object"
        ? {
          sourceKind: String(media.lineage.source_kind || ""),
          targetRelation: String(media.lineage.target_relation || ""),
        }
        : null,
    };
    if (!record.mediaNodeId || !record.targetNodeIds.length) continue;
    accepted.push(record);
    for (const targetId of record.targetNodeIds) {
      const key = `${mediaKind}:${targetId}`;
      if (!key || ambiguousTargets.has(key)) continue;
      if (byKindTarget.has(key)) {
        byKindTarget.delete(key);
        ambiguousTargets.add(key);
      } else {
        byKindTarget.set(key, record);
      }
    }
  }
  const byTarget = new Map();
  for (const [key, media] of byKindTarget.entries()) {
    const split = key.indexOf(":");
    const mediaKind = key.slice(0, split);
    const targetId = key.slice(split + 1);
    byTarget.set(targetId, {
      ...(byTarget.get(targetId) || {}),
      [mediaKind]: media,
    });
  }
  const items = accepted.filter((media) => media.targetNodeIds.every(
    (targetId) => byKindTarget.get(`${media.mediaKind}:${targetId}`) === media,
  ));
  return { byTarget, items };
}

function pendingVideoCandidateProjection(value, projectId) {
  const expectedProject = String(projectId || "");
  const routePattern = /^\/projects\/([A-Za-z0-9_.-]+)\/video-generations\/[A-Za-z0-9_.-]+\/candidates\/candidate_\d{3}\/preview$/;
  const byTarget = new Map();
  const ambiguousTargets = new Set();
  const accepted = [];
  for (const media of array(value)) {
    const previewUrl = String(media?.preview_url || "");
    const match = previewUrl.match(routePattern);
    if (
      String(media?.media_kind || "") !== "video"
      || String(media?.review_state || "") !== "candidate"
      || !match
      || !expectedProject
      || match[1] !== expectedProject
    ) {
      continue;
    }
    const record = {
      mediaNodeId: String(media?.media_node_id || ""),
      mediaKind: "video",
      reviewState: "candidate",
      previewUrl,
      mimeType: String(media?.mime_type || "video/mp4"),
      container: String(media?.container || "video/mp4"),
      width: Number(media?.width || 0),
      height: Number(media?.height || 0),
      durationSeconds: Number(media?.duration_sec || 0),
      codec: String(media?.codec || ""),
      model: String(media?.model || ""),
      resolution: String(media?.resolution || ""),
      generationMode: String(media?.generation_mode || ""),
      manifestId: String(media?.manifest_id || ""),
      manifestHash: String(media?.manifest_hash || ""),
      jobId: String(media?.job_id || ""),
      candidateId: String(media?.candidate_id || ""),
      sha256: String(media?.sha256 || ""),
      byteCount: Number(media?.byte_count || 0),
      targetNodeIds: array(media?.target_node_ids).map((item) => String(item || "")).filter(Boolean),
      lineage: media?.lineage && typeof media.lineage === "object"
        ? {
          sourceKind: String(media.lineage.source_kind || ""),
          targetRelation: String(media.lineage.target_relation || ""),
        }
        : null,
    };
    if (!record.mediaNodeId || !record.targetNodeIds.length || record.targetNodeIds.length !== 1) continue;
    const targetId = record.targetNodeIds[0];
    if (ambiguousTargets.has(targetId)) continue;
    if (byTarget.has(targetId)) {
      byTarget.delete(targetId);
      ambiguousTargets.add(targetId);
      continue;
    }
    accepted.push(record);
    byTarget.set(targetId, record);
  }
  const items = accepted.filter((media) => byTarget.get(media.targetNodeIds[0]) === media);
  return { byTarget, items };
}

function emptySummary() {
  return { scriptRevisions: 0, sequences: 0, characters: 0, locations: 0, props: 0, referenceSets: 0, tasks: 0, candidates: 0,
    productionAids: 0, selections: 0, reviews: 0, pendingReviews: 0, rejectedReviews: 0, deliveries: 0, versionHistory: [] };
}

function canvasNode(record, id, graphNodeId, type, fallbackTitle, slot, originY, projection) {
  const metadata = record.metadata || {};
  const media = projection.approvedMediaByTarget?.[graphNodeId]?.image || null;
  const videoCandidate = projection.videoCandidatesByTarget?.[graphNodeId] || null;
  const title = String(metadata.display_name || metadata.name || metadata.title || metadata.intent || fallbackTitle).trim() || fallbackTitle;
  const details = [];
  if (metadata.intent) details.push(String(metadata.intent));
  if (Number(metadata.duration_seconds || 0) > 0) details.push(`时长：${Number(metadata.duration_seconds).toFixed(1)} 秒`);
  if (media) details.push("参考图：已批准");
  if (videoCandidate) details.push("视频候选：待审看");
  if (record.state === "invalidated") details.push("需要更新");
  const aspectRatio = media?.width > 0 && media?.height > 0
    ? `${media.width}:${media.height}`
    : "";
  return {
    id,
    type,
    title: title.slice(0, 80),
    x: 80 + (slot % 4) * 330,
    y: originY + Math.floor(slot / 4) * 240,
    w: 280,
    h: 190,
    content: details.join("\n") || "已加入当前制作方案。",
    prompt: "",
    status: record.state === "invalidated" ? "blocked" : media || videoCandidate ? "complete" : "accepted",
    result: media ? "已批准参考图已保存到当前项目。" : videoCandidate ? "视频候选已写入当前项目，等待审看批准。" : null,
    previewUrl: media?.previewUrl || "",
    groupId: null,
    collapsed: false,
    params: {
      productionGraphProjection: "canonical_production_graph_projection",
      productionGraphTruth: { graph_node_id: graphNodeId, graph_version: projection.graphVersion, graph_digest: projection.graphDigest },
      approvedMedia: media ? {
        media_node_id: media.mediaNodeId,
        media_kind: media.mediaKind,
        source_node_ids: media.targetNodeIds,
        model: media.model,
        resolution: media.resolution,
        mime_type: media.mimeType,
        width: media.width,
        height: media.height,
        approval_graph_version: media.approvalGraphVersion,
      } : null,
      videoCandidate: videoCandidate ? {
        media_node_id: videoCandidate.mediaNodeId,
        media_kind: videoCandidate.mediaKind,
        review_state: videoCandidate.reviewState,
        source_node_ids: videoCandidate.targetNodeIds,
        model: videoCandidate.model,
        resolution: videoCandidate.resolution,
        mime_type: videoCandidate.mimeType,
        width: videoCandidate.width,
        height: videoCandidate.height,
        duration_sec: videoCandidate.durationSeconds,
        preview_url: videoCandidate.previewUrl,
      } : null,
      previewAspectRatio: aspectRatio,
      provider_dispatch_count: 0,
    },
  };
}

function mediaCanvasNode(media, id, graphNodeId, slot, originY, projection) {
  const aspectRatio = media.width > 0 && media.height > 0
    ? `${media.width}:${media.height}`
    : "16:9";
  return {
    id,
    type: media.mediaKind,
    title: media.mediaKind === "video" ? "已批准镜头视频" : "已批准镜头图片",
    x: 80 + (slot % 4) * 330,
    y: originY + Math.floor(slot / 4) * 240,
    w: 300,
    h: 230,
    content: "",
    prompt: "",
    status: "complete",
    result: media.mediaKind === "video" ? "视频已保存到当前项目。" : "图片已保存到当前项目。",
    previewUrl: media.previewUrl,
    groupId: null,
    collapsed: false,
    params: {
      productionGraphProjection: "canonical_production_graph_projection",
      productionGraphTruth: {
        graph_node_id: graphNodeId,
        graph_version: projection.graphVersion,
        graph_digest: projection.graphDigest,
      },
      approvedMedia: {
        media_kind: media.mediaKind,
        source_node_ids: media.targetNodeIds,
        model: media.model,
        resolution: media.resolution,
        generation_mode: media.generationMode,
        duration_sec: media.durationSeconds,
        mime_type: media.mimeType,
        container: media.container,
        codec: media.codec,
        width: media.width,
        height: media.height,
        approval_graph_version: media.approvalGraphVersion,
      },
      previewAspectRatio: aspectRatio,
      provider_dispatch_count: 0,
    },
  };
}

function removeCanvasProjection(state) {
  const remove = new Set();
  for (const [id, item] of Object.entries(state.nodes || {})) {
    if (item?.params?.productionGraphProjection === "canonical_production_graph_projection") remove.add(id);
  }
  for (const id of remove) delete state.nodes[id];
  state.order = array(state.order).filter((id) => !remove.has(id));
  for (const [edgeId, edge] of Object.entries(state.edges || {})) {
    if (remove.has(edge.from) || remove.has(edge.to) || String(edge.relation_type || "").startsWith("production_graph_")) delete state.edges[edgeId];
  }
  if (array(state.selection?.nodeIds).some((id) => remove.has(id))) state.selection = { nodeIds: [], edgeId: null };
}

function pushOrder(state, nodeId) {
  state.order = array(state.order).filter((id) => id !== nodeId);
  state.order.push(nodeId);
}

function canvasNodeId(value) {
  return `production_graph_${String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "_").slice(0, 160)}`;
}

function array(value) {
  return Array.isArray(value) ? value : [];
}
