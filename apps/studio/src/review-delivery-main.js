import { ensureAuthSession, signOut } from "./auth-gate.js";
import {
  authToken,
  createRuntimeClient,
  runtimeBaseUrl,
  runtimeMediaUrl,
  saveAuthToken,
} from "./runtime-client.js";
import { clearProjectSession, safeProjectId } from "./studio-project-session.js";
import { clearIdentityScopedStudioState } from "./store-persistence.js";
import {
  submitDedicatedReviewDecision,
} from "./candidate-selection-controller.js";
import {
  submitDedicatedProductionExport,
  submitDedicatedQualityApproval,
} from "./production-delivery-controller.js";
import {
  composeReviewDeliveryState,
  createReviewDeliveryState,
  focusReviewCandidate,
  protectedPreviewDisposition,
  selectedDeliverySubmission,
} from "./review-delivery-state.js";
import { renderReviewDeliveryWorkspace } from "./review-delivery-workspace.js";

let runtime = createRuntimeClient("studio-pending");
let mountedRoot = null;
let boundaryInFlight = false;
const previewObjectUrls = new Set();
const canonicalPreviewSession = {
  readToken: authToken,
  resolveUrl: runtimeMediaUrl,
  baseUrl: runtimeBaseUrl,
  clearToken: saveAuthToken,
};
const reviewState = createReviewDeliveryState((state) => {
  if (!mountedRoot) return;
  renderReviewDeliveryWorkspace(mountedRoot, state, handlers);
});

const handlers = {
  onProjectChange: (projectId) => void loadReviewWorkspace(projectId),
  onCandidateFocus: (candidateId, options = {}) => {
    reviewState.publish(focusReviewCandidate(reviewState.get(), candidateId));
    if (options.focus) requestAnimationFrame(() => mountedRoot?.querySelector('[role="radio"][aria-checked="true"]')?.focus());
  },
  onAction: (action) => void handleAction(action),
  canonicalPreviewSession,
};

if (!redirectLegacyReviewEntry()) bootstrap().catch((error) => showSecureEntry(readError(error), { error: true }));

function redirectLegacyReviewEntry() {
  const projectId = requestedProjectId();
  const target = new URL("/studio/", window.location.origin);
  if (projectId) target.searchParams.set("project", projectId);
  target.searchParams.set("stage", "review");
  window.location.replace(target.toString());
  return true;
}

async function bootstrap() {
  showSecureEntry("正在确认账户状态…");
  bindIdentityBoundary();
  const authRuntime = createRuntimeClient("studio-pending");
  const authState = await ensureAuthSession(authRuntime);
  if (authState?.auth_status_unknown || authState?.blocked) return;
  if (authState?.auth_required && !authState?.authenticated) return;
  reviewState.setIdentity(authState?.user || { user_id: "local-runtime-user" });
  mountReviewSurface();
  await loadReviewWorkspace(requestedProjectId());
}

function mountReviewSurface() {
  const app = document.getElementById("app");
  app.className = "review-page";
  app.replaceChildren();
  mountedRoot = document.createElement("div");
  mountedRoot.id = "review-delivery-root";
  const overlay = document.createElement("div");
  overlay.id = "overlay-root";
  app.append(mountedRoot, overlay);
  renderReviewDeliveryWorkspace(mountedRoot, reviewState.get(), handlers);
}

async function loadReviewWorkspace(requestedId = "") {
  revokePreviewMedia();
  const token = reviewState.beginLoad(requestedId);
  try {
    const discoveryRuntime = createRuntimeClient("studio-pending");
    const workspace = await discoveryRuntime.workspaceOverview();
    if (!reviewState.isCurrent(token)) return;
    const projects = Array.isArray(workspace?.projects) ? workspace.projects : [];
    if (!projects.length) {
      runtime = discoveryRuntime;
      reviewState.publish({ phase: "empty", workspace, project: null, projectId: "", error: "" });
      focusMain();
      return;
    }
    const safeRequested = safeProjectId(requestedId);
    const projectId = projects.some((item) => item.project_id === safeRequested)
      ? safeRequested
      : projects[0].project_id;
    runtime = createRuntimeClient(projectId);
    const [projectPayload, runsPayload] = await Promise.all([
      runtime.projectOverview(),
      runtime.listProductionRuns(),
    ]);
    if (!reviewState.isCurrent(token)) return;
    const next = composeReviewDeliveryState({
      workspace,
      project: projectPayload?.project || null,
      runsPayload,
      projectId,
    });
    next.candidates = await hydrateCandidateMedia(next.candidates, token);
    if (!reviewState.isCurrent(token)) return;
    reviewState.publish(next);
    syncProjectUrl(projectId);
    focusMain();
  } catch (error) {
    if (!reviewState.isCurrent(token)) return;
    reviewState.publish({ phase: "read_error", error: readError(error), busy: "" });
    focusMain();
  }
}

