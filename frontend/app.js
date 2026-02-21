/* ============================================================
   CEREBRAS FACT CHECKER — app.js
   Split-panel layout, dark theme
   ============================================================ */

'use strict';

const API_BASE = '';

/* ── State ── */
let isChecking = false;
let checkHistory = JSON.parse(localStorage.getItem('fc_history') || '[]');
let usageData = null;
let isSuperuser = false;

/* ── DOM refs & Approach 1 Intercept ── */
const _origGetElementById = document.getElementById.bind(document);
document.getElementById = function (id) {
    if (window.innerWidth <= 900) {
        const mob = _origGetElementById(id + 'Mobile');
        if (mob) return mob;
    }
    return _origGetElementById(id);
};
const $ = id => document.getElementById(id);

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initTabs();
    initTextareaEnter();
    checkHealth();
    loadHistory();
    checkUsage();
    initSuperuser();
    initButtonClickAnim();
});

/* ============================================================
   GOLD PARTICLE CANVAS
   ============================================================ */
function initParticles() {
    // ── Canvas particles (full-page gold) ──────────────────
    const canvas = document.getElementById('goldCanvas');
    if (canvas) initCanvasParticles(canvas);

    // ── Legacy DOM particles (left panel accent) ────────────
    const container = $('particles');
    if (!container) return;
    for (let i = 0; i < 12; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.cssText = `
            left: ${Math.random() * 100}%;
            bottom: -10px;
            width: ${1 + Math.random() * 2}px;
            height: ${1 + Math.random() * 2}px;
            opacity: ${0.06 + Math.random() * 0.12};
            animation-duration: ${16 + Math.random() * 24}s;
            animation-delay: ${-(Math.random() * 32)}s;
        `;
        container.appendChild(p);
    }
}

function initCanvasParticles(canvas) {
    const ctx = canvas.getContext('2d');

    // Palette of gold tones
    const GOLD_COLORS = [
        'rgba(212,168,83,',   // warm gold
        'rgba(232,200,120,',  // light gold
        'rgba(184,146,46,',   // deep gold
        'rgba(255,215,100,',  // bright gold
        'rgba(200,155,60,',   // amber
    ];

    let W, H, particles;

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function createParticle() {
        const color = GOLD_COLORS[Math.floor(Math.random() * GOLD_COLORS.length)];
        const size = 0.6 + Math.random() * 2.8;
        return {
            x: Math.random() * W,
            y: H + size + Math.random() * H,   // start below viewport
            vx: (Math.random() - 0.5) * 0.35,   // gentle horizontal drift
            vy: -(0.35 + Math.random() * 0.9),  // upward speed
            size,
            color,
            alpha: 0.04 + Math.random() * 0.22,
            sway: Math.random() * Math.PI * 2,     // phase offset for sinusoidal sway
            swayAmp: 0.2 + Math.random() * 0.6,     // sway amplitude
            swaySpd: 0.008 + Math.random() * 0.018, // sway speed
            glow: size > 1.8,                      // larger particles get glow
        };
    }

    function init() {
        resize();
        // Spread particles across the full height so they don't all start from bottom
        particles = Array.from({ length: 70 }, () => {
            const p = createParticle();
            p.y = Math.random() * H;  // random initial y
            return p;
        });
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);

        for (const p of particles) {
            // Sinusoidal horizontal sway
            p.sway += p.swaySpd;
            p.x += p.vx + Math.sin(p.sway) * p.swayAmp;
            p.y += p.vy;

            // Recycle when off-screen top
            if (p.y < -p.size * 2) {
                Object.assign(p, createParticle());
                p.x = Math.random() * W;
            }
            // Wrap horizontal edges
            if (p.x < -10) p.x = W + 10;
            if (p.x > W + 10) p.x = -10;

            ctx.save();
            if (p.glow) {
                ctx.shadowColor = `${p.color}0.8)`;
                ctx.shadowBlur = p.size * 4;
            }
            ctx.globalAlpha = p.alpha;
            ctx.fillStyle = `${p.color}1)`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', () => {
        resize();
        // Re-spread particles on resize
        particles.forEach(p => { if (p.x > W) p.x = Math.random() * W; });
    });

    init();
    draw();
}


