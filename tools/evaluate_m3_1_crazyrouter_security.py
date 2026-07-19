from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SECRET_MARKERS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"api[_-]?key\s*[=:]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
)
REQUIRED_UNIT_MARKERS = (
    "Type=oneshot",
    "EnvironmentFile=/etc/afs/afs-runtime.env",
    "User=afs-ops",
    "AFS_PROVIDER_CONFIG=/etc/afs/m3-1-crazyrouter.providers.json",
    "AFS_ALLOW_REMOTE_LLM=true",
    "AFS_ALLOW_REMOTE_IMAGE=false",
    "AFS_ALLOW_REMOTE_VIDEO=false",
    "AFS_ALLOW_REMOTE_AUDIO=false",
    "AFS_ALLOW_REMOTE_ASR=false",
    "AFS_ALLOW_REMOTE_VISION=false",
    "AFS_ALLOW_EXTERNAL_DOWNLOAD=false",
    "StateDirectory=afs-m3-1-crazyrouter",
    "UMask=0077",
    "NoNewPrivileges=true",
    "ProtectSystem=strict",
    "ProtectHome=read-only",
    "PrivateTmp=true",
    "CapabilityBoundingSet=",
    "RestrictSUIDSGID=true",
    "LockPersonality=true",
    "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
)
REQUIRED_RUNNER_MARKERS = (
    "EXPECTED_HEAD=",
    "EXPECTED_HARNESS_SHA256=",
    "EXPECTED_PROVIDER_CONFIG_SHA256=",
    "git -C \"$CANDIDATE_DIR\" rev-parse HEAD",
    "git -C \"$CANDIDATE_DIR\" status --porcelain",
    "sha256sum \"$HARNESS_PATH\"",
    "sha256sum \"$PROVIDER_CONFIG\"",
    "--service-id \"creative_script_planner\"",
    "--max-requests 8",
    "--max-total-cost-usd 20",
    "--expected-host \"api.crazyrouter.com\"",
    "--expected-model \"qwen-plus\"",
)
REQUIRED_HARNESS_MARKERS = (
    "EXPECTED_SERVICE_ID = \"creative_script_planner\"",
    "DISALLOWED_SHORT_CONTEXT_SERVICE_IDS",
    "MAX_REQUESTS = 8",
    "MAX_TOTAL_USD = 20.0",
    "DEFAULT_MIN_ESTIMATED_REQUEST_COST_USD = 2.50",
    "NON_LLM_GATES",
    "FORBIDDEN_STATIC_BASELINE_TERMS",
    "build_semantic_prior_context",
    "_semantic_closure",
    "semantic_prior_context",
    "semantic_closure",
    "_validate_m3_1_service_contract",
    "structured_output_json",
    "input_token_budget",
    "ArtifactWriter",
    "0o600",
    "load_pinned_provider_runtime",
    "provider_outputs_are_draft_evidence",
    "writes_canonical_truth",
    "credential_recorded",
)
REQUIRED_PROVIDER_MANIFEST_MARKERS = (
    "\"creative_script_planner\"",
    "\"bounded_creative_script_planning_text_gate\"",
    "\"structured_output_json\": true",
    "\"input_token_budget\": 8000",
    "\"prompt_char_limit\": 20000",
    "\"api_key_env\": \"CRAZYROUTER_API_KEY\"",
    "\"base_url\": \"https://api.crazyrouter.com/v1\"",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate M3.1 CrazyRouter harness/bootstrap security posture.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = evaluate(root=args.root.resolve(), bundle=args.bundle.resolve() if args.bundle else None)
    report_path = args.report or Path(f"/tmp/afs-m3-1-crazyrouter-security-{report['trace_id']}.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "P0": report["P0"],
                "P1": report["P1"],
                "provider_dispatch_count": report["provider_dispatch_count"],
                "report": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(*, root: Path, bundle: Path | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    harness = root / "tools/m3_1_crazyrouter_provider_harness.py"
    builder = root / "tools/build_m3_1_crazyrouter_bootstrap_bundle.py"
    provider_manifest = root / "configs/m3_1_crazyrouter_provider.manifest.json"
    _check_file(harness, findings, "harness")
    _check_file(builder, findings, "bundle_builder")
    _check_file(provider_manifest, findings, "provider_manifest")
    if harness.exists():
        text = harness.read_text(encoding="utf-8")
        _check_markers(text, REQUIRED_HARNESS_MARKERS, findings, "harness", "P0")
        _check_secret_markers(text, findings, "harness")
        for forbidden in ("_compact_for_prompt", "truncated_json"):
            if forbidden in text:
                findings.append(_finding("P1", "harness", f"blind prompt truncation marker remains: {forbidden}"))
        if "request_chat_completion" not in text:
            findings.append(_finding("P0", "harness", "does not call OpenAI-compatible raw response path"))
        if "AFS_ALLOW_REMOTE_LLM" not in text or "AFS_ALLOW_REMOTE_IMAGE" not in text:
            findings.append(_finding("P0", "harness", "provider gate checks are incomplete"))
        if "EXPECTED_SERVICE_ID = \"prompt_optimizer\"" in text or "--service-id \"prompt_optimizer\"" in text:
            findings.append(_finding("P0", "harness", "M3.1 harness must not target prompt_optimizer"))
    if builder.exists():
        text = builder.read_text(encoding="utf-8")
        _check_secret_markers(text, findings, "bundle_builder")
        for forbidden in ("systemd-run", "status afs-m3-1", "edit afs-m3-1", "ALL=(ALL) NOPASSWD: ALL"):
            if forbidden in text:
                findings.append(_finding("P0", "bundle_builder", f"forbidden sudo/systemd surface: {forbidden}"))
        if "/etc/afs/providers.local.json" in text and "does not modify" not in text:
            findings.append(_finding("P1", "bundle_builder", "bundle builder should not target existing providers.local.json"))
    if provider_manifest.exists():
        manifest_text = provider_manifest.read_text(encoding="utf-8")
        _check_markers(manifest_text, REQUIRED_PROVIDER_MANIFEST_MARKERS, findings, "provider_manifest", "P0")
        _check_secret_markers(manifest_text, findings, "provider_manifest")
        if "\"prompt_optimizer\"" in manifest_text:
            findings.append(_finding("P0", "provider_manifest", "dedicated M3.1 provider manifest must not define prompt_optimizer"))
    if bundle:
        _check_bundle(bundle, findings)
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "artifact_type": "afs_m3_1_crazyrouter_security_evaluation",
        "schema_version": "afs.m3_1.security_eval.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "P0": p0,
        "P1": p1,
        "P2": sum(1 for item in findings if item["severity"] == "P2"),
        "P3": sum(1 for item in findings if item["severity"] == "P3"),
        "findings": findings,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        "trace_id": _trace_id(findings, str(bundle or "")),
    }


def _check_bundle(bundle: Path, findings: list[dict[str, Any]]) -> None:
    required = {
        "runner": bundle / "afs-m3-1-crazyrouter-runner",
        "unit": bundle / "afs-m3-1-crazyrouter.service",
        "sudoers": bundle / "afs-m3-1-crazyrouter.sudoers",
        "install": bundle / "install.sh",
        "uninstall": bundle / "uninstall.sh",
        "readme": bundle / "README.md",
        "sums": bundle / "SHA256SUMS",
        "provider_manifest": bundle / "m3_1_crazyrouter_provider.manifest.json",
    }
    for key, path in required.items():
        _check_file(path, findings, f"bundle.{key}")
    unit = required["unit"].read_text(encoding="utf-8") if required["unit"].exists() else ""
    runner = required["runner"].read_text(encoding="utf-8") if required["runner"].exists() else ""
    sudoers = required["sudoers"].read_text(encoding="utf-8") if required["sudoers"].exists() else ""
    install = required["install"].read_text(encoding="utf-8") if required["install"].exists() else ""
    provider_manifest = required["provider_manifest"].read_text(encoding="utf-8") if required["provider_manifest"].exists() else ""
    for label, text in (("unit", unit), ("runner", runner), ("sudoers", sudoers), ("install", install)):
        _check_secret_markers(text, findings, f"bundle.{label}")
    _check_secret_markers(provider_manifest, findings, "bundle.provider_manifest")
    _check_markers(unit, REQUIRED_UNIT_MARKERS, findings, "bundle.unit", "P0")
    _check_markers(runner, REQUIRED_RUNNER_MARKERS, findings, "bundle.runner", "P0")
    _check_markers(provider_manifest, REQUIRED_PROVIDER_MANIFEST_MARKERS, findings, "bundle.provider_manifest", "P0")
    if "prompt_optimizer" in unit or "prompt_optimizer" in runner or "prompt_optimizer" in provider_manifest:
        findings.append(_finding("P0", "bundle", "bundle must not target prompt_optimizer for M3.1"))
    if "*" in sudoers or "systemd-run" in sudoers or " status " in sudoers or " edit " in sudoers:
        findings.append(_finding("P0", "bundle.sudoers", "sudoers grants wildcard/status/edit/systemd-run surface"))
    for command in ("start afs-m3-1-crazyrouter.service", "stop afs-m3-1-crazyrouter.service", "reset-failed afs-m3-1-crazyrouter.service"):
        if command not in sudoers:
            findings.append(_finding("P0", "bundle.sudoers", f"missing exact command {command}"))
    if "systemctl start" in install:
        findings.append(_finding("P0", "bundle.install", "install.sh must not start the unit"))
    if "stat -c '%a %U:%G' \"/etc/afs/afs-runtime.env\"" not in install:
        findings.append(_finding("P1", "bundle.install", "install.sh does not verify env file mode without reading it"))


def _check_file(path: Path, findings: list[dict[str, Any]], scope: str) -> None:
    if not path.exists():
        findings.append(_finding("P0", scope, f"missing {path}"))


def _check_markers(text: str, markers: tuple[str, ...], findings: list[dict[str, Any]], scope: str, severity: str) -> None:
    for marker in markers:
        if marker not in text:
            findings.append(_finding(severity, scope, f"missing marker {marker}"))


def _check_secret_markers(text: str, findings: list[dict[str, Any]], scope: str) -> None:
    for pattern in SECRET_MARKERS:
        if pattern.search(text):
            findings.append(_finding("P0", scope, "secret-like literal detected"))


def _finding(severity: str, scope: str, issue: str) -> dict[str, Any]:
    return {"severity": severity, "scope": scope, "issue": issue}


def _trace_id(findings: list[dict[str, Any]], bundle: str) -> str:
    import hashlib

    return hashlib.sha256(json.dumps({"findings": findings, "bundle": bundle}, sort_keys=True).encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    raise SystemExit(main())
