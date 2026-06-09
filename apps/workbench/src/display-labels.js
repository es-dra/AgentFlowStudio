const TEXT_MAP = {
  Assets: "素材库",
  Create: "创作画布",
  Jobs: "任务中心",
  Projects: "项目",
  Review: "审片室",
  Settings: "诊断",
  "Style Memory": "项目记忆",
  Storyboard: "分镜台",
  Continue: "继续",
  "Add source materials": "添加素材摘要",
  "Draft Canvas": "生成画布草稿",
  "Run first generation check": "运行首轮检查",
  "Record review feedback": "记录审片反馈",
  "Start next round": "进入下一轮",
  "Run provider preflight": "Provider 预检",
  "Record Review": "记录审片",
  "Run Next Round": "运行下一轮",
  "Run provider preflight": "运行 Provider 预检",
  "Source materials": "素材准备",
  "Draft canvas": "画布草稿",
  "First generation check": "首轮检查",
  "Review feedback": "审片反馈",
  "Next round": "下一轮复用",
  "Next Round": "下一轮复用",
  "Provider preflight": "Provider 预检",
  "Safe materials": "安全素材",
  Source: "素材准备",
  Draft: "画布草稿",
  "First Check": "首轮检查",
  "Provider Gate": "Provider 闸门",
  Plan: "计划",
  "Round 1": "首轮",
  "Round 2": "第二轮",
  Candidate: "候选",
  project: "项目",
  short_video_campaign: "短视频内容项目",
  planned_scene: "分镜计划",
  first_generation_check: "首轮检查",
  next_round: "下一轮复用",
  "Reviewable canvas": "可审片画布",
  "Deterministic asset check": "确定性内容检查",
  "Human feedback evidence": "审片反馈证据",
  "Reusable project preference": "可复用项目偏好",
  "Context reuse check": "上下文复用检查",
  "Capability preflight": "能力预检",
  "Operations workspace": "任务中心",
  "Runtime job": "运行任务",
  "Runtime event": "运行事件",
  "Job center": "任务中心",
  "Activity timeline": "运行记录",
  "Review decision recorded": "审片决定已记录",
  "Next round prepared": "下一轮已准备",
  "First generation check": "首轮检查",
  "Open Artifact": "打开证据",
  "Open Result": "打开结果证据",
  "Provider preflight has not run.": "Provider 预检尚未运行。",
  "Provider preflight remains gated.": "Provider 仍保持闸门关闭。",
  "Runtime jobs and provider preflight appear here.": "运行任务和 Provider 预检状态会显示在这里。",
  "No runtime jobs yet.": "还没有运行任务。",
  "Run a first check or provider preflight to create jobs.": "运行首轮检查或 Provider 预检后，这里会出现任务。",
  "Runtime events will appear after deterministic checks or review actions.": "确定性检查或审片操作后，这里会出现运行事件。",
  "Open the run details and inspect the error before retrying.": "先查看运行详情和错误，再决定是否重试。",
  "Provider remains gated; authorize the exact capability before real smoke.": "Provider 仍处于闸门关闭状态；真实 smoke 前必须显式授权对应能力。",
  "Open the first-check report, add missing project material, then retry.": "先查看首轮检查报告，补齐缺失项目材料后再重试。",
  "Open the next-round report and resolve blocked context refs.": "先查看下一轮报告，解决被阻塞的上下文引用。",
  "Decision is evidence only; it does not become durable memory.": "审片决定只是运行证据，不会自动成为长期记忆。",
  "Raw feedback is stored as evidence for later review.": "原始反馈只作为后续复查证据保存。",
  "Open the safe artifact to inspect the generated evidence.": "打开安全产物查看生成证据。",
  "Refresh the workbench to update runtime state.": "刷新工作台以更新运行状态。",
  "Deterministic work is ready; run provider preflight before real smoke.": "确定性链路已准备好；真实模型 smoke 前先运行 Provider 预检。",
  "Check provider readiness before real model smoke.": "真实模型 smoke 前先检查 Provider 就绪度。",
  "Reviewed project style profile is available for the next pass.": "已形成可用于下一轮的项目风格记忆。",
  "No project style memory has been applied yet.": "还没有形成可复用的项目记忆。",
  "Use this profile in the next round context.": "下一轮将复用当前项目风格记忆。",
  "Run and review a first pass before reuse.": "先完成首轮审片，再进入下一轮复用。",
  "Reuse the reviewed profile version for next-pass consistency.": "复用已审片的风格版本，保持下一轮一致性。",
  add_reference: "添加素材摘要",
  draft_canvas: "生成画布草稿",
  start_first_generation_check: "运行首轮检查",
  record_review_note: "记录审片反馈",
  start_next_round: "进入下一轮",
  run_provider_preflight: "Provider 预检",
  resolve_provider_preflight: "Provider 预检",
  ready_to_draft: "可生成草稿",
  provider_blocked: "Provider 阻塞",
  ["provider" + "_config_missing"]: "Provider 配置缺失",
  image_gate_unset: "图像能力闸门未开启",
  video_gate_unset: "视频能力闸门未开启",
  character_reference_image_missing: "缺少角色参考图",
  record_review_decision: "记录审片决定",
  record_feedback: "记录反馈",
  draft_canvas: "生成画布草稿",
  runtime_event: "运行事件",
  asset_test_run: "首轮检查",
  two_round_validate: "下一轮复用",
  provider_validation_plan: "Provider 预检",
  open_style_memory: "打开项目记忆",
  safe_summary: "安全摘要",
  "safe summaries": "安全摘要",
  "safe summary only": "仅安全摘要",
  brief: "需求摘要",
  reference: "参考素材",
  script: "脚本提纲",
  Asset: "素材",
  "Review candidate": "审片候选",
  "Project setup": "项目设置",
  "Build a provider-gated content memory workbench.": "构建一个受 Provider 闸门保护的内容制作与项目记忆工作台。",
  "Plan, inspect, and run the current production canvas from safe project summaries.": "基于安全项目摘要规划、检查并运行当前制作画布。",
  "Plan, inspect, and run the current production canvas from safe project refs.": "基于安全项目引用规划、检查并运行当前制作画布。",
  "The studio is waiting on a visible blocker before the next production action.": "创作工作区正在等待当前可见阻塞被处理后再继续。",
  Hook: "开场钩子",
  Proof: "证明段落",
  CTA: "行动引导",
  "Use approved safe reference summaries.": "使用已确认的安全参考摘要。",
  "Shape the story into hook, proof, and close.": "将内容组织为开场、证明和收束。",
  "Product workbench draft; refine before provider smoke.": "工作台草稿；真实 Provider smoke 前继续细化。",
  "Establish the first three seconds before any provider smoke.": "真实 Provider smoke 前先确认前三秒开场。",
  "Check clarity and visual continuity before next round.": "下一轮前先检查清晰度和视觉连续性。",
  "Keep the ending calm, specific, and reviewable.": "结尾保持克制、具体，并可审片。",
  "Visual reference": "视觉参考",
  "Scene planning": "分镜规划",
  "No artifact loaded": "未加载产物",
  "Reload Artifact": "重新加载产物",
  agentflow_project_manifest: "项目档案",
  agentflow_real_asset_test_report: "首轮检查报告",
  agentflow_two_round_context_runtime_report: "二轮上下文验证报告",
  agentflow_runtime_feedback_event: "运行反馈事件",
  agentflow_runtime_review_decision: "审片决定",
  agentflow_provider_safe_manifest: "Provider 安全档案",
  artifact: "产物",
  unknown: "未知",
  keep: "保留",
  revise: "修改",
  reject: "拒绝",
  "not started": "未启动",
  started: "已启动",
  short_video: "短视频",
  selected_review_candidate: "当前审片候选",
  review_decision: "审片决定",
  review_decision_note: "决定说明",
  source_asset_id: "素材 ID",
  source_asset_label: "素材名称",
  source_asset_summary: "素材摘要",
  "not human acceptance": "非人工验收",
  "not business validation": "非商业验证",
  "not durable memory": "非长期记忆晋升",
  "not durable company memory": "非公司长期记忆",
  "runtime verification is not human acceptance": "运行验证不等于人工验收",
  "provider preflight is not provider smoke": "Provider 预检不等于真实模型 smoke",
  "blocked provider gates require explicit capability authorization": "被阻塞的 Provider 闸门需要显式能力授权",
  "Keep this direction for the next pass.": "保留这个方向，用于下一轮复用。",
  "Resolve provider gate": "处理 Provider 闸门",
  "Provider capability": "Provider 能力",
  "Provider capability gate is still blocked.": "Provider 能力闸门仍处于阻塞状态。",
  "Provider capability gates remain blocked until explicitly authorized.": "Provider 能力闸门在显式授权前保持阻塞。",
  "Provider remains gated; resolve the exact blocked capability before real smoke.": "Provider 仍处于闸门关闭状态；真实 smoke 前先处理被阻塞的具体能力。",
  "Enable the image provider gate before live image smoke.": "真实图像 smoke 前必须先开启图像 Provider 闸门。",
  "Enable the video provider gate before live video smoke.": "真实视频 smoke 前必须先开启视频 Provider 闸门。",
  "Configure provider credentials before live provider smoke.": "真实 Provider smoke 前必须先完成凭据配置；凭据不能进入前端或仓库。",
  "Add a character reference image before live provider smoke.": "真实 Provider smoke 前需要先提供角色参考图。",
};