/* ============================================================
   TABS
   ============================================================ */
function initTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', e => {
            e.preventDefault();
            triggerHaptic('light');
            switchTab(tab.dataset.tab);
        });
    });
}

function switchTab(name) {
    // Update tabs
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));

    // Show/hide panels
    $('singleTab').style.display = name === 'single' ? '' : 'none';
    $('textTab').style.display = name === 'text' ? '' : 'none';

    // Update empty state text
    const emptySub = $('emptySub');
    if (emptySub) {
        if (name === 'text') {
            emptySub.innerHTML = 'Paste text on the left and hit <strong>Analyze Text</strong> to get started.';
        } else {
            emptySub.innerHTML = 'Enter a claim on the left and hit <strong>Verify Claim</strong> to get started.';
        }
    }

    // Clear results
    clearResults();
}

// Silent variant: switches the active tab UI without wiping the results panel
function switchTabSilent(name) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    $('singleTab').style.display = name === 'single' ? '' : 'none';
    $('textTab').style.display = name === 'text' ? '' : 'none';
}

/* ============================================================
   TEXTAREA ENTER KEY
   ============================================================ */
function initTextareaEnter() {
    $('claimInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleFactCheck();
        }
    });
    $('textInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleTextAnalysis();
        }
    });
}

/* ============================================================
   HEALTH CHECK
   ============================================================ */
async function checkHealth() {
    const statusEl = $('navStatus');
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
            statusEl.innerHTML = `<div class="status-dot connected"></div><span>Online</span>`;
        } else {
            statusEl.innerHTML = `<div class="status-dot error"></div><span>Degraded</span>`;
        }
    } catch {
        statusEl.innerHTML = `<div class="status-dot error"></div><span>Offline</span>`;
    }
}

/* ============================================================
   USAGE
   ============================================================ */
async function checkUsage() {
    try {
        const localUsed = localStorage.getItem('fc_used') || '0';
        const res = await fetch(`${API_BASE}/api/usage`, {
            headers: { 'X-Local-Used': localUsed }
        });
        if (!res.ok) return;
        const serverUsage = await res.json();

        let parsedLocal = parseInt(localUsed);
        if (serverUsage.used > parsedLocal) {
            localStorage.setItem('fc_used', serverUsage.used.toString());
        } else if (parsedLocal > serverUsage.used) {
            serverUsage.used = parsedLocal;
            serverUsage.remaining = Math.max(0, serverUsage.max - parsedLocal);
            serverUsage.limit_reached = serverUsage.used >= serverUsage.max;
        }

        usageData = serverUsage;
        renderUsageBadge();
    } catch { /* silent */ }
}

function renderUsageBadge() {
    const badges = [
        document.querySelector('#usageBadge'),
        document.querySelector('#usageBadgeMobile')
    ].filter(Boolean);

    if (!badges.length || !usageData) return;

    if (isSuperuser) {
        badges.forEach(b => {
            b.style.cssText = 'background:rgba(212,168,83,0.12);border:1px solid rgba(212,168,83,0.3);color:#d4a853;padding:4px 12px;border-radius:999px;font-size:0.75rem;font-weight:600;';
            b.innerHTML = '⚡ Superuser — Unlimited';
        });
        const btn = $('checkBtn');
        if (btn) btn.disabled = false;
        return;
    }

    const { used = 0, max = 5, remaining = 5 } = usageData;
    const pct = used / max;
    const color = pct >= 1 ? '#f87171' : pct >= 0.5 ? '#fbbf24' : '#4ade80';

    badges.forEach(b => {
        b.style.cssText = `background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08);color:${color};padding:4px 12px;border-radius:999px;font-size:0.75rem;font-weight:600;`;
        b.innerHTML = `${remaining} check${remaining === 1 ? '' : 's'} left`;
    });

    const btn = $('checkBtn');
    if (btn) btn.disabled = false;
}

/* ============================================================
   SUPERUSER
   ============================================================ */
function initSuperuser() {
    let seq = '';
    const code = 'superuser';
    document.addEventListener('keydown', e => {
        seq += e.key.toLowerCase();
        if (seq.length > code.length) seq = seq.slice(-code.length);
        if (seq === code) {
            isSuperuser = !isSuperuser;
            renderUsageBadge();
            showToast(isSuperuser ? '⚡ Superuser mode activated' : '🔒 Superuser mode deactivated');
        }
    });
}

