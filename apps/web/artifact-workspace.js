import { ARTIFACT_ALIASES, ARTIFACT_CLASSES, RECOMMENDED_ARTIFACTS, VIDEO_EXTENSIONS, sourceRoleFor } from "./artifact-contracts.js?v=m4-memory-canvas-tools";
import { normalizeAssetLedger, normalizeEvidenceMap, normalizeRiskLedger } from "./artifact-ledgers.js?v=m4-memory-canvas-tools";
import { asList, asObject, asText, collectChecks, normalizeStatus } from "./artifact-values.js?v=m4-memory-canvas-tools";

export { asText, normalizeStatus } from "./artifact-values.js?v=m4-memory-canvas-tools";

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

export function normalizeWorkspace(artifacts) {
  const summaryArtifacts = artifacts.filter((artifact) => artifact.participatesInSummary);
  const byType = (type) => summaryArtifacts.find((artifact) => artifact.artifactType === type);
  const reports = summaryArtifacts.filter((artifact) => artifact.artifactType === "markdown_report");
  const warnings = [];
  const errors = artifacts
    .filter((artifact) => artifact.artifactClass === ARTIFACT_CLASSES.INVALID)
    .map((artifact) => `${artifact.fileName}: ${artifact.message || "invalid artifact"}`);

  if (summaryArtifacts.length > 0) {
    for (const type of RECOMMENDED_ARTIFACTS) {
      if (!summaryArtifacts.some((artifact) => artifact.artifactType === type)) {
        warnings.push(`Missing recommended artifact: ${type}`);
      }
    }
  }

  for (const artifact of artifacts) {
    for (const schemaWarning of artifact.schemaWarnings) {
      warnings.push(`${artifact.fileName}: ${schemaWarning}`);
    }
    if (artifact.artifactClass === ARTIFACT_CLASSES.UNKNOWN_JSON) {
      warnings.push(`${artifact.fileName}: parsed but not included in summary (unknown_json).`);
    }
    if (artifact.artifactClass === ARTIFACT_CLASSES.UNSUPPORTED_FILE) {
      warnings.push(`${artifact.fileName}: unsupported_file; not included in summary.`);
    }
  }

  const run = normalizeRun(byType("run_manifest"));
  const packageSummary = normalizePackage(byType("package_manifest"));
  const memoryBundle = summaryArtifacts.filter((artifact) => artifact.artifactType.startsWith("agentflow_"));
  const memoryPackage = byType("agentflow_memory_video_pipeline_package") || null;
  const loulanPackage = byType("agentflow_loulan_memory_package") || null;
  const loulanApiWorkbenchPlan = byType("agentflow_loulan_api_workbench_plan") || null;
  const loulanHumanReviewPack = byType("agentflow_loulan_human_review_pack") || null;
  const loulanDecisionTemplate = byType("agentflow_loulan_promotion_decisions") || null;
  const loulanDecisionReviewPack = byType("agentflow_loulan_decision_review_pack") || null;
  const loulanDecisionWorksheet = byType("agentflow_loulan_decision_worksheet") || null;
  const loulanContextBundleProjection = byType("agentflow_loulan_context_bundle_projection") || null;
  const workspaceParts = {
    warnings,
    errors,
  };

  return {
    artifacts,
    run,
    package: packageSummary,
    memoryPackage,
    loulanPackage,
    loulanApiWorkbenchPlan,
    loulanHumanReviewPack,
    loulanDecisionTemplate,
    loulanDecisionReviewPack,
    loulanDecisionWorksheet,
    loulanContextBundleProjection,
    memoryBundle,
    quality: normalizeQuality(byType("quality_report")),
    review: normalizeReview(byType("review_report")),
    readiness: normalizeReadiness(byType("delivery_readiness")),
    reports,
    evidenceMap: normalizeEvidenceMap(summaryArtifacts, run),
    riskLedger: normalizeRiskLedger(summaryArtifacts, workspaceParts),
    assetLedger: normalizeAssetLedger(summaryArtifacts, packageSummary),
    videos: artifacts.filter((artifact) => artifact.artifactClass === ARTIFACT_CLASSES.LOCAL_MEDIA),
    errors,
    warnings,
  };
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

function normalizeRun(artifact) {
  const payload = asObject(artifact?.payload);
  if (!artifact?.payload) return null;
  const artifactIndex = asObject(payload.artifact_index);
  return {
    runId: asText(payload.run_id, "unknown"),
    workflow: asText(payload.workflow, "unknown"),
    mode: asText(payload.workflow_mode || payload.mode, "unknown"),
    status: normalizeStatus(payload.status),
    qualityProfile: asText(payload.quality_profile, "unknown"),
    artifacts: Object.entries(artifactIndex).map(([name, entry]) => ({
      name,
      path: asText(entry?.path, ""),
      required: Boolean(entry?.required),
      exists: entry?.exists === true,
    })),
  };
}

function normalizePackage(artifact) {
  const payload = asObject(artifact?.payload);
  if (!artifact?.payload) return null;
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  return {
    packageId: asText(payload.package_id, "unknown"),
    status: normalizeStatus(payload.status),
    manifestPath: asText(payload.manifest_path || artifact.fileName, artifact.fileName),
    assets: assets.map((asset) => ({
      role: asText(asset.role, "unknown"),
      path: asText(asset.path, ""),
      required: Boolean(asset.required),
      exists: asset.exists === true,
      sizeBytes: asset.size_bytes ?? null,
    })),
    errors: asList(payload.errors),
    warnings: asList(payload.warnings),
  };
}

function normalizeQuality(artifact) {
  const payload = asObject(artifact?.payload);
  if (!artifact?.payload) return null;
  return {
    status: normalizeStatus(payload.status),
    checks: collectChecks(payload),
    warnings: asList(payload.warnings),
    errors: asList(payload.errors),
  };
}

function normalizeReview(artifact) {
  const payload = asObject(artifact?.payload);
  if (!artifact?.payload) return null;
  const sections = Array.isArray(payload.sections) ? payload.sections : [];
  return {
    runId: asText(payload.run_id, "unknown"),
    status: normalizeStatus(payload.status),
    deliveryStatus: normalizeStatus(payload.delivery_status),
    qualityLevel: asText(payload.quality_level, "unknown"),
    summary: asObject(payload.summary),
    sections: sections.map((section) => ({
      name: asText(section.name, "unnamed_section"),
      status: normalizeStatus(section.status),
      checks: collectChecks(section),
    })),
    recommendations: asList(payload.recommendations),
  };
}

function normalizeReadiness(artifact) {
  const payload = asObject(artifact?.payload);
  if (!artifact?.payload) return null;
  const runs = Array.isArray(payload.runs) ? payload.runs : [];
  return {
    status: normalizeStatus(payload.status),
    summary: asObject(payload.summary),
    runs: runs.map((run) => ({
      runId: asText(run.run_id, "unknown"),
      mode: asText(run.mode, "unknown"),
      status: normalizeStatus(run.status),
      failures: asList(run.failures),
      warnings: asList(run.warnings),
    })),
  };
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
