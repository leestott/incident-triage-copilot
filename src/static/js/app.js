// ---------------------------------------------------------------------------
// Incident Triage Copilot — Frontend Logic
// ---------------------------------------------------------------------------
const API_BASE = window.location.origin;

// DOM refs
const form = document.getElementById('triage-form');
const queryInput = document.getElementById('query-input');
const contextInput = document.getElementById('context-input');
const submitBtn = document.getElementById('submit-btn');
const spinner = document.getElementById('spinner');
const btnText = document.getElementById('btn-text');
const resultsContainer = document.getElementById('results-container');
const resultsEmpty = document.getElementById('results-empty');
const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const modeText = document.getElementById('mode-text');
const mockBadge = document.getElementById('mock-badge');
const mockBanner = document.getElementById('mock-banner');

// State
let history = [];
let isProcessing = false;

// Pipeline steps
const pipelineSteps = ['receive', 'research', 'diagnostics', 'remediation', 'synthesize'];
const stepElements = {};
pipelineSteps.forEach(s => {
    stepElements[s] = {
        dot: document.getElementById(`step-${s}`),
        line: document.getElementById(`line-${s}`),
    };
});

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
// Configure marked
if (typeof marked !== 'undefined') {
    marked.use({
        breaks: true,
        gfm: true
    });
}

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        statusDot.classList.remove('offline');
        statusText.textContent = 'Online';
        if (data.mode === 'foundry') {
            modeText.textContent = 'Microsoft Foundry';
            mockBadge.style.display = 'none';
            mockBanner.style.display = 'none';
        } else {
            modeText.textContent = 'Local Mode';
            mockBadge.style.display = 'inline-block';
            mockBanner.style.display = 'block';
        }
    } catch {
        statusDot.classList.add('offline');
        statusText.textContent = 'Offline';
        modeText.textContent = 'Disconnected';
        mockBadge.style.display = 'none';
        mockBanner.style.display = 'none';
    }
}

// ---------------------------------------------------------------------------
// Pipeline animation
// ---------------------------------------------------------------------------
function resetPipeline() {
    pipelineSteps.forEach(s => {
        const el = stepElements[s];
        if (el.dot) { el.dot.className = 'step-dot waiting'; }
        if (el.line) { el.line.className = 'step-line'; }
    });
}

function activateStep(step) {
    const idx = pipelineSteps.indexOf(step);
    pipelineSteps.forEach((s, i) => {
        const el = stepElements[s];
        if (i < idx) {
            if (el.dot) el.dot.className = 'step-dot done';
            if (el.line) el.line.className = 'step-line done';
        } else if (i === idx) {
            if (el.dot) el.dot.className = 'step-dot active';
        } else {
            if (el.dot) el.dot.className = 'step-dot waiting';
            if (el.line) el.line.className = 'step-line';
        }
    });
}

function completePipeline() {
    pipelineSteps.forEach(s => {
        const el = stepElements[s];
        if (el.dot) el.dot.className = 'step-dot done';
        if (el.line) el.line.className = 'step-line done';
    });
}

