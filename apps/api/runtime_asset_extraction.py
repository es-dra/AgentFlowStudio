from __future__ import annotations

import re
from typing import Any


ASSET_TYPES = {"character", "scene", "prop"}
CHARACTER_SUBTYPES = {"human", "animal", "robot", "subject"}
GENERIC_CHARACTER_LABELS = {"人", "人物", "主角", "角色", "主体"}
GENERIC_SCENE_LABELS = {"场景", "主要场景"}
PRONOUN_LABELS = {"他", "她", "它", "他们", "她们", "ta", "they", "he", "she"}
ANIMAL_REFERENCE_TERMS = (
    "拉布拉多",
    "金毛",
    "边牧",
    "柯基",
    "哈士奇",
    "柴犬",
    "奶狗",
    "幼犬",
    "小狗",
    "狗狗",
    "橘猫",
    "狸花猫",
    "黑猫",
    "白猫",
    "小猫",
    "猫咪",
    "猫",
    "狗",
    "犬",
    "cat",
    "dog",
    "puppy",
    "kitten",
    "animal",
    "pet",
)
HUMAN_REFERENCE_TERMS = (
    "高中生",
    "学生",
    "女孩",
    "女生",
    "少女",
    "男孩",
    "少年",
    "女人",
    "男人",
    "老师",
    "person",
    "human",
    "girl",
    "boy",
    "woman",
    "man",
)
ROBOT_REFERENCE_TERMS = ("机器人", "机械人", "仿生人", "机甲", "robot", "android", "mecha")
PROP_REFERENCE_TERMS = (
    "荧光绿网球",
    "网球",
    "红绳",
    "牵引绳",
    "狗绳",
    "项圈",
    "断绳",
    "断戟",
    "青铜虎符",
    "虎符",
    "竹简",
    "军旗",
    "残旗",
    "旧军籍册",
    "军籍册",
    "试卷",
    "草稿纸",
    "寻狗启事",
    "启事",
    "手机",
    "地图",
    "钥匙",
    "信件",
    "信封",
    "照片",
    "金箍棒",
    "钢爪",
    "刀",
    "剑",
    "棍",
    "棒",
    "武器",
)
GENERIC_PROP_NOUN_TERMS = (
    "数学试卷",
    "试卷",
    "草稿纸",
    "启事",
    "寻狗启事",
    "照片",
    "信件",
    "信封",
    "手机",
    "钥匙",
    "地图",
    "竹简",
    "虎符",
    "军旗",
    "残旗",
    "断戟",
    "剑",
    "刀",
    "棍",
    "棒",
    "网球",
    "红绳",
    "牵引绳",
    "狗绳",
    "项圈",
    "断绳",
)
CRITICAL_PROP_ACTION_TERMS = (
    "手持",
    "死攥",
    "攥",
    "握",
    "拿",
    "捧",
    "叼",
    "吐",
    "拾起",
    "塞进",
    "夺过",
    "抢回",
    "翻转",
    "展开",
    "露出",
    "照亮",
    "反射",
    "检查",
    "查看",
    "写着",
    "批注",
    "锁定",
    "递",
    "递给",
    "交给",
    "交还",
    "推向",
    "holds",
    "holding",
    "carries",
    "carrying",
    "hands",
    "passes",
)
CRITICAL_PROP_LABEL_TERMS = (
    "断戟",
    "青铜虎符",
    "虎符",
    "竹简",
    "军旗",
    "残旗",
    "旧军籍册",
    "军籍册",
    "金箍棒",
    "钢爪",
    "荧光绿网球",
    "网球",
    "红绳",
    "牵引绳",
    "狗绳",
    "寻狗启事",
    "启事",
    "地图",
)
ACTION_FRAGMENT_LABEL_TERMS = (
    "挣脱",
    "转身",
    "轻巧",
    "跃下",
    "落地",
    "掏出",
    "本能",
    "悬停",
    "低头",
    "抬头",
    "回头",
    "侧身",
    "伸手",
    "抬手",
)
BODY_PART_LABEL_TERMS = (
    "右眼",
    "左眼",
    "瞳孔",
    "眼睛",
    "指尖",
    "手指",
    "指节",
    "爪子",
    "耳朵",
    "鼻尖",
    "鼻头",
    "肩",
    "手腕",
)

