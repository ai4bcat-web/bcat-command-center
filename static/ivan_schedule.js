/**
 * ivan_schedule.js — Calendar-style Dispatch Board for Ivan Cartage
 * IvanScheduleApp.mountSchedule(containerId)
 *
 * Layout: 5-column weekly calendar (Mon–Fri)
 * Each column: driver sections → assignment cards with inline edit
 * Driver color: deterministic hash of driver name (8-color palette)
 * Load chip: deterministic hash of loadId, shows PRO# badge
 */
var IvanScheduleApp = (function () {
    'use strict';

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

    // 8 driver colors — border, dark bg tint, text
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

    // 10 load chip colors
    var LOAD_COLORS = [
        '#38bdf8', '#fbbf24', '#34d399', '#f87171', '#c084fc',
        '#22d3ee', '#fb923c', '#a3e635', '#f472b6', '#818cf8',
    ];

    // ── State ─────────────────────────────────────────────────────────────────
    var _cid       = null;
    var _weekStart = null;
    var _asgns     = [];
    var _loads     = [];

    // ── Fetch / CSRF ──────────────────────────────────────────────────────────
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
    function _weekDays() { return [0,1,2,3,4].map(function(i){ return _addDays(_weekStart,i); }); }
    function _fmtWeek() {
        var d = new Date(_weekStart + 'T00:00:00');
        var e = new Date(_weekStart + 'T00:00:00'); e.setDate(e.getDate() + 6);
        var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return 'Week of ' + M[d.getMonth()] + ' ' + d.getDate() +
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
        var k = ((city||'') + ' ' + (state||'')).toLowerCase().trim().replace(/\s+/g,' ');
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
            if (i===sorted.length-1 && dest) retDH=_mi(_hav(dest,BASE));
            return {toDH:toDH,retDH:retDH};
        });
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    function _done(a) {
        return !!(a.dispatched && a.pickedUp && a.delivered &&
                  a.paperworkReceived && a.paperworkReviewed && a.invoicingReady);
    }
    function _e(s) {
        return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function _hash(str) {
        var h=0; for(var i=0;i<str.length;i++) h=(h*31+str.charCodeAt(i))&0xffff; return h;
    }
    function _dc(name)  { return DRIVER_COLORS[_hash((name||'').toLowerCase()) % DRIVER_COLORS.length]; }
    function _lc(id)    { return LOAD_COLORS[_hash(id||'') % LOAD_COLORS.length]; }
    function _drivers() {
        var seen={},out=[];
        _asgns.forEach(function(a){ var d=(a.driverName||'').trim(); if(d&&!seen[d]){seen[d]=1;out.push(d);} });
        return out.sort();
    }
    function _nextSeq(day, driver) {
        return _asgns.filter(function(a){
            return a.date===day && (a.driverName||'').trim()===(driver||'').trim();
        }).length + 1;
    }

    // ── Load data ─────────────────────────────────────────────────────────────
    function _load(week) {
        var el=document.getElementById(_cid);
        if(el) el.innerHTML='<div class="sc-loading">Loading schedule\u2026</div>';
        _api('GET','/api/ivan/schedule?weekStart='+week).then(function(data){
            _asgns  = Array.isArray(data) ? data : (data.assignments||[]);
            _loads  = Array.isArray(data) ? [] : (data.loads||[]);
            _weekStart = week;
            _render();
        }).catch(function(err){
            var el2=document.getElementById(_cid);
            if(el2) el2.innerHTML='<div class="sc-error">Failed to load: '+_e(err.message)+'</div>';
        });
    }

    // ── Render ────────────────────────────────────────────────────────────────
    function _render() {
        var el=document.getElementById(_cid); if(!el) return;
        var today=_iso(new Date()), days=_weekDays(), knownDrvs=_drivers();
        var html='<div class="sc-board">'+_navHTML();
        html+='<datalist id="sc-drvs-dl">';
        knownDrvs.forEach(function(d){ html+='<option value="'+_e(d)+'">'; });
        html+='</datalist>';
        html+='<div class="sc-calendar">';
        days.forEach(function(day){
            var isToday=day===today;
            var dayA=_asgns.filter(function(a){ return a.date===day; });
            html+=_colHTML(day,dayA,isToday);
        });
        html+='</div></div>';
        el.innerHTML=html;
        _bind(el);
    }

    function _navHTML() {
        return '<div class="sc-nav">'+
            '<button class="sc-nav-btn" data-action="prev-week">\u25c4 Prev</button>'+
            '<span class="sc-week-label">'+_fmtWeek()+'</span>'+
            '<button class="sc-nav-btn" data-action="next-week">Next \u25ba</button>'+
            '<button class="sc-nav-btn sc-today-btn" data-action="today-week">Today</button>'+
            '</div>';
    }

    function _colHTML(day, dayA, isToday) {
        var hdr=_fmtColHdr(day);
        var drvs=[];
        dayA.forEach(function(a){ var d=(a.driverName||'Unassigned').trim(); if(drvs.indexOf(d)<0) drvs.push(d); });
        drvs.sort();

        var cls='sc-col'+(isToday?' sc-col-today':'');
        var h='<div class="'+cls+'" data-day="'+day+'">';
        h+='<div class="sc-col-hdr">';
        h+='<span class="sc-col-dayname">'+hdr.day+'</span>';
        h+='<span class="sc-col-date">'+hdr.date+'</span>';
        if(isToday) h+='<span class="sc-today-pill">TODAY</span>';
        h+='</div>';

        if(drvs.length===0) {
            h+='<div class="sc-empty-col">No assignments yet</div>';
        } else {
            drvs.forEach(function(drv){
                var da=dayA.filter(function(a){ return (a.driverName||'Unassigned').trim()===drv; })
                           .sort(function(a,b){ return a.sequenceNumber-b.sequenceNumber; });
                h+=_drvSection(drv,day,da);
            });
        }

        h+=_addFormHTML(day);
        h+='<button class="sc-add-col-btn" data-action="show-add" data-day="'+day+'">+ Add Assignment</button>';
        h+='</div>';
        return h;
    }

    function _drvSection(drv, day, sorted) {
        var dc=_dc(drv), dh=_driverDH(sorted);
        var retDH=dh.length ? dh[dh.length-1].retDH : 0;
        var h='<div class="sc-drv-sec" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';
        h+='<div class="sc-drv-hdr">';
        h+='<span class="sc-drv-name">'+_e(drv)+'</span>';
        h+='<button class="sc-drv-add" data-action="show-add" data-day="'+day+'" data-driver="'+_e(drv)+'" title="Add move for this driver">+</button>';
        h+='</div>';
        sorted.forEach(function(a,i){ h+=_cardHTML(a, dh[i].toDH, dc); });
        if(retDH>0) h+='<div class="sc-ret-bar">\u21a9 Base: '+retDH+' mi</div>';
        h+='</div>';
        return h;
    }

    function _cardHTML(a, dhMi, dc) {
        var isDone=_done(a), load=a.load||{};
        var pro=load.alexeiId||'';
        var lc=a.loadId?_lc(a.loadId):null;
        var label=ACTION_LABEL[a.actionType]||a.actionType||'?';
        var actCss=ACTION_CSS[a.actionType]||'sc-badge-other';
        var orig=[a.originCity,a.originState].filter(Boolean).join(', ');
        var dest=[a.destCity,a.destState].filter(Boolean).join(', ');

        var cls='sc-card'+(isDone?' sc-card-done':'');
        var h='<div class="'+cls+'" data-id="'+a.id+'" style="--db:'+dc.b+';--dc:'+dc.bg+';--dt:'+dc.t+'">';

        // ── View ──
        h+='<div class="sc-card-view">';
        // Top row
        h+='<div class="sc-card-top">';
        h+='<span class="sc-seq">'+a.sequenceNumber+'</span>';
        h+='<span class="sc-badge '+actCss+'">'+_e(label)+'</span>';
        if(pro&&lc) h+='<span class="sc-chip" style="--lc:'+lc+'">'+_e(pro)+'</span>';
        if(dhMi>0)  h+='<span class="sc-dh-tag">'+dhMi+' mi</span>';
        h+='<span class="sc-card-acts">';
        h+='<button class="sc-btn-icon" data-action="toggle-edit" data-id="'+a.id+'" title="Edit">\u270e</button>';
        h+='<button class="sc-btn-icon sc-btn-del" data-action="del-asgn" data-id="'+a.id+'" title="Delete">\u00d7</button>';
        h+='</span>';
        h+='</div>';
        // Route
        if(orig||dest) h+='<div class="sc-route">'+_e(orig)+(orig&&dest?' \u2192 ':'')+_e(dest)+'</div>';
        // Appts
        var pts=[]; if(a.puAppt) pts.push('PU '+a.puAppt); if(a.deAppt) pts.push('DE '+a.deAppt);
        if(pts.length) h+='<div class="sc-appts">'+_e(pts.join(' \u00b7 '))+'</div>';
        // Checkboxes
        var CHKS=[
            ['dispatched','D','Dispatched'],
            ['pickedUp','P','Picked Up'],
            ['delivered','V','Delivered'],
            ['paperworkReceived','R','Paperwork Rcvd'],
            ['paperworkReviewed','W','Paperwork Rev\'d'],
            ['invoicingReady','I','Invoicing Ready'],
        ];
        h+='<div class="sc-chks">';
        CHKS.forEach(function(c){
            h+='<label class="sc-chk-lbl" title="'+c[2]+'">'+
               '<input type="checkbox" class="sc-chk"'+(a[c[0]]?' checked':'')+
               ' data-action="toggle-chk" data-id="'+a.id+'" data-field="'+c[0]+'">'+
               '<span>'+c[1]+'</span></label>';
        });
        if(isDone) h+='<span class="sc-done-mark" title="Fully complete">\u2713</span>';
        h+='</div>';
        // Notes
        if(a.notes) {
            var n=a.notes; h+='<div class="sc-notes">'+_e(n.length>55?n.substring(0,55)+'\u2026':n)+'</div>';
        }
        h+='</div>'; // sc-card-view

        // ── Edit form (hidden) ──
        h+=_editFormHTML(a);

        h+='</div>'; // sc-card
        return h;
    }

    function _editFormHTML(a) {
        var load=a.load||{};
        var h='<div class="sc-card-edit" style="display:none" data-edit-for="'+a.id+'">';
        h+='<div class="sc-ef-grid">';
        // PRO / TMS
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" value="'+_e(load.alexeiId||'')+'" placeholder="PRO-10421"></label>';
        h+='<label class="sc-ef-lbl">TMS<input class="sc-inp" name="tms" value="'+_e(load.tmsId||'')+'" placeholder="TMS-8801"></label>';
        h+='</div>';
        // Action / Driver
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Action'+_actSel('action',a.actionType||'PICKUP')+'</label>';
        h+='<label class="sc-ef-lbl">Driver<input class="sc-inp" name="driver" value="'+_e(a.driverName||'')+'" list="sc-drvs-dl" placeholder="Alexei"></label>';
        h+='</div>';
        // From
        h+='<div class="sc-ef-row-cs">';
        h+='<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" value="'+_e(a.originCity||'')+'" placeholder="Chicago"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" value="'+_e(a.originState||'')+'" maxlength="2" placeholder="IL"></label>';
        h+='</div>';
        // To
        h+='<div class="sc-ef-row-cs">';
        h+='<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" value="'+_e(a.destCity||'')+'" placeholder="Milwaukee"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" value="'+_e(a.destState||'')+'" maxlength="2" placeholder="WI"></label>';
        h+='</div>';
        // Appts + Seq
        h+='<div class="sc-ef-row3">';
        h+='<label class="sc-ef-lbl">PU Appt<input class="sc-inp" type="time" name="puappt" value="'+_e(a.puAppt||'')+'"></label>';
        h+='<label class="sc-ef-lbl">DE Appt<input class="sc-inp" type="time" name="deappt" value="'+_e(a.deAppt||'')+'"></label>';
        h+='<label class="sc-ef-lbl">Seq<input class="sc-inp" type="number" name="seq" value="'+_e(a.sequenceNumber||1)+'" min="1" max="20"></label>';
        h+='</div>';
        // Notes
        h+='<label class="sc-ef-lbl sc-ef-full">Notes<input class="sc-inp" name="notes" value="'+_e(a.notes||'')+'" placeholder="Notes\u2026"></label>';
        h+='</div>'; // sc-ef-grid
        h+='<div class="sc-ef-btns">';
        h+='<button class="sc-btn-cancel" data-action="cancel-edit" data-id="'+a.id+'">Cancel</button>';
        h+='<button class="sc-btn-save" data-action="save-edit" data-id="'+a.id+'">Save</button>';
        h+='</div>';
        h+='</div>'; // sc-card-edit
        return h;
    }

    function _addFormHTML(day) {
        var h='<div class="sc-add-form" data-add-day="'+day+'" style="display:none">';
        h+='<div class="sc-add-form-hdr">New Assignment</div>';
        h+='<div class="sc-ef-grid">';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">PRO #<input class="sc-inp" name="pro" placeholder="PRO-10421"></label>';
        h+='<label class="sc-ef-lbl">TMS<input class="sc-inp" name="tms" placeholder="TMS-8801"></label>';
        h+='</div>';
        h+='<div class="sc-ef-row2">';
        h+='<label class="sc-ef-lbl">Action'+_actSel('action','PICKUP')+'</label>';
        h+='<label class="sc-ef-lbl">Driver<input class="sc-inp" name="driver" list="sc-drvs-dl" placeholder="Alexei"></label>';
        h+='</div>';
        h+='<div class="sc-ef-row-cs">';
        h+='<label class="sc-ef-lbl sc-ef-city">From City<input class="sc-inp" name="origcity" placeholder="Chicago"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="origst" maxlength="2" placeholder="IL"></label>';
        h+='</div>';
        h+='<div class="sc-ef-row-cs">';
        h+='<label class="sc-ef-lbl sc-ef-city">To City<input class="sc-inp" name="dstcity" placeholder="Milwaukee"></label>';
        h+='<label class="sc-ef-lbl sc-ef-st">ST<input class="sc-inp" name="dstst" maxlength="2" placeholder="WI"></label>';
        h+='</div>';
        h+='<div class="sc-ef-row3">';
        h+='<label class="sc-ef-lbl">PU Appt<input class="sc-inp" type="time" name="puappt"></label>';
        h+='<label class="sc-ef-lbl">DE Appt<input class="sc-inp" type="time" name="deappt"></label>';
        h+='<label class="sc-ef-lbl">Seq<input class="sc-inp" type="number" name="seq" value="1" min="1" max="20"></label>';
        h+='</div>';
        h+='<label class="sc-ef-lbl sc-ef-full">Notes<input class="sc-inp" name="notes" placeholder="Notes\u2026"></label>';
        h+='</div>'; // sc-ef-grid
        h+='<div class="sc-ef-btns">';
        h+='<button class="sc-btn-cancel" data-action="cancel-add" data-day="'+day+'">Cancel</button>';
        h+='<button class="sc-btn-save" data-action="save-new" data-day="'+day+'">Save</button>';
        h+='</div>';
        h+='</div>'; // sc-add-form
        return h;
    }

    function _actSel(name, val) {
        var opts=[['PICKUP','PICKUP'],['DELIVERY','DELIVERY'],['PICKUP_AND_DELIVER','P&D'],['REPOSITION','REPOSITION'],['OTHER','OTHER']];
        var s='<select class="sc-inp" name="'+name+'">';
        opts.forEach(function(o){ s+='<option value="'+o[0]+'"'+(val===o[0]?' selected':'')+'>'+_e(o[1])+'</option>'; });
        return s+'</select>';
    }

    // ── Event binding ─────────────────────────────────────────────────────────
    function _bind(el) {
        el.addEventListener('click', function(e) {
            var b=e.target.closest('[data-action]'); if(!b) return;
            switch(b.dataset.action) {
                case 'prev-week':   _load(_addDays(_weekStart,-7)); break;
                case 'next-week':   _load(_addDays(_weekStart, 7)); break;
                case 'today-week':  _load(_mondayOf(new Date()));   break;
                case 'toggle-edit': _toggleEdit(b.dataset.id);      break;
                case 'cancel-edit': _cancelEdit(b.dataset.id);      break;
                case 'save-edit':   _saveEdit(b.dataset.id);        break;
                case 'del-asgn':    _delAsgn(b.dataset.id);         break;
                case 'show-add':    _showAdd(b.dataset.day, b.dataset.driver||''); break;
                case 'cancel-add':  _cancelAdd(b.dataset.day);      break;
                case 'save-new':    _saveNew(b.dataset.day);        break;
            }
        });
        el.addEventListener('change', function(e) {
            var t=e.target;
            if(t.dataset.action==='toggle-chk') _toggleChk(t.dataset.id, t.dataset.field, t.checked);
        });
    }

    // ── Toggle edit ───────────────────────────────────────────────────────────
    function _toggleEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if(!card) return;
        var ef=card.querySelector('.sc-card-edit'); if(!ef) return;
        var open=ef.style.display!=='none';
        ef.style.display=open?'none':'block';
        if(!open) { var fi=ef.querySelector('input,select'); if(fi) fi.focus(); }
    }
    function _cancelEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if(!card) return;
        var ef=card.querySelector('.sc-card-edit'); if(ef) ef.style.display='none';
    }

    // ── Save edit ─────────────────────────────────────────────────────────────
    function _saveEdit(id) {
        var card=document.querySelector('.sc-card[data-id="'+id+'"]'); if(!card) return;
        var ef=card.querySelector('.sc-card-edit'); if(!ef) return;
        var a=_asgns.find(function(x){ return x.id===id; }); if(!a) return;

        var g=function(name){ var inp=ef.querySelector('[name="'+name+'"]'); return inp?inp.value.trim():''; };
        var saveBtn=ef.querySelector('[data-action="save-edit"]');
        if(saveBtn){ saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        var loadBody={ alexeiId:g('pro'), tmsId:g('tms'), puCity:g('origcity'), puState:g('origst').toUpperCase(), deCity:g('dstcity'), deState:g('dstst').toUpperCase() };
        var asgnBody={
            date:a.date, weekStart:_weekStart,
            driverName:g('driver')||a.driverName,
            sequenceNumber:parseInt(g('seq')||a.sequenceNumber,10),
            actionType:g('action')||a.actionType,
            originCity:g('origcity'), originState:g('origst').toUpperCase(),
            destCity:g('dstcity'),   destState:g('dstst').toUpperCase(),
            puAppt:g('puappt'), deAppt:g('deappt'), notes:g('notes'),
        };

        var loadP;
        if(a.loadId) {
            loadP=_api('PUT','/api/ivan/loads/'+a.loadId,loadBody).then(function(){ return a.loadId; });
        } else if(g('pro')||g('tms')||g('origcity')||g('dstcity')) {
            loadP=_api('POST','/api/ivan/loads',loadBody).then(function(r){ return r.id; });
        } else {
            loadP=Promise.resolve(null);
        }

        loadP.then(function(lid){ if(lid) asgnBody.loadId=lid; return _api('PUT','/api/ivan/schedule/assignments/'+id,asgnBody); })
             .then(function(){ _load(_weekStart); })
             .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Add form ──────────────────────────────────────────────────────────────
    function _showAdd(day, driver) {
        document.querySelectorAll('.sc-add-form').forEach(function(f){ if(f.dataset.addDay!==day) f.style.display='none'; });
        var form=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if(!form) return;
        form.querySelectorAll('input,select').forEach(function(i){ i.value=''; });
        form.querySelector('[name="action"]').value='PICKUP';
        if(driver) { var di=form.querySelector('[name="driver"]'); if(di) di.value=driver; }
        var seqI=form.querySelector('[name="seq"]');
        if(seqI) seqI.value=_nextSeq(day,driver);
        form.style.display='block';
        setTimeout(function(){ form.scrollIntoView({behavior:'smooth',block:'nearest'}); },50);
        setTimeout(function(){ var fi=form.querySelector('input'); if(fi) fi.focus(); },80);
    }
    function _cancelAdd(day) {
        var f=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if(f) f.style.display='none';
    }

    // ── Save new ──────────────────────────────────────────────────────────────
    function _saveNew(day) {
        var form=document.querySelector('.sc-add-form[data-add-day="'+day+'"]'); if(!form) return;
        var g=function(name){ var inp=form.querySelector('[name="'+name+'"]'); return inp?inp.value.trim():''; };
        var saveBtn=form.querySelector('[data-action="save-new"]');
        if(saveBtn){ saveBtn.disabled=true; saveBtn.textContent='Saving\u2026'; }

        var proNum=g('pro'), origcity=g('origcity'), dstcity=g('dstcity');
        var loadBody={ alexeiId:proNum, tmsId:g('tms'), puCity:origcity, puState:g('origst').toUpperCase(), deCity:dstcity, deState:g('dstst').toUpperCase() };
        var asgnBody={
            date:day, weekStart:_weekStart,
            driverName:g('driver'),
            sequenceNumber:parseInt(g('seq')||'1',10),
            actionType:g('action')||'PICKUP',
            originCity:origcity, originState:g('origst').toUpperCase(),
            destCity:dstcity,    destState:g('dstst').toUpperCase(),
            puAppt:g('puappt'), deAppt:g('deappt'), notes:g('notes'),
        };

        var matchedLoad=proNum?_loads.find(function(l){ return l.alexeiId===proNum; }):null;
        var loadP;
        if(matchedLoad) { asgnBody.loadId=matchedLoad.id; loadP=Promise.resolve(matchedLoad.id); }
        else if(proNum||g('tms')||origcity||dstcity) { loadP=_api('POST','/api/ivan/loads',loadBody).then(function(r){ asgnBody.loadId=r.id; return r.id; }); }
        else { loadP=Promise.resolve(null); }

        loadP.then(function(){ return _api('POST','/api/ivan/schedule/assignments',asgnBody); })
             .then(function(){ _load(_weekStart); })
             .catch(function(err){ alert('Save failed: '+err.message); if(saveBtn){saveBtn.disabled=false;saveBtn.textContent='Save';} });
    }

    // ── Delete ────────────────────────────────────────────────────────────────
    function _delAsgn(id) {
        if(!confirm('Delete this assignment?')) return;
        _api('DELETE','/api/ivan/schedule/assignments/'+id)
            .then(function(){ _load(_weekStart); })
            .catch(function(err){ alert('Delete failed: '+err.message); });
    }

    // ── Checkbox toggle (optimistic) ──────────────────────────────────────────
    function _toggleChk(id, field, checked) {
        var a=_asgns.find(function(x){ return x.id===id; }); if(!a) return;
        var prev=a[field]; a[field]=checked;
        var isDone=_done(a);
        var card=document.querySelector('.sc-card[data-id="'+id+'"]');
        if(card) {
            card.classList.toggle('sc-card-done',isDone);
            var dm=card.querySelector('.sc-done-mark');
            if(isDone&&!dm) {
                var chkRow=card.querySelector('.sc-chks');
                if(chkRow){ var sp=document.createElement('span'); sp.className='sc-done-mark'; sp.title='Fully complete'; sp.textContent='\u2713'; chkRow.appendChild(sp); }
            } else if(!isDone&&dm) { dm.remove(); }
        }
        var patch={}; patch[field]=checked;
        _api('PUT','/api/ivan/schedule/assignments/'+id,patch).catch(function(err){
            a[field]=prev; alert('Save failed: '+err.message); _render();
        });
    }

    // ── Public ────────────────────────────────────────────────────────────────
    function mountSchedule(containerId) {
        _cid=containerId;
        _load(_mondayOf(new Date()));
    }

    return { mountSchedule: mountSchedule };
}());
