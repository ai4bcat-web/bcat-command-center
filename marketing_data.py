"""
Marketing mock data layer for all 3 business groups.
Replace individual data sections with live API calls as integrations come online.
AUTO_APPROVE_MARKETING_ACTIONS controls whether recommendations run unattended.
"""

AUTO_APPROVE_MARKETING_ACTIONS = True

MONTHS = [
    "2025-04","2025-05","2025-06","2025-07","2025-08","2025-09",
    "2025-10","2025-11","2025-12","2026-01","2026-02","2026-03"
]

def mts(values):
    return [{"month": m, "value": v} for m, v in zip(MONTHS, values)]

# ---------------------------------------------------------------------------
# BCAT LOGISTICS
# ---------------------------------------------------------------------------
_bcat = {
    "id": "bcat_logistics",
    "name": "BCAT Logistics",
    "short_name": "BCAT",
    "website": "bcatlogistics.com",
    "industry": "Freight Brokerage",
    "overview": {
        "total_leads": 428,
        "total_conversions": 64,
        "conversion_rate": 15.0,
        "cost_per_lead": 48.20,
        "cost_per_conversion": 321.50,
        "total_ad_spend": 20580,
        "roas": 4.2,
        "ctr": 3.8,
        "cpc": 9.40,
        "cpm": 26.80,
        "organic_traffic": 11400,
        "paid_traffic": 4200,
        "top_channels": [
            {"name":"Google Ads","leads":186,"conversions":28,"spend":12400},
            {"name":"Organic SEO","leads":142,"conversions":22,"spend":0},
            {"name":"Facebook Ads","leads":68,"conversions":9,"spend":5200},
            {"name":"Direct / Referral","leads":32,"conversions":5,"spend":0},
        ],
        "top_campaigns": [
            {"name":"Freight Broker | Brand","channel":"Google Ads","leads":54,"conversions":9,"spend":2800,"roas":5.6},
            {"name":"Freight Broker | Non-Brand","channel":"Google Ads","leads":82,"conversions":11,"spend":6200,"roas":3.8},
            {"name":"LTL Shipping","channel":"Google Ads","leads":32,"conversions":5,"spend":2100,"roas":3.2},
            {"name":"Retargeting","channel":"Facebook Ads","leads":28,"conversions":4,"spend":1400,"roas":4.0},
            {"name":"B2B Lookalike","channel":"Facebook Ads","leads":24,"conversions":3,"spend":2100,"roas":3.1},
        ],
        "top_landing_pages": [
            {"url":"/freight-quote","sessions":3100,"leads":84,"conv_rate":2.71},
            {"url":"/freight-broker-services","sessions":2400,"leads":52,"conv_rate":2.17},
            {"url":"/ltl-shipping","sessions":1800,"leads":38,"conv_rate":2.11},
            {"url":"/truckload-shipping","sessions":1200,"leads":22,"conv_rate":1.83},
        ],
        "funnel_stages": [
            {"stage":"Impressions","count":540000},
            {"stage":"Clicks","count":20500},
            {"stage":"Sessions","count":15600},
            {"stage":"Leads","count":428},
            {"stage":"Qualified","count":128},
            {"stage":"Converted","count":64},
        ],
        "leads_over_time": mts([28,32,35,38,41,44,36,33,38,42,48,53]),
        "conversions_over_time": mts([4,5,5,6,6,7,5,4,6,6,7,8]),
        "spend_over_time": mts([1200,1400,1600,1800,1900,2100,1600,1400,1700,1900,2200,2480]),
        "roas_over_time": mts([3.8,3.9,4.0,4.1,4.2,4.5,4.0,3.7,4.1,4.2,4.4,4.6]),
        "traffic_by_source": [
            {"source":"Organic","value":11400},
            {"source":"Google Ads","value":4200},
            {"source":"Facebook","value":1800},
            {"source":"Direct","value":2100},
            {"source":"Referral","value":900},
        ],
    },
    "seo": {
        "health_score": 72,
        "organic_traffic": 11400,
        "keywords_ranked": 284,
        "top_3_rankings": 18,
        "avg_position": 14.2,
        "keyword_rankings": [
            {"keyword":"freight broker","position":8,"volume":12100,"difficulty":68,"opportunity_score":72},
            {"keyword":"freight brokerage services","position":5,"volume":4400,"difficulty":58,"opportunity_score":81},
            {"keyword":"ltl freight broker","position":12,"volume":2900,"difficulty":52,"opportunity_score":76},
            {"keyword":"truckload freight broker","position":14,"volume":2400,"difficulty":55,"opportunity_score":70},
            {"keyword":"freight quote online","position":11,"volume":3600,"difficulty":48,"opportunity_score":79},
            {"keyword":"shipping rates","position":22,"volume":18100,"difficulty":72,"opportunity_score":58},
            {"keyword":"freight shipping company","position":18,"volume":5400,"difficulty":61,"opportunity_score":65},
            {"keyword":"full truckload shipping","position":9,"volume":1900,"difficulty":44,"opportunity_score":82},
        ],
        "keyword_opportunities": [
            {"keyword":"freight broker near me","volume":8100,"difficulty":46,"competitor_ranking":"Echo Global #3","gap_score":88},
            {"keyword":"best freight broker","volume":5400,"difficulty":51,"competitor_ranking":"Coyote #2","gap_score":84},
            {"keyword":"ftl freight rates","volume":3200,"difficulty":43,"competitor_ranking":"GlobalTranz #4","gap_score":80},
            {"keyword":"intermodal freight broker","volume":2700,"difficulty":39,"competitor_ranking":"Echo Global #5","gap_score":77},
            {"keyword":"refrigerated freight broker","volume":1800,"difficulty":35,"competitor_ranking":"Not ranked","gap_score":91},
            {"keyword":"expedited freight services","volume":2200,"difficulty":41,"competitor_ranking":"Coyote #6","gap_score":74},
        ],
        "technical_issues": [
            {"issue":"Missing meta descriptions","severity":"medium","count":24},
            {"issue":"Slow page speed (>3s LCP)","severity":"high","count":6},
            {"issue":"Broken internal links","severity":"medium","count":11},
            {"issue":"Missing schema markup","severity":"low","count":38},
            {"issue":"Duplicate title tags","severity":"medium","count":8},
            {"issue":"Images missing alt text","severity":"low","count":52},
        ],
        "top_pages": [
            {"url":"/freight-quote","sessions":3100,"leads":84,"conv_rate":2.71,"avg_position":6.2},
            {"url":"/freight-broker-services","sessions":2400,"leads":52,"conv_rate":2.17,"avg_position":8.4},
            {"url":"/ltl-shipping","sessions":1800,"leads":38,"conv_rate":2.11,"avg_position":11.1},
            {"url":"/blog/freight-rates-guide","sessions":1400,"leads":12,"conv_rate":0.86,"avg_position":4.1},
        ],
        "ranking_distribution": {"top3":18,"top10":54,"top20":98,"top50":172,"beyond50":112},
        "organic_traffic_trend": mts([820,880,920,1010,1080,1120,980,940,1020,1080,1180,1370]),
        "ctr_trend": mts([3.1,3.2,3.4,3.5,3.6,3.8,3.4,3.3,3.6,3.7,3.9,4.1]),
        "impressions_trend": mts([26000,28000,27000,30000,30000,29500,28000,28500,28400,29200,30200,33500]),
    },
    "google_ads": {
        "spend": 12400,
        "conversions": 28,
        "cpc": 9.40,
        "ctr": 4.1,
        "roas": 4.8,
        "cpa": 442.86,
        "quality_score_avg": 6.8,
        "impression_share": 38.4,
        "campaigns": [
            {"name":"Brand | Freight Broker","spend":2800,"conversions":9,"cpc":5.20,"ctr":8.4,"roas":5.6,"cpa":311,"status":"active"},
            {"name":"Non-Brand | Freight Brokerage","spend":6200,"conversions":11,"cpc":11.80,"ctr":3.2,"roas":3.8,"cpa":563,"status":"active"},
            {"name":"LTL Shipping","spend":2100,"conversions":5,"cpc":9.90,"ctr":3.8,"roas":3.2,"cpa":420,"status":"active"},
            {"name":"Competitor Conquest","spend":980,"conversions":2,"cpc":14.20,"ctr":2.1,"roas":2.8,"cpa":490,"status":"paused"},
            {"name":"Remarketing","spend":320,"conversions":1,"cpc":3.80,"ctr":1.4,"roas":4.1,"cpa":320,"status":"active"},
        ],
        "keywords": [
            {"keyword":"freight broker","match_type":"exact","spend":2100,"clicks":188,"conversions":5,"cpc":11.17,"quality_score":8,"status":"active"},
            {"keyword":"freight brokerage","match_type":"phrase","spend":1840,"clicks":162,"conversions":4,"cpc":11.36,"quality_score":7,"status":"active"},
            {"keyword":"shipping broker","match_type":"broad","spend":920,"clicks":148,"conversions":1,"cpc":6.22,"quality_score":5,"status":"active"},
            {"keyword":"transport company","match_type":"broad","spend":680,"clicks":210,"conversions":0,"cpc":3.24,"quality_score":4,"status":"flagged"},
            {"keyword":"logistics company","match_type":"broad","spend":540,"clicks":180,"conversions":0,"cpc":3.00,"quality_score":4,"status":"flagged"},
            {"keyword":"ltl freight","match_type":"exact","spend":1200,"clicks":102,"conversions":3,"cpc":11.76,"quality_score":7,"status":"active"},
        ],
        "wasted_spend": {
            "total": 1740,
            "items": [
                {"keyword":"transport company","spend":680,"reason":"Zero conversions, low quality score, broad intent"},
                {"keyword":"logistics company","spend":540,"reason":"Zero conversions, brand awareness only"},
                {"keyword":"shipping broker","spend":520,"reason":"Low conversion rate vs CPC"},
            ]
        },
        "search_terms": [
            {"term":"freight broker services","impressions":1840,"clicks":82,"conversions":3,"intent":"commercial"},
            {"term":"how to find a freight broker","impressions":1200,"clicks":38,"conversions":0,"intent":"informational"},
            {"term":"freight broker near me","impressions":980,"clicks":54,"conversions":2,"intent":"local"},
            {"term":"best freight broker rates","impressions":860,"clicks":44,"conversions":2,"intent":"commercial"},
            {"term":"freight broker vs carrier","impressions":640,"clicks":28,"conversions":0,"intent":"informational"},
        ],
        "spend_trend": mts([820,980,1100,1200,1280,1420,1100,980,1120,1200,1380,1820]),
        "conversions_trend": mts([2,2,3,3,3,4,2,2,3,2,3,3]),
        "roas_trend": mts([4.1,4.2,4.3,4.5,4.6,4.9,4.4,4.0,4.5,4.6,4.7,5.2]),
        "cpa_trend": mts([490,520,468,452,440,418,470,510,460,455,428,408]),
        "ctr_trend": mts([3.6,3.7,3.9,4.0,4.1,4.4,3.8,3.6,4.0,4.1,4.2,4.5]),
    },
    "facebook_ads": {
        "spend": 5200,
        "leads": 68,
        "conversions": 9,
        "cpm": 28.40,
        "cpc": 3.82,
        "ctr": 1.34,
        "cpa": 577.78,
        "roas": 2.9,
        "reach": 183000,
        "frequency": 2.4,
        "campaigns": [
            {"name":"Retargeting | Website Visitors","spend":1400,"leads":28,"conversions":4,"cpm":22.10,"cpc":2.60,"ctr":1.8,"cpa":350,"status":"active"},
            {"name":"B2B Lookalike | Shippers","spend":2100,"leads":24,"conversions":3,"cpm":31.20,"cpc":4.40,"ctr":1.2,"cpa":700,"status":"active"},
            {"name":"Cold | Manufacturing","spend":1100,"leads":12,"conversions":1,"cpm":29.80,"cpc":4.10,"ctr":1.1,"cpa":1100,"status":"active"},
            {"name":"Cold | Distribution","spend":600,"leads":4,"conversions":1,"cpm":34.20,"cpc":5.20,"ctr":0.9,"cpa":600,"status":"paused"},
        ],
        "creatives": [
            {"name":"Quote Calculator CTA","format":"single_image","spend":1800,"impressions":63000,"clicks":1020,"leads":26,"ctr":1.62,"cpa":692,"fatigue_score":28},
            {"name":"Cost-Per-Mile Savings Hook","format":"video","spend":1400,"impressions":49000,"clicks":730,"leads":18,"ctr":1.49,"cpa":778,"fatigue_score":41},
            {"name":"Shipper Testimonial","format":"carousel","spend":1100,"impressions":38000,"clicks":480,"leads":14,"ctr":1.26,"cpa":786,"fatigue_score":62},
            {"name":"24/7 Support Angle","format":"single_image","spend":900,"impressions":31000,"clicks":370,"leads":10,"ctr":1.19,"cpa":900,"fatigue_score":74},
        ],
        "audiences": [
            {"name":"Website Retargeting (30d)","type":"retargeting","spend":1400,"leads":28,"cpa":50,"performance_score":88},
            {"name":"Lookalike 1% (Customers)","type":"lookalike","spend":2100,"leads":24,"cpa":88,"performance_score":72},
            {"name":"Manufacturing Interest","type":"interest","spend":1100,"leads":12,"cpa":92,"performance_score":61},
            {"name":"Distribution & Logistics","type":"interest","spend":600,"leads":4,"cpa":150,"performance_score":38},
        ],
        "funnel_breakdown": [
            {"stage":"Reach","impressions":183000,"rate":100},
            {"stage":"Impression","impressions":183000,"rate":100},
            {"stage":"Click","impressions":2460,"rate":1.34},
            {"stage":"Lead","impressions":68,"rate":2.76},
            {"stage":"Converted","impressions":9,"rate":13.24},
        ],
        "spend_trend": mts([310,380,420,480,510,560,430,390,450,500,590,680]),
        "leads_trend": mts([4,5,6,6,7,8,5,4,6,7,8,10]),
        "cpm_trend": mts([24.2,25.1,26.4,27.8,28.4,30.1,27.2,26.8,27.9,28.2,29.4,31.0]),
        "cpa_trend": mts([640,620,590,580,560,540,590,610,570,555,530,510]),
    },
    "competitors": [
        {
            "name": "Echo Global Logistics",
            "domain": "echogloballogistics.com",
            "visibility_score": 84,
            "estimated_monthly_traffic": 98000,
            "seo": {
                "keywords_ranking": 1840,
                "top_keywords": [
                    {"kw":"freight broker","position":2,"volume":12100},
                    {"kw":"freight broker near me","position":3,"volume":8100},
                    {"kw":"shipping rates","position":6,"volume":18100},
                ],
                "content_strategy": "Heavy blog content on freight market trends, rate guides, and industry news. Dedicated service pages per freight mode.",
                "page_types": ["service pages","rate calculators","blog/guides","case studies","carrier network pages"],
            },
            "google_ads": {
                "visibility": 72,
                "ad_examples": [
                    {"headline":"Echo Freight Broker | Get Instant Rates","description":"Compare 50,000+ carriers. Book in minutes. Save up to 30% on shipping costs.","cta":"Get a Free Quote"},
                    {"headline":"Freight Brokerage Services | Echo Global","description":"Award-winning freight broker. Trusted by 30,000+ shippers nationwide.","cta":"Start Shipping"},
                ],
                "top_keywords": ["freight broker","freight brokerage","shipping quotes","ltl shipping"],
                "estimated_spend": 42000,
                "messaging_themes": ["carrier network size","cost savings","speed/technology","trust/awards"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Cut Shipping Costs by 30%","format":"video","hook":"Are you overpaying for freight?","offer":"Free rate comparison"},
                    {"headline":"50,000+ Carriers, One Platform","format":"carousel","hook":"Stop calling around. Book freight online.","offer":"Free quote tool"},
                ],
                "messaging_themes": ["cost savings","technology platform","carrier access","shipper testimonials"],
                "creative_types": ["video","carousel","single image"],
            },
            "strengths": ["brand recognition","carrier network scale","technology platform","content volume"],
            "weaknesses": ["generic messaging","high CPC spend","slow landing pages","weak local SEO"],
            "opportunity_gaps": ["refrigerated freight","local market pages","niche industry verticals"],
        },
        {
            "name": "GlobalTranz",
            "domain": "globaltranz.com",
            "visibility_score": 78,
            "estimated_monthly_traffic": 74000,
            "seo": {
                "keywords_ranking": 1420,
                "top_keywords": [
                    {"kw":"freight logistics","position":3,"volume":9900},
                    {"kw":"truckload freight","position":4,"volume":5400},
                    {"kw":"ltl freight broker","position":4,"volume":2900},
                ],
                "content_strategy": "Strong TMS/technology angle. Targets mid-market shippers with supply chain content.",
                "page_types": ["technology pages","case studies","service pages","whitepapers","ROI calculators"],
            },
            "google_ads": {
                "visibility": 61,
                "ad_examples": [
                    {"headline":"Freight Logistics Platform | GlobalTranz","description":"Manage all your freight in one TMS. LTL, FTL, intermodal.","cta":"Get a Demo"},
                    {"headline":"Cut Freight Costs | Smart TMS","description":"GlobalTranz technology reduces freight spend by 15-25%.","cta":"See the ROI"},
                ],
                "top_keywords": ["freight management","tms software","freight logistics","truckload rates"],
                "estimated_spend": 28000,
                "messaging_themes": ["technology/TMS","cost reduction","ROI","supply chain visibility"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Freight Management Made Simple","format":"single_image","hook":"One platform for all your freight.","offer":"Free TMS demo"},
                ],
                "messaging_themes": ["technology differentiation","supply chain control","shipper ROI"],
                "creative_types": ["single image","video"],
            },
            "strengths": ["technology angle","TMS differentiation","mid-market focus","ROI messaging"],
            "weaknesses": ["complex sales cycle","lower ad spend in paid search","weak brand search volume"],
            "opportunity_gaps": ["small business segment","spot freight","real-time rate quoting"],
        },
        {
            "name": "Coyote Logistics",
            "domain": "coyote.com",
            "visibility_score": 81,
            "estimated_monthly_traffic": 88000,
            "seo": {
                "keywords_ranking": 1680,
                "top_keywords": [
                    {"kw":"best freight broker","position":2,"volume":5400},
                    {"kw":"coyote freight","position":1,"volume":3600},
                    {"kw":"freight carrier rates","position":5,"volume":4400},
                ],
                "content_strategy": "Brand-heavy. Strong market data and freight rate indices as SEO hooks. Guest posting strategy.",
                "page_types": ["market data pages","rate index","press/media","service pages","carrier pages"],
            },
            "google_ads": {
                "visibility": 66,
                "ad_examples": [
                    {"headline":"Coyote Freight | Reliable Shipping","description":"Same-day coverage. Expert freight brokers. Trusted by Fortune 500.","cta":"Get Quote Now"},
                    {"headline":"Best Freight Broker | Coyote","description":"Consistent capacity. Competitive rates. Book freight instantly online.","cta":"Ship Now"},
                ],
                "top_keywords": ["freight broker","best freight broker","freight carrier","shipping carrier"],
                "estimated_spend": 35000,
                "messaging_themes": ["reliability","Fortune 500 trust","carrier relationships","speed"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Freight Without the Headache","format":"video","hook":"Tired of capacity issues?","offer":"99.4% on-time delivery"},
                    {"headline":"Book Freight in 60 Seconds","format":"single_image","hook":"Instant online booking.","offer":"Free spot quote"},
                ],
                "messaging_themes": ["reliability","speed of booking","carrier network","on-time performance"],
                "creative_types": ["video","single image","stories"],
            },
            "strengths": ["brand awareness","reliability messaging","Fortune 500 credibility","carrier network"],
            "weaknesses": ["premium pricing perception","complex onboarding","website UX friction"],
            "opportunity_gaps": ["SMB shippers","regional freight","same-day/urgent freight"],
        },
        {
            "name": "MoLo Solutions",
            "domain": "molosolutions.com",
            "visibility_score": 54,
            "estimated_monthly_traffic": 22000,
            "seo": {
                "keywords_ranking": 480,
                "top_keywords": [
                    {"kw":"freight broker chicago","position":2,"volume":1200},
                    {"kw":"dry van freight broker","position":4,"volume":1800},
                ],
                "content_strategy": "Regional + niche focus. Strong local SEO in Chicago market. Dry van specialist pages.",
                "page_types": ["local service pages","dry van pages","blog","about/team"],
            },
            "google_ads": {
                "visibility": 38,
                "ad_examples": [
                    {"headline":"MoLo Freight Broker | Chicago Based","description":"Local market knowledge. National carrier network. Personal service.","cta":"Call Now"},
                ],
                "top_keywords": ["freight broker chicago","dry van freight"],
                "estimated_spend": 8000,
                "messaging_themes": ["local expertise","personal service","specialist niche"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Local Freight Broker That Actually Picks Up","format":"single_image","hook":"Tired of being a number?","offer":"Direct broker access"},
                ],
                "messaging_themes": ["personal service","local expertise","accountability"],
                "creative_types": ["single image"],
            },
            "strengths": ["local SEO","niche specialist","personal service angle","lower CPC"],
            "weaknesses": ["limited brand awareness","small carrier network","limited content"],
            "opportunity_gaps": ["national expansion","technology differentiation"],
        },
    ],
    "knowledge_graph": {
        "entities": {
            "keywords": [
                {"id":"kw_freight_broker","label":"freight broker","type":"head_term","volume":12100,"our_position":8,"top_competitor":"Echo Global"},
                {"id":"kw_ltl_freight","label":"ltl freight broker","type":"service","volume":2900,"our_position":12,"top_competitor":"GlobalTranz"},
                {"id":"kw_refrigerated","label":"refrigerated freight broker","type":"opportunity","volume":1800,"our_position":None,"top_competitor":"None"},
            ],
            "campaigns": [
                {"id":"camp_brand","label":"Brand | Freight Broker","channel":"google_ads","roas":5.6,"leads":54},
                {"id":"camp_ltl","label":"LTL Shipping","channel":"google_ads","roas":3.2,"leads":32},
                {"id":"camp_retarget","label":"Retargeting","channel":"facebook","roas":4.0,"leads":28},
            ],
            "landing_pages": [
                {"id":"lp_quote","label":"/freight-quote","conv_rate":2.71,"top_traffic":"google_ads"},
                {"id":"lp_services","label":"/freight-broker-services","conv_rate":2.17,"top_traffic":"organic"},
                {"id":"lp_ltl","label":"/ltl-shipping","conv_rate":2.11,"top_traffic":"google_ads"},
            ],
            "audiences": [
                {"id":"aud_retarget","label":"Website Retargeting 30d","performance_score":88},
                {"id":"aud_lookalike","label":"1% Customer Lookalike","performance_score":72},
            ],
            "offers": [
                {"id":"off_quote","label":"Free Freight Quote","conversion_strength":"high"},
                {"id":"off_savings","label":"Save 30% on Shipping","conversion_strength":"medium"},
            ],
        },
        "relationships": [
            {"from_entity":"kw_freight_broker","to_entity":"lp_quote","type":"drives_traffic","strength":0.84,"notes":"Primary keyword to quote page. Strong alignment."},
            {"from_entity":"kw_ltl_freight","to_entity":"lp_ltl","type":"drives_traffic","strength":0.71,"notes":"LTL keyword cluster to LTL page. Moderate alignment."},
            {"from_entity":"camp_brand","to_entity":"lp_quote","type":"sends_traffic","strength":0.91,"notes":"Brand campaign routes almost exclusively to quote page."},
            {"from_entity":"camp_retarget","to_entity":"off_quote","type":"promotes","strength":0.78,"notes":"Retargeting uses quote offer effectively."},
            {"from_entity":"kw_refrigerated","to_entity":"lp_services","type":"opportunity_gap","strength":0.0,"notes":"Refrigerated freight keyword has no dedicated page. Competitor gap."},
            {"from_entity":"aud_retarget","to_entity":"off_quote","type":"responds_to","strength":0.88,"notes":"Retargeting audience converts at 88% higher rate with quote offer."},
        ],
        "insights": [
            {"type":"gap","title":"Refrigerated Freight Page Missing","description":"'Refrigerated freight broker' (1,800 mo. searches) has no competitor in organic top-10. We have zero presence. Echo Global does not target this either. Creating a dedicated page is a high-confidence, low-competition opportunity.","entities":["kw_refrigerated","lp_services"],"confidence":91,"action":"Create /refrigerated-freight page targeting this cluster"},
            {"type":"competitor","title":"Echo Global Dominates Head Terms But Has Slow Pages","description":"Echo Global ranks #2 for 'freight broker' but their landing page scores 42/100 on PageSpeed. Our page is faster. Improving our content depth + meta strategy could shift ranking within 60-90 days.","entities":["kw_freight_broker","lp_quote"],"confidence":74,"action":"Optimize /freight-quote content + meta tags to compete with Echo Global"},
            {"type":"performance","title":"Quote Page Over-Indexed for Paid, Underperforms Organic","description":"/freight-quote has 2.71% conv rate from paid traffic but only 0.86% from organic. The paid landing page experience does not match organic intent. Separate organic-optimized version recommended.","entities":["lp_quote","camp_brand"],"confidence":82,"action":"Create organic-first landing page variant for /freight-quote"},
            {"type":"audience","title":"Retargeting Audience Is High-Value, Underfunded","description":"Retargeting audience (30d) converts at $50 CPA vs. $88 for lookalike. Current retargeting budget is $1,400/mo. Increasing by $800/mo. would likely yield 6+ additional conversions.","entities":["aud_retarget","camp_retarget"],"confidence":86,"action":"Increase retargeting budget by $800/mo."},
        ],
    },
    "recommendations": [
        {
            "id":"rec_bcat_01","channel":"seo","title":"Create Refrigerated Freight Broker Page",
            "description":"Build a dedicated /refrigerated-freight page targeting 'refrigerated freight broker' and related terms. No major competitor currently ranks for this keyword cluster. High-confidence organic ranking opportunity.",
            "internal_trigger":"Zero organic impressions for refrigerated freight keyword cluster. 1,800 monthly searches unaddressed.",
            "competitor_insight":"Echo Global, Coyote, GlobalTranz — none rank in top 10 for 'refrigerated freight broker'. Market gap confirmed.",
            "knowledge_graph_insight":"Knowledge graph confirms no relationship exists between our landing pages and the refrigerated keyword cluster. Opportunity score: 91.",
            "priority":1,"expected_leads_impact":"+14/mo","expected_conversion_impact":"+2/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"medium","confidence":91,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"keyword","name":"refrigerated freight broker"},{"type":"landing_page","name":"/refrigerated-freight (new)"}],
        },
        {
            "id":"rec_bcat_02","channel":"google_ads","title":"Pause Wasted Spend Keywords — Reallocate $1,220",
            "description":"Keywords 'transport company' and 'logistics company' have generated $1,220 in spend with zero conversions over 90 days. Pause both and reallocate budget to 'freight broker near me' (exact match) which shows local intent and higher conversion probability.",
            "internal_trigger":"$1,220 wasted on 2 keywords with 0 conversions over 90 days. Quality scores 4/10.",
            "competitor_insight":"Coyote and Echo Global do not bid on these generic terms heavily — industry confirmation these terms do not convert for freight brokerage.",
            "knowledge_graph_insight":"No relationship between 'transport company' keyword and any converting landing page or audience segment.",
            "priority":1,"expected_leads_impact":"+8/mo","expected_conversion_impact":"+2/mo","estimated_spend_impact":"-$1,220 wasted",
            "implementation_difficulty":"low","confidence":94,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"keyword","name":"transport company"},{"type":"keyword","name":"logistics company"},{"type":"campaign","name":"Non-Brand | Freight Brokerage"}],
        },
        {
            "id":"rec_bcat_03","channel":"facebook_ads","title":"Refresh Fatigued Creatives — 3 New Variants",
            "description":"'24/7 Support Angle' creative has 74% fatigue score and frequency 3.2+. Generate 3 new creative variants testing hooks used by Echo Global ('cost savings angle') and Coyote ('reliability/on-time' angle). Rotate immediately.",
            "internal_trigger":"Creative fatigue score 74%. CTR declining 0.4% over last 6 weeks on this creative.",
            "competitor_insight":"Echo Global runs 'Cut Shipping Costs by 30%' hook consistently. Coyote uses 'Freight Without the Headache' emotional angle. Neither tested against our audience.",
            "knowledge_graph_insight":"Retargeting audience responds strongly to the quote offer. New creative variants should retain the quote CTA while testing new hooks.",
            "priority":2,"expected_leads_impact":"+6/mo","expected_conversion_impact":"+1/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"low","confidence":82,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"creative","name":"24/7 Support Angle"},{"type":"audience","name":"Website Retargeting 30d"}],
        },
        {
            "id":"rec_bcat_04","channel":"google_ads","title":"Add Local Freight Broker Keywords — City Targeting",
            "description":"'Freight broker near me' (8,100/mo) and city-specific terms are dominated by MoLo (Chicago local). Create a geo-targeted ad group for top 5 cities BCAT serves, with local landing pages. MoLo's weakness is limited national presence.",
            "internal_trigger":"No local keywords in current Google Ads. Search terms report shows 980 impressions for 'freight broker near me' — capturing only 54 clicks.",
            "competitor_insight":"MoLo Solutions ranks #2 for 'freight broker chicago' with a local page strategy, but has limited national presence. Opportunity to replicate their local SEO pattern at scale.",
            "knowledge_graph_insight":"Quote page (/freight-quote) converts at 2.71% for paid traffic — a local variant of this page targeting city-specific intent could outperform.",
            "priority":2,"expected_leads_impact":"+18/mo","expected_conversion_impact":"+3/mo","estimated_spend_impact":"+$1,800/mo budget",
            "implementation_difficulty":"medium","confidence":78,"requires_approval":False,
            "status":"draft",
            "linked_entities":[{"type":"keyword","name":"freight broker near me"},{"type":"campaign","name":"Local Geo-Targeting (new)"}],
        },
        {
            "id":"rec_bcat_05","channel":"seo","title":"Fix 6 Slow Pages — Core Web Vitals",
            "description":"6 pages have LCP >3 seconds including /freight-quote (our top converting page). Google uses Core Web Vitals as ranking signal. Fixing these pages could improve rankings for competitive terms.",
            "internal_trigger":"Technical audit shows 6 pages with LCP >3s. Our page speed disadvantage vs. competitors is confirmed.",
            "competitor_insight":"Echo Global's landing pages score 42/100 on PageSpeed despite their ranking. Our faster pages, once ranking, would have a CTR and conversion advantage.",
            "knowledge_graph_insight":"/freight-quote is our top converting page and primary destination for brand campaign. Speed improvement impacts both SEO rank and paid conversion rate.",
            "priority":2,"expected_leads_impact":"+6/mo","expected_conversion_impact":"+1/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"medium","confidence":77,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"landing_page","name":"/freight-quote"},{"type":"technical","name":"Core Web Vitals"}],
        },
        {
            "id":"rec_bcat_06","channel":"cross_channel","title":"Increase Retargeting Budget — High ROAS Audience",
            "description":"Retargeting audience converts at $50 CPA vs. $88 for lookalike. Increase retargeting budget from $1,400 to $2,200/mo. Expected 6 additional conversions/month at existing CPA.",
            "internal_trigger":"Retargeting audience performance score 88/100. Audience is underfunded relative to its CPA efficiency.",
            "competitor_insight":"Coyote runs aggressive retargeting at high frequency (4.2). Our frequency (2.4) suggests room to increase without fatigue.",
            "knowledge_graph_insight":"Retargeting audience + quote offer relationship scores 0.88 strength — highest relationship score in the graph. High-confidence recommendation.",
            "priority":1,"expected_leads_impact":"+10/mo","expected_conversion_impact":"+2/mo","estimated_spend_impact":"+$800/mo",
            "implementation_difficulty":"low","confidence":86,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"audience","name":"Website Retargeting 30d"},{"type":"campaign","name":"Retargeting"}],
        },
        {
            "id":"rec_bcat_07","channel":"seo","title":"Build 5 New Content Guides — Freight Market Topics",
            "description":"Echo Global and Coyote both use freight market content (rate guides, market reports) as top-of-funnel SEO. These pages rank for high-volume informational terms and build authority. Create 5 targeted guides.",
            "internal_trigger":"Blog content generates avg position 4.1 but only 0.86% lead conv rate — informational intent confirmed. Authority building opportunity.",
            "competitor_insight":"Echo Global's blog generates est. 28,000 monthly visits. Their content strategy uses freight rate indexes as SEO magnets. GlobalTranz uses whitepapers for lead gen.",
            "knowledge_graph_insight":"Content pages link organically to /freight-quote via internal linking. Improving content volume increases authority for the quote page.",
            "priority":3,"expected_leads_impact":"+8/mo","expected_conversion_impact":"+1/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"high","confidence":71,"requires_approval":False,
            "status":"draft",
            "linked_entities":[{"type":"channel","name":"Organic SEO"},{"type":"landing_page","name":"/blog"}],
        },
        {
            "id":"rec_bcat_08","channel":"google_ads","title":"Add Ad Copy Variants — Echo Global Competitive Angle",
            "description":"Current ads focus on generic messaging. Echo Global's top-performing angle is 'Compare 50,000+ carriers. Save up to 30%.' Create 3 new RSA variants testing specific savings claims and carrier network size as differentiators.",
            "internal_trigger":"Average quality score 6.8. Ad relevance sub-scores suggest copy is not matching search intent well enough.",
            "competitor_insight":"Echo Global's 'Save up to 30%' and 'Compare carriers' angles appear consistently across their ads — high-repeat messaging typically indicates it's performing.",
            "knowledge_graph_insight":"Quote offer (/freight-quote) responds well to cost-savings framing. Quote page existing copy aligns — new ad copy should match landing page messaging.",
            "priority":2,"expected_leads_impact":"+5/mo","expected_conversion_impact":"+1/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"low","confidence":73,"requires_approval":False,
            "status":"draft",
            "linked_entities":[{"type":"campaign","name":"Non-Brand | Freight Brokerage"},{"type":"competitor","name":"Echo Global Logistics"}],
        },
    ],
    "implementation_history": [
        {"id":"impl_bcat_01","date":"2026-02-14","recommendation_title":"Restructure Brand Campaign Ad Groups","channel":"google_ads","status":"completed","leads_before":42,"leads_after":54,"conversions_before":7,"conversions_after":9,"spend_before":2400,"spend_after":2800,"notes":"Separated brand exact vs phrase match. ROAS improved from 4.8 to 5.6 within 30 days."},
        {"id":"impl_bcat_02","date":"2026-01-22","recommendation_title":"Add Quote Calculator CTA to Facebook","channel":"facebook_ads","status":"completed","leads_before":14,"leads_after":26,"conversions_before":2,"conversions_after":4,"spend_before":1400,"spend_after":1800,"notes":"New creative outperformed previous by 86% on CPL within 14 days."},
        {"id":"impl_bcat_03","date":"2025-12-10","recommendation_title":"Fix Duplicate Title Tags (8 pages)","channel":"seo","status":"completed","leads_before":118,"leads_after":142,"conversions_before":18,"conversions_after":22,"spend_before":0,"spend_after":0,"notes":"Organic impressions increased 12% following fix. Rankings improved for 4 target keywords."},
    ],
}

