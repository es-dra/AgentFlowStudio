#!/usr/bin/env python3
"""Standalone read-only prototype: LLM judges whether a name mention is a character.

NOT wired into analysis-candidates. Does not write candidates or authority.
Requires:
  AFS_ALLOW_REMOTE_LLM=true
  AFS_PROVIDER_CONFIG=/etc/afs/providers.local.json
  CRAZYROUTER_API_KEY (or whatever credential_env the prompt_optimizer account uses)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentflow_studio.model_gateway.provider_adapter import (  # noqa: E402
    ProviderDispatchRequest,
    load_provider_registry,
)

DEFAULT_SERVICE_ID = "prompt_optimizer"
DEFAULT_PROVIDER_CONFIG = "/etc/afs/providers.local.json"

SYSTEM_RULES = """你是剧本理解助手。任务：判断给定「疑似人名」在这段剧本片段里，是否应被视为「角色候选」(character candidate)。

硬规则：
1. 仅在回忆、传闻、玩笑、信件/汇款单/背景叙述中被提到的名字，默认不算角色候选，应返回 is_character=false。
2. 需要有动作、对白、舞台指示中的在场行为、或明确作为出场人物被介绍等证据，才能返回 is_character=true。
3. 不确定时必须返回 is_character=false，并降低 confidence。
4. 只根据给定片段判断，不要臆造片段外剧情。
5. 只输出一个 JSON 对象，不要 Markdown，不要代码围栏。字段严格为：
   {"is_character": boolean, "confidence": number, "reason": string}
   confidence 范围 0 到 1；reason 用简短中文说明依据。
