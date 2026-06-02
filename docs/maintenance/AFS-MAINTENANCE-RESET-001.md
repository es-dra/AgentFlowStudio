# AFS-MAINTENANCE-RESET-001 - Classification Record

Status: classification complete. This record classifies the current dirty
checkout before more demo, provider, or Web implementation work is opened.

No provider calls were made for this maintenance pass. No local media,
generated runtime artifacts, model caches, or private Company knowledge-base
content should be promoted into Git by this reset.

## Why This Exists

The 2026-05-29 retro found that the project is carrying too much mixed
experiment, provider, Web, and acceptance state in one dirty checkout.

The tracker also contained invalid UTF-8 around an old Company memory path,
which made normal patch-based editing unsafe. The live tracker has therefore
been split from historical task history.

## Tracker Repair

Outcome:

- `TASK_TRACKER.md` is now a short UTF-8 live tracker for active, next, and
  blocked work.
- Historical task state was moved to `docs/archive/task_history_2026_05.md` at
  summary level.
- Raw pre-reset tracker bytes were preserved under ignored local evidence:
  `data/processed/maintenance_backups/AFS-MAINTENANCE-RESET-001/TASK_TRACKER.pre_reset_original_bytes.md`.

Validation target:

```powershell
$path='D:\Projects\AgentFlowStudio\TASK_TRACKER.md'
$bytes=[System.IO.File]::ReadAllBytes($path)
$utf8=[System.Text.UTF8Encoding]::new($false,$true)
$utf8.GetString($bytes) | Out-Null
```

## Dirty Worktree Classification

| Group | Current files / examples | Decision | Condition / next action |
|---|---|---|---|
| Local Alpha 0.4 acceptance and memory-quality docs | `docs/local_alpha_0_4_acceptance_reconciliation.md`, 0.4 goals/scenario docs, `AFS-MEMORY-QUALITY-002` handoff, related contract examples/tests | promote | Keep as current Local Alpha 0.4 evidence ledger. These are structural/runtime evidence docs, not human acceptance or business validation. |
| Web operator fixes | `apps/web/production-render.js`, `tests/test_web_production_mode_static.py`, `docs/handoff/AFS-WEB-OPERATOR-002.md` | promote after focused verification | Keep the stale-readiness blocker fix because it protects the 0.4 operator path. Do not add new Web product surface until `AFS-WORKBENCH-REDESIGN-001`. |
| Provider adapters and smoke clients | `agentflow_studio/model_gateway/kling_*`, `minimax_image_smoke.py`, CLI provider command files, provider tests | keep temporarily, then promote behind generic gateway boundary | Keep only if tests show no secret persistence, no ungated calls, sanitized manifests, and capability-specific gates. Later consolidate under a provider gateway instead of experiment commands. |
| Memory-advantage experiment code | `agentflow_studio/memory_advantage_demo_*`, `apps/cli/memory_demo_commands.py`, focused demo tests, demo handoffs | archive evidence, promote only generic parts | Do not add more numbered modules. Promote reusable protocol runner/review/contact-sheet pieces into `AFS-MEMORY-PIPELINE-MVP-001`; archive or remove bespoke demo modules after replacement. |
| RECORDING-016 script | `tools/run_memory_advantage_recording_016.ps1` and ignored run evidence | archive as demo evidence | Keep as a reproducibility artifact for competition material until a protocol-driven runner replaces it. Do not treat it as product command. |
| Task tracker / devlog / handoff archive | `TASK_TRACKER.md`, `DEVLOG.md`, `docs/archive/`, `docs/handoff/` | split and compress | Live tracker is fixed. `DEVLOG.md` remains too large and should be compressed into dated index entries in a follow-up cleanup if risk is acceptable. |
| Retrospectives and task briefs | `docs/retrospectives/`, `docs/task_briefs/AFS-MAINTENANCE-RESET-001.md`, `AFS-MEMORY-PIPELINE-MVP-001.md`, `AFS-WORKBENCH-REDESIGN-001.md` | promote | Use as the next operating queue. They should guide cleanup, pipeline MVP, and workbench redesign. |
| Ignored generated evidence | `data/processed/runs/*`, `data/raw/*`, `data/models/*` | keep ignored only | Do not commit. Reference by path only when needed for local review. |

## Numbered Memory-Advantage Demo Decisions

| Demo | Role in history | Decision | Retirement condition |
|---|---|---|---|
| DEMO-001 | Kling live-route probe and early setup | archive | Remove bespoke code after provider smoke behavior is covered by generic provider tests. |
| DEMO-002 | Three-shot fallback package | archive | Keep handoff as history; do not promote T2V fallback as core demo route. |
| DEMO-003 | T2I/I2V route isolation | archive | Keep only provider-learning notes; do not reopen as a product lane. |
| DEMO-006 / DEMO-007 | MiniMax/Kling transition and planning notes | archived as summary only | Long-form handoffs removed from the active handoff folder; experiment history remains in `docs/archive/task_history_2026_05.md`. |
| DEMO-008 / DEMO-009 / DEMO-010 | baseline-vs-memory prompt/protocol iterations | retired | Bespoke modules, tests, commands, and long-form handoffs removed after the generic protocol path replaced them. |
| DEMO-011 | character asset/visual memory card refinement | partially retired | Bespoke command/module/test removed; `memory_advantage_demo_011_content.py` remains temporarily as shared asset-card data for DEMO-012/015. |
| DEMO-012 | fixed reference -> MiniMax I2I keyframes -> Kling I2V comparison | promote evidence pattern | Treat as the first credible route pattern. Replace module with generic protocol runner. |
| DEMO-013 / DEMO-014 | 15s desert occlusion/recovery I2V | archive as comparison evidence | Useful for presentation, not enough for definitive proof. |
| DEMO-015 | memory-backed production protocol and 15s I2V runtime evidence | promote protocol concepts | Promote protocol-card, scorecard, and memory projection concepts into MVP runner. |
| RECORDING-016 | repeated same-keyframe I2V cross-run stability demo | promote as current strongest demo evidence | Use in competition materials with bounded claim: cross-run consistency and asset-anchor retention only. |

## Integration Plan

1. Keep this reset as the required entry record for the next implementation
   lane.
2. Continue `AFS-MEMORY-PIPELINE-MVP-001` from the new no-call protocol runner.
   Do not add numbered demo modules; extract reusable live execution/review
   pieces behind the protocol runner only.
3. Keep `AFS-WORKBENCH-REDESIGN-001` blocked until the product workflow and
   evidence states are described outside the Web implementation.
4. When implementation resumes, open isolated `codex/*` worktrees or use a
   clearly bounded main-checkout controller lane.

## Remaining Risks

- `DEVLOG.md` is still too large for a quick project memory surface.
- `agentflow_studio/model_gateway/kling_video_smoke.py` exceeds the 300-line ideal
  and needs consolidation or splitting before it becomes stable product code.
- `memory_advantage_demo_011_content.py` remains as shared legacy asset-card
  data for DEMO-012/015; migrate that shape into the generic protocol examples
  before deleting the last DEMO-011 file.
- Existing provider/demo files are useful but still mixed with experiment
  identity; the next MVP should load a protocol file instead of adding another
  numbered Python module.
- Memory-advantage results remain bounded evidence. They should be presented as
  repeatability and anchor-retention signals, not as statistical proof or
  business validation.

## Gate

Do not open a new numbered memory-advantage demo module or broad Web
implementation lane until this maintenance reset has fresh verification and the
next implementation lane starts from this classification record.
