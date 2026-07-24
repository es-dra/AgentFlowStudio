from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import textwrap

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_cache_identity import CACHE_IDENTITY_SCHEMA_VERSION
from studio_static_helpers import STUDIO_ROOT


def _run_node(script: str) -> None:
    subprocess.run(
        ["node", "--input-type=module", "-e", textwrap.dedent(script)],
        check=True,
    )


def test_project_identity_gate_blocks_mutations_before_fetch() -> None:
    _run_node(
        """
        import {
          beginProjectIdentityLoad,
          blockProjectIdentity,
          commitProjectIdentity,
        } from "./apps/studio/src/project-identity-gate.js";
        import { createRuntimeClient } from "./apps/studio/src/runtime-client.js";

        const storage = new Map();
        let fetchCount = 0;
        globalThis.localStorage = {
          getItem: (key) => storage.get(key) || null,
          setItem: (key, value) => storage.set(key, String(value)),
          removeItem: (key) => storage.delete(key),
        };
        globalThis.window = {
          location: {
            protocol: "http:",
            href: "http://127.0.0.1:8794/studio/?project=project-b",
            search: "?project=project-b",
          },
          localStorage: globalThis.localStorage,
          dispatchEvent: () => {},
        };
        globalThis.fetch = async () => {
          fetchCount += 1;
          return new Response(JSON.stringify({ ok: true }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        };

        const runtimeB = createRuntimeClient("project-b");
        await runtimeB.confirmAssetBibleCommand({ command: "lock" })
          .then(() => { throw new Error("uninitialized identity sent a mutation"); })
          .catch((error) => {
            if (error.errorCode !== "project_identity_not_ready") throw error;
          });
        if (fetchCount !== 0) throw new Error(`uninitialized mutation reached fetch: ${fetchCount}`);
        beginProjectIdentityLoad("project-b", "account-12");
        await runtimeB.confirmAssetBibleCommand({ command: "lock" })
          .then(() => { throw new Error("loading identity sent a mutation"); })
          .catch((error) => {
            if (error.errorCode !== "project_identity_not_ready") throw error;
          });
        if (fetchCount !== 0) throw new Error(`loading mutation reached fetch: ${fetchCount}`);

        blockProjectIdentity("project-b", { accountId: "account-12", reason: "project_access_denied" });
        await runtimeB.previewAssetBibleCommand({ command: "preview" })
          .then(() => { throw new Error("blocked identity sent a preview POST"); })
          .catch((error) => {
            if (error.errorCode !== "project_identity_not_ready") throw error;
          });
        if (fetchCount !== 0) throw new Error(`blocked mutation reached fetch: ${fetchCount}`);
        await runtimeB.createProject({
          project_id: "project-new",
          project_type: "studio_creator_authoring",
          goal: "blocked create",
        }).then(() => {
          throw new Error("blocked identity created a project");
        }).catch((error) => {
          if (error.errorCode !== "project_identity_not_ready") throw error;
        });
        if (fetchCount !== 0) throw new Error(`blocked project creation reached fetch: ${fetchCount}`);

        commitProjectIdentity({ projectId: "project-b", accountId: "account-12" });
        await runtimeB.confirmAssetBibleCommand({ command: "lock" });
        if (fetchCount !== 1) throw new Error(`ready mutation did not reach fetch exactly once: ${fetchCount}`);

        window.location.search = "?project=project-a";
        await runtimeB.confirmAssetBibleCommand({ command: "lock" })
          .then(() => { throw new Error("live URL drift sent a mutation"); })
          .catch((error) => {
            if (error.errorCode !== "project_identity_not_ready") throw error;
          });
        if (fetchCount !== 1) throw new Error(`URL drift changed fetch count: ${fetchCount}`);
        window.location.search = "?project=project-b";

        const runtimeA = createRuntimeClient("project-a");
        await runtimeA.confirmAssetBibleCommand({ command: "lock" })
          .then(() => { throw new Error("cross-project mutation reached fetch"); })
          .catch((error) => {
            if (error.errorCode !== "project_identity_not_ready") throw error;
          });
        if (fetchCount !== 1) throw new Error(`cross-project mutation changed fetch count: ${fetchCount}`);

        commitProjectIdentity({
          projectId: "project-b",
          accountId: "account-12",
          cacheProjectId: "project-b",
          readOnly: true,
        });
        await runtimeB.confirmAssetBibleCommand({ command: "lock" })
          .then(() => { throw new Error("read-only cache sent a mutation"); })
          .catch((error) => {
            if (error.errorCode !== "project_cache_read_only") throw error;
          });
        if (fetchCount !== 1) throw new Error(`read-only cache changed fetch count: ${fetchCount}`);
        """
    )


