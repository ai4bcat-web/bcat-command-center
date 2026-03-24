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

// ═══════════════════════════════════════════════════════════════════════════
// AMAZON DSP — WEEK UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════
//
// DATE FIELD USED TO ASSIGN A TRIP TO A WEEK:
//   Primary:  'trip_date'
//   Fallback: 'week'  (from legacy CSV import)
//
// To change the date field (e.g. to 'delivery_date' or 'settlement_date'),
// update AMAZON_TRIP_DATE_FIELD here AND the 'trip_date' key in
// finance_agent.py → _get_amazon_mock_trips() / _get_amazon_csv_trips().
//
// TIMEZONE ASSUMPTION: dates are ISO YYYY-MM-DD strings parsed as local
// dates (no UTC shift).  Expected timezone: US/Central (America/Chicago).
// If the server ever sends UTC timestamps, pre-strip the time component
// on the server before returning to the frontend.
// ═══════════════════════════════════════════════════════════════════════════

var AMAZON_TRIP_DATE_FIELD = 'trip_date'; // ← change here to remap the date field

/**
 * Returns the Sunday that starts the week containing `date`.
 * Handles both Date objects and YYYY-MM-DD strings (parsed as local dates).
 * @param {Date|string} date
 * @returns {Date}  midnight local Sunday
 */
function getWeekStart(date) {
    var d;
    if (typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
        var parts = date.split('-');
        d = new Date(+parts[0], +parts[1] - 1, +parts[2]); // local midnight, no UTC shift
    } else {
        d = new Date(date);
        d.setHours(0, 0, 0, 0);
    }
    var dow = d.getDay(); // 0 = Sunday
    d.setDate(d.getDate() - dow);
    return d;
}

/**
 * Returns the Saturday that ends the week containing `date`.
 * @param {Date|string} date
 * @returns {Date}  midnight local Saturday
 */
function getWeekEnd(date) {
    var start = getWeekStart(date);
    var end = new Date(start);
    end.setDate(end.getDate() + 6);
    return end;
}

/**
 * Groups trips into Sunday–Saturday week buckets.
 * Trips with a missing/invalid date field are silently skipped.
 * @param {Array}  trips  — array of trip objects
 * @returns {Object}  { "YYYY-MM-DD": [trip, ...], ... }  keyed by Sunday date
 */
function groupTripsByWeek(trips) {
    var groups = {};
    (trips || []).forEach(function(trip) {
        var dateVal = trip[AMAZON_TRIP_DATE_FIELD] || trip['week']; // fallback to 'week'
        if (!dateVal) return;
        var weekStart = getWeekStart(dateVal);
        // Produce a plain YYYY-MM-DD key without UTC offset issues
        var y  = weekStart.getFullYear();
        var m  = String(weekStart.getMonth() + 1).padStart(2, '0');
        var dy = String(weekStart.getDate()).padStart(2, '0');
        var key = y + '-' + m + '-' + dy;
        if (!groups[key]) groups[key] = [];
        groups[key].push(trip);
    });
    return groups;
}

/**
 * Formats a human-readable week label.
 * @param {Date} weekStart  Sunday
 * @param {Date} weekEnd    Saturday
 * @returns {string}  e.g. "Mar 3 – Mar 9"
 */
function formatWeekLabel(weekStart, weekEnd) {
    var opts = { month: 'short', day: 'numeric' };
    return weekStart.toLocaleDateString('en-US', opts) + ' \u2013 ' + weekEnd.toLocaleDateString('en-US', opts);
}

/**
 * Returns the ISO date string (YYYY-MM-DD) of the Sunday starting the current week.
 */
