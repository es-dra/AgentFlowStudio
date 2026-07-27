export function projectIdentityFailure(error) {
  const status = Number(error?.status || 0);
  const code = String(error?.errorCode || "").trim();
  if (status === 401 || code === "authentication_required") {
    return failure(
      "authentication_required",
      "登录状态已失效。项目内容已清空，请重新登录后再试。",
      false,
    );
  }
  if (isProjectAccessDeniedError(error)) {
    return failure(
      "project_access_denied",
      "当前账号无权访问此项目。没有加载其他项目，也未发送任何修改请求。",
      false,
    );
  }
  if (status === 404 || code === "project_not_found") {
    return failure(
      "project_not_found",
      "项目不存在或已被移除。没有加载其他项目，也未发送任何修改请求。",
      false,
    );
  }
  if (code === "project_identity_mismatch") {
    return failure(
      "project_identity_mismatch",
      "当前项目尚未正确载入。可以重新加载一次当前项目；不会切换到其他项目。",
      true,
    );
  }
  if (status === 0 || code === "network_connection_interrupted") {
    return failure(
      "network_unavailable",
      "暂时无法验证此项目，且没有可信的同项目缓存。可以重新加载一次当前项目。",
      true,
    );
  }
  return failure(
    "project_load_failed",
    "暂时无法读取此项目。可以重新加载一次当前项目。",
    true,
  );
}

export function terminalProjectLoadMessage(reason) {
  if (reason === "project_access_denied") {
    return "当前账号无权访问此项目。请选择一个可访问的项目。";
  }
  if (reason === "project_not_found") {
    return "项目不存在或已被移除。请选择其他项目继续。";
  }
  return "重新加载后仍无法验证此项目。为保护项目内容，已停止继续重试；请选择其他项目或稍后再打开此链接。";
}

function failure(reason, message, retryable) {
  return { reason, message, retryable };
}

function isProjectAccessDeniedError(error) {
  if (!error) return false;
  const code = String(
    error.errorCode
      || error.payload?.error
      || error.payload?.detail?.error
      || "",
  ).trim();
  if (code === "project_access_denied") return true;
  const status = Number(error.status || 0);
  const message = error instanceof Error ? error.message : String(error || "");
  return status === 403
    && /project[_ ]access[_ ]denied|没有访问该项目的权限/i.test(message);
}
