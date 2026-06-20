export const SPRITE_AGENT_STATES = {
  observe: "观察",
  think: "思考",
  suggest: "提案",
  preview: "预览",
  execute: "执行",
  complete: "完成",
  sleep: "休息",
};

// TuanTuan visualizes the AFS Agent sequence: Observe → Suggest → Execute.
const IDLE_AGENT_STATES = ["observe", "observe", "think", "observe", "sleep"];
let spriteTickerBound = false;
let idleStateIndex = 0;
let temporaryState = "";
let temporaryStateTimer = 0;

export function spriteStoryLayers() {
  return [
    '<span class="sprite-story-orbit" aria-hidden="true">',
    '  <i data-orbit-node="observe"></i>',
    '  <i data-orbit-node="suggest"></i>',
    '  <i data-orbit-node="preview"></i>',
    '  <i data-orbit-node="execute"></i>',
    '  <i data-orbit-node="complete"></i>',
    "</span>",
    '<span class="sprite-preview-ghost" aria-hidden="true"></span>',
    '<span class="sprite-suggestion-bubble" aria-hidden="true"><i></i><b></b><i></i></span>',
    '<span class="sprite-complete-sparks" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-sleep-mark" aria-hidden="true">zZ</span>',
    '<svg class="sprite-tuantuan-cat" aria-hidden="true" viewBox="0 0 286 166" focusable="false">',
    "  <defs>",
    '    <linearGradient id="tuantuanBody" x1="28" y1="26" x2="248" y2="148" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#24384b" />',
    '      <stop offset="0.46" stop-color="#0f1b25" />',
    '      <stop offset="1" stop-color="#03070b" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanEye" cx="36%" cy="26%" r="72%">',
    '      <stop offset="0" stop-color="#ffffff" />',
    '      <stop offset="0.18" stop-color="#ffffff" />',
    '      <stop offset="0.24" stop-color="#a8b6ff" />',
    '      <stop offset="0.43" stop-color="#00e5ff" />',
    '      <stop offset="0.5" stop-color="#07131d" />',
    '      <stop offset="1" stop-color="#000204" />',
    "    </radialGradient>",
    '    <linearGradient id="tuantuanSprout" x1="0" y1="0" x2="0" y2="46" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#cfff75" />',
    '      <stop offset="0.54" stop-color="#7cff82" />',
    '      <stop offset="1" stop-color="#274b35" />',
    "    </linearGradient>",
    "  </defs>",
    '  <ellipse class="sprite-cat-ground-glow" cx="146" cy="139" rx="116" ry="18" />',
    '  <g class="sprite-cat-tail">',
    '    <path class="sprite-cat-tail-shape" d="M214 103 C268 100 274 48 237 44 C209 41 205 70 232 72 C250 73 249 57 235 56" />',
    '    <path class="sprite-tail-panel one" d="M232 47 C247 52 257 62 260 75" />',
    '    <path class="sprite-tail-panel two" d="M213 61 C231 67 243 80 247 97" />',
    '    <path class="sprite-tail-panel three" d="M196 89 C214 91 228 101 236 115" />',
    "  </g>",
    '  <path class="sprite-cat-body sprite-cat-outline" d="M88 88 C98 55 137 39 178 45 C226 52 257 82 252 116 C248 143 217 151 173 143 C142 138 110 137 91 122 C81 114 80 101 88 88 Z" />',
    '  <path class="sprite-cat-body-shade" d="M126 58 C153 47 206 58 236 96 C207 82 176 80 142 87 C120 92 104 103 91 122 C78 100 91 73 126 58 Z" />',
    '  <path class="sprite-cat-tabby-mark body one" d="M144 56 C160 62 172 71 181 85" />',
    '  <path class="sprite-cat-tabby-mark body two" d="M194 62 C207 70 217 81 224 96" />',
    '  <path class="sprite-cat-tabby-mark body three" d="M216 106 C200 116 181 120 161 117" />',
    '  <g class="sprite-cat-head">',
    '    <path class="sprite-cat-ear left sprite-cat-outline" d="M55 55 C49 27 61 11 79 38 C86 49 83 64 69 68 Z" />',
    '    <path class="sprite-cat-inner-ear left" d="M62 48 C59 34 65 25 76 40 C80 47 78 56 70 58 Z" />',
    '    <path class="sprite-cat-ear right sprite-cat-outline" d="M128 55 C138 25 153 15 157 49 C157 65 146 73 133 66 Z" />',
    '    <path class="sprite-cat-inner-ear right" d="M136 51 C142 35 150 30 151 49 C151 58 145 62 139 59 Z" />',
    '    <path class="sprite-cat-face sprite-cat-outline" d="M54 66 C61 37 86 24 111 31 C138 39 149 65 142 94 C136 122 112 134 84 126 C59 119 46 94 54 66 Z" />',
    '    <path class="sprite-cat-cheek-glow" d="M60 94 C79 112 119 113 138 93 C134 119 112 133 85 126 C67 121 56 111 51 96 Z" />',
    '    <g class="sprite-cat-sprout">',
    '      <path d="M101 31 C100 18 99 10 96 2" />',
    '      <ellipse cx="89" cy="0" rx="16" ry="8" transform="rotate(24 89 0)" />',
    '      <ellipse cx="108" cy="1" rx="16" ry="8" transform="rotate(-26 108 1)" />',
    "    </g>",
    '    <path class="sprite-cat-face-mark forehead" d="M98 40 C87 48 91 57 102 62 C97 54 105 49 98 40 Z" />',
    '    <path class="sprite-cat-face-mark forehead-side left" d="M81 45 C72 48 67 54 64 62" />',
    '    <path class="sprite-cat-face-mark forehead-side right" d="M119 45 C130 49 134 56 135 65" />',
    '    <path class="sprite-cat-face-mark cheek left" d="M57 82 C68 79 76 80 83 85" />',
    '    <path class="sprite-cat-face-mark cheek right" d="M124 86 C133 81 139 80 145 82" />',
    '    <g class="sprite-cat-eye left"><ellipse cx="82" cy="77" rx="13" ry="18" /><circle cx="78" cy="70" r="4" /><circle cx="86" cy="84" r="3" /></g>',
    '    <g class="sprite-cat-eye right"><ellipse cx="118" cy="78" rx="13" ry="18" /><circle cx="114" cy="71" r="4" /><circle cx="122" cy="86" r="3" /></g>',
    '    <path class="sprite-cat-nose" d="M99 95 C103 91 108 93 110 96 C107 101 102 101 99 95 Z" />',
    '    <path class="sprite-cat-mouth" d="M104 100 C99 106 93 105 90 100 M105 100 C110 107 116 105 119 100" />',
    '    <g class="sprite-cat-whiskers left"><path d="M91 96 C72 92 61 91 45 93" /><path d="M91 103 C72 105 59 110 45 117" /></g>',
    '    <g class="sprite-cat-whiskers right"><path d="M118 97 C137 92 151 91 165 94" /><path d="M118 104 C139 106 151 112 164 119" /></g>',
    "  </g>",
    '  <path class="sprite-cat-paw left sprite-cat-outline" d="M72 121 C81 111 99 111 105 123 C104 136 78 139 70 131 C67 127 68 124 72 121 Z" />',
    '  <path class="sprite-cat-paw right sprite-cat-outline" d="M134 124 C144 113 164 115 169 128 C164 141 139 142 131 134 C128 130 130 127 134 124 Z" />',
    '  <g class="sprite-cat-story-panel">',
    '    <rect x="76" y="106" width="44" height="30" rx="10" />',
    '    <circle cx="91" cy="118" r="3" />',
    '    <circle cx="107" cy="118" r="3" />',
    '    <path d="M93 127 C98 132 105 132 110 127" />',
    "  </g>",
    "</svg>",
    '<span class="sprite-tuantuan-shadow" aria-hidden="true"></span>',
  ];
}

