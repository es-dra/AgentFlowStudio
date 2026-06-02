# AgentFlow Studio Development Retro - 2026-05-29

Status: reflective project review based on current worktree evidence. This is
not a release note and not a product acceptance decision.

## Evidence Base

Observed current state:

- Branch: `master...origin/master [ahead 14]`.
- Worktree: heavily dirty. Local Alpha 0.4, Web operator, Memory quality,
  Kling/MiniMax provider, and memory-advantage demo changes are mixed in one
  checkout.
- Visible repository files: 568.
- Memory-advantage demo source files under `agentflow_studio/`: 19.
- Demo/provider test files: 12.
- Demo/provider handoff files: 10.
- Large maintenance hotspots:
  - `DEVLOG.md`: 3255 lines.
  - `TASK_TRACKER.md`: 692 lines.
  - `apps/cli/memory_demo_commands.py`: 485 lines.
  - `agentflow_studio/model_gateway/kling_video_smoke.py`: 428 lines.
  - `apps/web/styles.css`: 452 lines.
  - `apps/web/index.html`: 429 lines.

Recent evidence considered:

- Local Alpha 0.4 real local run succeeded under ignored runtime evidence.
- Web operator path was patched to point at Local Alpha 0.4 and avoid stale
  readiness blockers.
- Memory evidence reuse review now validates the structural chain from runtime
  evidence to second-pass prompt without writing durable memory.
- DEMO-012 established the useful route: fixed character reference -> MiniMax
  I2I keyframes -> Kling I2V storyboard comparison.
- DEMO-014 and DEMO-015 produced 15-second Kling I2V comparison material.
- RECORDING-016 produced the strongest current signal: repeated same-task,
  same-keyframe runs where baseline varied more and memory-backed outputs stayed
  more structurally consistent.

## Executive Conclusion

AgentFlow Studio has crossed an important proof threshold. The team can now run
a complete local/video-generation evidence loop and explain why the memory
architecture matters. The strongest current demo signal is not "longer prompt
wins"; it is cross-run stability from structured asset, scene, and feedback
memory.

The engineering process has also drifted away from the company's own operating
rules. The repository absorbed too many experiment-specific files, handoffs,
and one-off demo modules. It can prove ideas quickly, but it is becoming harder
to maintain, review, and hand off.

The next milestone should not be another ad hoc demo. It should be a
maintenance reset plus a small productized pipeline:

```text
reference asset + script
-> memory compiler / asset cards
-> keyframe generation
-> I2V generation
-> side-by-side review
-> feedback capture
-> memory candidate / promotion decision
-> next context bundle
```

The workbench should become the operator surface for that loop. The current Web
UI is a useful local technical workbench, not the formal product workspace.

## Company Charter Follow-Through

What worked:

- Provider calls stayed gated by capability. Image, video, ASR, and LLM
  authorization remained separate.
- Secrets, provider URLs, JWTs, local media, model caches, and generated media
  stayed out of Git.
- Reports repeatedly separated structural verification, runtime verification,
  human acceptance, business validation, provider smoke, and durable Memory
  runtime.
- Experiments moved toward explicit protocol: same source keyframe, same
  provider, same duration, same user task, with only memory context changing.
- The final demo framing improved from prompt engineering to memory-backed
  production.

What failed:

- Too much substantial work happened in the main checkout after it became
  dirty. The rules say nontrivial or parallel work should use isolated
  `codex/*` worktrees with explicit write scopes.
- Experiment code accumulated as numbered modules. That optimized for speed but
  not for a maintainable product surface.
- `TASK_TRACKER.md` became a historical archive instead of a live tracker.
- `DEVLOG.md` became too large to serve as a quick memory surface.
- Web work was repeatedly patched around the current run instead of redesigned
  around the future operator workflow.
- Green tests did not prevent architectural sprawl.

The AI-native operating system helped us move fast, but did not enforce enough
cleanup pressure after each fast loop. The process needs a stronger
"promotion or archive" rule for experimental code and docs.

## Maintenance Debt

The current redundancy has three layers.

Code redundancy:

- Experiment identity is encoded in Python module names and CLI surfaces.
- Future agents may read old demo modules as active product paths.
- Provider adapters and experiment orchestration are mixed too closely.

Correction:

```text
experiments/<experiment_id>/protocol.json
generic experiment runner
generic provider adapters
generic review/contact-sheet tools
archived historical handoffs
```

