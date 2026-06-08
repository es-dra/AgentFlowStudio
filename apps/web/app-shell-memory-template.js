export function memoryShellTemplate() {
  return String.raw`      <section class="memory-workbench" id="memory-workbench" hidden>
        <section class="memory-studio-header" aria-labelledby="memory-studio-title">
          <div>
            <p class="eyebrow">AgentFlow Studio Canvas</p>
            <h2 id="memory-studio-title">一张画布串起剧本、资产、记忆、生成与反馈。</h2>
            <p>
              参考 RHTV、LibTV 这类画布工具的低摩擦操作，但核心不做复杂剪辑；AgentFlow 的特色是把证据链、记忆来源、双路对比和下一轮复用放在同一个生产台里。
            </p>
          </div>
          <div class="memory-studio-status" aria-label="memory studio status">
            <article>
              <span>Canvas mode</span>
              <strong>Evidence-first</strong>
            </article>
            <article>
              <span>Operator path</span>
              <strong>Load -> Compare -> Feedback</strong>
            </article>
            <article>
              <span>Runtime boundary</span>
              <strong>Local read-only</strong>
            </article>
          </div>
        </section>
        <aside class="workflow-rail" aria-label="memory project">
          <section class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Memory Workbench</p>
                <h2>项目与资产</h2>
              </div>
              <span class="chip">local canvas</span>
            </div>
            <div class="memory-load-actions">
              <label class="memory-primary-action" for="artifact-files">选择 Memory JSON</label>
            </div>
            <div id="memory-source-status" class="memory-source-status"></div>
            <div id="memory-project-summary" class="memory-project-summary"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>Evidence Bundle</h2>
              <span class="chip">explicit files</span>
            </div>
            <div id="memory-bundle-summary" class="memory-bundle-summary"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>Artifact Inspector</h2>
              <span class="chip">read-only</span>
            </div>
            <div id="memory-artifact-inspector" class="memory-artifact-inspector"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>资产准备</h2>
              <span class="chip">Assets</span>
            </div>
            <div id="memory-asset-summary" class="memory-asset-summary"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>状态标签</h2>
              <span class="chip">states</span>
            </div>
            <div id="memory-state-strip" class="memory-state-strip"></div>
          </section>
        </aside>

        <section class="memory-canvas-shell">
          <section class="memory-hero panel">
            <div>
              <p class="eyebrow">Memory Production Canvas</p>
              <h2>同一剧本下，比较普通提示词和记忆架构复用的生产路径。</h2>
              <p class="stage-subtitle">
                操作员只需要装载一组协议或样例包，就能看到角色资产、场景约束、Baseline、Memory-backed run、评审、反馈和下一轮复用如何连接。
              </p>
            </div>
            <div id="memory-focus-summary" class="memory-focus-summary" aria-live="polite"></div>
          </section>
          <section class="memory-toolbar panel" aria-label="memory canvas tools">
            <div>
              <p class="eyebrow">Canvas Tools</p>
              <strong>画布视图</strong>
            </div>
            <div class="memory-view-toggle" role="group" aria-label="memory canvas view">
              <button class="memory-view-button active" type="button" data-memory-view="flow">Flow</button>
              <button class="memory-view-button" type="button" data-memory-view="compare">Compare</button>
              <button class="memory-view-button" type="button" data-memory-view="review">Review</button>
            </div>
          </section>
          <section class="panel memory-operator-panel" aria-labelledby="memory-operator-dock-title">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Operator Command Dock</p>
                <h2 id="memory-operator-dock-title">Brief -> Assets -> Memory -> Generate -> Compare -> Feedback</h2>
              </div>
              <span class="chip">local controls</span>
            </div>
            <div id="memory-operator-dock" class="memory-operator-dock"></div>
          </section>
          <section class="panel memory-action-panel" aria-labelledby="memory-action-title">
            <div class="panel-heading">
              <h2 id="memory-action-title">Workflow Actions</h2>
              <span class="chip">read-only</span>
            </div>
            <div id="memory-action-strip" class="memory-action-strip"></div>
          </section>
          <section class="memory-canvas" aria-label="memory canvas">
            <div class="memory-canvas-caption">
              <span>Evidence Canvas</span>
              <strong>节点只负责聚焦证据，不启动模型、不写入记忆。</strong>
            </div>
            <div id="memory-canvas-stage" class="memory-canvas-stage"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>Experiment Protocol</h2>
              <span class="chip">fairness</span>
            </div>
            <div id="memory-protocol-summary" class="memory-protocol-summary"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>Baseline / Memory 双路径</h2>
              <span class="chip">comparison</span>
            </div>
            <div id="memory-lane-grid" class="memory-lane-grid"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <h2>Run Timeline</h2>
              <span class="chip">feedback loop</span>
            </div>
            <div id="memory-run-timeline" class="memory-run-timeline"></div>
          </section>
        </section>

        <aside class="review-rail" aria-label="memory provenance">
          <section class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Memory Loaded</p>
                <h2>来源与复用</h2>
              </div>
              <span class="chip">provenance</span>
            </div>
            <div id="memory-provenance-panel" class="memory-provenance-panel"></div>
          </section>
          <section class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Feedback Draft</p>
                <h2>Next-pass note</h2>
              </div>
              <span class="chip">copy JSON</span>
            </div>
            <div id="memory-feedback-preview" class="memory-feedback-preview"></div>
            <textarea id="memory-feedback-output" class="memory-feedback-output" rows="10" readonly></textarea>
            <button id="memory-feedback-copy" class="ghost-button memory-feedback-copy" type="button">Copy draft JSON</button>
            <p id="memory-feedback-status" class="meta">Select a memory package before copying.</p>
          </section>
        </aside>
      </section>`;
}