def test_store_prepares_only_exact_account_project_cache_and_never_foreign_fallback() -> None:
    _run_node(
        """
        import { createStore } from "./apps/studio/src/store.js";
        import { prepareIdentityStorage } from "./apps/studio/src/store-persistence.js";
        import { canonicalStudioCacheJson } from "./apps/studio/src/studio-cache-attestation.js";
        import { webcrypto } from "node:crypto";

        const storage = new Map();
        globalThis.crypto = webcrypto;
        globalThis.localStorage = {
          get length() { return storage.size; },
          key: (index) => [...storage.keys()][index] || null,
          getItem: (key) => storage.get(key) || null,
          setItem: (key, value) => storage.set(key, String(value)),
          removeItem: (key) => storage.delete(key),
        };
        globalThis.window = { dispatchEvent: () => {}, localStorage: globalThis.localStorage };
        prepareIdentityStorage("account-12");
        const token = "test-session-token-account-12";
        storage.set("afs_auth_session_token", token);
        const trustedState = {
          meta: {
            projectId: "project-b",
            projectName: "Trusted project B",
            canvasName: "Canvas",
            seq: 1,
            updated_at: "2026-07-24T00:00:00Z",
          },
          viewport: { x: 0, y: 0, scale: 1 },
          nodes: { b: { id: "b", type: "text", title: "B fact" } },
          edges: {},
          order: ["b"],
          assets: [],
          assetBible: {},
          production: {},
        };
        const stateSha = await digest(canonicalStudioCacheJson(trustedState));
        const message = [
          "afs.studio_cache_identity.v0.1",
          "account-12",
          "project-b",
          "studio_state:v1",
          stateSha,
        ].join("\\u001f");
        const key = await crypto.subtle.importKey(
          "raw",
          new TextEncoder().encode(token),
          { name: "HMAC", hash: "SHA-256" },
          false,
          ["sign"],
        );
        const proof = hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message)));
        const cacheIdentity = {
          schema_version: "afs.studio_cache_identity.v0.1",
          account_id: "account-12",
          project_id: "project-b",
          state_version: "studio_state:v1",
          state_sha256: stateSha,
          proof,
        };
        const trustedKey = "afs_studio_trusted_cache_v1:project-b";
        storage.set(trustedKey, JSON.stringify({
          schema_version: "afs_studio_trusted_cache.v1",
          identity: { account_id: "account-12", project_id: "project-b" },
          cache_identity: cacheIdentity,
          state: trustedState,
        }));

        const networkError = new Error("offline");
        networkError.status = 0;
        networkError.errorCode = "network_connection_interrupted";
        const exactStore = createStore("project-b", { deferProjectLoad: true });
        const exact = await exactStore.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw networkError; },
        }, { accountId: "account-12" });
        if (exact.source !== "trusted_cache" || !exact.readOnly || !exact.state.nodes.b) {
          throw new Error(`exact cache was not admitted read-only: ${JSON.stringify(exact)}`);
        }

        const forged = JSON.parse(storage.get(trustedKey));
        forged.identity.account_id = "account-11";
        storage.set(trustedKey, JSON.stringify(forged));
        const wrongAccountStore = createStore("project-b", { deferProjectLoad: true });
        const wrongAccount = await wrongAccountStore.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw networkError; },
        }, { accountId: "account-12" });
        if (wrongAccount.status !== "blocked" || Object.keys(wrongAccountStore.get().nodes).length) {
          throw new Error("wrong-account cache did not fail closed");
        }

        storage.set(trustedKey, JSON.stringify({
          schema_version: "afs_studio_trusted_cache.v1",
          identity: { account_id: "account-12", project_id: "project-a" },
          cache_identity: cacheIdentity,
          state: forged.state,
        }));
        const wrongProjectStore = createStore("project-b", { deferProjectLoad: true });
        const wrongProject = await wrongProjectStore.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw networkError; },
        }, { accountId: "account-12" });
        if (wrongProject.status !== "blocked") throw new Error("wrong-project cache did not fail closed");

        const tampered = {
          schema_version: "afs_studio_trusted_cache.v1",
          identity: { account_id: "account-12", project_id: "project-b" },
          cache_identity: cacheIdentity,
          state: structuredClone(trustedState),
        };
        tampered.state.nodes.b.title = "Forged B fact";
        storage.set(trustedKey, JSON.stringify(tampered));
        const tamperedStore = createStore("project-b", { deferProjectLoad: true });
        const tamperedResult = await tamperedStore.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw networkError; },
        }, { accountId: "account-12" });
        if (tamperedResult.status !== "blocked" || Object.keys(tamperedStore.get().nodes).length) {
          throw new Error("state content tamper did not fail closed");
        }

        const denied = new Error("denied");
        denied.status = 403;
        denied.errorCode = "project_access_denied";
        const deniedStore = createStore("project-b", { deferProjectLoad: true });
        const deniedResult = await deniedStore.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw denied; },
        }, { accountId: "account-12" });
        if (deniedResult.status !== "blocked" || deniedResult.reason !== "project_access_denied") {
          throw new Error("403 did not fail closed");
        }
        if (Object.keys(deniedStore.get().nodes).length) throw new Error("403 exposed cached facts");

        async function digest(value) {
          return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
        }
        function hex(value) {
          return [...new Uint8Array(value)].map((item) => item.toString(16).padStart(2, "0")).join("");
        }
        """
    )


