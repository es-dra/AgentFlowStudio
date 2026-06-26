# AgentFlow Studio Task Tracker

中文摘要：本文件是当前 AFS MVP 的任务入口，只记录仍需要执行、验证或交接的事项。当前主线已经锁定 Studio 前端、Runtime API、专业知识库、创作意图控制智能体和图片/关键帧 provider gate；旧 Workbench、旧 Web RC、历史候选记忆 UI 和过期支线不再作为任务来源。任何事项如果不能导向第一版 MVP 落地、真实模型接入或低成本维护，应从这里移除。

保留理由：本文的价值在于让后续维护者快速判断当前任务是否仍能推动 MVP 收口和真实模型接入。每个任务都必须对应明确接口、测试、证据和非声明边界；没有当前引用的旧任务直接删除。真实模型接入前，所有结论都要重新经过本地测试、provider gate 检查、safe manifest 检查和人工体验确认。

当前口径：待办只保留三类，一是 Studio 和 Runtime 的联合验收，二是图片/关键帧真实模型 gate，三是创作智能体规则、评分和反馈回路的可验证改进。除此之外的旧支线、旧 UI 设想和无测试证据的概念记录都不进入任务列表。

Last updated: 2026-06-26 by Codex

This file keeps only current work, blockers, and evidence entrypoints. Retired
Workbench, static memory-workbench, old Web RC, and old browser-QA threads are
not current task entrypoints.

Internal beta account/admin baseline: 2026-06-26 added the admin-only
`auth-invites` CLI on top of the existing Runtime auth store. Current
administrator entrypoint:
`docs/handoff/AFS-INTERNAL-BETA-ADMIN-20260626.md`. The CLI supports issuing,
listing, and revoking one-time invite codes; Runtime persists invite hashes and
safe metadata only. Plaintext invite codes are admin-local distribution
material and must not be copied into GitHub issues, PRs, handoffs, DEVLOG, or
TASK_TRACKER. This is an internal beta access mechanism, not a public admin UI,
SaaS role/org system, password reset system, or billing/accounting layer.
Addendum: the 2026-06-26 hardening pass adds auth failure rate limiting, safe
auth/request audit logs, weak static env invite-code skipping, atomic JSON
writes with file locks, an auth-level read-modify-write lock, and the
`runtime-backup create` administrator backup command. Maintenance ledger:
`docs/maintenance/AFS-INTERNAL-BETA-HARDENING-20260626.md`.

Studio generation/reference bugfix baseline: 2026-06-26 pass fixed the current
internal-test blockers around script import, progress percentages, asset-library
reference binding, and image relay provider naming/diagnostics. Script import
now accepts text/markdown plus Word/PPT (`.docx/.pptx` with OOXML extraction
and `.doc/.ppt` best-effort text extraction). Active image/video generation
shows percentages when available; prompt optimization, script expansion, and
storyboard breakdown write percentage state. Asset-library "用作参考" now binds
image assets to the selected node: video nodes get `firstFrameImageAssetId` and
a first-frame upload ref, image/keyframe nodes get a `reference_image` upload
ref. Current image service defaults moved from `codex_image` to external
`image_relay`; Runtime keeps a legacy alias for old ignored configs and splits
safe relay errors into reference-slot, unsupported-reference-route,
missing-service, auth, and HTTP block ids. Verification: JS syntax 122 files
passed, role-based local user simulation passed for script import, asset reuse,
progress, and provider route; focused generation/reference pytest 104 passed,
CLI help/version
passed, maintenance audit failed=0, `git diff --check` passed. Full pytest had
637 passed / 3 failed / 520 deselected / 1 warning; failures are environment or
pre-existing state (`D:/Learning materials/...` source KB absent on Linux and
untracked `ops/sub2api/*` retention review items). Maintenance ledger:
`docs/maintenance/AFS-STUDIO-GENERATION-REFERENCE-BUGFIX-20260626.md`.
Addendum: the same-day Runtime deployment guard now projects an ignored local
`codex_image` API relay service in `AFS_PROVIDER_CONFIG` into product-facing
`image_relay` in memory, including an `image_relay_pool`, `/images/edits`
default, and `reference_image_slots >= 1` for asset-reference image edits. This
lets server Runtime use current `image_relay` model plans even before a
privileged operator rewrites root-owned `/etc/afs/providers.local.json`.
Verification: focused provider/Runtime/Studio regression set passed 61,
`git diff --check` passed, and a read-only loader probe against
`/etc/afs/providers.local.json` exposed `image_relay` plus `seedance_i2v` while
rejecting `codex_image`. Remaining privileged ops cleanup: physically remove
old `codex_image` keys from `/etc/afs/providers.local.json` and disable
`afs-codex-image-worker.service`; current shell lacks passwordless sudo.

AFS+COS takeover baseline: 2026-06-26 branch cleanup completed across local,
GitHub, server `/home`, and server `/opt`. The intended clean branch state is
`master` only on all four surfaces. Merged server-local `codex/*` branches were
deleted. Stale `codex/open-source-handoff-governance` was inspected, not merged
because it was behind current video-chain work, then removed from local
worktree/local branch/GitHub after the current takeover handoff was recreated
on `master`. Current takeover entry:
`docs/handoff/AFS-COS-TAKEOVER-20260626.md`. Server `/home` still has an
untracked `ops/` directory and it remains intentionally untouched as an
ops-local artifact. Boundary: no provider call, secret read, media byte write,
or private Company OS source copy occurred.

Video node full-chain hardening follow-up: 2026-06-26 pass fixed four issues
from the robot/rooftop full-chain experiment. `扩写剧本` now requests and
falls back to formal short-video script prose before storyboard breakdown,
instead of emitting placeholder `分镜 01/02/03/04` lines. Keyframe generation
now builds an editable `keyframeAssetPlan` from connected asset cards and
writes candidate signatures/features/reference-image counts into the keyframe
prompt, with explicit constraints against unrequested stools, chairs, eaves,
extra props, new characters, text, watermarks, UI, or borders; keyframe image
nodes also expose `编辑关键帧资产约束` to open the editable generation prompt for
manual constraint revision before regeneration. The video
asset-card button now handles the `video-asset-card-draft` action and gives
visible no-video/running/success/failure feedback. Runtime video jobs now expose
safe timing fields (`provider_phase`, `elapsed_sec`, `queued_sec`,
`running_sec`) so slow 5s generation can be distinguished between provider
queue/wait and generation runtime where observable. Verification: Studio
script/assets static set 40 passed, Runtime video generation tests 12 passed
with 1 existing warning, and `npm.cmd run check:studio-js` passed for 121
files. The current robot/rooftop server job
`studio-1782460097617-ynsp23-video_generation-d5b554ffabf1` was inspected via
safe/task artifacts only and had succeeded with one MP4; old code lacked
granular timing, but safe file times indicate about 58 seconds before provider
task-state persistence and about 3 minutes 32 seconds until final candidate
write. Boundary: no new live provider call in this pass; timing is
Runtime/provider evidence, not creative quality or human acceptance.

Video timeline prompt follow-up: 2026-06-26 screenshot investigation found
Studio job `studio-1782194320739-0phdgx-video_generation-ed77c226b864` reached
the deployed `seedance_i2v` provider with first-frame image asset
`img_gen_0e4d7d2f6bbafbd2`, 5s, 720p, 16:9. The safe manifest ended
`poll_failed` with `remote_video_policy_block`, so the failure was an upstream
policy/copyright block after async provider queue/render/review, not a closed
video gate, missing first frame, Kling fallback, local timeout, credential
issue, or provider 404. Studio now generates a timeline-style keyframe-to-video
prompt with explicit 0.0s / 0.0-1.0s / 1.0-2.5s / 2.5-4.0s / 4.0-5.0s phases,
filters image-only `单张关键帧` language, and normalizes candidate asset-card
mentions so prompt-only references do not create duplicate malformed video
asset entries. Verification: Studio static set 24 passed, `npm.cmd run
check:studio-js` passed for 121 files, Runtime video generation tests 12 passed
with 1 existing warning, and `git diff --check` passed. Deployment: local
`master`, origin `master`, server `/home`, and server `/opt` were aligned at
`08dcf90`; Runtime `/health` stayed ready with video gate true, and
`/studio/src/keyframe-video-prompt.js` returned HTTP 200 from Runtime. Any live
provider smoke should use non-IP content unless the goal is explicitly to
observe provider policy blocking.

Seedance live video-node success follow-up: 2026-06-26 authorized Runtime smoke
used the deployed `/video-generations` route with `seedance_i2v`, a neutral
non-IP uploaded first frame, and a temporary authenticated server-local session.
The async task reached `succeeded` and wrote one MP4 candidate:
project `codex-video-node-smoke-189aa485`, job
`codex-video-node-smoke-189aa485-video_generation-ac869ed4d54e`,
`candidate_001.mp4`, 2,125,543 bytes, SHA-256
`a3616dccd6eae36689412f5c3525461cfeb612b03c543b4dced1ab8c95a39b27`.
Authenticated preview route returned HTTP 200 `video/mp4` after Runtime
restart. Local `master`, `origin/master`, server `/home`, and server `/opt`
are aligned at `4381b39`; `/health` is ready and video gate is true. Local
media QA from a temp copy: H.264, 1280x720, 24 fps, 5.041667 seconds, 121
frames; black/freeze events both 0. Boundary: runtime/provider/media
verification only, not human creative acceptance of the current IP storyboard;
no provider raw response, signed URL, secret, token, or media byte was written
to Git.

Current video provider addendum: 2026-06-25 pass retires the active Kling video
path and standardizes video generation/revision defaults on the Seedance relay
service `seedance_i2v` (`doubao-seedance-2-0-fast`). Server-side evidence for
the latest failed video node showed the video gate open and provider dispatch
started, but the selected service was the retired `kling_i2v`; this points to a
provider selection/config mismatch, not copyright/safety blocking. Active code,
config templates, CLI support surface, readiness scripts, and focused tests no
longer expose Kling provider entries. Verification: focused provider/Studio/API
regressions passed 105 with 5 deselected and 1 existing warning,
`npm.cmd run check:studio-js` passed for 120 files, and `git diff --check`
passed. Remaining work: deploy the cleanup to origin/server `/home` and `/opt`,
restart Runtime, confirm `/health` video gate/service alignment, then run an
authorized Seedance video smoke from a keyframe first frame.

Seedance 404 follow-up: the deployed provider config uses a shared Crazyrouter
account base URL with `/v1` plus a `seedance_i2v` service-level root base URL
for the Volc endpoint. The Seedance adapter now correctly lets the service
base URL override the account base URL, preventing `/v1/volc/v1/...` create
URLs that returned provider HTTP 404. Focused regression:
`tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py`
passed 15 with 1 existing warning.

Seedance timeout follow-up: the next server smoke no longer returned 404 but
timed out waiting for the create response after the generic 120s request
timeout. Seedance create requests now use the video descriptor async timeout
unless the service explicitly overrides it.

Seedance safe task-state follow-up: after the async timeout fix, a live server
smoke reached the relay and got past create, but Runtime returned a generic
422 because the async provider task state attempted to persist a credential
environment variable name containing the forbidden `api_key` fragment. This is
not a copyright or safety block. Seedance submit tasks now omit credential env
names from persisted task state, and poll rehydrates auth details from provider
config at runtime. Focused regression:
`tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py`
passed 16 with 1 existing warning.

Seedance policy-block follow-up: after the task-state fix, a deployed smoke
submitted successfully and polled the remote task, then the current
Wolverine/Sun Wukong keyframe was rejected by the upstream provider as a
copyright policy violation. The adapter now maps that provider response to a
safe policy-block reason and strips raw provider request ids before surfacing
the error. Runtime safe manifests now use `remote_video_policy_block` for this
case. This confirms the latest failure is content-policy related, not a Kling
fallback, 404, video gate, credential, or task-state persistence issue.

Current keyframe-to-video legacy-node addendum: 2026-06-25 follow-up expands
the right-click `接续视频节点` path so historical completed keyframe image nodes
whose title/prompt marks them as keyframes also get the same automation, even
when they lack newer `keyframe_generation` metadata. The created video node now
gets the keyframe image as explicit first frame plus a draft `videoAssetPlan`
assembled from keyframe visual assets, connected asset-card nodes, and any
remaining `@` references in the keyframe prompt. Prompt-only references fill
missing entries but do not duplicate connected asset cards. Verification:
focused continuation regressions passed 3, broader Studio static regressions
passed 36, `npm.cmd run check:studio-js` passed for 120 files, and
`git diff --check` passed. Residual risk: live provider video smoke and human
motion-quality acceptance remain separate claims.

Current keyframe-to-video addendum: 2026-06-25 pass adds a generic Studio
right-click continuation path from completed keyframe image nodes to video
nodes. The created video node is connected downstream of the keyframe and
stores the keyframe image asset as `firstFrameImageAssetId` with source
keyframe/asset metadata, so image-to-video submission starts from an explicit
first-frame contract instead of searching generated history. Video nodes now
also expose a right-click video asset-card recognition entry that reuses the
existing `afs:video-asset-card-draft` event and tells the user to generate the
video first when no video job exists. The regression is project-neutral and
does not special-case the Sun Wukong / Wolverine script. Verification so far:
focused red/green tests passed 2, broader Studio static regressions passed 35,
and `npm.cmd run check:studio-js` passed for 120 files. Residual risk:
provider-side video smoke and human creative review remain separate claims;
the latest keyframe screenshots still show asset drift from Wolverine wardrobe,
Sun Wukong armor exaggeration, prop-card character pollution, and loose aspect
ratio enforcement.

Current keyframe asset-reference addendum: 2026-06-25 pass inspected the live
Runtime manifests for the current Studio project and found the latest keyframe
failure reached the remote image provider before timing out. The safe blocked
manifest used `remote_image_provider_not_ready`; no copyright or safety block
was returned. Studio now carries connected asset-card image refs into keyframe
generation requests for the same storyboard tree, while fixed visual assets
remain project-wide strong references and unfixed asset cards remain local
candidate references only. Asset-card prompt-bar edits now create a conservative
`user_instruction` revision delta anchored by the prior generated/user
reference images, so typed image-adjustment instructions follow the same
low-drift route as panel field edits. A non-current-story regression
(`林晚 / 雨夜码头 / 蓝色雨伞`) guards against overfitting defaults to the
Sun Wukong / Wolverine test script, and generic prop signatures now summarize
the prop itself instead of copying unrelated shot text. Verification so far:
focused Studio regressions passed 3, broader Studio static regressions passed
33, Runtime keyframe/context regressions passed 37 with 1 existing warning,
`npm.cmd run check:studio-js` passed for 119 files, and `git diff --check`
passed. Local `master`, origin `master`, server `/home`, and server `/opt`
were fast-forwarded to the same commit, then Runtime was restarted with
`/health` ready and provider gates `image=true`, `video=true`. A server-side
keyframe provider smoke using the current storyboard intent succeeded with one
PNG output, confirming the current keyframe issue is not a copyright/safety
block. Residual risk: the smoke output dimensions did not strictly match the
requested `16:9`, so provider aspect enforcement remains a follow-up.

Current scene asset prompt isolation addendum: 2026-06-24 pass fixes the path
where a scene asset such as `山巅石台战场` could regenerate into a character
reference sheet. Scene asset-card defaults now strip story character names,
handheld weapons, and combat-summary text from reusable scene signatures and
feature-card fields; mountain stone-platform battlefields resolve to concrete
environment facts such as stone platform, cliff edge, cloud sea, distant ridges,
broken rocks, cracks, high-altitude light, and weather. Scene image prompts now
state that upstream character names are environmental-trace context only, not
permission to render characters, portraits, turnarounds, weapons, or
silhouettes. Asset-card image nodes now carry only user-uploaded reference
images into a new generation request; prior generated `scene_reference` /
`generated_keyframe_reference` outputs stay in node/history state but do not
auto-contaminate the next asset-card generation. The follow-up pass applies the
same isolation to target character cards: a `金刚狼` role card rejects unrelated
story characters, props, scene labels, shot metadata, and combat-summary text,
and the generated character prompt explicitly requests one target character
only with no second character, handheld prop, or scene background. A further
live-smoke follow-up anchors `金刚狼` away from silver-haired sci-fi armor by
specifying mature rugged male identity, dark short hair, sideburns / stubble,
stocky close-combat build, and body-integrated metal claws while rejecting
monkey traits, silver hair, sci-fi armor, cyan glow lines, and mythic armor.
Server-local image relay validation found the relay cache host was missing from
`codex_image.allowed_artifact_hosts`; the server config was updated without
writing provider key, signed URL, raw provider response, or media bytes to Git.
Verification: focused Studio regressions passed 3, broader Studio static set
passed 31, `npm.cmd run check:studio-js` passed for 119 files, and provider
control dispatch succeeded with one output after the allowlist update.
Remaining validation: GitHub/server three-end sync, Runtime health after
restart, live low-cost scene asset smoke, and browser visual acceptance.

Current asset-card adjustment/recovery addendum: 2026-06-24 pass separates the
asset-card system generation prompt from the editable prompt bar. Asset image
nodes now show only user revision instructions in the bottom input, while the
full typed asset-card prompt is assembled at generation time. Users can upload
reference images directly to an asset-card image node and those uploaded image
asset refs now carry into that asset-card generation request. Timeout recovery
now polls Runtime image assets for up to ten minutes so long provider runs that
finish after a browser timeout can still recover the node preview. Studio state
persistence prunes video media filenames such as `candidate_001.mp4` from safe
display fields before global safety scanning, while preserving safe Runtime
preview routes and asset ids. Verification: focused Studio regressions passed
2, Runtime state regression passed 1 / 1 existing warning, broader Studio
static set passed 28, Runtime Studio state set passed 16 / 1 existing warning,
`npm.cmd run check:studio-js` passed for 119 files, and `git diff --check`
passed. Remaining validation: GitHub/server three-end sync, Runtime health
after restart, and browser visual acceptance.