/* ============================================================
   PROGRESS BAR
   ============================================================ */
function setProgress(pct) {
    const bar = $('progressBar');
    if (!bar) return;
    if (pct === null) {
        bar.classList.add('hidden');
        bar.style.width = '0%';
        return;
    }
    bar.classList.remove('hidden');
    bar.style.width = pct + '%';
}

/* ============================================================
   EXAMPLE CLAIMS
   ============================================================ */
function setExample(claim) {
    triggerHaptic('light');
    if (window.innerWidth <= 900) {
        // Mobile: populate mobile input and scroll up to it
        const mobileInput = _origGetElementById('claimInputMobile');
        if (mobileInput) {
            mobileInput.value = claim;
            updateCharCount('claimInputMobile', 'claimCounterMobile', 500);
            toggleClearBtn('claimInputMobile', 'clearClaimMobile');
            mobileInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            mobileInput.style.transition = 'border-color 0.3s';
            mobileInput.style.borderColor = 'var(--primary)';
            mobileInput.style.boxShadow = '0 0 0 3px rgba(212,168,83,0.25)';
            setTimeout(() => {
                mobileInput.style.borderColor = '';
                mobileInput.style.boxShadow = '';
            }, 1600);
        }
        return;
    }
    // Desktop: populate directly without clearing the results panel
    const input = $('claimInput');
    if (!input) return;
    switchTabSilent('single');
    input.value = claim;
    updateCharCount('claimInput', 'claimCounter', 500);
    toggleClearBtn('claimInput', 'clearClaim');
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
    input.focus();
    input.style.transition = 'border-color 0.3s, box-shadow 0.3s';
    input.style.borderColor = 'var(--primary)';
    input.style.boxShadow = '0 0 0 3px rgba(212,168,83,0.25)';
    setTimeout(() => {
        input.style.borderColor = '';
        input.style.boxShadow = '';
    }, 1600);
}


/* ============================================================
   FACT CHECK
   ============================================================ */
