from __future__ import annotations

import json
import re
from typing import Any


class MockLLMProvider:
    """Deterministic local provider for Phase 2 ROI pipeline development."""

    def generate(self, prompt: str, *, task_type: str | None = None) -> str:
        if task_type == "hook_analysis":
            return json.dumps(self._hooks(), ensure_ascii=False)
        if task_type == "short_video_script":
            return json.dumps(self._scripts(prompt), ensure_ascii=False)
        raise ValueError(f"Unsupported mock task_type: {task_type}")

    def _hooks(self) -> list[dict[str, Any]]:
        return [
            {
                "hook_id": "hook_mock_001",
                "project_id": "proj_mock",
                "hook_type": "身份反转",
                "emotion_tags": ["委屈", "反击", "爽感"],
                "plot_summary": "女主被众人误会成骗子，关键证据出现后身份当场反转。",
                "core_conflict": "所有人都在否定她，真正的权威却站出来为她证明。",
                "user_trigger": "被误解后的当众打脸",
                "recommended_opening": "所有人都说她在骗人，下一秒真正的证明来了。",
                "recommended_ending": "可她真正隐藏的身份，还没有完全揭开。",
                "title_candidates": [
                    "她被全场嘲笑，下一秒身份反转",
                    "众人都说她输了，可证据刚刚开始出现",
                ],
                "risk_tags": ["夸张表达"],
                "score": 0.88,
            },
            {
                "hook_id": "hook_mock_002",
                "project_id": "proj_mock",
                "hook_type": "情绪压迫",
                "emotion_tags": ["委屈", "紧张", "期待"],
                "plot_summary": "女主被迫承认莫须有的错误，却在最后一刻拿出关键线索。",
                "core_conflict": "弱势角色被集体逼迫，但她掌握了改变局面的信息。",
                "user_trigger": "压迫感后的翻盘期待",
                "recommended_opening": "她明明什么都没做，却被逼着当众认错。",
                "recommended_ending": "她抬头说出一句话，全场突然安静了。",
                "title_candidates": [
                    "她被逼到绝境，只用一句话让全场闭嘴",
                    "所有人都在等她认错，她却拿出了证据",
                ],
                "risk_tags": [],
                "score": 0.82,
            },
            {
                "hook_id": "hook_mock_003",
                "project_id": "proj_mock",
                "hook_type": "悬念揭示",
                "emotion_tags": ["好奇", "反转", "期待"],
                "plot_summary": "一封旧信揭开多年误会，也指向更大的幕后人物。",
                "core_conflict": "表面冲突解决后，新的隐藏矛盾浮出水面。",
                "user_trigger": "旧秘密引出新悬念",
                "recommended_opening": "那封被藏了三年的信，终于被她打开。",
                "recommended_ending": "信里最后一个名字，让她彻底愣住了。",
                "title_candidates": [
                    "她打开一封旧信，发现真相不是她想的那样",
                    "三年前的误会被揭开，幕后人却另有其人",
                ],
                "risk_tags": [],
                "score": 0.78,
            },
        ]

    def _scripts(self, prompt: str) -> list[dict[str, Any]]:
        hooks = self._extract_hooks(prompt) or self._hooks()[:1]
        scripts: list[dict[str, Any]] = []
        for index, hook in enumerate(hooks, start=1):
            hook_id = str(hook.get("hook_id", f"hook_mock_{index:03d}"))
            project_id = str(hook.get("project_id", "proj_mock"))
            opening = str(hook.get("recommended_opening", "她以为一切都结束了。"))
            title_candidates = hook.get("title_candidates") or []
            title = title_candidates[0] if title_candidates else f"第{index}个反转正在发生"
            scripts.append(
                {
                    "script_id": f"script_mock_{index:03d}",
                    "project_id": project_id,
                    "hook_id": hook_id,
                    "platform": "douyin",
                    "target_duration_sec": 60,
                    "style": "suspense_hook",
                    "title": title,
                    "cover_text": str(hook.get("hook_type", "剧情反转")),
                    "opening_3s": opening,
                    "segments": [
                        {
                            "segment_type": "opening",
                            "text": opening,
                            "duration_sec": 3,
                        },
                        {
                            "segment_type": "body",
                            "text": str(hook.get("plot_summary", "剧情继续推进。")),
                            "duration_sec": 42,
                        },
                        {
                            "segment_type": "climax",
                            "text": str(hook.get("recommended_ending", "真正的反转才刚开始。")),
                            "duration_sec": 10,
                        },
                    ],
                    "cta": "想知道后面怎么反转，继续看完整剧情。",
                    "risk_tags": hook.get("risk_tags", []),
                    "score": min(float(hook.get("score", 0.75)) + 0.02, 1.0),
                }
            )
        return scripts

    def _extract_hooks(self, prompt: str) -> list[dict[str, Any]]:
        match = re.search(r"HOOKS_JSON_START\s*(.*?)\s*HOOKS_JSON_END", prompt, re.S)
        if not match:
            return []
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        return payload if isinstance(payload, list) else []