function currentWeekKey() {
    var ws = getWeekStart(new Date());
    var y  = ws.getFullYear();
    var m  = String(ws.getMonth() + 1).padStart(2, '0');
    var d  = String(ws.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + d;
}

// ═══════════════════════════════════════════════════════════════════════════
// AMAZON DSP — STATE & RENDERING
// ═══════════════════════════════════════════════════════════════════════════

var _amazonState = null;
/*  Shape:
    {
      trips:          Array,        all trips (all weeks)
      weekGroups:     Object,       { "YYYY-MM-DD": [trip, ...] }
      sortedWeekKeys: Array,        week-start keys, newest first
      activeWeekKey:  string,       "YYYY-MM-DD" or "all"
      expandedDriver: string|null   driver name in drill-down, or null
    }
*/

function _initAmazonState(amazonData) {
    var trips      = (amazonData && amazonData.trips) || [];
    var weekGroups = groupTripsByWeek(trips);
    var sortedWeekKeys = Object.keys(weekGroups).sort(function(a, b) { return b.localeCompare(a); });

    // Default: current week if it has data, else most recent week
    var cwk = currentWeekKey();
    var activeWeekKey = weekGroups[cwk] ? cwk : (sortedWeekKeys[0] || 'all');

    _amazonState = {
        trips:          trips,
        weekGroups:     weekGroups,
        sortedWeekKeys: sortedWeekKeys,
        activeWeekKey:  activeWeekKey,
        expandedDriver: null,
    };
}

function _getActiveWeekTrips() {
    if (!_amazonState) return [];
    if (_amazonState.activeWeekKey === 'all') return _amazonState.trips;
    return _amazonState.weekGroups[_amazonState.activeWeekKey] || [];
}

function _renderAmazonSection() {
    var container = document.getElementById('amazon-section');
    if (!container || !_amazonState) return;

    var trips          = _getActiveWeekTrips();
    var activeWeekKey  = _amazonState.activeWeekKey;
    var expandedDriver = _amazonState.expandedDriver;

    container.innerHTML =
        '<div class="section-title amazon-section-title">Amazon DSP \u2014 Weekly Performance</div>' +
        _buildAmazonWeekTabs() +
        _buildAmazonSummaryCards(trips, activeWeekKey) +
        (expandedDriver
            ? _buildDriverDrilldown(expandedDriver, trips)
            : _buildDriverTable(trips));

    _attachAmazonEvents(container);
}

function _buildAmazonWeekTabs() {
    var cwk  = currentWeekKey();
    var keys = _amazonState.sortedWeekKeys;
    var active = _amazonState.activeWeekKey;

    var tabsHTML = keys.map(function(key) {
        var ws    = getWeekStart(key);
        var we    = getWeekEnd(key);
        var label = formatWeekLabel(ws, we);
        var isCurrent = (key === cwk);
        var isActive  = (key === active);
        return '<button class="tab-btn amazon-week-tab' + (isActive ? ' active' : '') + '" data-week-key="' + key + '">' +
            label +
            (isCurrent ? '<span class="amazon-current-pip" title="Current week"></span>' : '') +
            '</button>';
    }).join('');

    tabsHTML += '<button class="tab-btn amazon-week-tab' + (active === 'all' ? ' active' : '') + '" data-week-key="all">All Weeks</button>';

    return '<div class="tabs amazon-week-tabs">' + tabsHTML + '</div>';
}

function _buildAmazonSummaryCards(trips, activeWeekKey) {
    var gross      = trips.reduce(function(s, t) { return s + Number(t.gross_load_revenue || 0); }, 0);
    var deductions = trips.reduce(function(s, t) { return s + Number(t.deductions || 0); }, 0);
    var net        = trips.reduce(function(s, t) { return s + Number(t.bcat_revenue || 0); }, 0);
    var drivers    = new Set(trips.map(function(t) { return t.driver; })).size;

    var periodLabel = activeWeekKey === 'all' ? 'All Weeks' : (function() {
        var ws = getWeekStart(activeWeekKey);
        var we = getWeekEnd(activeWeekKey);
        return formatWeekLabel(ws, we);
    })();

    return '<div class="amazon-period-label">' + periodLabel + '</div>' +
        '<div class="kpi-grid">' +
            '<div class="card"><div class="label">Gross Revenue</div><div class="value">' + money(gross) + '</div></div>' +
            '<div class="card"><div class="label">Total Deductions</div><div class="value">' + money(deductions) + '</div></div>' +
            '<div class="card"><div class="label">BCAT Net Revenue</div><div class="value positive">' + money(net) + '</div></div>' +
            '<div class="card"><div class="label">Total Trips</div><div class="value">' + integerFmt(trips.length) + '</div></div>' +
            '<div class="card"><div class="label">Active Drivers</div><div class="value">' + drivers + '</div></div>' +
        '</div>';
}

function _buildDriverTable(trips) {
    // Aggregate by driver
    var byDriver = {};
    trips.forEach(function(t) {
        if (!byDriver[t.driver]) byDriver[t.driver] = { driver: t.driver, type: t.driver_type, tripList: [] };
        byDriver[t.driver].tripList.push(t);
    });

    var rows = Object.values(byDriver).map(function(d) {
        var gross = d.tripList.reduce(function(s, t) { return s + Number(t.gross_load_revenue || 0); }, 0);
        var ded   = d.tripList.reduce(function(s, t) { return s + Number(t.deductions || 0); }, 0);
        var net   = d.tripList.reduce(function(s, t) { return s + Number(t.bcat_revenue || 0); }, 0);
        return { driver: d.driver, type: d.type, count: d.tripList.length, gross: gross, ded: ded, net: net };
    }).sort(function(a, b) { return b.net - a.net; });

    if (!rows.length) {
        return '<div class="table-card"><div class="empty-state">No trips for this period.</div></div>';
    }

    var typeChip = function(t) {
        return t === 'company'
            ? '<span class="amazon-type-chip company">Company</span>'
            : '<span class="amazon-type-chip owner-op">Owner Op.</span>';
    };

    var rowsHTML = rows.map(function(r) {
        return '<tr class="amazon-driver-row" data-driver="' + r.driver + '" style="cursor:pointer;">' +
            '<td>' + r.driver + '</td>' +
            '<td>' + typeChip(r.type) + '</td>' +
            '<td style="text-align:center;">' + r.count + '</td>' +
            '<td>' + money(r.gross) + '</td>' +
            '<td>' + money(r.ded) + '</td>' +
            '<td class="positive">' + money(r.net) + '</td>' +
            '<td style="color:#475569;font-size:0.72rem;">View \u25b8</td>' +
            '</tr>';
    }).join('');

    return '<div class="table-card">' +
        '<div class="amazon-table-hint">Click a driver row to view their trip history</div>' +
        '<div class="table-wrap"><table>' +
        '<thead><tr>' +
            '<th>Driver</th><th>Type</th><th style="text-align:center;">Trips</th>' +
            '<th>Gross Revenue</th><th>Deductions</th><th>BCAT Revenue</th><th></th>' +
        '</tr></thead>' +
        '<tbody>' + rowsHTML + '</tbody>' +
        '</table></div></div>';
}

function _buildDriverDrilldown(driverName, trips) {
    var driverTrips = trips
        .filter(function(t) { return t.driver === driverName; })
        .sort(function(a, b) { return (a.trip_date || '').localeCompare(b.trip_date || ''); });

    var gross = driverTrips.reduce(function(s, t) { return s + Number(t.gross_load_revenue || 0); }, 0);
    var ded   = driverTrips.reduce(function(s, t) { return s + Number(t.deductions || 0); }, 0);
    var net   = driverTrips.reduce(function(s, t) { return s + Number(t.bcat_revenue || 0); }, 0);
    var dtype = driverTrips.length ? (driverTrips[0].driver_type || '') : '';

    var typeChip = dtype === 'company'
        ? '<span class="amazon-type-chip company">Company</span>'
        : '<span class="amazon-type-chip owner-op">Owner Op.</span>';

    var header =
        '<div class="amazon-drilldown-header">' +
            '<button class="amazon-back-btn" data-action="back">\u2190 All Drivers</button>' +
            '<span class="amazon-drilldown-name">' + driverName + '</span>' +
            typeChip +
        '</div>';

    if (!driverTrips.length) {
        return '<div class="table-card">' + header +
            '<div class="empty-state">No trips for this driver in this period.</div></div>';
    }

    var summaryCards =
        '<div class="kpi-grid" style="margin:14px 0 16px;">' +
            '<div class="card"><div class="label">Trips</div><div class="value">' + driverTrips.length + '</div></div>' +
            '<div class="card"><div class="label">Gross Revenue</div><div class="value">' + money(gross) + '</div></div>' +
            '<div class="card"><div class="label">Deductions</div><div class="value">' + money(ded) + '</div></div>' +
            '<div class="card"><div class="label">BCAT Revenue</div><div class="value positive">' + money(net) + '</div></div>' +
        '</div>';

    var tripRowsHTML = driverTrips.map(function(t) {
        return '<tr>' +
            '<td style="font-family:monospace;font-size:0.77rem;">' + (t.trip_id || '\u2014') + '</td>' +
            '<td>' + (t.trip_date || '\u2014') + '</td>' +
            '<td>' + (t.route || '\u2014') + '</td>' +
            '<td style="text-align:center;">' + (t.stops != null ? t.stops : '\u2014') + '</td>' +
            '<td>' + money(t.gross_load_revenue) + '</td>' +
            '<td>' + money(t.deductions) + '</td>' +
            '<td class="positive">' + money(t.bcat_revenue) + '</td>' +
            '</tr>';
    }).join('');

    return '<div class="table-card">' + header + summaryCards +
        '<div class="table-wrap"><table>' +
        '<thead><tr>' +
            '<th>Trip ID</th><th>Date</th><th>Route</th><th style="text-align:center;">Stops</th>' +
            '<th>Gross</th><th>Deductions</th><th>BCAT Revenue</th>' +
        '</tr></thead>' +
        '<tbody>' + tripRowsHTML + '</tbody>' +
        '</table></div></div>';
}

function _attachAmazonEvents(container) {
    // Week tab clicks
    container.querySelectorAll('.amazon-week-tab').forEach(function(btn) {
        btn.addEventListener('click', function() {
            _amazonState.activeWeekKey  = btn.dataset.weekKey;
            _amazonState.expandedDriver = null;
            _renderAmazonSection();
        });
    });

    // Driver row → drill-down
    container.querySelectorAll('.amazon-driver-row').forEach(function(row) {
        row.addEventListener('click', function() {
            _amazonState.expandedDriver = row.dataset.driver;
            _renderAmazonSection();
        });
    });

    // Back button
    var backBtn = container.querySelector('[data-action="back"]');
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            _amazonState.expandedDriver = null;
            _renderAmazonSection();
        });
    }
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
    const amazon = data.amazon || {};

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

            <div id="amazon-section" class="amazon-section"></div>
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

        // Render Amazon section (has its own internal event handlers)
        _renderAmazonSection();

        document.querySelectorAll(".tab-btn:not(.amazon-week-tab)").forEach(btn => {
            btn.addEventListener("click", () => {
                const group = btn.dataset.tabGroup;
                const month = btn.dataset.month;

                if (group === "brokerageCustomers") activeBrokerageMonth = month;

                renderDashboard();
            });
        });
    }

    // Initialise Amazon weekly state BEFORE renderDashboard() calls _renderAmazonSection()
    _initAmazonState(amazon);

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

    if (company === 'bestcare' && dept === 'finance') {
        var container = document.getElementById('bestcare-finance-content');
        if (container) _loadBestCareFinance(container);
    }

    if (company === 'aiden') {
        if (typeof AidenApp !== 'undefined') AidenApp.init();
    }
}