# ---------------------------------------------------------------------------
# BEST CARE AUTO TRANSPORT
# ---------------------------------------------------------------------------
_best_care = {
    "id": "best_care_auto",
    "name": "Best Care Auto Transport",
    "short_name": "Best Care",
    "website": "bestcareautotransport.com",
    "industry": "Auto Transport",
    "overview": {
        "total_leads": 684,
        "total_conversions": 142,
        "conversion_rate": 20.8,
        "cost_per_lead": 38.60,
        "cost_per_conversion": 186.00,
        "total_ad_spend": 26400,
        "roas": 5.8,
        "ctr": 5.2,
        "cpc": 14.80,
        "cpm": 32.40,
        "organic_traffic": 28600,
        "paid_traffic": 9200,
        "top_channels": [
            {"name":"Google Ads","leads":312,"conversions":68,"spend":17800},
            {"name":"Organic SEO","leads":224,"conversions":48,"spend":0},
            {"name":"Facebook Ads","leads":98,"conversions":18,"spend":6400},
            {"name":"Direct / Referral","leads":50,"conversions":8,"spend":0},
        ],
        "top_campaigns": [
            {"name":"Auto Transport | Brand","channel":"Google Ads","leads":88,"conversions":22,"spend":3200,"roas":7.2},
            {"name":"Car Shipping | Non-Brand","channel":"Google Ads","leads":142,"conversions":28,"spend":9800,"roas":5.1},
            {"name":"Vehicle Transport | States","channel":"Google Ads","leads":62,"conversions":12,"spend":3400,"roas":4.8},
            {"name":"Retargeting | Quoted","channel":"Facebook Ads","leads":44,"conversions":9,"spend":1800,"roas":6.4},
            {"name":"Car Shipping Lookalike","channel":"Facebook Ads","leads":34,"conversions":6,"spend":2900,"roas":4.2},
        ],
        "top_landing_pages": [
            {"url":"/car-shipping-quote","sessions":6800,"leads":184,"conv_rate":2.71},
            {"url":"/auto-transport-services","sessions":4200,"leads":112,"conv_rate":2.67},
            {"url":"/door-to-door-car-shipping","sessions":2800,"leads":68,"conv_rate":2.43},
            {"url":"/enclosed-auto-transport","sessions":1800,"leads":38,"conv_rate":2.11},
        ],
        "funnel_stages": [
            {"stage":"Impressions","count":820000},
            {"stage":"Clicks","count":42600},
            {"stage":"Sessions","count":37800},
            {"stage":"Leads","count":684},
            {"stage":"Qualified","count":282},
            {"stage":"Converted","count":142},
        ],
        "leads_over_time": mts([44,52,58,62,68,72,56,48,58,64,74,88]),
        "conversions_over_time": mts([9,11,12,13,14,15,11,10,12,13,15,17]),
        "spend_over_time": mts([1600,1900,2200,2400,2600,2800,2100,1800,2200,2400,2800,3600]),
        "roas_over_time": mts([5.1,5.2,5.4,5.6,5.8,6.1,5.4,5.1,5.6,5.8,6.0,6.4]),
        "traffic_by_source": [
            {"source":"Organic","value":28600},
            {"source":"Google Ads","value":9200},
            {"source":"Facebook","value":3800},
            {"source":"Direct","value":4200},
            {"source":"Referral","value":1600},
        ],
    },
    "seo": {
        "health_score": 81,
        "organic_traffic": 28600,
        "keywords_ranked": 542,
        "top_3_rankings": 38,
        "avg_position": 11.4,
        "keyword_rankings": [
            {"keyword":"auto transport","position":6,"volume":22200,"difficulty":72,"opportunity_score":76},
            {"keyword":"car shipping","position":4,"volume":18100,"difficulty":69,"opportunity_score":80},
            {"keyword":"vehicle transport","position":8,"volume":12100,"difficulty":64,"opportunity_score":74},
            {"keyword":"enclosed auto transport","position":3,"volume":4400,"difficulty":58,"opportunity_score":84},
            {"keyword":"door to door car shipping","position":5,"volume":3600,"difficulty":52,"opportunity_score":82},
            {"keyword":"car transport quote","position":9,"volume":5400,"difficulty":61,"opportunity_score":77},
        ],
        "keyword_opportunities": [
            {"keyword":"best car shipping company","volume":9900,"difficulty":54,"competitor_ranking":"Montway #1","gap_score":86},
            {"keyword":"cheap auto transport","volume":8100,"difficulty":48,"competitor_ranking":"AmeriFreight #2","gap_score":82},
            {"keyword":"snowbird car shipping","volume":3200,"difficulty":34,"competitor_ranking":"Not ranked","gap_score":92},
            {"keyword":"military car shipping","volume":2700,"difficulty":38,"competitor_ranking":"Sherpa #3","gap_score":78},
            {"keyword":"luxury car transport","volume":2400,"difficulty":42,"competitor_ranking":"Not ranked","gap_score":89},
            {"keyword":"classic car shipping","volume":2100,"difficulty":36,"competitor_ranking":"Not ranked","gap_score":91},
        ],
        "technical_issues": [
            {"issue":"Missing schema markup (LocalBusiness)","severity":"high","count":1},
            {"issue":"Missing review schema","severity":"high","count":14},
            {"issue":"Slow mobile page speed","severity":"medium","count":8},
            {"issue":"Missing meta descriptions","severity":"medium","count":18},
            {"issue":"Thin content pages (<300 words)","severity":"medium","count":12},
        ],
        "top_pages": [
            {"url":"/car-shipping-quote","sessions":6800,"leads":184,"conv_rate":2.71,"avg_position":4.8},
            {"url":"/auto-transport-services","sessions":4200,"leads":112,"conv_rate":2.67,"avg_position":7.2},
            {"url":"/enclosed-auto-transport","sessions":1800,"leads":38,"conv_rate":2.11,"avg_position":3.2},
        ],
        "ranking_distribution": {"top3":38,"top10":112,"top20":198,"top50":294,"beyond50":248},
        "organic_traffic_trend": mts([1800,2000,2200,2400,2600,2800,2200,1900,2400,2600,2800,3400]),
        "ctr_trend": mts([4.2,4.4,4.6,4.8,5.0,5.2,4.6,4.4,4.8,5.0,5.2,5.6]),
        "impressions_trend": mts([42000,46000,48000,50000,52000,54000,48000,43000,50000,52000,54000,61000]),
    },
    "google_ads": {
        "spend": 17800,
        "conversions": 68,
        "cpc": 14.80,
        "ctr": 5.4,
        "roas": 5.8,
        "cpa": 261.76,
        "quality_score_avg": 7.4,
        "impression_share": 42.8,
        "campaigns": [
            {"name":"Brand | Auto Transport","spend":3200,"conversions":22,"cpc":8.20,"ctr":12.4,"roas":7.2,"cpa":145,"status":"active"},
            {"name":"Car Shipping | Non-Brand","spend":9800,"conversions":28,"cpc":18.20,"ctr":4.2,"roas":5.1,"cpa":350,"status":"active"},
            {"name":"Vehicle Transport | State Routes","spend":3400,"conversions":12,"cpc":14.60,"ctr":4.8,"roas":4.8,"cpa":283,"status":"active"},
            {"name":"Enclosed / Luxury","spend":1200,"conversions":4,"cpc":12.80,"ctr":6.2,"roas":6.1,"cpa":300,"status":"active"},
            {"name":"Military / Snowbird","spend":200,"conversions":2,"cpc":6.40,"ctr":8.1,"roas":8.4,"cpa":100,"status":"limited_budget"},
        ],
        "keywords": [
            {"keyword":"auto transport","match_type":"exact","spend":3200,"clicks":186,"conversions":9,"cpc":17.20,"quality_score":8,"status":"active"},
            {"keyword":"car shipping","match_type":"exact","spend":4800,"clicks":272,"conversions":14,"cpc":17.65,"quality_score":8,"status":"active"},
            {"keyword":"vehicle transport","match_type":"phrase","spend":2400,"clicks":168,"conversions":7,"cpc":14.29,"quality_score":7,"status":"active"},
            {"keyword":"cheap car transport","match_type":"broad","spend":840,"clicks":240,"conversions":1,"cpc":3.50,"quality_score":5,"status":"flagged"},
            {"keyword":"move my car","match_type":"broad","spend":560,"clicks":188,"conversions":0,"cpc":2.98,"quality_score":4,"status":"flagged"},
        ],
        "wasted_spend": {
            "total": 1400,
            "items": [
                {"keyword":"cheap car transport","spend":840,"reason":"Low QS, price-shopper intent, 1 conversion in 90 days"},
                {"keyword":"move my car","spend":560,"reason":"Zero conversions, low intent, off-brand messaging"},
            ]
        },
        "search_terms": [
            {"term":"auto transport companies","impressions":2800,"clicks":148,"conversions":6,"intent":"commercial"},
            {"term":"car shipping quote","impressions":2200,"clicks":124,"conversions":5,"intent":"transactional"},
            {"term":"how much does it cost to ship a car","impressions":1800,"clicks":62,"conversions":1,"intent":"informational"},
            {"term":"enclosed car shipping","impressions":1400,"clicks":88,"conversions":4,"intent":"commercial"},
            {"term":"ship car to another state","impressions":1200,"clicks":72,"conversions":3,"intent":"transactional"},
        ],
        "spend_trend": mts([1100,1300,1500,1680,1820,2100,1600,1400,1700,1900,2200,2900]),
        "conversions_trend": mts([4,5,5,6,6,8,5,4,6,6,7,10]),
        "roas_trend": mts([5.0,5.1,5.3,5.4,5.6,6.0,5.3,5.0,5.5,5.7,5.9,6.4]),
        "cpa_trend": mts([290,280,274,268,260,248,272,280,264,258,248,230]),
        "ctr_trend": mts([4.8,4.9,5.1,5.2,5.4,5.7,5.1,4.9,5.3,5.4,5.6,5.9]),
    },
    "facebook_ads": {
        "spend": 6400,
        "leads": 98,
        "conversions": 18,
        "cpm": 32.40,
        "cpc": 4.20,
        "ctr": 1.52,
        "cpa": 355.56,
        "roas": 4.8,
        "reach": 196000,
        "frequency": 2.8,
        "campaigns": [
            {"name":"Retargeting | Quoted Not Booked","spend":1800,"leads":44,"conversions":9,"cpm":24.80,"cpc":2.80,"ctr":2.2,"cpa":200,"status":"active"},
            {"name":"Car Shipping Lookalike 1%","spend":2900,"leads":34,"conversions":6,"cpm":36.20,"cpc":5.20,"ctr":1.2,"cpa":483,"status":"active"},
            {"name":"Moving Season Push","spend":1200,"leads":14,"conversions":2,"cpm":34.00,"cpc":4.80,"ctr":1.1,"cpa":600,"status":"seasonal"},
            {"name":"Snowbird Florida Route","spend":500,"leads":6,"conversions":1,"cpm":28.40,"cpc":3.60,"ctr":1.4,"cpa":500,"status":"active"},
        ],
        "creatives": [
            {"name":"Instant Quote CTA","format":"single_image","spend":2200,"impressions":68000,"clicks":1240,"leads":36,"ctr":1.82,"cpa":611,"fatigue_score":24},
            {"name":"5-Star Reviews Carousel","format":"carousel","spend":1800,"impressions":56000,"clicks":820,"leads":28,"ctr":1.46,"cpa":643,"fatigue_score":38},
            {"name":"Door-to-Door Video","format":"video","spend":1400,"impressions":43000,"clicks":600,"leads":18,"ctr":1.40,"cpa":778,"fatigue_score":51},
            {"name":"Price Comparison Hook","format":"single_image","spend":1000,"impressions":31000,"clicks":360,"leads":16,"ctr":1.16,"cpa":625,"fatigue_score":67},
        ],
        "audiences": [
            {"name":"Quoted Not Booked (7d)","type":"retargeting","spend":1800,"leads":44,"cpa":41,"performance_score":94},
            {"name":"Website Visitors (30d)","type":"retargeting","spend":800,"leads":12,"cpa":67,"performance_score":78},
            {"name":"1% Customer Lookalike","type":"lookalike","spend":2900,"leads":34,"cpa":85,"performance_score":68},
            {"name":"Moving Intent Interest","type":"interest","spend":900,"leads":8,"cpa":113,"performance_score":44},
        ],
        "funnel_breakdown": [
            {"stage":"Reach","impressions":196000,"rate":100},
            {"stage":"Impression","impressions":196000,"rate":100},
            {"stage":"Click","impressions":2980,"rate":1.52},
            {"stage":"Lead","impressions":98,"rate":3.29},
            {"stage":"Converted","impressions":18,"rate":18.37},
        ],
        "spend_trend": mts([380,440,520,580,640,720,540,480,560,640,740,960]),
        "leads_trend": mts([6,7,8,9,10,11,8,7,9,10,11,13]),
        "cpm_trend": mts([28.2,29.4,30.8,31.6,32.4,34.2,31.2,30.4,31.8,32.4,33.6,35.4]),
        "cpa_trend": mts([420,400,380,368,355,340,375,390,360,350,340,320]),
    },
    "competitors": [
        {
            "name": "Montway Auto Transport",
            "domain": "montway.com",
            "visibility_score": 92,
            "estimated_monthly_traffic": 184000,
            "seo": {
                "keywords_ranking": 3200,
                "top_keywords": [
                    {"kw":"auto transport","position":1,"volume":22200},
                    {"kw":"car shipping","position":1,"volume":18100},
                    {"kw":"best car shipping company","position":1,"volume":9900},
                ],
                "content_strategy": "Review aggregation, comparison pages, route-specific pages for top 100 city-pairs.",
                "page_types": ["route pages","comparison pages","reviews aggregator","calculator","blog"],
            },
            "google_ads": {
                "visibility": 88,
                "ad_examples": [
                    {"headline":"#1 Auto Transport | Instant Quote","description":"4.9 stars · 150,000+ shipments. Get your free quote in 30 seconds.","cta":"Get Free Quote"},
                    {"headline":"Montway Car Shipping | Trusted","description":"Fully insured door-to-door car shipping. Instant online booking.","cta":"Book Now"},
                ],
                "top_keywords": ["auto transport","car shipping","vehicle transport","car shipping quote"],
                "estimated_spend": 84000,
                "messaging_themes": ["#1 brand claim","review count","instant quote","insurance"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Ship Your Car in 3 Easy Steps","format":"video","hook":"Moving? Don't drive it. Ship it.","offer":"Instant online quote"},
                    {"headline":"150,000+ Happy Customers","format":"carousel","hook":"See why we're rated #1","offer":"Free quote + $50 off first shipment"},
                ],
                "messaging_themes": ["social proof","ease of booking","discount offer","customer count"],
                "creative_types": ["video","carousel","single image","dynamic"],
            },
            "strengths": ["#1 brand position","massive review count","route page SEO","discount offers"],
            "weaknesses": ["premium pricing","generic messaging at scale","slow customer support at volume"],
            "opportunity_gaps": ["luxury/enclosed specialty","military/snowbird niche","B2B fleet transport"],
        },
        {
            "name": "Sherpa Auto Transport",
            "domain": "sherpaautotransport.com",
            "visibility_score": 76,
            "estimated_monthly_traffic": 62000,
            "seo": {
                "keywords_ranking": 1180,
                "top_keywords": [
                    {"kw":"enclosed auto transport","position":2,"volume":4400},
                    {"kw":"military car shipping","position":3,"volume":2700},
                    {"kw":"best auto transport company","position":4,"volume":6600},
                ],
                "content_strategy": "Niche quality positioning. Strong review schema. Price-lock guarantee content pages.",
                "page_types": ["guarantee pages","review pages","specialty transport pages","comparison vs competitors"],
            },
            "google_ads": {
                "visibility": 62,
                "ad_examples": [
                    {"headline":"Sherpa | Price Lock Guarantee","description":"We guarantee your quote. No price changes. Enclosed & open transport.","cta":"Get Guaranteed Quote"},
                    {"headline":"Best Auto Transport | Price Lock","description":"The only auto transport company with a price guarantee. 5 stars.","cta":"Lock My Rate"},
                ],
                "top_keywords": ["enclosed auto transport","best auto transport","price lock car shipping"],
                "estimated_spend": 32000,
                "messaging_themes": ["price lock guarantee","quality/premium","enclosed specialist","trust"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Guaranteed Price. No Surprises.","format":"single_image","hook":"Tired of surprise fees on car shipping?","offer":"Price lock guarantee"},
                    {"headline":"Enclosed Transport Done Right","format":"video","hook":"Your luxury car deserves better.","offer":"Free enclosed quote"},
                ],
                "messaging_themes": ["price transparency","quality guarantee","premium positioning","peace of mind"],
                "creative_types": ["single image","video"],
            },
            "strengths": ["price lock differentiation","quality positioning","enclosed niche","trust messaging"],
            "weaknesses": ["smaller brand awareness","limited route coverage","higher price point"],
            "opportunity_gaps": ["open transport volume","snowbird routes","B2B fleet"],
        },
        {
            "name": "AmeriFreight",
            "domain": "amerifreight.net",
            "visibility_score": 68,
            "estimated_monthly_traffic": 48000,
            "seo": {
                "keywords_ranking": 920,
                "top_keywords": [
                    {"kw":"cheap auto transport","position":2,"volume":8100},
                    {"kw":"cheap car shipping","position":3,"volume":6600},
                    {"kw":"affordable car transport","position":4,"volume":3200},
                ],
                "content_strategy": "Price-focused positioning. Strong on price-comparison and 'cheap' keyword variants.",
                "page_types": ["pricing pages","comparison pages","discount pages","state route pages"],
            },
            "google_ads": {
                "visibility": 58,
                "ad_examples": [
                    {"headline":"Cheap Car Shipping | Save More","description":"Compare quotes from multiple carriers. Lowest price guarantee.","cta":"Compare Quotes"},
                    {"headline":"Affordable Auto Transport","description":"Get the best rate on car shipping. 5 star rated. Multiple carriers.","cta":"Get Cheapest Quote"},
                ],
                "top_keywords": ["cheap car shipping","affordable auto transport","cheap auto transport"],
                "estimated_spend": 22000,
                "messaging_themes": ["lowest price","multi-carrier comparison","affordability","savings"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Save Up to 40% on Car Shipping","format":"single_image","hook":"Paying too much to ship your car?","offer":"Free lowest-price quote"},
                ],
                "messaging_themes": ["cost savings","price comparison","affordability"],
                "creative_types": ["single image","carousel"],
            },
            "strengths": ["price positioning","cheap keyword dominance","comparison shopping SEO"],
            "weaknesses": ["quality perception","carrier vetting concerns","premium segment absent"],
            "opportunity_gaps": ["premium/quality messaging gap","enclosed transport","corporate accounts"],
        },
        {
            "name": "Nexus Auto Transport",
            "domain": "nexusautotransport.com",
            "visibility_score": 52,
            "estimated_monthly_traffic": 28000,
            "seo": {
                "keywords_ranking": 640,
                "top_keywords": [
                    {"kw":"snowbird car shipping","position":1,"volume":3200},
                    {"kw":"florida car transport","position":2,"volume":2400},
                    {"kw":"classic car transport","position":3,"volume":2100},
                ],
                "content_strategy": "Route + niche specialist. Snowbird and seasonal routes are their moat.",
                "page_types": ["route pages","seasonal pages","classic car pages","snowbird guide"],
            },
            "google_ads": {
                "visibility": 42,
                "ad_examples": [
                    {"headline":"Snowbird Car Shipping | Florida Routes","description":"Trusted by 10,000+ snowbirds. Safe, reliable seasonal vehicle transport.","cta":"Get Snowbird Quote"},
                ],
                "top_keywords": ["snowbird car shipping","florida car transport","seasonal vehicle transport"],
                "estimated_spend": 12000,
                "messaging_themes": ["seasonal specialist","snowbird community","route expertise","trusted"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Heading to Florida? Ship Your Car.","format":"single_image","hook":"Avoid the long drive. Ship it.","offer":"Special snowbird rates"},
                ],
                "messaging_themes": ["seasonal angle","route specific","lifestyle messaging"],
                "creative_types": ["single image","video"],
            },
            "strengths": ["snowbird niche dominance","seasonal route SEO","loyal repeat customer base"],
            "weaknesses": ["narrow audience","seasonal revenue dependency","limited national brand"],
            "opportunity_gaps": ["year-round messaging","military routes","luxury vehicle segment"],
        },
    ],
    "knowledge_graph": {
        "entities": {
            "keywords": [
                {"id":"kw_car_shipping","label":"car shipping","type":"head_term","volume":18100,"our_position":4,"top_competitor":"Montway"},
                {"id":"kw_snowbird","label":"snowbird car shipping","type":"niche","volume":3200,"our_position":None,"top_competitor":"Nexus"},
                {"id":"kw_luxury","label":"luxury car transport","type":"opportunity","volume":2400,"our_position":None,"top_competitor":"None"},
                {"id":"kw_enclosed","label":"enclosed auto transport","type":"service","volume":4400,"our_position":3,"top_competitor":"Sherpa"},
            ],
            "campaigns": [
                {"id":"camp_brand_bc","label":"Brand | Auto Transport","channel":"google_ads","roas":7.2,"leads":88},
                {"id":"camp_nonbrand","label":"Car Shipping | Non-Brand","channel":"google_ads","roas":5.1,"leads":142},
                {"id":"camp_retarget_bc","label":"Retargeting | Quoted","channel":"facebook","roas":6.4,"leads":44},
            ],
            "landing_pages": [
                {"id":"lp_quote_bc","label":"/car-shipping-quote","conv_rate":2.71,"top_traffic":"google_ads"},
                {"id":"lp_enclosed","label":"/enclosed-auto-transport","conv_rate":2.11,"top_traffic":"organic"},
                {"id":"lp_snowbird","label":"/snowbird-shipping (missing)","conv_rate":0,"top_traffic":"none"},
            ],
            "audiences": [
                {"id":"aud_quoted","label":"Quoted Not Booked 7d","performance_score":94},
                {"id":"aud_lookalike_bc","label":"1% Customer Lookalike","performance_score":68},
            ],
            "offers": [
                {"id":"off_quote_bc","label":"Instant Quote","conversion_strength":"high"},
                {"id":"off_snowbird","label":"Snowbird Special Rate","conversion_strength":"projected_high"},
            ],
        },
        "relationships": [
            {"from_entity":"kw_car_shipping","to_entity":"lp_quote_bc","type":"drives_traffic","strength":0.88,"notes":"Primary keyword routes to quote page. Top conversion path."},
            {"from_entity":"kw_snowbird","to_entity":"lp_snowbird","type":"opportunity_gap","strength":0.0,"notes":"Snowbird keyword cluster (3,200/mo) has no landing page. Nexus dominates this gap."},
            {"from_entity":"kw_luxury","to_entity":"lp_enclosed","type":"partial_match","strength":0.42,"notes":"Luxury seekers land on enclosed page — close but not optimized for luxury angle."},
            {"from_entity":"aud_quoted","to_entity":"off_quote_bc","type":"responds_to","strength":0.94,"notes":"Quoted-not-booked audience converts at highest rate in entire program ($41 CPA)."},
        ],
        "insights": [
            {"type":"gap","title":"Snowbird Niche Has Zero Coverage — Nexus Wins This Alone","description":"'Snowbird car shipping' (3,200/mo) is owned by Nexus. No other top competitor is present. We have no page, no campaign, no creative for this segment. Seasonal volume spikes Oct-Jan (Florida routes).","entities":["kw_snowbird","lp_snowbird"],"confidence":93,"action":"Create snowbird landing page + seasonal Google Ads campaign"},
            {"type":"competitor","title":"Montway's #1 Social Proof Position Is Beatable in Niches","description":"Montway dominates with '150,000+ shipments' messaging but uses generic creative at scale. Niche audiences (luxury, military, snowbird) respond to specialist messaging — an angle Montway cannot credibly own.","entities":["kw_luxury","kw_enclosed"],"confidence":81,"action":"Build niche specialist pages + test specialist ad creative"},
            {"type":"performance","title":"Quoted-Not-Booked Audience Is Your Best Asset","description":"The 'Quoted Not Booked 7d' audience converts at $41 CPA — 5x more efficient than cold lookalike. This audience is underfunded at $1,800/mo. Scaling this by $1,200 would yield ~15 additional conversions/mo.","entities":["aud_quoted","camp_retarget_bc"],"confidence":91,"action":"Scale retargeting budget to $3,000/mo immediately"},
            {"type":"gap","title":"Luxury + Classic Car Segment Completely Unaddressed","description":"'Luxury car transport' (2,400/mo) and 'classic car shipping' (2,100/mo) have zero competition in the top 10. Sherpa owns enclosed but does not specifically target luxury/classic as a segment. High-value customers, high CPA justifiable.","entities":["kw_luxury","lp_enclosed"],"confidence":88,"action":"Create /luxury-car-transport and /classic-car-shipping pages"},
        ],
    },
    "recommendations": [
        {
            "id":"rec_bc_01","channel":"seo","title":"Create Snowbird Car Shipping Landing Page",
            "description":"Build /snowbird-car-shipping page targeting seasonal route keywords. Nexus Auto Transport is the only player in this space. 3,200 monthly searches with no top-10 competitors except Nexus. Seasonal spike Oct-Jan.",
            "internal_trigger":"Zero organic impressions for snowbird keyword cluster. Route demand confirmed in search terms report.",
            "competitor_insight":"Nexus Auto Transport ranks #1 for 'snowbird car shipping' with a dedicated page. No other top competitor targets this segment. Pure gap play.",
            "knowledge_graph_insight":"Snowbird keyword cluster has 0.0 strength relationship to any existing landing page — complete gap in the knowledge graph.",
            "priority":1,"expected_leads_impact":"+22/mo (seasonal)","expected_conversion_impact":"+5/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"medium","confidence":93,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"keyword","name":"snowbird car shipping"},{"type":"landing_page","name":"/snowbird-car-shipping (new)"}],
        },
        {
            "id":"rec_bc_02","channel":"facebook_ads","title":"Scale Quoted-Not-Booked Retargeting — +$1,200 Budget",
            "description":"'Quoted Not Booked 7d' audience converts at $41 CPA — cheapest conversions in the program by far. Current $1,800 budget is undersized. Scale to $3,000 targeting expected 15 additional conversions at existing CPA.",
            "internal_trigger":"Audience performance score 94/100. CPA $41 vs program average $355. Clear scaling opportunity.",
            "competitor_insight":"Montway runs aggressive retargeting (frequency 4.2+). Their retargeting budget estimated at $18,000/mo. We are underinvesting here relative to program size.",
            "knowledge_graph_insight":"Quoted audience → quote offer relationship scores 0.94 — highest in the program. High-confidence scaling signal.",
            "priority":1,"expected_leads_impact":"+18/mo","expected_conversion_impact":"+5/mo","estimated_spend_impact":"+$1,200/mo",
            "implementation_difficulty":"low","confidence":91,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"audience","name":"Quoted Not Booked 7d"},{"type":"campaign","name":"Retargeting | Quoted Not Booked"}],
        },
        {
            "id":"rec_bc_03","channel":"seo","title":"Add Review Schema to 14 Pages — Missing Rich Snippets",
            "description":"14 service pages are missing review schema markup. Montway and Sherpa both display star ratings in SERPs. Adding schema increases CTR by est. 15-30% at existing ranking positions.",
            "internal_trigger":"Technical audit: 14 pages missing review schema. Avg position 11.4 — schema would improve click share at current positions.",
            "competitor_insight":"Montway displays 4.9 stars in SERP snippets for head terms. CTR advantage estimated at 22% over non-schema competitors.",
            "knowledge_graph_insight":"Top ranking pages (/car-shipping-quote, /auto-transport-services) lack schema — direct impact on click volume from existing rankings.",
            "priority":2,"expected_leads_impact":"+16/mo","expected_conversion_impact":"+3/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"low","confidence":87,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"technical","name":"Review Schema"},{"type":"landing_page","name":"/auto-transport-services"}],
        },
        {
            "id":"rec_bc_04","channel":"google_ads","title":"Create Luxury Car Transport Ad Group",
            "description":"'Luxury car transport' (2,400/mo) and 'classic car shipping' (2,100/mo) have no top-10 paid competitors. Create dedicated ad group with enclosed transport landing page variant emphasizing white-glove service.",
            "internal_trigger":"Enclosed campaign ROAS 6.1 (highest in program). Luxury segment not explicitly targeted.",
            "competitor_insight":"No major competitor runs specific luxury/classic car ads. Sherpa is closest with enclosed transport but does not use luxury-specific messaging.",
            "knowledge_graph_insight":"Luxury keywords partially match to enclosed page (0.42 strength) — dedicated page + ad group would raise this significantly.",
            "priority":2,"expected_leads_impact":"+12/mo","expected_conversion_impact":"+3/mo","estimated_spend_impact":"+$1,400/mo budget",
            "implementation_difficulty":"medium","confidence":85,"requires_approval":False,
            "status":"draft",
            "linked_entities":[{"type":"keyword","name":"luxury car transport"},{"type":"campaign","name":"Enclosed / Luxury"}],
        },
    ],
    "implementation_history": [
        {"id":"impl_bc_01","date":"2026-02-18","recommendation_title":"Add State Route Pages (Top 10 Routes)","channel":"seo","status":"completed","leads_before":188,"leads_after":224,"conversions_before":40,"conversions_after":48,"spend_before":0,"spend_after":0,"notes":"10 new route pages indexed. Organic traffic increased 19% within 45 days."},
        {"id":"impl_bc_02","date":"2026-01-30","recommendation_title":"Launch Snowbird Florida Facebook Campaign","channel":"facebook_ads","status":"completed","leads_before":6,"leads_after":14,"conversions_before":1,"conversions_after":3,"spend_before":0,"spend_after":500,"notes":"Seasonal campaign launched Jan 2026. CPL $83 — above average but high LTV customers."},
        {"id":"impl_bc_03","date":"2025-12-20","recommendation_title":"Pause 3 Wasted Spend Keywords","channel":"google_ads","status":"completed","leads_before":62,"leads_after":68,"conversions_before":10,"conversions_after":12,"spend_before":9800,"spend_after":8400,"notes":"$1,400 reallocated to brand and enclosed campaigns. ROAS improved program-wide."},
    ],
}

