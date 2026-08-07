# Indirect Mentions Eval — Analysis Notes

Status: research / verification-only evaluation dimension v0.1.

## What this dimension scores

Per gold mention, against a fixed `context_snippet`:

| Field | Meaning |
|---|---|
| `refers_to_real_character` | Is the mention string itself a trackable person name/alias? |
| `is_present_in_scene` | Does that person have direct on-stage evidence in the snippet? |
| `is_indirect_mention` | Derived: `refers && !present` |

This is a **binary classification** problem, not clustering (aliases) or
slot/relation missingness.

## Candidate input for scoring

The scorer only needs a JSON object of per-case structured judgments:

- `refers_to_real_character` (bool)
- `is_present_in_scene` (bool)
- optional `is_indirect_mention` (derived if omitted)
- optional confidence/reason strings for human review

This research slice ships:

1. `gold_cases.json` — hand-authored expectations
2. `score_indirect_mentions.py` — offline scorer (no production imports)
3. `llm_candidates.json` / `llm_score_report.json` — historical structured
   snapshots from a prior paid oracle run (judgment fields only; no raw
   provider HTTP bodies, no `raw_judgment_text`)

A production extract path or paid runner is **not** part of this PR. Those
belong in a later, separate production PR if the protocol is adopted.

## Known limitation

`I5` 悦安 is `scoring_policy=known_limitation_excluded`.

Gold expects `refers=true, present=true` (林悦 on-stage acknowledges the alias).
Historical runs often returned `present=false`, which would look like a false
indirect mention if mixed into primary metrics. Boundary cases are reported
separately and do not enter FP/FN denominators. A single later run may pass;
the exclusion remains because the behavior is not yet stable enough to require.

## Shape-gate vs judgment score

If a production emit path later applies a person-name shape gate after
judgment, long quoted clauses that contain a person name (e.g. `I22`
`第七格——顾衡案——不得夜班单独开启。`) can still receive `refers=true` from the
judge and count as a judgment FP here, even when emit filtering would drop
them as proposals. This eval scores **judgment fields**, not emit filtering.

## Metric discipline

- Report refers / present / indirect rates separately.
- Separate false-positive rate (noise → person/indirect) from false-negative
  rate (missed true indirect mention).
- Do not invent a single composite score with aliases or missing-evidence.

## 2026-08-06 historical score snapshot (structured candidates)

Reproducible offline by scoring the checked-in `llm_candidates.json`:

- Required cases: 23; historical LLM calls: 24 (includes boundary I5); wall ~95s.
- True indirect (沈岚/江澄/顾衡/柯衡): 4/4 TP on refers and derived indirect.
- Noise: 18/19 TN; **1 FP** on I22 long quoted clause (`refers=true`).
- Derived indirect accuracy: **0.957**; FP rate **0.053**; FN rate **0.0**.
- Boundary I5 悦安 on that run: present=true (passes gold); still excluded.
