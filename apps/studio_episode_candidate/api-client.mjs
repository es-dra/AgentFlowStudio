export const EPISODE_AGGREGATE_ROUTE = "/projects/{project_id}/episode-production-aggregate";

export class EpisodeWorkspaceRequestError extends Error {
  constructor(kind, message, status = null) {
    super(message);
    this.name = "EpisodeWorkspaceRequestError";
    this.kind = kind;
    this.status = status;
  }
}

function routeFor(template, projectId) {
  if (!projectId || typeof projectId !== "string") {
    throw new EpisodeWorkspaceRequestError("missing_project", "未指定要打开的项目。");
  }
  return template.replace("{project_id}", encodeURIComponent(projectId));
}

async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new EpisodeWorkspaceRequestError("invalid_response", "项目数据暂时无法读取。", response.status);
  }
  return response.json();
}

function classifyFailure(response) {
  if (response.status === 401 || response.status === 403) {
    return new EpisodeWorkspaceRequestError("auth", "登录状态已失效，请重新登录后继续。", response.status);
  }
  if (response.status === 404) {
    return new EpisodeWorkspaceRequestError("not_found", "找不到这个项目，或你已无权访问。", response.status);
  }
  if (response.status === 409 || response.status === 412) {
    return new EpisodeWorkspaceRequestError("stale", "项目已在其他位置更新，请刷新后再继续。", response.status);
  }
  return new EpisodeWorkspaceRequestError("server", "项目暂时无法打开，请稍后重试。", response.status);
}

export async function loadEpisodeAggregate(projectId, { signal } = {}) {
  let response;
  try {
    response = await fetch(routeFor(EPISODE_AGGREGATE_ROUTE, projectId), {
      method: "GET",
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new EpisodeWorkspaceRequestError("network", "网络连接中断，你的工作没有被本地改写。");
  }
  if (!response.ok) throw classifyFailure(response);
  return readResponse(response);
}
