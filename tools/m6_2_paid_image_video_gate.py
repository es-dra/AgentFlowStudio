from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentflow.harness.json_io import write_json
from agentflow_studio.production.adaptive_canvas_v2 import (
    AdaptiveProductionProfile,
    AdaptiveRunOptions,
    AdaptiveShotSpec,
    build_script_truth_from_profile,
    load_adaptive_workspace,
    run_adaptive_canvas_production,
    sha256_file,
)
from agentflow_studio.production.runtime_safe_io import read_json, safe_id
from apps.api.runtime_store import RuntimeStore


DEFAULT_CASES = ("dialogue_room", "four_person_action", "sci_fi_chamber")
PUBLIC_IMAGE_PRICE_USD = 0.0377
CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC = 0.25
EVIDENCE_SCHEMA = "afs.m6_2.paid_image_video_gate.v0.1"
NEGATIVE_LOCKS = (
    "no cigarettes or smoke",
    "no blood or gore",
    "no weapons",
    "no logos",
    "no readable text",
    "no celebrity likeness",
    "no explicit injury",
    "no copyrighted character styling",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the M6.2 paid image/video asset reuse gate.")
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--m6-1-root", required=True, type=Path)
    parser.add_argument("--runtime-pid", required=True, type=int)
    parser.add_argument("--provider-config", type=Path)
    parser.add_argument("--case-id", action="append", choices=DEFAULT_CASES)
    parser.add_argument("--budget-usd", type=float, default=100.0)
    parser.add_argument("--run-id", default="paid-media-v2")
    parser.add_argument("--poll-interval-sec", type=float, default=15.0)
    parser.add_argument("--poll-timeout-sec", type=float, default=5400.0)
    args = parser.parse_args()

    run_root: Path = args.run_root.resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    if _is_inside_git_worktree(run_root):
        raise SystemExit(f"evidence run root is inside a Git worktree: {run_root}")
    _inherit_provider_env(args.runtime_pid)
    os.environ["AFS_ALLOW_REMOTE_IMAGE"] = "true"
    os.environ["AFS_ALLOW_REMOTE_VIDEO"] = "true"
    for closed in (
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        os.environ[closed] = "false"
    if args.provider_config is not None:
        os.environ["AFS_PROVIDER_CONFIG"] = str(args.provider_config)

    case_ids = tuple(args.case_id or DEFAULT_CASES)
    cases = [_load_case(args.m6_1_root, case_id) for case_id in case_ids]
    profiles = [_profile_from_case(case) for case in cases]
    budget = _budget_projection(profiles)
    if budget["conservative_estimated_total_usd"] > args.budget_usd:
        write_json(run_root / "budget_projection.json", budget)
        raise SystemExit(f"conservative estimate exceeds budget: {budget['conservative_estimated_total_usd']}")
    write_json(run_root / "budget_projection.json", budget)

    runtime_root = run_root / "candidate_runtime"
    case_results = []
    for case, profile in zip(cases, profiles, strict=True):
        case_results.append(
            _run_case(
                run_root=run_root,
                runtime_root=runtime_root,
                case=case,
                profile=profile,
                run_id=args.run_id,
                provider_config_path=args.provider_config,
                poll_interval_sec=args.poll_interval_sec,
                poll_timeout_sec=args.poll_timeout_sec,
            )
        )

    report = _compile_report(run_root=run_root, runtime_root=runtime_root, budget=budget, case_results=case_results)
    write_json(run_root / "m6_2_paid_image_video_gate_report.json", report)
    print(json.dumps({"status": report["status"], "run_root": str(run_root), "case_count": len(case_results)}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


def _inherit_provider_env(pid: int) -> None:
    raw = Path(f"/proc/{pid}/environ").read_bytes()
    allowed_names = {"AFS_PROVIDER_CONFIG", "CRAZYROUTER_API_KEY"}
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        name = key.decode("utf-8", errors="ignore")
        if name in allowed_names:
            os.environ[name] = value.decode("utf-8", errors="ignore")
    if not os.environ.get("AFS_PROVIDER_CONFIG"):
        raise RuntimeError("AFS_PROVIDER_CONFIG is not available from runtime process")
    if not os.environ.get("CRAZYROUTER_API_KEY"):
        raise RuntimeError("CrazyRouter credential env is not available from runtime process")


def _load_case(m6_1_root: Path, case_id: str) -> dict[str, Any]:
    path = m6_1_root / "cases" / case_id / "case_report.json"
    payload = read_json(path)
    revision = payload.get("revision2")
    if not isinstance(revision, dict):
        raise RuntimeError(f"M6.1 case report missing revision2: {case_id}")
    return {
        "case_id": case_id,
        "path": str(path),
        "title": payload.get("case", {}).get("title") or revision.get("title") or case_id,
        "revision2": revision,
        "revision2_scores": payload.get("revision2_scores") or {},
        "confirmed": payload.get("confirmed"),
    }


def _profile_from_case(case: dict[str, Any]) -> AdaptiveProductionProfile:
    revision = case["revision2"]
    character_names = {str(item.get("character_id")): str(item.get("display_name") or item.get("name") or "") for item in revision.get("characters") or []}
    scene_names = {str(item.get("scene_id")): str(item.get("name") or item.get("space") or "") for item in revision.get("scenes") or []}
    shots = []
    for index, shot in enumerate(revision.get("shots") or [], start=1):
        source_duration = float(shot.get("duration_seconds") or 5)
        duration = 10.0 if source_duration >= 10 else 5.0
        shot_id = safe_id(f"{case['case_id']}-{index:02d}-{shot.get('shot_id')}", max_length=96)
        characters = tuple(
            name for ref in (shot.get("character_refs") or []) if (name := character_names.get(str(ref), ""))
        )
        if not characters:
            characters = tuple(item for item in character_names.values() if item)[:2] or ("Fictional performer",)
        scene_id = str(shot.get("scene_id") or "")
        location = scene_names.get(scene_id) or str(shot.get("location") or f"Scene {index}")
        camera = "; ".join(
            _clean_text(shot.get(key))
            for key in ("shot_size", "camera_angle", "camera_movement")
            if _clean_text(shot.get(key))
        )
        action = "; ".join(
            _clean_text(shot.get(key))
            for key in ("blocking", "narrative_purpose", "sound")
            if _clean_text(shot.get(key))
        )
        shots.append(
            AdaptiveShotSpec(
                shot_id=shot_id,
                summary=_clean_text(shot.get("intent") or shot.get("summary") or f"Shot {index}"),
                location=_clean_text(location),
                characters=characters,
                action=action,
                camera=camera or "controlled cinematic camera",
                duration_sec=duration,
                generation_strategy="image_to_video",
                strategy_reason="M6.2 paid media gate requires a tracked keyframe and i2v video per confirmed ProductionGraph shot.",
                continuity_in=_clean_text(shot.get("content_driven_duration_reason") or "continue from prior confirmed graph state"),
                continuity_out=_clean_text(shot.get("transition") or "preserve the next shot continuity"),
            )
        )
    if not shots:
        raise RuntimeError(f"case has no revision2 shots: {case['case_id']}")
    return AdaptiveProductionProfile(
        project_type="m6_2_paid_image_video_asset_reuse",
        title=_clean_text(revision.get("title") or case["title"]),
        logline=_clean_text(revision.get("logline") or case["title"]),
        style_bible=_style_bible(revision),
        characters=tuple(_safe_character(item) for item in revision.get("characters") or []),
        scenes=tuple(_safe_scene(item) for item in revision.get("scenes") or []),
        shots=tuple(shots),
        llm_service_id="m6_1_upstream_server_codex_revision2",
        script_candidate_id=f"{case['case_id']}-m6-1-revision2",
        script_source_type="provider",
        provider_supported_video_durations_sec=(10, 5),
        max_paid_attempts=20,
        media_prompt_style="cinematic_live_action",
        media_aspect_ratio="16:9",
        video_resolution="480p",
        video_motion="controlled live-action camera movement; preserve identity, wardrobe, props, lighting, and scene continuity",
        media_negative_locks=NEGATIVE_LOCKS,
    )


def _run_case(
    *,
    run_root: Path,
    runtime_root: Path,
    case: dict[str, Any],
    profile: AdaptiveProductionProfile,
    run_id: str,
    provider_config_path: Path | None,
    poll_interval_sec: float,
    poll_timeout_sec: float,
) -> dict[str, Any]:
    project_id = f"m6-2-{case['case_id']}"
    run_id = safe_id(run_id, max_length=96)
    case_evidence = run_root / "cases" / case["case_id"]
    case_evidence.mkdir(parents=True, exist_ok=True)
    events_path = case_evidence / "events.jsonl"
    _seed_upstream_script_truth(runtime_root, project_id, run_id, profile, case)
    started = time.monotonic()
    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=runtime_root,
            project_id=project_id,
            run_id=run_id,
            profile=profile,
            mode="real",
            provider_config_path=provider_config_path,
            video_poll_interval_sec=poll_interval_sec,
            video_poll_timeout_sec=poll_timeout_sec,
        ),
        callback=lambda event: _append_event(events_path, event),
    )
    elapsed = round(time.monotonic() - started, 2)
    store = RuntimeStore(runtime_root)
    workspace = load_adaptive_workspace(store, project_id=project_id, run_id=run_id)
    ledger_path = Path(result["ledger_path"])
    ledger_before = read_json(ledger_path)
    idempotency = _rerun_idempotency(
        runtime_root=runtime_root,
        project_id=project_id,
        run_id=run_id,
        profile=profile,
        provider_config_path=provider_config_path,
        poll_interval_sec=poll_interval_sec,
        poll_timeout_sec=poll_timeout_sec,
        ledger_before=ledger_before,
    )
    qa = read_json(Path(result["run_root"]) / "qa" / "technical_qa.json")
    delivery = read_json(Path(result["run_root"]) / "delivery_manifest.json")
    visual = _visual_summary(Path(result["run_root"]), profile)
    case_result = {
        "case_id": case["case_id"],
        "status": "PASS" if result["status"] == "succeeded" and qa["status"] == "pass" and idempotency["status"] == "PASS" else "FAIL",
        "elapsed_sec": elapsed,
        "project_id": project_id,
        "run_id": run_id,
        "run_root": result["run_root"],
        "source_m6_1_case_report": case["path"],
        "source_candidate_digest": case["revision2"].get("candidate_digest"),
        "m6_1_scores": case["revision2_scores"],
        "shot_count": profile.shot_count,
        "video_seconds": profile.target_duration_sec,
        "paid_attempt_count": result["paid_attempt_count"],
        "ledger_path": result["ledger_path"],
        "final_path": result["final_path"],
        "final_sha256": result["final_sha256"],
        "qa": qa,
        "delivery_manifest": delivery,
        "workspace_digest": _sha256_json(workspace),
        "idempotency": idempotency,
        "visual_summary": visual,
    }
    write_json(case_evidence / "case_result.json", case_result)
    return case_result


def _seed_upstream_script_truth(
    runtime_root: Path,
    project_id: str,
    run_id: str,
    profile: AdaptiveProductionProfile,
    case: dict[str, Any],
) -> None:
    run_dir = runtime_root / "projects" / safe_id(project_id) / "adaptive_canvas_v2" / safe_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = run_dir / "script_truth.json"
    if script_path.exists():
        return
    script = build_script_truth_from_profile(profile)
    script["aggregate_version"] = "afs.m6_2.upstream_m6_1_revision2.script_truth.v0.1"
    script["provenance"] = {
        "source_type": "m6_1_server_codex_revision2",
        "provider_generated": True,
        "llm_success": True,
        "owner_acceptance": False,
        "source_case_id": case["case_id"],
        "source_candidate_digest": case["revision2"].get("candidate_digest"),
        "source_revision_id": (case["revision2"].get("revision") or {}).get("revision_id"),
        "source_validation": case["revision2"].get("validation"),
        "media_safety_translation": "prompts remove smoke, blood, weapons, logos, readable text, and celebrity likeness while preserving graph intent",
    }
    write_json(script_path, script)


def _rerun_idempotency(
    *,
    runtime_root: Path,
    project_id: str,
    run_id: str,
    profile: AdaptiveProductionProfile,
    provider_config_path: Path | None,
    poll_interval_sec: float,
    poll_timeout_sec: float,
    ledger_before: dict[str, Any],
) -> dict[str, Any]:
    before_count = int(ledger_before.get("paid_attempt_count") or 0)
    before_attempts = len(ledger_before.get("attempts") or [])
    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=runtime_root,
            project_id=project_id,
            run_id=run_id,
            profile=profile,
            mode="real",
            provider_config_path=provider_config_path,
            video_poll_interval_sec=poll_interval_sec,
            video_poll_timeout_sec=poll_timeout_sec,
        )
    )
    ledger_after = read_json(Path(result["ledger_path"]))
    after_count = int(ledger_after.get("paid_attempt_count") or 0)
    after_attempts = len(ledger_after.get("attempts") or [])
    return {
        "status": "PASS" if after_count == before_count and after_attempts == before_attempts else "FAIL",
        "paid_attempt_count_before": before_count,
        "paid_attempt_count_after": after_count,
        "attempt_rows_before": before_attempts,
        "attempt_rows_after": after_attempts,
    }


