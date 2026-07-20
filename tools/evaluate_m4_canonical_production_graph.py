"""Independent structural evaluator for the M4 graph foundation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate(root: Path) -> dict:
    findings: list[dict[str, str]] = []
    graph = (root / "apps/api/runtime_production_graph.py").read_text(encoding="utf-8")
    adapter = (root / "apps/api/runtime_film_production_graph.py").read_text(encoding="utf-8")
    runs = (root / "apps/api/runtime_production_runs.py").read_text(encoding="utf-8")
    service = (root / "apps/api/runtime_service.py").read_text(encoding="utf-8")
    for forbidden in ("brief", "script", "shot", "film"):
        if forbidden in graph.lower(): findings.append({"severity": "P0", "issue": f"universal graph contains domain term: {forbidden}"})
    for required in ("GraphPlanningRequired", "trusted_candidate", "read_only_graph_projection", "execute_outside_graph_lock"):
        if required not in adapter and required not in graph: findings.append({"severity": "P0", "issue": f"missing M4 contract: {required}"})
    gate_index, dispatch_index = runs.find("if not real_story_recovery_route_enabled()"), runs.find("production = execute_real_story_production(")
    if gate_index < 0 or dispatch_index < 0 or gate_index > dispatch_index:
        findings.append({"severity": "P0", "issue": "legacy fixed production dispatch is not recovery-gated"})
    if "register_runtime_film_production_graph_routes" not in service:
        findings.append({"severity": "P0", "issue": "M4 graph adapter is not registered"})
    p0 = sum(item["severity"] == "P0" for item in findings); p1 = sum(item["severity"] == "P1" for item in findings)
    return {"verdict": "PASS" if not findings else "FAIL", "P0": p0, "P1": p1, "provider_dispatch_count": 0,
            "cost_usd": 0, "findings": findings,
            "non_claims": ["not_provider_smoke", "not_media_qa", "not_human_acceptance", "not_business_validation"]}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", default="."); args = parser.parse_args()
    report = evaluate(Path(args.root).resolve()); print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
