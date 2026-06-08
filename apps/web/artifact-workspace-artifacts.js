import { ARTIFACT_ALIASES, ARTIFACT_CLASSES, VIDEO_EXTENSIONS, sourceRoleFor } from "./artifact-contracts.js?v=m4-memory-canvas-tools";
import { asText } from "./artifact-values.js?v=m4-memory-canvas-tools";

const AGENTFLOW_KIND_ARTIFACTS = new Set(Object.keys(ARTIFACT_ALIASES).filter((type) => type.startsWith("agentflow_")));

export async function parseFiles(files) {
  const artifacts = [];
  for (const file of files) {
    const extension = file.name.toLowerCase().split(".").pop();
    if (VIDEO_EXTENSIONS.has(extension)) {
      artifacts.push(buildArtifact({ file, rawText: "", payload: null, parseStatus: "valid", localFile: file }));
      continue;
    }
    const text = await file.text();
    if (extension === "md") {
      artifacts.push(buildArtifact({ file, rawText: text, payload: null, parseStatus: "valid" }));
      continue;
    }
    if (extension !== "json") {
      artifacts.push(
        buildArtifact({
          file,
          rawText: text,
          payload: null,
          parseStatus: "unsupported",
          message: "Unsupported file type.",
        }),
      );
      continue;
    }
    try {
      const payload = JSON.parse(text);
      const isObject = payload !== null && !Array.isArray(payload) && typeof payload === "object";
      artifacts.push(
        buildArtifact({
          file,
          rawText: text,
          payload: isObject ? payload : null,
          parseStatus: isObject ? "valid" : "invalid",
          message: isObject ? "" : "JSON payload is not an object.",
        }),
      );
    } catch (error) {
      artifacts.push(
        buildArtifact({
          file,
          rawText: text,
          payload: null,
          parseStatus: "invalid",
          message: error.message,
        }),
      );
    }
  }
  return artifacts;
}

function buildArtifact({ file, rawText, payload, parseStatus, message = "", localFile = null }) {
  const type = detectArtifactType(file.name, payload);
  const schemaInfo = schemaInfoFor(type, payload, parseStatus);
  const artifactClass = artifactClassFor(type, parseStatus);
  return {
    fileName: file.name,
    artifactType: type,
    artifactClass,
    sourceRole: sourceRoleFor(type, file.name),
    schemaVersion: schemaInfo.version,
    schemaStatus: schemaInfo.status,
    schemaWarnings: schemaInfo.warnings,
    parseStatus,
    known: artifactClass === ARTIFACT_CLASSES.KNOWN_CONTRACT,
    participatesInSummary: artifactClass === ARTIFACT_CLASSES.KNOWN_CONTRACT,
    payload,
    rawText,
    localFile,
    mediaType: localFile?.type || "",
    message,
  };
}

function detectArtifactType(fileName, payload) {
  const normalizedName = fileName.toLowerCase();
  const extension = normalizedName.split(".").pop();
  if (VIDEO_EXTENSIONS.has(extension)) return "local_video";
  if (!["json", "md"].includes(extension)) return "unsupported_file";
  for (const [type, aliases] of Object.entries(ARTIFACT_ALIASES)) {
    if (aliases.includes(normalizedName)) return type;
  }
  if (payload && payload.artifact_index && payload.workflow) return "run_manifest";
  if (payload && AGENTFLOW_KIND_ARTIFACTS.has(payload.kind)) return payload.kind;
  if (payload && typeof payload.artifact_type === "string" && payload.artifact_type.startsWith("agentflow_")) return payload.artifact_type;
  if (payload && payload.assets && payload.package_id) return "package_manifest";
  if (payload && payload.sections && payload.summary) return "review_report";
  if (payload && payload.runs && payload.summary) return "delivery_readiness";
  if (payload && payload.checks && payload.status) return "quality_report";
  return normalizedName.endsWith(".md") ? "unsupported_file" : "unknown";
}

function artifactClassFor(type, parseStatus) {
  if (parseStatus === "invalid") return ARTIFACT_CLASSES.INVALID;
  if (type === "local_video") return ARTIFACT_CLASSES.LOCAL_MEDIA;
  if (type === "unsupported_file" || parseStatus === "unsupported") return ARTIFACT_CLASSES.UNSUPPORTED_FILE;
  if (type === "unknown") return ARTIFACT_CLASSES.UNKNOWN_JSON;
  return ARTIFACT_CLASSES.KNOWN_CONTRACT;
}

function schemaInfoFor(type, payload, parseStatus) {
  if (["markdown_report", "unsupported_file", "local_video"].includes(type)) {
    return { version: "n/a", status: "n/a", warnings: [] };
  }
  if (parseStatus !== "valid") {
    return { version: "unknown", status: "unknown", warnings: [] };
  }
  if (!payload || type === "unknown") {
    return { version: "unknown", status: "unknown", warnings: [] };
  }
  const version = asText(payload.schema_version, "");
  if (!version) {
    return {
      version: "unknown",
      status: "warning",
      warnings: ["schema_version missing; warning only, artifact remains readable."],
    };
  }
  return { version, status: "present", warnings: [] };
}
