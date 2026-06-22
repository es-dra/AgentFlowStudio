from __future__ import annotations

import re
from typing import Any


ASSET_RE = re.compile(r"@([A-Za-z0-9_\-\u4e00-\u9fff·]+)")
SCENE_HINTS = ("主要场景", "场景", "办公室", "房间", "街道", "屋顶", "楼顶", "天台", "城市", "天际线", "森林", "海边", "山谷", "餐厅", "车内", "走廊", "宫殿", "庭院", "广场", "屏幕")
CHARACTER_HINTS = ("主角", "角色", "人物", "女孩", "男孩", "女人", "男人", "老人", "孩子", "机器人", "队长", "老师", "学生")
PROP_HINTS = ("手机", "电脑", "键盘", "刀", "剑", "车辆", "汽车", "信件", "信封", "信纸", "照片", "路灯", "台灯", "灯具", "灯柱", "书", "门", "地图")
GENERIC_CHARACTER_LABELS = {"主角", "角色", "人物"}
GENERIC_SCENE_LABELS = {"主要场景", "场景"}


def local_storyboard_shots(script_text: str, shot_count_hint: int | None = None) -> list[dict[str, Any]]:
    chunks = _script_chunks(script_text, shot_count_hint=shot_count_hint)
    return [structured_shot(chunk, index + 1) for index, chunk in enumerate(chunks[:80])]


def structured_shot(text: str, index: int) -> dict[str, Any]:
    source = _clean(text)
    refs = _asset_refs(source)
    return {
        "shot_id": f"shot_{index:02d}",
        "index": index,
        "duration": _duration(source),
        "description": _description_with_assets(source, refs),
        "shot_size": _shot_size(source),
        "light_atmosphere": _lighting(source),
        "camera_motion": _camera_motion(source),
        "dialogue": _dialogue(source),
        "sound": _sound(source),
        "asset_refs": refs,
        "source_text": source,
    }


def normalize_asset_ref(asset: Any, index: int, context: str = "") -> dict[str, str]:
    if not isinstance(asset, dict):
        return {}
    label = str(asset.get("label") or asset.get("name") or "").strip()[:24]
    asset_type = str(asset.get("asset_type") or "character")
    if asset_type not in {"character", "scene", "prop"}:
        asset_type = "character"
    if not label:
        return {}
    label = _semantic_asset_label(label, asset_type, context)
    return {
        "label": label,
        "asset_id": str(asset.get("asset_id") or f"candidate:{asset_type}:{index + 1}"),
        "asset_type": asset_type,
        "status": str(asset.get("status") or "candidate"),
        "source": str(asset.get("source") or "llm"),
    }


def _script_chunks(text: str, shot_count_hint: int | None = None) -> list[str]:
    source = str(text or "").strip()
    if not source:
        return []
    paragraphs = [_clean(part) for part in re.split(r"\n\s*\n", source) if _clean(part)]
    if len(paragraphs) > 1:
        units = paragraphs
    else:
        units = [_clean(part) for part in re.split(r"(?<=[。！？!?；;])\s*", source) if _clean(part)]
        if not units:
            return [source]
    target_count = _target_shot_count(units, source, shot_count_hint)
    return _balanced_chunks(units, target_count)