# ---------------------------------------------------------------------------
# IVAN CARTAGE AMAZON DRIVERS
# ---------------------------------------------------------------------------
_ivan = {
    "id": "ivan_amazon",
    "name": "Ivan Cartage Amazon Drivers",
    "short_name": "Ivan Amazon",
    "website": "ivancartage.com",
    "industry": "Last-Mile / Amazon Driver Recruitment",
    "overview": {
        "total_leads": 892,
        "total_conversions": 168,
        "conversion_rate": 18.8,
        "cost_per_lead": 12.40,
        "cost_per_conversion": 65.80,
        "total_ad_spend": 11060,
        "roas": None,
        "ctr": 6.8,
        "cpc": 4.20,
        "cpm": 18.60,
        "organic_traffic": 6400,
        "paid_traffic": 14200,
        "top_channels": [
            {"name":"Google Ads","leads":428,"conversions":84,"spend":6200},
            {"name":"Facebook Ads","leads":312,"conversions":58,"spend":3800},
            {"name":"Indeed / Job Boards","leads":108,"conversions":20,"spend":1060},
            {"name":"Organic SEO","leads":44,"conversions":6,"spend":0},
        ],
        "top_campaigns": [
            {"name":"Amazon Driver Jobs | Local","channel":"Google Ads","leads":182,"conversions":38,"spend":2400,"roas":None},
            {"name":"CDL Delivery Driver","channel":"Google Ads","leads":142,"conversions":28,"spend":2200,"roas":None},
            {"name":"Driver Recruitment | FB","channel":"Facebook Ads","leads":168,"conversions":32,"spend":2100,"roas":None},
            {"name":"Driver Lookalike","channel":"Facebook Ads","leads":98,"conversions":18,"spend":1400,"roas":None},
            {"name":"Indeed Sponsored","channel":"Indeed","leads":108,"conversions":20,"spend":1060,"roas":None},
        ],
        "top_landing_pages": [
            {"url":"/apply-now","sessions":8400,"leads":282,"conv_rate":3.36},
            {"url":"/amazon-delivery-driver-jobs","sessions":4200,"leads":148,"conv_rate":3.52},
            {"url":"/cdl-driver-jobs","sessions":2800,"leads":88,"conv_rate":3.14},
            {"url":"/driver-pay-benefits","sessions":2100,"leads":62,"conv_rate":2.95},
        ],
        "funnel_stages": [
            {"stage":"Impressions","count":1640000},
            {"stage":"Clicks","count":111000},
            {"stage":"Sessions","count":20600},
            {"stage":"Applications","count":892},
            {"stage":"Screened","count":384},
            {"stage":"Hired","count":168},
        ],
        "leads_over_time": mts([58,64,72,80,88,94,78,68,80,88,102,120]),
        "conversions_over_time": mts([11,12,14,15,17,18,14,12,15,17,19,22]),
        "spend_over_time": mts([680,780,900,1000,1080,1200,960,820,1000,1080,1260,1500]),
        "roas_over_time": mts([None,None,None,None,None,None,None,None,None,None,None,None]),
        "traffic_by_source": [
            {"source":"Google Ads","value":14200},
            {"source":"Facebook","value":8200},
            {"source":"Indeed","value":2800},
            {"source":"Organic","value":6400},
            {"source":"Direct","value":1800},
        ],
    },
    "seo": {
        "health_score": 58,
        "organic_traffic": 6400,
        "keywords_ranked": 128,
        "top_3_rankings": 8,
        "avg_position": 18.4,
        "keyword_rankings": [
            {"keyword":"amazon delivery driver jobs","position":12,"volume":8100,"difficulty":42,"opportunity_score":82},
            {"keyword":"delivery driver jobs near me","position":18,"volume":22200,"difficulty":38,"opportunity_score":76},
            {"keyword":"cdl delivery driver jobs","position":9,"volume":4400,"difficulty":34,"opportunity_score":84},
            {"keyword":"amazon dsp driver","position":14,"volume":3600,"difficulty":36,"opportunity_score":80},
            {"keyword":"delivery driver pay","position":6,"volume":5400,"difficulty":28,"opportunity_score":88},
        ],
        "keyword_opportunities": [
            {"keyword":"amazon driver jobs near me","volume":14800,"difficulty":32,"competitor_ranking":"OnTrac #8","gap_score":91},
            {"keyword":"amazon dsp jobs","volume":6600,"difficulty":28,"competitor_ranking":"Not ranked","gap_score":94},
            {"keyword":"delivery driver benefits","volume":4400,"difficulty":22,"competitor_ranking":"Not ranked","gap_score":96},
            {"keyword":"amazon delivery driver pay","volume":5400,"difficulty":30,"competitor_ranking":"LaserShip #9","gap_score":90},
            {"keyword":"warehouse delivery driver","volume":3200,"difficulty":24,"competitor_ranking":"Not ranked","gap_score":93},
        ],
        "technical_issues": [
            {"issue":"No schema markup (JobPosting schema missing)","severity":"high","count":1},
            {"issue":"No mobile optimization on apply form","severity":"high","count":1},
            {"issue":"Missing meta descriptions","severity":"medium","count":22},
            {"issue":"Thin content on job pages (<200 words)","severity":"high","count":8},
            {"issue":"No Google for Jobs integration","severity":"high","count":1},
        ],
        "top_pages": [
            {"url":"/apply-now","sessions":8400,"leads":282,"conv_rate":3.36,"avg_position":8.2},
            {"url":"/amazon-delivery-driver-jobs","sessions":4200,"leads":148,"conv_rate":3.52,"avg_position":12.1},
            {"url":"/driver-pay-benefits","sessions":2100,"leads":62,"conv_rate":2.95,"avg_position":6.1},
        ],
        "ranking_distribution": {"top3":8,"top10":28,"top20":58,"top50":96,"beyond50":32},
        "organic_traffic_trend": mts([420,460,500,540,580,620,540,480,540,580,640,780]),
        "ctr_trend": mts([3.8,4.0,4.2,4.4,4.6,4.8,4.2,4.0,4.4,4.6,4.8,5.2]),
        "impressions_trend": mts([11000,12000,12000,12200,12600,13000,12800,12000,12200,12600,13200,15000]),
    },
    "google_ads": {
        "spend": 6200,
        "conversions": 84,
        "cpc": 4.20,
        "ctr": 6.8,
        "roas": None,
        "cpa": 73.81,
        "quality_score_avg": 7.8,
        "impression_share": 54.2,
        "campaigns": [
            {"name":"Amazon Driver Jobs | Local","spend":2400,"conversions":38,"cpc":3.80,"ctr":8.4,"roas":None,"cpa":63,"status":"active"},
            {"name":"CDL Delivery Driver","spend":2200,"conversions":28,"cpc":4.60,"ctr":6.2,"roas":None,"cpa":79,"status":"active"},
            {"name":"Delivery Driver | Broad","spend":1200,"conversions":12,"cpc":4.00,"ctr":5.8,"roas":None,"cpa":100,"status":"active"},
            {"name":"Competitor DSP Conquest","spend":400,"conversions":6,"cpc":4.80,"ctr":5.1,"roas":None,"cpa":67,"status":"active"},
        ],
        "keywords": [
            {"keyword":"amazon delivery driver jobs","match_type":"exact","spend":1200,"clicks":292,"conversions":22,"cpc":4.11,"quality_score":9,"status":"active"},
            {"keyword":"amazon dsp driver jobs","match_type":"exact","spend":980,"clicks":218,"conversions":16,"cpc":4.50,"quality_score":8,"status":"active"},
            {"keyword":"delivery driver jobs","match_type":"phrase","spend":1400,"clicks":380,"conversions":18,"cpc":3.68,"quality_score":7,"status":"active"},
            {"keyword":"warehouse jobs near me","match_type":"broad","spend":420,"clicks":280,"conversions":2,"cpc":1.50,"quality_score":5,"status":"flagged"},
            {"keyword":"truck driver jobs","match_type":"broad","spend":320,"clicks":188,"conversions":0,"cpc":1.70,"quality_score":4,"status":"flagged"},
        ],
        "wasted_spend": {
            "total": 740,
            "items": [
                {"keyword":"warehouse jobs near me","spend":420,"reason":"Low conversion, different intent — warehouse vs delivery"},
                {"keyword":"truck driver jobs","spend":320,"reason":"Zero conversions, wrong driver type targeting"},
            ]
        },
        "search_terms": [
            {"term":"amazon delivery driver jobs near me","impressions":4800,"clicks":380,"conversions":28,"intent":"transactional"},
            {"term":"amazon dsp jobs","impressions":3200,"clicks":248,"conversions":18,"intent":"transactional"},
            {"term":"delivery driver jobs hiring now","impressions":2400,"clicks":184,"conversions":12,"intent":"transactional"},
            {"term":"amazon driver pay","impressions":1800,"clicks":92,"conversions":4,"intent":"informational"},
            {"term":"how to become amazon driver","impressions":1400,"clicks":48,"conversions":2,"intent":"informational"},
        ],
        "spend_trend": mts([420,480,540,600,660,720,580,500,600,660,780,960]),
        "conversions_trend": mts([6,7,7,8,8,9,7,6,8,8,9,11]),
        "roas_trend": mts([None]*12),
        "cpa_trend": mts([90,86,82,80,78,74,80,84,78,76,72,68]),
        "ctr_trend": mts([6.0,6.2,6.4,6.6,6.8,7.2,6.4,6.0,6.6,6.8,7.0,7.6]),
    },
    "facebook_ads": {
        "spend": 3800,
        "leads": 312,
        "conversions": 58,
        "cpm": 18.60,
        "cpc": 2.80,
        "ctr": 1.34,
        "cpa": 65.52,
        "roas": None,
        "reach": 204000,
        "frequency": 2.2,
        "campaigns": [
            {"name":"Driver Recruitment | Local","spend":2100,"leads":168,"conversions":32,"cpm":16.40,"cpc":2.40,"ctr":1.6,"cpa":66,"status":"active"},
            {"name":"Driver Lookalike 1%","spend":1400,"leads":98,"conversions":18,"cpm":20.80,"cpc":3.20,"ctr":1.1,"cpa":78,"status":"active"},
            {"name":"CDL Driver Interest","spend":300,"leads":46,"conversions":8,"cpm":18.20,"cpc":2.60,"ctr":1.4,"cpa":38,"status":"active"},
        ],
        "creatives": [
            {"name":"Driver Pay Highlight","format":"single_image","spend":1400,"impressions":75000,"clicks":1200,"leads":128,"ctr":1.60,"cpa":109,"fatigue_score":22},
            {"name":"Day-in-Life Video","format":"video","spend":1100,"impressions":59000,"clicks":880,"leads":96,"ctr":1.49,"cpa":115,"fatigue_score":34},
            {"name":"Benefits Comparison","format":"carousel","spend":800,"impressions":43000,"clicks":560,"leads":58,"ctr":1.30,"cpa":138,"fatigue_score":48},
            {"name":"Apply Now Urgency","format":"single_image","spend":500,"impressions":27000,"clicks":320,"leads":30,"ctr":1.19,"cpa":167,"fatigue_score":61},
        ],
        "audiences": [
            {"name":"Gig Workers Interest","type":"interest","spend":1200,"leads":138,"cpa":87,"performance_score":84},
            {"name":"Prior Amazon Applicants","type":"retargeting","spend":600,"leads":82,"cpa":73,"performance_score":91},
            {"name":"Delivery Driver Lookalike","type":"lookalike","spend":1400,"leads":68,"cpa":206,"performance_score":62},
            {"name":"Warehouse Worker Interest","type":"interest","spend":600,"leads":24,"cpa":250,"performance_score":38},
        ],
        "funnel_breakdown": [
            {"stage":"Reach","impressions":204000,"rate":100},
            {"stage":"Impression","impressions":204000,"rate":100},
            {"stage":"Click","impressions":2740,"rate":1.34},
            {"stage":"Lead","impressions":312,"rate":11.39},
            {"stage":"Hired","impressions":58,"rate":18.59},
        ],
        "spend_trend": mts([220,260,300,340,380,420,340,300,360,400,460,580]),
        "leads_trend": mts([20,24,28,30,34,36,28,24,30,34,40,52]),
        "cpm_trend": mts([16.2,16.8,17.4,18.0,18.6,20.0,18.4,17.8,18.2,18.6,19.4,21.2]),
        "cpa_trend": mts([80,78,74,72,68,64,72,76,70,68,64,60]),
    },
    "competitors": [
        {
            "name": "OnTrac",
            "domain": "ontrac.com",
            "visibility_score": 74,
            "estimated_monthly_traffic": 62000,
            "seo": {
                "keywords_ranking": 840,
                "top_keywords": [
                    {"kw":"delivery driver jobs","position":4,"volume":22200},
                    {"kw":"package delivery jobs","position":6,"volume":8100},
                    {"kw":"courier driver jobs","position":5,"volume":4400},
                ],
                "content_strategy": "Job board integration, route-specific pages, pay + benefits comparison content.",
                "page_types": ["job listing pages","pay pages","route pages","benefits pages"],
            },
            "google_ads": {
                "visibility": 62,
                "ad_examples": [
                    {"headline":"OnTrac Drivers Earn $20-28/hr","description":"Weekly pay. Flexible routes. Apply in 5 minutes online. Hiring now.","cta":"Apply Today"},
                    {"headline":"Delivery Driver Jobs | OnTrac","description":"Full-time, part-time, and contract delivery routes available now.","cta":"View Open Routes"},
                ],
                "top_keywords": ["delivery driver jobs","package delivery","courier driver"],
                "estimated_spend": 18000,
                "messaging_themes": ["hourly pay rate","flexibility","weekly pay","fast apply"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Earn $20-28/hr Delivering Packages","format":"video","hook":"Tired of your current job?","offer":"$500 sign-on bonus"},
                    {"headline":"OnTrac Is Hiring Drivers Now","format":"single_image","hook":"Flexible hours, weekly pay.","offer":"Instant online application"},
                ],
                "messaging_themes": ["pay rate","sign-on bonus","flexibility","speed of application"],
                "creative_types": ["video","single image"],
            },
            "strengths": ["pay rate messaging","sign-on bonus offers","Google for Jobs integration","fast apply flow"],
            "weaknesses": ["brand less known than Amazon","limited niche targeting","impersonal messaging"],
            "opportunity_gaps": ["Amazon DSP-specific angle","local community feel","driver advancement path"],
        },
        {
            "name": "LaserShip",
            "domain": "lasership.com",
            "visibility_score": 61,
            "estimated_monthly_traffic": 44000,
            "seo": {
                "keywords_ranking": 620,
                "top_keywords": [
                    {"kw":"last mile delivery jobs","position":3,"volume":5400},
                    {"kw":"amazon delivery partner","position":8,"volume":4400},
                ],
                "content_strategy": "East Coast market focus. Route-based pages, driver testimonials, pay transparency.",
                "page_types": ["route pages","driver stories","pay calculator","job listings"],
            },
            "google_ads": {
                "visibility": 48,
                "ad_examples": [
                    {"headline":"LaserShip | Last Mile Delivery Jobs","description":"East Coast routes. Competitive pay. Immediate openings.","cta":"Apply Now"},
                ],
                "top_keywords": ["last mile delivery","delivery driver east coast"],
                "estimated_spend": 12000,
                "messaging_themes": ["regional specialist","immediate openings","pay transparency"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Drive for LaserShip","format":"single_image","hook":"East Coast routes, flexible hours.","offer":"$300 sign-on bonus"},
                ],
                "messaging_themes": ["regional","immediate hiring","sign-on bonus"],
                "creative_types": ["single image"],
            },
            "strengths": ["regional focus","pay calculator","driver testimonials"],
            "weaknesses": ["limited national brand","east coast only","lower ad investment"],
            "opportunity_gaps": ["Amazon DSP-specific branding","driver advancement stories","flexible schedule messaging"],
        },
        {
            "name": "Amazon DSP (Competitor Operators)",
            "domain": "amazon.com/dsp",
            "visibility_score": 88,
            "estimated_monthly_traffic": 280000,
            "seo": {
                "keywords_ranking": 4200,
                "top_keywords": [
                    {"kw":"amazon delivery driver jobs","position":1,"volume":8100},
                    {"kw":"amazon dsp driver","position":1,"volume":3600},
                    {"kw":"amazon flex driver","position":1,"volume":14800},
                ],
                "content_strategy": "Amazon brand authority. Job listing integration. Pay + benefits transparency.",
                "page_types": ["job listings","pay/benefits pages","driver stories","application flow"],
            },
            "google_ads": {
                "visibility": 82,
                "ad_examples": [
                    {"headline":"Amazon Delivery Partner | Apply Now","description":"Join Amazon's delivery network. Competitive pay, benefits, flexible hours.","cta":"Apply Today"},
                    {"headline":"Amazon DSP Driver Openings","description":"Earn competitive wages with Amazon DSP. Immediate openings near you.","cta":"View Jobs"},
                ],
                "top_keywords": ["amazon delivery driver","amazon dsp jobs","amazon driver pay"],
                "estimated_spend": 120000,
                "messaging_themes": ["Amazon brand authority","pay + benefits","flexibility","immediate openings"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Drive for Amazon Near You","format":"video","hook":"Be part of Amazon's delivery mission.","offer":"Competitive pay + benefits"},
                ],
                "messaging_themes": ["brand trust","community","pay + benefits","local openings"],
                "creative_types": ["video","carousel","single image"],
            },
            "strengths": ["Amazon brand recognition","massive budget","Google for Jobs dominance","trust"],
            "weaknesses": ["impersonal at scale","rigid structure","corporate feel","no local community angle"],
            "opportunity_gaps": ["personal/community DSP angle","driver advancement story","flexible schedule detail","local routes emphasis"],
        },
        {
            "name": "LSO (Lone Star Overnight)",
            "domain": "lso.com",
            "visibility_score": 44,
            "estimated_monthly_traffic": 18000,
            "seo": {
                "keywords_ranking": 280,
                "top_keywords": [
                    {"kw":"delivery driver jobs texas","position":2,"volume":2800},
                    {"kw":"overnight delivery driver","position":4,"volume":1800},
                ],
                "content_strategy": "Texas/regional specialist. Overnight delivery driver focus.",
                "page_types": ["regional job pages","overnight driver pages","benefits pages"],
            },
            "google_ads": {
                "visibility": 32,
                "ad_examples": [
                    {"headline":"LSO Driver Jobs | Texas","description":"Overnight delivery driver positions. Competitive pay. Apply now.","cta":"Apply Now"},
                ],
                "top_keywords": ["delivery driver texas","overnight driver jobs"],
                "estimated_spend": 6000,
                "messaging_themes": ["regional specialist","overnight shift","pay transparency"],
            },
            "facebook_ads": {
                "ad_examples": [
                    {"headline":"Drive for LSO in Texas","format":"single_image","hook":"Local routes. Competitive pay.","offer":"Immediate openings"},
                ],
                "messaging_themes": ["local","regional","immediate openings"],
                "creative_types": ["single image"],
            },
            "strengths": ["Texas regional SEO","overnight niche","low competition in region"],
            "weaknesses": ["limited national presence","low ad investment","small brand"],
            "opportunity_gaps": ["national expansion","Amazon DSP angle","driver community content"],
        },
    ],
    "knowledge_graph": {
        "entities": {
            "keywords": [
                {"id":"kw_amazon_driver","label":"amazon delivery driver jobs","type":"head_term","volume":8100,"our_position":12,"top_competitor":"Amazon DSP"},
                {"id":"kw_amazon_dsp","label":"amazon dsp jobs","type":"head_term","volume":6600,"our_position":None,"top_competitor":"None"},
                {"id":"kw_driver_pay","label":"amazon delivery driver pay","type":"informational","volume":5400,"our_position":6,"top_competitor":"LaserShip"},
                {"id":"kw_flex","label":"amazon flex driver","type":"adjacent","volume":14800,"our_position":None,"top_competitor":"Amazon DSP"},
            ],
            "campaigns": [
                {"id":"camp_local_driver","label":"Amazon Driver Jobs | Local","channel":"google_ads","roas":None,"leads":182},
                {"id":"camp_fb_recruit","label":"Driver Recruitment | FB","channel":"facebook","roas":None,"leads":168},
                {"id":"camp_prior_applicants","label":"Prior Amazon Applicants","channel":"facebook","roas":None,"leads":82},
            ],
            "landing_pages": [
                {"id":"lp_apply","label":"/apply-now","conv_rate":3.36,"top_traffic":"google_ads"},
                {"id":"lp_amazon_jobs","label":"/amazon-delivery-driver-jobs","conv_rate":3.52,"top_traffic":"google_ads"},
                {"id":"lp_dsp","label":"/amazon-dsp-jobs (missing)","conv_rate":0,"top_traffic":"none"},
            ],
            "audiences": [
                {"id":"aud_prior_applicants","label":"Prior Amazon Applicants","performance_score":91},
                {"id":"aud_gig_workers","label":"Gig Workers Interest","performance_score":84},
            ],
            "offers": [
                {"id":"off_apply","label":"Apply in 5 Minutes","conversion_strength":"high"},
                {"id":"off_pay","label":"$X/hr Pay Transparency","conversion_strength":"high"},
            ],
        },
        "relationships": [
            {"from_entity":"kw_amazon_driver","to_entity":"lp_amazon_jobs","type":"drives_traffic","strength":0.86,"notes":"Primary keyword to Amazon jobs page. Strong alignment."},
            {"from_entity":"kw_amazon_dsp","to_entity":"lp_dsp","type":"opportunity_gap","strength":0.0,"notes":"Amazon DSP jobs keyword (6,600/mo) has zero competition. No page exists."},
            {"from_entity":"aud_prior_applicants","to_entity":"off_apply","type":"responds_to","strength":0.91,"notes":"Prior applicants return at 91% performance score — best retargeting audience."},
            {"from_entity":"kw_driver_pay","to_entity":"lp_apply","type":"partial_match","strength":0.54,"notes":"Pay-focused searchers land on apply page which lacks pay details. Friction point."},
        ],
        "insights": [
            {"type":"gap","title":"Amazon DSP Jobs Page Missing — 6,600/mo Uncontested","description":"'Amazon dsp jobs' (6,600/mo) has no top-10 competitor. Amazon DSP's own page is not optimized for this exact query. Creating /amazon-dsp-jobs would rank within 30-60 days with minimal competition.","entities":["kw_amazon_dsp","lp_dsp"],"confidence":94,"action":"Create /amazon-dsp-jobs page immediately"},
            {"type":"performance","title":"Pay Info Seekers Land on Apply Page — Friction","description":"Searchers for 'amazon delivery driver pay' (5,400/mo) land on /apply-now which shows application steps but not pay rates. Adding a /driver-pay-benefits section and linking pay-focused ads to a pay-first landing page would reduce bounce.","entities":["kw_driver_pay","lp_apply"],"confidence":86,"action":"Create pay-focused landing page variant for pay-intent traffic"},
            {"type":"competitor","title":"Amazon DSP Brand Can Be Leveraged — We ARE a DSP","description":"As an Amazon DSP operator, we can legitimately compete against other DSPs using Amazon's own brand terms. OnTrac and LaserShip do not have this advantage. This is a unique competitive positioning play.","entities":["kw_amazon_driver","camp_local_driver"],"confidence":88,"action":"Launch Amazon DSP-specific ad campaigns emphasizing our DSP status"},
            {"type":"audience","title":"Prior Applicants Retargeting Underutilized","description":"Prior Amazon applicants retarget at 91% performance score and $73 CPA — program best. Budget only $600/mo. Scale to $1,500 would yield est. 45 additional leads at existing CPA.","entities":["aud_prior_applicants","camp_prior_applicants"],"confidence":89,"action":"Scale prior applicant retargeting budget to $1,500/mo"},
        ],
    },
    "recommendations": [
        {
            "id":"rec_ivan_01","channel":"seo","title":"Create /amazon-dsp-jobs Landing Page — Zero Competition",
            "description":"'Amazon dsp jobs' (6,600/mo) has no top-10 competitor. We are an Amazon DSP operator — this is our strongest positioning. A dedicated page would rank within 30-60 days.",
            "internal_trigger":"Zero impressions for 'amazon dsp jobs' keyword despite being a literal Amazon DSP. Gap confirmed by knowledge graph.",
            "competitor_insight":"Amazon DSP's own recruitment page ranks for generic 'amazon driver' terms but NOT for 'amazon dsp jobs' specifically. No other competitor targets this exact query.",
            "knowledge_graph_insight":"Amazon DSP jobs keyword has 0.0 strength connection to any landing page. Opportunity score 94 — highest in the program.",
            "priority":1,"expected_leads_impact":"+32/mo","expected_conversion_impact":"+6/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"medium","confidence":94,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"keyword","name":"amazon dsp jobs"},{"type":"landing_page","name":"/amazon-dsp-jobs (new)"}],
        },
        {
            "id":"rec_ivan_02","channel":"seo","title":"Add JobPosting Schema + Google for Jobs Integration",
            "description":"Job pages missing JobPosting schema. Google for Jobs displays job listings in a rich SERP feature — direct applications from search results. OnTrac and Amazon DSP both appear in Google for Jobs. We do not.",
            "internal_trigger":"Technical audit: JobPosting schema missing on all job pages. Google for Jobs is not indexing our positions.",
            "competitor_insight":"OnTrac and Amazon DSP appear in Google for Jobs results. This drives direct applications without requiring a click-through. Estimated 40-60% increase in application volume.",
            "knowledge_graph_insight":"Application page (/apply-now) has highest conv rate (3.36%) — Google for Jobs would drive higher-intent traffic directly to this page.",
            "priority":1,"expected_leads_impact":"+48/mo","expected_conversion_impact":"+9/mo","estimated_spend_impact":"$0",
            "implementation_difficulty":"low","confidence":92,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"technical","name":"JobPosting Schema"},{"type":"landing_page","name":"/apply-now"}],
        },
        {
            "id":"rec_ivan_03","channel":"facebook_ads","title":"Scale Prior Applicants Retargeting — +$900 Budget",
            "description":"Prior Amazon applicants retarget at $73 CPA — program best. Budget $600/mo. Scale to $1,500 targeting est. 45 additional leads at existing CPA.",
            "internal_trigger":"Performance score 91/100. CPA $73 vs. program average $66. Audience size supports scaling.",
            "competitor_insight":"OnTrac uses aggressive retargeting with sign-on bonus offers. Our prior applicants are already pre-qualified — sign-on bonus is not needed to re-engage them.",
            "knowledge_graph_insight":"Prior applicants → apply offer relationship scores 0.91. Highest retargeting signal in the program.",
            "priority":1,"expected_leads_impact":"+45/mo","expected_conversion_impact":"+8/mo","estimated_spend_impact":"+$900/mo",
            "implementation_difficulty":"low","confidence":89,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"audience","name":"Prior Amazon Applicants"},{"type":"campaign","name":"Driver Recruitment | FB"}],
        },
        {
            "id":"rec_ivan_04","channel":"google_ads","title":"Pause Wasted Spend — Reallocate $740 to Amazon DSP Terms",
            "description":"'Warehouse jobs near me' and 'truck driver jobs' generated $740 spend with 2 conversions total. Reallocate to amazon dsp jobs and delivery driver hiring exact match terms which convert at $63-79 CPA.",
            "internal_trigger":"$740 wasted on wrong intent keywords. 'Warehouse jobs' and 'truck driver' are wrong audience segments.",
            "competitor_insight":"OnTrac and LaserShip do not bid on these terms — industry confirmation these are off-target keywords for last-mile delivery recruitment.",
            "knowledge_graph_insight":"No relationship between warehouse/truck keywords and any converting landing page in the graph.",
            "priority":1,"expected_leads_impact":"+12/mo","expected_conversion_impact":"+2/mo","estimated_spend_impact":"-$740 wasted",
            "implementation_difficulty":"low","confidence":96,"requires_approval":False,
            "status":"ready",
            "linked_entities":[{"type":"keyword","name":"warehouse jobs near me"},{"type":"keyword","name":"truck driver jobs"}],
        },
    ],
    "implementation_history": [
        {"id":"impl_ivan_01","date":"2026-02-20","recommendation_title":"Launch Driver Pay Transparency Page","channel":"seo","status":"completed","leads_before":38,"leads_after":62,"conversions_before":7,"conversions_after":11,"spend_before":0,"spend_after":0,"notes":"Pay page ranks #6 for 'delivery driver pay'. Reduced bounce from pay-intent traffic by 34%."},
        {"id":"impl_ivan_02","date":"2026-01-15","recommendation_title":"Facebook Driver Pay Creative Test","channel":"facebook_ads","status":"completed","leads_before":96,"leads_after":128,"conversions_before":22,"conversions_after":32,"spend_before":1000,"spend_after":1400,"notes":"'Driver Pay Highlight' creative outperformed previous by 42% on CPL. Now primary creative."},
        {"id":"impl_ivan_03","date":"2025-12-08","recommendation_title":"Add City-Specific Delivery Driver Ad Groups","channel":"google_ads","status":"completed","leads_before":142,"leads_after":182,"conversions_before":28,"conversions_after":38,"spend_before":1800,"spend_after":2400,"notes":"Local city campaigns outperform generic terms by 31% on CPA. 5 city campaigns active."},
    ],
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
BUSINESS_GROUPS = {
    "bcat_logistics": _bcat,
    "best_care_auto": _best_care,
    "ivan_amazon": _ivan,
}

