from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def test_studio_sprite_widget_is_wired_to_runtime_chat() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    sprite = (STUDIO_ROOT / "src" / "sprite-widget.js").read_text(encoding="utf-8")
    character = (STUDIO_ROOT / "src" / "sprite-character.js").read_text(encoding="utf-8")
    motion = (STUDIO_ROOT / "src" / "sprite-motion.js").read_text(encoding="utf-8")
    position = (STUDIO_ROOT / "src" / "sprite-position.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "studio-sprite.css").read_text(encoding="utf-8")
    avatar_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar.css").read_text(encoding="utf-8")
    avatar_motion_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-motion.css").read_text(encoding="utf-8")
    avatar_story_cat_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-story-cat.css").read_text(encoding="utf-8")
    avatar_story_cat_details = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-story-cat-details.css").read_text(encoding="utf-8")
    avatar_story_state_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-story-states.css").read_text(encoding="utf-8")
    sprite_styles = (
        styles
        + avatar_styles
        + avatar_motion_styles
        + avatar_story_cat_styles
        + avatar_story_cat_details
        + avatar_story_state_styles
    )

    assert '<div id="sprite-root"></div>' in index
    assert './styles/studio-sprite.css' in index
    assert 'from "./sprite-widget.js"' in main
    assert "renderSpriteWidget" in main
    assert "spriteChat(payload)" in runtime_client
    assert "/sprite/chat" in runtime_client

    assert "afs-sprite" in sprite
    assert 'from "./sprite-position.js"' in sprite
    assert 'from "./sprite-character.js"' in sprite
    assert 'from "./sprite-motion.js"' in sprite
    assert "团团" in sprite
    assert "观察 · 提案 · 执行" in sprite
    assert "data-sprite-draggable" in sprite
    assert 'data-sprite-role", "embodied-agent"' in sprite
    assert 'data-sprite-character", "story-cat"' in sprite
    assert "bindSpriteMotion" in sprite
    assert "setSpriteMotionMode" in sprite
    assert "pulseSpriteMotion" in sprite
    assert "bindSpritePoseTicker" in sprite
    assert "currentSpritePose" in sprite
    assert "setTemporarySpritePose" in sprite
    assert "data-sprite-state" in sprite
    assert "spriteStoryLayers()" in sprite
    assert "sprite-move-handle" in sprite
    assert "sprite-agent-sequence" in sprite
    assert "runtime.spriteChat" in sprite
    assert "data-sprite-drag-handle" in sprite
    assert 'data-sprite-drag-handle="true"' in sprite
    assert "spriteSettingsPanel" in sprite
    assert "contextmenu" in sprite
    assert "setSpriteScale" in sprite
    assert "getSpriteScale" in sprite
    assert "isSpriteHidden" in sprite
    assert "setSpriteHidden" in sprite
    assert "spriteRestoreButton" in sprite
    assert "关闭团团" in sprite
    assert "显示团团" in sprite
    assert "afs-sprite-close" in sprite
    assert "afs-sprite-restore" in sprite
    assert "data-sprite-settings" in sprite
    assert "startSpriteDrag" in sprite
    assert "nudgeSpritePosition" in sprite
    assert "rememberSpritePositionFromRoot" in sprite
    assert 'button.addEventListener("keydown", nudgeSpritePosition)' in sprite
    assert "handleSpriteDrag" in sprite
    assert "__afsStudio" not in sprite
    assert "provider raw" not in sprite
    assert "mascot" not in sprite
    assert "desktop pet" not in sprite
    assert len(sprite.splitlines()) <= 300

    assert "SPRITE_AGENT_STATES" in character
    assert "Observe → Suggest → Execute" in character
    assert "spriteStoryLayers" in character
    assert '<svg class="sprite-tuantuan-cat"' in character
    assert 'viewBox="0 0 390 230"' in character
    assert "tuantuanBody" in character
    assert "tuantuanEar" in character
    assert "tuantuanStripe" in character
    assert "tuantuanSoftGlow" in character
    assert "sprite-story-orbit" in character
    assert "sprite-tuantuan-cat" in character
    assert "sprite-cat-resting-silhouette" in character
    assert "sprite-cat-body" in character
    assert "sprite-cat-face" in character
    assert "sprite-cat-eye" in character
    assert "sprite-cat-tail" in character
    assert "sprite-cat-rear-paw" in character
    assert "sprite-cat-pupil" in character
    assert "sprite-cat-outline" in character
    assert "sprite-cat-ear-rim" in character
    assert "sprite-cat-tabby-mark" in character
    assert "sprite-cat-tabby-mark body four" in character
    assert "sprite-cat-face-mark brow" in character
    assert "sprite-cat-face-ridge" in character
    assert "sprite-cat-ground-glow" in character
    assert "sprite-cat-inner-ear" in character
    assert "sprite-cat-face-mark" in character
    assert "sprite-cat-whiskers" in character
    assert "sprite-cat-eye-shine" in character
    assert "sprite-cat-nose" in character
    assert "sprite-cat-story-panel" in character
    assert "sprite-cat-sprout" in character
    assert "sprite-tail-panel" in character
    assert "sprite-cat-forepaws" in character
    assert "sprite-cat-back-glow" in character
    assert "sprite-suggestion-bubble" in character
    assert "SPRITE_POSE_ASSETS" not in character
    assert "Object.entries(SPRITE_POSE_ASSETS)" not in character
    assert "sprite-tuantuan-asset" not in character
    for state in ["observe", "think", "suggest", "preview", "execute", "complete", "sleep"]:
        assert state in character
    assert len(character.splitlines()) <= 300

    assert len(motion.splitlines()) <= 300
    assert "requestAnimationFrame" in motion
    assert "pointermove" in motion
    assert "targetMotion" in motion
    assert "motionTarget" in motion
    assert "prefersReducedMotion" in motion
    assert "--sprite-shift-x" in motion
    assert "--sprite-shift-y" in motion
    assert "--sprite-tilt-deg" in motion
    assert "--sprite-shadow-scale" in motion
    assert "--sprite-shadow-opacity" in motion
    assert "dataset.spriteMotion" in motion

    assert "SPRITE_POSITION_KEY" in position
    assert "SPRITE_POSITION_VERSION" in position
    assert "2026-06-tuantuan-reference-cat-v3" in position
    assert "SPRITE_SIZE = 232" in position
    assert "const SPRITE_HEIGHT = 212" in position
    assert "SPRITE_SCALE_KEY" in position
    assert "SPRITE_HIDDEN_KEY" in position
    assert '{ id: "normal", label: "中", value: 0.9 }' in position
    assert "SPRITE_SCALE_OPTIONS" in position
    assert "getSpriteScale" in position
    assert "setSpriteScale" in position
    assert "isSpriteHidden" in position
    assert "setSpriteHidden" in position
    assert "safeDefaultSpritePosition" in position
    assert "captureSpritePointer" in position
    assert "setPointerCapture" in position
    assert "storeSpritePosition" in position
    assert "clampSpritePosition" in position
    assert len(position.splitlines()) <= 300

    assert '@import url("./studio-sprite-avatar.css");' in styles
    assert '@import url("./studio-sprite-avatar-motion.css");' in styles
    assert '@import url("./studio-sprite-avatar-story-cat.css");' in styles
    assert '@import url("./studio-sprite-avatar-story-cat-details.css");' in styles
    assert '@import url("./studio-sprite-avatar-story-states.css");' in styles
    assert "studio-sprite-avatar-tuantuan.css" not in styles
    assert "width: calc(232px * var(--sprite-scale, 1))" in styles
    assert "height: calc(212px * var(--sprite-scale, 1))" in styles
    assert '#sprite-root[data-sprite-hidden="true"]' in styles
    assert "position: fixed" in styles
    assert "calc(var(--z-modal) + 1)" in styles
    assert ".afs-sprite-orb" in styles
    assert ".afs-sprite-grip" in styles
    assert ".afs-sprite-settings" in sprite_styles
    assert ".afs-sprite-size-button" in sprite_styles
    assert "--sprite-scale" in sprite_styles
    assert ".afs-sprite-avatar" in sprite_styles
    assert ".sprite-story-orbit" in sprite_styles
    assert ".sprite-tuantuan-cat" in sprite_styles
    assert ".sprite-cat-body" in sprite_styles
    assert ".sprite-cat-face" in sprite_styles
    assert ".sprite-cat-resting-silhouette" in sprite_styles
    assert ".sprite-cat-rear-paw" in sprite_styles
    assert ".sprite-cat-back-glow" in sprite_styles
    assert ".sprite-cat-eye" in sprite_styles
    assert ".sprite-cat-pupil" in sprite_styles
    assert ".sprite-cat-ear-rim" in sprite_styles
    assert ".sprite-cat-face-ridge" in sprite_styles
    assert ".sprite-cat-eye-shine" in sprite_styles
    assert ".sprite-cat-outline" in sprite_styles
    assert ".sprite-cat-tabby-mark" in sprite_styles
    assert ".sprite-cat-ground-glow" in sprite_styles
    assert ".sprite-cat-inner-ear" in sprite_styles
    assert ".sprite-cat-face-mark" in sprite_styles
    assert ".sprite-cat-whiskers" in sprite_styles
    assert ".sprite-cat-nose" in sprite_styles
    assert ".sprite-cat-story-panel" in sprite_styles
    assert ".sprite-cat-sprout" in sprite_styles
    assert ".sprite-tail-panel" in sprite_styles
    assert ".sprite-suggestion-bubble" in sprite_styles
    assert ".sprite-move-handle" in sprite_styles
    assert ".sprite-move-handle::after" in sprite_styles
    assert ".sprite-drag-halo" in sprite_styles
    assert ".sprite-agent-sequence" in sprite_styles
    assert ".sprite-tuantuan-shadow" in sprite_styles
    assert "TuanTuan story-cat agent projection" in avatar_story_cat_styles
    assert "Observe > Suggest > Execute" in avatar_story_cat_styles
    assert '[data-sprite-state="observe"]' in sprite_styles
    assert '[data-sprite-state="suggest"]' in sprite_styles
    assert '[data-sprite-state="execute"]' in sprite_styles
    assert '[data-sprite-state="complete"]' in sprite_styles
    assert '[data-sprite-state="sleep"]' in sprite_styles
    assert "--sprite-shift-x" in avatar_story_cat_styles
    assert "--sprite-shift-y" in avatar_story_cat_styles
    assert "--sprite-tilt-deg" in avatar_story_cat_styles
    assert "--sprite-shadow-scale" in avatar_story_cat_styles
    assert "translate3d(var(--sprite-shift-x), var(--sprite-shift-y), 0)" in avatar_story_cat_styles
    assert "@keyframes tuantuan-orbit" in sprite_styles
    assert '[data-sprite-motion="execute"]' in sprite_styles
    assert '[data-sprite-motion="success"]' in sprite_styles
    assert "mascot skin" not in sprite_styles
    assert 'content: ""' in sprite_styles
    assert "@media (prefers-reduced-motion: reduce)" in sprite_styles
