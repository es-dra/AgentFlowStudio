import { AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID } from "./agent-chat-lifecycle.js";

export function assetBibleConfirmRequest(preview, graphVersion = 0) {
  const commandId = String(preview?.command_id || "").trim();
  const previewDigest = String(preview?.preview_digest || "").trim();
  if (!commandId || !previewDigest || !preview?.request) {
    throw new Error("资产命令预览缺少可恢复确认信息，请重新预览。");
  }
  const previewGraphVersion = Number(preview?.expected_graph_version);
  return {
    ...preview.request,
    preview_digest: previewDigest,
    command_id: commandId,
    expected_graph_version: Math.max(
      0,
      Number.isFinite(previewGraphVersion)
        ? previewGraphVersion
        : Number(graphVersion || 0),
    ),
  };
}

export function assetBibleConfirmRecovery(error) {
  const status = Number(error?.status || 0);
  const code = String(error?.errorCode || "");
  const name = String(error?.cause?.name || error?.name || "");
  if (name === "AbortError" || code === "request_aborted") {
    return {
      category: "确认超时",
      preserve_preview: true,
      retryable: true,
      message: "确认回执未返回；已保留本次审阅命令。重试会恢复已完成结果或只应用一次。",
    };
  }
  if (
    code === "network_connection_interrupted"
    || /network connection interrupted|Failed to fetch/i.test(String(error?.message || ""))
  ) {
    return {
      category: "连接中断",
      preserve_preview: true,
      retryable: true,
      message: "公共连接在确认时中断；已保留本次审阅命令。重试会恢复已完成结果或只应用一次。",
    };
  }
  if ([502, 503, 504].includes(status)) {
    return {
      category: "公共入口暂不可用",
      preserve_preview: true,
      retryable: true,
      message: "确认回执暂未返回；已保留本次审阅命令。服务恢复后可重试同一确认。",
    };
  }
  return {
    category: status === 409 || status === 422 ? "预览已失效" : "确认失败",
    preserve_preview: false,
    retryable: false,
    message: "当前事实已保留。请重新预览影响范围后再确认。",
  };
}

export function syncAssetBibleCommandAssistantReceipt(session, bible) {
  const receipt = bible?.last_receipt || bible?.raw?.last_receipt || {};
  const receiptId = String(receipt.receipt_id || "").trim();
  const summary = String(receipt.summary || "").trim();
  if (!session || receipt.status !== "confirmed" || !receiptId || !summary) return false;

  const terminalKey = `asset-bible-terminal:${receiptId}`;
  const sourceMessages = Array.isArray(session.messages) ? session.messages : [];
  const messages = sourceMessages.filter((message) => !(
    message?.role === "assistant"
    && message.placeholder_id === AGENT_COMMAND_PREVIEW_PLACEHOLDER_ID
    && (!message.context_key || !session.context_key || message.context_key === session.context_key)
  ));
  const existingIndex = messages.findIndex((message) => message.asset_bible_terminal_key);
  const replacement = {
    role: "assistant",
    tone: "success",
    text: summary,
    asset_bible_terminal_key: terminalKey,
  };
  if (existingIndex >= 0) messages[existingIndex] = replacement;
  else messages.push(replacement);
  const changed = messages.length !== sourceMessages.length
    || existingIndex < 0
    || sourceMessages[existingIndex]?.asset_bible_terminal_key !== terminalKey;
  session.messages = messages.slice(-28);
  return changed;
}
