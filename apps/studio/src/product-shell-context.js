export function createDirectorContextStore() {
  const contexts = new Map();
  return {
    get(key) {
      const safeKey = String(key || "unknown");
      if (!contexts.has(safeKey)) {
        contexts.set(safeKey, {
          conversations: [],
          proposalApplied: false,
          proposalText: "先核对主体目标、连续性影响和确认边界",
          actionLabel: "",
        });
      }
      return contexts.get(safeKey);
    },
  };
}

export function productContextKey({ projectId, sceneIndex, shotIndex, shot } = {}) {
  const identity = shot?.nodeId || shot?.title || "empty-shot";
  return [projectId || "local-project", Number(sceneIndex || 0), Number(shotIndex || 0), identity].join(":");
}

export function findNextProductionTarget(scenes = [], current = {}) {
  const candidates = [];
  scenes.forEach((scene, sceneIndex) => {
    scene.shots.forEach((shot, shotIndex) => candidates.push({ sceneIndex, shotIndex, scene, shot }));
  });
  return candidates.find((item) => item.shot.state === "blocked")
    || candidates.find((item) => item.shot.state === "draft")
    || candidates.find((item) => item.sceneIndex === current.sceneIndex && item.shotIndex === current.shotIndex)
    || candidates[0]
    || null;
}
