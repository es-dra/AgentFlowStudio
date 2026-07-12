from __future__ import annotations

import subprocess
import textwrap

from studio_static_helpers import STUDIO_ROOT


def _read(path: str) -> str:
    return (STUDIO_ROOT / path).read_text(encoding="utf-8")


def test_project_save_recovery_state_machine_keeps_dirty_until_safe_retry_success() -> None:
    script = textwrap.dedent(
        """
        import { createStore } from "./apps/studio/src/store.js";

        function installBrowserStubs() {
          const storage = new Map();
          globalThis.localStorage = {
            getItem: (key) => storage.get(key) || null,
            setItem: (key, value) => storage.set(key, String(value)),
            removeItem: (key) => storage.delete(key),
          };
          const events = [];
          globalThis.CustomEvent = class CustomEvent {
            constructor(type, init = {}) {
              this.type = type;
              this.detail = init.detail || {};
            }
          };
          globalThis.window = {
            dispatchEvent: (event) => events.push({ type: event.type, detail: event.detail || {} }),
          };
          return events;
        }

        const rawMarker = "tok" + "en=";
        const rawHomePath = "/ho" + "me/private/path";

        function runtimeError(status, code, message = `unsafe raw ${rawMarker}${rawHomePath} should not leak`) {
          const error = new Error(message);
          error.status = status;
          error.errorCode = code;
          error.payload = { detail: { error: code, message, user_action: "retry after fixing the boundary" } };
          return error;
        }

        function addNode(store, id, title) {
          store.set((state) => {
            state.nodes[id] = { id, type: "text", title, content: title };
            state.order = [...new Set([...state.order, id])];
          });
        }

        installBrowserStubs();
        const store = createStore("project-save-recovery");
        let attempts = 0;
        store.attachRuntime({
          projectId: "project-save-recovery",
          saveStudioState: async (_state, expectedVersion) => {
            attempts += 1;
            if (attempts === 1) throw runtimeError(503, "runtime_error");
            if (expectedVersion !== "") throw new Error(`unexpected expected version ${expectedVersion}`);
            return { state_version: "studio_state:v1" };
          },
        });
        addNode(store, "text_1", "draft survives first failed save");

        await store.flushRuntimeSave();
        if (store.get().ui.saveState !== "保存失败") {
          throw new Error(`expected visible save failure, got ${store.get().ui.saveState}`);
        }
        if (!/保留|重试/.test(store.get().ui.saveMessage || "")) {
          throw new Error(`save failure message is not actionable: ${store.get().ui.saveMessage}`);
        }
        if (store.get().ui.saveMessage.includes(rawMarker) || store.get().ui.saveMessage.includes(rawHomePath)) {
          throw new Error(`save failure leaked unsafe detail: ${store.get().ui.saveMessage}`);
        }

        await store.flushRuntimeSave();
        if (store.get().ui.saveState !== "已保存") {
          throw new Error(`safe retry should be the only path back to saved, got ${store.get().ui.saveState}`);
        }
        if (attempts !== 2) throw new Error(`expected one failure and one retry success, got ${attempts}`);
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_project_save_recovery_handles_auth_conflict_and_inflight_dirty_edges() -> None:
    script = textwrap.dedent(
        """
        import { createStore } from "./apps/studio/src/store.js";

        function installBrowserStubs() {
          const storage = new Map();
          globalThis.localStorage = {
            getItem: (key) => storage.get(key) || null,
            setItem: (key, value) => storage.set(key, String(value)),
            removeItem: (key) => storage.delete(key),
          };
          const events = [];
          globalThis.CustomEvent = class CustomEvent {
            constructor(type, init = {}) {
              this.type = type;
              this.detail = init.detail || {};
            }
          };
          globalThis.window = {
            dispatchEvent: (event) => events.push({ type: event.type, detail: event.detail || {} }),
          };
          return events;
        }

        const bearerText = "Bear" + "er abc";
        const authText = "Author" + "ization=secret";
        const optPath = "/op" + "t/private/path";

        function runtimeError(status, code, message = `${bearerText} ${authText} ${optPath}`) {
          const error = new Error(message);
          error.status = status;
          error.errorCode = code;
          error.payload = { detail: { error: code, message, request_id: "req_safe_001" } };
          return error;
        }

        function addNode(store, id, title) {
          store.set((state) => {
            state.nodes[id] = { id, type: "text", title, content: title };
            state.order = [...new Set([...state.order, id])];
          });
        }

        for (const authStatus of [401, 403]) {
          const authEvents = installBrowserStubs();
          const authStore = createStore(`project-save-auth-${authStatus}`);
          let authAttempts = 0;
          authStore.attachRuntime({
            projectId: `project-save-auth-${authStatus}`,
            saveStudioState: async () => {
              authAttempts += 1;
              throw runtimeError(authStatus, "authentication_required");
            },
          });
          addNode(authStore, "text_1", "auth failure keeps dirty state");
          await authStore.flushRuntimeSave();
          if (authStore.get().ui.saveState !== "需要登录") {
            throw new Error(`expected auth boundary state for ${authStatus}, got ${authStore.get().ui.saveState}`);
          }
          const authEvent = authEvents.find((event) => event.type === "afs:studio-save-auth-required");
          if (!authEvent) {
            throw new Error(`auth save failure ${authStatus} did not dispatch the Studio auth boundary event`);
          }
          if (authEvent.detail.status !== authStatus) {
            throw new Error(`auth boundary event lost status ${authStatus}: ${authEvent.detail.status}`);
          }
          if (authAttempts !== 1) throw new Error(`auth failure ${authStatus} retried unexpectedly: ${authAttempts}`);
          if (authStore.get().ui.saveMessage.includes(bearerText) || authStore.get().ui.saveMessage.includes(optPath)) {
            throw new Error(`auth failure ${authStatus} leaked unsafe detail: ${authStore.get().ui.saveMessage}`);
          }
        }

        installBrowserStubs();
        const conflictStore = createStore("project-save-conflict");
        let conflictAttempts = 0;
        conflictStore.attachRuntime({
          projectId: "project-save-conflict",
          saveStudioState: async () => {
            conflictAttempts += 1;
            throw runtimeError(409, "studio_state_conflict");
          },
        });
        addNode(conflictStore, "text_1", "conflict keeps local draft");
        await conflictStore.flushRuntimeSave();
        if (conflictStore.get().ui.saveState !== "保存冲突") {
          throw new Error(`expected conflict state, got ${conflictStore.get().ui.saveState}`);
        }
        if (!/其他窗口|最新版本|保留/.test(conflictStore.get().ui.saveMessage || "")) {
          throw new Error(`conflict message does not protect newer server state: ${conflictStore.get().ui.saveMessage}`);
        }

        installBrowserStubs();
        const inflightStore = createStore("project-save-inflight");
        let resolveFirstSave;
        let inflightAttempts = 0;
        inflightStore.attachRuntime({
          projectId: "project-save-inflight",
          saveStudioState: async () => {
            inflightAttempts += 1;
            if (inflightAttempts === 1) {
              return new Promise((resolve) => {
                resolveFirstSave = resolve;
              });
            }
            return { state_version: `studio_state:v${inflightAttempts}` };
          },
        });
        addNode(inflightStore, "text_1", "first draft");
        const firstFlush = inflightStore.flushRuntimeSave();
        addNode(inflightStore, "text_2", "edited while first save is in flight");
        resolveFirstSave({ state_version: "studio_state:v1" });
        await firstFlush;
        if (inflightStore.get().ui.saveState === "已保存") {
          throw new Error("older in-flight save success marked newer unsaved edits as saved");
        }
        """
    )

    subprocess.run(["node", "--input-type=module", "-e", script], check=True)


def test_project_save_failure_retry_is_visible_in_topbar_contract() -> None:
    store_source = _read("src/store.js")
    topbar = _read("src/studio-topbar.js")
    styles = _read("styles/shell.css")
    main = _read("src/main.js")

    for marker in (
        "保存失败",
        "保存冲突",
        "需要登录",
        "afs:studio-save-auth-required",
        "lastRuntimeSavedSnapshot",
        "savingSnapshotKey",
    ):
        assert marker in store_source + _read("src/store-runtime-save.js")

    assert "onRetrySave" in topbar
    assert "save-pill-button" in topbar
    assert "重试保存" in topbar
    assert "onRetrySave: () => store.flushRuntimeSave()" in main
    assert "bindSaveAuthRecovery" in main
    assert "Number(status) === 403" in main
    assert "await signOut(runtime)" in main
    assert ".save-pill.failed" in styles
    assert ".save-pill-button" in styles