def _visual_summary(run_dir: Path, profile: AdaptiveProductionProfile) -> dict[str, Any]:
    final_path = run_dir / "final" / "adaptive_canvas_v2_final.mp4"
    probe = _ffprobe(final_path)
    contact_sheet = run_dir / "qa" / "contact_sheet_1fps.jpg"
    return {
        "reference_sheet": _file_summary(run_dir / "reference_sheet.png"),
        "keyframes": [_file_summary(path) for path in sorted((run_dir / "keyframes").glob("*.png"))],
        "video_chunks": [_file_summary(path) for path in sorted((run_dir / "video_chunks").glob("*/*.mp4"))],
        "shot_composes": [_file_summary(path) for path in sorted((run_dir / "shot_composes").glob("*.mp4"))],
        "final": _file_summary(final_path),
        "contact_sheet": _file_summary(contact_sheet),
        "final_probe": probe,
        "media_prompt_style": profile.media_prompt_style,
        "media_aspect_ratio": profile.media_aspect_ratio,
    }


def _budget_projection(profiles: list[AdaptiveProductionProfile]) -> dict[str, Any]:
    image_count = sum(1 + profile.shot_count for profile in profiles)
    video_seconds = sum(profile.target_duration_sec for profile in profiles)
    image_cost = image_count * PUBLIC_IMAGE_PRICE_USD
    video_cost = video_seconds * CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "status": "PASS",
        "image_count": image_count,
        "video_seconds": video_seconds,
        "image_unit_usd_public_doc": PUBLIC_IMAGE_PRICE_USD,
        "conservative_video_unit_usd_per_sec": CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC,
        "conservative_image_cost_usd": round(image_cost, 4),
        "conservative_video_cost_usd": round(video_cost, 4),
        "conservative_estimated_total_usd": round(image_cost + video_cost, 4),
        "pricing_sources": [
            "https://crazyrouter.com/guide/gpt-image-2-api",
            "https://docs.crazyrouter.com/video/seedance",
            "https://crazyrouter.com/en/blog/seedance-2-0-actual-output-token-billing-explained",
        ],
        "actual_provider_receipt_boundary": "provider adapters record usage if returned; otherwise actual billed cost remains provider-account external",
    }


