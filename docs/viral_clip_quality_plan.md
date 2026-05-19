# Viral Clip Quality Plan

Date: 2026-05-19

## Current Baseline

NarratoCut can now close the local product chain for two cases:

1. Source video only.
2. Source video plus script.

The current system can produce:

- `transcript.json`
- `highlight_plan.json`
- `clip_plan.json`
- real clips
- `final_video.mp4`
- clip-timeline subtitles
- BGM-mixed final video
- `finished_package_manifest.json`
- `quality_report.json`
- `review_report.json`

The remaining quality gap is not slicing execution. It is choosing better clips.

## Product Reference Notes

Mature short-video clipping products tend to combine several capabilities:

- ASR transcript understanding.
- On-screen subtitle/OCR understanding.
- Embedded subtitle extraction when subtitle streams exist.
- Keyframe or scene evidence for visual review.
- Multiple highlight candidates rather than a single first segment.
- A score or ranking layer, often framed as hook strength, virality, or audience
  retention.
- Auto captions and visual formatting.
- Human editing controls after the AI pass.
- Platform-aware outputs such as Shorts, Reels, TikTok, or Douyin.

Public examples reviewed:

- OpusClip: advertises AI clipping, a virality score, active-speaker/layout
  support, captions, and social-ready shorts.
- CapCut: combines automatic captions, templates/effects, and editing controls.
- Vizard: focuses on turning long videos into multiple short clips with AI
  clipping and captions.
- Descript: combines transcript-based editing with clip creation and captions.

The common lesson is that ASR is one input signal, not the final quality judge.
For short videos, on-screen subtitles often represent what the audience
actually reads, especially in silent viewing contexts. OCR should therefore be
treated as a second local content-understanding channel rather than a
replacement for ASR.

## Current Gaps

### 1. ASR Quality Is Necessary But Not Sufficient

`faster-whisper small` provides usable local Chinese transcripts on the current
one-minute demos, but transcript quality still has errors. Better ASR improves
candidate text and timestamps, but it does not decide whether a moment is
actually a strong short-video hook.

### 2. Highlight Detection Is Still Deterministic MVP Logic

The current detector uses fixed keyword/rule scoring. It can produce stable
multi-segment plans, but it does not deeply evaluate:

- hook strength in the first 1-3 seconds
- conflict escalation
- reversal or payoff
- emotional intensity
- information density
- scene continuity
- whether the clip is understandable without surrounding context

### 3. Script Alignment Is Lexical

The Chinese sliding-window aligner is now useful enough for local acceptance,
but confidence remains low when ASR and script text differ. It needs semantic
matching or a stronger reranker before it can be treated as editorially strong.

### 4. No OCR, Visual, or Audio Signal Yet

The system does not inspect:

- speaker changes
- face presence
- shot changes
- motion intensity
- silence or loudness peaks
- subtitles already present in the source video
- embedded subtitle streams
- keyframe text or contact sheets
- visual action or emotional reaction

This limits true "viral moment" recognition.

## Recommended Quality Architecture

### Content Understanding Layer

NarratoCut should treat content understanding as multiple local evidence
channels:

```text
video
  -> ASR transcript optional
  -> subtitle OCR transcript optional
  -> embedded subtitle transcript optional
  -> keyframe/contact-sheet evidence optional
  -> candidate windows
  -> scoring and selection
```

The product modes should remain explicit:

- ASR mode: best for no-subtitle source videos, interviews, and raw talking
  footage.
- OCR subtitle mode: best for already-captioned short videos, courses, screen
  recordings, and knowledge clips.
- Hybrid mode: best for product acceptance and higher-quality generation,
  fusing ASR, OCR, script alignment, and later keyframe evidence.

### Layer 1: Candidate Expansion

Generate more candidate windows before ranking:

- transcript segment windows: 1, 2, 3, 4 adjacent segments
- OCR subtitle transcript windows when available
- script-aligned windows
- opening hook candidates
- conflict/reversal candidates
- ending/payoff candidates

Output:

```text
candidate_windows.json
```

Each candidate should include:

- source segment ids
- start/end/duration
- transcript text
- content channel, such as `asr_transcript`, `ocr_subtitle`, or `fused_transcript`
- script evidence if available
- OCR evidence if available
- detector evidence

### Layer 2: Subtitle OCR Timeline

Before scoring is treated as product-grade, add a narrow local OCR transcript
path for videos that already contain visible subtitles:

```text
video
  -> sampled frames
  -> cropped subtitle region
  -> OCR provider
  -> dedupe and merge
  -> ocr_transcript.json
```

Keep this slice explicit and optional. It should not replace ASR for videos
without subtitles.

The first OCR MVP should prefer:

- configured subtitle region, such as the bottom 35 percent of the frame
- frame interval sampling, such as 0.5s or 1s
- mock OCR provider for tests
- optional local OCR provider for real smokes
- text normalization, adjacent-frame dedupe, short-gap merge, and confidence
  aggregation

### Layer 3: Scoring

Score each candidate with transparent factors:

- hook_strength
- conflict_intensity
- clarity_without_context
- payoff_or_reversal
- duration_fit
- transcript_confidence
- on_screen_hook_strength
- asr_ocr_consistency
- script_alignment_confidence
- platform_fit

