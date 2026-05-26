import { ARTIFACT_CLASSES } from "./artifact-contracts.js";
import { asList, asObject, asText, describeValue, firstText, normalizeStatus } from "./artifact-values.js";

export function normalizeEvidenceMap(summaryArtifacts, run) {
  const selected = summaryArtifacts
    .filter((artifact) => artifact.artifactClass === ARTIFACT_CLASSES.KNOWN_CONTRACT)
    .map((artifact) => ({
      artifactType: artifact.artifactType,
      fileName: artifact.fileName,
      sourceRole: artifact.sourceRole,
      status: normalizeStatus(artifact.parseStatus),
      relation: relationFor(artifact.artifactType),
      path: "",
    }));

  const packageEvidence = summaryArtifacts
    .filter((artifact) => artifact.artifactType === "package_manifest")
    .flatMap((artifact) =>
      Object.entries(asObject(artifact.payload?.evidence)).map(([artifactType, path]) => ({
        artifactType,
        fileName: asText(path, artifactType),
        sourceRole: "package evidence reference",
        status: "unknown",
        relation: "package_manifest.evidence",
        path: asText(path, ""),
      })),
    );

  const indexed = (run?.artifacts || []).map((entry) => ({
    artifactType: entry.name,
    fileName: entry.path || entry.name,
    sourceRole: entry.required ? "required by run_manifest" : "optional in run_manifest",
    status: entry.exists ? "pass" : entry.required ? "missing" : "unknown",
    relation: "run_manifest.artifact_index",
    path: entry.path || "",
  }));

  return dedupeEvidence([...selected, ...packageEvidence, ...indexed]);
}

export function normalizeRiskLedger(summaryArtifacts, workspaceParts) {
  const risks = [];
  for (const artifact of summaryArtifacts) {
    const payload = asObject(artifact.payload);
    addListRisks(risks, artifact, "warning", payload.warnings);
    addListRisks(risks, artifact, "fail", payload.errors);
    addListRisks(risks, artifact, "fail", payload.failures);
    addCheckRisks(risks, artifact, payload.checks);
    if (artifact.artifactType === "selection_diagnostics") {
      addSelectionDiagnosticsRisks(risks, artifact, payload);
    }
    if (artifact.artifactType === "review_report") {
      addListRisks(risks, artifact, "warning", payload.recommendations);
      addReviewSectionRisks(risks, artifact, payload);
    }
    if (artifact.artifactType === "delivery_readiness") {
      addDeliveryReadinessRisks(risks, artifact, payload);
    }
  }

  for (const warning of workspaceParts.warnings || []) {
    risks.push({ source: "viewer", severity: "warning", message: warning });
  }
  for (const error of workspaceParts.errors || []) {
    risks.push({ source: "viewer", severity: "fail", message: error });
  }

  return risks.filter((risk) => risk.message);
}

export function normalizeAssetLedger(summaryArtifacts, packageSummary) {
  const assets = [];
  for (const asset of packageSummary?.assets || []) {
    assets.push({
      role: asText(asset.role, "asset"),
      path: asText(asset.path, ""),
      source: "package_manifest",
      status: asset.exists ? "pass" : asset.required ? "missing" : "unknown",
      detail: asset.sizeBytes !== null && asset.sizeBytes !== undefined ? `${asset.sizeBytes} bytes` : "",
    });
  }

  for (const artifact of summaryArtifacts) {
    const payload = asObject(artifact.payload);
    if (artifact.artifactType === "final_video_manifest") {
      addAsset(assets, "final_video", firstText(payload, ["output_video_path", "output_path", "final_video_path", "final_video"]), artifact);
    }
    if (artifact.artifactType === "real_slice_manifest") {
      for (const clip of collectAssetObjects(payload, ["clips", "outputs", "clip_paths"])) {
        addAsset(assets, "clip", firstText(clip, ["path", "output_path", "file", "clip_path"]), artifact);
      }
    }
    if (artifact.artifactType === "clip_plan") {
      for (const segment of collectAssetObjects(payload, ["segments", "clips"])) {
        addAsset(assets, "planned_clip", firstText(segment, ["output_name", "output_path", "path"]), artifact);
      }
    }
    if (artifact.artifactType === "subtitle_manifest") {
      addAsset(assets, "subtitle", firstText(payload, ["subtitle_path", "srt_path", "output_path", "path"]), artifact);
    }
    if (artifact.artifactType === "audio_mix_manifest") {
      addAsset(assets, "audio_mix_video", firstText(payload, ["output_video_path", "output_path", "final_video_path"]), artifact);
      addAsset(assets, "bgm_audio", firstText(payload, ["bgm_path", "audio_path"]), artifact);
    }
    if (artifact.artifactType === "cover_manifest") {
      addAsset(assets, "cover", firstText(payload, ["cover_path", "output_path", "path"]), artifact);
    }
  }

  return dedupeAssets(assets);
}

