import {
  apiSurfaceFor,
  type AppSurface,
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
  if (value.schema_version !== "afs.studio_bff.v0.1") {
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
