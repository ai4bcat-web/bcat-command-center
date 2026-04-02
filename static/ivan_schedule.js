/**
 * ivan_schedule.js — Round 9: Multi-week Calendar Dispatch Board for Ivan Cartage
 *
 * New in Round 9:
 *  - Bug fix: only ONE "Add Delivery" prompt per shipment (canonical first-pickup only)
 *  - Pick count / drop count fields on loads, drives leg progress display
 *  - Load type field (E2OPEN / BCAT BROKER / IVAN BROKER / IVAN CUSTOMER)
 *  - Carrier Name field (visible when load type = BCAT BROKER)
 *  - E2OPEN CLOSED checkbox (visible when load type = E2OPEN)
 *  - Green card requires both isComplete + e2openClosed for E2OPEN loads
 *  - Add Delivery preserves deLocationName
 *  - Sequence inline editable directly on card (no edit mode needed)
 *  - Driver inline assignable directly on card
 *  - FCFS appointment support with optional time ranges
 *  - Hide PU appt section for DELIVERY legs; hide DE section for PICKUP legs
 *  - Post-creation edit bug fix (fallback date from DOM when weekData missing)
 */
var IvanScheduleApp = (function () {
    'use strict';

    var NUM_WEEKS = 4;
    var BASE = [43.1006, -87.8751]; // Pleasant Prairie, WI

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
        NEED:      'sc-apst-need',
        REQUESTED: 'sc-apst-req',
        APPOINTED: 'sc-apst-apt',
    };
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
    var UNASSIGNED_COLOR = { b: '#475569', bg: '#0c1118', t: '#94a3b8' };
    var LOAD_COLORS = [
        '#38bdf8','#fbbf24','#34d399','#f87171','#c084fc',
        '#22d3ee','#fb923c','#a3e635','#f472b6','#818cf8',
    ];
    var LOAD_TYPE_CSS = {
        'E2OPEN':        'sc-lt-e2open',
        'BCAT BROKER':   'sc-lt-bcat',
        'IVAN BROKER':   'sc-lt-ivan-broker',
        'IVAN CUSTOMER': 'sc-lt-ivan-cust',
    };

    // ── State ─────────────────────────────────────────────────────────────────
    var _cid        = null;
    var _viewStart  = null;
    var _weekData   = {};
    var _missingDel = {};   // loadId -> canonical pickup assignment id
    var _auditData  = [];
    var _auditOpen  = false;
    // Driver Day View
    var _viewMode   = 'calendar';  // 'calendar' | 'ddv'
    var _ddvDriver  = '';
    var _ddvDate    = '';
    var _ddvData    = [];          // assignments loaded for DDV

    // Shipment color palette (10 distinct operational colors)
    var SHIP_COLORS = ['#3b82f6','#f59e0b','#10b981','#f43f5e','#a78bfa',
                       '#22d3ee','#fb923c','#84cc16','#f472b6','#e879f9'];

    // ── CSRF / API ────────────────────────────────────────────────────────────
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
                if (ct.indexOf('application/json') >= 0)
                    return r.json().then(function (e) { throw new Error(e.error || r.statusText); });
                throw new Error('HTTP ' + r.status + ' ' + r.statusText +
                    (r.status === 401 ? ' (session expired — refresh)' : ''));
            }
            if (ct.indexOf('application/json') < 0)
                throw new Error('Server returned non-JSON (HTTP ' + r.status + ').');
            return r.json();
        });
    }

    // ── Date helpers ──────────────────────────────────────────────────────────
    function _iso(d) {
        return d.getFullYear() + '-' +
               String(d.getMonth()+1).padStart(2,'0') + '-' +
               String(d.getDate()).padStart(2,'0');
    }
    function _mondayOf(d) {
        var dt = new Date(d), wd = dt.getDay();
        dt.setDate(dt.getDate() + (wd === 0 ? -6 : 1 - wd));
        return _iso(dt);
    }
    function _addDays(iso, n) {
        var d = new Date(iso + 'T00:00:00'); d.setDate(d.getDate() + n); return _iso(d);
    }
    function _weekOf(iso) { return [0,1,2,3,4].map(function(i){ return _addDays(iso,i); }); }
    function _fmtWeek(ws) {
        var d = new Date(ws+'T00:00:00'), e = new Date(ws+'T00:00:00');
        e.setDate(e.getDate()+6);
        var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return M[d.getMonth()]+' '+d.getDate()+' \u2013 '+M[e.getMonth()]+' '+e.getDate()+', '+e.getFullYear();
    }
    function _fmtColHdr(iso) {
        var d = new Date(iso+'T00:00:00');
        var DAY=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return { day: DAY[d.getDay()], date: MON[d.getMonth()]+' '+d.getDate() };
    }
    function _nextBizDay(isoDate) {
        var d = new Date(isoDate + 'T00:00:00');
        d.setDate(d.getDate() + 1);
        while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
        return _iso(d);
    }
    function _relTime(isoStr) {
        if (!isoStr) return '';
        var t = new Date(isoStr.indexOf('T') >= 0 ? isoStr+'Z' : isoStr+'T00:00:00Z');
        var s = (Date.now() - t.getTime()) / 1000;
        if (s < 60)    return 'just now';
        if (s < 3600)  return Math.floor(s/60)+'m ago';
        if (s < 86400) return Math.floor(s/3600)+'h ago';
        return Math.floor(s/86400)+'d ago';
    }

    // ── Deadhead (always from BASE) ───────────────────────────────────────────
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
    function _driverDH(sorted) {
        return sorted.map(function(a,i) {
            var orig=_ll(a.originCity,a.originState), dest=_ll(a.destCity,a.destState);
            var toDH=0, retDH=0;
            if (i===0) { if(orig) toDH=_mi(_hav(BASE,orig)); }
            else { var pd=_ll(sorted[i-1].destCity,sorted[i-1].destState); if(pd&&orig) toDH=_mi(_hav(pd,orig)); }
            if (i===sorted.length-1&&dest) retDH=_mi(_hav(dest,BASE));
            return {toDH:toDH, retDH:retDH};
        });
    }

    // ── Misc helpers ──────────────────────────────────────────────────────────
    function _isCardGreen(a) {
        var load = a.load || {};
        if (load.loadType === 'E2OPEN') return !!(a.isComplete && a.e2openClosed);
        return !!a.isComplete;
    }
    function _done(a) { return _isCardGreen(a); }
    function _e(s) {
        return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function _hash(str) { var h=0; for(var i=0;i<str.length;i++) h=(h*31+str.charCodeAt(i))&0xffff; return h; }
    function _dc(name) { if(!name||!name.trim()) return UNASSIGNED_COLOR; return DRIVER_COLORS[_hash(name.toLowerCase())%DRIVER_COLORS.length]; }
    function _lc(id)   { return LOAD_COLORS[_hash(id||'')%LOAD_COLORS.length]; }

    // ── Data accessors ────────────────────────────────────────────────────────
    function _allAsgns() {
        var all=[];
        Object.keys(_weekData).forEach(function(w){ all=all.concat(_weekData[w].assignments||[]); });
        return all;
    }
    function _allLoads() {
        var seen={}, all=[];
        Object.keys(_weekData).forEach(function(w){
            (_weekData[w].loads||[]).forEach(function(l){ if(!seen[l.id]){seen[l.id]=1;all.push(l);} });
        });
        return all;
    }
    function _getDriversFromLS() {
        try {
            var raw = localStorage.getItem('bcat_ivan_drivers');
            if (!raw) return [];
            return JSON.parse(raw).filter(function(d){ return d.status==='active'; }).map(function(d){ return d.name; }).sort();
        } catch(e) { return []; }
    }
    function _drivers() {
        var seen={}, out=[];
        _allAsgns().forEach(function(a){ var d=(a.driverName||'').trim(); if(d&&!seen[d]){seen[d]=1;out.push(d);} });
        _getDriversFromLS().forEach(function(n){ if(!seen[n]){seen[n]=1;out.push(n);} });
        return out.sort();
    }
    function _nextSeq(day, driver) {
        var week=_mondayOf(new Date(day+'T00:00:00'));
        return ((_weekData[week]||{}).assignments||[]).filter(function(a){
            return a.date===day && (a.driverName||'').trim()===(driver||'').trim();
        }).length+1;
    }

    // ── Missing delivery detection (FIXED: stores canonical pickup ID) ────────
    function _computeMissingDel() {
        var all=_allAsgns();
        var pickupMap={};   // loadId -> earliest pickup assignment
        var delivCounts={}; // loadId -> count of delivery legs
        all.forEach(function(a) {
            if (!a.loadId) return;
            if (a.actionType==='PICKUP') {
                var ex=pickupMap[a.loadId];
                if (!ex || a.date < ex.date || (a.date===ex.date && (a.sequenceNumber||0) < (ex.sequenceNumber||0))) {
                    pickupMap[a.loadId]=a;
                }
            }
            if (a.actionType==='DELIVERY'||a.actionType==='PICKUP_AND_DELIVER') {
                delivCounts[a.loadId]=(delivCounts[a.loadId]||0)+1;
            }
        });
        _missingDel={};
        Object.keys(pickupMap).forEach(function(lid) {
            var a=pickupMap[lid];
            var needed=(a.load||{}).dropCount||1;
            var have=delivCounts[lid]||0;
            if (have < needed) _missingDel[lid]=a.id; // only show on canonical pickup
        });
    }

    // ── ZIP lookup ────────────────────────────────────────────────────────────
    function _lookupZipGeneric(zipInput) {
        var zip=(zipInput.value||'').trim();
        if (!/^\d{5}$/.test(zip)) return;
        var form=zipInput.closest('.sc-card-edit,.sc-add-form,.sc-delivery-form');
        if (!form) return;
        var cityName,stName,warnClass;
        if (zipInput.name==='puzip')   { cityName='origcity'; stName='origst'; warnClass='sc-zip-warn-pu'; }
        else if (zipInput.name==='dezip') { cityName='dstcity'; stName='dstst'; warnClass='sc-zip-warn-de'; }
        else return;
        var cityI=form.querySelector('[name="'+cityName+'"]');
        var stI  =form.querySelector('[name="'+stName+'"]');
        var warn = warnClass ? form.querySelector('.'+warnClass) : null;
        if (warn) { warn.textContent=''; warn.style.display='none'; }
        fetch('https://api.zippopotam.us/us/'+zip)
            .then(function(r){ return r.ok?r.json():null; })
            .then(function(data){
                if (!data||!data.places||!data.places.length) { if(warn){warn.textContent='ZIP not found';warn.style.display='';} return; }
                if (cityI) cityI.value=data.places[0]['place name'];
                if (stI)   stI.value  =data.places[0]['state abbreviation'];
            })
            .catch(function(){ if(warn){warn.textContent='Lookup failed';warn.style.display='';} });
    }

    // ── Multi-week data load ──────────────────────────────────────────────────
    function _loadMultiWeek(viewStart) {
        _viewStart=viewStart;
        var el=document.getElementById(_cid);
        if (el) el.innerHTML='<div class="sc-loading">Loading schedule\u2026</div>';
        var weeks=[];
        for (var i=0;i<NUM_WEEKS;i++) weeks.push(_addDays(viewStart,i*7));
        _weekData={};
        var promises=weeks.map(function(week){
            return _api('GET','/api/ivan/schedule?weekStart='+week).then(function(data){
                _weekData[week]={
                    assignments: Array.isArray(data)?data:(data.assignments||[]),
                    loads:       Array.isArray(data)?[]:(data.loads||[]),
                };
            }).catch(function(){ _weekData[week]={assignments:[],loads:[]}; });
        });
        Promise.all(promises).then(function(){ _render(); });
    }
    function _reload() { _loadMultiWeek(_viewStart); }

    // ── Render ────────────────────────────────────────────────────────────────
    function _render() {
        var el=document.getElementById(_cid); if(!el) return;
        _computeMissingDel();

        if (_viewMode==='ddv') {
            _renderDDV(el);
            _bindDDV(el);
            return;
        }

        var today=_iso(new Date()), curWeek=_mondayOf(new Date());
        var drvs=_drivers();

        var html='<div class="sc-board">'+_navHTML();

        html+='<datalist id="sc-drvs-dl">';
        drvs.forEach(function(d){ html+='<option value="'+_e(d)+'">'; });
        html+='</datalist>';

        var weeks=[];
        for (var i=0;i<NUM_WEEKS;i++) weeks.push(_addDays(_viewStart,i*7));
        weeks.forEach(function(week){
            var data=_weekData[week]||{assignments:[],loads:[]};
            var isCur=week===curWeek, asgns=data.assignments, total=asgns.length;
            html+='<div class="sc-week-section'+(isCur?' sc-week-current':'')+'" data-week="'+week+'">';
            html+='<div class="sc-week-hdr">';
            html+='<span class="sc-week-label">Week of '+_fmtWeek(week)+'</span>';
            html+='<span class="sc-week-count">'+total+' assignment'+(total!==1?'s':'')+'</span>';
            if (isCur) html+='<span class="sc-week-now-pill">CURRENT</span>';
            html+='</div>';
            html+='<div class="sc-calendar">';
            _weekOf(week).forEach(function(day){
                var isToday=day===today;
                var dayA=asgns.filter(function(a){ return a.date===day; });
                html+=_colHTML(day,dayA,isToday);
            });
            html+='</div></div>';
        });
        html+='</div>';
        el.innerHTML=html;
        _bind(el);
        // Audit overlay lives outside the board so it persists across renders
        _ensureAuditOverlay();
        if (_auditOpen) _loadAudit();
    }

    // ── Ensure audit overlay in DOM (outside container) ──────────────────────
    function _ensureAuditOverlay() {
        if (!document.getElementById('sc-audit-overlay')) {
            var ov=document.createElement('div');
            ov.id='sc-audit-overlay';
            ov.className='sc-audit-overlay';
            ov.style.display='none';
            document.body.appendChild(ov);
        }
    }

    function _navHTML() {
        var endLabel=_fmtWeek(_addDays(_viewStart,(NUM_WEEKS-1)*7));
        var label=_fmtWeek(_viewStart)+' \u2013 '+endLabel;
        var isCal=_viewMode==='calendar';
        var isDDV=_viewMode==='ddv';
        var h='<div class="sc-nav">';
        // View toggle tabs
        h+='<button class="sc-nav-btn sc-view-tab'+(isCal?' sc-view-tab-active':'')+'" data-action="view-calendar">\uD83D\uDDD3 Calendar</button>';
        h+='<button class="sc-nav-btn sc-view-tab'+(isDDV?' sc-view-tab-active':'')+'" data-action="view-ddv">\uD83D\uDC64 Driver Day</button>';
        h+='<span class="sc-nav-sep"></span>';
        if (isCal) {
            h+='<button class="sc-nav-btn" data-action="prev-week">\u25c4 Prev</button>';
            h+='<span class="sc-week-label">'+label+'</span>';
            h+='<button class="sc-nav-btn" data-action="next-week">Next \u25ba</button>';
            h+='<button class="sc-nav-btn sc-today-btn" data-action="today-week">Today</button>';
        }
        h+='<button class="sc-nav-btn sc-audit-toggle-btn'+(isDDV?' sc-nav-right':'')+'" data-action="toggle-audit">\uD83D\uDCCB Audit</button>';
        h+='</div>';
        return h;
    }

    // ── Driver Day View ───────────────────────────────────────────────────────
    function _renderDDV(el) {
        var today=_iso(new Date());
        if (!_ddvDate) _ddvDate=today;
        var drvs=_drivers();
        var h='<div class="sc-board sc-ddv-board">'+_navHTML();
        // Controls bar
        h+='<div class="sc-ddv-controls">';
        h+='<label class="sc-ddv-lbl">Driver';
        h+='<select class="sc-ddv-sel" data-action="ddv-driver">';
        h+='<option value="">— Select driver —</option>';
        drvs.forEach(function(d){ h+='<option value="'+_e(d)+'"'+(_ddvDriver===d?' selected':'')+'>'+_e(d)+'</option>'; });
        h+='</select></label>';
        h+='<label class="sc-ddv-lbl">Date<input class="sc-ddv-date-inp" type="date" data-action="ddv-date" value="'+_e(_ddvDate)+'"></label>';
        h+='</div>';

        if (!_ddvDriver) {
            h+='<div class="sc-ddv-empty">Select a driver to see their day.</div>';
            h+='</div>';
            el.innerHTML=h;
            return;
        }

        // Filter assignments for this driver+date from weekData + ddvData
        var all=_allAsgns().concat(_ddvData.filter(function(a){
            var already=_allAsgns().find(function(x){return x.id===a.id;});
            return !already;
        }));
        var dayA=all.filter(function(a){
            return a.date===_ddvDate && (a.driverName||'').trim()===_ddvDriver.trim();
        }).sort(function(a,b){ return (a.sequenceNumber||0)-(b.sequenceNumber||0); });

        var dc=_dc(_ddvDriver);
        h+='<div class="sc-ddv-day" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';
        h+='<div class="sc-ddv-day-hdr">';
        h+='<span class="sc-ddv-drv-name">'+_e(_ddvDriver)+'</span>';
        h+='<span class="sc-ddv-date-label">'+_e(_ddvDate)+'</span>';
        h+='<span class="sc-ddv-count">'+dayA.length+' stop'+(dayA.length!==1?'s':'')+'</span>';
        h+='</div>';

        if (!dayA.length) {
            h+='<div class="sc-ddv-empty">No assignments for this driver on '+_e(_ddvDate)+'.</div>';
        } else {
            var dh=_driverDH(dayA);
            dayA.forEach(function(a,i) {
                h+=_ddvCardHTML(a, dh[i].toDH, i+1, dayA.length, dc);
            });
        }
        h+='</div></div>';
        el.innerHTML=h;
    }

    function _ddvCardHTML(a, dhMi, step, total, dc) {
        var isDone=_done(a), load=a.load||{};
        var pro=load.alexeiId||'', tmsId=load.tmsId||'', puNum=load.puNumber||'';
        var shipRef=load.shipmentRef||'';
        var label=ACTION_LABEL[a.actionType]||a.actionType||'?';
        var actCss=ACTION_CSS[a.actionType]||'sc-badge-other';
        var loadType=load.loadType||'', carrierName=load.carrierName||'';
        var ltCss=LOAD_TYPE_CSS[loadType]||'';
        var orig=[a.originCity,a.originState].filter(Boolean).join(', ');
        var dest=[a.destCity,a.destState].filter(Boolean).join(', ');
        var puLoc=a.puLocationName||'', deLoc=a.deLocationName||'';
        var isPU=a.actionType==='PICKUP', isDE=a.actionType==='DELIVERY';

        var shipColor=(!isDone&&load.shipmentColor)?load.shipmentColor:'';
        var borderStyle=shipColor?'border-left:3px solid '+shipColor+';':'';

        var cls='sc-ddv-card'+(isDone?' sc-card-done':'');
        var h='<div class="'+cls+'" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+';'+borderStyle+'">';
        // Step number
        h+='<div class="sc-ddv-step"><span class="sc-ddv-step-num">'+step+'</span>';
        if (step<total) h+='<span class="sc-ddv-step-line"></span>';
        h+='</div>';
        h+='<div class="sc-ddv-content">';
        // Row 1: action badge | PRO | load type | DH
        h+='<div class="sc-ddv-row1">';
        h+='<span class="sc-badge '+actCss+'">'+_e(label)+'</span>';
        if (pro) h+=' <span class="sc-ddv-pro">'+_e(pro)+'</span>';
        else h+=' <span class="sc-ntb-badge">NEED TO BUILD</span>';
        if (shipRef) h+=' <span class="sc-ddv-ref">'+_e(shipRef)+'</span>';
        if (loadType&&ltCss) h+=' <span class="sc-load-type-badge '+ltCss+'">'+_e(loadType)+'</span>';
        if (dhMi>0) h+=' <span class="sc-dh-tag">DH '+dhMi+' mi</span>';
        if (isDone) h+=' <span class="sc-ddv-done-pill">\u2713 DONE</span>';
        h+='</div>';
        // Row 2: locations
        var locParts=[];
        if (!isDE&&(puLoc||orig)) locParts.push((puLoc?puLoc+' ':'')+orig);
        if (!isPU&&(deLoc||dest))  locParts.push('\u2192 '+(deLoc?deLoc+' ':'')+dest);
        if (locParts.length) h+='<div class="sc-ddv-locs">'+locParts.map(_e).join(' ')+'</div>';
        // Row 3: appt details
        var apptParts=[];
        if (!isDE) {
            var puAT=a.puApptType||'APPT';
            if (puAT==='FCFS') apptParts.push('PU FCFS '+([a.puFcfsStart,a.puFcfsEnd].filter(Boolean).join('\u2013')));
            else if (a.puAppt) apptParts.push('PU '+a.puAppt+' ('+( a.puApptStatus||'NEED')+')');
            else apptParts.push('PU: '+(a.puApptStatus||'NEED'));
        }
        if (!isPU) {
            var deAT=a.deApptType||'APPT';
            if (deAT==='FCFS') apptParts.push('DE FCFS '+([a.deFcfsStart,a.deFcfsEnd].filter(Boolean).join('\u2013')));
            else if (a.deAppt) apptParts.push('DE '+a.deAppt+' ('+(a.deApptStatus||'NEED')+')');
            else apptParts.push('DE: '+(a.deApptStatus||'NEED'));
        }
        if (apptParts.length) h+='<div class="sc-ddv-appt">'+apptParts.map(_e).join(' \u00b7 ')+'</div>';
        // Row 4: IDs + carrier
        var ids=[];
        if (tmsId) ids.push('TMS: '+tmsId);
        if (puNum) ids.push('PU#: '+puNum);
        if (carrierName) ids.push(carrierName);
        if (ids.length) h+='<div class="sc-ddv-ids">'+_e(ids.join(' \u00b7 '))+'</div>';
        if (a.notes) h+='<div class="sc-ddv-notes">'+_e(a.notes)+'</div>';
        h+='</div></div>';
        return h;
    }

    function _bindDDV(el) {
        el.addEventListener('change', function(e) {
            var t=e.target;
            if (t.dataset.action==='ddv-driver') { _ddvDriver=t.value; _ddvLoadData(); }
            else if (t.dataset.action==='ddv-date') { _ddvDate=t.value; _ddvLoadData(); }
        });
        el.addEventListener('click', function(e) {
            var b=e.target.closest('[data-action]'); if (!b) return;
            switch (b.dataset.action) {
                case 'view-calendar': _viewMode='calendar'; _reload(); break;
                case 'view-ddv':      _viewMode='ddv';      _render(); break;
                case 'toggle-audit':  _toggleAudit(); break;
            }
        });
    }

    function _ddvLoadData() {
        // First try to serve from existing weekData
        if (_ddvDate && _ddvDriver) {
            var week=_mondayOf(new Date(_ddvDate+'T00:00:00'));
            if (_weekData[week]) { _render(); return; }
            // Fetch week data
            _api('GET','/api/ivan/schedule?weekStart='+week).then(function(data){
                _weekData[week]={
                    assignments: Array.isArray(data)?data:(data.assignments||[]),
                    loads:       Array.isArray(data)?[]:(data.loads||[]),
                };
                _render();
            }).catch(function(){ _render(); });
        } else {
            _render();
        }
    }

    function _colHTML(day, dayA, isToday) {
        var hdr=_fmtColHdr(day), drvs=[];
        dayA.forEach(function(a){ var d=(a.driverName||'').trim()||'Unassigned'; if(drvs.indexOf(d)<0) drvs.push(d); });
        drvs.sort();
        var cls='sc-col'+(isToday?' sc-col-today':'');
        var h='<div class="'+cls+'" data-day="'+day+'">';
        h+='<div class="sc-col-hdr">';
        h+='<span class="sc-col-dayname">'+hdr.day+'</span>';
        h+='<span class="sc-col-date">'+hdr.date+'</span>';
        if (isToday) h+='<span class="sc-today-pill">TODAY</span>';
        h+='</div>';
        if (drvs.length===0) {
            h+='<div class="sc-empty-col">No assignments</div>';
        } else {
            drvs.forEach(function(drv){
                var da=dayA.filter(function(a){ return ((a.driverName||'').trim()||'Unassigned')===drv; })
                           .sort(function(a,b){ return (a.sequenceNumber||0)-(b.sequenceNumber||0); });
                h+=_drvSection(drv,day,da);
            });
        }
        h+=_addFormHTML(day);
        h+='<button class="sc-add-col-btn" data-action="show-add" data-day="'+day+'">+ Add</button>';
        h+='</div>';
        return h;
    }

    function _drvSection(drv, day, sorted) {
        var isUnassigned=drv==='Unassigned';
        var dc=isUnassigned?UNASSIGNED_COLOR:_dc(drv);
        var dh=_driverDH(sorted);
        var retDH=dh.length?dh[dh.length-1].retDH:0;
        // Find load of first assignment for paint bucket context (first loadId in section)
        var firstLoadId=sorted.length&&sorted[0].loadId?sorted[0].loadId:'';
        var h='<div class="sc-drv-sec" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';
        h+='<div class="sc-drv-hdr">';
        h+='<span class="sc-drv-name">'+_e(drv)+'</span>';
        h+='<div class="sc-drv-hdr-acts">';
        if (firstLoadId) {
            h+='<button class="sc-drv-color-btn" data-action="open-color-picker" data-load-id="'+_e(firstLoadId)+'" title="\uD83C\uDFA8 Set shipment color">\uD83C\uDFA8</button>';
        }
        h+='<button class="sc-drv-add" data-action="show-add" data-day="'+day+'" data-driver="'+_e(isUnassigned?'':drv)+'" title="Add move for this driver">+</button>';
        h+='</div></div>';
        sorted.forEach(function(a,i){ h+=_cardHTML(a,dh[i].toDH,dc); });
        if (retDH>0) h+='<div class="sc-ret-bar">\u21a9 Base: '+retDH+' mi</div>';
        h+='</div>';
        return h;
    }

    // ── Card HTML — all fields visible, inline driver + seq ───────────────────
    function _cardHTML(a, dhMi, dc) {
        var isDone=_done(a), load=a.load||{};
        var pro=load.alexeiId||'', tmsId=load.tmsId||'', puNum=load.puNumber||'';
        var shipRef=load.shipmentRef||'', shipColor=load.shipmentColor||'';
        var lc=a.loadId?_lc(a.loadId):null;
        var label=ACTION_LABEL[a.actionType]||a.actionType||'?';
        var actCss=ACTION_CSS[a.actionType]||'sc-badge-other';
        var puSt=a.puApptStatus||'NEED', deSt=a.deApptStatus||'NEED';
        var puCss=APPT_CSS[puSt]||'sc-apst-need', deCss=APPT_CSS[deSt]||'sc-apst-need';
        var orig=[a.originCity,a.originState].filter(Boolean).join(', ');
        var dest=[a.destCity,a.destState].filter(Boolean).join(', ');
        var puLoc=a.puLocationName||'', deLoc=a.deLocationName||'';
        var seq=a.sequenceNumber||0;
        var loadType=load.loadType||'';
        var carrierName=load.carrierName||'';
        var pickCount=load.pickCount||1;
        var dropCount=load.dropCount||1;
        var isE2open=loadType==='E2OPEN';
        var isBcat  =loadType==='BCAT BROKER';
        var isPU    =a.actionType==='PICKUP';
        var isDE    =a.actionType==='DELIVERY';
        var isPAD   =a.actionType==='PICKUP_AND_DELIVER';
        // Checkboxes only appear on delivery/P&D legs (req 12)
        var isDeliveryLeg=isDE||isPAD;
        // Missing delivery: only on canonical pickup assignment
        var isMissingDel=isPU&&a.loadId&&_missingDel[a.loadId]===a.id;
        // Shipment color accent (non-done only)
        var shipColorStyle=(!isDone&&shipColor)?'border-left:3px solid '+shipColor+';background:'+shipColor+'18;':'';

        var cls='sc-card'+(isDone?' sc-card-done':'')+(isMissingDel?' sc-card-missing-del':'');
        var h='<div class="'+cls+'" data-id="'+a.id+'" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+';'+shipColorStyle+'" title="Double-click to edit">';
        h+='<div class="sc-card-view">';

        // ── Line 1: Inline driver dropdown · seq input | actions ──
        h+='<div class="sc-cv-hdr">';
        h+='<div class="sc-cv-drv">';
        h+=_driverSelInline(a.driverName||'', a.id);
        h+='<span class="sc-cv-seq-wrap">\u00b7\u00a0<input class="sc-seq-input" type="number" min="0" step="1"'+
           ' value="'+_e(seq>0?seq:'')+'" data-action="inline-seq" data-id="'+a.id+'" title="Sequence"></span>';
        h+='</div>';
        h+='<div class="sc-card-acts">';
        if (!isDone&&a.loadId) {
            h+='<button class="sc-btn-icon sc-color-btn" data-action="open-color-picker" data-load-id="'+_e(a.loadId)+'" title="\uD83C\uDFA8 Shipment color">\uD83C\uDFA8</button>';
        }
        h+='<button class="sc-btn-icon" data-action="toggle-edit" data-id="'+a.id+'" title="Edit">\u270e</button>';
        h+='<button class="sc-btn-icon sc-btn-del" data-action="del-asgn" data-id="'+a.id+'" title="Delete">\u00d7</button>';
        h+='</div></div>';

        // ── Color swatch row (hidden until open) ──
        if (!isDone&&a.loadId) {
            h+='<div class="sc-color-picker-row" id="sc-cp-'+_e(a.loadId)+'" style="display:none">';
            SHIP_COLORS.forEach(function(c){
                var isSel=c===shipColor;
                h+='<button class="sc-color-swatch'+(isSel?' sc-color-swatch-sel':'')+'" data-action="apply-color"'+
                   ' data-load-id="'+_e(a.loadId)+'" data-color="'+_e(c)+'" style="background:'+c+'" title="'+c+'"></button>';
            });
            h+='<button class="sc-color-swatch sc-color-clear" data-action="apply-color" data-load-id="'+_e(a.loadId)+'" data-color="" title="Clear color">\u00d7</button>';
            h+='</div>';
        }

        // ── Line 2: Action badge | PRO# / NEED TO BUILD | ShipRef | Load type | DH ──
        h+='<div class="sc-cv-badges">';
        h+='<span class="sc-badge '+actCss+'">'+_e(label)+'</span>';
        if (pro) {
            if (lc) h+=' <span class="sc-chip" style="--lc:'+lc+'" title="PRO# (click to copy)" data-copyval="'+_e(pro)+'">'+_e(pro)+'</span>';
            else    h+=' <span class="sc-pro-txt" title="PRO#">'+_e(pro)+'</span>';
        } else {
            h+=' <span class="sc-ntb-badge" title="No PRO# — needs to be built">NEED TO BUILD</span>';
        }
        if (shipRef) h+=' <span class="sc-ship-ref" title="Shipment ref (click to copy)" data-copyval="'+_e(shipRef)+'">'+_e(shipRef)+'</span>';
        if (loadType) {
            var ltCss=LOAD_TYPE_CSS[loadType]||'sc-lt-other';
            h+=' <span class="sc-load-type-badge '+ltCss+'">'+_e(loadType)+'</span>';
        }
        if (dhMi>0) h+=' <span class="sc-dh-tag">'+dhMi+' mi</span>';
        h+='</div>';

        // ── Line 3: TMS/PU# IDs (selectable text) ──
        var ids=[];
        if (tmsId) ids.push('TMS: '+tmsId);
        if (puNum) ids.push('PU#: '+puNum);
        if (isBcat&&carrierName) ids.push('\u2022 '+carrierName);
        if (ids.length) h+='<div class="sc-load-ids sc-selectable">'+_e(ids.join(' \u00b7 '))+'</div>';

        // Leg progress (only when counts > default)
        if (a.loadId&&(pickCount>1||dropCount>1)) {
            var allA=_allAsgns();
            var puDone=allA.filter(function(x){return x.loadId===a.loadId&&x.actionType==='PICKUP';}).length;
            var deDone=allA.filter(function(x){return x.loadId===a.loadId&&(x.actionType==='DELIVERY'||x.actionType==='PICKUP_AND_DELIVER');}).length;
            h+='<div class="sc-leg-progress">PU '+puDone+'/'+pickCount+' \u00b7 DE '+deDone+'/'+dropCount+'</div>';
        }

        // ── Lines 4-5: Locations ──
        if (!isDE&&(puLoc||orig)) {
            h+='<div class="sc-route sc-route-pu">';
            if (puLoc) h+='<span class="sc-loc-name sc-selectable">'+_e(puLoc)+'</span> ';
            if (orig)  h+='<span class="sc-loc-city sc-selectable">'+_e(orig)+'</span>';
            h+='</div>';
        }
        if (!isPU&&(deLoc||dest)) {
            h+='<div class="sc-route sc-route-de">';
            h+='\u2192 ';
            if (deLoc) h+='<span class="sc-loc-name sc-selectable">'+_e(deLoc)+'</span> ';
            if (dest)  h+='<span class="sc-loc-city sc-selectable">'+_e(dest)+'</span>';
            h+='</div>';
        }

        // ── Line 6: Appt info ──
        var showPU=!isDE, showDE=!isPU;
        if (showPU||showDE) {
            h+='<div class="sc-appt-row">';
            if (showPU) {
                var puAT=(a.puApptType||'APPT');
                if (puAT==='FCFS') {
                    var puRange=[a.puFcfsStart,a.puFcfsEnd].filter(Boolean).join('\u2013');
                    h+='<span class="sc-appts sc-selectable">PU FCFS'+(puRange?' '+puRange:'')+'</span>';
                } else {
                    if (a.puAppt) { h+='<span class="sc-appts sc-selectable">PU '+_e(a.puAppt)+'</span><span class="sc-apst '+puCss+'">'+_e(puSt)+'</span>'; }
                    else          { h+='<span class="sc-apst-sm '+puCss+'">PU: '+_e(puSt)+'</span>'; }
                }
            }
            if (showDE) {
                var deAT=(a.deApptType||'APPT');
                if (deAT==='FCFS') {
                    var deRange=[a.deFcfsStart,a.deFcfsEnd].filter(Boolean).join('\u2013');
                    h+='<span class="sc-appts sc-selectable">DE FCFS'+(deRange?' '+deRange:'')+'</span>';
                } else {
                    if (a.deAppt) { h+='<span class="sc-appts sc-selectable">DE '+_e(a.deAppt)+'</span><span class="sc-apst '+deCss+'">'+_e(deSt)+'</span>'; }
                    else          { h+='<span class="sc-apst-sm '+deCss+'">DE: '+_e(deSt)+'</span>'; }
                }
            }
            h+='</div>';
        }

        // ── Line 7: Notes ──
        if (a.notes) { var n=a.notes; h+='<div class="sc-notes sc-selectable">'+_e(n.length>60?n.substring(0,60)+'\u2026':n)+'</div>'; }

        // ── Checkboxes — DELIVERY legs only (req 12) ──
        if (isDeliveryLeg) {
            if (isE2open) {
                h+='<div class="sc-e2open-row">';
                h+='<label class="sc-chk-lbl sc-e2open-lbl" title="Mark E2OPEN system closed">';
                h+='<input type="checkbox" class="sc-chk"'+(a.e2openClosed?' checked':'')+
                   ' data-action="toggle-chk" data-id="'+a.id+'" data-field="e2openClosed" data-propagate="1">';
                h+='<span>E2OPEN CLOSED</span></label>';
                h+='</div>';
            }
            h+='<div class="sc-done-row">';
            h+='<label class="sc-chk-lbl sc-done-lbl" title="Mark shipment complete">';
            h+='<input type="checkbox" class="sc-chk sc-done-chk"'+(isDone?' checked':'')+
               ' data-action="toggle-chk" data-id="'+a.id+'" data-field="isComplete" data-propagate="1">';
            h+='<span>'+(isDone?'\u2713 DONE':'DONE')+'</span></label>';
            h+='</div>';
        }

        h+='</div>'; // sc-card-view

        // ── Missing delivery warning (single per shipment) ──
        if (isMissingDel) {
            var needMore=(load.dropCount||1)-((function(){
                return _allAsgns().filter(function(x){return x.loadId===a.loadId&&(x.actionType==='DELIVERY'||x.actionType==='PICKUP_AND_DELIVER');}).length;
            })());
            h+='<div class="sc-missing-del-bar">';
            h+='<span class="sc-missing-del-badge">\u26a0 '+(needMore>1?needMore+' DELIVERIES NEEDED':'DELIVERY NOT ADDED')+'</span>';
            h+='<button class="sc-add-del-btn" data-action="show-delivery-form" data-id="'+a.id+'">\u271a Add Delivery</button>';
            h+='</div>';
            h+=_deliveryFormHTML(a);
        }

        h+=_editFormHTML(a);
        h+='</div>'; // sc-card
        return h;
    }

    // ── Edit form ─────────────────────────────────────────────────────────────
    function _editFormHTML(a) {
        var load=a.load||{};
        var puSt=a.puApptStatus||'NEED', deSt=a.deApptStatus||'NEED';
        var loadType=load.loadType||'';
        var isBcat=loadType==='BCAT BROKER';
        var actionType=a.actionType||'PICKUP';
        var isPU=actionType==='PICKUP', isDE=actionType==='DELIVERY';
        var puAT=(a.puApptType||'APPT'), deAT=(a.deApptType||'APPT');
        var h='<div class="sc-card-edit" style="display:none" data-edit-for="'+a.id+'">';
        h+='<div class="sc-ef-grid">';

        // Load Type | Picks · Drops
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Load Type'+_loadTypeSel('loadtype',loadType)+'</label>';
        h+='<div class="sc-ef-row2" style="gap:3px">';
        h+='<label class="sc-ef-lbl">Picks<input class="sc-inp" name="pickcount" type="number" min="1" value="'+_e(load.pickCount||1)+'"></label>';
        h+='<label class="sc-ef-lbl">Drops<input class="sc-inp" name="dropcount" type="number" min="1" value="'+_e(load.dropCount||1)+'"></label>';
        h+='</div>';
        h+='</div>';
        // Carrier name (conditional)
        h+='<div class="sc-carrier-row'+(isBcat?' sc-carrier-row--visible':'')+'">';
        h+='<label class="sc-ef-lbl sc-ef-full">Carrier Name<input class="sc-inp" name="carriername" value="'+_e(load.carrierName||'')+'" placeholder="Carrier company"></label>';
        h+='</div>';

        // PRO# | TMS ID
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" value="'+_e(load.alexeiId||'')+'" placeholder="PRO-10421"></label>';
        h+='<label class="sc-ef-lbl">TMS ID<input class="sc-inp" name="tms" value="'+_e(load.tmsId||'')+'" placeholder="TMS-8801"></label>';
        h+='</div>';
        h+='<label class="sc-ef-lbl">Pickup Number<input class="sc-inp" name="punum" value="'+_e(load.puNumber||'')+'" placeholder="PU-4421"></label>';
        // Action | Driver
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Action'+_actSel('action',actionType)+'</label>';
        h+='<label class="sc-ef-lbl">Driver'+_driverSel('driver',a.driverName||'')+'</label>';
        h+='</div>';

        // PU section (hidden for DELIVERY)
        h+='<div class="sc-ef-pu-section"'+(isDE?' style="display:none"':'')+' data-section="pu">';
        h+='<label class="sc-ef-lbl">PU Location Name<input class="sc-inp" name="puloc" value="'+_e(a.puLocationName||'')+'" placeholder="Walmart DC #6045"></label>';
        h+='<div class="sc-ef-row-zip">';
        h+='<label class="sc-ef-lbl sc-ef-zip">PU ZIP<input class="sc-inp" name="puzip" placeholder="60601" maxlength="5"></label>';
        h+='<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" value="'+_e(a.originCity||'')+'" placeholder="Chicago"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" value="'+_e(a.originState||'')+'" maxlength="2" placeholder="IL"></label>';
        h+='</div>';
        h+='<span class="sc-zip-warn sc-zip-warn-pu" style="display:none"></span>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PU Appt Type'+_apptTypeSel('puappttype',puAT)+'</label>';
        h+='<label class="sc-ef-lbl">PU Appt Status'+_apptSel('puApptStatus',puSt)+'</label>';
        h+='</div>';
        h+='<div data-appt-row="pu" data-for-type="APPT"'+(puAT!=='APPT'?' style="display:none"':'')+' style="'+(puAT!=='APPT'?'display:none':'')+'">';
        h+='<label class="sc-ef-lbl">PU Appt (HH:MM)<input class="sc-inp" type="time" name="puappt" value="'+_e(a.puAppt||'')+'"></label>';
        h+='</div>';
        h+='<div data-appt-row="pu" data-for-type="FCFS"'+(puAT!=='FCFS'?' style="display:none"':'')+' style="'+(puAT!=='FCFS'?'display:none':'')+'">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PU FCFS Start<input class="sc-inp" type="time" name="pufcfsstart" value="'+_e(a.puFcfsStart||'')+'"></label>';
        h+='<label class="sc-ef-lbl">PU FCFS End<input class="sc-inp" type="time" name="pufcfsend" value="'+_e(a.puFcfsEnd||'')+'"></label>';
        h+='</div></div>';
        h+='</div>'; // pu-section

        // DE section (hidden for PICKUP)
        h+='<div class="sc-ef-de-section"'+(isPU?' style="display:none"':'')+' data-section="de">';
        h+='<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="deloc" value="'+_e(a.deLocationName||'')+'" placeholder="Target RDC"></label>';
        h+='<div class="sc-ef-row-zip">';
        h+='<label class="sc-ef-lbl sc-ef-zip">DE ZIP<input class="sc-inp" name="dezip" placeholder="53202" maxlength="5"></label>';
        h+='<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" value="'+_e(a.destCity||'')+'" placeholder="Milwaukee"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" value="'+_e(a.destState||'')+'" maxlength="2" placeholder="WI"></label>';
        h+='</div>';
        h+='<span class="sc-zip-warn sc-zip-warn-de" style="display:none"></span>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE Appt Type'+_apptTypeSel('deappttype',deAT)+'</label>';
        h+='<label class="sc-ef-lbl">DE Appt Status'+_apptSel('deApptStatus',deSt)+'</label>';
        h+='</div>';
        h+='<div data-appt-row="de" data-for-type="APPT"'+(deAT!=='APPT'?' style="display:none"':'')+' style="'+(deAT!=='APPT'?'display:none':'')+'">';
        h+='<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="deappt" value="'+_e(a.deAppt||'')+'"></label>';
        h+='</div>';
        h+='<div data-appt-row="de" data-for-type="FCFS"'+(deAT!=='FCFS'?' style="display:none"':'')+' style="'+(deAT!=='FCFS'?'display:none':'')+'">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE FCFS Start<input class="sc-inp" type="time" name="defcfsstart" value="'+_e(a.deFcfsStart||'')+'"></label>';
        h+='<label class="sc-ef-lbl">DE FCFS End<input class="sc-inp" type="time" name="defcfsend" value="'+_e(a.deFcfsEnd||'')+'"></label>';
        h+='</div></div>';
        h+='</div>'; // de-section

        h+='<label class="sc-ef-lbl">Notes<input class="sc-inp" name="notes" value="'+_e(a.notes||'')+'" placeholder="Notes\u2026"></label>';
        h+='</div>'; // ef-grid
        h+='<div class="sc-ef-btns">';
        h+='<button class="sc-btn-cancel" data-action="cancel-edit" data-id="'+a.id+'">Cancel</button>';
        if (a.loadId) {
            h+='<button class="sc-btn-move" data-action="move-shipment" data-load-id="'+a.loadId+'" title="Move entire shipment (all legs) by N days">\u21c4 Move Shipment</button>';
        }
        h+='<button class="sc-btn-save" data-action="save-edit" data-id="'+a.id+'">Save</button>';
        h+='</div>';
        h+='</div>'; // sc-card-edit
        return h;
    }

    // ── Delivery creation form ─────────────────────────────────────────────────
    function _deliveryFormHTML(a) {
        var load=a.load||{};
        var delOrigCity=a.destCity||'', delOrigState=a.destState||'';
        var delDstCity=load.deCity||'', delDstState=load.deState||'';
        var delOrigLoc=a.deLocationName||'';      // pickup's destination = delivery's origin loc
        var delDestLoc=a.deLocationName||'';      // pre-fill DE location name from pickup context
        var defaultDate=_nextBizDay(a.date);
        var routeInfo='';
        var from=[delOrigCity,delOrigState].filter(Boolean).join(', ');
        var to=[delDstCity,delDstState].filter(Boolean).join(', ');
        if (from||to) routeInfo=(from||'?')+' \u2192 '+(to||'?');

        var h='<div class="sc-delivery-form" data-del-for="'+a.id+'" style="display:none">';
        h+='<div class="sc-del-form-hdr">';
        h+='<span class="sc-del-form-title">\u26a1 Add Delivery Leg</span>';
        if (load.alexeiId) h+='<span class="sc-chip" style="--lc:'+_lc(a.loadId||'')+'">'+_e(load.alexeiId)+'</span>';
        h+='</div>';
        if (routeInfo) h+='<div class="sc-del-route-info">'+_e(routeInfo)+'</div>';

        h+='<input type="hidden" name="del-loadid"   value="'+_e(a.loadId||'')+'">';
        h+='<input type="hidden" name="del-origcity" value="'+_e(delOrigCity)+'">';
        h+='<input type="hidden" name="del-origst"   value="'+_e(delOrigState)+'">';
        h+='<input type="hidden" name="del-dstcity"  value="'+_e(delDstCity)+'">';
        h+='<input type="hidden" name="del-dstst"    value="'+_e(delDstState)+'">';
        h+='<input type="hidden" name="del-origloc"  value="'+_e(delOrigLoc)+'">';

        h+='<div class="sc-ef-grid">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl sc-del-required-lbl">Delivery Date \u2736<input class="sc-inp" type="date" name="del-date" value="'+defaultDate+'" required></label>';
        h+='<label class="sc-ef-lbl">Driver'+_driverSel('del-driver','')+'</label>';
        h+='</div>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE Appt Type'+_apptTypeSel('del-deappttype','APPT')+'</label>';
        h+='<label class="sc-ef-lbl">DE Appt Status'+_apptSel('del-deApptStatus','NEED')+'</label>';
        h+='</div>';
        // APPT row
        h+='<div data-appt-row="del-de" data-for-type="APPT">';
        h+='<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="del-deappt"></label>';
        h+='</div>';
        // FCFS row
        h+='<div data-appt-row="del-de" data-for-type="FCFS" style="display:none">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE FCFS Start<input class="sc-inp" type="time" name="del-defcfsstart"></label>';
        h+='<label class="sc-ef-lbl">DE FCFS End<input class="sc-inp" type="time" name="del-defcfsend"></label>';
        h+='</div></div>';
        // DE Location Name — prefilled from pickup context
        h+='<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="del-deloc" value="'+_e(delDestLoc)+'" placeholder="Final delivery location\u2026"></label>';
        h+='<label class="sc-ef-lbl">Notes<input class="sc-inp" name="del-notes" value="'+_e(a.notes||'')+'" placeholder="Notes\u2026"></label>';
        h+='</div>';
        h+='<div class="sc-ef-btns">';
        h+='<button class="sc-btn-cancel" data-action="cancel-delivery-form" data-id="'+a.id+'">Cancel</button>';
        h+='<button class="sc-btn-save sc-btn-del-save" data-action="save-delivery" data-id="'+a.id+'">\u26a1 Save Delivery</button>';
        h+='</div>';
        h+='</div>';
        return h;
    }

    // ── Add form ──────────────────────────────────────────────────────────────
    function _addFormHTML(day) {
        var h='<div class="sc-add-form" data-add-day="'+day+'" style="display:none">';
        h+='<div class="sc-add-form-hdr">New Assignment</div>';
        h+='<div class="sc-ef-grid">';

        // Load Type | Picks · Drops
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Load Type'+_loadTypeSel('loadtype','')+'</label>';
        h+='<div class="sc-ef-row2" style="gap:3px">';
        h+='<label class="sc-ef-lbl">Picks<input class="sc-inp" name="pickcount" type="number" min="1" value="1"></label>';
        h+='<label class="sc-ef-lbl">Drops<input class="sc-inp" name="dropcount" type="number" min="1" value="1"></label>';
        h+='</div>';
        h+='</div>';
        // Carrier name (hidden by default)
        h+='<div class="sc-carrier-row">';
        h+='<label class="sc-ef-lbl sc-ef-full">Carrier Name<input class="sc-inp" name="carriername" placeholder="Carrier company"></label>';
        h+='</div>';

        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" placeholder="PRO-10421"></label>';
        h+='<label class="sc-ef-lbl">TMS ID<input class="sc-inp" name="tms" placeholder="TMS-8801"></label>';
        h+='</div>';
        h+='<label class="sc-ef-lbl">Pickup Number<input class="sc-inp" name="punum" placeholder="PU-4421"></label>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Action'+_actSel('action','PICKUP')+'</label>';
        h+='<label class="sc-ef-lbl">Driver'+_driverSel('driver','')+'</label>';
        h+='</div>';

        // PU section
        h+='<div class="sc-ef-pu-section" data-section="pu">';
        h+='<label class="sc-ef-lbl">PU Location Name<input class="sc-inp" name="puloc" placeholder="Walmart DC #6045"></label>';
        h+='<div class="sc-ef-row-zip">';
        h+='<label class="sc-ef-lbl sc-ef-zip">PU ZIP<input class="sc-inp" name="puzip" placeholder="60601" maxlength="5"></label>';
        h+='<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" placeholder="Chicago"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" maxlength="2" placeholder="IL"></label>';
        h+='</div>';
        h+='<span class="sc-zip-warn sc-zip-warn-pu" style="display:none"></span>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PU Appt Type'+_apptTypeSel('puappttype','APPT')+'</label>';
        h+='<label class="sc-ef-lbl">PU Appt Status'+_apptSel('puApptStatus','NEED')+'</label>';
        h+='</div>';
        h+='<div data-appt-row="pu" data-for-type="APPT">';
        h+='<label class="sc-ef-lbl">PU Appt (HH:MM)<input class="sc-inp" type="time" name="puappt"></label>';
        h+='</div>';
        h+='<div data-appt-row="pu" data-for-type="FCFS" style="display:none">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PU FCFS Start<input class="sc-inp" type="time" name="pufcfsstart"></label>';
        h+='<label class="sc-ef-lbl">PU FCFS End<input class="sc-inp" type="time" name="pufcfsend"></label>';
        h+='</div></div>';
        h+='</div>'; // pu-section

        // DE section
        h+='<div class="sc-ef-de-section" data-section="de">';
        h+='<label class="sc-ef-lbl">DE Location Name<input class="sc-inp" name="deloc" placeholder="Target RDC"></label>';
        h+='<div class="sc-ef-row-zip">';
        h+='<label class="sc-ef-lbl sc-ef-zip">DE ZIP<input class="sc-inp" name="dezip" placeholder="53202" maxlength="5"></label>';
        h+='<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" placeholder="Milwaukee"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" maxlength="2" placeholder="WI"></label>';
        h+='</div>';
        h+='<span class="sc-zip-warn sc-zip-warn-de" style="display:none"></span>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE Appt Type'+_apptTypeSel('deappttype','APPT')+'</label>';
        h+='<label class="sc-ef-lbl">DE Appt Status'+_apptSel('deApptStatus','NEED')+'</label>';
        h+='</div>';
        h+='<div data-appt-row="de" data-for-type="APPT">';
        h+='<label class="sc-ef-lbl">DE Appt (HH:MM)<input class="sc-inp" type="time" name="deappt"></label>';
        h+='</div>';
        h+='<div data-appt-row="de" data-for-type="FCFS" style="display:none">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">DE FCFS Start<input class="sc-inp" type="time" name="defcfsstart"></label>';
        h+='<label class="sc-ef-lbl">DE FCFS End<input class="sc-inp" type="time" name="defcfsend"></label>';
        h+='</div></div>';
        h+='</div>'; // de-section

        h+='<label class="sc-ef-lbl">Notes<input class="sc-inp" name="notes" placeholder="Notes\u2026"></label>';
        h+='</div>'; // ef-grid
        h+='<div class="sc-ef-btns">';
        h+='<button class="sc-btn-cancel" data-action="cancel-add" data-day="'+day+'">Cancel</button>';
        h+='<button class="sc-btn-save" data-action="save-new" data-day="'+day+'">Save</button>';
        h+='</div>';
        h+='</div>';
        return h;
    }

    // ── Select helpers ────────────────────────────────────────────────────────
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
    function _apptTypeSel(name, val) {
        var s='<select class="sc-inp" name="'+name+'">';
        s+='<option value="APPT"'+(val==='APPT'?' selected':'')+'>APPT</option>';
        s+='<option value="FCFS"'+(val==='FCFS'?' selected':'')+'>FCFS</option>';
        return s+'</select>';
    }
    function _loadTypeSel(name, val) {
        var types=['','E2OPEN','BCAT BROKER','IVAN BROKER','IVAN CUSTOMER'];
        var labels=['\u2014 None \u2014','E2OPEN','BCAT BROKER','IVAN BROKER','IVAN CUSTOMER'];
        var s='<select class="sc-inp" name="'+name+'">';
        types.forEach(function(t,i){ s+='<option value="'+t+'"'+(val===t?' selected':'')+'>'+labels[i]+'</option>'; });
        return s+'</select>';
    }
    function _driverSel(name, val) {
        var drvs=_drivers();
        var s='<select class="sc-inp" name="'+name+'">';
        s+='<option value=""'+(val===''?' selected':'')+'>— Unassigned —</option>';
        drvs.forEach(function(d){ s+='<option value="'+_e(d)+'"'+(val===d?' selected':'')+'>'+_e(d)+'</option>'; });
        return s+'</select>';
    }
    function _driverSelInline(val, aId) {
        var drvs=_drivers();
        var s='<select class="sc-drv-inline-sel" data-action="inline-driver" data-id="'+aId+'">';
        s+='<option value=""'+(val===''?' selected':'')+'>— Unassigned —</option>';
        drvs.forEach(function(d){ s+='<option value="'+_e(d)+'"'+(val===d?' selected':'')+'>'+_e(d)+'</option>'; });
        return s+'</select>';
    }

    // ── Form visibility helpers ───────────────────────────────────────────────
    function _updateActionSections(form, action) {
        var puSec=form.querySelector('.sc-ef-pu-section');
        var deSec=form.querySelector('.sc-ef-de-section');
        if (puSec) puSec.style.display=(action==='DELIVERY')?'none':'';
        if (deSec) deSec.style.display=(action==='PICKUP')?'none':'';
    }
    function _updateCarrierRow(form, loadType) {
        var row=form.querySelector('.sc-carrier-row'); if (!row) return;
        if (loadType==='BCAT BROKER') row.classList.add('sc-carrier-row--visible');
        else row.classList.remove('sc-carrier-row--visible');
    }
    function _updateApptTypeRows(form, section, val) {
        // section = 'pu', 'de', or 'del-de'
        var apptRow=form.querySelector('[data-appt-row="'+section+'"][data-for-type="APPT"]');
        var fcfsRow=form.querySelector('[data-appt-row="'+section+'"][data-for-type="FCFS"]');
        if (apptRow) apptRow.style.display=(val==='APPT')?'':'none';
        if (fcfsRow) fcfsRow.style.display=(val==='FCFS')?'':'none';
    }

    // ── Event binding ─────────────────────────────────────────────────────────
    function _bind(el) {
        // Click
        el.addEventListener('click', function(e) {
            // Copy-on-click for key ID chips
            var copyEl=e.target.closest('[data-copyval]');
            if (copyEl && !e.target.closest('button,input,select,a')) {
                var val=copyEl.dataset.copyval;
                if (val) {
                    navigator.clipboard && navigator.clipboard.writeText(val).catch(function(){});
                    copyEl.title='Copied!';
                    setTimeout(function(){ copyEl.title=copyEl.dataset.copytitle||''; },1500);
                }
                // Don't return — let other handlers run too
            }

            var b=e.target.closest('[data-action]'); if (!b) return;
            switch (b.dataset.action) {
                case 'prev-week':            _loadMultiWeek(_addDays(_viewStart,-7)); break;
                case 'next-week':            _loadMultiWeek(_addDays(_viewStart, 7)); break;
                case 'today-week':           _loadMultiWeek(_mondayOf(new Date()));   break;
                case 'view-calendar':        _viewMode='calendar'; _reload(); break;
                case 'view-ddv':             _viewMode='ddv'; if(!_ddvDate)_ddvDate=_iso(new Date()); _render(); break;
                case 'toggle-edit':          _toggleEdit(b.dataset.id);               break;
                case 'cancel-edit':          _cancelEdit(b.dataset.id);               break;
                case 'save-edit':            _saveEdit(b.dataset.id);                 break;
                case 'del-asgn':             _delAsgn(b.dataset.id);                  break;
                case 'show-add':             _showAdd(b.dataset.day, b.dataset.driver||''); break;
                case 'cancel-add':           _cancelAdd(b.dataset.day);               break;
                case 'save-new':             _saveNew(b.dataset.day);                 break;
                case 'show-delivery-form':   _showDeliveryForm(b.dataset.id);         break;
                case 'cancel-delivery-form': _cancelDeliveryForm(b.dataset.id);       break;
                case 'save-delivery':        _saveDelivery(b.dataset.id);             break;
                case 'toggle-audit':         _toggleAudit();                          break;
                case 'revert-audit':         _revertAudit(parseInt(b.dataset.logId,10)); break;
                case 'open-color-picker':    _openColorPicker(b.dataset.loadId); break;
                case 'apply-color':          _applyShipmentColor(b.dataset.loadId, b.dataset.color); break;
                case 'move-shipment':        _promptMoveShipment(b.dataset.loadId); break;
            }
        });

        // Double-click to edit (guards against inline controls)
        el.addEventListener('dblclick', function(e) {
            if (e.target.closest('button,input,select,a,.sc-missing-del-bar,.sc-delivery-form,.sc-card-edit')) return;
            var card=e.target.closest('.sc-card');
            if (!card||!card.dataset.id) return;
            _toggleEdit(card.dataset.id);
            e.preventDefault();
        });

        // Change: checkboxes, inline driver, form visibility
        el.addEventListener('change', function(e) {
            var t=e.target;
            if (t.dataset.action==='toggle-chk') {
                _toggleChk(t.dataset.id, t.dataset.field, t.checked);
                return;
            }
            if (t.dataset.action==='inline-driver') {
                _saveInlineDriver(t.dataset.id, t.value);
                return;
            }
            var form=t.closest('.sc-card-edit,.sc-add-form,.sc-delivery-form');
            if (!form) return;
            if (t.name==='action')       { _updateActionSections(form, t.value); return; }
            if (t.name==='loadtype')     { _updateCarrierRow(form, t.value); return; }
            if (t.name==='puappttype')   { _updateApptTypeRows(form, 'pu', t.value); return; }
            if (t.name==='deappttype')   { _updateApptTypeRows(form, 'de', t.value); return; }
            if (t.name==='del-deappttype') { _updateApptTypeRows(form, 'del-de', t.value); return; }
        });

        // Inline seq: blur saves, Enter triggers blur
        el.addEventListener('keydown', function(e) {
            if (e.target.dataset.action==='inline-seq' && (e.key==='Enter'||e.key==='Tab')) {
                e.target.blur();
                if (e.key==='Enter') e.preventDefault();
            }
        });
        el.addEventListener('focusout', function(e) {
            if (e.target.dataset.action==='inline-seq') _saveSeq(e.target);
        });

        // ZIP lookup
        el.addEventListener('input', function(e) {
            var t=e.target;
            if ((t.name==='puzip'||t.name==='dezip') && t.value.length===5) _lookupZipGeneric(t);
        });
    }

    // ── Inline field savers ───────────────────────────────────────────────────
    function _saveInlineDriver(id, driverName) {
        var a=_allAsgns().find(function(x){return x.id===id;});
        if (a) a.driverName=driverName; // optimistic local
        _api('PUT','/api/ivan/schedule/assignments/'+id,{driverName:driverName})
            .then(function(){ _reload(); })
            .catch(function(err){ alert('Save failed: '+err.message); _render(); });
    }
    function _saveSeq(input) {
        var id=input.dataset.id;
        var raw=input.value.trim();
        var num=raw===''?0:parseInt(raw,10);
        if (isNaN(num)) num=0;
        var a=_allAsgns().find(function(x){return x.id===id;}); if (!a) return;
        var prev=a.sequenceNumber||0;
        if (prev===num) return; // no change
        a.sequenceNumber=num; // optimistic
        _api('PUT','/api/ivan/schedule/assignments/'+id,{sequenceNumber:num})
            .then(function(){ _reload(); })
            .catch(function(err){ a.sequenceNumber=prev; alert('Save failed: '+err.message); _render(); });
    }

    // ── Card edit toggle ──────────────────────────────────────────────────────
    function _toggleEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef=card.querySelector('.sc-card-edit'); if (!ef) return;
        var open=ef.style.display!=='none'&&ef.style.display!=='';
        ef.style.display=open?'none':'block';
        if (!open) {
            ef.scrollIntoView({behavior:'smooth',block:'nearest'});
            var fi=ef.querySelector('input,select'); if (fi) fi.focus();
        }
    }
    function _cancelEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef=card.querySelector('.sc-card-edit'); if (ef) ef.style.display='none';
    }

    // ── Save edit (robust: fallback date from DOM) ────────────────────────────
    function _saveEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if (!card) return;
        var ef=card.querySelector('.sc-card-edit'); if (!ef) return;
        var g=function(n){ var i=ef.querySelector('[name="'+n+'"]'); return i?i.value.trim():''; };
        var saveBtn=ef.querySelector('[data-action="save-edit"]');
        if (saveBtn) { saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        // Get assignment data; fall back to DOM date if not in weekData yet
        var a=_allAsgns().find(function(x){ return x.id===id; });
        var dayDate='';
        if (a) {
            dayDate=a.date;
        } else {
            var dayCol=card.closest('[data-day]');
            dayDate=dayCol?dayCol.dataset.day:'';
            a={id:id, date:dayDate, loadId:null, actionType:g('action')||'PICKUP'};
        }

        var loadBody={
            alexeiId:    g('pro'),    tmsId:    g('tms'),    puNumber: g('punum'),
            puCity:      g('origcity'), puState:g('origst').toUpperCase(),
            deCity:      g('dstcity'),  deState:g('dstst').toUpperCase(),
            loadType:    g('loadtype'),
            carrierName: g('carriername'),
            pickCount:   parseInt(g('pickcount'),10)||1,
            dropCount:   parseInt(g('dropcount'),10)||1,
        };
        var asgnBody={
            date:dayDate, weekStart:_mondayOf(new Date(dayDate+'T00:00:00')),
            driverName:    g('driver'),
            actionType:    g('action')||a.actionType,
            originCity:    g('origcity'), originState:g('origst').toUpperCase(),
            destCity:      g('dstcity'),  destState:  g('dstst').toUpperCase(),
            puAppt:        g('puappt'),   deAppt:     g('deappt'),
            puLocationName:g('puloc'),    deLocationName:g('deloc'),
            puApptStatus:  g('puApptStatus'),
            deApptStatus:  g('deApptStatus'),
            puApptType:    g('puappttype')||'APPT',
            puFcfsStart:   g('pufcfsstart'),
            puFcfsEnd:     g('pufcfsend'),
            deApptType:    g('deappttype')||'APPT',
            deFcfsStart:   g('defcfsstart'),
            deFcfsEnd:     g('defcfsend'),
            notes:         g('notes'),
        };

        var loadP;
        if (a.loadId) {
            loadP=_api('PUT','/api/ivan/loads/'+a.loadId,loadBody).then(function(){ return a.loadId; });
        } else if (g('pro')||g('tms')||g('punum')||g('origcity')||g('dstcity')) {
            loadP=_api('POST','/api/ivan/loads',loadBody).then(function(r){ return r.id; });
        } else {
            loadP=Promise.resolve(null);
        }
        loadP.then(function(lid){
            if (lid) asgnBody.loadId=lid;
            return _api('PUT','/api/ivan/schedule/assignments/'+id,asgnBody);
        }).then(function(){ _reload(); })
          .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Add form ──────────────────────────────────────────────────────────────
    function _showAdd(day, driver) {
        document.querySelectorAll('.sc-add-form').forEach(function(f){ if(f.dataset.addDay!==day) f.style.display='none'; });
        var form=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (!form) return;
        form.querySelectorAll('input[type!=hidden]').forEach(function(i){ if(i.type!=='number') i.value=''; });
        var actEl=form.querySelector('[name="action"]'); if(actEl) actEl.value='PICKUP';
        var puEl=form.querySelector('[name="puApptStatus"]'); if(puEl) puEl.value='NEED';
        var deEl=form.querySelector('[name="deApptStatus"]'); if(deEl) deEl.value='NEED';
        var ltEl=form.querySelector('[name="loadtype"]'); if(ltEl) ltEl.value='';
        var piEl=form.querySelector('[name="pickcount"]'); if(piEl) piEl.value=1;
        var drEl=form.querySelector('[name="dropcount"]'); if(drEl) drEl.value=1;
        var drvSel=form.querySelector('[name="driver"]'); if (drvSel) drvSel.value=driver||'';
        // Reset visibility
        _updateActionSections(form,'PICKUP');
        _updateCarrierRow(form,'');
        form.style.display='block';
        setTimeout(function(){ form.scrollIntoView({behavior:'smooth',block:'nearest'}); },50);
        setTimeout(function(){ var fi=form.querySelector('input'); if(fi) fi.focus(); },80);
    }
    function _cancelAdd(day) {
        var f=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (f) f.style.display='none';
    }
    function _saveNew(day) {
        var form=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if (!form) return;
        var g=function(n){ var i=form.querySelector('[name="'+n+'"]'); return i?i.value.trim():''; };
        var saveBtn=form.querySelector('[data-action="save-new"]');
        if (saveBtn) { saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        var driver=g('driver');
        var proNum=g('pro'), origcity=g('origcity'), dstcity=g('dstcity');
        var loadBody={
            alexeiId:    proNum,       tmsId:    g('tms'),    puNumber: g('punum'),
            puCity:      origcity,     puState:  g('origst').toUpperCase(),
            deCity:      dstcity,      deState:  g('dstst').toUpperCase(),
            loadType:    g('loadtype'),
            carrierName: g('carriername'),
            pickCount:   parseInt(g('pickcount'),10)||1,
            dropCount:   parseInt(g('dropcount'),10)||1,
        };
        var asgnBody={
            date:          day,
            weekStart:     _mondayOf(new Date(day+'T00:00:00')),
            driverName:    driver,
            sequenceNumber:_nextSeq(day, driver),
            actionType:    g('action')||'PICKUP',
            originCity:    origcity, originState:g('origst').toUpperCase(),
            destCity:      dstcity,  destState:  g('dstst').toUpperCase(),
            puAppt:        g('puappt'),    deAppt:    g('deappt'),
            puLocationName:g('puloc'),     deLocationName:g('deloc'),
            puApptStatus:  g('puApptStatus')||'NEED',
            deApptStatus:  g('deApptStatus')||'NEED',
            puApptType:    g('puappttype')||'APPT',
            puFcfsStart:   g('pufcfsstart'),
            puFcfsEnd:     g('pufcfsend'),
            deApptType:    g('deappttype')||'APPT',
            deFcfsStart:   g('defcfsstart'),
            deFcfsEnd:     g('defcfsend'),
            notes:         g('notes'),
        };

        var matchedLoad=proNum?_allLoads().find(function(l){ return l.alexeiId===proNum; }):null;
        var loadP;
        if (matchedLoad) {
            asgnBody.loadId=matchedLoad.id; loadP=Promise.resolve(matchedLoad.id);
        } else if (proNum||g('tms')||g('punum')||origcity||dstcity) {
            loadP=_api('POST','/api/ivan/loads',loadBody).then(function(r){ asgnBody.loadId=r.id; return r.id; });
        } else {
            loadP=Promise.resolve(null);
        }
        loadP.then(function(){ return _api('POST','/api/ivan/schedule/assignments',asgnBody); })
             .then(function(){ _reload(); })
             .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Delete ────────────────────────────────────────────────────────────────
    function _delAsgn(id) {
        if (!confirm('Delete this assignment?')) return;
        _api('DELETE','/api/ivan/schedule/assignments/'+id)
            .then(function(){ _reload(); })
            .catch(function(err){ alert('Delete failed: '+err.message); });
    }

    // ── Delivery form ─────────────────────────────────────────────────────────
    function _showDeliveryForm(id) {
        document.querySelectorAll('.sc-delivery-form').forEach(function(f){ if(f.dataset.delFor!==id) f.style.display='none'; });
        var form=document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]'); if (!form) return;
        form.style.display='block';
        setTimeout(function(){
            form.scrollIntoView({behavior:'smooth',block:'nearest'});
            var di=form.querySelector('[name="del-date"]'); if(di) di.focus();
        },60);
    }
    function _cancelDeliveryForm(id) {
        var form=document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]');
        if (form) form.style.display='none';
    }
    function _saveDelivery(id) {
        var form=document.querySelector('.sc-delivery-form[data-del-for="'+id+'"]'); if (!form) return;
        var g=function(n){ var i=form.querySelector('[name="'+n+'"]'); return i?i.value.trim():''; };
        var dateVal=g('del-date');
        if (!dateVal) { var di=form.querySelector('[name="del-date"]'); if(di){di.focus();di.classList.add('sc-inp-error');} return; }
        var saveBtn=form.querySelector('[data-action="save-delivery"]');
        if (saveBtn) { saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }
        var pickupA=_allAsgns().find(function(x){ return x.id===id; }); if (!pickupA) return;
        var driver=g('del-driver');
        var loadId=g('del-loadid')||pickupA.loadId||null;
        var deAT=g('del-deappttype')||'APPT';
        var asgnBody={
            date:          dateVal,
            weekStart:     _mondayOf(new Date(dateVal+'T00:00:00')),
            loadId:        loadId,
            driverName:    driver,
            sequenceNumber:_nextSeq(dateVal, driver),
            actionType:    'DELIVERY',
            originCity:    g('del-origcity'), originState:g('del-origst').toUpperCase(),
            destCity:      g('del-dstcity'),  destState:  g('del-dstst').toUpperCase(),
            puLocationName:g('del-origloc'),  deLocationName:g('del-deloc'),
            puAppt:'', deAppt:(deAT==='APPT'?g('del-deappt'):''),
            puApptStatus:'NEED', deApptStatus:g('del-deApptStatus')||'NEED',
            deApptType:  deAT,
            deFcfsStart: deAT==='FCFS'?g('del-defcfsstart'):'',
            deFcfsEnd:   deAT==='FCFS'?g('del-defcfsend'):'',
            notes:g('del-notes'),
        };
        // Optimistically clear missing del indicator to avoid flash
        if (loadId) delete _missingDel[loadId];
        _api('POST','/api/ivan/schedule/assignments',asgnBody)
            .then(function(){ _reload(); })
            .catch(function(err){
                if (loadId) _computeMissingDel(); // restore
                alert('Save failed: '+err.message);
                if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='\u26a1 Save Delivery';}
            });
    }

    // ── DONE / checkbox toggle — propagates to all legs of same loadId ───────
    function _toggleChk(id, field, checked) {
        var a=_allAsgns().find(function(x){ return x.id===id; }); if (!a) return;
        var loadId=a.loadId||null;

        // Build list of assignments to update: this one + all sibling legs if propagate
        var targets=[a];
        if (loadId) {
            _allAsgns().forEach(function(x){
                if (x.id!==id && x.loadId===loadId) targets.push(x);
            });
        }

        var prevValues={};
        targets.forEach(function(t){ prevValues[t.id]=t[field]; t[field]=checked; });

        // Optimistic UI update for all cards
        targets.forEach(function(t){
            var card=document.querySelector('.sc-card[data-id="'+t.id+'"]');
            if (!card) return;
            card.classList.toggle('sc-card-done', _done(t));
            if (field==='isComplete') {
                var sp=card.querySelector('.sc-done-lbl span');
                if (sp) sp.textContent=checked?'\u2713 DONE':'DONE';
            }
        });

        var patch={}; patch[field]=checked;
        var promises=targets.map(function(t){
            return _api('PUT','/api/ivan/schedule/assignments/'+t.id,patch);
        });
        Promise.all(promises).catch(function(err){
            targets.forEach(function(t){ t[field]=prevValues[t.id]; });
            alert('Save failed: '+err.message);
            _render();
        });
    }

    // ── Shipment color picker ─────────────────────────────────────────────────
    function _openColorPicker(loadId) {
        // Toggle color picker row for this loadId
        document.querySelectorAll('.sc-color-picker-row').forEach(function(r){
            r.style.display=(r.id==='sc-cp-'+loadId && r.style.display==='none')?'flex':'none';
        });
    }
    function _applyShipmentColor(loadId, color) {
        if (!loadId) return;
        // Optimistic update on all cards for this loadId
        var all=_allAsgns();
        all.forEach(function(a){
            if (a.loadId===loadId && a.load) a.load.shipmentColor=color;
        });
        // Update all loads in weekData
        Object.keys(_weekData).forEach(function(w){
            (_weekData[w].loads||[]).forEach(function(l){ if(l.id===loadId) l.shipmentColor=color; });
        });
        _api('PUT','/api/ivan/loads/'+loadId,{shipmentColor:color})
            .then(function(){ _render(); })
            .catch(function(err){ alert('Color save failed: '+err.message); _render(); });
    }

    // ── Move shipment as a unit ───────────────────────────────────────────────
    function _promptMoveShipment(loadId) {
        if (!loadId) return;
        var raw=prompt('Move all legs by how many days? (negative = earlier, positive = later)');
        if (raw===null||raw==='') return;
        var n=parseInt(raw,10);
        if (isNaN(n)||n===0) { alert('Enter a non-zero integer.'); return; }
        _api('POST','/api/ivan/schedule/shipments/'+loadId+'/move',{offsetDays:n})
            .then(function(r){ _reload(); })
            .catch(function(err){ alert('Move failed: '+err.message); });
    }

    // ── Audit panel (fixed overlay) ───────────────────────────────────────────
    function _getAuditPanel() {
        _ensureAuditOverlay();
        return document.getElementById('sc-audit-overlay');
    }
    function _toggleAudit() {
        _ensureAuditOverlay();
        _auditOpen=!_auditOpen;
        var panel=_getAuditPanel();
        if (panel) panel.style.display=_auditOpen?'flex':'none';
        // Toggle button active state (there may be two: nav + DDV nav)
        document.querySelectorAll('[data-action="toggle-audit"]').forEach(function(btn){
            btn.classList.toggle('sc-audit-toggle-active', _auditOpen);
        });
        if (_auditOpen) _loadAudit();
    }
    function _loadAudit() {
        var panel=_getAuditPanel();
        if (panel) panel.innerHTML='<div class="sc-audit-overlay-inner"><div class="sc-audit-hdr">'+
            '<span style="color:#e2e8f0;font-weight:700;font-size:13px;">Recent Changes</span>'+
            '<button class="sc-nav-btn" onclick="document.getElementById(\'sc-audit-overlay\').style.display=\'none\'; IvanScheduleApp&&(IvanScheduleApp._auditClose&&IvanScheduleApp._auditClose());" style="margin-left:auto">Close \u00d7</button>'+
            '</div><div class="sc-audit-loading" style="color:#94a3b8;padding:24px;text-align:center">Loading audit log\u2026</div></div>';
        _api('GET','/api/ivan/schedule/audit?limit=100')
            .then(function(data){ _auditData=data; _renderAuditPanel(); })
            .catch(function(err){
                var p=_getAuditPanel();
                if (p) p.innerHTML='<div class="sc-audit-overlay-inner">'+
                    '<div class="sc-audit-hdr"><span style="color:#e2e8f0;font-weight:700">Audit Log</span>'+
                    '<button class="sc-nav-btn" onclick="document.getElementById(\'sc-audit-overlay\').style.display=\'none\'">Close \u00d7</button></div>'+
                    '<div style="color:#f87171;padding:20px;font-size:12px">Failed to load: '+_e(err.message)+'</div></div>';
            });
    }
    function _renderAuditPanel() {
        var panel=_getAuditPanel(); if (!panel) return;
        var h='<div class="sc-audit-overlay-inner">';
        h+='<div class="sc-audit-hdr"><span style="color:#e2e8f0;font-weight:700;font-size:13px">Recent Changes ('+_auditData.length+')</span>';
        h+='<button class="sc-nav-btn" data-action="toggle-audit" style="margin-left:auto">Close \u00d7</button></div>';
        if (!_auditData.length) {
            h+='<div style="color:#64748b;padding:24px;text-align:center;font-size:12px">No changes recorded yet.</div>';
        } else {
            h+='<div class="sc-audit-list">';
            _auditData.forEach(function(log) {
                var actCls='sc-audit-act-'+log.action;
                h+='<div class="sc-audit-row'+(log.reverted?' sc-audit-reverted':'')+'">';
                h+='<div class="sc-audit-meta">';
                h+='<span class="sc-audit-time">'+_e(_relTime(log.createdAt))+'</span>';
                h+='<span class="sc-audit-badge '+actCls+'">'+_e(log.action)+'</span>';
                h+='<span class="sc-audit-user" title="'+_e(log.userEmail||'')+'">'+_e(log.userName||log.userEmail||'system')+'</span>';
                h+='</div>';
                h+='<div class="sc-audit-summary" style="color:#cbd5e1">'+_e(log.summary||log.entityId)+'</div>';
                // Field-level diff
                var diffHtml=_auditDiff(log);
                if (diffHtml) h+='<div class="sc-audit-diff">'+diffHtml+'</div>';
                if (!log.reverted&&log.action!=='revert') {
                    h+='<button class="sc-audit-revert-btn" data-action="revert-audit" data-log-id="'+log.id+'">\u21a9 Revert</button>';
                } else if (log.reverted) {
                    h+='<span class="sc-audit-reverted-tag">reverted</span>';
                }
                h+='</div>';
            });
            h+='</div>';
        }
        h+='</div>';
        panel.innerHTML=h;
        // Re-bind click for revert buttons inside overlay
        panel.querySelectorAll('[data-action="revert-audit"]').forEach(function(btn){
            btn.addEventListener('click', function(){ _revertAudit(parseInt(btn.dataset.logId,10)); });
        });
        panel.querySelectorAll('[data-action="toggle-audit"]').forEach(function(btn){
            btn.addEventListener('click', function(){ _toggleAudit(); });
        });
    }
    function _auditDiff(log) {
        // Parse before/after JSON and show changed fields
        var before={}, after={};
        try { before=JSON.parse(log.beforeJson||'{}'); } catch(e){}
        try { after =JSON.parse(log.afterJson||'{}'); } catch(e){}
        var SKIP=['updatedAt','createdAt','load','completedAt'];
        var rows=[];
        var keys=Object.keys(after).concat(Object.keys(before));
        var seen={};
        keys.forEach(function(k){
            if (seen[k]||SKIP.indexOf(k)>=0) return;
            seen[k]=1;
            var bv=before[k], av=after[k];
            if (JSON.stringify(bv)===JSON.stringify(av)) return;
            var bStr=bv===undefined?'—':String(bv===''?'(empty)':bv);
            var aStr=av===undefined?'—':String(av===''?'(empty)':av);
            rows.push('<span class="sc-diff-field">'+_e(k)+'</span>: '+
                '<span class="sc-diff-before">'+_e(bStr.length>30?bStr.substring(0,30)+'\u2026':bStr)+'</span>'+
                ' \u2192 <span class="sc-diff-after">'+_e(aStr.length>30?aStr.substring(0,30)+'\u2026':aStr)+'</span>');
        });
        return rows.slice(0,4).join('<br>');
    }
    function _revertAudit(logId) {
        if (!confirm('Revert this change? The record will be restored to its previous state.\nA new audit entry will be created for the revert.')) return;
        _api('POST','/api/ivan/schedule/audit/'+logId+'/revert')
            .then(function(){ _reload(); _loadAudit(); })
            .catch(function(err){ alert('Revert failed: '+err.message); });
    }

    // ── Public ────────────────────────────────────────────────────────────────
    function mountSchedule(containerId) {
        _cid=containerId;
        _loadMultiWeek(_mondayOf(new Date()));
    }
    return { mountSchedule: mountSchedule };
}());
