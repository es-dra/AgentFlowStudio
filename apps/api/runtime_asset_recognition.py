from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping

from apps.api.runtime_asset_extraction import normalize_asset_refs_with_diagnostics
from apps.api.runtime_store import safe_id


ASSET_TYPES = ("character", "scene", "prop")
PROP_FAMILIES = {
    "bag": ("行囊", "包袱", "背包", "书包"),
    "blade": ("长刀", "短刀", "刀", "长剑", "短剑", "剑"),
    "book": ("册", "书", "笔记本", "卷轴", "竹简"),
    "document": ("试卷", "纸", "信件", "信封", "地图", "照片"),
    "key": ("钥匙", "门卡", "卡片"),
    "rake": ("钉耙", "耙子", "耙"),
    "rod": ("金箍棒", "棒", "棍", "杖"),
    "rope": ("牵引绳", "狗绳", "红绳", "绳"),
    "shield": ("盾牌", "盾"),
    "spear": ("长枪", "短枪", "枪", "戟"),
    "umbrella": ("雨伞", "折叠伞", "伞"),
}
PROP_TERMS = tuple(
    sorted({term for terms in PROP_FAMILIES.values() for term in terms}, key=len, reverse=True)
)
PROP_ACTION_PREFIXES = (
    "重新系过的",
    "磨损严重的",
    "先把",
    "再把",
    "手持",
    "手握",
    "握紧",
    "握着",
    "拿起",
    "拿着",
    "拾起",
    "捡起",
    "扛着",
    "抡起",
    "抡着",
    "举起",
    "举着",
    "收起",
    "藏起",
    "掏出",
    "抽出",
    "拔出",
    "放下",
    "护住",
    "靠近",
    "一柄",
    "一把",
    "一根",
    "一个",
    "一只",
    "那柄",
    "那把",
    "那根",
    "这个",
    "那个",
)
GENERIC_PROP_TERMS = {
    term
    for terms in PROP_FAMILIES.values()
    for term in terms
    if len(term) <= 2 or term in {"钉耙", "耙子", "行囊", "包袱", "背包", "书包"}
}
GENERIC_PROP_LABELS = {"武器", "道具", "物件", "装备", "随身物品"}
GROUP_CHARACTER_TERMS = ("两人", "二人", "双方", "他们", "她们", "众人")
ROLE_ALIAS_TERMS = ("师父", "老师", "队长", "父亲", "母亲", "哥哥", "姐姐")
VOCATIVE_STOPWORDS = {
    "怎么",
    "什么",
    "这里",
    "那里",
    "等等",
    "快点",
    "住手",
    "小心",
    "听着",
    "别动",
    "走开",
    "够了",
}
CHARACTER_SUFFIX_STOPWORDS = {
    "场景",
    "镜头",
    "画面",
    "环境",
    "远景",
    "近景",
    "特写",
    "动作",
    "目的",
    "黄昏",
    "夜晚",
}
PROP_DESCRIPTOR_STOP_CHARS = set(
    "把将着的其这那一个只柄根件张在以从于向后前里外上下来去"
    "拿握扛抡举收藏掏抽拔放护靠拾捡落过紧住看见发现"
)


