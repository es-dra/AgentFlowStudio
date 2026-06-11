from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_KNOWLEDGE_ROOT = Path("agentflow/knowledge")
EXTERNAL_KNOWLEDGE_ROOT = Path(
    "D:/Learning materials/Learning_notes/10-Startup/70-Projects/AgentFlow-Studio/knowledgebase"
)
REGISTRY_FILE = "registry.json"
REQUIRED_RULE_FIELDS = {
    "rule_id",
    "domain",
    "priority",
    "weight",
    "applies_to",
    "required_slots",
    "prompt_transform",
    "negative_constraints",
    "quality_checks",
    "source_refs",
    "version",
}
REQUIRED_TRANSFORM_FIELDS = {"output_section", "guidance", "template"}
UNSAFE_FRAGMENTS = ("api_key", "bearer ", "signed_url", "provider_config", "data/processed/runs")


def load_registry(root: Path = REPO_KNOWLEDGE_ROOT) -> dict[str, Any]:
    path = root / REGISTRY_FILE
    if not path.exists():
        raise FileNotFoundError(f"Missing knowledgebase registry: {path}")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("artifact_type") != "agentflow_creative_prompt_knowledgebase_registry":
        raise ValueError("Invalid knowledgebase registry artifact_type")
    if not isinstance(registry.get("rule_files"), list) or not registry["rule_files"]:
        raise ValueError("Knowledgebase registry must list rule_files")
    return registry