// ── Best Care Finance / Google Ads Panel ──────────────────────────────────

function _loadBestCareFinance(container) {
    container.innerHTML = '<div style="padding:40px 0;color:#94a3b8;text-align:center;">Loading Google Ads data…</div>';
    Promise.all([
        fetch('/api/best-care/sync-status').then(function(r) { return r.json(); }),
        fetch('/api/best-care/google-ads/monthly').then(function(r) { return r.json(); }),
        fetch('/api/best-care/google-ads/campaigns').then(function(r) { return r.json(); }),
    ]).then(function(results) {
        _renderBestCareFinancePanel(container, results[0], results[1], results[2]);
    }).catch(function(err) {
        container.innerHTML = '<div style="padding:40px;color:#ef4444;">Failed to load: ' + err.message + '</div>';
    });
}

function _renderBestCareFinancePanel(container, syncStatus, monthly, campaigns) {
    var configured = syncStatus && syncStatus.configured;
    var synced     = syncStatus && syncStatus.synced_at;

    if (!configured) {
        container.innerHTML = _buildAdsNotConfiguredHTML(syncStatus);
        return;
    }

    var syncedAt   = synced ? new Date(syncStatus.synced_at).toLocaleString() : 'Never';
    var syncBtnId  = 'bc-sync-btn-' + Date.now();
    var monthTabsId = 'bc-campaign-tabs-' + Date.now();

    // Build KPI totals from monthly data
    var totalSpend = 0, totalClicks = 0, totalConv = 0, totalImpr = 0;
    var latestMonth = null, latestSpend = 0, latestConv = 0;
    if (Array.isArray(monthly) && monthly.length > 0) {
        monthly.forEach(function(m) {
            totalSpend  += (m.cost || 0);
            totalClicks += (m.clicks || 0);
            totalConv   += (m.conversions || 0);
            totalImpr   += (m.impressions || 0);
        });
        var sorted = monthly.slice().sort(function(a, b) { return (b.month || '').localeCompare(a.month || ''); });
        latestMonth = sorted[0];
        latestSpend = latestMonth.cost || 0;
        latestConv  = latestMonth.conversions || 0;
    }
    var costPerLead = totalConv > 0 ? totalSpend / totalConv : null;
    var latestCPL   = latestConv > 0 ? latestSpend / latestConv : null;

    function fmt$(n) { return n == null ? '—' : '$' + n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }
    function fmtN(n) { return n == null ? '—' : n.toLocaleString('en-US'); }

    // Unique months for campaign tabs
    var months = [];
    if (Array.isArray(campaigns) && campaigns.length > 0) {
        var seen = {};
        campaigns.forEach(function(c) { if (c.month && !seen[c.month]) { seen[c.month] = 1; months.push(c.month); } });
        months.sort(function(a, b) { return b.localeCompare(a); });
    }
    var activeMonth = months[0] || '';

    function buildCampaignTable(month) {
        var rows = Array.isArray(campaigns) ? campaigns.filter(function(c) { return c.month === month; }) : [];
        if (!rows.length) return '<div class="empty-state">No campaign data for this month.</div>';
        return '<div class="table-wrap"><table><thead><tr>' +
            '<th>Campaign</th><th>Spend</th><th>Clicks</th><th>Impr.</th><th>Conversions</th><th>Cost/Lead</th>' +
            '</tr></thead><tbody>' +
            rows.map(function(r) {
                var cpl = r.conversions > 0 ? fmt$(r.cost / r.conversions) : '—';
                return '<tr>' +
                    '<td>' + (r.campaign_name || '—') + '</td>' +
                    '<td>' + fmt$(r.cost) + '</td>' +
                    '<td>' + fmtN(r.clicks) + '</td>' +
                    '<td>' + fmtN(r.impressions) + '</td>' +
                    '<td>' + fmtN(r.conversions) + '</td>' +
                    '<td>' + cpl + '</td>' +
                    '</tr>';
            }).join('') +
            '</tbody></table></div>';
    }

    var monthTabsHTML = months.map(function(m) {
        return '<button class="tab-btn bc-month-tab' + (m === activeMonth ? ' active' : '') + '" data-month="' + m + '">' + m + '</button>';
    }).join('');

    var monthlyTableHTML = '<div class="table-wrap"><table><thead><tr>' +
        '<th>Month</th><th>Spend</th><th>Clicks</th><th>Impr.</th><th>Conversions</th><th>Cost/Lead</th>' +
        '</tr></thead><tbody>' +
        (Array.isArray(monthly) ? monthly.slice().sort(function(a,b){return (b.month||'').localeCompare(a.month||'');}).map(function(m) {
            var cpl = m.conversions > 0 ? fmt$(m.cost / m.conversions) : '—';
            return '<tr>' +
                '<td>' + (m.month || '—') + '</td>' +
                '<td>' + fmt$(m.cost) + '</td>' +
                '<td>' + fmtN(m.clicks) + '</td>' +
                '<td>' + fmtN(m.impressions) + '</td>' +
                '<td>' + fmtN(m.conversions) + '</td>' +
                '<td>' + cpl + '</td>' +
                '</tr>';
        }).join('') : '') +
        '</tbody></table></div>';

    container.innerHTML =
        '<div class="bc-ads-panel">' +

        // Sync bar
        '<div class="bc-sync-bar">' +
            '<span class="bc-sync-status">Last synced: ' + syncedAt + '</span>' +
            '<button id="' + syncBtnId + '" class="bc-sync-btn">Sync Now</button>' +
        '</div>' +

        // KPI cards — all-time
        '<div class="section-title">Google Ads — All-Time</div>' +
        '<div class="kpi-grid">' +
            '<div class="card"><div class="label">Total Spend</div><div class="value">' + fmt$(totalSpend) + '</div></div>' +
            '<div class="card"><div class="label">Total Clicks</div><div class="value">' + fmtN(totalClicks) + '</div></div>' +
            '<div class="card"><div class="label">Total Conversions</div><div class="value">' + fmtN(totalConv) + '</div></div>' +
            '<div class="card"><div class="label">Cost / Lead</div><div class="value">' + fmt$(costPerLead) + '</div></div>' +
        '</div>' +

        // KPI cards — latest month
        (latestMonth ? (
            '<div class="section-title">' + latestMonth.month + ' (Latest)</div>' +
            '<div class="kpi-grid">' +
                '<div class="card"><div class="label">Spend</div><div class="value">' + fmt$(latestSpend) + '</div></div>' +
                '<div class="card"><div class="label">Clicks</div><div class="value">' + fmtN(latestMonth.clicks) + '</div></div>' +
                '<div class="card"><div class="label">Conversions</div><div class="value">' + fmtN(latestConv) + '</div></div>' +
                '<div class="card"><div class="label">Cost / Lead</div><div class="value">' + fmt$(latestCPL) + '</div></div>' +
            '</div>'
        ) : '') +

        // Monthly summary table
        '<div class="section-title">Monthly Summary</div>' +
        '<div class="table-card">' + (monthly && monthly.length ? monthlyTableHTML : '<div class="empty-state">No monthly data — run a sync first.</div>') + '</div>' +

        // Campaign breakdown with month tabs
        '<div class="section-title">Campaign Breakdown</div>' +
        (months.length ? (
            '<div class="tabs bc-campaign-tabs" id="' + monthTabsId + '">' + monthTabsHTML + '</div>' +
            '<div class="table-card" id="bc-campaign-table">' + buildCampaignTable(activeMonth) + '</div>'
        ) : '<div class="table-card"><div class="empty-state">No campaign data — run a sync first.</div></div>') +

        '</div>';

    // Sync button
    var syncBtn = document.getElementById(syncBtnId);
    if (syncBtn) {
        syncBtn.addEventListener('click', function() {
            syncBtn.disabled = true;
            syncBtn.textContent = 'Syncing…';
            fetch('/api/best-care/sync/google-ads', { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function() { _loadBestCareFinance(container); })
                .catch(function(err) {
                    syncBtn.disabled = false;
                    syncBtn.textContent = 'Sync Now';
                    alert('Sync failed: ' + err.message);
                });
        });
    }

    // Campaign month tabs
    var tabsEl = document.getElementById(monthTabsId);
    if (tabsEl) {
        tabsEl.addEventListener('click', function(e) {
            var btn = e.target.closest('.bc-month-tab');
            if (!btn) return;
            tabsEl.querySelectorAll('.bc-month-tab').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var tableEl = document.getElementById('bc-campaign-table');
            if (tableEl) tableEl.innerHTML = buildCampaignTable(btn.dataset.month);
        });
    }
}

function _buildAdsNotConfiguredHTML(syncStatus) {
    var customerId = (syncStatus && syncStatus.customer_id) ? syncStatus.customer_id : 'not set';
    var creds = [
        'GOOGLE_ADS_DEVELOPER_TOKEN',
        'GOOGLE_ADS_CLIENT_ID',
        'GOOGLE_ADS_CLIENT_SECRET',
        'GOOGLE_ADS_REFRESH_TOKEN',
        'GOOGLE_ADS_LOGIN_CUSTOMER_ID',
        'BEST_CARE_GOOGLE_ADS_CUSTOMER_ID',
    ];
    return '<div class="bc-ads-panel">' +
        '<div class="section-title">Google Ads — Not Configured</div>' +
        '<div class="table-card">' +
        '<p style="color:#94a3b8;margin:0 0 12px 0;">Add the following credentials to <code>.env</code> to enable Google Ads data:</p>' +
        '<div class="bc-cred-list">' +
        creds.map(function(k) { return '<div class="bc-cred-row"><code>' + k + '</code></div>'; }).join('') +
        '</div>' +
        '<p style="color:#94a3b8;margin:12px 0 0 0;">Customer ID detected: <code>' + customerId + '</code></p>' +
        '</div>' +
        '</div>';
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