// ---------------------------------------------------------------------------
// Submit triage request
// ---------------------------------------------------------------------------
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (isProcessing) return;

    const message = queryInput.value.trim();
    if (!message) return;

    let context = null;
    const ctxVal = contextInput.value.trim();
    if (ctxVal) {
        try {
            context = JSON.parse(ctxVal);
        } catch {
            alert('Context must be valid JSON. Example: {"log_data": "ERROR 500..."}');
            return;
        }
    }

    isProcessing = true;
    submitBtn.disabled = true;
    spinner.style.display = 'block';
    btnText.textContent = 'Triaging...';
    resultsEmpty.style.display = 'none';

    // Show loading skeleton
    resultsContainer.innerHTML = `
        <div class="card">
            <div class="card-header"><span class="icon">⏳</span> Processing Triage Request...</div>
            <div class="card-body">
                <div class="skeleton skeleton-line" style="width:90%"></div>
                <div class="skeleton skeleton-line" style="width:75%"></div>
                <div class="skeleton skeleton-line" style="width:85%"></div>
                <div class="skeleton skeleton-line" style="width:60%"></div>
            </div>
        </div>
    `;

    // Animate pipeline
    resetPipeline();
    activateStep('receive');

    const body = { message };
    if (context) body.context = context;

    // Simulate pipeline progression
    const pipelineTimer = setTimeout(() => activateStep('research'), 800);
    const pipelineTimer2 = setTimeout(() => activateStep('diagnostics'), 2500);
    const pipelineTimer3 = setTimeout(() => activateStep('remediation'), 4500);
    const pipelineTimer4 = setTimeout(() => activateStep('synthesize'), 6500);

    try {
        const res = await fetch(`${API_BASE}/triage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        clearTimeout(pipelineTimer);
        clearTimeout(pipelineTimer2);
        clearTimeout(pipelineTimer3);
        clearTimeout(pipelineTimer4);

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${res.status}`);
        }

        const data = await res.json();
        completePipeline();
        renderResult(data);
        addToHistory(message, data);
    } catch (err) {
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-header" style="color: var(--error);">
                    <span class="icon">❌</span> Triage Failed
                </div>
                <div class="card-body">
                    <p>${escapeHtml(err.message)}</p>
                    <p style="margin-top:0.75rem; color: var(--text-secondary); font-size: 0.8125rem;">
                        Check that the server is running and try again.
                    </p>
                </div>
            </div>
        `;
        resetPipeline();
    } finally {
        isProcessing = false;
        submitBtn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = 'Run Triage';
    }
});

// ---------------------------------------------------------------------------
// Render triage result
// ---------------------------------------------------------------------------
function renderResult(data) {
    const agentsHtml = data.results.map((r, i) => {
        const conf = r.confidence != null ? r.confidence : 0.7;
        const confPct = Math.round(conf * 100);
        const confClass = conf >= 0.7 ? 'high' : conf >= 0.4 ? 'medium' : 'low';
        const toolsHtml = r.tools_used.length
            ? `<div class="tools-used">${r.tools_used.map(t => `<span class="tool-tag">${escapeHtml(t)}</span>`).join('')}</div>`
            : '';

        return `
            <div class="agent-card">
                <div class="agent-card-header" onclick="toggleAgent(${i})">
                    <div class="agent-card-header-left">
                        <span class="agent-badge ${r.agent}">${agentIcon(r.agent)} ${r.agent}</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill ${confClass}" style="width: ${confPct}%"></div>
                        </div>
                        <span style="font-size:0.75rem; color: var(--text-secondary);">${confPct}%</span>
                    </div>
                    <span class="toggle-icon" id="toggle-${i}">▼</span>
                </div>
                <div class="agent-card-body ${i === 0 ? 'open' : ''}" id="agent-body-${i}">
                    <div class="markdown-body">${DOMPurify.sanitize(marked.parse(r.content || ''))}</div>
                    ${toolsHtml}
                </div>
            </div>
        `;
    }).join('');

    resultsContainer.innerHTML = `
        <div class="triage-result">
            <div class="card">
                <div class="card-header">
                    <span class="icon">📋</span> Triage Report
                </div>
                <div class="card-body">
                    <div class="result-meta">
                        <div class="meta-item">
                            <span>🔗</span>
                            <span class="value">${escapeHtml(data.correlation_id)}</span>
                        </div>
                        <div class="meta-item">
                            <span>🤖</span>
                            <span class="value">${data.specialists_invoked.length} agents</span>
                        </div>
                        <div class="meta-item">
                            <span>🔄</span>
                            <span class="value">${data.turn_count} turns</span>
                        </div>
                    </div>
                    <div class="summary-block markdown-body">${DOMPurify.sanitize(marked.parse(data.summary || ''))}</div>
                    <div class="agent-results">
                        ${agentsHtml}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Auto-open first agent
    const firstToggle = document.getElementById('toggle-0');
    if (firstToggle) firstToggle.classList.add('open');
}

function agentIcon(role) {
    const icons = { research: '🔍', diagnostics: '🔬', remediation: '🛠️', coordinator: '🎯' };
    return icons[role] || '🤖';
}

function toggleAgent(idx) {
    const body = document.getElementById(`agent-body-${idx}`);
    const icon = document.getElementById(`toggle-${idx}`);
    if (body && icon) {
        body.classList.toggle('open');
        icon.classList.toggle('open');
    }
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------
function addToHistory(query, data) {
    history.unshift({
        query,
        data,
        time: new Date(),
    });
    if (history.length > 20) history.pop();
    renderHistory();
}

function renderHistory() {
    if (history.length === 0) {
        historyEmpty.style.display = 'block';
        return;
    }
    historyEmpty.style.display = 'none';
    historyList.innerHTML = history.map((h, i) => `
        <div class="history-item" onclick="loadHistory(${i})">
            <div class="history-query">${escapeHtml(h.query)}</div>
            <div class="history-time">${timeAgo(h.time)}</div>
        </div>
    `).join('');
}

function loadHistory(idx) {
    const h = history[idx];
    if (!h) return;
    queryInput.value = h.query;
    renderResult(h.data);
    completePipeline();
    resultsEmpty.style.display = 'none';
}

function timeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
}

// ---------------------------------------------------------------------------
// Example chips
// ---------------------------------------------------------------------------
function useExample(text) {
    queryInput.value = text;
    queryInput.focus();
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
checkHealth();
setInterval(checkHealth, 30000);
