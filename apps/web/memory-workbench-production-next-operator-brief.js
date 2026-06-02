export function buildNextOperatorBrief(startPacket) {
  const packet = objectValue(startPacket);
  const ready = packet.start_packet_status === "ready" && packet.ready_for_next_operator === true;
  const action = actionValue(packet.next_operator_action);
  const promptExcerpt = promptExcerptFor(packet);
  const requirements = arrayValue(packet.start_requirements).map(String);
  return {
    title: "Next operator brief",
    status: ready ? "review ready" : "blocked",
    action,
    prompt_excerpt: promptExcerpt,
    requirements,
    boundary: "Use checked package items only; no provider call, Company KB write, or durable memory write.",
  };
}

export function nextOperatorBriefCards(brief) {
  const item = objectValue(brief);
  if (!item.action && !item.prompt_excerpt && !arrayValue(item.requirements).length) return [];
  return [
    {
      label: "Operator prompt",
      status: item.status || "planned",
      detail: item.prompt_excerpt || item.action || "operator prompt not recorded",
    },
    {
      label: "Start requirements",
      status: arrayValue(item.requirements).length ? "review ready" : "planned",
      detail: `${arrayValue(item.requirements).length} requirements visible`,
    },
  ];
}

function actionValue(value) {
  if (typeof value === "string") return value;
  return objectValue(value).action || "unknown";
}

function promptExcerptFor(packet) {
  const source = packet.operator_prompt_excerpt || packet.operator_prompt || "";
  const text = String(source).replace(/\s+/g, " ").trim();
  return text.length > 480 ? `${text.slice(0, 477).trim()}...` : text;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