async function handleFactCheck() {
    if (isChecking) return;

    // Pre-flight: check if limit already reached
    if (!isSuperuser && usageData && usageData.remaining === 0) {
        const resultArea = $('resultArea');
        showEmptyState(false);
        showResultsClear(true);
        toggleMobileInputs(false);
        resultArea.innerHTML = renderLimitReached();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    const claim = $('claimInput')?.value?.trim();
    if (!claim) {
        shakeInput('claimInput');
        return;
    }
    if (claim.length > 500) {
        shakeInput('claimInput');
        return;
    }

    const reasoningEffort = $('reasoningEffort')?.value || 'medium';
    const numSources = parseInt($('numSources')?.value || '3');

    triggerHaptic('medium');
    setLoading('checkBtn', true);
    showEmptyState(true);
    setCubeProcessing(true, 'Scouring the internet...');
    showResultsClear(false);
    toggleMobileInputs(false);
    setProgress(10);

    const resultArea = $('resultArea');
    resultArea.innerHTML = '';
    setProgress(30);

    try {
        setProgress(50);
        setCubeStatus('Dissecting the evidence...');

        const res = await fetch(`${API_BASE}/api/fact-check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Local-Used': localStorage.getItem('fc_used') || '0',
                ...(isSuperuser ? { 'X-Superuser': 'cerebras2024' } : {})
            },
            body: JSON.stringify({ claim, reasoning_effort: reasoningEffort, num_sources: numSources })
        });

        setProgress(80);
        setCubeStatus('Rendering judgment...');

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            if (res.status === 429 || err.limit_reached) {
                await checkUsage();
                setCubeProcessing(false);
                showEmptyState(false);
                resultArea.innerHTML = renderLimitReached();
                setProgress(null);
                setLoading('checkBtn', false);
                isChecking = false;
                showResultsClear(true);
                return;
            }
            throw new Error(err.error || `Server error ${res.status}`);
        }

        const data = await res.json();
        setProgress(100);

        // Render result
        setTimeout(() => {
            setCubeProcessing(false);
            showEmptyState(false);
            resultArea.innerHTML = renderResultCard(data, claim);
            showResultsClear(true);
            addToHistory(claim, data.verdict);
            setProgress(null);

            if (data.verdict === 'TRUE') {
                triggerHaptic('success');
            } else if (data.verdict === 'FALSE') {
                triggerHaptic('heavy');
            } else {
                triggerHaptic('medium');
            }
        }, 300);

        await checkUsage();

    } catch (err) {
        setCubeProcessing(false);
        showEmptyState(false);
        setProgress(null);
        resultArea.innerHTML = renderError(err.message);
        showResultsClear(true);
    } finally {
        setLoading('checkBtn', false);
        isChecking = false;
    }
}

/* ============================================================
   TEXT ANALYSIS
   ============================================================ */
async function handleTextAnalysis() {
    if (isChecking) return;

    // Pre-flight: check if limit already reached
    if (!isSuperuser && usageData && usageData.remaining === 0) {
        const textResultArea = $('textResultArea');
        showEmptyState(false);
        showResultsClear(true);
        toggleMobileInputs(false);
        textResultArea.innerHTML = renderLimitReached();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    const text = $('textInput')?.value?.trim();
    if (!text) {
        shakeInput('textInput');
        return;
    }
    if (text.length > 5000) {
        shakeInput('textInput');
        return;
    }

    const maxClaims = parseInt($('maxClaims')?.value || '6');
    const numSources = parseInt($('textNumSources')?.value || '3');
    const reasoningEffort = $('textReasoningEffort')?.value || 'medium';

    setLoading('analyzeBtn', true);
    showEmptyState(true);
    setCubeProcessing(true, 'Decoding your text...');
    showResultsClear(false);
    toggleMobileInputs(false);
    setProgress(10);

    const textResultArea = $('textResultArea');
    textResultArea.innerHTML = '';

    try {
        setProgress(40);
        setCubeStatus('Cross-referencing sources...');

        const res = await fetch(`${API_BASE}/api/fact-check-text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Local-Used': localStorage.getItem('fc_used') || '0',
                ...(isSuperuser ? { 'X-Superuser': 'cerebras2024' } : {})
            },
            body: JSON.stringify({
                text,
                max_claims: maxClaims,
                num_sources: numSources,
                reasoning_effort: reasoningEffort
            })
        });

        setProgress(80);
        setCubeStatus('Rendering verdicts...');

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            if (res.status === 429 || err.limit_reached) {
                await checkUsage();
                setCubeProcessing(false);
                showEmptyState(false);
                textResultArea.innerHTML = renderLimitReached();
                setProgress(null);
                setLoading('analyzeBtn', false);
                isChecking = false;
                showResultsClear(true);
                return;
            }
            throw new Error(err.error || `Server error ${res.status}`);
        }

        const data = await res.json();
        setProgress(100);

        setTimeout(() => {
            setCubeProcessing(false);
            showEmptyState(false);
            textResultArea.innerHTML = renderTextResults(data);
            showResultsClear(true);
            setProgress(null);
        }, 300);

        await checkUsage();

    } catch (err) {
        setCubeProcessing(false);
        showEmptyState(false);
        setProgress(null);
        textResultArea.innerHTML = renderError(err.message);
        showResultsClear(true);
    } finally {
        setLoading('analyzeBtn', false);
        isChecking = false;
    }
}

/* ============================================================
   RENDER HELPERS
   ============================================================ */

/* ── Cube processing animation ── */
function setCubeProcessing(active, statusText) {
    const emptyState = document.getElementById('emptyState');
    const statusEl   = document.getElementById('processingStatus');
    if (emptyState) {
        if (active) {
            emptyState.classList.add('is-processing');
            if (statusEl && statusText) statusEl.textContent = statusText;
        } else {
            emptyState.classList.remove('is-processing');
            if (statusEl) statusEl.textContent = '';
        }
    }
    // Mobile hex loader
    const mobLoader  = document.getElementById('mobileHexLoader');
    const mobStatus  = document.getElementById('mobileProcessingStatus');
    if (mobLoader) {
        mobLoader.style.display = active ? 'flex' : 'none';
        if (mobStatus) mobStatus.textContent = statusText || '';
    }
}