Documentation redundancy:

- Docs currently serve as tracker, devlog, handoff archive, acceptance ledger,
  roadmap, phase history, experiment report, and operating model.
- This looks documented but slows down entry.

Correction:

- Keep `TASK_TRACKER.md` to active, next, and blocked tasks.
- Move old completed rows to `docs/archive/task_history_YYYY_MM.md`.
- Keep `DEVLOG.md` to short dated pointers.
- Move long analysis to `docs/retrospectives/` or `docs/experiments/`.
- Keep one current "next action" file instead of several competing handoffs.

UI redundancy:

- The Web workbench grew from artifact viewer into production mode, readiness
  view, review surface, feedback helper, bridge status display, and operator
  panel.
- It does not yet embody the core product loop:

```text
project -> assets -> memory -> generation -> review -> feedback -> reuse
```

Until it does, Web changes will continue to feel like patches.

## Current Product State

What is basically working:

- Local Alpha 0.4 proves a local media/script/BGM workflow can run.
- The package can be inspected and reviewed.
- Web can point at the run and show local readiness.
- Memory evidence reuse can be structurally validated.
- MiniMax can generate character-referenced keyframes.
- Kling can generate 15-second I2V videos from selected keyframes.
- The same user task can be run through baseline and memory-backed lanes.
- Repeated RECORDING-016 runs showed baseline variability and memory-backed
  cross-run consistency.

What is not yet productized:

- The full memory-advantage pipeline is not yet one formal product command.
- The current route is stitched from scripts, demo modules, and manual review.
- The workbench is not ready for formal daily use.
- Durable Memory runtime is not implemented.
- Human acceptance feedback is not yet a first-class persisted loop.
- Business validation is not performed.
- GitHub maintenance is behind the pace of local experimentation.

Product state in one sentence:

```text
AgentFlow Studio is a strong experimental prototype for evidence-backed AI
production, with a working local/video path and a compelling memory advantage
demo, but it needs cleanup and productization before it can become a
maintainable workbench-driven product.
```

## Operating Rules To Enforce

Rule 1: experiment code must have a retirement path.

Every new experiment declares one of:

- promote to generic runner;
- archive as evidence;
- delete after successful replacement.

Rule 2: live tracker must stay live.

`TASK_TRACKER.md` should contain active tasks, next tasks, blocked tasks, and
links to archives. Completed historical detail moves out.

Rule 3: devlog becomes an index.

`DEVLOG.md` stores date, change summary, link to detailed doc, and
verification. Long analysis belongs elsewhere.

Rule 4: workbench changes need product design first.

No more Web patching without:

```text
operator goal
primary workflow
states
loaded evidence
review action
feedback action
```

Rule 5: memory advantage claims need repeatability evidence.

A stronger claim needs:

- same source;
- same user task;
- at least two runs per lane when budget allows;
- cross-run consistency observation;
- named anchor-retention evidence;
- human review boundary.

## Recommended Next Actions

Immediate next work:

1. Create a maintenance-reset branch or worktree.
2. Classify all current uncommitted changes into coherent groups.
3. Replace numbered memory-advantage demo code with one protocol-driven runner
   where practical.
4. Archive historical handoffs and compress the active tracker.
5. Create a workbench redesign brief before touching Web UI again.
6. Create a local Memory MVP brief centered on asset cards, promotion
   decisions, context bundles, and feedback capture.
7. Use RECORDING-016 as the current strongest demo case in competition
   material, with the claim limited to cross-run consistency and asset-anchor
   retention.

The next product milestone:

```text
AgentFlow Studio can run one memory-backed video production experiment from a
single protocol file, show baseline versus memory-backed outputs in the
workbench, capture human feedback, and generate the next memory candidate
without adding another bespoke demo module.
```

## Final Reflection

The project is closer to the real goal than it was before these experiments.
The memory architecture is no longer just a concept: repeated video tests
showed that structured memory can reduce output variance and preserve assets
across generation.

But the way we reached that insight was too expensive for the codebase. The
next phase should treat maintainability as a product feature. For an AI-native
one-person company, the repository is not just code; it is the operating memory
of the company. If it becomes noisy, the company gets slower.

The right response is not to stop experimenting. It is to make experiments
cheaper to run, easier to compare, and easier to retire.
