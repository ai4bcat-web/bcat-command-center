/* sales.js — BCAT Command Center Sales Tab */
(function () {
    'use strict';

    // ── State ─────────────────────────────────────────────────────────────────
    const S = {
        workspace: 'bcat_sales',
        section: 'overview',
        charts: {},
        data: {}
    };

    // ── Workspace meta ────────────────────────────────────────────────────────
    const WORKSPACES = [
        { id: 'bcat_sales',            label: 'BCAT Logistics — Sales',      color: '#58a6ff', icon: '🚛' },
        { id: 'bcat_recruitment',      label: 'BCAT Recruitment',             color: '#3fb950', icon: '👤' },
        { id: 'best_care_sales',       label: 'Best Care Auto Transport',     color: '#bc8cff', icon: '🚗' },
        { id: 'ivan_dsp_recruitment',  label: 'Ivan DSP — Driver Recruitment',color: '#f59e0b', icon: '🚐' },
    ];

    const SECTIONS = [
        { id: 'overview',        label: 'Overview',          icon: '📊' },
        { id: 'leads',           label: 'Leads & Lists',     icon: '🎯' },
        { id: 'email',           label: 'Email Campaigns',   icon: '✉️'  },
        { id: 'linkedin',        label: 'LinkedIn',          icon: '🔗' },
        { id: 'meetings',        label: 'Meetings',          icon: '📅' },
        { id: 'messaging',       label: 'Messaging',         icon: '💬' },
        { id: 'recommendations', label: 'Recommendations',   icon: '💡' },
        { id: 'activity',        label: 'Activity',          icon: '📋' }
    ];

    // ── Utilities ─────────────────────────────────────────────────────────────
    function pct(n)  { return (n == null ? '—' : Number(n).toFixed(1) + '%'); }
    function num(n)  { return (n == null ? '—' : Number(n).toLocaleString()); }
    function money(n){ return (n == null ? '—' : '$' + Number(n).toLocaleString()); }
    function ago(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const diff = Math.floor((Date.now() - d) / 86400000);
        if (diff === 0) return 'today';
        if (diff === 1) return '1d ago';
        return diff + 'd ago';
    }
    function trendChip(val, suffix = '%', higherBetter = true) {
        if (val == null) return '';
        const cls = val > 0 === higherBetter ? 'up' : 'down';
        const arrow = val > 0 ? '▲' : '▼';
        return `<span class="sal-trend ${cls}">${arrow} ${Math.abs(val).toFixed(1)}${suffix}</span>`;
    }
    function loading(msg = 'Loading…') {
        return `<div class="sal-loading"><div class="sal-spinner"></div>${msg}</div>`;
    }
    function empty(icon, title, sub = '') {
        return `<div class="sal-empty">
            <div class="sal-empty-icon">${icon}</div>
            <div class="sal-empty-title">${title}</div>
            ${sub ? `<div>${sub}</div>` : ''}
        </div>`;
    }
    function sourceTag(src) {
        const cls = src === 'mock' ? 'sal-source-mock' : src === 'apollo' ? 'sal-source-apollo' : src === 'gcal' ? 'sal-source-gcal' : 'sal-source-live';
        return `<span class="sal-source-badge ${cls}">${src || 'mock'}</span>`;
    }
    function stageBadge(s) {
        if (!s) return '';
        const key = s.toLowerCase().replace(/\s+/g, '_');
        return `<span class="sal-stage sal-stage-${key}">${s}</span>`;
    }
    function priorityBadge(p) {
        if (!p) return '';
        return `<span class="sal-tag sal-priority-${p.toLowerCase()}">${p}</span>`;
    }

    // ── API fetch helper ──────────────────────────────────────────────────────
    async function api(path, opts = {}) {
        const r = await fetch('/api/sales/' + path, opts);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    }
    async function post(path, body = {}) {
        return api(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
    }
    function destroyCharts() {
        Object.values(S.charts).forEach(c => { try { c.destroy(); } catch(_){} });
        S.charts = {};
    }

    // ── Shell ─────────────────────────────────────────────────────────────────
    function renderShell() {
        const app = document.getElementById('sales-app');
        if (!app) return;

        const ws = WORKSPACES.find(w => w.id === S.workspace) || WORKSPACES[0];

        app.innerHTML = `
            <div class="sal-sidebar">
                <div class="sal-sidebar-header">Workspaces</div>
                ${WORKSPACES.map(w => `
                    <button class="sal-workspace-btn ${w.id === S.workspace ? 'active' : ''}"
                            onclick="SalesApp.switchWorkspace('${w.id}')">
                        <span class="sal-workspace-dot" style="background:${w.color}"></span>
                        ${w.label}
                    </button>
                `).join('')}

                <div class="sal-nav-divider"></div>
                <div class="sal-nav-label">Sections</div>
                ${SECTIONS.map(sec => `
                    <button class="sal-nav-btn ${sec.id === S.section ? 'active' : ''}"
                            onclick="SalesApp.switchSection('${sec.id}')">
                        <span class="sal-nav-icon">${sec.icon}</span>
                        ${sec.label}
                    </button>
                `).join('')}

                <div class="sal-sync-bar">
                    <div>Last sync: <span id="sal-sync-time">—</span></div>
                    <button onclick="SalesApp.syncAll()">⟳ Sync All</button>
                </div>
            </div>
            <div class="sal-main" id="sal-main">
                ${loading()}
            </div>`;

        loadSyncStatus();
        renderSection();
    }

    // ── Section router ────────────────────────────────────────────────────────
    function renderSection() {
        destroyCharts();
        const main = document.getElementById('sal-main');
        if (!main) return;
        main.innerHTML = loading();
        ({
            overview:        renderOverview,
            leads:           renderLeads,
            email:           renderEmail,
            linkedin:        renderLinkedIn,
            meetings:        renderMeetings,
            messaging:       renderMessaging,
            recommendations: renderRecommendations,
            activity:        renderActivity
        }[S.section] || renderOverview)();
    }

    // ── Overview ──────────────────────────────────────────────────────────────
    async function renderOverview() {
        const main = document.getElementById('sal-main');
        try {
            const [ov, daily] = await Promise.all([
                api(S.workspace + '/overview'),
                api(S.workspace + '/daily')
            ]);
            const k = ov.kpis || {};
            const days = daily.days || [];
            const ws = WORKSPACES.find(w => w.id === S.workspace);

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">${ws ? ws.icon + ' ' + ws.label : 'Overview'}</span>
                    <div class="sal-section-actions">
                        <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.syncAll()">⟳ Sync</button>
                    </div>
                </div>

                <div class="sal-kpi-grid">
                    ${kpi('Emails Sent MTD', num(k.emails_sent_mtd), `target ${num(k.target_emails_per_day)}/day`)}
                    ${kpi('Open Rate', pct(k.open_rate), '')}
                    ${kpi('Reply Rate', pct(k.reply_rate), '')}
                    ${kpi('Positive Replies', pct(k.positive_reply_rate), '')}
                    ${kpi('Meetings Booked', num(k.meetings_booked_mtd), `${num(k.meetings_held_mtd)} held`)}
                    ${kpi('Show Rate', pct(k.show_rate), '')}
                    ${kpi('Opp Conversion', pct(k.opp_conversion), '')}
                    ${kpi('Active Prospects', num(k.active_prospects), `+${num(k.leads_added_mtd)} MTD`)}
                    ${kpi('LI Sent MTD', num(k.linkedin_sent_mtd), '')}
                    ${kpi('LI Reply Rate', pct(k.linkedin_reply_rate), '')}
                    ${k.pipeline_value != null ? kpi('Pipeline Value', money(k.pipeline_value), '', '#3fb950') : ''}
                </div>

                <div class="sal-chart-row">
                    <div class="sal-chart-box">
                        <div class="sal-chart-label">Emails Sent (30d)</div>
                        <canvas id="sal-chart-sent"></canvas>
                    </div>
                    <div class="sal-chart-box">
                        <div class="sal-chart-label">Open & Reply Rates (30d)</div>
                        <canvas id="sal-chart-rates"></canvas>
                    </div>
                </div>

                <div class="sal-two-col">
                    <div class="sal-card">
                        <div class="sal-card-title">Email Funnel (MTD)</div>
                        ${renderFunnel([
                            { label: 'Sent',            val: k.emails_sent_mtd,     base: k.emails_sent_mtd },
                            { label: 'Opens',           val: Math.round((k.emails_sent_mtd||0)*(k.open_rate||0)/100), base: k.emails_sent_mtd },
                            { label: 'Replies',         val: Math.round((k.emails_sent_mtd||0)*(k.reply_rate||0)/100), base: k.emails_sent_mtd },
                            { label: 'Pos. Replies',    val: Math.round((k.emails_sent_mtd||0)*(k.positive_reply_rate||0)/100), base: k.emails_sent_mtd },
                            { label: 'Meetings',        val: k.meetings_booked_mtd, base: k.emails_sent_mtd }
                        ])}
                    </div>
                    <div class="sal-card">
                        <div class="sal-card-title">Activity Feed</div>
                        <div id="sal-activity-inline">${loading('Loading activity…')}</div>
                    </div>
                </div>`;

            buildSentChart(days);
            buildRatesChart(days);
            loadActivityInline();
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Failed to load overview: ${e.message}</div>`;
        }
    }

    function kpi(label, value, sub, valueColor = '') {
        return `<div class="sal-kpi">
            <div class="sal-kpi-label">${label}</div>
            <div class="sal-kpi-value" style="${valueColor ? 'color:' + valueColor : ''}">${value}</div>
            ${sub ? `<div class="sal-kpi-sub">${sub}</div>` : ''}
        </div>`;
    }

    function renderFunnel(steps) {
        const maxVal = steps[0].val || 1;
        return `<div class="sal-funnel">` +
            steps.map(s => {
                const pctW = Math.max(4, Math.round((s.val / maxVal) * 100));
                const pctLabel = s.base ? (s.val / s.base * 100).toFixed(1) + '%' : '';
                return `<div class="sal-funnel-row">
                    <div class="sal-funnel-label">${s.label}</div>
                    <div class="sal-funnel-bar-wrap">
                        <div class="sal-funnel-bar" style="width:${pctW}%">${num(s.val)}</div>
                    </div>
                    <div class="sal-funnel-pct">${pctLabel}</div>
                </div>`;
            }).join('') + `</div>`;
    }

    function buildSentChart(days) {
        const ctx = document.getElementById('sal-chart-sent');
        if (!ctx || !days.length) return;
        const labels = days.slice(-14).map(d => d.date.slice(5));
        const vals   = days.slice(-14).map(d => d.emails_sent || 0);
        S.charts.sent = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{ label: 'Sent', data: vals, backgroundColor: 'rgba(88,166,255,0.6)', borderRadius: 3 }]
            },
            options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#6e7681', font: { size: 10 } }, grid: { color: '#21262d' } }, y: { ticks: { color: '#6e7681' }, grid: { color: '#21262d' } } } }
        });
    }

    function buildRatesChart(days) {
        const ctx = document.getElementById('sal-chart-rates');
        if (!ctx || !days.length) return;
        const labels   = days.slice(-14).map(d => d.date.slice(5));
        const opens    = days.slice(-14).map(d => d.open_rate || 0);
        const replies  = days.slice(-14).map(d => d.reply_rate || 0);
        S.charts.rates = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Open %',  data: opens,   borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)', tension: 0.3, pointRadius: 2 },
                    { label: 'Reply %', data: replies,  borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.08)',  tension: 0.3, pointRadius: 2 }
                ]
            },
            options: { plugins: { legend: { labels: { color: '#8b949e', font: { size: 11 } } } }, scales: { x: { ticks: { color: '#6e7681', font: { size: 10 } }, grid: { color: '#21262d' } }, y: { ticks: { color: '#6e7681', callback: v => v + '%' }, grid: { color: '#21262d' } } } }
        });
    }

    async function loadActivityInline() {
        const el = document.getElementById('sal-activity-inline');
        if (!el) return;
        try {
            const d = await api(S.workspace + '/activity');
            const items = (d.activity || []).slice(0, 6);
            el.innerHTML = items.length
                ? `<div class="sal-activity-feed">` + items.map(a =>
                    `<div class="sal-activity-item">
                        <div class="sal-activity-dot"></div>
                        <div><div class="sal-activity-text">${a.description}</div>
                        <div class="sal-activity-time">${a.date}</div></div>
                    </div>`).join('') + `</div>`
                : empty('📋', 'No activity yet');
        } catch(e) { el.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`; }
    }

    // ── Leads ─────────────────────────────────────────────────────────────────
    async function renderLeads() {
        const main = document.getElementById('sal-main');
        try {
            const [leadsRes, listsRes] = await Promise.all([
                api(S.workspace + '/leads'),
                api(S.workspace + '/lead-lists')
            ]);
            const leads = leadsRes.leads || [];
            const lists = listsRes.lists || [];

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">🎯 Leads & Lists</span>
                    <div class="sal-section-actions">
                        <button class="sal-btn sal-btn-blue sal-btn-sm" onclick="SalesApp.showScrapeDialog()">+ Scrape Leads</button>
                        <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.syncApollo()">⟳ Apollo Sync</button>
                    </div>
                </div>

                <div class="sal-card" style="margin-bottom:16px">
                    <div class="sal-card-title">Lead Lists ${sourceTag(listsRes.source)}</div>
                    <div class="sal-table-wrap">
                        <table class="sal-table">
                            <thead><tr>
                                <th>Name</th><th>Count</th><th>Enrolled</th>
                                <th>Source</th><th>Persona</th><th>Status</th>
                            </tr></thead>
                            <tbody>${lists.map(l => `<tr>
                                <td>${l.name}</td>
                                <td>${num(l.count)}</td>
                                <td>${num(l.enrolled)}</td>
                                <td>${l.source}</td>
                                <td style="color:#8b949e;font-size:12px">${l.persona}</td>
                                <td>${stageBadge(l.status)}</td>
                            </tr>`).join('') || `<tr><td colspan="6">${empty('📂','No lead lists yet')}</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="sal-card">
                    <div class="sal-card-title">Leads ${sourceTag(leadsRes.source)}</div>
                    <div class="sal-table-wrap">
                        <table class="sal-table">
                            <thead><tr>
                                <th>Name</th><th>Company</th><th>Title</th>
                                <th>Location</th><th>Stage</th><th>Score</th>
                                <th>Touches</th><th>Last Touch</th>
                            </tr></thead>
                            <tbody>${leads.map(l => `<tr>
                                <td>
                                    <div style="font-weight:600;color:#e2e8f0">${l.first_name} ${l.last_name}</div>
                                    <div style="font-size:11px;color:#6e7681">${l.email || ''}</div>
                                </td>
                                <td>${l.company}</td>
                                <td style="color:#8b949e;font-size:12px">${l.title}</td>
                                <td style="font-size:12px">${l.location}</td>
                                <td>${stageBadge(l.status)}</td>
                                <td>
                                    <span style="color:${fitColor(l.fit_score)};font-weight:700">${l.fit_score || '—'}</span>
                                </td>
                                <td>${l.touches}</td>
                                <td style="color:#6e7681;font-size:12px">${ago(l.last_touch)}</td>
                            </tr>`).join('') || `<tr><td colspan="8">${empty('👤','No leads yet','Run Apollo sync or scrape to get started')}</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    function fitColor(score) {
        if (!score) return '#6e7681';
        if (score >= 80) return '#3fb950';
        if (score >= 60) return '#d29922';
        return '#f85149';
    }

    // ── Email Campaigns ───────────────────────────────────────────────────────
    async function renderEmail() {
        const main = document.getElementById('sal-main');
        try {
            const d = await api(S.workspace + '/email/campaigns');
            const campaigns = d.campaigns || [];

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">✉️ Email Campaigns</span>
                    <div class="sal-section-actions">
                        <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.syncInstantly()">⟳ Sync Instantly</button>
                    </div>
                </div>
                ${sourceTag(d.source)}
                <div style="margin-top:16px"></div>

                ${campaigns.length ? campaigns.map(c => renderCampaignCard(c)).join('') : empty('✉️', 'No campaigns', 'Sync Instantly to load campaigns')}`;
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    function renderCampaignCard(c) {
        const m = c.metrics || {};
        const openPct  = m.open_rate || 0;
        const replyPct = m.reply_rate || 0;
        const openFill  = openPct > 40 ? '' : openPct > 25 ? 'warn' : 'bad';
        const replyFill = replyPct > 5  ? '' : replyPct > 2  ? 'warn' : 'bad';
        return `<div class="sal-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                <div>
                    <div style="font-size:15px;font-weight:700;color:#e2e8f0">${c.name}</div>
                    <div style="font-size:12px;color:#6e7681;margin-top:2px">${c.list} · ${c.sequence_steps} steps · started ${c.started_at}</div>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    ${stageBadge(c.status)}
                    <button class="sal-btn sal-btn-blue sal-btn-sm" onclick="SalesApp.enrollLeads('${c.id}')">+ Enroll</button>
                </div>
            </div>
            <div class="sal-kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(110px,1fr))">
                ${kpi('Enrolled',    num(c.leads_enrolled), '')}
                ${kpi('Active',      num(c.leads_active),   '')}
                ${kpi('Sent',        num(m.sent),           '')}
                ${kpi('Open Rate',   pct(m.open_rate),      '')}
                ${kpi('Reply Rate',  pct(m.reply_rate),     '')}
                ${kpi('Pos. Reply',  pct(m.positive_reply_rate), '')}
                ${kpi('Meetings',    num(m.meetings_booked), '')}
                ${kpi('Unsubscribes',num(m.unsubscribes),   '')}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:8px">
                <div>
                    <div style="font-size:11px;color:#6e7681;margin-bottom:4px">Open Rate ${pct(m.open_rate)}</div>
                    <div class="sal-perf-bar"><div class="sal-perf-fill ${openFill}" style="width:${Math.min(openPct,100)}%"></div></div>
                </div>
                <div>
                    <div style="font-size:11px;color:#6e7681;margin-bottom:4px">Reply Rate ${pct(m.reply_rate)}</div>
                    <div class="sal-perf-bar"><div class="sal-perf-fill ${replyFill}" style="width:${Math.min(replyPct*10,100)}%"></div></div>
                </div>
            </div>
        </div>`;
    }

    // ── LinkedIn ──────────────────────────────────────────────────────────────
    async function renderLinkedIn() {
        const main = document.getElementById('sal-main');
        try {
            const [liRes, scrapedRes] = await Promise.all([
                api(S.workspace + '/linkedin/campaigns'),
                api(S.workspace + '/leads/scraped?source=linkedin')
            ]);
            const campaigns = liRes.campaigns || [];
            const scraped   = scrapedRes.leads || [];

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">🔗 LinkedIn</span>
                    <div class="sal-section-actions">
                        <button class="sal-btn sal-btn-blue sal-btn-sm" onclick="SalesApp.showLinkedInScrape()">+ Scrape LinkedIn</button>
                    </div>
                </div>

                ${campaigns.map(c => `
                <div class="sal-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                        <div>
                            <div style="font-size:15px;font-weight:700;color:#e2e8f0">${c.name}</div>
                            <div style="font-size:12px;color:#6e7681;margin-top:2px">${c.tool} · ${c.persona} · started ${c.started_at}</div>
                        </div>
                        ${stageBadge(c.status)}
                    </div>
                    <div class="sal-kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(110px,1fr))">
                        ${kpi('Connections Sent', num(c.connection_requests_sent), '')}
                        ${kpi('Accepted', num(c.connections_accepted), pct(c.acceptance_rate))}
                        ${kpi('Messages Sent', num(c.messages_sent), '')}
                        ${kpi('Replies', num(c.replies), pct(c.reply_rate))}
                        ${kpi('Positive', num(c.positive_replies), pct(c.positive_rate))}
                        ${kpi('Meetings', num(c.meetings_booked), '')}
                    </div>
                    ${c.sequence && c.sequence.length ? `
                    <div style="margin-top:12px">
                        <div class="sal-card-title">Sequence</div>
                        ${c.sequence.map((step, i) => `
                            <div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #21262d;font-size:12.5px">
                                <span style="color:#6e7681;width:22px;flex-shrink:0">S${i+1}</span>
                                <span style="color:#8b949e;width:60px;flex-shrink:0">${step.day ? 'Day ' + step.day : ''}</span>
                                <span style="color:#c9d1d9">${step.message || step.type || ''}</span>
                            </div>`).join('')}
                    </div>` : ''}
                </div>`).join('') || empty('🔗', 'No LinkedIn campaigns', 'Start a campaign to see data here')}

                ${scraped.length ? `
                <div class="sal-card">
                    <div class="sal-card-title">Scraped LinkedIn Leads (${scraped.length})</div>
                    <div class="sal-table-wrap">
                        <table class="sal-table">
                            <thead><tr><th>Name</th><th>Title</th><th>Company</th><th>Location</th></tr></thead>
                            <tbody>${scraped.map(l => `<tr>
                                <td>${l.name || (l.first_name + ' ' + l.last_name)}</td>
                                <td style="color:#8b949e">${l.title || ''}</td>
                                <td>${l.company || ''}</td>
                                <td style="color:#6e7681">${l.location || ''}</td>
                            </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>` : ''}`;
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    // ── Meetings ──────────────────────────────────────────────────────────────
    async function renderMeetings() {
        const main = document.getElementById('sal-main');
        try {
            const d = await api(S.workspace + '/meetings');
            const meetings = d.meetings || [];

            const upcoming = meetings.filter(m => m.status === 'upcoming');
            const past     = meetings.filter(m => m.status !== 'upcoming');

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">📅 Meetings</span>
                    <div class="sal-section-actions">
                        <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.syncCalendar()">⟳ Sync Calendar</button>
                    </div>
                </div>
                ${sourceTag(d.source)}
                <div style="margin-top:16px"></div>

                <div class="sal-card">
                    <div class="sal-card-title">Upcoming (${upcoming.length})</div>
                    ${upcoming.length
                        ? `<div class="sal-meeting-list">${upcoming.map(m => meetingCard(m)).join('')}</div>`
                        : `<div class="sal-no-meetings">No upcoming meetings</div>`}
                </div>

                ${past.length ? `
                <div class="sal-card">
                    <div class="sal-card-title">Past Meetings (${past.length})</div>
                    <div class="sal-meeting-list">${past.map(m => meetingCard(m)).join('')}</div>
                </div>` : ''}`;
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    function meetingCard(m) {
        const dateParts = (m.date || '').split('-');
        const monthNames = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        const day   = dateParts[2] || '?';
        const month = monthNames[parseInt(dateParts[1])] || '';
        const outcome = m.outcome ? `<span class="sal-stage sal-stage-${m.outcome.toLowerCase()}">${m.outcome}</span>` : '';
        return `<div class="sal-meeting-card">
            <div class="sal-meeting-date">
                <div class="day">${day}</div>
                <div class="month">${month}</div>
            </div>
            <div class="sal-meeting-info">
                <div class="sal-meeting-title">${m.prospect} · ${m.company} ${outcome}</div>
                <div class="sal-meeting-sub">${m.time || ''} · via ${m.source} · ${m.campaign || ''}</div>
                ${m.notes ? `<div class="sal-meeting-sub" style="margin-top:4px;font-style:italic">${m.notes}</div>` : ''}
                ${m.cal_event_id ? `<div class="sal-meeting-link">📅 Calendar event linked</div>` : ''}
            </div>
        </div>`;
    }

    // ── Messaging ─────────────────────────────────────────────────────────────
    async function renderMessaging() {
        const main = document.getElementById('sal-main');
        try {
            const d = await api(S.workspace + '/messaging/templates');
            const styles   = d.styles || ['carnegie','challenger','consultative','hyper-personalized'];
            const saved    = d.saved_templates || [];

            main.innerHTML = `
                <div class="sal-section-header">
                    <span class="sal-section-title">💬 Messaging Generator</span>
                </div>
                <div class="sal-msg-layout">
                    <div class="sal-msg-controls">
                        <div>
                            <label>Style</label>
                            <select id="msg-style">
                                ${styles.map(s => `<option value="${s}">${s.charAt(0).toUpperCase()+s.slice(1)}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label>Channel</label>
                            <select id="msg-channel">
                                <option value="email">Email</option>
                                <option value="linkedin">LinkedIn</option>
                                <option value="sms">SMS</option>
                            </select>
                        </div>
                        <div>
                            <label>Goal</label>
                            <select id="msg-goal">
                                <option value="cold_outreach">Cold Outreach</option>
                                <option value="follow_up">Follow Up</option>
                                <option value="break_up">Break-up</option>
                                <option value="referral">Referral</option>
                            </select>
                        </div>
                        <div class="sal-msg-vars">
                            <label>Variables</label>
                            ${['first_name','company','title','location','industry'].map(v => `
                            <div class="sal-msg-var-row">
                                <label>{{${v}}}</label>
                                <input type="text" id="msg-var-${v}" placeholder="${v.replace('_',' ')}" />
                            </div>`).join('')}
                        </div>
                        <button class="sal-btn sal-btn-primary" onclick="SalesApp.generateMessage()">Generate Message</button>
                    </div>
                    <div class="sal-msg-output">
                        <div class="sal-msg-subject" id="msg-subject" style="color:#6e7681">Subject line will appear here</div>
                        <div class="sal-msg-body" id="msg-body">Generated message will appear here…</div>
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div id="msg-missing" class="sal-msg-missing"></div>
                            <button class="sal-btn sal-btn-secondary sal-btn-sm sal-msg-copy-btn" onclick="SalesApp.copyMessage()">Copy</button>
                        </div>
                    </div>
                </div>

                ${saved.length ? `
                <div class="sal-card" style="margin-top:20px">
                    <div class="sal-card-title">Saved Templates (${saved.length})</div>
                    <div class="sal-table-wrap">
                        <table class="sal-table">
                            <thead><tr><th>Name</th><th>Style</th><th>Channel</th><th>Goal</th><th>Open %</th><th>Reply %</th><th>Meetings</th></tr></thead>
                            <tbody>${saved.map(t => `<tr>
                                <td style="font-weight:600">${t.name}</td>
                                <td>${t.style}</td>
                                <td>${t.channel}</td>
                                <td>${t.goal}</td>
                                <td>${pct((t.performance||{}).open_rate)}</td>
                                <td>${pct((t.performance||{}).reply_rate)}</td>
                                <td>${num((t.performance||{}).meetings)}</td>
                            </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>` : ''}`;
        } catch(e) {
            main.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    // ── Recommendations ───────────────────────────────────────────────────────
    async function renderRecommendations() {
        const main = document.getElementById('sal-main');
        main.innerHTML = `
            <div class="sal-section-header">
                <span class="sal-section-title">💡 Recommendations</span>
                <div class="sal-section-actions">
                    <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.generateRecs()">⟳ Generate New</button>
                </div>
            </div>
            <div id="sal-recs-list">${loading()}</div>`;
        await loadRecs();
    }

    async function loadRecs() {
        const el = document.getElementById('sal-recs-list');
        if (!el) return;
        try {
            const d = await api(S.workspace + '/recommendations');
            const recs = d.recommendations || [];
            el.innerHTML = recs.length
                ? `<div class="sal-rec-list">${recs.map(r => recCard(r)).join('')}</div>`
                : empty('💡', 'No recommendations', 'Click "Generate New" to analyze your pipeline');
        } catch(e) { el.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`; }
    }

    function recCard(r) {
        const implemented = r.status === 'implemented';
        const dismissed   = r.status === 'dismissed';
        return `<div class="sal-rec-card ${r.priority} ${implemented ? 'sal-rec-implemented' : ''}">
            <div class="sal-rec-header">
                <div class="sal-rec-title">${r.title}</div>
                <div class="sal-rec-meta">
                    ${priorityBadge(r.priority)}
                    <span class="sal-tag" style="background:rgba(139,148,158,.1);color:#8b949e">${r.category}</span>
                </div>
            </div>
            <div class="sal-rec-finding">${r.rationale}</div>
            ${r.expected_impact ? `<div class="sal-rec-action">Expected: ${r.expected_impact}</div>` : ''}
            <div class="sal-rec-footer">
                <div class="sal-rec-effort">Confidence: ${r.confidence || '—'} · Difficulty: ${r.difficulty || '—'}</div>
                ${!implemented && !dismissed ? `
                <div class="sal-rec-actions">
                    <button class="sal-btn sal-btn-secondary sal-btn-sm" onclick="SalesApp.dismissRec('${r.id}')">Dismiss</button>
                    <button class="sal-btn sal-btn-primary sal-btn-sm"   onclick="SalesApp.implementRec('${r.id}')">Implement</button>
                </div>` : ''}
            </div>
        </div>`;
    }

    // ── Activity ──────────────────────────────────────────────────────────────
    async function renderActivity() {
        const main = document.getElementById('sal-main');
        main.innerHTML = `
            <div class="sal-section-header">
                <span class="sal-section-title">📋 Activity Log</span>
            </div>
            <div class="sal-card" id="sal-activity-full">${loading()}</div>`;
        try {
            const d = await api(S.workspace + '/activity');
            const items = d.activity || [];
            const el = document.getElementById('sal-activity-full');
            el.innerHTML = items.length
                ? `<div class="sal-activity-feed">${items.map(a =>
                    `<div class="sal-activity-item">
                        <div class="sal-activity-dot"></div>
                        <div>
                            <div class="sal-activity-text">${a.description}</div>
                            <div class="sal-activity-time">${a.date} · ${a.type || ''}</div>
                        </div>
                    </div>`).join('')}</div>`
                : empty('📋', 'No activity logged yet');
        } catch(e) {
            const el = document.getElementById('sal-activity-full');
            if (el) el.innerHTML = `<div class="sal-loading">Error: ${e.message}</div>`;
        }
    }

    // ── Sync status strip ─────────────────────────────────────────────────────
    async function loadSyncStatus() {
        try {
            const d = await api(S.workspace + '/sync-status');
            const el = document.getElementById('sal-sync-time');
            if (!el) return;
            const ts = d.instantly && d.instantly.last_sync_at
                ? new Date(d.instantly.last_sync_at).toLocaleTimeString()
                : 'never';
            el.textContent = ts;
        } catch(_) {}
    }

    // ── Actions ───────────────────────────────────────────────────────────────
    async function syncAll() {
        const btn = document.querySelector('.sal-sync-bar button');
        if (btn) { btn.textContent = '⟳ Syncing…'; btn.disabled = true; }
        try {
            await post(S.workspace + '/sync/all');
            if (btn) { btn.textContent = '✓ Synced'; }
            loadSyncStatus();
            setTimeout(() => { if (btn) { btn.textContent = '⟳ Sync All'; btn.disabled = false; } }, 2000);
        } catch(e) {
            if (btn) { btn.textContent = '✗ Failed'; btn.disabled = false; }
        }
    }

    async function syncInstantly() {
        try {
            await post(S.workspace + '/sync/instantly');
            renderSection();
        } catch(e) { alert('Instantly sync failed: ' + e.message); }
    }

    async function syncCalendar() {
        try {
            await post(S.workspace + '/sync/calendar');
            renderSection();
        } catch(e) { alert('Calendar sync failed: ' + e.message); }
    }

    async function syncApollo() {
        const query = prompt('Search titles/keywords (e.g. "Logistics Manager"):');
        if (!query) return;
        try {
            await post(S.workspace + '/leads/sync-apollo', { titles: [query] });
            renderSection();
        } catch(e) { alert('Apollo sync failed: ' + e.message); }
    }

    function showScrapeDialog() {
        const q = prompt('Google Maps search query (e.g. "freight broker Chicago"):');
        if (!q) return;
        const loc = prompt('Location (e.g. "Chicago, IL"):') || '';
        post(S.workspace + '/leads/scrape-maps', { query: q, location: loc })
            .then(() => { alert('Scrape started.'); renderSection(); })
            .catch(e => alert('Scrape failed: ' + e.message));
    }

    function showLinkedInScrape() {
        const url = prompt('LinkedIn Sales Navigator search URL:');
        if (!url) return;
        post(S.workspace + '/leads/scrape-linkedin', { search_url: url })
            .then(() => { alert('LinkedIn scrape started.'); renderSection(); })
            .catch(e => alert('Scrape failed: ' + e.message));
    }

    function enrollLeads(campaignId) {
        const emails = prompt('Paste emails to enroll (comma-separated):');
        if (!emails) return;
        const list = emails.split(',').map(e => e.trim()).filter(Boolean);
        post(S.workspace + '/email/enroll', { campaign_id: campaignId, emails: list })
            .then(d => { alert(`Enrolled ${d.count || list.length} leads.`); })
            .catch(e => alert('Enroll failed: ' + e.message));
    }

    async function generateMessage() {
        const body = document.getElementById('msg-body');
        const subj = document.getElementById('msg-subject');
        const miss = document.getElementById('msg-missing');
        if (!body) return;
        body.textContent = 'Generating…';

        const vars = {};
        ['first_name','company','title','location','industry'].forEach(k => {
            const el = document.getElementById('msg-var-' + k);
            if (el && el.value) vars[k] = el.value;
        });

        try {
            const d = await post(S.workspace + '/messaging/generate', {
                style:     document.getElementById('msg-style').value,
                channel:   document.getElementById('msg-channel').value,
                goal:      document.getElementById('msg-goal').value,
                variables: vars
            });
            subj.textContent   = d.subject || '(no subject)';
            body.textContent   = d.body || '(empty)';
            miss.textContent   = d.missing_fields && d.missing_fields.length
                ? 'Missing: ' + d.missing_fields.join(', ') : '';
        } catch(e) {
            body.textContent = 'Error: ' + e.message;
        }
    }

    function copyMessage() {
        const body = document.getElementById('msg-body');
        const subj = document.getElementById('msg-subject');
        const text = (subj ? subj.textContent + '\n\n' : '') + (body ? body.textContent : '');
        navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard.'));
    }

    async function generateRecs() {
        const btn = document.querySelector('[onclick="SalesApp.generateRecs()"]');
        if (btn) { btn.textContent = '⟳ Generating…'; btn.disabled = true; }
        try {
            await post(S.workspace + '/recommendations/generate');
            if (btn) { btn.textContent = '⟳ Generate New'; btn.disabled = false; }
            await loadRecs();
        } catch(e) {
            if (btn) { btn.textContent = '⟳ Generate New'; btn.disabled = false; }
        }
    }

    async function implementRec(recId) {
        try {
            await post(S.workspace + '/recommendations/' + recId + '/implement');
            await loadRecs();
        } catch(e) { alert('Failed: ' + e.message); }
    }

    async function dismissRec(recId) {
        try {
            await post(S.workspace + '/recommendations/' + recId + '/dismiss');
            await loadRecs();
        } catch(e) { alert('Failed: ' + e.message); }
    }

    // ── Navigation ────────────────────────────────────────────────────────────
    function switchWorkspace(id) {
        S.workspace = id;
        S.section = 'overview';
        renderShell();
    }

    function switchSection(id) {
        S.section = id;
        // Update sidebar active state without full re-render
        document.querySelectorAll('.sal-nav-btn').forEach(b => {
            b.classList.toggle('active', b.getAttribute('onclick') === `SalesApp.switchSection('${id}')`);
        });
        renderSection();
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    function init() {
        mountTo('sales-app', ['bcat_sales']);
    }

    // ── Scoped mount (for Best Care / other company panels) ──────────────────
    function mountTo(containerId, allowedWorkspaceIds) {
        const app = document.getElementById(containerId);
        if (!app) return;

        const filtered = WORKSPACES.filter(w => allowedWorkspaceIds.includes(w.id));
        if (!filtered.length) return;

        if (!allowedWorkspaceIds.includes(S.workspace)) {
            S.workspace = filtered[0].id;
        }
        S.section = 'overview';

        const ws = filtered.find(w => w.id === S.workspace) || filtered[0];

        app.innerHTML = `
            <div class="sal-sidebar">
                ${filtered.length > 1 ? `<div class="sal-sidebar-header">Workspaces</div>
                ${filtered.map(w => `
                    <button class="sal-workspace-btn ${w.id === S.workspace ? 'active' : ''}"
                            data-ws="${w.id}" data-container="${containerId}">
                        <span class="sal-workspace-dot" style="background:${w.color}"></span>
                        ${w.label}
                    </button>
                `).join('')}
                <div class="sal-nav-divider"></div>` : `
                <div class="sal-sidebar-header">${ws.icon} ${ws.label}</div>`}
                <div class="sal-nav-label">Sections</div>
                ${SECTIONS.map(sec => `
                    <button class="sal-nav-btn ${sec.id === S.section ? 'active' : ''}"
                            data-section="${sec.id}" data-container="${containerId}">
                        <span class="sal-nav-icon">${sec.icon}</span>
                        ${sec.label}
                    </button>
                `).join('')}
                <div class="sal-sync-bar">
                    <div>Last sync: <span id="sal-sync-time-${containerId}">—</span></div>
                    <button onclick="SalesApp.syncAll()">⟳ Sync All</button>
                </div>
            </div>
            <div class="sal-main" id="sal-main-${containerId}">
                ${loading()}
            </div>`;

        // Bind workspace buttons
        app.querySelectorAll('[data-ws]').forEach(btn => {
            btn.addEventListener('click', () => {
                S.workspace = btn.dataset.ws;
                S.section = 'overview';
                app.querySelectorAll('[data-ws]').forEach(b => b.classList.toggle('active', b.dataset.ws === S.workspace));
                _renderSectionInto('sal-main-' + containerId);
            });
        });

        // Bind section buttons
        app.querySelectorAll('[data-section]').forEach(btn => {
            btn.addEventListener('click', () => {
                S.section = btn.dataset.section;
                app.querySelectorAll('[data-section]').forEach(b => b.classList.toggle('active', b.dataset.section === S.section));
                _renderSectionInto('sal-main-' + containerId);
            });
        });

        _renderSectionInto('sal-main-' + containerId);
    }

    function _renderSectionInto(mainId) {
        destroyCharts();
        const main = document.getElementById(mainId);
        if (!main) return;
        main.innerHTML = loading();

        // Temporarily swap sal-main id so existing renderSection functions target it
        const realMain = document.getElementById('sal-main');
        if (realMain) realMain.id = '_sal-main-hidden';
        main.id = 'sal-main';

        const renderFn = {
            overview:        renderOverview,
            leads:           renderLeads,
            email:           renderEmail,
            linkedin:        renderLinkedIn,
            meetings:        renderMeetings,
            messaging:       renderMessaging,
            recommendations: renderRecommendations,
            activity:        renderActivity
        }[S.section];

        if (renderFn) renderFn();

        main.id = mainId;
        if (realMain) realMain.id = 'sal-main';
    }

    // ── Public API ────────────────────────────────────────────────────────────
    window.SalesApp = {
        init,
        mountTo,
        switchWorkspace,
        switchSection,
        syncAll,
        syncInstantly,
        syncCalendar,
        syncApollo,
        showScrapeDialog,
        showLinkedInScrape,
        enrollLeads,
        generateMessage,
        copyMessage,
        generateRecs,
        implementRec,
        dismissRec
    };

    // Auto-init when the Sales tab becomes visible
    const salesTab = document.getElementById('sales');
    if (salesTab) {
        const observer = new MutationObserver(() => {
            if (salesTab.classList.contains('active') && !document.getElementById('sal-main')) {
                init();
            }
        });
        observer.observe(salesTab, { attributes: true, attributeFilter: ['class'] });
    }

})();
