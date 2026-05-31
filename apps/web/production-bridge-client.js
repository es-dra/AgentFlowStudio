export const BRIDGE_BASE_URL = "http://127.0.0.1:8787";

export async function bridgeGet(path) {
  const response = await fetch(`${BRIDGE_BASE_URL}${path}`);
  return readBridgeResponse(response);
}

export async function bridgePost(path, payload) {
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
