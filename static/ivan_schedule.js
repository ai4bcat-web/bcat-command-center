/**
 * ivan_schedule.js — Driver Scheduling / Dispatch Board for Ivan Cartage
 * IIFE module: IvanScheduleApp.mountSchedule(containerId)
 *
 * Backend API:
 *   GET  /api/ivan/schedule?weekStart=YYYY-MM-DD
 *   POST /api/ivan/schedule/entries          { ...fields }
 *   PUT  /api/ivan/schedule/entries/:id      { ...fields }
 *   DELETE /api/ivan/schedule/entries/:id
 *   POST /api/ivan/schedule/entries/reorder  { entries:[{id,dayDate,rowOrder},...] }
 */
var IvanScheduleApp = (function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────────────────
    var _containerId = null;
    var _weekStart   = null;   // ISO Monday string, e.g. '2025-07-14'
    var _entries     = [];     // flat array of entry objects from API
    var _editingId   = null;   // null = new entry

    // ── CSRF / API helper ────────────────────────────────────────────────────
    function _csrf() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function _api(method, path, body) {
        var opts = {
            method: method,
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': _csrf() }
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        return fetch(path, opts).then(function (r) {
            if (!r.ok) return r.json().then(function (e) { throw new Error(e.error || r.statusText); });
            return r.json();
        });
    }

    // ── Week helpers ─────────────────────────────────────────────────────────
    function _mondayOf(date) {
        var d = new Date(date);
        var day = d.getDay();                    // 0=Sun
        var diff = (day === 0) ? -6 : 1 - day;  // Monday offset
        d.setDate(d.getDate() + diff);
        return _isoDate(d);
    }

    function _isoDate(d) {
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var dy = String(d.getDate()).padStart(2, '0');
        return y + '-' + m + '-' + dy;
    }

    function _addDays(iso, n) {
        var d = new Date(iso + 'T00:00:00');
        d.setDate(d.getDate() + n);
        return _isoDate(d);
    }

    function _weekDays(weekMon) {
        return [0, 1, 2, 3, 4].map(function (i) {
            return _addDays(weekMon, i);
        });
    }

    function _fmtWeekLabel(weekMon) {
        var d = new Date(weekMon + 'T00:00:00');
        var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        var sun = new Date(weekMon + 'T00:00:00');
        sun.setDate(sun.getDate() + 6);
        return 'Week of ' + months[d.getMonth()] + ' ' + d.getDate() + ' – ' +
               months[sun.getMonth()] + ' ' + sun.getDate() + ', ' + sun.getFullYear();
    }

    function _fmtDayHeader(iso) {
        var d = new Date(iso + 'T00:00:00');
        var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
        var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return days[d.getDay()] + ', ' + months[d.getMonth()] + ' ' + d.getDate();
    }

    // ── Deadhead Calculator ──────────────────────────────────────────────────
    // City coordinates lookup — augment as needed
    // Integration point: replace _cityCoords() with a real geocoding call for full coverage
    var CITY_COORDS = {
        'chicago il':          [41.8781, -87.6298],
        'chicago heights il':  [41.5061, -87.6373],
        'kenosha wi':          [42.5847, -87.8212],
        'milwaukee wi':        [43.0389, -87.9065],
        'waukegan il':         [42.3636, -87.8448],
        'joliet il':           [41.5250, -88.0817],
        'racine wi':           [42.7261, -87.7829],
        'rockford il':         [42.2711, -89.0940],
        'elgin il':            [42.0354, -88.2826],
        'gary in':             [41.5934, -87.3464],
        'aurora il':           [41.7606, -88.3201],
        'champaign il':        [40.1164, -88.2434],
        'indianapolis in':     [39.7684, -86.1581],
        'detroit mi':          [42.3314, -83.0458],
        'st louis mo':         [38.6270, -90.1994],
        'base terminal':       [41.8781, -87.6298],  // Default base: Chicago IL
    };

    function _latLon(city, state) {
        if (!city) return null;
        var key = (city + ' ' + (state || '')).toLowerCase().trim();
        return CITY_COORDS[key] || null;
    }

    function _haversineKm(a, b) {
        var R = 6371;
        var dLat = (b[0] - a[0]) * Math.PI / 180;
        var dLon = (b[1] - a[1]) * Math.PI / 180;
        var sin1 = Math.sin(dLat / 2), sin2 = Math.sin(dLon / 2);
        var c = 2 * Math.asin(Math.sqrt(sin1 * sin1 + Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * sin2 * sin2));
        return R * c;
    }

    function _straightMilesToRoad(km) {
        return Math.round(km * 0.621371 * 1.25); // km → miles × road factor
    }

    function _calcDeadhead(puCity, puState, deCity, deState, prevDeCity, prevDeState, isFirst, isLast) {
        var base = CITY_COORDS['base terminal'];
        var pu   = _latLon(puCity, puState);
        var de   = _latLon(deCity, deState);
        var prev = prevDeCity ? _latLon(prevDeCity, prevDeState) : null;

        var start   = 0;
        var between = 0;
        var ret     = 0;

        if (isFirst && pu) {
            start = _straightMilesToRoad(_haversineKm(base, pu));
        }
        if (!isFirst && prev && pu) {
            between = _straightMilesToRoad(_haversineKm(prev, pu));
        }
        if (isLast && de) {
            ret = _straightMilesToRoad(_haversineKm(de, base));
        }

        return { start: start, between: between, ret: ret, total: start + between + ret };
    }

    // ── Data loading ─────────────────────────────────────────────────────────
    function _loadWeek(weekMon, cb) {
        var container = document.getElementById(_containerId);
        if (container) container.innerHTML = '<div class="sch-loading">Loading schedule…</div>';
        _api('GET', '/api/ivan/schedule?weekStart=' + weekMon).then(function (data) {
            _entries = Array.isArray(data) ? data : (data.entries || []);
            _weekStart = weekMon;
            _render();
            if (cb) cb();
        }).catch(function (err) {
            if (container) container.innerHTML = '<div class="sch-error">Failed to load: ' + err.message + '</div>';
        });
    }

    // ── Render ───────────────────────────────────────────────────────────────
    function _render() {
        var container = document.getElementById(_containerId);
        if (!container) return;

        var days = _weekDays(_weekStart);
        var byDay = {};
        days.forEach(function (d) { byDay[d] = []; });
        _entries.forEach(function (e) {
            if (byDay[e.dayDate]) byDay[e.dayDate].push(e);
            else byDay[e.dayDate] = [e];
        });
        days.forEach(function (d) {
            byDay[d].sort(function (a, b) { return a.rowOrder - b.rowOrder; });
        });

        var html = '<div class="sch-board">';

        // ── Week navigation bar ──
        html += '<div class="sch-nav">' +
            '<button class="sch-nav-btn" data-action="prev-week">&#9664; Prev</button>' +
            '<span class="sch-week-label">' + _fmtWeekLabel(_weekStart) + '</span>' +
            '<button class="sch-nav-btn" data-action="next-week">Next &#9654;</button>' +
            '<button class="sch-nav-btn sch-today-btn" data-action="today-week">Today</button>' +
            '<button class="sch-add-btn" data-action="add-entry">+ Add Load</button>' +
            '</div>';

        // ── Dispatch board columns header ──
        html += '<div class="sch-col-header">' +
            '<div class="sch-col sch-col-order"></div>' +
            '<div class="sch-col sch-col-id">PRO #</div>' +
            '<div class="sch-col sch-col-tms">TMS ID</div>' +
            '<div class="sch-col sch-col-pu">PU #</div>' +
            '<div class="sch-col sch-col-appt">PU Appt</div>' +
            '<div class="sch-col sch-col-appt">DE Appt</div>' +
            '<div class="sch-col sch-col-city">PU City</div>' +
            '<div class="sch-col sch-col-city">DE City</div>' +
            '<div class="sch-col sch-col-dh">DH mi</div>' +
            '<div class="sch-col sch-col-status">Status</div>' +
            '<div class="sch-col sch-col-notes">Notes</div>' +
            '<div class="sch-col sch-col-actions"></div>' +
            '</div>';

        // ── Day groups ──
        days.forEach(function (dayDate) {
            var rows = byDay[dayDate];
            html += '<div class="sch-day-group" data-day="' + dayDate + '">';
            html += '<div class="sch-day-header">' +
                '<span class="sch-day-name">' + _fmtDayHeader(dayDate) + '</span>' +
                '<span class="sch-day-count">' + rows.length + ' load' + (rows.length !== 1 ? 's' : '') + '</span>' +
                '<button class="sch-day-add-btn" data-action="add-entry" data-day="' + dayDate + '">+ Add</button>' +
                '</div>';

            if (rows.length === 0) {
                html += '<div class="sch-empty-day">No loads scheduled</div>';
            } else {
                rows.forEach(function (e, idx) {
                    var isFirst = idx === 0;
                    var isLast  = idx === rows.length - 1;
                    var prevEntry = isFirst ? null : rows[idx - 1];
                    var dh = _calcDeadhead(
                        e.puCity, e.puState, e.deCity, e.deState,
                        prevEntry ? prevEntry.deCity : null,
                        prevEntry ? prevEntry.deState : null,
                        isFirst, isLast
                    );
                    var dhMi = dh.start || dh.between || dh.ret;

                    var statusClass = 'sch-status-' + (e.status || 'pending').replace(/\s+/g, '-');
                    html += '<div class="sch-row" data-id="' + e.id + '">' +
                        '<div class="sch-col sch-col-order">' +
                            (idx > 0 ? '<button class="sch-arrow" data-action="move-up" data-id="' + e.id + '" title="Move up">&#9650;</button>' : '<span class="sch-arrow-ph"></span>') +
                            (idx < rows.length - 1 ? '<button class="sch-arrow" data-action="move-down" data-id="' + e.id + '" title="Move down">&#9660;</button>' : '<span class="sch-arrow-ph"></span>') +
                        '</div>' +
                        '<div class="sch-col sch-col-id">' + _esc(e.alexeiId || '') + '</div>' +
                        '<div class="sch-col sch-col-tms">' + _esc(e.tmsId || '') + '</div>' +
                        '<div class="sch-col sch-col-pu">' + _esc(e.puNumber || '') + '</div>' +
                        '<div class="sch-col sch-col-appt">' + _esc(e.puAppt || '') + '</div>' +
                        '<div class="sch-col sch-col-appt">' + _esc(e.deAppt || '') + '</div>' +
                        '<div class="sch-col sch-col-city">' + _esc(e.puCity || '') + (e.puState ? ', ' + _esc(e.puState) : '') + '</div>' +
                        '<div class="sch-col sch-col-city">' + _esc(e.deCity || '') + (e.deState ? ', ' + _esc(e.deState) : '') + '</div>' +
                        '<div class="sch-col sch-col-dh' + (dhMi > 0 ? ' sch-dh-val' : '') + '">' + (dhMi > 0 ? dhMi + ' mi' : '—') + '</div>' +
                        '<div class="sch-col sch-col-status"><span class="sch-status-badge ' + statusClass + '">' + _esc(e.status || 'pending') + '</span></div>' +
                        '<div class="sch-col sch-col-notes sch-notes-cell" title="' + _esc(e.notes || '') + '">' + _esc((e.notes || '').substring(0, 30)) + (e.notes && e.notes.length > 30 ? '…' : '') + '</div>' +
                        '<div class="sch-col sch-col-actions">' +
                            '<button class="sch-edit-btn" data-action="edit-entry" data-id="' + e.id + '">Edit</button>' +
                            '<button class="sch-del-btn" data-action="del-entry" data-id="' + e.id + '">&#128465;</button>' +
                        '</div>' +
                        '</div>';
                });
            }
            html += '</div>'; // .sch-day-group
        });

        html += '</div>'; // .sch-board
        html += _modalHTML();

        container.innerHTML = html;
        _bindEvents(container);
    }

    function _esc(str) {
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ── Modal HTML ────────────────────────────────────────────────────────────
    function _modalHTML() {
        return '<div id="sch-modal" class="sch-modal-overlay" style="display:none">' +
            '<div class="sch-modal">' +
                '<div class="sch-modal-header">' +
                    '<span id="sch-modal-title">Add Load</span>' +
                    '<button class="sch-modal-close" data-action="close-modal">&#10005;</button>' +
                '</div>' +
                '<div class="sch-modal-body">' +
                    '<div class="sch-form-grid">' +
                        '<label>Day<br><input type="date" id="sf-day" class="sch-inp"></label>' +
                        '<label>PRO # (Alexei ID)<br><input type="text" id="sf-alexei" class="sch-inp" placeholder="PRO-10421"></label>' +
                        '<label>TMS ID<br><input type="text" id="sf-tms" class="sch-inp" placeholder="TMS-8801"></label>' +
                        '<label>PU Number<br><input type="text" id="sf-pu-num" class="sch-inp" placeholder="PU-4421"></label>' +
                        '<label>PU Appt<br><input type="time" id="sf-pu-appt" class="sch-inp"></label>' +
                        '<label>DE Appt<br><input type="time" id="sf-de-appt" class="sch-inp"></label>' +
                        '<label>PU City<br><input type="text" id="sf-pu-city" class="sch-inp" placeholder="Chicago"></label>' +
                        '<label>PU State<br><input type="text" id="sf-pu-state" class="sch-inp" placeholder="IL" maxlength="2"></label>' +
                        '<label>DE City<br><input type="text" id="sf-de-city" class="sch-inp" placeholder="Milwaukee"></label>' +
                        '<label>DE State<br><input type="text" id="sf-de-state" class="sch-inp" placeholder="WI" maxlength="2"></label>' +
                        '<label>Status<br><select id="sf-status" class="sch-inp">' +
                            '<option value="pending" selected>Pending</option>' +
                            '<option value="dispatched">Dispatched</option>' +
                            '<option value="delivered">Delivered</option>' +
                            '<option value="cancelled">Cancelled</option>' +
                        '</select></label>' +
                        '<label>Notes<br><textarea id="sf-notes" class="sch-inp sch-textarea" rows="2"></textarea></label>' +
                    '</div>' +
                '</div>' +
                '<div class="sch-modal-footer">' +
                    '<button class="sch-btn-cancel" data-action="close-modal">Cancel</button>' +
                    '<button class="sch-btn-save" data-action="save-entry">Save Load</button>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    // ── Event Binding ─────────────────────────────────────────────────────────
    function _bindEvents(container) {
        container.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action]');
            if (!btn) return;
            var action = btn.dataset.action;

            if (action === 'prev-week') {
                _loadWeek(_addDays(_weekStart, -7));
            } else if (action === 'next-week') {
                _loadWeek(_addDays(_weekStart, 7));
            } else if (action === 'today-week') {
                _loadWeek(_mondayOf(new Date()));
            } else if (action === 'add-entry') {
                _openModal(null, btn.dataset.day || null);
            } else if (action === 'edit-entry') {
                var entry = _entries.find(function (en) { return en.id === btn.dataset.id; });
                if (entry) _openModal(entry, null);
            } else if (action === 'del-entry') {
                _deleteEntry(btn.dataset.id);
            } else if (action === 'move-up') {
                _moveRow(btn.dataset.id, -1);
            } else if (action === 'move-down') {
                _moveRow(btn.dataset.id, 1);
            } else if (action === 'save-entry') {
                _saveEntry();
            } else if (action === 'close-modal') {
                _closeModal();
            }
        });

        // Close modal on overlay click
        var overlay = container.querySelector('#sch-modal');
        if (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) _closeModal();
            });
        }
    }

    // ── Modal open/close ──────────────────────────────────────────────────────
    function _openModal(entry, defaultDay) {
        _editingId = entry ? entry.id : null;

        var modal = document.getElementById('sch-modal');
        if (!modal) return;

        document.getElementById('sch-modal-title').textContent = entry ? 'Edit Load' : 'Add Load';

        var defDay = defaultDay || (entry && entry.dayDate) || _weekStart;
        document.getElementById('sf-day').value       = defDay;
        document.getElementById('sf-alexei').value    = entry ? (entry.alexeiId || '') : '';
        document.getElementById('sf-tms').value       = entry ? (entry.tmsId || '') : '';
        document.getElementById('sf-pu-num').value    = entry ? (entry.puNumber || '') : '';
        document.getElementById('sf-pu-appt').value   = entry ? (entry.puAppt || '') : '';
        document.getElementById('sf-de-appt').value   = entry ? (entry.deAppt || '') : '';
        document.getElementById('sf-pu-city').value   = entry ? (entry.puCity || '') : '';
        document.getElementById('sf-pu-state').value  = entry ? (entry.puState || '') : '';
        document.getElementById('sf-de-city').value   = entry ? (entry.deCity || '') : '';
        document.getElementById('sf-de-state').value  = entry ? (entry.deState || '') : '';
        document.getElementById('sf-notes').value     = entry ? (entry.notes || '') : '';

        // Restore select default without wiping it
        var statusEl = document.getElementById('sf-status');
        var targetStatus = entry ? (entry.status || 'pending') : 'pending';
        Array.from(statusEl.options).forEach(function (opt) {
            opt.selected = (opt.value === targetStatus);
        });

        modal.style.display = 'flex';
        document.getElementById('sf-alexei').focus();
    }

    function _closeModal() {
        var modal = document.getElementById('sch-modal');
        if (modal) modal.style.display = 'none';
        _editingId = null;
    }

    // ── Save / Delete / Reorder ───────────────────────────────────────────────
    function _saveEntry() {
        var dayDate = document.getElementById('sf-day').value.trim();
        if (!dayDate) { alert('Please select a day.'); return; }

        // Ensure day is within the displayed week
        var weekDays = _weekDays(_weekStart);
        if (weekDays.indexOf(dayDate) < 0) {
            alert('The selected day is outside the current week (' + _weekStart + ' to ' + _addDays(_weekStart, 4) + '). Please choose a day within the visible week.');
            return;
        }

        var body = {
            dayDate:   dayDate,
            weekStart: _weekStart,
            alexeiId:  document.getElementById('sf-alexei').value.trim(),
            tmsId:     document.getElementById('sf-tms').value.trim(),
            puNumber:  document.getElementById('sf-pu-num').value.trim(),
            puAppt:    document.getElementById('sf-pu-appt').value.trim(),
            deAppt:    document.getElementById('sf-de-appt').value.trim(),
            puCity:    document.getElementById('sf-pu-city').value.trim(),
            puState:   document.getElementById('sf-pu-state').value.trim().toUpperCase(),
            deCity:    document.getElementById('sf-de-city').value.trim(),
            deState:   document.getElementById('sf-de-state').value.trim().toUpperCase(),
            status:    document.getElementById('sf-status').value,
            notes:     document.getElementById('sf-notes').value.trim(),
        };

        var saveBtn = document.querySelector('[data-action="save-entry"]');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }

        var req;
        if (_editingId) {
            req = _api('PUT', '/api/ivan/schedule/entries/' + _editingId, body);
        } else {
            req = _api('POST', '/api/ivan/schedule/entries', body);
        }

        req.then(function () {
            _closeModal();
            _loadWeek(_weekStart);
        }).catch(function (err) {
            alert('Save failed: ' + err.message);
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Save Load'; }
        });
    }

    function _deleteEntry(id) {
        if (!confirm('Delete this load? This cannot be undone.')) return;
        _api('DELETE', '/api/ivan/schedule/entries/' + id).then(function () {
            _loadWeek(_weekStart);
        }).catch(function (err) {
            alert('Delete failed: ' + err.message);
        });
    }

    function _moveRow(id, direction) {
        // Find the entry and its day peers
        var entry = _entries.find(function (e) { return e.id === id; });
        if (!entry) return;

        var peers = _entries.filter(function (e) { return e.dayDate === entry.dayDate; });
        peers.sort(function (a, b) { return a.rowOrder - b.rowOrder; });

        var idx = peers.findIndex(function (e) { return e.id === id; });
        var swapIdx = idx + direction;
        if (swapIdx < 0 || swapIdx >= peers.length) return;

        // Swap row orders
        var tmp = peers[idx].rowOrder;
        peers[idx].rowOrder = peers[swapIdx].rowOrder;
        peers[swapIdx].rowOrder = tmp;

        // If same rowOrder, give unique values
        if (peers[idx].rowOrder === peers[swapIdx].rowOrder) {
            peers[swapIdx].rowOrder = peers[idx].rowOrder + (direction > 0 ? 1 : -1);
        }

        // Reassign 0-based
        peers.sort(function (a, b) { return a.rowOrder - b.rowOrder; });
        peers.forEach(function (e, i) { e.rowOrder = i; });

        var payload = peers.map(function (e) {
            return { id: e.id, dayDate: e.dayDate, rowOrder: e.rowOrder };
        });

        _api('POST', '/api/ivan/schedule/entries/reorder', { entries: payload }).then(function () {
            _loadWeek(_weekStart);
        }).catch(function (err) {
            alert('Reorder failed: ' + err.message);
            _render(); // revert visual
        });
    }

    // ── Public API ────────────────────────────────────────────────────────────
    function mountSchedule(containerId) {
        _containerId = containerId;
        var today    = new Date();
        var mon      = _mondayOf(today);
        _loadWeek(mon);
    }

    return { mountSchedule: mountSchedule };
}());
