/**
 * ivan_schedule.js — Multi-week Calendar Dispatch Board for Ivan Cartage
 * IvanScheduleApp.mountSchedule(containerId)
 *
 * Renders NUM_WEEKS consecutive weeks in a scrollable vertical stack.
 * Each week: 5-column calendar (Mon–Fri) with inline-editable driver cards.
 *
 * Features:
 *  - Multi-week stacked view (default 4 weeks)
 *  - Driver dropdown from Ivan Drivers localStorage + Unassigned option
 *  - ZIP → City/State auto-fill via zippopotam.us
 *  - Per-leg PU/DE appointment status (NEED | REQUESTED | APPOINTED)
 *  - Pickup/delivery location names
 *  - Driver starting location per day (overrides base for deadhead calc)
 *  - Driver color coding, load continuity chips, deadhead, manual DONE toggle
 *  - 24-hour (military) time throughout
 */
var IvanScheduleApp = (function () {
    'use strict';

    var NUM_WEEKS = 4;  // number of weeks to display simultaneously

    var BASE = [43.1006, -87.8751]; // Pleasant Prairie, WI (default start)

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

    var ACTION_LABEL = {
        PICKUP:             'PICKUP',
        DELIVERY:           'DELIVERY',
        PICKUP_AND_DELIVER: 'P&D',
        REPOSITION:         'REPO',
        OTHER:              'OTHER',
    };
    var ACTION_CSS = {
        PICKUP:             'sc-badge-pickup',
        DELIVERY:           'sc-badge-delivery',
        PICKUP_AND_DELIVER: 'sc-badge-pad',
        REPOSITION:         'sc-badge-repo',
        OTHER:              'sc-badge-other',
    };
    var APPT_CSS = {
        NEED:       'sc-apst-need',
        REQUESTED:  'sc-apst-req',
        APPOINTED:  'sc-apst-apt',
    };

    // 8 driver colors
    var DRIVER_COLORS = [
        { b: '#3b82f6', bg: '#0c1e36', t: '#93c5fd' },
        { b: '#f59e0b', bg: '#1f1200', t: '#fcd34d' },
        { b: '#10b981', bg: '#021f17', t: '#6ee7b7' },
        { b: '#f43f5e', bg: '#200811', t: '#fda4af' },
        { b: '#a78bfa', bg: '#150928', t: '#c4b5fd' },
        { b: '#22d3ee', bg: '#081e26', t: '#67e8f9' },
        { b: '#fb923c', bg: '#1e0a02', t: '#fdba74' },
        { b: '#84cc16', bg: '#0d1a02', t: '#bef264' },
    ];
    // Neutral gray for Unassigned
    var UNASSIGNED_COLOR = { b: '#475569', bg: '#0c1118', t: '#94a3b8' };

    // 10 load chip colors
    var LOAD_COLORS = [
        '#38bdf8','#fbbf24','#34d399','#f87171','#c084fc',
        '#22d3ee','#fb923c','#a3e635','#f472b6','#818cf8',
    ];

    // ── State ─────────────────────────────────────────────────────────────────
    var _cid       = null;
    var _viewStart = null;   // Monday of first visible week
    var _weekData  = {};     // weekStart → { assignments: [], loads: [] }
    var _missingDel = {};    // loadId → true for loads with pickup but no delivery

    // ── Fetch / CSRF ──────────────────────────────────────────────────────────
    function _csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute('content') : '';
    }
    function _api(method, path, body) {
        var opts = { method: method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': _csrf() } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        return fetch(path, opts).then(function (r) {
            var ct = r.headers.get('content-type') || '';
            if (!r.ok) {
                if (ct.indexOf('application/json') >= 0) {
                    return r.json().then(function (e) { throw new Error(e.error || r.statusText); });
                }
                throw new Error('HTTP ' + r.status + ' ' + r.statusText +
                    (r.status === 302 || r.status === 401 ? ' (session expired — please refresh)' : ''));
            }
            if (ct.indexOf('application/json') < 0) {
                throw new Error('Server returned non-JSON response (HTTP ' + r.status + '). Check server logs.');
            }
            return r.json();
        });
    }

    // ── Date helpers ──────────────────────────────────────────────────────────
    function _iso(d) {
        return d.getFullYear() + '-' +
               String(d.getMonth() + 1).padStart(2, '0') + '-' +
               String(d.getDate()).padStart(2, '0');
    }
    function _mondayOf(d) {
        var dt = new Date(d), wd = dt.getDay();
        dt.setDate(dt.getDate() + (wd === 0 ? -6 : 1 - wd));
        return _iso(dt);
    }
    function _addDays(iso, n) {
        var d = new Date(iso + 'T00:00:00');
        d.setDate(d.getDate() + n);
        return _iso(d);
    }
    function _weekOf(iso) { return [0,1,2,3,4].map(function(i){ return _addDays(iso,i); }); }
    function _fmtWeek(ws) {
        var d = new Date(ws + 'T00:00:00');
        var e = new Date(ws + 'T00:00:00'); e.setDate(e.getDate() + 6);
        var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return M[d.getMonth()] + ' ' + d.getDate() +
               ' \u2013 ' + M[e.getMonth()] + ' ' + e.getDate() + ', ' + e.getFullYear();
    }
    function _fmtColHdr(iso) {
        var d   = new Date(iso + 'T00:00:00');
        var DAY = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        var MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return { day: DAY[d.getDay()], date: MON[d.getMonth()] + ' ' + d.getDate() };
    }

    // ── Deadhead ──────────────────────────────────────────────────────────────
    function _ll(city, state) {
        if (!city) return null;
        var k = ((city||'')+' '+(state||'')).toLowerCase().trim().replace(/\s+/g,' ');
        return COORDS[k] || COORDS[(city||'').toLowerCase().trim()] || null;
    }
    function _hav(a, b) {
        var R=6371, dL=(b[0]-a[0])*Math.PI/180, dO=(b[1]-a[1])*Math.PI/180;
        var s=Math.sin(dL/2), t=Math.sin(dO/2);
        return 2*R*Math.asin(Math.sqrt(s*s+Math.cos(a[0]*Math.PI/180)*Math.cos(b[0]*Math.PI/180)*t*t));
    }
    function _mi(km) { return Math.round(km*0.621371*1.25); }

    /**
     * Compute deadhead for each assignment in a driver's sorted day.
     * sorted[0].driverStartCity/State overrides BASE as the starting point.
     */
    function _driverDH(sorted) {
        // Determine starting location: use driver start from first assignment if set
        var startLoc = BASE;
        if (sorted.length && sorted[0].driverStartCity) {
            var sl = _ll(sorted[0].driverStartCity, sorted[0].driverStartState);
            if (sl) startLoc = sl;
        }
        return sorted.map(function(a,i) {
            var orig=_ll(a.originCity,a.originState), dest=_ll(a.destCity,a.destState);
            var toDH=0, retDH=0;
            if (i===0) { if(orig) toDH=_mi(_hav(startLoc,orig)); }
            else { var pd=_ll(sorted[i-1].destCity,sorted[i-1].destState); if(pd&&orig) toDH=_mi(_hav(pd,orig)); }
            if (i===sorted.length-1 && dest) retDH=_mi(_hav(dest,BASE));
            return {toDH:toDH,retDH:retDH};
        });
    }

    // ── Misc helpers ──────────────────────────────────────────────────────────
    function _done(a) { return !!a.isComplete; }
    function _e(s) {
        return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function _hash(str) {
        var h=0; for(var i=0;i<str.length;i++) h=(h*31+str.charCodeAt(i))&0xffff; return h;
    }
    function _dc(name) {
        if (!name || !name.trim()) return UNASSIGNED_COLOR;
        return DRIVER_COLORS[_hash(name.toLowerCase()) % DRIVER_COLORS.length];
    }
    function _lc(id)    { return LOAD_COLORS[_hash(id||'') % LOAD_COLORS.length]; }

    // ── Data accessors ────────────────────────────────────────────────────────
    function _allAsgns() {
        var all = [];
        Object.keys(_weekData).forEach(function(w){ all = all.concat(_weekData[w].assignments||[]); });
        return all;
    }
    function _allLoads() {
        var seen = {}, all = [];
        Object.keys(_weekData).forEach(function(w){
            (_weekData[w].loads||[]).forEach(function(l){ if(!seen[l.id]){seen[l.id]=1;all.push(l);} });
        });
        return all;
    }

    // Driver names: merge from assignments + Ivan Drivers localStorage (active)
    function _getDriversFromLS() {
        try {
            var raw = localStorage.getItem('bcat_ivan_drivers');
            if (!raw) return [];
            return JSON.parse(raw)
                .filter(function(d){ return d.status === 'active'; })
                .map(function(d){ return d.name; })
                .sort();
        } catch(e) { return []; }
    }
    function _drivers() {
        var seen = {}, out = [];
        _allAsgns().forEach(function(a){ var d=(a.driverName||'').trim(); if(d&&!seen[d]){seen[d]=1;out.push(d);} });
        _getDriversFromLS().forEach(function(n){ if(!seen[n]){seen[n]=1;out.push(n);} });
        return out.sort();
    }
    function _nextSeq(day, driver) {
        var week = _mondayOf(new Date(day+'T00:00:00'));
        return ((_weekData[week]||{}).assignments||[]).filter(function(a){
            return a.date===day && (a.driverName||'').trim()===(driver||'').trim();
        }).length + 1;
    }

    /**
     * Scan all loaded assignments and find loads that have a PICKUP
     * but no DELIVERY or PICKUP_AND_DELIVER leg yet.
     * Results stored in _missingDel = { loadId: true }.
     */
    function _computeMissingDel() {
        var all = _allAsgns();
        var hasPickup = {}, hasDelivery = {};
        all.forEach(function(a) {
            if (!a.loadId) return;
            if (a.actionType === 'PICKUP') {
                hasPickup[a.loadId] = a; // store assignment for prefill
            }
            if (a.actionType === 'DELIVERY' || a.actionType === 'PICKUP_AND_DELIVER') {
                hasDelivery[a.loadId] = true;
            }
        });
        _missingDel = {};
        Object.keys(hasPickup).forEach(function(lid) {
            if (!hasDelivery[lid]) _missingDel[lid] = true;
        });
    }

    // ── ZIP lookup (zippopotam.us) ────────────────────────────────────────────
    function _lookupZip(zipInput) {
        var zip = (zipInput.value||'').trim();
        if (!/^\d{5}$/.test(zip)) return;
        var form = zipInput.closest('.sc-card-edit, .sc-add-form');
        if (!form) return;
        var isPu  = zipInput.name === 'puzip';
        var cityI = form.querySelector('[name="'+(isPu?'origcity':'dstcity')+'"]');
        var stI   = form.querySelector('[name="'+(isPu?'origst':'dstst')+'"]');
        var warn  = form.querySelector('.sc-zip-warn-'+(isPu?'pu':'de'));
        if (warn) { warn.textContent = ''; warn.style.display = 'none'; }
        fetch('https://api.zippopotam.us/us/'+zip)
            .then(function(r){ return r.ok ? r.json() : null; })
            .then(function(data){
                if (!data||!data.places||!data.places.length) {
                    if (warn) { warn.textContent = 'ZIP not found'; warn.style.display = ''; }
                    return;
                }
                if (cityI) cityI.value = data.places[0]['place name'];
                if (stI)   stI.value   = data.places[0]['state abbreviation'];
            })
            .catch(function(){
                if (warn) { warn.textContent = 'Lookup failed'; warn.style.display = ''; }
            });
    }

    // ── Multi-week data load ──────────────────────────────────────────────────
    function _loadMultiWeek(viewStart) {
        _viewStart = viewStart;
        var el = document.getElementById(_cid);
        if (el) el.innerHTML = '<div class="sc-loading">Loading schedule\u2026</div>';

        var weeks = [];
        for (var i = 0; i < NUM_WEEKS; i++) weeks.push(_addDays(viewStart, i*7));

        _weekData = {};
        var promises = weeks.map(function(week){
            return _api('GET', '/api/ivan/schedule?weekStart='+week).then(function(data){
                _weekData[week] = {
                    assignments: Array.isArray(data) ? data : (data.assignments||[]),
                    loads:       Array.isArray(data) ? [] : (data.loads||[]),
                };
            }).catch(function(){
                _weekData[week] = { assignments: [], loads: [] };
            });
        });

        Promise.all(promises).then(function(){ _render(); });
    }

    function _reload() { _loadMultiWeek(_viewStart); }

    // ── Render ────────────────────────────────────────────────────────────────
    function _render() {
        var el = document.getElementById(_cid); if (!el) return;
        _computeMissingDel();
        var today   = _iso(new Date());
        var drvs    = _drivers();
        var curWeek = _mondayOf(new Date());

        var html = '<div class="sc-board">'+_navHTML(curWeek);
        html += '<datalist id="sc-drvs-dl">';
        drvs.forEach(function(d){ html+='<option value="'+_e(d)+'">'; });
        html += '</datalist>';

        var weeks = [];
        for (var i = 0; i < NUM_WEEKS; i++) weeks.push(_addDays(_viewStart, i*7));

        weeks.forEach(function(week){
            var data    = _weekData[week] || { assignments:[], loads:[] };
            var isCur   = week === curWeek;
            var asgns   = data.assignments;
            var total   = asgns.length;
            html += '<div class="sc-week-section'+(isCur?' sc-week-current':'')+'" data-week="'+week+'">';
            html += '<div class="sc-week-hdr">';
            html += '<span class="sc-week-label">Week of '+_fmtWeek(week)+'</span>';
            html += '<span class="sc-week-count">'+total+' assignment'+(total!==1?'s':'')+'</span>';
            if (isCur) html += '<span class="sc-week-now-pill">CURRENT</span>';
            html += '</div>';
            html += '<div class="sc-calendar">';
            _weekOf(week).forEach(function(day){
                var isToday = day === today;
                var dayA    = asgns.filter(function(a){ return a.date===day; });
                html += _colHTML(day, dayA, isToday);
            });
            html += '</div>'; // sc-calendar
            html += '</div>'; // sc-week-section
        });

        html += '</div>'; // sc-board
        el.innerHTML = html;
        _bind(el);
    }

    function _navHTML(curWeek) {
        var endLabel = _fmtWeek(_addDays(_viewStart, (NUM_WEEKS-1)*7));
        var label    = _fmtWeek(_viewStart) + ' \u2013 ' + endLabel;
        return '<div class="sc-nav">'+
            '<button class="sc-nav-btn" data-action="prev-week">\u25c4 Prev</button>'+
            '<span class="sc-week-label">'+label+'</span>'+
            '<button class="sc-nav-btn" data-action="next-week">Next \u25ba</button>'+
            '<button class="sc-nav-btn sc-today-btn" data-action="today-week">Today</button>'+
            '</div>';
    }

    function _colHTML(day, dayA, isToday) {
        var hdr  = _fmtColHdr(day);
        var drvs = [];
        dayA.forEach(function(a){
            var d=(a.driverName||'').trim()||'Unassigned';
            if(drvs.indexOf(d)<0) drvs.push(d);
        });
        drvs.sort();

        var cls = 'sc-col'+(isToday?' sc-col-today':'');
        var h = '<div class="'+cls+'" data-day="'+day+'">';
        h += '<div class="sc-col-hdr">';
        h += '<span class="sc-col-dayname">'+hdr.day+'</span>';
        h += '<span class="sc-col-date">'+hdr.date+'</span>';
        if (isToday) h += '<span class="sc-today-pill">TODAY</span>';
        h += '</div>';

        if (drvs.length===0) {
            h += '<div class="sc-empty-col">No assignments</div>';
        } else {
            drvs.forEach(function(drv){
                var da = dayA.filter(function(a){
                    return ((a.driverName||'').trim()||'Unassigned')===drv;
                }).sort(function(a,b){ return a.sequenceNumber-b.sequenceNumber; });
                h += _drvSection(drv, day, da);
            });
        }

        h += _addFormHTML(day);
        h += '<button class="sc-add-col-btn" data-action="show-add" data-day="'+day+'">+ Add</button>';
        h += '</div>';
        return h;
    }

    function _drvSection(drv, day, sorted) {
        var isUnassigned = drv === 'Unassigned';
        var dc  = isUnassigned ? UNASSIGNED_COLOR : _dc(drv);
        var dh  = _driverDH(sorted);
        var retDH = dh.length ? dh[dh.length-1].retDH : 0;

        // Show driver start location if set on first assignment
        var startLoc = '';
        if (sorted.length && sorted[0].driverStartCity) {
            startLoc = sorted[0].driverStartCity +
                       (sorted[0].driverStartState ? ', '+sorted[0].driverStartState : '');
        }

        var h = '<div class="sc-drv-sec" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';
        h += '<div class="sc-drv-hdr">';
        h += '<div class="sc-drv-hdr-left">';
        h += '<span class="sc-drv-name">'+_e(drv)+'</span>';
        if (startLoc) h += '<span class="sc-drv-start">\u25ba '+_e(startLoc)+'</span>';
        h += '</div>';
        h += '<button class="sc-drv-add" data-action="show-add" data-day="'+day+'" data-driver="'+_e(isUnassigned?'':drv)+'" title="Add move for this driver">+</button>';
        h += '</div>';
        sorted.forEach(function(a,i){ h += _cardHTML(a, dh[i].toDH, dc); });
        if (retDH>0) h += '<div class="sc-ret-bar">\u21a9 Base: '+retDH+' mi</div>';
        h += '</div>';
        return h;
    }

    function _cardHTML(a, dhMi, dc) {
        var isDone = _done(a), load = a.load||{};
        var pro    = load.alexeiId||'';
        var lc     = a.loadId ? _lc(a.loadId) : null;
        var label  = ACTION_LABEL[a.actionType]||a.actionType||'?';
        var actCss = ACTION_CSS[a.actionType]||'sc-badge-other';
        var puSt   = a.puApptStatus||'NEED';
        var deSt   = a.deApptStatus||'NEED';
        var puCss  = APPT_CSS[puSt]||'sc-apst-need';
        var deCss  = APPT_CSS[deSt]||'sc-apst-need';
        var orig   = [a.originCity,a.originState].filter(Boolean).join(', ');
        var dest   = [a.destCity,a.destState].filter(Boolean).join(', ');
        var puLoc  = a.puLocationName||'';
        var deLoc  = a.deLocationName||'';
        // Missing delivery: PICKUP leg with no delivery leg on same load
        var isMissingDel = a.actionType === 'PICKUP' && a.loadId && _missingDel[a.loadId];

        var cls = 'sc-card'+(isDone?' sc-card-done':'')+(isMissingDel?' sc-card-missing-del':'');
        var h = '<div class="'+cls+'" data-id="'+a.id+'" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';

        // ── View ──
        h += '<div class="sc-card-view">';
        h += '<div class="sc-card-top">';
        h += '<span class="sc-seq">'+a.sequenceNumber+'</span>';
        h += '<span class="sc-badge '+actCss+'">'+_e(label)+'</span>';
        if (pro&&lc) h += '<span class="sc-chip" style="--lc:'+lc+'">'+_e(pro)+'</span>';
        if (dhMi>0)  h += '<span class="sc-dh-tag">'+dhMi+' mi</span>';
        h += '<span class="sc-card-acts">';
        h += '<button class="sc-btn-icon" data-action="toggle-edit" data-id="'+a.id+'" title="Edit">\u270e</button>';
        h += '<button class="sc-btn-icon sc-btn-del" data-action="del-asgn" data-id="'+a.id+'" title="Delete">\u00d7</button>';
        h += '</span>';
        h += '</div>'; // sc-card-top

        // Route + location names
        if (puLoc || orig) {
            h += '<div class="sc-route sc-route-pu">';
            if (puLoc) h += '<span class="sc-loc-name">'+_e(puLoc)+'</span> ';
            if (orig)  h += '<span class="sc-loc-city">'+_e(orig)+'</span>';
            h += '</div>';
        }
        if (deLoc || dest) {
            h += '<div class="sc-route sc-route-de">';
            h += '\u2192 ';
            if (deLoc) h += '<span class="sc-loc-name">'+_e(deLoc)+'</span> ';
            if (dest)  h += '<span class="sc-loc-city">'+_e(dest)+'</span>';
            h += '</div>';
        }

        // Appt times + per-leg status badges
        h += '<div class="sc-appt-row">';
        if (a.puAppt) {
            h += '<span class="sc-appts">PU '+_e(a.puAppt)+'</span>';
            h += '<span class="sc-apst '+puCss+'">'+_e(puSt)+'</span>';
        }
        if (a.deAppt) {
            h += '<span class="sc-appts">DE '+_e(a.deAppt)+'</span>';
            h += '<span class="sc-apst '+deCss+'">'+_e(deSt)+'</span>';
        }
        if (!a.puAppt && !a.deAppt) {
            // Show at least the combined status if no times
            h += '<span class="sc-apst '+puCss+'">PU: '+_e(puSt)+'</span>';
            h += '<span class="sc-apst '+deCss+'">DE: '+_e(deSt)+'</span>';
        }
        h += '</div>';

        // DONE toggle only (no workflow checkboxes)
        h += '<div class="sc-chks">';
        h += '<span class="sc-chks-sep"></span>';
        h += '<label class="sc-chk-lbl sc-done-lbl" title="Mark complete">';
        h += '<input type="checkbox" class="sc-chk sc-done-chk"'+(isDone?' checked':'')+
             ' data-action="toggle-chk" data-id="'+a.id+'" data-field="isComplete">';
        h += '<span>'+(isDone?'\u2713 DONE':'DONE')+'</span></label>';
        h += '</div>';

        if (a.notes) {
            var n=a.notes; h += '<div class="sc-notes">'+_e(n.length>55?n.substring(0,55)+'\u2026':n)+'</div>';
        }
        h += '</div>'; // sc-card-view

        // ── Missing delivery warning + quick action ──
        if (isMissingDel) {
            h += '<div class="sc-missing-del-bar">';
            h += '<span class="sc-missing-del-badge">\u26a0 DELIVERY NOT ADDED</span>';
            h += '<button class="sc-add-del-btn" data-action="show-delivery-form" data-id="'+a.id+'">\u271a Add Delivery</button>';
            h += '</div>';
            h += _deliveryFormHTML(a);
        }

        h += _editFormHTML(a);
        h += '</div>'; // sc-card
        return h;
    }

    // ── Edit form (inside card, hidden by default) ────────────────────────────
    function _editFormHTML(a) {
        var load  = a.load||{};
        var puSt  = a.puApptStatus||'NEED';
        var deSt  = a.deApptStatus||'NEED';
        var h = '<div class="sc-card-edit" style="display:none" data-edit-for="'+a.id+'">';
        h += '<div class="sc-ef-grid">';
        // Row: PRO # | TMS ID
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" value="'+_e(load.alexeiId||'')+'" placeholder="PRO-10421"></label>';
        h += '<label class="sc-ef-lbl">TMS ID<input class="sc-inp" name="tms" value="'+_e(load.tmsId||'')+'" placeholder="TMS-8801"></label>';
        h += '</div>';
        // Row: Pickup Number
        h += '<label class="sc-ef-lbl">Pickup Number<input class="sc-inp" name="punum" value="'+_e(load.puNumber||'')+'" placeholder="PU-4421"></label>';
        // Row: Action | Driver
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">Action'+_actSel('action',a.actionType||'PICKUP')+'</label>';
        h += '<label class="sc-ef-lbl">Driver'+_driverSel('driver',a.driverName||'')+'</label>';
        h += '</div>';
        // Row: Driver start ZIP | City | ST
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">Start ZIP<input class="sc-inp" name="startzip" placeholder="60601" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">Start City<input class="sc-inp" name="startcity" value="'+_e(a.driverStartCity||'')+'" placeholder="Chicago"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="startst" value="'+_e(a.driverStartState||'')+'" maxlength="2" placeholder="IL"></label>';
        h += '</div>';
        // Row: PU Location Name (full width)
        h += '<label class="sc-ef-lbl">PU Location Name<input class="sc-inp" name="puloc" value="'+_e(a.puLocationName||'')+'" placeholder="Walmart DC #6045"></label>';
        // Row: PU ZIP | From City | ST
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">PU ZIP<input class="sc-inp" name="puzip" placeholder="60601" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" value="'+_e(a.originCity||'')+'" placeholder="Chicago"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" value="'+_e(a.originState||'')+'" maxlength="2" placeholder="IL"></label>';
        h += '</div>';
        h += '<span class="sc-zip-warn sc-zip-warn-pu" style="display:none"></span>';
        // Row: DE Location Name (full width)
        h += '<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="deloc" value="'+_e(a.deLocationName||'')+'" placeholder="Target RDC"></label>';
        // Row: DE ZIP | To City | ST
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">DE ZIP<input class="sc-inp" name="dezip" placeholder="53202" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" value="'+_e(a.destCity||'')+'" placeholder="Milwaukee"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" value="'+_e(a.destState||'')+'" maxlength="2" placeholder="WI"></label>';
        h += '</div>';
        h += '<span class="sc-zip-warn sc-zip-warn-de" style="display:none"></span>';
        // Row: PU Appt | PU Status
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">PU Appt (HH:MM)<input class="sc-inp" type="time" name="puappt" value="'+_e(a.puAppt||'')+'"></label>';
        h += '<label class="sc-ef-lbl">PU Appt Status'+_apptSel('puApptStatus',puSt)+'</label>';
        h += '</div>';
        // Row: DE Appt | DE Status
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="deappt" value="'+_e(a.deAppt||'')+'"></label>';
        h += '<label class="sc-ef-lbl">DE Appt Status'+_apptSel('deApptStatus',deSt)+'</label>';
        h += '</div>';
        // Row: Seq | Notes
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">Seq<input class="sc-inp" type="number" name="seq" value="'+_e(a.sequenceNumber||1)+'" min="1" max="20"></label>';
        h += '<label class="sc-ef-lbl">Notes<input class="sc-inp" name="notes" value="'+_e(a.notes||'')+'" placeholder="Notes\u2026"></label>';
        h += '</div>';
        h += '</div>'; // sc-ef-grid
        h += '<div class="sc-ef-btns">';
        h += '<button class="sc-btn-cancel" data-action="cancel-edit" data-id="'+a.id+'">Cancel</button>';
        h += '<button class="sc-btn-save" data-action="save-edit" data-id="'+a.id+'">Save</button>';
        h += '</div>';
        h += '</div>'; // sc-card-edit
        return h;
    }

    // ── Delivery creation form (embedded in pickup card) ─────────────────────
    function _deliveryFormHTML(a) {
        var load = a.load || {};
        // Origin of delivery leg = where pickup ended (pickup's destCity)
        var delOrigCity  = a.destCity   || '';
        var delOrigState = a.destState  || '';
        // Destination of delivery = master load's de_city/de_state
        var delDstCity   = load.deCity  || '';
        var delDstState  = load.deState || '';
        // Origin location name for delivery = where pickup was staged/dropped
        var delOrigLoc   = a.deLocationName || '';

        var routeInfo = '';
        var from = [delOrigCity, delOrigState].filter(Boolean).join(', ');
        var to   = [delDstCity,  delDstState].filter(Boolean).join(', ');
        if (from || to) routeInfo = (from||'?') + ' \u2192 ' + (to||'?');

        var h = '<div class="sc-delivery-form" data-del-for="'+a.id+'" style="display:none">';
        h += '<div class="sc-del-form-hdr">';
        h += '<span class="sc-del-form-title">\u26a1 Add Delivery Leg</span>';
        if (load.alexeiId) h += '<span class="sc-chip" style="--lc:'+_lc(a.loadId||'')+'">'+_e(load.alexeiId)+'</span>';
        h += '</div>';

        if (routeInfo) h += '<div class="sc-del-route-info">'+_e(routeInfo)+'</div>';

        // Hidden carry-over fields
        h += '<input type="hidden" name="del-loadid" value="'+_e(a.loadId||'')+'">';
        h += '<input type="hidden" name="del-origcity" value="'+_e(delOrigCity)+'">';
        h += '<input type="hidden" name="del-origst" value="'+_e(delOrigState)+'">';
        h += '<input type="hidden" name="del-dstcity" value="'+_e(delDstCity)+'">';
        h += '<input type="hidden" name="del-dstst" value="'+_e(delDstState)+'">';
        h += '<input type="hidden" name="del-origloc" value="'+_e(delOrigLoc)+'">';

        h += '<div class="sc-ef-grid">';
        // Date (required) | Driver
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl sc-del-required-lbl">Delivery Date \u2736<input class="sc-inp" type="date" name="del-date" required></label>';
        h += '<label class="sc-ef-lbl">Driver'+_driverSel('del-driver','')+'</label>';
        h += '</div>';
        // DE Appt | DE Status
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="del-deappt"></label>';
        h += '<label class="sc-ef-lbl">DE Appt Status'+_apptSel('del-deApptStatus','NEED')+'</label>';
        h += '</div>';
        // DE Location Name
        h += '<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="del-deloc" placeholder="Final delivery location\u2026"></label>';
        // Notes (carry over from pickup)
        h += '<label class="sc-ef-lbl">Notes<input class="sc-inp" name="del-notes" value="'+_e(a.notes||'')+'" placeholder="Notes\u2026"></label>';
        h += '</div>'; // sc-ef-grid

        h += '<div class="sc-ef-btns">';
        h += '<button class="sc-btn-cancel" data-action="cancel-delivery-form" data-id="'+a.id+'">Cancel</button>';
        h += '<button class="sc-btn-save sc-btn-del-save" data-action="save-delivery" data-id="'+a.id+'">\u26a1 Save Delivery</button>';
        h += '</div>';
        h += '</div>'; // sc-delivery-form
        return h;
    }

    // ── Add form (per day column, hidden by default) ──────────────────────────
    function _addFormHTML(day) {
        var h = '<div class="sc-add-form" data-add-day="'+day+'" style="display:none">';
        h += '<div class="sc-add-form-hdr">New Assignment</div>';
        h += '<div class="sc-ef-grid">';
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" placeholder="PRO-10421"></label>';
        h += '<label class="sc-ef-lbl">TMS ID<input class="sc-inp" name="tms" placeholder="TMS-8801"></label>';
        h += '</div>';
        h += '<label class="sc-ef-lbl">Pickup Number<input class="sc-inp" name="punum" placeholder="PU-4421"></label>';
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">Action'+_actSel('action','PICKUP')+'</label>';
        h += '<label class="sc-ef-lbl">Driver'+_driverSel('driver','')+'</label>';
        h += '</div>';
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">Start ZIP<input class="sc-inp" name="startzip" placeholder="60601" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">Start City<input class="sc-inp" name="startcity" placeholder="Chicago"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="startst" maxlength="2" placeholder="IL"></label>';
        h += '</div>';
        h += '<label class="sc-ef-lbl">PU Location Name<input class="sc-inp" name="puloc" placeholder="Walmart DC #6045"></label>';
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">PU ZIP<input class="sc-inp" name="puzip" placeholder="60601" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" placeholder="Chicago"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" maxlength="2" placeholder="IL"></label>';
        h += '</div>';
        h += '<span class="sc-zip-warn sc-zip-warn-pu" style="display:none"></span>';
        h += '<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="deloc" placeholder="Target RDC"></label>';
        h += '<div class="sc-ef-row-zip">';
        h += '<label class="sc-ef-lbl sc-ef-zip">DE ZIP<input class="sc-inp" name="dezip" placeholder="53202" maxlength="5"></label>';
        h += '<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" placeholder="Milwaukee"></label>';
        h += '<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" maxlength="2" placeholder="WI"></label>';
        h += '</div>';
        h += '<span class="sc-zip-warn sc-zip-warn-de" style="display:none"></span>';
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">PU Appt (HH:MM)<input class="sc-inp" type="time" name="puappt"></label>';
        h += '<label class="sc-ef-lbl">PU Appt Status'+_apptSel('puApptStatus','NEED')+'</label>';
        h += '</div>';
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="deappt"></label>';
        h += '<label class="sc-ef-lbl">DE Appt Status'+_apptSel('deApptStatus','NEED')+'</label>';
        h += '</div>';
        h += '<div class="sc-ef-row2">';
        h += '<label class="sc-ef-lbl">Seq<input class="sc-inp" type="number" name="seq" value="1" min="1" max="20"></label>';
        h += '<label class="sc-ef-lbl">Notes<input class="sc-inp" name="notes" placeholder="Notes\u2026"></label>';
        h += '</div>';
        h += '</div>'; // sc-ef-grid
        h += '<div class="sc-ef-btns">';
        h += '<button class="sc-btn-cancel" data-action="cancel-add" data-day="'+day+'">Cancel</button>';
        h += '<button class="sc-btn-save" data-action="save-new" data-day="'+day+'">Save</button>';
        h += '</div>';
        h += '</div>'; // sc-add-form
        return h;
    }

    function _actSel(name, val) {
        var opts=[['PICKUP','PICKUP'],['DELIVERY','DELIVERY'],['PICKUP_AND_DELIVER','P&D'],['REPOSITION','REPOSITION'],['OTHER','OTHER']];
        var s='<select class="sc-inp" name="'+name+'">';
        opts.forEach(function(o){ s+='<option value="'+o[0]+'"'+(val===o[0]?' selected':'')+'>'+_e(o[1])+'</option>'; });
        return s+'</select>';
    }
    function _apptSel(name, val) {
        var opts=[['NEED','NEED'],['REQUESTED','REQUESTED'],['APPOINTED','APPOINTED']];
        var s='<select class="sc-inp" name="'+name+'">';
        opts.forEach(function(o){ s+='<option value="'+o[0]+'"'+(val===o[0]?' selected':'')+'>'+_e(o[1])+'</option>'; });
        return s+'</select>';
    }
    function _driverSel(name, val) {
        var drvs = _drivers();
        var s = '<select class="sc-inp" name="'+name+'">';
        s += '<option value=""'+(val===''?' selected':'')+'>— Unassigned —</option>';
        drvs.forEach(function(d){
            s += '<option value="'+_e(d)+'"'+(val===d?' selected':'')+'>'+_e(d)+'</option>';
        });
        return s+'</select>';
    }

    // ── Event binding ─────────────────────────────────────────────────────────
    function _bind(el) {
        el.addEventListener('click', function(e) {
            var b = e.target.closest('[data-action]'); if (!b) return;
            switch (b.dataset.action) {
                case 'prev-week':   _loadMultiWeek(_addDays(_viewStart,-7)); break;
                case 'next-week':   _loadMultiWeek(_addDays(_viewStart, 7)); break;
                case 'today-week':  _loadMultiWeek(_mondayOf(new Date()));   break;
                case 'toggle-edit': _toggleEdit(b.dataset.id);               break;
                case 'cancel-edit': _cancelEdit(b.dataset.id);               break;
                case 'save-edit':   _saveEdit(b.dataset.id);                 break;
                case 'del-asgn':    _delAsgn(b.dataset.id);                  break;
                case 'show-add':              _showAdd(b.dataset.day, b.dataset.driver||''); break;
                case 'cancel-add':            _cancelAdd(b.dataset.day);               break;
                case 'save-new':              _saveNew(b.dataset.day);                 break;
                case 'show-delivery-form':    _showDeliveryForm(b.dataset.id);         break;
                case 'cancel-delivery-form':  _cancelDeliveryForm(b.dataset.id);       break;
                case 'save-delivery':         _saveDelivery(b.dataset.id);             break;
            }
        });
        el.addEventListener('change', function(e) {
            var t = e.target;
            if (t.dataset.action === 'toggle-chk') _toggleChk(t.dataset.id, t.dataset.field, t.checked);
        });
        el.addEventListener('input', function(e) {
            var t = e.target;
            if ((t.name === 'puzip' || t.name === 'dezip' || t.name === 'startzip') && t.value.length === 5) {
                _lookupZipGeneric(t);
            }
        });
    }

    // Generic ZIP lookup — determines target fields by input name
    function _lookupZipGeneric(zipInput) {
        var zip = (zipInput.value||'').trim();
        if (!/^\d{5}$/.test(zip)) return;
        var form = zipInput.closest('.sc-card-edit, .sc-add-form');
        if (!form) return;
        var cityName, stName, warnClass;
        if (zipInput.name === 'puzip') {
            cityName = 'origcity'; stName = 'origst'; warnClass = 'sc-zip-warn-pu';
        } else if (zipInput.name === 'dezip') {
            cityName = 'dstcity';  stName = 'dstst';  warnClass = 'sc-zip-warn-de';
        } else {
            cityName = 'startcity'; stName = 'startst'; warnClass = null;
        }
        var cityI = form.querySelector('[name="'+cityName+'"]');
        var stI   = form.querySelector('[name="'+stName+'"]');
        var warn  = warnClass ? form.querySelector('.'+warnClass) : null;
        if (warn) { warn.textContent = ''; warn.style.display = 'none'; }
        fetch('https://api.zippopotam.us/us/'+zip)
            .then(function(r){ return r.ok ? r.json() : null; })
            .then(function(data){
                if (!data||!data.places||!data.places.length) {
                    if (warn) { warn.textContent = 'ZIP not found'; warn.style.display = ''; }
                    return;
                }
                if (cityI) cityI.value = data.places[0]['place name'];
                if (stI)   stI.value   = data.places[0]['state abbreviation'];
            })
            .catch(function(){
                if (warn) { warn.textContent = 'Lookup failed'; warn.style.display = ''; }
            });
    }

    // ── Card edit toggle ──────────────────────────────────────────────────────
    function _toggleEdit(id) {
        var card = document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef   = card.querySelector('.sc-card-edit'); if (!ef) return;
        var open = ef.style.display !== 'none';
        ef.style.display = open ? 'none' : 'block';
        if (!open) { var fi = ef.querySelector('input,select'); if (fi) fi.focus(); }
    }
    function _cancelEdit(id) {
        var card = document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef   = card.querySelector('.sc-card-edit'); if (ef) ef.style.display = 'none';
    }

    // ── Save edit ─────────────────────────────────────────────────────────────
    function _saveEdit(id) {
        var card = document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef   = card.querySelector('.sc-card-edit'); if (!ef) return;
        var a    = _allAsgns().find(function(x){ return x.id===id; }); if (!a) return;
        var g    = function(n){ var i=ef.querySelector('[name="'+n+'"]'); return i?i.value.trim():''; };

        var saveBtn = ef.querySelector('[data-action="save-edit"]');
        if (saveBtn) { saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        var loadBody = {
            alexeiId: g('pro'), tmsId: g('tms'), puNumber: g('punum'),
            puCity: g('origcity'), puState: g('origst').toUpperCase(),
            deCity: g('dstcity'),  deState: g('dstst').toUpperCase(),
        };
        var asgnBody = {
            date:             a.date,
            weekStart:        _mondayOf(new Date(a.date+'T00:00:00')),
            driverName:       g('driver'),
            sequenceNumber:   parseInt(g('seq') || a.sequenceNumber, 10),
            actionType:       g('action') || a.actionType,
            originCity:       g('origcity'), originState: g('origst').toUpperCase(),
            destCity:         g('dstcity'),  destState:   g('dstst').toUpperCase(),
            puAppt:           g('puappt'),   deAppt:      g('deappt'),
            puLocationName:   g('puloc'),    deLocationName: g('deloc'),
            driverStartCity:  g('startcity'),
            driverStartState: g('startst').toUpperCase(),
            puApptStatus:     g('puApptStatus'),
            deApptStatus:     g('deApptStatus'),
            notes:            g('notes'),
        };

        var loadP;
        if (a.loadId) {
            loadP = _api('PUT', '/api/ivan/loads/'+a.loadId, loadBody).then(function(){ return a.loadId; });
        } else if (g('pro')||g('tms')||g('punum')||g('origcity')||g('dstcity')) {
            loadP = _api('POST', '/api/ivan/loads', loadBody).then(function(r){ return r.id; });
        } else {
            loadP = Promise.resolve(null);
        }

        loadP.then(function(lid){
            if (lid) asgnBody.loadId = lid;
            return _api('PUT', '/api/ivan/schedule/assignments/'+id, asgnBody);
        }).then(function(){ _reload(); })
          .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Add form show/hide ────────────────────────────────────────────────────
    function _showAdd(day, driver) {
        document.querySelectorAll('.sc-add-form').forEach(function(f){ if(f.dataset.addDay!==day) f.style.display='none'; });
        var form = document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (!form) return;
        form.querySelectorAll('input').forEach(function(i){ i.value=''; });
        form.querySelector('[name="action"]').value = 'PICKUP';
        form.querySelector('[name="puApptStatus"]').value = 'NEED';
        form.querySelector('[name="deApptStatus"]').value = 'NEED';
        // Set driver select
        var drvSel = form.querySelector('[name="driver"]');
        if (drvSel) drvSel.value = driver || '';
        var seqI = form.querySelector('[name="seq"]');
        if (seqI) seqI.value = _nextSeq(day, driver);
        form.style.display = 'block';
        setTimeout(function(){ form.scrollIntoView({behavior:'smooth',block:'nearest'}); }, 50);
        setTimeout(function(){ var fi=form.querySelector('input'); if(fi) fi.focus(); }, 80);
    }
    function _cancelAdd(day) {
        var f = document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (f) f.style.display='none';
    }

    // ── Save new assignment ───────────────────────────────────────────────────
    function _saveNew(day) {
        var form = document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (!form) return;
        var g    = function(n){ var i=form.querySelector('[name="'+n+'"]'); return i?i.value.trim():''; };
        var saveBtn = form.querySelector('[data-action="save-new"]');
        if (saveBtn) { saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        var proNum   = g('pro'), origcity = g('origcity'), dstcity = g('dstcity');
        var loadBody = {
            alexeiId: proNum, tmsId: g('tms'), puNumber: g('punum'),
            puCity: origcity, puState: g('origst').toUpperCase(),
            deCity: dstcity,  deState: g('dstst').toUpperCase(),
        };
        var asgnBody = {
            date:             day,
            weekStart:        _mondayOf(new Date(day+'T00:00:00')),
            driverName:       g('driver'),
            sequenceNumber:   parseInt(g('seq')||'1', 10),
            actionType:       g('action')||'PICKUP',
            originCity:       origcity, originState: g('origst').toUpperCase(),
            destCity:         dstcity,  destState:   g('dstst').toUpperCase(),
            puAppt:           g('puappt'),  deAppt:       g('deappt'),
            puLocationName:   g('puloc'),   deLocationName: g('deloc'),
            driverStartCity:  g('startcity'),
            driverStartState: g('startst').toUpperCase(),
            puApptStatus:     g('puApptStatus')||'NEED',
            deApptStatus:     g('deApptStatus')||'NEED',
            notes:            g('notes'),
        };

        var matchedLoad = proNum ? _allLoads().find(function(l){ return l.alexeiId===proNum; }) : null;
        var loadP;
        if (matchedLoad) {
            asgnBody.loadId = matchedLoad.id; loadP = Promise.resolve(matchedLoad.id);
        } else if (proNum||g('tms')||g('punum')||origcity||dstcity) {
            loadP = _api('POST', '/api/ivan/loads', loadBody).then(function(r){ asgnBody.loadId=r.id; return r.id; });
        } else {
            loadP = Promise.resolve(null);
        }

        loadP.then(function(){ return _api('POST', '/api/ivan/schedule/assignments', asgnBody); })
             .then(function(){ _reload(); })
             .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Delivery form show/hide ───────────────────────────────────────────────
    function _showDeliveryForm(id) {
        // Close any other open delivery forms
        document.querySelectorAll('.sc-delivery-form').forEach(function(f){
            if (f.dataset.delFor !== id) f.style.display = 'none';
        });
        var form = document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]');
        if (!form) return;
        form.style.display = 'block';
        setTimeout(function(){
            form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            var di = form.querySelector('[name="del-date"]'); if (di) di.focus();
        }, 60);
    }
    function _cancelDeliveryForm(id) {
        var form = document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]');
        if (form) form.style.display = 'none';
    }

    // ── Save delivery leg ─────────────────────────────────────────────────────
    function _saveDelivery(id) {
        var form = document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]');
        if (!form) return;
        var g = function(n) { var i = form.querySelector('[name="'+n+'"]'); return i ? i.value.trim() : ''; };

        var dateVal = g('del-date');
        if (!dateVal) {
            var di = form.querySelector('[name="del-date"]');
            if (di) { di.focus(); di.classList.add('sc-inp-error'); }
            return;
        }

        var saveBtn = form.querySelector('[data-action="save-delivery"]');
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving\u2026'; }

        var pickupA = _allAsgns().find(function(x) { return x.id === id; });
        if (!pickupA) return;

        var weekStart = _mondayOf(new Date(dateVal + 'T00:00:00'));

        var asgnBody = {
            date:             dateVal,
            weekStart:        weekStart,
            loadId:           g('del-loadid') || pickupA.loadId || null,
            driverName:       g('del-driver'),
            sequenceNumber:   1,
            actionType:       'DELIVERY',
            // Origin of delivery = where pickup ended up (staging/yard)
            originCity:       g('del-origcity'),
            originState:      g('del-origst').toUpperCase(),
            // Destination = master load's delivery destination
            destCity:         g('del-dstcity'),
            destState:        g('del-dstst').toUpperCase(),
            // Location names: pickup's dest location → delivery origin; user enters dest
            puLocationName:   g('del-origloc'),
            deLocationName:   g('del-deloc'),
            // Appt: PU time blank for delivery leg; DE time from user
            puAppt:           '',
            deAppt:           g('del-deappt'),
            puApptStatus:     'NEED',
            deApptStatus:     g('del-deApptStatus') || 'NEED',
            notes:            g('del-notes'),
        };

        _api('POST', '/api/ivan/schedule/assignments', asgnBody)
            .then(function() { _reload(); })
            .catch(function(err) {
                alert('Save failed: ' + err.message);
                if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '\u26a1 Save Delivery'; }
            });
    }

    // ── Delete ────────────────────────────────────────────────────────────────
    function _delAsgn(id) {
        if (!confirm('Delete this assignment?')) return;
        _api('DELETE', '/api/ivan/schedule/assignments/'+id)
            .then(function(){ _reload(); })
            .catch(function(err){ alert('Delete failed: '+err.message); });
    }

    // ── DONE toggle (optimistic) ──────────────────────────────────────────────
    function _toggleChk(id, field, checked) {
        var a = _allAsgns().find(function(x){ return x.id===id; }); if (!a) return;
        var prev = a[field]; a[field] = checked;
        var isDone = _done(a);
        var card = document.querySelector('.sc-card[data-id="'+id+'"]');
        if (card) {
            card.classList.toggle('sc-card-done', isDone);
            if (field==='isComplete') {
                var doneSpan = card.querySelector('.sc-done-lbl span');
                if (doneSpan) doneSpan.textContent = checked ? '\u2713 DONE' : 'DONE';
            }
        }
        var patch = {}; patch[field] = checked;
        _api('PUT', '/api/ivan/schedule/assignments/'+id, patch).catch(function(err){
            a[field] = prev; alert('Save failed: '+err.message); _render();
        });
    }

    // ── Public ────────────────────────────────────────────────────────────────
    function mountSchedule(containerId) {
        _cid = containerId;
        _loadMultiWeek(_mondayOf(new Date()));
    }

    return { mountSchedule: mountSchedule };
}());
