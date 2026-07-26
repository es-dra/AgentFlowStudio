import { authToken, runtimeBaseUrl, runtimeMediaUrl } from "./runtime-client.js";

const mediaObjectUrls = new WeakMap();
const mediaBlobCache = new Map();
let mediaAuthToken = null;
let mediaAuthGeneration = 0;

export async function setRuntimeMediaSource(element, value) {
  if (!element) return "";
  const raw = String(value || "").trim();
  const url = runtimeMediaUrl(value);
  const authorized = shouldFetchAuthorizedMedia(value, url);
  const token = authorized ? authToken() : "";
  if (authorized) syncAuthorizedMediaSession(token);
  const current = mediaObjectUrls.get(element);
  if (
    element.dataset.afsMediaRaw === raw
    && element.dataset.afsMediaResolved === url
    && currentMediaUrl(element)
    && (!authorized || current?.authGeneration === mediaAuthGeneration)
  ) {
    return currentMediaUrl(element);
  }
  revokeRuntimeMediaSource(element, { keepCached: true });
  if (!url) {
    assignMediaUrl(element, "");
    return "";
  }
  if (!authorized) {
    assignMediaUrl(element, url);
    return url;
  }
  if (!token) {
    failAuthorizedMediaLoad(element);
    return "";
  }
  const authGeneration = mediaAuthGeneration;
  const cached = cachedAuthorizedMediaUrl(url);
  if (cached) {
    assignCachedMediaUrl(element, raw, url, cached, authGeneration);
    return cached;
  }
  const requestId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  element.dataset.afsMediaRaw = raw;
  element.dataset.afsMediaResolved = url;
  element.dataset.afsMediaRequest = requestId;
  try {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error(`media ${response.status}`);
    const objectUrl = URL.createObjectURL(await response.blob());
    if (
      element.dataset.afsMediaRequest !== requestId
      || authToken() !== token
      || mediaAuthGeneration !== authGeneration
    ) {
      URL.revokeObjectURL(objectUrl);
      if (element.dataset.afsMediaRequest === requestId) failAuthorizedMediaLoad(element);
      return "";
    }
    mediaBlobCache.set(url, objectUrl);
    mediaObjectUrls.set(element, { url: objectUrl, cached: true, authGeneration });
    assignMediaUrl(element, objectUrl);
    return objectUrl;
  } catch {
    if (element.dataset.afsMediaRequest === requestId) failAuthorizedMediaLoad(element);
    return "";
  }
}

export function revokeRuntimeMediaSource(element, options = {}) {
  const existing = element ? mediaObjectUrls.get(element) : "";
  const url = typeof existing === "string" ? existing : existing?.url;
  if (url && !existing?.cached && !options.keepCached) URL.revokeObjectURL(url);
  if (element) {
    mediaObjectUrls.delete(element);
    delete element.dataset.afsMediaRequest;
    delete element.dataset.afsMediaRaw;
    delete element.dataset.afsMediaResolved;
  }
}

function assignMediaUrl(element, url) {
  if (element.tagName === "A") element.href = url;
  else element.src = url;
}

function failAuthorizedMediaLoad(element) {
  if (element.tagName === "A") {
    if (typeof element.removeAttribute === "function") element.removeAttribute("href");
    else element.href = "";
  }
  else {
    if (typeof element.removeAttribute === "function") element.removeAttribute("src");
    else element.src = "";
    if (typeof element.dispatchEvent === "function") {
      queueMicrotask(() => element.dispatchEvent(new Event("error")));
    }
  }
}

function assignCachedMediaUrl(element, raw, resolvedUrl, objectUrl, authGeneration) {
  element.dataset.afsMediaRaw = raw;
  element.dataset.afsMediaResolved = resolvedUrl;
  mediaObjectUrls.set(element, { url: objectUrl, cached: true, authGeneration });
  assignMediaUrl(element, objectUrl);
}

function cachedAuthorizedMediaUrl(url) {
  return mediaBlobCache.get(url) || "";
}

function syncAuthorizedMediaSession(token) {
  if (mediaAuthToken === token) return;
  for (const objectUrl of mediaBlobCache.values()) URL.revokeObjectURL(objectUrl);
  mediaBlobCache.clear();
  mediaAuthToken = token;
  mediaAuthGeneration += 1;
}

function currentMediaUrl(element) {
  return element.tagName === "A" ? element.href : element.src;
}

function shouldFetchAuthorizedMedia(value, resolvedUrl) {
  const raw = String(value || "").trim();
  if (!raw || raw.startsWith("blob:") || raw.startsWith("data:")) return false;
  try {
    const url = new URL(resolvedUrl);
    const runtimeOrigin = new URL(runtimeBaseUrl()).origin;
    if (url.origin !== runtimeOrigin) return false;
    return url.pathname.startsWith("/projects/");
  } catch {
    return raw.startsWith("/projects/");
  }
}
