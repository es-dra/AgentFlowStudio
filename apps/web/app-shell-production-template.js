export function productionShellTemplate() {
  return String.raw`      <section class="production-workbench" id="production-workbench" hidden>
        <aside class="workflow-rail" aria-label="production path">
          <section class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Production Path</p>
                <h2>生产路径</h2>
              </div>
              <span class="chip">local bridge</span>
            </div>
            <ol id="production-path" class="production-path" aria-label="Local Alpha 0.4 operator loop">
              <li>输入准备</li>
              <li>生成 workflow_plan.json</li>
              <li>运行 workflow</li>
              <li>artifact inspection</li>
              <li>刷新验收报告</li>
              <li>feedback capture</li>
            </ol>
          </section>

          <section class="panel">
            <div class="panel-heading">
              <h2>工作流选择</h2>
              <span class="chip">workflows/*.yaml</span>
            </div>
            <div class="workflow-quick-actions" aria-label="workflow quick start">
              <button id="quick-demo-button" class="ghost-button" type="button">本机演示</button>
              <button id="product-workflow-button" class="ghost-button" type="button">完整成品</button>
            </div>
            <div id="workflow-profile" class="muted-box workflow-profile">
              等待本机 bridge 返回 workflow profile。
            </div>
            <form class="production-form" id="production-form">
              <label>
                <span>Workflow</span>
                <select id="workflow-select"></select>
              </label>
              <label>
                <span>Input file</span>
                <input id="workflow-input-path" type="text" value="data/processed/local_alpha_0_4/video_script_local_asr_input.json" />
              </label>
              <label>
                <span>Output directory</span>
                <input id="workflow-output-dir" type="text" value="data/processed/runs/local_alpha_0_4_product_loop" />
              </label>
              <div class="action-row">
                <button id="create-plan-button" class="ghost-button" type="button">生成计划</button>
                <button id="run-workflow-button" class="primary-import" type="button">运行流程</button>
              </div>
              <button id="refresh-review-button" class="ghost-button" type="button">刷新验收报告</button>
            </form>
          </section>
        </aside>

        <section class="content-stage">
          <section class="panel production-readiness" id="production-readiness" aria-labelledby="production-readiness-title">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Production Readiness</p>
                <h2 id="production-readiness-title">生产准备</h2>
              </div>
              <span class="chip">preflight</span>
            </div>
            <div id="readiness-checklist" class="readiness-grid"></div>
          </section>

          <section class="panel production-acceptance" id="production-acceptance-path" aria-labelledby="production-acceptance-title">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Acceptance Path</p>
                <h2 id="production-acceptance-title">Local Alpha 0.4 operator loop</h2>
              </div>
              <span id="production-next-action" class="chip">等待 bridge</span>
            </div>
            <ol class="acceptance-steps">
              <li>先连 bridge，再生成计划</li>
              <li>确认输入和本机依赖后运行 workflow</li>
              <li>运行完成后检查 artifact timeline 和成片预览</li>
              <li>artifact inspection 后刷新验收报告</li>
              <li>feedback capture：生成 run_feedback_event JSON，只复制不写入。</li>
            </ol>
            <div id="acceptance-path-detail" class="muted-box acceptance-path-detail">
              Production Mode 不保存浏览器状态；验收证据来自本机 run artifacts、inspect/review/package report。
            </div>
            <div id="operator-loop-status" class="muted-box operator-loop-status">
              Local Alpha 0.4 operator loop waits for local input setup, workflow selection, artifact inspection, review refresh, and feedback capture.
            </div>
          </section>

          <section class="stage-intro panel">
            <div>
              <p class="eyebrow">Supervised Production Workspace</p>
              <h2>当前任务、下一步、阻塞项和可交付物在一个任务台里看清楚。</h2>
              <p class="stage-subtitle">
                浏览器只连接本机 bridge。执行仍由 NarratoCut CLI 和 workflow engine 完成；用户在这里选择 workflow、生成计划、启动本地运行、查看步骤和进入验收。
              </p>
            </div>
          </section>

          <section class="panel" aria-labelledby="production-current-title">
            <div class="panel-heading">
              <h2 id="production-current-title">当前任务</h2>
              <span id="bridge-health" class="chip">bridge unknown</span>
            </div>
            <div id="production-overview" class="summary-grid"></div>
          </section>

          <section class="panel" aria-labelledby="step-timeline-title">
            <div class="panel-heading">
              <h2 id="step-timeline-title">步骤时间线</h2>
              <span class="chip">Step Trace</span>
            </div>
            <div id="step-timeline" class="step-timeline"></div>
          </section>

          <section class="panel" id="production-video-review" aria-labelledby="production-video-review-title">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Video Review</p>
                <h2 id="production-video-review-title">成片审看</h2>
              </div>
              <span class="chip">显式选择视频</span>
            </div>
            <div class="production-video-grid">
              <div id="production-video-preview" class="video-preview muted-box">
                选择本地视频文件后，这里会用于成片审看；不会自动读取 manifest 路径。
              </div>
              <div id="production-asset-match" class="stack muted-box">
                运行后会显示 final video、subtitle、cover、BGM 等 asset 提示；文件名匹配时会标记“可能对应最终成片”。
              </div>
            </div>
          </section>

          <section class="panel" aria-labelledby="artifact-timeline-title">
            <div class="panel-heading">
              <h2 id="artifact-timeline-title">Artifact Timeline</h2>
              <span class="chip">files</span>
            </div>
            <div id="production-artifacts" class="summary-grid"></div>
          </section>
        </section>

        <aside class="review-rail" aria-label="production supervisor">
          <section class="panel">
            <div class="panel-heading">
              <h2>监督栏</h2>
              <span class="chip">human gate</span>
            </div>
            <div id="supervision-panel" class="stack"></div>
            <div id="supervision-actions" class="supervision-actions">
              <button class="ghost-button" type="button" data-supervision="continue">确认继续</button>
              <button class="ghost-button" type="button" data-supervision="pause">记录暂停意见</button>
              <button class="ghost-button" type="button" data-supervision="rerun_step">记录重跑建议</button>
              <button class="ghost-button" type="button" data-supervision="needs_changes">记录修改意见</button>
            </div>
          </section>

          <section class="panel" id="run-feedback-panel" aria-labelledby="run-feedback-title">
            <div class="panel-heading">
              <h2 id="run-feedback-title">生产反馈</h2>
              <span class="chip">run-level JSON</span>
            </div>
            <form class="feedback-form" id="run-feedback-form">
              <label>
                <span>验收结论</span>
                <select id="run-feedback-decision">
                  <option value="approved">approved</option>
                  <option value="needs_changes">needs_changes</option>
                  <option value="blocked">blocked</option>
                </select>
              </label>
              <label>
                <span>风险分类</span>
                <select id="run-feedback-risk">
                  <option value="production_readiness">production_readiness</option>
                  <option value="content_quality">content_quality</option>
                  <option value="video_review">video_review</option>
                  <option value="delivery_readiness">delivery_readiness</option>
                </select>
              </label>
              <label>
                <span>视频时间点（秒，可选）</span>
                <input id="run-feedback-time" type="number" min="0" step="0.1" inputmode="decimal" />
              </label>
              <label class="feedback-note-field">
                <span>生产备注</span>
                <textarea id="run-feedback-note" rows="4"></textarea>
              </label>
              <button id="run-feedback-copy" class="ghost-button feedback-copy" type="button">生成并复制 run feedback JSON</button>
            </form>
            <textarea id="run-feedback-output" class="feedback-output" rows="4" readonly></textarea>
            <p id="run-feedback-status" class="meta">只复制 JSON，不写 feedback.jsonl，不上传。</p>
          </section>

          <section class="panel">
            <div class="panel-heading">
              <h2>执行日志</h2>
              <span class="chip">local stdout</span>
            </div>
            <pre id="production-log" class="log-output">等待连接本机 bridge。</pre>
          </section>
        </aside>
      </section>`;
}
