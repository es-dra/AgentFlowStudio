# AFS-COMPETITION-DEMO-RUN-SHEET

Status: competition-day execution sheet for the current memory-advantage demo.

## Goal

Use the existing Slidev deck, RECORDING-016 videos, and optional live I2V
recording script to present one clear point:

> Under the same keyframe, model, duration, and storyboard, memory-backed
> production shows a stronger stability signal than a stateless baseline in the
> current repeated-generation demo.

Keep the claim bounded. This is demo evidence, not final product acceptance,
business validation, or durable Memory runtime proof.

## Materials

Primary deck:

```text
D:\Learning materials\Learning_notes\Slidev\Slidev\AgentFlow-Studio-memory-advantage-competition.md
```

Operator runbook:

```text
docs/handoff/AFS-MEMORY-ADVANTAGE-RECORDING-016.md
```

Talk track:

```text
docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md
```

One-click recording script:

```text
tools/run_memory_advantage_recording_016.ps1
```

## Preflight

Run these before the presentation or recording session.

From `D:\Learning materials\Learning_notes\Slidev`:

```powershell
npx.cmd slidev build "Slidev/AgentFlow-Studio-memory-advantage-competition.md" --base /
```

From `D:\Projects\AgentFlowStudio`:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -DryRun -NoOpen
```

Expected result:

- Slidev build succeeds.
- Dry run prints "provider calls were not made".
- No secrets, provider keys, or generated media are added to Git.

## Start The Deck

From `D:\Learning materials\Learning_notes\Slidev`:

```powershell
npx.cmd slidev "Slidev/AgentFlow-Studio-memory-advantage-competition.md" --port 3030
```

If port 3030 is busy:

```powershell
npx.cmd slidev "Slidev/AgentFlow-Studio-memory-advantage-competition.md" --port 3031
```

Open the shown local URL in the browser. Do not use `npx` in PowerShell on this
machine; use `npx.cmd`.

## Recommended Live Order

1. Open with the production problem: AI video is easy to generate once, hard to
   keep consistent across rounds.
2. Show the architecture slide: evidence becomes reusable context.
3. Show the demo chain: character asset, keyframe, I2V, review.
4. Show RECORDING-016 setup: same keyframe, task, model, duration, storyboard.
5. Show baseline repeated-generation page.
6. Show memory-backed repeated-generation page.
7. Show observation result.
8. Close with the core value: memory turns prior production work into reusable
   assets for the next round.

Use the 60-second talk track in
`docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md` if time is tight.

Current machine rehearsal route map:

```text
/10  repeated-generation input difference
/11  baseline repeated-generation page
/12  memory-backed repeated-generation page
/13  observation result page
/21  core value page
```

This route map is from a local Slidev check on 2026-05-29. If the deck changes,
rerun the browser check instead of assuming the page numbers still match.

## Optional Live Recording

Only do this when you are intentionally consuming Kling video quota.

From `D:\Projects\AgentFlowStudio`:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -ProviderConfig <local_ignored_provider_config.json> -AllowRemoteVideo
```

The explicit video switch is required. If it is missing, the script stops
before remote video calls. Provider config is also explicit: pass
`-ProviderConfig` or set `AFS_PROVIDER_CONFIG` in the current shell.

During recording, show:

- dry-run command;
- generated `protocol/` path;
- baseline prompt versus memory-backed prompt difference;
- live command with `-ProviderConfig` and `-AllowRemoteVideo`;
- final comparison video path.

Use the 3-minute recording script in
`docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md`.

## Fallback If Live Provider Fails

Do not debug the provider live unless the session is explicitly about
debugging.

Use the existing Slidev videos instead. Say:

> For the live stage I am using the already captured RECORDING-016 evidence, so
> we do not depend on provider queue time or network behavior during the
> presentation.

Then continue with the baseline and memory-backed comparison pages.

## Fallback If Slidev Fails

1. Run the build command again to confirm the deck still compiles.
2. If the dev server fails because the port is busy, use port 3031.
3. If the browser still fails, present from the Markdown file and open the
   videos directly from the Slidev `public/media` folder.

Do not change dependencies or system execution policy during the presentation.

## Language Boundary

Safe wording:

- "bounded demo evidence"
- "stability signal"
- "same keyframe, same model, same script"
- "memory-backed lane reused structured character, scene, and feedback context"
- "not final product acceptance"

Avoid:

- "already proved product quality"
- "business validation is complete"
- "the memory runtime is done"
- "baseline is bad"
- "this always works"

## After The Session

Record the actual outcome in `DEVLOG.md` or a new handoff note:

- which deck command was used;
- whether live provider recording was run;
- where the output artifacts are;
- whether the audience saw the baseline/memory-backed difference;
- any questions that should become next-loop product requirements.

## Human Rehearsal Checklist

Use this after the machine preflight and before the actual presentation.

Setup:

- [ ] Close unrelated windows and private material.
- [ ] Open Slidev on the chosen port.
- [ ] Open this run sheet and the talk-track document.
- [ ] Confirm the videos on `/11` and `/12` can be played manually.
- [ ] Keep the terminal in `D:\Projects\AgentFlowStudio` if the I2V recording
      flow will be shown.

60-second live pass:

- [ ] Explain the problem in one sentence: generation is easy once, consistency
      across rounds is hard.
- [ ] Say the comparison is controlled: same keyframe, model, duration, and
      storyboard.
- [ ] Say baseline is usable, not intentionally weak.
- [ ] Say the memory-backed lane reuses character, scene, and feedback context.
- [ ] End with the bounded claim: stronger stability signal, not final proof.

3-minute recording pass:

- [ ] Run `.\tools\run_memory_advantage_recording_016.ps1 -DryRun -NoOpen`.
- [ ] Show the generated `protocol/` folder path.
- [ ] Explain baseline prompt versus memory-backed prompt.
- [ ] If quota and timing allow, run with `-AllowRemoteVideo`.
- [ ] If live provider timing is uncertain, switch to the already captured
      RECORDING-016 videos.

Timing check:

- [ ] Baseline page explanation stays under 30 seconds.
- [ ] Memory-backed page explanation stays under 30 seconds.
- [ ] Observation result page stays under 30 seconds.
- [ ] Total demo segment stays within the allowed presentation time.

## Feedback Capture Template

Use this after the session. Keep it factual.

```markdown
## Competition Demo Session Notes - YYYY-MM-DD

Deck command used:

Live provider recording:

Artifacts shown:

What landed clearly:

Where the audience looked confused:

Questions asked:

Potential product requirements:

Memory architecture follow-up:

Workbench follow-up:

Claim boundary corrections needed:
```

## Machine Rehearsal Log

2026-05-29 local check:

- Slidev dev server started on port 3032 for verification and was stopped after
  the check.
- Browser check found no Chinese mojibake on the checked pages.
- Verified visible route mapping:
  - `/11`: baseline repeated-generation page;
  - `/12`: memory-backed repeated-generation page;
  - `/13`: observation result page.
- `.\tools\run_memory_advantage_recording_016.ps1 -DryRun -NoOpen` completed
  and printed that provider calls were not made.
- Focused tests passed: `43 passed`.
