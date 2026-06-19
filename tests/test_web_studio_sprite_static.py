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
    avatar_mascot_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-mascot.css").read_text(encoding="utf-8")
    avatar_tuantuan_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-tuantuan.css").read_text(encoding="utf-8")
    sprite_styles = styles + avatar_styles + avatar_motion_styles + avatar_mascot_styles + avatar_tuantuan_styles
    pose_assets = {
        "idle": STUDIO_ROOT / "assets" / "tuantuan-idle.png",
        "happy": STUDIO_ROOT / "assets" / "tuantuan-happy.png",
        "curious": STUDIO_ROOT / "assets" / "tuantuan-curious.png",
        "thinking": STUDIO_ROOT / "assets" / "tuantuan-thinking.png",
        "surprised": STUDIO_ROOT / "assets" / "tuantuan-surprised.png",
        "sleepy": STUDIO_ROOT / "assets" / "tuantuan-sleepy.png",
        "working": STUDIO_ROOT / "assets" / "tuantuan-working.png",
        "celebrate": STUDIO_ROOT / "assets" / "tuantuan-celebrate.png",
    }
    mascot_asset = STUDIO_ROOT / "assets" / "tuantuan-mascot.png"

    assert '<div id="sprite-root"></div>' in index
    assert './styles/studio-sprite.css' in index
    assert 'from "./sprite-widget.js"' in main
    assert "renderSpriteWidget" in main
    assert "spriteChat(payload)" in runtime_client
    assert "/sprite/chat" in runtime_client
    for asset in pose_assets.values():
        assert asset.exists(), asset
        assert asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert asset.stat().st_size > 100_000
    assert mascot_asset.exists()
    assert mascot_asset.read_bytes() == pose_assets["idle"].read_bytes()
    assert "afs-sprite" in sprite
    assert 'from "./sprite-position.js"' in sprite
    assert 'from "./sprite-character.js"' in sprite
    assert 'from "./sprite-motion.js"' in sprite
    assert "AFS 小精灵" in sprite
    assert "data-sprite-draggable" in sprite
    assert 'data-sprite-role", "movable-companion"' in sprite
    assert 'data-sprite-character", "mascot"' in sprite
    assert "bindSpriteMotion" in sprite
    assert "setSpriteMotionMode" in sprite
    assert "pulseSpriteMotion" in sprite
    assert "bindSpritePoseTicker" in sprite
    assert "currentSpritePose" in sprite
    assert "setTemporarySpritePose" in sprite
    assert "data-sprite-pose" in sprite
    assert "sprite-tuantuan-stage" in sprite
    assert "sprite-tuantuan-asset" in character
    assert "spritePoseImages()" in sprite
    for pose in pose_assets:
        assert f"./assets/tuantuan-{pose}.png" in character
    assert 'data-pose="${pose}"' in character
    assert "Object.entries(SPRITE_POSE_ASSETS)" in character
    assert "IDLE_SPRITE_POSES" in character
    assert "spriteIdlePoseIndex" in character
    assert "draggable=\"false\"" in character
    assert "sprite-move-handle" in sprite
    assert "sprite-grab-ribbon" in sprite
    assert "sprite-mascot-tag" in sprite
    assert "团团" in sprite
    assert "runtime.spriteChat" in sprite
    assert "data-sprite-drag-handle" in sprite
    assert 'data-sprite-drag-handle="true"' in sprite
    assert "spriteSettingsPanel" in sprite
    assert "contextmenu" in sprite
    assert "setSpriteScale" in sprite
    assert "getSpriteScale" in sprite
    assert "data-sprite-settings" in sprite
    assert "startSpriteDrag" in sprite
    assert "nudgeSpritePosition" in sprite
    assert "rememberSpritePositionFromRoot" in sprite
    assert 'button.addEventListener("keydown", nudgeSpritePosition)' in sprite
    assert "handleSpriteDrag" in sprite
    assert "__afsStudio" not in sprite
    assert "provider raw" not in sprite
    assert len(sprite.splitlines()) <= 300
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
    assert "2026-06-tuantuan-raster-v1" in position
    assert "SPRITE_SIZE = 190" in position
    assert "const SPRITE_HEIGHT = 238" in position
    assert "SPRITE_SCALE_KEY" in position
    assert "SPRITE_SCALE_OPTIONS" in position
    assert "getSpriteScale" in position
    assert "setSpriteScale" in position
    assert "safeDefaultSpritePosition" in position
    assert "captureSpritePointer" in position
    assert "setPointerCapture" in position
    assert "storeSpritePosition" in position
    assert "clampSpritePosition" in position
    assert len(position.splitlines()) <= 300

    assert '@import url("./studio-sprite-avatar.css");' in styles
    assert '@import url("./studio-sprite-avatar-motion.css");' in styles
    assert '@import url("./studio-sprite-avatar-mascot.css");' in styles
    assert '@import url("./studio-sprite-avatar-tuantuan.css");' in styles
    assert "width: calc(190px * var(--sprite-scale, 1))" in styles
    assert "height: calc(238px * var(--sprite-scale, 1))" in styles
    assert "position: fixed" in styles
    assert "calc(var(--z-modal) + 1)" in styles
    assert ".afs-sprite-orb" in styles
    assert ".afs-sprite-grip" in styles
    assert ".afs-sprite-settings" in sprite_styles
    assert ".afs-sprite-size-button" in sprite_styles
    assert "--sprite-scale" in sprite_styles
    assert ".afs-sprite-avatar" in sprite_styles
    assert ".sprite-tuantuan-stage" in sprite_styles
    assert ".sprite-tuantuan-asset" in sprite_styles
    assert ".sprite-move-handle" in sprite_styles
    assert ".sprite-move-handle::after" in sprite_styles
    assert ".sprite-drag-halo" in sprite_styles
    assert ".sprite-grab-ribbon" in sprite_styles
    assert ".sprite-mascot-tag" in sprite_styles
    assert ".sprite-mascot-shadow" in sprite_styles
    assert "Multi-pose raster TuanTuan mascot skin" in avatar_mascot_styles
    assert "CSS reconstruction" in avatar_mascot_styles
    assert "TuanTuan reference asset layer" in avatar_tuantuan_styles
    assert '[data-sprite-pose="idle"]' in avatar_mascot_styles
    assert '[data-sprite-pose="working"]' in avatar_mascot_styles
    assert '[data-sprite-pose="celebrate"]' in avatar_mascot_styles
    assert "--sprite-shift-x" in avatar_mascot_styles
    assert "--sprite-shift-y" in avatar_mascot_styles
    assert "--sprite-tilt-deg" in avatar_mascot_styles
    assert "--sprite-shadow-scale" in avatar_mascot_styles
    assert "translate3d(var(--sprite-shift-x), var(--sprite-shift-y), 0)" in avatar_mascot_styles
    assert '[data-sprite-motion="working"]' in avatar_mascot_styles
    assert '[data-sprite-motion="success"]' in avatar_mascot_styles
    assert 'content: ""' in avatar_mascot_styles
    assert "@media (prefers-reduced-motion: reduce)" in sprite_styles
