import {
  renderArtifactTimeline,
  renderBridgeHealth,
  renderOverview,
  renderProductionVideoReview,
  renderProductionPath,
  renderReadinessWizard,
  renderStepTimeline,
  renderSupervision,
  renderWorkflowProfile,
  renderWorkflowSelect,
} from "./production-render.js";
import {
  DEMO_WORKFLOW_NAME,
  PRODUCT_WORKFLOW_NAME,
  knownWorkflowInputs,
  preferredWorkflow,
  workflowByName,
  workflowDefaultInput,
  workflowDefaultOutput,
  workflowRequires,
} from "./production-workflows.js";

const BRIDGE_BASE_URL = "http://127.0.0.1:8787";
const RUN_POLL_INTERVAL_MS = 1500;
let runPollTimer = null;

export const productionState = {
  bridge: null,
  workflows: [],
  selectedWorkflowPath: "",
  plan: null,
  run: null,
  review: null,
  log: ["Production Mode 只连接本机 bridge，不上传媒体或调用远程服务。"],
  supervisionEvents: [],
};

export function initializeProductionMode(elements, copy) {
  elements.quickDemoButton.addEventListener("click", () => selectWorkflowByName(DEMO_WORKFLOW_NAME, elements, copy));
  elements.productWorkflowButton.addEventListener("click", () => selectWorkflowByName(PRODUCT_WORKFLOW_NAME, elements, copy));
  elements.createPlanButton.addEventListener("click", () => createPlan(elements, copy));
  elements.runWorkflowButton.addEventListener("click", () => runSelectedWorkflow(elements, copy));
  elements.refreshReviewButton.addEventListener("click", () => refreshReview(elements, copy));
  elements.workflowSelect.addEventListener("change", () => {
    productionState.selectedWorkflowPath = elements.workflowSelect.value;
    applyWorkflowDefaults(elements, { force: true });
    renderProductionState(elements, copy);
  });
  checkBridge(elements, copy);
}

export async function checkBridge(elements, copy) {
  try {
    const [health, workflowsPayload] = await Promise.all([bridgeGet("/health"), bridgeGet("/workflows")]);
    productionState.bridge = health;
    productionState.workflows = workflowsPayload.workflows || [];
    productionState.selectedWorkflowPath = productionState.selectedWorkflowPath || preferredWorkflow(productionState.workflows);
    appendLog(`Bridge ${health.status}: ${BRIDGE_BASE_URL}`);
  } catch (error) {
    productionState.bridge = { status: "offline", error: error.message };
    appendLog(`Bridge offline: ${error.message}`);
  }
  productionState.selectedWorkflowPath = renderWorkflowSelect(
    elements,
    productionState.workflows,
    productionState.selectedWorkflowPath,
  );
  applyWorkflowDefaults(elements, { force: false });
  renderProductionState(elements, copy);
}

export async function createPlan(elements, copy) {
  const workflowPath = selectedWorkflowPath(elements);
  try {
    const plan = await bridgePost("/plans", {
      workflow_path: workflowPath,
      input_path: elements.workflowInputPath.value,
      output_dir: `${elements.workflowOutputDir.value}_plan`,
    });
    productionState.plan = plan;
    appendLog(`已生成 workflow_plan.json: ${plan.plan_path}`);
  } catch (error) {
    appendLog(`生成计划失败: ${error.message}`);
  }
  renderProductionState(elements, copy);
}

export async function runSelectedWorkflow(elements, copy) {
  const workflowPath = selectedWorkflowPath(elements);
  try {
    const run = await bridgePost("/runs", {
      workflow_path: workflowPath,
      input_path: elements.workflowInputPath.value,
      output_dir: elements.workflowOutputDir.value,
    });
    productionState.run = run;
    appendLog(`Workflow ${run.status}: ${run.run_dir}`);
    startRunPolling(elements, copy);
  } catch (error) {
    appendLog(`运行失败: ${error.message}`);
  }
  renderProductionState(elements, copy);
}