def _target_shot_count(units: list[str], source: str, shot_count_hint: int | None = None) -> int:
    if not units:
        return 0
    if shot_count_hint:
        return max(1, min(int(shot_count_hint), len(units), 80))
    by_units = (len(units) + 1) // 2
    by_length = max(1, (len(source) + 179) // 180)
    return max(1, min(max(by_units, by_length), len(units), 12))


def _balanced_chunks(units: list[str], target_count: int) -> list[str]:
    if target_count <= 0:
        return []
    if target_count >= len(units):
        return units
    chunks: list[str] = []
    for index in range(target_count):
        start = round(index * len(units) / target_count)
        end = round((index + 1) * len(units) / target_count)
        chunk = "".join(units[start:end]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _asset_refs(text: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for match in ASSET_RE.finditer(text):
        _push_ref(refs, match.group(1), _classify_asset(match.group(1), text), "explicit", text)
    if not any(ref["asset_type"] == "character" for ref in refs) and any(hint in text for hint in CHARACTER_HINTS):
        _push_ref(refs, _infer_character_label(text) or "主角", "character", "candidate", text)
    if not any(ref["asset_type"] == "scene" for ref in refs) and any(hint in text for hint in SCENE_HINTS):
        _push_ref(refs, _infer_scene_label(text) or "主要场景", "scene", "candidate", text)
    if not any(ref["asset_type"] == "prop" for ref in refs):
        prop = next((hint for hint in PROP_HINTS if hint in text), "")
        if prop:
            _push_ref(refs, prop, "prop", "candidate", text)
    if not refs:
        _push_ref(refs, _infer_character_label(text) or "主角", "character", "candidate", text)
        _push_ref(refs, _infer_scene_label(text) or "主要场景", "scene", "candidate", text)
    return refs


def _push_ref(refs: list[dict[str, str]], label: str, asset_type: str, source: str, context: str = "") -> None:
    clean = _semantic_asset_label(label, asset_type, context)
    if not clean or any(ref["label"] == clean for ref in refs):
        return
    refs.append(
        {
            "label": clean,
            "asset_id": f"candidate:{asset_type}:{_indexable_slug(clean)}",
            "asset_type": asset_type,
            "status": "mentioned" if source == "explicit" else "candidate",
            "source": source,
        }
    )


def _description_with_assets(source: str, refs: list[dict[str, str]]) -> str:
    visible_source = _replace_generic_asset_tokens(source, refs)
    missing = [ref for ref in refs if f"@{ref['label']}" not in visible_source]
    prefix = " ".join(f"@{ref['label']}" for ref in missing)
    return f"{prefix}。{visible_source}" if prefix else visible_source


def _replace_generic_asset_tokens(source: str, refs: list[dict[str, str]]) -> str:
    text = str(source or "")
    character = next((ref for ref in refs if ref["asset_type"] == "character" and ref["label"] not in GENERIC_CHARACTER_LABELS), None)
    scene = next((ref for ref in refs if ref["asset_type"] == "scene" and ref["label"] not in GENERIC_SCENE_LABELS), None)
    if character:
        for label in GENERIC_CHARACTER_LABELS:
            text = text.replace(f"@{label}", f"@{character['label']}")
    if scene:
        for label in GENERIC_SCENE_LABELS:
            text = text.replace(f"@{label}", f"@{scene['label']}")
    return text


def _semantic_asset_label(label: str, asset_type: str, context: str) -> str:
    clean = re.sub(r"[，。；:：,.!?！？]+$", "", str(label or "")).strip()[:24]
    if asset_type == "character" and clean in GENERIC_CHARACTER_LABELS:
        return _infer_character_label(context) or clean
    if asset_type == "scene" and clean in GENERIC_SCENE_LABELS:
        return _infer_scene_label(context) or clean
    return clean


def _infer_character_label(text: str) -> str:
    source = str(text or "")
    if re.search(r"未来.*机器人|机器人.*未来", source):
        return "未来机器人"
    if re.search(r"机器人|机械人|仿生人", source):
        return "机器人"
    if re.search(r"女孩|少女", source):
        return "女孩"
    if re.search(r"男孩|少年", source):
        return "男孩"
    if "老人" in source:
        return "老人"
    if "孩子" in source:
        return "孩子"
    return ""


def _infer_scene_label(text: str) -> str:
    source = str(text or "")
    is_night = bool(re.search(r"夜|星空|月光|霓虹|灯火", source))
    is_city = bool(re.search(r"城市|高楼|天际线|霓虹|楼宇", source))
    is_rooftop = bool(re.search(r"屋顶|楼顶|天台", source))
    if is_night and is_city and is_rooftop:
        return "夜晚城市屋顶"
    if is_city and is_rooftop:
        return "城市屋顶"
    if is_night and is_city:
        return "夜晚城市"
    if is_rooftop:
        return "屋顶平台"
    if is_city:
        return "城市场景"
    return ""


def _duration(text: str) -> str:
    match = re.search(r"(\d{1,2})\s*(?:s|秒)", text, flags=re.I)
    if match:
        return f"{match.group(1)}s"
    if len(text) > 130:
        return "8s"
    if len(text) > 70:
        return "6s"
    return "5s"


def _shot_size(text: str) -> str:
    if re.search(r"大远景|远景|全貌|城市|山谷|天空", text):
        return "远景"
    if re.search(r"全景|全身|环境", text):
        return "全景"
    if re.search(r"近景|脸|眼神|表情", text):
        return "近景"
    if re.search(r"特写|手指|瞳孔|细节|屏幕|地图", text):
        return "特写"
    if re.search(r"半身|肩", text):
        return "半身景"
    return "中景"


def _lighting(text: str) -> str:
    if re.search(r"夜|霓虹|暗|阴影", text):
        return "低照度，冷色阴影压低环境"
    if re.search(r"晨|清晨|阳光|明亮", text):
        return "自然主光，明亮通透"
    if re.search(r"雨|雾|烟|尘", text):
        return "柔散光，空气颗粒增强层次"
    if re.search(r"紧张|压迫|冲突", text):
        return "高反差侧光，氛围紧张"
    return "自然光影，氛围服务情绪推进"


def _camera_motion(text: str) -> str:
    if re.search(r"推近|逼近|靠近", text):
        return "缓慢推近"
    if re.search(r"拉远|退后", text):
        return "缓慢拉远"
    if re.search(r"跟随|追|奔跑", text):
        return "跟拍移动"
    if re.search(r"摇|环绕", text):
        return "轻微摇移"
    if re.search(r"切|闪回|突然", text):
        return "快速切入"
    return "固定机位，轻微呼吸感"


def _dialogue(text: str) -> str:
    quote = re.search(r"[“\"](.*?)[”\"]", text)
    if quote:
        return quote.group(1)[:80]
    line = re.search(r"(?:对白|旁白|台词)\s*[:：]\s*(.+)$", text)
    return line.group(1)[:80] if line else "无明确对白"


def _sound(text: str) -> str:
    if re.search(r"键盘|电脑|屏幕|地图", text):
        return "设备低频与电子提示音"
    if re.search(r"雨|海|风", text):
        return "环境自然声持续铺底"
    if re.search(r"冲突|奔跑|撞|爆", text):
        return "急促动作音与低频冲击"
    return "环境底噪，动作音随画面同步"


def _classify_asset(label: str, context: str) -> str:
    if any(hint in label or f"{label}里" in context or f"{label}中" in context for hint in SCENE_HINTS):
        return "scene"
    if label == "灯":
        return "prop" if re.search(r"@灯|路灯|台灯|灯具|灯柱|灯盏", context) else "scene"
    if label == "信":
        return "prop" if re.search(r"@信|信件|信封|信纸|一封信|书信", context) else "character"
    if any(hint in label for hint in PROP_HINTS):
        return "prop"
    return "character"


def _indexable_slug(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower()[:32] or "asset"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


__all__ = ("local_storyboard_shots", "normalize_asset_ref", "structured_shot")
