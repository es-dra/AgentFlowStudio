from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_storyboard_provider_localization import (
    CAMERA_MOTION_LABELS,
    FOCUS_TARGET_LABELS,
    LIGHT_ATMOSPHERE_RULES,
    SHOT_SIZE_LABELS,
    SOUND_RULES,
)
from apps.api.runtime_storyboard_provider_text import has_cjk, has_latin, token_key


DISPLAY_LOCALIZED_FIELDS = (
    "description",
    "shot_size",
    "light_atmosphere",
    "camera_motion",
    "dialogue",
    "sound",
)

LATIN_FRAGMENT_RE = re.compile(r"[A-Za-z0-9]+(?:[._'-][A-Za-z0-9]+)*")

ALLOWED_LATIN_UNIT_TOKENS = {
    "s",
    "ms",
    "fps",
    "hz",
    "khz",
    "db",
    "px",
    "dpi",
    "p",
    "k",
    "kb",
    "mb",
    "gb",
    "tb",
    "mm",
    "cm",
    "m",
    "kg",
    "rgb",
    "rgba",
    "hex",
    "iso",
}

ENGLISH_PHRASE_CONNECTOR_TOKENS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "beneath",
    "between",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "over",
    "the",
    "through",
    "to",
    "under",
    "with",
}

FIELD_ALLOWED_RAW_LATIN_TOKENS = {
    "dialogue": {"os", "vo", "v_o"},
}


def validate_raw_display_field_english(raw_shots: list[Any], source_script_text: str) -> None:
    if _source_is_latin_language(source_script_text):
        return
    source_allowed = _source_latin_token_keys(source_script_text)
    for item in raw_shots:
        if not isinstance(item, dict):
            continue
        asset_allowed = _asset_ref_latin_token_keys(item.get("asset_refs"))
        for field in DISPLAY_LOCALIZED_FIELDS:
            unknown = _unapproved_latin_fragments(
                item.get(field),
                source_allowed=source_allowed.union(asset_allowed),
                field_allowed=_raw_field_allowed_latin_tokens(field),
            )
            if unknown:
                raise ValueError(f"provider storyboard response has untranslated English in {field}")


def validate_localized_display_fields(shots: list[dict[str, Any]], source_script_text: str) -> None:
    if _source_is_latin_language(source_script_text):
        return
    source_allowed = _source_latin_token_keys(source_script_text)
    for item in shots:
        asset_allowed = _asset_ref_latin_token_keys(item.get("asset_refs"))
        for field in DISPLAY_LOCALIZED_FIELDS:
            unknown = _unapproved_latin_fragments(
                item.get(field),
                source_allowed=source_allowed.union(asset_allowed),
            )
            if unknown:
                raise ValueError(f"provider storyboard response has untranslated English in {field}")


def _source_is_latin_language(source_script_text: str) -> bool:
    text = str(source_script_text or "")
    return has_latin(text) and not has_cjk(text)


def _unapproved_latin_fragments(
    value: Any,
    *,
    source_allowed: set[str],
    field_allowed: set[str] | None = None,
) -> list[str]:
    allowed = set(field_allowed or set())
    unknown: list[str] = []
    seen: set[str] = set()
    for fragment in _latin_fragments(value):
        key = _latin_fragment_key(fragment)
        if not key or key in seen:
            continue
        seen.add(key)
        if _is_allowed_latin_fragment(key, source_allowed=source_allowed, field_allowed=allowed):
            continue
        unknown.append(fragment)
    return unknown


def _latin_fragments(value: Any) -> list[str]:
    fragments: list[str] = []
    for match in LATIN_FRAGMENT_RE.finditer(str(value or "")):
        fragment = match.group(0).strip("._'-")
        if fragment and re.search(r"[A-Za-z]", fragment):
            fragments.append(fragment)
    return fragments


def _latin_fragment_key(value: str) -> str:
    return token_key(value)


def _is_allowed_latin_fragment(key: str, *, source_allowed: set[str], field_allowed: set[str]) -> bool:
    if key in source_allowed or key in field_allowed or key in ALLOWED_LATIN_UNIT_TOKENS:
        return True
    possessive_base = _possessive_base_key(key)
    if possessive_base and (possessive_base in source_allowed or possessive_base in field_allowed):
        return True
    parts = [part for part in key.split("_") if part]
    if len(parts) > 1 and all(
        part in source_allowed
        or part in field_allowed
        or part in ALLOWED_LATIN_UNIT_TOKENS
        or _is_model_like_latin_key(part)
        for part in parts
    ):
        return True
    return _is_model_like_latin_key(key)


def _possessive_base_key(key: str) -> str:
    if key.endswith("_s") and len(key) > 2:
        return key[:-2]
    return ""


def _is_model_like_latin_key(key: str) -> bool:
    return bool(re.search(r"[a-z]", key)) and bool(re.search(r"\d", key))


def _source_latin_token_keys(source_script_text: str) -> set[str]:
    keys: set[str] = set()
    for fragment in _latin_fragments(source_script_text):
        key = _latin_fragment_key(fragment)
        if not key:
            continue
        keys.add(key)
        possessive_base = _possessive_base_key(key)
        if possessive_base:
            keys.add(possessive_base)
    return keys


def _asset_ref_latin_token_keys(asset_refs: Any) -> set[str]:
    if not isinstance(asset_refs, list):
        return set()
    keys: set[str] = set()
    for ref in asset_refs:
        if not isinstance(ref, dict):
            continue
        for fragment in _latin_fragments(ref.get("label")):
            key = _latin_fragment_key(fragment)
            if not key:
                continue
            keys.add(key)
            keys.update(part for part in key.split("_") if part)
    return keys


def _raw_field_allowed_latin_tokens(field: str) -> set[str]:
    tokens = set(FIELD_ALLOWED_RAW_LATIN_TOKENS.get(field, set()))
    if field == "shot_size":
        tokens.update(_latin_tokens_from_keys(SHOT_SIZE_LABELS))
    elif field == "camera_motion":
        tokens.update(_latin_tokens_from_keys(CAMERA_MOTION_LABELS))
        tokens.update(_latin_tokens_from_keys(FOCUS_TARGET_LABELS))
        tokens.update(ENGLISH_PHRASE_CONNECTOR_TOKENS)
        tokens.update({"focus", "mimic", "mimicked", "mimicking", "mimick", "jump", "leap"})
    elif field == "light_atmosphere":
        tokens.update(_latin_tokens_from_rule_keys(LIGHT_ATMOSPHERE_RULES))
        tokens.update(ENGLISH_PHRASE_CONNECTOR_TOKENS)
        tokens.update({"pooling"})
    elif field == "sound":
        tokens.update(_latin_tokens_from_rule_keys(SOUND_RULES))
        tokens.update(ENGLISH_PHRASE_CONNECTOR_TOKENS)
    return tokens


def _latin_tokens_from_keys(mapping: dict[str, str]) -> set[str]:
    tokens: set[str] = set()
    for key in mapping:
        normalized = token_key(key)
        if not normalized:
            continue
        tokens.add(normalized)
        tokens.update(part for part in normalized.split("_") if part)
    return tokens


def _latin_tokens_from_rule_keys(rules: tuple[tuple[tuple[str, ...], str], ...]) -> set[str]:
    tokens: set[str] = set()
    for required_tokens, _label in rules:
        for token in required_tokens:
            normalized = token_key(token)
            if not normalized:
                continue
            tokens.add(normalized)
            tokens.update(part for part in normalized.split("_") if part)
    return tokens


__all__ = ("validate_localized_display_fields", "validate_raw_display_field_english")