Current Runtime image timeout addendum: 2026-06-24 follow-up found the latest
Wolverine live smoke was failing because the remote image provider read timed
out and Runtime let the built-in `TimeoutError` escape as HTTP 500 before a
safe manifest could be written. Runtime now retries one provider timeout and,
if it still times out, returns a safe blocked image-generation manifest with
`remote_image_provider_not_ready` instead of leaving an empty run directory.
This failure evidence is provider timeout, not copyright/safety blocking.
Verification: focused Runtime timeout regression passed 1 and
`npm.cmd run check:studio-js` passed for 119 files. Remaining validation:
commit/push, server sync, Runtime restart/health, and another live smoke after
deploy.

Current Studio asset scope addendum: 2026-06-24 pass tightens Studio asset
reference scope and the material/history split. `@` suggestions now treat
ordinary generated image candidates as history, not project-fixed assets:
unconnected nodes only see fixed visual assets, while connected script trees
can also see unfixed asset-card draft nodes in that same connected tree. The
asset drawer now keeps fixed visual assets plus the latest renderable candidate
per source node, and older generated candidates move into `历史资产` with safe
Runtime previews when available. Script node context menus now expose one
`新增资产` action instead of separate role/scene/prop entries; the modal asks for
the asset name, infers the asset type from script/shot context plus conservative
local rules, and creates the same editable asset-card node path. Verification:
focused Studio static regressions passed 5 and `npm.cmd run check:studio-js`
passed for 119 files. Remaining validation: browser visual acceptance,
GitHub/server three-end sync, and Runtime health after restart.

Current Runtime-backed shot asset planning addendum: 2026-06-24 pass adds a
safe `/shot-asset-plans` Runtime route and rewires Studio right-click
`识别资产` to prefer that Runtime planning contract before falling back locally.
The route returns character / scene / prop refs with evidence text and a safe
manifest; it does not create nodes, call media providers, write provider raw
responses, store generated media bytes, or promote fixed memory. Studio now
supports manual asset-card creation from script nodes, project-wide `@`
suggestions for fixed assets, connected-tree-only suggestions for unfixed
asset-card drafts, filtering of retired assets, left-port upstream node
creation, and visible `取消固定资产` from image node menus. Generated image and
video results now support `放大查看`, and image/video export resolves Runtime
media at click time so `导出原图` / `下载视频` is an actual download action instead
of a stale link. Verification: Studio JS syntax check passed for 118 files; full
pytest passed 634 / 520 deselected / 2 existing warnings; CLI help/version
passed; `git diff --check` passed. Remaining validation: GitHub + server
three-end sync, Runtime health after restart, and browser visual acceptance.

Current asset-card fixed-asset carry addendum: 2026-06-24 pass narrows fixed
asset carry behavior for asset-card image generation. Character asset-card
generation automatically excludes unrelated fixed assets, so creating a new
character such as `金刚狼` is not constrained by another fixed character such as
`孙悟空`. Scene and prop asset-card generation treats fixed assets as optional
references: checked assets carry into that one request, unchecked fixed assets
are excluded. Ordinary image and video generation still use the stricter
fixed-asset confirmation path. Verification route: focused Studio static
regression passed 1, `npm.cmd run check:studio-js` passed for 118 files, and
`git diff --check` passed. Remaining validation: GitHub + server three-end
sync, Runtime health after restart, video gate state, and browser visual
acceptance.

Current Seedance video relay addendum: 2026-06-24 pass adds a `volc_seedance`
provider adapter and example `seedance_i2v` descriptor for the target
`doubao-seedance-2-0-fast` relay shape. Runtime now passes the optional last
frame image as a second provider reference for first/last-frame video tasks.
The adapter builds text + image reference payloads for `/volc/v1/contents/generations/tasks`,
polls the task, downloads the video into Runtime candidate storage, and keeps
provider raw responses, provider URLs, signed URLs, secrets, and generated bytes
out of Git and API payloads. Verification: Seedance adapter tests passed 4,
provider/runtime video focused tests passed 41, `npm.cmd run check:studio-js`
passed for 118 files, and `git diff --check` passed. Remaining validation:
server provider-local config alignment, live low-cost video provider smoke,
objective media QA, and human visual acceptance.

Current asset revision reference addendum: 2026-06-23 pass addresses asset-card
regeneration drift where editing a single card detail, such as changing a robot
surface from metal to plush, caused a full text-to-image reinterpretation. The
fix adds a Studio-side `assetCardRevision` plan that preserves ordered safe
image asset refs from prior generated/uploaded candidates, records changed card
fields and preserve locks, and sends only those explicit refs into keyframe
generation for asset-card drafts. Runtime adds an asset-card revision prompt
guard so provider prompts treat references as identity/layout anchors and apply
only the field delta instead of creating a new toy/chibi/mascot-style subject.
The second pass adds field-specific edit policy and prompt-priority handling:
`服装/外观` edits are constrained to outer-garment layering, `外形辨识` material
edits are constrained to surface treatment, and revision instructions are
prepended for asset-card revisions so prompt-length trimming preserves the
changed-field delta and anti-drift constraints.
The third pass upgrades this into reference-first / delta-only semantics:
reference image #1 is the primary visual source of truth for identity,
proportions, reference-sheet layout, camera distance, and non-edited details;
changed card fields are the only editable delta. Runtime avoids the generic
"reference image is only supplemental" guard for asset-card local revision.
The fourth pass upgrades provider dispatch from reference-backed regeneration
to source-image edit semantics for external APIs: asset-card revisions with a
prior image now set `image_operation=edit`, send the first prior image as
`edit_source_image_path`, carry ordered edit references, and request
`image_input_fidelity=high`. OpenAI Images-compatible API relay providers now
use multipart `/images/edits` with the source image in the `image` field for
this path while keeping ordinary generation on `/images/generations`. AFS keeps
the high-fidelity edit intent in request planning, but the OpenAI Images HTTP
payload omits `input_fidelity` unless a provider config explicitly opts in, so
the external API receives only supported default parameters. Provider
descriptors can now allow up to 16 reference image slots for multi-source edit
providers. Runtime also tolerates deployed legacy descriptors that still report
`reference_image_slots=0` by allowing the first prior image to act as the
required edit source for asset-card revisions. Studio labels the action as
`保存并局部修订生成`.
Verification: source-image edit focused regression passed 58 / 1 existing
warning; full pytest passed 626 / 520 deselected / 2 existing warnings;
`npm run check:studio-js` passed for 113 files; CLI help/version passed;
maintenance audit failed=0 with existing warnings only; `git diff --check`
passed. Follow-up provider compatibility regression passed 37 / 1 existing
warning after defaulting multipart image field to `image` and omitting
unsupported `input_fidelity`; legacy zero-slot source-edit regression passed
38 / 1 existing warning. Deployed server provider smoke then succeeded for the
robot metal-to-plush source-image edit: the output preserved multi-view
character-sheet layout, adult humanoid proportions, head shape, blue glow
details, and neutral grey background without chibi/toy drift. Boundary: no
provider raw response, signed URL, secret, local private path, generated media
byte, or Company OS private source content was written to the repo. Remaining
validation: human visual acceptance in the browser workflow.

Current keyframe timeout recovery addendum: 2026-06-23 pass fixes the browser
state mismatch where a long image/asset generation can complete in Runtime
after Nginx/browser request timeout, leaving the asset drawer populated while
the source node still displays failure. Runtime now treats an async-described
API relay result with `already_complete` as a completed image response and
returns safe previews/assets immediately. Studio sanitizes non-JSON 504 HTML,
keeps timed-out generation nodes in recovery, polls Runtime image assets by
`source_node_id`, and restores the node preview/upload refs if the saved asset
appears. Project creation also retries once on transient Runtime network
errors. Scene asset draft defaults now preserve rain-night street cues and only
select rooftop when the shot explicitly mentions rooftop/roof/terrace.
Verification: Studio JS syntax check passed for 113 files; focused timeout /
scene-asset regressions passed 4 / 1 existing warning; broader Runtime/Studio
keyframe-state suite passed 44 / 1 existing warning; `git diff --check`
passed. Maintenance follow-up: extract provider status normalization and
keyframe result recovery out of the existing 500+ line
`apps/api/runtime_keyframes.py`.

Current storyboard / asset intelligence addendum: 2026-06-23 pass upgrades the
script-to-shot and shot-to-asset contract. Local storyboard fallback now uses a
global entity pass plus per-shot resolution, keeps line-based scripts as
line-based shot units, inherits named subjects into pronoun/continuation shots,
and avoids generic `主角` / `主要场景` when concrete script labels exist. It
detects named characters such as `孙悟空`, `金刚狼`, repeated CJK actor names
such as `沈昭昭`, concrete scenes such as `暗办公室` / `山巅石台战场`, and prop
assets such as `金箍棒`. Provider storyboard prompts now explicitly require the
same real-name and prop classification behavior. Asset-card drafts now use a
more detailed typed feature card: character hair/face/build, scene palette, and
prop interaction/continuity are included by default, while character asset
generation is constrained to the fixed layout `正面半身特写 + 全身正面居中 +
左侧面全身 + 背面全身` with no weapons or background objects. Studio also
recovers nodes from reusable image asset previews when candidates are missing,
adds original-resolution image export, and prunes unsafe stale preview state
before Runtime saves. Verification: Studio JS passed for 115 files; storyboard
regressions passed 9 / 1 existing warning; web Studio static contract
regressions passed 31; full `pytest -q` passed 630 / 520 deselected / 2
existing warnings; `git diff --check` passed; added-line sensitive pattern scan
had no output. Remaining validation: deployment to GitHub + server `/home` +
server `/opt`, runtime health, and user visual acceptance in browser.
Maintenance follow-up: split storyboard local entity inference and asset-card
draft heuristics, because the two files are now just over the 300-line warning
threshold but below the 500-line hard split line.

Current Studio asset UX repair addendum: 2026-06-23 pass fixes the active
canvas issues reported from the user screenshots. Storyboard fallback and
provider-discard fallback now preserve semantic asset labels for robot/rooftop
scripts instead of producing generic `主角` / `主要场景`; right-click
`识别资产` reuses the stored structured shot and refines it before creating
candidate asset cards. Text/script/asset-card prompt input now keeps the bottom
prompt bar open while typing, all node double-clicks route to the prompt editor
instead of the create menu, blank-canvas double-click remains the only create
menu path, and node click/drag landing scale animation was removed to stop the
down-right jitter. Asset-card drafts now expose `保存资产卡` and
`保存并重新生成`, leaving final asset fixing optional after visual review.
Verification: focused Runtime/Studio tests passed 17 / 1 existing warning;
provider/static/interaction regression tests passed 33 / 1 existing warning;
`npm run check:studio-js` passed for 111 files; `git diff --check` passed;
maintenance audit failed=0 with existing warnings only; Playwright smoke on
local Runtime 8797 passed for text-node creation, prompt persistence,
storyboard split, semantic asset recognition, and asset-card save/regenerate
visibility. Boundary: no provider gate, secret, signed URL, provider raw
response, generated media byte, user account data, or Company OS private source
content was written. Remaining validation after deploy: public `/studio/`
smoke and human visual acceptance for regenerated asset images.

Current parallel feature integration addendum: 2026-06-23 pass first repaired
the server `/opt/afs/AgentFlowStudio` release checkout from dirty `b24dc57`
metadata to clean `e201346`, preserving the prior diff backup at
`/tmp/afs-opt-dirty-before-e201346-20260622-165701.patch`. It then merged the
Director Stage V2 Runtime compiler contract, TuanTuan confirmed-memory Runtime
API, and public-site social square request board into `master` with
fast-forward commits. A focused test run caught a missing social-square route
module after route registration; the missing `apps/api/runtime_social_square.py`
file was added as a follow-up commit before deployment. The AFS Debug Studio
generation repair at `e201346` was preserved: this integration did not modify
the repaired Studio generation guard, keyframe flow, asset popover, storyboard
fallback, or context resolver files. Verification: integration focused tests
passed 53 / 1 existing warning; full pytest passed 622 / 520 deselected / 2
existing warnings; `npm run check:studio-js` passed for 111 files; CLI
help/version passed; maintenance audit failed=0 with existing warnings only;
`git diff --check` passed. Boundary: no provider secret, provider raw response,
signed URL, generated media byte, user account data, or Company OS private
source content was written. Remaining validation after deploy: public social
square and Runtime health smoke, plus human review for director/sprite/social
product fit.

Current asset image prompt quality addendum: 2026-06-22 pass tightened the
storyboard-to-asset image request contract after live Crazyrouter `gpt-image-2`
outputs still looked abstract and UI-like. Provider-facing asset prompts are now
assembled in `asset-card-image-prompts.js` instead of the asset-card data module;
existing live asset nodes prefer the current structured `asset_card_draft`
prompt before stale `node.prompt`; character/scene candidates default to `16:9`
reference images and prop candidates to `1:1`. The model prompt now says
character turnaround, environment reference, or object reference, explicitly
forbids dashboards, app UI, charts, typography, labels, watermarks, and
decorative card layouts, and strips `@` asset tags before calling the image
provider. Verification: prompt static regressions passed 20; full pytest passed
600 / 520 deselected / 2 existing warnings; `npm run check:studio-js` passed for
110 files; CLI help/version passed; maintenance audit failed=0 with existing
warnings only; `git diff --check` passed; Node prompt sample confirmed no `@`
labels in provider-facing character/scene prompts. Deployment: local, GitHub,
server `/home`, and server `/opt` aligned at `1b9892e`; `afs-runtime` restarted
and health is ready. Live Crazyrouter smoke: character reference image succeeded
in 30.34s; scene reference image succeeded in 29.23s; both produced 16:9
non-UI reference images and did not collapse role/scene into the same abstract
picture. Boundary: no provider secret, provider raw response, signed URL,
generated media byte, user account data, or Company OS private source content
was written to repo records. Remaining validation: user canvas regeneration and
human visual acceptance.

Current asset reference lookup / keyframe flow addendum: 2026-06-22 pass fixed
the live-canvas failure where editing a fixed asset card and regenerating could
fail with `named_asset_not_connected_fail_closed`. Runtime context resolution
now includes fixed assets explicitly mentioned by `@label` even if they are not
connected to the target node; connected graph assets still retain distance
priority. The Studio preflight guard no longer hard-fails on unconnected named
assets and instead offers a one-run exclusion fallback. Storyboard keyframe
layers can now be created and generated without fixed candidate asset cards;
candidate cards remain editable review material until promoted. Fixed assets can
also be cancelled from the asset detail popover, which calls the Runtime retire
route and marks local refs as retired/excluded. Local storyboard fallback now
uses adaptive sentence/length distribution instead of mechanical three-sentence
chunks, reducing the apparent "always three shots" behavior when LLM breakdown
is gated off or discarded. Verification: focused Runtime/Studio regressions
passed 49 / 1 existing warning; `npm run check:studio-js` passed for 110 files;
CLI help/version passed; maintenance audit failed=0 with existing warnings
only; `git diff --check` passed; full pytest passed 602 / 520 deselected / 2
existing warnings. Boundary: no provider secret, provider raw response, signed
URL, generated media byte, user account data, or Company OS private source
content was written. Remaining validation: fresh user canvas regeneration and
human visual acceptance.

Current Crazyrouter image relay addendum: 2026-06-22 pass added
OpenAI Images-compatible `api_relay` support so `codex_image` can be switched
server-side to Crazyrouter `gpt-image-2` without changing Studio front-end
model IDs. The relay can now send `/images/generations` payloads and download
`data[0].url` provider media into local AFS candidate artifacts without
persisting provider URLs or raw responses. Server diagnosis before the switch
showed current `afs-runtime` was still loading
`/opt/afs/AgentFlowStudio/configs/providers.local.json`, had no Crazyrouter
service in the active registry, and did not have `CRAZYROUTER_API_KEY` in the
service environment; a user shell export is not sufficient for live Runtime
generation. Verification: provider registry tests passed 30; focused provider /
Studio / image-handoff regressions passed 95 with 1 existing warning; JS syntax
check passed for 109 files; `git diff --check` and provider module compile
passed. Remaining blocker: persist the Crazyrouter key and provider config into
systemd, restart Runtime, then run a real low-cost image smoke before claiming
speed or visual-quality improvement.

Current asset reference sheet addendum: 2026-06-22 pass changed the
storyboard-to-asset target from generic asset pictures to reviewable reusable
definition boards. Candidate role assets now ask for multi-view character
sheets; scene assets ask for same-space multi-angle environment boards; prop
assets ask for front/side/top/detail object sheets. Candidate asset cards and
fixed-asset review cards now carry reference-view fields, and fixing a
storyboard-derived asset image keeps the original asset-card draft defaults
instead of degrading to generic reference-image wording. Asset-tag markers such
as `@主角（角色）` are stripped before deriving short signature/mood text, and
the current robot rooftop case now gets local defaults for robot structure,
cold-blue metal palette, rooftop skyline layout, and moon/star/neon lighting.
Verification: `npm run check:studio-js` passed for 109 files; focused Studio
asset/prompt/runtime-state tests passed 48 / 1 existing warning; full pytest
passed 598 / 520 deselected / 2 existing warnings; CLI help and version
passed; maintenance audit failed=0 with existing warnings only; `git diff
--check` passed. Boundary: provider gates were not changed and no media bytes,
provider raw response, signed URL, secret, user account data, or Company OS
private source content was written. Remaining user-facing risk: final visual
quality still needs a fresh live generation and human acceptance on the canvas.

