/* demo_dashboard.js — BCAT Command Center Demo Frontend
 * Fetches from /api/dashboard (served by demo_app.py on port 5051 with mock data).
 * Adds hero KPI cards: $1.2M Cost Savings + 30% Efficiency Gain.
 * Zero connection to production data.
 */

// ── Formatters ────────────────────────────────────────────────────────────────

function money(n) {
    return "$" + Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function numberFmt(n) {
    return Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function integerFmt(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
}
function moneyK(n) {
    const v = Number(n || 0);
    if (v >= 1000000) return "$" + (v / 1000000).toFixed(2) + "M";
    if (v >= 1000)    return "$" + (v / 1000).toFixed(0) + "K";
    return money(v);
}

// ── Table/tab helpers ─────────────────────────────────────────────────────────

function groupByMonth(rows) {
    const grouped = {};
    (rows || []).forEach(row => {
        const month = row.month || "Unknown";
        if (!grouped[month]) grouped[month] = [];
        grouped[month].push(row);
    });
    return grouped;
}

function sortMonthsDescending(months) {
    return [...months].sort((a, b) => b.localeCompare(a));
}

function buildTabsHTML(idPrefix, months, activeMonth) {
    return `<div class="tabs">${months.map(m =>
        `<button class="tab-btn ${m === activeMonth ? "active" : ""}"
             data-tab-group="${idPrefix}" data-month="${m}">${m}</button>`
    ).join("")}</div>`;
}

function findMonthRow(rows, month) {
    return (rows || []).find(r => r.month === month) || null;
}

// ── BCAT Finance: Brokerage section ──────────────────────────────────────────

function renderBrokerageCustomersSection(grouped, activeMonth, monthlyBrokerage) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const monthRow = findMonthRow(monthlyBrokerage, activeMonth) || {};

    return `
        <div class="table-card">
            <div class="section-title">Top Brokerage Customers</div>
            ${buildTabsHTML("brokerageCustomers", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span>
                <strong>${money(monthRow.revenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Carrier Pay</span>
                <strong>${money(monthRow.carrier_pay)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Gross Profit</span>
                <strong class="positive">${money(monthRow.gross_profit)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Margin</span>
                <strong class="positive">${numberFmt(monthRow.brokerage_margin)}%</strong>
                <span style="margin-left:18px;color:#94a3b8;">Shipments</span>
                <strong>${integerFmt(monthRow.shipment_volume)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap"><table>
                    <thead><tr>
                        <th>Rank</th><th>Customer</th><th>Revenue</th>
                        <th>Shipments</th><th>Carrier Pay</th><th>Profit</th><th>Margin</th>
                    </tr></thead>
                    <tbody>${rows
                        .sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999))
                        .map(r => `<tr>
                            <td>${r.rank}</td>
                            <td>${r.customer}</td>
                            <td>${money(r.revenue)}</td>
                            <td>${integerFmt(r.shipment_volume)}</td>
                            <td>${money(r.carrier_pay)}</td>
                            <td class="positive">${money(r.gross_profit)}</td>
                            <td>${numberFmt(r.profit_percentage)}%</td>
                        </tr>`).join("")}
                    </tbody>
                </table></div>
            ` : `<div class="empty-state">No data for this month.</div>`}
        </div>`;
}

// ── Ivan Finance sections ─────────────────────────────────────────────────────

function renderIvanExpensesSection(grouped, activeMonth, ivanMonthly) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const mr = findMonthRow(ivanMonthly, activeMonth) || {};

    return `
        <div class="table-card">
            <div class="section-title">Ivan Revenue &amp; Expenses by Category</div>
            ${buildTabsHTML("ivanExpenses", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span><strong>${money(mr.revenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Expenses</span><strong>${money(mr.expenses)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit</span><strong class="positive">${money(mr.true_profit)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Miles</span><strong>${integerFmt(mr.miles)}</strong>
            </div>
            <div class="month-total">
                <span>Rev/Mile</span><strong>${money(mr.revenue_per_mile)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Cost/Mile</span><strong>${money(mr.cost_per_mile)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit/Mile</span><strong class="positive">${money(mr.profit_per_mile)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap"><table>
                    <thead><tr><th>Category</th><th>Amount</th></tr></thead>
                    <tbody>${rows
                        .sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0))
                        .map(r => `<tr>
                            <td>${r.category}</td>
                            <td>${money(r.amount)}</td>
                        </tr>`).join("")}
                    </tbody>
                </table></div>
            ` : `<div class="empty-state">No data.</div>`}
        </div>`;
}

function renderIvanTopCustomersSection(grouped, activeMonth, ivanMonthly) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const mr = findMonthRow(ivanMonthly, activeMonth) || {};

    return `
        <div class="table-card">
            <div class="section-title">Ivan Top Customers by Month</div>
            ${buildTabsHTML("ivanTopCustomers", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span><strong>${money(mr.revenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Shipments</span><strong>${integerFmt(mr.shipment_volume)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap"><table>
                    <thead><tr><th>Rank</th><th>Customer</th><th>Revenue</th><th>Trips</th></tr></thead>
                    <tbody>${rows
                        .sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999))
                        .map(r => `<tr>
                            <td>${r.rank}</td>
                            <td>${r.customer}</td>
                            <td>${money(r.revenue)}</td>
                            <td>${integerFmt(r.volume)}</td>
                        </tr>`).join("")}
                    </tbody>
                </table></div>
            ` : `<div class="empty-state">No data.</div>`}
        </div>`;
}

// ── Savings breakdown (BCAT Finance supplemental) ─────────────────────────────

function renderSavingsBreakdown() {
    const items = [
        { label: "Carrier cost optimisation (load matching)",   amount: 480000, pct: 40 },
        { label: "Route & fuel efficiency improvements",         amount: 280000, pct: 23 },
        { label: "Administrative automation & overhead",         amount: 220000, pct: 18 },
        { label: "Compliance & penalty reduction",               amount: 140000, pct: 12 },
        { label: "Vendor renegotiation & procurement",           amount:  80000, pct:  7 },
    ];
    return `
        <div class="savings-breakdown">
            <div class="savings-title">$1.2M Cost Savings — Breakdown by Category</div>
            ${items.map(it => `
                <div class="savings-row">
                    <div class="savings-row-label">${it.label}</div>
                    <div class="savings-bar-wrap"><div class="savings-bar" style="width:${it.pct}%"></div></div>
                    <div class="savings-row-val">${moneyK(it.amount)}</div>
                </div>
            `).join("")}
        </div>
        <div class="efficiency-note">
            ⚡ <strong>30% Efficiency Gain</strong>&nbsp;— loads processed per FTE increased from 180/mo → 234/mo after platform deployment
        </div>`;
}

// ── Global Metrics (hero + operational KPIs) ──────────────────────────────────

function renderGlobalMetrics(data) {
    const brokerage = data.brokerage || {};
    const ivan = data.ivan || {};
    const el = document.getElementById("global-metrics");
    if (!el) return;

    el.innerHTML = `
        <div class="kpi-grid" style="margin-bottom:12px">
            <div class="card hero-savings">
                <div class="label">Total Cost Savings</div>
                <div class="value">${moneyK(data.cost_savings || 1200000)}</div>
            </div>
            <div class="card hero-efficiency">
                <div class="label">Efficiency Gain</div>
                <div class="value">${data.efficiency_gain || 30}%</div>
            </div>
            <div class="card">
                <div class="label">Total Company Revenue</div>
                <div class="value">${moneyK(data.total_company_revenue)}</div>
            </div>
            <div class="card">
                <div class="label">Brokerage Gross Profit</div>
                <div class="value">${moneyK(brokerage.gross_profit)}</div>
            </div>
            <div class="card">
                <div class="label">Brokerage Margin</div>
                <div class="value">${numberFmt(brokerage.brokerage_margin)}%</div>
            </div>
            <div class="card">
                <div class="label">Ivan Revenue</div>
                <div class="value">${moneyK(ivan.ivan_cartage_revenue)}</div>
            </div>
            <div class="card">
                <div class="label">Ivan True Profit</div>
                <div class="value">${moneyK(ivan.ivan_true_profit)}</div>
            </div>
            <div class="card">
                <div class="label">Report Period</div>
                <div class="value date-range-value">
                    <span>${data.report_start_date || "2025-01-01"}</span>
                    <span>${data.report_end_date   || "2025-12-31"}</span>
                </div>
            </div>
        </div>`;
}

// ── BCAT Finance render ───────────────────────────────────────────────────────

function renderBCATFinance(data) {
    const brokerage = data.brokerage || {};
    const monthlyBrokerage = brokerage.monthly_brokerage_summary || [];
    const brokerageCustomersGrouped = groupByMonth(brokerage.brokerage_top_customers_by_month || []);
    const brokerageMonths = sortMonthsDescending(Object.keys(brokerageCustomersGrouped));
    let activeBrokerageMonth = brokerageMonths[0] || "";

    const dashboard = document.getElementById("dashboard");
    if (!dashboard) return;

    function render() {
        dashboard.innerHTML = `
            ${renderSavingsBreakdown()}
            <div class="chart-grid">
                <div class="chart-card">
                    <div class="section-title">Brokerage Monthly Revenue &amp; Profit (2025)</div>
                    <canvas id="brokerageChart"></canvas>
                </div>
                <div class="chart-card">
                    <div class="section-title">Brokerage Margin Trend (%)</div>
                    <canvas id="marginChart"></canvas>
                </div>
            </div>
            ${renderBrokerageCustomersSection(brokerageCustomersGrouped, activeBrokerageMonth, monthlyBrokerage)}
        `;

        const brokerageCanvas = document.getElementById("brokerageChart");
        if (brokerageCanvas) {
            new Chart(brokerageCanvas, {
                type: "bar",
                data: {
                    labels: monthlyBrokerage.map(r => r.month),
                    datasets: [
                        { label: "Revenue",      data: monthlyBrokerage.map(r => r.revenue      || 0), backgroundColor: "#06b6d4" },
                        { label: "Carrier Pay",  data: monthlyBrokerage.map(r => r.carrier_pay  || 0), backgroundColor: "#a855f7" },
                        { label: "Gross Profit", data: monthlyBrokerage.map(r => r.gross_profit || 0), backgroundColor: "#22c55e" },
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: "white" } } },
                    scales: {
                        x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                        y: { ticks: { color: "white" }, grid: { color: "#262630" } }
                    }
                }
            });
        }

        const marginCanvas = document.getElementById("marginChart");
        if (marginCanvas) {
            new Chart(marginCanvas, {
                type: "line",
                data: {
                    labels: monthlyBrokerage.map(r => r.month),
                    datasets: [{
                        label: "Gross Margin %",
                        data: monthlyBrokerage.map(r => r.brokerage_margin || 0),
                        borderColor: "#f59e0b", backgroundColor: "rgba(245,158,11,0.15)",
                        fill: true, tension: 0.3, pointRadius: 4,
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: "white" } } },
                    scales: {
                        x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                        y: { ticks: { color: "white", callback: v => v + "%" }, grid: { color: "#262630" }, min: 27, max: 32 }
                    }
                }
            });
        }

        dashboard.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                if (btn.dataset.tabGroup === "brokerageCustomers") activeBrokerageMonth = btn.dataset.month;
                render();
            });
        });
    }

    render();
}

// ── Ivan Finance render ───────────────────────────────────────────────────────

function renderIvanFinance(data, container) {
    if (!container) return;
    const ivan = data.ivan || {};
    const ivanMonthly = ivan.ivan_monthly_true_profit || [];
    const ivanExpensesGrouped = groupByMonth(ivan.ivan_expenses_category_monthly || []);
    const ivanTopCustomersGrouped = groupByMonth(ivan.ivan_top_customers_by_month || []);
    const expenseMonths = sortMonthsDescending(Object.keys(ivanExpensesGrouped));
    const tcMonths = sortMonthsDescending(Object.keys(ivanTopCustomersGrouped));

    let activeExpMonth = expenseMonths[0] || "";
    let activeTCMonth  = tcMonths[0] || "";

    function render() {
        container.innerHTML = `
            <div class="chart-grid">
                <div class="chart-card">
                    <div class="section-title">Ivan Monthly Revenue &amp; Profit (2025)</div>
                    <canvas id="ivanChart"></canvas>
                </div>
                <div class="chart-card">
                    <div class="section-title">Ivan Per-Mile Rates (2025)</div>
                    <canvas id="ivanMileChart"></canvas>
                </div>
            </div>
            ${renderIvanExpensesSection(ivanExpensesGrouped, activeExpMonth, ivanMonthly)}
            ${renderIvanTopCustomersSection(ivanTopCustomersGrouped, activeTCMonth, ivanMonthly)}
        `;

        const ivanCanvas = document.getElementById("ivanChart");
        if (ivanCanvas) {
            new Chart(ivanCanvas, {
                type: "line",
                data: {
                    labels: ivanMonthly.map(r => r.month),
                    datasets: [
                        { label: "Revenue",    data: ivanMonthly.map(r => r.revenue    || 0), borderColor: "#06b6d4", backgroundColor: "rgba(6,182,212,0.1)",   fill: false, tension: 0.3 },
                        { label: "Expenses",   data: ivanMonthly.map(r => r.expenses   || 0), borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.1)",    fill: false, tension: 0.3 },
                        { label: "True Profit",data: ivanMonthly.map(r => r.true_profit|| 0), borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,0.15)",   fill: true,  tension: 0.3 },
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: "white" } } },
                    scales: {
                        x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                        y: { ticks: { color: "white" }, grid: { color: "#262630" } }
                    }
                }
            });
        }

        const mileCanvas = document.getElementById("ivanMileChart");
        if (mileCanvas) {
            new Chart(mileCanvas, {
                type: "bar",
                data: {
                    labels: ivanMonthly.map(r => r.month),
                    datasets: [
                        { label: "Rev/Mile",    data: ivanMonthly.map(r => r.revenue_per_mile  || 0), backgroundColor: "#06b6d4" },
                        { label: "Cost/Mile",   data: ivanMonthly.map(r => r.cost_per_mile     || 0), backgroundColor: "#ef4444" },
                        { label: "Profit/Mile", data: ivanMonthly.map(r => r.profit_per_mile   || 0), backgroundColor: "#22c55e" },
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: "white" } } },
                    scales: {
                        x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                        y: { ticks: { color: "white", callback: v => "$" + v.toFixed(2) }, grid: { color: "#262630" } }
                    }
                }
            });
        }

        container.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const g = btn.dataset.tabGroup, m = btn.dataset.month;
                if (g === "ivanExpenses")    activeExpMonth = m;
                if (g === "ivanTopCustomers") activeTCMonth = m;
                render();
            });
        });
    }

    render();
}

// ── Load + wire everything ────────────────────────────────────────────────────

var _dashData       = null;
var _initializedPanels = {};

async function loadDashboard() {
    const res = await fetch("/api/dashboard");
    if (!res.ok) throw new Error("Dashboard API failed: " + res.status);
    const data = await res.json();
    _dashData = data;

    renderGlobalMetrics(data);
    renderBCATFinance(data);

    // If the user landed on a non-BCAT panel before data loaded, init it now
    delete _initializedPanels[_activeCompany + ":" + _activeDept];
    _onWorkspaceActivated(_activeCompany, _activeDept);
}

function _onWorkspaceActivated(company, dept) {
    var key = company + ":" + dept;
    if (_initializedPanels[key]) return;
    _initializedPanels[key] = true;

    if (company === "bcat" && dept === "operations") {
        var opsContainer = document.getElementById("operations-app");
        if (!opsContainer) { _initializedPanels[key] = false; return; }
        opsContainer.innerHTML = '<div class="empty-state">Loading operations…</div>';
        fetch("/api/operations")
            .then(r => r.json())
            .then(data => renderBCATOperations(data, opsContainer))
            .catch(err => { opsContainer.innerHTML = '<div class="table-card"><div class="empty-state">Error: ' + err.message + '</div></div>'; });
    }

    if (company === "bcat" && dept === "compliance") {
        var cmpContainer = document.getElementById("compliance-app");
        if (!cmpContainer) { _initializedPanels[key] = false; return; }
        cmpContainer.innerHTML = '<div class="empty-state">Loading compliance…</div>';
        fetch("/api/compliance")
            .then(r => r.json())
            .then(data => renderBCATCompliance(data, cmpContainer))
            .catch(err => { cmpContainer.innerHTML = '<div class="table-card"><div class="empty-state">Error: ' + err.message + '</div></div>'; });
    }
}

// ── Navigation ────────────────────────────────────────────────────────────────

var _activeCompany = "bcat";
var _activeDept    = "finance";

function openCompany(btn, companyId) {
    _activeCompany = companyId;
    document.querySelectorAll(".cc-company-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".cc-company-panel").forEach(p => p.classList.remove("active"));
    var panel = document.getElementById("cc-company-" + companyId);
    if (panel) panel.classList.add("active");
    var deptBar = document.getElementById("cc-dept-bar");
    if (deptBar) deptBar.style.display = (companyId === "agents") ? "none" : "flex";
    _applyDept();
    if (companyId === "agents") loadAgents();
    _onWorkspaceActivated(companyId, _activeDept);
}

function openDept(btn, deptId) {
    _activeDept = deptId;
    document.querySelectorAll(".cc-dept-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _applyDept();
    _onWorkspaceActivated(_activeCompany, deptId);
}

function _applyDept() {
    var companyPanel = document.getElementById("cc-company-" + _activeCompany);
    if (!companyPanel) return;
    companyPanel.querySelectorAll(".cc-dept-panel").forEach(p => {
        p.classList.toggle("active", p.dataset.dept === _activeDept);
    });
}

function openTab(event, tabName) {
    if (tabName === "agents") {
        var b = document.querySelector('.cc-company-tab[onclick*="agents"]');
        if (b) openCompany(b, "agents");
    } else {
        var d = document.querySelector('.cc-dept-tab[onclick*="' + tabName + '"]');
        if (d) openDept(d, tabName);
    }
}

// ── Agents panel ──────────────────────────────────────────────────────────────

async function loadAgents() {
    var panel = document.getElementById("agents-panel");
    if (!panel) return;
    panel.innerHTML = '<div class="empty-state">Loading agents…</div>';
    try {
        var res = await fetch("/api/agents");
        if (!res.ok) throw new Error("HTTP " + res.status);
        var agents = await res.json();
        panel.innerHTML = renderAgents(agents);
    } catch(err) {
        panel.innerHTML = '<div class="table-card"><div class="empty-state">Failed: ' + err.message + '</div></div>';
    }
}

function renderAgents(agents) {
    if (!agents || !agents.length) {
        return '<div class="table-card"><div class="empty-state">No agents registered.</div></div>';
    }
    var cards = agents.map(a => {
        var status = a.status || "unknown";
        var hb = a.last_heartbeat ? new Date(a.last_heartbeat).toLocaleString() : "—";
        return `<div class="agent-card">
            <div class="agent-header">
                <span class="status-dot status-${status}"></span>
                <span class="agent-name">${a.name}</span>
                <span class="agent-status">${status}</span>
            </div>
            ${a.description ? `<div class="agent-desc">${a.description}</div>` : ""}
            <div class="agent-meta">
                <div><span class="meta-label">Last Task</span><span>${a.last_task || "—"}</span></div>
                <div><span class="meta-label">Heartbeat</span><span>${hb}</span></div>
                <div><span class="meta-label">Registered</span><span>${a.registered_at ? new Date(a.registered_at).toLocaleString() : "—"}</span></div>
            </div>
        </div>`;
    }).join("");
    return `<div class="section-title" style="margin-bottom:14px;">Agent Registry</div>
            <div class="agent-grid">${cards}</div>`;
}

// ── BCAT Operations render ──────────────────────────────────────────────────
function renderBCATOperations(data, container) {
    if (!container) return;
    const kpis    = data.kpis            || {};
    const trends  = data.monthly_trends  || [];
    const costs   = data.cost_breakdown  || [];
    const fleet   = data.fleet           || [];
    const mlog    = data.maintenance_log || [];
    const alerts  = data.alerts          || [];

    const safe = v => (v === null || v === undefined) ? "—" : v;

    // ── PM status badge ──
    function pmBadge(status) {
        const s = (status || "").toLowerCase();
        if (s === "ok")            return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#14532d;color:#4ade80;font-size:11px;font-weight:600;">OK</span>`;
        if (s.includes("soon"))    return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#78350f;color:#fbbf24;font-size:11px;font-weight:600;">Due Soon</span>`;
        if (s.includes("over"))    return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#7f1d1d;color:#f87171;font-size:11px;font-weight:600;">Overdue</span>`;
        return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#1e293b;color:#94a3b8;font-size:11px;">${safe(status)}</span>`;
    }

    // ── Maintenance status badge ──
    function maintBadge(status) {
        const s = (status || "").toLowerCase();
        if (s === "completed")  return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#14532d;color:#4ade80;font-size:11px;font-weight:600;">Completed</span>`;
        if (s === "scheduled")  return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#1e3a5f;color:#60a5fa;font-size:11px;font-weight:600;">Scheduled</span>`;
        if (s === "in progress") return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#78350f;color:#fbbf24;font-size:11px;font-weight:600;">In Progress</span>`;
        return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#1e293b;color:#94a3b8;font-size:11px;">${safe(status)}</span>`;
    }

    // ── Alert row ──
    function alertCard(a) {
        const level = (a.level || "info").toLowerCase();
        let bg, border, color;
        if (level === "critical") { bg = "#2d0a0a"; border = "#ef4444"; color = "#f87171"; }
        else if (level === "warning") { bg = "#2d1a05"; border = "#f59e0b"; color = "#fbbf24"; }
        else { bg = "#0a1628"; border = "#3b82f6"; color = "#60a5fa"; }
        return `<div style="background:${bg};border-left:4px solid ${border};border-radius:6px;padding:10px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px;">
            <span style="color:${color};font-weight:700;min-width:68px;text-transform:uppercase;font-size:11px;">${a.level || "info"}</span>
            <span style="color:#e2e8f0;flex:1;">${safe(a.message)}</span>
            <span style="color:#64748b;font-size:12px;">${safe(a.date)}</span>
        </div>`;
    }

    container.innerHTML = `
        <!-- KPI Row 1: cost metrics -->
        <div class="kpi-grid" style="margin-bottom:12px;">
            <div class="card">
                <div class="label">Fuel MTD</div>
                <div class="value">${moneyK(kpis.fuel_spend_mtd)}</div>
            </div>
            <div class="card">
                <div class="label">Insurance / Month</div>
                <div class="value">${moneyK(kpis.insurance_monthly)}</div>
            </div>
            <div class="card">
                <div class="label">Driver Payroll MTD</div>
                <div class="value">${moneyK(kpis.driver_payroll_mtd)}</div>
            </div>
            <div class="card">
                <div class="label">Maintenance MTD</div>
                <div class="value">${moneyK(kpis.maintenance_mtd)}</div>
            </div>
            <div class="card">
                <div class="label">Cost / Mile</div>
                <div class="value">${kpis.cost_per_mile !== undefined ? "$" + Number(kpis.cost_per_mile).toFixed(2) : "—"}</div>
            </div>
            <div class="card">
                <div class="label">Fleet Utilization</div>
                <div class="value">${kpis.fleet_utilization !== undefined ? Number(kpis.fleet_utilization).toFixed(1) + "%" : "—"}</div>
            </div>
            <div class="card">
                <div class="label">Active Trucks</div>
                <div class="value">${safe(kpis.active_trucks)}</div>
            </div>
            <div class="card">
                <div class="label">Out of Service</div>
                <div class="value" style="color:#f87171;">${safe(kpis.out_of_service)}</div>
            </div>
            <div class="card">
                <div class="label">Operating Ratio</div>
                <div class="value">${kpis.operating_ratio !== undefined ? Number(kpis.operating_ratio).toFixed(1) + "%" : "—"}</div>
            </div>
        </div>

        <!-- KPI Row 2: miles/rate stats -->
        <div class="kpi-grid" style="margin-bottom:24px;grid-template-columns:repeat(4,1fr);">
            <div class="card">
                <div class="label">Loaded Miles MTD</div>
                <div class="value">${integerFmt(kpis.loaded_miles_mtd)}</div>
            </div>
            <div class="card">
                <div class="label">Empty Miles MTD</div>
                <div class="value">${integerFmt(kpis.empty_miles_mtd)}</div>
            </div>
            <div class="card">
                <div class="label">Deadhead %</div>
                <div class="value">${kpis.deadhead_pct !== undefined ? Number(kpis.deadhead_pct).toFixed(1) + "%" : "—"}</div>
            </div>
            <div class="card">
                <div class="label">Revenue / Mile</div>
                <div class="value">${kpis.revenue_per_mile !== undefined ? "$" + Number(kpis.revenue_per_mile).toFixed(2) : "—"}</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="chart-grid" style="margin-bottom:24px;">
            <div class="chart-card">
                <div class="section-title">Monthly Cost Trend</div>
                <canvas id="opsStackedCostChart"></canvas>
            </div>
            <div class="chart-card">
                <div class="section-title">Cost Per Mile &amp; Revenue Per Mile</div>
                <canvas id="opsMileRateChart"></canvas>
            </div>
        </div>

        <!-- Cost Breakdown table -->
        <div class="table-card" style="margin-bottom:24px;">
            <div class="section-title">Cost Breakdown — Current Month</div>
            ${costs.length ? `
            <div class="table-wrap"><table>
                <thead><tr><th>Category</th><th>Amount</th><th>% of Total</th><th style="min-width:140px;">Share</th></tr></thead>
                <tbody>${costs.map(c => `<tr>
                    <td>${safe(c.category)}</td>
                    <td>${money(c.amount)}</td>
                    <td>${c.pct !== undefined ? Number(c.pct).toFixed(1) + "%" : "—"}</td>
                    <td><div style="background:#1e293b;border-radius:4px;height:10px;"><div style="background:#06b6d4;height:10px;border-radius:4px;width:${Math.min(Number(c.pct)||0,100)}%;"></div></div></td>
                </tr>`).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state">No cost data.</div>`}
        </div>

        <!-- Fleet Status table -->
        <div class="table-card" style="margin-bottom:24px;">
            <div class="section-title">Fleet Status</div>
            ${fleet.length ? `
            <div class="table-wrap"><table>
                <thead><tr>
                    <th>Unit</th><th>Driver</th><th>Terminal</th><th>Status</th>
                    <th>Odometer</th><th>Last PM</th><th>Next PM Due</th><th>PM Status</th><th>Utilization</th>
                </tr></thead>
                <tbody>${fleet.map(f => {
                    const oos = (f.status || "").toLowerCase() === "out of service";
                    const rowStyle = oos ? 'background:#1a0a0a;' : '';
                    return `<tr style="${rowStyle}">
                        <td style="font-weight:600;">${safe(f.unit)}</td>
                        <td>${safe(f.driver)}</td>
                        <td>${safe(f.terminal)}</td>
                        <td style="color:${oos ? '#f87171' : '#4ade80'};">${safe(f.status)}</td>
                        <td>${f.odometer !== undefined ? integerFmt(f.odometer) : "—"}</td>
                        <td>${safe(f.last_pm_date)}</td>
                        <td>${safe(f.next_pm_due)}</td>
                        <td>${pmBadge(f.pm_status)}</td>
                        <td>${f.utilization_pct !== undefined ? Number(f.utilization_pct).toFixed(0) + "%" : "—"}</td>
                    </tr>`;
                }).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state">No fleet data.</div>`}
        </div>

        <!-- Maintenance Log table -->
        <div class="table-card" style="margin-bottom:24px;">
            <div class="section-title">Maintenance Log</div>
            ${mlog.length ? `
            <div class="table-wrap"><table>
                <thead><tr>
                    <th>Date</th><th>Unit</th><th>Driver</th><th>Type</th><th>Shop</th><th>Cost</th><th>Status</th>
                </tr></thead>
                <tbody>${mlog.map(m => `<tr>
                    <td>${safe(m.date)}</td>
                    <td style="font-weight:600;">${safe(m.unit)}</td>
                    <td>${safe(m.driver)}</td>
                    <td>${safe(m.type)}</td>
                    <td>${safe(m.shop)}</td>
                    <td>${money(m.cost)}</td>
                    <td>${maintBadge(m.status)}</td>
                </tr>`).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state">No maintenance records.</div>`}
        </div>

        <!-- Operational Alerts -->
        <div class="table-card">
            <div class="section-title">Operational Alerts</div>
            ${alerts.length
                ? alerts.map(alertCard).join("")
                : `<div class="empty-state">No active alerts.</div>`}
        </div>
    `;

    // ── Stacked bar: monthly cost trend ──
    const stackedCanvas = document.getElementById("opsStackedCostChart");
    if (stackedCanvas && trends.length) {
        new Chart(stackedCanvas, {
            type: "bar",
            data: {
                labels: trends.map(r => r.month),
                datasets: [
                    { label: "Fuel",          data: trends.map(r => r.fuel          || 0), backgroundColor: "#f59e0b", stack: "costs" },
                    { label: "Driver Wages",  data: trends.map(r => r.driver_wages  || 0), backgroundColor: "#06b6d4", stack: "costs" },
                    { label: "Maintenance",   data: trends.map(r => r.maintenance   || 0), backgroundColor: "#a855f7", stack: "costs" },
                    { label: "Insurance",     data: trends.map(r => r.insurance     || 0), backgroundColor: "#22c55e", stack: "costs" },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: "white" } } },
                scales: {
                    x: { ticks: { color: "white" }, grid: { color: "#262630" }, stacked: true },
                    y: { ticks: { color: "white", callback: v => moneyK(v) }, grid: { color: "#262630" }, stacked: true }
                }
            }
        });
    }

    // ── Dual line: cost per mile + revenue per mile ──
    const mileCanvas = document.getElementById("opsMileRateChart");
    if (mileCanvas && trends.length) {
        new Chart(mileCanvas, {
            type: "line",
            data: {
                labels: trends.map(r => r.month),
                datasets: [
                    {
                        label: "Cost / Mile",
                        data: trends.map(r => r.cost_per_mile || 0),
                        borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.1)",
                        fill: false, tension: 0.3, pointRadius: 4
                    },
                    {
                        label: "Revenue / Mile",
                        data: trends.map(r => r.revenue !== undefined && r.miles ? (r.revenue / r.miles) : 0),
                        borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,0.1)",
                        fill: false, tension: 0.3, pointRadius: 4
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: "white" } } },
                scales: {
                    x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                    y: { ticks: { color: "white", callback: v => "$" + Number(v).toFixed(2) }, grid: { color: "#262630" } }
                }
            }
        });
    }
}

// ── BCAT Compliance render ──────────────────────────────────────────────────
function renderBCATCompliance(data, container) {
    if (!container) return;
    const dkpis    = data.driver_kpis    || {};
    const ekpis    = data.equipment_kpis || {};
    const drivers  = data.drivers        || [];
    const trucks   = data.trucks         || [];
    const trailers = data.trailers       || [];

    const safe = v => (v === null || v === undefined) ? "—" : v;

    // ── status badge helpers ──
    function overallBadge(status) {
        switch ((status || "").toLowerCase()) {
            case "compliant":
                return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#14532d;color:#4ade80;font-size:11px;font-weight:600;">Compliant</span>`;
            case "expiring_soon":
            case "expiring soon":
                return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#78350f;color:#fbbf24;font-size:11px;font-weight:600;">Expiring Soon</span>`;
            case "expired":
                return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#7f1d1d;color:#f87171;font-size:11px;font-weight:600;">Expired</span>`;
            case "high_risk":
            case "high risk":
                return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#450a0a;color:#dc2626;font-size:11px;font-weight:700;">High Risk</span>`;
            default:
                return `<span style="display:inline-block;padding:2px 10px;border-radius:9px;background:#1e293b;color:#94a3b8;font-size:11px;">${safe(status)}</span>`;
        }
    }

    function fieldBadge(status) {
        const s = (status || "").toLowerCase();
        if (s === "ok" || s === "current" || s === "paid")
            return `<span style="color:#4ade80;font-weight:600;">${safe(status)}</span>`;
        if (s.includes("expir") || s.includes("soon"))
            return `<span style="color:#fbbf24;font-weight:600;">${safe(status)}</span>`;
        if (s === "expired" || s === "overdue")
            return `<span style="color:#f87171;font-weight:600;">${safe(status)}</span>`;
        return `<span style="color:#94a3b8;">${safe(status)}</span>`;
    }

    function rowStyle(status, oos) {
        if (oos) return "background:#1a0a0a;border-left:3px solid #ef4444;";
        switch ((status || "").toLowerCase()) {
            case "compliant":      return "border-left:3px solid #22c55e;";
            case "expiring_soon":
            case "expiring soon":  return "border-left:3px solid #f59e0b;background:#1a1205;";
            case "expired":        return "border-left:3px solid #ef4444;background:#1a0808;";
            case "high_risk":
            case "high risk":      return "border-left:3px solid #dc2626;background:#200a0a;";
            default:               return "";
        }
    }

    // ── unique ID suffix so charts don't collide on re-render ──
    const uid = "comp_" + Date.now();

    // ── Driver section HTML ──
    function buildDriverSection(filterStatus) {
        const filtered = filterStatus
            ? drivers.filter(d => {
                const s = (d.overall_status || "").toLowerCase().replace(/\s+/g, "_");
                return s === filterStatus;
              })
            : drivers;

        const filterBtns = [
            ["", "All"],
            ["expiring_soon", "Expiring Soon"],
            ["expired", "Expired"],
            ["high_risk", "High Risk"]
        ].map(([val, label]) =>
            `<button onclick="(function(){
                var ds = document.getElementById('driver-section-${uid}');
                if (!ds) return;
                ds.innerHTML = buildDriverSectionHTML_${uid}('${val}');
                ds.querySelectorAll('.ops-filter-btn').forEach(function(b){
                    b.style.background = b.dataset.filter === '${val}' ? '#0e7490' : '#1e293b';
                });
             })()"
             class="ops-filter-btn tab-btn ${val === filterStatus ? "active" : ""}"
             data-filter="${val}"
             style="background:${val === (filterStatus||"") ? "#0e7490" : "#1e293b"};margin-right:6px;margin-bottom:10px;"
            >${label}</button>`
        ).join("");

        return `
            <div style="margin-bottom:10px;">${filterBtns}</div>
            ${filtered.length ? `
            <div class="table-wrap"><table>
                <thead><tr>
                    <th>ID</th><th>Name</th><th>Terminal</th><th>CDL</th>
                    <th>CDL Exp</th><th>Medical Card</th><th>Drug Test</th>
                    <th>Annual Review</th><th>Endorsements</th><th>Status</th>
                </tr></thead>
                <tbody>${filtered.map(d => `<tr style="${rowStyle(d.overall_status, false)}">
                    <td style="font-weight:600;color:#94a3b8;">${safe(d.id)}</td>
                    <td style="font-weight:600;">${safe(d.name)}</td>
                    <td>${safe(d.terminal)}</td>
                    <td style="text-align:center;">${safe(d.cdl_class)}</td>
                    <td>${safe(d.cdl_exp)}<br><small>${fieldBadge(d.cdl_status)}</small></td>
                    <td>${safe(d.med_card_exp)}<br><small>${fieldBadge(d.med_card_status)}</small></td>
                    <td>${safe(d.drug_test_due)}<br><small>${fieldBadge(d.drug_test_status)}</small></td>
                    <td>${safe(d.annual_review_due)}</td>
                    <td style="font-size:11px;color:#94a3b8;">${safe(d.endorsements)}</td>
                    <td>${overallBadge(d.overall_status)}</td>
                </tr>`).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state">No drivers match this filter.</div>`}
        `;
    }

    // ── Trucks & Trailers section HTML ──
    function buildEquipmentSection() {
        return `
            <!-- Trucks -->
            <div class="section-title" style="margin-bottom:10px;margin-top:0;">Trucks</div>
            ${trucks.length ? `
            <div class="table-wrap" style="margin-bottom:24px;"><table>
                <thead><tr>
                    <th>Unit</th><th>Year / Make / Model</th><th>Terminal</th>
                    <th>Plates Exp</th><th>IFTA</th><th>HVUT</th>
                    <th>Annual Insp Due</th><th>PM Due</th><th>Odometer</th><th>Status</th>
                </tr></thead>
                <tbody>${trucks.map(t => `<tr style="${rowStyle(t.overall_status, t.oos)}">
                    <td style="font-weight:600;">${safe(t.unit)}${t.oos ? ' <span style="color:#f87171;font-size:10px;font-weight:700;">OOS</span>' : ""}</td>
                    <td>${safe(t.year)} ${safe(t.make)} ${safe(t.model)}</td>
                    <td>${safe(t.terminal)}</td>
                    <td>${safe(t.plates_exp)}<br><small>${fieldBadge(t.plates_status)}</small></td>
                    <td>${fieldBadge(t.ifta_status)}</td>
                    <td>${fieldBadge(t.hvut_status)}</td>
                    <td>${safe(t.annual_insp_due)}<br><small>${fieldBadge(t.annual_insp_status)}</small></td>
                    <td>${safe(t.maintenance_due)}<br><small>${fieldBadge(t.maintenance_status)}</small></td>
                    <td>${t.odometer !== undefined ? integerFmt(t.odometer) : "—"}</td>
                    <td>${overallBadge(t.overall_status)}</td>
                </tr>`).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state" style="margin-bottom:16px;">No truck data.</div>`}

            <!-- Trailers -->
            <div class="section-title" style="margin-bottom:10px;">Trailers</div>
            ${trailers.length ? `
            <div class="table-wrap"><table>
                <thead><tr>
                    <th>Unit</th><th>Type</th><th>Terminal</th>
                    <th>Plates Exp</th><th>Annual Insp Due</th><th>PM Due</th><th>Status</th>
                </tr></thead>
                <tbody>${trailers.map(t => `<tr style="${rowStyle(t.overall_status, t.oos)}">
                    <td style="font-weight:600;">${safe(t.unit)}${t.oos ? ' <span style="color:#f87171;font-size:10px;font-weight:700;">OOS</span>' : ""}</td>
                    <td>${safe(t.type)}</td>
                    <td>${safe(t.terminal)}</td>
                    <td>${safe(t.plates_exp)}<br><small>${fieldBadge(t.plates_status)}</small></td>
                    <td>${safe(t.annual_insp_due)}<br><small>${fieldBadge(t.annual_insp_status)}</small></td>
                    <td>${safe(t.maintenance_due)}<br><small>${fieldBadge(t.maintenance_status)}</small></td>
                    <td>${overallBadge(t.overall_status)}</td>
                </tr>`).join("")}</tbody>
            </table></div>
            ` : `<div class="empty-state">No trailer data.</div>`}
        `;
    }

    // Expose builder so inline onclick can call it
    window["buildDriverSectionHTML_" + uid] = buildDriverSection;

    // ── Sub-tab switcher (inline, no global namespace collision) ──
    function switchTab(tabName) {
        ["drivers", "equipment"].forEach(function(name) {
            var el = document.getElementById("compliance-tab-" + name + "-" + uid);
            var btn = document.getElementById("compliance-btn-" + name + "-" + uid);
            if (el)  el.style.display  = (name === tabName) ? "block" : "none";
            if (btn) btn.style.background = (name === tabName) ? "#0e7490" : "#1e293b";
        });
    }
    window["complianceSwitchTab_" + uid] = switchTab;

    container.innerHTML = `
        <!-- Sub-tab nav -->
        <div style="display:flex;gap:8px;margin-bottom:20px;">
            <button id="compliance-btn-drivers-${uid}"
                onclick="window['complianceSwitchTab_${uid}']('drivers')"
                class="tab-btn"
                style="background:#0e7490;padding:8px 22px;border-radius:6px;border:none;color:white;cursor:pointer;font-size:13px;font-weight:600;">
                Drivers
            </button>
            <button id="compliance-btn-equipment-${uid}"
                onclick="window['complianceSwitchTab_${uid}']('equipment')"
                class="tab-btn"
                style="background:#1e293b;padding:8px 22px;border-radius:6px;border:none;color:white;cursor:pointer;font-size:13px;font-weight:600;">
                Trucks &amp; Trailers
            </button>
        </div>

        <!-- ── Drivers panel ── -->
        <div id="compliance-tab-drivers-${uid}" style="display:block;">
            <!-- Driver KPIs -->
            <div class="kpi-grid" style="grid-template-columns:repeat(6,1fr);margin-bottom:16px;">
                <div class="card">
                    <div class="label">Total Drivers</div>
                    <div class="value">${safe(dkpis.total)}</div>
                </div>
                <div class="card">
                    <div class="label">Compliant</div>
                    <div class="value" style="color:#4ade80;">${safe(dkpis.compliant)}</div>
                </div>
                <div class="card">
                    <div class="label">Expiring (30d)</div>
                    <div class="value" style="color:#fbbf24;">${safe(dkpis.expiring_30d)}</div>
                </div>
                <div class="card">
                    <div class="label">Expired</div>
                    <div class="value" style="color:#f87171;">${safe(dkpis.expired)}</div>
                </div>
                <div class="card">
                    <div class="label">High Risk</div>
                    <div class="value" style="color:#dc2626;">${safe(dkpis.high_risk)}</div>
                </div>
                <div class="card">
                    <div class="label">Training Overdue</div>
                    <div class="value" style="color:#f87171;">${safe(dkpis.training_overdue)}</div>
                </div>
            </div>

            <!-- Driver table with filter -->
            <div class="table-card">
                <div class="section-title">Driver Compliance Detail</div>
                <div id="driver-section-${uid}">
                    ${buildDriverSection("")}
                </div>
            </div>
        </div>

        <!-- ── Trucks & Trailers panel ── -->
        <div id="compliance-tab-equipment-${uid}" style="display:none;">
            <!-- Equipment KPIs -->
            <div class="kpi-grid" style="grid-template-columns:repeat(6,1fr);margin-bottom:16px;">
                <div class="card">
                    <div class="label">Total Units</div>
                    <div class="value">${safe(ekpis.total_units)}</div>
                </div>
                <div class="card">
                    <div class="label">Compliant</div>
                    <div class="value" style="color:#4ade80;">${safe(ekpis.compliant)}</div>
                </div>
                <div class="card">
                    <div class="label">Expiring (30d)</div>
                    <div class="value" style="color:#fbbf24;">${safe(ekpis.expiring_30d)}</div>
                </div>
                <div class="card">
                    <div class="label">Overdue PM</div>
                    <div class="value" style="color:#f87171;">${safe(ekpis.overdue_maintenance)}</div>
                </div>
                <div class="card">
                    <div class="label">Out of Service</div>
                    <div class="value" style="color:#f87171;">${safe(ekpis.out_of_service)}</div>
                </div>
                <div class="card">
                    <div class="label">Expired Docs</div>
                    <div class="value" style="color:#dc2626;">${safe(ekpis.expired_docs)}</div>
                </div>
            </div>

            <!-- Equipment tables -->
            <div class="table-card">
                ${buildEquipmentSection()}
            </div>
        </div>
    `;
}

// ── Boot ──────────────────────────────────────────────────────────────────────

loadDashboard().catch(err => {
    var d = document.getElementById("dashboard");
    if (d) d.innerHTML = `<div class="table-card"><div class="section-title">Error</div>
        <div class="empty-state">${err.message}</div></div>`;
    console.error(err);
});
