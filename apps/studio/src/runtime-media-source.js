import { authToken, runtimeBaseUrl, runtimeMediaUrl } from "./runtime-client.js";

const mediaObjectUrls = new WeakMap();

export async function setRuntimeMediaSource(element, value) {
  if (!element) return "";
  const url = runtimeMediaUrl(value);
  revokeRuntimeMediaSource(element);
  if (!url) {
    assignMediaUrl(element, "");
    return "";
  }
  if (!shouldFetchAuthorizedMedia(value, url)) {
    assignMediaUrl(element, url);
    return url;
  }
  const token = authToken();
  if (!token) {
    assignMediaUrl(element, url);
    return url;
  }
  const requestId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  element.dataset.afsMediaRequest = requestId;
  try {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error(`media ${response.status}`);
    const objectUrl = URL.createObjectURL(await response.blob());
    if (element.dataset.afsMediaRequest !== requestId) {
      URL.revokeObjectURL(objectUrl);
      return "";
    }
    mediaObjectUrls.set(element, objectUrl);
    assignMediaUrl(element, objectUrl);
    return objectUrl;
  } catch {
    if (element.dataset.afsMediaRequest === requestId) assignMediaUrl(element, url);
    return url;
  }
}

export function revokeRuntimeMediaSource(element) {
  const existing = element ? mediaObjectUrls.get(element) : "";
  if (existing) URL.revokeObjectURL(existing);
  if (element) {
    mediaObjectUrls.delete(element);
    delete element.dataset.afsMediaRequest;
  }
}

function assignMediaUrl(element, url) {
  if (element.tagName === "A") element.href = url;
  else element.src = url;
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