function setCubeStatus(text) {
    const statusEl = document.getElementById('processingStatus');
    if (statusEl) {
        statusEl.style.animation = 'none';
        void statusEl.offsetWidth;
        statusEl.style.animation = '';
        statusEl.textContent = text;
    }
    const mobStatus = document.getElementById('mobileProcessingStatus');
    if (mobStatus) {
        mobStatus.style.animation = 'none';
        void mobStatus.offsetWidth;
        mobStatus.style.animation = '';
        mobStatus.textContent = text;
    }
}

function formatReasoning(text) {
    if (!text) return '';

    // Strip trailing "Verdict: X." line (LLM output leak — verdict shown in badge)
    text = text.replace(/\n?\**Verdict\**:\s*\w+\.?\s*$/i, '').trim();

    // Strip inline URLs like (https://...) — sources already shown in cards below
    text = text.replace(/\s*\(https?:\/\/[^\s)]+\)/g, '');

    let formatted = escHtml(text);

    // Bold: **text** -> <strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--text-primary); font-weight: 600;">$1</strong>');

    // Convert newlines to breaks
    formatted = formatted.replace(/\n/g, '<br>');

    // Convert asterisk bullets (* item) — common LLM list format
    formatted = formatted.replace(/(?:^|<br>)\*\s+/g, '<br><span style="color:var(--primary); margin-right:6px;">&bull;</span> ');

    // Convert dash bullets (- item)
    formatted = formatted.replace(/(?:^|<br>|\s{2,})-\s+/g, '<br><span style="color:var(--primary); margin-right:6px;">&bull;</span> ');

    // Highlight numbered lists (e.g. 1. 2.)
    formatted = formatted.replace(/(?:^|<br>|\s{2,})(\d+\.)\s+/g, '<br><span style="color:var(--primary); margin-right:4px; font-weight:600;">$1</span> ');

    // Clean up excessive <br>
    formatted = formatted.replace(/(<br>\s*){3,}/g, '<br><br>');
    formatted = formatted.replace(/^(<br>\s*)+/, '');

    return formatted;
}

function renderResultCard(data, claim) {
    const verdict = (data.verdict || 'UNCERTAIN').toUpperCase();
    const verdictClass = verdict === 'TRUE' ? 'true' : verdict === 'FALSE' ? 'false' : 'uncertain';
    const icon = verdict === 'TRUE' ? '✓' : verdict === 'FALSE' ? '✕' : '?';
    const label = verdict === 'TRUE' ? 'TRUE' : verdict === 'FALSE' ? 'FALSE' : 'UNCERTAIN';

    // API response fields
    const searchSources = data.search_sources || [];
    const citedUrls = new Set(data.sources || []);
    const reasoning = data.reason || data.reasoning || data.explanation || '';
    const tokens = data.tokens_used ? `${(data.tokens_used / 1000).toFixed(1)}k tokens` : '';
    const time = data.elapsed_seconds ? `${data.elapsed_seconds.toFixed(1)}s` : (data.time_taken ? `${data.time_taken.toFixed(1)}s` : '');

    return `
    <div class="result-card">
        <div class="result-verdict-row">
            <div class="verdict-badge ${verdictClass}">
                <div class="verdict-icon-wrap">${icon}</div>
                ${label}
            </div>
            <div class="verdict-meta">
                ${tokens ? `<div class="meta-item">⚡ ${tokens}</div>` : ''}
                ${time ? `<div class="meta-item">⏱ ${time}</div>` : ''}
            </div>
        </div>

        <div class="result-claim">${escHtml(claim)}</div>

        ${reasoning ? `
        <div class="result-reason">
            <h4>Reasoning</h4>
            <p>${formatReasoning(reasoning)}</p>
        </div>` : ''}

        ${searchSources.length ? `
        <div class="result-sources">
            <h4>Sources (${searchSources.length})</h4>
            <div class="source-list">
                ${searchSources.map((s, i) => renderSource(s, i, citedUrls)).join('')}
            </div>
        </div>` : ''}
    </div>`;
}

