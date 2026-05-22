# Post-v0.1.0 Plan

This page records the first operating plan after the NarratoCut `v0.1.0`
delivery closeout.

NarratoCut is the distribution-side short-video highlight, packaging, report,
and review module of AgentFlow Studio. The repository container was later
renamed to `AgentFlowStudio`; the post-`v0.1.0` goal remains to protect the
local-first CLI/Agent MVP while preparing the next workstreams without turning
the stable distribution module into a premature hosted platform runtime.

## Baseline

Current release baseline confirmed during the post-`v0.1.0` startup scan:

- branch: `master`
- remote at release time: `git@github.com:es-dra/NarratoCut.git`
- `master`, `origin/master`, and `v0.1.0^{}`: `bf5e7a1`
- `v0.1.0` tag type: annotated tag
- `v0.1.0` tag object: `460deba`
- working tree: clean at scan time

This baseline is a release state, not a frozen product state. Future sessions
must still run fresh verification before making new delivery or release claims.

## Release Meaning

`v0.1.0` means:

```text
Local-first CLI/Agent MVP for distribution-side short highlight packaging.
```

It does not mean:

```text
Full AgentFlow Studio platform, Web UI product, automatic publishing system,
or mature multimodal creative-selection engine.
```

## Operating Priorities

### 1. Stability First

Keep `v0.1.0` usable while other workstreams open.

Do:

- fix contract, report, documentation, or delivery-readiness regressions
- keep the recommended local workflows executable
- keep examples and docs aligned with the actual artifact surface
- run fresh verification before release, tag, PR, or handoff claims

Avoid:

- changing artifact contracts without migration notes and tests
- replacing the CLI-first path with Web/API assumptions
- committing local media, model caches, generated runs, or secrets
- calling remote LLM/ASR providers unless explicitly opted in

### 2. Web UI Branch

The first Web UI branch should be a viewer, not an editor.

Recommended branch objective:

```text
NarratoCut package/run viewer for existing local artifacts.
```

The branch should consume stable artifacts in this order:

1. `run_manifest.json` and `artifact_index`
2. `finished_package_manifest.json`
3. `package_report.md`
4. `review_report.json`
5. `quality_report.json`
6. `delivery_readiness.json` when present
7. `feedback.jsonl` for user feedback

Expected viewer capabilities:

- open a chosen local run or package directory
- show run metadata and artifact availability
- play `final_video_with_bgm.mp4` or the best available final video
- list selected clips with reasons and quality status
- render `package_report.md`
- show review checks, warnings, and `delivery_status`
- append user feedback using the feedback contract

Out of scope for the first Web UI branch:

- timeline editing
- transition templates
- automatic publishing
- hosted accounts, database, queue, or permissions
- real-time workflow orchestration
- custom media upload management beyond reading local artifacts

Merge condition:

- the viewer reads artifact contracts instead of hard-coding demo paths
- missing optional artifacts are shown as unavailable, not treated as crashes
- no generated media or run outputs are committed
- local browser verification covers at least one fixture or ignored local run

### 3. AgentFlow Studio Mainline

The mainline should expand architecture and contracts before runtime.

Near-term architecture documents should define:

- AgentFlow Studio top-level module map
- NarratoStudio production-side artifact contracts
- AgentFlow Skills task/skill contract boundaries
- AgentFlow Router MVP scope and non-goals
- AgentFlow Memory feedback and learning contract
- how NarratoCut package artifacts flow into downstream publishing or feedback

Boundaries:

- do not rename Python packages, workflows, artifacts, or CLI commands in this
  post-release lane
- do not add a platform runtime inside NarratoCut before the contracts are clear
- keep AgentFlow keys machine-readable and stable
- keep human-facing product docs clear about what is implemented versus planned

### 4. Highlight Quality Lane

Selection-quality work should stay measurable and artifact-driven.

Useful next slices:

- richer rejected-candidate reasons in `selection_diagnostics.json`
- clearer platform-profile influence on ranking and packaging
- stronger evidence fusion between transcript, script, OCR, audio, and future
  visual signals
- more flexible clip-boundary policy when local evidence supports it
- acceptance samples that separate execution correctness from editorial quality

Each quality slice needs:

- a focused hypothesis
- a baseline run or fixture
- an artifact path for evidence
- a metric or warning condition
- a clear residual-risk note

## Decision Points

Choose the next branch by user goal:

- Delivery polish: update release notes, handoff docs, and guide clarity on
  `master` or a small docs branch.
- Web UI: open a dedicated viewer branch and consume existing artifacts only.
- AgentFlow Studio: open a mainline architecture/contracts branch.
- Selection quality: open a focused quality branch with deterministic tests and
  current local acceptance reruns.

The default next step is not to modify core workflow behavior. The default is
to keep the released MVP stable and make the next branch consume its contracts.
