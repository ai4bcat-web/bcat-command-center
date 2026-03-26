// ── Permission-aware navigation ───────────────────────────────────────────────
var _userPerms = null;

function _loadPermissions(callback) {
    fetch('/api/me').then(function(r){ return r.json(); }).then(function(perms) {
        _userPerms = perms;
        _applyPermissions(perms);
        if (callback) callback();
    }).catch(function() {
        if (callback) callback();
    });
}

function _applyPermissions(perms) {
    if (!perms || perms.is_admin) return; // admin sees everything

    var companies = perms.companies || [];

    // Hide company tabs the user cannot access
    var companyMap = { bcat: 'bcat', ivan: 'ivan', bestcare: 'bestcare', amazon: 'amazon', aiden: 'aiden', agents: 'agents' };
    document.querySelectorAll('.cc-company-tab').forEach(function(btn) {
        var onclick = btn.getAttribute('onclick') || '';
        var match = onclick.match(/'([^']+)'\)/);
        if (!match) return;
        var company = match[1];
        if (companies.indexOf(company) < 0) {
            btn.style.display = 'none';
            var panel = document.getElementById('cc-company-' + company);
            if (panel) panel.style.display = 'none';
        }
    });

    // If current company is hidden, switch to first visible
    var firstVisible = document.querySelector('.cc-company-tab:not([style*="none"])');
    if (firstVisible) {
        var onclick = firstVisible.getAttribute('onclick') || '';
        var match = onclick.match(/'([^']+)'\)/);
        if (match) openCompany(firstVisible, match[1]);
    }

    // Per-company tab restrictions
    var tabs = perms.tabs || {};
    Object.keys(tabs).forEach(function(company) {
        var allowedTabs = tabs[company];
        var deptBar = document.getElementById('cc-dept-bar');
        if (!deptBar) return;
        deptBar.querySelectorAll('.cc-dept-tab').forEach(function(btn) {
            var onclick = btn.getAttribute('onclick') || '';
            var match = onclick.match(/'([^']+)'\)/);
            if (!match) return;
            var tabName = match[1];
            if (allowedTabs.indexOf(tabName) < 0) {
                btn.style.display = 'none';
            }
        });
    });
}

// Show admin link if user is admin
function _maybeShowAdminLink(perms) {
    if (perms && perms.is_admin) {
        var hdr = document.querySelector('.cc-header');
        if (hdr && !document.getElementById('admin-link')) {
            var link = document.createElement('a');
            link.id = 'admin-link';
            link.href = '/admin';
            link.textContent = 'Admin';
            link.style.cssText = 'color:#94a3b8;font-size:12px;text-decoration:none;padding:6px 10px;border:1px solid #243047;border-radius:6px;';
            link.onmouseover = function(){ this.style.color='#f3f4f6'; };
            link.onmouseout  = function(){ this.style.color='#94a3b8'; };
            hdr.insertBefore(link, hdr.querySelector('form'));
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    _loadPermissions(function() {
        _maybeShowAdminLink(_userPerms);
    });
});

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
      trips:          Array,   all qualifying trips (already filtered by backend)
      weekGroups:     Object,  { "YYYY-MM-DD": [trip, ...] }
      sortedWeekKeys: Array,   week-start keys, newest first
      activeWeekKey:  string,  "YYYY-MM-DD" or "all"
      dataSource:     string,  "relay_csv" | "mock"
    }
*/

function _initAmazonState(amazonData) {
    var trips          = (amazonData && amazonData.trips) || [];
    var weekGroups     = groupTripsByWeek(trips);
    var sortedWeekKeys = Object.keys(weekGroups).sort(function(a, b) { return b.localeCompare(a); });

    // Default: current week if it has data, else most recent week
    var cwk = currentWeekKey();
    var activeWeekKey = weekGroups[cwk] ? cwk : (sortedWeekKeys[0] || 'all');

    _amazonState = {
        trips:               trips,
        weekGroups:          weekGroups,
        sortedWeekKeys:      sortedWeekKeys,
        activeWeekKey:       activeWeekKey,
        dataSource:          (amazonData && amazonData.data_source) || 'mock',
        expandedDrivers:     new Set(),
        collapsedRevenue:    new Set(),
        collapsedDeductions: new Set(),
    };

    // ── DEBUG: log state summary to browser console ────────────────────────
    // Remove this block once weekly tabs are confirmed working.
    console.group('[Amazon DSP] State initialised');
    console.log('Total trips:', trips.length);
    console.log('Data source:', _amazonState.dataSource);
    console.log('Unique weeks detected:', sortedWeekKeys);
    console.log('Active week:', activeWeekKey);
    var sampleDates = trips.slice(0, 5).map(function(t) {
        return { driver: t.driver, trip_id: t.trip_id, trip_date: t.trip_date, revenue: t.trip_revenue };
    });
    console.log('Sample trips (first 5):', sampleDates);
    var driverTotals = {};
    trips.forEach(function(t) {
        if (!t.driver) return;
        driverTotals[t.driver] = (driverTotals[t.driver] || 0) + (parseFloat(t.trip_revenue) || 0);
    });
    console.log('Driver totals (all weeks):', driverTotals);
    console.groupEnd();
    // ── END DEBUG ──────────────────────────────────────────────────────────
}

// ═══════════════════════════════════════════════════════════════════════════
// AMAZON DSP — DRIVER EXPENSE CONFIG
// ═══════════════════════════════════════════════════════════════════════════
//
// Per-driver weekly expense rules and default payout percentages.
//
// hasFuel {boolean}        — true = fuel line item shown (TBD until injected)
// expenses {Array}         — fixed weekly deductions for this driver
// defaultPayoutPct {number}— payout fraction (0.30 = 30%) used until overridden
//
// TO ADD A DRIVER: add an entry keyed by their exact name from the relay CSV.
// UNKNOWN DRIVERS: fall through to AMAZON_DEFAULT_DRIVER_CONFIG (no expenses, 25%).
//
// FORMULA: final_payout = (gross_revenue − total_expenses) × payout_pct
// ═══════════════════════════════════════════════════════════════════════════

