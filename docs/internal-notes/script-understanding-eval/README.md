# Script Understanding Eval Framework

Status: internal evaluation framework v0.1.

This framework measures the quality of script-understanding candidate proposals.
It does not confirm facts, write authoritative Production Graph state, perform
human acceptance, validate generated media, or prove business readiness.

## Purpose

The framework keeps representative script-understanding evaluations in one
place while preserving each dimension's verified scoring protocol. Different
dimensions keep separate metrics because they measure different failure modes;
the framework reports health and coverage instead of inventing a combined score.

## Current Dimensions

| Dimension | Path | What it measures | Key metrics |
|---|---|---|---|
| Aliases | `aliases/` | Whether candidate identity clusters link alias surfaces that should be the same person without false merges. | macro BCubed F1, linkable-cluster coverage, false split rate, false merge rate, hard-fail count |
| Missing evidence | `missing-evidence/` | Whether slot-level and `scene_cast` relationship judgments correctly mark missing versus present evidence. | missing judgment accuracy, false-positive missing rate, false-negative missing rate, relation judgment coverage |

Each dimension includes gold cases, its scorer, a way to produce current real
candidates, and saved analysis/report artifacts.

## Not Covered

Long scripts are not a separate v0.1 dimension. Current analysis treats long
scripts as an amplifier for alias linking, mention discovery, and indirect
mention failures; adding a separate long-script score would duplicate those
dimensions without a clearer protocol.

Indirect mentions are also not a v0.1 dimension. Current judgment is that they
need model-assisted candidate generation or policy support before a stable
offline scoring protocol would be meaningful.

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
- writes `script_understanding_eval_summary.json`;
- updates each dimension's saved real score report.

You can still run a dimension directly from its subdirectory, using that
dimension's local scripts and `gold_cases.json`.

## Framework Health

Framework health answers three questions:

1. Which dimensions are currently covered.
2. Whether each dimension's scoring protocol has been checked with synthetic
   data that should produce known pass/fail behavior.
3. What the current real candidate path scores for that dimension.

It does not average alias F1 with missing-evidence accuracy. Those numbers are
not commensurate.

## Adding A Dimension

Add a new dimension as a sibling directory, for example `long-scripts/` only if
it has a distinct protocol.

Use this pattern:

- `gold_cases.json` with stable case IDs and explicit expected judgments.
- one scorer script that can score supplied candidate JSON.
- synthetic scorer checks with at least a perfect case and one meaningful
  failure mode.
- one real-candidate runner or generator for the current implementation path.
- saved candidate/report artifacts when useful for analysis.
- a short `ANALYSIS.md` if the dimension has interpretation caveats.
- a `run_all.py` adapter that reports dimension-level metrics and protocol
  verification without changing the scorer's internal logic.

Candidate outputs remain proposals. A passing score does not authorize automatic
confirmation or durable graph writes.
