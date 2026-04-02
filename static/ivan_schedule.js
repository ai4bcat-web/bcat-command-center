/**
 * ivan_schedule.js — Multi-driver Dispatch Board for Ivan Cartage
 * IvanScheduleApp.mountSchedule(containerId)
 *
 * Concept: one IvanLoad may span multiple driver assignments across days.
 * Board groups by day → driver → sequence number.
 * Inline checkboxes update immediately via optimistic UI.
 * Rows turn green when all 6 workflow steps are complete.
 *
 * API:
 *   GET  /api/ivan/schedule?weekStart=         → {assignments, loads}
 *   POST /api/ivan/loads                        → create load
 *   PUT  /api/ivan/loads/:id                   → update load
 *   POST /api/ivan/schedule/assignments         → create assignment
 *   PUT  /api/ivan/schedule/assignments/:id    → update / toggle checkboxes
 *   DELETE /api/ivan/schedule/assignments/:id  → delete
 */
var IvanScheduleApp = (function () {
    'use strict';

    // ── Base terminal ────────────────────────────────────────────────────────
    // Pleasant Prairie, WI — all driver days start and end here
    var BASE = [43.1006, -87.8751];

    // ── City coordinates (lat, lon) ──────────────────────────────────────────
    // Integration point: replace _latLon() with a geocoding API for full coverage
    var COORDS = {
        'chicago il':          [41.8781, -87.6298],
        'chicago heights il':  [41.5061, -87.6373],
        'kenosha wi':          [42.5847, -87.8212],
        'milwaukee wi':        [43.0389, -87.9065],
        'pleasant prairie wi': [43.1006, -87.8751],
        'pleasant prairie':    [43.1006, -87.8751],
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
        'schaumburg il':       [42.0334, -88.0834],
        'oak brook il':        [41.8317, -87.9484],
        'carol stream il':     [41.9131, -88.1348],
        'bolingbrook il':      [41.6986, -88.0684],
    };

    // ── Action display config ────────────────────────────────────────────────
    var ACTION_LABEL = {
        PICKUP:             'PICKUP',
        DELIVERY:           'DELIVERY',
        PICKUP_AND_DELIVER: 'P&D',
        REPOSITION:         'REPOSITION',
        OTHER:              'OTHER',
    };
    var ACTION_CSS = {
        PICKUP:             'sch-badge-pickup',
        DELIVERY:           'sch-badge-delivery',
        PICKUP_AND_DELIVER: 'sch-badge-pad',
        REPOSITION:         'sch-badge-reposition',
        OTHER:              'sch-badge-other',
    };

    // ── State ────────────────────────────────────────────────────────────────
    var _cid         = null;   // container element ID
    var _weekStart   = null;   // ISO Monday string
    var _assignments = [];     // flat array from API
    var _loads       = [];     // all loads (for dropdown)
    var _editAsgn    = null;   // assignment being edited (null = new)
    var _editLoadId  = null;   // load being referenced in open modal

    // ── CSRF / fetch helper ──────────────────────────────────────────────────
    function _csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute('content') : '';
    }
    function _api(method, path, body) {
        var opts = { method: method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': _csrf() } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        return fetch(path, opts).then(function (r) {
            if (!r.ok) return r.json().then(function (e) { throw new Error(e.error || r.statusText); });
            return r.json();
        });
    }

    // ── Week helpers ─────────────────────────────────────────────────────────
    function _isoDate(d) {
        return d.getFullYear() + '-' +
               String(d.getMonth() + 1).padStart(2, '0') + '-' +
               String(d.getDate()).padStart(2, '0');
    }
    function _mondayOf(d) {
        var dt = new Date(d);
        var wd = dt.getDay();
        dt.setDate(dt.getDate() + (wd === 0 ? -6 : 1 - wd));
        return _isoDate(dt);
    }
    function _addDays(iso, n) {
        var d = new Date(iso + 'T00:00:00');
        d.setDate(d.getDate() + n);
        return _isoDate(d);
    }
    function _weekDays() {
        return [0, 1, 2, 3, 4].map(function (i) { return _addDays(_weekStart, i); });
    }
    function _fmtWeekLabel() {
        var d = new Date(_weekStart + 'T00:00:00');
        var e = new Date(_weekStart + 'T00:00:00'); e.setDate(e.getDate() + 6);
        var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return 'Week of ' + M[d.getMonth()] + ' ' + d.getDate() +
               ' \u2013 ' + M[e.getMonth()] + ' ' + e.getDate() + ', ' + e.getFullYear();
    }
    function _fmtDay(iso) {
        var d = new Date(iso + 'T00:00:00');
        var D = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
        var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return D[d.getDay()] + ', ' + M[d.getMonth()] + ' ' + d.getDate();
    }

    // ── Deadhead calculator ──────────────────────────────────────────────────
    function _latLon(city, state) {
        if (!city) return null;
        var k = ((city || '') + ' ' + (state || '')).toLowerCase().trim().replace(/\s+/g, ' ');
        return COORDS[k] || COORDS[city.toLowerCase().trim()] || null;
    }
    function _haversineKm(a, b) {
        var R = 6371, dLat = (b[0]-a[0])*Math.PI/180, dLon = (b[1]-a[1])*Math.PI/180;
        var s = Math.sin(dLat/2), t = Math.sin(dLon/2);
        return 2*R*Math.asin(Math.sqrt(s*s + Math.cos(a[0]*Math.PI/180)*Math.cos(b[0]*Math.PI/180)*t*t));
    }
    function _road(km) { return Math.round(km * 0.621371 * 1.25); }

    // Compute per-assignment deadhead for a driver's sorted day sequence.
    // Returns [{toDH, retDH}] — retDH is non-zero only for the last assignment.
    function _driverDH(sorted) {
        return sorted.map(function (a, i) {
            var orig = _latLon(a.originCity, a.originState);
            var dest = _latLon(a.destCity,   a.destState);
            var toDH = 0, retDH = 0;
            if (i === 0) {
                if (orig) toDH = _road(_haversineKm(BASE, orig));
            } else {
                var prev = sorted[i - 1];
                var pd = _latLon(prev.destCity, prev.destState);
                if (pd && orig) toDH = _road(_haversineKm(pd, orig));
            }
            if (i === sorted.length - 1 && dest) retDH = _road(_haversineKm(dest, BASE));
            return { toDH: toDH, retDH: retDH };
        });
    }

    // ── Completion ───────────────────────────────────────────────────────────
    function _complete(a) {
        return !!(a.dispatched && a.pickedUp && a.delivered &&
                  a.paperworkReceived && a.paperworkReviewed && a.invoicingReady);
    }

    // ── HTML escape ──────────────────────────────────────────────────────────
    function _e(s) {
        return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                               .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ── Load data ────────────────────────────────────────────────────────────
    function _load(weekMon) {
        var el = document.getElementById(_cid);
        if (el) el.innerHTML = '<div class="sch-loading">Loading schedule\u2026</div>';
        _api('GET', '/api/ivan/schedule?weekStart=' + weekMon).then(function (data) {
            _assignments = Array.isArray(data) ? data : (data.assignments || []);
            _loads       = Array.isArray(data) ? [] : (data.loads || []);
            _weekStart   = weekMon;
            _render();
        }).catch(function (err) {
            var el = document.getElementById(_cid);
            if (el) el.innerHTML = '<div class="sch-error">Failed to load: ' + err.message + '</div>';
        });
    }

    // ── Render ───────────────────────────────────────────────────────────────
    function _render() {
        var el = document.getElementById(_cid);
        if (!el) return;
        var html = '<div class="sch-board">' + _navHTML();
        _weekDays().forEach(function (day) {
            html += _dayHTML(day, _assignments.filter(function (a) { return a.date === day; }));
        });
        html += '</div>' + _modalHTML();
        el.innerHTML = html;
        _bind(el);
    }

    function _navHTML() {
        return '<div class="sch-nav">' +
            '<button class="sch-nav-btn" data-action="prev-week">\u25c4 Prev</button>' +
            '<span class="sch-week-label">' + _fmtWeekLabel() + '</span>' +
            '<button class="sch-nav-btn" data-action="next-week">Next \u25ba</button>' +
            '<button class="sch-nav-btn sch-today-btn" data-action="today-week">Today</button>' +
            '<button class="sch-add-btn" data-action="add-asgn">+ Add Assignment</button>' +
            '</div>';
    }

    function _dayHTML(day, dayAsgns) {
        var drivers = [];
        dayAsgns.forEach(function (a) {
            var d = (a.driverName || 'Unassigned').trim();
            if (drivers.indexOf(d) < 0) drivers.push(d);
        });
        drivers.sort();

        var html = '<div class="sch-day-section">' +
            '<div class="sch-day-hdr">' +
                '<span class="sch-day-name">' + _fmtDay(day) + '</span>' +
                '<span class="sch-day-count">' + dayAsgns.length + ' assignment' + (dayAsgns.length !== 1 ? 's' : '') + '</span>' +
                '<button class="sch-day-add" data-action="add-asgn" data-day="' + day + '">+ Add</button>' +
            '</div>';

        if (drivers.length === 0) {
            html += '<div class="sch-empty-day">No assignments scheduled</div>';
        } else {
            drivers.forEach(function (driver) {
                var da = dayAsgns.filter(function (a) {
                    return (a.driverName || 'Unassigned').trim() === driver;
                }).sort(function (a, b) { return a.sequenceNumber - b.sequenceNumber; });
                html += _driverGroupHTML(driver, day, da);
            });
        }
        return html + '</div>';
    }

    var COL_HDR =
        '<div class="sch-col-hdr">' +
        '<div class="sch-c sch-c-seq">#</div>' +
        '<div class="sch-c sch-c-ref">Load Ref</div>' +
        '<div class="sch-c sch-c-act">Action</div>' +
        '<div class="sch-c sch-c-city">From</div>' +
        '<div class="sch-c sch-c-city">To</div>' +
        '<div class="sch-c sch-c-time">PU</div>' +
        '<div class="sch-c sch-c-time">DE</div>' +
        '<div class="sch-c sch-c-dh">DH</div>' +
        '<div class="sch-c sch-c-chks"><span title="Dispatched">D</span>' +
            '<span title="Picked Up">P</span><span title="Delivered">V</span>' +
            '<span title="Paperwork Rcvd">R</span><span title="Paperwork Rev\'d">W</span>' +
            '<span title="Invoicing Ready">I</span></div>' +
        '<div class="sch-c sch-c-done"></div>' +
        '<div class="sch-c sch-c-btn"></div>' +
        '</div>';

    function _driverGroupHTML(driver, day, sorted) {
        var dh     = _driverDH(sorted);
        var totalDH = dh.reduce(function (s, v) { return s + v.toDH; }, 0);
        var retDH   = dh.length ? dh[dh.length - 1].retDH : 0;

        var html = '<div class="sch-driver-group">' +
            '<div class="sch-driver-hdr">' +
                '<span class="sch-driver-name">' + _e(driver.toUpperCase()) + '</span>' +
                (totalDH > 0 ? '<span class="sch-driver-dh">DH in: ' + totalDH + ' mi</span>' : '') +
                '<button class="sch-driver-add" data-action="add-asgn" data-day="' + day + '" data-driver="' + _e(driver) + '">+ Add</button>' +
            '</div>' + COL_HDR;

        sorted.forEach(function (a, i) {
            html += _rowHTML(a, dh[i].toDH);
        });

        if (retDH > 0) {
            html += '<div class="sch-return-bar">\u21a9 Return to base (Pleasant Prairie, WI): ' + retDH + ' mi</div>';
        }
        return html + '</div>';
    }

    function _rowHTML(a, dhMi) {
        var done  = _complete(a);
        var load  = a.load || {};
        var ref   = _e(load.alexeiId || (a.loadId ? a.loadId.substring(0, 12) : '\u2014'));
        var label = ACTION_LABEL[a.actionType] || a.actionType || '?';
        var css   = ACTION_CSS[a.actionType]   || 'sch-badge-other';

        function chk(field, val) {
            return '<input type="checkbox" class="sch-chk"' + (val ? ' checked' : '') +
                   ' data-action="toggle-chk" data-id="' + a.id + '" data-field="' + field + '">';
        }

        var row = '<div class="sch-row' + (done ? ' sch-row-done' : '') + '" data-id="' + a.id + '">' +
            '<div class="sch-c sch-c-seq">' + a.sequenceNumber + '</div>' +
            '<div class="sch-c sch-c-ref" title="' + _e(load.tmsId || '') + '">' + ref + '</div>' +
            '<div class="sch-c sch-c-act"><span class="sch-badge ' + css + '">' + _e(label) + '</span></div>' +
            '<div class="sch-c sch-c-city">' + _e(a.originCity || '') + (a.originState ? ', ' + _e(a.originState) : '') + '</div>' +
            '<div class="sch-c sch-c-city">' + _e(a.destCity   || '') + (a.destState   ? ', ' + _e(a.destState)   : '') + '</div>' +
            '<div class="sch-c sch-c-time">' + _e(a.puAppt || '') + '</div>' +
            '<div class="sch-c sch-c-time">' + _e(a.deAppt || '') + '</div>' +
            '<div class="sch-c sch-c-dh' + (dhMi > 0 ? ' sch-dh-hi' : '') + '">' + (dhMi > 0 ? dhMi + ' mi' : '\u2014') + '</div>' +
            '<div class="sch-c sch-c-chks">' +
                chk('dispatched',         a.dispatched) +
                chk('pickedUp',           a.pickedUp) +
                chk('delivered',          a.delivered) +
                chk('paperworkReceived',  a.paperworkReceived) +
                chk('paperworkReviewed',  a.paperworkReviewed) +
                chk('invoicingReady',     a.invoicingReady) +
            '</div>' +
            '<div class="sch-c sch-c-done">' + (done ? '<span class="sch-done-icon" title="Fully complete">\u2713</span>' : '') + '</div>' +
            '<div class="sch-c sch-c-btn">' +
                '<button class="sch-edit-btn" data-action="edit-asgn" data-id="' + a.id + '">Edit</button>' +
                '<button class="sch-del-btn"  data-action="del-asgn"  data-id="' + a.id + '">\u{1F5D1}</button>' +
            '</div>' +
            '</div>';

        if (a.notes) {
            row += '<div class="sch-row-notes" title="' + _e(a.notes) + '">' +
                '\u{1F4CB} ' + _e(a.notes.length > 80 ? a.notes.substring(0, 80) + '\u2026' : a.notes) +
                '</div>';
        }
        return row;
    }

    // ── Modal ────────────────────────────────────────────────────────────────
    function _modalHTML() {
        var loadOpts = '<option value="">— New Load —</option>';
        _loads.forEach(function (l) {
            var label = [l.alexeiId, l.tmsId,
                (l.puCity && l.deCity ? l.puCity + ' \u2192 ' + l.deCity : '')
            ].filter(Boolean).join(' | ');
            loadOpts += '<option value="' + _e(l.id) + '">' + _e(label || l.id) + '</option>';
        });

        return '<div id="sch-modal" class="sch-modal-overlay" style="display:none">' +
            '<div class="sch-modal">' +
                '<div class="sch-modal-hdr">' +
                    '<span id="sch-modal-title">Add Assignment</span>' +
                    '<button class="sch-modal-x" data-action="close-modal">\u2715</button>' +
                '</div>' +
                '<div class="sch-modal-body">' +
                    '<div class="sch-section-label">SHIPMENT</div>' +
                    '<div class="sch-form-grid">' +
                        '<label class="sch-full">Link to existing load<br>' +
                            '<select id="sf-load" class="sch-inp">' + loadOpts + '</select>' +
                        '</label>' +
                        '<label>PRO #<br><input id="sf-pro" class="sch-inp" placeholder="PRO-10421"></label>' +
                        '<label>TMS ID<br><input id="sf-tms" class="sch-inp" placeholder="TMS-8801"></label>' +
                        '<label>PU #<br><input id="sf-punum" class="sch-inp" placeholder="PU-4421"></label>' +
                        '<label>PU City<br><input id="sf-pucity" class="sch-inp" placeholder="Chicago"></label>' +
                        '<label>PU State<br><input id="sf-pust" class="sch-inp" maxlength="2" placeholder="IL"></label>' +
                        '<label>DE City<br><input id="sf-decity" class="sch-inp" placeholder="Milwaukee"></label>' +
                        '<label>DE State<br><input id="sf-dest" class="sch-inp" maxlength="2" placeholder="WI"></label>' +
                    '</div>' +
                    '<div class="sch-section-label" style="margin-top:14px">ASSIGNMENT</div>' +
                    '<div class="sch-form-grid">' +
                        '<label>Date<br><input type="date" id="sf-date" class="sch-inp"></label>' +
                        '<label>Driver<br><input id="sf-driver" class="sch-inp" placeholder="Alexei"></label>' +
                        '<label>Seq #<br><input type="number" id="sf-seq" class="sch-inp" min="1" max="10" value="1"></label>' +
                        '<label>Action Type<br>' +
                            '<select id="sf-action" class="sch-inp">' +
                                '<option value="PICKUP">PICKUP</option>' +
                                '<option value="DELIVERY">DELIVERY</option>' +
                                '<option value="PICKUP_AND_DELIVER">PICKUP &amp; DELIVER</option>' +
                                '<option value="REPOSITION">REPOSITION</option>' +
                                '<option value="OTHER">OTHER</option>' +
                            '</select>' +
                        '</label>' +
                        '<label>Origin City<br><input id="sf-origcity" class="sch-inp" placeholder="Chicago"></label>' +
                        '<label>Origin State<br><input id="sf-origst" class="sch-inp" maxlength="2" placeholder="IL"></label>' +
                        '<label>Dest City<br><input id="sf-dstcity" class="sch-inp" placeholder="Milwaukee"></label>' +
                        '<label>Dest State<br><input id="sf-dstst" class="sch-inp" maxlength="2" placeholder="WI"></label>' +
                        '<label>PU Appt<br><input type="time" id="sf-puappt" class="sch-inp"></label>' +
                        '<label>DE Appt<br><input type="time" id="sf-deappt" class="sch-inp"></label>' +
                        '<label class="sch-full">Notes<br><textarea id="sf-notes" class="sch-inp sch-textarea" rows="2"></textarea></label>' +
                    '</div>' +
                '</div>' +
                '<div class="sch-modal-ftr">' +
                    '<button class="sch-btn-cancel" data-action="close-modal">Cancel</button>' +
                    '<button class="sch-btn-save" data-action="save-asgn">Save</button>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    // ── Event binding ─────────────────────────────────────────────────────────
    function _bind(el) {
        el.addEventListener('click', function (e) {
            var b = e.target.closest('[data-action]');
            if (!b) return;
            switch (b.dataset.action) {
                case 'prev-week':    _load(_addDays(_weekStart, -7)); break;
                case 'next-week':    _load(_addDays(_weekStart, 7));  break;
                case 'today-week':   _load(_mondayOf(new Date()));    break;
                case 'add-asgn':     _openModal(null, b.dataset.day, b.dataset.driver); break;
                case 'edit-asgn': {
                    var a = _assignments.find(function (x) { return x.id === b.dataset.id; });
                    if (a) _openModal(a, null, null);
                    break;
                }
                case 'del-asgn':     _deleteAsgn(b.dataset.id); break;
                case 'close-modal':  _closeModal(); break;
                case 'save-asgn':    _saveAsgn(); break;
            }
        });

        el.addEventListener('change', function (e) {
            var t = e.target;
            if (t.dataset.action === 'toggle-chk') {
                _toggleChk(t.dataset.id, t.dataset.field, t.checked);
            }
            if (t.id === 'sf-load') {
                _onLoadSelect(t.value);
            }
        });

        var overlay = document.getElementById('sch-modal');
        if (overlay) overlay.addEventListener('click', function (e) {
            if (e.target === overlay) _closeModal();
        });
    }

    // ── Load selector auto-fill ───────────────────────────────────────────────
    function _onLoadSelect(id) {
        var set = function (eid, v) { var el = document.getElementById(eid); if (el) el.value = v || ''; };
        if (!id) {
            ['sf-pro','sf-tms','sf-punum','sf-pucity','sf-pust','sf-decity','sf-dest'].forEach(function (eid) { set(eid, ''); });
            return;
        }
        var l = _loads.find(function (x) { return x.id === id; });
        if (!l) return;
        set('sf-pro',    l.alexeiId);
        set('sf-tms',    l.tmsId);
        set('sf-punum',  l.puNumber);
        set('sf-pucity', l.puCity);
        set('sf-pust',   l.puState);
        set('sf-decity', l.deCity);
        set('sf-dest',   l.deState);

        // Auto-fill origin/dest from action type
        var action  = (document.getElementById('sf-action') || {}).value || 'PICKUP';
        var setIf   = function (eid, v) { var el = document.getElementById(eid); if (el && !el.value) el.value = v || ''; };
        if (action === 'PICKUP' || action === 'PICKUP_AND_DELIVER') {
            setIf('sf-origcity', l.puCity);  setIf('sf-origst', l.puState);
        }
        if (action === 'DELIVERY' || action === 'PICKUP_AND_DELIVER') {
            setIf('sf-dstcity', l.deCity);   setIf('sf-dstst', l.deState);
        }
    }

    // ── Modal open / close ────────────────────────────────────────────────────
    function _openModal(asgn, defaultDay, defaultDriver) {
        _editAsgn   = asgn;
        _editLoadId = asgn ? (asgn.loadId || null) : null;

        var modal = document.getElementById('sch-modal');
        if (!modal) return;
        document.getElementById('sch-modal-title').textContent = asgn ? 'Edit Assignment' : 'Add Assignment';

        var load = asgn && asgn.load ? asgn.load : null;
        var set  = function (id, v) { var el = document.getElementById(id); if (el) el.value = v || ''; };

        // Load selector
        var loadSel = document.getElementById('sf-load');
        if (loadSel) loadSel.value = _editLoadId || '';

        // Load fields
        set('sf-pro',    load ? load.alexeiId : '');
        set('sf-tms',    load ? load.tmsId    : '');
        set('sf-punum',  load ? load.puNumber : '');
        set('sf-pucity', load ? load.puCity   : '');
        set('sf-pust',   load ? load.puState  : '');
        set('sf-decity', load ? load.deCity   : '');
        set('sf-dest',   load ? load.deState  : '');

        // Assignment fields
        set('sf-date',     asgn ? asgn.date        : (defaultDay    || _weekStart));
        set('sf-driver',   asgn ? asgn.driverName  : (defaultDriver || ''));
        set('sf-origcity', asgn ? asgn.originCity  : '');
        set('sf-origst',   asgn ? asgn.originState : '');
        set('sf-dstcity',  asgn ? asgn.destCity    : '');
        set('sf-dstst',    asgn ? asgn.destState   : '');
        set('sf-puappt',   asgn ? asgn.puAppt      : '');
        set('sf-deappt',   asgn ? asgn.deAppt      : '');
        set('sf-notes',    asgn ? asgn.notes       : '');

        // Sequence number: auto-next for driver+day
        var seqEl = document.getElementById('sf-seq');
        if (seqEl) {
            if (asgn) {
                seqEl.value = asgn.sequenceNumber;
            } else {
                var date   = defaultDay || _weekStart;
                var driver = (defaultDriver || '').trim();
                var count  = _assignments.filter(function (a) {
                    return a.date === date && (a.driverName || '').trim() === driver;
                }).length;
                seqEl.value = count + 1;
            }
        }

        // Action type
        var actionEl = document.getElementById('sf-action');
        var target   = asgn ? (asgn.actionType || 'PICKUP') : 'PICKUP';
        if (actionEl) Array.from(actionEl.options).forEach(function (o) { o.selected = o.value === target; });

        modal.style.display = 'flex';
        setTimeout(function () { var df = document.getElementById('sf-driver'); if (df) df.focus(); }, 60);
    }

    function _closeModal() {
        var m = document.getElementById('sch-modal');
        if (m) m.style.display = 'none';
        _editAsgn = null; _editLoadId = null;
    }

    // ── Save ──────────────────────────────────────────────────────────────────
    function _saveAsgn() {
        var date = (document.getElementById('sf-date') || {}).value || '';
        if (!date) { alert('Please select a date.'); return; }

        var weekDays = _weekDays();
        if (weekDays.indexOf(date) < 0) {
            alert('Date must be within the current week (' + _weekStart + ' \u2013 ' + _addDays(_weekStart, 4) + ').');
            return;
        }

        var saveBtn = document.querySelector('[data-action="save-asgn"]');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving\u2026'; }

        var g = function (id) { return (document.getElementById(id) || {}).value || ''; };
        var loadSel = document.getElementById('sf-load');
        var selectedLoadId = loadSel ? loadSel.value : '';

        var loadBody = {
            alexeiId: g('sf-pro'),
            tmsId:    g('sf-tms'),
            puNumber: g('sf-punum'),
            puCity:   g('sf-pucity'),
            puState:  g('sf-pust').toUpperCase(),
            deCity:   g('sf-decity'),
            deState:  g('sf-dest').toUpperCase(),
        };
        var asgnBody = {
            date:           date,
            weekStart:      _weekStart,
            driverName:     g('sf-driver').trim(),
            sequenceNumber: parseInt(g('sf-seq') || '1', 10),
            actionType:     g('sf-action') || 'PICKUP',
            originCity:     g('sf-origcity'),
            originState:    g('sf-origst').toUpperCase(),
            destCity:       g('sf-dstcity'),
            destState:      g('sf-dstst').toUpperCase(),
            puAppt:         g('sf-puappt'),
            deAppt:         g('sf-deappt'),
            notes:          g('sf-notes'),
        };

        var loadP;
        if (selectedLoadId) {
            loadP = _api('PUT', '/api/ivan/loads/' + selectedLoadId, loadBody)
                        .then(function () { return selectedLoadId; });
        } else if (_editAsgn && _editAsgn.loadId) {
            loadP = _api('PUT', '/api/ivan/loads/' + _editAsgn.loadId, loadBody)
                        .then(function () { return _editAsgn.loadId; });
        } else {
            loadP = _api('POST', '/api/ivan/loads', loadBody)
                        .then(function (r) { return r.id; });
        }

        loadP.then(function (loadId) {
            asgnBody.loadId = loadId;
            return _editAsgn
                ? _api('PUT',  '/api/ivan/schedule/assignments/' + _editAsgn.id, asgnBody)
                : _api('POST', '/api/ivan/schedule/assignments', asgnBody);
        }).then(function () {
            _closeModal();
            _load(_weekStart);
        }).catch(function (err) {
            alert('Save failed: ' + err.message);
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Save'; }
        });
    }

    // ── Delete ────────────────────────────────────────────────────────────────
    function _deleteAsgn(id) {
        if (!confirm('Delete this assignment? This cannot be undone.')) return;
        _api('DELETE', '/api/ivan/schedule/assignments/' + id).then(function () {
            _load(_weekStart);
        }).catch(function (err) { alert('Delete failed: ' + err.message); });
    }

    // ── Checkbox toggle (optimistic) ──────────────────────────────────────────
    function _toggleChk(id, field, checked) {
        var a = _assignments.find(function (x) { return x.id === id; });
        if (!a) return;

        var prev = a[field];
        a[field] = checked;
        a.isFullyComplete = _complete(a);

        var row = document.querySelector('.sch-row[data-id="' + id + '"]');
        if (row) {
            row.classList.toggle('sch-row-done', a.isFullyComplete);
            var dc = row.querySelector('.sch-c-done');
            if (dc) dc.innerHTML = a.isFullyComplete
                ? '<span class="sch-done-icon" title="Fully complete">\u2713</span>' : '';
        }

        var patch = {};
        patch[field] = checked;
        _api('PUT', '/api/ivan/schedule/assignments/' + id, patch).catch(function (err) {
            a[field] = prev;
            a.isFullyComplete = _complete(a);
            alert('Save failed: ' + err.message);
            _render();
        });
    }

    // ── Public ────────────────────────────────────────────────────────────────
    function mountSchedule(containerId) {
        _cid = containerId;
        _load(_mondayOf(new Date()));
    }

    return { mountSchedule: mountSchedule };
}());