Current asset image generation audit addendum: 2026-06-22 pass fixed the
live-canvas issue where角色/场景 asset-card image nodes could generate the same
abstract picture. Root cause was request construction: asset-card nodes often
had empty `node.prompt`, so image generation fell back to a generic prompt and
the context resolver injected the same upstream storyboard text for both assets.
Asset-card image nodes now build requests from the editable asset card body and
safe `asset_card_draft` snapshot, add type-specific guards for character /
scene / prop asset images, label progress and result text as `资产图生成`, and
store generated uploads as character / scene / prop references rather than
generic keyframe references. Codex image handoff jobs now project safe
created/started/completed plus elapsed/queued/running seconds through Runtime
polling so long generation can be distinguished from queue wait. Verification:
full pytest passed 598 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 108 files; CLI help and version passed; focused
image-handoff and Studio asset/front-end regressions passed; `git diff --check`
Python compile checks, and maintenance audit passed with warnings only.
Deployment: GitHub `master`, server `/home/afs-ops/AgentFlowStudio`, and
server `/opt/afs/AgentFlowStudio` aligned at `94fb9e1`; `afs-runtime` and
`afs-codex-image-worker` are active; Runtime health is ready. Boundary:
provider gates were not changed; no generated media byte, provider raw
response, signed URL, secret, invite code, session token, user account data, or
Company OS private source content was written. Remaining user-facing risk: live
image quality still depends on the active image provider/worker, but the
request now gives role-specific inputs instead of duplicated keyframe prompts.

Current Studio chain regeneration addendum: 2026-06-22 pass fixed the
internal-test chain issues found on the live canvas. Runtime Studio state now
keeps safe structured params for storyboard shots, asset-card drafts, fixed
visual assets, keyframe layers, uploads, warnings, and one-run exclusions, so
reload/server save no longer erases the reviewed production graph. Storyboard
LLM JSON parsing accepts fenced/trailing output instead of silently degrading
to coarse text splitting, and the local fallback no longer misclassifies
contextual `信号` / `灯火` as prop assets. Valid-but-sparse provider storyboard
JSON is now quality-gated for long scripts and falls back explicitly when it
lacks enough shots, visual detail, or asset refs. Candidate asset-card images remain
editable drafts and are excluded from keyframe prompt/context until human
confirmation promotes them to fixed assets; keyframe nodes show missing
candidate cards and block generation before fixed assets exist. Keyframe
polling now reduces repeated full-state saves to lower Runtime pressure during
long image jobs. Verification before merge: full pytest passed 597 / 520
deselected / 2 existing warnings; `npm run check:studio-js` passed for 107
files; CLI help and version passed; full Studio browser QA passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed. Boundary: no
provider raw response, signed URL, local media byte, secret, invite code,
session token, or Company OS private source content was written. Project
lesson to retain: candidate/fixed asset separation must be enforced in
Runtime state, node UI state, and prompt assembly, not only in labels.

Current script review flow addendum: 2026-06-22 pass changed the active
text-to-storyboard chain to the reviewed sequence. Text-node `拆分为分镜` now
routes through Runtime `/storyboard-breakdowns`, uses LLM only behind the LLM
provider gate, falls back to deterministic structured splitting when the gate is
closed, and creates only editable storyboard script nodes. The canvas bottom
workflow toolbar row (`继续生成 / 保存素材 / 整理卡片 / 看过程`) is retired across
nodes. Text, script, and asset-card nodes expose editable scrollable body text,
and node double-click opens the prompt bar while blank-canvas double-click still
opens node creation. Storyboard nodes now gate downstream automation: `识别资产`
creates editable asset-card image nodes from the current reviewed storyboard
text, and `生成关键帧层` requires an existing asset layer rather than silently
creating it. Completed asset image nodes show the generated image preview while
preserving the editable asset draft in `params.assetCardDraft`. Verification:
focused storyboard/API/static regression passed 39 / 1 existing warning; full
pytest passed 592 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 107
files; CLI help and version passed; full coverage browser QA passed with
console_error_count=0, response_error_count=0, provider_calls_started=false;
maintenance audit failed=0 with warnings only; `git diff --check` passed.
Boundary: provider gates were not opened; no merge, push, deployment, server
sync, generated media, raw provider response, signed URL, local media byte,
secret, invite code, session token, or Company OS private source content was
written; this is local code/runtime evidence, not human acceptance, provider
smoke, business validation, or durable memory promotion.

Current storyboard asset-card and keyframe-layer addendum: 2026-06-22 pass
connected structured storyboard nodes to editable candidate asset cards and a
fixed-asset-only keyframe layer. Script nodes now expose `识别资产` and
`生成关键帧层`; identified角色/场景/道具 become downstream image nodes with
`params.assetCardDraft`, while `params.visualAssets` remains reserved for
human-confirmed fixed assets. Keyframe nodes connect to the storyboard and
asset-card nodes, but inject only fixed visual assets into their prompt/context
and record unconfirmed candidate nodes as missing. Prop assets are now supported
across Studio panels, summaries, drawer actions, Runtime draft/promotion
contracts, context asset limits, and asset-card drafting. Verification: full
pytest passed 587 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 107 files; CLI help and version passed; full
coverage browser QA passed; maintenance audit failed=0 with warnings only; `git
diff --check` passed with CRLF/LF warnings only. Boundary: provider gates were
not opened; no merge, push, deployment, server sync, raw provider response,
signed URL, local media byte, secret, invite code, session token, or Company OS
private source content was written; this is code/runtime evidence, not human
acceptance, provider smoke, business validation, or durable memory promotion.

Current prompt/template and provider cleanup addendum: 2026-06-21 pass repaired
the reference-image prompt contract that was leaking old human-edit wording into
animal image flows. Active prompt sections now use `角色/主体`; animal reference
flows preserve fur, markings, eyes, ears, tail, and body ratio while treating
old asset signatures and default locks as lower-priority context. Explicit
animal clothing/stylization requests are allowed only when the user asks for
them, preventing the previous conflict between "cat dancing" and human
short-hair/uniform constraints. Minimax image/provider paths were removed from
the active registry, CLI, posterflow provider, smoke helpers, and preflight
tools; only negative compatibility tests remain. Prompt optimization now runs
inline with shimmer feedback instead of a blocking modal, fixed assets can be
reopened for adjustment, and the Codex image worker can recover stable
candidate files from stale/running jobs. Verification: full pytest passed 582 /
520 deselected / 2 existing warnings; `npm run check:studio-js` passed for 102
files; CLI help and version passed; maintenance audit failed=0 with warnings
only; `git diff --check` passed with existing CRLF/LF warnings only. Boundary:
video provider execution remains out of scope; this is code/runtime evidence,
not human acceptance, business validation, or durable memory promotion.

Current text-to-storyboard authoring addendum: 2026-06-22 pass moved text-node
script import and idea expansion results into the node body instead of the
bottom prompt input, with a visible shimmer state while the source text is being
expanded. Text nodes now hide the selected-node workflow toolbar to remove the
`继续生成 / 保存素材 / 整理卡片 / 看过程` clutter from script drafting. Script
breakdown now creates structured storyboard script nodes with explicit `镜号 /
时长 / 画面描述 / 景别 / 光影氛围 / 运镜 / 对白/旁白 / 音效 / 资产` fields and
candidate `@` asset references, then spawns downstream image asset-prep nodes
for the identified角色/场景/道具 candidates. Verification: prompt/script
focused static tests passed 5; Studio static regression set passed 30;
`npm run check:studio-js` passed for 102 files; full coverage browser QA passed
with `provider_calls_started=false`; `git diff --check` passed with existing
CRLF/LF warnings only. Boundary: asset-prep nodes are candidates only, not
fixed assets, durable memory promotion, human acceptance, provider smoke, or
business validation; no Runtime API shape, provider gate, server state, secret,
signed URL, session token, invite code, provider raw response, local media byte,
or Company OS private source content was written.

Current authenticated media and TuanTuan stability addendum: 2026-06-21 pass
fixed broken uploaded/reference image rendering in image nodes and the asset
drawer without weakening Runtime media auth. Studio now fetches protected
`/projects/...` media with the current logged-in session and assigns blob URLs
at render boundaries for node previews, candidate grids, job thumbnails,
downloads, and asset thumbnails. TuanTuan now rejects LLM prompt/persona echo,
falls back to safe first-person replies, preserves chat scroll across rerenders,
and avoids full redraw during IME composition so Chinese input does not lose
focus. Codex image handoff polling can recover a stable generated candidate
from a job still marked running, and Studio startup/project switch now performs
a one-shot refresh for image nodes still marked `generating`, reducing stale
progress failures after a page refresh or interrupted session. Runtime poll
also now recovers a stale terminal failed/blocked state when the Codex handoff
worker has already written a completed safe candidate result. Verification:
focused regression passed 33 / 1 existing warning; Codex handoff regression
passed 9 / 1 existing warning; keyframe/frontend regression passed 22 / 1
existing warning; full pytest passed 575 / 527
deselected / 2 existing warnings; `npm run check:studio-js` passed for 99
files; CLI help and version passed; maintenance audit failed=0 with warnings
only and oversized warning count reduced from 37 to 36 after moving protected
media DOM logic into a single-purpose helper; `git diff --check` passed.
Boundary: video remains out of scope; backend media auth was not opened; no
provider raw response, signed URL, local media byte, secret, invite code,
session token, or Company OS private source content was written; not human
acceptance, business validation, or durable memory promotion.

Current non-video Codex flow and Studio feedback repair addendum: 2026-06-21
pass fixed the image handoff worker's Codex CLI resolution for service
environments, restored readable prompt optimizer retry instructions, tightened
TuanTuan's first-person persona prompt, hard-limited TuanTuan LLM replies to
two sentences / 220 characters, added a visible TuanTuan pending state, moved
media quality feedback to the node right-click menu, made completed image nodes
fill their node body, and adjusted prompt bar placement to avoid the selected
node. Verification: full pytest passed 562 / 527 deselected / 2
existing warnings; `npm run check:studio-js` passed for 96 files; CLI help and
version passed; local Playwright smoke on 8797 passed image fill, right-click
feedback, prompt-bar avoidance, TuanTuan pending state, and no internal
Codex/server wording; `git diff --check` passed. Boundary: video remains out
of scope; no provider raw response, signed URL, local media byte, secret,
invite code, session token, or Company OS private source content was written;
browser smoke used intercepted Studio state and sprite response, not human
acceptance or business validation.

Current public edge and TuanTuan usability addendum: 2026-06-21 pass reduced
the default TuanTuan canvas footprint from 260 x 238 to 232 x 212 and lowered
the default scale to 0.9. The sprite settings panel now supports `关闭团团`,
persisted through `afs_studio_sprite_hidden`, and a small `显示团团` restore
chip keeps the feature reversible without clearing browser storage.
Verification: focused sprite/runtime tests passed 6 / 1 existing warning;
`npm run check:studio-js` passed for 96 files. Public edge status remains
`blocked_by_edge_basic_auth`; server dry-run for
`tools.afs_public_edge_nginx_fix --config /etc/nginx/sites-available/afs-runtime`
returned `ready_to_apply` and `target_line_count=2`, but the file is root-owned
and the current SSH user lacks passwordless sudo, so the Nginx removal still
needs one interactive sudo application. Boundary: no Runtime API shape changed,
no provider gate/config/call, no invite code/session token/provider raw
response/signed URL/local media byte/secret was written; not invite-login
acceptance, human acceptance, business validation, or durable memory promotion.

Current server Codex LLM path addendum: 2026-06-21 pass verified local
`master`, `origin/master`, server `/home`, and server `/opt` were aligned at
`0205148`. The deployed TuanTuan fallback was traced to the Runtime systemd
environment not resolving the local `codex` executable, even though the sprite
route already used the unified LLM dispatch. Server-local `codex_local`
provider services were pointed at `/home/afs-ops/.local/bin/codex`, then
provider-level and Runtime route smoke checks for `sprite_chat` passed with
`provider_calls_started=true` and `mode=llm`. Local code now wraps a missing
Codex CLI as `ModelGatewayError` with a regression test. Verification:
provider/sprite/registry focused tests passed 37 / 1 existing warning.
Boundary: video remains disabled; no ASR or external-download gate was opened;
no provider raw response, invite code, session token, signed URL, local media
byte, secret, or Company OS private source content was written; public
authenticated browser UI chat remains a separate human-session check.

Current TuanTuan reference-shape lock addendum: 2026-06-20 pass fixed,
calibrated, and then reset the Studio `story-cat` visual baseline around the
latest user-approved dark TuanTuan reference. The default canvas companion is
now a low-profile dark tabby story cat with a wider resting body, larger
triangular ears, brighter inner ear rims, black pupils with blue-white
highlights, a quiet sprout, forepaws, rear paw, closed curled tail, body tabby
marks, whiskers, and a cyan story orbit. The story belly panel remains a
low-opacity internal symbol so TuanTuan reads as a canvas-native story cat
rather than a robot or sticker. The implementation remains DOM/SVG/CSS instead
of raster pose swaps, preserving a path toward continuous interaction.
Verification: focused sprite static test passed; `npm run check:studio-js`
passed for 96 files; in-app browser render smoke confirmed viewBox `0 0 390
230`, ears=2, innerEars=2, eyes=2, pupils=2, tailShapes=1, tabbyMarks=4,
orbitNodes=5, state=observe, and no old PNG/sticker sprite path.
Boundary: no Runtime API shape changed, no provider gate/config/call, no local
reference image, provider raw response, signed URL, media byte, invite code, or
secret was exposed; not final IP acceptance, human acceptance, business
validation, or durable memory promotion.

Current Studio mascot and edge disconnect addendum: 2026-06-19 pass made two
front-end interaction improvements requested during Studio polish. The movable
`AFS 小精灵` now uses a cartoon mascot skin through
`apps/studio/styles/studio-sprite-avatar-mascot.css`, opens a small settings
panel on right-click, and persists local size choices through
`afs_studio_sprite_scale`. Canvas connections now support natural removal:
clicking an edge selects it, a compact inline disconnect control appears on the
line, and Delete / Backspace removes the selected connection through the same
store mutation path. Verification: sprite and edge tests first failed on the
missing mascot skin and missing edge-action module, then passed after
implementation; focused Studio/sprite regression passed 28 / 1 existing warning;
`npm run check:studio-js` passed for 94 files; browser smoke confirmed the
mascot rendered, size persisted, old mechanical body stayed hidden, and the
real render-chain edge disconnect removed edge `e1`; maintenance audit
failed=0 with warnings only; `git diff --check` passed with one CRLF
normalization warning for `apps/studio/src/nodes.js`. Boundary: no Runtime API
shape changed, no provider gate changed, no provider config changed, no
provider call was made, and no provider raw response, signed URL, local media
byte, local path, invite code, or secret was exposed; not human acceptance or
business validation.

Current Studio generation action module split addendum: 2026-06-19 pass split
`apps/studio/src/node-actions.js` from a 446-line mixed action/generation module
into an 80-line top-level node action router plus focused generation helpers:
`node-keyframe-actions.js` for keyframe submit/poll/result persistence and
`node-video-actions.js` for video first-frame setup, video submit/poll/cancel,
and experimental video revision state. Existing public imports remain available
through `node-actions.js`, so prompt bar, node menu, and canvas action handlers
do not change their call surface. Verification: structure tests first failed on
missing `node-keyframe-actions.js` and then on missing `node-video-actions.js`;
after implementation Studio static regression passed 43; wider Studio/runtime
focused regression passed 60 / 1 existing warning; `npm run check:studio-js`
passed for 90 files; full pytest passed 536 / 527 deselected / 2 existing
warnings; maintenance audit failed=0 with warnings only and oversized warning
count dropped from 34 to 33, with `node-actions.js` removed from oversized
findings; local HTTP static checks returned 200 for `/studio/`,
`/studio/src/node-keyframe-actions.js`, and `/studio/src/node-video-actions.js`;
`git diff --check` passed. Boundary: no Runtime API shape changed, no provider
gate changed, no provider config changed, no provider call was made, no Studio
UI behavior was intentionally changed, and no provider raw response, signed
URL, local media byte, local path, invite code, or secret was exposed; not human
acceptance or business validation.

Current LLM enhancement module split addendum: 2026-06-19 pass split
`apps/api/runtime_llm_enhancement.py` from a 600+ line prompt optimization
runtime module into a 181-line orchestration surface plus focused helpers:
`runtime_llm_enhancement_constants.py`, `runtime_llm_enhancement_gate.py`,
`runtime_llm_enhancement_safety.py`, `runtime_llm_enhancement_instructions.py`,
`runtime_llm_enhancement_fallback.py`, and
`runtime_llm_enhancement_dispatch.py`. The route-facing module keeps existing
compatibility exports and monkeypatch seams, including `load_provider_registry`,
`llm_provider_gate`, `provider_text_requested`, `sanitize_enhanced_prompt`, and
`deterministic_chinese_fallback_prompt`, while the helper modules keep provider
selection, safety parsing, fallback prompt construction, instruction assembly,
and dispatch fallback under separate maintenance thresholds. Verification:
structural split test first failed on missing helper modules, then passed after
implementation; UTF-8 label guard was added to prevent Chinese prompt contract
drift; LLM prompt-memory regression passed 18 / 1 existing warning; wider
focused Runtime set passed 59 / 1 existing warning; full pytest passed 536 /
527 deselected / 2 existing warnings; CLI help and version passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed. Boundary: no
Runtime API shape changed, no provider gate changed, no provider config changed,
no provider call was made, and no provider raw response, signed URL, local media
byte, local path, or secret was added to API payloads or reports; not human
acceptance or business validation.

