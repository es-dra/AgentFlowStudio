# Long-script runtime stability — protocol

Status: internal evaluation dimension v0.1.

## What this is (and is not)

| | |
|---|---|
| **Is** | Operability / stability under longer and varied scripts |
| **Is not** | Understanding accuracy (alias linking, missing evidence, indirect-mention judgment quality) |

Today's conclusion stands: long scripts amplify alias / indirect-mention *correctness* failures; those scores live in their own dimensions. Re-measuring F1/accuracy on long text would duplicate work and look like a fourth accuracy dimension when it is not.

## Checklist probes

1. **Deterministic free-path bit-stability**  
   Same script twice → identical digests for:
   - indirect-mention *discovery* (free)
   - character + scene extraction
   - alias link proposals
   - scene-name normalization proposals  

2. **Discovery volume bounded**  
   Per-script discovery count ≤ soft ceiling (warn/fail checklist) and hard ceiling (hard fail).  
   Also report `discovery_per_1k_chars` so growth vs length is visible without inventing a fake regression R².

3. **Paid budget truncation**  
   `build_indirect_mention_proposals(..., max_calls=N)` with a **mock judge**:
   - `judged_count == min(discovered, N)`
   - `len(budget_skipped) == max(0, discovered - N)`
   - never silently drops over-budget mentions

4. **Crash-free**  
   No uncaught exception on the above paths.

## Explicitly out of scope

- Bit-exact repeatability of **remote LLM** judgments (not deterministic).
- Accuracy of refers/present/indirect labels (covered by `indirect-mentions/`).
- Open-vocabulary unquoted CJK NER (intentionally disabled; enabling it would explode volume — that is a product decision, not this checklist).

## Synthetic scorer checks

Hand-written observation payloads:

- `perfect` → all probes pass  
- `nondeterministic` → free-path digest mismatch fails  
- `budget_bypass` → judged_count > max_calls fails  

## Cost

Default real runner uses **zero** remote LLM calls (mock judge). Optional
`--live-smoke` (not wired into `run_all.py`) may issue a single budget-capped
live call for one script if manually requested.

## Budget semantics note

`AFS_INDIRECT_MENTION_LLM_MAX_CALLS` applies to **eligible** discoveries after
known-identity suppression (`already_extracted_as_character` /
`suppressed_known_identity`), not to the raw discovery count. Checklist
expectation uses `eligible = discovered - suppressed`.
