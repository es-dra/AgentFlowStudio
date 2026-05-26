import { clearNode, metaLine, metricCard, node, row, statusPill } from "./render-helpers.js";
import { workflowDisplayName, workflowProfileSummary, workflowRequirementsText, workflowRequires } from "./production-workflows.js";
import { renderLocalVideoPreview } from "./video-preview.js";

export function renderBridgeHealth(elements, bridge) {
  const status = bridge?.status || "unknown";
  elements.bridgeHealth.textContent = `bridge ${status}`;
  elements.bridgeHealth.className = `chip status-${status === "ready" ? "pass" : status === "offline" ? "fail" : "warning"}`;
}

export function renderAcceptancePath(elements, state, nextAction, blockerText) {
  if (!elements.productionNextAction || !elements.acceptancePathDetail) return;
  const blocked = Boolean(blockerText && blockerText !== "暂无阻塞");
  elements.productionNextAction.textContent = nextAction;
  elements.productionNextAction.className = `chip status-${blocked ? "warning" : "pass"}`;
  elements.acceptancePathDetail.textContent = blocked
    ? `先处理：${blockerText}`
    : acceptanceDetail(state);
}

export function renderWorkflowProfile(elements, workflow, copy) {
  if (!elements.workflowProfile) return;
  clearNode(elements.workflowProfile);
  if (!workflow) {
    elements.workflowProfile.textContent = "等待本机 bridge 返回 workflows/*.yaml 列表。";
    return;
  }
  const profile = workflow.web_profile || {};
  elements.workflowProfile.append(
    row(profile.kind === "demo" ? "本机演示" : "完整成品", statusPill(profile.quick_start ? "pass" : "warning", copy)),
    metaLine(profile.display_name || workflow.name),
    metaLine(workflowProfileSummary(workflow)),
    metaLine(`依赖: ${workflowRequirementsText(workflow)}`),
  );
}

function acceptanceDetail(state) {
  if (!state.plan) return "当前验收路径：先连 bridge，再生成计划。浏览器不保存状态，不读取 provider secrets。";
  if (!state.run) return "当前验收路径：计划已生成，下一步运行本机 workflow。";
  if (!state.review) return "当前验收路径：运行完成后刷新验收报告。";
  return "当前验收路径：回到 Review Mode 选择产物审片，并记录人工验收意见。";
}

export function renderReadinessWizard(elements, state, workflow, readiness) {
  clearNode(elements.readinessChecklist);
  const bridgeStatus = state.bridge?.status || "offline";
  const media = state.bridge?.media || {};
  const localAsr = state.bridge?.local_asr || {};
  const inputCheck = state.run?.input_check || state.plan?.input_check;
  const profile = workflow?.web_profile || {};

  elements.readinessChecklist.append(
    metricCard("生产目标", workflowDisplayName(workflow), profile.kind === "demo" ? "本机演示，可用于验证链路" : "完整成品包，需要本地依赖和素材"),
    metricCard("本机环境", bridgeStatus, environmentDetail(state.bridge, workflow)),
    metricCard("输入诊断", inputCheck?.summary || "尚未生成计划，等待检查 input bundle", inputCheck?.next_action || "先生成 workflow_plan.json"),
    metricCard("下一步动作", readiness.nextAction, readiness.blocker || profile.next_step_hint || "检查输入后再继续"),
  );
}

export function renderOverview(elements, state, workflow, blockerText, inputCheckText, nextAction) {
  clearNode(elements.productionOverview);
  const run = state.run;
  const review = state.review;
  elements.productionOverview.append(
    metricCard("当前任务", workflowDisplayName(workflow), workflow?.name || "未选择 workflow"),
    metricCard("下一步", nextAction, "生成计划、运行流程、刷新验收或进入 Review Mode"),
    metricCard("阻塞项", blockerText, inputCheckText || "本地 bridge、输入文件、FFmpeg/ASR 依赖会影响执行"),
    metricCard("当前步骤", run?.current_step || run?.event || "等待启动", "运行中会轮询 bridge_status.json"),
    metricCard(
      "可交付物",
      review?.package_report || run?.manifest_path || run?.bridge_status_path || "等待 workflow_plan.json",
      "workflow_plan.json / manifest.json / review_report.json",
    ),
  );
}