function renderSource(s, i, citedUrls = new Set()) {
    // search_sources shape: {url, title, quality_tier}
    const rawTier = s.quality_tier || s.tier || 'Other';
    const tierClass = rawTier.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const title = s.title || s.url || 'Source';
    const url = s.url || '#';
    const cited = citedUrls.has(url);

    return `
    <div class="source-item" style="animation-delay:${i * 0.06}s">
        <div class="source-tier ${tierClass}">${escHtml(rawTier)}</div>
        <div class="source-info">
            <div class="source-title">${escHtml(title)}</div>
            <a href="${escHtml(url)}" target="_blank" rel="noopener" class="source-url">${escHtml(url)}</a>
        </div>
        ${cited ? '<div class="source-cited">Cited</div>' : ''}
    </div>`;
}

function renderTextResults(data) {
    const results = data.results || [];
    if (!results.length) return renderError('No claims were extracted from the text.');

    const trueCount = results.filter(r => (r.verdict || '').toUpperCase() === 'TRUE').length;
    const falseCount = results.filter(r => (r.verdict || '').toUpperCase() === 'FALSE').length;
    const uncertainCount = results.length - trueCount - falseCount;

    return `
    <div class="summary-bar">
        <div class="summary-stat"><strong>${results.length}</strong> Claims</div>
        <div class="summary-divider"></div>
        <div class="summary-stat true"><strong>${trueCount}</strong> True</div>
        <div class="summary-stat false"><strong>${falseCount}</strong> False</div>
        <div class="summary-stat uncertain"><strong>${uncertainCount}</strong> Uncertain</div>
    </div>
    ${results.map((r, i) => `
    <div style="animation-delay:${i * 0.08}s">
        ${renderResultCard(r, r.claim || `Claim ${i + 1}`)}
    </div>`).join('')}`;
}

function renderError(msg) {
    return `
    <div class="error-card">
        <h4>⚠ Error</h4>
        <p>${escHtml(msg || 'Something went wrong. Please try again.')}</p>
    </div>`;
}

function renderLimitReached() {
    return `
    <div class="limit-card">
        <div class="limit-icon">🔒</div>
        <h3 class="limit-title">Free Limit Reached</h3>
        <p class="limit-msg">You've used all <strong>5 free fact-checks</strong> for this session. Thank you for trying Cerebras FactCheck!</p>
    </div>`;
}


/* ============================================================
   UI HELPERS
   ============================================================ */
function setLoading(btnId, loading) {
    isChecking = loading;
    const btn = $(btnId);
    if (!btn) return;
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');
    btn.disabled = loading;
    if (loading) {
        btn.classList.add('is-loading');
    } else {
        btn.classList.remove('is-loading');
    }
    if (text) text.style.display = loading ? 'none' : '';
    if (loader) loader.style.display = loading ? 'flex' : 'none';
}

/* ── Button click spring + ring-burst animation ── */
function initButtonClickAnim() {
    document.addEventListener('mousedown', e => {
        const btn = e.target.closest('.btn-verify');
        if (!btn || btn.disabled) return;
        // Remove and re-add to restart animation cleanly
        btn.classList.remove('btn-pressed');
        void btn.offsetWidth;
        btn.classList.add('btn-pressed');
        btn.addEventListener('animationend', () => btn.classList.remove('btn-pressed'), { once: true });
    });
}

function showEmptyState(show) {
    const el = $('emptyState');
    if (el) el.style.display = show ? '' : 'none';
}

function showResultsClear(show) {
    const btn = $('resultsClearBtn');
    if (btn) btn.style.display = show ? '' : 'none';
}

function clearResults() {
    triggerHaptic('light');
    const ra = $('resultArea');
    const ta = $('textResultArea');
    if (ra) ra.innerHTML = '';
    if (ta) ta.innerHTML = '';
    setCubeProcessing(false);
    showEmptyState(true);
    showResultsClear(false);
    toggleMobileInputs(true);
}

function toggleMobileInputs(show) {
    if (window.innerWidth > 900) return;

    const singleCard = document.querySelector('#singleTabMobile .mobile-input-card');
    const singleBtn = _origGetElementById('checkBtnMobile');
    const singleExamples = _origGetElementById('mobileExamplesSection');

    if (singleCard) singleCard.style.display = show ? '' : 'none';
    if (singleBtn) singleBtn.style.display = show ? '' : 'none';
    if (singleExamples) singleExamples.style.display = show ? '' : 'none';

    const textCard = document.querySelector('#textTabMobile .mobile-input-card');
    const textBtn = _origGetElementById('analyzeBtnMobile');
    if (textCard) textCard.style.display = show ? '' : 'none';
    if (textBtn) textBtn.style.display = show ? '' : 'none';
}