const SUMMARY_MAP = {
  "Add safe source summaries before drafting or checking content.": "先添加安全素材摘要，再进入草稿或检查。",
  "Add safe source summaries before drafting the production canvas.": "先添加安全素材摘要，再生成制作画布。",
  "Source material is ready; draft a first reviewable canvas.": "素材已就绪，可以生成第一版可审片画布。",
  "Create a first reviewable canvas from the current safe source material.": "基于当前安全素材生成第一版可审片画布。",
  "Run deterministic checks before any real provider smoke.": "在任何真实 provider smoke 前先运行确定性检查。",
  "Record a candidate-bound review decision for the next pass.": "为下一轮记录绑定候选的审片决定。",
  "Reuse accepted context and review evidence in a second pass.": "在第二轮复用已接受的上下文和审片证据。",
  "Check provider readiness without starting a real model run.": "只检查 provider 就绪度，不启动真实模型调用。",
  "Start with safe source summaries.": "从安全素材摘要开始。",
  "Run the first deterministic content check.": "运行第一轮确定性内容检查。",
  "Canvas content is ready for the first deterministic check.": "画布内容已就绪，可以运行首轮确定性检查。",
  "Reference library is ready for planning and review.": "素材库已可用于分镜规划和审片。",
  "Select a card with a safe artifact ref.": "选择带安全产物引用的卡片。",
  "Continue current production step.": "继续当前制作步骤。",
  "Add scene cards and run checks before review.": "添加分镜卡并运行检查后再审片。",
  "Run or draft reviewable output before building project memory.": "先生成可审片输出，再建立项目记忆。",
  "Project review evidence has produced a reusable style profile for the next pass.": "审片证据已经形成可用于下一轮的风格档案。",
  "Editable through the scene inspector before generation.": "生成前可在分镜检查器中继续调整。",
  "Scene card is ready for review.": "分镜卡已可审片。",
};