var AMAZON_DRIVER_CONFIG = {
    'Chad Salerno': {
        hasFuel:         true,
        expenses: [
            { type: 'TABLET',      label: 'Tablet',      amount: 20,  source: 'fixed', status: 'confirmed' },
            { type: 'ELD',         label: 'ELD',         amount: 20,  source: 'fixed', status: 'confirmed' },
            { type: 'INSURANCE',   label: 'Insurance',   amount: 300, source: 'fixed', status: 'confirmed' },
            { type: 'PLATES',      label: 'Plates',      amount: 75,  source: 'fixed', status: 'confirmed' },
            // MAINTENANCE: update `amount` when the weekly figure is known. Default 0 = no deduction until set.
            { type: 'MAINTENANCE', label: 'Maintenance', amount: 0,   source: 'fixed', status: 'confirmed' },
            // FUEL appended dynamically by getDriverWeeklyExpenses()
        ],
        payoutPresets:    [35, 38, 40, 42],
        defaultPayoutPct: 0.35,
    },
    'Roy Workman': {
        hasFuel:         false,  // Roy has no fuel deduction
        expenses: [
            { type: 'INSURANCE', label: 'Insurance', amount: 250, source: 'fixed', status: 'confirmed' },
        ],
        payoutPresets:    [85, 88],
        defaultPayoutPct: 0.85,
    },
};

// Fallback for any driver not explicitly listed above.
var AMAZON_DEFAULT_DRIVER_CONFIG = {
    hasFuel:         false,
    expenses:        [],
    payoutPresets:    [25, 27, 28, 30],
    defaultPayoutPct: 0.25,
};

// ── Fuel Store ─────────────────────────────────────────────────────────────
// Keys:   "driverName::weekStart"  (e.g. "Chad Salerno::2026-03-08")
// Values: { amount: number, source: string }
//
// source values:
//   'manual'      — amount set manually in this file (used until email import is live)
//   'fuel-report' — amount parsed from the weekly email fuel report
//
// ── EMAIL IMPORT HOOK ──────────────────────────────────────────────────────
// When Chad's weekly fuel report arrives via email, call:
//   injectFuelDeduction("Chad Salerno", "2026-03-17", 412.50, "fuel-report");
//   _renderAmazonSection();
// The email-based call will overwrite any prior manual entry for the same week.
// Only drivers with hasFuel=true will show a fuel line item.
// ──────────────────────────────────────────────────────────────────────────
var AMAZON_FUEL_STORE = {};

// ── Manual fuel entries ────────────────────────────────────────────────────
// These override the TBD placeholder until email-based import is wired up.
// weekStart = Sunday of the week (YYYY-MM-DD).
// To update: change the amount and reload the page.
// To remove: delete the line (week reverts to TBD).
// ──────────────────────────────────────────────────────────────────────────
(function seedManualFuel() {
    var entries = [
        // Chad Salerno — manual fuel receipts
        { driver: 'Chad Salerno', weekStart: '2026-03-08', amount: 359.78  },
        { driver: 'Chad Salerno', weekStart: '2026-03-15', amount: 1284.78 },
    ];
    entries.forEach(function(e) {
        AMAZON_FUEL_STORE[e.driver + '::' + e.weekStart] = { amount: e.amount, source: 'manual' };
    });
}());

// ── Payout Percentage Store ────────────────────────────────────────────────
// Keys:   "driverName::weekStart"  (e.g. "Chad Salerno::2026-03-17")
// Values: number — payout fraction (0.30 = 30%)
//
// Persists across page loads via localStorage (key: 'bcat_amazon_payout_store').
// Format: { "driverName::YYYY-MM-DD": 0.35, ... }
// ──────────────────────────────────────────────────────────────────────────
var AMAZON_PAYOUT_STORE = (function() {
    try {
        var saved = localStorage.getItem('bcat_amazon_payout_store');
        return saved ? JSON.parse(saved) : {};
    } catch(e) {
        return {};
    }
}());

// Global fallback presets (used only when a driver has no payoutPresets in their config).
var AMAZON_PAYOUT_PRESETS = [25, 27, 28, 30];

// ── Helper functions ───────────────────────────────────────────────────────

/**
 * EMAIL FUEL IMPORT ADAPTER
 * Call this when the weekly email fuel report is parsed.
 * After calling, trigger _renderAmazonSection() to refresh the UI.
 * An email-based call will overwrite any manual entry for the same week.
 *
 * @param {string} driverName  exact name as it appears in the relay CSV
 * @param {string} weekStart   "YYYY-MM-DD" Sunday that starts the week
 * @param {number} amount      fuel cost in USD
 * @param {string} [source]    'fuel-report' (default) or 'manual'
 */
function injectFuelDeduction(driverName, weekStart, amount, source) {
    AMAZON_FUEL_STORE[driverName + '::' + weekStart] = {
        amount: Number(amount),
        source: source || 'fuel-report',
    };
}

/** Returns the config for driverName, or the default if not found. */
function getDriverConfig(driverName) {
    return AMAZON_DRIVER_CONFIG[driverName] || AMAZON_DEFAULT_DRIVER_CONFIG;
}

/**
 * Returns fixed expense line items for a driver (no fuel).
 * @param {string} driverName
 * @returns {Array<ExpenseRecord>}
 */
function getDriverFixedExpenses(driverName) {
    return getDriverConfig(driverName).expenses.map(function(e) {
        return {
            driverName:    driverName,
            deductionType: e.type,
            label:         e.label,
            amount:        e.amount,
            source:        e.source,
            status:        e.status,
        };
    });
}

/**
 * Returns the fuel line item for a driver/week, or null if driver has no fuel.
 * Shows TBD when weekStart is "all" or fuel has not been injected yet.
 *
 * @param {string} driverName
 * @param {string} weekStart  "YYYY-MM-DD" or "all"
 * @returns {ExpenseRecord|null}
 */
function getDriverWeeklyFuel(driverName, weekStart) {
    if (!getDriverConfig(driverName).hasFuel) return null;
    var key      = driverName + '::' + weekStart;
    var stored   = (weekStart !== 'all') ? AMAZON_FUEL_STORE[key] : undefined;
    var hasValue = stored != null;
    // stored is { amount, source } — fall back gracefully if a bare number was written directly
    var amount = hasValue ? (typeof stored === 'object' ? stored.amount : Number(stored)) : null;
    var source = hasValue ? (typeof stored === 'object' ? stored.source : 'fuel-report') : 'fuel-report';
    return {
        driverName:    driverName,
        deductionType: 'FUEL',
        label:         'Fuel',
        amount:        amount,
        source:        source,
        status:        hasValue ? 'confirmed' : 'TBD',
    };
}

