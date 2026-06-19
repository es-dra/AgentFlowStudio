# AFS Studio TuanTuan V1 Canvas Agent Handoff - 2026-06-19

## Source Intent

This slice treats the latest product intent as the source of truth:

- TuanTuan is not a mascot, desktop pet, chatbot avatar, or floating assistant widget.
- TuanTuan is the embodied projection of the AFS Agent system inside the canvas.
- The default state should be valuable: quiet, present, observing, and non-interruptive.
- The visible operating principle is `Observe -> Suggest -> Execute`.
- The story orbit represents ideas, plans, suggestions, stories, and creative structure.

## Implementation

- `apps/studio/src/sprite-character.js`
  - Replaced the previous pose image registry with `SPRITE_AGENT_STATES`.
  - Added `spriteStoryLayers()` for story orbit, suggestion bubble, preview ghost, complete sparks, sleep mark, and a DOM-layered resting story cat.
  - Keeps compatibility exports such as `currentSpritePose()` and `setTemporarySpritePose()` while internally using state semantics.

- `apps/studio/src/sprite-motion.js`
  - Uses `observe`, `think`, `suggest`, `execute`, `success`, `error`, and `drag` motion modes.
  - Pointer attention and drag still drive low-level motion variables, but the default mode is now `observe`.

- `apps/studio/src/sprite-widget.js`
  - Exposes `data-sprite-role="embodied-agent"` and `data-sprite-character="story-cat"`.
  - Uses quiet copy: TuanTuan observes first and suggests when needed.
  - The panel is still a lightweight chat/suggestion surface, but it is not positioned as the product identity.

- `apps/studio/styles/studio-sprite-avatar-story-cat.css`
  - Defines the base resting story-cat shape.
  - Keeps the low-profile dark-canvas compatible visual language.

- `apps/studio/styles/studio-sprite-avatar-story-states.css`
  - Owns orbit speed, suggest/preview/execute/complete/sleep state behavior, drag affordance, sequence label, and reduced-motion fallback.

- Previous `apps/studio/assets/tuantuan-*.png` pose assets
  - Retired from the current Studio surface because V1 should not be implemented as sticker swapping.

## Verification

```text
npm run check:studio-js
=> JS syntax check passed: 96 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py tests\test_web_studio_sprite_static.py tests\test_api_runtime_sprite.py -q
=> 16 passed, 1 existing Starlette/httpx warning

.\.venv\Scripts\python.exe -m pytest -q
=> 543 passed, 527 deselected, 2 existing warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
=> failed=0, warnings only

git diff --check
=> passed

Chrome smoke at /studio/?project=tuantuan-v1-smoke
=> role=embodied-agent
=> character=story-cat
=> initial state=observe
=> hover state=think
=> open state=suggest
=> story orbit / cat / body / eyes present
=> old sprite-tuantuan-asset image layer absent
=> console warning/error count 0
=> screenshot: runs/tuantuan-v1-story-cat-smoke-20260619.png

Chrome smoke after retiring the old PNG assets
=> assetImageCount=0
=> no failed requests
=> console warning/error count 0
```

## Public Server Diagnosis

The public login loop at `https://afstudio.art/studio/` is caused by Nginx Basic Auth in front of the Runtime app:

```text
curl -I https://afstudio.art/studio/
=> 401 Unauthorized
=> WWW-Authenticate: Basic realm="AFS Studio Internal Test"
```

The Runtime app itself responds locally on the server:

```text
http://127.0.0.1:8790/studio/
=> 200 OK
```

The server file `/etc/nginx/sites-available/afs-runtime` currently protects `location /` with:

```nginx
auth_basic "AFS Studio Internal Test";
auth_basic_user_file /etc/nginx/.htpasswd_afs;
```

Recommended server fix after sudo access is available:

```bash
sudo cp /etc/nginx/sites-available/afs-runtime /etc/nginx/sites-available/afs-runtime.bak-$(date +%Y%m%d%H%M%S)
sudoedit /etc/nginx/sites-available/afs-runtime
sudo nginx -t
sudo systemctl reload nginx
```

Inside `location /`, either remove the two Basic Auth lines or set `auth_basic off;`. Runtime app auth remains enabled and should own the product login/invite flow.

## Deployment Gate

The server still runs `master`, so it will not show this TuanTuan V1 review branch until the branch is merged and deployed.

Do not claim the public site is fixed until:

1. This branch is merged to `master`.
2. `origin/master` is updated.
3. `/home/afs-ops/AgentFlowStudio` is fast-forwarded.
4. `/opt/afs/AgentFlowStudio` is synced.
5. `afs-runtime` is restarted.
6. Nginx Basic Auth is adjusted or intentionally kept with verified credentials.
7. `/health`, `/site/`, and `/studio/` are verified through the public domain.

## Boundaries

- No Runtime API shape changed.
- No provider gate changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, secret, or Company OS private source content was written.
- This is frontend/runtime verification only, not human acceptance or business validation.
