# DEVLOG

Status: active short development log. Keep this file as the current-session
ledger only; move long historical narrative into `docs/archive/` or focused
handoff files.

Current references:

- Live work ledger: `TASK_TRACKER.md`.
- Full rename maintainability pass:
  `docs/maintenance/AFS-FULL-RENAME-MAINTAINABILITY-001.md`.
- Mainline foundation cleanup:
  `docs/maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md`.
- Maintenance slimming boundary:
  `docs/maintenance/AFS-MAINTENANCE-SLIMMING-001.md`.
- Historical DEVLOG archive:
  `docs/archive/devlog_history_2026_06_03_pre_slimming.md`.
- Historical task archive:
  `docs/archive/task_history_2026_06_03_pre_slimming.md`.

## 2026-06-03 - Full Rename Maintainability 001

- Opened `codex/afs-full-rename-maintainability-001` from clean
  `origin/master` to perform the requested full public rename in one pass.
- Renamed package metadata to `agentflow-studio`, moved Python imports to
  `agentflow_studio`, nested production handoff code under
  `agentflow_studio.production`, and replaced public runtime gates with the
  `AFS_*` prefix.
- Replaced the public console script with `afs` and removed the legacy console
  script. Short Production Memory commands are now the visible product surface;
  old long `production-memory-loop-*` commands remain hidden aliases for
  internal compatibility.
- Boundary kept: no provider calls, Company KB writes, runtime media commits,
  durable-memory claim, human acceptance claim, or business validation claim.

## 2026-06-03 - Maintenance Slimming 001

- Opened `codex/afs-maintenance-slimming-001` from clean `origin/master`
  after branch/worktree cleanup left `master` as the local and remote mainline.
- Scoped this maintenance pass to five low-risk consolidation nodes:
  documentation/status slimming, CLI product surface layering, Web artifact
  registry consolidation, Production Memory asset facade, and ignored runtime
  cleanup manifest.
- Boundary kept: no provider calls, Company KB writes, Loulan-specific
  adaptation, durable-memory claim, human acceptance claim, or business
  validation claim.

## 2026-06-03 - Mainline Foundation Cleanup 001

- Merged PR #80 into `master`, making the remote mainline include the complete
  deterministic Production Memory Asset Loop through the read-only Web cockpit.
- Audited `codex/loulan-memory-pilot` as pressure-sample evidence, preserved
  it as an archive tag, adopted only generic positioning lessons, and removed
  stale feature branches/worktrees.
- Recorded boundaries in
  `docs/maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md`.

## Archive

- Pre-slimming DEVLOG history:
  `docs/archive/devlog_history_2026_06_03_pre_slimming.md`.
- Pre-slimming task tracker history:
  `docs/archive/task_history_2026_06_03_pre_slimming.md`.
- Older pre-reset tracker history:
  `docs/archive/task_history_2026_05.md`.
