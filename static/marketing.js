/* marketing.js — BCAT Marketing Intelligence Dashboard */
'use strict';

const MarketingApp = {
    _initialized: false,
    currentGroup: 'bcat_logistics',
    currentSection: 'overview',
    charts: {},

    groups: [
        { id: 'bcat_logistics', label: 'BCAT Logistics' },
    ],

    sections: [
        { id: 'overview',         label: 'Overview' },
        { id: 'seo',              label: 'SEO' },
        { id: 'google_ads',       label: 'Google Ads' },
        { id: 'facebook_ads',     label: 'Facebook Ads' },
        { id: 'linkedin',         label: 'LinkedIn' },
        { id: 'email',            label: 'Email' },
        { id: 'knowledge',        label: 'Knowledge Graph' },
        { id: 'recommendations',  label: 'Recommendations' }
    ],

    // ── Init ────────────────────────────────────────────────────────────────
    init() {
        if (this._initialized) return;
        this._initialized = true;
        this.render();
    },

    render() {
        const app = document.getElementById('marketing-app');
        if (!app) return;
        app.innerHTML = this.shellHTML();
        this.bindSectionTabs();
        this.loadSection(this.currentGroup, this.currentSection);
    },

    shellHTML() {
        const sectionBtns = this.sections.map(s =>
            `<button class="mkt-section-btn${s.id === this.currentSection ? ' active' : ''}"
                     data-section="${s.id}">${s.label}</button>`
        ).join('');

        return `
        <div class="mkt-shell">
            <div class="mkt-section-nav">${sectionBtns}</div>
            <div id="mkt-content" class="mkt-content"></div>
        </div>`;
    },

    bindSectionTabs() {
        document.querySelectorAll('.mkt-section-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentSection = btn.dataset.section;
                document.querySelectorAll('.mkt-section-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.loadSection(this.currentGroup, this.currentSection);
            });
        });
    },

    // ── Section dispatcher ───────────────────────────────────────────────────
    async loadSection(groupId, section) {
        const content = document.getElementById('mkt-content');
        if (!content) return;
        content.innerHTML = '<div class="mkt-loading">Loading…</div>';

        // destroy any lingering charts
        Object.values(this.charts).forEach(c => { try { c.destroy(); } catch(_) {} });
        this.charts = {};

        try {
            switch (section) {
                case 'overview':        await this.loadOverview(groupId, content);        break;
                case 'seo':             await this.loadSEO(groupId, content);             break;
                case 'google_ads':      await this.loadGoogleAds(groupId, content);       break;
                case 'facebook_ads':    await this.loadFacebookAds(groupId, content);     break;
                case 'linkedin':        await this.loadLinkedIn(groupId, content);        break;
                case 'email':           await this.loadEmail(groupId, content);           break;
                case 'knowledge':       await this.loadKnowledge(groupId, content);       break;
                case 'recommendations': await this.loadRecommendations(groupId, content); break;
                default: content.innerHTML = '<p class="mkt-empty">Unknown section.</p>';
            }
        } catch(e) {
            content.innerHTML = `<p class="mkt-empty" style="color:#f87171">Error: ${e.message}</p>`;
        }
    },

    // ── Overview ─────────────────────────────────────────────────────────────
    async loadOverview(groupId, content) {
        const [ov, comp] = await Promise.all([
            this.api(`/api/marketing/${groupId}/overview`),
            this.api(`/api/marketing/${groupId}/competitors`)
        ]);

        const kpis = ov.kpis || {};
        const kpisExt = ov.kpis_extended || {};
        const channels = ov.channels || {};
        const trendsExt = ov.trends_extended || {};
        const trends = ov.trends || {};
        const channelTable = ov.channel_table || [];

        const bestCh = kpisExt.best_channel || '—';
        const topCampaign = kpisExt.top_campaign || '—';

        content.innerHTML = `
        <div class="mkt-kpi-grid" style="grid-template-columns:repeat(auto-fill,minmax(155px,1fr));">
            ${this.kpiCard('Total Spend MTD',    this.money(kpis.monthly_spend))}
            ${this.kpiCard('Total Leads MTD',    this.num(kpisExt.total_leads_mtd))}
            ${this.kpiCard('Booked Calls MTD',   this.num(kpisExt.total_booked_calls_mtd))}
            ${this.kpiCard('Conversions MTD',    this.num(kpisExt.total_conversions_mtd))}
            ${this.kpiCard('Blended ROAS',       this.num(kpis.blended_roas, 2) + 'x')}
            ${this.kpiCard('Blended CPL',        this.money(kpisExt.blended_cpl))}
            ${this.kpiCard('Blended CAC',        this.money(kpisExt.blended_cac))}
            ${this.kpiCard('Attributed Rev',     this.money(kpisExt.attributed_revenue))}
            ${this.kpiCard('Organic Sessions',   this.num(kpis.organic_sessions))}
            ${this.kpiCard('Best Channel',       bestCh)}
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Monthly Spend by Channel</div>
                <canvas id="ch-spend"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Inbound Leads by Channel (Monthly)</div>
                <canvas id="ch-leads"></canvas>
            </div>
        </div>

        ${channelTable.length ? `
        <div class="mkt-section-subtitle">Channel Performance Summary</div>
        <div class="mkt-table-card">
            <div class="table-wrap">
                <table>
                    <thead><tr>
                        <th>Channel</th><th>Spend</th><th>Leads</th><th>Booked Calls</th>
                        <th>Conversions</th><th>Conv Rate</th><th>CPL</th><th>CAC</th><th>ROAS</th><th>vs Prior Mo</th>
                    </tr></thead>
                    <tbody>${channelTable.map(r => `<tr>
                        <td style="font-weight:600;">${r.channel}</td>
                        <td>${r.spend ? this.money(r.spend) : '—'}</td>
                        <td>${this.num(r.leads)}</td>
                        <td>${this.num(r.booked_calls)}</td>
                        <td>${this.num(r.conversions)}</td>
                        <td>${r.conv_rate != null ? this.num(r.conv_rate, 1) + '%' : '—'}</td>
                        <td>${r.cpl ? this.money(r.cpl) : '—'}</td>
                        <td>${r.cac ? this.money(r.cac) : '—'}</td>
                        <td>${r.roas != null ? this.num(r.roas, 2) + 'x' : '—'}</td>
                        <td><span style="color:${(r.trend||'').startsWith('+') ? '#4ade80' : '#f87171'}">${r.trend || '—'}</span></td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>
        </div>` : `
        <div class="mkt-channel-grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr));">
            ${this.channelCard('SEO',          channels.seo          || {})}
            ${this.channelCard('Google Ads',   channels.google_ads   || {})}
            ${this.channelCard('Facebook Ads', channels.facebook_ads || {})}
            ${this.channelCard('LinkedIn',     channels.linkedin     || {})}
            ${this.channelCard('Email',        channels.email        || {})}
        </div>`}

        <div class="mkt-section-subtitle">Competitor Landscape</div>
        ${this.renderCompetitorSEOPanel(comp)}`;

        // Spend chart — all paid channels
        const spendRows = trendsExt.spend_by_channel || trends.spend_by_channel || [];
        if (spendRows.length) {
            const labels = spendRows.map(r => r.month);
            this.renderChart('ch-spend', 'bar', labels, [
                { label: 'Google Ads',   data: spendRows.map(r => r.google    || 0), backgroundColor: '#4285F4' },
                { label: 'Facebook Ads', data: spendRows.map(r => r.facebook  || 0), backgroundColor: '#1877F2' },
                { label: 'LinkedIn',     data: spendRows.map(r => r.linkedin  || 0), backgroundColor: '#0a66c2' },
                { label: 'Email',        data: spendRows.map(r => r.email     || 0), backgroundColor: '#10b981' },
            ], { stacked: true });
        }

        // Leads chart — all channels including SEO
        const leadsRows = trendsExt.leads_by_channel || [];
        if (leadsRows.length) {
            const labels = leadsRows.map(r => r.month);
            this.renderChart('ch-leads', 'bar', labels, [
                { label: 'SEO',          data: leadsRows.map(r => r.seo      || 0), backgroundColor: '#22c55e' },
                { label: 'Email',        data: leadsRows.map(r => r.email    || 0), backgroundColor: '#10b981' },
                { label: 'Facebook Ads', data: leadsRows.map(r => r.facebook || 0), backgroundColor: '#1877F2' },
                { label: 'LinkedIn',     data: leadsRows.map(r => r.linkedin || 0), backgroundColor: '#0a66c2' },
                { label: 'Google Ads',   data: leadsRows.map(r => r.google   || 0), backgroundColor: '#4285F4' },
            ], { stacked: true });
        }
    },

    channelCard(name, ch) {
        return `<div class="mkt-channel-card">
            <div class="mkt-channel-name">${name}</div>
            ${ch.spend      != null ? `<div class="mkt-channel-row"><span>Spend</span><span>${ch.spend ? this.money(ch.spend) : '—'}</span></div>` : ''}
            ${ch.leads      != null ? `<div class="mkt-channel-row"><span>Leads</span><span>${this.num(ch.leads)}</span></div>` : ''}
            ${ch.booked_calls != null ? `<div class="mkt-channel-row"><span>Booked Calls</span><span>${this.num(ch.booked_calls)}</span></div>` : ''}
            <div class="mkt-channel-row"><span>Conversions</span><span>${this.num(ch.conversions)}</span></div>
            ${ch.conv_rate  != null ? `<div class="mkt-channel-row"><span>Conv Rate</span><span>${this.num(ch.conv_rate, 1)}%</span></div>` : ''}
            ${ch.roas       != null ? `<div class="mkt-channel-row"><span>ROAS</span><span>${this.num(ch.roas,2)}x</span></div>` : ''}
            ${ch.cpl        != null ? `<div class="mkt-channel-row"><span>CPL</span><span>${ch.cpl ? this.money(ch.cpl) : '—'}</span></div>` : ''}
            ${ch.cac        != null ? `<div class="mkt-channel-row"><span>CAC</span><span>${ch.cac ? this.money(ch.cac) : '—'}</span></div>` : ''}
            ${ch.cpc        != null ? `<div class="mkt-channel-row"><span>CPC</span><span>${this.money(ch.cpc)}</span></div>` : ''}
            ${ch.ctr        != null ? `<div class="mkt-channel-row"><span>CTR</span><span>${this.pct(ch.ctr)}</span></div>` : ''}
            ${ch.open_rate  != null ? `<div class="mkt-channel-row"><span>Open Rate</span><span>${this.pct(ch.open_rate)}</span></div>` : ''}
            ${ch.reply_rate != null ? `<div class="mkt-channel-row"><span>Reply Rate</span><span>${this.pct(ch.reply_rate)}</span></div>` : ''}
        </div>`;
    },

    // ── SEO ──────────────────────────────────────────────────────────────────
    async loadSEO(groupId, content) {
        const [seo, comp] = await Promise.all([
            this.api(`/api/marketing/${groupId}/seo`),
            this.api(`/api/marketing/${groupId}/competitors`)
        ]);

        const m = seo.metrics || {};
        const trends = seo.trends || {};
        const keywords = seo.keywords || [];
        const tech = seo.technical || {};

        content.innerHTML = `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Domain Authority', m.domain_authority || '—')}
            ${this.kpiCard('Organic Sessions', this.num(m.organic_sessions) + '/mo')}
            ${this.kpiCard('Ranked Keywords', this.num(m.ranked_keywords))}
            ${this.kpiCard('Avg Position', m.avg_position || '—')}
            ${this.kpiCard('Core Web Vitals', m.core_web_vitals_score ? m.core_web_vitals_score + '/100' : '—')}
            ${this.kpiCard('Backlinks', this.num(m.backlinks))}
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Organic Traffic Trend</div>
                <canvas id="seo-traffic"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Keyword Ranking Distribution</div>
                <canvas id="seo-kwdist"></canvas>
            </div>
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Top Keywords</div>
            <div class="table-wrap">${this.kwTable(keywords)}</div>
        </div>

        <div class="mkt-section-subtitle">Technical SEO</div>
        <div class="mkt-tech-grid">
            ${this.techItem('Page Speed (mobile)', tech.page_speed_mobile)}
            ${this.techItem('Page Speed (desktop)', tech.page_speed_desktop)}
            ${this.techItem('Core Web Vitals', tech.core_web_vitals_score)}
            ${this.techItem('Schema Markup', tech.schema_markup)}
            ${this.techItem('Mobile Friendly', tech.mobile_friendly)}
            ${this.techItem('SSL', tech.ssl_certificate)}
            ${this.techItem('XML Sitemap', tech.xml_sitemap)}
            ${this.techItem('Robots.txt', tech.robots_txt)}
        </div>

        <div class="mkt-section-subtitle">SEO Competitor Analysis</div>
        ${this.renderCompetitorSEOPanel(comp)}

        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="MarketingApp.runAnalysis('${groupId}','seo')">Run SEO Analysis</button>
            <button class="mkt-btn mkt-btn-secondary" onclick="MarketingApp.generatePlan('${groupId}','seo')">Generate Plan</button>
        </div>`;

        if (trends.organic_sessions) {
            this.renderChart('seo-traffic', 'line',
                trends.organic_sessions.map(r => r.month),
                [{ label: 'Sessions', data: trends.organic_sessions.map(r => r.value),
                   borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.15)', fill: true }]
            );
        }
        if (m.keyword_distribution) {
            const kd = m.keyword_distribution;
            this.renderChart('seo-kwdist', 'doughnut',
                ['Top 3', 'Top 10', 'Top 30', 'Below 30'],
                [{ data: [kd.top_3||0, kd.top_10||0, kd.top_30||0, kd.below_30||0],
                   backgroundColor: ['#22c55e','#0ea5e9','#f59e0b','#6b7280'] }]
            );
        }
    },

    kwTable(keywords) {
        if (!keywords.length) return '<p class="mkt-empty">No keyword data.</p>';
        return `<table><thead><tr>
            <th>Keyword</th><th>Position</th><th>Volume</th><th>Difficulty</th><th>Intent</th>
        </tr></thead><tbody>${keywords.map(k => `<tr>
            <td>${k.keyword}</td>
            <td>${k.position || '—'}</td>
            <td>${this.num(k.volume)}</td>
            <td>${k.difficulty || '—'}</td>
            <td><span class="mkt-badge">${k.intent || '—'}</span></td>
        </tr>`).join('')}</tbody></table>`;
    },

    techItem(label, val) {
        const display = val == null ? '—' : (typeof val === 'boolean' ? (val ? '✓' : '✗') : val);
        const cls = val === true ? 'positive' : (val === false ? 'negative' : '');
        return `<div class="mkt-tech-item"><span class="mkt-tech-label">${label}</span><span class="mkt-tech-val ${cls}">${display}</span></div>`;
    },

    // ── Google Ads ───────────────────────────────────────────────────────────
    async loadGoogleAds(groupId, content) {
        const [ads, comp] = await Promise.all([
            this.api(`/api/marketing/${groupId}/google-ads`),
            this.api(`/api/marketing/${groupId}/competitors`)
        ]);

        const m = ads.metrics || {};
        const campaigns = ads.campaigns || [];
        const trends = ads.trends || {};

        const totalImpressions = campaigns.reduce((s, c) => s + (c.impressions || 0), 0);
        const totalClicks      = campaigns.reduce((s, c) => s + (c.clicks      || 0), 0);

        content.innerHTML = `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Monthly Spend',    this.money(m.monthly_spend))}
            ${this.kpiCard('Impressions',       this.num(m.impressions || totalImpressions))}
            ${this.kpiCard('Clicks',            this.num(m.clicks || totalClicks))}
            ${this.kpiCard('Conversions',       this.num(m.conversions))}
            ${m.roas != null ? this.kpiCard('ROAS', this.num(m.roas,2)+'x') : ''}
            ${this.kpiCard('Avg CPC',           this.money(m.avg_cpc))}
            ${this.kpiCard('CTR',               this.pct(m.ctr))}
            ${this.kpiCard('Quality Score',     m.quality_score || '—')}
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Monthly Spend &amp; Conversions Trend</div>
                <canvas id="gads-trend"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Campaign Performance (Spend vs Conversions)</div>
                <canvas id="gads-camp"></canvas>
            </div>
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Campaign Detail</div>
            <div class="table-wrap">${this.campaignTable(campaigns)}</div>
        </div>

        <div class="mkt-section-subtitle">Competitor PPC Intelligence</div>
        ${this.renderCompetitorPaidPanel(comp, 'google')}

        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="MarketingApp.runAnalysis('${groupId}','google_ads')">Run Analysis</button>
            <button class="mkt-btn mkt-btn-secondary" onclick="MarketingApp.generatePlan('${groupId}','google_ads')">Generate Plan</button>
        </div>`;

        if (trends.spend) {
            this.renderChart('gads-trend', 'bar',
                trends.spend.map(r => r.month),
                [
                    { label: 'Spend ($)', data: trends.spend.map(r => r.value), backgroundColor: '#4285F4', yAxisID: 'y' },
                    { label: 'Conversions', data: (trends.conversions||[]).map(r => r.value), type: 'line',
                      borderColor: '#22c55e', yAxisID: 'y1' }
                ],
                { dualAxis: true }
            );
        }
        if (campaigns.length) {
            this.renderChart('gads-camp', 'bar',
                campaigns.map(c => c.name),
                [
                    { label: 'Spend', data: campaigns.map(c => c.spend||0), backgroundColor: '#4285F4' },
                    { label: 'Conversions', data: campaigns.map(c => c.conversions||0), backgroundColor: '#22c55e' }
                ],
                { stacked: false, horizontal: true }
            );
        }
    },

    campaignTable(campaigns) {
        if (!campaigns.length) return '<p class="mkt-empty">No campaign data.</p>';
        return `<table><thead><tr>
            <th>Campaign</th><th>Status</th><th>Spend</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>CPC</th><th>Conversions</th><th>CPA</th><th>ROAS</th>
        </tr></thead><tbody>${campaigns.map(c => `<tr>
            <td>${c.name}</td>
            <td><span class="mkt-badge mkt-badge-${(c.status||'').toLowerCase()}">${c.status||'—'}</span></td>
            <td>${this.money(c.spend)}</td>
            <td>${c.impressions != null ? this.num(c.impressions) : '—'}</td>
            <td>${c.clicks      != null ? this.num(c.clicks)      : '—'}</td>
            <td>${c.ctr         != null ? this.pct(c.ctr)         : '—'}</td>
            <td>${c.cpc         != null ? this.money(c.cpc)       : '—'}</td>
            <td>${this.num(c.conversions)}</td>
            <td>${c.cpa         != null && c.cpa > 0 ? this.money(c.cpa) : '—'}</td>
            <td>${c.roas        != null && c.roas > 0 ? this.num(c.roas,2)+'x' : '—'}</td>
        </tr>`).join('')}</tbody></table>`;
    },

    // ── Facebook Ads ─────────────────────────────────────────────────────────
    async loadFacebookAds(groupId, content) {
        const [ads, comp] = await Promise.all([
            this.api(`/api/marketing/${groupId}/facebook-ads`),
            this.api(`/api/marketing/${groupId}/competitors`)
        ]);

        const m = ads.metrics || {};
        const campaigns = ads.campaigns || [];
        const audiences = ads.audiences || [];
        const trends = ads.trends || {};

        content.innerHTML = `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Monthly Spend', this.money(m.monthly_spend))}
            ${this.kpiCard('Reach', this.num(m.reach))}
            ${m.roas != null ? this.kpiCard('ROAS', this.num(m.roas,2)+'x') : ''}
            ${this.kpiCard('CPM', this.money(m.cpm))}
            ${this.kpiCard('CTR', this.pct(m.ctr))}
            ${this.kpiCard('Ad Fatigue', m.ad_fatigue_score != null ? m.ad_fatigue_score+'%' : '—')}
        </div>

        ${m.ad_fatigue_score != null ? this.fatigueBar(m.ad_fatigue_score) : ''}

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Spend Trend</div>
                <canvas id="fb-trend"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Audience Split</div>
                <canvas id="fb-aud"></canvas>
            </div>
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Campaigns</div>
            <div class="table-wrap">${this.fbCampaignTable(campaigns)}</div>
        </div>

        <div class="mkt-section-subtitle">Competitor Social Intelligence</div>
        ${this.renderCompetitorPaidPanel(comp, 'facebook')}

        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="MarketingApp.runAnalysis('${groupId}','facebook_ads')">Run Analysis</button>
            <button class="mkt-btn mkt-btn-secondary" onclick="MarketingApp.generatePlan('${groupId}','facebook_ads')">Generate Plan</button>
        </div>`;

        if (trends.spend) {
            this.renderChart('fb-trend', 'line',
                trends.spend.map(r => r.month),
                [{ label: 'Spend', data: trends.spend.map(r => r.value),
                   borderColor: '#1877F2', backgroundColor: 'rgba(24,119,242,0.15)', fill: true }]
            );
        }
        const audMap = {};
        audiences.forEach(a => { audMap[a.name] = a.percentage || a.size || 0; });
        if (Object.keys(audMap).length) {
            this.renderChart('fb-aud', 'doughnut',
                Object.keys(audMap),
                [{ data: Object.values(audMap),
                   backgroundColor: ['#1877F2','#42B72A','#F02849','#F59E0B','#8B5CF6'] }]
            );
        }
    },

    fbCampaignTable(campaigns) {
        if (!campaigns.length) return '<p class="mkt-empty">No campaign data.</p>';
        return `<table><thead><tr>
            <th>Campaign</th><th>Objective</th><th>Status</th><th>Spend</th><th>Reach</th>
            <th>Clicks</th><th>CTR</th><th>CPC</th><th>Leads</th><th>CPL</th><th>Conversions</th><th>CPA</th>
        </tr></thead><tbody>${campaigns.map(c => `<tr>
            <td>${c.name}</td>
            <td>${c.objective||'—'}</td>
            <td><span class="mkt-badge mkt-badge-${(c.status||'').toLowerCase()}">${c.status||'—'}</span></td>
            <td>${this.money(c.spend)}</td>
            <td>${c.reach   != null ? this.num(c.reach)   : '—'}</td>
            <td>${c.clicks  != null ? this.num(c.clicks)  : '—'}</td>
            <td>${c.ctr     != null ? this.pct(c.ctr)     : '—'}</td>
            <td>${c.cpc     != null ? this.money(c.cpc)   : '—'}</td>
            <td>${c.leads   != null ? this.num(c.leads)   : '—'}</td>
            <td>${c.cpl     != null ? this.money(c.cpl)   : '—'}</td>
            <td>${this.num(c.conversions)}</td>
            <td>${c.cpa     != null ? this.money(c.cpa)   : '—'}</td>
        </tr>`).join('')}</tbody></table>`;
    },

    fatigueBar(score) {
        const color = score > 70 ? '#ef4444' : score > 40 ? '#f59e0b' : '#22c55e';
        return `<div class="mkt-fatigue-wrap">
            <span class="mkt-fatigue-label">Ad Fatigue Score</span>
            <div class="mkt-fatigue-track"><div class="mkt-fatigue-fill" style="width:${score}%;background:${color}"></div></div>
            <span class="mkt-fatigue-val">${score}%</span>
        </div>`;
    },

    // ── LinkedIn ─────────────────────────────────────────────────────────────
    async loadLinkedIn(groupId, content) {
        const campaigns = await this.api(`/api/marketing/${groupId}/linkedin-campaigns`);
        const list = Array.isArray(campaigns) ? campaigns : [];

        const totSpend  = list.reduce((s, c) => s + (c.budget || 0), 0);
        const totLeads  = list.reduce((s, c) => s + (c.leads  || 0), 0);
        const totConv   = list.reduce((s, c) => s + (c.conversions || 0), 0);
        const totImp    = list.reduce((s, c) => s + (c.impressions || 0), 0);
        const avgCPL    = totLeads ? Math.round(totSpend / totLeads) : 0;

        content.innerHTML = `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Total Budget',    this.money(totSpend))}
            ${this.kpiCard('Impressions',     this.num(totImp))}
            ${this.kpiCard('Leads',           this.num(totLeads))}
            ${this.kpiCard('Conversions',     this.num(totConv))}
            ${this.kpiCard('Avg CPL',         this.money(avgCPL))}
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">LinkedIn Campaigns</div>
            <div class="table-wrap">
                <table>
                    <thead><tr>
                        <th>Campaign</th><th>Status</th><th>Budget</th>
                        <th>Impressions</th><th>Clicks</th><th>CTR</th>
                        <th>Leads</th><th>Conversions</th><th>CPL</th><th>CAC</th><th>ROAS</th>
                    </tr></thead>
                    <tbody>${list.map(c => `<tr>
                        <td>${c.name || '—'}</td>
                        <td><span style="color:${c.status==='Active'?'#4ade80':'#94a3b8'}">${c.status||'—'}</span></td>
                        <td>${this.money(c.budget)}</td>
                        <td>${this.num(c.impressions)}</td>
                        <td>${this.num(c.clicks)}</td>
                        <td>${this.pct(c.ctr)}</td>
                        <td>${this.num(c.leads)}</td>
                        <td>${this.num(c.conversions)}</td>
                        <td>${this.money(c.cpl)}</td>
                        <td>${this.money(c.cac)}</td>
                        <td>${c.roas != null ? this.num(c.roas,2)+'x' : '—'}</td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Budget vs Leads by Campaign</div>
                <canvas id="li-bud-leads"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">CPL vs CAC by Campaign</div>
                <canvas id="li-cpl-cac"></canvas>
            </div>
        </div>`;

        if (list.length) {
            const labels = list.map(c => c.name.length > 28 ? c.name.slice(0, 28) + '…' : c.name);
            this.renderChart('li-bud-leads', 'bar', labels, [
                { label: 'Budget ($)', data: list.map(c => c.budget || 0), backgroundColor: '#0a66c2', yAxisID: 'y' },
                { label: 'Leads',      data: list.map(c => c.leads  || 0), backgroundColor: '#22c55e', yAxisID: 'y1' },
            ], { dualAxis: true });
            this.renderChart('li-cpl-cac', 'bar', labels, [
                { label: 'CPL ($)', data: list.map(c => c.cpl || 0), backgroundColor: '#f59e0b' },
                { label: 'CAC ($)', data: list.map(c => c.cac || 0), backgroundColor: '#ef4444' },
            ]);
        }
    },

    // ── Email ────────────────────────────────────────────────────────────────
    async loadEmail(groupId, content) {
        const em = await this.api(`/api/marketing/${groupId}/email-marketing`);
        const kpis = em.kpis || {};
        const campaigns = em.campaigns || [];
        const sequences = em.sequences || [];

        content.innerHTML = `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Contacts Active',  this.num(kpis.contacts_active))}
            ${this.kpiCard('Emails Sent MTD',  this.num(kpis.emails_sent_mtd))}
            ${this.kpiCard('Open Rate',        this.pct(kpis.open_rate))}
            ${this.kpiCard('Reply Rate',       this.pct(kpis.reply_rate))}
            ${this.kpiCard('Leads MTD',        this.num(kpis.leads_mtd))}
            ${this.kpiCard('Conversions MTD',  this.num(kpis.conversions_mtd))}
            ${this.kpiCard('CPL',              this.money(kpis.cpl))}
            ${this.kpiCard('CAC',              this.money(kpis.cac))}
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Active Campaigns</div>
            <div class="table-wrap">
                <table>
                    <thead><tr>
                        <th>Campaign</th><th>Status</th><th>Contacts</th>
                        <th>Sent</th><th>Opened</th><th>Replied</th><th>Meetings</th>
                        <th>Open Rate</th><th>Reply Rate</th>
                    </tr></thead>
                    <tbody>${campaigns.map(c => `<tr>
                        <td>${c.name||'—'}</td>
                        <td><span style="color:${c.status==='Active'?'#4ade80':'#94a3b8'}">${c.status||'—'}</span></td>
                        <td>${this.num(c.contacts)}</td>
                        <td>${this.num(c.sent)}</td>
                        <td>${this.num(c.opened)}</td>
                        <td>${this.num(c.replied)}</td>
                        <td>${this.num(c.meetings)}</td>
                        <td>${this.pct(c.open_rate)}</td>
                        <td>${this.pct(c.reply_rate)}</td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>
        </div>

        ${sequences.length ? `
        <div class="mkt-table-card" style="margin-top:16px;">
            <div class="mkt-chart-title">Email Sequences</div>
            <div class="table-wrap">
                <table>
                    <thead><tr>
                        <th>Sequence</th><th>Steps</th><th>Enrolled</th>
                        <th>Avg Open Rate</th><th>Avg Reply Rate</th><th>Conversions</th>
                    </tr></thead>
                    <tbody>${sequences.map(s => `<tr>
                        <td>${s.name||'—'}</td>
                        <td>${s.steps||'—'}</td>
                        <td>${this.num(s.enrolled)}</td>
                        <td>${this.pct(s.avg_open_rate)}</td>
                        <td>${this.pct(s.avg_reply_rate)}</td>
                        <td>${this.num(s.conversions)}</td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>
        </div>` : ''}

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Campaign Performance — Meetings Booked</div>
                <canvas id="em-meetings"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Open vs Reply Rate by Campaign</div>
                <canvas id="em-rates"></canvas>
            </div>
        </div>`;

        if (campaigns.length) {
            const labels = campaigns.map(c => c.name.length > 25 ? c.name.slice(0, 25) + '…' : c.name);
            this.renderChart('em-meetings', 'bar', labels, [
                { label: 'Meetings Booked', data: campaigns.map(c => c.meetings || 0), backgroundColor: '#10b981' },
            ]);
            this.renderChart('em-rates', 'bar', labels, [
                { label: 'Open Rate %',  data: campaigns.map(c => c.open_rate  || 0), backgroundColor: '#3b82f6' },
                { label: 'Reply Rate %', data: campaigns.map(c => c.reply_rate || 0), backgroundColor: '#f59e0b' },
            ]);
        }
    },

    // ── Knowledge Graph ───────────────────────────────────────────────────────
    async loadKnowledge(groupId, content) {
        const kg = await this.api(`/api/marketing/${groupId}/knowledge-graph`);
        const entities = kg.entities || [];
        const relationships = kg.relationships || [];
        const insights = kg.insights || [];

        content.innerHTML = `
        <div class="mkt-kg-header">
            <div>
                <span class="mkt-kg-stat">${entities.length} entities</span>
                <span class="mkt-kg-stat">${relationships.length} relationships</span>
                <span class="mkt-kg-stat">${insights.length} insights</span>
            </div>
            <button class="mkt-btn" onclick="MarketingApp.buildKG('${groupId}')">Refresh Intelligence</button>
        </div>

        <div class="mkt-section-subtitle">Key Insights</div>
        <div class="mkt-insights-grid">
            ${insights.map(i => this.insightCard(i)).join('') || '<p class="mkt-empty">No insights yet.</p>'}
        </div>

        <div class="mkt-section-subtitle">Entity Map</div>
        <div class="mkt-entity-grid">
            ${entities.map(e => this.entityCard(e)).join('') || '<p class="mkt-empty">No entities.</p>'}
        </div>

        <div class="mkt-section-subtitle">Relationships</div>
        <div class="table-wrap">
            <table><thead><tr><th>From</th><th>Relationship</th><th>To</th><th>Strength</th></tr></thead>
            <tbody>${relationships.map(r => `<tr>
                <td>${r.from}</td>
                <td><span class="mkt-badge">${r.type}</span></td>
                <td>${r.to}</td>
                <td>${this.scoreBar(r.strength || 0)}</td>
            </tr>`).join('') || '<tr><td colspan="4" class="mkt-empty">No relationships.</td></tr>'}</tbody></table>
        </div>`;
    },

    insightCard(insight) {
        const impactClass = insight.impact === 'high' ? 'mkt-insight-high' : insight.impact === 'medium' ? 'mkt-insight-med' : 'mkt-insight-low';
        return `<div class="mkt-insight-card ${impactClass}">
            <div class="mkt-insight-title">${insight.title || insight.insight || ''}</div>
            <div class="mkt-insight-body">${insight.description || insight.detail || ''}</div>
            ${insight.impact ? `<div class="mkt-insight-footer">${this.priorityBadge(insight.impact)} impact</div>` : ''}
        </div>`;
    },

    entityCard(entity) {
        return `<div class="mkt-entity-card">
            <div class="mkt-entity-type">${entity.type || 'entity'}</div>
            <div class="mkt-entity-name">${entity.name}</div>
            ${entity.score != null ? this.scoreBar(entity.score) : ''}
        </div>`;
    },

    scoreBar(score) {
        const pct = Math.min(100, Math.round(score * (score <= 1 ? 100 : 1)));
        const color = pct > 70 ? '#22c55e' : pct > 40 ? '#f59e0b' : '#ef4444';
        return `<div class="mkt-score-track"><div class="mkt-score-fill" style="width:${pct}%;background:${color}"></div></div>`;
    },

    // ── Recommendations ──────────────────────────────────────────────────────
    async loadRecommendations(groupId, content) {
        const [recs, hist] = await Promise.all([
            this.api(`/api/marketing/${groupId}/recommendations`),
            this.api(`/api/marketing/${groupId}/implementation-history`)
        ]);

        const pending = (recs || []).filter(r => r.status === 'pending' || !r.status);
        const inprog  = (recs || []).filter(r => r.status === 'in_progress');
        const done    = (recs || []).filter(r => r.status === 'implemented' || r.status === 'done');

        content.innerHTML = `
        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="MarketingApp.runAnalysis('${groupId}','full')">Run Full Analysis</button>
            <button class="mkt-btn" onclick="MarketingApp.implementAll('${groupId}')">Implement All Pending</button>
            <button class="mkt-btn mkt-btn-secondary" onclick="MarketingApp.runAnalysis('${groupId}','cross_channel')">Cross-Channel Insights</button>
        </div>

        ${pending.length ? `<div class="mkt-section-subtitle">Pending (${pending.length})</div>
        <div class="mkt-rec-grid">${pending.map(r => this.renderRecCard(r, groupId)).join('')}</div>` : ''}

        ${inprog.length ? `<div class="mkt-section-subtitle">In Progress (${inprog.length})</div>
        <div class="mkt-rec-grid">${inprog.map(r => this.renderRecCard(r, groupId)).join('')}</div>` : ''}

        ${done.length ? `<div class="mkt-section-subtitle">Implemented (${done.length})</div>
        <div class="mkt-rec-grid">${done.map(r => this.renderRecCard(r, groupId)).join('')}</div>` : ''}

        ${!recs.length ? '<p class="mkt-empty">No recommendations yet. Run a full analysis to generate them.</p>' : ''}

        <div class="mkt-section-subtitle">Implementation History</div>
        ${this.renderImplementationHistory(hist)}`;
    },

    renderRecCard(rec, groupId) {
        const implemented = rec.status === 'implemented' || rec.status === 'done';
        return `<div class="mkt-rec-card priority-${(rec.priority||'medium').toLowerCase()}">
            <div class="mkt-rec-header">
                <span class="mkt-rec-channel">${this.channelBadge(rec.channel)}</span>
                ${this.priorityBadge(rec.priority)}
                ${rec.estimated_impact ? `<span class="mkt-rec-impact">+${rec.estimated_impact}</span>` : ''}
            </div>
            <div class="mkt-rec-title">${rec.title}</div>
            <div class="mkt-rec-desc">${rec.description || rec.rationale || ''}</div>
            ${rec.effort ? `<div class="mkt-rec-meta">Effort: ${rec.effort}</div>` : ''}
            ${!implemented ? `<div class="mkt-rec-actions">
                <button class="mkt-btn mkt-btn-sm" onclick="MarketingApp.implementRec('${groupId}','${rec.id}')">Implement</button>
            </div>` : '<div class="mkt-rec-done">✓ Implemented</div>'}
        </div>`;
    },

    renderImplementationHistory(history) {
        if (!history || !history.length) return '<p class="mkt-empty">No implementation history.</p>';
        return `<div class="mkt-impl-list">${history.map(h => `
            <div class="mkt-impl-item">
                <div class="mkt-impl-date">${h.date || h.implemented_at || ''}</div>
                <div class="mkt-impl-title">${h.title || h.action || ''}</div>
                <div class="mkt-impl-result">${h.result || h.outcome || ''}</div>
                ${h.impact ? `<div class="mkt-impl-impact">${h.impact}</div>` : ''}
            </div>`).join('')}</div>`;
    },

    renderCompetitorSEOPanel(competitors) {
        if (!competitors || !competitors.length) return '<p class="mkt-empty">No competitor data.</p>';
        return `<div class="mkt-comp-grid">${competitors.map(c => `
            <div class="mkt-comp-card">
                <div class="mkt-comp-name">${c.name}</div>
                <div class="mkt-comp-row"><span>Domain Authority</span><span>${c.domain_authority || '—'}</span></div>
                <div class="mkt-comp-row"><span>Organic Traffic</span><span>${this.num(c.organic_traffic)}/mo</span></div>
                <div class="mkt-comp-row"><span>Keywords</span><span>${this.num(c.ranked_keywords)}</span></div>
                <div class="mkt-comp-row"><span>Backlinks</span><span>${this.num(c.backlinks)}</span></div>
                ${c.top_keywords ? `<div class="mkt-comp-kws">${c.top_keywords.slice(0,3).map(k=>`<span class="mkt-kw-chip">${k}</span>`).join('')}</div>` : ''}
            </div>`).join('')}</div>`;
    },

    renderCompetitorPaidPanel(competitors, channel) {
        if (!competitors || !competitors.length) return '<p class="mkt-empty">No competitor data.</p>';
        return `<div class="mkt-comp-grid">${competitors.map(c => {
            const paid = channel === 'google' ? c.google_ads : c.facebook_ads;
            if (!paid) return '';
            return `<div class="mkt-comp-card">
                <div class="mkt-comp-name">${c.name}</div>
                <div class="mkt-comp-row"><span>Est. Spend</span><span>${this.money(paid.estimated_spend)}/mo</span></div>
                <div class="mkt-comp-row"><span>Keywords</span><span>${this.num(paid.keywords || paid.ads_count)}</span></div>
                ${paid.avg_position ? `<div class="mkt-comp-row"><span>Avg Position</span><span>${paid.avg_position}</span></div>` : ''}
                ${paid.ad_copies ? `<div class="mkt-comp-msgs"><strong>Messaging:</strong> ${paid.ad_copies.slice(0,2).join(' · ')}</div>` : ''}
            </div>`;
        }).join('')}</div>`;
    },

    // ── API actions ──────────────────────────────────────────────────────────
    async runAnalysis(groupId, channel) {
        this.showToast(`Running ${channel} analysis…`);
        try {
            const r = await this.apiPost(`/api/marketing/${groupId}/analyze/${channel}`);
            this.showToast(r.message || 'Analysis complete.', 'success');
            this.loadSection(groupId, this.currentSection);
        } catch(e) { this.showToast('Analysis failed: ' + e.message, 'error'); }
    },

    async generatePlan(groupId, channel) {
        this.showToast(`Generating ${channel} plan…`);
        try {
            const r = await this.apiPost(`/api/marketing/${groupId}/generate-plan/${channel}`);
            this.showToast(r.message || 'Plan generated.', 'success');
        } catch(e) { this.showToast('Failed: ' + e.message, 'error'); }
    },

    async implementRec(groupId, recId) {
        this.showToast('Implementing recommendation…');
        try {
            const r = await this.apiPost(`/api/marketing/${groupId}/implement/${recId}`);
            this.showToast(r.message || 'Implemented.', 'success');
            this.loadSection(groupId, 'recommendations');
        } catch(e) { this.showToast('Failed: ' + e.message, 'error'); }
    },

    async implementAll(groupId) {
        this.showToast('Implementing all pending recommendations…');
        try {
            const recs = await this.api(`/api/marketing/${groupId}/recommendations`);
            const pending = (recs || []).filter(r => !r.status || r.status === 'pending');
            for (const rec of pending) {
                await this.apiPost(`/api/marketing/${groupId}/implement/${rec.id}`);
            }
            this.showToast(`Implemented ${pending.length} recommendation(s).`, 'success');
            this.loadSection(groupId, 'recommendations');
        } catch(e) { this.showToast('Failed: ' + e.message, 'error'); }
    },

    async buildKG(groupId) {
        this.showToast('Building knowledge graph…');
        try {
            const r = await this.apiPost(`/api/marketing/${groupId}/analyze/cross_channel`);
            this.showToast(r.message || 'Knowledge graph updated.', 'success');
            this.loadSection(groupId, 'knowledge');
        } catch(e) { this.showToast('Failed: ' + e.message, 'error'); }
    },

    // ── Chart helper ─────────────────────────────────────────────────────────
    renderChart(canvasId, type, labels, datasets, opts = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        if (this.charts[canvasId]) { try { this.charts[canvasId].destroy(); } catch(_){} }

        const defaults = {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#cbd5e1', font: { size: 12 } } }
            },
            scales: {}
        };

        if (type !== 'doughnut' && type !== 'pie') {
            defaults.scales.x = {
                ticks: { color: '#94a3b8', maxRotation: 45 },
                grid: { color: '#1e2535' }
            };
            defaults.scales.y = {
                ticks: { color: '#94a3b8' },
                grid: { color: '#1e2535' }
            };
        }

        if (opts.stacked) {
            defaults.scales.x.stacked = true;
            defaults.scales.y.stacked = true;
        }

        if (opts.dualAxis) {
            defaults.scales.y1 = {
                position: 'right',
                ticks: { color: '#22c55e' },
                grid: { drawOnChartArea: false }
            };
        }

        if (opts.horizontal) {
            defaults.indexAxis = 'y';
        }

        this.charts[canvasId] = new Chart(canvas, {
            type,
            data: { labels, datasets },
            options: defaults
        });
    },

    // ── HTTP helpers ─────────────────────────────────────────────────────────
    async api(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${url}`);
        return r.json();
    },

    async apiPost(url, body = {}) {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${url}`);
        return r.json();
    },

    // ── Toast ─────────────────────────────────────────────────────────────────
    showToast(msg, type = 'info') {
        let container = document.getElementById('mkt-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'mkt-toast-container';
            container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `mkt-toast mkt-toast-${type}`;
        toast.textContent = msg;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    },

    // ── Formatters ────────────────────────────────────────────────────────────
    money(v) {
        if (v == null || v === '') return '—';
        return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    },
    pct(v) {
        if (v == null || v === '') return '—';
        return (Number(v) * (Number(v) > 1 ? 1 : 100)).toFixed(1) + '%';
    },
    num(v, dec = 0) {
        if (v == null || v === '') return '—';
        return Number(v).toLocaleString('en-US', { maximumFractionDigits: dec });
    },

    // ── Badge helpers ─────────────────────────────────────────────────────────
    kpiCard(label, value) {
        return `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`;
    },
    channelBadge(ch) {
        const map = { seo:'SEO', google_ads:'Google Ads', facebook_ads:'Facebook Ads', cross:'Cross-Channel' };
        return `<span class="mkt-badge mkt-badge-channel">${map[ch]||ch||'—'}</span>`;
    },
    priorityBadge(p) {
        const cls = p === 'high' ? 'mkt-badge-high' : p === 'medium' ? 'mkt-badge-med' : 'mkt-badge-low';
        return `<span class="mkt-badge ${cls}">${p||'—'}</span>`;
    }
};

// ── Lazy init via MutationObserver ──────────────────────────────────────────
(function() {
    const marketingTab = document.getElementById('marketing');
    if (!marketingTab) return;

    function initBcatMarketing() {
        if (!MarketingApp._initialized) {
            MarketingApp._initialized = true;
            MarketingApp.mountTo('marketing-app', 'bcat_logistics');
        }
    }

    // If already active on load
    if (marketingTab.classList.contains('active')) {
        initBcatMarketing();
        return;
    }

    const observer = new MutationObserver(() => {
        if (marketingTab.classList.contains('active')) {
            initBcatMarketing();
        }
    });
    observer.observe(marketingTab, { attributes: true, attributeFilter: ['class'] });
})();


// ═══════════════════════════════════════════════════════════════════════════
// BestCare — Real Data Module
// Consumes /api/best-care/* endpoints.
// Falls back gracefully to placeholder messaging when data is not yet synced.
// ═══════════════════════════════════════════════════════════════════════════

const BestCare = {

    // ── Quality badge helper ────────────────────────────────────────────────
    qualityBadge(q) {
        const map = {
            ACTUAL:    ['mkt-badge-high',    'ACTUAL'],
            MODELED:   ['mkt-badge-med',     'MODELED'],
            ESTIMATED: ['mkt-badge-low',     'ESTIMATED'],
            MISSING:   ['mkt-badge',         'MISSING'],
        };
        const [cls, label] = map[q] || ['mkt-badge', q || '—'];
        return `<span class="mkt-badge ${cls}" title="Data quality: ${label}">${label}</span>`;
    },

    qualityTip(q) {
        const tips = {
            ACTUAL:    'Sourced directly from a verified integration (Google Ads API or 8x8).',
            MODELED:   'Calculated from connected data sources using an explicit formula.',
            ESTIMATED: 'Derived from configurable assumptions. May not reflect exact reality.',
            MISSING:   'No data available — sync required.',
        };
        return tips[q] || '';
    },

    kpiCard(label, value, quality) {
        const badge = quality ? this.qualityBadge(quality) : '';
        const tip   = quality ? `title="${this.qualityTip(quality)}"` : '';
        return `<div class="card bc-kpi-card" ${tip}>
            <div class="label">${label} ${badge}</div>
            <div class="value">${value}</div>
        </div>`;
    },

    // ── Sync status bar ─────────────────────────────────────────────────────
    async renderSyncBar(container) {
        let status = {};
        try { status = await MarketingApp.api('/api/best-care/sync-status'); } catch(_) {}

        const gads  = status.google_ads  || {};
        const calls = status.calls       || {};
        const comp  = status.competitors || {};

        const dot = (ok) => `<span class="bc-sync-dot ${ok ? 'bc-sync-ok' : 'bc-sync-err'}"></span>`;

        container.insertAdjacentHTML('afterbegin', `
        <div class="bc-sync-bar">
            <div class="bc-sync-items">
                <span class="bc-sync-item">
                    ${dot(gads.synced_at)} Google Ads
                    ${gads.synced_at ? `<span class="bc-sync-ts">${new Date(gads.synced_at).toLocaleDateString()}</span>` : '<span class="bc-sync-ts">Not synced</span>'}
                    ${!gads.configured ? '<span class="bc-sync-warn">⚠ Credentials missing</span>' : ''}
                </span>
                <span class="bc-sync-item">
                    ${dot(calls.synced_at)} 8x8 Calls
                    ${calls.synced_at ? `<span class="bc-sync-ts">${new Date(calls.synced_at).toLocaleDateString()}</span>` : '<span class="bc-sync-ts">Not synced</span>'}
                    ${!calls.configured ? '<span class="bc-sync-warn">⚠ Credentials missing</span>' : ''}
                </span>
                <span class="bc-sync-item">
                    ${dot(comp.synced_at)} Competitor Intel
                    ${comp.synced_at ? `<span class="bc-sync-ts">${new Date(comp.synced_at).toLocaleDateString()}</span>` : '<span class="bc-sync-ts">Not synced</span>'}
                    ${!comp.configured ? '<span class="bc-sync-warn">⚠ No API key</span>' : ''}
                </span>
            </div>
            <div class="bc-sync-actions">
                <button class="mkt-btn mkt-btn-sm" onclick="BestCare.syncAll()">Sync All</button>
                <button class="mkt-btn mkt-btn-sm mkt-btn-secondary" onclick="BestCare.openAssumptions()">Assumptions</button>
            </div>
        </div>`);
    },

    async syncAll() {
        MarketingApp.showToast('Syncing all Best Care data sources…');
        try {
            const r = await MarketingApp.apiPost('/api/best-care/sync/all');
            const ok = Object.values(r).filter(v => v && v.ok).length;
            MarketingApp.showToast(`Sync complete. ${ok} sources updated.`, 'success');
            MarketingApp.loadSection('best_care_auto', MarketingApp.currentSection);
        } catch(e) { MarketingApp.showToast('Sync failed: ' + e.message, 'error'); }
    },

    async openAssumptions() {
        let cfg = {};
        try { cfg = await MarketingApp.api('/api/best-care/assumptions'); } catch(_) {}

        MarketingApp.showToast('Assumptions editor — edit config.json or set env vars to override.', 'info');
        // Future: render a modal with editable fields
        console.log('Current assumptions:', cfg);
    },

    // ── Overview ────────────────────────────────────────────────────────────
    async loadOverview(content) {
        const [dash, syncStatus] = await Promise.all([
            MarketingApp.api('/api/best-care/dashboard').catch(() => null),
            MarketingApp.api('/api/best-care/sync-status').catch(() => ({})),
        ]);

        const monthly = (dash && dash.monthly_performance) || [];
        const quality = (dash && dash.data_quality) || {};
        const hasData = monthly.length > 0;

        content.innerHTML = `<div id="bc-sync-bar-slot"></div>` + (hasData
            ? this._overviewHTML(monthly, quality)
            : this._noDataHTML('overview'));

        await this.renderSyncBar(content);

        if (hasData) {
            this._drawOverviewCharts(monthly);
        }
    },

    _overviewHTML(monthly, quality) {
        const latest = monthly[0] || {};
        const prev   = monthly[1] || {};

        const mom = (curr, prev) => {
            if (!curr || !prev) return '';
            const delta = ((curr - prev) / prev * 100).toFixed(1);
            const cls   = delta >= 0 ? 'positive' : 'negative';
            return `<span class="${cls}" style="font-size:11px;margin-left:6px">${delta >= 0 ? '▲' : '▼'}${Math.abs(delta)}%</span>`;
        };

        return `
        <div class="mkt-section-subtitle">Monthly Performance — ${latest.month || '—'}</div>
        <div class="bc-kpi-grid">
            ${this.kpiCard('Ad Spend',        MarketingApp.money(latest.spend),        quality.spend)}
            ${this.kpiCard('Phone Calls',     MarketingApp.num(latest.total_calls),    quality.calls)}
            ${this.kpiCard('Answered Calls',  MarketingApp.num(latest.answered_calls) + (latest.answer_rate ? ` (${latest.answer_rate}%)` : ''), quality.calls)}
            ${this.kpiCard('Leads (Est.)',    MarketingApp.num(latest.leads),          quality.conversions)}
            ${this.kpiCard('Conversions',     MarketingApp.num(latest.conversions, 1), quality.conversions)}
            ${this.kpiCard('CAC',             MarketingApp.money(latest.cac),          quality.conversions)}
            ${this.kpiCard('Revenue',         MarketingApp.money(latest.revenue),      quality.revenue)}
            ${this.kpiCard('Profit',          MarketingApp.money(latest.profit),       quality.revenue)}
            ${this.kpiCard('ROAS',            latest.roas != null ? latest.roas + 'x' : '—', quality.spend)}
            ${this.kpiCard('Cost / Call',     MarketingApp.money(latest.cost_per_call), quality.spend)}
            ${this.kpiCard('Cost / Lead',     MarketingApp.money(latest.cost_per_lead), quality.conversions)}
            ${this.kpiCard('Conv. Rate',      latest.conversion_rate != null ? latest.conversion_rate + '%' : '—', quality.conversions)}
        </div>

        <div class="bc-quality-note">
            <strong>Data quality:</strong>
            Spend = ${this.qualityBadge(quality.spend)},
            Calls = ${this.qualityBadge(quality.calls)},
            Conversions = ${this.qualityBadge(quality.conversions)},
            Revenue = ${this.qualityBadge(quality.revenue)}.
            MODELED and ESTIMATED values use configurable assumptions.
            Click <strong>Assumptions</strong> to review or update them.
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Monthly Spend vs Revenue vs Profit</div>
                <canvas id="bc-spend-rev"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Calls & Conversions by Month</div>
                <canvas id="bc-calls-conv"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">CAC Trend</div>
                <canvas id="bc-cac"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">ROAS Trend</div>
                <canvas id="bc-roas"></canvas>
            </div>
        </div>

        <div class="mkt-section-subtitle">Monthly Performance Table</div>
        <div class="mkt-table-card">
            <div class="table-wrap">${this._monthlyTable(monthly)}</div>
        </div>`;
    },

    _monthlyTable(monthly) {
        if (!monthly.length) return '<p class="mkt-empty">No data.</p>';
        return `<table><thead><tr>
            <th>Month</th><th>Spend</th><th>Calls</th><th>Ans.</th><th>Leads</th>
            <th>Conv.</th><th>CAC</th><th>Revenue</th><th>Profit</th><th>ROAS</th>
            <th>Conv%</th><th>CPC</th>
        </tr></thead><tbody>
        ${monthly.map(m => `<tr>
            <td>${m.month}</td>
            <td>${MarketingApp.money(m.spend)}</td>
            <td>${MarketingApp.num(m.total_calls)}</td>
            <td>${m.answer_rate != null ? m.answer_rate + '%' : '—'}</td>
            <td>${MarketingApp.num(m.leads)}</td>
            <td>${MarketingApp.num(m.conversions, 1)}</td>
            <td>${MarketingApp.money(m.cac)}</td>
            <td>${MarketingApp.money(m.revenue)}</td>
            <td class="${m.profit > 0 ? 'positive' : ''}">${MarketingApp.money(m.profit)}</td>
            <td>${m.roas != null ? m.roas + 'x' : '—'}</td>
            <td>${m.conversion_rate != null ? m.conversion_rate + '%' : '—'}</td>
            <td>${MarketingApp.money(m.avg_cpc)}</td>
        </tr>`).join('')}
        </tbody></table>`;
    },

    _drawOverviewCharts(monthly) {
        const months  = monthly.map(m => m.month).reverse();
        const spend   = monthly.map(m => m.spend || 0).reverse();
        const revenue = monthly.map(m => m.revenue || 0).reverse();
        const profit  = monthly.map(m => m.profit || 0).reverse();
        const calls   = monthly.map(m => m.total_calls || 0).reverse();
        const conv    = monthly.map(m => m.conversions || 0).reverse();
        const cac     = monthly.map(m => m.cac || 0).reverse();
        const roas    = monthly.map(m => m.roas || 0).reverse();

        MarketingApp.renderChart('bc-spend-rev', 'bar', months, [
            { label: 'Spend',   data: spend,   backgroundColor: '#ef4444' },
            { label: 'Revenue', data: revenue, backgroundColor: '#0ea5e9' },
            { label: 'Profit',  data: profit,  backgroundColor: '#22c55e' },
        ]);

        MarketingApp.renderChart('bc-calls-conv', 'bar', months, [
            { label: 'Total Calls',  data: calls, backgroundColor: '#6366f1', yAxisID: 'y' },
            { label: 'Conversions',  data: conv,  type: 'line',
              borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.15)', fill: false, yAxisID: 'y1' },
        ], { dualAxis: true });

        MarketingApp.renderChart('bc-cac', 'line', months, [
            { label: 'CAC ($)', data: cac, borderColor: '#f59e0b',
              backgroundColor: 'rgba(245,158,11,0.15)', fill: true },
        ]);

        MarketingApp.renderChart('bc-roas', 'line', months, [
            { label: 'ROAS', data: roas, borderColor: '#a78bfa',
              backgroundColor: 'rgba(167,139,250,0.15)', fill: true },
        ]);
    },

    // ── Google Ads real-data view ────────────────────────────────────────────
    async loadGoogleAds(content) {
        const [monthly, campaigns, keywords] = await Promise.all([
            MarketingApp.api('/api/best-care/google-ads/monthly').catch(() => []),
            MarketingApp.api('/api/best-care/google-ads/campaigns').catch(() => []),
            MarketingApp.api('/api/best-care/google-ads/keywords').catch(() => []),
        ]);

        content.innerHTML = `<div id="bc-sync-bar-slot"></div>` + (monthly.length
            ? this._gadsHTML(monthly, campaigns, keywords)
            : this._noDataHTML('google_ads'));

        await this.renderSyncBar(content);
        if (monthly.length) this._drawGadsCharts(monthly);
    },

    _gadsHTML(monthly, campaigns, keywords) {
        const latest = monthly[0] || {};

        // Wasted spend keywords
        const wasted = keywords.filter(k => k.cost > 100 && k.conversions === 0)
                               .sort((a, b) => b.cost - a.cost).slice(0, 20);
        const wastedTotal = wasted.reduce((s, k) => s + k.cost, 0);

        // Top converting keywords
        const topConv = [...keywords].sort((a, b) => b.conversions - a.conversions).slice(0, 20);

        // Campaign drilldown from most recent month
        const latestMonth = latest.month ? latest.month.slice(0, 7) : '';
        const latestCampaigns = campaigns.filter(c => c.month && c.month.startsWith(latestMonth));

        return `
        <div class="mkt-kpi-grid">
            ${this.kpiCard('Spend', MarketingApp.money(latest.spend), 'ACTUAL')}
            ${this.kpiCard('Clicks', MarketingApp.num(latest.clicks), 'ACTUAL')}
            ${this.kpiCard('Impressions', MarketingApp.num(latest.impressions), 'ACTUAL')}
            ${this.kpiCard('CTR', latest.ctr + '%', 'ACTUAL')}
            ${this.kpiCard('Avg CPC', MarketingApp.money(latest.avg_cpc), 'ACTUAL')}
            ${this.kpiCard('Conversions', MarketingApp.num(latest.conversions, 1), 'ACTUAL')}
            ${latest.roas ? this.kpiCard('ROAS', latest.roas + 'x', 'ACTUAL') : ''}
            ${latest.cost_per_conv ? this.kpiCard('Cost/Conv.', MarketingApp.money(latest.cost_per_conv), 'ACTUAL') : ''}
        </div>

        <div class="mkt-chart-grid">
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Monthly Spend</div>
                <canvas id="bc-gads-spend"></canvas>
            </div>
            <div class="mkt-chart-card">
                <div class="mkt-chart-title">Clicks & Conversions</div>
                <canvas id="bc-gads-clicks"></canvas>
            </div>
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Campaign Performance — ${latestMonth || 'All'}</div>
            <div class="table-wrap">${this._campaignTable(latestCampaigns)}</div>
        </div>

        ${wastedTotal > 0 ? `
        <div class="bc-alert bc-alert-warn">
            <strong>⚠ Wasted Spend Alert:</strong> ${wasted.length} keywords spent
            ${MarketingApp.money(wastedTotal)} with 0 conversions.
            <button class="mkt-btn mkt-btn-sm" style="margin-left:12px"
                onclick="BestCare.generateAndQueueNegatives()">Queue as Negatives</button>
        </div>` : ''}

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Zero-Conversion Keywords (wasted spend)</div>
            <div class="table-wrap">${this._kwTable(wasted)}</div>
        </div>

        <div class="mkt-table-card">
            <div class="mkt-chart-title">Top Converting Keywords</div>
            <div class="table-wrap">${this._kwTable(topConv)}</div>
        </div>

        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="BestCare.syncGoogleAds()">Sync Google Ads</button>
            <button class="mkt-btn mkt-btn-secondary"
                onclick="BestCare.generateRecs()">Generate Recommendations</button>
        </div>`;
    },

    _campaignTable(campaigns) {
        if (!campaigns.length) return '<p class="mkt-empty">No campaign data for this month.</p>';
        return `<table><thead><tr>
            <th>Campaign</th><th>Spend</th><th>Impr.</th><th>Clicks</th>
            <th>CTR</th><th>CPC</th><th>Conv.</th><th>Cost/Conv.</th><th>ROAS</th>
        </tr></thead><tbody>${campaigns.map(c => `<tr>
            <td>${c.campaign_name}</td>
            <td>${MarketingApp.money(c.cost)}</td>
            <td>${MarketingApp.num(c.impressions)}</td>
            <td>${MarketingApp.num(c.clicks)}</td>
            <td>${c.ctr}%</td>
            <td>${MarketingApp.money(c.avg_cpc)}</td>
            <td>${MarketingApp.num(c.conversions, 1)}</td>
            <td>${MarketingApp.money(c.cost_per_conv)}</td>
            <td>${c.conversion_value > 0 && c.cost > 0 ? (c.conversion_value / c.cost).toFixed(2) + 'x' : '—'}</td>
        </tr>`).join('')}</tbody></table>`;
    },

    _kwTable(keywords) {
        if (!keywords.length) return '<p class="mkt-empty">No keyword data.</p>';
        return `<table><thead><tr>
            <th>Keyword</th><th>Match</th><th>Campaign</th>
            <th>Spend</th><th>Clicks</th><th>Conv.</th><th>Cost/Conv.</th><th>QS</th>
        </tr></thead><tbody>${keywords.map(k => `<tr>
            <td>${k.keyword}</td>
            <td><span class="mkt-badge">${k.match_type || '—'}</span></td>
            <td>${k.campaign || '—'}</td>
            <td class="${k.conversions === 0 && k.cost > 100 ? 'bc-wasted' : ''}">${MarketingApp.money(k.cost)}</td>
            <td>${MarketingApp.num(k.clicks)}</td>
            <td>${MarketingApp.num(k.conversions, 1)}</td>
            <td>${MarketingApp.money(k.cost_per_conv)}</td>
            <td>${k.quality_score || '—'}</td>
        </tr>`).join('')}</tbody></table>`;
    },

    _drawGadsCharts(monthly) {
        const months = monthly.map(m => m.month).reverse();
        MarketingApp.renderChart('bc-gads-spend', 'bar', months, [
            { label: 'Spend ($)', data: monthly.map(m => m.spend || 0).reverse(),
              backgroundColor: '#ef4444' },
        ]);
        MarketingApp.renderChart('bc-gads-clicks', 'bar', months, [
            { label: 'Clicks', data: monthly.map(m => m.clicks || 0).reverse(),
              backgroundColor: '#6366f1', yAxisID: 'y' },
            { label: 'Conversions', data: monthly.map(m => m.conversions || 0).reverse(),
              type: 'line', borderColor: '#22c55e', fill: false, yAxisID: 'y1' },
        ], { dualAxis: true });
    },

    async syncGoogleAds() {
        MarketingApp.showToast('Syncing Google Ads…');
        try {
            const r = await MarketingApp.apiPost('/api/best-care/sync/google-ads');
            if (r.ok) {
                MarketingApp.showToast(`Google Ads synced. ${r.records} months.`, 'success');
                MarketingApp.loadSection('best_care_auto', 'google_ads');
            } else {
                MarketingApp.showToast('Sync failed: ' + r.error, 'error');
            }
        } catch(e) { MarketingApp.showToast('Sync error: ' + e.message, 'error'); }
    },

    async generateAndQueueNegatives() {
        MarketingApp.showToast('Generating negatives recommendation…');
        try {
            await MarketingApp.apiPost('/api/best-care/recommendations/generate');
            MarketingApp.showToast('Recommendations generated.', 'success');
            MarketingApp.loadSection('best_care_auto', 'recommendations');
        } catch(e) { MarketingApp.showToast('Failed: ' + e.message, 'error'); }
    },

    // ── Recommendations real-data view ───────────────────────────────────────
    async loadRecommendations(content) {
        const [recs, queue] = await Promise.all([
            MarketingApp.api('/api/best-care/recommendations').catch(() => []),
            MarketingApp.api('/api/best-care/implementation-queue').catch(() => []),
        ]);

        content.innerHTML = `<div id="bc-sync-bar-slot"></div>` + this._recsHTML(recs, queue);
        await this.renderSyncBar(content);
    },

    _recsHTML(recs, queue) {
        const pending    = recs.filter(r => r.status === 'pending');
        const done       = recs.filter(r => r.status === 'implemented');
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        pending.sort((a, b) => (priorityOrder[a.priority] || 9) - (priorityOrder[b.priority] || 9));

        return `
        <div class="mkt-action-bar">
            <button class="mkt-btn" onclick="BestCare.generateRecs()">Generate Recommendations</button>
            <button class="mkt-btn" onclick="BestCare.implementAllRecs()">Implement All Pending</button>
        </div>

        ${pending.length ? `
        <div class="mkt-section-subtitle">Pending Recommendations (${pending.length})</div>
        <div class="mkt-rec-grid">${pending.map(r => this._recCard(r)).join('')}</div>` : ''}

        ${done.length ? `
        <div class="mkt-section-subtitle">Implemented (${done.length})</div>
        <div class="mkt-rec-grid">${done.map(r => this._recCard(r)).join('')}</div>` : ''}

        ${!recs.length ? `
        <div class="mkt-empty">No recommendations yet. Sync data first, then click Generate.</div>` : ''}

        ${queue.length ? `
        <div class="mkt-section-subtitle">Implementation Queue (${queue.length})</div>
        <div class="mkt-table-card">
            <div class="table-wrap">${this._queueTable(queue)}</div>
        </div>` : ''}`;
    },

    _recCard(rec) {
        const done = rec.status === 'implemented';
        const ci   = rec.competitor_insight;
        return `<div class="mkt-rec-card priority-${rec.priority || 'medium'}">
            <div class="mkt-rec-header">
                ${MarketingApp.channelBadge(rec.channel)}
                ${MarketingApp.priorityBadge(rec.priority)}
                <span class="mkt-badge" title="Confidence">${rec.confidence || '—'}</span>
                <span class="mkt-badge mkt-badge-channel">${rec.difficulty || '—'} effort</span>
                ${rec.source === 'live' ? '<span class="bc-live-badge">LIVE DATA</span>' : ''}
            </div>
            <div class="mkt-rec-title">${rec.title}</div>
            <div class="mkt-rec-desc">${rec.rationale || ''}</div>
            ${ci ? `<div class="bc-comp-insight">
                <strong>Competitor insight:</strong>
                ${ci.theme ? `"${ci.theme}" used by ${ci.prevalence_pct || 0}% of competitors.` : ''}
                ${ci.domain ? `${ci.domain} — ${ci.ad_count || 0} ads observed.` : ''}
            </div>` : ''}
            ${rec.expected_impact ? `<div class="bc-impact">
                ${Object.entries(rec.expected_impact).filter(([,v]) => v).map(([k, v]) =>
                    `<span class="bc-impact-item">${k.replace(/_/g,' ')}: ${v > 0 ? '+' : ''}${v}${k.includes('pct') ? '%' : ''}</span>`
                ).join('')}
            </div>` : ''}
            ${!done ? `<div class="mkt-rec-actions">
                <button class="mkt-btn mkt-btn-sm"
                    onclick="BestCare.implementRec('${rec.id}')">Implement</button>
            </div>` : '<div class="mkt-rec-done">✓ Implemented</div>'}
        </div>`;
    },

    _queueTable(queue) {
        return `<table><thead><tr>
            <th>ID</th><th>Action</th><th>Status</th><th>Queued</th><th>Result</th>
        </tr></thead><tbody>${queue.map(a => `<tr>
            <td style="font-size:11px;color:#6b7280">${a.id}</td>
            <td>${a.action_type}</td>
            <td><span class="mkt-badge mkt-badge-${a.status === 'completed' ? 'high' : a.status === 'failed' ? '' : 'med'}">${a.status}</span></td>
            <td style="font-size:11px">${a.queued_at ? new Date(a.queued_at).toLocaleString() : '—'}</td>
            <td style="font-size:11px;color:#94a3b8">${a.result ? (a.result.message || '') : '—'}</td>
        </tr>`).join('')}</tbody></table>`;
    },

    async generateRecs() {
        MarketingApp.showToast('Generating recommendations from live data…');
        try {
            const r = await MarketingApp.apiPost('/api/best-care/recommendations/generate');
            MarketingApp.showToast(`Generated ${r.count} recommendations.`, 'success');
            MarketingApp.loadSection('best_care_auto', 'recommendations');
        } catch(e) { MarketingApp.showToast('Failed: ' + e.message, 'error'); }
    },

    async implementRec(recId) {
        MarketingApp.showToast('Queueing implementation…');
        try {
            const r = await MarketingApp.apiPost(`/api/best-care/recommendations/${recId}/implement`,
                { action_type: 'generic' });
            MarketingApp.showToast(r.result ? r.result.message : 'Queued.', 'success');
            MarketingApp.loadSection('best_care_auto', 'recommendations');
        } catch(e) { MarketingApp.showToast('Failed: ' + e.message, 'error'); }
    },

    async implementAllRecs() {
        try {
            const recs = await MarketingApp.api('/api/best-care/recommendations');
            const pending = recs.filter(r => r.status === 'pending');
            for (const rec of pending) {
                await MarketingApp.apiPost(`/api/best-care/recommendations/${rec.id}/implement`,
                    { action_type: 'generic' });
            }
            MarketingApp.showToast(`Implemented ${pending.length} recommendation(s).`, 'success');
            MarketingApp.loadSection('best_care_auto', 'recommendations');
        } catch(e) { MarketingApp.showToast('Failed: ' + e.message, 'error'); }
    },

    // ── Scoped mount (for Ivan / Best Care panels) ──────────────────────────
    mountTo(containerId, groupId) {
        const app = document.getElementById(containerId);
        if (!app) return;
        this.currentGroup = groupId;
        this.currentSection = 'overview';

        const sectionBtns = this.sections.map(s =>
            `<button class="mkt-section-btn${s.id === this.currentSection ? ' active' : ''}"
                     data-section="${s.id}">${s.label}</button>`
        ).join('');

        app.innerHTML = `
        <div class="mkt-shell" data-mount-container="${containerId}">
            <div class="mkt-section-nav">${sectionBtns}</div>
            <div id="mkt-content-${containerId}" class="mkt-content"></div>
        </div>`;

        // Bind section tabs scoped to this container
        app.querySelectorAll('.mkt-section-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                app.querySelectorAll('.mkt-section-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSection = btn.dataset.section;
                this._loadSectionInto('mkt-content-' + containerId, groupId, this.currentSection);
            });
        });

        this._loadSectionInto('mkt-content-' + containerId, groupId, this.currentSection);
    },

    _loadSectionInto(contentId, groupId, section) {
        // Temporarily swap the content div ID so loadSection targets it
        const real = document.getElementById('mkt-content');
        const target = document.getElementById(contentId);
        if (!target) return;
        if (real) real.id = '_mkt-content-hidden';
        target.id = 'mkt-content';
        const prevGroup = this.currentGroup;
        this.currentGroup = groupId;
        this.loadSection(groupId, section);
        this.currentGroup = prevGroup;
        target.id = contentId;
        if (real) real.id = 'mkt-content';
    },

    // ── No-data placeholder ─────────────────────────────────────────────────
    _noDataHTML(section) {
        return `
        <div class="bc-no-data">
            <div class="bc-no-data-icon">⚡</div>
            <div class="bc-no-data-title">No real data synced yet for ${section}.</div>
            <div class="bc-no-data-body">
                Click <strong>Sync All</strong> above to pull live data from Google Ads and 8x8.
                Make sure credentials are configured in <code>.env</code> first.
            </div>
        </div>`;
    },
};