AUDIO_ONLY_TERMS = (
    "城市噪音",
    "城市环境底噪",
    "环境底噪",
    "底噪",
    "噪音",
    "环境音",
    "ambience",
    "ambient",
    "city noise",
    "distant city noise",
    "audio",
    "sound",
    "black screen",
)
CITY_TERMS = ("城市", "city", "街道", "street", "road")
KNOWN_CHARACTER_NAMES = ("唐僧", "白骨精", "孙悟空", "猪八戒", "沙僧", "金刚狼", "林晚")
VISUAL_CITY_TERMS = (
    "rain-night city street",
    "city street",
    "skyline",
    "building",
    "buildings",
    "neon",
    "wet road",
    "visible lights",
    "rooftop",
    "雨夜",
    "街道",
    "屋顶",
    "天际线",
    "建筑",
    "高楼",
    "霓虹",
    "湿路",
    "路面",
    "灯光",
)
VISUAL_CHARACTER_TERMS = (
    "walks",
    "runs",
    "face",
    "coat",
    "hand",
    "under the visible lights",
    "站",
    "走",
    "奔跑",
    "穿",
    "低头",
    "手部",
    "展开",
    "外套",
    "侧脸",
    "女孩",
    "林晚",
    "机器人",
    "唐僧",
    "白骨精",
    "孙悟空",
    "猪八戒",
)


