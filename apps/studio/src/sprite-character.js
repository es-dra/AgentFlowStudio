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
    '    <linearGradient id="tuantuanBody" x1="42" y1="30" x2="286" y2="170" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#162f44" />',
    '      <stop offset="0.34" stop-color="#0e1a25" />',
    '      <stop offset="1" stop-color="#030509" />',
    "    </linearGradient>",
    '    <linearGradient id="tuantuanEar" x1="61" y1="16" x2="176" y2="92" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#25455f" />',
    '      <stop offset="0.58" stop-color="#111b26" />',
    '      <stop offset="1" stop-color="#020509" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanEye" cx="38%" cy="28%" r="72%">',
    '      <stop offset="0" stop-color="#ffffff" />',
    '      <stop offset="0.2" stop-color="#ffffff" />',
    '      <stop offset="0.28" stop-color="#a8b6ff" />',
    '      <stop offset="0.48" stop-color="#00e5ff" />',
    '      <stop offset="0.58" stop-color="#07131d" />',
    '      <stop offset="1" stop-color="#000204" />',
    "    </radialGradient>",
    '    <linearGradient id="tuantuanSprout" x1="0" y1="0" x2="0" y2="46" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#d8ff78" />',
    '      <stop offset="0.54" stop-color="#7cff82" />',
    '      <stop offset="1" stop-color="#244a34" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanSoftGlow" cx="50%" cy="50%" r="72%">',
    '      <stop offset="0" stop-color="#00e5ff" stop-opacity="0.3" />',
    '      <stop offset="1" stop-color="#00e5ff" stop-opacity="0" />',
    "    </radialGradient>",
    "  </defs>",
    '  <ellipse class="sprite-cat-ground-glow" cx="164" cy="166" rx="138" ry="22" />',
    '  <g class="sprite-cat-resting-silhouette">',
    '    <g class="sprite-cat-tail">',
    '      <path class="sprite-cat-tail-shape" d="M226 123 C279 115 300 64 265 43 C235 25 210 48 221 75 C231 97 262 88 264 62" />',
    '      <path class="sprite-tail-panel one" d="M260 42 C277 56 280 75 270 91" />',
    '      <path class="sprite-tail-panel two" d="M225 67 C240 79 250 94 254 113" />',
    '      <path class="sprite-tail-panel three" d="M211 123 C230 126 247 135 258 150" />',
    "    </g>",
    '    <path class="sprite-cat-body sprite-cat-outline" d="M118 122 C136 80 183 61 225 69 C275 78 298 110 288 140 C278 174 219 179 166 159 C134 147 106 151 88 138 C76 129 96 124 118 122 Z" />',
    '    <path class="sprite-cat-body-shade" d="M147 82 C183 62 241 76 274 112 C233 97 190 98 150 110 C124 118 103 132 87 141 C83 116 105 93 147 82 Z" />',
    '    <path class="sprite-cat-back-glow" d="M153 75 C199 54 268 81 282 133" />',
    '    <path class="sprite-cat-tabby-mark body one" d="M172 79 C189 88 202 103 209 120" />',
    '    <path class="sprite-cat-tabby-mark body two" d="M219 83 C234 98 242 114 244 131" />',
    '    <path class="sprite-cat-tabby-mark body three" d="M239 142 C217 154 188 154 159 143" />',
    '    <g class="sprite-cat-head">',
    '      <path class="sprite-cat-ear left sprite-cat-outline" d="M61 78 C48 32 67 13 103 47 C114 59 106 82 86 88 Z" />',
    '      <path class="sprite-cat-inner-ear left" d="M72 69 C67 45 77 30 96 51 C101 63 94 74 83 76 Z" />',
    '      <path class="sprite-cat-ear right sprite-cat-outline" d="M151 73 C170 31 195 19 193 66 C190 84 171 94 155 85 Z" />',
    '      <path class="sprite-cat-inner-ear right" d="M161 66 C173 43 184 35 184 62 C181 73 171 78 162 75 Z" />',
    '      <path class="sprite-cat-face sprite-cat-outline" d="M53 88 C65 48 101 31 136 41 C172 51 188 86 175 123 C163 157 126 170 88 155 C55 142 42 113 53 88 Z" />',
    '      <path class="sprite-cat-cheek-glow" d="M57 117 C84 142 139 142 170 115 C163 151 126 170 88 155 C65 146 52 131 49 115 Z" />',
    '      <g class="sprite-cat-sprout">',
    '        <path d="M121 40 C119 24 117 13 113 3" />',
    '        <ellipse cx="105" cy="6" rx="14" ry="8" transform="rotate(24 105 6)" />',
    '        <ellipse cx="128" cy="7" rx="14" ry="8" transform="rotate(-24 128 7)" />',
    "      </g>",
    '      <path class="sprite-cat-face-mark forehead" d="M119 52 C102 64 111 79 126 84 C116 70 132 63 119 52 Z" />',
    '      <path class="sprite-cat-face-mark forehead-side left" d="M94 57 C82 62 74 73 71 85" />',
    '      <path class="sprite-cat-face-mark forehead-side right" d="M143 58 C157 64 164 75 165 89" />',
    '      <path class="sprite-cat-face-mark cheek left" d="M58 103 C75 99 89 103 99 111" />',
    '      <path class="sprite-cat-face-mark cheek right" d="M144 111 C157 103 168 101 178 105" />',
    '      <g class="sprite-cat-eye left"><ellipse cx="91" cy="101" rx="15" ry="23" /><circle cx="86" cy="91" r="5" /><circle cx="98" cy="114" r="3.6" /></g>',
    '      <g class="sprite-cat-eye right"><ellipse cx="138" cy="102" rx="15" ry="23" /><circle cx="133" cy="92" r="5" /><circle cx="145" cy="116" r="3.6" /></g>',
    '      <path class="sprite-cat-nose" d="M113 122 C119 117 125 119 128 123 C125 129 117 129 113 122 Z" />',
    '      <path class="sprite-cat-mouth" d="M121 128 C114 135 106 134 102 128 M122 128 C129 136 138 134 143 128" />',
    '      <g class="sprite-cat-whiskers left"><path d="M103 121 C80 115 63 116 44 121" /><path d="M104 130 C81 132 64 140 47 150" /></g>',
    '      <g class="sprite-cat-whiskers right"><path d="M137 122 C161 116 179 117 197 122" /><path d="M137 131 C162 134 179 143 196 153" /></g>',
    "    </g>",
    '    <g class="sprite-cat-forepaws">',
    '      <path class="sprite-cat-paw left sprite-cat-outline" d="M70 151 C84 138 107 140 115 154 C113 170 79 172 68 162 C64 158 66 154 70 151 Z" />',
    '      <path class="sprite-cat-paw right sprite-cat-outline" d="M146 151 C159 138 184 140 190 156 C184 172 151 172 141 162 C137 158 141 154 146 151 Z" />',
    "    </g>",
    '    <g class="sprite-cat-story-panel">',
    '      <rect x="97" y="137" width="42" height="25" rx="10" />',
    '      <circle cx="109" cy="147" r="3" />',
    '      <circle cx="126" cy="147" r="3" />',
    '      <path d="M110 156 C116 160 123 160 129 156" />',
    "    </g>",
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