/**
 * Returns true if the driver has a fuel line item not yet injected for this week.
 * Always false for Roy Workman (hasFuel=false).
 */
function hasPendingFuel(driverName, weekStart) {
    var fuel = getDriverWeeklyFuel(driverName, weekStart);
    return fuel != null && (fuel.status === 'TBD' || fuel.amount == null);
}

/**
 * Returns all expense line items for a driver/week: fixed items + fuel (if applicable).
 * @param {string} driverName
 * @param {string} weekStart
 * @returns {Array<ExpenseRecord>}
 */
function getDriverWeeklyExpenses(driverName, weekStart) {
    var fixed = getDriverFixedExpenses(driverName);
    var fuel  = getDriverWeeklyFuel(driverName, weekStart);
    return fuel ? fixed.concat([fuel]) : fixed;
}

/**
 * Sums confirmed expense amounts. TBD fuel is treated as $0 but flagged.
 * @param {Array<ExpenseRecord>} expenses
 * @returns {{ total: number, hasPendingFuel: boolean }}
 */
function calculateExpenseSubtotal(expenses) {
    var total   = 0;
    var pending = false;
    (expenses || []).forEach(function(e) {
        if (e.status === 'TBD' || e.amount == null) {
            if (e.source === 'fuel-report') pending = true;
        } else {
            total += parseFloat(e.amount) || 0;
        }
    });
    return { total: Math.round(total * 100) / 100, hasPendingFuel: pending };
}

/**
 * Returns the payout percentage for a driver/week (from store or driver default).
 * @param {string} driverName
 * @param {string} weekStart
 * @returns {number}  e.g. 0.30
 */
function getWeeklyPayoutPercentage(driverName, weekStart) {
    var key = driverName + '::' + weekStart;
    return AMAZON_PAYOUT_STORE[key] != null
        ? AMAZON_PAYOUT_STORE[key]
        : getDriverConfig(driverName).defaultPayoutPct;
}

/**
 * Stores the payout percentage for a driver/week. Clamps to [0, 1].
 * @param {string} driverName
 * @param {string} weekStart
 * @param {number} pct  fraction (0.30 = 30%)
 */
function setWeeklyPayoutPercentage(driverName, weekStart, pct) {
    AMAZON_PAYOUT_STORE[driverName + '::' + weekStart] = Math.max(0, Math.min(1, Number(pct) || 0));
    try { localStorage.setItem('bcat_amazon_payout_store', JSON.stringify(AMAZON_PAYOUT_STORE)); } catch(e) {}
}

/**
 * Net revenue = gross revenue − confirmed expense subtotal.
 * @param {number} revenue
 * @param {number} expenseSubtotal
 * @returns {number}
 */
function calculateNetRevenue(revenue, expenseSubtotal) {
    return Math.round((revenue - expenseSubtotal) * 100) / 100;
}

/**
 * Final payout = net revenue × payout percentage. Never negative.
 * @param {number} netRevenue
 * @param {number} pct  fraction
 * @returns {number}
 */
function calculateFinalPayout(netRevenue, pct) {
    return Math.round(Math.max(0, netRevenue * pct) * 100) / 100;
}

// ── Pay-split calculation helpers ─────────────────────────────────────────
//
// Business rule:
//   payout percentage = DRIVER'S share
//   company percentage = 1 - driver percentage
//
//   net_after_expenses = revenue - expenses
//   driver_pay         = net_after_expenses * driver_pct   (never negative)
//   company_pay        = net_after_expenses - driver_pay
//
// Negative net: driver_pay clamps to 0; company absorbs the full loss.
//   e.g. net = -$100, driver_pct = 35%  →  driver_pay = $0, company_pay = -$100

/**
 * @param {number} revenue
 * @param {number} expenses
 * @returns {number}
 */
function calculateNetAfterExpenses(revenue, expenses) {
    return Math.round((revenue - expenses) * 100) / 100;
}

/**
 * @param {number} netAfterExpenses
 * @param {number} driverPct  fraction (0.35 = 35%)
 * @returns {number}  never negative
 */
function calculateDriverPay(netAfterExpenses, driverPct) {
    return Math.round(Math.max(0, netAfterExpenses * driverPct) * 100) / 100;
}

/**
 * @param {number} netAfterExpenses
 * @param {number} driverPay
 * @returns {number}  may be negative if net is negative
 */
function calculateCompanyPay(netAfterExpenses, driverPay) {
    return Math.round((netAfterExpenses - driverPay) * 100) / 100;
}

// ── Shared sub-section component ──────────────────────────────────────────

/**
 * Reusable collapsible sub-section used inside each driver card.
 * Both Revenue and Deductions use this same component.
 *
 * Collapsed state: add class 'sub-collapsed' to hide the body and rotate chevron.
 * Default state: body is visible (open).
 *
 * @param {string}  driver      driver name (for data-driver attribute)
 * @param {string}  sub         "revenue" | "deductions" (for data-sub attribute)
 * @param {string}  titleHTML   left-side label HTML
 * @param {string}  metaHTML    middle metadata HTML (e.g. trip count)
 * @param {string}  totalHTML   right-side total HTML
 * @param {string}  bodyHTML    collapsible content
 * @param {boolean} isCollapsed whether to render collapsed
 */
