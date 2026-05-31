export function reviewShellTemplate() {
  return String.raw`      <header class="topbar">
        <div class="brand">
          <span class="brand-mark">NC</span>
          <div>
            <p class="eyebrow" data-copy="brandKicker">内容生产验收</p>
            <h1 data-copy="brandName">NarratoCut 本地验收台</h1>
          </div>
        </div>

        <section class="topbar-metrics stat-strip" aria-label="artifact metrics">
          <article>
            <span data-copy="statArtifactsLabel">已选文件</span>
            <strong id="stat-artifacts">0 项</strong>
          </article>
          <article>
            <span data-copy="statKnownLabel">参与验收</span>
            <strong id="stat-known">0 项</strong>
          </article>
          <article>
            <span data-copy="statWarningsLabel">风险提示</span>
            <strong id="stat-warnings">0 项</strong>
          </article>
          <article>
            <span data-copy="statErrorsLabel">解析错误</span>
            <strong id="stat-errors">0 项</strong>
          </article>
        </section>

        <div class="topbar-actions">
          <div id="overall-status" class="status-card status-unknown">
            <span id="overall-status-label">交付状态</span>
            <strong id="overall-status-value">未知 unknown</strong>
          </div>
          <button id="language-toggle" class="ghost-button" type="button">English</button>
          <div class="mode-toggle" aria-label="Workbench mode">
            <button id="mode-review" class="mode-button active" type="button">验收</button>
            <button id="mode-production" class="mode-button" type="button">生产</button>
            <button id="mode-memory" class="mode-button" type="button">Memory</button>
          </div>
          <label class="primary-import" for="artifact-files">
            <span data-copy="importButton">选择验收文件</span>
            <input
              id="artifact-files"
              class="file-input"
              type="file"
              multiple
              accept=".json,.md,.mp4,.webm,.mov,application/json,text/markdown,text/plain,video/mp4,video/webm,video/quicktime"
            />
          </label>
        </div>
      </header>

      <section class="boundary-strip" aria-label="local boundary">
        <span data-copy="boundaryUpload">不上传</span>
        <span data-copy="boundaryBackend">不执行后端</span>
        <span data-copy="boundaryPersistence">不持久化</span>
        <span data-copy="boundaryScanning">不扫描目录</span>
        <span data-copy="boundaryManifest">不自动读取 manifest 路径</span>
      </section>

      <section class="workbench" id="review-workbench">
        <aside class="workflow-rail" aria-label="review workflow">
          <section class="panel workflow-panel" aria-labelledby="workflow-title">
            <p class="eyebrow" data-copy="workflowKicker">Review Flow</p>
            <h2 id="workflow-title" data-copy="workflowTitle">验收路径</h2>
            <nav class="review-nav" aria-label="review sections">
              <a href="#summary-panel" data-copy="navOverview">交付总览</a>
              <a href="#video-preview-panel" data-copy="navVideo">视频预览</a>
              <a href="#asset-ledger-panel" data-copy="navAssets">资产核对</a>
              <a href="#risk-ledger-panel" data-copy="navRisks">风险处理</a>
              <a href="#report-preview" data-copy="navReports">报告审阅</a>
              <a href="#contract-inspector" data-copy="navContract">合同检查</a>
            </nav>
          </section>

          <section class="panel" id="recommended-artifacts" aria-labelledby="recommended-title">
            <div class="panel-heading">
              <h2 id="recommended-title" data-copy="recommendedTitle">推荐文件组</h2>
              <span class="chip" data-copy="localChip">local files</span>
            </div>
            <div class="file-groups">
              <article>
                <h3 data-copy="packageGroupTitle">交付包</h3>
                <p>run_manifest.json</p>
                <p>finished_package_manifest.json</p>
                <p>quality_report.json</p>
                <p>review_report.json</p>
                <p>package_report.md</p>
              </article>
              <article>
                <h3 data-copy="evidenceGroupTitle">上游证据</h3>
                <p>clip_plan.json</p>
                <p>real_slice_manifest.json</p>
                <p>final_video_manifest.json</p>
                <p>subtitle_manifest.json</p>
                <p>highlight_score_report.json</p>
              </article>
              <article>
                <h3 data-copy="handoffGroupTitle">交付门禁</h3>
                <p>delivery_readiness.json</p>
                <p>delivery_readiness.md</p>
              </article>
            </div>
          </section>
        </aside>

        <section class="content-stage">
          <section class="stage-intro panel" aria-labelledby="stage-title">
            <div>
              <p class="eyebrow" data-copy="stageKicker">Local Review Workbench</p>
              <h2 id="stage-title" data-copy="stageTitle">先看成品能否交付，再看证据和风险。</h2>
              <p class="stage-subtitle" data-copy="stageSubtitle">
                这里不会启动工作流。请先用 CLI 产出 NarratoCut artifacts，再把需要审查的 JSON、Markdown 和视频文件选入本页。
              </p>
            </div>
          </section>

          <section class="panel" id="summary-panel" aria-labelledby="summary-title">
            <div class="panel-heading">
              <h2 id="summary-title" data-copy="summaryTitle">交付总览</h2>
              <span class="chip" data-copy="summaryChip">acceptance</span>
            </div>
            <div id="summary-content" class="summary-grid"></div>
          </section>

          <section class="panel" id="video-preview-panel" aria-labelledby="video-preview-title">
            <div class="panel-heading">
              <h2 id="video-preview-title" data-copy="videoPreviewTitle">视频预览</h2>
              <span class="chip" data-copy="videoChip">explicit file only</span>
            </div>
            <div id="video-preview-content" class="video-preview muted-box">
              只预览你主动选择的 mp4 / webm / mov 文件，不跟随 manifest 路径。
            </div>
          </section>

          <section class="panel" id="asset-ledger-panel" aria-labelledby="asset-ledger-title">
            <div class="panel-heading">
              <h2 id="asset-ledger-title" data-copy="assetLedgerTitle">资产核对</h2>
              <span class="chip" data-copy="assetChip">assets</span>
            </div>
            <div id="asset-ledger-content" class="summary-grid"></div>
          </section>

          <section class="panel" id="report-preview" aria-labelledby="report-title">
            <div class="panel-heading">
              <h2 id="report-title" data-copy="reportTitle">报告审阅</h2>
              <span class="chip" data-copy="escapedChip">escaped text</span>
            </div>
            <div id="report-tabs" class="report-tabs" hidden></div>
            <pre id="report-content" class="report-text">Markdown 报告会以安全文本方式展示。请选择 package_report.md 或 delivery_readiness.md。</pre>
          </section>
        </section>

        <aside class="review-rail" aria-label="review inspector">
          <section class="panel" id="risk-ledger-panel" aria-labelledby="risk-ledger-title">
            <div class="panel-heading">
              <h2 id="risk-ledger-title" data-copy="riskLedgerTitle">风险处理</h2>
              <span class="chip" data-copy="riskChip">risk</span>
            </div>
            <div id="risk-ledger-content" class="stack"></div>
          </section>

          <section class="panel" id="inspector-panel" aria-labelledby="inspector-title">
            <div class="panel-heading">
              <h2 id="inspector-title" data-copy="inspectorTitle">审查 Inspector</h2>
              <span class="chip" data-copy="checksChip">checks</span>
            </div>
            <div id="inspector-content" class="stack"></div>
          </section>

          <section class="panel" id="evidence-map-panel" aria-labelledby="evidence-map-title">
            <div class="panel-heading">
              <h2 id="evidence-map-title" data-copy="evidenceMapTitle">证据链</h2>
              <span class="chip" data-copy="lineageChip">lineage</span>
            </div>
            <div id="evidence-map-content" class="stack"></div>
          </section>

          <section class="panel" id="contract-inspector" aria-labelledby="contract-inspector-title">
            <div class="panel-heading">
              <h2 id="contract-inspector-title" data-copy="contractInspectorTitle">Contract Inspector</h2>
              <span id="artifact-count" class="count">0</span>
            </div>
            <div id="artifact-inventory" aria-labelledby="contract-inspector-title">
              <div id="inventory-list" class="stack muted-box">
                选择本地 artifact 后，这里会显示文件名、合同类型、schema_version 和解析状态。
              </div>
            </div>
          </section>

          <section class="panel" id="feedback-panel" aria-labelledby="feedback-title">
            <div class="panel-heading">
              <div>
                <p class="eyebrow" data-copy="feedbackKicker">M2 local copy</p>
                <h2 id="feedback-title" data-copy="feedbackTitle">反馈事件复制</h2>
              </div>
              <span class="chip" data-copy="feedbackChip">copy JSON</span>
            </div>
            <p class="meta feedback-intro" data-copy="feedbackBody">
              生成 feedback_event JSON 并复制，不写本地文件、不上传。
            </p>
            <form id="feedback-form" class="feedback-form">
              <label>
                <span data-copy="feedbackArtifactLabel">关联 artifact</span>
                <select id="feedback-artifact"></select>
              </label>
              <label>
                <span data-copy="feedbackDecisionLabel">验收结论</span>
                <select id="feedback-decision">
                  <option value="approved">approved</option>
                  <option value="needs_changes">needs_changes</option>
                  <option value="blocked">blocked</option>
                </select>
              </label>
              <label>
                <span data-copy="feedbackRiskLabel">风险分类</span>
                <select id="feedback-risk">
                  <option value="general_review">general_review</option>
                  <option value="artifact_contract">artifact_contract</option>
                  <option value="content_quality">content_quality</option>
                  <option value="delivery_readiness">delivery_readiness</option>
                </select>
              </label>
              <label>
                <span data-copy="feedbackTimeLabel">视频时间点（秒，可选）</span>
                <input id="feedback-time" type="number" min="0" step="0.1" inputmode="decimal" />
              </label>
              <label class="feedback-note-field">
                <span data-copy="feedbackNoteLabel">审查备注</span>
                <textarea id="feedback-note" rows="4"></textarea>
              </label>
              <button id="feedback-copy" class="ghost-button feedback-copy" type="button" data-copy="feedbackCopyButton">生成并复制 JSON</button>
            </form>
            <textarea id="feedback-output" class="feedback-output" rows="4" readonly></textarea>
            <p id="feedback-status" class="meta" data-copy="feedbackFallbackHint">Clipboard 不可用时，可以从文本框手动复制。</p>
          </section>
        </aside>
      </section>`;
}
