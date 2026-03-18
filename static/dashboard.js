function money(n) {
    return "$" + Number(n || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function numberFmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function integerFmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
        maximumFractionDigits: 0
    });
}

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
    return `
        <div class="tabs">
            ${months.map(month => `
                <button
                    class="tab-btn ${month === activeMonth ? "active" : ""}"
                    data-tab-group="${idPrefix}"
                    data-month="${month}"
                >
                    ${month}
                </button>
            `).join("")}
        </div>
    `;
}

function findMonthRow(rows, month) {
    return (rows || []).find(row => row.month === month) || null;
}

function renderBrokerageCustomersSection(grouped, activeMonth, monthlyBrokerage) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const monthRow = findMonthRow(monthlyBrokerage, activeMonth) || {};

    const monthlyRevenue = Number(monthRow.revenue || 0);
    const monthlyExpense = Number(monthRow.carrier_pay || 0);
    const monthlyProfit = Number(monthRow.gross_profit || 0);
    const monthlyVolume = Number(monthRow.shipment_volume || 0);

    return `
        <div class="table-card">
            <div class="section-title">Top Brokerage Customers</div>
            ${buildTabsHTML("brokerageCustomers", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span>
                <strong>${money(monthlyRevenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Expense</span>
                <strong>${money(monthlyExpense)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit</span>
                <strong class="positive">${money(monthlyProfit)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Shipment Volume</span>
                <strong>${numberFmt(monthlyVolume)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Customer</th>
                                <th>Revenue</th>
                                <th>Shipments</th>
                                <th>Expense</th>
                                <th>Profit</th>
                                <th>Profit %</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows
                                .sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999))
                                .map(row => `
                                    <tr>
                                        <td>${row.rank || ""}</td>
                                        <td>${row.customer || ""}</td>
                                        <td>${money(row.revenue)}</td>
                                        <td>${numberFmt(row.shipment_volume || 0)}</td>
                                        <td>${money(row.carrier_pay)}</td>
                                        <td class="positive">${money(row.gross_profit)}</td>
                                        <td>${numberFmt(row.profit_percentage)}%</td>
                                    </tr>
                                `).join("")}
                        </tbody>
                    </table>
                </div>
            ` : `<div class="empty-state">No data for this month.</div>`}
        </div>
    `;
}

function renderIvanExpensesSection(grouped, activeMonth, ivanMonthly) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const monthRow = findMonthRow(ivanMonthly, activeMonth) || {};

    const monthlyRevenue = Number(monthRow.revenue || 0);
    const monthlyExpenses = Number(monthRow.expenses || 0);
    const monthlyProfit = Number(monthRow.true_profit || 0);
    const monthlyMiles = Number(monthRow.miles || 0);
    const monthlyRPM = Number(monthRow.revenue_per_mile || 0);
    const monthlyCPM = Number(monthRow.cost_per_mile || 0);
    const monthlyPPM = Number(monthRow.profit_per_mile || 0);
    const monthlyVolume = Number(monthRow.shipment_volume || 0);

    return `
        <div class="table-card">
            <div class="section-title">Ivan Revenue and Expenses by Category and Month</div>
            ${buildTabsHTML("ivanExpenses", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span>
                <strong>${money(monthlyRevenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Expenses</span>
                <strong>${money(monthlyExpenses)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit</span>
                <strong class="positive">${money(monthlyProfit)}</strong>
            </div>
            <div class="month-total">
                <span>Miles</span>
                <strong>${numberFmt(monthlyMiles)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Revenue / Mile</span>
                <strong>${money(monthlyRPM)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Cost / Mile</span>
                <strong>${money(monthlyCPM)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit / Mile</span>
                <strong class="positive">${money(monthlyPPM)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Shipment Volume</span>
                <strong>${numberFmt(monthlyVolume)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Amount</th>
                                <th>Miles</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows
                                .sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0))
                                .map(row => `
                                    <tr>
                                        <td>${row.category || ""}</td>
                                        <td>${money(row.amount)}</td>
                                        <td>${numberFmt(row.miles || 0)}</td>
                                    </tr>
                                `).join("")}
                        </tbody>
                    </table>
                </div>
            ` : `<div class="empty-state">No data for this month.</div>`}
        </div>
    `;
}

function renderIvanTopCustomersSection(grouped, activeMonth, ivanMonthly) {
    const months = sortMonthsDescending(Object.keys(grouped));
    const rows = grouped[activeMonth] || [];
    const monthRow = findMonthRow(ivanMonthly, activeMonth) || {};

    const monthlyRevenue = Number(monthRow.revenue || 0);
    const monthlyExpense = Number(monthRow.expenses || 0);
    const monthlyProfit = Number(monthRow.true_profit || 0);
    const monthlyVolume = Number(monthRow.shipment_volume || 0);

    return `
        <div class="table-card">
            <div class="section-title">Ivan Top Customers by Month</div>
            ${buildTabsHTML("ivanTopCustomers", months, activeMonth)}
            <div class="month-total">
                <span>${activeMonth} Revenue</span>
                <strong>${money(monthlyRevenue)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Expense</span>
                <strong>${money(monthlyExpense)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Profit</span>
                <strong class="positive">${money(monthlyProfit)}</strong>
                <span style="margin-left:18px;color:#94a3b8;">Shipment Volume</span>
                <strong>${numberFmt(monthlyVolume)}</strong>
            </div>
            ${rows.length ? `
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Customer</th>
                                <th>Revenue</th>
                                <th>Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows
                                .sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999))
                                .map(row => `
                                    <tr>
                                        <td>${row.rank || ""}</td>
                                        <td>${row.customer || ""}</td>
                                        <td>${money(row.revenue)}</td>
                                        <td>${numberFmt(row.volume || 0)}</td>
                                    </tr>
                                `).join("")}
                        </tbody>
                    </table>
                </div>
            ` : `<div class="empty-state">No data for this month.</div>`}
        </div>
    `;
}

async function loadDashboard() {
    const res = await fetch("/api/dashboard");
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Dashboard API failed: ${res.status} ${text}`);
    }

    const data = await res.json();

    const brokerage = data.brokerage || {};
    const ivan = data.ivan || {};

    const monthlyBrokerage = brokerage.monthly_brokerage_summary || [];
    const ivanMonthly = ivan.ivan_monthly_true_profit || [];

    const brokerageCustomersGrouped = groupByMonth(brokerage.brokerage_top_customers_by_month || []);
    const ivanExpensesGrouped = groupByMonth(ivan.ivan_expenses_category_monthly || []);
    const ivanTopCustomersGrouped = groupByMonth(ivan.ivan_top_customers_by_month || []);

    const brokerageMonths = sortMonthsDescending(Object.keys(brokerageCustomersGrouped));
    const ivanExpenseMonths = sortMonthsDescending(Object.keys(ivanExpensesGrouped));
    const ivanTopCustomerMonths = sortMonthsDescending(Object.keys(ivanTopCustomersGrouped));

    let activeBrokerageMonth = brokerageMonths[0] || "";
    let activeIvanExpenseMonth = ivanExpenseMonths[0] || "";
    let activeIvanTopCustomerMonth = ivanTopCustomerMonths[0] || "";

    const dashboard = document.getElementById("dashboard");

    // Render global metric cards (always visible, above all tabs)
    function renderGlobalMetrics() {
        const globalMetrics = document.getElementById("global-metrics");
        if (!globalMetrics) return;
        globalMetrics.innerHTML = `
            <div class="kpi-grid">
                <div class="card">
                    <div class="label">Report Date Range</div>
                    <div class="value date-range-value">
                        <span>${data.report_start_date || "2026-01-01"}</span>
                        <span>${data.report_end_date || "Latest Upload"}</span>
                    </div>
                </div>
                <div class="card">
                    <div class="label">Brokerage Gross Revenue</div>
                    <div class="value">${money(brokerage.gross_revenue)}</div>
                </div>
                <div class="card">
                    <div class="label">Carrier Pay</div>
                    <div class="value">${money(brokerage.carrier_pay)}</div>
                </div>
                <div class="card">
                    <div class="label">Brokerage Gross Profit</div>
                    <div class="value">${money(brokerage.gross_profit)}</div>
                </div>
                <div class="card">
                    <div class="label">Brokerage Margin</div>
                    <div class="value">${numberFmt(brokerage.brokerage_margin)}%</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Revenue</div>
                    <div class="value">${money(ivan.ivan_cartage_revenue)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Expenses</div>
                    <div class="value">${money(ivan.ivan_expenses)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan True Profit</div>
                    <div class="value">${money(ivan.ivan_true_profit)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Total Miles</div>
                    <div class="value">${numberFmt(ivan.ivan_total_miles)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Revenue / Mile</div>
                    <div class="value">${money(ivan.ivan_revenue_per_mile)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Cost / Mile</div>
                    <div class="value">${money(ivan.ivan_cost_per_mile)}</div>
                </div>
                <div class="card">
                    <div class="label">Ivan Profit / Mile</div>
                    <div class="value">${money(ivan.ivan_profit_per_mile)}</div>
                </div>
                <div class="card">
                    <div class="label">Total Company Revenue</div>
                    <div class="value">${money(data.total_company_revenue)}</div>
                </div>
            </div>`;
    }

    function renderDashboard() {
        dashboard.innerHTML = `
            <div class="chart-grid">
                <div class="chart-card">
                    <div class="section-title">Brokerage Monthly Summary</div>
                    <canvas id="brokerageChart"></canvas>
                </div>
            </div>

            ${renderBrokerageCustomersSection(brokerageCustomersGrouped, activeBrokerageMonth, monthlyBrokerage)}
        `;

        const brokerageCanvas = document.getElementById("brokerageChart");
        if (brokerageCanvas) {
            new Chart(brokerageCanvas, {
                type: "bar",
                data: {
                    labels: monthlyBrokerage.map(row => row.month),
                    datasets: [
                        {
                            label: "Revenue",
                            data: monthlyBrokerage.map(row => row.revenue || 0),
                            backgroundColor: "#06b6d4"
                        },
                        {
                            label: "Carrier Pay",
                            data: monthlyBrokerage.map(row => row.carrier_pay || 0),
                            backgroundColor: "#a855f7"
                        },
                        {
                            label: "Gross Profit",
                            data: monthlyBrokerage.map(row => row.gross_profit || 0),
                            backgroundColor: "#f59e0b"
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: "white" } }
                    },
                    scales: {
                        x: { ticks: { color: "white" }, grid: { color: "#262630" } },
                        y: { ticks: { color: "white" }, grid: { color: "#262630" } }
                    }
                }
            });
        }

        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const group = btn.dataset.tabGroup;
                const month = btn.dataset.month;

                if (group === "brokerageCustomers") activeBrokerageMonth = month;

                renderDashboard();
            });
        });
    }

    renderGlobalMetrics();
    renderDashboard();

    // Store data for lazy init of other company panels
    _dashData = data;
    _ivanState = {
        ivanMonthly,
        ivanExpensesGrouped,
        ivanTopCustomersGrouped,
        activeIvanExpenseMonth: ivanExpenseMonths[0] || "",
        activeIvanTopCustomerMonth: ivanTopCustomerMonths[0] || ""
    };

    // If another company panel was already active before data loaded, init it now
    delete _initializedPanels[_activeCompany + ':' + _activeDept];
    _onWorkspaceActivated(_activeCompany, _activeDept);
}

// Module-level storage for lazy panel init
var _dashData = null;
var _ivanState = null;
var _initializedPanels = {};

function _renderIvanFinancePanel(container, ivanState) {
    var { ivanMonthly, ivanExpensesGrouped, ivanTopCustomersGrouped } = ivanState;

    function render() {
        container.innerHTML = `
            <div class="chart-grid">
                <div class="chart-card">
                    <div class="section-title">Ivan Monthly Profit</div>
                    <canvas id="ivanChart"></canvas>
                </div>
            </div>
            ${renderIvanExpensesSection(ivanExpensesGrouped, ivanState.activeIvanExpenseMonth, ivanMonthly)}
            ${renderIvanTopCustomersSection(ivanTopCustomersGrouped, ivanState.activeIvanTopCustomerMonth, ivanMonthly)}
        `;

        const ivanCanvas = document.getElementById("ivanChart");
        if (ivanCanvas) {
            new Chart(ivanCanvas, {
                type: "line",
                data: {
                    labels: ivanMonthly.map(row => row.month),
                    datasets: [
                        { label: "Revenue",    data: ivanMonthly.map(row => row.revenue    || 0), borderColor: "#06b6d4", backgroundColor: "#06b6d4", tension: 0.3 },
                        { label: "Expenses",   data: ivanMonthly.map(row => row.expenses   || 0), borderColor: "#ef4444", backgroundColor: "#ef4444", tension: 0.3 },
                        { label: "True Profit",data: ivanMonthly.map(row => row.true_profit|| 0), borderColor: "#22c55e", backgroundColor: "#22c55e", tension: 0.3 }
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

        container.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const group = btn.dataset.tabGroup;
                const month = btn.dataset.month;
                if (group === "ivanExpenses") ivanState.activeIvanExpenseMonth = month;
                if (group === "ivanTopCustomers") ivanState.activeIvanTopCustomerMonth = month;
                render();
            });
        });
    }

    render();
}

function _onWorkspaceActivated(company, dept) {
    var key = company + ':' + dept;
    if (_initializedPanels[key]) return;
    _initializedPanels[key] = true;

    if (company === 'ivan' && dept === 'finance') {
        var container = document.getElementById('ivan-finance-content');
        if (container && _ivanState) _renderIvanFinancePanel(container, _ivanState);
    }

    if (company === 'ivan' && dept === 'marketing') {
        if (typeof MarketingApp !== 'undefined') {
            MarketingApp.mountTo('ivan-marketing-app', 'ivan_amazon');
        }
    }

    if (company === 'bestcare' && dept === 'marketing') {
        if (typeof MarketingApp !== 'undefined') {
            MarketingApp.mountTo('bestcare-marketing-app', 'best_care_auto');
        }
    }

    if (company === 'bestcare' && dept === 'sales') {
        if (typeof SalesApp !== 'undefined') {
            SalesApp.mountTo('bestcare-sales-app', ['best_care_sales']);
        }
    }

    if (company === 'aiden') {
        if (typeof AidenApp !== 'undefined') AidenApp.init();
    }
}

function renderMarketingDashboard() {
    const marketing = document.getElementById("marketing-dashboard");
    if (!marketing) return;

    marketing.innerHTML = `
        <div class="section-title">BCAT Marketing Command Center</div>

        <div class="kpi-grid">
            <div class="card">
                <div class="label">New Leads Today</div>
                <div class="value">24</div>
            </div>

            <div class="card">
                <div class="label">Emails Sent</div>
                <div class="value">340</div>
            </div>

            <div class="card">
                <div class="label">Reply Rate</div>
                <div class="value">6.8%</div>
            </div>

            <div class="card">
                <div class="label">Positive Replies</div>
                <div class="value">11</div>
            </div>
        </div>
    `;
}

// ── Command Center Navigation ──────────────────────────────────────────────

// Tracks active state so switching company preserves active dept
var _activeCompany = 'bcat';
var _activeDept    = 'finance';

function openCompany(btn, companyId) {
    _activeCompany = companyId;

    // Company tab buttons
    document.querySelectorAll('.cc-company-tab').forEach(function(b) {
        b.classList.remove('active');
    });
    btn.classList.add('active');

    // Company panels
    document.querySelectorAll('.cc-company-panel').forEach(function(p) {
        p.classList.remove('active');
    });
    var panel = document.getElementById('cc-company-' + companyId);
    if (panel) panel.classList.add('active');

    // Show/hide dept bar — Agents has no dept subtabs
    var deptBar = document.getElementById('cc-dept-bar');
    if (deptBar) deptBar.style.display = (companyId === 'agents' || companyId === 'aiden') ? 'none' : 'flex';

    // Apply active dept within the newly shown company
    _applyDept();

    if (companyId === 'agents') loadAgents();
    _onWorkspaceActivated(companyId, _activeDept);
}

function openDept(btn, deptId) {
    _activeDept = deptId;

    // Dept tab buttons
    document.querySelectorAll('.cc-dept-tab').forEach(function(b) {
        b.classList.remove('active');
    });
    btn.classList.add('active');

    _applyDept();
    _onWorkspaceActivated(_activeCompany, deptId);
}

function _applyDept() {
    // Within the active company panel, show only the active dept panel
    var companyPanel = document.getElementById('cc-company-' + _activeCompany);
    if (!companyPanel) return;
    companyPanel.querySelectorAll('.cc-dept-panel').forEach(function(p) {
        p.classList.toggle('active', p.dataset.dept === _activeDept);
    });
}

// Legacy shim — kept for any external callers
function openTab(event, tabName) {
    var deptMap = { finance: 'finance', marketing: 'marketing', sales: 'sales', agents: 'agents' };
    if (tabName === 'agents') {
        var agentBtn = document.querySelector('.cc-company-tab[onclick*="agents"]');
        if (agentBtn) openCompany(agentBtn, 'agents');
    } else if (deptMap[tabName]) {
        var deptBtn = document.querySelector('.cc-dept-tab[onclick*="' + tabName + '"]');
        if (deptBtn) openDept(deptBtn, tabName);
    }
}

async function loadAgents() {
    const panel = document.getElementById("agents-panel");
    if (!panel) return;
    panel.innerHTML = `<div class="empty-state">Loading agents…</div>`;
    try {
        const res = await fetch("/api/agents");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const agents = await res.json();
        panel.innerHTML = renderAgents(agents);
    } catch (err) {
        panel.innerHTML = `<div class="table-card"><div class="empty-state">Failed to load agents: ${err.message}</div></div>`;
    }
}

function renderAgents(agents) {
    if (!agents || agents.length === 0) {
        return `<div class="table-card"><div class="empty-state">No agents registered yet.</div></div>`;
    }

    const cards = agents.map(agent => {
        const status = agent.status || "unknown";
        const heartbeat = agent.last_heartbeat
            ? new Date(agent.last_heartbeat).toLocaleString()
            : "—";
        const lastTask = agent.last_task || "—";
        const registeredAt = agent.registered_at
            ? new Date(agent.registered_at).toLocaleString()
            : "—";

        return `
            <div class="agent-card">
                <div class="agent-header">
                    <span class="status-dot status-${status}"></span>
                    <span class="agent-name">${agent.name}</span>
                    <span class="agent-status">${status}</span>
                </div>
                ${agent.description ? `<div class="agent-desc">${agent.description}</div>` : ""}
                <div class="agent-meta">
                    <div><span class="meta-label">Last Task</span><span>${lastTask}</span></div>
                    <div><span class="meta-label">Heartbeat</span><span>${heartbeat}</span></div>
                    <div><span class="meta-label">Registered</span><span>${registeredAt}</span></div>
                </div>
            </div>
        `;
    }).join("");

    return `
        <div class="section-title" style="margin-bottom:14px;">Agent Registry</div>
        <div class="agent-grid">${cards}</div>
    `;
}

loadDashboard().catch(err => {
    const dashboard = document.getElementById("dashboard");
    if (dashboard) {
        dashboard.innerHTML = `
            <h1>BCAT Finance Dashboard</h1>
            <div class="table-card">
                <div class="section-title">Dashboard Error</div>
                <div class="empty-state">${err.message}</div>
            </div>
        `;
    }
    console.error(err);
});
