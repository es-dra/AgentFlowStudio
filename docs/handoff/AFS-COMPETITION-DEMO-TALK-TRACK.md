# AFS-COMPETITION-DEMO-TALK-TRACK

Status: speaker notes for the current competition demo package.

## Scope

Use this with the Slidev deck, the RECORDING-016 operator runbook, and the
competition run sheet. It is not part of the product runtime and does not
expand the claim boundary.

Current strongest demo evidence:

- Same source keyframe.
- Same user task.
- Same Kling I2V model and 15-second duration.
- Same storyboard checkpoints.
- Baseline uses the current task plus source keyframe.
- Memory-backed uses the same inputs plus character, scene, and feedback memory
  projection.
- Observed signal: baseline repeated runs vary more; memory-backed repeated
  runs are more stable.

## 60-Second Live Talk Track

AgentFlow Studio is trying to solve a very concrete production problem: AI
content generation is easy to start, but hard to keep consistent across rounds.
The same role, the same scene, and the same revision requirement often drift
when we move from keyframe to video.

This demo compares two production modes under the same task. The baseline lane
gets the source keyframe and the current storyboard. The memory-backed lane gets
the same inputs, plus three pieces of reusable context: a character card, a
scene card, and a feedback patch from earlier review.

The important point is not that we wrote a longer prompt. The point is that the
extra context comes from prior production evidence: what the character looks
like, what the scene should preserve, and what mistakes should be avoided after
occlusion or camera motion.

In the repeated-generation test, both lanes use the same keyframe, same model,
same 15-second script, and same provider route. The baseline runs are visually
usable, but the camera path and details drift more between runs. The
memory-backed runs stay closer to the same character, outfit, rain scene, and
final staging.

So the current claim is deliberately narrow: this is bounded demo evidence that
memory-backed production can reduce repeated-generation divergence. It is not
final product acceptance or business validation yet, but it shows why this
architecture is worth building into a real workbench.

## 3-Minute Recording Script

### 0:00-0:25 - Frame The Problem

I am going to show the workflow behind the demo, not a polished magic result.
The problem we are testing is consistency: after we already have a character
asset and a keyframe, can the system keep the same person, outfit, scene, and
motion logic when generating video?

The two lanes are intentionally close. Baseline is a normal professional I2V
request. Memory-backed uses the same request, but it also projects structured
memory from earlier production evidence.

### 0:25-0:55 - Show Dry Run

Run:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -DryRun -NoOpen
```

Say:

This first command prepares the run without calling the provider. It writes the
shared task, the baseline prompt, the memory-backed prompt, and recording notes
under `data/processed/`, which is ignored by Git.

The dry run matters because it lets us inspect the protocol before spending
provider quota.

### 0:55-1:35 - Show Input Difference

Open or mention the generated `protocol/` folder.

Say:

Here are the two inputs. The baseline lane receives the current task, the
source keyframe, and the five shot checkpoints: readable character, walking
through neon rain, light and rain occlusion, turn back, then stop under the
neon sign.

The memory-backed lane receives the same task and the same keyframe. The
difference is the projected memory: character anchors, scene anchors, and a
feedback patch. The feedback patch is especially important because it tells the
system what earlier review found fragile: recover the same face and outfit
after occlusion, avoid hair and clothing drift, and keep foot contact plausible.

### 1:35-2:05 - Run Live I2V

Run only when you intend to consume Kling video quota:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -ProviderConfig <local_ignored_provider_config.json> -AllowRemoteVideo
```

Say:

The live command requires an explicit video gate and explicit local provider
config. That is intentional. This project treats provider calls as
capability-specific operations, so a script cannot silently turn on remote
video generation or infer a machine-local secret path.

The script runs Kling I2V once for baseline and once for memory-backed, then
builds a side-by-side comparison video with ffmpeg.

### 2:05-2:40 - Show Result

Open the comparison video or the Slidev comparison pages.

Say:

The baseline result is not bad. That is important. We are not comparing a bad
prompt against a good prompt.

The useful signal is repeatability. Across repeated runs, baseline tends to
make more independent choices about camera path, staging, and detail recovery.
The memory-backed version stays closer to the same character and scene after
motion and occlusion.

### 2:40-3:00 - Close With Boundary

Say:

This does not prove final creative quality. It is a controlled demo signal:
same keyframe, same model, same script, different context strategy.

For a one-person AI-native production system, that matters because memory is
not just chat history. It becomes a reusable production asset: character,
scene, feedback, and review evidence that can be carried into the next round.

## What Not To Say

- Do not say this proves final product quality.
- Do not say this is business validation.
- Do not say durable Memory runtime is already implemented.
- Do not say the baseline is intentionally weak.
- Do not describe this as pure prompt engineering.
- Do not claim the result will always be better on every model or scene.

## If Judges Ask

Question: Is this just a longer prompt?

Answer: The current implementation projects memory into the provider prompt,
so the provider ultimately sees text. The difference is where that text comes
from. In baseline, the operator rewrites context manually each time. In the
memory-backed lane, character, scene, and feedback context are structured assets
selected from prior production evidence. The product value is repeatability and
reuse, not prompt length.

Question: Why use the same source keyframe for both lanes?

Answer: To isolate the video-generation step. Earlier tests already covered
keyframe consistency. RECORDING-016 asks a narrower question: from the same
keyframe to video, does memory context reduce run-to-run divergence?

Question: What is missing before this becomes a product?

Answer: Three things. First, the workbench needs to make this workflow usable
without scripts. Second, memory promotion needs a durable runtime rather than
demo artifacts. Third, quality evaluation needs more scenes, more repeats, and
clearer review metrics.

Question: Why is the claim bounded?

Answer: Because the evidence is still small-sample visual evidence. The
pipeline, prompts, provider calls, manifests, and videos exist, but we should
not confuse that with market validation or final human acceptance.

## Slidev Cue

Recommended live order:

1. Architecture pages.
2. Demo chain page.
3. RECORDING-016 setup page.
4. Baseline repeated-generation page.
5. Memory-backed repeated-generation page.
6. Observation result page.
7. Core value page.

For command order, provider fallback, and presentation-day checks, use
`docs/handoff/AFS-COMPETITION-DEMO-RUN-SHEET.md`.