def load_creative_prompt_rules(root: Path = REPO_KNOWLEDGE_ROOT) -> list[dict[str, Any]]:
    registry = load_registry(root)
    rules: list[dict[str, Any]] = []
    for relative_path in registry["rule_files"]:
        rule_path = root / str(relative_path)
        if not rule_path.exists():
            raise FileNotFoundError(f"Missing rule file: {rule_path}")
        for line_number, line in enumerate(rule_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            rule = json.loads(line)
            rule["_rule_file"] = str(relative_path)
            rule["_line_number"] = line_number
            validate_creative_prompt_rule(rule)
            rules.append(rule)
    rule_ids = [str(rule["rule_id"]) for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("Knowledgebase rule_id values must be unique")
    return rules


def validate_creative_prompt_rule(rule: dict[str, Any]) -> None:
    missing = REQUIRED_RULE_FIELDS - set(rule)
    if missing:
        raise ValueError(f"Rule {rule.get('rule_id', '<unknown>')} missing fields: {sorted(missing)}")
    if rule["priority"] != "professional_knowledge_base":
        raise ValueError(f"Rule {rule['rule_id']} must stay in professional_knowledge_base priority")
    if not isinstance(rule["weight"], (int, float)) or not 0 < float(rule["weight"]) <= 1:
        raise ValueError(f"Rule {rule['rule_id']} has invalid weight")
    if not isinstance(rule["applies_to"], dict):
        raise ValueError(f"Rule {rule['rule_id']} applies_to must be an object")
    if not isinstance(rule["prompt_transform"], dict):
        raise ValueError(f"Rule {rule['rule_id']} prompt_transform must be an object")
    transform_missing = REQUIRED_TRANSFORM_FIELDS - set(rule["prompt_transform"])
    if transform_missing:
        raise ValueError(f"Rule {rule['rule_id']} prompt_transform missing fields: {sorted(transform_missing)}")
    for list_field in ("required_slots", "negative_constraints", "quality_checks", "source_refs"):
        if not isinstance(rule[list_field], list) or not rule[list_field]:
            raise ValueError(f"Rule {rule['rule_id']} must have non-empty {list_field}")
    serialized = json.dumps(_public_rule(rule), ensure_ascii=False).lower()
    if any(fragment in serialized for fragment in UNSAFE_FRAGMENTS):
        raise ValueError(f"Rule {rule['rule_id']} contains unsafe payload fragment")
    if "\\" in serialized and ":\\\\" in serialized:
        raise ValueError(f"Rule {rule['rule_id']} appears to contain a local absolute path")


def normalized_knowledgebase_hash(root: Path = REPO_KNOWLEDGE_ROOT) -> str:
    registry = load_registry(root)
    digest = hashlib.sha256()
    digest.update(_canonical_json(_strip_volatile(registry)).encode("utf-8"))
    for relative_path in sorted(str(path) for path in registry["rule_files"]):
        digest.update(relative_path.encode("utf-8"))
        rule_path = root / relative_path
        lines = [line for line in rule_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            rule = _strip_volatile(json.loads(line))
            digest.update(_canonical_json(rule).encode("utf-8"))
    for relative_path in sorted(str(path) for path in registry.get("example_files", [])):
        digest.update(relative_path.encode("utf-8"))
        digest.update((root / relative_path).read_text(encoding="utf-8").strip().encode("utf-8"))
    return digest.hexdigest()


def assert_knowledgebase_in_sync(
    repo_root: Path = REPO_KNOWLEDGE_ROOT,
    external_root: Path = EXTERNAL_KNOWLEDGE_ROOT,
) -> None:
    repo_hash = normalized_knowledgebase_hash(repo_root)
    external_hash = normalized_knowledgebase_hash(external_root)
    if repo_hash != external_hash:
        raise AssertionError(f"Knowledgebase copies are out of sync: repo={repo_hash} external={external_hash}")


def select_creative_prompt_rules(
    rules: list[dict[str, Any]],
    *,
    node_type: str,
    generation_target: str,
    target_platform: str,
    slots: dict[str, str],
    limit: int = 12,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, str, dict[str, Any]]] = []
    slot_keys = {key for key, value in slots.items() if value}
    for rule in rules:
        score, reasons = _score_rule(rule, node_type, generation_target, target_platform, slot_keys)
        if score <= 0:
            continue
        selected = _public_rule(rule)
        selected["match_reason"] = "; ".join(reasons)
        selected["score"] = round(score, 4)
        scored.append((score, str(rule["rule_id"]), selected))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_rules = [item[2] for item in scored[:limit]]
    for rule_id in ("cinematography_shot_intent_v1", "lighting_mood_v1", "character_consistency_v1"):
        _ensure_rule_id(selected_rules, rules, rule_id, node_type, generation_target, target_platform, slot_keys)
    if node_type in {"image", "keyframe", "video", "director"} or generation_target in {"image", "keyframe", "video"}:
        _ensure_domain(selected_rules, rules, "production_design", node_type, generation_target, target_platform, slot_keys)
    _ensure_domain(selected_rules, rules, "negative_constraints", node_type, generation_target, target_platform, slot_keys)
    return selected_rules


def _ensure_rule_id(
    selected: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    rule_id: str,
    node_type: str,
    generation_target: str,
    target_platform: str,
    slot_keys: set[str],
) -> None:
    if any(rule["rule_id"] == rule_id for rule in selected):
        return
    for rule in rules:
        if rule["rule_id"] != rule_id:
            continue
        selected_rule = _public_rule(rule)
        selected_rule["match_reason"] = "required professional baseline"
        selected_rule["score"] = round(_score_rule(rule, node_type, generation_target, target_platform, slot_keys)[0], 4)
        selected.append(selected_rule)
        return


def _ensure_domain(
    selected: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    domain: str,
    node_type: str,
    generation_target: str,
    target_platform: str,
    slot_keys: set[str],
) -> None:
    if any(rule["domain"] == domain for rule in selected):
        return
    candidates = [rule for rule in rules if rule["domain"] == domain]
    if not candidates:
        return
    candidates.sort(key=lambda rule: (-float(rule["weight"]), str(rule["rule_id"])))
    fallback = _public_rule(candidates[0])
    fallback["match_reason"] = "required safety baseline"
    fallback["score"] = round(_score_rule(candidates[0], node_type, generation_target, target_platform, slot_keys)[0], 4)
    selected.append(fallback)


def _score_rule(
    rule: dict[str, Any],
    node_type: str,
    generation_target: str,
    target_platform: str,
    slot_keys: set[str],
) -> tuple[float, list[str]]:
    applies = rule["applies_to"]
    score = float(rule["weight"])
    reasons: list[str] = ["base professional rule"]
    if _contains(applies.get("node_types"), node_type):
        score += 0.35
        reasons.append(f"node_type={node_type}")
    if _contains(applies.get("generation_targets"), generation_target):
        score += 0.35
        reasons.append(f"generation_target={generation_target}")
    if _contains(applies.get("platforms"), target_platform):
        score += 0.1
        reasons.append(f"platform={target_platform}")
    matched_slots = sorted(slot_keys.intersection(set(applies.get("slots", []))))
    if matched_slots:
        score += min(0.4, len(matched_slots) * 0.08)
        reasons.append("slots=" + ",".join(matched_slots))
    if _contains(applies.get("languages"), "zh") and "language" in slot_keys:
        score += 0.05
        reasons.append("language-aware")
    return score, reasons


def _contains(values: Any, value: str) -> bool:
    return isinstance(values, list) and ("*" in values or value in values)


def _public_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in rule.items() if not key.startswith("_")}


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_volatile(val) for key, val in value.items() if not key.startswith("_")}
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


__all__ = (
    "EXTERNAL_KNOWLEDGE_ROOT",
    "REPO_KNOWLEDGE_ROOT",
    "assert_knowledgebase_in_sync",
    "load_creative_prompt_rules",
    "load_registry",
    "normalized_knowledgebase_hash",
    "select_creative_prompt_rules",
    "validate_creative_prompt_rule",
)
