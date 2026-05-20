const ARTIFACT_ALIASES = {
  run_manifest: ["run_manifest.json"],
  package_manifest: ["package_manifest.json", "finished_package_manifest.json"],
  quality_report: ["quality_report.json"],
  review_report: ["review_report.json"],
  delivery_readiness: ["delivery_readiness.json"],
  markdown_report: ["package_report.md", "delivery_readiness.md"],
};

const RECOMMENDED_ARTIFACTS = [
  "run_manifest",
  "package_manifest",
  "quality_report",
  "review_report",
  "markdown_report",
];

const ARTIFACT_CLASSES = {
  KNOWN_CONTRACT: "known_contract",
  UNKNOWN_JSON: "unknown_json",
  UNSUPPORTED_FILE: "unsupported_file",
  INVALID: "invalid",
};

export async function parseFiles(files) {
  const artifacts = [];
  for (const file of files) {
    const text = await file.text();
    const extension = file.name.toLowerCase().split(".").pop();
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

  for (const type of RECOMMENDED_ARTIFACTS) {
    if (!summaryArtifacts.some((artifact) => artifact.artifactType === type)) {
      warnings.push(`Missing recommended artifact: ${type}`);
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

  return {
    artifacts,
    run: normalizeRun(byType("run_manifest")),
    package: normalizePackage(byType("package_manifest")),
    quality: normalizeQuality(byType("quality_report")),
    review: normalizeReview(byType("review_report")),
    readiness: normalizeReadiness(byType("delivery_readiness")),
    reports,
    errors,
    warnings,
  };
}

export function normalizeStatus(value) {
  const status = asText(value, "unknown").toLowerCase();
  if (["pass", "passed", "success", "succeeded", "valid"].includes(status)) return "pass";
  if (["fail", "failed", "error", "invalid"].includes(status)) return "fail";
  if (["warning", "unsupported"].includes(status)) return "warning";
  if (status === "missing") return "missing";
  if (status === "optional") return "unknown";
  return status || "unknown";
}

export function asText(value, fallback) {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function buildArtifact({ file, rawText, payload, parseStatus, message = "" }) {
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
    message,
  };
}

function detectArtifactType(fileName, payload) {
  const normalizedName = fileName.toLowerCase();
  const extension = normalizedName.split(".").pop();
  if (!["json", "md"].includes(extension)) return "unsupported_file";
  for (const [type, aliases] of Object.entries(ARTIFACT_ALIASES)) {
    if (aliases.includes(normalizedName)) return type;
  }
  if (payload && payload.artifact_index && payload.workflow) return "run_manifest";
  if (payload && payload.assets && payload.package_id) return "package_manifest";
  if (payload && payload.sections && payload.summary) return "review_report";
  if (payload && payload.runs && payload.summary) return "delivery_readiness";
  if (payload && payload.checks && payload.status) return "quality_report";
  return normalizedName.endsWith(".md") ? "unsupported_file" : "unknown";
}

function artifactClassFor(type, parseStatus) {
  if (parseStatus === "invalid") return ARTIFACT_CLASSES.INVALID;
  if (type === "unsupported_file" || parseStatus === "unsupported") return ARTIFACT_CLASSES.UNSUPPORTED_FILE;
  if (type === "unknown") return ARTIFACT_CLASSES.UNKNOWN_JSON;
  return ARTIFACT_CLASSES.KNOWN_CONTRACT;
}

function normalizeRun(artifact) {
  const payload = artifact?.payload;
  if (!payload) return null;
  const artifactIndex = payload.artifact_index && typeof payload.artifact_index === "object" ? payload.artifact_index : {};
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
  const payload = artifact?.payload;
  if (!payload) return null;
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
  const payload = artifact?.payload;
  if (!payload) return null;
  return {
    status: normalizeStatus(payload.status),
    checks: collectChecks(payload),
    warnings: asList(payload.warnings),
    errors: asList(payload.errors),
  };
}

function normalizeReview(artifact) {
  const payload = artifact?.payload;
  if (!payload) return null;
  const sections = Array.isArray(payload.sections) ? payload.sections : [];
  return {
    runId: asText(payload.run_id, "unknown"),
    status: normalizeStatus(payload.status),
    deliveryStatus: normalizeStatus(payload.delivery_status),
    qualityLevel: asText(payload.quality_level, "unknown"),
    summary: payload.summary && typeof payload.summary === "object" ? payload.summary : {},
    sections: sections.map((section) => ({
      name: asText(section.name, "unnamed_section"),
      status: normalizeStatus(section.status),
      checks: collectChecks(section),
    })),
    recommendations: asList(payload.recommendations),
  };
}

function normalizeReadiness(artifact) {
  const payload = artifact?.payload;
  if (!payload) return null;
  const runs = Array.isArray(payload.runs) ? payload.runs : [];
  return {
    status: normalizeStatus(payload.status),
    summary: payload.summary && typeof payload.summary === "object" ? payload.summary : {},
    runs: runs.map((run) => ({
      runId: asText(run.run_id, "unknown"),
      mode: asText(run.mode, "unknown"),
      status: normalizeStatus(run.status),
      failures: asList(run.failures),
      warnings: asList(run.warnings),
    })),
  };
}

function collectChecks(payload) {
  const checks = Array.isArray(payload?.checks) ? payload.checks : [];
  return checks.filter((check) => check && typeof check === "object");
}

function sourceRoleFor(type, fileName) {
  if (type === "markdown_report") return fileName.toLowerCase() === "delivery_readiness.md" ? "delivery handoff" : "human package report";
  if (type === "quality_report") return "inspection trust artifact";
  if (type === "review_report") return "agent review artifact";
  if (type === "package_manifest") return "package asset index";
  if (type === "run_manifest") return "workflow run index";
  if (type === "delivery_readiness") return "release gate";
  if (type === "unsupported_file") return "unsupported file";
  return "unclassified";
}

function schemaInfoFor(type, payload, parseStatus) {
  if (type === "markdown_report" || type === "unsupported_file") {
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

function asList(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item)));
}
