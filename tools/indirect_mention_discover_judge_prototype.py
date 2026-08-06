#!/usr/bin/env python3
"""Discover suspected indirect mentions, then LLM-judge them (exploratory runner).

Production path (flagged, paid):
  apps.api.runtime_script_indirect_mention_proposals
  gated by AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS (default off).

This CLI remains a read-only exploration harness. It does not confirm/merge/
authorize and still incurs real LLM cost when run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.indirect_mention_discovery import (  # noqa: E402
    context_window,
    discover_indirect_mention_candidates,
)
from tools.indirect_mention_llm_prototype import (  # noqa: E402
    DEFAULT_PROVIDER_CONFIG,
    DEFAULT_SERVICE_ID,
    judge_one,
)

LONG_SCRIPTS = (
    REPO_ROOT / "docs/internal-notes/long-script-observation-20260805/01_echo_inn_long.txt",
    REPO_ROOT / "docs/internal-notes/long-script-observation-20260805/02_night_post_long.txt",
)


def proposal_from_judgment(
    discovery: dict[str, Any],
    judgment: dict[str, Any],
    *,
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "mention": discovery["mention"],
        "source_span": discovery["source_span"],
        "refers_to_real_character": bool(judgment.get("refers_to_real_character")),
        "refers_to_real_character_confidence": float(
            judgment.get("refers_to_real_character_confidence") or 0.0
        ),
        "refers_to_real_character_reason": str(
            judgment.get("refers_to_real_character_reason") or ""
        ),
        "is_present_in_scene": bool(judgment.get("is_present_in_scene")),
        "is_present_in_scene_confidence": float(
            judgment.get("is_present_in_scene_confidence") or 0.0
        ),
        "is_present_in_scene_reason": str(judgment.get("is_present_in_scene_reason") or ""),
        "is_indirect_mention": bool(judgment.get("is_indirect_mention")),
        # Legacy presence alias for older report readers.
        "is_character": bool(judgment.get("is_present_in_scene")),
        "confidence": float(judgment.get("is_present_in_scene_confidence") or 0.0),
        "reason": str(judgment.get("is_present_in_scene_reason") or ""),
        "status": "candidate",
        "authority": "non_authoritative_proposal",
        "discovery_method": discovery.get("discovery_method"),
        "discovery_methods": list(discovery.get("discovery_methods") or []),
        "occurrence_count": int(discovery.get("occurrence_count") or 1),
        "already_extracted_as_character": bool(discovery.get("already_extracted_as_character")),
        "latency_ms": latency_ms,
        "raw_judgment_text": judgment.get("raw_text"),
    }


def run_script(
    script_path: Path,
    *,
    service_id: str,
    timeout_sec: float,
    max_mentions: int,
    context_radius: int,
    output_dir: Path,
) -> dict[str, Any]:
    source_text = script_path.read_text(encoding="utf-8")
    discoveries = discover_indirect_mention_candidates(source_text)
    selected = discoveries if max_mentions <= 0 else discoveries[:max_mentions]
    proposals: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    wall_started = time.perf_counter()

    for index, discovery in enumerate(selected, start=1):
        mention = discovery["mention"]
        window = context_window(
            source_text,
            int(discovery["start"]),
            int(discovery["end"]),
            radius=context_radius,
        )
        print(
            f"[{script_path.name} {index}/{len(selected)}] "
            f"mention={mention} method={discovery.get('discovery_method')}",
            flush=True,
        )
        case_dir = output_dir / script_path.stem / f"{index:02d}_{mention}"
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = judge_one(
                text=window,
                mention=mention,
                service_id=service_id,
                output_dir=case_dir,
                timeout_sec=timeout_sec,
            )
            proposal = proposal_from_judgment(
                discovery,
                result["judgment"],
                latency_ms=float(result["latency_ms"]),
            )
            proposal["context_window"] = window
            proposals.append(proposal)
            print(json.dumps(proposal, ensure_ascii=False, indent=2), flush=True)
        except Exception as exc:  # noqa: BLE001 - prototype records real failures
            entry = {
                "mention": mention,
                "source_span": discovery["source_span"],
                "status": "error",
                "authority": "non_authoritative_proposal",
                "error_type": type(exc).__name__,
                "error": str(exc)[:400],
            }
            errors.append(entry)
            print(json.dumps(entry, ensure_ascii=False, indent=2), flush=True)

    return {
        "script": str(script_path.relative_to(REPO_ROOT)),
        "script_chars": len(source_text),
        "discovered_count": len(discoveries),
        "judged_count": len(selected),
        "discoveries": discoveries,
        "proposals": proposals,
        "errors": errors,
        "wall_time_sec": round(time.perf_counter() - wall_started, 2),
        "llm_call_count": len(proposals) + len(errors),
        "ok_llm_call_count": len(proposals),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Indirect-mention discover+judge closed loop (read-only prototype)."
    )
    parser.add_argument(
        "--script",
        action="append",
        default=[],
        help="Script path (repeatable). Defaults to the two long-script observation files.",
    )
    parser.add_argument("--service-id", default=DEFAULT_SERVICE_ID)
    parser.add_argument(
        "--provider-config",
        default=os.environ.get("AFS_PROVIDER_CONFIG", DEFAULT_PROVIDER_CONFIG),
    )
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument(
        "--max-mentions",
        type=int,
        default=1000,
        help="Maximum discoveries to judge. Use <=0 to judge every discovery.",
    )
    parser.add_argument("--context-radius", type=int, default=220)
    parser.add_argument(
        "--report",
        default=str(
            REPO_ROOT / "docs/internal-notes/indirect-mention-discover-judge-prototype-20260805.json"
        ),
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Skip LLM calls; only emit discovery results.",
    )
    args = parser.parse_args(argv)

    os.environ["AFS_PROVIDER_CONFIG"] = str(Path(args.provider_config).resolve())
    os.environ.setdefault("AFS_ALLOW_REMOTE_LLM", "true")

    scripts = [Path(item).resolve() for item in args.script] if args.script else list(LONG_SCRIPTS)
    report: dict[str, Any] = {
        "schema_version": "afs.indirect_mention_discover_judge_prototype.v0.1",
        "authority": "non_authoritative_prototype_only",
        "writes_candidates": False,
        "wired_into_analysis_candidates": False,
        "confirm_or_merge": False,
        "provider_config": os.environ["AFS_PROVIDER_CONFIG"],
        "service_id": args.service_id,
        "discover_only": bool(args.discover_only),
        "started_at_unix": time.time(),
        "scripts": [],
    }
    wall_started = time.perf_counter()

    if args.discover_only:
        for script_path in scripts:
            source_text = script_path.read_text(encoding="utf-8")
            discoveries = discover_indirect_mention_candidates(source_text)
            report["scripts"].append(
                {
                    "script": str(script_path.relative_to(REPO_ROOT)),
                    "script_chars": len(source_text),
                    "discovered_count": len(discoveries),
                    "judged_count": 0,
                    "discoveries": discoveries,
                    "proposals": [],
                    "errors": [],
                    "wall_time_sec": 0.0,
                    "llm_call_count": 0,
                    "ok_llm_call_count": 0,
                }
            )
    else:
        if os.environ.get("AFS_ALLOW_REMOTE_LLM", "").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            print("AFS_ALLOW_REMOTE_LLM must be true", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory(prefix="afs-indirect-mention-loop-") as tmp:
            out_root = Path(tmp)
            for script_path in scripts:
                report["scripts"].append(
                    run_script(
                        script_path,
                        service_id=args.service_id,
                        timeout_sec=args.timeout_sec,
                        max_mentions=args.max_mentions,
                        context_radius=args.context_radius,
                        output_dir=out_root,
                    )
                )

    report["finished_at_unix"] = time.time()
    report["wall_time_sec"] = round(time.perf_counter() - wall_started, 2)
    report["llm_call_count"] = sum(item.get("llm_call_count", 0) for item in report["scripts"])
    report["ok_llm_call_count"] = sum(item.get("ok_llm_call_count", 0) for item in report["scripts"])
    report["discovered_total"] = sum(item.get("discovered_count", 0) for item in report["scripts"])

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}", flush=True)
    if args.discover_only:
        return 0
    return 0 if report["ok_llm_call_count"] == report["llm_call_count"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