def _compile_report(
    *,
    run_root: Path,
    runtime_root: Path,
    budget: dict[str, Any],
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    statuses = [item["status"] for item in case_results]
    attempts = sum(int(item["paid_attempt_count"]) for item in case_results)
    p0 = []
    p1 = []
    for result in case_results:
        if result["status"] != "PASS":
            p0.append({"case_id": result["case_id"], "issue": "case did not pass"})
        qa_findings = result.get("qa", {}).get("findings") or []
        for finding in qa_findings:
            if finding.get("severity") == "P0":
                p0.append({"case_id": result["case_id"], **finding})
            if finding.get("severity") == "P1":
                p1.append({"case_id": result["case_id"], **finding})
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "status": "PASS" if statuses and all(status == "PASS" for status in statuses) and not p0 and not p1 else "FAIL",
        "run_root": str(run_root),
        "runtime_root": str(runtime_root),
        "case_count": len(case_results),
        "provider_services": {
            "image": {"service_id": "image_relay", "model": "gpt-image-2"},
            "video": {"service_id": "seedance_i2v", "model": "doubao-seedance-2-0"},
        },
        "dispatch": {
            "paid_attempt_count": attempts,
            "retry_policy": "idempotent rerun must not add attempts; provider failures may retry only by new prompt/fingerprint",
            "actual_receipt_status": "usage recorded if returned by provider; no secret or raw provider response stored",
        },
        "budget_projection": budget,
        "issue_ledger": {"P0": len(p0), "P1": len(p1), "P0_findings": p0, "P1_findings": p1},
        "case_results": case_results,
        "non_claims": [
            "not_owner_human_acceptance",
            "not_business_validation",
            "not_public_release",
            "not_media_provider_quality_certification",
        ],
    }


