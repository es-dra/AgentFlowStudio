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
    '<svg class="sprite-tuantuan-cat" aria-hidden="true" viewBox="0 0 320 190" focusable="false">',
    "  <defs>",
    '    <linearGradient id="tuantuanBody" x1="44" y1="18" x2="285" y2="169" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#193148" />',
    '      <stop offset="0.42" stop-color="#0e1822" />',
    '      <stop offset="1" stop-color="#05070b" />',
    "    </linearGradient>",
    '    <linearGradient id="tuantuanEar" x1="76" y1="18" x2="146" y2="88" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#243f57" />',
    '      <stop offset="0.62" stop-color="#0d1822" />',
    '      <stop offset="1" stop-color="#04080d" />',
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
    '    <radialGradient id="tuantuanSoftGlow" cx="50%" cy="50%" r="72%">',
    '      <stop offset="0" stop-color="#00e5ff" stop-opacity="0.34" />',
    '      <stop offset="1" stop-color="#00e5ff" stop-opacity="0" />',
    "    </radialGradient>",
    "  </defs>",
    '  <ellipse class="sprite-cat-ground-glow" cx="162" cy="165" rx="134" ry="22" />',
    '  <g class="sprite-cat-resting-silhouette">',
    '  <g class="sprite-cat-tail">',
    '    <path class="sprite-cat-tail-shape" d="M230 118 C296 107 312 42 261 32 C225 25 211 62 238 76 C260 88 275 68 259 56" />',
    '    <path class="sprite-tail-panel one" d="M260 34 C279 44 289 61 287 79" />',
    '    <path class="sprite-tail-panel two" d="M228 61 C250 70 264 87 269 106" />',
    '    <path class="sprite-tail-panel three" d="M211 104 C230 105 248 114 258 128" />',
    "  </g>",
    '  <path class="sprite-cat-body sprite-cat-outline" d="M118 118 C127 73 174 51 221 63 C274 77 296 115 278 147 C262 176 211 174 165 157 C139 148 113 150 93 138 C83 132 105 125 118 118 Z" />',
    '  <path class="sprite-cat-body-shade" d="M148 78 C178 61 232 68 264 103 C229 91 190 92 153 104 C131 112 113 125 95 139 C88 115 109 90 148 78 Z" />',
    '  <path class="sprite-cat-back-glow" d="M151 74 C195 52 259 78 275 133" />',
    '  <path class="sprite-cat-tabby-mark body one" d="M169 75 C188 84 202 98 210 116" />',
    '  <path class="sprite-cat-tabby-mark body two" d="M218 81 C233 94 242 109 245 127" />',
    '  <path class="sprite-cat-tabby-mark body three" d="M237 139 C215 151 188 151 160 141" />',
    '  <g class="sprite-cat-head">',
    '    <path class="sprite-cat-ear left sprite-cat-outline" d="M64 71 C57 31 73 10 101 48 C109 62 100 79 82 82 Z" />',
    '    <path class="sprite-cat-inner-ear left" d="M73 62 C70 43 78 29 94 50 C99 61 93 70 83 72 Z" />',
    '    <path class="sprite-cat-ear right sprite-cat-outline" d="M149 71 C164 29 187 15 187 60 C184 78 167 87 153 79 Z" />',
    '    <path class="sprite-cat-inner-ear right" d="M158 65 C167 42 179 34 178 60 C176 70 167 74 160 72 Z" />',
    '    <path class="sprite-cat-face sprite-cat-outline" d="M58 84 C68 46 101 29 133 39 C166 49 181 84 169 119 C158 153 124 166 88 152 C56 140 45 110 58 84 Z" />',
    '    <path class="sprite-cat-cheek-glow" d="M61 116 C84 139 137 139 165 113 C159 148 123 166 88 152 C66 143 54 130 50 115 Z" />',
    '    <g class="sprite-cat-sprout">',
    '      <path d="M120 38 C118 22 117 12 113 2" />',
    '      <ellipse cx="105" cy="4" rx="16" ry="9" transform="rotate(24 105 4)" />',
    '      <ellipse cx="128" cy="5" rx="16" ry="9" transform="rotate(-24 128 5)" />',
    "    </g>",
    '    <path class="sprite-cat-face-mark forehead" d="M117 51 C104 62 110 74 124 80 C116 69 129 61 117 51 Z" />',
    '    <path class="sprite-cat-face-mark forehead-side left" d="M94 58 C82 63 75 72 72 83" />',
    '    <path class="sprite-cat-face-mark forehead-side right" d="M141 57 C155 63 161 73 162 86" />',
    '    <path class="sprite-cat-face-mark cheek left" d="M62 103 C77 99 88 101 97 108" />',
    '    <path class="sprite-cat-face-mark cheek right" d="M143 108 C155 101 164 100 172 103" />',
    '    <g class="sprite-cat-eye left"><ellipse cx="92" cy="99" rx="15" ry="22" /><circle cx="87" cy="89" r="5" /><circle cx="97" cy="111" r="3.5" /></g>',
    '    <g class="sprite-cat-eye right"><ellipse cx="137" cy="100" rx="15" ry="22" /><circle cx="132" cy="90" r="5" /><circle cx="142" cy="113" r="3.5" /></g>',
    '    <path class="sprite-cat-nose" d="M113 121 C118 116 124 118 127 122 C124 128 117 128 113 121 Z" />',
    '    <path class="sprite-cat-mouth" d="M120 127 C114 134 106 133 102 127 M121 127 C128 135 136 133 141 127" />',
    '    <g class="sprite-cat-whiskers left"><path d="M103 121 C80 115 64 115 45 119" /><path d="M104 129 C81 131 65 138 48 148" /></g>',
    '    <g class="sprite-cat-whiskers right"><path d="M136 122 C159 116 176 116 193 121" /><path d="M136 130 C160 133 176 141 192 151" /></g>',
    "  </g>",
    '  <g class="sprite-cat-forepaws">',
    '    <path class="sprite-cat-paw left sprite-cat-outline" d="M72 151 C84 138 106 139 114 153 C112 169 80 171 70 162 C66 158 68 154 72 151 Z" />',
    '    <path class="sprite-cat-paw right sprite-cat-outline" d="M145 151 C157 138 181 140 188 155 C182 171 151 171 141 162 C137 158 140 154 145 151 Z" />',
    "  </g>",
    '  <g class="sprite-cat-story-panel">',
    '    <rect x="94" y="136" width="42" height="26" rx="10" />',
    '    <circle cx="106" cy="146" r="3" />',
    '    <circle cx="123" cy="146" r="3" />',
    '    <path d="M108 155 C113 160 121 160 127 155" />',
    "  </g>",
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