Output:

```text
highlight_score_report.json
```

### Layer 4: Product Review Gate

Before real slicing, add a review gate:

- reject clips shorter than a useful minimum
- reject unclear candidates with weak evidence
- require at least two distinct source windows
- flag low alignment confidence
- flag repeated or overlapping windows
- flag low OCR confidence when OCR is used as primary evidence
- flag ASR/OCR disagreement when both channels are available

This should remain deterministic first, then optionally support an LLM reviewer
behind explicit opt-in.

### Layer 5: Optional Visual/Audio Enrichment

After OCR and text scoring are stable, add lightweight local media signals:

- ffmpeg scene-detect metadata
- audio loudness/silence segmentation
- keyframe/contact sheet generation for manual review
- optional keyframe OCR for screen text or title cards
- optional face/speaker activity later

Output:

```text
media_signal_report.json
```

### Layer 6: Human-Reviewable Edit Plan

Produce a human-readable package report:

```text
package_report.md
```

It should include:

- candidate ranking table
- chosen clips and reasons
- transcript excerpts
- OCR subtitle excerpts when available
- keyframe/contact-sheet references when available
- alignment confidence
- warnings
- paths to final video, clips, subtitles, and cover

## Proposed Next Phases

### Phase 14.2A: Candidate Windows

Goal:

```text
Move from direct highlight selection to reusable candidate windows.
```

Do:

- Add transcript window candidate generation.
- Record content channel metadata so ASR, OCR, and fused transcripts can share
  the same candidate layer.
- Write `candidate_windows.json`.

Do not:

- Add viral scoring.
- Add OCR implementation.
- Add Web UI.
- Add visual multimodal models.
- Add remote LLM by default.

### Phase 14.2B: Subtitle OCR Timeline

Goal:

```text
Turn visible source-video subtitles into timestamped transcript evidence.
```

Do:

- Add configured frame sampling and subtitle-region cropping.
- Add a mock OCR provider for tests.
- Add optional local OCR provider behind explicit opt-in or optional
  dependency.
- Normalize, dedupe, and merge frame-level OCR into `ocr_transcript.json`.
- Keep `ocr_transcript.json` compatible with transcript-based candidate
  generation.

Do not:

- Replace ASR globally.
- Do full visual scene understanding.
- Add default remote OCR.
- Add scoring in the same slice.

### Phase 14.2C: ASR/OCR Candidate Fusion and Viral Scoring

Goal:

```text
Score candidates with explainable evidence from ASR, OCR, and script alignment.
```

Do:

- Generate candidate windows from ASR and/or OCR transcripts.
- Add transparent scoring factors.
- Write `highlight_score_report.json`.
- Update review to flag low evidence, overlap, low OCR confidence, and ASR/OCR
  disagreement.

### Phase 14.3: Package Report and Manual Review

Goal:

```text
Make output quality explainable to humans.
```

Do:

- Add `package_report.md`.
- Include selected clips, reasons, confidence, and artifact paths.
- Include top rejected candidates.
- Include ASR text, OCR subtitle text, and keyframe/contact-sheet references
  when available.

### Phase 14.4: Lightweight Media Signals

Goal:

```text
Use local non-LLM media signals to improve clip boundaries.
```

Phase 14.4A started with transcript-only boundary hardening before adding new
media detectors:

- Replace fixed five-second splits for long transcript windows with elastic
  short-window boundaries.
- Prefer balanced 4-6 second windows when a long source window can be split
  cleanly.
- Trim unsplittable 6-8 second source windows to a target-length core instead
  of producing weak sub-four-second fragments.
- Preserve `boundary_strategy`, `target_duration_sec`, and source-window
  evidence so `package_report.md` can explain why the selected clip starts and
  ends where it does.

Phase 14.4C adds the first local media signal:

- Analyze the extracted WAV artifact for low-energy windows and energy peaks.
- Write `boundary_signal_manifest.json`.
- Attach nearest audio boundary evidence to candidate windows when analysis
  succeeds.
- Keep the evidence advisory so mock audio, unsupported audio, or weak boundary
  results do not block ASR, scoring, slicing, or packaging.

Do:

- Scene boundary detection via FFmpeg.
- Stronger silence/loudness checks that can refine actual cut points, not only
  explain nearby boundaries.
- Optional contact sheets.
- Optional keyframe OCR evidence.

### Phase 15: Semantics and Product Editing

Goal:

```text
Improve viral judgment beyond deterministic rules.
```

Options:

- Explicit opt-in LLM highlight reviewer.
- Local embedding reranker for script/transcript alignment.
- Visual model reranker for source videos.

## Immediate Recommendation

Before adding UI or publishing features, keep the current Phase 14.2A candidate
window slice narrow, then add OCR transcript evidence before product-grade
scoring:

```text
transcript.json or ocr_transcript.json
  -> candidate_windows.json
  -> highlight_score_report.json with ASR/OCR/script evidence
  -> stronger ClipPlan
  -> real clips
```

This targets the core product issue directly: better clip choice with evidence
that matches what viewers hear and what they see on screen.