def _style_bible(revision: dict[str, Any]) -> str:
    assets = revision.get("assets") if isinstance(revision.get("assets"), list) else []
    styles = [str(item.get("style") or item.get("name") or "") for item in assets if str(item.get("kind") or "") == "style"]
    scene_styles = [str(item.get("visual_expression") or item.get("lighting") or "") for item in revision.get("scenes") or []]
    return _clean_text(" ".join(styles + scene_styles) or revision.get("logline") or "cinematic continuity style")


def _safe_character(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "character_id": safe_id(str(item.get("character_id") or item.get("display_name") or "character"), max_length=96),
        "name": _clean_text(item.get("display_name") or item.get("name") or "Fictional performer"),
        "role": _clean_text(item.get("goal") or item.get("relationship_arc") or "story performer"),
        "continuity": _clean_text(" ".join(str(v) for v in (item.get("signature_features") or [])) or item.get("wardrobe") or ""),
        "appearance": _clean_text(item.get("appearance") or ""),
        "wardrobe": _clean_text(item.get("wardrobe") or ""),
    }


def _safe_scene(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_id": safe_id(str(item.get("scene_id") or item.get("name") or "scene"), max_length=96),
        "name": _clean_text(item.get("name") or item.get("space") or "Scene"),
        "visual_mood": _clean_text(item.get("visual_expression") or item.get("lighting") or item.get("emotion") or ""),
        "story_function": _clean_text(item.get("action") or item.get("continuity") or ""),
    }


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    replacements = {
        "血迹": "深色雨水痕迹",
        "血": "红色封签",
        "伤痕": "旧记号",
        "旧伤": "旧记号",
        "枪": "工具",
        "武器": "工具",
        "烟": "雾感灯光",
        "smoke": "soft haze lighting",
        "blood": "dark rain mark",
        "weapon": "tool",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text[:1800]


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {key: value for key, value in event.items() if key not in {"raw", "secret", "authorization"}}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")


def _file_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    return {"path": str(path), "exists": True, "sha256": sha256_file(path), "byte_count": path.stat().st_size}


def _ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {"status": "FAIL", "stderr_tail": proc.stderr[-500:]}
    payload = json.loads(proc.stdout or "{}")
    return {"status": "PASS", **payload}


def _sha256_json(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(body).hexdigest()


def _is_inside_git_worktree(path: Path) -> bool:
    proc = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return proc.returncode == 0 and bool(proc.stdout.strip())


if __name__ == "__main__":
    raise SystemExit(main())
