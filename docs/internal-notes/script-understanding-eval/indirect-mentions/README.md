# Indirect Mentions — Research / Verification Protocol

Status: **research / verification-only** (v0.1).

This directory is a self-contained evaluation protocol for indirect-mention
judgment quality. It does **not** wire anything into production extract,
analysis-candidates, or Studio.

## What is in this PR slice

| File | Role |
|---|---|
| `gold_cases.json` | Hand-authored gold: mention + `context_snippet` + expected booleans |
| `score_indirect_mentions.py` | Offline scorer (stdlib only; no `apps.api`) |
| `ANALYSIS.md` | Metric contract, known limitations, historical snapshot notes |
| `llm_candidates.json` | Historical structured judgments (no raw provider payloads) |
| `llm_score_report.json` | Historical score from scoring those candidates |

## What is intentionally out of scope here

- Production modules (`apps/api/runtime_script_indirect_mention_*.py`)
- Prototype runners under `tools/indirect_mention_*.py`
- Any paid LLM harness that imports production judge code
- Raw provider HTTP bodies / `raw_judgment_text` dumps

Production wiring (if adopted later) belongs in a **separate** PR after this
protocol is reviewed.

## How to run (no network, no provider)

From repo root:

```bash
# Synthetic perfect predictions (scorer self-check)
python3 docs/internal-notes/script-understanding-eval/indirect-mentions/score_indirect_mentions.py \
  docs/internal-notes/script-understanding-eval/indirect-mentions/gold_cases.json \
  --synthetic perfect --pretty

# Score the checked-in historical structured candidates
python3 docs/internal-notes/script-understanding-eval/indirect-mentions/score_indirect_mentions.py \
  docs/internal-notes/script-understanding-eval/indirect-mentions/gold_cases.json \
  docs/internal-notes/script-understanding-eval/indirect-mentions/llm_candidates.json \
  --pretty
```

## Notes on `source_script` paths in gold

Some gold rows list a `source_script` path that lived on an exploratory branch.
The authoritative input for scoring is the embedded `context_snippet`; missing
external script files do not block the scorer.