function _buildSubSection(driver, sub, titleHTML, metaHTML, totalHTML, bodyHTML, isCollapsed) {
    var safeDriver = driver.replace(/"/g, '&quot;');
    return '<div class="amazon-sub-section' + (isCollapsed ? ' sub-collapsed' : '') + '" data-sub="' + sub + '" data-driver="' + safeDriver + '">' +
        '<div class="amazon-sub-header">' +
            '<span class="amazon-sub-chevron"></span>' +
            '<span class="amazon-sub-title">' + titleHTML + '</span>' +
            '<span class="amazon-sub-meta">' + metaHTML + '</span>' +
            '<span class="amazon-sub-total">' + totalHTML + '</span>' +
        '</div>' +
        '<div class="amazon-sub-body">' + bodyHTML + '</div>' +
    '</div>';
}

/**
 * Builds the revenue trip table HTML used inside the Revenue sub-section.
 */
function _buildRevenueTripTable(trips, total, count) {
    var rowsHTML = trips.map(function(t) {
        var rev = t.trip_revenue != null ? t.trip_revenue
                : t.gross_load_revenue != null ? t.gross_load_revenue
                : (t.bcat_revenue || 0);
        return '<tr>' +
            '<td class="trip-id-cell">' + (t.trip_id || '\u2014') + '</td>' +
            '<td>' + (t.trip_date || '\u2014') + '</td>' +
            '<td class="positive">' + money(rev) + '</td>' +
            '<td><span class="amazon-status-chip">' + (t.status || '\u2014') + '</span></td>' +
            '</tr>';
    }).join('');

    return '<div class="table-wrap">' +
        '<table class="amazon-trip-table">' +
        '<thead><tr><th>Trip ID</th><th>Date</th><th>Revenue</th><th>Status</th></tr></thead>' +
        '<tbody>' + rowsHTML + '</tbody>' +
        '<tfoot><tr class="driver-total-row">' +
            '<td colspan="2">Revenue subtotal</td>' +
            '<td class="positive"><strong>' + money(total) + '</strong></td>' +
            '<td>' + count + ' trip' + (count !== 1 ? 's' : '') + '</td>' +
        '</tr></tfoot>' +
        '</table></div>';
}

/**
 * Builds the expenses table HTML used inside the Expenses sub-section.
 * TBD fuel rows show an amber badge; confirmed rows show the deducted amount.
 * Each row: Category | Source | Amount
 */
function _buildDeductionsTable(expenses) {
    var rowsHTML = expenses.map(function(e) {
        var isTbd    = e.status === 'TBD' || e.amount == null;
        var amtCell  = isTbd
            ? '<span class="amazon-tbd-badge">TBD</span>'
            : '<span class="deduction-amount">-' + money(e.amount) + '</span>';
        var srcBadge = '<span class="amazon-source-badge amazon-source-' + e.source + '">' + e.source + '</span>';
        return '<tr class="' + (isTbd ? 'deduction-row-tbd' : '') + '">' +
            '<td>' + e.label + '</td>' +
            '<td>' + srcBadge + '</td>' +
            '<td class="deduction-amount-cell">' + amtCell + '</td>' +
            '</tr>';
    }).join('');

    var totals   = calculateExpenseSubtotal(expenses);
    var pending  = totals.hasPendingFuel;
    var footNote = pending ? ' <span class="amazon-tbd-badge">\u26a0 + Fuel TBD</span>' : '';

    return '<div class="table-wrap">' +
        '<table class="amazon-trip-table amazon-ded-table">' +
        '<thead><tr><th>Category</th><th>Source</th><th>Amount</th></tr></thead>' +
        '<tbody>' + rowsHTML + '</tbody>' +
        '<tfoot><tr class="driver-total-row">' +
            '<td colspan="2">Expenses subtotal</td>' +
            '<td class="deduction-amount-cell"><strong>-' + money(totals.total) + '</strong>' + footNote + '</td>' +
        '</tr></tfoot>' +
        '</table></div>';
}

function _getActiveWeekTrips() {
    if (!_amazonState) return [];
    if (_amazonState.activeWeekKey === 'all') return _amazonState.trips;
    return _amazonState.weekGroups[_amazonState.activeWeekKey] || [];
}

function _renderAmazonSection() {
    var container = document.getElementById('amazon-panel-content') || document.getElementById('amazon-section');
    if (!container || !_amazonState) return;

    var trips         = _getActiveWeekTrips();
    var activeWeekKey = _amazonState.activeWeekKey;
    var dataSource    = _amazonState.dataSource || 'mock';

    container.innerHTML =
        '<div class="section-title amazon-section-title">Amazon DSP \u2014 Weekly Performance</div>' +
        _buildAmazonWeekTabs() +
        _buildAmazonSummaryCards(trips, activeWeekKey, dataSource) +
        _buildDriverList(trips, dataSource);

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

// ── Summary calculation helpers ────────────────────────────────────────────

/**
 * Converts a local Date to a YYYY-MM-DD week-key string (same format as groupTripsByWeek).
 * @param {Date} d
 * @returns {string}
 */
function _dateToWeekKey(d) {
    return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0');
}

/**
 * Full pay-split summary for one driver over the selected scope.
 *
 * For a single week: expenses applied once; payout % from store (or default).
 * For "all" weeks: groups this driver's trips by week, accumulates revenue,
 *   expenses, and driver pay week-by-week (so each week's pct is respected),
 *   then derives company pay from the cumulative net.
 *
 * Negative net: driver_pay clamps to 0; company absorbs the full loss.
 * Fuel TBD: expense total excludes TBD fuel; isPending flag is set.
 *
 * @param {string} driverName
 * @param {Array}  driverTrips  trips already filtered to the active scope
 * @param {string} weekKey      YYYY-MM-DD or 'all'
 * @returns {{
 *   driver, revenue, expenses, netAfterExpenses,
 *   driverPct, companyPct, driverPay, companyPay,
 *   isPending, isAllWeeks
 * }}
 */
function calculateDriverSummary(driverName, driverTrips, weekKey) {
    var isPending = false;

    if (weekKey === 'all') {
        // Group this driver's trips by week
        var byWeek = {};
        driverTrips.forEach(function(t) {
            var dateVal = t[AMAZON_TRIP_DATE_FIELD] || t['week'];
            if (!dateVal) return;
            var wk = _dateToWeekKey(getWeekStart(dateVal));
            if (!byWeek[wk]) byWeek[wk] = [];
            byWeek[wk].push(t);
        });

        var totalRevenue = 0, totalExpenses = 0, totalDriverPay = 0;
        Object.keys(byWeek).forEach(function(wk) {
            var wkRev  = calculateDriverTotals(byWeek[wk]).total;
            var expRes = calculateExpenseSubtotal(getDriverWeeklyExpenses(driverName, wk));
            if (expRes.hasPendingFuel) isPending = true;
            var wkExp  = expRes.total;
            var wkNet  = wkRev - wkExp;
            var wkPct  = getWeeklyPayoutPercentage(driverName, wk);
            totalRevenue   += wkRev;
            totalExpenses  += wkExp;
            totalDriverPay += calculateDriverPay(wkNet, wkPct);
        });

        totalRevenue   = Math.round(totalRevenue   * 100) / 100;
        totalExpenses  = Math.round(totalExpenses  * 100) / 100;
        totalDriverPay = Math.round(totalDriverPay * 100) / 100;
        var net        = calculateNetAfterExpenses(totalRevenue, totalExpenses);
        var companyPay = calculateCompanyPay(net, totalDriverPay);
        // Representative pct for display in "all" view = driver's configured default
        var driverPct  = getDriverConfig(driverName).defaultPayoutPct;

        return {
            driver: driverName, revenue: totalRevenue, expenses: totalExpenses,
            netAfterExpenses: net, driverPct: driverPct,
            companyPct: Math.round((1 - driverPct) * 100) / 100,
            driverPay: totalDriverPay, companyPay: companyPay,
            isPending: isPending, isAllWeeks: true,
        };
    }

    // Single week
    var revenue  = calculateDriverTotals(driverTrips).total;
    var expRes   = calculateExpenseSubtotal(getDriverWeeklyExpenses(driverName, weekKey));
    isPending    = expRes.hasPendingFuel;
    var expenses = Math.round(expRes.total * 100) / 100;
    var net      = calculateNetAfterExpenses(revenue, expenses);
    var driverPct  = getWeeklyPayoutPercentage(driverName, weekKey);
    var driverPay  = calculateDriverPay(net, driverPct);
    var companyPay = calculateCompanyPay(net, driverPay);

    return {
        driver: driverName, revenue: revenue, expenses: expenses,
        netAfterExpenses: net, driverPct: driverPct,
        companyPct: Math.round((1 - driverPct) * 100) / 100,
        driverPay: driverPay, companyPay: companyPay,
        isPending: isPending, isAllWeeks: false,
    };
}

/**
 * Returns calculateDriverSummary for every driver in the current trip set.
 * @param {Array}  trips    already filtered to active scope
 * @param {string} weekKey  YYYY-MM-DD or 'all'
 * @returns {Array<DriverSummary>}
 */
function calculateAllDriverSummaries(trips, weekKey) {
    return groupTripsByDriver(trips).map(function(d) {
        return calculateDriverSummary(d.driver, d.trips, weekKey);
    });
}

/**
 * Sums all pay-split fields across every driver summary.
 * company_pay = netAfterExpenses - totalDriverPay  (derived here, not summed,
 * to avoid rounding drift from summing per-driver company pays).
 * @param {Array} driverSummaries  output of calculateAllDriverSummaries
 * @returns {{ revenue, expenses, netAfterExpenses, driverPay, companyPay, isPending }}
 */
function calculateOverallAmazonTotals(driverSummaries) {
    var rev = 0, exp = 0, dPay = 0, pending = false;
    driverSummaries.forEach(function(s) {
        rev   += s.revenue;
        exp   += s.expenses;
        dPay  += s.driverPay;
        if (s.isPending) pending = true;
    });
    rev  = Math.round(rev  * 100) / 100;
    exp  = Math.round(exp  * 100) / 100;
    dPay = Math.round(dPay * 100) / 100;
    var net  = calculateNetAfterExpenses(rev, exp);
    var cPay = calculateCompanyPay(net, dPay);
    return {
        revenue: rev, expenses: exp, netAfterExpenses: net,
        driverPay: dPay, companyPay: cPay, isPending: pending,
    };
}

function _buildAmazonSummaryCards(trips, activeWeekKey, dataSource) {
    var periodLabel = activeWeekKey === 'all' ? 'All Weeks' : (function() {
        var ws = getWeekStart(activeWeekKey);
        var we = getWeekEnd(activeWeekKey);
        return formatWeekLabel(ws, we);
    })();

    var notice = (dataSource === 'relay_csv')
        ? '<div class="amazon-live-notice">Live data \u2014 Amazon Relay CSV</div>'
        : '<div class="amazon-mock-notice">\u26a0 Mock data \u2014 upload <code>amazon_relay.csv</code> to see live trips</div>';

    var driverSummaries = calculateAllDriverSummaries(trips, activeWeekKey);
    var o               = calculateOverallAmazonTotals(driverSummaries);

    var provBadge = o.isPending ? '&nbsp;<span class="amazon-tbd-badge">\u26a0 Provisional</span>' : '';

    // ── 5 overall KPI cards ────────────────────────────────────────────────
    var overallCards =
        '<div class="kpi-grid amazon-overall-kpi">' +
            _kpiCard('Total Revenue',        money(o.revenue),         'positive') +
            _kpiCard('Total Expenses',       money(o.expenses),        '') +
            _kpiCard('Net After Expenses',   money(o.netAfterExpenses) + provBadge,
                                             o.netAfterExpenses >= 0 ? 'positive' : 'amazon-negative') +
            _kpiCard('Total Driver Pay',     money(o.driverPay)  + provBadge, 'positive') +
            _kpiCard('Total Company Pay',    money(o.companyPay) + provBadge,
                                             o.companyPay >= 0 ? 'positive' : 'amazon-negative') +
        '</div>';

    // ── Per-driver summary cards ───────────────────────────────────────────
    var driverCards = driverSummaries.map(function(s) {
        var driverPctInt  = Math.round(s.driverPct  * 100);
        var companyPctInt = Math.round(s.companyPct * 100);
        var pctNote = s.isAllWeeks
            ? '<span class="amazon-driver-kpi-pct-note">(default ' + driverPctInt + '% / ' + companyPctInt + '%; may vary per week)</span>'
            : '';
        var sBadge  = s.isPending ? '&nbsp;<span class="amazon-tbd-badge">\u26a0 Prov.</span>' : '';

        return '<div class="amazon-driver-kpi-card">' +
            '<div class="amazon-driver-kpi-name">' + s.driver + '</div>' +
            // Revenue / Expenses / Net
            '<div class="amazon-driver-kpi-row">' +
                '<span class="amazon-driver-kpi-label">Revenue</span>' +
                '<span class="positive">' + money(s.revenue) + '</span>' +
            '</div>' +
            '<div class="amazon-driver-kpi-row">' +
                '<span class="amazon-driver-kpi-label">Expenses</span>' +
                '<span>' + money(s.expenses) + '</span>' +
            '</div>' +
            '<div class="amazon-driver-kpi-row amazon-driver-kpi-net">' +
                '<span class="amazon-driver-kpi-label">Net After Expenses</span>' +
                '<span class="' + (s.netAfterExpenses >= 0 ? 'positive' : 'amazon-negative') + '">' +
                    money(s.netAfterExpenses) + sBadge +
                '</span>' +
            '</div>' +
            // Pay split
            '<div class="amazon-driver-kpi-row amazon-driver-kpi-split-header">' +
                '<span class="amazon-driver-kpi-label">Driver Pay</span>' +
                '<span class="amazon-driver-kpi-pct">' + driverPctInt + '%</span>' +
                '<span class="positive">' + money(s.driverPay) + sBadge + '</span>' +
            '</div>' +
            '<div class="amazon-driver-kpi-row">' +
                '<span class="amazon-driver-kpi-label">Company Pay</span>' +
                '<span class="amazon-driver-kpi-pct">' + companyPctInt + '%</span>' +
                '<span class="' + (s.companyPay >= 0 ? 'positive' : 'amazon-negative') + '">' +
                    money(s.companyPay) + sBadge +
                '</span>' +
            '</div>' +
            (pctNote ? '<div class="amazon-driver-kpi-row">' + pctNote + '</div>' : '') +
        '</div>';
    }).join('');

    var driverRow = driverSummaries.length
        ? '<div class="amazon-driver-kpi-row-wrap">' + driverCards + '</div>'
        : '';

    return '<div class="amazon-period-label">' + periodLabel + '</div>' +
        notice +
        overallCards +
        driverRow;
}

/** Small helper: builds a single .card for the kpi-grid. */
function _kpiCard(label, valueHTML, valueClass) {
    return '<div class="card">' +
        '<div class="label">' + label + '</div>' +
        '<div class="value ' + valueClass + '">' + valueHTML + '</div>' +
    '</div>';
}

// ═══════════════════════════════════════════════════════════════════════════
// AMAZON DSP — DRIVER AGGREGATION UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Groups qualifying trips by driver, sorted by total revenue descending.
 * Each driver's trips are sorted by trip_date ascending.
 *
 * Revenue field priority: trip_revenue (relay CSV) → gross_load_revenue → bcat_revenue.
 * ASSUMPTION: trips passed in are already filtered (qualifying only).
 *
 * @param {Array} trips
 * @returns {Array}  [{ driver, trips, count, total }, ...] sorted by total desc
 */
function groupTripsByDriver(trips) {
    var byDriver = {};
    (trips || []).forEach(function(t) {
        var name = (t.driver || 'Unknown').trim();
        if (!byDriver[name]) byDriver[name] = [];
        byDriver[name].push(t);
    });
    return Object.keys(byDriver)
        .map(function(driver) {
            var driverTrips = byDriver[driver].slice().sort(function(a, b) {
                return (a.trip_date || '').localeCompare(b.trip_date || '');
            });
            var totals = calculateDriverTotals(driverTrips);
            return { driver: driver, trips: driverTrips, count: totals.count, total: totals.total };
        })
        .sort(function(a, b) { return b.total - a.total; });
}

/**
 * Calculates total revenue and trip count for a set of trips.
 *
 * Revenue field priority: trip_revenue (relay CSV) → gross_load_revenue → bcat_revenue → 0.
 * ASSUMPTION: All totals use only qualifying trips (> $100 filter applied on backend).
 *
 * @param {Array} trips
 * @returns {{ total: number, count: number }}
 */
function calculateDriverTotals(trips) {
    var total = (trips || []).reduce(function(s, t) {
        var rev = t.trip_revenue != null ? t.trip_revenue
                : t.gross_load_revenue != null ? t.gross_load_revenue
                : (t.bcat_revenue || 0);
        return s + (parseFloat(rev) || 0);
    }, 0);
    return { total: Math.round(total * 100) / 100, count: (trips || []).length };
}

/**
 * Builds the payout percentage segmented control for one driver card.
 * Preset buttons + a custom numeric input.
 * In "all weeks" mode the control is replaced with a static label.
 *
 * @param {string}  driverName
 * @param {string}  weekKey     "YYYY-MM-DD" or "all"
 * @param {number}  currentPct  current fraction (0.30)
 * @param {boolean} isAllWeeks
 * @returns {string} HTML
 */
function _buildPayoutPctControl(driverName, weekKey, currentPct, isAllWeeks) {
    var safeDriver    = driverName.replace(/"/g, '&quot;');
    var currentPctInt = Math.round(currentPct * 100);
    var presets       = getDriverConfig(driverName).payoutPresets || AMAZON_PAYOUT_PRESETS;

    if (isAllWeeks) {
        return '<div class="amazon-payout-control">' +
            '<span class="amazon-payout-label">Payout %</span>' +
            '<span class="amazon-payout-all-note">Select a week to adjust</span>' +
        '</div>';
    }

    var presetsHTML = presets.map(function(pInt) {
        var isActive = (pInt === currentPctInt);
        return '<button class="amazon-payout-btn' + (isActive ? ' active' : '') + '" ' +
            'data-driver="' + safeDriver + '" data-week="' + weekKey + '" data-pct="' + (pInt / 100) + '">' +
            pInt + '%' +
        '</button>';
    }).join('');

    var isCustom  = presets.indexOf(currentPctInt) === -1;
    var customVal = isCustom ? currentPctInt : '';

    return '<div class="amazon-payout-control">' +
        '<span class="amazon-payout-label">Payout %</span>' +
        '<div class="amazon-payout-presets">' + presetsHTML + '</div>' +
        '<input type="number" class="amazon-payout-custom" ' +
            'data-driver="' + safeDriver + '" data-week="' + weekKey + '" ' +
            'min="0" max="100" step="1" placeholder="other" ' +
            'value="' + customVal + '" title="Enter a custom payout %">' +
        '<button class="amazon-payout-save-btn" ' +
            'data-driver="' + safeDriver + '" data-week="' + weekKey + '" ' +
            'title="Save custom payout %">Save</button>' +
    '</div>';
}

/**
 * Builds the collapsible per-driver list view.
 *
 * Each driver card shows:
 *   Header:     name · trip count · final payout · CSV download
 *   Body:       [default-config note if auto-discovered]
 *               Payout % control (presets + custom + Save)
 *               Revenue (collapsible) · Expenses (collapsible)
 *               Net Revenue row · Final Payout row
 *
 * Formula: final_payout = (gross_revenue − expense_subtotal) × payout_pct
 * Provisional flag shown when Chad's fuel has not yet been injected.
 */
function _buildDriverList(trips, dataSource) {
    var drivers    = groupTripsByDriver(trips);
    var weekKey    = _amazonState.activeWeekKey;
    var isAllWeeks = weekKey === 'all';

    if (!drivers.length) {
        return '<div class="table-card"><div class="empty-state">No qualifying trips for this period.</div></div>';
    }

    var overallTotals = calculateDriverTotals(trips);

    var overallBar =
        '<div class="amazon-overall-total">' +
            '<div>' +
                '<strong>' + integerFmt(overallTotals.count) + '</strong> qualifying trip' +
                (overallTotals.count !== 1 ? 's' : '') +
                ' across <strong>' + drivers.length + '</strong> driver' +
                (drivers.length !== 1 ? 's' : '') +
            '</div>' +
            '<div>Total Revenue: <strong class="positive">' + money(overallTotals.total) + '</strong></div>' +
        '</div>';

    var driversHTML = drivers.map(function(d) {
        var isExpanded   = _amazonState.expandedDrivers.has(d.driver);
        var revCollapsed = _amazonState.collapsedRevenue.has(d.driver);
        var dedCollapsed = _amazonState.collapsedDeductions.has(d.driver);
        var safeDriver   = d.driver.replace(/"/g, '&quot;');

        // Auto-discover: flag drivers not in explicit config
        var isDefaultConfig = !AMAZON_DRIVER_CONFIG.hasOwnProperty(d.driver);

        // Expenses
        var expenses   = getDriverWeeklyExpenses(d.driver, weekKey);
        var expTotals  = calculateExpenseSubtotal(expenses);
        var pending    = expTotals.hasPendingFuel;

        // Payout calculation
        var pct        = isAllWeeks
            ? getDriverConfig(d.driver).defaultPayoutPct
            : getWeeklyPayoutPercentage(d.driver, weekKey);
        var netRevenue  = calculateNetRevenue(d.total, expTotals.total);
        var finalPayout = calculateFinalPayout(netRevenue, pct);

        // Header shows final payout (provisional badge if fuel TBD)
        var headerPayoutLabel = pending
            ? '<span class="positive">' + money(finalPayout) + '</span><span class="amazon-tbd-badge">\u26a0 Fuel TBD</span>'
            : '<span class="positive">' + money(finalPayout) + '</span>';

        var pctDisplay = Math.round(pct * 100);
        var header =
            '<div class="amazon-driver-header">' +
                '<span class="amazon-driver-chevron"></span>' +
                '<span class="amazon-driver-name">' + d.driver + '</span>' +
                '<span class="amazon-driver-meta">' +
                    d.count + ' trip' + (d.count !== 1 ? 's' : '') +
                    ' &nbsp;&middot;&nbsp; <span class="amazon-driver-pct-badge">' + pctDisplay + '%</span>' +
                '</span>' +
                '<span class="amazon-driver-total">' + headerPayoutLabel + '</span>' +
                '<button class="amazon-download-btn" data-driver="' + safeDriver + '" title="Download trips as CSV">' +
                    '\u2193 CSV' +
                '</button>' +
            '</div>';

        // Revenue sub-section
        var revMeta    = d.count + ' trip' + (d.count !== 1 ? 's' : '');
        var revTotal   = '<span class="positive">' + money(d.total) + '</span>';
        var revBody    = _buildRevenueTripTable(d.trips, d.total, d.count);
        var revSection = _buildSubSection(d.driver, 'revenue', 'Revenue', revMeta, revTotal, revBody, revCollapsed);

        // Expenses sub-section
        var expMeta    = expenses.length + ' item' + (expenses.length !== 1 ? 's' : '');
        var expTotalLabel = pending
            ? '<span class="deduction-amount">-' + money(expTotals.total) + '</span><span class="amazon-tbd-badge">+ Fuel TBD</span>'
            : '<span class="deduction-amount">-' + money(expTotals.total) + '</span>';
        var expBody    = _buildDeductionsTable(expenses);
        var dedSection = _buildSubSection(d.driver, 'deductions', 'Expenses', expMeta, expTotalLabel, expBody, dedCollapsed);

        // Net revenue row (after expenses, before payout %)
        var netRow =
            '<div class="amazon-net-row">' +
                '<span class="amazon-net-label">Net Revenue</span>' +
                '<span>' +
                    '<strong class="positive">' + money(netRevenue) + '</strong>' +
                    (pending ? '&nbsp;<span class="amazon-tbd-badge">\u26a0 Provisional</span>' : '') +
                '</span>' +
            '</div>';

        // Payout % control (at top of body)
        var pctControl = _buildPayoutPctControl(d.driver, weekKey, pct, isAllWeeks);

        // Default-config notice for auto-discovered drivers
        var defaultConfigNote = isDefaultConfig
            ? '<div class="amazon-default-config-note">\u2139 New driver \u2014 using default config (no expenses, ' +
              Math.round(AMAZON_DEFAULT_DRIVER_CONFIG.defaultPayoutPct * 100) + '% payout)</div>'
            : '';

        // Final payout row
        var finalRow =
            '<div class="amazon-final-payout-row' + (pending ? ' provisional' : '') + '">' +
                '<span class="amazon-net-label">Final Payout <span class="amazon-pct-hint">(' + pctDisplay + '%)</span></span>' +
                '<span>' +
                    '<strong class="positive">' + money(finalPayout) + '</strong>' +
                    (pending ? '&nbsp;<span class="amazon-tbd-badge">\u26a0 Provisional</span>' : '') +
                '</span>' +
            '</div>';

        return '<div class="amazon-driver-section' + (isExpanded ? ' expanded' : '') + '" data-driver="' + safeDriver + '">' +
            header +
            '<div class="amazon-driver-body">' +
                defaultConfigNote +
                pctControl +
                revSection +
                dedSection +
                netRow +
                finalRow +
            '</div>' +
        '</div>';
    }).join('');

    return overallBar + '<div class="table-card amazon-driver-list">' + driversHTML + '</div>';
}

/**
 * Generates and downloads a CSV file for one driver's trips.
 * Columns: Trip ID, Date, Revenue, Status
 * Filename: driver-name-YYYY-MM-DD.csv  (week start date, or "all-weeks")
 */
function _downloadDriverCsv(driverName, driverTrips, weekKey) {
    var weekLabel = (weekKey === 'all') ? 'all-weeks' : weekKey;
    var safeName  = driverName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    var filename  = safeName + '-' + weekLabel + '.csv';

    var escape = function(v) { return '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'; };

    var header = ['Trip ID', 'Date', 'Revenue', 'Status'].join(',');
    var rows = driverTrips.map(function(t) {
        var rev = t.trip_revenue != null ? t.trip_revenue
                : t.gross_load_revenue != null ? t.gross_load_revenue
                : (t.bcat_revenue || 0);
        return [
            escape(t.trip_id),
            escape(t.trip_date),
            parseFloat(rev).toFixed(2),
            escape(t.status)
        ].join(',');
    });

    var csv  = [header].concat(rows).join('\r\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function _attachAmazonEvents(container) {
    // Week tab clicks
    container.querySelectorAll('.amazon-week-tab').forEach(function(btn) {
        btn.addEventListener('click', function() {
            _amazonState.activeWeekKey = btn.dataset.weekKey;
            _renderAmazonSection();
        });
    });

    // Driver header clicks — toggle top-level expand/collapse
    container.querySelectorAll('.amazon-driver-header').forEach(function(header) {
        header.addEventListener('click', function(e) {
            if (e.target.closest('.amazon-download-btn')) return;
            var section    = header.closest('.amazon-driver-section');
            var driverName = section && section.dataset.driver;
            if (!driverName) return;

            if (_amazonState.expandedDrivers.has(driverName)) {
                _amazonState.expandedDrivers.delete(driverName);
                section.classList.remove('expanded');
            } else {
                _amazonState.expandedDrivers.add(driverName);
                section.classList.add('expanded');
            }
        });
    });

    // Sub-section header clicks — toggle Revenue or Deductions independently
    container.querySelectorAll('.amazon-sub-header').forEach(function(subHeader) {
        subHeader.addEventListener('click', function(e) {
            e.stopPropagation(); // don't bubble to driver header
            var subSection = subHeader.closest('.amazon-sub-section');
            if (!subSection) return;
            var driverName = subSection.dataset.driver;
            var sub        = subSection.dataset.sub; // "revenue" | "deductions"
            if (!driverName || !sub) return;

            var stateSet = (sub === 'revenue')
                ? _amazonState.collapsedRevenue
                : _amazonState.collapsedDeductions;

            if (stateSet.has(driverName)) {
                stateSet.delete(driverName);
                subSection.classList.remove('sub-collapsed');
            } else {
                stateSet.add(driverName);
                subSection.classList.add('sub-collapsed');
            }
        });
    });

    // Download button clicks
    container.querySelectorAll('.amazon-download-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var driverName = btn.dataset.driver;
            if (!driverName) return;
            var trips = _getActiveWeekTrips().filter(function(t) {
                return t.driver === driverName;
            });
            _downloadDriverCsv(driverName, trips, _amazonState.activeWeekKey);
        });
    });

    // Payout % preset button clicks
    container.querySelectorAll('.amazon-payout-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var pct = parseFloat(btn.dataset.pct);
            if (isNaN(pct)) return;
            setWeeklyPayoutPercentage(btn.dataset.driver, btn.dataset.week, pct);
            _renderAmazonSection();
        });
    });

    // Payout % custom input (commit on Enter or blur)
    container.querySelectorAll('.amazon-payout-custom').forEach(function(input) {
        function commit() {
            var val = parseFloat(input.value);
            if (isNaN(val) || val < 0 || val > 100) return;
            setWeeklyPayoutPercentage(input.dataset.driver, input.dataset.week, val / 100);
            _renderAmazonSection();
        }
        input.addEventListener('blur', commit);
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); commit(); }
        });
        // Stop click/mousedown from bubbling to the driver header toggle
        input.addEventListener('click',     function(e) { e.stopPropagation(); });
        input.addEventListener('mousedown', function(e) { e.stopPropagation(); });
    });

    // Payout % Save button — commits the custom input value
    container.querySelectorAll('.amazon-payout-save-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var control = btn.closest('.amazon-payout-control');
            var input   = control && control.querySelector('.amazon-payout-custom');
            if (!input) return;
            var val = parseFloat(input.value);
            if (isNaN(val) || val < 0 || val > 100) return;
            setWeeklyPayoutPercentage(btn.dataset.driver, btn.dataset.week, val / 100);
            _renderAmazonSection();
        });
        btn.addEventListener('mousedown', function(e) { e.stopPropagation(); });
    });
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
    // Ivan Equipment + Drivers: always re-render so localStorage changes are reflected
    if (company === 'ivan' && dept === 'marketing') {
        if (typeof IvanOpsApp !== 'undefined') IvanOpsApp.mountEquipment('ivan-equipment-content');
        return;
    }
    if (company === 'ivan' && dept === 'sales') {
        if (typeof IvanOpsApp !== 'undefined') IvanOpsApp.mountDrivers('ivan-drivers-content');
        return;
    }

    var key = company + ':' + dept;
    if (_initializedPanels[key]) return;
    _initializedPanels[key] = true;

    if (company === 'ivan' && dept === 'finance') {
        var container = document.getElementById('ivan-finance-content');
        if (container && _ivanState) _renderIvanFinancePanel(container, _ivanState);
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

// Dept tab labels vary by company — Ivan uses Equipment/Drivers instead of Marketing/Sales
var _DEPT_TAB_LABELS = {
    ivan:    { marketing: 'Equipment', sales: 'Drivers' },
    _default: { marketing: 'Marketing', sales: 'Sales'  }
};

function _updateDeptTabLabels(companyId) {
    var labels = _DEPT_TAB_LABELS[companyId] || _DEPT_TAB_LABELS._default;
    // Match on substring of onclick value — 'marketing' and 'sales' are unique dept ids
    var mktBtn = document.querySelector('.cc-dept-tab[onclick*="marketing"]');
    var salBtn = document.querySelector('.cc-dept-tab[onclick*="sales"]');
    if (mktBtn) mktBtn.textContent = labels.marketing;
    if (salBtn) salBtn.textContent = labels.sales;
}

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
    if (deptBar) deptBar.style.display = (companyId === 'agents' || companyId === 'aiden' || companyId === 'amazon') ? 'none' : 'flex';

    // Update dept tab labels for this company (e.g. Ivan: Equipment / Drivers)
    _updateDeptTabLabels(companyId);

    // Apply active dept within the newly shown company
    _applyDept();

    if (companyId === 'agents') loadAgents();
    if (companyId === 'amazon') _renderAmazonSection();
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
