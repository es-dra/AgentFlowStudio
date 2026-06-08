export function fact(label, value) {
  return { label, value: String(value) };
}

export function yesNo(value) {
  return value === true ? "true" : "false";
}

export function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

export function usedContextRefCount(outputArtifacts) {
  const refs = arrayValue(outputArtifacts).flatMap((item) => arrayValue(item?.used_context_refs).map(String));
  return new Set(refs).size;
}
