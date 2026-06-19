from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def test_studio_sprite_widget_is_wired_to_runtime_chat() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    sprite = (STUDIO_ROOT / "src" / "sprite-widget.js").read_text(encoding="utf-8")
    position = (STUDIO_ROOT / "src" / "sprite-position.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "studio-sprite.css").read_text(encoding="utf-8")
    avatar_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar.css").read_text(encoding="utf-8")
    avatar_character_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-character.css").read_text(encoding="utf-8")
    avatar_parts_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-parts.css").read_text(encoding="utf-8")
    avatar_motion_styles = (STUDIO_ROOT / "styles" / "studio-sprite-avatar-motion.css").read_text(encoding="utf-8")
    sprite_styles = styles + avatar_styles + avatar_character_styles + avatar_parts_styles + avatar_motion_styles

    assert '<div id="sprite-root"></div>' in index
    assert './styles/studio-sprite.css' in index
    assert 'from "./sprite-widget.js"' in main
    assert "renderSpriteWidget" in main
    assert "spriteChat(payload)" in runtime_client
    assert "/sprite/chat" in runtime_client
    assert "afs-sprite" in sprite
    assert 'from "./sprite-position.js"' in sprite
    assert "AFS 小精灵" in sprite
    assert "data-sprite-draggable" in sprite
    assert "sprite-character-shell" in sprite
    assert "sprite-move-handle" in sprite
    assert "sprite-ear left" in sprite
    assert "sprite-ear right" in sprite
    assert "sprite-scarf" in sprite
    assert "sprite-drag-chip" in sprite
    assert "sprite-hood" in sprite
    assert "sprite-eye left" in sprite
    assert "sprite-eye right" in sprite
    assert "sprite-torso-panel" in sprite
    assert "sprite-nameplate" in sprite
    assert 'data-sprite-role", "movable-companion"' in sprite
    assert "runtime.spriteChat" in sprite
    assert "SPRITE_POSITION_KEY" in position
    assert "SPRITE_SIZE" in position
    assert "startSpriteDrag" in sprite
    assert "nudgeSpritePosition" in sprite
    assert "rememberSpritePositionFromRoot" in sprite
    assert 'button.addEventListener("keydown", nudgeSpritePosition)' in sprite
    assert "handleSpriteDrag" in sprite
    assert "captureSpritePointer" in position
    assert "setPointerCapture" in position
    assert "storeSpritePosition" in position
    assert "clampSpritePosition" in position
    assert len(sprite.splitlines()) <= 300
    assert len(position.splitlines()) <= 300
    assert "data-dock" not in sprite
    assert "root.dataset.dock" in position
    assert "root.dataset.vertical" in position
    assert "__afsStudio" not in sprite
    assert "provider raw" not in sprite
    assert '@import url("./studio-sprite-avatar.css");' in styles
    assert '@import url("./studio-sprite-avatar-character.css");' in styles
    assert '@import url("./studio-sprite-avatar-parts.css");' in styles
    assert '@import url("./studio-sprite-avatar-motion.css");' in styles
    assert "position: fixed" in styles
    assert "calc(var(--z-modal) + 1)" in styles
    assert ".afs-sprite-orb" in styles
    assert ".afs-sprite-grip" in styles
    assert ".afs-sprite-avatar" in sprite_styles
    assert ".sprite-character-shell" in sprite_styles
    assert ".sprite-move-handle" in sprite_styles
    assert ".sprite-ear.left" in sprite_styles
    assert ".sprite-scarf" in sprite_styles
    assert ".sprite-drag-halo" in sprite_styles
    assert ".sprite-drag-chip" in sprite_styles
    assert ".sprite-dock-ring" in sprite_styles
    assert ".sprite-backplate" in sprite_styles
    assert ".sprite-tail-fin" in sprite_styles
    assert ".sprite-cockpit" in sprite_styles
    assert ".sprite-canopy" in sprite_styles
    assert ".sprite-head-shell" in sprite_styles
    assert ".sprite-body" in sprite_styles
    assert ".sprite-shoulder.left" in sprite_styles
    assert ".sprite-arm.left" in sprite_styles
    assert ".sprite-hand.left" in sprite_styles
    assert ".sprite-mitten.left" in sprite_styles
    assert ".sprite-face" in sprite_styles
    assert ".sprite-visor" in sprite_styles
    assert ".sprite-cheek.left" in sprite_styles
    assert ".sprite-mouth" in sprite_styles
    assert ".sprite-eye-glow" in sprite_styles
    assert ".sprite-hood" in sprite_styles
    assert ".sprite-eye.left" in sprite_styles
    assert ".sprite-torso-panel" in sprite_styles
    assert ".sprite-nameplate" in sprite_styles
    assert ".sprite-move-handle::after" in sprite_styles
    assert ".sprite-status-light" in sprite_styles
    assert ".sprite-core" in sprite_styles
    assert ".sprite-thruster" in sprite_styles
    assert ".sprite-glow-trail" in sprite_styles
    assert "#sprite-root.is-dragging .sprite-thruster" in sprite_styles
    assert ".sprite-wing.left" in sprite_styles
    assert ".sprite-foot.left" in sprite_styles
    assert "#sprite-root[data-dock=\"left\"] .afs-sprite-panel" in styles
    assert "#sprite-root[data-vertical=\"top\"] .afs-sprite-panel" in styles
    assert "data-sprite-drag-handle" in sprite
    assert ".afs-sprite.open .sprite-status-light" in sprite_styles
    assert "@media (prefers-reduced-motion: reduce)" in sprite_styles
