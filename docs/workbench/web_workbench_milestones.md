# Web Workbench Milestones

This note keeps the milestone history that used to make `apps/web/README.md`
too long. The Web folder README should stay as the operator entry point.

## Review Mode

- M1.1 hardened safe local parsing for explicitly selected artifacts.
- M1.2 made the workbench Chinese-first with an in-memory language toggle.
- M1.2.1 tightened layout density, Chinese panel titles, empty states, and
  acceptance-oriented metrics.
- M1.3 expanded the artifact universe beyond the first package-run files.
- M1.4 shifted the first screen from artifact-first dashboard to
  production-oriented local review.
- M1.5 added explicit local video preview for selected `.mp4`, `.webm`, or
  `.mov` files only.
- M2 added browser-local feedback event copy for manual JSON export.

## Production Mode

M3 introduced a supervised production workspace backed only by the local Web
Bridge:

- workflow discovery from `workflows/*.yaml`;
- plan generation through the existing planner;
- input bundle diagnostics for missing local references;
- background workflow execution through the existing workflow engine;
- polling through `bridge_status.json`;
- review refresh through `inspect-run`, `review-run`, and `package-report`;
- step timeline, artifact timeline, current task, blockers, and supervision
  controls in the browser.

M3.1 added production readiness:

- product-facing workflow display names for local demo and full package paths;
- preflight panel for production target, local environment, input diagnostics,
  and next action;
- categorized blockers for local media, BGM, scripts, configs, and other file
  references;
- Production Mode video review for explicitly selected local files;
- honest supervision actions that record intent instead of pretending to pause,
  resume, or rerun Python;
- run-level feedback JSON with run/workflow context and optional video time.

Local Alpha 0.3/0.4 shaped the operator loop as workflow selection -> plan ->
supervised run -> artifact inspection -> review refresh -> feedback capture.

## Memory Workbench

M4 introduced the first static Memory Workbench screen:

- canvas-style view centered on AgentFlow's memory reuse loop;
- Baseline and Memory-backed lanes from a sanitized
  `agentflow_memory_video_pipeline_package` fixture;
- memory provenance with eligibility, evidence refs, promotion status, request
  projection, and feedback effect;
- state labels for no plan, planned, generating, review ready, feedback
  captured, memory candidate drafted, promotion decision ready, and blocked.

M4.1 through M4.9 added:

- explicit package loading from selected package JSON;
- selected bundle summaries for review, observation, presentation, and feedback
  draft JSON;
- evidence bundle visibility for selected, referenced-only, and missing refs;
- read-only artifact inspector cards;
- canvas-to-inspector focus;
- read-only workflow action strip;
- browser-local feedback draft preview;
- one-click sanitized sample bundle;
- evidence source status, Flow / Compare / Review view chips, protocol panel,
  and demo evidence summary.

M5 through M5.3 polished the AgentFlow Studio canvas:

- first screen framed as an evidence-first Studio Canvas;
- `#memory` and `#production` hash routes for demo/QA;
- demo-ready checklist for source/package, review evidence, observation notes,
  presentation summary, lane parity, feedback draft, and claim boundaries;
- readiness cockpit with `Can present`, `Evidence gaps`, and `Do not claim`;
- operator command dock for Brief -> Assets -> Memory -> Generate -> Compare ->
  Feedback.

All Memory Workbench controls remain local-only and read-only. They do not call
providers, call the bridge, scan directories, write artifacts, persist browser
state, or implement durable Memory runtime behavior.
