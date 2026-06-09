let timer = null;
let activeKey = "";

export function configureJobPolling(state, refresh) {
  const polling = state.workbench?.job_center?.polling;
  const interval = Math.max(2000, Number(polling?.suggested_interval_ms || 0));
  if (!polling?.enabled || !state.projectId) {
    clearPolling();
    return;
  }
  const key = `${state.baseUrl}|${state.projectId}|${interval}`;
  if (timer && activeKey === key) return;
  clearPolling();
  activeKey = key;
  timer = setInterval(refresh, interval);
}

export function clearPolling() {
  if (timer) clearInterval(timer);
  timer = null;
  activeKey = "";
}
