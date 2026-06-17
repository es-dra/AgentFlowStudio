export function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/AFS_ALLOW_REMOTE_|provider service not found|provider gate is closed|Remote .* calls are disabled/i.test(clean)) {
    return "生成服务未就绪，请检查本机配置与创作服务启动状态后重试。";
  }
  return clean.slice(0, 160);
}

export function setNodeError(store, nodeId, message) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    n.status = "error";
    n.result = message;
  });
}