Current sprite companion personality polish addendum: 2026-06-19 pass refined
the movable `AFS 小精灵` from a parts-heavy helper into a clearer Studio
navigator character. The widget now declares `data-sprite-character="navigator"`
and adds a halo crown, glass helmet, face window, small wand, and personality
tag, with the final silhouette isolated in
`apps/studio/styles/studio-sprite-avatar-personality.css` so existing sprite
CSS files stay below the maintenance threshold. Verification: sprite static
test first failed on the missing character-shape contract, then passed after
the implementation; `npm run check:studio-js` passed for 88 files; browser QA
on `127.0.0.1:8797/studio/` confirmed the new parts rendered, cursor was
`grab`, drag moved the sprite from `(558, 191)` to `(478, 151)`, opening the
panel kept the moved position, and console warn/error count was 0. Boundary:
no Runtime API shape changed, no provider gate changed, no provider call, no
provider raw response, signed URL, local media byte, or secret exposure; not
human acceptance or business validation.

Current video routes module split addendum: 2026-06-19 pass split
`apps/api/runtime_video_routes.py` from a 739-line route/orchestration module
into a 105-line route assembly surface plus focused helpers:
`runtime_video_constants.py`, `runtime_video_gate.py`,
`runtime_video_prompt.py`, `runtime_video_candidates.py`,
`runtime_video_manifest.py`, `runtime_video_task_state.py`, and
`runtime_video_dispatch.py`. The route module keeps the compatibility exports
used by existing tests, including `VideoGenerationRequest`,
`load_provider_registry`, and `_video_provider_prompt`, while dispatch receives
the registry loader by dependency injection so existing monkeypatch tests keep
covering provider-gate behavior. Verification: structural split test first
failed on missing helper modules, then passed after the split; video/runtime
focused regression passed 17 / 1 existing warning; wider video, manifest,
ModelCallContext, internal-beta, and three-end focused set passed 34 / 1
existing warning; maintenance audit failed=0 with warnings only and oversized
warning count dropped from 36 to 35; `git diff --check` passed. Boundary: no
Runtime API shape changed, no provider gate changed, no provider call, no
provider config, local media byte, local path, signed URL, provider raw
response, invite code, or session token was added to API payloads or reports;
not human acceptance or business validation.

Current sprite companion redesign addendum: 2026-06-19 pass reworked the
movable `AFS 小精灵` visual layer from a subtle component cluster into a more
recognizable Studio companion. The avatar footprint was expanded to 180 x 206,
with a stronger silhouette, visible drag handle, clearer eyes/visor, arms,
feet, scarf, status light, and docking label. Position clamping now uses the
larger character bounds while preserving viewport-only local persistence and
the existing Runtime `sprite/chat` boundary. Verification: sprite/Studio
focused regression passed 16 / 1 existing warning; `npm run check:studio-js`
passed for 88 files; browser QA on `127.0.0.1:8797/studio/` confirmed role
parts rendered, cursor=grab, drag moved the sprite from `(628, 228)` to
`(558, 191)`, opening the panel kept the same position, panel docked below in
the top half of the viewport, and console warn/error count was 0; maintenance
audit failed=0 with warnings only and the new CSS file stayed under the
maintenance line threshold; `git diff --check` passed. Boundary: no provider
gate changed, no provider call, no provider raw response, signed URL, local
media bytes, or secret exposure; not human acceptance or business validation.

Current Studio state module split addendum: 2026-06-19 pass split
`apps/api/runtime_studio_state.py` from a route plus sanitizer file into a thin
route module and focused safe-state helpers:
`runtime_studio_state_sanitizer.py`, `runtime_studio_state_context.py`,
`runtime_studio_state_assets.py`, and `runtime_studio_state_preview.py`.
The public `sanitize_studio_state` compatibility export remains available
from the route module, while preview URL allow-listing, context bundle
projection, and asset-list sanitization now have separate regression coverage.
Verification: Studio state focused regression passed 10 / 1 existing warning;
Runtime/internal-beta focused set passed 32 / 1 existing warning; full pytest
passed 534 / 527 deselected / 2 existing warnings; maintenance audit failed=0
with warnings only and oversized warning count dropped from 37 to 36;
`git diff --check` passed. Boundary: no Runtime API shape changed, no auth
policy changed, no provider gate changed, no provider call, no local path,
signed URL, provider raw response, media byte, invite code, or session token
was added to persisted Studio state; not human acceptance or business
validation.

Current internal beta acceptance split addendum: 2026-06-19 pass split HTTP
preflight readiness logic out of `tools/afs_internal_beta_acceptance.py` into
`tools/afs_internal_beta_acceptance_preflight.py`, and moved the shared
configuration error into `tools/afs_internal_beta_acceptance_errors.py`. The
runner now remains a thin CLI/in-process/HTTP acceptance wrapper while
continuing to export `run_http_preflight` for existing callers. The preflight
contract still reports Runtime `/health`, `/auth/status`, Studio static
readiness, provider gate projection, and optional safe three-end status without
requiring invite codes or starting provider calls. Verification: red/green
split test added; internal beta plus three-end focused regression passed 16 /
1 existing warning; full pytest passed 531 / 527 deselected / 2 existing
warnings; maintenance audit failed=0 with warnings only and oversized warning
count dropped from 40 to 39; `git diff --check` passed. Boundary: no provider
gate changed, no provider call, no invite code/session token/base URL/local
path/signed URL/provider raw/media byte added to reports; not human acceptance
or business validation.

Current sprite companion design addendum: 2026-06-19 pass strengthened the
decorative `AFS 小精灵` from a floating helper into a clearer movable companion.
The avatar now declares `data-sprite-role="movable-companion"` and adds a hood,
explicit left/right eyes, torso panel, nameplate, and visible drag hint while
preserving the existing Runtime `sprite/chat` boundary. Pointer capture is now
defensive so browser automation or synthetic pointer events cannot break drag
startup. Verification: sprite static test passed; Runtime sprite regression
passed 6 / 1 existing warning; Studio JS syntax check passed for 88 files;
full pytest passed 530 / 527 deselected / 2 existing warnings; maintenance
audit failed=0 with warnings only; `git diff --check` passed; Chrome
automation on `127.0.0.1:8797/studio/` confirmed character parts rendered,
drag moved and persisted viewport position, panel open kept position stable,
green open status light, and zero console warn/error. Boundary: no provider
gate changed, no provider call, no provider raw response, no signed URL, no
local media bytes, no secret exposure; not human acceptance or business
validation.

Current sprite draggable character addendum: 2026-06-19 pass made the
decorative `AFS 小精灵` more clearly movable and character-shaped. The avatar
now includes a dedicated character silhouette layer, visible move handle,
left/right ear fins, scarf accent, and keyboard arrow-key nudging in addition
to pointer dragging. The visual shell was split into
`apps/studio/styles/studio-sprite-avatar-character.css` to keep existing
sprite files under the project maintenance warning line. Verification:
sprite static test passed; Studio JS syntax check passed for 87 files; focused
Runtime sprite tests passed; in-app browser on `127.0.0.1:8797/studio/`
confirmed role parts rendered, pointer drag movement, arrow-key movement,
panel-open position stability, green open status light, and zero console
warn/error. Boundary: no provider gate changed, no provider call, no provider
raw response, no signed URL, no local media bytes, no secret exposure; not
human acceptance or business validation.

Current HTTP preflight three-end addendum: 2026-06-19 pass connected the safe
three-end status reporter into `tools/afs_internal_beta_acceptance.py
--preflight-only` through explicit `--three-end-status`,
`--three-end-repo-root`, and `--three-end-server` parameters. The resulting
preflight report can now include local/GitHub/server drift state alongside
Runtime `/health`, `/auth/status`, Studio static readiness, and provider gate
projection. If three-end status is not `aligned`, the report becomes
`needs_attention` even when Runtime health passes. The collection and
whitelist projection live in `tools/afs_internal_beta_preflight_three_end.py`
so the new safety projection stays isolated from the acceptance runner; the
runner itself remains an existing maintenance split candidate. Verification:
preflight tests 10 passed / 1 warning; three-end plus preflight focused tests
15 passed / 1 warning; CLI help exposes the new flags. Boundary: no provider
gate changed, no provider call, no invite code/session token/base URL/local
path/signed URL/provider raw/media byte in the report; not human acceptance or
business validation.

Current sprite character design addendum: 2026-06-19 pass reworked the
decorative `AFS 小精灵` from a button-like floating helper into a clearer
movable canvas companion. It now has a larger fixed footprint, visible drag
chip, cockpit glass, canopy highlight, scanner visor, cheek/mouth detail,
status light, shoulders, arms, mittens, wings, feet, tail fin, dock ring, glow
trail, and thruster. Dragging remains available from the avatar and panel
header, the position clamp separates width and height, and only viewport
coordinates are persisted in local storage. Limb and propulsion styles live in
`apps/studio/styles/studio-sprite-avatar-parts.css` so sprite files remain
under the project maintenance warning line. Verification: sprite static plus
Runtime sprite tests 6 passed / 1 warning; Studio JS syntax check passed for 87
files; `git diff --check` passed; browser check on `127.0.0.1:8799/studio`
confirmed character parts=8, avatar drag movement, panel-header drag movement,
position storage, panel open state, viewport clamp, green open status light,
and console warn/error count=0. Boundary: no provider gate changed, no provider
call, no provider raw response, signed URL, local media bytes, or secret
exposure; not human acceptance or business validation.

Current three-end status addendum: 2026-06-19 pass added
`tools/afs_three_end_status.py` as a safe local/GitHub/server status reporter.
It checks the local checkout, optional server `/home` checkout, optional server
`/opt` checkout, and Runtime `/health` using safe fields only. The report
captures commit alignment, dirty state, Studio static readiness, auth
readiness, and provider gate booleans without recording provider config,
server-local runtime paths, signed URLs, session tokens, provider raw
responses, media bytes, or secrets. Empty or failed checked health is now
treated as `needs_attention` rather than silent success. Verification:
three-end status tests 5 passed; three-end plus beta acceptance focused tests
13 passed / 1 warning; full pytest passed 528 / 527 deselected / 2 warnings;
maintenance audit failed=0 with warnings only; `git diff --check` passed.
Boundary: ops/readiness report only, not git pull/deploy/restart automation,
not provider smoke, not human acceptance, not business validation, not
durable-memory promotion.

Current HTTP internal beta preflight addendum: 2026-06-19 pass added
`--preflight-only` to `tools/afs_internal_beta_acceptance.py`. This mode checks
deployed Runtime readiness through `/health` and `/auth/status` without
requiring disposable invite codes and without executing the full acceptance
contract. The safe report covers runtime health, auth surface, Studio static
readiness, provider gate projection, and non-claims while excluding base URLs,
invite codes, session tokens, signed URLs, provider raw responses, media bytes,
and local paths. Verification: preflight tests 8 passed / 1 warning; local dev
preflight against `127.0.0.1:8797` returned `needs_attention` because
`auth_required=false`, with `provider_calls_started=false`; CLI help/version
passed; full pytest passed 523 / 527 deselected / 2 warnings; maintenance audit
failed=0 with warnings only; `git diff --check` passed. Boundary: readiness
inspection only, not full HTTP beta acceptance, not provider smoke, not human
acceptance, not business validation, not durable-memory promotion.

Current HTTP internal beta acceptance addendum: 2026-06-19 pass extended
`tools/afs_internal_beta_acceptance.py` from in-process deterministic contract
verification to deployed Runtime HTTP contract verification. The tool now
accepts `--base-url` and disposable invite codes via CLI flags or
`AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE` /
`AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA`, generates isolated project
IDs and emails per run, and keeps reports free of invite codes, session tokens,
passwords, base URLs, local paths, provider raw responses, signed URLs, and
media bytes. HTTP mode requires two disposable invite codes so the alpha/beta
project-isolation checks exercise separate users. The HTTP client disables system proxy inheritance with
`trust_env=False` to connect directly to the target Runtime. Verification:
acceptance tests 6 passed / 1 warning; default in-process runner returned
`contract_verified_pending_human_acceptance`; HTTP missing-invite mode returned
safe `configuration_error`; temporary local Runtime HTTP smoke returned
`deployed_http_runtime`, 12 steps, 0 failed, provider_calls_started=false; full
pytest passed 521 / 527 deselected / 2 warnings; maintenance audit failed=0
with warnings only; `git diff --check` passed.
Boundary: deployed Runtime contract verification only, not live provider smoke,
not human acceptance, not business validation, not durable-memory promotion.

Current sprite avatar polish addendum: 2026-06-19 pass strengthened the
decorative `AFS 小精灵` into a more recognizable movable canvas companion. The
avatar now has an explicit drag halo, larger body shell, head shell, visor, core
light, side wings, feet, and bottom thruster; the fixed layer sits above modal
level so the sprite remains reachable while Studio panels are open. The drag
state now remembers the current DOM position before re-rendering, preventing a
post-drag panel-open click from jumping the sprite back to an older stored
position. Verification: focused sprite static test passed; Studio static plus
Runtime sprite regression 16 passed / 1 warning; Studio JS syntax check passed
for 87 files; `git diff --check` passed; browser check on
`127.0.0.1:8797/studio` confirmed avatar parts, z-index=81, avatar drag,
open-panel position delta=0, panel-header drag, and console warn/error count=0.
Boundary: no provider gate changed, no provider call, no generated media byte
persistence, no human acceptance, no business validation, no durable-memory
promotion.

Current sprite character follow-up: 2026-06-19 pass reworked the decorative
`AFS 小精灵` into a fixed-viewport micro-assistant character instead of a
generic floating control. The avatar now has a recognizable visor, glowing
core, side stabilizers, feet, antenna, shadow, and docking label; it can be
moved by dragging the avatar or the open panel header. The idle breathing
motion now runs on the inner body rather than the clickable shell, keeping the
hit target stable for browser automation. Verification: browser check on
`127.0.0.1:8797/studio` confirmed fixed layer, avatar drag, panel-header drag,
character parts present, and console warn/error count=0; Studio static
regression 11 passed; sprite Runtime regression 5 passed / 1 warning; Studio
JS syntax check passed for 87 files; `git diff --check` passed. Boundary: no
provider gate changed, no provider call, no generated media byte persistence,
no human acceptance, no business validation, no durable-memory promotion.

Current Studio panels and sprite assistant addendum: 2026-06-19 pass fixed the
remaining persistent-edge gap by anchoring saved edges to the node frame
boundary while keeping drag previews tied to the plus port. The Studio shell now
has a draggable left drawer width, collapsible right inspector, and
non-selectable chrome with form fields still selectable. A decorative `AFS
小精灵` was added through Runtime endpoint
`/projects/{project_id}/sprite/chat`; it uses the unified LLM dispatch only
when the LLM gate is ready, otherwise returns local safe rule replies. The
sprite can be dragged around the viewport, persists its local position, adapts
its panel to left/right and top/bottom docking, and now has a recognizable
micro-assistant body/visor/side-fin/antenna silhouette instead of a generic
floating button. It does not execute actions, expose local paths, return
provider raw responses, bypass project-owner auth scope, or write durable
memory. A deterministic internal beta acceptance runner now covers auth scope,
project isolation, image assets, draft-vs-fixed asset lifecycle, context reuse,
feedback evidence, artifact scope, and video gate-closed behavior without
opening providers; it is split across small tool modules to avoid new oversized
maintenance debt. Verification: focused Studio/Runtime regression 26 passed / 1
warning; internal beta acceptance runner reports
`contract_verified_pending_human_acceptance`; full pytest 517 passed / 527
deselected / 2 warnings; `npm run
check:studio-js` passed for 87 files; CLI help/version passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed with Windows CRLF
notice only. In-app browser automation was blocked by Browser URL policy for
the local Studio URL in this pass, so movable-avatar visual acceptance is not
claimed. Remaining non-blocking warnings are existing maintenance-audit
warnings for legacy frozen surfaces, Chinese-doc coverage, secret-like
test/config fragments, and oversized files.

Current deep hardening addendum: 2026-06-19 pass completed and was merged to
`master` through `fda2dcafb3a5609deddc9e4ad664b6be060cb053`, then aligned
across GitHub, server `/home`, and server `/opt`. The work strengthened
internal beta usability, homepage product framing, Studio operation feel, and
frontend structure while preserving provider gates. Implemented: `/health`
runtime-root persistence is a safe boolean projection; cross-user auth tests now
cover Studio state, image assets, image previews, jobs, and artifact manifests;
homepage first viewport is more directly positioned as a professional AI video
creation entry; inspector defaults to next action and current reference summary
with details folded; edge anchors use visible port centers; selected edge flow
is lighter/slower; port magnet vertical range is tighter; generating text
shimmer is slower; `main.js` project lifecycle logic moved into
`studio-project-controller.js`; `npm run check:studio-js` added. Verification:
Studio/Site JS syntax check passed for 86 files; focused Runtime/Studio
regression passed 69 / 1 warning; Runtime CLI now maps `AFS_RUNTIME_ROOT` into
`--runtime-root`; full pytest passed 508 / 527 deselected / 2 warnings; CLI
help/version passed with version 0.1.0 and runtime-service help shows
`AFS_RUNTIME_ROOT`; maintenance audit failed=0 with warnings only; `git diff
--check` passed. Boundary: no video gate opened, no new provider introduced, no
provider raw/signed URL/secret/media byte persistence, no human acceptance or
business validation claimed. Maintenance ledger:
`docs/maintenance/AFS-DEEP-UX-RUNTIME-HARDENING-20260619.md`. Closeout:
`docs/handoff/AFS-DEEP-UX-RUNTIME-HARDENING-CLOSEOUT-20260619.md`.

