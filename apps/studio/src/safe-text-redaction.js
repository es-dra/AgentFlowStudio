const RAW_MARKER_RE = /\b(?:raw[_ -]?provider[_ -]?response|provider[_ -]?raw[_ -]?response|data[_ -]?base64|raw[_ -]?media|media[_ -]?bytes|image[_ -]?bytes|video[_ -]?bytes|audio[_ -]?bytes)\b/gi;
const DATA_URI_RE = /\bdata:[^\s"'<>]+/gi;
const BEARER_RE = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const SECRET_LABEL_RE = /\b(?:token|access[_-]?token|secret|api[_-]?key|signed[_-]?url|cookie|session|authorization|auth)\s*[:=]\s*['"]?[^'",;\s]+/gi;
const WINDOWS_PATH_RE = /\b[A-Za-z]:\\[^\s"'<>]+/g;
const COMPACT_WINDOWS_PATH_RE = /\b[A-Za-z]:[^\s"'<>]+/g;
const POSIX_PRIVATE_PATH_RE = /\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g;
const URL_RE = /https?:\/\/[^\s"'<>]+/gi;
const MEDIA_SIGNATURE_RE = /\b(?:iVBORw0KGgo|\/9j\/|R0lGOD|UklGR|AAAAGGZ0eXB|AAAAFGZ0eXB|JVBERi0|SUQz|T2dnUw)[A-Za-z0-9+/=]{8,}\b/gi;
const LONG_BASE64_RE = /\b[A-Za-z0-9+/]{96,}={0,2}\b/g;

export function redactUnsafeText(value, limit = 160) {
  return String(value || "")
    .replace(DATA_URI_RE, "<media-bytes-redacted>")
    .replace(MEDIA_SIGNATURE_RE, "<media-bytes-redacted>")
    .replace(LONG_BASE64_RE, "<media-bytes-redacted>")
    .replace(RAW_MARKER_RE, "<redacted>")
    .replace(BEARER_RE, "Bearer <redacted>")
    .replace(SECRET_LABEL_RE, "<redacted>")
    .replace(WINDOWS_PATH_RE, "<local-path-redacted>")
    .replace(COMPACT_WINDOWS_PATH_RE, "<local-path-redacted>")
    .replace(POSIX_PRIVATE_PATH_RE, "<local-path-redacted>")
    .replace(URL_RE, "<url-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

export function containsUnsafeText(value) {
  const text = String(value || "");
  RAW_MARKER_RE.lastIndex = 0;
  DATA_URI_RE.lastIndex = 0;
  BEARER_RE.lastIndex = 0;
  SECRET_LABEL_RE.lastIndex = 0;
  WINDOWS_PATH_RE.lastIndex = 0;
  COMPACT_WINDOWS_PATH_RE.lastIndex = 0;
  POSIX_PRIVATE_PATH_RE.lastIndex = 0;
  URL_RE.lastIndex = 0;
  MEDIA_SIGNATURE_RE.lastIndex = 0;
  LONG_BASE64_RE.lastIndex = 0;
  return RAW_MARKER_RE.test(text)
    || DATA_URI_RE.test(text)
    || BEARER_RE.test(text)
    || SECRET_LABEL_RE.test(text)
    || WINDOWS_PATH_RE.test(text)
    || COMPACT_WINDOWS_PATH_RE.test(text)
    || POSIX_PRIVATE_PATH_RE.test(text)
    || URL_RE.test(text)
    || MEDIA_SIGNATURE_RE.test(text)
    || LONG_BASE64_RE.test(text);
}