function relationFor(type) {
  if (type === "run_manifest") return "root run index";
  if (type === "package_manifest") return "delivery package index";
  if (type === "quality_report" || type === "review_report") return "acceptance evidence";
  if (type === "delivery_readiness") return "handoff gate";
  if (type === "markdown_report") return "human-readable report";
  return "workflow artifact";
}

function addListRisks(risks, artifact, severity, values) {
  for (const message of asList(values)) {
    risks.push({ source: artifact.artifactType, severity, message });
  }
}

function addCheckRisks(risks, artifact, checks) {
  if (!Array.isArray(checks)) return;
  for (const check of checks) {
    const status = normalizeStatus(check?.status);
    if (status !== "warning" && status !== "fail" && status !== "missing") continue;
    risks.push({
      source: artifact.artifactType,
      severity: status,
      message: describeValue(check?.message || check?.name || check?.id || check),
    });
  }
}

function addSelectionDiagnosticsRisks(risks, artifact, payload) {
  const rejectionCounts = asObject(payload.rejection_reason_counts);
  for (const [reason, count] of Object.entries(rejectionCounts)) {
    if (Number(count) > 0) {
      risks.push({
        source: artifact.artifactType,
        severity: "warning",
        message: `${reason}: ${count}`,
      });
    }
  }
}

function addReviewSectionRisks(risks, artifact, payload) {
  const sections = Array.isArray(payload.sections) ? payload.sections : [];
  for (const section of sections) {
    const checks = Array.isArray(section?.checks) ? section.checks : [];
    for (const check of checks) {
      const status = normalizeStatus(check?.status);
      if (status !== "warning" && status !== "fail" && status !== "missing") continue;
      risks.push({
        source: `${artifact.artifactType}:${asText(section.name, "section")}`,
        severity: status,
        message: describeValue(check?.message || check?.id || check),
      });
    }
  }
}

function addDeliveryReadinessRisks(risks, artifact, payload) {
  const runs = Array.isArray(payload.runs) ? payload.runs : [];
  for (const run of runs) {
    const source = `${artifact.artifactType}:${asText(run.run_id, "run")}`;
    addRunMessages(risks, source, "fail", run.failures);
    addRunMessages(risks, source, "warning", run.warnings);
  }
}

function addRunMessages(risks, source, severity, values) {
  for (const message of asList(values)) {
    risks.push({ source, severity, message });
  }
}

function collectAssetObjects(payload, fields) {
  const collected = [];
  for (const field of fields) {
    const value = payload[field];
    if (Array.isArray(value)) {
      collected.push(...value.map((item) => (typeof item === "object" ? item : { path: item })));
    }
  }
  return collected;
}

function addAsset(assets, role, path, artifact) {
  if (!path) return;
  assets.push({
    role,
    path,
    source: artifact.artifactType,
    status: "unknown",
    detail: artifact.fileName,
  });
}

function dedupeEvidence(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.artifactType}|${item.fileName}|${item.relation}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function dedupeAssets(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.role}|${item.path}|${item.source}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