Current frontend hardening addendum: 2026-06-19 pass continued Studio UX
hardening after edge and homepage review. Root `/` now leads with the AI video
creation entry and keeps the six core algorithms behind a folded technical
boundary instead of a primary section. `/studio/` now separates asset lifecycle
states in the asset drawer, redraws on asset search/filter state changes, and
shows right-inspector summaries for included context, excluded context, and
asset confirmation state; object-shaped context warnings are rendered through
safe summary fields rather than raw objects. Canvas edges are thinner by default
and selected-node related edges now render a directional spark overlay: upstream
selection flows forward, downstream selection reverses; the selected-edge spark
was slowed and generating/optimizing/running text now has a subtle shimmer with
reduced-motion fallback. Verification so far:
browser QA on
`127.0.0.1:8797` confirmed homepage entry/no horizontal overflow/no console
warn-error, selected edge forward/reverse spark, `1.35px` default edge width,
`1.75px` associated edge width, lifecycle filter redraw, and inspector context
copy. Current-scope maintainability risks from this pass were closed by
splitting edge SVG styles into `canvas-edges.css` and splitting the broad Studio
static regression file into focused asset/generation and mature-shell test
files; focused Studio/Site static and interaction regression 46 passed;
post-split focused Studio static and edge regression 33 passed; changed
Studio/Site JS `node --check` passed; generating-feedback and mature-shell
regression 20 passed; browser style verification confirmed
`generation-feedback.css` loaded, selected-edge spark duration 2.6s,
generating-text shimmer duration 3.2s, and console warn/error count=0; full
default pytest passed 493 / 527 deselected / 2 warnings; maintenance audit
failed=0 with warnings only; `git diff --check` passed with the existing CRLF
notice on `apps/studio/styles/assets.css`. Boundary: no provider call, no
generated media bytes, no human acceptance, no business validation, no
durable-memory promotion.

Current frontend closeout addendum: 2026-06-19 pass fixed Studio port geometry
and homepage entry. Root `/` now serves the new professional AI video creation
homepage; `/studio/` inspector is reduced to next action, current reference
summary, drawer links, and collapsed trace/details. Pending drag lines originate
from visible plus ports, persisted connection paths anchor to node frame
boundaries with port-aligned vertical placement, default stable edges are solid
round-capped lines, left/right magnet states are distinct, and vertical magnet
range is bounded. Verification: browser QA on `127.0.0.1:8797` confirmed
homepage/cards/no horizontal overflow, inspector declutter, frame-attached edge
alignment, drag-follow with edge opacity=1, left/right magnet behavior, far-y
magnet clearing, and zero console warn/error; focused frontend/runtime tests 46
passed; Studio/Site JS `node --check` passed for 82 files; full `pytest -q` 491
passed / 527 deselected / 2 warnings; CLI help/version passed; maintenance audit
failed=0 with warnings only; `git diff --check` passed with the existing CRLF
notice. Boundary: no provider call, no human acceptance, no business validation,
no durable-memory promotion.

Current closeout note: Loop 005 baseline is green after moving local input
Markdown files out of the repository root and generalizing retention review for
root-level untracked Markdown inputs. Studio pages opened on local static/dev
ports now fall back to Runtime Service `http://127.0.0.1:8790`, fixing the
`Failed to fetch` path seen on stale `8796/studio` sessions. Verification:
`pytest -q` 386 passed / 527 deselected; `pytest -m legacy -q` 527 passed / 386
deselected; Studio JS `node --check` 37 files passed; maintenance audit
failed=0; `git diff --check` exit 0.

Current browser acceptance addendum: The 2026-06-15 Browser drill used an
isolated branch and external evidence root, opened only LLM/image/video gates,
and kept ASR plus external download closed. Browser/runtime coverage passed
project persistence, T2I, fixed assets, Kling I2V, safe preview, and responsive
checks. The initial Path 3 gap was closed after explicit user approval for one
additional MiniMax image call: the Browser rerun completed true reference-backed
I2I with `reference_image_count=1`, `candidate_count=1`, and no provider
raw/media-byte persistence in the safe manifest. The drill is now AI/browser
pre-acceptance `recommended`, pending the user's human acceptance and creative
quality scoring.

Final verification passed on the browser-drill branch: default pytest 406
passed / 527 deselected; legacy pytest 527 passed / 406 deselected; Studio JS
`node --check` 37 files passed; maintenance audit failed=0 with warnings only;
`git diff --check` exit 0.

Continuation verification after the authorized Path 3 rerun: focused readiness
and reference-asset tests 11 passed / 1 warning; readiness audit reports
`recommended`, provider_blocker_count=0, passed_role_count=7; maintenance audit
failed=0 with warnings only; `git diff --check` exit 0.