export function renderProductionVideoReview(elements, state, workspace, copy) {
  if (!elements.productionVideoPreview || !elements.productionAssetMatch) return;
  clearNode(elements.productionVideoPreview);
  clearNode(elements.productionAssetMatch);

  const video = workspace?.videos?.[0];
  if (video?.localFile) {
    renderLocalVideoPreview(elements.productionVideoPreview, video, copy);
  } else {
    elements.productionVideoPreview.textContent = "显式选择视频后，这里会显示本地成片预览；不会自动读取 manifest 路径。";
  }

  const files = state.run?.files || [];
  const assetFiles = files.filter((file) => /final_video|finished_package|subtitle|cover|bgm|audio_mix/i.test(file));
  if (!assetFiles.length) {
    elements.productionAssetMatch.textContent = "运行 workflow 后，会在这里显示 final video、subtitle、cover、BGM 等 asset 提示。";
    return;
  }
  for (const file of assetFiles.slice(0, 10)) {
    const maybeMatch = video?.fileName && file.toLowerCase().includes(video.fileName.toLowerCase());
    elements.productionAssetMatch.append(
      row(file, statusPill(maybeMatch ? "pass" : "unknown", copy)),
      metaLine(maybeMatch ? "可能对应最终成片" : "仅展示 artifact 路径提示，不自动读取磁盘"),
    );
  }
}

export function renderProductionPath(status, activeIndex) {
  const items = Array.from(document.querySelectorAll("#production-path li"));
  items.forEach((item, index) => {
    item.classList.toggle("active", index === activeIndex);
    item.classList.toggle("done", index < activeIndex || (index === 2 && ["success", "failed"].includes(status)));
  });
}

export function renderStepTimeline(elements, steps, copy) {
  clearNode(elements.stepTimeline);
  if (!steps.length) {
    elements.stepTimeline.textContent = "选择 workflow 后，这里会显示计划步骤；运行后会显示真实 step status。";
    return;
  }
  for (const [index, step] of steps.entries()) {
    const status = step.status || step.execution_status || "not_started";
    const label = step.id || step.step_id || `step_${index + 1}`;
    const type = step.type || step.tool || "";
    elements.stepTimeline.append(
      row(`${String(index + 1).padStart(2, "0")} ${label}`, statusPill(status, copy)),
      metaLine(`${type} | inputs: ${compactList(step.inputs)} | outputs: ${compactList(step.outputs || step.expected_outputs)}${step.duration_ms ? ` | ${step.duration_ms} ms` : ""}`),
    );
    if (step.error) elements.stepTimeline.append(metaLine(`error: ${step.error}`));
  }
}

export function renderArtifactTimeline(elements, files, expected) {
  clearNode(elements.productionArtifacts);
  const values = files.length ? files : expected;
  if (!values.length) {
    elements.productionArtifacts.textContent = "生成 plan 或运行 workflow 后，这里会列出预期/实际 artifact。";
    return;
  }
  for (const value of values.slice(0, 20)) {
    elements.productionArtifacts.append(metricCard("artifact", value, files.length ? "actual run file" : "expected output"));
  }
}

export function renderSupervision(elements, state, copy) {
  clearNode(elements.supervisionPanel);
  const run = state.run;
  const review = state.review;
  elements.supervisionPanel.append(
    row("确认继续", statusPill(run?.status === "success" ? "pass" : "unknown", copy)),
    metaLine("用于确认当前 gate 通过，继续到下一步或进入验收。"),
    row("记录暂停意见", statusPill("warning", copy)),
    metaLine("仅记录人工意见，不直接中断已启动的本地 Python 步骤。"),
    row("记录重跑建议", statusPill("warning", copy)),
    metaLine("当前不伪装成 step-level rerun；如需重跑，先重新运行整个 workflow。"),
    row("记录修改意见", statusPill(review?.status === "failed" ? "fail" : "unknown", copy)),
    metaLine("可先在反馈事件里记录意见，后续再接 run note。"),
  );
  if (state.supervisionEvents.length) {
    elements.supervisionPanel.append(metaLine(`本次监督意图: ${state.supervisionEvents.slice(-4).join(" / ")}`));
  }
}

export function renderWorkflowSelect(elements, workflows, selectedWorkflowPath) {
  const desired = selectedWorkflowPath || elements.workflowSelect.value;
  clearNode(elements.workflowSelect);
  for (const workflow of workflows) {
    const option = node("option", "", `${workflow.name} (${workflow.metadata?.status || workflow.status})`);
    option.value = workflow.path;
    elements.workflowSelect.append(option);
  }
  elements.workflowSelect.value = [...elements.workflowSelect.options].some((option) => option.value === desired)
    ? desired
    : workflows[0]?.path || "";
  return elements.workflowSelect.value;
}

function compactList(value) {
  if (Array.isArray(value)) return value.slice(0, 4).join(", ") || "-";
  if (value && typeof value === "object") return Object.values(value).slice(0, 4).join(", ") || "-";
  return value ? String(value) : "-";
}

function environmentDetail(bridge, workflow) {
  if (!bridge) return "本机 bridge 未连接。";
  const details = [`Python ${bridge.python?.version || "unknown"}`];
  if (workflowRequires(workflow, "ffmpeg")) details.push(`FFmpeg ${bridge.media?.status || "unknown"}`);
  if (workflowRequires(workflow, "local_asr")) details.push(`local ASR ${bridge.local_asr?.status || "unknown"}`);
  return details.join(" | ");
}