"""


CASES: list[dict[str, Any]] = [
    {
        "case_id": "neg_memory_chenmo",
        "mention": "陈默",
        "expected": "false（纯回忆/转述提及）",
        "text": "她想起他昨天说起了陈默。窗外雨还在下，她没有再追问。",
    },
    {
        "case_id": "neg_letter_guheng",
        "mention": "顾衡",
        "expected": "false 或低置信度（信件/汇款单叙事 + 他人转述，无在场动作/对白）",
        "text": (
            "顾晚拆开：里面是一张旧式汇款单复印件，收款人是「顾衡」，金额空白，"
            "备注栏写着「夜班邮筒第七格」。没有信件正文。\n\n"
            "方糖\n顾衡是谁？你亲戚？\n\n"
            "顾晚\n我爸。他去世三年了。他从不让我碰邮局的夜班。\n\n"
            "何婶\n你爸顾衡以前也上夜班。有一年来了一个女人，只寄「留局待领」，"
            "收件人永远写顾衡。后来女人不来了，你爸开始守第七格。"
        ),
    },
    {
        "case_id": "pos_dialogue_chenmo",
        "mention": "陈默",
        "expected": "true / 高置信度（有对白与动作，虽无「人物：」标签）",
        "text": (
            "风把床单吹成一面白墙。陈默（四十岁上下，沉默，自称修缮工人）蹲在排水沟边，"
            "手套上沾着铁锈。他听见有人走近，没有抬头。\n\n"
            "苏晴\n陈师傅，后院水管是你修的？\n\n"
            "陈默\n是。\n\n"
            "苏晴\n三零二的墙里有没有空管？我夜里听见流水声。\n\n"
            "陈默愣了一下，终于抬眼。\n\n"
            "陈默\n旧楼都这样。别自己拆。"
        ),
    },
    {
        "case_id": "boundary_suheng_mentioned",
        "mention": "苏衡",
        "expected": "边界：仅被提到的亡父名字，倾向 false",
        "text": (
            "苏晴\n我爸以前也住过这栋楼。苏衡。\n\n"
            "陈默的手套停在半空，又重新握住扳手。\n\n"
            "陈默\n不认识。"
        ),
    },
    {
        "case_id": "pos_dialogue_liuzheng",
        "mention": "刘正",
        "expected": "true / 高置信度（有对白与动作）",
        "text": (
            "站长刘正（五十岁，严厉）把考勤表拍在桌上。\n\n"
            "刘正\n顾晚，你请假去查私人的事，邮局不是你家祠堂。\n\n"
            "顾晚\n刘站长，第七格——\n\n"
            "刘正\n第七格封存。上面有令。你再问，夜班调走。"
        ),
    },
]


def build_prompt(text: str, mention: str) -> str:
    return (
        f"{SYSTEM_RULES}\n\n"
        f"疑似人名：{mention}\n\n"
        f"剧本片段：\n---\n{text}\n---\n\n"
        "请只返回 JSON。"
    )


def parse_judgment(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("judgment is not an object")
    return {
        "is_character": bool(payload.get("is_character")),
        "confidence": float(payload.get("confidence") if payload.get("confidence") is not None else 0.0),
        "reason": str(payload.get("reason") or "").strip(),
        "raw_text": raw_text,
    }


def judge_one(
    *,
    text: str,
    mention: str,
    service_id: str,
    output_dir: Path,
    timeout_sec: float,
) -> dict[str, Any]:
    registry = load_provider_registry()
    prompt = build_prompt(text, mention)
    started = time.perf_counter()
    result = registry.dispatch(
        "llm",
        service_id,
        ProviderDispatchRequest(
            prompt=prompt,
            output_dir=output_dir,
            task_type="m3_1_structured_json",
            timeout_sec=timeout_sec,
        ),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    raw_text = str(result.get("text") or "")
    judgment = parse_judgment(raw_text)
    return {
        "latency_ms": latency_ms,
        "provider_calls_started": bool(result.get("provider_calls_started")),
        "judgment": judgment,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indirect-mention LLM judgment prototype (read-only).")
    parser.add_argument("--case-id", action="append", default=[], help="Run only these case_ids (repeatable).")
    parser.add_argument("--service-id", default=DEFAULT_SERVICE_ID)
    parser.add_argument("--provider-config", default=os.environ.get("AFS_PROVIDER_CONFIG", DEFAULT_PROVIDER_CONFIG))
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "docs/internal-notes/indirect-mention-llm-prototype-20260805.json"),
    )
    args = parser.parse_args(argv)

    os.environ["AFS_PROVIDER_CONFIG"] = str(Path(args.provider_config).resolve())
    os.environ.setdefault("AFS_ALLOW_REMOTE_LLM", "true")
    if os.environ.get("AFS_ALLOW_REMOTE_LLM", "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("AFS_ALLOW_REMOTE_LLM must be true", file=sys.stderr)
        return 2

    selected = CASES
    if args.case_id:
        wanted = set(args.case_id)
        selected = [c for c in CASES if c["case_id"] in wanted]
        missing = wanted - {c["case_id"] for c in selected}
        if missing:
            print(f"unknown case_id: {sorted(missing)}", file=sys.stderr)
            return 2

    report: dict[str, Any] = {
        "schema_version": "afs.indirect_mention_llm_prototype.v0.1",
        "authority": "non_authoritative_prototype_only",
        "writes_candidates": False,
        "provider_config": os.environ["AFS_PROVIDER_CONFIG"],
        "service_id": args.service_id,
        "started_at_unix": time.time(),
        "cases": [],
    }
    wall_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="afs-indirect-mention-proto-") as tmp:
        out_root = Path(tmp)
        for index, case in enumerate(selected, start=1):
            case_dir = out_root / case["case_id"]
            case_dir.mkdir(parents=True, exist_ok=True)
            print(f"[{index}/{len(selected)}] calling {case['case_id']} mention={case['mention']}", flush=True)
            try:
                result = judge_one(
                    text=case["text"],
                    mention=case["mention"],
                    service_id=args.service_id,
                    output_dir=case_dir,
                    timeout_sec=args.timeout_sec,
                )
                entry = {
                    "case_id": case["case_id"],
                    "mention": case["mention"],
                    "expected": case["expected"],
                    "input_text": case["text"],
                    "status": "ok",
                    **result,
                }
            except Exception as exc:  # noqa: BLE001 - prototype must record real failures
                entry = {
                    "case_id": case["case_id"],
                    "mention": case["mention"],
                    "expected": case["expected"],
                    "input_text": case["text"],
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:400],
                }
            report["cases"].append(entry)
            print(json.dumps(entry, ensure_ascii=False, indent=2), flush=True)

    report["finished_at_unix"] = time.time()
    report["wall_time_sec"] = round(time.perf_counter() - wall_started, 2)
    report["call_count"] = len(report["cases"])
    report["ok_count"] = sum(1 for c in report["cases"] if c.get("status") == "ok")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={report_path}", flush=True)
    return 0 if report["ok_count"] == report["call_count"] else 3


__all__ = (
    "CASES",
    "DEFAULT_PROVIDER_CONFIG",
    "DEFAULT_SERVICE_ID",
    "SYSTEM_RULES",
    "build_prompt",
    "judge_one",
    "parse_judgment",
)


if __name__ == "__main__":
    raise SystemExit(main())
