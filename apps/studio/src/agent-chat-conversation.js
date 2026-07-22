const NODE_LABELS = {
  text: "文本 / 想法",
  idea: "想法",
  script: "剧本 / 分镜",
  sequence: "段落",
  scene: "场景",
  shot: "镜头",
  character: "角色",
  location: "场景空间",
  prop: "道具",
  ref: "参考集",
  image: "图片 / 关键帧",
  video: "视频",
  audio: "音频",
  director: "导演台",
};

export function conversationalReply(message, context = {}) {
  const text = cleanText(message, 900);
  if (!text) return null;
  if (isGreeting(text)) return reply(greetingReply(context), "local_context_answer");
  if (asksAboutNode(text)) return reply(nodeReply(context), "local_context_answer");
  if (asksAboutNextStep(text)) return reply(nextStepReply(context), "local_context_answer");
  if (asksAboutEdge(text)) return reply(edgeReply(context), "local_context_answer");
  if (looksLikeQuestion(text)) return reply(generalQuestionReply(text, context), "local_context_answer");
  return reply(openEndedReply(context), "local_context_answer");
}

function greetingReply(context) {
  const target = context.selected_node_title
    ? `我已经看到你选中的「${context.selected_node_title}」。`
    : "你可以直接从想法、剧本、镜头、角色、参考图、图片或视频开始。";
  return [
    "你好，我是 AI 创作搭档。",
    target,
    "问问题时我会直接回答；要改动画布或准备生成时，我会先给出目标、范围、费用和影响预览，确认前不会改动 ProductionGraph。",
  ].join("");
}

function nodeReply(context) {
  if (!context.selected_node_id) {
    return "当前还没有选中节点。你可以点选画布上的节点，或用左下角加号创建想法、剧本、角色、场景、参考图、图片或视频节点。";
  }
  const label = NODE_LABELS[context.selected_node_type] || context.selected_node_type || "节点";
  const status = statusText(context.selected_node_status);
  const textHint = context.selected_node_text ? `内容约 ${context.selected_node_text.length} 字。` : "还没有正文或提示词。";
  return `这是「${context.selected_node_title || label}」，类型是${label}，状态是${status}。${textHint}我可以帮你解释它、给下一步建议，或先预览一次不会立即执行的修改。`;
}

function nextStepReply(context) {
  if (context.media_operations) {
    const media = context.media_operations;
    return `当前适合先审看 ${Number(media.ready_shot_count || 0)}/${Number(media.shot_count || 0)} 个可用镜头，确认连续性、费用和恢复状态；需要重做时只选择受影响镜头。`;
  }
  if (context.selected_node_id) {
    const type = context.selected_node_type;
    if (type === "text" || type === "idea") return "下一步可以先在当前节点内精修文字；确认满意后再显式派生为剧本或分镜，不会默认制造新节点。";
    if (type === "script") return "下一步可以分析剧本结构，或派生场景/镜头节点；缺少角色或场景时只补最小必要信息。";
    if (type === "shot") return "下一步可以检查镜头目的、景别、机位、运动和声音，再预览关键帧生成命令。";
    if (type === "image") return "下一步可以把这张图标为参考、连接到角色/场景/镜头，或预览视频生成命令。";
    if (type === "video") return "下一步可以审片、标记问题，或只对当前片段预览局部重做。";
    return "下一步建议先补齐这个节点的用途和关系，再连接到需要消费它的镜头、图片或视频节点。";
  }
  return "现在最小的下一步是创建一个起点：想法、剧本、角色、参考图、图片或视频都可以。画布不会强迫你先写完整剧本。";
}

function edgeReply(context) {
  if (!context.selected_edge_id) {
    return "当前没有选中连线。点选一条线后，我可以说明它的方向、关系类型、上下游节点，并预览改成参考、派生或生成关系。";
  }
  const relation = relationLabel(context.selected_edge_relation_type);
  const from = context.selected_edge_from_title || "上游节点";
  const to = context.selected_edge_to_title || "下游节点";
  return `这条连线表示「${from}」到「${to}」的${relation}关系。改变关系类型会先显示预览；删除连线会保留可撤销记录，不会静默丢失节点。`;
}

function generalQuestionReply(message, context) {
  const scope = context.selected_node_title ? `当前问题会结合「${context.selected_node_title}」回答。` : "当前没有选中具体对象，我先按整个画布回答。";
  return `${scope}我可以解释节点、连线、下一步、费用与恢复状态；如果你想实际改动画布，请说清目标和范围，我会先给命令预览而不是直接写入。`;
}

function openEndedReply(context) {
  const target = context.selected_node_title ? `当前目标：${context.selected_node_title}。` : "当前没有固定目标。";
  return `${target}我已把这句话作为创作讨论处理，没有改动画布。要让我执行，请使用明确动作，例如“创建角色节点”“优化当前文本”“把这条连线改为参考”或“预览生成图片”。`;
}

function isGreeting(text) {
  return /^(你好|您好|嗨|hi|hello|hey|哈喽)[!！。.\s]*$/i.test(text);
}

function asksAboutNode(text) {
  return /(这个|当前|选中).*(节点|对象).*(是什么|说明|介绍)|节点是什么/.test(text);
}

function asksAboutNextStep(text) {
  return /(下一步|接下来|建议|该做什么|怎么继续)/.test(text);
}

function asksAboutEdge(text) {
  return /(这条|当前|选中).*(连线|关系|边).*(代表|是什么|说明|改成)|连线代表什么/.test(text);
}

function looksLikeQuestion(text) {
  return /[?？]$|^(为什么|怎么|如何|能不能|是否|可否|哪里|哪个|什么)/.test(text);
}

function statusText(status) {
  const value = String(status || "").trim();
  if (!value || value === "empty") return "空白，需要输入";
  if (value === "draft") return "草稿";
  if (value === "complete") return "可审阅";
  if (value === "generating") return "生成中";
  if (value === "error") return "失败，需要处理";
  return value.replace(/_/g, " ");
}

function relationLabel(relation) {
  const value = String(relation || "generation").trim();
  return {
    generation: "生成/派生",
    reference: "参考",
    director: "导演控制",
    fork: "分支版本",
    sequence: "叙事顺序",
    proposed: "待确认建议",
  }[value] || value.replace(/_/g, " ");
}

function reply(text, source) {
  return {
    status: "answered",
    text: cleanText(text, 900),
    source,
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}

function cleanText(value, limit) {
  return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, limit);
}
