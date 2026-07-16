from __future__ import annotations

import subprocess
from pathlib import Path


STUDIO = Path("apps/studio")


def test_secure_entry_is_the_only_pre_auth_dom_and_mount_happens_after_identity_check() -> None:
    index = (STUDIO / "index.html").read_text(encoding="utf-8")
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")

    assert 'id="secure-entry"' in index
    assert 'id="overlay-root"' in index
    for forbidden in ('id="canvas-root"', 'id="node-layer"', 'id="drawer"', 'id="inspector"', 'id="product-shell-root"'):
        assert forbidden not in index
    assert main.index("await ensureAuthSession(authRuntime)") < main.index("mountStudioDom()")
    assert main.index("prepareIdentityStorage(") < main.index("mountStudioDom()")
    assert "app.replaceChildren();" in bootstrap
    assert "showSecureEntry(\"正在安全退出…\")" in main
    assert "showSecureEntry(\"登录已过期，请重新登录后继续。\")" in main


def test_identity_change_logout_and_session_expiry_clear_every_project_surface() -> None:
    persistence = (STUDIO / "src" / "store-persistence.js").read_text(encoding="utf-8")
    store = (STUDIO / "src" / "store.js").read_text(encoding="utf-8")
    session = (STUDIO / "src" / "studio-project-session.js").read_text(encoding="utf-8")
    runtime = (STUDIO / "src" / "runtime-client.js").read_text(encoding="utf-8")
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")

    assert 'key.startsWith("afs_studio_")' in persistence
    assert "previous !== nextIdentity" in persistence
    assert "resetIdentityState" in store
    for marker in ("state.nodes = {};", "state.edges = {};", "state.assets = [];", "state.selection = { nodeIds: [], edgeId: null };"):
        assert marker in store
    assert "clearProjectSession" in session
    assert 'url.searchParams.delete("project")' in session
    assert 'new CustomEvent("afs:auth-session-expired"' in runtime
    assert "clearIdentityScopedStudioState();" in main
    assert "app.replaceChildren();" in bootstrap


def test_teardown_disables_editor_rendering_before_store_notification_and_topbar_is_null_safe() -> None:
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    for start, end in (("async function handleSignOut()", "async function recoverExpiredSession()"), ("async function recoverExpiredSession()", "async function refreshRuntimeSurfaceStatus")):
        segment = main[main.index(start):main.index(end)]
        assert segment.index("editorMounted = false;") < segment.index("store?.resetIdentityState?.();")
    assert "if (!editorMounted) return;" in main

    script = """
globalThis.document = { getElementById: () => null };
const { renderTopbar } = await import('./apps/studio/src/studio-topbar.js');
renderTopbar({});
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
    )