function shakeInput(id) {
    triggerHaptic('error');
    const el = $(id);
    if (!el) return;
    el.style.animation = 'none';
    el.offsetHeight; // reflow
    el.style.animation = 'shake 0.4s ease';
    el.style.borderColor = 'var(--danger)';
    el.focus();
    setTimeout(() => {
        el.style.animation = '';
        el.style.borderColor = '';
    }, 600);
}

function escHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function showToast(msg) {
    const t = document.createElement('div');
    t.style.cssText = `
        position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);
        background:rgba(20,23,32,0.95);border:1px solid rgba(212,168,83,0.3);
        color:#e8e2d6;padding:10px 20px;border-radius:999px;font-size:0.82rem;
        font-weight:500;z-index:9999;opacity:0;transition:all 0.3s ease;
        backdrop-filter:blur(12px);box-shadow:0 8px 24px rgba(0,0,0,0.4);
    `;
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => {
        t.style.opacity = '1';
        t.style.transform = 'translateX(-50%) translateY(0)';
    });
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateX(-50%) translateY(10px)';
        setTimeout(() => t.remove(), 300);
    }, 2500);
}

/* ============================================================
   HAPTICS
   ============================================================ */
function triggerHaptic(type = 'light') {
    if (!navigator.vibrate) return;

    switch (type) {
        case 'light':
            navigator.vibrate(10);
            break;
        case 'medium':
            navigator.vibrate(25);
            break;
        case 'heavy':
            navigator.vibrate(50);
            break;
        case 'success':
            navigator.vibrate([15, 60, 20]); // Double tap
            break;
        case 'error':
            navigator.vibrate([30, 40, 30, 40, 40]); // Stutter
            break;
    }
}

/* ============================================================
   HISTORY
   ============================================================ */
function addToHistory(claim, verdict) {
    const entry = {
        claim,
        verdict: (verdict || 'uncertain').toLowerCase(),
        time: Date.now()
    };
    checkHistory.unshift(entry);
    if (checkHistory.length > 20) checkHistory = checkHistory.slice(0, 20);
    localStorage.setItem('fc_history', JSON.stringify(checkHistory));
    loadHistory();
}

function loadHistory() {
    const section = $('historySection');
    const list = $('historyList');
    if (!section || !list) return;

    if (!checkHistory.length) {
        section.style.display = 'none';
        return;
    }

    section.style.display = '';
    list.innerHTML = checkHistory.slice(0, 8).map(h => {
        const vClass = h.verdict === 'true' ? 'true' : h.verdict === 'false' ? 'false' : 'uncertain';
        const timeAgo = getTimeAgo(h.time);
        return `
        <div class="history-item" data-claim="${escHtml(h.claim)}">
            <div class="history-verdict ${vClass}"></div>
            <div class="history-claim">${escHtml(h.claim)}</div>
            <div class="history-time">${timeAgo}</div>
            <div class="history-load-icon" title="Load into editor">↩</div>
        </div>`;
    }).join('');

    // Delegated click — safe against quotes/special chars in claim text
    list.onclick = e => {
        const item = e.target.closest('.history-item');
        if (item && item.dataset.claim) setExample(item.dataset.claim);
    };
}

function clearHistory() {
    checkHistory = [];
    localStorage.removeItem('fc_history');
    loadHistory();
}

function getTimeAgo(ts) {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

/* ============================================================
   CUSTOM DROPDOWN LOGIC
   ============================================================ */
function toggleDropdown(id) {
    const menu = document.getElementById(id);
    if (!menu) return;

    const isOpen = menu.classList.contains('active');

    // Close all other menus
    document.querySelectorAll('.select-menu').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.control-pill').forEach(el => el.classList.remove('active'));

    if (!isOpen) {
        menu.classList.add('active');
        const pill = menu.closest('.control-pill');
        if (pill) pill.classList.add('active');
    }
}

function selectOption(inputId, value, displayInfo) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.value = value;

    // Structure: .select-display -> .select-menu -> input[hidden]
    const menu = input.previousElementSibling;
    const display = menu ? menu.previousElementSibling : null;

    // Only update the <span> inside .select-display — do NOT replace textContent
    // which would wipe the dropdown-arrow SVG and break subsequent interactions.
    if (display) {
        const span = display.querySelector('span');
        if (span) span.textContent = displayInfo;
    }

    if (menu) {
        Array.from(menu.children).forEach(child => {
            child.classList.remove('selected');
            if (child.dataset.value === value) {
                child.classList.add('selected');
            }
        });
        menu.classList.remove('active');
        const pill = menu.closest('.control-pill');
        if (pill) pill.classList.remove('active');
    }
}

