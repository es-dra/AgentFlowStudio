from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_web_artifact_registry_exports_asset_contract_metadata() -> None:
    script = """
import {
  ARTIFACT_REGISTRY,
  artifactAliasesFromRegistry,
  artifactFocusTargetsFor,
  artifactSourceRoleFor,
  artifactViewRouteFor,
  artifactWorkspaceSlotsFromRegistry,
} from "./apps/web/artifact-registry.js";

const artifactType = "agentflow_production_memory_asset_profile_context_projection";
const slots = artifactWorkspaceSlotsFromRegistry((type) => ({ artifactType: type }));
console.log(JSON.stringify({
  registrySize: Object.keys(ARTIFACT_REGISTRY).length,
  aliases: artifactAliasesFromRegistry()[artifactType],
  sourceRole: artifactSourceRoleFor(artifactType),
  focusTargets: artifactFocusTargetsFor(artifactType),
  workspaceSlot: slots.productionMemoryAssetProfileContextProjection.artifactType,
  viewRoute: artifactViewRouteFor(artifactType),
  factsBuilder: ARTIFACT_REGISTRY[artifactType].factsBuilder,
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["registrySize"] >= 10
    assert "asset_profile_context_projection.json" in payload["aliases"]
    assert payload["sourceRole"] == "production memory asset profile context projection"
    assert "assets" in payload["focusTargets"]
    assert payload["workspaceSlot"] == "agentflow_production_memory_asset_profile_context_projection"
    assert payload["viewRoute"] == "production_asset_cockpit"
    assert payload["factsBuilder"] == "productionAssetProfileContextProjectionFacts"


def test_web_artifact_registry_is_consumed_by_core_static_modules() -> None:
    consumers = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/artifact-workspace-artifacts.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-inspector-focus.js"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in consumers)

    assert "artifact-registry.js" in combined
    assert "artifactAliasesFromRegistry" in combined
    assert "artifactWorkspaceSlotsFromRegistry" in combined
    assert "artifactFocusTargetsFor" in combined
    assert "artifactLabelFor" in combined