def normalize_asset_refs_with_diagnostics(
    asset_refs: list[Any],
    *,
    context: str = "",
    include_inferred: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = [item for item in asset_refs if isinstance(item, dict)]
    if include_inferred:
        candidates = [*candidates, *_inferred_asset_refs(context)]

    accepted_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    accepted_order: list[tuple[str, str]] = []
    diagnostics: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        normalized, diagnostic = normalize_asset_ref_for_contract(candidate, index, context=context)
        if normalized:
            key = (normalized["asset_type"], normalized["display_name"])
            current = accepted_by_key.get(key)
            if current is None:
                accepted_by_key[key] = normalized
                accepted_order.append(key)
            elif _asset_ref_authority(normalized) > _asset_ref_authority(current) or (
                _asset_ref_authority(normalized) == _asset_ref_authority(current)
                and float(normalized.get("confidence") or 0.0) > float(current.get("confidence") or 0.0)
            ):
                accepted_by_key[key] = normalized
        elif diagnostic:
            diagnostic_key = (diagnostic["asset_type"], diagnostic["display_name"], diagnostic["reason"])
            if diagnostic_key not in {(item["asset_type"], item["display_name"], item["reason"]) for item in diagnostics}:
                diagnostics.append(diagnostic)
    return _drop_subsumed_asset_refs([accepted_by_key[key] for key in accepted_order]), diagnostics


def principal_asset_refs_with_diagnostics(
    asset_refs: list[dict[str, Any]],
    dropped_refs: list[dict[str, Any]] | None = None,
    *,
    max_auto_characters: int = 2,
    max_auto_scenes: int = 1,
    max_auto_props: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = list(dropped_refs or [])
    auto_character_count = 0
    auto_scene_count = 0
    auto_prop_count = 0
    for ref in asset_refs:
        asset_type = str(ref.get("asset_type") or "")
        if _is_manual_or_fixed_asset_ref(ref):
            accepted.append(ref)
            continue
        explicit_named = _is_explicit_named_asset_ref(ref)
        if asset_type == "prop":
            evidence = _critical_prop_evidence(ref)
            if evidence and auto_prop_count < max_auto_props:
                accepted.append(
                    {
                        **ref,
                        "status": str(ref.get("status") or "prop_relevant"),
                        "critical_prop_evidence": evidence,
                    }
                )
                auto_prop_count += 1
            else:
                diagnostics.append(_principal_diagnostic(ref, "prop_requires_critical_evidence_or_manual_asset_entry"))
            continue
        if asset_type == "character":
            if explicit_named or auto_character_count < max_auto_characters:
                accepted.append(ref)
                if not explicit_named:
                    auto_character_count += 1
            else:
                diagnostics.append(_principal_diagnostic(ref, "secondary_character_requires_manual_asset_entry"))
            continue
        if asset_type == "scene":
            if explicit_named or auto_scene_count < max_auto_scenes:
                accepted.append(ref)
                if not explicit_named:
                    auto_scene_count += 1
            else:
                diagnostics.append(_principal_diagnostic(ref, "secondary_scene_requires_manual_asset_entry"))
            continue
        diagnostics.append(_principal_diagnostic(ref, "unsupported_asset_type_requires_manual_entry"))
    return accepted, diagnostics


def normalize_asset_ref_for_contract(
    asset: dict[str, Any],
    index: int,
    *,
    context: str = "",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    asset_type = _asset_type(asset.get("asset_type"))
    raw_label = _clean_label(asset.get("display_name") or asset.get("label") or asset.get("name") or "")
    if not raw_label:
        return None, None

    evidence = _clean_text(asset.get("evidence_text") or asset.get("visual_evidence_span") or context)
    context_text = _clean_text(context or evidence)
    display_name = raw_label
    provisional_name = bool(asset.get("provisional_name"))
    name_source = str(asset.get("name_source") or asset.get("source") or "candidate")

    if asset_type == "character" and _looks_like_prop_reference(raw_label, evidence, context_text):
        asset_type = "prop"
        display_name = _clean_prop_label(raw_label) or raw_label
    elif asset_type == "prop" and _looks_like_prop_phrase_label(display_name):
        display_name = _clean_prop_label(display_name) or display_name

    if asset_type == "scene" and _is_audio_only_city_reference(raw_label, evidence, context_text):
        return None, _diagnostic(raw_label, asset_type, "audio_only_non_visual_city_reference", evidence or context_text)

    if asset_type == "character" and raw_label in PRONOUN_LABELS:
        return None, _diagnostic(raw_label, asset_type, "ambiguous_alias_not_auto_merged", evidence or context_text)

    if asset_type == "character" and _looks_like_action_fragment_label(raw_label):
        return None, _diagnostic(raw_label, asset_type, "action_fragment_not_asset", evidence or context_text)

    if asset_type == "character" and raw_label in GENERIC_CHARACTER_LABELS:
        provisional = _provisional_character_name(context_text)
        if not provisional:
            return None, _diagnostic(raw_label, asset_type, "unresolved_generic_character", evidence or context_text)
        display_name = provisional
        provisional_name = True
        name_source = "visual_context_provisional"

    if asset_type == "scene" and raw_label in GENERIC_SCENE_LABELS:
        scene_name = _visual_scene_name(context_text)
        if not scene_name:
            return None, _diagnostic(raw_label, asset_type, "unresolved_generic_scene", evidence or context_text)
        display_name = scene_name
        provisional_name = True
        name_source = "visual_context_provisional"
    elif asset_type == "scene":
        scene_name = _stable_scene_entity_name(raw_label, context_text)
        if scene_name:
            display_name = scene_name
            name_source = "stable_scene_entity"

    visual_span = _visual_evidence_span(context_text, evidence, display_name, asset_type)
    if asset_type == "scene" and _has_audio_only_terms(evidence or context_text) and not visual_span:
        return None, _diagnostic(raw_label, asset_type, "audio_only_non_visual_reference", evidence or context_text)
    if not visual_span and asset_type == "scene":
        visual_span = (evidence or context_text)[:240]
    evidence_modality = "visual"

    normalized = {
        "label": display_name,
        "display_name": display_name,
        "asset_id": str(asset.get("asset_id") or f"candidate:{asset_type}:{_slug(display_name)}"),
        "graph_asset_id": str(asset.get("graph_asset_id") or asset.get("graphAssetId") or ""),
        "asset_type": asset_type,
        "status": str(asset.get("status") or "candidate"),
        "source": str(asset.get("source") or "candidate"),
        "scope": str(asset.get("scope") or "shot_tree"),
        "confidence": _confidence(asset.get("confidence"), provisional_name=provisional_name),
        "evidence_text": (visual_span or evidence or context_text)[:240],
        "descriptive_signature": _descriptive_signature(asset, visual_span or evidence or context_text),
        "evidence_modality": evidence_modality,
        "visual_evidence_span": visual_span,
        "modality_gate_status": "accepted",
        "name_source": name_source,
        "provisional_name": provisional_name,
    }
    character_subtype = _character_subtype(asset.get("character_subtype"))
    if asset_type == "character" and not character_subtype:
        character_subtype = _inferred_character_subtype(display_name, evidence or context_text)
    if asset_type == "character" and character_subtype:
        normalized["character_subtype"] = character_subtype
    if asset_type == "prop":
        evidence_kinds = _critical_prop_evidence(normalized)
        if evidence_kinds:
            normalized["critical_prop_evidence"] = evidence_kinds
    return normalized, None


def _inferred_asset_refs(context: str) -> list[dict[str, Any]]:
    text = _clean_text(context)
    refs: list[dict[str, Any]] = []
    for name in _named_characters(text):
        refs.append({"label": name, "asset_type": "character", "source": "candidate", "evidence_text": text})
    for name in _named_animal_characters(text):
        refs.append(
            {
                "label": name,
                "asset_type": "character",
                "character_subtype": "animal",
                "source": "grounded_mention",
                "evidence_text": text,
            }
        )
    scene_name = _visual_scene_name(text)
    if scene_name:
        refs.append({"label": scene_name, "asset_type": "scene", "source": "candidate", "evidence_text": text})
    for name in _visual_prop_names(text):
        refs.append(
            {
                "label": name,
                "asset_type": "prop",
                "status": "prop_relevant",
                "source": "grounded_mention",
                "evidence_text": text,
            }
        )
    return _drop_subsumed_asset_refs(refs)


def _specific_asset_types(candidates: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for item in candidates:
        asset_type = _asset_type(item.get("asset_type"))
        label = _clean_label(item.get("display_name") or item.get("label") or item.get("name") or "")
        if label and label not in GENERIC_CHARACTER_LABELS and label not in GENERIC_SCENE_LABELS and label not in PRONOUN_LABELS:
            result.add(asset_type)
    return result


def _named_characters(text: str) -> list[str]:
    names: list[str] = []
    for left, right in re.findall(
        r"([\u4e00-\u9fffA-Za-z0-9·]{2,12})(?:大战|对决|迎娶|娶了|娶|嫁给|爱上|遇见|面对|追击|追杀|营救|守护)([\u4e00-\u9fffA-Za-z0-9·]{2,12})",
        text,
    ):
        names.extend([_trim_character_name(left), _trim_character_name(right)])
    names.extend(_known_characters_in_source_order(text))
    if re.search(r"\bLin\s+Wan\b", text, flags=re.I):
        names.append("Lin Wan")
    if "女孩" in text:
        names.append("女孩")
    if "机器人" in text:
        names.append("机器人")
    if re.search(r"\bfuture robot\b|\brobot\b", text, flags=re.I):
        names.append("Future Robot")
    return _dedupe([name for name in names if name])


def _known_characters_in_source_order(text: str) -> list[str]:
    return [
        name
        for name, _index in sorted(
            ((name, text.find(name)) for name in KNOWN_CHARACTER_NAMES if text.find(name) >= 0),
            key=lambda item: item[1],
        )
    ]


def _named_animal_characters(text: str) -> list[str]:
    source = str(text or "")
    names: list[str] = []
    animal_pattern = "|".join(re.escape(term) for term in sorted(ANIMAL_REFERENCE_TERMS, key=len, reverse=True))
    names.extend(
        match.group(1)
        for match in re.finditer(
            rf"(?:{animal_pattern})[“\"']([\u4e00-\u9fffA-Za-z0-9·]{{1,8}})[”\"']",
            source,
            flags=re.I,
        )
    )
    breed_pattern = re.compile(
        r"((?:黑色|白色|灰色|棕色|黄色|金色|橘色|灰白相间|黑白相间)?(?:拉布拉多|金毛|边牧|柯基|哈士奇|柴犬)(?:幼崽|幼犬)?)"
    )
    names.extend(match.group(1) for match in breed_pattern.finditer(source))
    longer_species_present = any(
        term in source
        for term in ("拉布拉多", "金毛", "边牧", "柯基", "哈士奇", "柴犬", "奶狗", "幼犬", "小狗", "橘猫", "狸花猫", "黑猫", "白猫", "小猫")
    )
    for term in ("奶狗", "幼犬", "小狗", "狗狗", "橘猫", "狸花猫", "黑猫", "白猫", "小猫", "猫咪", "猫", "狗", "犬"):
        if term in source and (len(term) > 1 or not longer_species_present):
            names.append(term)
    return _dedupe([name for name in names if name and name not in PRONOUN_LABELS])


def _trim_character_name(value: str) -> str:
    clean = re.sub(r"^(以|把|将|当|用|和|与|及|、)+", "", str(value or "")).strip()
    clean = re.sub(r"^.*(?:是|讲述|关于|围绕)", "", clean).strip()
    clean = re.sub(r"(为核心|为主题|为主|展开|对决|战斗|格斗|碰撞).*$", "", clean).strip()
    clean = re.sub(r"(但是|但|却|旁观|观战|从旁).*$", "", clean).strip()
    return clean[:24]


def _provisional_character_name(text: str) -> str:
    for name in _named_characters(text):
        if name not in {"他", "她", "它"}:
            return name
    lowered = text.lower()
    if any(term in text for term in ("红色外套", "侧脸", "霓虹")):
        return "红色外套人物"
    if "女孩" in text:
        return "女孩"
    if "robot" in lowered or "机器人" in text:
        return "Future Robot" if "robot" in lowered else "机器人"
    if _has_visual_character_context(text):
        return "可见人物"
    return ""


def _visual_scene_name(text: str) -> str:
    if _has_negated_visual_context(text):
        return ""
    lowered = text.lower()
    if "rain-night city street" in lowered:
        return "rain-night city street"
    if "city street" in lowered or ("street" in lowered and "city" in lowered):
        return "city street"
    if "rooftop" in lowered and "city" in lowered:
        return "city rooftop"
    if "雨夜" in text and ("城市" in text or "街道" in text):
        return "雨夜城市街道"
    if "城市" in text and "屋顶" in text:
        return "城市屋顶"
    if "城市" in text and any(term in text for term in ("街道", "天际线", "建筑", "高楼", "霓虹", "湿路", "路面", "灯光")):
        return "城市街道"
    grounded = _grounded_scene_name(text)
    if grounded:
        return grounded
    return ""


def _grounded_scene_name(text: str) -> str:
    source = str(text or "")
    if re.search(r"暗办公室|昏暗办公室", source):
        return "暗办公室"
    if "办公室" in source:
        return "办公室"
    if "餐厅" in source:
        return "餐厅"
    if "厨房" in source:
        return "厨房"
    if "古战场" in source:
        return "古战场"
    if "老城区巷口" in source:
        return "老城区巷口"
    if "斜坡草甸" in source:
        return "斜坡草甸"
    if re.search(r"山巅|山脊|云海", source) and "战场" in source:
        return "山巅石台战场"
    if "战场" in source:
        return "战场"
    patterns = (
        r"([\u4e00-\u9fffA-Za-z0-9·]{0,10}(?:校门口|巷口|窄巷|巷子|公园长椅旁|公园长椅|公园|草甸|草坪|厨房|房间|屋顶|楼顶|天台|城墙|城垛|街道|走廊|宫殿|庭院|广场|餐厅|山洞|洞口|洞内))",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, source):
            label = _clean_scene_label(match.group(1))
            if label:
                return label
    return ""


def _clean_scene_label(value: str) -> str:
    clean = re.sub(
        r"^(?:在|从|向|朝|远处|路对面|空荡|焦黑|破碎|湿漉漉|梧桐树影斑驳的)+",
        "",
        str(value or ""),
    ).strip()
    clean = re.sub(r"^.*(?:站在|坐在|蹲在|躺在|停在|来到|走进|冲向|落在|映着|在)", "", clean).strip()
    clean = re.sub(r"(?:上|里|中|外|内)$", "", clean)
    if clean in GENERIC_SCENE_LABELS or len(clean) < 2:
        return ""
    if clean in {"青石台阶", "青砖", "石台"}:
        return ""
    return clean[:24]


def _stable_scene_entity_name(label: str, context: str) -> str:
    clean = _clean_scene_label(label)
    if clean and clean != label:
        return clean
    return ""


def _visual_prop_names(text: str) -> list[str]:
    source = str(text or "")
    names: list[str] = []
    for term in sorted(PROP_REFERENCE_TERMS, key=len, reverse=True):
        if term and term in source:
            names.append(_clean_prop_label(term))
    noun_pattern = "|".join(re.escape(term) for term in sorted(GENERIC_PROP_NOUN_TERMS, key=len, reverse=True))
    if noun_pattern:
        context_prefix = (
            r"(?:手中|手里|嘴里|怀里|脚边|身旁|面前|指尖|掌心|画面中|镜头中|"
            r"叼着|吐出|吐在|捧着|拿着|握着|攥着|撑着|拾起|翻转|露出|放在|递给|交给|反射|写着|批注)"
        )
        generic_re = re.compile(
            rf"(?:{context_prefix})[^\u3002\uff01\uff1f!?；;]{{0,18}}?((?:[\u4e00-\u9fff]{{0,8}})?(?:{noun_pattern}))"
        )
        names.extend(_clean_prop_label(match.group(1)) for match in generic_re.finditer(source))
        measure_re = re.compile(
            rf"(?:一|半|那|这|其)?(?:个|只|张|卷|枚|截|根|柄|把|块|团)?((?:[\u4e00-\u9fff]{{0,8}})?(?:{noun_pattern}))"
        )
        for match in measure_re.finditer(source):
            window = source[max(0, match.start() - 16) : min(len(source), match.end() + 16)]
            if _contains_any(window, CRITICAL_PROP_ACTION_TERMS) or re.search(r"手中|手里|嘴里|怀里|脚边|面前|画面|镜头", window):
                names.append(_clean_prop_label(match.group(1)))
    return _dedupe_non_overlapping([name for name in names if name])[:4]


def _dedupe_non_overlapping(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in sorted(_dedupe(values), key=len, reverse=True):
        if any(value != other and value in other for other in result):
            continue
        result.append(value)
    return sorted(result, key=lambda item: values.index(item))


def _drop_subsumed_asset_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ref in refs:
        label = str(ref.get("label") or ref.get("display_name") or "").strip()
        asset_type = str(ref.get("asset_type") or "")
        if not label:
            continue
        if _asset_ref_authority(ref) < 40 and any(
            asset_type == str(other.get("asset_type") or "")
            and label != str(other.get("label") or other.get("display_name") or "")
            and label in str(other.get("label") or other.get("display_name") or "")
            and _asset_ref_authority(other) >= _asset_ref_authority(ref)
            for other in refs
        ):
            continue
        result.append(ref)
    return result


def _visual_evidence_span(context: str, evidence: str, display_name: str, asset_type: str) -> str:
    source = _clean_text(context or evidence)
    if not source:
        return ""
    candidates = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", source) if part.strip()]
    candidates = candidates or [source]
    for sentence in candidates:
        if display_name and display_name in sentence:
            return sentence[:240]
    if asset_type == "scene":
        for sentence in candidates:
            if _has_visual_city_context(sentence):
                return sentence[:240]
    if asset_type == "character":
        for sentence in candidates:
            if _has_visual_character_context(sentence):
                return sentence[:240]
    if asset_type == "prop":
        return candidates[0][:240]
    return ""


def _is_audio_only_city_reference(label: str, evidence: str, context: str) -> bool:
    text = f"{label} {evidence} {context}"
    return _has_city_terms(text) and _has_audio_only_terms(text) and not _has_visual_city_context(text)


def _has_city_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered if term.isascii() else term in text for term in CITY_TERMS)


def _has_audio_only_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered if term.isascii() else term in text for term in AUDIO_ONLY_TERMS)


def _has_visual_city_context(text: str) -> bool:
    if _has_negated_visual_context(text):
        return False
    lowered = text.lower()
    return any(term in lowered if term.isascii() else term in text for term in VISUAL_CITY_TERMS)


def _has_visual_character_context(text: str) -> bool:
    if _has_negated_visual_context(text):
        return False
    lowered = text.lower()
    return any(term in lowered if term.isascii() else term in text for term in VISUAL_CHARACTER_TERMS)


def _has_negated_visual_context(text: str) -> bool:
    lowered = text.lower()
    return any(
        term in lowered if term.isascii() else term in text
        for term in (
            "没有可见",
            "不可见",
            "无可见",
            "没有画面",
            "no visible",
            "not visible",
            "black screen",
        )
    )


def _looks_like_prop_reference(label: str, evidence: str, context: str) -> bool:
    text = f"{label} {evidence} {context}".casefold()
    label_text = str(label or "").casefold()
    if _contains_any(label_text, PROP_REFERENCE_TERMS):
        return True
    if label_text in {"球", "ball"} and re.search(r"网球|球面|球体|吐在|叼着|tennis\s+ball", text, flags=re.I):
        return True
    return False


def _looks_like_prop_phrase_label(value: str) -> bool:
    clean = str(value or "").strip()
    if not clean:
        return False
    if re.search(r"^(?:他|她|它|这|那|其|我|你)", clean):
        return True
    return _contains_any(
        clean,
        (
            "掏出",
            "叼着",
            "吐出",
            "吐在",
            "捧着",
            "拿着",
            "握着",
            "攥着",
            "撑着",
            "拾起",
            "翻转",
            "露出",
            "放在",
            "压住",
            "勾着",
        ),
    )


def _looks_like_action_fragment_label(value: str) -> bool:
    clean = str(value or "").strip()
    if not clean:
        return False
    if re.search(r"^(?:他|她|它|这|那|其|我|你)", clean):
        return True
    if _contains_any(clean, ACTION_FRAGMENT_LABEL_TERMS):
        return True
    if _contains_any(clean, BODY_PART_LABEL_TERMS):
        return True
    if _contains_any(clean, PROP_REFERENCE_TERMS):
        return True
    return False


def _clean_prop_label(value: str) -> str:
    clean = re.sub(
        r"^(?:叼着|吐出|吐在|捧着|拿着|握着|攥着|撑着|拾起|翻转|露出|放在|压住|反射|写着|批注|捏着|"
        r"磨损严重的|没吃完的|湿漉漉的|湿透的|褪色的|发光的|发光|半截|半枚|一卷|一张|一只|一柄|一根|一块|一团|那柄|那张|那只|那截|那根|这根|这张|这只)+",
        "",
        str(value or ""),
    ).strip()
    for term in sorted((*CRITICAL_PROP_LABEL_TERMS, *PROP_REFERENCE_TERMS), key=len, reverse=True):
        if term and term in clean:
            return term[:24]
    for term in sorted(GENERIC_PROP_NOUN_TERMS, key=len, reverse=True):
        if term and clean.endswith(term):
            return clean[-min(len(clean), len(term) + 8) :][:24]
    return clean[:24]


def _critical_prop_evidence(ref: dict[str, Any]) -> list[str]:
    label = str(ref.get("display_name") or ref.get("label") or "").strip()
    if not label:
        return []
    evidence = _clean_text(
        " ".join(
            str(ref.get(key) or "")
            for key in (
                "evidence_text",
                "visual_evidence_span",
                "descriptive_signature",
                "source_text",
                "critical_prop_note",
            )
        )
    )
    source = str(ref.get("source") or "").lower()
    status = str(ref.get("status") or "").lower()
    kinds: list[str] = []
    if _is_manual_or_fixed_asset_ref(ref):
        kinds.append("approved_manual_or_fixed_asset")
    if "cross_shot" in source:
        kinds.append("cross_shot_reuse")
    if any(str(ref.get(key) or "").strip() for key in ("keyframe_requirement", "video_motion_requirement", "continuity_need")):
        kinds.append("keyframe_video_continuity_need")
    window = f"{label} {evidence}"
    if label in evidence and _contains_any(window, CRITICAL_PROP_ACTION_TERMS):
        kinds.append("character_possession_or_handoff")
    if label in evidence and (
        _contains_any(label, CRITICAL_PROP_LABEL_TERMS)
        and (
            _contains_any(evidence, ("大战", "对决", "冲突", "横扫", "迎面", "火花", "战场", "照亮", "反射", "写着", "锁定"))
        )
    ):
        kinds.append("plot_function")
    if status in {"prop_relevant", "key_prop"} and label in evidence and _contains_any(evidence, CRITICAL_PROP_ACTION_TERMS):
        kinds.append("plot_function")
    return _dedupe(kinds)


def _inferred_character_subtype(label: str, evidence: str) -> str:
    text = f"{label} {evidence}"
    lowered = text.casefold()
    if _contains_any(lowered, ROBOT_REFERENCE_TERMS):
        return "robot"
    if _contains_any(label, ANIMAL_REFERENCE_TERMS) or _animal_alias_bound_to_label(label, evidence):
        return "animal"
    if _contains_any(text, HUMAN_REFERENCE_TERMS):
        return "human"
    return ""


def _animal_alias_bound_to_label(label: str, evidence: str) -> bool:
    clean = re.escape(str(label or "").strip())
    if not clean:
        return False
    animal_pattern = "|".join(re.escape(term) for term in sorted(ANIMAL_REFERENCE_TERMS, key=len, reverse=True))
    return bool(
        re.search(rf"(?:{animal_pattern})[“\"']{clean}[”\"']", evidence, flags=re.I)
        or re.search(rf"{clean}[^，。；,;\n]{{0,12}}(?:是一只|这只|那只)(?:{animal_pattern})", evidence, flags=re.I)
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = str(text or "").casefold()
    return any(term.casefold() in lowered for term in terms)


def _diagnostic(label: str, asset_type: str, reason: str, evidence: str) -> dict[str, Any]:
    return {
        "label": label,
        "display_name": label,
        "asset_type": asset_type,
        "reason": reason,
        "evidence_text": _clean_text(evidence)[:240],
        "evidence_modality": "audio" if _has_audio_only_terms(evidence) else "textual",
        "modality_gate_status": "held",
    }


def _principal_diagnostic(ref: dict[str, Any], reason: str) -> dict[str, Any]:
    label = str(ref.get("display_name") or ref.get("label") or "").strip()
    asset_type = str(ref.get("asset_type") or "prop").strip() or "prop"
    evidence = str(ref.get("evidence_text") or ref.get("visual_evidence_span") or "")
    return _diagnostic(label, asset_type, reason, evidence)


def _is_manual_or_fixed_asset_ref(ref: dict[str, Any]) -> bool:
    source = str(ref.get("source") or "").lower()
    status = str(ref.get("status") or "").lower()
    return (
        source in {"manual", "approved", "fixed_visual_asset_reuse"}
        or status in {"fixed", "approved"}
        or bool(ref.get("graph_asset_id") or ref.get("graphAssetId"))
    )


def _is_explicit_named_asset_ref(ref: dict[str, Any]) -> bool:
    asset_type = str(ref.get("asset_type") or "")
    if asset_type == "prop":
        return False
    source = str(ref.get("source") or "").lower()
    status = str(ref.get("status") or "").lower()
    if "explicit" not in source and status != "mentioned":
        return False
    label = str(ref.get("display_name") or ref.get("label") or "").strip()
    return label not in GENERIC_CHARACTER_LABELS and label not in GENERIC_SCENE_LABELS


def _descriptive_signature(asset: dict[str, Any], fallback: str) -> str:
    return _clean_text(
        asset.get("descriptive_signature")
        or asset.get("signature")
        or asset.get("visual_description_seed")
        or fallback
    )[:240]


def _asset_type(value: Any) -> str:
    asset_type = str(value or "").strip()
    aliases = {
        "角色": "character",
        "人物": "character",
        "动物角色": "character",
        "animal_character": "character",
        "场景": "scene",
        "location": "scene",
        "道具": "prop",
        "object": "prop",
        "item": "prop",
    }
    normalized = aliases.get(asset_type) or aliases.get(asset_type.lower())
    if normalized:
        return normalized
    return asset_type if asset_type in ASSET_TYPES else "character"


def _character_subtype(value: Any) -> str:
    subtype = str(value or "").strip()
    return subtype if subtype in CHARACTER_SUBTYPES else ""


def _asset_ref_authority(ref: dict[str, Any]) -> int:
    source = str(ref.get("source") or "").lower()
    status = str(ref.get("status") or "").lower()
    if _is_manual_or_fixed_asset_ref(ref):
        return 50
    if source == "fixed_visual_asset_reuse" or status in {"fixed", "approved"}:
        return 45
    if "cross_shot" in source:
        return 35
    if "explicit" in source or status == "mentioned":
        return 30
    if source == "grounded_mention" or status in {"prop_relevant", "key_prop"}:
        return 25
    return 10


def _confidence(value: Any, *, provisional_name: bool = False) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return 0.72 if provisional_name else 0.82


def _clean_label(value: Any) -> str:
    return re.sub(r"^[\s@]+|[\s，。；:：.!?！？]+$", "", str(value or "")).strip()[:40]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", str(value or "")).lower()[:48] or "asset"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


__all__ = (
    "GENERIC_CHARACTER_LABELS",
    "GENERIC_SCENE_LABELS",
    "normalize_asset_ref_for_contract",
    "normalize_asset_refs_with_diagnostics",
    "principal_asset_refs_with_diagnostics",
)