// Close dropdowns when clicking outside
// Use mousedown so it fires before any blur events but still respects option clicks.
window.addEventListener('mousedown', (e) => {
    if (!e.target.closest('.control-pill')) {
        document.querySelectorAll('.select-menu').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.control-pill').forEach(el => el.classList.remove('active'));
    }
});


/* ============================================================
   SHAKE ANIMATION (injected)
   ============================================================ */
(function injectShakeAnim() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%,100% { transform: translateX(0); }
            20%      { transform: translateX(-6px); }
            40%      { transform: translateX(6px); }
            60%      { transform: translateX(-4px); }
            80%      { transform: translateX(4px); }
        }
    `;
    document.head.appendChild(style);
})();

/* ============================================================
   INPUT CLEARING
   ============================================================ */
function toggleClearBtn(inputId, btnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input || !btn) return;

    if (input.value.length > 0) {
        btn.classList.add('visible');
    } else {
        btn.classList.remove('visible');
    }
}

/* ── Character counter ── */
function updateCharCount(inputId, counterId, limit) {
    const input = document.getElementById(inputId);
    const counter = document.getElementById(counterId);
    if (!input || !counter) return;

    const len = input.value.length;
    const limitStr = limit >= 1000 ? (limit / 1000).toFixed(0) + ',000' : String(limit);
    counter.textContent = `${len.toLocaleString()} / ${limitStr}`;

    counter.classList.remove('warn', 'error');
    if (len >= limit) {
        counter.classList.add('error');
    } else if (len >= limit * 0.85) {
        counter.classList.add('warn');
    }
}

function clearInput(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.value = '';
    input.focus();
    input.dispatchEvent(new Event('input'));
}

// Update clear button visibility when clicking example chips
document.addEventListener('click', e => {
    if (e.target.matches('.example-chip') || e.target.closest('.example-chip')) {
        setTimeout(() => {
            const inputId = document.getElementById('textTab').style.display === 'none' ? 'claimInput' : 'textInput';
            const clearBtnId = inputId === 'claimInput' ? 'clearClaim' : 'clearText';
            toggleClearBtn(inputId, clearBtnId);
        }, 50);
    }
});

/* ============================================================
   MOBILE COLLAPSE LOGIC
   ============================================================ */
function toggleMobileInput(collapsed) {
    // Only apply on mobile width
    if (window.innerWidth > 900) return;

    const inputSection = document.getElementById('singleTab');
    const claimInput = document.getElementById('claimInput');
    const collapsedClaimText = document.getElementById('collapsedClaimText');

    if (!inputSection || !claimInput || !collapsedClaimText) return;

    if (collapsed) {
        // Set summary text
        const claim = claimInput.value.trim() || 'No claim entered';
        collapsedClaimText.textContent = claim;
        inputSection.classList.add('collapsed');

        // Scroll to top of results (or top of page since input is sticky)
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        inputSection.classList.remove('collapsed');
    }
}

// Hook into fact check to collapse on submit
const originalHandleFactCheck = handleFactCheck;
handleFactCheck = async function () {
    // Collapse first if mobile
    if (window.innerWidth <= 900) {
        toggleMobileInput(true);
    }
    // Call original function
    await originalHandleFactCheck.apply(this, arguments);
};

/* ============================================================
   HELP MODAL
   ============================================================ */
function openHelpModal() {
    document.getElementById('helpModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeHelpModal(e) {
    if (!e || e.target === document.getElementById('helpModal')) {
        document.getElementById('helpModal').classList.remove('active');
        document.body.style.overflow = '';
    }
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeHelpModal();
});