async function handleAction(action) {
  if (action === "signout") return handleSignOut();
  if (action === "reload") return window.location.reload();
  if (action === "retry" || action === "refresh") return loadReviewWorkspace(reviewState.get().projectId);
  const state = reviewState.get();
  if (state.busy || state.stale) return;

  const note = String(mountedRoot?.querySelector("[data-revision-note]")?.value || "").trim();
  const checklist = Object.fromEntries([...mountedRoot?.querySelectorAll("[data-quality-check]") || []]
    .map((input) => [input.dataset.qualityCheck, input.checked === true]));
  const selectedDelivery = selectedDeliverySubmission(state);
  if (["revise", "reject"].includes(action) && !note) {
    reviewState.publish({ writeError: "请先写明修改原因，再提交这次主创决定。", notice: "" });
    mountedRoot?.querySelector("[data-revision-note]")?.focus();
    return;
  }
  if (action === "approve" && Object.values(checklist).some((checked) => checked !== true)) {
    reviewState.publish({ writeError: "请逐项完成叙事、画面一致性、镜头覆盖与改版要求检查。", notice: "" });
    mountedRoot?.querySelector("[data-quality-check]:not(:checked)")?.focus();
    return;
  }
  if (["approve", "export"].includes(action) && !selectedDelivery) {
    reviewState.publish({
      stale: true,
      deliverySnapshot: null,
      writeError: "",
      notice: "",
      error: "当前交付版本与权威选择不一致，请读取最新状态。",
    });
    focusMain();
    return;
  }

  const token = reviewState.beginAction(action);
  if (!token) return;
  let result;
  if (["select", "revise", "reject"].includes(action)) {
    const intent = action === "select" ? "将当前方案设为制作基准。" : note;
    result = await submitDedicatedReviewDecision(runtime, state.reviewSnapshot, action, intent);
  } else if (action === "approve") {
    result = await submitDedicatedQualityApproval(runtime, selectedDelivery.snapshot, checklist);
  } else if (action === "export") {
    result = await submitDedicatedProductionExport(runtime, selectedDelivery.snapshot);
  } else {
    reviewState.finishAction(token);
    return;
  }
  if (!reviewState.isCurrent(token)) return;
  if (result?.ok) {
    const notice = successMessage(action);
    reviewState.finishAction(token, { notice, writeError: "", stale: false });
    await loadReviewWorkspace(state.projectId);
    if (reviewState.get().phase === "ready") reviewState.publish({ notice });
    return;
  }
  if (result?.stale) {
    reviewState.finishAction(token, {
      stale: true,
      writeError: "",
      notice: "",
      error: result.message || "版本已发生变化。",
      deliverySnapshot: null,
    });
    focusMain();
    return;
  }
  reviewState.finishAction(token, {
    writeError: writeError(result),
    notice: "",
  });
  focusMain();
}

function bindIdentityBoundary() {
  window.addEventListener("afs:auth-session-expired", () => void recoverExpiredSession());
}

async function handleSignOut() {
  if (boundaryInFlight) return;
  boundaryInFlight = true;
  const logoutRuntime = runtime;
  clearReviewIdentity("正在安全退出…");
  try {
    await signOut(logoutRuntime);
  } finally {
    window.location.replace("/studio/");
  }
}

async function recoverExpiredSession() {
  if (boundaryInFlight) return;
  boundaryInFlight = true;
  clearReviewIdentity("登录已过期，请重新登录后继续。", { error: true });
  await signOut(runtime);
  const authState = await ensureAuthSession(createRuntimeClient("studio-pending"), {
    onAuthenticated: () => window.location.reload(),
  });
  if (!authState?.auth_required || authState?.authenticated) window.location.reload();
}

