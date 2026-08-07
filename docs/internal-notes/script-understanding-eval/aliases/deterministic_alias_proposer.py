#!/usr/bin/env python3
"""Deterministic alias / identity-link *proposals* for offline eval only.

Boundary (read carefully):
  - This module emits candidate identity clusters for scoring.
  - It does NOT confirm, merge_alias, write Production Graph, or touch apps/api.
  - Proposals are never authoritative facts.

Coverage (DESIGN.md L1–L3 style, scoped by the current task):
  - Explicit aka in labeled cast lines, e.g. 周可（外号「阿可」）
  - Same-scene surname + occupational title, e.g. 陈默 + 陈师傅
  - Conservative whole-script 老X when a unique 本名 anchor exists and there is
    no same-surname conflict
  - Conservative same-scene full-name suffix, e.g. 林悦安 + 悦安, when the
    suffix is standalone and has a unique full-name anchor

Explicitly out of scope (no proposals, do not force):
  - Cross-scene cast inference beyond surface 老X indexing
  - Pronoun / coreference chains
  - Off-stage / distant shouts (surname+title is suppressed there)
  - Nickname without explicit label (浩子)
  - Ambiguous honorific 先生 as an auto-link bridge
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "alias_identity_linking_candidates_v0.1"
PROPOSER_VERSION = "deterministic_alias_proposer_v0.1"

# Occupational / relational titles safe enough for high-confidence surname binding.
# 「先生」 is intentionally excluded: it often addresses any adult of that surname.
_LINKABLE_TITLES = ("师傅", "老师", "医生", "老板", "教授", "警官", "主任", "经理")

_CHARACTER_LABEL = re.compile(
    r"(?im)^[ \t]*(?:人物|角色|characters|cast)[ \t]*[:：][ \t]*(?P<values>[^\r\n]+)"
)
_SCENE_SPLIT = re.compile(r"(?m)^[ \t]*第[一二三四五六七八九十百零\d]+场\b")
_SPEAKER_CUE = re.compile(r"(?m)^[ \t]*(?P<name>[\u4e00-\u9fff]{2,4})[ \t]*\r?$")
_EXPLICIT_AKA = re.compile(
    r"(?P<name>[\u4e00-\u9fff]{2,4})\s*[（(]\s*(?:外号|又名|也叫|小名)\s*[「『\"“]?"
    r"(?P<aka>[\u4e00-\u9fff]{1,4})[」』\"”]?\s*[）)]"
)
_TITLE_FORM = re.compile(
    rf"(?<![\u4e00-\u9fff])(?P<form>(?P<surname>[\u4e00-\u9fff])(?:{'|'.join(_LINKABLE_TITLES)}))"
)
_LAO_X = re.compile(r"(?<![\u4e00-\u9fff])老(?P<root>[\u4e00-\u9fff])(?![\u4e00-\u9fff])")
_STANDALONE_CHINESE_TEMPLATE = r"(?<![\u4e00-\u9fff]){surface}(?![\u4e00-\u9fff])"
# Off-stage only when the title form is the *content* of a shout after 喊：/喊:
# (e.g. 「远处有人喊：\n陈师傅！修车的！」). A nearby narrative 「门外有人喊。」 before
# a normal dialogue address must NOT suppress linking.
_OFFSTAGE_BEFORE_TITLE = re.compile(
    r"(?:远处[^。\n]{0,16})?(?:有人)?喊[：:]\s*$"
)

_GENERIC = frozenset(
    {
        "女人",
        "男人",
        "女孩",
        "男孩",
        "老人",
        "孩子",
        "陌生人",
        "来电者",
        "对方",
        "路人",
        "标题",
        "时间",
        "地点",
        "场景",
        "人物",
        "角色",
        "第一场",
        "第二场",
        "第三场",
        "第四场",
        "第五场",
    }
)
_ROLE_PREFIXES = ("邮局职员", "职员", "医生", "警察", "老师", "导演")


@dataclass
class _UF:
    parent: dict[str, str] = field(default_factory=dict)

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _strip_role_prefix(name: str) -> str:
    value = name.strip()
    for prefix in _ROLE_PREFIXES:
        if value.startswith(prefix) and len(value) > len(prefix):
            return value[len(prefix) :]
    return value


def _is_person_surface(name: str) -> bool:
    value = name.strip()
    if not value or value in _GENERIC:
        return False
    if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", value):
        return False
    return True


def _labeled_segments(raw_values: str) -> list[str]:
    parts: list[str] = []
    for match in re.finditer(r"[^、,，/;；]+", raw_values):
        segment = match.group(0).strip()
        if segment:
            parts.append(segment)
    return parts


def _scene_spans(source_text: str) -> list[tuple[int, int]]:
    starts = [match.start() for match in _SCENE_SPLIT.finditer(source_text)]
    if not starts:
        return [(0, len(source_text))]
    if starts[0] > 0:
        starts = [0, *starts]
    spans: list[tuple[int, int]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(source_text)
        spans.append((start, end))
    return spans


def _scene_index_for(offset: int, spans: list[tuple[int, int]]) -> int:
    for index, (start, end) in enumerate(spans):
        if start <= offset < end:
            return index
    return max(0, len(spans) - 1)


def _next_nonempty_line(source_text: str, offset: int) -> str:
    for line in source_text[offset:].splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _looks_like_heading(line: str) -> bool:
    return bool(re.match(r"^第[一二三四五六七八九十百零\d]+场\b", line)) or line.startswith("标题")


def extract_mentions(source_text: str) -> dict[str, Any]:
    """Collect surface mentions and lightweight provenance for linking rules."""
    scenes = _scene_spans(source_text)
    surfaces: set[str] = set()
    anchors: set[str] = set()  # likely 本名 / labeled identities
    aka_pairs: list[tuple[str, str, str]] = []  # name, aka, method
    title_hits: list[dict[str, Any]] = []
    lao_hits: list[dict[str, Any]] = []

    for match in _CHARACTER_LABEL.finditer(source_text):
        for segment in _labeled_segments(match.group("values")):
            aka_match = _EXPLICIT_AKA.search(segment)
            if aka_match:
                name = aka_match.group("name")
                aka = aka_match.group("aka")
                if _is_person_surface(name):
                    surfaces.add(name)
                    anchors.add(name)
                if _is_person_surface(aka) or re.fullmatch(r"[\u4e00-\u9fff]{1,4}", aka):
                    surfaces.add(aka)
                    aka_pairs.append((name, aka, "explicit_aka_label"))
                continue

            without_paren = re.sub(r"[（(][^）)]*[）)]", "", segment).strip()
            cleaned = _strip_role_prefix(without_paren)
            if _is_person_surface(cleaned):
                surfaces.add(cleaned)
                anchors.add(cleaned)

    for match in _SPEAKER_CUE.finditer(source_text):
        name = match.group("name").strip()
        next_line = _next_nonempty_line(source_text, match.end())
        if not next_line or _looks_like_heading(next_line) or not _is_person_surface(name):
            continue
        # Speaker cues that are pure title-forms are still mentions, but not 本名 anchors.
        surfaces.add(name)
        if not _TITLE_FORM.fullmatch(name) and not _LAO_X.fullmatch(name):
            anchors.add(name)
        elif _LAO_X.fullmatch(name):
            # 「老王」 as a speaker/name can itself be an anchor identity.
            anchors.add(name)

    for match in _TITLE_FORM.finditer(source_text):
        form = match.group("form")
        surname = match.group("surname")
        start = match.start("form")
        # Skip if this title-form is already a labeled person whose full name is the form
        # (e.g. 王师傅): still a mention/anchor, recorded above; keep hit for completeness.
        title_hits.append(
            {
                "form": form,
                "surname": surname,
                "start": start,
                "end": match.end("form"),
                "scene": _scene_index_for(start, scenes),
                "offstage": _is_offstage(source_text, start),
            }
        )
        surfaces.add(form)

    for match in _LAO_X.finditer(source_text):
        form = f"老{match.group('root')}"
        start = match.start()
        lao_hits.append(
            {
                "form": form,
                "root": match.group("root"),
                "start": start,
                "end": match.end(),
                "scene": _scene_index_for(start, scenes),
            }
        )
        surfaces.add(form)

    # Ambiguous honorific surfaces (mention only; never auto-linked by this proposer).
    for match in re.finditer(r"(?P<form>(?P<surname>[\u4e00-\u9fff])先生)", source_text):
        surfaces.add(match.group("form"))

    return {
        "surfaces": surfaces,
        "anchors": anchors,
        "aka_pairs": aka_pairs,
        "title_hits": title_hits,
        "lao_hits": lao_hits,
        "scene_count": len(scenes),
    }


def _is_offstage(source_text: str, offset: int) -> bool:
    before = source_text[max(0, offset - 80) : offset]
    return bool(_OFFSTAGE_BEFORE_TITLE.search(before))


def _anchors_with_surname(anchors: set[str], surname: str) -> list[str]:
    return sorted(name for name in anchors if name.startswith(surname) and name != f"老{surname}")


def propose_identity_clusters(source_text: str) -> dict[str, Any]:
    """Return predicted_clusters compatible with score_alias_linking.py."""
    extracted = extract_mentions(source_text)
    surfaces: set[str] = set(extracted["surfaces"])
    anchors: set[str] = set(extracted["anchors"])
    uf = _UF()
    for surface in surfaces:
        uf.add(surface)

    proposals: list[dict[str, Any]] = []

    # L1: explicit aka from labels.
    for name, aka, method in extracted["aka_pairs"]:
        if name not in surfaces or aka not in surfaces:
            continue
        uf.union(name, aka)
        proposals.append(
            {
                "left": name,
                "right": aka,
                "method": method,
                "confidence": 0.95,
            }
        )

    # L2: same-scene surname + title, unique same-surname 本名 anchor, not off-stage.
    for hit in extracted["title_hits"]:
        form = hit["form"]
        if hit["offstage"]:
            continue
        # If the title-form is itself a labeled/speaker anchor (王师傅), do not treat it
        # as an alias of someone else.
        if form in anchors:
            continue
        candidates = _anchors_with_surname(anchors, hit["surname"])
        # Restrict to anchors that also appear in the same scene when we can locate them.
        same_scene_anchors = [
            name
            for name in candidates
            if _surface_appears_in_scene(source_text, name, hit["scene"], extracted["scene_count"])
        ]
        pool = same_scene_anchors if same_scene_anchors else []
        if len(pool) != 1:
            # Ambiguous or missing same-scene anchor → no proposal (protects A5/A6).
            continue
        anchor = pool[0]
        uf.union(anchor, form)
        proposals.append(
            {
                "left": anchor,
                "right": form,
                "method": "surname_title_same_scene",
                "confidence": 0.9,
                "scene": hit["scene"],
            }
        )

    # L3: conservative 老X with unique whole-script 本名 anchor (no same-surname conflict).
    for hit in extracted["lao_hits"]:
        form = hit["form"]
        # 「老王」 may already be the person's labeled name; linking 老王→老王 is a no-op.
        if form in anchors and not any(
            name != form and name.startswith(hit["root"]) for name in anchors
        ):
            continue
        candidates = [
            name
            for name in _anchors_with_surname(anchors, hit["root"])
            if name != form
        ]
        if len(candidates) != 1:
            continue
        anchor = candidates[0]
        uf.union(anchor, form)
        proposals.append(
            {
                "left": anchor,
                "right": form,
                "method": "lao_x_unique_anchor",
                "confidence": 0.8,
            }
        )

    # L4: conservative full-name suffix in the same scene.
    for anchor in sorted(anchors):
        suffix = _safe_given_name_suffix(anchor)
        if not suffix:
            continue
        if len([name for name in anchors if name.endswith(suffix)]) != 1:
            continue
        pattern = re.compile(_STANDALONE_CHINESE_TEMPLATE.format(surface=re.escape(suffix)))
        for match in pattern.finditer(source_text):
            scene = _scene_index_for(match.start(), _scene_spans(source_text))
            if not _surface_appears_in_scene(source_text, anchor, scene, extracted["scene_count"]):
                continue
            surfaces.add(suffix)
            uf.union(anchor, suffix)
            proposals.append(
                {
                    "left": anchor,
                    "right": suffix,
                    "method": "given_name_suffix_same_scene_unique_anchor",
                    "confidence": 0.72,
                    "scene": scene,
                }
            )
            break

    clusters_map: dict[str, list[str]] = {}
    for surface in sorted(surfaces):
        root = uf.find(surface)
        clusters_map.setdefault(root, []).append(surface)

    predicted = [
        {"id": f"P{index}", "mentions": mentions}
        for index, mentions in enumerate(clusters_map.values(), start=1)
    ]
    return {
        "predicted_clusters": predicted,
        "link_proposals": proposals,
        "proposer_version": PROPOSER_VERSION,
        "extraction": {
            "surfaces": sorted(surfaces),
            "anchors": sorted(anchors),
        },
    }


def _surface_appears_in_scene(source_text: str, surface: str, scene_index: int, scene_count: int) -> bool:
    spans = _scene_spans(source_text)
    if scene_index < 0 or scene_index >= len(spans):
        return False
    start, end = spans[scene_index]
    return surface in source_text[start:end]


def _safe_given_name_suffix(anchor: str) -> str:
    if not re.fullmatch(r"[\u4e00-\u9fff]{3,4}", anchor):
        return ""
    suffix = anchor[1:]
    return suffix if 2 <= len(suffix) <= 3 else ""


def propose_for_gold_cases(gold_data: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for gold_case in gold_data.get("cases", []):
        case_id = str(gold_case["id"])
        source = str(gold_case.get("source") or "")
        result = propose_identity_clusters(source)
        cases.append(
            {
                "id": case_id,
                "predicted_clusters": result["predicted_clusters"],
                "link_proposals": result["link_proposals"],
                "proposer_version": result["proposer_version"],
                "extraction": result["extraction"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "deterministic_alias_proposer",
        "proposer_version": PROPOSER_VERSION,
        "cases": cases,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path(__file__).with_name("gold_cases.json"),
        help="Path to gold_cases.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write candidate JSON to this path (default: stdout)",
    )
    parser.add_argument(
        "--case",
        dest="case_id",
        help="Only propose for one case id",
    )
    args = parser.parse_args(argv)

    with args.gold.open("r", encoding="utf-8") as handle:
        gold_data = json.load(handle)

    if args.case_id:
        matched = [case for case in gold_data.get("cases", []) if str(case["id"]) == args.case_id]
        if not matched:
            raise SystemExit(f"case not found: {args.case_id}")
        gold_data = {**gold_data, "cases": matched}

    candidate_data = propose_for_gold_cases(gold_data)
    text = json.dumps(candidate_data, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