def get_groups_summary():
    return [
        {"id": g["id"], "name": g["name"], "short_name": g["short_name"],
         "website": g["website"], "industry": g["industry"]}
        for g in BUSINESS_GROUPS.values()
    ]

def get_group(group_id):
    return BUSINESS_GROUPS.get(group_id)

def get_overview(group_id):
    g = get_group(group_id)
    return g["overview"] if g else None

def get_seo(group_id):
    g = get_group(group_id)
    return g["seo"] if g else None

def get_google_ads(group_id):
    g = get_group(group_id)
    return g["google_ads"] if g else None

def get_facebook_ads(group_id):
    g = get_group(group_id)
    return g["facebook_ads"] if g else None

def get_competitors(group_id):
    g = get_group(group_id)
    return g["competitors"] if g else None

def get_knowledge_graph(group_id):
    g = get_group(group_id)
    return g["knowledge_graph"] if g else None

def get_recommendations(group_id):
    g = get_group(group_id)
    return g["recommendations"] if g else None

def get_implementation_history(group_id):
    g = get_group(group_id)
    return g["implementation_history"] if g else None

def update_recommendation_status(group_id, rec_id, status):
    g = get_group(group_id)
    if not g:
        return False
    for rec in g["recommendations"]:
        if rec["id"] == rec_id:
            rec["status"] = status
            return True
    return False
