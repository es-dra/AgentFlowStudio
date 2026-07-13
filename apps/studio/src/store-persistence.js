import { hasStudioContent, initialState, normalizeSnapshot, replaceSerializable, snapshotStudioState } from "./store-state.js";

const STORAGE_KEY_PREFIX = "afs_studio_canvas_v2:";
const STORAGE_KEY = "afs_studio_canvas_v2";
const LEGACY_STORAGE_KEY = "afs_studio_canvas_v1";
const LEGACY_MIGRATION_MARKER = "afs_studio_canvas_v2:legacy_migrated";
const IDENTITY_MARKER_KEY = "afs_studio_identity_marker";

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
}

export function persist(state) {
  try {
    localStorage.setItem(storageKey(state.meta.projectId), JSON.stringify(snapshotStudioState(state)));
  } catch {
    /* Local persistence is best-effort; the in-memory canvas remains usable. */
  }
}

export function loadPersisted(projectId = "studio-local-001") {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    if (!raw) return null;
    const snap = normalizeSnapshot(JSON.parse(raw));
    if (!hasStudioContent(snap)) return null;
    const base = initialState(projectId);
    replaceSerializable(base, snap);
    base.meta.projectId = projectId;
    return base;
  } catch {
    return null;
  }
}

export function migrateLegacyCanvasStorage(projectId = "studio-local-001") {
  try {
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

function storageKey(projectId) {
  return `${STORAGE_KEY_PREFIX}${projectId || "studio-local-001"}`;
}