export function currentSpritePose(state = {}) {
  return currentSpriteState(state);
}

export function currentSpriteState(state = {}) {
  if (temporaryState) return temporaryState;
  if (state.sending) return "think";
  if (state.settingsOpen) return "think";
  if (state.open) return "suggest";
  return IDLE_AGENT_STATES[idleStateIndex] || "observe";
}

export function setSpritePose(button = document.querySelector(".afs-sprite-avatar"), state = currentSpriteState()) {
  if (!button) return;
  const nextState = SPRITE_AGENT_STATES[state] ? state : "observe";
  button.dataset.spriteState = nextState;
  button.dataset.spritePose = nextState;
}

export function applySpritePose(root = document.getElementById("sprite-root"), state = {}) {
  setSpritePose(root?.querySelector(".afs-sprite-avatar"), currentSpriteState(state));
}

export function bindSpritePoseTicker(getState, onTick) {
  if (spriteTickerBound || typeof window === "undefined") return;
  spriteTickerBound = true;
  window.setInterval(() => {
    const state = getState?.() || {};
    if (state.open || state.settingsOpen || state.sending || temporaryState) return;
    const root = document.getElementById("sprite-root");
    if (root?.classList.contains("is-dragging")) return;
    idleStateIndex = (idleStateIndex + 1) % IDLE_AGENT_STATES.length;
    onTick?.();
  }, 9000);
}

export function setTemporarySpritePose(state, duration = 1500, onExpire) {
  if (!SPRITE_AGENT_STATES[state] || typeof window === "undefined") return;
  temporaryState = state;
  window.clearTimeout(temporaryStateTimer);
  temporaryStateTimer = window.setTimeout(() => {
    temporaryState = "";
    onExpire?.();
  }, duration);
}
