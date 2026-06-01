from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_manifest_reference_audit() -> None:
    payload = _inspect(
        "manifest_reference_audit.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_manifest_reference_audit",
            "status": "pass",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "new_media_generated": False,
            "summary": {
                "json_files_checked": 14,
                "registry_assets": 87,
                "errors": 0,
                "missing_sha256": 0,
                "missing_files": 0,
                "absolute_refs": 0,
                "secret_like_refs": 0,
                "invalid_asset_types": 0,
                "invalid_statuses": 0,
            },
        },
    )

    assert payload["artifactType"] == "loulan_manifest_reference_audit"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan manifest reference audit"
    assert payload["memoryBundleCount"] == 1
    assert payload["inspector"]["title"] == "Loulan manifest reference audit"
    assert payload["inspector"]["status"] == "pass"
    assert payload["inspector"]["focus_targets"] == ["project", "review", "next-pass"]
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["json_files_checked"] == "14"
    assert facts["registry_assets"] == "87"
    assert facts["errors"] == "0"
    assert facts["missing_sha256"] == "0"
    assert facts["missing_files"] == "0"
    assert facts["absolute_refs"] == "0"
    assert facts["secret_like_refs"] == "0"
    assert facts["invalid_asset_types"] == "0"
    assert facts["invalid_statuses"] == "0"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
    assert facts["new_media_generated"] == "false"


def test_static_viewer_recognizes_loulan_text_encoding_audit() -> None:
    payload = _inspect(
        "text_encoding_audit.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_text_encoding_audit",
            "status": "pass",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "new_media_generated": False,
            "summary": {
                "text_files_checked": 268,
                "decode_errors": 0,
                "marker_hits": 0,
                "errors": 0,
            },
        },
    )

    assert payload["artifactType"] == "loulan_text_encoding_audit"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan text encoding audit"
    assert payload["memoryBundleCount"] == 1
    assert payload["inspector"]["title"] == "Loulan text encoding audit"
    assert payload["inspector"]["status"] == "pass"
    assert payload["inspector"]["focus_targets"] == ["project", "review", "next-pass"]
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["text_files_checked"] == "268"
    assert facts["decode_errors"] == "0"
    assert facts["marker_hits"] == "0"
    assert facts["errors"] == "0"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
    assert facts["new_media_generated"] == "false"


def _inspect(file_name: str, artifact: dict) -> dict:
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView, memorySourceForArtifacts }} from "./apps/web/memory-workbench-controller.js";

const artifact = {json.dumps(artifact)};
const artifacts = await parseFiles([
  {{ name: "{file_name}", text: async () => JSON.stringify(artifact) }},
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspector: view.artifact_inspector[0],
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
