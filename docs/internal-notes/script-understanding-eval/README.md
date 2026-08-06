# Script Understanding Eval Framework

Status: internal evaluation framework v0.1.

This framework measures script-understanding candidate quality **and** long-text
runtime stability. It does not confirm facts, write authoritative Production
Graph state, perform human acceptance, validate generated media, or prove
business readiness.

## Purpose

The framework keeps representative evaluations in one place while preserving
each dimension's verified scoring protocol. Dimensions measure **different
failure categories**; the framework reports health and coverage instead of
inventing a combined score.

## Current Dimensions (4 / 4)

Two categories of question:

| Category | Dimension | Path | What it measures | Key metrics |
|---|---|---|---|---|
| **Understanding correctness** | Aliases | `aliases/` | Whether identity clusters link alias surfaces that should be the same person without false merges. | macro BCubed F1, linkable-cluster coverage, false split / false merge rates, hard-fail count |
| **Understanding correctness** | Missing evidence | `missing-evidence/` | Whether slot-level and `scene_cast` judgments correctly mark missing versus present evidence. | missing judgment accuracy, FP/FN missing rates, relation coverage |
| **Understanding correctness** | Indirect mentions | `indirect-mentions/` | Whether paid LLM split-field judgments classify person-reference vs on-stage presence (and derived indirect). | refers/present/indirect accuracy, precision, recall; FP vs FN separately |
| **Runtime stability / operability** | Long scripts | `long-scripts/` | Whether free deterministic paths stay bit-stable on long+generalization scripts, discovery volume stays bounded, paid LLM budgets truncate, and the pipeline does not crash. | checklist pass rate; free-path determinism rate; soft/hard discovery ceilings; budget enforcement rate; crash-free rate |

Coverage: **4 / 4**. These are not four parallel accuracy scores.

### Why long-scripts is stability, not accuracy

Long scripts amplify alias and indirect-mention *correctness* failures; those
are already scored in `aliases/` and `indirect-mentions/`. Re-running those
accuracy metrics on longer text would duplicate information and contradict the
finding that “long script” is not a separate understanding problem.

`long-scripts/` therefore uses a **checklist protocol** (self-consistency +
boundary behavior), not precision/recall gold labels.

## Running

From this directory:

```bash
python run_all.py --pretty
```

If the active shell does not have the runtime dependencies installed, pass the
repository virtualenv explicitly:

```bash
python run_all.py --python /path/to/.venv/bin/python --pretty
```

The unified runner:

- runs scorer synthetic checks for each dimension;
- regenerates alias deterministic candidates and scores them;
- runs the missing-evidence runtime extraction harness and scores it;
- runs the indirect-mention oracle LLM harness (paid) and scores it;
- runs long-script stability observations (**mock judge, zero remote LLM by default**) and scores the checklist;
- writes `script_understanding_eval_summary.json`;
- updates each dimension's saved real score report.

**Cost note:** indirect-mentions real path issues one remote LLM call per gold
case. Long-scripts default path issues **no** remote LLM calls (budget probe
uses a mock judge). Requires `AFS_ALLOW_REMOTE_LLM=true` only for the
indirect-mentions real path.

You can still run a dimension directly from its subdirectory.

## Framework Health

Framework health answers:

1. Which dimensions are covered.
2. Whether each dimension's scoring protocol was checked with synthetic data.
3. What the current real candidate / observation path scores for that dimension.

It does not average alias F1 with missing-evidence accuracy, indirect-mention
binary rates, or long-script checklist rates. Those numbers are not commensurate.

## Adding A Dimension

Add a sibling directory only if it has a **distinct** protocol (accuracy vs
stability vs another category).

Use this pattern:

- corpus or `gold_cases.json` with stable IDs;
- one scorer that can score supplied candidate/observation JSON;
- synthetic scorer checks (perfect + meaningful failure modes);
- one real runner for the current implementation path;
- saved report artifacts;
- short `PROTOCOL.md` / `ANALYSIS.md` when interpretation caveats matter;
- a `run_all.py` adapter that reports dimension-level metrics without changing
  the scorer's internal logic.

Candidate outputs remain proposals. A passing score does not authorize automatic
confirmation or durable graph writes.
