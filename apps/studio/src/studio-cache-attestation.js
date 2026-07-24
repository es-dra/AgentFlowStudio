import { authToken } from "./runtime-client.js";

const SCHEMA_VERSION = "afs.studio_cache_identity.v0.1";

export async function verifyStudioCacheAttestation(attestation, state, {
  projectId,
  accountId,
} = {}) {
  const proof = safeHex(attestation?.proof);
  const stateSha256 = safeHex(attestation?.state_sha256);
  const stateVersion = String(attestation?.state_version || "");
  if (
    attestation?.schema_version !== SCHEMA_VERSION
    || String(attestation?.project_id || "") !== String(projectId || "")
    || String(attestation?.account_id || "") !== String(accountId || "")
    || !proof
    || !stateSha256
  ) return false;
  const token = authToken();
  if (!token || !globalThis.crypto?.subtle) return false;
  const actualStateSha256 = await sha256Hex(canonicalJson(state));
  if (actualStateSha256 !== stateSha256) return false;
  const message = [
    SCHEMA_VERSION,
    String(accountId || ""),
    String(projectId || ""),
    stateVersion,
    stateSha256,
  ].join("\u001f");
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(token),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return constantTimeEqual(hex(signature), proof);
}

export function canonicalStudioCacheJson(value) {
  return canonicalJson(value);
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return hex(digest);
}

function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const entries = Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
  return `{${entries.join(",")}}`;
}

function hex(value) {
  return [...new Uint8Array(value)].map((item) => item.toString(16).padStart(2, "0")).join("");
}

function safeHex(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(normalized) ? normalized : "";
}

function constantTimeEqual(left, right) {
  if (left.length !== right.length) return false;
  let mismatch = 0;
  for (let index = 0; index < left.length; index += 1) {
    mismatch |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return mismatch === 0;
}
