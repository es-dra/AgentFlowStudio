export const STUDIO_MODES = [
  {
    id: "produce",
    label: "制作",
    meta: "镜头与检查",
    empty: "生成画布草稿后，这里会出现可制作的镜头节点。",
  },
  {
    id: "plan",
    label: "规划",
    meta: "需求与素材",
    empty: "先补充项目目标和安全素材摘要，再进入制作。",
  },
  {
    id: "review",
    label: "审片",
    meta: "候选与阻塞",
    empty: "首轮检查或候选产物出现后，再进入审片模式。",
  },
  {
    id: "reuse",
    label: "复用",
    meta: "记忆与下一轮",
    empty: "完成审片反馈后，这里会出现下一轮复用信号。",
  },
];

export function studioMode(state) {
  const allowed = STUDIO_MODES.map((item) => item.id);
  return allowed.includes(state?.studioMode) ? state.studioMode : "produce";
}

export function studioModeById(mode) {
  return STUDIO_MODES.find((item) => item.id === mode) || STUDIO_MODES[0];
}

export function studioModeCards(cards, mode) {
  return cards.filter((card, index) => studioModeMatchesCard(card, index, mode, cards.length));
}

export function studioModePrimaryCard(cards, mode) {
  return studioModeCards(cards, mode)[0] || cards[0] || null;
}

function studioModeMatchesCard(card, index, mode, total) {
  const kind = String(card?.kind || "");
  const status = String(card?.status || "");
  const hasArtifact = Boolean(card?.primary_artifact_id);
  const hasBlockers = Array.isArray(card?.blockers) && card.blockers.length > 0;
  if (mode === "plan") return index === 0 || kind === "source" || kind === "brief";
  if (mode === "review") return kind === "review" || kind === "generation_check" || hasArtifact || hasBlockers || status === "blocked";
  if (mode === "reuse") return kind === "memory" || kind === "style_memory" || kind === "next_round" || index === total - 1;
  return kind === "scene_card" || kind === "generation_check" || index > 0;
}