export async function refreshReview(elements, copy) {
  if (!elements.workflowOutputDir.value) {
    appendLog("缺少 output directory，无法刷新验收报告。");
    renderProductionState(elements, copy);
    return;
  }
  try {
    const review = await bridgePost(`/runs/${encodeURIComponent(elements.workflowOutputDir.value)}/review`, {});
    productionState.review = review;
    appendLog(`验收报告已刷新: ${review.status}`);
  } catch (error) {
    appendLog(`刷新验收报告失败: ${error.message}`);
  }
  renderProductionState(elements, copy);
}

export function renderProductionState(elements, copy, workspace = null) {
  const workflow = selectedWorkflow();
  const activePathIndex = !productionState.plan ? 1 : !productionState.run ? 2 : !productionState.review ? 3 : 4;
  const readiness = productionReadiness(workflow);
  renderBridgeHealth(elements, productionState.bridge);
  renderWorkflowProfile(elements, workflow, copy);
  renderReadinessWizard(elements, productionState, workflow, readiness);
  renderOverview(elements, productionState, workflow, blockerText(), inputCheckText(), nextAction());
  renderProductionPath(productionState.run?.status || "pending", activePathIndex);
  renderStepTimeline(elements, productionState.run?.steps || productionState.plan?.steps || workflow?.steps || [], copy);
  renderArtifactTimeline(elements, productionState.run?.files || [], productionState.plan?.artifacts?.expected || workflow?.outputs || []);
  renderProductionVideoReview(elements, productionState, workspace, copy);
  renderSupervision(elements, productionState, copy);
  renderProductionButtons(elements);
  elements.productionLog.textContent = productionState.log.slice(-16).join("\n");
}

function renderProductionButtons(elements) {
  const running = ["pending", "running"].includes(productionState.run?.status || "");
  elements.runWorkflowButton.disabled = running;
  elements.createPlanButton.disabled = running;
  elements.refreshReviewButton.disabled = running;
}

function applyWorkflowDefaults(elements, { force }) {
  const workflow = selectedWorkflow();
  const defaultInput = workflowDefaultInput(workflow);
  const defaultOutput = workflowDefaultOutput(workflow);
  const currentInput = elements.workflowInputPath.value.trim();
  const shouldReplaceInput = force || !currentInput || knownWorkflowInputs().includes(currentInput);
  if (shouldReplaceInput) elements.workflowInputPath.value = defaultInput;
  const currentOutput = elements.workflowOutputDir.value.trim();
  const shouldReplaceOutput = force || !currentOutput || currentOutput.startsWith("data/processed/runs/web_bridge/");
  if (shouldReplaceOutput) elements.workflowOutputDir.value = defaultOutput;
}

async function bridgeGet(path) {
  const response = await fetch(`${BRIDGE_BASE_URL}${path}`);
  return readBridgeResponse(response);
}