## Current Work

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-STUDIO-VISUAL-ASSET-PANEL-SPLIT-20260619 | Studio Interaction Designer + Frontend Maintainability Steward + QA Gatekeeper | Split visual asset confirmation rendering out of the asset review workflow so the panel stays under the 300-line threshold while preserving draft-card, fixed/rejected review, and safe store projection behavior. | Local verification completed. Focused Studio static tests passed; Studio JS syntax check passed; browser load check passed with no console warn/error; full pytest passed; maintenance audit failed=0 and oversized warning count dropped from 33 to 32. Boundary: no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation. | `apps/studio/src/panels/visual-asset-panel.js`, `apps/studio/src/panels/visual-asset-panel-render.js`, `tests/test_web_studio_assets_generation_static.py`, `tests/test_web_studio_loop003_static.py`, `DEVLOG.md` |
| AFS-STUDIO-SPRITE-MOVABLE-POLISH-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Polish the decorative `AFS 小精灵` so it is visibly draggable, keeps a designed companion silhouette, avoids inspector/dock default overlap, and remains on the existing safe Runtime chat boundary. | Local verification completed. Focused sprite static test passed; Studio static + sprite regression passed; Studio JS syntax check passed; full pytest passed; maintenance audit failed=0. Browser check on `127.0.0.1:8797/studio/` confirmed default inspector/dock avoidance and drag movement from `(768,414)` to `(598,315)`. Boundary: no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation. | `apps/studio/src/sprite-widget.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite-avatar-personality.css`, `tests/test_web_studio_sprite_static.py`, `DEVLOG.md` |
| AFS-COS-GFR-DISPLAY-PACKAGE-V01-20260619 | AI-Native Operating Architect + Product Narrative Editor + QA Gatekeeper + Rule Steward | Source-KB display-package slice: freeze current COS/GFR TaskRun flow map as versioned bilingual SVG/PNG/PDF, rewrite one-page and mechanism HTML toward a restrained evidence-bound narrative, and add a concrete TaskRun example. | Structure/render verification completed. Source JSON parse passed; versioned SVG XML parse passed at 2600x2860; HTML local href/src check passed; Playwright desktop/mobile render check passed with no horizontal overflow, no broken images, and no console warn/error; Company OS contract validator passed; GFR audit passed with checked_paths=41, checked_packets=5, errors=0, warnings=0. Boundary: no Runtime API or Studio code changed in this slice, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | Source KB: `03-one-page-html.html`, `08-cos-gfr-deep-dive.html`, `assets/cos-gfr-taskrun-flow-map.v0.1.*`, `taskrun-examples/2026-06-19-cos-gfr-display-package-v0.1.*`, `TASKRUN-LEDGER-V0.json`; AFS repo: `DEVLOG.md`, `TASK_TRACKER.md` |
| AFS-STUDIO-INTERACTION-DETAIL-FIXES-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Focused follow-up for `/studio/` operation feel: prevent dragged-node edge visual detachment, add side-port magnetic plus feedback, compact the add-node menu, clamp expanded popovers inside the viewport, and bound generated media previews. | Local implementation completed on `master`. Focused interaction tests passed: 7 passed. Studio static + interaction regression passed: 37 passed. Studio JS syntax check passed for 76 files. Browser QA on `127.0.0.1:8797/studio/?project=frontend-fix-overlap-browser` passed right-side port magnet, default compact add menu, expanded scroll-safe menu bounds, drag cleanup with preserved edge count, prompt-bar non-overlap, and console warn/error count=0. Full default pytest passed: 487 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only. `git diff --check` exit 0 with Windows CRLF notice on `apps/studio/src/overlay.js` only. Boundary: no Runtime API change, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/interaction/port-magnet.js`, `apps/studio/src/interaction/feedback-layer.js`, `apps/studio/src/canvas-input.js`, `apps/studio/src/overlay.js`, `apps/studio/src/panels/add-node-menu.js`, `apps/studio/styles/interaction-motion.css`, `apps/studio/styles/studio-interactions.css`, `apps/studio/styles/node-result.css`, `tests/test_studio_interaction_layer.py`, `DEVLOG.md` |
| AFS-STUDIO-INTERACTION-LAYER-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | First operation-feel slice for `/studio/`: modular interaction layer, drag lift/landing feedback, visible grid/alignment snap guides, edge-follow nudging, bounded inertial pan, and connection-source feedback while keeping Runtime/provider boundaries unchanged. | Local implementation completed on `master`. New interaction tests passed: 4 passed. Studio static + interaction regression passed: 34 passed. Studio JS syntax check passed for 75 files. Browser QA on `127.0.0.1:8797/studio/` passed node drag feedback creation, align snap state, landing feedback, feedback-layer auto-clear, and console warn/error count=0. Full default pytest passed: 484 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only. Boundary: no Runtime API change, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/interaction/motion-tokens.js`, `apps/studio/src/interaction/pointer-kinematics.js`, `apps/studio/src/interaction/auto-pan.js`, `apps/studio/src/interaction/snap-engine.js`, `apps/studio/src/interaction/feedback-layer.js`, `apps/studio/src/canvas-input.js`, `apps/studio/src/canvas-connection.js`, `apps/studio/styles/interaction-motion.css`, `apps/studio/index.html`, `tests/test_studio_interaction_layer.py`, `DEVLOG.md` |
| AFS-COS-GFR-LOOP-ENGINEERING-V0-20260619 | AI-Native Operating Architect + Rule Steward + QA Gatekeeper | Source-KB loop-engineering slice: LoopSpec v0 schema, TaskRun Ledger v0 schema/object, GFR templates updated to require loop planning, and bilingual SVG distribution diagram for the learning Agent production control system. | Structure verification completed. Company OS contract validator passed including `loop_spec_v0` and `taskrun_ledger_v0`; GFR audit passed with checked_paths=41, checked_packets=5, errors=0, warnings=0; source JSON parse passed; bilingual SVG UTF-8 XML parse passed at 2400x1500; Chrome render check completed with final screenshots reviewed; full default pytest passed 484 / 527 deselected / 2 warnings; maintenance audit failed=0 with warnings only; `git diff --check` passed. Boundary: candidate loop-control structure and distribution asset only; not runtime COS enforcement, provider smoke, human acceptance, business validation, or durable memory promotion. | Source KB: `loop_spec_v0.schema.json`, `taskrun_ledger_v0.schema.json`, `TASKRUN-LEDGER-V0.json`, `2026-06-19-cos-gfr-loop-engineering-v0.*`, `cos-learning-agent-production-loop.zh-CN.svg`, `cos-learning-agent-production-loop.en.svg`; AFS repo: `docs/GFR_EXECUTION_PROJECTION.md`, `DEVLOG.md`, `TASK_TRACKER.md` |
| AFS-INTERNAL-BETA-ENTRY-CONFLICT-GUARD-20260618 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Security Boundary Steward | Next internal-test hardening slice: session TTL for invite-gated accounts, optimistic `studio-state` version conflict guard, homepage auth-aware Studio entry, and focused browser QA with provider gates explicitly closed. | Local implementation completed on `codex/cos-gfr-v0-control-layer-20260618`. Focused auth/state/site/studio/OpenAPI regression passed: 63 passed / 1 warning. Changed Studio/site JS syntax checks passed. Browser QA on `127.0.0.1:8810` passed anonymous homepage auth entry, invite registration, account-scoped default project creation/save, authenticated homepage entry, homepage-to-Studio navigation, and console warn/error count=0. Full default pytest passed: 480 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only; `git diff --check` passed with Windows CRLF notice only. Boundary: no provider gate opened, no provider call, no local secret provider config edited, no human acceptance, no business validation, no durable memory promotion. | `apps/api/runtime_auth.py`, `apps/api/runtime_studio_state.py`, `apps/api/runtime_service.py`, `apps/site/index.html`, `apps/site/site.js`, `apps/site/styles/site.css`, `apps/studio/src/runtime-client.js`, `apps/studio/src/store.js`, `apps/studio/src/main.js`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_auth.py`, `tests/test_api_runtime_studio_state.py`, `tests/test_api_runtime_studio_state_persistence.py`, `tests/test_site_homepage_static.py`, `tests/test_web_studio_static.py`, `.env.example`, `DEVLOG.md` |
| AFS-COS-GFR-V0-CONTROL-LAYER-20260618 | AI-Native Operating Architect + Engineering Delivery Lead + Rule Steward + QA Gatekeeper | First COS/GFR operationalization slice: source-KB COS Registry v0, GFR Packet v0 schema and real task packet, Evidence Ledger v0, candidate feedback packet, plus AFS Runtime safe `GET /company-os/gfr-projection` endpoint and tests. | Local implementation completed on `codex/cos-gfr-v0-control-layer-20260618`. Company OS contract validator passed for new registry/packet/ledger fixtures; GFR audit passed with checked_paths=41, checked_packets=4, errors=0, warnings=0. Focused Runtime tests passed: 13 passed / 1 warning; post-OpenAPI focused Runtime/OpenAPI tests passed: 17 passed / 2 warnings. Full default pytest passed: 476 passed / 527 deselected / 2 warnings. CLI help/version and `git diff --check` passed. Boundary: candidate control-layer slice only, not full COS runtime enforcement, provider smoke, human acceptance, business validation, or durable memory promotion. | Source KB: `COS-REGISTRY-V0.json`, `EVIDENCE-LEDGER-V0.json`, `gfr_packet_v0.schema.json`, `2026-06-18-cos-gfr-v0-control-layer.*`, `2026-06-18-cos-gfr-v0-control-layer.md`; AFS repo: `apps/api/runtime_company_os.py`, `apps/api/runtime_service.py`, `apps/api/runtime_info.py`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_company_os.py`, `tests/test_api_runtime_service.py`, `docs/GFR_EXECUTION_PROJECTION.md`, `DEVLOG.md` |
| AFS-INTERNAL-AUTH-INVITE-ISOLATION-20260618 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Security Boundary Steward | Add first internal-test account gate: invite-code registration, login sessions, user-owned project filtering, Studio auth gate, account-scoped default project creation, explicit Studio-to-homepage navigation, and non-dismissible auth gate when auth is required. | Local implementation completed on `master`. Auth-focused pytest passed: 3 passed / 1 warning. Focused Runtime/Auth/Studio/Site regression passed: 54 passed / 1 warning. Auth gate/site focused regression after backdrop-lock fix passed: 7 passed / 1 warning. Full default pytest passed: 474 passed / 527 deselected / 2 warnings. CLI help/version, Studio JS syntax check for 70 files, maintenance audit failed=0 with warnings only, and `git diff --check` passed. Runtime HTTP auth smoke on `127.0.0.1:8802` passed for homepage, Studio static, health auth projection, anonymous project rejection, invite registration, project creation, and owned project list. Boundary: internal-test auth only, not full SaaS accounts/roles/sharing; no provider gate opened, no provider call, no human acceptance, no business validation. | `apps/api/runtime_auth.py`, `apps/api/runtime_service.py`, `apps/api/runtime_info.py`, `apps/studio/src/auth-gate.js`, `apps/studio/src/runtime-client.js`, `apps/studio/src/main.js`, `apps/studio/src/studio-topbar.js`, `apps/studio/src/overlay.js`, `apps/studio/styles/modals.css`, `tests/test_api_runtime_auth.py`, `tests/test_web_studio_static.py`, `.env.example`, `DEVLOG.md` |
| AFS-SITE-STUDIO-UX-CONSOLIDATION-20260618 | Frontend Product Designer + Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Consolidate the next-step UX after the site/studio audit: fix homepage product-preview overlap, make the homepage preview a bounded creation-chain layout, and reframe the Studio empty inspector around user creation decisions while keeping algorithm trace available as a folded safe audit surface. | Local implementation completed on `master`. Focused Runtime/site/Studio static regression passed: 42 passed / 1 warning. Full default pytest passed: 470 passed / 527 deselected / 2 warnings. Studio JS syntax check, Runtime HTTP smoke on `127.0.0.1:8801` for `/`, `/studio/`, `/health`, in-app Browser QA, maintenance audit failed=0, and `git diff --check` passed. Boundary: no provider gate opened, no provider call, no local secret provider config edited, no human acceptance, no business validation. | `apps/site/index.html`, `apps/site/styles/site.css`, `apps/site/styles/site-preview.css`, `apps/site/styles/site-responsive.css`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/panels/algorithm-context-panel.js`, `tests/test_site_homepage_static.py`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-MODEL-ROUTE-SURFACE-20260618 | Runtime/API Integrator + Studio Product Surface Owner + Provider Gate Steward + QA Gatekeeper | Consolidate current model-route surface: Image/keyframe product path uses Image2 via `codex_image`; prompt optimization uses server-configured `prompt_optimizer` without exposing model identity; visual understanding is split into `vision_image` and `vision_video`; example provider config reflects only current execution projection. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Focused model route/runtime/static regression passed: 100 passed / 1 warning. Full default pytest passed: 469 passed / 527 deselected / 2 warnings. Studio JS syntax check, provider example JSON parse, maintenance audit failed=0, and `git diff --check` passed. Boundary: no provider gate opened, no live provider call, no local secret provider config edited, no human acceptance, no business validation. | `apps/studio/src/presets/models.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/panels/visual-asset-panel.js`, `apps/studio/src/main.js`, `apps/api/runtime_models.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_creative_agent.py`, `configs/providers.example.json`, `tests/test_web_studio_static.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_provider_adapter_registry.py`, `DEVLOG.md` |
| AFS-SITE-HOMEPAGE-ROOT-20260618 | Frontend Product Designer + Runtime/API Integrator + QA Gatekeeper | Add a real website homepage at Runtime root `/` while keeping `/studio/` as the creative workspace. Homepage introduces AFS Studio, the product preview, workflow, six core algorithms, and direct Studio entry without exposing internal provider/runtime details. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Focused Runtime/static regression passed: `tests/test_api_runtime_service.py`, `tests/test_site_homepage_static.py`, and `tests/test_web_studio_static.py` report 41 passed / 1 warning. Boundary: no provider gate opened, no provider call, no human acceptance, no business validation. | `apps/site/index.html`, `apps/site/styles/site.css`, `apps/site/styles/site-preview.css`, `apps/site/styles/site-responsive.css`, `apps/api/runtime_studio_static.py`, `apps/api/runtime_service.py`, `tests/test_api_runtime_service.py`, `tests/test_site_homepage_static.py`, `DEVLOG.md` |
| AFS-STUDIO-DECLUTTER-FOLLOWUP-20260618 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Frontend-only declutter after design review: shrink the top-left workbench into a compact project menu, return creative entry to the canvas starter rail, collapse six-core-algorithm details behind a system-process disclosure, and reduce right-inspector card density. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Static Studio regression passed, changed Studio JS syntax checks passed, `git diff --check` passed, and touched/new frontend files remain below the 300-line maintenance warning threshold. In-app browser automation for the local `/studio/` URL was blocked by Browser URL policy in this pass, so this is not a fresh visual/human acceptance claim. Boundary: no Runtime API contract change, no provider call, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/project-hub.js`, `apps/studio/src/studio-topbar.js`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/panels/algorithm-context-panel.js`, `apps/studio/styles/studio-workbench.css`, `apps/studio/styles/studio-mature-shell.css`, `apps/studio/styles/studio-inspector-declutter.css`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-STUDIO-MATURE-SHELL-20260618 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Frontend-only desktop polish for `/studio/`: mature workbench shell, quick-start workflow rail, right-side six-algorithm production console, and follow-up fixes for inspector overlap plus workbench modal vertical scrolling. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Studio static tests passed, all Studio JS files passed `node --check`, `git diff --check` passed, and in-app browser verification on `127.0.0.1:8797/studio/` confirmed starter-flow inspector sections had zero detected overlaps, the workbench modal accepted real wheel scroll to lower content, and console error/warning count was 0. Boundary: no Runtime API contract change, no provider call, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/panels/algorithm-context-panel.js`, `apps/studio/src/canvas-starter-rail.js`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/canvas-view.js`, `apps/studio/styles/studio-mature-shell.css`, `apps/studio/styles/studio-workbench.css`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-MODEL-CALL-CONTEXT-CONTRACT-20260618 | Engineering Delivery Lead + Runtime/API Integrator + Rule Steward + QA Gatekeeper | First algorithm-contract slice for the six-core-algorithm plan: define `ModelCallContext`, separate core/auxiliary algorithm taxonomy, add request projection and visual-understanding normalization, and wire prompt/keyframe, video generation, visual inspect / asset-card draft, and video revision Runtime artifacts to the same context id discipline. | Local implementation completed on `codex/afs-model-call-context-contract`. Prompt, image/keyframe, video, visual inspect, and revision entrypoints now emit safe algorithm artifacts without opening providers. Full default pytest passed: `464 passed, 527 deselected, 2 warnings`; maintenance audit failed=0 with warnings only; `git diff --check` passed with CRLF notices only; final closeout HTTP smoke passed on `127.0.0.1:8797` with `/health` ready, `/studio/` 200, and runtime client 200. Boundary: no live provider smoke, no human acceptance, no business validation, no durable memory promotion. | `agentflow/algorithms/model_call_context/`, `agentflow/algorithms/request_projection/`, `agentflow/algorithms/visual_understanding/`, `agentflow/algorithms/revision_drift_control/`, `apps/api/runtime_model_call_context.py`, `apps/api/runtime_video_routes.py`, `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_video_revision_context.py`, `apps/api/runtime_video_revision_routes.py`, `tests/test_model_call_context_contract.py`, `tests/test_model_call_context_runtime_routes.py`, `docs/architecture/AFS_MODEL_CALL_CONTEXT_CONTRACT.zh-CN.md`, `docs/architecture/AFS_ALGORITHM_LIBRARY.zh-CN.md`, `docs/architecture/AFS_CORE_ALGORITHM_AND_OPERATION_MAP.zh-CN.md`, `docs/handoff/AFS-MODEL-CALL-CONTEXT-CONTRACT-20260618.md` |
| AFS-ALGORITHM-CORE-WAVE2-20260617 | Engineering Delivery Lead + Runtime/API Integrator + QA Gatekeeper | Second algorithm-library migration after provider-flow intake: move i2v/t2v creative-intent logic, video-safe provider prompt projection, reference-asset merge rules, and Studio video first-frame/auto-poll helper logic out of oversized Runtime/Studio files. | Local Wave 2 migration completed with focused and wider Runtime/Studio tests passing. Maintenance audit remains failed=0 with existing warning classes; oversized files remain a tracked maintenance debt, but `node-actions.js` is reduced and new video helper is single-purpose. Boundary: no live provider smoke, no human acceptance, no business validation, no durable memory promotion. | `agentflow/algorithms/creative_intent_control/video_prompt.py`, `agentflow/algorithms/provider_gate_manifest/video_prompt.py`, `agentflow/algorithms/context_resolver/references.py`, `apps/studio/src/video-node-flow.js`, `tests/test_algorithm_library_contracts.py`, `docs/handoff/AFS-ALGORITHM-CORE-WAVE2-20260617.md` |
| AFS-PROVIDER-FLOW-INTAKE-20260617 | Engineering Delivery Lead + Runtime/API Integrator + QA Gatekeeper + Provider Gate Steward | Integrate server-side PR #87 video provider-flow fixes after the GFR baseline: keep reference assets attached, use i2v/t2v prompt semantics, project video-safe Kling prompts, infer upstream keyframes as first frames, auto-poll video jobs, and refresh no-cost readiness. | Local integration completed without conflicts on the Wave 1 branch. Focused Studio JS and Runtime tests passed; no live provider call was started locally. Readiness report is `ready_for_provider_smoke`, but still requires explicit human authorization before spending provider calls. Boundary: server-side Kling smoke is provider-smoke evidence only, not human acceptance or business validation. | `apps/api/runtime_keyframes.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_video_routes.py`, `apps/studio/src/node-actions.js`, `apps/studio/src/node-result-view.js`, `apps/studio/src/optimizer-contract.js`, `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-20260617.md`, `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-READINESS-20260617.json` |
| AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617 | QA Gatekeeper + Provider Gate Steward + Engineering Delivery Lead | No-cost readiness gate before the first post-algorithm provider-connected validation: check GFR packet, Runtime action surface, provider config source, gate projection, and next required human authorization. | Ready for human authorization. Tool reports `ready_for_provider_smoke` with LLM/image gates currently projected open and video/vision closed, but also reports `human_approval_required=true` and `current_session_approval_inferred_from_env=false`; no provider call was started. Focused readiness tests and full default pytest now pass. Boundary: live smoke still requires explicit user approval for exact capability and candidate count. | `tools/afs_provider_connected_validation_readiness.py`, `tests/test_afs_provider_connected_validation_readiness.py`, `docs/handoff/AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617.md` |
| AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617 | Engineering Delivery Lead + Rule Steward + Runtime/API Integrator | First executable algorithm-library slice: asset-card drafts, fixed-asset context boundary, provider safe manifest, independent vision gate, video asset promotion, and external feedback boundary. | Required local smoke passed for visual assets, provider registry, Studio static, context resolver, video revisions, creative keyframes, prompt loop, algorithm contracts, asset-card drafts, Runtime service, changed Studio JS, OpenAPI export, CLI help/version, maintenance audit, and diff check. Boundary: no real provider smoke, no human acceptance, no business validation, no automatic COS rule promotion. | `agentflow/algorithms/`, `apps/api/runtime_asset_card_drafts.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_fake_vision.py`, `tests/test_algorithm_library_contracts.py`, `tests/test_api_runtime_asset_card_drafts.py`, `docs/architecture/AFS_ALGORITHM_LIBRARY.zh-CN.md`, `docs/openapi/afs-runtime-service.openapi.json`, `docs/handoff/AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617.md`, `docs/maintenance/AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617.md` |
| AFS-CODEX-IMAGE-HANDOFF-WORKER-20260617 | Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer + QA Gatekeeper | Add automated async image provider path: Runtime keyframe submit writes safe job package, background worker consumes it, Runtime poll returns safe preview/reusable image asset, and Studio auto-polls without exposing internal worker/provider jargon. | Implemented with fake executor contract verification and `codex exec` executor shell. Focused provider/runtime/static tests passed. Boundary: fake executor proves file contract only; server `codex exec` real image smoke remains required before human test. | `agentflow_studio/model_gateway/codex_image_handoff.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `agentflow_studio/model_gateway/provider_codex_handoff.py`, `tools/codex_image_worker.py`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_keyframe_async.py`, `apps/api/runtime_keyframe_routes.py`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `tests/test_codex_image_handoff.py`, `docs/handoff/AFS-CODEX-IMAGE-HANDOFF-WORKER-20260617.md` |
| AFS-FULL-CHAIN-LOCALIZED-QA-20260615 | QA Gatekeeper + Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer | Full-chain browser/runtime/live-provider QA focused on end-to-end flow and localized image/video adjustment through the current prompt/asset/context/runtime architecture. | Safe summary merged into mainline from the isolated QA branch. Deterministic full suite passed before live calls; MiniMax T2I, MiniMax reference-backed I2I, and Kling I2V completed in that run. Localized image quality failed in the first paid sample, then a deterministic prompt-ordering fix was added; paid retest remains pending. Video localized editing remains experimental and not productized. | `docs/handoff/AFS-FULL-CHAIN-LOCALIZED-QA-20260615.md`, external evidence root `20260615-afs-full-chain-localized-qa`, `apps/api/runtime_context_text.py`, `tests/test_runtime_context_text.py` |
| AFS-MVP-EXPERIENCE-HARDENING-20260615 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Provider Gate Steward | Harden internal-test readiness after latest Studio feedback: Runtime health self-check, safe internal launcher, node-level asset carry visibility, shared asset-reference inspector, explicit video local-cancel boundary, server-sanitized structured quality feedback capture, and explicit external-download closure. | Focused tests passed; Runtime `/health` smoke ready with Studio static ready and all provider gates closed. Claude closeout review approved with no must-fix blockers after follow-up hardening. In-app Browser localhost smoke was blocked by Browser URL policy and recorded as blocked evidence; no alternate browser was used to bypass policy. Boundary: no live provider calls, no ASR/external download, no human acceptance, and no claim that video localized editing is productized. | `docs/handoff/AFS-MVP-EXPERIENCE-HARDENING-20260615.md`, external evidence root `20260615-afs-mvp-experience-hardening`, `tools/run_studio_internal_test.ps1`, `apps/api/runtime_info.py`, `apps/studio/src/asset-reference-summary.js`, `apps/studio/src/asset-reference-inspector.js`, `apps/studio/src/quality-feedback.js`, `tests/test_api_runtime_service.py`, `tests/test_web_studio_static.py`, `tests/test_studio_internal_launcher.py` |
| AFS-VIDEO-LOCALIZED-REGEN-001 | Product Framing + Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Define the next video MVP requirement: accepted video as a base clip, prompt-driven targeted revision, explicit preserve/change controls, temporal scope, and A/B drift scoring. | Experimental contract/UI skeleton implemented. Runtime now has `VideoRevisionRequest`, `/video-revisions/preflight`, `/video-revisions`, safe manifest, feature flag, base lineage, and best-effort preserve/change taxonomy. Studio has revision draft entrypoint and fail-closed unconnected fixed-asset submit guard. Boundary: no provider video-revision submit yet; current Kling path is still I2V, not guaranteed localized editing. | `apps/api/runtime_video_revision_routes.py`, `tests/test_api_runtime_video_revisions.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-VIDEO-LOCALIZED-REGEN-20260615.md`, `BACKLOG.md` |
| AFS-BROWSER-ACCEPTANCE-DRILL-20260615 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer + Provider Gate Steward + Frontend UI Reviewer | Browser-led near-human acceptance drill on Runtime-hosted `/studio/`: Runbook paths 1-6, seven role lenses, micro full-chain provider smoke, responsive UI screenshots, safety scan, and readiness audit compatibility for browser-drill evidence. | AI/browser pre-acceptance `recommended`, not human acceptance. Paths 1-6 passed; Path 5 passed by auxiliary browser QA; Path 3 was closed by an explicitly authorized MiniMax reference-backed I2I rerun with `reference_image_count=1`. LLM optimize smoke passed, MiniMax T2I and reference-backed I2I succeeded, Kling I2V submit/poll/preview/reload passed with one submit, seven role checks passed, and provider blockers are zero in the readiness audit. Remaining action is user-run human acceptance plus creative quality scoring; I2I optimizer explicit-edit preservation is a non-blocking follow-up before relying on optimized I2I text. | `docs/handoff/AFS-BROWSER-ACCEPTANCE-DRILL-20260615.md`, external evidence root `20260615-afs-browser-acceptance-drill`, `tools/afs_mvp_joint_qa_readiness_audit.py`, `tests/test_afs_mvp_joint_qa_readiness_audit.py` |
| AFS-MVP-JOINT-QA-CLOSEOUT-20260614 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer + Frontend UI Reviewer + Provider Gate Steward | Codex + Claude joint closeout lane: gate-closed verification, LLM/MiniMax/Kling provider smoke attempt, seven-role AI pre-acceptance, frontend UI audit, P0/P1 repair loop, and safe evidence handoff. | AI recommended / pending human acceptance. Stale Runtime preflight 404 now reports a restart-specific Studio error; image and video gates were opened on Runtime 8790 per user direction while ASR stayed closed. MiniMax image live smoke succeeded with `candidate_count=1`; Kling I2V preflight, submit, poll, preview, and offline inspection succeeded with `candidate_count=1`; MiniMax B-only live retry succeeded and cleared `P1-IMAGE-B-PROVIDER-READINESS`. Final readiness audit reports `recommended`, seven role checks passed, zero provider blockers, and `human_acceptance_claim=not_claimed`. Final verification passed: default pytest 404 passed / 527 deselected; legacy pytest 527 passed / 404 deselected; Studio JS 37 files passed; maintenance audit failed=0; `git diff --check` exit 0. One post-fix asset-context browser QA rerun with explicit live LLM reached the first optimize and then hit an upstream SSL EOF on second re-optimize; no image/video provider call was started by that QA path and it was not retried further. This is not human acceptance or business validation. | `docs/handoff/AFS-MVP-JOINT-QA-CLOSEOUT-20260614.md`, external evidence root `20260614-afs-mvp-joint-qa`, `tools/afs_mvp_joint_qa_readiness_audit.py`, `tests/test_afs_mvp_joint_qa_readiness_audit.py`, `tools/minimax_image_provider_preflight.py`, `tests/test_minimax_image_provider_preflight_tool.py`, `tools/kling_provider_preflight.py`, `tools/studio_asset_context_live_comparison.py`, `tests/test_kling_provider_preflight_tool.py`, `tests/test_api_runtime_generation_comparison.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `tests/test_kling_video_task_recovery.py`, `tools/studio_asset_context_browser_qa.py`, `tests/test_studio_asset_context_browser_qa_tool.py`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `tests/test_web_studio_static.py` |
| AFS-BROWSER-REPAIR-LOOP-005 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer | Continue the north-star browser takeover loop toward human-acceptance readiness: Loop 003 red baseline, known-issue regressions, generation manifest leak assertions, live provider/browser role-matrix rounds, and current human acceptance runbook. | Runtime/browser verification closed for tested MVP paths. Round A fixed live LLM formatting 422, legacy provider gate drift, duplicate excluded-asset trace rows, and a P0 Kling task-state path leak. Round B fixed tiny reference media reaching paid providers. Round C fixed Studio image-model selection masking LLM provider fields. Round D and Round E were consecutive clean role-matrix rounds with remote LLM optimize, T2I, upload/I2I, fixed asset detail, fixed carry, one-run exclusion, Kling I2V, and Studio load; no new P0/P1. Remaining boundary: user must run human acceptance runbook and score MiniMax/Kling creative quality. | `docs/maintenance/AFS-AGENT-BROWSER-QA-LOOP-003.md`, `docs/maintenance/AFS-BROWSER-QA-LOOP-005-GAP-AUDIT.md`, `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md`, `tests/test_web_studio_static.py`, `tests/test_api_runtime_generation_manifest_safety.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_video_generations.py`, `tests/test_api_runtime_keyframe_reference_assets.py`, `runs/agent_browser_qa_loop_005/` |
| AFS-BROWSER-REPAIR-LOOP-004 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper | Request-level fixed asset exclusion, keyframe/video preflight consistency, Runtime-backed asset detail, Studio carry confirmation, one-run exclusion UX, and agent-led browser QA evidence/runbook. | Track A Runtime contract merged; Track B browser loop verified carry confirmation, one-run exclusion reset, cancel persistence, asset detail popover, and Kling no-sound spec UI. Focused Runtime tests 27 passed; Studio static 14 passed; changed JS `node --check` passed. Remaining boundary: human acceptance must be executed by user with the runbook; image/video creative quality still requires human scoring. | `apps/api/runtime_generation_preflight.py`, `apps/api/runtime_context_resolver.py`, `apps/api/runtime_keyframe_routes.py`, `apps/api/runtime_video_routes.py`, `apps/studio/src/node-actions.js`, `apps/studio/src/panels/asset-detail-popover.js`, `docs/maintenance/AFS-BROWSER-QA-LOOP-004.md`, `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-004.md`, `runs/agent_browser_qa_loop_004/` |
| AFS-LEGACY-FREEZE-20260613 | Maintenance Steward + QA Gatekeeper + Provider Gate Steward | Freeze Production Memory and distribution-chain legacy tests behind `pytest -m legacy`, normalize repo line-ending policy, retire stale v0.2 handoff and old `NARRATOCUT_ALLOW_REMOTE_*` gate compatibility, and keep current Runtime/Studio gate as default. | `legacy-frozen-20260613` tag pushed; default pytest 363 passed / 527 deselected; legacy pytest 527 passed / 363 deselected; focused provider/schema/runtime/static tests 66 passed; maintenance audit failed=0 with legacy-frozen warning segment; no provider gates opened. | `.gitattributes`, `pyproject.toml`, `tests/conftest.py`, `tools/maintenance_audit.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `docs/maintenance/AFS-LEGACY-FREEZE-20260613.md` |
| AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-001 | Runtime/API Integrator + Maintenance Steward + QA Gatekeeper | Remove Production Memory HTTP routes from Runtime Service, align default OpenAPI with legacy v02 gate closed, harden current-route error projection, and keep production-memory CLI/harness as non-HTTP compatibility. | Focused Runtime contract set 31 passed; default OpenAPI export regenerated and parsed without retired routes or v02 paths; maintenance audit failed=0; CLI help/version passed; full pytest 886 passed; `git diff --check` exit 0 with CRLF notices only. Provider gates not opened. | `apps/api/runtime_service.py`, `apps/api/runtime_models.py`, `apps/api/runtime_errors.py`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_service.py`, `tests/test_api_runtime_service_v02.py`, `tests/test_cli_command_registry_boundaries.py`, `tests/test_studio_mainline_cleanup.py`, `tests/test_maintenance_audit.py`, `docs/maintenance/AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613.md` |
| AFS-BROWSER-QA-HARDENING-002 | Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Fix Claude walkthrough P0/P1 findings and continue agent-led browser QA: project isolation, modal removal, provider gate normalization, T2I/I2I optimizer split, refresh preview persistence, asset drawer/detail restore, I2I guardrail quality gate, video dead-control cleanup, and Kling video resume UI. | Focused prompt/state/static paths passed; browser loops covered project isolation, asset drawer/detail restore, live MiniMax T2I/I2I optimize/generate, asset attach-to-node semantics, video first-frame guard, and live Kling I2V submit/poll/preview. Kling now returns `submitted`, polls through `running` to `succeeded`, survives refresh through `lastVideoJobId`, and renders a safe `<video controls>` preview. Loop 5 fixed drawer fixed-asset labels/thumbnails, node placement avoidance, and `用于当前节点 -> visualAssets -> 本次携带` continuity. Remaining risks: image identity similarity and video first-frame quality need human scoring. | `apps/studio/src/store.js`, `apps/studio/src/main.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/prompt-bar.js`, `apps/studio/src/canvas-view.js`, `apps/studio/src/node-actions.js`, `apps/studio/src/node-result-view.js`, `apps/studio/src/panels/drawer.js`, `apps/studio/src/panels/add-node-menu.js`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_studio_state.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `docs/maintenance/AFS-BROWSER-QA-HARDENING-20260613.md`, `runs/i2i-gen-studio-loop-i2igen-1781307999.png`, `runs/kling-poll-ui-video-preview-20260613.png`, `runs/loop-attached-asset-generation-20260613.png` |
| AFS-KLING-PREFLIGHT-001 | Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer | Kling I2V preflight: project list/new project, safe preview persistence, ProviderDescriptor v0.2, Kling registry adapter, Runtime video submit/poll/cancel/preview, Studio explicit first-frame flow. | Live Kling I2V is now connected through the registry with local ignored provider config: browser submit returned `submitted`, API poll returned `running` then `succeeded`, preview endpoint returned `video/mp4`, and safe manifest stored no provider raw/URLs. Focused provider/video set 44 passed after async adapter fix. | `apps/api/runtime_video_routes.py`, `apps/api/runtime_models.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_adapter_impl.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `apps/studio/src/`, `tools/kling_provider_preflight.py`, `tests/test_api_runtime_video_generations.py`, `tests/test_provider_adapter_registry.py`, `docs/handoff/AFS-KLING-PREFLIGHT-001.md`, `docs/provider_adapter_v02_video_addendum.md`, `runs/kling-async-081724-first.png`, `runs/kling-async-081724-last.png` |
| AFS-MVP-HARDENING-001 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper | Dynamic-stage preflight hardening: section-header-free provider prompt, bounded generate asset injection, reference-edge hop semantics, visual asset version arbitration, reproducible bundle metadata, provider retry manifest, and Studio dead-control cleanup. | Backend focused hardening set 33 passed; Studio static 12 passed; full pytest 855 passed; changed Studio JS `node --check` passed; maintenance audit failed=0 with existing warnings. Browser light QA passed for `/studio/` load, no console errors, removed local-preview/cost/internal wording, and Chinese fixed-asset action title; current browser state had no asset badge, so readonly asset-detail click remains covered by static tests only. | `apps/api/runtime_context_resolver.py`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_prompt_text.py`, `apps/api/runtime_visual_assets.py`, `apps/studio/src/`, `tests/test_api_runtime_context_resolver.py`, `tests/test_api_runtime_creative_agent_keyframes.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-MVP-HARDENING-001.md` |
| AFS-STUDIO-MVP-USABILITY-P0 | Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Remove user-facing deterministic prompt optimization fallback; require remote LLM for Studio optimization; improve provider/gate errors; fix failed-generation state persistence; make canvas nodes direct asset-marking entrypoints. | Focused prompt/state/static tests 4 passed; related prompt/state/static suite 21 passed; changed Studio JS passed `node --check`; full pytest 844 passed; user-env image/LLM gates opened locally for this machine only. | `apps/api/runtime_prompt_memory.py`, `apps/api/runtime_studio_state.py`, `apps/studio/src/optimizer.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `apps/studio/src/panels/node-menu.js`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_studio_state_persistence.py`, `docs/handoff/AFS-STUDIO-MVP-USABILITY-P0.md` |
| AFS-PROJECT-INVENTORY-001 | Maintenance Steward + QA / Release Gatekeeper | 全量项目 inventory、ignored 本地产物审计、直接删减无用 tracked 入口、provider gateway 前维护债基线。 | Inventory/cleanup 工具 focused tests 3 passed；低风险清理累计删除 14,452 个缓存目标、约 30.24MB；直接删除 `asset_manager` 空壳和 6 份旧 production-memory asset handoff；production-memory CLI 短别名已退出默认产品面；本地重复媒体证据 80 组、约 827MB 理论可回收但需 canonical evidence retention；`data/processed/pytest-basetemp` 仍有 Windows 所有权/ACL 阻塞。 | `tools/project_inventory.py`, `tools/project_inventory_core.py`, `tests/test_project_inventory_cleanup.py`, `tests/test_cli_command_registry_boundaries.py`, `docs/maintenance/AFS-PROJECT-INVENTORY-20260612.md`, `docs/maintenance/AFS-DEEP-LOCAL-REVIEW-20260612.md`, `docs/handoff/AFS-PROJECT-INVENTORY-001.md` |
| AFS-STUDIO-MAINLINE-CLEANUP-001 | Runtime/API Integrator + Maintenance Steward | Studio 主线口径收敛; legacy Runtime v02 默认隐藏; `agentflow/memory` 标记只读遗产; tracked `*_sop` 空壳审计和最小删除。 | Focused cleanup/static tests 15 passed; full pytest 828 passed; Studio JS `node --check` 35 files passed; maintenance audit has 0 failed checks and 1 oversized-files warning; `git diff --check` clean except CRLF notices; provider gates not opened. | `AGENTS.md`, `docs/current_architecture.md`, `apps/api/runtime_service.py`, `tests/test_api_runtime_service_v02.py`, `tests/test_studio_mainline_cleanup.py`, `docs/maintenance/AFS-STUDIO-MAINLINE-CLEANUP-001.md` |
| AFS-DIRECTOR-COMPILER-V1 | Runtime/API Integrator + Studio Interaction Designer | Director Compiler v1 deterministic backend compiler; blank-stage director defaults; active camera/subjects; subject visual asset id binding; Studio confirmed prompt append. | Focused compiler/API/context/static set 24 passed; changed director JS passed `node --check`; provider gates not opened. | `apps/api/runtime_director_compiler.py`, `apps/api/runtime_prompt_memory_user_prompt.py`, `apps/api/runtime_context_resolver.py`, `apps/studio/src/director-data.js`, `apps/studio/src/panels/director-shell.js`, `docs/director_compiler_v1.md`, `tests/test_runtime_director_compiler.py`, `tests/test_api_runtime_director_setup_prompt.py`, `tests/test_web_studio_static.py` |
| AFS-PROVIDER-ADAPTER-V0-1 | Runtime/API Integrator + Provider Gate Steward | Provider Gateway v0.1: service descriptor registry, account pool selection, MiniMax image dispatch, OpenAI-compatible LLM dispatch, fake async video lifecycle contract, descriptor-driven prompt budget/reference slots. | Focused provider/keyframe/resolver/prompt tests 42 passed; provider registry tests 11 passed; provider gates remain closed except mocked dispatch paths; no live provider smoke. | `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_account_pool.py`, `configs/providers.example.json`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_context_resolver.py`, `docs/provider_adapter_contract.md`, `tests/test_provider_adapter_registry.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_creative_agent_keyframes.py` |
| AFS-ASSET-CONTEXT-S1-FOLLOWUP-001 | Runtime/API Integrator + QA Gatekeeper | S1 完成审计三缺口收尾:预算分段裁剪真执行(锁定永不裁/可见保底 550/分隔符余量)、冲突检测属性词表化、上游摘要与偏好段补填;交付特征卡模板、A/B/C runbook、内测手册。 | Focused pytest `tests/test_runtime_attribute_vocabulary_and_budget.py tests/test_api_runtime_context_resolver.py` 16 passed; changed Studio JS passed `node --check`; `git diff --check` clean except CRLF warnings. | `apps/api/runtime_attribute_vocabulary.py`, `apps/api/runtime_context_budget.py`, `apps/api/runtime_context_resolver.py`, `tests/test_runtime_attribute_vocabulary_and_budget.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1-FOLLOWUP-001.md`, `docs/visual_asset_feature_card_template.zh-CN.md`, `docs/abc_comparison_runbook.zh-CN.md`, `docs/afs_studio_internal_test_handbook.zh-CN.md` |
| AFS-ASSET-CONTEXT-S1 | Runtime/API Integrator + Studio Interaction Designer + Provider Gate Steward | Fixed visual assets, graph-scoped context resolver, dual prompt/model channels, and A/B/C comparison report. | Gate-closed Runtime/Web implementation, browser QA, live-comparison readiness runner, sample reference generator, and completion audit passed on `codex/afs-asset-context-s1`; no-call readiness has used the ignored provider config path, and live provider evidence now requires explicit `AFS_ALLOW_REMOTE_IMAGE=true` plus `--allow-live-provider`. | `apps/api/runtime_visual_assets.py`, `apps/api/runtime_context_resolver.py`, `apps/api/runtime_generation_comparisons.py`, `apps/studio/`, `tools/studio_asset_context_browser_qa.py`, `tools/studio_asset_context_live_comparison.py`, `tools/studio_asset_context_sample_reference.py`, `tests/test_api_runtime_visual_assets.py`, `tests/test_api_runtime_context_resolver.py`, `tests/test_api_runtime_generation_comparison.py`, `tests/test_studio_asset_context_live_comparison_tool.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1.md`, `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md`, `docs/maintenance/AFS-ASSET-CONTEXT-S1.md` |
| AFS-STUDIO-V02-DELIVERY-POLISH-001 | Frontend Interaction Designer + Runtime/API Integrator + QA Gatekeeper | AFS Studio v0.2 internal delivery polish: flow-native starter, safe Studio state save/restore, visible asset drawer actions, semantic edges, prompt copilot feedback, mobile overflow guard. | Verified on `codex/afs-studio-v02-delivery-polish-001`; provider gates remain closed. | `apps/studio/`, `apps/api/runtime_studio_state.py`, `tests/test_api_runtime_studio_state.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-STUDIO-V02-DELIVERY-POLISH-001.md` |
| AFS-STUDIO-UI-POLISH-DIRECTOR-002 | Frontend Interaction Designer + Runtime/API Integrator | 修复 Studio 左上角布局；落地二维导演台；将导演台结构化布置接入节点提示词优化；修复 dock 添加节点安全区。 | 已验证：全量 pytest 和浏览器 QA 通过；provider 仍关闭。 | `apps/studio/`, `apps/api/runtime_prompt_memory_user_prompt.py`, `tests/test_api_runtime_director_setup_prompt.py`, `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-STUDIO-HARD-CLEANUP-001 | Frontend Contract Steward + Maintainability Steward + QA / Release Gatekeeper | Delete retired Workbench/static memory-workbench user surfaces; make `/studio/` the only frontend entry. | In integration verification on `codex/afs-studio-hard-cleanup-001` | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-CREATIVE-INTENT-AGENT-V1 | Runtime/API Integrator + Creative Agent Architect | Add deterministic creative intent control agent trace: constraint layers, candidate scoring, selected prompt, provider translation. | Focused tests passing | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` |
| AFS-KEYFRAME-GENERATION-GATE-001 | Runtime/API Integrator + Provider Gate Steward | Add `POST /projects/{project_id}/keyframe-generations`; gate closed path returns blocked safe manifest without network. | Focused tests passing | `tests/test_api_runtime_creative_agent_keyframes.py` |
| AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001 | Runtime/API Integrator + Knowledgebase Steward | Professional rules, hidden background context, prompt assembly, trace and safe manifest. | Baseline active; now feeds creative agent | `agentflow/knowledge/`, `docs/handoff/AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md` |

## Current Baseline

### Current Verification Addendum - AFS-BROWSER-QA-HARDENING-002

- 2026-06-13 最终浏览器 QA 加固回合已收口 runtime/browser verification。
- 新增覆盖：`lastContextBundle` 安全摘要刷新持久化、生成后主动保存最终状态、资产抽屉把现有 image asset 显式设为视频首帧/尾帧、视频节点只恢复 Runtime video preview、prompt bar 对生成中的视频执行继续轮询而不是重复 submit。
- 最终验证：focused pytest 72 passed；Studio JS `node --check` 37 files passed；full pytest 886 passed；maintenance audit failed=0；`git diff --check` exit 0；浏览器最终检查显示 safe video preview 存在、发送按钮为“生成”、console warn/error 为空。
- 剩余边界：MiniMax 人物身份相似度和 Kling 首帧创意质量仍需要人工评分；本条不是 human acceptance 或 business validation。

| Area | Path | Notes |
|---|---|---|
| Frontend | `apps/studio/` | Served through `/studio/`; only current user-facing Web product. |
| Runtime API | `apps/api/` | Frontend boundary; no CLI internals, provider secrets, local private paths, signed URLs, provider raw, or media bytes. |
| Prompt optimizer contract | `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md` | Node prompt optimization only; no memory review UI. |
| Creative agent summary | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` | Repo-safe engineering summary; detailed algorithm note is private in `10-Startup`. |
| Maintenance ledger | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` | Deletion decisions and verification plan. |

## Boundaries

- Provider gates are closed unless a task explicitly opens one capability.
- Image/keyframe authorization does not authorize video, LLM, ASR, or downloads.
- Browser/runtime verification, provider smoke, human acceptance, business validation, and durable-memory promotion are separate claim levels.
- Feedback and extracted context remain evidence/background unless explicitly promoted by a human workflow.

## Next Queue

| ID | Scope | Trigger |
|---|---|---|
| AFS-STUDIO-BROWSER-QA-001 | Runtime-hosted `/studio/` browser QA: create nodes, move nodes, connect ports, optimize prompt, open director panel, check mobile layout. | Before merging/pushing this branch. |
| AFS-IMAGE-PROVIDER-SMOKE-001 | Open `AFS_ALLOW_REMOTE_IMAGE=true` and run explicit MiniMax keyframe smoke with safe artifacts. | After branch is clean and user confirms real image provider smoke. |
| AFS-KEYFRAME-QA-001 | Add visual QA for generated keyframes: subject count, text/watermark, black/blank, composition, reference consistency. | After first real keyframe provider output exists. |
| AFS-STUDIO-SPRITE-V2-S0 | v2 画布小精灵首迭代前置：undo/redo 命令栈、Action Registry（L0-L3 白名单 + schema 校验）、`#sprite-layer`。规划见 `docs/architecture/AFS_STUDIO_SPRITE_V2_PLAN.zh-CN.md`（S0-S5 全里程碑、三工作模式、LLM gate 降级策略、lottie vendored 例外）。 | After MVP v1 联合验收（AFS-STUDIO-BROWSER-QA-001）收口。 |