def test_store_rejects_wrong_runtime_project_identity_and_preserves_old_state_until_commit() -> None:
    _run_node(
        """
        import { createStore } from "./apps/studio/src/store.js";

        const storage = new Map();
        globalThis.localStorage = {
          get length() { return storage.size; },
          key: (index) => [...storage.keys()][index] || null,
          getItem: (key) => storage.get(key) || null,
          setItem: (key, value) => storage.set(key, String(value)),
          removeItem: (key) => storage.delete(key),
        };
        globalThis.window = { dispatchEvent: () => {} };

        const store = createStore("project-a");
        store.set((state) => {
          state.meta.projectName = "Project A";
          state.nodes.a = { id: "a", type: "text", title: "A fact" };
          state.order = ["a"];
        });
        let resolveLoad;
        const pending = store.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => new Promise((resolve) => { resolveLoad = resolve; }),
        });
        if (!store.get().nodes.a || store.get().meta.projectId !== "project-a") {
          throw new Error("candidate load mutated the visible project before validation");
        }
        await Promise.resolve();
        resolveLoad({
          project_id: "project-a",
          source: "runtime",
          state: { meta: { projectId: "project-a" }, nodes: { a: { id: "a" } }, order: ["a"] },
        });
        const prepared = await pending;
        if (prepared.status !== "blocked" || prepared.reason !== "project_identity_mismatch") {
          throw new Error(`wrong response identity was admitted: ${JSON.stringify(prepared)}`);
        }
        if (!store.get().nodes.a || store.get().meta.projectId !== "project-a") {
          throw new Error("failed candidate load mutated the old project");
        }
        """
    )


def test_store_rejects_missing_ids_404_and_stale_transition_commit() -> None:
    _run_node(
        """
        import { createStore } from "./apps/studio/src/store.js";

        const storage = new Map();
        globalThis.localStorage = {
          get length() { return storage.size; },
          key: (index) => [...storage.keys()][index] || null,
          getItem: (key) => storage.get(key) || null,
          setItem: (key, value) => storage.set(key, String(value)),
          removeItem: (key) => storage.delete(key),
        };
        globalThis.window = { dispatchEvent: () => {} };

        const store = createStore("project-a");
        store.set((state) => {
          state.meta.projectName = "Project A";
          state.nodes.a = { id: "a", type: "text", title: "A fact" };
          state.order = ["a"];
        });
        const missingOuter = await store.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => ({
            source: "runtime",
            state: { meta: { projectId: "project-b" }, nodes: {}, order: [] },
          }),
        });
        if (missingOuter.reason !== "project_identity_mismatch") {
          throw new Error("missing response project_id was admitted");
        }
        const missingState = await store.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => ({
            project_id: "project-b",
            source: "runtime",
            state: { meta: {}, nodes: {}, order: [] },
          }),
        });
        if (missingState.reason !== "project_identity_mismatch") {
          throw new Error("missing state projectId was admitted");
        }

        const notFound = new Error("not found");
        notFound.status = 404;
        notFound.errorCode = "project_not_found";
        const absent = await store.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => { throw notFound; },
        });
        if (absent.reason !== "project_not_found") throw new Error("404 was not classified");

        const prepared = await store.prepareProject("project-b", {
          projectId: "project-b",
          loadStudioState: async () => ({
            project_id: "project-b",
            source: "runtime",
            state_version: "studio_state:v2",
            state: {
              meta: { projectId: "project-b", projectName: "Project B" },
              nodes: { b: { id: "b", type: "text", title: "B fact" } },
              edges: {},
              order: ["b"],
            },
          }),
        });
        if (!prepared.state.ui || !prepared.state.selection || !Array.isArray(prepared.state.selection.nodeIds)) {
          throw new Error("prepared project omitted transient UI or selection defaults");
        }
        const committed = await store.commitPreparedProject(prepared, {
          projectId: "project-b",
        }, { isCurrent: () => false });
        if (committed !== false) throw new Error("stale transition reported a commit");
        if (!store.get().nodes.a || store.get().nodes.b || store.get().meta.projectId !== "project-a") {
          throw new Error("stale transition replaced the visible project");
        }
        """
    )


