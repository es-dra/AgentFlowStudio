# Memory Architecture Next Loop - 2026-05-29

Status: architecture reflection derived from the recent MiniMax/Kling
memory-advantage experiments. This is a design direction, not an implemented
durable Memory runtime.

## What The Experiments Taught

### The Unit Of Memory Is Not A Better Prompt

The useful unit is a reviewed production asset:

- character identity card;
- scene card;
- style card;
- physical and continuity constraints;
- feedback patch from prior failures;
- promotion decision explaining why reuse is allowed.

The provider prompt is only the final projection. It should be generated from
those assets, not handcrafted every time.

### Repeatability Is The Stronger Claim

Single-run comparisons are fragile. A baseline can get lucky, and a
memory-backed run can fail.

RECORDING-016 gave a stronger evaluation frame:

```text
same source keyframe
same user task
same provider/model/duration
repeat twice
compare cross-run stability
```

Baseline produced decent but more variable interpretations. Memory-backed
outputs were more consistent in shot structure, character recovery, and scene
anchors. This is closer to the product promise: the system should make good
results easier to repeat and improve.

### Reference Assets Matter More Than Text Alone

The early text/T2V attempts were too close to prompt lottery. The route became
credible only after the fixed character asset entered the loop:

```text
user-accepted reference
-> I2I keyframe
-> I2V storyboard
```

For character consistency, visual memory must include real visual evidence,
not only textual traits.

### Feedback Memory Should Be Small And Concrete

The most useful feedback patches were narrow corrections:

- do not expose midriff;
- do not introduce hair accessories;
- recover same face after occlusion;
- keep scene anchor visible;
- keep rain, cloth, hair, and foot contact physically coherent.

The Memory Compiler should prefer small, testable rules over long aesthetic
essays.

### Reuse Needs Review Gates

The earlier fix that rejected promotion decisions cannot enter context reuse
was important. Without this gate, "has a decision" could be confused with
"allowed for reuse".

Mature rule:

```text
candidate memory is inert
rejected memory is blocked
promoted / merged memory may enter context
reuse still requires task-specific decision
```

## Proposed Core Architecture

The next architecture should be an Evidence-backed Memory Production Loop.

### 1. Project Brief

Inputs:

- user goal;
- script or storyboard;
- target format;
- reference assets;
- provider budget and gates.

Outputs:

- `project_brief.json`;
- `storyboard.json`;
- `run_policy.json`.

### 2. Artifact Ledger

Records every important input and output without committing generated media:

- local refs;
- hashes;
- byte counts;
- artifact type;
- provider/model;
- source relationship;
- claim boundary.

The artifact ledger is the trace backbone.

### 3. Asset Memory Ledger

Stores reviewed reusable production assets:

- character card;
- scene card;
- style card;
- storyboard pattern;
- feedback patch;
- rejected asset notes.

This should start local and file-based. A database can come later.

### 4. Memory Compiler

Turns evidence into structured memory candidates:

```text
reference image / generated result / human note
-> extracted anchors
-> candidate memory
-> review question
```

For the next demo, the compiler can be partly manual. The artifact shape should
be stable before adding automation.

### 5. Promotion And Reuse Policy

Controls whether memory can affect a run:

- candidate;
- promoted;
- merged;
- rejected;
- expired.

The policy must preserve evidence refs and prevent rejected memory from being
loaded.

### 6. Context Runtime

Builds provider-facing context bundles:

```text
short user task
+ selected asset cards
+ scene cards
+ feedback patches
+ provider-specific constraints
-> provider prompt / request package
```

This is where memory becomes visible in execution, but the prompt itself is not
the product architecture.

### 7. Provider Gateway

Current providers:

- MiniMax for image and image-to-image;
- Kling for image-to-video and text-to-video;
- DeepSeek and other LLM providers later for analysis and compilation.

Current local file config is acceptable for now if secret boundaries remain
strict. A central provider gateway is still the right later architecture, but
it should come after the local product loop is cleaner.

Gateway responsibilities later:

- provider credential management;
- model routing;
- async job tracking;
- cost and quota tracking;
- provider-specific retries;
- redacted logs;
- unified media artifact download policy.

### 8. Review Harness

Separates:

- technical media verification;
- storyboard adherence;
- anchor retention;
- cross-run variance;
- human acceptance;
- business validation.

For memory advantage, the useful rubric is:

```text
identity retention
wardrobe retention
scene anchor retention
motion / physics plausibility
occlusion or lighting recovery
cross-run stability
feedback incorporation
```

### 9. Workbench

The workbench should be the operator cockpit for:

```text
Brief
Assets
Memory Loaded
Generation Runs
Side-by-side Review
Feedback Capture
Promotion Decision
Next Pass
```

It should make the memory advantage inspectable:

- what memory was loaded;
- why it was eligible;
- which prompt projection it produced;
- what changed versus baseline;
- what feedback was captured;
- what will be reused next time.

## Productization Roadmap

P0: stop the sprawl.

- Freeze the current dirty worktree into reviewable groups.
- Decide what is product code, experiment code, and archive.
- Stop adding numbered demo modules for each experiment.
- Add a generic experiment runner before the next major demo loop.

P1: productize the demo pipeline.

Build one command or workflow that can run:

```text
project brief
-> keyframe generation from asset memory
-> I2V generation
-> comparison video
-> contact sheet
-> review JSON
-> feedback event draft
```

It should accept a protocol file instead of hard-coded demo ids.

P1: local Memory MVP.

Start file-based:

```text
memory/
  assets.jsonl
  feedback.jsonl
  candidates.jsonl
  promotion_decisions.jsonl
  context_bundles/
```

Rules:

- append-only raw feedback;
- candidates are inert;
- only promoted/merged items can enter context;
- every context bundle stores why each memory item was selected;
- no private Company content is copied into project memory unless explicitly
  approved.

P1: redesign the workbench.

Required first screen:

- current project;
- selected character/scene assets;
- memory loaded;
- baseline run;
- memory-backed run;
- review and feedback.

Avoid a dashboard of every possible artifact. The workbench should guide the
operator through a repeatable production loop.

P2: provider gateway.

The gateway is compatible with the current local config approach. It should be
introduced after the loop is cleaner, not before.

P2: GitHub and release hygiene.

- Split the current dirty worktree into coherent commits.
- Push `master` or move work into a named branch before more large changes.
- Archive old experiment branches and handoffs.
- Tag a demo evidence checkpoint.
- Keep generated media ignored.
- Add issue or milestone groups:
  - `maintenance-reset`;
  - `memory-pipeline-mvp`;
  - `workbench-redesign`;
  - `provider-gateway`;
  - `competition-materials`.

## Next Milestone Definition

The next product milestone should be:

```text
AgentFlow Studio can run one memory-backed video production experiment from a
single protocol file, show baseline versus memory-backed outputs in the
workbench, capture human feedback, and generate the next memory candidate
without adding another bespoke demo module.
```
