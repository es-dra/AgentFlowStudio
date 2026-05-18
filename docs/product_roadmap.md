# Product Roadmap

This roadmap records the mainline direction after Phase 9. It keeps Phase 9 as
the real video slicing foundation and avoids presenting it as a complete
automatic short-video product.

## Positioning

NarratoCut is an ROI-aware short-video workflow system for existing videos and
scripts. The long-term product path is:

```text
video or script
  -> highlights
  -> clip plan
  -> real slicing
  -> final video assembly
  -> quality inspection
  -> review report
```

Phase 9 has completed only the execution foundation:

```text
local video + ROI settings + provided ClipPlan
  -> metadata
  -> validation
  -> real clips
  -> inspect/review
```

## Mainline Phases

### Phase 9: Real Video Slicing Workflow

Status: complete on the feature branch.

Purpose:

- execute a provided `ClipPlan` against a local video
- validate the plan against video metadata and ROI settings
- produce real `.mp4` clips
- keep run artifacts inspectable and reviewable

Not included:

- automatic highlight detection
- ASR
- final-video assembly
- subtitles, BGM, cover, Web UI, or agent runtime

### Phase 10: Script / Timestamped Transcript Highlight Detection

Purpose:

- answer "what should be clipped?"
- detect hooks, conflicts, reversals, highlights, quotes, summaries, and CTA
  candidates from text inputs

Modes:

- `script_only`: input is normal script text; output is `highlight_plan.json`;
  no executable `clip_plan.json` is produced because there is no timeline.
- `timestamped_transcript`: input has segment timestamps; output is
  `highlight_plan.json` and `clip_plan.json`; the clip plan can enter the
  Phase 9 real slicing workflow.

Phase 10 does not process raw video directly.

### Phase 11: Video ASR + Timestamped Highlights

Purpose:

- turn a local video into a timestamped transcript that can be clipped

Phase 11.1 starts with the narrow video-to-transcript foundation:

```text
local video
  -> audio artifact
  -> mock/local ASR adapter
  -> transcript.json
```

This first step is intentionally deterministic and does not inspect video
frames for highlights.

Phase 11.2 composes that transcript foundation with the existing Phase 10
highlight pipeline:

```text
local video
  -> audio artifact
  -> mock ASR transcript
  -> highlight_plan.json
  -> clip_plan.json
```

This composition still does not add real ASR, video-frame highlight detection,
FFmpeg slicing, or final video assembly.

Phase 11.3 adds auditable real FFmpeg audio extraction metadata while preserving
the mock extraction path for deterministic tests. Phase 11.4 adds an optional
OpenAI-compatible ASR adapter behind an explicit `NARRATOCUT_ALLOW_REMOTE_ASR`
gate. The default demo workflows still use mock ASR fixtures.

Target flow:

```text
input video
  -> probe metadata
  -> extract audio
  -> ASR with timestamps
  -> transcript.json
  -> highlight_plan.json
  -> clip_plan.json
  -> Phase 9 slicing
```

Provider strategy:

- include a deterministic mock ASR provider for tests
- add local ASR providers behind adapters
- keep cloud ASR optional and explicitly configured

### Phase 12: Clip Assembly MVP

Purpose:

- turn one or more generated clips into `final_video.mp4`

P0:

- `assembly_plan.json`
- concat ordered clips
- `final_video.mp4`
- `final_video_manifest.json`
- final-video quality checks

P1:

- subtitle burn-in
- user-provided BGM
- BGM volume control
- basic audio mixing

P1 does not include automatic music recommendation, complex subtitle templates,
beat matching, transitions, or platform publishing.

### Phase 13: Web UI v0

Purpose:

- provide a product console for local workflow operation

Expected surface:

- choose input video or script
- configure ROI
- view highlights and clip plans
- run workflow
- preview clips/final video
- view inspect/review reports

The mainline Web UI should call stable workflow/API surfaces rather than
hard-code demo paths.

### Phase 14: Agent Runtime / Workflow-as-Tool

Purpose:

- expose workflow actions as controlled agent tools
- keep approval, risk checks, and audit trails explicit

The mainline should not bind to one agent framework too early.

## Competition Branch Strategy

Preferred branch point:

- after Phase 12, when the project can demonstrate a complete short-video
  assembly MVP.

Fallback branch point:

- after Phase 10, if the competition schedule requires earlier demo work.

Fallback demo scope:

```text
script or timestamped transcript
  -> highlights
  -> clip plan
  -> real slicing
  -> inspect/review
```

The fallback branch must not promise complete final-video assembly. A competition
Web UI may be built early only if it remains reusable, avoids hard-coded demo
logic, and does not bypass workflow contracts.