async function bridgePost(path, payload) {
  const response = await fetch(`${BRIDGE_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readBridgeResponse(response);
}

async function readBridgeResponse(response) {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.error || `HTTP ${response.status}`);
  return payload;
}

function selectedWorkflowPath(elements) {
  return elements.workflowSelect.value || productionState.selectedWorkflowPath || preferredWorkflow(productionState.workflows);
}

function selectedWorkflow() {
  return productionState.workflows.find((workflow) => workflow.path === productionState.selectedWorkflowPath);
}

function nextAction() {
  if (!productionState.bridge || productionState.bridge.status === "offline") return "启动本地 bridge";
  if (!productionState.plan) return "生成 workflow_plan.json";
  if (["pending", "running"].includes(productionState.run?.status || "")) return "观察步骤执行";
  if (!productionState.run) return "运行 workflow";
  if (!productionState.review) return "刷新验收报告";
  return "进入 Review Mode 审片";
}

function productionReadiness(workflow) {
  const blocker = blockerText();
  if (!productionState.bridge || productionState.bridge.status === "offline") {
    return { status: "blocked", nextAction: "启动本地 bridge", blocker };
  }
  if (blocker !== "暂无阻塞") {
    return { status: "blocked", nextAction: workflow?.web_profile?.quick_start ? "检查输入后运行演示" : "先处理阻塞项", blocker };
  }
  if (!productionState.plan) return { status: "ready", nextAction: "生成 workflow_plan.json", blocker: "" };
  if (!productionState.run) return { status: "ready", nextAction: "运行 workflow", blocker: "" };
  if (!productionState.review) return { status: "ready", nextAction: "刷新验收报告", blocker: "" };
  return { status: "ready", nextAction: "进入 Review Mode 审片", blocker: "" };
}

function blockerText() {
  if (!productionState.bridge || productionState.bridge.status === "offline") return "本机 bridge 未连接";
  const inputCheck = productionState.run?.input_check || productionState.plan?.input_check;
  if (inputCheck?.status === "fail") return inputCheck.warnings?.join("; ") || "输入文件引用缺失";
  if (productionState.run?.status === "failed") return (productionState.run.errors || []).join("; ") || "workflow failed";
  if (
    workflowRequires(selectedWorkflow(), "local_asr") &&
    productionState.bridge.local_asr?.status === "missing_optional_dependency"
  ) {
    return `本地 ASR 依赖缺失: ${productionState.bridge.local_asr.missing.join(", ")}`;
  }
  if (workflowRequires(selectedWorkflow(), "ffmpeg") && productionState.bridge.media?.status !== "ready") {
    return "FFmpeg/FFprobe 未完全就绪";
  }
  return "暂无阻塞";
}

export function selectWorkflowByName(name, elements, copy) {
  const workflow = workflowByName(productionState.workflows, name);
  if (!workflow) {
    appendLog(`未找到 workflow: ${name}`);
    renderProductionState(elements, copy);
    return;
  }
  productionState.selectedWorkflowPath = workflow.path;
  productionState.plan = null;
  productionState.run = null;
  productionState.review = null;
  productionState.selectedWorkflowPath = renderWorkflowSelect(
    elements,
    productionState.workflows,
    productionState.selectedWorkflowPath,
  );
  applyWorkflowDefaults(elements, { force: true });
  appendLog(`已切换到 ${workflow.name}`);
  renderProductionState(elements, copy);
}

function inputCheckText() {
  const inputCheck = productionState.run?.input_check || productionState.plan?.input_check;
  if (!inputCheck) return "";
  if (inputCheck.status === "pass") return `${inputCheck.inputs?.length || 0} 个输入引用可用`;
  return `缺失: ${(inputCheck.missing || []).slice(0, 3).join(", ")}`;
}

async function pollRunStatus(elements, copy) {
  if (!productionState.run?.run_dir) return;
  try {
    productionState.run = await bridgeGet(`/runs/${encodeURIComponent(productionState.run.run_dir)}`);
    appendLog(`Run ${productionState.run.status}: ${productionState.run.current_step || productionState.run.event || productionState.run.run_id}`);
    if (!["pending", "running"].includes(productionState.run.status)) stopRunPolling();
  } catch (error) {
    appendLog(`刷新 run 状态失败: ${error.message}`);
    stopRunPolling();
  }
  renderProductionState(elements, copy);
}

function startRunPolling(elements, copy) {
  stopRunPolling();
  runPollTimer = window.setInterval(() => pollRunStatus(elements, copy), RUN_POLL_INTERVAL_MS);
  pollRunStatus(elements, copy);
}

function stopRunPolling() {
  if (runPollTimer) {
    window.clearInterval(runPollTimer);
    runPollTimer = null;
  }
}

export function recordSupervisionIntent(intent, elements, copy) {
  productionState.supervisionEvents.push(`${new Date().toLocaleTimeString()} ${intent}`);
  appendLog(`监督意图: ${intent}`);
  renderProductionState(elements, copy);
}

function appendLog(message) {
  productionState.log.push(`[${new Date().toLocaleTimeString()}] ${message}`);
}
