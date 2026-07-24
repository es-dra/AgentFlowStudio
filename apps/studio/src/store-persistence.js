import { hasStudioContent, initialState, normalizeSnapshot, replaceSerializable, snapshotStudioState } from "./store-state.js";
import { verifyStudioCacheAttestation } from "./studio-cache-attestation.js";

const STORAGE_KEY_PREFIX = "afs_studio_canvas_v2:";
const STORAGE_KEY = "afs_studio_canvas_v2";
const LEGACY_STORAGE_KEY = "afs_studio_canvas_v1";
const LEGACY_MIGRATION_MARKER = "afs_studio_canvas_v2:legacy_migrated";
const IDENTITY_MARKER_KEY = "afs_studio_identity_marker";
const CACHE_SCHEMA_VERSION = "afs_studio_cache.v3";
const TRUSTED_CACHE_SCHEMA_VERSION = "afs_studio_trusted_cache.v1";
const TRUSTED_CACHE_KEY_PREFIX = "afs_studio_trusted_cache_v1:";
let activeIdentity = "";

export function prepareIdentityStorage(userId) {
  const nextIdentity = String(userId || "").trim();
  if (!nextIdentity) {
    clearIdentityScopedStudioState();
    return { changed: true, identity: "" };
  }
  let previous = "";
  try {
    previous = String(localStorage.getItem(IDENTITY_MARKER_KEY) || "").trim();
  } catch {
    return { changed: true, identity: nextIdentity };
  }
  if (previous !== nextIdentity) clearIdentityScopedStudioState();
  try {
    localStorage.setItem(IDENTITY_MARKER_KEY, nextIdentity);
  } catch {
    // Browser storage may be blocked; runtime ownership remains authoritative.
  }
  activeIdentity = nextIdentity;
  return { changed: previous !== nextIdentity, identity: nextIdentity };
}

export function clearIdentityScopedStudioState() {
  try {
    const keys = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key && key.startsWith("afs_studio_")) keys.push(key);
    }
    for (const key of keys) localStorage.removeItem(key);
  } catch {
    // Runtime ownership still prevents foreign reads when storage is unavailable.
  }
  activeIdentity = "";
}

export function persist(state) {
  try {
    const key = storageKey(state.meta.projectId);
    if (!key) return;
    localStorage.setItem(key, JSON.stringify({
      schema_version: CACHE_SCHEMA_VERSION,
      identity: {
        account_id: activeIdentity || storedIdentity(),
        project_id: String(state.meta.projectId || "").trim(),
      },
      state: snapshotStudioState(state),
    }));
  } catch {
    /* Local persistence is best-effort; the in-memory canvas remains usable. */
  }
}

export function loadPersisted(projectId = "", { accountId = "", requireTrusted = false } = {}) {
  try {
    const key = storageKey(projectId);
    if (!key) return null;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const expectedProject = String(projectId || "").trim();
    const expectedAccount = String(accountId || activeIdentity || storedIdentity()).trim();
    const envelope = parsed?.schema_version === CACHE_SCHEMA_VERSION ? parsed : null;
    if (requireTrusted && !trustedEnvelope(envelope, expectedProject, expectedAccount)) return null;
    const snap = normalizeSnapshot(envelope?.state || parsed);
    if (!hasStudioContent(snap)) return null;
    const base = initialState(projectId);
    replaceSerializable(base, snap);
    base.meta.projectId = projectId;
    return base;
  } catch {
    return null;
  }
}

export function migrateLegacyCanvasStorage(projectId = "") {
  try {
    if (!storageKey(projectId)) return;
    if (localStorage.getItem(LEGACY_MIGRATION_MARKER)) return;
    const targetKey = storageKey(projectId);
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (raw && !localStorage.getItem(targetKey)) {
      const snap = normalizeSnapshot(JSON.parse(raw));
      if (hasStudioContent(snap)) {
        snap.meta.projectId = projectId;
        localStorage.setItem(targetKey, JSON.stringify(snap));
      }
    }
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    localStorage.setItem(LEGACY_MIGRATION_MARKER, new Date().toISOString());
  } catch {
    /* Legacy storage cleanup is best-effort; project-scoped state remains authoritative. */
  }
}

export async function trustedProjectCache(projectId = "", accountId = "") {
  try {
    const raw = localStorage.getItem(`${TRUSTED_CACHE_KEY_PREFIX}${projectId}`);
    if (!raw) return null;
    const envelope = JSON.parse(raw);
    if (envelope?.schema_version !== TRUSTED_CACHE_SCHEMA_VERSION) return null;
    if (!trustedEnvelope(envelope, projectId, accountId)) return null;
    if (!await verifyStudioCacheAttestation(envelope.cache_identity, envelope.state, { projectId, accountId })) return null;
    const snap = normalizeSnapshot(envelope.state);
    if (!hasStudioContent(snap)) return null;
    const base = initialState(projectId);
    replaceSerializable(base, snap);
    base.meta.projectId = projectId;
    return base;
  } catch {
    return null;
  }
}

export async function persistTrustedProjectCache(cacheState, cacheIdentity, { accountId = "" } = {}) {
  try {
    const projectId = String(cacheIdentity?.project_id || "").trim();
    if (!projectId || !await verifyStudioCacheAttestation(cacheIdentity, cacheState, { projectId, accountId })) return false;
    localStorage.setItem(`${TRUSTED_CACHE_KEY_PREFIX}${projectId}`, JSON.stringify({
      schema_version: TRUSTED_CACHE_SCHEMA_VERSION,
      identity: { account_id: accountId, project_id: projectId },
      cache_identity: cacheIdentity,
      state: cacheState,
    }));
    return true;
  } catch {
    return false;
  }
}

function trustedEnvelope(envelope, projectId, accountId) {
  if (!envelope || !projectId || !accountId) return false;
  return String(envelope.identity?.project_id || "").trim() === projectId
    && String(envelope.identity?.account_id || "").trim() === accountId;
}

function storedIdentity() {
  try {
    return String(localStorage.getItem(IDENTITY_MARKER_KEY) || "").trim();
  } catch {
    return "";
  }
}

function storageKey(projectId) {
  const safe = String(projectId || "").trim();
  return safe ? `${STORAGE_KEY_PREFIX}${safe}` : "";
}