const STATUS_MAP = {
  blocked: "阻塞",
  failed: "失败",
  in_progress: "进行中",
  needs_assets: "需要素材",
  needs_review: "待审片",
  not_started: "未开始",
  ready: "就绪",
  ready_for_first_check: "可首轮检查",
  ready_for_provider_preflight: "可做 Provider 预检",
  ready_not_run: "就绪未运行",
  ready_to_draft: "可生成草稿",
  provider_blocked: "Provider 阻塞",
  running: "运行中",
  succeeded: "已完成",
  completed_with_blocks: "完成但有阻塞",
  verified: "已验证",
};

export function displayText(value, fallback = "") {
  if (typeof value === "string" && value.endsWith(" safe source summaries are attached.")) {
    const count = value.split(" ")[0];
    return `已登记 ${count} 条安全素材摘要。`;
  }
  if (typeof value === "string" && value.includes(" review candidates are ready for feedback before memory reuse.")) {
    const count = value.split(" ")[0];
    return `${count} 个审片候选已就绪，记录反馈后才能复用为项目记忆。`;
  }
  if (typeof value === "string" && value.includes(" candidates are ready for review.")) {
    const count = value.split(" ")[0];
    return `${count} 个候选已可审片。`;
  }
  if (typeof value === "string" && value.includes(" candidates with ") && value.includes(" recorded decisions.")) {
    return value.replace(" candidates with ", " 个候选，已有 ").replace(" recorded decisions.", " 条审片决定。");
  }
  if (typeof value === "string" && value.includes(" runtime jobs tracked; provider preflight has ") && value.includes(" blockers.")) {
    return value.replace(" runtime jobs tracked; provider preflight has ", " 个运行任务，Provider 预检还有 ").replace(" blockers.", " 个阻塞。");
  }
  if (typeof value === "string" && value.includes(" runtime jobs tracked with no provider preflight blockers.")) {
    return value.replace(" runtime jobs tracked with no provider preflight blockers.", " 个运行任务，Provider 预检没有阻塞。");
  }
  if (typeof value === "string" && value.match(/^\d+ jobs: /)) {
    return value
      .replace(" jobs: ", " 个任务：")
      .replace(" succeeded, ", " 已完成，")
      .replace(" blocked, ", " 阻塞，")
      .replace(" failed.", " 失败。");
  }
  if (typeof value === "string" && value.includes(" runtime events with ") && value.includes(" blocked and ") && value.includes(" failed.")) {
    return value
      .replace(" runtime events with ", " 个运行事件，")
      .replace(" blocked and ", " 个阻塞，")
      .replace(" failed.", " 个失败。");
  }
  if (typeof value === "string" && value.startsWith("Target: ")) return `目标平台：${TEXT_MAP[value.slice(8)] || value.slice(8)}`;
  if (typeof value === "string" && value.startsWith("Open with the audience problem and project promise: ")) {
    return `提出受众问题和项目承诺：${displayText(value.slice(51).trim())}`;
  }
  if (typeof value === "string" && value.startsWith("Show the concrete product or story proof: ")) {
    return `展示具体产品或叙事证据：${displayText(value.slice(42).trim())}`;
  }
  if (typeof value === "string" && value.startsWith("Close with a simple next step that matches the project goal: ")) {
    return `用匹配项目目标的简单下一步收束：${displayText(value.slice(60).trim())}`;
  }
  if (typeof value === "string" && value.startsWith("Provider calls: ")) return `Provider 调用：${TEXT_MAP[value.slice(16)] || value.slice(16)}`;
  if (typeof value === "string" && value.startsWith("Verification: ")) return `验证：${displayStatus(value.slice(14), value.slice(14))}`;
  if (typeof value === "string" && value.startsWith("Assessment: ")) return `评估：${TEXT_MAP[value.slice(12)] || value.slice(12)}`;
  if (typeof value === "string" && value.startsWith("Blockers: ")) return `阻塞项：${value.slice(10)}`;
  return TEXT_MAP[value] || SUMMARY_MAP[value] || value || fallback;
}

export function displayStatus(value, fallback = "未开始") {
  return STATUS_MAP[value] || value || fallback;
}

export function displayList(items) {
  return (Array.isArray(items) ? items : []).map((item) => displayText(item));
}
