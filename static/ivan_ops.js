/**
 * static/ivan_ops.js
 *
 * Ivan Cartage — Equipment & Drivers operations module.
 *
 * Public API:
 *   IvanOpsApp.mountEquipment(containerId)  — render Equipment tab
 *   IvanOpsApp.mountDrivers(containerId)    — render Drivers tab
 *
 * Data persistence: PostgreSQL via REST API (/api/ivan/*)
 * Drivers: still stored in localStorage (LS_DRIVERS).
 *
 * Architecture notes:
 *   - Equipment records, maintenance tasks, and invoices are stored in
 *     PostgreSQL via the Flask API. Drivers remain in localStorage.
 *   - Invoice uploads (Phase 1): metadata + filename stored only. No binary
 *     file content is stored client-side. Phase 2 would add server-side upload
 *     and text extraction from PDF/image.
 *   - Insurance toggle: persisted immediately via API on change.
 *   - Driver ↔ truck link: driver.assignedTruckId references an equipment.id.
 *   - Event delegation is used throughout so innerHTML replacements do not
 *     require re-binding. The container element gets one listener set per mount.
 */

var IvanOpsApp = (function () {
    'use strict';

    // ── localStorage keys (drivers only) ─────────────────────────────────
    var LS_DRIVERS = 'bcat_ivan_drivers';

    // ── In-memory stores ─────────────────────────────────────────────────
    var _equipment   = [];
    var _maintenance = [];   // tasks, shaped like old schema for rendering compat
    var _invoices    = [];   // invoices, shaped like old schema for rendering compat
    var _drivers     = [];

    // ── UI state ─────────────────────────────────────────────────────────
    var _es = {                       // equipment tab state
        filter:    'all',             // 'all' | 'truck' | 'trailer'
        search:    '',
        selectedId: null,             // expanded detail panel
        mFilter:     'all',           // maintenance section filter
        sortCol:     'unitNumber',    // active sort column key
        sortDir:     'asc',          // 'asc' | 'desc'
        spendPeriod: 'year',          // 'year' | 'alltime'
        histPage:   0                 // maintenance history current page (0-indexed)
    };
    var _ds = {                       // drivers tab state
        search: ''
    };

    // Container IDs (set on mount)
    var _equipCid  = null;
    var _driverCid = null;

    // ── Colors (matching dashboard palette) ──────────────────────────────
    var C = {
        fg:      '#f8fafc',
        muted:   '#94a3b8',
        accent:  '#0ea5e9',
        green:   '#22c55e',
        red:     '#ef4444',
        amber:   '#f59e0b',
        border:  '#20263a'
    };

    // ── localStorage helpers (drivers only) ───────────────────────────────
    function _loadLS(key) {
        try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : []; }
        catch (e) { return []; }
    }
    function _saveLS(key, data) {
        try { localStorage.setItem(key, JSON.stringify(data)); } catch (e) {}
    }

    // ── ID and date helpers ───────────────────────────────────────────────
    function _genId() {
        return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    }
    function _nowIso() { return new Date().toISOString(); }
    function _today()  { return new Date().toISOString().slice(0, 10); }

    // ── API helpers ───────────────────────────────────────────────────────
    function _api(method, path, body) {
        var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
        if (body) opts.body = JSON.stringify(body);
        return fetch(path, opts).then(function(r) { return r.json(); });
    }

    // ── Map API task → internal format (old field names for rendering compat) ──
    function _taskFromApi(t) {
        return {
            maintenanceTaskId: t.id,
            equipmentId:       t.equipId,
            equipmentType:     '', // not stored in new schema; filled from equipment lookup
            title:             t.title,
            description:       t.notes || '',
            dueDate:           t.dueDate || '',
            priority:          t.priority === 'med' ? 'medium' : (t.priority || 'medium'),
            status:            t.status === 'complete' ? 'completed' : (t.status || 'upcoming'),
            milageDue:         null,
            vendor:            '',
            estimatedCost:     null,
            actualCost:        null,
            autoDot:           t.autoDot || false,
            createdAt:         t.createdAt || '',
            completedAt:       null,
            _apiId:            t.id   // keep API id for PUT/DELETE calls
        };
    }

    // ── Map API invoice → internal format (old field names for rendering compat) ──
    function _invoiceFromApi(inv) {
        return {
            invoiceId:     inv.id,
            equipmentId:   inv.equipId,
            invoiceDate:   inv.date || '',
            vendor:        inv.vendor || '',
            invoiceNumber: inv.invoiceNumber || '',
            totalAmount:   inv.amount || 0,
            description:   inv.description || '',
            paymentMethod: inv.paymentMethod || null,
            paymentDate:   inv.paymentDate || null,
            fileRef:       null,
            _apiId:        inv.id   // keep API id for PUT/DELETE calls
        };
    }

    // ── Load all data from API, then call cb() ────────────────────────────
    function _loadAll(cb) {
        Promise.all([
            fetch('/api/ivan/equipment').then(function(r){ return r.json(); }),
            fetch('/api/ivan/tasks').then(function(r){ return r.json(); }),
            fetch('/api/ivan/invoices').then(function(r){ return r.json(); })
        ]).then(function(results) {
            _equipment = results[0];
            // Enrich tasks with equipmentType from equipment lookup
            _maintenance = results[1].map(function(t) {
                var task = _taskFromApi(t);
                var eq = _equipment.find(function(e) { return e.id === task.equipmentId; });
                task.equipmentType = eq ? eq.type : 'truck';
                return task;
            });
            _invoices = results[2].map(_invoiceFromApi);
            if (cb) cb();
        }).catch(function(e) {
            console.error('Ivan data load failed', e);
            if (cb) cb();
        });
    }

    // ── Summary calculations ──────────────────────────────────────────────
    function calculateEquipmentSummary() {
        var today    = _today();
        var active   = _equipment.filter(function (e) { return e.active; });
        var upcoming = _maintenance.filter(function (m) { return m.status !== 'completed' && m.dueDate >= today; });
        var overdue  = _maintenance.filter(function (m) { return m.status !== 'completed' && m.dueDate < today; });
        var high     = _maintenance.filter(function (m) { return m.status !== 'completed' && m.priority === 'high'; });
        var cutoff = _spendCutoff();
        var repairSpend = _invoices
            .filter(function (inv) { return !cutoff || (inv.invoiceDate || '') >= cutoff; })
            .reduce(function (s, inv) { return s + (inv.totalAmount || 0); }, 0);
        return {
            trucks:       active.filter(function (e) { return e.type === 'truck';   }).length,
            trailers:     active.filter(function (e) { return e.type === 'trailer'; }).length,
            insured:      active.filter(function (e) { return e.insured;  }).length,
            notInsured:   active.filter(function (e) { return !e.insured; }).length,
            upcoming:     upcoming.length,
            overdue:      overdue.length,
            highPriority: high.length,
            repairSpend:  repairSpend
        };
    }

    function getUpcomingMaintenance() {
        var today = _today();
        return _maintenance
            .filter(function (m) { return m.status !== 'completed'; })
            .map(function (m) {
                if (m.dueDate < today && m.status !== 'overdue') { m.status = 'overdue'; }
                return m;
            })
            .sort(function (a, b) { return a.dueDate.localeCompare(b.dueDate); });
    }

    function _spendCutoff() {
        if (_es.spendPeriod === 'year') {
            return new Date().getFullYear() + '-01-01';
        }
        return null; // all time
    }
    function getRepairSpendByEquipment(equipId) {
        var cutoff = _spendCutoff();
        return _invoices
            .filter(function (inv) {
                return inv.equipmentId === equipId
                    && (!cutoff || (inv.invoiceDate || '') >= cutoff);
            })
            .reduce(function (s, inv) { return s + (inv.totalAmount || 0); }, 0);
    }

    function getEquipmentMaintenanceHistory(equipId) {
        return _maintenance.filter(function (m) { return m.equipmentId === equipId; });
    }

    function getEquipmentInvoices(equipId) {
        return _invoices.filter(function (inv) { return inv.equipmentId === equipId; });
    }

    function _findEquip(id)  { return _equipment.find(function (e) { return e.id === id; }) || null; }
    function _findDriver(id) { return _drivers.find(function (d)   { return d.id === id; }) || null; }

    // ── Formatting helpers ────────────────────────────────────────────────
    function _money(n) {
        if (n == null || isNaN(n)) return '—';
        return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function _fmtDate(s) {
        if (!s) return '—';
        var parts = s.split('-');
        if (parts.length !== 3) return s;
        var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return months[parseInt(parts[1], 10) - 1] + ' ' + parseInt(parts[2], 10) + ', ' + parts[0];
    }
    function _daysUntil(dateStr) {
        if (!dateStr) return null;
        return Math.round((new Date(dateStr) - new Date(_today())) / 86400000);
    }
    function _esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // ── Badge helpers ─────────────────────────────────────────────────────
    function _priorityBadge(p) {
        var cls = { high: 'ivan-badge-high', medium: 'ivan-badge-med', low: 'ivan-badge-low' }[p] || 'ivan-badge-low';
        return '<span class="ivan-badge ' + cls + '">' + (p ? p.charAt(0).toUpperCase() + p.slice(1) : '—') + '</span>';
    }
    function _statusBadge(s) {
        var map = { overdue: 'ivan-badge-overdue', completed: 'ivan-badge-done', in_progress: 'ivan-badge-inprog', upcoming: 'ivan-badge-upcoming' };
        var label = { overdue: 'Overdue', completed: 'Completed', in_progress: 'In Progress', upcoming: 'Upcoming' }[s] || s;
        return '<span class="ivan-badge ' + (map[s] || '') + '">' + label + '</span>';
    }
    function _insuranceBadge(insured) {
        return insured
            ? '<span class="ivan-badge ivan-badge-insured">Insured</span>'
            : '<span class="ivan-badge ivan-badge-uninsured">Not Insured</span>';
    }
    function _typeBadge(type) {
        return '<span class="ivan-badge ' + (type === 'truck' ? 'ivan-badge-truck' : 'ivan-badge-trailer') + '">'
            + (type === 'truck' ? 'Truck' : 'Trailer') + '</span>';
    }
    function _sortTh(label, col) {
        var active = _es.sortCol === col;
        var arrow  = active ? (_es.sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        var style  = 'cursor:pointer;user-select:none;white-space:nowrap'
                   + (active ? ';color:#f3f4f6' : '');
        return '<th data-sort="' + col + '" style="' + style + '">' + label
            + '<span style="font-size:10px;opacity:' + (active ? '1' : '0.4') + '">' + arrow + '</span></th>';
    }
    function _dotInspBadge(lastDateStr) {
        if (!lastDateStr) return '<span style="color:' + C.muted + '">—</span>';
        var next = new Date(lastDateStr);
        next.setFullYear(next.getFullYear() + 1);
        var nextStr = next.toISOString().slice(0, 10);
        var days = _daysUntil(nextStr);
        var title = 'Last: ' + _fmtDate(lastDateStr) + ' · Next due: ' + _fmtDate(nextStr);
        if (days < 0)
            return '<span class="ivan-badge ivan-badge-overdue" title="' + title + '">' + Math.abs(days) + 'd overdue</span>';
        if (days <= 30)
            return '<span class="ivan-badge ivan-badge-warn" title="' + title + '">Due ' + _fmtDate(nextStr) + '</span>';
        return '<span class="ivan-badge ivan-badge-done" title="' + title + '">Due ' + _fmtDate(nextStr) + '</span>';
    }

    // ── _syncDotInspectionTasks — API-backed ──────────────────────────────
    function _syncDotInspectionTasks(cb) {
        var today = _today();
        var pending = [];

        _equipment.filter(function (e) { return e.active; }).forEach(function (e) {
            var needsTask = false;
            var dueDate = today;

            if (!e.dotInspectionDate) {
                needsTask = true;
            } else {
                var next = new Date(e.dotInspectionDate);
                next.setFullYear(next.getFullYear() + 1);
                var nextStr = next.toISOString().slice(0, 10);
                dueDate = nextStr;
                if (nextStr < today) needsTask = true;
            }

            var existing = _maintenance.find(function (m) {
                return m.autoDot && m.equipmentId === e.id && m.status !== 'completed';
            });

            if (needsTask && !existing) {
                var newId = 'dot-' + _genId();
                var task = {
                    id:       newId,
                    equipId:  e.id,
                    title:    'DOT Inspection',
                    dueDate:  dueDate,
                    priority: 'high',
                    status:   dueDate < today ? 'upcoming' : 'upcoming',
                    notes:    'Annual DOT inspection required.',
                    autoDot:  true
                };
                pending.push(_api('POST', '/api/ivan/tasks', task));
            } else if (!needsTask && existing) {
                pending.push(_api('DELETE', '/api/ivan/tasks/' + existing.maintenanceTaskId));
            }
        });

        if (pending.length === 0) {
            if (cb) cb();
            return;
        }

        Promise.all(pending).then(function() {
            if (cb) cb();
        }).catch(function(err) {
            console.error('DOT sync error', err);
            if (cb) cb();
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    // EQUIPMENT TAB — HTML builders
    // ══════════════════════════════════════════════════════════════════════

    function _renderEquipmentTab() {
        var container = document.getElementById(_equipCid);
        if (!container) return;

        // Auto-mark overdue tasks (in-memory only, status update happens on next full reload)
        var today = _today();
        _maintenance.forEach(function (m) {
            if (m.status !== 'completed' && m.dueDate < today && m.status !== 'overdue') {
                m.status = 'overdue';
            }
        });

        var summary = calculateEquipmentSummary();
        var filtered = _filteredEquipment();
        var openMaint = getUpcomingMaintenance();

        container.innerHTML = [
            _htmlSummaryCards(summary),
            _htmlSpendByMonth(),
            _htmlUpcomingMaintenance(openMaint),
            _htmlMaintenanceHistory(),
            _htmlEquipmentList(filtered),
            _es.selectedId ? _htmlDetailPanel(_es.selectedId) : '',
            _htmlEquipModal(),
            _htmlMaintModal(),
            _htmlInvoiceModal(),
            _htmlPaymentModal(),
            _htmlHistoryEditModal()
        ].join('');
    }

    function _filteredEquipment() {
        var list = _equipment.filter(function (e) {
            if (!e.active) return false;
            if (_es.filter !== 'all' && e.type !== _es.filter) return false;
            if (_es.search) {
                var q = _es.search.toLowerCase();
                return (e.unitNumber || '').toLowerCase().indexOf(q) >= 0
                    || (e.nickname   || '').toLowerCase().indexOf(q) >= 0
                    || (e.make       || '').toLowerCase().indexOf(q) >= 0
                    || (e.model      || '').toLowerCase().indexOf(q) >= 0
                    || (e.plate      || '').toLowerCase().indexOf(q) >= 0;
            }
            return true;
        });

        var col = _es.sortCol, dir = _es.sortDir === 'asc' ? 1 : -1;
        list.sort(function (a, b) {
            var av, bv;
            if (col === 'openTasks') {
                av = _maintenance.filter(function (m) { return m.equipmentId === a.id && m.status !== 'completed'; }).length;
                bv = _maintenance.filter(function (m) { return m.equipmentId === b.id && m.status !== 'completed'; }).length;
            } else if (col === 'repairSpend') {
                av = getRepairSpendByEquipment(a.id);
                bv = getRepairSpendByEquipment(b.id);
            } else if (col === 'dotInspectionDate') {
                // sort by next due date
                av = a.dotInspectionDate ? (function(d){ var x=new Date(d); x.setFullYear(x.getFullYear()+1); return x.toISOString().slice(0,10); })(a.dotInspectionDate) : '';
                bv = b.dotInspectionDate ? (function(d){ var x=new Date(d); x.setFullYear(x.getFullYear()+1); return x.toISOString().slice(0,10); })(b.dotInspectionDate) : '';
            } else {
                av = (a[col] != null ? a[col] : '').toString().toLowerCase();
                bv = (b[col] != null ? b[col] : '').toString().toLowerCase();
            }
            if (av < bv) return -1 * dir;
            if (av > bv) return  1 * dir;
            return 0;
        });
        return list;
    }

    // ── Summary cards ─────────────────────────────────────────────────────
    function _htmlSummaryCards(s) {
        function card(label, val, danger, warn, good) {
            var cls = danger && val > 0 ? 'ivan-val-danger' : warn && val > 0 ? 'ivan-val-warn' : good ? 'positive' : '';
            return '<div class="card"><div class="label">' + label + '</div>'
                + '<div class="value ' + cls + '">' + val + '</div></div>';
        }
        return '<div class="kpi-grid" style="margin-bottom:1.5rem">'
            + card('Trucks',              s.trucks)
            + card('Trailers',            s.trailers)
            + card('Insured',             s.insured, false, false, true)
            + card('Not Insured',         s.notInsured, false, s.notInsured > 0)
            + card('Upcoming Maintenance',s.upcoming)
            + card('Overdue',             s.overdue, s.overdue > 0)
            + card('High Priority',       s.highPriority, false, s.highPriority > 0)
            + '<div class="card"><div class="label" style="display:flex;align-items:center;justify-content:space-between">Repair Spend'
            + '<span style="display:flex;gap:0">'
            + '<button class="ivan-fbtn' + (_es.spendPeriod === 'year'    ? ' active' : '') + '" data-spendperiod="year"    style="padding:2px 7px;font-size:10px">YTD</button>'
            + '<button class="ivan-fbtn' + (_es.spendPeriod === 'alltime' ? ' active' : '') + '" data-spendperiod="alltime" style="padding:2px 7px;font-size:10px">All</button>'
            + '</span></div>'
            + '<div class="value" style="font-size:1.4rem">' + _money(s.repairSpend) + '</div></div>'
            + '</div>';
    }

    // ── Repair spend by month ─────────────────────────────────────────────
    function _htmlSpendByMonth() {
        var cutoff = _spendCutoff();
        var filtered = _invoices.filter(function (inv) {
            return !cutoff || (inv.invoiceDate || '') >= cutoff;
        });

        // Group by YYYY-MM
        var map = {};
        filtered.forEach(function (inv) {
            var key = (inv.invoiceDate || '').slice(0, 7); // 'YYYY-MM'
            if (!key) return;
            map[key] = (map[key] || 0) + (inv.totalAmount || 0);
        });

        var months = Object.keys(map).sort().reverse(); // newest first

        if (months.length === 0) {
            return '<div class="chart-card" style="margin-bottom:1.5rem">'
                + '<div class="section-title" style="margin:0 0 .75rem">Repair Spend by Month</div>'
                + '<p style="color:' + C.muted + ';font-size:.875rem">No invoice data yet.</p></div>';
        }

        var max = Math.max.apply(null, months.map(function (m) { return map[m]; }));

        var MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        var bars = months.map(function (key) {
            var parts = key.split('-');
            var label = MONTH_NAMES[parseInt(parts[1], 10) - 1] + ' ' + parts[0];
            var pct   = max > 0 ? (map[key] / max * 100).toFixed(1) : 0;
            return '<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem">'
                + '<div style="width:72px;text-align:right;font-size:12px;color:' + C.muted + ';flex-shrink:0">' + label + '</div>'
                + '<div style="flex:1;background:#1b2235;border-radius:4px;height:22px;overflow:hidden">'
                + '<div style="width:' + pct + '%;background:#0ea5e9;height:100%;border-radius:4px;min-width:' + (map[key] > 0 ? '3px' : '0') + '"></div>'
                + '</div>'
                + '<div style="width:80px;text-align:right;font-size:13px;font-weight:600;color:#f3f4f6;flex-shrink:0">' + _money(map[key]) + '</div>'
                + '</div>';
        }).join('');

        return '<div class="chart-card" style="margin-bottom:1.5rem">'
            + '<div class="ivan-section-hdr" style="margin-bottom:.75rem">'
            + '<div class="section-title" style="margin:0">Repair Spend by Month</div>'
            + '<span style="display:flex;gap:0">'
            + '<button class="ivan-fbtn' + (_es.spendPeriod === 'year'    ? ' active' : '') + '" data-spendperiod="year"    style="padding:2px 7px;font-size:10px">YTD</button>'
            + '<button class="ivan-fbtn' + (_es.spendPeriod === 'alltime' ? ' active' : '') + '" data-spendperiod="alltime" style="padding:2px 7px;font-size:10px">All</button>'
            + '</span>'
            + '</div>'
            + bars
            + '</div>';
    }

    // ── Upcoming maintenance section ──────────────────────────────────────
    function _htmlUpcomingMaintenance(tasks) {
        var today = _today();
        var filterBtns = ['all', 'upcoming', 'overdue', 'high'].map(function (f) {
            var label = f === 'high' ? 'High Priority' : f.charAt(0).toUpperCase() + f.slice(1);
            return '<button class="ivan-fbtn' + (_es.mFilter === f ? ' active' : '') + '" data-mfilter="' + f + '">' + label + '</button>';
        }).join('');

        var visible = tasks.filter(function (m) {
            var f = _es.mFilter;
            if (f === 'upcoming') return m.status !== 'overdue' && m.dueDate >= today;
            if (f === 'overdue')  return m.dueDate < today;
            if (f === 'high')     return m.priority === 'high';
            return true;
        });

        var rows = visible.map(function (m) {
            var eq     = _findEquip(m.equipmentId);
            var label  = eq ? (eq.unitNumber + (eq.nickname ? ' · ' + eq.nickname : '')) : m.equipmentId;
            var days   = _daysUntil(m.dueDate);
            var dLabel = days === 0 ? 'Today' : days > 0 ? 'In ' + days + 'd' : Math.abs(days) + 'd overdue';
            var dCls   = days < 0 ? 'ivan-val-danger' : days <= 7 ? 'ivan-val-warn' : '';
            return '<tr>'
                + '<td>' + _typeBadge(m.equipmentType) + '&nbsp;' + _esc(label) + '</td>'
                + '<td>' + _esc(m.title) + '</td>'
                + '<td>' + _priorityBadge(m.priority) + '</td>'
                + '<td>' + _statusBadge(m.status) + '</td>'
                + '<td><span class="' + dCls + '">' + dLabel + '</span><br><small style="color:' + C.muted + '">' + _fmtDate(m.dueDate) + '</small></td>'
                + '<td>' + _esc(m.vendor || '—') + '</td>'
                + '<td>' + (m.estimatedCost != null ? _money(m.estimatedCost) : '—') + '</td>'
                + '<td style="white-space:nowrap">'
                + '<button class="ivan-btn ivan-btn-sm" data-action="mark-complete" data-mtid="' + m.maintenanceTaskId + '" title="Mark complete">✓ Done</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-maint" data-mtid="' + m.maintenanceTaskId + '" title="Delete task">Delete</button>'
                + '</td>'
                + '</tr>';
        }).join('');

        return '<div class="chart-card" style="margin-bottom:1.5rem">'
            + '<div class="ivan-section-hdr">'
            + '<div class="section-title" style="margin:0">Upcoming &amp; Overdue Maintenance</div>'
            + '<div class="ivan-fgroup">' + filterBtns + '</div>'
            + '</div>'
            + '<div class="table-wrap"><table class="ivan-table"><thead><tr>'
            + '<th>Equipment</th><th>Task</th><th>Priority</th><th>Status</th><th>Due</th><th>Vendor</th><th>Est. Cost</th><th></th>'
            + '</tr></thead><tbody>'
            + (rows || '<tr><td colspan="8" style="color:' + C.muted + ';text-align:center;padding:1.5rem">No open tasks match the current filter.</td></tr>')
            + '</tbody></table></div></div>';
    }

    // ── Maintenance history section (invoices only) ───────────────────────
    function _htmlMaintenanceHistory() {
        var PAGE_SIZE = 10;
        var sorted = _invoices.slice().sort(function (a, b) {
            var da = a.invoiceDate || '', db = b.invoiceDate || '';
            return da < db ? 1 : da > db ? -1 : 0;
        });

        var total     = sorted.length;
        var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        var page      = Math.min(_es.histPage, totalPages - 1);
        var pageItems = sorted.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

        var rows = pageItems.map(function (inv) {
            var eq    = _findEquip(inv.equipmentId);
            var label = eq ? (eq.unitNumber + (eq.nickname ? ' · ' + eq.nickname : '')) : '—';
            var descCell = _esc(inv.description || '—')
                + (inv.fileRef ? '&nbsp;<span class="ivan-badge ivan-badge-upcoming" style="font-size:10px">' + _esc(inv.fileRef) + '</span>' : '');
            var payCell = inv.paymentMethod
                ? '<span class="ivan-badge ivan-badge-done">Paid</span>'
                  + '&nbsp;<span style="color:#f3f4f6;font-weight:600">' + _esc(inv.paymentMethod) + '</span>'
                  + (inv.paymentDate ? '<br><small style="color:' + C.muted + '">' + _fmtDate(inv.paymentDate) + '</small>' : '')
                : '<span class="ivan-badge ivan-badge-overdue">Unpaid</span>'
                  + '&nbsp;<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="open-pay-modal"'
                  + ' data-paytype="invoice" data-payid="' + inv.invoiceId + '">Record Payment</button>';
            return '<tr>'
                + '<td>' + (eq ? _typeBadge(eq.type) + '&nbsp;' : '') + _esc(label) + '</td>'
                + '<td style="max-width:240px;white-space:normal">' + descCell + '</td>'
                + '<td>' + (inv.invoiceNumber ? _esc(inv.invoiceNumber) : '<span style="color:' + C.muted + '">—</span>') + '</td>'
                + '<td><span style="color:#86efac;font-weight:600">' + _fmtDate(inv.invoiceDate) + '</span></td>'
                + '<td>' + _esc(inv.vendor || '—') + '</td>'
                + '<td>' + _money(inv.totalAmount) + '</td>'
                + '<td style="white-space:nowrap">' + payCell + '</td>'
                + '<td><button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="open-hist-edit"'
                  + ' data-paytype="invoice" data-payid="' + inv.invoiceId + '">Edit</button></td>'
                + '</tr>';
        }).join('');

        var start = total === 0 ? 0 : page * PAGE_SIZE + 1;
        var end   = Math.min(page * PAGE_SIZE + PAGE_SIZE, total);
        var pagination = '<div style="display:flex;align-items:center;justify-content:space-between;padding:.6rem 0 0;flex-wrap:wrap;gap:.5rem">'
            + '<span style="font-size:12px;color:' + C.muted + '">'
            + (total === 0 ? 'No records' : 'Showing ' + start + '–' + end + ' of ' + total) + '</span>'
            + '<div style="display:flex;gap:.4rem;align-items:center">'
            + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="hist-page" data-histpage="' + (page - 1) + '"'
            + (page === 0 ? ' disabled style="opacity:.35;cursor:default"' : '') + '>← Prev</button>'
            + '<span style="font-size:12px;color:' + C.muted + ';padding:0 .25rem">Page ' + (page + 1) + ' of ' + totalPages + '</span>'
            + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="hist-page" data-histpage="' + (page + 1) + '"'
            + (page >= totalPages - 1 ? ' disabled style="opacity:.35;cursor:default"' : '') + '>Next →</button>'
            + '</div></div>';

        return '<div class="chart-card" style="margin-bottom:1.5rem">'
            + '<div class="ivan-section-hdr">'
            + '<div class="section-title" style="margin:0">Maintenance History</div>'
            + '</div>'
            + '<div class="table-wrap"><table class="ivan-table"><thead><tr>'
            + '<th>Equipment</th><th>Description</th><th>Invoice #</th><th>Date</th><th>Vendor</th><th>Amount</th><th>Payment</th><th></th>'
            + '</tr></thead><tbody>'
            + (rows || '<tr><td colspan="8" style="color:' + C.muted + ';text-align:center;padding:1.5rem">No invoices yet.</td></tr>')
            + '</tbody></table></div>'
            + pagination
            + '</div>';
    }

    // ── Equipment list ────────────────────────────────────────────────────
    function _htmlEquipmentList(equip) {
        var typeBtns = ['all', 'truck', 'trailer'].map(function (f) {
            var label = f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1) + 's';
            return '<button class="ivan-fbtn' + (_es.filter === f ? ' active' : '') + '" data-efilter="' + f + '">' + label + '</button>';
        }).join('');

        var rows = equip.map(function (e) {
            var spend   = getRepairSpendByEquipment(e.id);
            var open    = _maintenance.filter(function (m) { return m.equipmentId === e.id && m.status !== 'completed'; }).length;
            var sel     = _es.selectedId === e.id;
            return '<tr class="ivan-erow' + (sel ? ' ivan-erow-sel' : '') + '" data-action="select-equip" data-equipid="' + e.id + '">'
                + '<td>' + _typeBadge(e.type) + '</td>'
                + '<td><strong>' + _esc(e.unitNumber) + '</strong>'
                + (e.nickname ? '<br><small style="color:' + C.muted + '">' + _esc(e.nickname) + '</small>' : '') + '</td>'
                + '<td>' + e.year + ' ' + _esc(e.make) + ' ' + _esc(e.model) + '</td>'
                + '<td>' + _esc(e.plate || '—') + '</td>'
                + '<td>' + _dotInspBadge(e.dotInspectionDate) + '</td>'
                + '<td>' + (e.ownership ? e.ownership.charAt(0).toUpperCase() + e.ownership.slice(1) : '—') + '</td>'
                + '<td>' + _insuranceBadge(e.insured) + '</td>'
                + '<td>' + (open > 0
                    ? '<span class="ivan-badge ivan-badge-warn">' + open + ' open</span>'
                    : '<span class="ivan-badge ivan-badge-done">None</span>') + '</td>'
                + '<td>' + _money(spend) + '</td>'
                + '<td style="white-space:nowrap">'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="edit-equip" data-equipid="' + e.id + '">Edit</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm" data-action="open-add-maint" data-equipid="' + e.id + '">+ Task</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="open-add-inv" data-equipid="' + e.id + '">+ Invoice</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-equip" data-equipid="' + e.id + '" title="Delete equipment">Delete</button>'
                + '</td>'
                + '</tr>';
        }).join('');

        return '<div class="chart-card" style="margin-bottom:1.5rem">'
            + '<div class="ivan-section-hdr">'
            + '<div class="section-title" style="margin:0">Equipment</div>'
            + '<div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">'
            + '<div class="ivan-fgroup">' + typeBtns + '</div>'
            + '<input class="ivan-search" placeholder="Search unit, make, plate…" value="' + _esc(_es.search) + '" data-action="search-equip">'
            + '<button class="ivan-btn" data-action="open-add-equip">+ Add Equipment</button>'
            + '</div></div>'
            + '<div class="table-wrap"><table class="ivan-table"><thead><tr>'
            + _sortTh('Type',               'type')
            + _sortTh('Unit',               'unitNumber')
            + _sortTh('Year / Make / Model','year')
            + _sortTh('Plate',              'plate')
            + _sortTh('DOT Inspection',     'dotInspectionDate')
            + _sortTh('Ownership',          'ownership')
            + _sortTh('Insurance',          'insured')
            + _sortTh('Open Tasks',         'openTasks')
            + _sortTh('Repair Spend',       'repairSpend')
            + '<th></th>'
            + '</tr></thead><tbody>'
            + (rows || '<tr><td colspan="10" style="color:' + C.muted + ';text-align:center;padding:1.5rem">No equipment found.</td></tr>')
            + '</tbody></table></div></div>';
    }

    // ── Equipment detail panel ────────────────────────────────────────────
    function _htmlDetailPanel(equipId) {
        var eq = _findEquip(equipId);
        if (!eq) return '';

        var maint  = getEquipmentMaintenanceHistory(equipId);
        var invs   = getEquipmentInvoices(equipId);
        var spend  = getRepairSpendByEquipment(equipId);
        var today  = _today();

        var open = maint.filter(function (m) { return m.status !== 'completed'; })
                        .sort(function (a, b) { return a.dueDate.localeCompare(b.dueDate); });
        var done = maint.filter(function (m) { return m.status === 'completed'; })
                        .sort(function (a, b) { return (b.completedAt || '').localeCompare(a.completedAt || ''); });

        var openRows = open.map(function (m) {
            var days   = _daysUntil(m.dueDate);
            var dLabel = days === 0 ? 'Today' : days > 0 ? 'In ' + days + 'd' : Math.abs(days) + 'd overdue';
            var dCls   = days < 0 ? 'ivan-val-danger' : days <= 7 ? 'ivan-val-warn' : '';
            return '<tr>'
                + '<td>' + _esc(m.title) + '</td>'
                + '<td>' + _priorityBadge(m.priority) + '</td>'
                + '<td>' + _statusBadge(m.status) + '</td>'
                + '<td><span class="' + dCls + '">' + dLabel + '</span><br><small style="color:' + C.muted + '">' + _fmtDate(m.dueDate) + '</small></td>'
                + '<td>' + _esc(m.vendor || '—') + '</td>'
                + '<td>' + (m.estimatedCost != null ? _money(m.estimatedCost) : '—') + '</td>'
                + '<td style="white-space:nowrap">'
                + '<button class="ivan-btn ivan-btn-sm" data-action="mark-complete" data-mtid="' + m.maintenanceTaskId + '">✓</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-maint" data-mtid="' + m.maintenanceTaskId + '" title="Delete task">✕</button>'
                + '</td>'
                + '</tr>';
        }).join('');

        var doneRows = done.map(function (m) {
            return '<tr>'
                + '<td>' + _esc(m.title) + '</td>'
                + '<td>' + _statusBadge('completed') + '</td>'
                + '<td>' + _fmtDate(m.completedAt) + '</td>'
                + '<td>' + _esc(m.vendor || '—') + '</td>'
                + '<td>' + (m.actualCost != null ? _money(m.actualCost) : '—') + '</td>'
                + '<td><button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-maint" data-mtid="' + m.maintenanceTaskId + '" title="Delete task">✕</button></td>'
                + '</tr>';
        }).join('');

        var invRows = invs.map(function (inv) {
            return '<tr>'
                + '<td>' + _fmtDate(inv.invoiceDate) + '</td>'
                + '<td>' + _esc(inv.vendor || '—') + '</td>'
                + '<td>' + _esc(inv.invoiceNumber || '—') + '</td>'
                + '<td>' + _money(inv.totalAmount) + '</td>'
                + '<td style="max-width:220px;white-space:normal">' + _esc(inv.description || '—') + '</td>'
                + '<td>' + (inv.fileRef
                    ? '<span class="ivan-badge ivan-badge-done">' + _esc(inv.fileRef) + '</span>'
                    : '<span style="color:' + C.muted + '">No file</span>') + '</td>'
                + '<td><button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-inv" data-invid="' + inv.invoiceId + '" title="Delete invoice">✕</button></td>'
                + '</tr>';
        }).join('');

        function dfield(lbl, val) {
            return '<div class="ivan-dfield"><div class="ivan-dlbl">' + lbl + '</div><div class="ivan-dval">' + val + '</div></div>';
        }

        return '<div class="chart-card ivan-detail">'
            + '<div class="ivan-section-hdr" style="margin-bottom:1rem">'
            + '<div>'
            + '<span style="font-size:1.2rem;font-weight:700;color:' + C.fg + '">' + _esc(eq.unitNumber) + (eq.nickname ? ' · ' + _esc(eq.nickname) : '') + '</span>'
            + '&nbsp;&nbsp;' + _typeBadge(eq.type)
            + (eq.active ? '&nbsp;<span class="ivan-badge ivan-badge-active">Active</span>' : '&nbsp;<span class="ivan-badge ivan-badge-inactive">Inactive</span>')
            + '</div>'
            + '<div style="display:flex;gap:.5rem">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="edit-equip" data-equipid="' + eq.id + '">Edit</button>'
            + '<button class="ivan-btn ivan-btn-danger" data-action="delete-equip" data-equipid="' + eq.id + '">Delete</button>'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-detail">✕ Close</button>'
            + '</div>'
            + '</div>'

            + '<div class="ivan-dgrid">'
            + dfield('Year / Make / Model', eq.year + ' ' + _esc(eq.make) + ' ' + _esc(eq.model))
            + dfield('VIN',   _esc(eq.vin   || '—'))
            + dfield('Plate', _esc(eq.plate || '—'))
            + dfield('Mileage', eq.mileage != null ? Number(eq.mileage).toLocaleString() + ' mi' : '—')
            + dfield('DOT Inspection', eq.dotInspectionDate ? _dotInspBadge(eq.dotInspectionDate) + '&nbsp;<small style="color:' + C.muted + '">Last: ' + _fmtDate(eq.dotInspectionDate) + '</small>' : '<span style="color:' + C.muted + '">Not set</span>')
            + dfield('Notes', _esc(eq.notes || '—'))
            + dfield(_es.spendPeriod === 'year' ? 'Repair Spend (YTD)' : 'Repair Spend (All Time)', _money(spend))
            + '</div>'

            + '<div style="margin:.75rem 0;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">'
            + '<span style="font-weight:600;color:' + C.fg + '">Insurance:</span>'
            + _insuranceBadge(eq.insured)
            + '<label class="ivan-toggle" title="Toggle insurance">'
            + '<input type="checkbox" ' + (eq.insured ? 'checked' : '') + ' data-action="toggle-ins" data-equipid="' + eq.id + '">'
            + '<span class="ivan-toggle-track"><span class="ivan-toggle-thumb"></span></span></label>'
            + '</div>'

            + '<div class="ivan-detail-sub-hdr">'
            + '<strong style="color:' + C.fg + '">Open Maintenance (' + open.length + ')</strong>'
            + '<button class="ivan-btn ivan-btn-sm" data-action="open-add-maint" data-equipid="' + eq.id + '">+ Add Task</button>'
            + '</div>'
            + (openRows
                ? '<div class="table-wrap"><table class="ivan-table"><thead><tr><th>Task</th><th>Priority</th><th>Status</th><th>Due</th><th>Vendor</th><th>Est. Cost</th><th></th><th></th></tr></thead><tbody>' + openRows + '</tbody></table></div>'
                : '<p style="color:' + C.muted + ';font-size:.875rem">No open tasks.</p>')

            + '<div class="ivan-detail-sub-hdr"><strong style="color:' + C.fg + '">Completed Maintenance (' + done.length + ')</strong></div>'
            + (doneRows
                ? '<div class="table-wrap"><table class="ivan-table"><thead><tr><th>Task</th><th>Status</th><th>Completed</th><th>Vendor</th><th>Actual Cost</th><th></th></tr></thead><tbody>' + doneRows + '</tbody></table></div>'
                : '<p style="color:' + C.muted + ';font-size:.875rem">No completed tasks.</p>')

            + '<div class="ivan-detail-sub-hdr">'
            + '<strong style="color:' + C.fg + '">Invoices &amp; Repair History (' + invs.length + ')</strong>'
            + '<button class="ivan-btn ivan-btn-sm" data-action="open-add-inv" data-equipid="' + eq.id + '">+ Upload Invoice</button>'
            + '</div>'
            + (invRows
                ? '<div class="table-wrap"><table class="ivan-table"><thead><tr><th>Date</th><th>Vendor</th><th>Invoice #</th><th>Amount</th><th>Description</th><th>File</th><th></th></tr></thead><tbody>' + invRows + '</tbody></table></div>'
                : '<p style="color:' + C.muted + ';font-size:.875rem">No invoices yet.</p>')

            + '</div>';
    }

    // ── Modals ────────────────────────────────────────────────────────────

    function _htmlEquipModal() {
        return '<div id="ivan-equip-modal" class="ivan-overlay">'
            + '<div class="ivan-modal">'
            + '<div class="ivan-modal-hdr"><span id="ivan-equip-modal-title">Add Equipment</span>'
            + '<button class="ivan-mclose" data-action="close-equip-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + '<div class="ivan-frow">'
            + _fgroup('Type *',        '<select name="type" class="ivan-input"><option value="truck">Truck</option><option value="trailer">Trailer</option></select>')
            + _fgroup('Unit Number *', '<input name="unitNumber" class="ivan-input" placeholder="e.g. T-03">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Nickname',      '<input name="nickname" class="ivan-input" placeholder="Optional label">')
            + _fgroup('Year',          '<input name="year" type="number" class="ivan-input" placeholder="e.g. 2022">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Make',          '<input name="make" class="ivan-input" placeholder="e.g. Freightliner">')
            + _fgroup('Model',         '<input name="model" class="ivan-input" placeholder="e.g. Cascadia">')
            + '</div><div class="ivan-frow">'
            + _fgroup('VIN',           '<input name="vin" class="ivan-input" placeholder="Optional">')
            + _fgroup('Plate Number',  '<input name="plate" class="ivan-input" placeholder="Optional">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Ownership', '<select name="ownership" class="ivan-input"><option value="owned">Owned</option><option value="leased">Leased</option><option value="rented">Rented</option><option value="financed">Financed</option></select>')
            + _fgroup('Mileage', '<input name="mileage" type="number" class="ivan-input" placeholder="Optional">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Last DOT Inspection', '<input name="dotInspectionDate" type="date" class="ivan-input">')
            + '<div class="ivan-fg"></div>'
            + '</div>'
            + '<div class="ivan-frow">'
            + '<div class="ivan-fg" style="display:flex;align-items:flex-end;padding-bottom:.25rem">'
            + '<label style="display:flex;align-items:center;gap:.5rem;color:' + C.fg + ';cursor:pointer">'
            + '<input name="insured" type="checkbox" checked> Insured</label></div>'
            + '</div>'
            + _fgroup('Notes', '<textarea name="notes" class="ivan-input ivan-ta" rows="2" placeholder="Optional notes"></textarea>')
            + '</div>'
            + '<div class="ivan-modal-ftr">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-equip-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-equip" id="ivan-equip-save-btn">Add Equipment</button>'
            + '</div></div></div>';
    }

    function _htmlMaintModal() {
        var opts = _equipment.filter(function (e) { return e.active; }).map(function (e) {
            return '<option value="' + e.id + '">' + _esc(e.unitNumber) + (e.nickname ? ' · ' + _esc(e.nickname) : '') + ' (' + e.type + ')</option>';
        }).join('');
        return '<div id="ivan-maint-modal" class="ivan-overlay">'
            + '<div class="ivan-modal">'
            + '<div class="ivan-modal-hdr"><span id="ivan-maint-modal-title">Add Maintenance Task</span>'
            + '<button class="ivan-mclose" data-action="close-maint-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + '<div class="ivan-frow">'
            + _fgroup('Equipment *', '<select name="equipmentId" id="ivan-maint-equip-sel" class="ivan-input">' + opts + '</select>')
            + _fgroup('Priority *',  '<select name="priority" class="ivan-input"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select>')
            + '</div>'
            + _fgroup('Title *', '<input name="title" class="ivan-input" placeholder="e.g. Oil Change">')
            + _fgroup('Description', '<textarea name="description" class="ivan-input ivan-ta" rows="2" placeholder="Optional details"></textarea>')
            + '<div class="ivan-frow">'
            + _fgroup('Due Date *', '<input name="dueDate" type="date" class="ivan-input">')
            + _fgroup('Status',     '<select name="status" class="ivan-input"><option value="upcoming">Upcoming</option><option value="in_progress">In Progress</option></select>')
            + '</div><div class="ivan-frow">'
            + _fgroup('Vendor / Shop',  '<input name="vendor" class="ivan-input" placeholder="Optional">')
            + _fgroup('Estimated Cost', '<input name="estimatedCost" type="number" step="0.01" class="ivan-input" placeholder="0.00">')
            + '</div>'
            + _fgroup('Mileage Due', '<input name="milageDue" type="number" class="ivan-input" placeholder="Optional odometer reading">')
            + '</div>'
            + '<div class="ivan-modal-ftr">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-maint-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-maint" id="ivan-maint-save-btn">Add Task</button>'
            + '</div></div></div>';
    }

    function _htmlPaymentModal() {
        return '<div id="ivan-payment-modal" class="ivan-overlay">'
            + '<div class="ivan-modal" style="max-width:400px">'
            + '<div class="ivan-modal-hdr"><span>Record Payment</span>'
            + '<button class="ivan-mclose" data-action="close-payment-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + _fgroup('Payment Method', '<select name="paymentMethod" class="ivan-input">'
                + '<option value="">Select…</option>'
                + '<option value="Check">Check</option>'
                + '<option value="ACH / Bank Transfer">ACH / Bank Transfer</option>'
                + '<option value="Credit Card">Credit Card</option>'
                + '<option value="Cash">Cash</option>'
                + '<option value="Zelle">Zelle</option>'
                + '<option value="Other">Other</option>'
                + '</select>')
            + _fgroup('Payment Date', '<input name="paymentDate" type="date" class="ivan-input">')
            + '</div>'
            + '<div class="ivan-modal-ftr">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-payment-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-payment">Save Payment</button>'
            + '</div></div></div>';
    }

    function _htmlHistoryEditModal() {
        return '<div id="ivan-hist-modal" class="ivan-overlay">'
            + '<div class="ivan-modal">'
            + '<div class="ivan-modal-hdr"><span>Edit Invoice</span>'
            + '<button class="ivan-mclose" data-action="close-hist-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + '<div class="ivan-frow">'
            + _fgroup('Invoice Date',   '<input name="hist_invoiceDate" type="date" class="ivan-input">')
            + _fgroup('Invoice Number', '<input name="hist_invoiceNumber" class="ivan-input" placeholder="Optional">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Vendor / Shop',  '<input name="hist_vendor" class="ivan-input">')
            + _fgroup('Total Amount',   '<input name="hist_totalAmount" type="number" step="0.01" class="ivan-input">')
            + '</div>'
            + _fgroup('Description', '<textarea name="hist_description" class="ivan-input ivan-ta" rows="2"></textarea>')
            + '<div class="ivan-frow">'
            + _fgroup('Payment Method', '<select name="hist_paymentMethod" class="ivan-input">'
                + '<option value="">— Not recorded —</option>'
                + '<option value="Check">Check</option>'
                + '<option value="ACH / Bank Transfer">ACH / Bank Transfer</option>'
                + '<option value="Credit Card">Credit Card</option>'
                + '<option value="Cash">Cash</option>'
                + '<option value="Zelle">Zelle</option>'
                + '<option value="Other">Other</option>'
                + '</select>')
            + _fgroup('Payment Date', '<input name="hist_paymentDate" type="date" class="ivan-input">')
            + '</div>'
            + '</div>'
            + '<div class="ivan-modal-ftr" style="justify-content:space-between">'
            + '<button class="ivan-btn ivan-btn-danger" data-action="delete-hist-record">Delete</button>'
            + '<div style="display:flex;gap:.6rem">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-hist-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-hist-edit" id="ivan-hist-save-btn">Save Changes</button>'
            + '</div></div></div></div>';
    }

    function _htmlInvoiceModal() {
        var opts = _equipment.filter(function (e) { return e.active; }).map(function (e) {
            return '<option value="' + e.id + '">' + _esc(e.unitNumber) + (e.nickname ? ' · ' + _esc(e.nickname) : '') + ' (' + e.type + ')</option>';
        }).join('');
        return '<div id="ivan-inv-modal" class="ivan-overlay">'
            + '<div class="ivan-modal">'
            + '<div class="ivan-modal-hdr"><span>Upload Invoice</span>'
            + '<button class="ivan-mclose" data-action="close-inv-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + '<div class="ivan-phase-note">Phase 1 — Enter invoice details manually. File name is stored for reference. Automatic text extraction from PDF/image is planned for Phase 2.</div>'
            + '<div class="ivan-frow">'
            + _fgroup('Equipment *',    '<select name="equipmentId" id="ivan-inv-equip-sel" class="ivan-input">' + opts + '</select>')
            + _fgroup('Invoice Date *', '<input name="invoiceDate" type="date" class="ivan-input">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Vendor / Shop *',  '<input name="vendor" class="ivan-input" placeholder="e.g. Chicago Truck Service">')
            + _fgroup('Invoice Number',   '<input name="invoiceNumber" class="ivan-input" placeholder="Optional">')
            + '</div><div class="ivan-frow">'
            + _fgroup('Total Amount *',       '<input name="totalAmount" type="number" step="0.01" class="ivan-input" placeholder="0.00">')
            + _fgroup('Attach File (PDF/Image)', '<input name="invoiceFile" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" class="ivan-input">')
            + '</div>'
            + _fgroup('Description / Repair Summary *', '<textarea name="description" class="ivan-input ivan-ta" rows="3" placeholder="Describe the repair or service performed"></textarea>')
            + '<div class="ivan-frow">'
            + _fgroup('Payment Method', '<select name="paymentMethod" class="ivan-input">'
                + '<option value="">— Not yet paid —</option>'
                + '<option value="Check">Check</option>'
                + '<option value="ACH / Bank Transfer">ACH / Bank Transfer</option>'
                + '<option value="Credit Card">Credit Card</option>'
                + '<option value="Cash">Cash</option>'
                + '<option value="Zelle">Zelle</option>'
                + '<option value="Other">Other</option>'
                + '</select>')
            + _fgroup('Payment Date', '<input name="paymentDate" type="date" class="ivan-input">')
            + '</div>'
            + '</div>'
            + '<div class="ivan-modal-ftr">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-inv-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-inv">Save Invoice</button>'
            + '</div></div></div>';
    }

    function _fgroup(label, inputHtml) {
        return '<div class="ivan-fg"><label class="ivan-flbl">' + label + '</label>' + inputHtml + '</div>';
    }

    // ── Modal utilities ───────────────────────────────────────────────────
    function _openModal(id)  { var el = document.getElementById(id); if (el) el.classList.add('open'); }
    function _closeModal(id) { var el = document.getElementById(id); if (el) el.classList.remove('open'); }

    function _clearModal(id) {
        var el = document.getElementById(id);
        if (!el) return;
        el.querySelectorAll('input:not([type="checkbox"]):not([type="file"]),select,textarea').forEach(function (f) { f.value = ''; });
        el.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = cb.defaultChecked; });
    }
    function _readForm(id) {
        var el = document.getElementById(id), data = {};
        if (!el) return data;
        el.querySelectorAll('[name]').forEach(function (f) {
            if (f.type === 'checkbox' || f.type === 'file') return;
            data[f.name] = f.value.trim();
        });
        return data;
    }
    function _fillForm(id, data) {
        var el = document.getElementById(id);
        if (!el) return;
        Object.keys(data).forEach(function (k) {
            var f = el.querySelector('[name="' + k + '"]');
            if (f && f.type !== 'file') f.value = data[k] || '';
        });
    }

    // ── Equipment event binding (once per container) ──────────────────────
    function _attachEquipmentListeners(container) {
        // Delegate all clicks
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;
            var a = btn.dataset.action;

            // ── Equipment modal
            if (a === 'open-add-equip') {
                _clearModal('ivan-equip-modal');
                document.getElementById('ivan-equip-modal-title').textContent = 'Add Equipment';
                document.getElementById('ivan-equip-save-btn').removeAttribute('data-editid');
                document.getElementById('ivan-equip-save-btn').textContent = 'Add Equipment';
                _openModal('ivan-equip-modal');
                return;
            }
            if (a === 'edit-equip') {
                var eq = _findEquip(btn.dataset.equipid);
                if (!eq) return;
                _clearModal('ivan-equip-modal');
                _fillForm('ivan-equip-modal', eq);
                document.querySelector('#ivan-equip-modal [name="insured"]').checked = !!eq.insured;
                document.getElementById('ivan-equip-modal-title').textContent = 'Edit Equipment';
                var sb = document.getElementById('ivan-equip-save-btn');
                sb.dataset.editid = eq.id; sb.textContent = 'Save Changes';
                _openModal('ivan-equip-modal');
                return;
            }
            if (a === 'close-equip-modal') { _closeModal('ivan-equip-modal'); return; }
            if (a === 'save-equip') {
                var data = _readForm('ivan-equip-modal');
                if (!data.type || !data.unitNumber) { alert('Type and Unit Number are required.'); return; }
                data.year    = data.year    ? parseInt(data.year, 10)    : null;
                data.mileage = data.mileage ? parseInt(data.mileage, 10) : null;
                data.insured = !!document.querySelector('#ivan-equip-modal [name="insured"]').checked;
                data.active  = true;
                var eid = btn.dataset.editid;
                if (eid) {
                    // If DOT inspection date is set and next due is in the future,
                    // delete any open auto-DOT tasks for this equipment via API.
                    var dotTasksToDelete = [];
                    if (data.dotInspectionDate) {
                        var next = new Date(data.dotInspectionDate);
                        next.setFullYear(next.getFullYear() + 1);
                        if (next.toISOString().slice(0, 10) >= _today()) {
                            dotTasksToDelete = _maintenance.filter(function (m) {
                                return m.equipmentId === eid && m.status !== 'completed'
                                    && (m.autoDot || m.title === 'DOT Inspection');
                            });
                        }
                    }
                    var deletePromises = dotTasksToDelete.map(function(m) {
                        return _api('DELETE', '/api/ivan/tasks/' + m.maintenanceTaskId);
                    });
                    Promise.all(deletePromises).then(function() {
                        return _api('PUT', '/api/ivan/equipment/' + eid, data);
                    }).then(function() {
                        _closeModal('ivan-equip-modal');
                        _loadAll(function() { _renderEquipmentTab(); });
                    });
                } else {
                    data.id = 'eq-' + _genId();
                    _api('POST', '/api/ivan/equipment', data).then(function() {
                        _closeModal('ivan-equip-modal');
                        _loadAll(function() { _renderEquipmentTab(); });
                    });
                }
                return;
            }

            // ── Select / deselect equipment row
            if (a === 'select-equip') {
                var id = e.target.closest('[data-equipid]') ? e.target.closest('[data-equipid]').dataset.equipid : btn.dataset.equipid;
                _es.selectedId = (_es.selectedId === id) ? null : id;
                _renderEquipmentTab();
                if (_es.selectedId) {
                    setTimeout(function () {
                        var panel = container.querySelector('.ivan-detail');
                        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 60);
                }
                return;
            }
            if (a === 'close-detail') { _es.selectedId = null; _renderEquipmentTab(); return; }

            // ── Maintenance modal
            if (a === 'open-add-maint') {
                _clearModal('ivan-maint-modal');
                document.getElementById('ivan-maint-modal-title').textContent = 'Add Maintenance Task';
                var sel = document.getElementById('ivan-maint-equip-sel');
                if (sel && btn.dataset.equipid) sel.value = btn.dataset.equipid;
                var dd = document.querySelector('#ivan-maint-modal [name="dueDate"]');
                if (dd) dd.value = _today();
                var saveBtn = document.getElementById('ivan-maint-save-btn');
                if (saveBtn) { saveBtn.removeAttribute('data-editid'); saveBtn.textContent = 'Add Task'; }
                _openModal('ivan-maint-modal');
                return;
            }
            if (a === 'close-maint-modal') { _closeModal('ivan-maint-modal'); return; }
            if (a === 'save-maint') {
                var data = _readForm('ivan-maint-modal');
                if (!data.equipmentId || !data.title || !data.dueDate) { alert('Equipment, Title, and Due Date are required.'); return; }
                // Map form priority 'medium' → API 'med'
                var apiPriority = data.priority === 'medium' ? 'med' : (data.priority || 'med');
                var taskPayload = {
                    id:       'mt-' + _genId(),
                    equipId:  data.equipmentId,
                    title:    data.title,
                    dueDate:  data.dueDate,
                    priority: apiPriority,
                    status:   data.status || 'upcoming',
                    notes:    data.description || '',
                    autoDot:  false
                };
                _api('POST', '/api/ivan/tasks', taskPayload).then(function() {
                    _closeModal('ivan-maint-modal');
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }

            // ── Mark complete
            if (a === 'mark-complete') {
                _api('PUT', '/api/ivan/tasks/' + btn.dataset.mtid, { status: 'complete' }).then(function() {
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }

            // ── Delete equipment (cascades tasks + invoices via DB)
            if (a === 'delete-equip') {
                var eq = _findEquip(btn.dataset.equipid);
                if (!eq) return;
                if (!confirm('Delete ' + eq.unitNumber + (eq.nickname ? ' (' + eq.nickname + ')' : '') + '?\n\nThis will also delete all maintenance tasks and invoices linked to this equipment.')) return;
                if (_es.selectedId === btn.dataset.equipid) _es.selectedId = null;
                _api('DELETE', '/api/ivan/equipment/' + btn.dataset.equipid).then(function() {
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }

            // ── Delete maintenance task
            if (a === 'delete-maint') {
                if (!confirm('Delete this maintenance task?')) return;
                _api('DELETE', '/api/ivan/tasks/' + btn.dataset.mtid).then(function() {
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }

            // ── Delete invoice
            if (a === 'delete-inv') {
                if (!confirm('Delete this invoice record?')) return;
                _api('DELETE', '/api/ivan/invoices/' + btn.dataset.invid).then(function() {
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }

            // ── Invoice modal
            if (a === 'open-add-inv') {
                _clearModal('ivan-inv-modal');
                var sel = document.getElementById('ivan-inv-equip-sel');
                if (sel && btn.dataset.equipid) sel.value = btn.dataset.equipid;
                var dd = document.querySelector('#ivan-inv-modal [name="invoiceDate"]');
                if (dd) dd.value = _today();
                _openModal('ivan-inv-modal');
                return;
            }
            if (a === 'close-payment-modal') { _closeModal('ivan-payment-modal'); return; }
            if (a === 'open-pay-modal') {
                _clearModal('ivan-payment-modal');
                var saveBtn = document.getElementById('ivan-payment-modal').querySelector('[data-action="save-payment"]');
                saveBtn.dataset.paytype = btn.dataset.paytype;
                saveBtn.dataset.payid   = btn.dataset.payid;
                // Default date to today
                var pd = document.querySelector('#ivan-payment-modal [name="paymentDate"]');
                if (pd) pd.value = _today();
                _openModal('ivan-payment-modal');
                return;
            }
            if (a === 'save-payment') {
                var payMethod = document.querySelector('#ivan-payment-modal [name="paymentMethod"]').value;
                var payDate   = document.querySelector('#ivan-payment-modal [name="paymentDate"]').value;
                if (!payMethod) { alert('Please select a payment method.'); return; }
                var ptype = btn.dataset.paytype, pid = btn.dataset.payid;
                if (ptype === 'invoice') {
                    _api('PUT', '/api/ivan/invoices/' + pid, { paymentMethod: payMethod, paymentDate: payDate }).then(function() {
                        _closeModal('ivan-payment-modal');
                        _loadAll(function() { _renderEquipmentTab(); });
                    });
                } else {
                    _api('PUT', '/api/ivan/tasks/' + pid, { paymentMethod: payMethod, paymentDate: payDate }).then(function() {
                        _closeModal('ivan-payment-modal');
                        _loadAll(function() { _renderEquipmentTab(); });
                    });
                }
                return;
            }
            if (a === 'close-hist-modal') { _closeModal('ivan-hist-modal'); return; }
            if (a === 'open-hist-edit') {
                var inv = _invoices.find(function (i) { return i.invoiceId === btn.dataset.payid; });
                if (!inv) return;
                var sb = document.getElementById('ivan-hist-save-btn');
                sb.dataset.payid = inv.invoiceId;
                document.querySelector('#ivan-hist-modal [name="hist_invoiceDate"]').value   = inv.invoiceDate   || '';
                document.querySelector('#ivan-hist-modal [name="hist_invoiceNumber"]').value = inv.invoiceNumber || '';
                document.querySelector('#ivan-hist-modal [name="hist_vendor"]').value        = inv.vendor        || '';
                document.querySelector('#ivan-hist-modal [name="hist_totalAmount"]').value   = inv.totalAmount != null ? inv.totalAmount : '';
                document.querySelector('#ivan-hist-modal [name="hist_description"]').value   = inv.description   || '';
                document.querySelector('#ivan-hist-modal [name="hist_paymentMethod"]').value = inv.paymentMethod || '';
                document.querySelector('#ivan-hist-modal [name="hist_paymentDate"]').value   = inv.paymentDate   || '';
                _openModal('ivan-hist-modal');
                return;
            }
            if (a === 'save-hist-edit') {
                var pid = btn.dataset.payid;
                var payload = {
                    date:          document.querySelector('#ivan-hist-modal [name="hist_invoiceDate"]').value,
                    invoiceNumber: document.querySelector('#ivan-hist-modal [name="hist_invoiceNumber"]').value,
                    vendor:        document.querySelector('#ivan-hist-modal [name="hist_vendor"]').value,
                    amount:        parseFloat(document.querySelector('#ivan-hist-modal [name="hist_totalAmount"]').value) || 0,
                    description:   document.querySelector('#ivan-hist-modal [name="hist_description"]').value,
                    paymentMethod: document.querySelector('#ivan-hist-modal [name="hist_paymentMethod"]').value || '',
                    paymentDate:   document.querySelector('#ivan-hist-modal [name="hist_paymentDate"]').value   || ''
                };
                _api('PUT', '/api/ivan/invoices/' + pid, payload).then(function() {
                    _closeModal('ivan-hist-modal');
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }
            if (a === 'delete-hist-record') {
                var pid = document.getElementById('ivan-hist-save-btn').dataset.payid;
                if (!confirm('Delete this invoice? This cannot be undone.')) return;
                _api('DELETE', '/api/ivan/invoices/' + pid).then(function() {
                    _closeModal('ivan-hist-modal');
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }
            if (a === 'close-inv-modal') { _closeModal('ivan-inv-modal'); return; }
            if (a === 'save-inv') {
                var data = _readForm('ivan-inv-modal');
                if (!data.equipmentId || !data.invoiceDate || !data.vendor || !data.totalAmount) {
                    alert('Equipment, Date, Vendor, and Amount are required.'); return;
                }
                var fi = document.querySelector('#ivan-inv-modal [name="invoiceFile"]');
                var invPayload = {
                    id:            'inv-' + _genId(),
                    equipId:       data.equipmentId,
                    date:          data.invoiceDate,
                    vendor:        data.vendor,
                    invoiceNumber: data.invoiceNumber || '',
                    amount:        parseFloat(data.totalAmount) || 0,
                    description:   data.description || '',
                    paymentMethod: data.paymentMethod || '',
                    paymentDate:   data.paymentDate   || ''
                };
                _api('POST', '/api/ivan/invoices', invPayload).then(function() {
                    _es.histPage = 0;
                    _closeModal('ivan-inv-modal');
                    _loadAll(function() { _renderEquipmentTab(); });
                });
                return;
            }
        });

        // Spend period toggle
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-spendperiod]');
            if (!btn) return;
            _es.spendPeriod = btn.dataset.spendperiod;
            _renderEquipmentTab();
        });

        // Maintenance history pagination
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-histpage]');
            if (!btn || btn.disabled) return;
            var p = parseInt(btn.dataset.histpage, 10);
            if (!isNaN(p) && p >= 0) { _es.histPage = p; _renderEquipmentTab(); }
        });

        // Column sort
        container.addEventListener('click', function (e) {
            var th = e.target.closest('[data-sort]');
            if (!th) return;
            var col = th.dataset.sort;
            if (_es.sortCol === col) {
                _es.sortDir = _es.sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                _es.sortCol = col;
                _es.sortDir = 'asc';
            }
            _renderEquipmentTab();
        });

        // Equipment type filter buttons
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-efilter]');
            if (!btn) return;
            _es.filter = btn.dataset.efilter;
            _renderEquipmentTab();
        });

        // Maintenance filter buttons
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-mfilter]');
            if (!btn) return;
            _es.mFilter = btn.dataset.mfilter;
            _renderEquipmentTab();
        });

        // Search
        container.addEventListener('input', function (e) {
            if (e.target.dataset.action === 'search-equip') {
                _es.search = e.target.value;
                _renderEquipmentTab();
            }
        });

        // Insurance toggle + ownership select (change events)
        container.addEventListener('change', function (e) {
            if (e.target.dataset.action === 'toggle-ins') {
                e.stopPropagation();
                var equipId = e.target.dataset.equipid;
                var eq = _findEquip(equipId);
                if (!eq) return;
                _api('PUT', '/api/ivan/equipment/' + equipId, { insured: !eq.insured }).then(function() {
                    _loadAll(function() { _renderEquipmentTab(); });
                });
            }
            if (e.target.dataset.action === 'set-ownership') {
                e.stopPropagation();
                _api('PUT', '/api/ivan/equipment/' + e.target.dataset.equipid, { ownership: e.target.value });
            }
        });

        // Overlay background click → close modal
        container.addEventListener('click', function (e) {
            if (e.target.classList.contains('ivan-overlay')) {
                e.target.classList.remove('open');
            }
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    // DRIVERS TAB — HTML builders
    // ══════════════════════════════════════════════════════════════════════

    function _renderDriversTab() {
        var container = document.getElementById(_driverCid);
        if (!container) return;
        container.innerHTML = _htmlDrivers();
    }

    function _htmlDrivers() {
        var q = _ds.search.toLowerCase();
        var list = _drivers.filter(function (d) {
            if (!q) return true;
            return (d.name  || '').toLowerCase().indexOf(q) >= 0
                || (d.phone || '').toLowerCase().indexOf(q) >= 0
                || (d.email || '').toLowerCase().indexOf(q) >= 0
                || (d.cdl   || '').toLowerCase().indexOf(q) >= 0;
        });

        var rows = list.map(function (d) {
            var truck = _findEquip(d.assignedTruckId);
            var tLabel = truck ? (_esc(truck.unitNumber) + (truck.nickname ? ' · ' + _esc(truck.nickname) : '')) : '—';
            var isOO   = d.driverType === 'owner_operator';
            var typeBadge = isOO
                ? '<span class="ivan-badge ivan-badge-oo">Owner Op</span>'
                : '<span class="ivan-badge ivan-badge-company">Company</span>';
            return '<tr>'
                + '<td><strong>' + _esc(d.name) + '</strong></td>'
                + '<td>' + _esc(d.phone || '—') + '</td>'
                + '<td>' + (d.email ? '<a href="mailto:' + _esc(d.email) + '" style="color:' + C.accent + '">' + _esc(d.email) + '</a>' : '—') + '</td>'
                + '<td>' + _esc(d.cdl || '—') + '</td>'
                + '<td>' + (d.status === 'active'
                    ? '<span class="ivan-badge ivan-badge-active">Active</span>'
                    : '<span class="ivan-badge ivan-badge-inactive">Inactive</span>') + '</td>'
                + '<td style="white-space:nowrap">'
                + typeBadge + '&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="toggle-driver-type" data-driverid="' + d.id + '" title="Switch type">Switch</button>'
                + '</td>'
                + '<td>' + tLabel + '</td>'
                + '<td style="max-width:160px;white-space:normal">' + _esc(d.notes || '—') + '</td>'
                + '<td style="white-space:nowrap">'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-ghost" data-action="edit-driver" data-driverid="' + d.id + '">Edit</button>&nbsp;'
                + '<button class="ivan-btn ivan-btn-sm ivan-btn-danger" data-action="delete-driver" data-driverid="' + d.id + '">Delete</button>'
                + '</td>'
                + '</tr>';
        }).join('');

        var truckOpts = '<option value="">— Unassigned —</option>'
            + _equipment.filter(function (e) { return e.type === 'truck' && e.active; }).map(function (e) {
                return '<option value="' + e.id + '">' + _esc(e.unitNumber) + (e.nickname ? ' · ' + _esc(e.nickname) : '') + '</option>';
            }).join('');

        var modal = '<div id="ivan-driver-modal" class="ivan-overlay">'
            + '<div class="ivan-modal">'
            + '<div class="ivan-modal-hdr"><span id="ivan-driver-modal-title">Add Driver</span>'
            + '<button class="ivan-mclose" data-action="close-driver-modal">✕</button></div>'
            + '<div class="ivan-modal-body">'
            + '<div class="ivan-frow">'
            + _fgroup('Full Name *', '<input name="name" class="ivan-input" placeholder="First Last">')
            + _fgroup('Status',      '<select name="status" class="ivan-input"><option value="active">Active</option><option value="inactive">Inactive</option></select>')
            + '</div><div class="ivan-frow">'
            + _fgroup('Driver Type', '<select name="driverType" class="ivan-input"><option value="company_driver">Company Driver</option><option value="owner_operator">Owner Operator</option></select>')
            + '<div class="ivan-fg"></div>'
            + '</div><div class="ivan-frow">'
            + _fgroup('Phone', '<input name="phone" class="ivan-input" placeholder="(312) 555-0100">')
            + _fgroup('Email', '<input name="email" type="email" class="ivan-input" placeholder="driver@example.com">')
            + '</div><div class="ivan-frow">'
            + _fgroup('CDL / License', '<input name="cdl" class="ivan-input" placeholder="e.g. CDL-A IL-1234567">')
            + _fgroup('Assigned Truck', '<select name="assignedTruckId" class="ivan-input">' + truckOpts + '</select>')
            + '</div>'
            + _fgroup('Notes', '<textarea name="notes" class="ivan-input ivan-ta" rows="2" placeholder="Optional"></textarea>')
            + '</div>'
            + '<div class="ivan-modal-ftr">'
            + '<button class="ivan-btn ivan-btn-ghost" data-action="close-driver-modal">Cancel</button>'
            + '<button class="ivan-btn" data-action="save-driver" id="ivan-driver-save-btn">Add Driver</button>'
            + '</div></div></div>';

        return '<div class="ivan-section-hdr" style="margin-bottom:1.25rem">'
            + '<div class="section-title" style="margin:0">Drivers</div>'
            + '<div style="display:flex;gap:.6rem;align-items:center">'
            + '<input class="ivan-search" placeholder="Search name, phone, CDL…" value="' + _esc(_ds.search) + '" data-action="search-driver">'
            + '<button class="ivan-btn" data-action="open-add-driver">+ Add Driver</button>'
            + '</div></div>'
            + '<div class="chart-card"><div class="table-wrap">'
            + '<table class="ivan-table"><thead><tr>'
            + '<th>Name</th><th>Phone</th><th>Email</th><th>CDL</th><th>Status</th><th>Driver Type</th><th>Assigned Truck</th><th>Notes</th><th></th>'
            + '</tr></thead><tbody>'
            + (rows || '<tr><td colspan="9" style="color:' + C.muted + ';text-align:center;padding:1.5rem">No drivers found. Add a driver to get started.</td></tr>')
            + '</tbody></table></div></div>'
            + modal;
    }

    function _bindDriverEvents(container) {
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;
            var a = btn.dataset.action;

            if (a === 'open-add-driver') {
                _clearModal('ivan-driver-modal');
                document.getElementById('ivan-driver-modal-title').textContent = 'Add Driver';
                var sb = document.getElementById('ivan-driver-save-btn');
                sb.removeAttribute('data-editid'); sb.textContent = 'Add Driver';
                _openModal('ivan-driver-modal');
                return;
            }
            if (a === 'close-driver-modal') { _closeModal('ivan-driver-modal'); return; }

            if (a === 'edit-driver') {
                var d = _findDriver(btn.dataset.driverid);
                if (!d) return;
                _clearModal('ivan-driver-modal');
                _fillForm('ivan-driver-modal', d);
                document.getElementById('ivan-driver-modal-title').textContent = 'Edit Driver';
                var sb = document.getElementById('ivan-driver-save-btn');
                sb.dataset.editid = d.id; sb.textContent = 'Save Changes';
                _openModal('ivan-driver-modal');
                return;
            }

            if (a === 'save-driver') {
                var data = _readForm('ivan-driver-modal');
                if (!data.name) { alert('Name is required.'); return; }
                var eid = btn.dataset.editid;
                if (eid) {
                    var i = _drivers.findIndex(function (d) { return d.id === eid; });
                    if (i >= 0) { _drivers[i] = Object.assign({}, _drivers[i], data); _saveLS(LS_DRIVERS, _drivers); }
                } else {
                    data.id = 'drv-' + _genId(); data.createdAt = _nowIso();
                    _drivers.push(data); _saveLS(LS_DRIVERS, _drivers);
                }
                _closeModal('ivan-driver-modal');
                _renderDriversTab();
                return;
            }

            if (a === 'toggle-driver-type') {
                var d = _findDriver(btn.dataset.driverid);
                if (!d) return;
                var next = d.driverType === 'owner_operator' ? 'company_driver' : 'owner_operator';
                var i = _drivers.findIndex(function (x) { return x.id === d.id; });
                if (i >= 0) { _drivers[i] = Object.assign({}, _drivers[i], { driverType: next }); _saveLS(LS_DRIVERS, _drivers); }
                _renderDriversTab();
                return;
            }

            if (a === 'delete-driver') {
                var d = _findDriver(btn.dataset.driverid);
                if (!d) return;
                if (!confirm('Delete driver ' + d.name + '?')) return;
                _drivers = _drivers.filter(function (x) { return x.id !== d.id; });
                _saveLS(LS_DRIVERS, _drivers);
                _renderDriversTab();
                return;
            }
        });

        container.addEventListener('input', function (e) {
            if (e.target.dataset.action === 'search-driver') {
                _ds.search = e.target.value;
                _renderDriversTab();
            }
        });

        container.addEventListener('click', function (e) {
            if (e.target.classList.contains('ivan-overlay')) e.target.classList.remove('open');
        });
    }

    // ══════════════════════════════════════════════════════════════════════
    // PUBLIC MOUNT FUNCTIONS
    // ══════════════════════════════════════════════════════════════════════

    function mountEquipment(containerId) {
        _equipCid = containerId;
        var container = document.getElementById(containerId);
        if (!container) return;
        _loadAll(function() {
            _syncDotInspectionTasks(function() {
                _loadAll(function() {
                    _renderEquipmentTab();
                    if (!container._ivanEquipBound) {
                        _attachEquipmentListeners(container);
                        container._ivanEquipBound = true;
                    }
                });
            });
        });
    }

    function mountDrivers(containerId) {
        _driverCid = containerId;
        var container = document.getElementById(containerId);
        if (!container) return;
        _drivers = _loadLS(LS_DRIVERS);
        _renderDriversTab();
        if (!container._ivanDriverBound) {
            _bindDriverEvents(container);
            container._ivanDriverBound = true;
        }
    }

    return {
        mountEquipment: mountEquipment,
        mountDrivers:   mountDrivers
    };
}());
