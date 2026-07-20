"""Adversarial structural evaluator for the M5 graph-backed product adapter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate(root: Path) -> dict:
    findings = []
    shell = (root / "apps/studio/src/product-shell.js").read_text(encoding="utf-8")
    client = (root / "apps/studio/src/runtime-client.js").read_text(encoding="utf-8")
    projection = (root / "apps/studio/src/production-graph-workspace-projection.js").read_text(encoding="utf-8")
    chat = (root / "apps/studio/src/agent-chat-lifecycle.js").read_text(encoding="utf-8")
    store_state = (root / "apps/studio/src/store-state.js").read_text(encoding="utf-8")
    store = (root / "apps/studio/src/store.js").read_text(encoding="utf-8")
    persistence = (root / "apps/studio/src/store-runtime-persistence-controller.js").read_text(encoding="utf-8")
    canvas_body = (root / "apps/studio/src/canvas-node-body.js").read_text(encoding="utf-8")
    prompt_bar = (root / "apps/studio/src/prompt-bar.js").read_text(encoding="utf-8")
    adapter = (root / "apps/api/runtime_film_production_graph.py").read_text(encoding="utf-8")
    graph = (root / "apps/api/runtime_production_graph.py").read_text(encoding="utf-8")
    studio_state = (root / "apps/api/runtime_studio_state.py").read_text(encoding="utf-8")
    checks = [
        ("P0", "parallel card-stack workspace replaces shell", "return buildGraphSequenceWorkspace" not in shell and "m5-sequence-layout" not in shell),
        ("P0", "legacy Canvas/Storyboard/Agent Chat unreachable", all(token in shell for token in ("buildCanvasWorkspace", "buildStoryboardWorkspace", "buildAgentChat"))),
        ("P0", "single projection adapter missing", "production-graph-workspace-projection.js" in shell and all(token in projection for token in ("productionGraphWorkspaceProjection", "applyProductionGraphCanvasProjection", "productionGraphAgentContext"))),
        ("P0", "graph projection persists studio state", "persist: false" in shell and "productionGraphProjection" in projection),
        ("P0", "later canvas saves can persist graph projection", "projectedNodeIds" in store_state and "canonical_production_graph_projection" in store_state),
        ("P0", "graph project can write legacy Studio truth", "graph_has_authority(store, project_id)" in studio_state and "production graph is authoritative" in studio_state),
        ("P0", "client keeps runtime Studio writes enabled after graph migration", "production_graph_read_only" in persistence and "setRuntimePersistenceMode" in shell),
        ("P1", "runtime persistence mode responsibility remains compressed into store wiring",
         "createRuntimePersistenceController" in store
         and "let runtimePersistenceMode" not in store
         and all(token in persistence for token in ("cancelPendingSave", "publishGraphReadOnlyStatus", "saveQueuedAfterSuccess", "GRAPH_READ_ONLY_MODE"))
         and not any(line.count(";") > 1 for line in store.splitlines() if "runtimePersistence" in line)),
        ("P0", "migrated legacy nodes remain editable parallel truth", "productionGraphLegacyProjection" in projection and "productionGraphLegacyProjection" in canvas_body),
        ("P1", "read-only graph nodes expose legacy prompt actions", "graphReadOnly" in prompt_bar and "productionGraphProjection" in prompt_bar),
        ("P0", "graph command client disconnected", all(token in client for token in ("sequenceWorkspace", "previewSequenceImpact", "confirmSequenceMutation", "confirmSequenceAction"))),
        ("P0", "Agent Chat command lifecycle bypassed", "stageProductionGraphCommand" in shell and all(token in chat for token in ("m5_graph_mutation", "m5_graph_action", "productionGraphAgentReceipt"))),
        ("P0", "planning import bypasses Agent Chat or canonical confirm", all(token in shell for token in ("导入结构化制作方案", "stageProductionGraphCandidateCommand")) and "confirmFilmCandidate" in client and "m5_graph_candidate" in chat),
        ("P0", "graph product adapter writes studio_state", "studio_state" not in adapter.lower()),
        ("P0", "storyboard is not the same version/digest projection", "workspace.storyboard?.graph_version" in projection and "workspace.storyboard?.graph_digest" in projection),
        ("P0", "fixture or keyword fallback", not any(token in adapter.lower() for token in ("keyword", "fixture", "sample story", "blue raincoat", "postal robot"))),
        ("P0", "impact preview lacks dependency evidence", "impacted_descendants" in adapter and "dependency_evidence" in graph),
        ("P0", "Canvas entity mutations have no impact-confirm path", all(token in shell for token in ("selectedGraphTarget", "预览所选对象影响", "previewGraphMutation"))),
        ("P0", "version conflict not enforced", "expected_graph_version" in adapter and "GraphVersionConflict" in adapter),
        ("P0", "review, redo, selection, or delivery escapes graph", all(token in adapter for token in ("select_candidate", "review_decision", "redo_rejected", "delivery_state")) and all(token in graph for token in ("artifact_selected", "review_updated", "delivery_updated"))),
        ("P1", "planning-required structured path missing", "planning_required" in adapter and "buildGraphCanvasStatus" in shell),
        ("P1", "professional hierarchy missing", all(token in projection for token in ("script_revisions", "sequences", "characters", "reference_sets", "tasks", "reviews", "delivery_plan")) and "graphLifecycleList" in shell),
        ("P1", "raw schema or digest shown as default product copy", "schema_version" not in shell and "graphDigest}`" not in shell),
    ]
    for severity, issue, passed in checks:
        if not passed: findings.append({"severity": severity, "issue": issue})
    p0 = sum(item["severity"] == "P0" for item in findings); p1 = sum(item["severity"] == "P1" for item in findings)
    return {"verdict": "PASS" if not findings else "FAIL", "P0": p0, "P1": p1, "findings": findings,
            "provider_dispatch_count": 0, "cost_usd": 0,
            "non_claims": ["not_provider_smoke", "not_media_qa", "not_creative_qa", "not_owner_acceptance", "not_business_validation"]}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", default="."); args = parser.parse_args()
    report = evaluate(Path(args.root).resolve()); print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