def test_project_controller_and_shell_contract_forbid_automatic_recovery() -> None:
    controller = (STUDIO_ROOT / "src" / "studio-project-controller.js").read_text(encoding="utf-8")
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    runtime = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")

    assert "projectSummaries.find((item) => item.project_id)" not in controller
    assert "没有自动切换到其他项目" in shell
    assert "选择其他项目" in shell
    assert "agentChatContexts.clear()" in shell
    assert "assertProjectRequestIdentity(route, method, payload)" in runtime
    assert "bindProjectHistoryNavigation" in main


def test_stale_runtime_asset_result_cannot_write_into_new_project() -> None:
    _run_node(
        """
        import { syncRuntimeAssets } from "./apps/studio/src/runtime-asset-sync.js";

        let resolveImages;
        let current = true;
        let mutations = 0;
        const state = { assets: [] };
        const store = {
          get: () => state,
          set: (mutator) => {
            mutations += 1;
            mutator(state);
          },
        };
        const pending = syncRuntimeAssets(store, {
          projectId: "project-b",
          listImageAssets: async () => new Promise((resolve) => { resolveImages = resolve; }),
          listVisualAssets: async () => ({ assets: [] }),
        }, { isCurrent: () => current });
        await Promise.resolve();
        current = false;
        resolveImages({ assets: [{ asset_id: "foreign-a", filename: "A asset" }] });
        const result = await pending;
        if (result.skipped !== "stale_project_transition") throw new Error("stale sync was not classified");
        if (mutations !== 0 || state.assets.length) throw new Error("stale sync mutated the new project");
        """
    )


def test_runtime_issues_account_project_state_bound_cache_attestation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = client.post(
        "/auth/register",
        json={
            "email": "identity-cache@example.com",
            "password": "strong-password-123",
            "display_name": "Identity Cache",
            "invite_code": "",
        },
    )
    assert registered.status_code == 200
    session_token = registered.json()["session_token"]
    account_id = registered.json()["user"]["user_id"]
    headers = {"Authorization": f"Bearer {session_token}"}
    project_id = "identity-cache-project"
    created = client.post(
        "/projects",
        headers=headers,
        json={"project_id": project_id, "project_type": "studio_creator_authoring", "goal": "Identity cache"},
    )
    assert created.status_code == 200
    state = {
        "meta": {
            "projectId": project_id,
            "projectName": "Identity cache",
            "canvasName": "Canvas",
            "seq": 1,
            "updated_at": "2026-07-24T00:00:00Z",
        },
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {"text_1": {"id": "text_1", "type": "text", "title": "Identity fact"}},
        "edges": {},
        "order": ["text_1"],
        "assets": [],
        "assetBible": {},
        "production": {},
    }
    saved = client.put(f"/projects/{project_id}/studio-state", headers=headers, json={"state": state})
    assert saved.status_code == 200
    loaded = client.get(f"/projects/{project_id}/studio-state", headers=headers)
    assert loaded.status_code == 200
    payload = loaded.json()
    assert payload["project_id"] == project_id
    assert payload["state"]["meta"]["projectId"] == project_id
    attestation = payload["cache_identity"]
    assert attestation["schema_version"] == CACHE_IDENTITY_SCHEMA_VERSION
    assert attestation["account_id"] == account_id
    assert attestation["project_id"] == project_id
    canonical = json.dumps(
        _canonical_value(payload["state"]),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == attestation["state_sha256"]
    message = "\x1f".join((
        CACHE_IDENTITY_SCHEMA_VERSION,
        account_id,
        project_id,
        attestation["state_version"],
        attestation["state_sha256"],
    ))
    expected = hmac.new(session_token.encode(), message.encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, attestation["proof"])
    serialized = json.dumps(attestation)
    assert session_token not in serialized
    assert "authorization" not in serialized.lower()


def _canonical_value(value):
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