## Current Addendum - MiniMax Provider Smoke Prep

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001 | Runtime/API Integrator + Provider Gate Steward | Add gated MiniMax-M3 prompt enhancement and MiniMax `image-01` keyframe path; keep video/audio off. | Local live smoke passed on `127.0.0.1:8793`; manual comparison pending. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md`, `configs/models.example.yaml`, `configs/providers.example.json` |
| AFS-MINIMAX-MANUAL-COMPARISON-001 | QA / Release Gatekeeper + Creative Director | Run A/B/C keyframe comparison: raw prompt, deterministic agent prompt, MiniMax-M3 enhanced prompt. | Ready for manual operation; latest provider output shows text/watermark risk to score. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md` |
| AFS-CONNECTED-REFERENCE-KEYFRAME-001 | Runtime/API Integrator + Studio Interaction Designer | Upload images on any Studio node; collect connected upstream reference images and prompt notes for keyframe generation. | Focused tests and Runtime upload smoke passed; live creative comparison pending. | `apps/api/runtime_image_assets.py`, `apps/studio/src/optimizer-contract.js`, `tests/test_api_runtime_creative_agent_keyframes.py` |

## Current Addendum - MVP Follow-up Live Comparisons

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612 | Runtime/API Integrator + Provider Gate Steward + QA Gatekeeper | Run the pre-internal-test Group 2 character+scene asset comparison and Group 3 lock-conflict locked/unlocked live MiniMax image checks. | Implemented follow-up runner and focused tests. Group 2 first run succeeded for A/B/C; Group 3 retry succeeded for locked and temporary-unlocked runs. One later Group 2 rerun hit provider/CLI readiness block and is preserved as intermittency evidence. | `tools/studio_asset_context_followup_comparisons.py`, `tests/test_studio_asset_context_followup_comparisons.py`, `docs/handoff/AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612.md`, `runs/studio_asset_context_followup_20260612_group2_success/`, `runs/studio_asset_context_followup_20260612_group3_retry/` |