def recognize_asset_occurrences(
    source_text: str,
    source_context_texts: list[str],
    scenes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    contexts = _dedupe_texts([source_text, *source_context_texts])
    scene_catalog: list[dict[str, Any]] = []
    shot_catalog: list[dict[str, Any]] = []
    scene_shots: dict[str, list[str]] = {}
    shot_contexts: dict[str, str] = {}
    scene_contexts: dict[str, str] = {}
    shot_count = 0
    for scene_number, scene in enumerate(scenes, start=1):
        scene_id = safe_id(str(scene.get("scene_id") or f"scene-{scene_number}"))
        scene_name = str(scene.get("name") or scene.get("title") or f"场景 {scene_number}").strip()[:120]
        scene_catalog.append({"scene_id": scene_id, "name": scene_name, "number": scene_number})
        shot_ids: list[str] = []
        scene_parts = [
            scene_name,
            *(
                str(scene.get(key) or "")
                for key in ("description", "summary", "narrative_purpose", "blocking", "dialogue")
            ),
        ]
        for shot_number, shot in enumerate(
            (item for item in scene.get("shots", []) if isinstance(item, Mapping)),
            start=1,
        ):
            shot_count += 1
            shot_id = safe_id(str(shot.get("shot_id") or f"{scene_id}-shot-{shot_number}"))
            shot_title = str(shot.get("title") or f"镜头 {scene_number}-{shot_number}").strip()[:120]
            context = " ".join(
                str(shot.get(key) or "")
                for key in (
                    "title",
                    "description",
                    "narrative_purpose",
                    "purpose",
                    "blocking",
                    "dialogue",
                    "action",
                    "sound",
                )
            ).strip()
            shot_ids.append(shot_id)
            shot_contexts[shot_id] = context
            scene_parts.append(context)
            shot_catalog.append(
                {
                    "shot_id": shot_id,
                    "scene_id": scene_id,
                    "title": shot_title,
                    "number": shot_count,
                }
            )
        scene_shots[scene_id] = shot_ids
        scene_contexts[scene_id] = " ".join(part for part in scene_parts if part).strip()

    corpus = "\n".join([*contexts, *scene_contexts.values(), *shot_contexts.values()])
    records: list[dict[str, Any]] = []
    order = 0

    def add(
        asset_type: str,
        label: str,
        *,
        scene_id: str = "",
        shot_id: str = "",
        evidence: str = "",
        confidence: float = 0.8,
        source: str = "grounded_text",
    ) -> None:
        nonlocal order
        clean = _clean_label(label)
        if asset_type not in ASSET_TYPES or not clean:
            return
        records.append(
            {
                "asset_type": asset_type,
                "label": clean,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "evidence": _evidence_excerpt(evidence, clean),
                "confidence": confidence,
                "source": source,
                "order": order,
            }
        )
        order += 1

    for context in contexts:
        refs, _ = normalize_asset_refs_with_diagnostics([], context=context, include_inferred=True)
        for ref in refs:
            add(
                str(ref.get("asset_type") or ""),
                str(ref.get("display_name") or ref.get("label") or ""),
                evidence=str(ref.get("evidence_text") or context),
                confidence=float(ref.get("confidence") or 0.75),
                source="script_normalizer",
            )
    for scene in scene_catalog:
        scene_id = scene["scene_id"]
        add(
            "scene",
            scene["name"],
            scene_id=scene_id,
            evidence=scene_contexts[scene_id],
            confidence=1.0,
            source="applied_scene",
        )
        for shot_id in scene_shots[scene_id]:
            add(
                "scene",
                scene["name"],
                scene_id=scene_id,
                shot_id=shot_id,
                evidence=shot_contexts[shot_id] or scene_contexts[scene_id],
                confidence=1.0,
                source="scene_descendant",
            )
        refs, _ = normalize_asset_refs_with_diagnostics(
            [],
            context=scene_contexts[scene_id],
            include_inferred=True,
        )
        for ref in refs:
            add(
                str(ref.get("asset_type") or ""),
                str(ref.get("display_name") or ref.get("label") or ""),
                scene_id=scene_id,
                evidence=str(ref.get("evidence_text") or scene_contexts[scene_id]),
                confidence=float(ref.get("confidence") or 0.7),
                source="scene_context",
            )

    for shot in shot_catalog:
        shot_id = shot["shot_id"]
        scene_id = shot["scene_id"]
        context = shot_contexts[shot_id]
        refs, _ = normalize_asset_refs_with_diagnostics([], context=context, include_inferred=True)
        for ref in refs:
            add(
                str(ref.get("asset_type") or ""),
                str(ref.get("display_name") or ref.get("label") or ""),
                scene_id=scene_id,
                shot_id=shot_id,
                evidence=str(ref.get("evidence_text") or context),
                confidence=float(ref.get("confidence") or 0.72),
                source="shot_context",
            )

    for context in contexts:
        for mention in _prop_mentions(context):
            add(
                "prop",
                mention["label"],
                evidence=context,
                confidence=mention["confidence"],
                source="script_prop_anchor" if mention["named"] else "script_prop_alias",
            )
    for context in scene_contexts.values():
        for mention in _prop_mentions(context):
            add(
                "prop",
                mention["label"],
                evidence=context,
                confidence=mention["confidence"],
                source="scene_prop_anchor" if mention["named"] else "scene_prop_alias",
            )
    for shot in shot_catalog:
        context = shot_contexts[shot["shot_id"]]
        for mention in _prop_mentions(context):
            add(
                "prop",
                mention["label"],
                scene_id=shot["scene_id"],
                shot_id=shot["shot_id"],
                evidence=context,
                confidence=mention["confidence"],
                source="shot_prop_anchor" if mention["named"] else "shot_prop_alias",
            )

    characters = _cluster_characters(records, corpus, shot_catalog, shot_contexts)
    props, ambiguities = _cluster_props(records, corpus)
    scene_assets = _cluster_scenes(records, scene_catalog, scene_shots)
    assets = [*characters, *scene_assets, *props]
    assets.sort(key=lambda item: (ASSET_TYPES.index(item["asset_type"]), item["order"], item["display_name"]))

    for asset in assets:
        if asset["asset_type"] not in {"character", "prop"}:
            continue
        aliases = [asset["display_name"], *asset["aliases"]]
        direct_shots = {
            shot_id
            for shot_id, context in shot_contexts.items()
            if _contains_alias(context, aliases)
        }
        if asset["asset_type"] == "character":
            for scene_id, shot_ids in scene_shots.items():
                scene_cast = {
                    candidate["display_name"]
                    for candidate in characters
                    if any(_contains_alias(shot_contexts[shot_id], [candidate["display_name"], *candidate["aliases"]]) for shot_id in shot_ids)
                }
                if asset["display_name"] not in scene_cast:
                    continue
                for shot_id in shot_ids:
                    if any(term in shot_contexts[shot_id] for term in GROUP_CHARACTER_TERMS):
                        direct_shots.add(shot_id)
        asset["shot_ids"].update(direct_shots)
        asset["scene_ids"].update(
            shot["scene_id"] for shot in shot_catalog if shot["shot_id"] in asset["shot_ids"]
        )

    anchors = [
        {
            "anchor_id": f"anchor-{item['asset_type']}-{_slug(item['display_name'])}",
            "asset_type": item["asset_type"],
            "display_name": item["display_name"],
            "aliases": sorted({item["display_name"], *item["aliases"]}),
            "scene_ids": sorted(item["scene_ids"]),
            "shot_ids": sorted(item["shot_ids"]),
            "ambiguity": next(
                (
                    issue["code"]
                    for issue in ambiguities
                    if issue["asset_type"] == item["asset_type"]
                    and item["display_name"] in issue["labels"]
                ),
                "",
            ),
        }
        for item in assets
    ]
    return {
        "scene_catalog": scene_catalog,
        "shot_catalog": shot_catalog,
        "assets": assets,
        "required_asset_anchors": anchors,
        "recognition_ambiguities": ambiguities,
    }


def _cluster_characters(
    records: list[dict[str, Any]],
    corpus: str,
    shot_catalog: list[dict[str, Any]],
    shot_contexts: Mapping[str, str],
) -> list[dict[str, Any]]:
    labels = _ordered_unique(
        record["label"]
        for record in records
        if record["asset_type"] == "character"
        and record["source"] in {"script_normalizer", "scene_context", "shot_context"}
    )
    labels = [
        label
        for label in labels
        if label not in CHARACTER_SUFFIX_STOPWORDS and not _looks_like_action(label)
    ]
    canonical = [
        label
        for label in labels
        if not any(label != other and len(other) > len(label) and other.endswith(label) for other in labels)
    ]
    if not canonical:
        canonical = labels
    bindings = _dialogue_alias_bindings(corpus, canonical)
    protected_aliases = {
        label: name
        for name in canonical
        for label in [*labels, name[-2:] if len(name) > 2 else name]
        if label == name or (len(label) >= 2 and name.endswith(label))
    }
    bindings = {
        alias: target
        for alias, target in bindings.items()
        if _valid_character_alias(alias)
        and (alias not in protected_aliases or protected_aliases[alias] == target)
    }
    labels.extend(alias for alias in bindings if alias not in labels)
    result = []
    for name in canonical:
        aliases = {
            label
            for label in labels
            if label == name or (len(label) >= 2 and name.endswith(label))
        }
        if len(name) > 2:
            aliases.add(name[-2:])
        aliases.update(alias for alias, target in bindings.items() if target == name)
        matching = [
            record
            for record in records
            if record["asset_type"] == "character"
            and (
                record["label"] in aliases
                or record["label"] == name
                or name.endswith(record["label"])
            )
        ]
        scene_ids = {record["scene_id"] for record in matching if record["scene_id"]}
        shot_ids = {record["shot_id"] for record in matching if record["shot_id"]}
        for shot in shot_catalog:
            if _contains_alias(shot_contexts[shot["shot_id"]], [name, *aliases]):
                scene_ids.add(shot["scene_id"])
                shot_ids.add(shot["shot_id"])
        result.append(
            _cluster(
                "character",
                name,
                aliases,
                matching,
                scene_ids=scene_ids,
                shot_ids=shot_ids,
            )
        )
    return _drop_empty_duplicate_clusters(result)


def _cluster_props(
    records: list[dict[str, Any]],
    corpus: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    labels = _ordered_unique(record["label"] for record in records if record["asset_type"] == "prop")
    labels = [label for label in labels if label not in GENERIC_PROP_LABELS]
    by_family: dict[str, list[str]] = defaultdict(list)
    for label in labels:
        family = _prop_family(label)
        if family:
            by_family[family].append(label)
    result: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    consumed: set[str] = set()
    for family, family_labels in by_family.items():
        specifics = [
            label
            for label in family_labels
            if label not in GENERIC_PROP_TERMS and len(label) > min(len(term) for term in PROP_FAMILIES[family])
        ]
        viable_specifics = [
            label
            for label in _drop_contained_labels(specifics)
            if _is_grounded_specific_prop(label, family, records)
        ]
        has_normalized_family_evidence = any(
            record["asset_type"] == "prop"
            and record["label"] in family_labels
            and record["source"] in {"script_normalizer", "scene_context", "shot_context"}
            for record in records
        )
        if not viable_specifics and not has_normalized_family_evidence:
            consumed.update(family_labels)
            continue
        explicit_instances = _explicit_distinct_prop_instances(corpus, family, viable_specifics)
        if len(explicit_instances) > 1:
            ambiguities.append(
                {
                    "code": "ambiguous_prop_instances",
                    "asset_type": "prop",
                    "labels": sorted(explicit_instances),
                    "message": "同类具名道具存在多个实例，需确认别名或保持独立。",
                }
            )
        targets = explicit_instances or [
            max(
                viable_specifics or family_labels,
                key=lambda value: (
                    _specific_prop_score(value, family, records),
                    len(value),
                    -family_labels.index(value),
                ),
            )
        ]
        for target in targets:
            aliases = {
                label
                for label in family_labels
                if label == target
                or label in GENERIC_PROP_TERMS
                or any(
                    record["label"] == label and record["source"] == "script_normalizer"
                    for record in records
                )
            }
            if len(targets) > 1:
                aliases = {label for label in aliases if label == target or label in target}
            matching = [
                record
                for record in records
                if record["asset_type"] == "prop" and record["label"] in aliases
            ]
            result.append(_cluster("prop", target, aliases, matching))
            consumed.update(aliases)
    for label in labels:
        if label in consumed:
            continue
        if _prop_family(label):
            continue
        matching = [
            record for record in records if record["asset_type"] == "prop" and record["label"] == label
        ]
        result.append(_cluster("prop", label, {label}, matching))
    return _drop_empty_duplicate_clusters(result), ambiguities


def _cluster_scenes(
    records: list[dict[str, Any]],
    scene_catalog: list[dict[str, Any]],
    scene_shots: Mapping[str, list[str]],
) -> list[dict[str, Any]]:
    result = []
    for scene in scene_catalog:
        matching = [
            record
            for record in records
            if record["asset_type"] == "scene"
            and record["scene_id"] == scene["scene_id"]
        ]
        result.append(
            _cluster(
                "scene",
                scene["name"],
                {scene["name"]},
                matching,
                scene_ids={scene["scene_id"]},
                shot_ids=set(scene_shots.get(scene["scene_id"], [])),
            )
        )
    return result


def _cluster(
    asset_type: str,
    display_name: str,
    aliases: set[str],
    records: list[dict[str, Any]],
    *,
    scene_ids: set[str] | None = None,
    shot_ids: set[str] | None = None,
) -> dict[str, Any]:
    evidence = _ordered_unique(record["evidence"] for record in records if record["evidence"])
    return {
        "asset_type": asset_type,
        "display_name": display_name,
        "aliases": set(_ordered_unique([display_name, *aliases])),
        "scene_ids": set(scene_ids or ()) | {record["scene_id"] for record in records if record["scene_id"]},
        "shot_ids": set(shot_ids or ()) | {record["shot_id"] for record in records if record["shot_id"]},
        "confidence": max([float(record["confidence"]) for record in records] or [0.7]),
        "evidence": evidence[:8],
        "order": min([int(record["order"]) for record in records] or [100000]),
    }


def _prop_mentions(text: str) -> list[dict[str, Any]]:
    source = str(text or "")
    result: list[dict[str, Any]] = []
    for term in PROP_TERMS:
        for match in re.finditer(re.escape(term), source):
            result.append(
                {
                    "label": term,
                    "named": term not in GENERIC_PROP_TERMS,
                    "confidence": 0.86 if term not in GENERIC_PROP_TERMS else 0.78,
                    "order": match.start(),
                }
            )
            prefix = re.search(r"[\u4e00-\u9fff]{0,4}$", source[max(0, match.start() - 8) : match.start()])
            leading = prefix.group(0) if prefix else ""
            for marker in PROP_ACTION_PREFIXES:
                if leading.endswith(marker):
                    leading = ""
                    break
            leading = re.sub(r"^(?:把|将|着|的|其|这|那|一|个|只|柄|把|根|件|张)+", "", leading)
            if len(leading) > 2:
                leading = leading[-2:]
            if any(character in PROP_DESCRIPTOR_STOP_CHARS for character in leading):
                leading = ""
            label = _clean_label(f"{leading}{term}")
            label = _strip_prop_action_prefix(label)
            if not label:
                continue
            named = label not in GENERIC_PROP_TERMS and len(label) > len(term)
            if label != term:
                result.append(
                    {
                        "label": label,
                        "named": named,
                        "confidence": 0.94 if named else 0.78,
                        "order": match.start(),
                    }
                )
    ordered = []
    for item in sorted(result, key=lambda value: value["order"]):
        if any(
            item["label"] != other["label"]
            and item["label"] in other["label"]
            and _prop_family(item["label"]) == _prop_family(other["label"])
            for other in result
        ):
            # Keep the short form as an alias, but only once.
            pass
        if item["label"] not in {value["label"] for value in ordered}:
            ordered.append(item)
    return ordered


def _dialogue_alias_bindings(text: str, canonical: list[str]) -> dict[str, str]:
    source = str(text or "")
    if not canonical:
        return {}
    speaker_pattern = re.compile(
        rf"({'|'.join(re.escape(name) for name in sorted(canonical, key=len, reverse=True))})\s+(?=[^\s])"
    )
    markers = list(speaker_pattern.finditer(source))
    bindings: dict[str, str] = {}
    previous_speaker = ""
    for index, marker in enumerate(markers):
        speaker = marker.group(1)
        end = markers[index + 1].start() if index + 1 < len(markers) else min(len(source), marker.end() + 180)
        dialogue = source[marker.end() : end].strip()
        for alias in re.findall(
            r"(?:别喊我|不要叫我|别叫我|我不是)([\u4e00-\u9fff]{2,4})(?=[，。！？,.!?])",
            dialogue,
        ):
            if alias not in VOCATIVE_STOPWORDS:
                bindings[alias] = speaker
        for alias in re.findall(
            r"俺老([\u4e00-\u9fff]{1,2})(?=的|，|。|！|？|,|\s)",
            dialogue,
        ):
            bindings[f"老{alias}"] = speaker
        for character in speaker:
            if f"俺老{character}" in dialogue:
                bindings[f"老{character}"] = speaker
        vocative = re.match(r"([\u4e00-\u9fff]{2,3})[，,！!]", dialogue)
        if vocative and vocative.group(1) not in VOCATIVE_STOPWORDS:
            target = previous_speaker if previous_speaker and previous_speaker != speaker else ""
            if not target:
                preceding = source[max(0, marker.start() - 120) : marker.start()]
                candidates = [
                    name for name in canonical if name != speaker and preceding.rfind(name) >= 0
                ]
                if candidates:
                    target = max(candidates, key=preceding.rfind)
            if target:
                bindings[vocative.group(1)] = target
        previous_speaker = speaker
    for role in ROLE_ALIAS_TERMS:
        if role not in source:
            continue
        speakers_using_role = {
            marker.group(1)
            for index, marker in enumerate(markers)
            if role
            in source[
                marker.end() : (
                    markers[index + 1].start()
                    if index + 1 < len(markers)
                    else min(len(source), marker.end() + 180)
                )
            ]
        }
        possible_targets = [name for name in canonical if name not in speakers_using_role]
        if len(possible_targets) == 1 and speakers_using_role:
            bindings.setdefault(role, possible_targets[0])
    return bindings


def _is_grounded_specific_prop(
    label: str,
    family: str,
    records: list[dict[str, Any]],
) -> bool:
    sources = {
        record["source"]
        for record in records
        if record["asset_type"] == "prop" and record["label"] == label
    }
    if "script_normalizer" in sources:
        return True
    return (
        "script_prop_anchor" in sources
        and bool({"scene_prop_anchor", "shot_prop_anchor"} & sources)
        and _specific_prop_score(label, family, records) > 0
    )


def _specific_prop_score(
    label: str,
    family: str,
    records: list[dict[str, Any]],
) -> int:
    sources = {
        record["source"]
        for record in records
        if record["asset_type"] == "prop" and record["label"] == label
    }
    score = 20 if "script_normalizer" in sources else 0
    score += 8 if "script_prop_anchor" in sources else 0
    score += 6 if "shot_prop_anchor" in sources else 0
    score += 3 if "scene_prop_anchor" in sources else 0
    generic_suffix = next(
        (term for term in PROP_FAMILIES[family] if label.endswith(term)),
        "",
    )
    descriptor = label[: -len(generic_suffix)] if generic_suffix else ""
    if descriptor and not any(character in PROP_DESCRIPTOR_STOP_CHARS for character in descriptor):
        score += 4
    if re.search(r"[一二三四五六七八九十百千两]", descriptor):
        score += 2
    return score


def _explicit_distinct_prop_instances(
    corpus: str,
    family: str,
    specifics: list[str],
) -> list[str]:
    del family
    if len(specifics) < 2:
        return []
    distinct = []
    for label in specifics:
        others = [other for other in specifics if other != label]
        if any(
            re.search(
                rf"{re.escape(label)}.{{0,12}}(?:与|和|及|另一个|另一件).{{0,12}}{re.escape(other)}"
                rf"|{re.escape(other)}.{{0,12}}(?:与|和|及|另一个|另一件).{{0,12}}{re.escape(label)}",
                corpus,
            )
            for other in others
        ):
            distinct.append(label)
    return _ordered_unique(distinct)


def _drop_empty_duplicate_clusters(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["asset_type"], _normalized(item["display_name"]))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _drop_contained_labels(labels: list[str]) -> list[str]:
    return [
        label
        for label in labels
        if not any(label != other and label in other for other in labels)
    ]


def _prop_family(label: str) -> str:
    for family, terms in PROP_FAMILIES.items():
        if any(term in label for term in terms):
            return family
    return ""


def _strip_prop_action_prefix(value: str) -> str:
    clean = value
    changed = True
    while changed:
        changed = False
        for prefix in PROP_ACTION_PREFIXES:
            if clean.startswith(prefix):
                clean = clean[len(prefix) :]
                changed = True
    return _clean_label(clean)


def _contains_alias(text: str, aliases: list[str] | set[str]) -> bool:
    source = str(text or "")
    return any(alias and alias in source for alias in aliases)


def _valid_character_alias(value: str) -> bool:
    clean = _clean_label(value)
    if not 2 <= len(clean) <= 4 or clean in VOCATIVE_STOPWORDS:
        return False
    return not any(
        term in clean
        for term in (
            "少夸",
            "别喊",
            "别叫",
            "不要",
            "只问",
            "会顾",
            "能收",
            "先别",
            "明日",
            "担子",
            "账咱",
        )
    )


def _looks_like_action(value: str) -> bool:
    return any(
        term in value
        for term in (
            "发现",
            "走进",
            "冲向",
            "转身",
            "回头",
            "抬头",
            "低头",
            "停手",
            "同行",
            "选择",
            "对峙",
        )
    )


def _evidence_excerpt(text: str, label: str) -> str:
    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if not source:
        return ""
    position = source.find(label)
    if position < 0:
        return source[:240]
    return source[max(0, position - 72) : position + len(label) + 128][:240]


def _clean_label(value: str) -> str:
    return re.sub(r"^[\s，。；:：.!?！？、]+|[\s，。；:：.!?！？、]+$", "", str(value or "")).strip()[:120]


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _slug(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", str(value or "")).strip("-").lower()[:48] or "asset"


def _ordered_unique(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _dedupe_texts(values: list[str]) -> list[str]:
    return _ordered_unique(value[:12000] for value in values if str(value or "").strip())


__all__ = ("recognize_asset_occurrences",)