function clearReviewIdentity(message, options = {}) {
  reviewState.clearIdentity();
  revokePreviewMedia();
  mountedRoot?.replaceChildren();
  mountedRoot = null;
  clearProjectSession();
  clearIdentityScopedStudioState();
  showSecureEntry(message, options);
}

async function hydrateCandidateMedia(candidates, token) {
  const sessionToken = authToken();
  return Promise.all(candidates.map(async (item) => {
    if (!item.preview_url || !sessionToken) return { ...item, available: false, preview_url: "" };
    try {
      const response = await fetch(runtime.toMediaUrl(item.preview_url), {
        headers: { Authorization: `Bearer ${sessionToken}` },
        cache: "no-store",
      });
      if (!response.ok) {
        if (protectedPreviewDisposition(response.status) === "session_expired") {
          saveAuthToken("");
          window.dispatchEvent(new CustomEvent("afs:auth-session-expired", {
            detail: { route: item.preview_url, status: response.status },
          }));
          return { ...item, available: false, preview_url: "" };
        }
        throw new Error("preview_unavailable");
      }
      const contentType = String(response.headers.get("content-type") || "").toLowerCase();
      const expectedContentType = item.media_kind === "video" ? "video/" : "image/";
      if (!contentType.startsWith(expectedContentType)) throw new Error("preview_type_invalid");
      const blob = await response.blob();
      if (!reviewState.isCurrent(token)) return { ...item, available: false, preview_url: "" };
      const objectUrl = URL.createObjectURL(blob);
      previewObjectUrls.add(objectUrl);
      return {
        ...item,
        available: true,
        preview_url: objectUrl,
      };
    } catch {
      return { ...item, available: false, preview_url: "" };
    }
  }));
}

function revokePreviewMedia() {
  for (const url of previewObjectUrls) URL.revokeObjectURL(url);
  previewObjectUrls.clear();
}

function showSecureEntry(message, { error = false } = {}) {
  const app = document.getElementById("app");
  app.className = "identity-pending";
  app.replaceChildren();
  const secure = document.createElement("main");
  secure.id = "secure-entry";
  secure.setAttribute("aria-live", "polite");
  const brand = document.createElement("strong");
  brand.textContent = "AgentFlow Studio";
  const text = document.createElement("p");
  text.textContent = message;
  secure.append(brand, text);
  secure.classList.toggle("error", error);
  const overlay = document.createElement("div");
  overlay.id = "overlay-root";
  app.append(secure, overlay);
}

function requestedProjectId() {
  try {
    return safeProjectId(new URL(window.location.href).searchParams.get("project"));
  } catch {
    return "";
  }
}

function syncProjectUrl(projectId) {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("project", projectId);
    window.history.replaceState({}, "", url);
  } catch {
    // The authoritative project is still scoped by the authenticated runtime.
  }
}

function focusMain() {
  requestAnimationFrame(() => document.getElementById("review-main")?.focus());
}

function successMessage(action) {
  return ({
    select: "当前方案已保存，并已读取最新版本。",
    revise: "返修要求已保存，并已读取最新版本。",
    reject: "退回决定已保存，批准与导出已撤销。",
    approve: "当前修订的质量门禁已通过。",
    export: "交付包已生成，并已读取交付记录。",
  })[action] || "状态已更新。";
}

function readError(error) {
  if ([401, 403].includes(Number(error?.status))) return "账户状态已变化，请重新登录后继续。";
  if (Number(error?.status) === 404) return "这个项目暂时没有可读取的审核状态。";
  return "暂时无法读取最新审核状态，请检查连接后重试。";
}

function writeError(result) {
  if (["auth_required", "delivery_auth_required"].includes(result?.code)) return "账户状态已变化，请重新登录后继续。";
  if (result?.code === "missing_revision_intent") return "请先写明修改原因。";
  if (result?.code === "delivery_checklist_incomplete") return "请完成所有可用的交付检查。";
  return "这次操作没有保存。请读取最新状态后重试。";
}
