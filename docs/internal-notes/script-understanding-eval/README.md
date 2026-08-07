# Script Understanding Eval Framework

Status: **research / verification-only** (v0.1).

This framework measures script-understanding candidate quality **and** long-text
runtime stability. It does not confirm facts, write Production Graph state,
perform human acceptance, validate generated media, or prove business readiness.

Baseline for this slice: current `origin/master` (no production code changes).

## Dimensions in this PR (3 / 4)

| Category | Dimension | Path | What it measures |
|---|---|---|---|
| Understanding correctness | Aliases | `aliases/` | Identity-cluster linking without false merges |
| Understanding correctness | Missing evidence | `missing-evidence/` | Slot / `scene_cast` missing vs present judgments |
| Runtime stability | Long scripts | `long-scripts/` | Checklist: free-path determinism, discovery ceilings, budget truncate, crash-free |

### Fourth dimension (already shipped separately)

**Indirect mentions** live in PR **#235**
(`docs/internal-notes/script-understanding-eval/indirect-mentions/`).
This PR does **not** re-copy that tree (avoid double-shipping). After #235 merges,
the four directories sit under the same parent path.

## Research-only discipline

Included:

- Gold / corpus JSON, offline scorers, historical structured candidate/observation
  snapshots, analysis notes, and this orchestration entrypoint.

Excluded (same rule as #235):

- Any `apps.api` / production module changes
- Production-dependent runners:
  - `missing-evidence/run_against_runtime.py`
  - `long-scripts/run_stability_checks.py`
  - (indirect) `run_against_llm.py` — already out of #235
- Raw provider HTTP bodies / `raw_judgment_text`

`run_all.py` in this slice:

- runs **synthetic** protocol self-checks for all three dimensions;
- regenerates alias candidates via the **stdlib** `deterministic_alias_proposer.py`;
- scores checked-in historical snapshots for missing-evidence and long-scripts
  (no live runtime / no provider).

## Running

From this directory (stdlib only — no venv required for scorers):

```bash
python3 run_all.py --pretty
```

Or per dimension:

```bash
python3 aliases/score_alias_linking.py aliases/gold_cases.json --synthetic perfect --pretty
python3 missing-evidence/score_missing_evidence.py missing-evidence/gold_cases.json --synthetic perfect --pretty
python3 long-scripts/score_long_script_stability.py long-scripts/corpus.json --synthetic perfect --pretty
```

## Framework health

Reports which dimensions are covered and whether each scoring protocol passes
synthetic checks. It does **not** average alias F1 with missing-evidence accuracy
or long-script checklist rates — those numbers are not commensurate.

## Notes on external corpus paths

`long-scripts/corpus.json` lists `path` fields that historically pointed at
exploratory script files outside this tree. Offline scoring of checked-in
`stability_observations.json` does not require those files to be present.
