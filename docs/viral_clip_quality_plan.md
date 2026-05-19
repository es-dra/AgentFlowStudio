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

The common lesson is that ASR is the input signal, not the final quality judge.

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

### 4. No Visual/Audio Signal Yet

The system does not inspect:

- speaker changes
- face presence
- shot changes
- motion intensity
- silence or loudness peaks
- subtitles already present in the source video
- visual action or emotional reaction

This limits true "viral moment" recognition.

## Recommended Quality Architecture

### Layer 1: Candidate Expansion

Generate more candidate windows before ranking:

- transcript segment windows: 1, 2, 3, 4 adjacent segments
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
- script evidence if available
- detector evidence

### Layer 2: Scoring

Score each candidate with transparent factors:

- hook_strength
- conflict_intensity
- clarity_without_context
- payoff_or_reversal
- duration_fit
- transcript_confidence
- script_alignment_confidence
- platform_fit

Output:

```text
highlight_score_report.json
```

### Layer 3: Product Review Gate

Before real slicing, add a review gate:

- reject clips shorter than a useful minimum
- reject unclear candidates with weak evidence
- require at least two distinct source windows
- flag low alignment confidence
- flag repeated or overlapping windows

This should remain deterministic first, then optionally support an LLM reviewer
behind explicit opt-in.

### Layer 4: Optional Visual/Audio Enrichment

After text quality is stable, add lightweight local media signals:

- ffmpeg scene-detect metadata
- audio loudness/silence segmentation
- keyframe/contact sheet generation for manual review
- optional face/speaker activity later

Output:

```text
media_signal_report.json
```

### Layer 5: Human-Reviewable Edit Plan

Produce a human-readable package report:

```text
package_report.md
```

It should include:

- candidate ranking table
- chosen clips and reasons
- transcript excerpts
- alignment confidence
- warnings
- paths to final video, clips, subtitles, and cover

## Proposed Next Phases

### Phase 14.2: Candidate Windows and Scoring

Goal:

```text
Move from keyword-selected highlights to ranked candidate windows.
```

Do:

- Add transcript window candidate generation.
- Add script-aligned candidate generation.
- Add transparent scoring factors.
- Write `candidate_windows.json` and `highlight_score_report.json`.
- Update review to flag low evidence and overlap.

Do not:

- Add Web UI.
- Add visual multimodal models.
- Add remote LLM by default.

### Phase 14.3: Package Report and Manual Review

Goal:

```text
Make output quality explainable to humans.
```

Do:

- Add `package_report.md`.
- Include selected clips, reasons, confidence, and artifact paths.
- Include top rejected candidates.

### Phase 14.4: Lightweight Media Signals

Goal:

```text
Use local non-LLM media signals to improve clip boundaries.
```

Do:

- Scene boundary detection via FFmpeg.
- Silence/loudness checks.
- Optional contact sheets.

### Phase 15: Semantics and Product Editing

Goal:

```text
Improve viral judgment beyond deterministic rules.
```

Options:

- Explicit opt-in LLM highlight reviewer.
- Local embedding reranker for script/transcript alignment.
- Visual model or OCR/subtitle extraction for source videos.

## Immediate Recommendation

Before adding UI or publishing features, implement Phase 14.2:

```text
candidate_windows.json
  -> highlight_score_report.json
  -> stronger ClipPlan
  -> real clips
```

This targets the core product issue directly: better clip choice.