## Current Addendum - Asset Card Draft Module Split

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-ASSET-CARD-DRAFT-MODULE-SPLIT-20260619 | Runtime/API Integrator + Maintainability Steward | Split asset-card draft route helpers for visual inspection dispatch/provider observation and safe artifact writing into focused modules. | Local verification passed; provider gates unchanged; no live provider call. Oversized warning count dropped from 39 to 38. | `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_asset_card_observation.py`, `apps/api/runtime_asset_card_artifacts.py`, `tests/test_api_runtime_asset_card_modules.py`; pytest 532 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |

## Current Addendum - Auth Module Split

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-AUTH-MODULE-SPLIT-20260619 | Runtime/API Integrator + Internal Beta Steward | Split auth route/middleware assembly and password/session/token helpers out of `runtime_auth.py` while preserving invite registration, session auth, and project-owner isolation. | Local verification passed; auth policy unchanged; provider gates unchanged. Oversized warning count dropped from 38 to 37. | `apps/api/runtime_auth.py`, `apps/api/runtime_auth_routes.py`, `apps/api/runtime_auth_security.py`, `apps/api/runtime_service.py`, `tests/test_api_runtime_auth_modules.py`; auth/internal-beta focused tests 17 passed; pytest 533 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-DIRECTOR-SHELL-RENDER-SPLIT-20260619 | Studio Interaction Designer + Maintainability Steward | Split Director Shell rendering and default object construction out of the interactive shell so the director node remains easier to evolve with prompt/context workflows. | Local verification passed; provider gates unchanged; no live provider call. Oversized warning count dropped from 32 to 31. | `apps/studio/src/panels/director-shell.js`, `apps/studio/src/panels/director-shell-render.js`, `apps/studio/src/panels/director-object-factory.js`, `tests/test_web_studio_mature_shell_static.py`; red/green static test; Studio static set 32 passed; JS check 93 files passed; browser load console warn/error=0; pytest 536 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-PACKET-20260619 | QA Gatekeeper + Internal Beta Steward | Add a safe human-review packet to deterministic internal beta acceptance reports so machine verification hands off to operator scoring without claiming human acceptance. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_acceptance_review.py`, `tools/afs_internal_beta_acceptance_contract.py`, `tests/test_afs_internal_beta_acceptance.py`; red/green acceptance tests; Acceptance CLI smoke status `contract_verified_pending_human_acceptance` with `pending_human_review`; acceptance/three-end focused tests 17 passed; pytest 537 passed / 527 deselected / 2 warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-MARKDOWN-20260619 | QA Gatekeeper + Internal Beta Steward | Add optional Markdown output for the human-review packet so internal beta operators can score and decide the next beta round from a safe checklist. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_review.py`, `tests/test_afs_internal_beta_acceptance_review.py`; red/green CLI/output tests; Acceptance CLI smoke with `--human-review-md`; acceptance focused tests 18 passed; pytest 538 passed / 527 deselected / 2 warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-SPRITE-NAVIGATOR-POLISH-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Refine the movable `AFS 小精灵` into a clearer Studio navigator character with stronger silhouette, facial expression, and drag affordance. | Local verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. | `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-personality.css`, `tests/test_web_studio_sprite_static.py`; red/green sprite static test; sprite/API focused tests 6 passed / 1 existing warning; JS check 93 files passed; browser drag/open verification passed with console warn/error=0; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-SPRITE-TUANTUAN-MULTIPOSE-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Convert `AFS 小精灵` from a single reference sticker into a multi-pose `团团` companion using reference-derived idle/happy/curious/thinking/surprised/sleepy/working/celebrate PNG assets and state-driven pose switching. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. | `apps/studio/assets/tuantuan-*.png`, `apps/studio/src/sprite-widget.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite-avatar-mascot.css`, `tests/test_web_studio_sprite_static.py`; sprite/API tests 6 passed / 1 existing warning; JS check 94 files passed; browser smoke confirmed initial=idle, hover/drag=happy, settings=thinking, open=curious, 8 assets loaded, console warn/error=0. |
| AFS-STUDIO-SPRITE-TUANTUAN-MOTION-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Add a lossless continuous motion layer for TuanTuan so pointer attention, hover, drag, working, success, and error states change character transform and shadow rather than only swapping pose images. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call; full skeletal rig remains future work pending layered source art or animation assets. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-motion.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-mascot.css`, `tests/test_web_studio_sprite_static.py`; JS check 96 files passed; sprite/API focused tests 16 passed / 1 existing warning; browser smoke confirmed pointer/hover/drag changed shift, tilt, squash, and shadow variables; screenshot `runs/tuantuan-sprite-motion-smoke-20260619.png`. |
| AFS-STUDIO-SPRITE-TUANTUAN-V1-CANVAS-AGENT-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper + Product Intent Steward | Reframe TuanTuan as the embodied AFS Agent projection inside the canvas, not a mascot, desktop pet, or chatbot avatar. Implement a resting story-cat DOM rig with story orbit and Observe / Suggest / Execute state semantics. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. Public server still needs the review branch merged/deployed; the current login loop is caused by Nginx Basic Auth in front of Runtime app auth and requires sudo-side Nginx adjustment. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-motion.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `apps/studio/styles/studio-sprite-avatar-story-states.css`, `tests/test_web_studio_sprite_static.py`, `docs/handoff/AFS-STUDIO-TUANTUAN-V1-CANVAS-AGENT-20260619.md`; retired old `apps/studio/assets/tuantuan-*.png` sticker poses; added reference-shape anchors: inner ears, tabby face marks, whiskers, nose/mouth, story belly panel, front paws, segmented tail; JS check 96 files passed; sprite/API focused tests 16 passed / 1 existing warning; browser smoke confirmed role=embodied-agent, character=story-cat, observe->think->suggest state path, no old image-asset sprite, console warn/error=0. |
| AFS-STUDIO-SPRITE-TUANTUAN-REFERENCE-SHAPE-20260620 | Studio Interaction Designer + Frontend QA Gatekeeper + Product Intent Steward | Reset TuanTuan's V1 visual baseline to the user-approved reference direction: dark low resting tabby story cat, large ears/eyes, sprout, cyan story orbit, body tabby marks, paws, whiskers, and story belly panel. Keep the implementation as animatable SVG/DOM, not a sticker. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. This is a more faithful V1 visual baseline, not final IP illustration acceptance or full animation rig. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite.css`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `tests/test_web_studio_sprite_static.py`; JS check 96 files passed; sprite/API focused tests 6 passed / 1 existing warning; browser smoke confirmed `catTag=svg`, eyes=2, ears=2, tabbyMarks=3, orbitNodes=5, state=observe; screenshot `runs/tuantuan-reference-shape-20260620/tuantuan-reference-shape-avatar-v2.png`. |
| AFS-STUDIO-SPRITE-TUANTUAN-REFERENCE-CALIBRATION-20260620 | Studio Interaction Designer + Frontend QA Gatekeeper | Calibrate the V1 SVG rig closer to the latest dark resting TuanTuan reference: lower body, clearer tabby silhouette, calmer eyes, smaller sprout, quieter story panel, and canvas-native orbit. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call; not final IP acceptance. | `apps/studio/src/sprite-character.js`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `DEVLOG.md`; sprite/API tests 6 passed / 1 existing warning; JS check 96 files passed; `git diff --check` passed; Chrome render smoke inspected at `/studio/?project=tuantuan-local-preview-2`. |
| AFS-STUDIO-RUNTIME-UI-FIXES-20260621 | Runtime/API Integrator + Studio Interaction Designer + Frontend QA Gatekeeper | Fix non-video model-flow UI gaps before internal test: honest image job progress, long keyframe polling, stale Codex image worker recovery, render-safe media URLs for reference images, image asset deletion, TuanTuan focus/pending shimmer/rotating copy, and Works library drawer layout. | Local full verification passed on `codex/studio-runtime-ui-fixes`; provider gates unchanged; no live provider call; browser/runtime smoke passed. | `apps/api/runtime_jobs.py`, `apps/api/runtime_image_assets.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `apps/studio/src/`, `tests/test_api_runtime_jobs.py`, `tests/test_web_studio_frontend_wave.py`, `tests/test_web_studio_sprite_static.py`; pytest 569 passed / 527 deselected / 2 warnings; JS check 98 files passed; browser smoke `runs/studio_runtime_ui_fixes_browser_smoke.json`. |
| AFS-STUDIO-FULL-COVERAGE-QA-20260621 | QA Gatekeeper + Studio Interaction Designer + Runtime/API Integrator + Release Gatekeeper | Run a multi-role internal-test replacement pass across Studio browser UX, Runtime contracts, non-video model paths, public edge, and three-end state. Fix QA proxy handling, stale browser selectors, TuanTuan modal overlap, image asset detail 404, and add reusable browser QA coverage. | Final local browser/API verification passed; server non-video LLM/image/vision smoke passed; video gate remained closed. Commit/deploy synchronization is handled as the release step for this addendum. | `docs/maintenance/AFS-STUDIO-FULL-COVERAGE-TEST-PLAN-20260621.md`, `docs/maintenance/AFS-STUDIO-FULL-COVERAGE-TEST-RUN-20260621.md`, `tools/studio_full_coverage_browser_qa.py`, `tools/studio_asset_context_browser_qa.py`, `tools/studio_asset_context_browser_qa_support.py`, `apps/studio/src/panels/asset-detail-popover.js`, `apps/studio/styles/studio-sprite.css`; final browser reports `runs/final_existing_browser_qa_stub_20260621.json`, `runs/final_full_coverage_browser_qa_20260621.json`; server reports `runs/full_coverage_three_end_status_20260621.json`, `runs/full_coverage_public_edge_preflight_20260621.json`. |
| AFS-STUDIO-CONCURRENCY-PROMPT-RENDER-FIXES-20260621 | Runtime/API Integrator + Studio Interaction Designer + Frontend QA Gatekeeper | Finish current internal-test blocker set: real Codex image queue states, worker claim isolation, job-scoped Codex home, deterministic generated image assets, style-vs-subject reference prompt optimization, cached Runtime media rendering, full-bleed image nodes, asset context-menu delete, and TuanTuan focused-input/prompt-leak guards. | Local full verification passed on `codex/studio-concurrency-hardening`; local `master`, `origin/master`, server `/home`, and server `/opt` synchronized and deployed; server queue audit shows no active pending/running image jobs. | `agentflow_studio/model_gateway/codex_image_handoff.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `apps/api/runtime_llm_enhancement_*`, `apps/studio/src/runtime-media-source.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/src/canvas-node-body.js`, `tests/test_codex_image_handoff.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_web_studio_frontend_wave.py`; pytest 585 passed / 527 deselected / 2 warnings; JS check 99 files passed; Browser plugin smoke passed; `tools/studio_full_coverage_browser_qa.py` passed; server queue pending=0/running=0; Runtime active with image/LLM gates true and video gate false. |
| AFS-STUDIO-WEB-DIRECTOR-POLISH-20260623 | Studio Interaction Designer + Runtime/API Integrator + Frontend QA Gatekeeper | Fix current Studio interaction blockers, asset-card regeneration/persistence, standalone Social Square, homepage polish, and Director Stage production package. | Merged to `master`, pushed, deployed to server `/home` and `/opt`, Runtime/worker restarted, three-end status aligned at `53a0f17`; provider gates unchanged; live provider calls not started. | `apps/studio/src/canvas-input.js`, `apps/studio/src/store.js`, `apps/studio/src/optimizer-contract.js`, `apps/api/runtime_image_assets.py`, `apps/site/index.html`, `apps/site/social-square.html`, `apps/site/social-square.js`, `apps/studio/src/panels/director-shell-render.js`, `tests/test_site_homepage_static.py`, `tests/test_site_social_square_static.py`, `tests/test_web_studio_prompt_script_static.py`, `tests/test_api_runtime_keyframe_reference_assets.py`; JS check 112 files passed; focused pytest 42 passed; social/runtime/state pytest 52 passed; local Runtime/browser smoke passed for homepage, Social Square, image-node double-click, and asset-card homepage roundtrip persistence; public `/site/` and `/site/social-square.html` returned 200; final three-end report `runs/three_end_status_20260623_web_director_polish_final_after_restart.json` aligned. |
| AFS-INTERNAL-BETA-PUBLIC-EDGE-ACCEPTANCE-GATE-20260620 | Internal Beta Steward + Release Gatekeeper | Gate deployed HTTP internal-beta acceptance on public Studio edge readiness before invite codes or auth/project writes start. | Local and live gate verification passed; current public edge still returns `public_edge_not_ready` because Nginx Basic Auth remains active; provider gates unchanged; no live provider call. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_args.py`, `tools/afs_internal_beta_acceptance_edge_gate.py`, `tests/test_afs_internal_beta_preflight_public_edge.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`, `DEVLOG.md`; focused public-edge/acceptance tests 23 passed / 1 existing warning; live HTTP acceptance edge gate without invite codes returned `public_edge_not_ready`, exit_code=2, edge_basic_auth=true, runtime_status=ready. |
| AFS-INTERNAL-BETA-THREE-END-STATUS-CLI-20260620 | QA Gatekeeper + Release Gatekeeper | Fix standalone `tools/afs_internal_beta_acceptance.py --three-end-status` so three-end drift checks produce the safe status report instead of accidentally running deterministic acceptance. | Local focused verification passed; provider gates unchanged; no live provider call; not human acceptance or business validation. | `tools/afs_internal_beta_acceptance.py`, `tests/test_afs_internal_beta_acceptance_cli.py`, `tests/test_afs_internal_beta_acceptance.py`, `DEVLOG.md`; red/green regression for standalone three-end status; focused acceptance/preflight/three-end tests 17 passed / 1 existing warning. |
| AFS-PUBLIC-EDGE-NGINX-BASIC-AUTH-FIX-TOOL-20260620 | Release Gatekeeper + Internal Beta Steward | Add a tested server-side Nginx repair command for the public Studio edge so old Basic Auth can be removed safely when an interactive sudo session is available. | Local diagnosis and tooling completed; live edge still reports `blocked_by_edge_basic_auth` because current SSH session has no passwordless sudo; provider gates unchanged; no live provider call. | `tools/afs_public_edge_nginx_fix.py`, `tools/afs_public_edge_preflight.py`, `tests/test_afs_public_edge_nginx_fix.py`, `tests/test_afs_public_edge_preflight.py`, `tests/test_afs_internal_beta_preflight_public_edge.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`, `DEVLOG.md`; live preflight before fix blocked by Basic Auth; three-end status aligned; server Runtime health ready; focused public-edge tests 11 passed / 1 existing warning. |
| AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620 | Internal Beta Steward + QA Gatekeeper + Release Gatekeeper | Add a safe public-edge preflight and runbook to distinguish Nginx Basic Auth blocking from Runtime app auth, so deployed `/studio/` login loops are diagnosed consistently. | Local tests passed; live preflight currently reports `blocked_by_edge_basic_auth` because the public edge returns 401 Basic Auth while Runtime health is ready. Sudo-side Nginx change is still required. | `tools/afs_public_edge_preflight.py`, `tests/test_afs_public_edge_preflight.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`; focused tests 3 passed; live report `runs/public_edge_preflight_20260620.json`; provider calls not started. |
| AFS-INTERNAL-BETA-PREFLIGHT-PUBLIC-EDGE-GATE-20260620 | Internal Beta Steward + QA Gatekeeper | Wire public edge auth status into deployed HTTP internal-beta preflight, so acceptance reports fail explicitly on `public_edge_auth` when Nginx Basic Auth blocks Runtime auth. | Local focused tests passed; live deployed preflight currently reports `needs_attention` with `public_edge_auth=failed` and `blocked_by_edge_basic_auth`; provider calls not started. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_preflight.py`, `tools/afs_internal_beta_preflight_public_edge.py`, `tests/test_afs_internal_beta_acceptance.py`; focused tests 16 passed / 1 existing warning; live report `runs/internal_beta_preflight_public_edge_latest_20260620.json`. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-RECORD-20260619 | QA Gatekeeper + Internal Beta Steward | Add a safe human-review record step so completed operator scores and decisions can become a bounded internal-beta evidence artifact after the Markdown checklist. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_human_review_record.py`, `tests/test_afs_internal_beta_human_review_record.py`; red/green record tests; PowerShell UTF-8 BOM regression; CLI smoke generated `accepted_for_next_beta_round` while keeping business/durable claims not claimed; acceptance focused tests 22 passed; `git diff --check` passed. |
