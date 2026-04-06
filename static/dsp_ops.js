/**
 * static/dsp_ops.js
 * Amazon DSP Operations — per-driver expense tracking UI
 * Mounts into #amazon-panel-content when the Amazon DSP tab is opened.
 *
 * Architecture notes:
 *  - DspOpsApp is a singleton IIFE module exposing only { show }.
 *  - All state lives inside the closure — no globals polluted.
 *  - API calls go to /api/dsp/... routes in dashboard.py.
 *  - Data model: DspDriver + DriverExpense per week. Summary aggregates
 *    trip revenue from AmazonTrip records matched by driver name.
 *  - Future: driver read-only portal uses separate auth, same API.
 */

var DspOpsApp = (function () {
    'use strict';

    // ── State ─────────────────────────────────────────────────────────────────
    var _initialized  = false;
    var _drivers      = [];         // DspDriver[]
    var _expenses     = [];         // DriverExpense[] for current week
    var _expDefaults  = {};         // { driverId: DriverExpenseDefault[] }
    var _summary      = {};         // response from /api/dsp/summary
    var _importBatches = [];
    var _weekStart    = '';         // YYYY-MM-DD (Sunday)
    var _driverFilter = 'all';      // 'all' | String(driverId)
    var _logOpen      = false;
    var _modal        = { open: false, type: null, data: null, driverId: null };

    // ── Constants ─────────────────────────────────────────────────────────────
    var EXP_CATS = [
        { value: 'fuel',      label: 'Fuel'      },
        { value: 'rental',    label: 'Rental'    },
        { value: 'deduction', label: 'Deduction' },
        { value: 'other',     label: 'Other'     },
    ];

    // ── Utilities ─────────────────────────────────────────────────────────────
    function _fmt(n) {
        return '$' + (+(n || 0)).toLocaleString('en-US', {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        });
    }

    function _esc(s) {
        return (s || '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function _csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.content : '';
    }

    function _api(method, url, body) {
        var opts = {
            method:      method,
            credentials: 'same-origin',
            headers:     { 'Content-Type': 'application/json', 'X-CSRFToken': _csrf() },
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        return fetch(url, opts).then(function (r) {
            if (!r.ok) throw new Error(method + ' ' + url + ' → ' + r.status);
            return r.json();
        });
    }

    // ── Date helpers ──────────────────────────────────────────────────────────
    function _isoDate(d) {
        return d.getFullYear() + '-' +
               String(d.getMonth() + 1).padStart(2, '0') + '-' +
               String(d.getDate()).padStart(2, '0');
    }

    function _currentSunday() {
        var d = new Date();
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() - d.getDay());
        return _isoDate(d);
    }

    function _addDays(iso, n) {
        var p = iso.split('-');
        var d = new Date(+p[0], +p[1] - 1, +p[2]);
        d.setDate(d.getDate() + n);
        return _isoDate(d);
    }

    function _weekLabel(sunday) {
        if (!sunday) return '';
        var p   = sunday.split('-');
        var sun = new Date(+p[0], +p[1] - 1, +p[2]);
        var sat = new Date(sun);
        sat.setDate(sat.getDate() + 6);
        function md(dt) { return (dt.getMonth() + 1) + '/' + dt.getDate(); }
        return 'Week of ' + md(sun) + ' – ' + md(sat) + ', ' + sun.getFullYear();
    }

    // ── Data loading ──────────────────────────────────────────────────────────
    function _loadAll(cb) {
        Promise.all([
            _api('GET', '/api/dsp/drivers').catch(function () { return []; }),
            _api('GET', '/api/dsp/summary?weekStart=' + _weekStart).catch(function () { return {}; }),
            _api('GET', '/api/dsp/expenses?weekStart=' + _weekStart).catch(function () { return []; }),
        ]).then(function (res) {
            _drivers  = res[0] || [];
            _summary  = res[1] || {};
            _expenses = res[2] || [];
            if (cb) cb();
        });
    }

    function _loadExpenseDefaults(driverId, cb) {
        _api('GET', '/api/dsp/drivers/' + driverId + '/expense-defaults')
            .then(function (data) {
                _expDefaults[driverId] = data || [];
                if (cb) cb();
            })
            .catch(function () {
                _expDefaults[driverId] = [];
                if (cb) cb();
            });
    }

    function _loadImportLog(cb) {
        _api('GET', '/api/dsp/import-batches?limit=10')
            .then(function (data) {
                _importBatches = data || [];
                if (cb) cb();
            })
            .catch(function () { if (cb) cb(); });
    }

    // ── Rendering ─────────────────────────────────────────────────────────────
    function _render() {
        var root = document.getElementById('dsp-root');
        if (!root) return;
        root.innerHTML =
            _htmlTopBar() +
            _htmlDriverTabs() +
            _htmlSummaryBar() +
            _htmlDriverGrid() +
            _htmlImportLog() +
            _htmlModal();
    }

    // ── Top bar ────────────────────────────────────────────────────────────────
    function _htmlTopBar() {
        return '<div class="dsp-topbar">' +
               '<div class="dsp-week-nav">' +
               '<button class="dsp-nav-btn" data-action="week-prev">&#8249;</button>' +
               '<span class="dsp-week-label">' + _weekLabel(_weekStart) + '</span>' +
               '<button class="dsp-nav-btn" data-action="week-next">&#8250;</button>' +
               '</div>' +
               '<button class="ivan-btn" data-action="add-driver">+ Add Driver</button>' +
               '</div>';
    }

    // ── Driver filter tabs ─────────────────────────────────────────────────────
    function _htmlDriverTabs() {
        var html = '<div class="dsp-driver-tabs"><div class="ivan-fgroup">';
        html += '<button class="ivan-fbtn' + (_driverFilter === 'all' ? ' active' : '') +
                '" data-action="filter-driver" data-did="all">All Drivers</button>';
        _drivers.forEach(function (d) {
            if (!d.active) return;
            var act = _driverFilter === String(d.id) ? ' active' : '';
            html += '<button class="ivan-fbtn' + act +
                    '" data-action="filter-driver" data-did="' + d.id + '">' +
                    _esc(d.name) + '</button>';
        });
        html += '</div></div>';
        return html;
    }

    // ── Summary bar ────────────────────────────────────────────────────────────
    function _htmlSummaryBar() {
        var s = _summary || {};
        return '<div class="dsp-summary-bar">' +
               '<div class="dsp-sum-item">' +
               '<div class="dsp-sum-label">Gross Revenue</div>' +
               '<div class="dsp-sum-val dsp-blue">' + _fmt(s.totalGross) + '</div>' +
               '</div>' +
               '<div class="dsp-sum-item">' +
               '<div class="dsp-sum-label">Total Expenses</div>' +
               '<div class="dsp-sum-val dsp-red">' + _fmt(s.totalExpenses) + '</div>' +
               '</div>' +
               '<div class="dsp-sum-item">' +
               '<div class="dsp-sum-label">Net Payout</div>' +
               '<div class="dsp-sum-val dsp-green">' + _fmt(s.totalNetPayout) + '</div>' +
               '</div>' +
               '</div>';
    }

    // ── Driver card grid ───────────────────────────────────────────────────────
    function _htmlDriverGrid() {
        var drvSums = (_summary && _summary.drivers) || [];

        // If no DB-backed summary yet but drivers exist, synthesize empty entries
        if (drvSums.length === 0 && _drivers.length > 0) {
            drvSums = _drivers.filter(function (d) { return d.active; }).map(function (d) {
                return { driver: d, tripCount: 0, gross: 0, tripRevenue: 0, expenses: 0, netPayout: 0 };
            });
        }

        var shown = drvSums.filter(function (ds) {
            return _driverFilter === 'all' || String(ds.driver.id) === _driverFilter;
        });

        if (shown.length === 0 && _drivers.length === 0) {
            return '<div class="dsp-empty">No drivers configured. Click " + Add Driver" to get started.</div>';
        }
        if (shown.length === 0) {
            return '<div class="dsp-empty">No data for selected driver.</div>';
        }

        return '<div class="dsp-driver-grid">' +
               shown.map(_htmlDriverCard).join('') +
               '</div>';
    }

    function _htmlDriverCard(ds) {
        var drv = ds.driver;
        var isOO = drv.driverType === 'owner_op';

        var badge = isOO
            ? '<span class="dsp-badge dsp-badge-oo">Owner Op</span>'
            : '<span class="dsp-badge dsp-badge-co">Company</span>';

        // Expenses for this driver from this week
        var drvExps = _expenses.filter(function (e) { return e.driverId === drv.id; });
        var totalExp = drvExps.reduce(function (s, e) { return s + (e.amount || 0); }, 0);
        var net = (ds.tripRevenue || 0) - totalExp;

        // Revenue block
        var revHtml = '<div class="dsp-rev-row">' +
            '<div class="dsp-rev-item">' +
            '<div class="dsp-rev-label">Gross Revenue</div>' +
            '<div class="dsp-rev-val dsp-blue">' + _fmt(ds.gross) + '</div>' +
            '</div>';
        if (isOO) {
            revHtml += '<div class="dsp-rev-item">' +
                '<div class="dsp-rev-label">Trip Rev (' + (drv.defaultPayoutPct || 0) + '%)</div>' +
                '<div class="dsp-rev-val">' + _fmt(ds.tripRevenue) + '</div>' +
                '</div>';
        } else {
            revHtml += '<div class="dsp-rev-item">' +
                '<div class="dsp-rev-label">Trips</div>' +
                '<div class="dsp-rev-val">' + (ds.tripCount || 0) + '</div>' +
                '</div>';
        }
        revHtml += '</div>';

        // Expense rows
        var expRows = drvExps.map(function (e) {
            var catObj  = EXP_CATS.filter(function (c) { return c.value === e.category; })[0];
            var catLabel = catObj ? catObj.label : e.category;
            return '<tr>' +
                '<td class="dsp-ecat"><span class="dsp-cat-badge dsp-cat-' + _esc(e.category) + '">' + _esc(catLabel) + '</span></td>' +
                '<td class="dsp-elabel">' + _esc(e.label) + '</td>' +
                '<td class="dsp-eamt dsp-red">' + _fmt(e.amount) + '</td>' +
                '<td class="dsp-eact">' +
                '<button class="dsp-icon-btn" data-action="edit-expense" data-eid="' + e.id + '" title="Edit">✏</button> ' +
                '<button class="dsp-icon-btn dsp-del" data-action="del-expense" data-eid="' + e.id + '" title="Delete">✕</button>' +
                '</td>' +
                '</tr>';
        }).join('');

        var expTable = drvExps.length > 0
            ? '<table class="dsp-exp-table"><tbody>' + expRows + '</tbody></table>'
            : '<div class="dsp-no-exp">No expenses this week.</div>';

        return '<div class="dsp-driver-card">' +
               '<div class="dsp-card-hdr">' +
               '<div><span class="dsp-drv-name">' + _esc(drv.name) + '</span>' + badge + '</div>' +
               '<div class="dsp-card-btns">' +
               '<button class="dsp-icon-btn" data-action="manage-defaults" data-did="' + drv.id + '" title="Manage expense defaults">⚙</button>' +
               '<button class="dsp-icon-btn" data-action="edit-driver" data-did="' + drv.id + '" title="Edit driver">✏</button>' +
               '</div>' +
               '</div>' +
               revHtml +
               '<div class="dsp-exp-hdr">' +
               '<span class="dsp-exp-title">Expenses</span>' +
               '<button class="dsp-sm-btn" data-action="add-expense" data-did="' + drv.id + '">+ Add</button>' +
               '</div>' +
               expTable +
               '<div class="dsp-net-row">' +
               '<span class="dsp-net-label">Net Payout</span>' +
               '<span class="dsp-net-val ' + (net >= 0 ? 'dsp-green' : 'dsp-red') + '">' + _fmt(net) + '</span>' +
               '</div>' +
               '</div>';
    }

    // ── Import log ─────────────────────────────────────────────────────────────
    function _htmlImportLog() {
        var arrow = _logOpen ? '&#9660;' : '&#9658;';
        var html = '<div class="dsp-import-log">' +
                   '<div class="dsp-log-hdr" data-action="toggle-log">' +
                   arrow + ' Import Log' +
                   '</div>';
        if (_logOpen) {
            if (_importBatches.length === 0) {
                html += '<div class="dsp-no-exp" style="padding:12px 16px">No import batches yet.</div>';
            } else {
                html += '<table class="dsp-log-table">' +
                        '<thead><tr><th>Source</th><th>File</th><th>Rows</th><th>By</th><th>Date</th></tr></thead>' +
                        '<tbody>';
                _importBatches.forEach(function (b) {
                    html += '<tr>' +
                            '<td><span class="dsp-src-badge dsp-src-' + _esc(b.source) + '">' + _esc(b.source) + '</span></td>' +
                            '<td>' + _esc(b.filename || '—') + '</td>' +
                            '<td>' + (b.rowsImported || 0) + '</td>' +
                            '<td>' + _esc(b.createdBy || '—') + '</td>' +
                            '<td>' + (b.createdAt ? b.createdAt.slice(0, 10) : '—') + '</td>' +
                            '</tr>';
                });
                html += '</tbody></table>';
            }
        }
        html += '</div>';
        return html;
    }

    // ── Modal ──────────────────────────────────────────────────────────────────
    function _htmlModal() {
        if (!_modal.open) return '<div id="dsp-modal" style="display:none"></div>';

        var inner = '';
        if (_modal.type === 'expense')  inner = _htmlExpenseModal();
        if (_modal.type === 'driver')   inner = _htmlDriverModal();
        if (_modal.type === 'defaults') inner = _htmlDefaultsModal();

        return '<div id="dsp-modal" class="dsp-modal-overlay" data-action="modal-overlay">' +
               '<div class="dsp-modal-box">' + inner + '</div>' +
               '</div>';
    }

    function _modalHdr(title) {
        return '<div class="dsp-modal-hdr">' +
               '<span class="dsp-modal-title">' + _esc(title) + '</span>' +
               '<button class="dsp-modal-close" data-action="modal-close" type="button">✕</button>' +
               '</div>';
    }

    function _catOptions(selected) {
        return EXP_CATS.map(function (c) {
            return '<option value="' + c.value + '"' + (c.value === selected ? ' selected' : '') + '>' + c.label + '</option>';
        }).join('');
    }

    // ── Expense modal ──────────────────────────────────────────────────────────
    function _htmlExpenseModal() {
        var e    = _modal.data || {};
        var isEdit = !!e.id;
        var drvId = e.driverId || _modal.driverId;
        var drv   = _drivers.filter(function (d) { return d.id === drvId; })[0] || {};

        // Quick-fill buttons from saved defaults
        var defs = (_expDefaults[drvId] || []).filter(function (d) { return d.active; });
        var defsHtml = '';
        if (!isEdit && defs.length > 0) {
            defsHtml = '<div class="dsp-defaults-row">' +
                       '<span class="dsp-def-label">Quick fill:</span>' +
                       defs.map(function (df) {
                           var amtStr = df.isPercentage ? df.amount + '%' : _fmt(df.amount);
                           return '<button type="button" class="dsp-def-btn" data-action="fill-default"' +
                                  ' data-cat="' + _esc(df.category) + '"' +
                                  ' data-label="' + _esc(df.label) + '"' +
                                  ' data-amt="' + df.amount + '">' +
                                  _esc(df.label) + ' (' + amtStr + ')' +
                                  '</button>';
                       }).join('') +
                       '</div>';
        }

        return _modalHdr(isEdit ? 'Edit Expense' : 'Add Expense') +
               '<form data-form="expense">' +
               '<input type="hidden" name="eid"       value="' + (e.id || '') + '">' +
               '<input type="hidden" name="driverId"  value="' + (drvId || '') + '">' +
               '<input type="hidden" name="weekStart" value="' + _weekStart + '">' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Driver</label>' +
               '<div class="dsp-form-val">' + _esc(drv.name || '?') + '</div>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Week</label>' +
               '<div class="dsp-form-val">' + _weekLabel(_weekStart) + '</div>' +
               '</div>' +
               defsHtml +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Category</label>' +
               '<select name="category" class="dsp-select">' + _catOptions(e.category || 'deduction') + '</select>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Label</label>' +
               '<input name="label" class="dsp-input" value="' + _esc(e.label || '') + '" placeholder="e.g. Weekly truck rental" required>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Amount ($)</label>' +
               '<input name="amount" type="number" step="0.01" min="0" class="dsp-input" value="' + (e.amount || '') + '" placeholder="0.00" required>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Notes</label>' +
               '<textarea name="notes" class="dsp-textarea" placeholder="Optional">' + _esc(e.notes || '') + '</textarea>' +
               '</div>' +
               '<div class="dsp-modal-footer">' +
               '<button type="button" class="dsp-btn-ghost" data-action="modal-close">Cancel</button>' +
               '<button type="submit" class="ivan-btn">' + (isEdit ? 'Save Changes' : 'Add Expense') + '</button>' +
               '</div>' +
               '</form>';
    }

    // ── Driver modal ───────────────────────────────────────────────────────────
    function _htmlDriverModal() {
        var d      = _modal.data || {};
        var isEdit = !!d.id;
        var isOO   = d.driverType === 'owner_op';

        return _modalHdr(isEdit ? 'Edit Driver' : 'Add Driver') +
               '<form data-form="driver">' +
               '<input type="hidden" name="did" value="' + (d.id || '') + '">' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Name</label>' +
               '<input name="name" class="dsp-input" value="' + _esc(d.name || '') + '" placeholder="Full name" required>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Type</label>' +
               '<select name="driverType" class="dsp-select" id="dsp-type-sel">' +
               '<option value="company"'  + (!isOO ? ' selected' : '') + '>Company Driver</option>' +
               '<option value="owner_op"' + (isOO  ? ' selected' : '') + '>Owner Operator</option>' +
               '</select>' +
               '</div>' +
               '<div class="dsp-form-row" id="dsp-payout-row" style="' + (!isOO ? 'display:none' : '') + '">' +
               '<label class="dsp-form-label">Payout %</label>' +
               '<input name="defaultPayoutPct" type="number" step="0.1" min="0" max="100" class="dsp-input" value="' + (d.defaultPayoutPct || 0) + '" placeholder="e.g. 88">' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Phone</label>' +
               '<input name="phone" class="dsp-input" value="' + _esc(d.phone || '') + '" placeholder="Optional">' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Email</label>' +
               '<input name="email" type="email" class="dsp-input" value="' + _esc(d.email || '') + '" placeholder="Optional">' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Fuel Card</label>' +
               '<label class="dsp-check-row"><input type="checkbox" name="fuelCardHolder"' + (d.fuelCardHolder ? ' checked' : '') + '> Has fuel card</label>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Active</label>' +
               '<label class="dsp-check-row"><input type="checkbox" name="active"' + (d.active !== false ? ' checked' : '') + '> Active</label>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Notes</label>' +
               '<textarea name="notes" class="dsp-textarea" placeholder="Optional">' + _esc(d.notes || '') + '</textarea>' +
               '</div>' +
               '<div class="dsp-modal-footer">' +
               (isEdit ? '<button type="button" class="dsp-btn-del" data-action="del-driver" data-did="' + d.id + '">Delete Driver</button>' : '') +
               '<button type="button" class="dsp-btn-ghost" data-action="modal-close">Cancel</button>' +
               '<button type="submit" class="ivan-btn">' + (isEdit ? 'Save Changes' : 'Add Driver') + '</button>' +
               '</div>' +
               '</form>';
    }

    // ── Expense defaults modal ─────────────────────────────────────────────────
    function _htmlDefaultsModal() {
        var drv  = _modal.data || {};
        var defs = _expDefaults[drv.id] || [];

        var rows = defs.map(function (df) {
            var catObj = EXP_CATS.filter(function (c) { return c.value === df.category; })[0];
            var catLabel = catObj ? catObj.label : df.category;
            var amtStr   = df.isPercentage ? df.amount + '%' : _fmt(df.amount);
            return '<tr class="' + (!df.active ? 'dsp-def-inactive' : '') + '">' +
                   '<td><span class="dsp-cat-badge dsp-cat-' + _esc(df.category) + '">' + _esc(catLabel) + '</span></td>' +
                   '<td>' + _esc(df.label) + '</td>' +
                   '<td>' + _esc(amtStr) + '</td>' +
                   '<td>' +
                   '<button type="button" class="dsp-icon-btn dsp-del" data-action="del-default"' +
                   ' data-dfid="' + df.id + '" data-did="' + drv.id + '" title="Remove">✕</button>' +
                   '</td>' +
                   '</tr>';
        }).join('');

        var tableHtml = defs.length > 0
            ? '<table class="dsp-exp-table"><thead><tr><th>Category</th><th>Label</th><th>Amount</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>'
            : '<div class="dsp-no-exp">No defaults yet — add one below.</div>';

        return _modalHdr('Expense Defaults — ' + _esc(drv.name || '')) +
               '<div class="dsp-defaults-list">' + tableHtml + '</div>' +
               '<form data-form="add-default" style="border-top:1px solid #243047;margin-top:.75rem">' +
               '<input type="hidden" name="did" value="' + (drv.id || '') + '">' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Category</label>' +
               '<select name="category" class="dsp-select">' + _catOptions('deduction') + '</select>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Label</label>' +
               '<input name="label" class="dsp-input" placeholder="e.g. Weekly truck rental" required>' +
               '</div>' +
               '<div class="dsp-form-row">' +
               '<label class="dsp-form-label">Amount ($)</label>' +
               '<input name="amount" type="number" step="0.01" min="0" class="dsp-input" placeholder="0.00" required>' +
               '</div>' +
               '<div class="dsp-modal-footer">' +
               '<button type="button" class="dsp-btn-ghost" data-action="modal-close">Done</button>' +
               '<button type="submit" class="ivan-btn">+ Add Default</button>' +
               '</div>' +
               '</form>';
    }

    // ── Event handling ─────────────────────────────────────────────────────────
    function _onClick(ev) {
        // Close modal on overlay background click
        if (ev.target && ev.target.dataset && ev.target.dataset.action === 'modal-overlay') {
            _modal = { open: false, type: null, data: null, driverId: null };
            _render();
            return;
        }

        var btn = ev.target.closest('[data-action]');
        if (!btn) return;
        var action = btn.dataset.action;

        switch (action) {

            case 'week-prev':
                _weekStart = _addDays(_weekStart, -7);
                _loadAll(_render);
                break;

            case 'week-next':
                _weekStart = _addDays(_weekStart, 7);
                _loadAll(_render);
                break;

            case 'filter-driver':
                _driverFilter = btn.dataset.did;
                _render();
                break;

            case 'add-driver':
                _modal = { open: true, type: 'driver', data: {}, driverId: null };
                _render();
                break;

            case 'edit-driver': {
                var edid = parseInt(btn.dataset.did);
                var edrv = _drivers.filter(function (d) { return d.id === edid; })[0];
                _modal = { open: true, type: 'driver', data: edrv || {}, driverId: null };
                _render();
                break;
            }

            case 'del-driver': {
                if (!confirm('Delete this driver? All their expenses will also be deleted.')) return;
                var delDid = parseInt(btn.dataset.did);
                _api('DELETE', '/api/dsp/drivers/' + delDid)
                    .then(function () {
                        _modal = { open: false };
                        _driverFilter = 'all';
                        _loadAll(_render);
                    })
                    .catch(function (e) { alert('Error: ' + e.message); });
                break;
            }

            case 'add-expense': {
                var adid = parseInt(btn.dataset.did);
                _modal = { open: true, type: 'expense', data: {}, driverId: adid };
                if (!_expDefaults[adid]) {
                    _loadExpenseDefaults(adid, _render);
                } else {
                    _render();
                }
                break;
            }

            case 'edit-expense': {
                var eid = parseInt(btn.dataset.eid);
                var exp = _expenses.filter(function (e) { return e.id === eid; })[0];
                if (exp) {
                    _modal = { open: true, type: 'expense', data: exp, driverId: exp.driverId };
                    _render();
                }
                break;
            }

            case 'del-expense': {
                if (!confirm('Delete this expense?')) return;
                var delEid = parseInt(btn.dataset.eid);
                _api('DELETE', '/api/dsp/expenses/' + delEid)
                    .then(function () { _loadAll(_render); })
                    .catch(function (e) { alert('Error: ' + e.message); });
                break;
            }

            case 'manage-defaults': {
                var mdid = parseInt(btn.dataset.did);
                var mdrv = _drivers.filter(function (d) { return d.id === mdid; })[0] || { id: mdid };
                _modal = { open: true, type: 'defaults', data: mdrv, driverId: mdid };
                _loadExpenseDefaults(mdid, _render);
                break;
            }

            case 'del-default': {
                var dfid = parseInt(btn.dataset.dfid);
                var ddid = parseInt(btn.dataset.did);
                _api('DELETE', '/api/dsp/drivers/' + ddid + '/expense-defaults/' + dfid)
                    .then(function () { _loadExpenseDefaults(ddid, _render); })
                    .catch(function (e) { alert('Error: ' + e.message); });
                break;
            }

            case 'fill-default': {
                var frm = btn.closest('form');
                if (!frm) return;
                var catSel = frm.querySelector('[name="category"]');
                var lblInp = frm.querySelector('[name="label"]');
                var amtInp = frm.querySelector('[name="amount"]');
                if (catSel) catSel.value = btn.dataset.cat || '';
                if (lblInp) lblInp.value = btn.dataset.label || '';
                if (amtInp) amtInp.value = btn.dataset.amt || '';
                break;
            }

            case 'modal-close':
                _modal = { open: false, type: null, data: null, driverId: null };
                _render();
                break;

            case 'toggle-log':
                _logOpen = !_logOpen;
                if (_logOpen && _importBatches.length === 0) {
                    _loadImportLog(_render);
                } else {
                    _render();
                }
                break;
        }
    }

    function _onChange(ev) {
        // Show/hide payout % row when driver type changes
        if (ev.target.name === 'driverType') {
            var row = document.getElementById('dsp-payout-row');
            if (row) row.style.display = ev.target.value === 'owner_op' ? '' : 'none';
        }
    }

    function _onSubmit(ev) {
        var form = ev.target.closest('[data-form]');
        if (!form) return;
        ev.preventDefault();

        var ft = form.dataset.form;

        if (ft === 'expense') {
            var fd   = _readForm(form);
            var eid  = fd.eid;
            var payload = {
                driverId:  parseInt(fd.driverId) || 0,
                weekStart: fd.weekStart,
                category:  fd.category,
                label:     fd.label,
                amount:    parseFloat(fd.amount) || 0,
                notes:     fd.notes || '',
            };
            var prom = eid
                ? _api('PUT',  '/api/dsp/expenses/' + eid, payload)
                : _api('POST', '/api/dsp/expenses',        payload);
            prom.then(function () {
                _modal = { open: false };
                _loadAll(_render);
            }).catch(function (e) { alert('Error saving expense: ' + e.message); });
        }

        if (ft === 'driver') {
            var dd = _readForm(form);
            var dpayload = {
                name:              dd.name,
                driverType:        dd.driverType,
                phone:             dd.phone || '',
                email:             dd.email || '',
                active:            !!(form.querySelector('[name="active"]') || {}).checked,
                notes:             dd.notes || '',
                defaultPayoutPct:  parseFloat(dd.defaultPayoutPct) || 0,
                fuelCardHolder:    !!(form.querySelector('[name="fuelCardHolder"]') || {}).checked,
            };
            var did = dd.did;
            var dprom = did
                ? _api('PUT',  '/api/dsp/drivers/' + did, dpayload)
                : _api('POST', '/api/dsp/drivers',        dpayload);
            dprom.then(function () {
                _modal = { open: false };
                _loadAll(_render);
            }).catch(function (e) { alert('Error saving driver: ' + e.message); });
        }

        if (ft === 'add-default') {
            var ad  = _readForm(form);
            var adid = parseInt(ad.did);
            _api('POST', '/api/dsp/drivers/' + adid + '/expense-defaults', {
                category:     ad.category,
                label:        ad.label,
                amount:       parseFloat(ad.amount) || 0,
                isPercentage: false,
                active:       true,
            }).then(function () {
                _loadExpenseDefaults(adid, _render);
                // Clear add form fields
                var lbl = form.querySelector('[name="label"]');
                var amt = form.querySelector('[name="amount"]');
                if (lbl) lbl.value = '';
                if (amt) amt.value = '';
            }).catch(function (e) { alert('Error adding default: ' + e.message); });
        }
    }

    function _readForm(form) {
        var out = {};
        Array.prototype.slice.call(form.elements).forEach(function (el) {
            if (el.name && el.type !== 'checkbox' && el.type !== 'button' && el.type !== 'submit') {
                out[el.name] = el.value;
            }
        });
        return out;
    }

    // ── Mount ──────────────────────────────────────────────────────────────────
    function _mount() {
        var container = document.getElementById('amazon-panel-content');
        if (!container) return;
        container.innerHTML = '<div id="dsp-root" class="dsp-root"></div>';
        // Delegate all events to the stable container (not dsp-root, which is replaced)
        container.addEventListener('click',  _onClick);
        container.addEventListener('change', _onChange);
        container.addEventListener('submit', _onSubmit);
    }

    // ── Public API ─────────────────────────────────────────────────────────────
    function show() {
        if (!_initialized) {
            _weekStart   = _currentSunday();
            _driverFilter = 'all';
            _mount();
            _initialized = true;
        }
        _loadAll(_render);
    }

    return { show: show };

}());

// ── Hook into company tab switching ────────────────────────────────────────────
(function () {
    function _hookOpenCompany() {
        var _orig = window.openCompany;
        window.openCompany = function (btn, company) {
            if (_orig) _orig.call(this, btn, company);
            if (company === 'amazon') DspOpsApp.show();
        };
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _hookOpenCompany);
    } else {
        _hookOpenCompany();
    }
}());
