# Indirect Mentions Eval — Analysis Notes

Status: internal evaluation dimension v0.1.

## What this dimension scores

Per gold mention, against a fixed `context_snippet`:

| Field | Meaning |
|---|---|
| `refers_to_real_character` | Is the mention string itself a trackable person name/alias? |
| `is_present_in_scene` | Does that person have direct on-stage evidence in the snippet? |
| `is_indirect_mention` | Derived: `refers && !present` |

This is a **binary classification** problem, not clustering (aliases) or slot/relation missingness.

## Real candidate path

`run_against_llm.py` uses the **production** split-fields judge
(`apps.api.runtime_script_indirect_mention_proposals._default_remote_judge`)
on each gold snippet (oracle path).

It deliberately does **not** run full-script discovery+extract for scoring.
Full-script discovery cost scales with quote density and would burn dozens of
calls on the long scripts; judgment quality is the protocol for this dimension.

## Known limitation

`I5` 悦安 is `scoring_policy=known_limitation_excluded`.

Gold expects `refers=true, present=true` (林悦 on-stage acknowledges the alias).
Historical runs often returned `present=false`, which would look like a false
indirect mention if mixed into primary metrics. Boundary cases are reported
separately and do not enter FP/FN denominators. A single later run may pass;
the exclusion remains because the behavior is not yet stable enough to require.

## Shape-gate vs judgment score

Production proposal emission also applies `_is_person_name` after judgment.
Long quoted clauses that contain a person name (e.g. `I22`
`第七格——顾衡案——不得夜班单独开启。`) can still receive `refers=true` from the
raw LLM judge and count as a judgment FP here, even when the emit path would
drop them as proposals. This eval scores judgment fields, not emit filtering.

## Metric discipline

- Report refers / present / indirect rates separately.
- Separate false-positive rate (noise → person/indirect) from false-negative
  rate (missed true indirect mention).
- Do not invent a single composite score with aliases or missing-evidence.

## 2026-08-06 real score snapshot

- Required cases: 23; LLM calls: 24 (includes boundary I5); wall ~95s.
- True indirect (沈岚/江澄/顾衡/柯衡): 4/4 TP on refers and derived indirect.
- Noise: 18/19 TN; **1 FP** on I22 long quoted clause (`refers=true`).
- Derived indirect accuracy: **0.957**; FP rate **0.053**; FN rate **0.0**.
- Boundary I5 悦安 on this run: present=true (passes gold); still excluded.
