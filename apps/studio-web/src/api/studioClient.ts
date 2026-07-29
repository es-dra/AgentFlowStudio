import {
  apiSurfaceFor,
  type AppSurface,
  type StudioReworkConfirmReceipt,
  type StudioReworkPreviewReceipt,
  type StudioRequestError,
  type StudioSurfaceEnvelope
} from "./studioTypes";

const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";
const runtimeQueryKeys = ["runtimeBaseUrl", "runtime_base_url", "runtime"];

interface GetStudioSurfaceOptions {
  projectId: string;
  surface: AppSurface;
  signal?: AbortSignal;
}

export async function getStudioSurface({
  projectId,
  surface,
  signal
}: GetStudioSurfaceOptions): Promise<StudioSurfaceEnvelope> {
  const encodedProjectId = encodeURIComponent(projectId);
  const apiSurface = apiSurfaceFor(surface);
  const headers: HeadersInit = { Accept: "application/json" };
  const token = readAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(
      `${resolveRuntimeBaseUrl()}/api/v1/projects/${encodedProjectId}/studio?surface=${apiSurface}`,
      { headers, signal }
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw requestError("error", 0, "未能连接制作服务，页面没有覆盖任何已有结果。");
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw requestError("forbidden", response.status, "你没有查看这个项目的权限。");
    }
    if (response.status === 404) {
      throw requestError("empty", response.status, "没有找到这个项目或工作面。");
    }
    if (response.status === 409) {
      throw requestError("stale", response.status, "内容已经更新，需要重新检查。");
    }
    throw requestError("error", response.status, "读取项目失败，已有结果保持不变。");
  }

  return parseStudioEnvelope(await response.json());
}

interface ReworkCommandOptions {
  projectId: string;
  targetEntityId: string;
  expectedGraphVersion: number;
  expectedGraphDigest: string;
  signal?: AbortSignal;
}

interface ConfirmReworkOptions extends ReworkCommandOptions {
  previewId: string;
  idempotencyKey: string;
}

export async function previewLocalRework({
  projectId,
  targetEntityId,
  expectedGraphVersion,
  expectedGraphDigest,
  signal
}: ReworkCommandOptions): Promise<StudioReworkPreviewReceipt> {
  const payload = await postStudioCommand({
    projectId,
    path: "preview",
    body: {
      target_entity_id: targetEntityId,
      expected_graph_version: expectedGraphVersion,
      expected_graph_digest: expectedGraphDigest
    },
    signal
  });
  return parseReworkPreviewReceipt(payload);
}

export async function confirmLocalRework({
  projectId,
  targetEntityId,
  expectedGraphVersion,
  expectedGraphDigest,
  previewId,
  idempotencyKey,
  signal
}: ConfirmReworkOptions): Promise<StudioReworkConfirmReceipt> {
  const payload = await postStudioCommand({
    projectId,
    path: "confirm",
    body: {
      target_entity_id: targetEntityId,
      expected_graph_version: expectedGraphVersion,
      expected_graph_digest: expectedGraphDigest,
      preview_id: previewId,
      idempotency_key: idempotencyKey
    },
    signal
  });
  return parseReworkConfirmReceipt(payload);
}

export function resolveRuntimeBaseUrl(location = window.location): string {
  const candidates: Array<string | null | undefined> = [];
  const params = new URLSearchParams(location.search);
  for (const key of runtimeQueryKeys) candidates.push(params.get(key));
  candidates.push(import.meta.env.VITE_AFS_RUNTIME_BASE_URL);

  for (const candidate of candidates) {
    const safe = normalizeRuntimeBaseUrl(candidate, location.origin);
    if (safe) return safe;
  }
  return location.origin;
}

export function parseStudioEnvelope(value: unknown): StudioSurfaceEnvelope {
  if (!isRecord(value)) throw new Error("制作服务返回了无法识别的数据。");
  if (value.schema_version !== "afs.studio_bff.v0.2") {
    throw new Error("制作服务版本与当前界面不兼容。");
  }
  if (!isRecord(value.project) || typeof value.project_id !== "string") {
    throw new Error("制作服务缺少项目摘要。");
  }
  if (!Array.isArray(value.entities) || !Array.isArray(value.allowed_actions)) {
    throw new Error("制作服务缺少工作面对象。");
  }
  return value as unknown as StudioSurfaceEnvelope;
}

function parseReworkPreviewReceipt(value: unknown): StudioReworkPreviewReceipt {
  if (!isRecord(value) || value.schema_version !== "afs.studio_rework_preview.v0.1") {
    throw new Error("局部返工预览回执无法识别。");
  }
  if (value.status !== "preview" || typeof value.preview_id !== "string") {
    throw new Error("局部返工预览回执缺少确认依据。");
  }
  return value as unknown as StudioReworkPreviewReceipt;
}

function parseReworkConfirmReceipt(value: unknown): StudioReworkConfirmReceipt {
  if (!isRecord(value) || value.schema_version !== "afs.studio_command_receipt.v0.1") {
    throw new Error("局部返工确认回执无法识别。");
  }
  if (value.status !== "confirmed" || value.dispatch_state !== "planned_not_dispatched") {
    throw new Error("局部返工确认没有返回计划任务回执。");
  }
  return value as unknown as StudioReworkConfirmReceipt;
}

async function postStudioCommand({
  projectId,
  path,
  body,
  signal
}: {
  projectId: string;
  path: "preview" | "confirm";
  body: Record<string, unknown>;
  signal?: AbortSignal;
}): Promise<unknown> {
  const encodedProjectId = encodeURIComponent(projectId);
  const headers: HeadersInit = {
    Accept: "application/json",
    "Content-Type": "application/json"
  };
  const token = readAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(
      `${resolveRuntimeBaseUrl()}/api/v1/projects/${encodedProjectId}/studio/commands/rework/${path}`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal
      }
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw requestError("error", 0, "未能连接制作服务，页面没有派发任何任务。");
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw requestError("forbidden", response.status, "你没有执行这个项目操作的权限。");
    }
    if (response.status === 404) {
      throw requestError("empty", response.status, "没有找到这个项目或命令入口。");
    }
    if (response.status === 409) {
      throw requestError("stale", response.status, "版本已变化，请刷新后重新预览。");
    }
    throw requestError("error", response.status, "局部返工命令失败，没有派发制作任务。");
  }
  return response.json();
}

function normalizeRuntimeBaseUrl(
  value: string | null | undefined,
  currentOrigin: string
): string {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw, currentOrigin);
    const current = new URL(currentOrigin);
    const loopback = ["127.0.0.1", "localhost", "::1", "[::1]"].includes(
      url.hostname
    );
    if (!["http:", "https:"].includes(url.protocol)) return "";
    if (url.origin !== current.origin && !loopback) return "";
    url.pathname = url.pathname.replace(/\/+$/, "");
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return "";
  }
}

function readAuthToken(): string {
  try {
    return String(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) ?? "").trim();
  } catch {
    return "";
  }
}

function requestError(
  kind: StudioRequestError["kind"],
  status: number,
  message: string
): StudioRequestError {
  return { kind, status, message };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isStudioRequestError(value: unknown): value is StudioRequestError {
  return (
    isRecord(value) &&
    typeof value.kind === "string" &&
    typeof value.status === "number" &&
    typeof value.message === "string"
  );
}
