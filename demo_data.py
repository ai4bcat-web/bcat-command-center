"""
demo_data.py — Mock data for BCAT Command Center demo dashboard.
All data is synthetic. Zero production dependencies.
"""
from datetime import date, timedelta
import random

# ── Helpers ──────────────────────────────────────────────────────────────────

def _months():
    return [f"2025-{m:02d}" for m in range(1, 13)]

# ── Finance: Brokerage ───────────────────────────────────────────────────────

MONTHLY_BROKERAGE = [
    {"month": "2025-01", "revenue": 580000,  "carrier_pay": 417600,  "gross_profit": 162400,  "brokerage_margin": 28.0, "shipment_volume": 312},
    {"month": "2025-02", "revenue": 621000,  "carrier_pay": 446000,  "gross_profit": 175000,  "brokerage_margin": 28.2, "shipment_volume": 334},
    {"month": "2025-03", "revenue": 689000,  "carrier_pay": 494000,  "gross_profit": 195000,  "brokerage_margin": 28.3, "shipment_volume": 371},
    {"month": "2025-04", "revenue": 738000,  "carrier_pay": 524000,  "gross_profit": 214000,  "brokerage_margin": 29.0, "shipment_volume": 397},
    {"month": "2025-05", "revenue": 782000,  "carrier_pay": 552000,  "gross_profit": 230000,  "brokerage_margin": 29.4, "shipment_volume": 421},
    {"month": "2025-06", "revenue": 820000,  "carrier_pay": 577000,  "gross_profit": 243000,  "brokerage_margin": 29.6, "shipment_volume": 441},
    {"month": "2025-07", "revenue": 858000,  "carrier_pay": 602000,  "gross_profit": 256000,  "brokerage_margin": 29.8, "shipment_volume": 462},
    {"month": "2025-08", "revenue": 903000,  "carrier_pay": 633000,  "gross_profit": 270000,  "brokerage_margin": 29.9, "shipment_volume": 486},
    {"month": "2025-09", "revenue": 871000,  "carrier_pay": 609000,  "gross_profit": 262000,  "brokerage_margin": 30.1, "shipment_volume": 469},
    {"month": "2025-10", "revenue": 944000,  "carrier_pay": 659000,  "gross_profit": 285000,  "brokerage_margin": 30.2, "shipment_volume": 508},
    {"month": "2025-11", "revenue": 978000,  "carrier_pay": 682000,  "gross_profit": 296000,  "brokerage_margin": 30.3, "shipment_volume": 526},
    {"month": "2025-12", "revenue": 914000,  "carrier_pay": 632000,  "gross_profit": 282000,  "brokerage_margin": 30.9, "shipment_volume": 492},
]

_BROKERAGE_CUSTOMERS = [
    ("Midwest Freight Solutions", 0.090),
    ("TransAmerica Logistics",    0.076),
    ("National Carrier Group",    0.069),
    ("Eagle Transport Inc",       0.061),
    ("Delta Shipping Co",         0.055),
    ("Horizon Freight LLC",       0.050),
    ("Peak Load Solutions",       0.046),
    ("Summit Transport",          0.041),
    ("Keystone Carriers",         0.037),
    ("American Freight Inc",      0.033),
]

def _brokerage_customers_for_month(month_row):
    rows = []
    rev = month_row["revenue"]
    vol = month_row["shipment_volume"]
    margin = month_row["brokerage_margin"] / 100
    for rank, (name, share) in enumerate(_BROKERAGE_CUSTOMERS, 1):
        r = round(rev * share)
        v = max(1, round(vol * share * 1.1))
        cp = round(r * (1 - margin - 0.01))
        gp = r - cp
        pct = round(gp / r * 100, 1) if r else 0
        rows.append({
            "month": month_row["month"], "rank": rank, "customer": name,
            "revenue": r, "shipment_volume": v,
            "carrier_pay": cp, "gross_profit": gp, "profit_percentage": pct,
        })
    return rows

BROKERAGE_TOP_CUSTOMERS_BY_MONTH = []
for _mb in MONTHLY_BROKERAGE:
    BROKERAGE_TOP_CUSTOMERS_BY_MONTH.extend(_brokerage_customers_for_month(_mb))

# ── Finance: Ivan Cartage ────────────────────────────────────────────────────

IVAN_MONTHLY = [
    {"month": "2025-01", "revenue": 198000, "expenses": 141000, "true_profit": 57000,  "miles": 58000, "shipment_volume": 87},
    {"month": "2025-02", "revenue": 207000, "expenses": 147000, "true_profit": 60000,  "miles": 61000, "shipment_volume": 91},
    {"month": "2025-03", "revenue": 224000, "expenses": 158000, "true_profit": 66000,  "miles": 66000, "shipment_volume": 98},
    {"month": "2025-04", "revenue": 236000, "expenses": 164000, "true_profit": 72000,  "miles": 69000, "shipment_volume": 103},
    {"month": "2025-05", "revenue": 248000, "expenses": 172000, "true_profit": 76000,  "miles": 73000, "shipment_volume": 108},
    {"month": "2025-06", "revenue": 242000, "expenses": 169000, "true_profit": 73000,  "miles": 71000, "shipment_volume": 105},
    {"month": "2025-07", "revenue": 234000, "expenses": 162000, "true_profit": 72000,  "miles": 69000, "shipment_volume": 102},
    {"month": "2025-08", "revenue": 259000, "expenses": 179000, "true_profit": 80000,  "miles": 76000, "shipment_volume": 113},
    {"month": "2025-09", "revenue": 238000, "expenses": 165000, "true_profit": 73000,  "miles": 70000, "shipment_volume": 104},
    {"month": "2025-10", "revenue": 262000, "expenses": 180000, "true_profit": 82000,  "miles": 77000, "shipment_volume": 115},
    {"month": "2025-11", "revenue": 245000, "expenses": 169000, "true_profit": 76000,  "miles": 72000, "shipment_volume": 107},
    {"month": "2025-12", "revenue": 220000, "expenses": 167000, "true_profit": 53000,  "miles": 80000, "shipment_volume": 96},
]
for _im in IVAN_MONTHLY:
    m = _im["miles"]
    _im["revenue_per_mile"]  = round(_im["revenue"]  / m, 2) if m else 0
    _im["cost_per_mile"]     = round(_im["expenses"] / m, 2) if m else 0
    _im["profit_per_mile"]   = round(_im["true_profit"] / m, 2) if m else 0

_IVAN_EXPENSE_CATS = [
    ("Driver Wages",  0.41),
    ("Fuel",          0.23),
    ("Depreciation",  0.10),
    ("Maintenance",   0.09),
    ("Insurance",     0.08),
    ("Tolls",         0.05),
    ("Admin & Other", 0.04),
]

IVAN_EXPENSES_CATEGORY_MONTHLY = []
for _im in IVAN_MONTHLY:
    for cat, share in _IVAN_EXPENSE_CATS:
        IVAN_EXPENSES_CATEGORY_MONTHLY.append({
            "month": _im["month"], "category": cat,
            "amount": round(_im["expenses"] * share),
            "miles": round(_im["miles"] * share),
        })

_IVAN_CUSTOMERS = [
    "Amazon DSP Chicago",
    "Amazon DSP Milwaukee",
    "Amazon DSP Indianapolis",
    "Amazon DSP Detroit",
    "Amazon DSP Cincinnati",
]
_IVAN_SHARES = [0.31, 0.25, 0.21, 0.14, 0.09]

IVAN_TOP_CUSTOMERS_BY_MONTH = []
for _im in IVAN_MONTHLY:
    for rank, (name, share) in enumerate(zip(_IVAN_CUSTOMERS, _IVAN_SHARES), 1):
        r = round(_im["revenue"] * share)
        IVAN_TOP_CUSTOMERS_BY_MONTH.append({
            "month": _im["month"], "rank": rank, "customer": name,
            "revenue": r, "volume": max(1, round(_im["shipment_volume"] * share)),
        })

# ── Dashboard summary totals ─────────────────────────────────────────────────

_br_total_rev  = sum(r["revenue"]       for r in MONTHLY_BROKERAGE)
_br_total_cp   = sum(r["carrier_pay"]   for r in MONTHLY_BROKERAGE)
_br_total_gp   = sum(r["gross_profit"]  for r in MONTHLY_BROKERAGE)
_iv_total_rev  = sum(r["revenue"]       for r in IVAN_MONTHLY)
_iv_total_exp  = sum(r["expenses"]      for r in IVAN_MONTHLY)
_iv_total_prof = sum(r["true_profit"]   for r in IVAN_MONTHLY)
_iv_total_mi   = sum(r["miles"]         for r in IVAN_MONTHLY)

DASHBOARD_DATA = {
    "report_start_date":    "2025-01-01",
    "report_end_date":      "2025-12-31",
    "cost_savings":         1200000,
    "efficiency_gain":      30,
    "total_company_revenue": _br_total_rev + _iv_total_rev,
    "brokerage": {
        "gross_revenue":    _br_total_rev,
        "carrier_pay":      _br_total_cp,
        "gross_profit":     _br_total_gp,
        "brokerage_margin": round(_br_total_gp / _br_total_rev * 100, 1),
        "monthly_brokerage_summary":        MONTHLY_BROKERAGE,
        "brokerage_top_customers_by_month": BROKERAGE_TOP_CUSTOMERS_BY_MONTH,
    },
    "ivan": {
        "ivan_cartage_revenue":  _iv_total_rev,
        "ivan_expenses":         _iv_total_exp,
        "ivan_true_profit":      _iv_total_prof,
        "ivan_total_miles":      _iv_total_mi,
        "ivan_revenue_per_mile": round(_iv_total_rev  / _iv_total_mi, 2),
        "ivan_cost_per_mile":    round(_iv_total_exp  / _iv_total_mi, 2),
        "ivan_profit_per_mile":  round(_iv_total_prof / _iv_total_mi, 2),
        "ivan_monthly_true_profit":         IVAN_MONTHLY,
        "ivan_expenses_category_monthly":   IVAN_EXPENSES_CATEGORY_MONTHLY,
        "ivan_top_customers_by_month":      IVAN_TOP_CUSTOMERS_BY_MONTH,
    },
}

# ── Marketing Data ────────────────────────────────────────────────────────────

_MKT_SPEND_MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]

def _mkt_trends(google_base, fb_base, conv_base, growth=1.04):
    spend, conv = [], []
    g, f, c = google_base, fb_base, conv_base
    for mo in _MKT_SPEND_MONTHS:
        spend.append({"month": mo, "google": round(g), "facebook": round(f)})
        conv.append({"month": mo, "value": round(c)})
        g *= growth; f *= growth * 0.97; c *= growth * 1.02
    return spend, conv

def _mkt_seo_trend(base, growth=1.05):
    vals = []
    v = base
    for mo in _MKT_SPEND_MONTHS:
        vals.append({"month": mo, "value": round(v)})
        v *= growth
    return vals

MARKETING_DATA = {
    "bcat_logistics": {
        "overview": {
            "kpis": {
                "monthly_spend": 33500, "monthly_conversions": 50,
                "blended_roas": 4.2, "organic_sessions": 8420, "domain_authority": 42,
            },
            "channels": {
                "seo":          {"spend": 0,     "leads": 84, "booked_calls": 18, "conversions": 12, "conv_rate": 14.3, "cpl": 0,    "cac": 0,    "sessions": 8420},
                "google_ads":   {"spend": 15200, "leads": 42, "booked_calls": 14, "conversions": 13, "conv_rate": 31.0, "cpl": 362,  "cac": 1169, "roas": 3.8, "cpc": 4.20, "ctr": 3.8},
                "facebook_ads": {"spend": 9300,  "leads": 189,"booked_calls": 12, "conversions": 6,  "conv_rate": 3.2,  "cpl": 49,   "cac": 1550, "roas": 2.6, "cpc": 6.50, "ctr": 2.1},
                "linkedin":     {"spend": 6800,  "leads": 68, "booked_calls": 16, "conversions": 8,  "conv_rate": 11.8, "cpl": 100,  "cac": 850,  "roas": 2.9},
                "email":        {"spend": 2200,  "leads": 214,"booked_calls": 37, "conversions": 11, "conv_rate": 5.1,  "cpl": 10.3, "cac": 200,  "open_rate": 28.4, "reply_rate": 4.9},
            },
            "kpis_extended": {
                "total_leads_mtd": 597, "total_booked_calls_mtd": 97, "total_conversions_mtd": 50,
                "blended_cpl": 53, "blended_cac": 820, "attributed_revenue": 412000,
                "best_channel": "SEO",  "top_campaign": "BCAT Freight Broker — Brand",
            },
            "channel_table": [
                {"channel": "SEO / Organic",  "spend": 0,     "leads": 84,  "booked_calls": 18, "conversions": 12, "conv_rate": 14.3, "cpl": 0,    "cac": 0,    "roas": None, "trend": "+12%"},
                {"channel": "Google Ads",     "spend": 15200, "leads": 42,  "booked_calls": 14, "conversions": 13, "conv_rate": 31.0, "cpl": 362,  "cac": 1169, "roas": 3.8,  "trend": "+8%"},
                {"channel": "Facebook Ads",   "spend": 9300,  "leads": 189, "booked_calls": 12, "conversions": 6,  "conv_rate": 3.2,  "cpl": 49,   "cac": 1550, "roas": 2.6,  "trend": "+5%"},
                {"channel": "LinkedIn Ads",   "spend": 6800,  "leads": 68,  "booked_calls": 16, "conversions": 8,  "conv_rate": 11.8, "cpl": 100,  "cac": 850,  "roas": 2.9,  "trend": "+18%"},
                {"channel": "Email Outreach", "spend": 2200,  "leads": 214, "booked_calls": 37, "conversions": 11, "conv_rate": 5.1,  "cpl": 10,   "cac": 200,  "roas": None, "trend": "+3%"},
            ],
            "trends": dict(zip(
                ["spend_by_channel", "conversions"],
                _mkt_trends(12000, 7400, 22)
            )),
            "trends_extended": {
                "spend_by_channel": [
                    {"month": "2025-01", "google": 10800, "facebook": 7100, "linkedin": 4200, "email": 900},
                    {"month": "2025-02", "google": 11200, "facebook": 7300, "linkedin": 4400, "email": 950},
                    {"month": "2025-03", "google": 11800, "facebook": 7600, "linkedin": 4800, "email": 980},
                    {"month": "2025-04", "google": 12400, "facebook": 7900, "linkedin": 5200, "email": 1000},
                    {"month": "2025-05", "google": 13100, "facebook": 8200, "linkedin": 5600, "email": 1050},
                    {"month": "2025-06", "google": 13800, "facebook": 8600, "linkedin": 6000, "email": 1080},
                    {"month": "2025-07", "google": 14200, "facebook": 8900, "linkedin": 6200, "email": 1100},
                    {"month": "2025-08", "google": 14600, "facebook": 9100, "linkedin": 6400, "email": 1120},
                    {"month": "2025-09", "google": 14900, "facebook": 9000, "linkedin": 6500, "email": 1140},
                    {"month": "2025-10", "google": 15000, "facebook": 9200, "linkedin": 6700, "email": 1160},
                    {"month": "2025-11", "google": 15100, "facebook": 9300, "linkedin": 6800, "email": 1180},
                    {"month": "2025-12", "google": 15200, "facebook": 9300, "linkedin": 6800, "email": 1200},
                ],
                "leads_by_channel": [
                    {"month": "2025-01", "google": 28, "facebook": 128, "linkedin": 38, "email": 142, "seo": 58},
                    {"month": "2025-02", "google": 30, "facebook": 134, "linkedin": 42, "email": 158, "seo": 62},
                    {"month": "2025-03", "google": 32, "facebook": 148, "linkedin": 48, "email": 168, "seo": 68},
                    {"month": "2025-04", "google": 34, "facebook": 156, "linkedin": 54, "email": 178, "seo": 72},
                    {"month": "2025-05", "google": 36, "facebook": 162, "linkedin": 58, "email": 188, "seo": 76},
                    {"month": "2025-06", "google": 38, "facebook": 168, "linkedin": 62, "email": 196, "seo": 78},
                    {"month": "2025-07", "google": 39, "facebook": 174, "linkedin": 64, "email": 202, "seo": 80},
                    {"month": "2025-08", "google": 40, "facebook": 178, "linkedin": 66, "email": 208, "seo": 82},
                    {"month": "2025-09", "google": 39, "facebook": 172, "linkedin": 65, "email": 205, "seo": 80},
                    {"month": "2025-10", "google": 41, "facebook": 180, "linkedin": 67, "email": 210, "seo": 82},
                    {"month": "2025-11", "google": 41, "facebook": 184, "linkedin": 68, "email": 212, "seo": 84},
                    {"month": "2025-12", "google": 42, "facebook": 189, "linkedin": 68, "email": 214, "seo": 84},
                ],
            },
            "competitors": [
                {"name": "FreightQuote Pro",    "google_ads": {"status": "active", "ads_count": 8},  "facebook_ads": {"status": "active", "ads_count": 4}},
                {"name": "LoadBoard Direct",    "google_ads": {"status": "active", "ads_count": 5},  "facebook_ads": {"status": "inactive"}},
                {"name": "FastFreight Network", "google_ads": {"status": "active", "ads_count": 12}, "facebook_ads": {"status": "active", "ads_count": 9}},
            ],
        },
        "seo": {
            "metrics": {
                "domain_authority": 42, "organic_sessions": 8420, "ranked_keywords": 347,
                "avg_position": "14.2", "core_web_vitals_score": 81, "backlinks": 1840,
                "keyword_distribution": {"top_3": 12, "top_10": 48, "top_30": 89, "below_30": 198},
            },
            "trends": {"organic_sessions": _mkt_seo_trend(6200, 1.06)},
            "keywords": [
                {"keyword": "freight broker chicago",           "position": 3,  "volume": 2200, "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "logistics company chicago",        "position": 7,  "volume": 2800, "difficulty": "High",   "intent": "Commercial"},
                {"keyword": "ltl freight quotes midwest",       "position": 11, "volume": 4100, "difficulty": "High",   "intent": "Transactional"},
                {"keyword": "truckload brokerage illinois",     "position": 6,  "volume": 1400, "difficulty": "Medium", "intent": "Informational"},
                {"keyword": "flatbed freight rates chicago",    "position": 9,  "volume": 890,  "difficulty": "Low",    "intent": "Transactional"},
                {"keyword": "expedited freight broker",         "position": 5,  "volume": 1680, "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "reefer freight broker midwest",    "position": 14, "volume": 1650, "difficulty": "Medium", "intent": "Transactional"},
                {"keyword": "intermodal shipping broker il",   "position": 18, "volume": 980,  "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "spot freight pricing tool",        "position": 16, "volume": 720,  "difficulty": "Low",    "intent": "Informational"},
                {"keyword": "freight broker near me",           "position": 8,  "volume": 6400, "difficulty": "High",   "intent": "Commercial"},
                {"keyword": "drayage services chicago",         "position": 12, "volume": 1120, "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "partial truckload freight quote",  "position": 24, "volume": 860,  "difficulty": "Low",    "intent": "Transactional"},
            ],
            "technical": {
                "page_speed_mobile": "78/100", "page_speed_desktop": "91/100",
                "core_web_vitals_score": "81/100", "schema_markup": True,
                "mobile_friendly": True, "ssl_certificate": True,
                "xml_sitemap": True, "robots_txt": True,
            },
        },
        "google_ads": {
            "metrics": {
                "monthly_spend": 15200, "conversions": 13, "roas": 3.8,
                "avg_cpc": 4.20, "ctr": 3.8, "quality_score": "7.8 avg",
                "impressions": 402000, "clicks": 3619, "cost_per_conv": 1169,
            },
            "campaigns": [
                {"name": "BCAT Freight Broker — Brand",              "status": "Active", "spend": 3200,  "impressions": 42400,  "clicks": 1612,  "ctr": 3.80, "cpc": 1.98, "conversions": 4,  "cpa": 800,  "roas": 4.9},
                {"name": "Chicago Freight Quotes — LTL/Truckload",   "status": "Active", "spend": 4800,  "impressions": 98200,  "clicks": 924,   "ctr": 0.94, "cpc": 5.19, "conversions": 4,  "cpa": 1200, "roas": 3.2},
                {"name": "Midwest Logistics Services — Broad",       "status": "Active", "spend": 2900,  "impressions": 121000, "clicks": 604,   "ctr": 0.50, "cpc": 4.80, "conversions": 2,  "cpa": 1450, "roas": 2.8},
                {"name": "Expedited Freight — High Intent",          "status": "Active", "spend": 2400,  "impressions": 31800,  "clicks": 864,   "ctr": 2.72, "cpc": 2.78, "conversions": 2,  "cpa": 1200, "roas": 4.1},
                {"name": "Flatbed & Reefer Freight — Specialty",     "status": "Active", "spend": 1200,  "impressions": 48600,  "clicks": 388,   "ctr": 0.80, "cpc": 3.09, "conversions": 1,  "cpa": 1200, "roas": 3.6},
                {"name": "Competitor Conquest — FreightQuote/Echo",  "status": "Active", "spend": 800,   "impressions": 22800,  "clicks": 182,   "ctr": 0.80, "cpc": 4.40, "conversions": 0,  "cpa": 0,    "roas": 0},
                {"name": "Display — Freight Trade Audiences",        "status": "Paused", "spend": 1900,  "impressions": 38000,  "clicks": 45,    "ctr": 0.12, "cpc": 42.22,"conversions": 0,  "cpa": 0,    "roas": 1.9},
            ],
            "trends": {
                "spend_conversions": [
                    {"month": m, "spend": round(10000 * (1.04 ** i)), "conversions": round(8 * (1.05 ** i))}
                    for i, m in enumerate(_MKT_SPEND_MONTHS)
                ],
                "spend": [
                    {"month": m, "value": round(10000 * (1.04 ** i))}
                    for i, m in enumerate(_MKT_SPEND_MONTHS)
                ],
                "conversions": [
                    {"month": m, "value": round(8 * (1.05 ** i))}
                    for i, m in enumerate(_MKT_SPEND_MONTHS)
                ],
            },
        },
        "facebook_ads": {
            "metrics": {
                "monthly_spend": 9300, "conversions": 6, "roas": 2.6,
                "reach": 48200, "impressions": 142000, "cpm": 65.5,
                "avg_cpc": 6.50, "ctr": 2.1, "quality_score": "6.4 avg",
                "ad_fatigue_score": 58,
            },
            "campaigns": [
                {"name": "Freight Shipper Decision-Makers — Lead Gen", "status": "Active", "objective": "Lead Generation",  "spend": 4100, "reach": 22400, "impressions": 68200, "clicks": 1432, "ctr": 2.10, "cpc": 2.86, "leads": 89,  "cpl": 46, "conversions": 3, "cpa": 1367},
                {"name": "Midwest Logistics Lookalike 1% — Top Accounts","status": "Active", "objective": "Lead Generation",  "spend": 3200, "reach": 18900, "impressions": 52800, "clicks": 1056, "ctr": 2.00, "cpc": 3.03, "leads": 64,  "cpl": 50, "conversions": 2, "cpa": 1600},
                {"name": "Retargeting — Freight Quote Page Visitors",  "status": "Active", "objective": "Conversions",       "spend": 2000, "reach": 6900,  "impressions": 21000, "clicks": 378,  "ctr": 1.80, "cpc": 5.29, "leads": 36,  "cpl": 56, "conversions": 1, "cpa": 2000},
            ],
            "audiences": [
                {"name": "Logistics Decision-Makers",       "percentage": 42},
                {"name": "Lookalike 1% — Top Customers",   "percentage": 31},
                {"name": "Remarketing — Quote Visitors",   "percentage": 18},
                {"name": "Broad Freight Interest",         "percentage": 9},
            ],
            "trends": {
                "spend": [
                    {"month": "2025-01", "value": 6800},
                    {"month": "2025-02", "value": 7100},
                    {"month": "2025-03", "value": 7600},
                    {"month": "2025-04", "value": 7900},
                    {"month": "2025-05", "value": 8200},
                    {"month": "2025-06", "value": 8600},
                    {"month": "2025-07", "value": 8900},
                    {"month": "2025-08", "value": 9100},
                    {"month": "2025-09", "value": 9000},
                    {"month": "2025-10", "value": 9200},
                    {"month": "2025-11", "value": 9300},
                    {"month": "2025-12", "value": 9300},
                ],
            },
        },
        "knowledge_graph": {
            "entities": [
                {"name": "BCAT Logistics",           "type": "Organization", "status": "Verified",  "score": 0.94},
                {"name": "Chicago, IL",              "type": "Location",     "status": "Linked",    "score": 0.88},
                {"name": "Freight Brokerage",        "type": "Service",      "status": "Linked",    "score": 0.82},
                {"name": "LTL Shipping",             "type": "Service",      "status": "Linked",    "score": 0.76},
                {"name": "Truckload Services",       "type": "Service",      "status": "Linked",    "score": 0.79},
                {"name": "Expedited Freight",        "type": "Service",      "status": "Pending",   "score": 0.61},
                {"name": "Midwest Logistics Hub",    "type": "Concept",      "status": "Linked",    "score": 0.68},
                {"name": "Drayage Services",         "type": "Service",      "status": "Pending",   "score": 0.55},
                {"name": "FreightQuote Pro",         "type": "Competitor",   "status": "Monitored", "score": 0.71},
                {"name": "FastFreight Network",      "type": "Competitor",   "status": "Monitored", "score": 0.80},
            ],
            "relationships": [
                {"from": "BCAT Logistics",      "to": "Chicago, IL",        "type": "located_in",     "strength": 0.96},
                {"from": "BCAT Logistics",      "to": "Freight Brokerage",  "type": "provides",       "strength": 0.92},
                {"from": "BCAT Logistics",      "to": "LTL Shipping",       "type": "provides",       "strength": 0.84},
                {"from": "BCAT Logistics",      "to": "Truckload Services", "type": "provides",       "strength": 0.80},
                {"from": "BCAT Logistics",      "to": "Expedited Freight",  "type": "provides",       "strength": 0.62},
                {"from": "Freight Brokerage",   "to": "Midwest Logistics Hub", "type": "part_of",    "strength": 0.74},
                {"from": "Chicago, IL",         "to": "Midwest Logistics Hub", "type": "anchor_for", "strength": 0.78},
                {"from": "FreightQuote Pro",    "to": "Freight Brokerage",  "type": "competes_in",    "strength": 0.71},
                {"from": "FastFreight Network", "to": "Freight Brokerage",  "type": "competes_in",    "strength": 0.80},
            ],
            "insights": [
                {"title": "Brand Entity Verified", "description": "BCAT entity verified on Google — brand searches up 34% YoY. Knowledge Panel shows in 92% of brand queries.", "impact": "high"},
                {"title": "LTL / Truckload Entity Gap", "description": "'LTL Shipping' entity linked but score 0.76 — publish 3 authoritative pages around LTL to push score above 0.85.", "impact": "high"},
                {"title": "Expedited Freight Opportunity", "description": "Expedited Freight entity still Pending (score 0.61) — competitors lack this entity. First-mover advantage available.", "impact": "medium"},
                {"title": "Drayage Entity Unclaimed", "description": "Drayage Services entity at Pending status — zero competitors have this entity verified in the Chicago market.", "impact": "medium"},
                {"title": "Competitor Gap — FastFreight", "description": "FastFreight Network has high entity score (0.80) for brand but no LTL or drayage entities — attack those with content.", "impact": "high"},
            ],
        },
        "recommendations": [
            {"id": 1, "status": "implemented", "channel": "google_ads",   "category": "google_ads",   "priority": "high",   "title": "Increase Brand campaign budget +$800/mo",             "description": "Brand campaign ROAS of 4.9x — budget-constrained. Incremental spend returns ~$4.90 per $1.", "impact": "high", "effort": "low",    "estimated_impact": "$3,900/mo additional revenue"},
            {"id": 2, "status": "implemented", "channel": "google_ads",   "category": "google_ads",   "priority": "high",   "title": "Add 47 negative keywords across all campaigns",         "description": "Eliminated carrier/driver job-seeker traffic. CTR improved from 2.9% to 3.8%, wasted spend reduced ~$1,200/mo.", "impact": "high", "effort": "low", "estimated_impact": "-$1,200/mo wasted spend"},
            {"id": 3, "status": "pending",     "channel": "seo",          "category": "seo",          "priority": "high",   "title": "Publish LTL freight guide cluster (4 pages)",          "description": "Target 'ltl freight quotes midwest' (#11, 4,100 vol) and 3 related queries. Estimated +420 organic sessions/mo.", "impact": "high", "effort": "medium", "estimated_impact": "+420 organic visits/mo"},
            {"id": 4, "status": "in_progress", "channel": "seo",          "category": "seo",          "priority": "medium", "title": "Recover 12 broken backlinks (DA 40–55 sites)",          "description": "12 referring domains show 404s. Recovery estimated +4 DA points and +180 sessions/mo from referral.", "impact": "medium", "effort": "low",  "estimated_impact": "+4 DA, +180 sessions/mo"},
            {"id": 5, "status": "pending",     "channel": "seo",          "category": "seo",          "priority": "high",   "title": "Create drayage services landing page — Chicago",        "description": "Zero competitors have drayage-specific pages with Schema markup in Chicago. Clear path to top 5.", "impact": "high", "effort": "medium", "estimated_impact": "+180 leads/yr"},
            {"id": 6, "status": "pending",     "channel": "google_ads",   "category": "google_ads",   "priority": "medium", "title": "Activate Expedited Freight campaign — high CPC, high intent","description": "Expedited freight queries convert at 2x rate of LTL terms. Current gap in coverage = $48K/mo in addressable spend.", "impact": "high", "effort": "low",  "estimated_impact": "+6 conversions/mo"},
            {"id": 7, "status": "pending",     "channel": "facebook_ads", "category": "facebook_ads", "priority": "medium", "title": "Expand LAL audience to 2% — current 1% saturating",   "description": "1% LAL frequency is 4.2 — creative fatigue confirmed. Expand to 2% adds ~38K new users in ICP.", "impact": "medium", "effort": "low",  "estimated_impact": "+28 leads/mo"},
            {"id": 8, "status": "pending",     "channel": "linkedin",     "category": "linkedin",     "priority": "high",   "title": "Add Procurement Director targeting — missing ICP segment","description": "Supply chain and procurement directors represent 34% of BCAT's top accounts but are not currently targeted on LinkedIn.", "impact": "high", "effort": "low",  "estimated_impact": "+12 qualified leads/mo"},
            {"id": 9, "status": "pending",     "channel": "email",        "category": "email",        "priority": "medium", "title": "Launch Chicago manufacturer cold outreach sequence",     "description": "2,400 Midwest manufacturers not yet in nurture. 8-touch sequence at current rates = est. 115 leads, 14 conversions.", "impact": "high", "effort": "medium", "estimated_impact": "+14 conversions"},
            {"id": 10,"status": "pending",     "channel": "seo",          "category": "seo",          "priority": "low",    "title": "Add Schema markup to 8 service pages",                 "description": "Service pages lack LocalBusiness + Service schema. Adds rich results eligibility for high-intent queries.", "impact": "low",    "effort": "low",  "estimated_impact": "+12% CTR on service pages"},
        ],
        "competitors": [
            {"name": "FreightQuote Pro",    "google_ads": {"status": "active", "ads_count": 8,  "keywords": 214}, "facebook_ads": {"status": "active", "ads_count": 4}},
            {"name": "LoadBoard Direct",    "google_ads": {"status": "active", "ads_count": 5,  "keywords": 87},  "facebook_ads": {"status": "inactive"}},
            {"name": "FastFreight Network", "google_ads": {"status": "active", "ads_count": 12, "keywords": 398}, "facebook_ads": {"status": "active", "ads_count": 9}},
        ],
        "implementation_history": [
            {"date": "2025-12-10", "action": "Increased Brand campaign budget +$800/mo (Google Ads)", "result": "ROAS improved 4.1x → 4.9x within 14 days"},
            {"date": "2025-11-22", "action": "Added 47 negative keywords — blocked carrier/job-seeker traffic", "result": "CTR improved 2.9% → 3.8%, wasted spend -$1,200/mo"},
            {"date": "2025-11-05", "action": "Launched Facebook Lookalike 1% audience — Top Shippers seed", "result": "+28 leads in first 30 days, CPL $46"},
            {"date": "2025-10-18", "action": "Published 'Chicago LTL Freight Guide' blog post (1,800 words)", "result": "Now ranking #11 for 'ltl freight quotes midwest' — up from #34"},
            {"date": "2025-10-01", "action": "Launched LinkedIn 'Supply Chain Director Retargeting' campaign", "result": "14 leads in first 30 days, 3 conversions, ROAS 3.3x"},
            {"date": "2025-09-14", "action": "Rebuilt 'Request a Quote' landing page — new headline + form layout", "result": "Conversion rate improved 1.8% → 3.2% on paid traffic"},
            {"date": "2025-08-28", "action": "Started 'New Shipper Onboarding' email sequence (5-step)", "result": "18 conversions from 184 enrolled — 9.8% conversion rate"},
            {"date": "2025-08-08", "action": "Added Retargeting campaign — Freight Quote page visitors (Facebook)", "result": "+36 form fills/mo, CPL $56 (vs. $124 cold)"},
        ],
        "linkedin_campaigns": [
            {"name": "Chicago Freight Shipper Decision-Makers",      "status": "Active",   "budget": 3200, "impressions": 48400,  "clicks": 892,  "leads": 22, "conversions": 4, "cpl": 145, "cac": 800,  "roas": 3.1, "ctr": 1.84},
            {"name": "Supply Chain / Procurement Directors — Retarget","status": "Active", "budget": 2100, "impressions": 31200,  "clicks": 641,  "leads": 14, "conversions": 3, "cpl": 150, "cac": 700,  "roas": 3.3, "ctr": 2.05},
            {"name": "Thought Leadership — Freight Market 2025",     "status": "Active",   "budget": 1500, "impressions": 82000,  "clicks": 410,  "leads": 6,  "conversions": 1, "cpl": 250, "cac": 1500, "roas": 1.8, "ctr": 0.50},
            {"name": "Midwest Manufacturers — Cold Outreach",        "status": "Active",   "budget": 1800, "impressions": 28600,  "clicks": 514,  "leads": 18, "conversions": 2, "cpl": 100, "cac": 900,  "roas": 2.4, "ctr": 1.80},
            {"name": "Logistics Directors — Expedited Freight",      "status": "Paused",   "budget": 1200, "impressions": 19400,  "clicks": 272,  "leads": 8,  "conversions": 1, "cpl": 150, "cac": 1200, "roas": 2.1, "ctr": 1.40},
        ],
        "email_marketing": {
            "kpis": {
                "contacts_total": 4820, "contacts_active": 3140,
                "emails_sent_mtd": 9240, "open_rate": 28.4,
                "reply_rate": 4.9, "click_rate": 6.2,
                "leads_mtd": 214, "conversions_mtd": 11, "cpl": 5.6, "cac": 109,
            },
            "campaigns": [
                {"name": "Q1 Shipper Outreach — LTL Focus",       "status": "Active",   "contacts": 840,  "sent": 3360, "opened": 954,  "replied": 165, "meetings": 12, "open_rate": 28.4, "reply_rate": 4.9},
                {"name": "Warm Lead Re-engage — Nov Clicks",       "status": "Active",   "contacts": 212,  "sent": 636,  "opened": 198,  "replied": 36,  "meetings": 5,  "open_rate": 31.1, "reply_rate": 5.7},
                {"name": "Competitor Conquest — FreightQuote",     "status": "Active",   "contacts": 520,  "sent": 1560, "opened": 436,  "replied": 58,  "meetings": 7,  "open_rate": 28.0, "reply_rate": 3.7},
                {"name": "Cold Outreach — Midwest Manufacturers",  "status": "Complete", "contacts": 680,  "sent": 2040, "opened": 551,  "replied": 82,  "meetings": 9,  "open_rate": 27.0, "reply_rate": 4.0},
                {"name": "Holiday Check-In — Top 200 Shippers",   "status": "Complete", "contacts": 200,  "sent": 200,  "opened": 86,   "replied": 24,  "meetings": 4,  "open_rate": 43.0, "reply_rate": 12.0},
            ],
            "sequences": [
                {"name": "New Shipper Onboarding",        "steps": 5, "enrolled": 184, "avg_open_rate": 34.2, "avg_reply_rate": 7.1, "conversions": 18},
                {"name": "Cold → Warm Nurture (8-touch)", "steps": 8, "enrolled": 620, "avg_open_rate": 26.8, "avg_reply_rate": 4.2, "conversions": 31},
                {"name": "Re-engagement — 90-Day Ghosts", "steps": 4, "enrolled": 280, "avg_open_rate": 22.4, "avg_reply_rate": 3.1, "conversions": 9},
            ],
        },
    },

    "best_care_auto": {
        "overview": {
            "kpis": {
                "monthly_spend": 18400, "monthly_conversions": 22,
                "blended_roas": 3.9, "organic_sessions": 5240, "domain_authority": 36,
            },
            "channels": {
                "seo":          {"spend": 0,     "conversions": 8, "sessions": 5240},
                "google_ads":   {"spend": 12800, "conversions": 11, "roas": 3.4, "cpc": 7.80, "ctr": 4.1},
                "facebook_ads": {"spend": 5600,  "conversions": 3,  "roas": 2.1, "cpc": 9.20, "ctr": 1.8},
            },
            "trends": dict(zip(
                ["spend_by_channel", "conversions"],
                _mkt_trends(9800, 4200, 14, 1.05)
            )),
            "competitors": [
                {"name": "AutoShip Express",  "google_ads": {"status": "active", "ads_count": 6},  "facebook_ads": {"status": "active", "ads_count": 3}},
                {"name": "CarMove Direct",    "google_ads": {"status": "active", "ads_count": 9},  "facebook_ads": {"status": "active", "ads_count": 7}},
            ],
        },
        "seo": {
            "metrics": {
                "domain_authority": 36, "organic_sessions": 5240, "ranked_keywords": 218,
                "avg_position": "18.4", "core_web_vitals_score": 74, "backlinks": 920,
                "keyword_distribution": {"top_3": 6, "top_10": 28, "top_30": 64, "below_30": 120},
            },
            "trends": {"organic_sessions": _mkt_seo_trend(3800, 1.07)},
            "keywords": [
                {"keyword": "auto transport company",      "position": 8,  "volume": 3200, "difficulty": "High",   "intent": "Commercial"},
                {"keyword": "car shipping quotes",         "position": 14, "volume": 5800, "difficulty": "High",   "intent": "Transactional"},
                {"keyword": "enclosed auto transport",     "position": 5,  "volume": 1100, "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "vehicle transport midwest",   "position": 11, "volume": 890,  "difficulty": "Low",    "intent": "Commercial"},
                {"keyword": "door to door car shipping",   "position": 18, "volume": 2400, "difficulty": "Medium", "intent": "Transactional"},
            ],
            "technical": {
                "page_speed_mobile": "71/100", "page_speed_desktop": "86/100",
                "core_web_vitals_score": "74/100", "schema_markup": True,
                "mobile_friendly": True, "ssl_certificate": True,
                "xml_sitemap": True, "robots_txt": True,
            },
        },
        "google_ads": {
            "metrics": {
                "monthly_spend": 12800, "conversions": 11, "roas": 3.4,
                "avg_cpc": 7.80, "ctr": 4.1, "quality_score": "7.2 avg",
            },
            "campaigns": [
                {"name": "Auto Transport — Brand",       "status": "Active", "spend": 2800,  "conversions": 4, "cpa": 700,  "roas": 5.2},
                {"name": "Car Shipping Keywords",        "status": "Active", "spend": 5200,  "conversions": 4, "cpa": 1300, "roas": 2.9},
                {"name": "Enclosed Transport Specialty", "status": "Active", "spend": 2900,  "conversions": 2, "cpa": 1450, "roas": 3.1},
                {"name": "Competitor Conquest",          "status": "Active", "spend": 1900,  "conversions": 1, "cpa": 1900, "roas": 2.2},
            ],
            "trends": {
                "spend_conversions": [
                    {"month": m, "spend": round(8500 * (1.05 ** i)), "conversions": round(7 * (1.06 ** i))}
                    for i, m in enumerate(_MKT_SPEND_MONTHS)
                ]
            },
        },
        "facebook_ads": {
            "metrics": {
                "monthly_spend": 5600, "conversions": 3, "roas": 2.1,
                "avg_cpc": 9.20, "ctr": 1.8, "quality_score": "5.8 avg",
            },
            "campaigns": [
                {"name": "Auto Owners — Interest Targeting", "status": "Active", "spend": 3100, "leads": 48, "cpl": 65, "conversions": 2},
                {"name": "Lookalike — Past Customers",       "status": "Active", "spend": 2500, "leads": 32, "cpl": 78, "conversions": 1},
            ],
        },
        "knowledge_graph": {
            "entities": [
                {"name": "Best Care Auto Transport", "type": "Organization", "status": "Pending"},
                {"name": "Illinois",                  "type": "Location",     "status": "Linked"},
            ],
            "relationships": [
                {"from": "Best Care Auto Transport", "to": "Illinois", "type": "located_in"},
            ],
            "insights": [
                "Entity not yet verified — submit to Google Business Profile",
                "Brand search volume up 19% after Q3 campaign",
            ],
        },
        "recommendations": [
            {"id": 1, "status": "pending",     "category": "google_ads",  "title": "Expand 'car shipping quotes' bid strategy",      "description": "High-volume keyword at position 14 — switch to tROAS bid strategy. Estimated +8 conversions/mo.", "impact": "high", "effort": "low"},
            {"id": 2, "status": "pending",     "category": "seo",         "title": "Optimize Core Web Vitals (74 → 85+ target)",     "description": "LCP 3.8s on mobile — image compression + lazy load estimated to fix. DA increase expected +4 pts within 90 days.", "impact": "high", "effort": "medium"},
            {"id": 3, "status": "implemented", "category": "facebook_ads","title": "Paused low-CTR ad sets (< 0.8% CTR)",             "description": "Removed 3 underperforming ad sets — freed $800/mo budget. CPL improved $94 → $65.", "impact": "medium", "effort": "low"},
            {"id": 4, "status": "pending",     "category": "seo",         "title": "Build out auto transport service area pages",    "description": "Create state-specific pages for IL, IN, OH — 'car shipping [state]' keywords total 8,200 monthly searches with low competition.", "impact": "high", "effort": "medium"},
            {"id": 5, "status": "in_progress", "category": "google_ads",  "title": "Claim Google Business Profile + launch Local Services Ads", "description": "LSA verification in progress — expected -40% CPA vs. standard search for local searches once live.", "impact": "high", "effort": "low"},
        ],
        "competitors": [
            {"name": "AutoShip Express",  "google_ads": {"status": "active", "ads_count": 6, "keywords": 148}, "facebook_ads": {"status": "active", "ads_count": 3}},
            {"name": "CarMove Direct",    "google_ads": {"status": "active", "ads_count": 9, "keywords": 276}, "facebook_ads": {"status": "active", "ads_count": 7}},
        ],
        "implementation_history": [
            {"date": "2025-12-02", "action": "Paused 3 low-CTR Facebook ad sets", "result": "CPL improved $94 → $65, freed $800/mo budget"},
        ],
    },

    "ivan_amazon": {
        "overview": {
            "kpis": {
                "monthly_driver_goal": "120 routes/mo", "monthly_spend": 8100, "monthly_conversions": 18,
                "organic_sessions": 2140, "domain_authority": 24,
            },
            "channels": {
                "seo":          {"spend": 0,    "conversions": 6,  "sessions": 2140},
                "google_ads":   {"spend": 5400, "conversions": 9,  "roas": 3.1, "cpc": 8.40, "ctr": 2.9},
                "facebook_ads": {"spend": 2700, "conversions": 3,  "roas": 1.8, "cpc": 11.20,"ctr": 1.4},
            },
            "trends": dict(zip(
                ["spend_by_channel", "conversions"],
                _mkt_trends(4200, 2100, 12, 1.03)
            )),
            "competitors": [
                {"name": "DSP Connect",      "google_ads": {"status": "active", "ads_count": 4}, "facebook_ads": {"status": "inactive"}},
                {"name": "AmazonFleet Plus", "google_ads": {"status": "active", "ads_count": 7}, "facebook_ads": {"status": "active", "ads_count": 2}},
            ],
        },
        "seo": {
            "metrics": {
                "domain_authority": 24, "organic_sessions": 2140, "ranked_keywords": 98,
                "avg_position": "22.1", "core_web_vitals_score": 68, "backlinks": 340,
                "keyword_distribution": {"top_3": 3, "top_10": 14, "top_30": 31, "below_30": 50},
            },
            "trends": {"organic_sessions": _mkt_seo_trend(1400, 1.08)},
            "keywords": [
                {"keyword": "amazon dsp driver jobs chicago",   "position": 7,  "volume": 1800, "difficulty": "Medium", "intent": "Commercial"},
                {"keyword": "amazon flex driver requirements",   "position": 12, "volume": 3200, "difficulty": "High",   "intent": "Informational"},
                {"keyword": "logistics delivery partner midwest","position": 16, "volume": 640,  "difficulty": "Low",    "intent": "Commercial"},
            ],
            "technical": {
                "page_speed_mobile": "64/100", "page_speed_desktop": "79/100",
                "core_web_vitals_score": "68/100", "schema_markup": False,
                "mobile_friendly": True, "ssl_certificate": True,
                "xml_sitemap": True, "robots_txt": True,
            },
        },
        "google_ads": {
            "metrics": {
                "monthly_spend": 5400, "conversions": 9, "roas": 3.1,
                "avg_cpc": 8.40, "ctr": 2.9, "quality_score": "6.6 avg",
            },
            "campaigns": [
                {"name": "DSP Driver Recruitment",     "status": "Active", "spend": 3200, "conversions": 6, "cpa": 533, "roas": 3.8},
                {"name": "Amazon Partner — Brand",     "status": "Active", "spend": 2200, "conversions": 3, "cpa": 733, "roas": 2.2},
            ],
            "trends": {
                "spend_conversions": [
                    {"month": m, "spend": round(3800 * (1.03 ** i)), "conversions": round(6 * (1.04 ** i))}
                    for i, m in enumerate(_MKT_SPEND_MONTHS)
                ]
            },
        },
        "facebook_ads": {
            "metrics": {
                "monthly_spend": 2700, "conversions": 3, "roas": 1.8,
                "avg_cpc": 11.20, "ctr": 1.4, "quality_score": "5.2 avg",
            },
            "campaigns": [
                {"name": "Driver Prospects — Interest", "status": "Active", "spend": 2700, "leads": 41, "cpl": 66, "conversions": 3},
            ],
        },
        "knowledge_graph": {
            "entities": [
                {"name": "Ivan Cartage",  "type": "Organization", "status": "Pending"},
                {"name": "Amazon DSP",    "type": "Partner",      "status": "Linked"},
            ],
            "relationships": [
                {"from": "Ivan Cartage", "to": "Amazon DSP", "type": "partner_of"},
            ],
            "insights": [
                "Brand entity not yet claimed — claim Google Business Profile",
                "Amazon partner badge increases trust signals in SERP",
            ],
        },
        "recommendations": [
            {"id": 1, "status": "pending",     "category": "seo",          "title": "Add schema markup to homepage",              "description": "Missing structured data — add LocalBusiness + JobPosting schema for +12% CTR.", "impact": "medium", "effort": "low"},
            {"id": 2, "status": "pending",     "category": "google_ads",   "title": "Add location extensions to campaigns",       "description": "DSP drivers are hyper-local — location extensions expected +22% CTR.", "impact": "high", "effort": "low"},
            {"id": 3, "status": "pending",     "category": "seo",          "title": "Create 'Amazon DSP Driver Jobs Chicago' landing page", "description": "Dedicated landing page targeting high-volume 'amazon driver jobs chicago' (2,400 searches/mo) — currently not ranking.", "impact": "high", "effort": "medium"},
            {"id": 4, "status": "pending",     "category": "facebook_ads", "title": "Launch driver recruitment Facebook campaign",  "description": "Facebook interest targeting for delivery workers + lookalike from existing driver list — estimated CPL $48 vs. Indeed $72.", "impact": "high", "effort": "low"},
        ],
        "competitors": [
            {"name": "DSP Connect",      "google_ads": {"status": "active", "ads_count": 4, "keywords": 62},  "facebook_ads": {"status": "inactive"}},
            {"name": "AmazonFleet Plus", "google_ads": {"status": "active", "ads_count": 7, "keywords": 114}, "facebook_ads": {"status": "active", "ads_count": 2}},
        ],
        "implementation_history": [
            {"date": "2025-11-18", "action": "Added location extensions to DSP Driver Recruitment campaign", "result": "CTR improved 2.9% → 4.1%, CPA dropped $533 → $418"},
            {"date": "2025-10-30", "action": "Added schema markup (LocalBusiness + JobPosting) to homepage", "result": "CTR on brand queries improved 11%, rich results appearing on 3 key pages"},
        ],
    },
}

# Best Care real-data endpoints (mocked)
BEST_CARE_DASHBOARD = {
    "monthly_performance": [
        {"month": m, "spend": round(10000 * (1.05**i)), "total_calls": round(140*(1.04**i)),
         "answered_calls": round(112*(1.04**i)), "answer_rate": 80,
         "leads": round(18*(1.04**i)), "conversions": round(14*(1.04**i))}
        for i, m in enumerate(_MKT_SPEND_MONTHS)
    ],
    "data_quality": {"spend": "live", "calls": "live", "conversions": "live", "revenue": "estimated"},
}

# ── Sales Data ────────────────────────────────────────────────────────────────

import random as _rand
_rand.seed(42)

def _daily_sales(base_emails=120, base_open=41, base_reply=8, days=30):
    result = []
    d = date(2025, 12, 1)
    for i in range(days):
        sent  = base_emails + _rand.randint(-15, 20)
        openr = base_open  + _rand.uniform(-3, 4)
        repr_ = base_reply + _rand.uniform(-1, 1.5)
        result.append({
            "date": str(d + timedelta(days=i)),
            "emails_sent": sent,
            "open_rate":   round(openr, 1),
            "reply_rate":  round(max(1, repr_), 1),
        })
    return result

_BCAT_LEADS = [
    ("Marcus","Johnson","VP of Operations","Midwest Freight Partners","Chicago, IL","Qualified","87"),
    ("Sarah","Chen","Director of Logistics","Pacific Rim Transport","Los Angeles, CA","Contacted","72"),
    ("David","Martinez","VP Supply Chain","Heartland Distributors","Des Moines, IA","Meeting Booked","94"),
    ("Emily","Rodriguez","Logistics Manager","Great Lakes Shipping","Milwaukee, WI","Qualified","68"),
    ("James","Wilson","CEO","Wilson Transport LLC","Indianapolis, IN","Closing","91"),
    ("Priya","Patel","Director of Procurement","Atlas Freight","Columbus, OH","Contacted","61"),
    ("Robert","Thompson","VP Operations","Cardinal Logistics","Cincinnati, OH","Qualified","79"),
    ("Jennifer","Lee","Supply Chain Lead","Tri-State Carriers","Louisville, KY","Nurture","54"),
    ("Michael","Davis","COO","Davis & Sons Transport","St. Louis, MO","Meeting Booked","88"),
    ("Amanda","Brown","Logistics Coordinator","Brown Eagle Freight","Detroit, MI","Contacted","63"),
    ("Carlos","Gomez","Fleet Manager","Gomez Trucking","Kansas City, MO","Qualified","76"),
    ("Rachel","Kim","VP Sales","Northstar Logistics","Minneapolis, MN","Interested","82"),
    ("Thomas","Anderson","Director Ops","Anderson Freight","Pittsburgh, PA","Nurture","49"),
    ("Lisa","Taylor","Procurement Head","Taylor Supply Co","Nashville, TN","Contacted","71"),
    ("Kevin","White","COO","White Line Transport","Cleveland, OH","Meeting Booked","93"),
]

def _leads(data, workspace):
    return [{"first_name": r[0], "last_name": r[1], "title": r[2], "company": r[3],
             "location": r[4], "status": r[5], "score": int(r[6]),
             "email": f"{r[0].lower()}.{r[1].lower()}@{r[3].lower().replace(' ','')}.com",
             "touches": _rand.randint(1,8), "last_touch": f"2025-12-{_rand.randint(1,30):02d}"}
            for r in data]

SALES_DATA = {
    "bcat_sales": {
        "overview": {
            "kpis": {
                "emails_sent_mtd": 2847, "target_emails_per_day": 140,
                "open_rate": 42.3, "reply_rate": 8.4, "positive_reply_rate": 3.1,
                "meetings_booked_mtd": 47, "meetings_held_mtd": 38, "show_rate": 80.9,
                "opp_conversion": 23.7, "active_prospects": 1482, "leads_added_mtd": 316,
                "linkedin_sent_mtd": 847, "linkedin_reply_rate": 12.4, "pipeline_value": 2840000,
            },
        },
        "daily": {"days": _daily_sales(120, 42, 8.4)},
        "activity": {"activity": [
            {"description": "47 new leads added from Apollo — Logistics Decision Makers IL", "date": "2025-12-30", "type": "sync"},
            {"description": "Meeting booked: James Wilson, Wilson Transport LLC", "date": "2025-12-29", "type": "meeting"},
            {"description": "Reply received from Marcus Johnson — interested in Q1 capacity", "date": "2025-12-28", "type": "reply"},
            {"description": "Campaign 'Midwest Freight Outreach Dec' launched — 312 contacts", "date": "2025-12-27", "type": "campaign"},
            {"description": "Meeting held: David Martinez — moved to Closing stage", "date": "2025-12-26", "type": "meeting"},
            {"description": "LinkedIn connection accepted: Rachel Kim, Northstar Logistics", "date": "2025-12-26", "type": "linkedin"},
            {"description": "38 new leads added from Google Maps scrape — Chicago freight brokers", "date": "2025-12-24", "type": "sync"},
            {"description": "Meeting booked: Kevin White, White Line Transport", "date": "2025-12-23", "type": "meeting"},
        ]},
        "leads": {"source": "apollo", "leads": _leads(_BCAT_LEADS, "bcat_sales")},
        "lead_lists": {"source": "apollo", "lists": [
            {"name": "Midwest Logistics VPs",       "count": 487, "enrolled": 312, "source": "Apollo",    "persona": "VP Ops / Supply Chain Lead", "status": "Active"},
            {"name": "Chicago Freight Brokers",     "count": 284, "enrolled": 218, "source": "Maps Scrape","persona": "Owner / Operations Manager",  "status": "Active"},
            {"name": "IL-IN-OH Decision Makers",    "count": 391, "enrolled": 267, "source": "Apollo",    "persona": "Director+ Logistics",         "status": "Active"},
            {"name": "Great Lakes Fleet Managers",  "count": 162, "enrolled": 98,  "source": "LinkedIn",  "persona": "Fleet Manager / COO",         "status": "Paused"},
            {"name": "Q4 Warm Re-engage",           "count": 94,  "enrolled": 94,  "source": "CRM Export","persona": "Previous Demo / Trial",        "status": "Complete"},
        ]},
        "email_campaigns": {"campaigns": [
            {"name": "Midwest Freight Outreach Dec", "status": "Active", "contacts": 312, "sent": 1284, "opened": 542, "replied": 108, "meetings": 14, "open_rate": 42.2, "reply_rate": 8.4},
            {"name": "Chicago Brokers Nov",          "status": "Active", "contacts": 218, "sent": 872,  "opened": 375, "replied": 74,  "meetings": 9,  "open_rate": 43.0, "reply_rate": 8.5},
            {"name": "Decision Makers IL-IN-OH",     "status": "Active", "contacts": 267, "sent": 691,  "opened": 284, "replied": 58,  "meetings": 7,  "open_rate": 41.1, "reply_rate": 8.4},
        ]},
        "linkedin_campaigns": {"campaigns": [
            {"name": "VP Ops Midwest Connect", "connection_requests_sent": 284, "connections_accepted": 97, "acceptance_rate": 34.2, "messages_sent": 97, "replies": 38, "reply_rate": 39.2, "positive_replies": 12, "positive_rate": 12.4, "meetings_booked": 4, "sequence": ["Connect + note","Value msg D3","Case study D7","Ask D14"]},
        ]},
        "meetings": {"meetings": [
            {"prospect": "James Wilson",   "company": "Wilson Transport LLC",     "date": "2026-01-08", "time": "2:00 PM CST", "source": "email", "campaign": "Midwest Freight Dec",   "status": "upcoming", "cal_event_id": "evt_1"},
            {"prospect": "Kevin White",    "company": "White Line Transport",     "date": "2026-01-10", "time": "10:00 AM CST","source": "email", "campaign": "Midwest Freight Dec",   "status": "upcoming", "cal_event_id": "evt_2"},
            {"prospect": "Michael Davis",  "company": "Davis & Sons Transport",   "date": "2026-01-14", "time": "3:00 PM CST", "source": "linkedin","campaign": "VP Ops Connect",      "status": "upcoming"},
            {"prospect": "David Martinez", "company": "Heartland Distributors",   "date": "2025-12-18", "time": "11:00 AM CST","source": "email", "campaign": "Decision Makers",      "status": "held", "outcome": "Won", "cal_event_id": "evt_3"},
            {"prospect": "Marcus Johnson", "company": "Midwest Freight Partners", "date": "2025-12-12", "time": "2:30 PM CST", "source": "email", "campaign": "Chicago Brokers Nov",  "status": "held", "outcome": "Follow-up"},
        ]},
        "messaging_templates": {"styles": ["carnegie","challenger","consultative","hyper-personalized"], "saved_templates": [
            {"channel": "email", "goal": "Book intro call", "performance": {"open_rate": 44.1, "reply_rate": 9.2, "meetings": 18}},
            {"channel": "linkedin", "goal": "Connect + qualify", "performance": {"open_rate": None, "reply_rate": 38.4, "meetings": 4}},
        ]},
        "recommendations": {"recommendations": [
            {"id": 1, "title": "Launch re-engagement sequence for 94 warm Q4 leads", "priority": "high"},
            {"id": 2, "title": "Add 3 more LinkedIn sequences targeting CFOs in logistics", "priority": "high"},
            {"id": 3, "title": "A/B test subject line: question vs. stat — expected +2.1% open rate", "priority": "medium"},
            {"id": 4, "title": "Increase daily send volume from 140 → 160 (inbox warming complete)", "priority": "medium"},
        ]},
        "sync_status": {"instantly": {"last_sync_at": "2025-12-31T08:14:00Z"}},
    },

    "best_care_sales": {
        "overview": {
            "kpis": {
                "emails_sent_mtd": 1284, "target_emails_per_day": 65,
                "open_rate": 38.7, "reply_rate": 6.2, "positive_reply_rate": 2.4,
                "meetings_booked_mtd": 18, "meetings_held_mtd": 14, "show_rate": 77.8,
                "opp_conversion": 21.4, "active_prospects": 642, "leads_added_mtd": 148,
                "linkedin_sent_mtd": 312, "linkedin_reply_rate": 10.8, "pipeline_value": 940000,
            },
        },
        "daily": {"days": _daily_sales(55, 38, 6.2, 30)},
        "activity": {"activity": [
            {"description": "24 new leads added from Maps scrape — Auto Transport Companies IL", "date": "2025-12-30", "type": "sync"},
            {"description": "Meeting booked: Patricia Kim, Kim Auto Group", "date": "2025-12-29", "type": "meeting"},
            {"description": "Reply: Thomas Reed — requesting Q1 fleet transport quote", "date": "2025-12-28", "type": "reply"},
        ]},
        "leads": {"source": "apollo", "leads": [
            {"first_name": "Patricia", "last_name": "Kim",   "title": "Fleet Manager",    "company": "Kim Auto Group",      "location": "Chicago, IL",       "status": "Meeting Booked", "score": 89, "email": "p.kim@kimauto.com",    "touches": 4, "last_touch": "2025-12-29"},
            {"first_name": "Thomas",   "last_name": "Reed",  "title": "Operations Dir.",  "company": "Reed Motors",          "location": "Naperville, IL",    "status": "Qualified",      "score": 76, "email": "t.reed@reedmotors.com","touches": 3, "last_touch": "2025-12-28"},
            {"first_name": "Sandra",   "last_name": "Cruz",  "title": "Purchasing Mgr",   "company": "Cruz Dealerships",     "location": "Joliet, IL",        "status": "Contacted",      "score": 62, "email": "s.cruz@cruzdealer.com","touches": 2, "last_touch": "2025-12-26"},
            {"first_name": "Brian",    "last_name": "Foster","title": "Fleet Director",   "company": "Foster Fleet Mgmt",   "location": "Rockford, IL",      "status": "Qualified",      "score": 71, "email": "b.foster@fosterfleet.com","touches": 5, "last_touch": "2025-12-24"},
        ]},
        "lead_lists": {"source": "apollo", "lists": [
            {"name": "IL Auto Dealerships",    "count": 214, "enrolled": 148, "source": "Apollo",     "persona": "Fleet Manager / Purchasing", "status": "Active"},
            {"name": "Chicago Auction Houses", "count": 89,  "enrolled": 67,  "source": "Maps Scrape","persona": "Operations Manager",        "status": "Active"},
            {"name": "Midwest Car Collectors", "count": 124, "enrolled": 78,  "source": "LinkedIn",   "persona": "High-value individual",     "status": "Paused"},
        ]},
        "email_campaigns": {"campaigns": [
            {"name": "IL Auto Dealers Dec",      "status": "Active", "contacts": 148, "sent": 592, "opened": 229, "replied": 37, "meetings": 8, "open_rate": 38.7, "reply_rate": 6.3},
            {"name": "Auction Houses Nov",       "status": "Active", "contacts": 67,  "sent": 268, "opened": 101, "replied": 16, "meetings": 4, "open_rate": 37.7, "reply_rate": 6.0},
        ]},
        "linkedin_campaigns": {"campaigns": [
            {"name": "Fleet Manager Connect", "connection_requests_sent": 124, "connections_accepted": 38, "acceptance_rate": 30.6, "messages_sent": 38, "replies": 14, "reply_rate": 36.8, "positive_replies": 5, "positive_rate": 13.2, "meetings_booked": 2, "sequence": ["Connect","Value msg D3","Ask D10"]},
        ]},
        "meetings": {"meetings": [
            {"prospect": "Patricia Kim",  "company": "Kim Auto Group",   "date": "2026-01-09", "time": "1:00 PM CST", "source": "email",    "campaign": "IL Auto Dealers Dec", "status": "upcoming"},
            {"prospect": "Thomas Reed",   "company": "Reed Motors",      "date": "2026-01-13", "time": "10:30 AM CST","source": "email",    "campaign": "IL Auto Dealers Dec", "status": "upcoming"},
        ]},
        "messaging_templates": {"styles": ["carnegie","challenger","consultative"], "saved_templates": [
            {"channel": "email", "goal": "Book transport quote call", "performance": {"open_rate": 39.4, "reply_rate": 6.8, "meetings": 9}},
        ]},
        "recommendations": {"recommendations": [
            {"id": 1, "title": "Target independent used car dealers — high fleet transport need", "priority": "high"},
            {"id": 2, "title": "Add follow-up sequence at Day 5 — currently stopping at Day 3", "priority": "medium"},
        ]},
        "sync_status": {"instantly": {"last_sync_at": "2025-12-31T07:52:00Z"}},
    },

    "bcat_recruitment": {
        "overview": {
            "kpis": {
                "emails_sent_mtd": 982, "target_emails_per_day": 50,
                "open_rate": 35.4, "reply_rate": 5.8, "positive_reply_rate": 2.1,
                "meetings_booked_mtd": 12, "meetings_held_mtd": 9, "show_rate": 75.0,
                "opp_conversion": 33.3, "active_prospects": 318, "leads_added_mtd": 87,
                "linkedin_sent_mtd": 214, "linkedin_reply_rate": 9.4, "pipeline_value": 0,
            },
        },
        "daily": {"days": _daily_sales(42, 35, 5.8, 30)},
        "activity": {"activity": [
            {"description": "12 carrier profiles added from FMCSA database", "date": "2025-12-30", "type": "sync"},
            {"description": "Carrier onboarding call: Rodriguez Trucking LLC", "date": "2025-12-28", "type": "meeting"},
        ]},
        "leads": {"source": "fmcsa", "leads": [
            {"first_name": "Dale",    "last_name": "Hutchins",  "title": "Owner-Operator",  "company": "Hutchins Hauling LLC",      "location": "Peoria, IL",       "status": "Meeting Booked", "score": 88, "email": "dale.hutchins@hutchinshauling.com",    "touches": 5, "last_touch": "2025-12-29"},
            {"first_name": "Tony",    "last_name": "Vasquez",   "title": "Fleet Owner",     "company": "Vasquez Freight Inc",       "location": "Joliet, IL",       "status": "Qualified",      "score": 81, "email": "tony.vasquez@vasquezfreight.com",       "touches": 4, "last_touch": "2025-12-28"},
            {"first_name": "Greg",    "last_name": "Novak",     "title": "Owner-Operator",  "company": "Novak Transport LLC",       "location": "Rockford, IL",     "status": "Contacted",      "score": 67, "email": "greg.novak@novaktransport.com",         "touches": 2, "last_touch": "2025-12-26"},
            {"first_name": "Sheila",  "last_name": "Park",      "title": "Fleet Manager",   "company": "Park Brothers Carriers",    "location": "Elgin, IL",        "status": "Qualified",      "score": 74, "email": "sheila.park@parkbrothers.com",          "touches": 3, "last_touch": "2025-12-24"},
            {"first_name": "Marcus",  "last_name": "Tran",      "title": "Owner-Operator",  "company": "Tran Logistics LLC",        "location": "Aurora, IL",       "status": "Interested",     "score": 79, "email": "marcus.tran@tranlogistics.com",         "touches": 4, "last_touch": "2025-12-23"},
            {"first_name": "Donna",   "last_name": "Reeves",    "title": "Operations Mgr",  "company": "Reeves & Sons Transport",   "location": "Springfield, IL",  "status": "Nurture",        "score": 55, "email": "donna.reeves@reevessons.com",           "touches": 2, "last_touch": "2025-12-20"},
            {"first_name": "Hector",  "last_name": "Morales",   "title": "Fleet Owner",     "company": "Morales Freight Co",        "location": "Waukegan, IL",     "status": "Meeting Booked", "score": 92, "email": "hector.morales@moralesfreight.com",     "touches": 6, "last_touch": "2025-12-28"},
            {"first_name": "Keith",   "last_name": "Simmons",   "title": "Owner-Operator",  "company": "Simmons Carrier Services",  "location": "Champaign, IL",    "status": "Contacted",      "score": 61, "email": "keith.simmons@simmonscarrier.com",      "touches": 2, "last_touch": "2025-12-22"},
            {"first_name": "Brenda",  "last_name": "Okafor",    "title": "Fleet Director",  "company": "Okafor Trucking LLC",       "location": "Gary, IN",         "status": "Qualified",      "score": 77, "email": "brenda.okafor@okafortrucking.com",      "touches": 3, "last_touch": "2025-12-27"},
            {"first_name": "Travis",  "last_name": "Lundqvist", "title": "Owner-Operator",  "company": "Lundqvist Freight LLC",     "location": "Kankakee, IL",     "status": "Nurture",        "score": 48, "email": "travis.lundqvist@lundqvistfreight.com", "touches": 1, "last_touch": "2025-12-15"},
        ]},
        "lead_lists": {"source": "fmcsa", "lists": [
            {"name": "Midwest Owner Operators",     "count": 214, "enrolled": 148, "source": "FMCSA",   "persona": "Owner-Operator MC# holder", "status": "Active"},
            {"name": "Small Fleet Carriers 5–20",   "count": 104, "enrolled": 87,  "source": "Apollo",  "persona": "Fleet owner, midwest",       "status": "Active"},
            {"name": "Reefer Specialist Carriers",  "count": 68,  "enrolled": 42,  "source": "FMCSA",   "persona": "Reefer-certified owner-op",  "status": "Active"},
            {"name": "IL-IN Flatbed Operators",     "count": 89,  "enrolled": 61,  "source": "FMCSA",   "persona": "Flatbed owner 2–10 trucks",  "status": "Active"},
            {"name": "Q4 Warm Carriers Re-engage",  "count": 34,  "enrolled": 34,  "source": "CRM",     "persona": "Previously contacted, warm", "status": "Complete"},
        ]},
        "email_campaigns": {"campaigns": [
            {"name": "Owner-Op Recruitment Dec",   "status": "Active",    "contacts": 148, "sent": 592, "opened": 209, "replied": 34, "meetings": 7, "open_rate": 35.3, "reply_rate": 5.7},
            {"name": "Reefer Specialist Outreach", "status": "Active",    "contacts": 42,  "sent": 126, "opened": 44,  "replied": 7,  "meetings": 2, "open_rate": 34.9, "reply_rate": 5.6},
            {"name": "Small Fleet Nov Re-engage",  "status": "Complete",  "contacts": 87,  "sent": 261, "opened": 89,  "replied": 14, "meetings": 3, "open_rate": 34.1, "reply_rate": 5.4},
        ]},
        "linkedin_campaigns": {"campaigns": [
            {"name": "Midwest Owner-Op Connect", "connection_requests_sent": 148, "connections_accepted": 42, "acceptance_rate": 28.4, "messages_sent": 42, "replies": 14, "reply_rate": 33.3, "positive_replies": 6, "positive_rate": 14.3, "meetings_booked": 3, "sequence": ["Connect + note", "Value msg D3", "Ask D10"]},
            {"name": "Reefer Carrier Specialty",  "connection_requests_sent": 68,  "connections_accepted": 21, "acceptance_rate": 30.9, "messages_sent": 21, "replies": 8,  "reply_rate": 38.1, "positive_replies": 4, "positive_rate": 19.0, "meetings_booked": 2, "sequence": ["Connect", "Lane offer D4", "Onboarding ask D9"]},
        ]},
        "meetings": {"meetings": [
            {"prospect": "Hector Morales", "company": "Morales Freight Co",      "date": "2026-01-07", "time": "11:00 AM CST", "source": "email",    "campaign": "Owner-Op Recruitment Dec",  "status": "upcoming"},
            {"prospect": "Dale Hutchins",  "company": "Hutchins Hauling LLC",    "date": "2026-01-09", "time": "2:00 PM CST",  "source": "email",    "campaign": "Owner-Op Recruitment Dec",  "status": "upcoming"},
            {"prospect": "Tony Vasquez",   "company": "Vasquez Freight Inc",     "date": "2025-12-19", "time": "10:00 AM CST", "source": "linkedin", "campaign": "Midwest Owner-Op Connect",  "status": "held", "outcome": "Onboarded"},
            {"prospect": "Greg Novak",     "company": "Novak Transport LLC",     "date": "2025-12-11", "time": "3:00 PM CST",  "source": "email",    "campaign": "Small Fleet Nov Re-engage", "status": "held", "outcome": "Follow-up"},
        ]},
        "messaging_templates": {"styles": ["carnegie", "consultative"], "saved_templates": [
            {"channel": "email",    "goal": "Recruit owner-op for high-volume midwest lanes", "performance": {"open_rate": 35.8, "reply_rate": 6.1, "meetings": 8}},
            {"channel": "linkedin", "goal": "Connect + qualify for reefer capacity",          "performance": {"open_rate": None, "reply_rate": 34.2, "meetings": 3}},
        ]},
        "recommendations": {"recommendations": [
            {"id": 1, "title": "Target reefer carriers — highest margin freight currently undersourced", "priority": "high"},
            {"id": 2, "title": "Add flatbed specialist sequence — 8 open lanes in IL/IN with no coverage", "priority": "high"},
            {"id": 3, "title": "Re-engage Q4 warm carrier list before rate season kicks in (Jan 15)", "priority": "medium"},
        ]},
        "sync_status": {"instantly": {"last_sync_at": "2025-12-31T07:40:00Z"}},
    },

    "ivan_dsp_recruitment": {
        "overview": {
            "kpis": {
                "emails_sent_mtd": 1240, "target_emails_per_day": 62,
                "open_rate": 28.4, "reply_rate": 4.8, "positive_reply_rate": 2.1,
                "meetings_booked_mtd": 28, "meetings_held_mtd": 21, "show_rate": 75.0,
                "opp_conversion": 38.1, "active_prospects": 186, "leads_added_mtd": 312,
                "linkedin_sent_mtd": 0, "linkedin_reply_rate": 0, "pipeline_value": 0,
            },
        },
        "daily": {"days": _daily_sales(60, 28, 4.8, 30)},
        "activity": {"activity": [
            {"description": "32 driver leads added from Indeed scrape — Chicago DSP drivers", "date": "2025-12-30", "type": "sync"},
            {"description": "Orientation session scheduled: Marcus Webb — Jan 8 @ 9am", "date": "2025-12-29", "type": "meeting"},
            {"description": "Reply from Darnell Cooper — interested in FT DSP route, available Jan 6", "date": "2025-12-28", "type": "reply"},
            {"description": "Orientation completed: Keisha Thompson — Started Jan 2 (Aurora route)", "date": "2025-12-27", "type": "meeting"},
            {"description": "Campaign 'Chicago DSP Drivers Dec' launched — 284 contacts", "date": "2025-12-26", "type": "campaign"},
            {"description": "18 Amazon Flex alumni added from internal referral list", "date": "2025-12-24", "type": "sync"},
            {"description": "Orientation completed: Tony Ruiz — No-show, rescheduling", "date": "2025-12-23", "type": "meeting"},
            {"description": "Reply from Sandra Okonkwo — asking about benefits and pay schedule", "date": "2025-12-22", "type": "reply"},
            {"description": "Jerome Banks background check cleared — orientation confirmed", "date": "2025-12-21", "type": "sync"},
        ]},
        "leads": {"source": "indeed", "leads": [
            {"first_name": "Marcus",  "last_name": "Webb",      "title": "Delivery Driver",       "company": "FedEx Ground",        "location": "Chicago, IL",       "status": "Meeting Booked", "score": 91, "email": "marcus.webb@gmail.com",        "touches": 3, "last_touch": "2025-12-29"},
            {"first_name": "Darnell", "last_name": "Cooper",    "title": "Amazon Flex Driver",     "company": "Self-employed",       "location": "Joliet, IL",        "status": "Qualified",      "score": 84, "email": "darnell.cooper@gmail.com",     "touches": 4, "last_touch": "2025-12-28"},
            {"first_name": "Keisha",  "last_name": "Thompson",  "title": "Delivery Associate",     "company": "UPS Supply Chain",    "location": "Aurora, IL",        "status": "Qualified",      "score": 78, "email": "keisha.thompson@gmail.com",    "touches": 2, "last_touch": "2025-12-27"},
            {"first_name": "Tony",    "last_name": "Ruiz",      "title": "CDL-A Driver",           "company": "US Foods",            "location": "Cicero, IL",        "status": "Nurture",        "score": 62, "email": "tony.ruiz@gmail.com",          "touches": 3, "last_touch": "2025-12-23"},
            {"first_name": "Sandra",  "last_name": "Okonkwo",   "title": "Delivery Driver",        "company": "DoorDash",            "location": "Harvey, IL",        "status": "Contacted",      "score": 69, "email": "sandra.okonkwo@gmail.com",     "touches": 2, "last_touch": "2025-12-22"},
            {"first_name": "Luis",    "last_name": "Pena",      "title": "Route Driver",           "company": "PepsiCo",             "location": "Blue Island, IL",   "status": "Meeting Booked", "score": 88, "email": "luis.pena@gmail.com",          "touches": 4, "last_touch": "2025-12-29"},
            {"first_name": "Angela",  "last_name": "Morris",    "title": "Amazon Flex Driver",     "company": "Self-employed",       "location": "Evanston, IL",      "status": "Interested",     "score": 76, "email": "angela.morris@gmail.com",      "touches": 2, "last_touch": "2025-12-26"},
            {"first_name": "Derrick", "last_name": "Hayes",     "title": "Delivery Driver",        "company": "Walmart Spark",       "location": "Calumet City, IL",  "status": "Contacted",      "score": 58, "email": "derrick.hayes@gmail.com",      "touches": 1, "last_touch": "2025-12-20"},
            {"first_name": "Carmen",  "last_name": "Diaz",      "title": "Driver / Courier",       "company": "Instacart",           "location": "Berwyn, IL",        "status": "Qualified",      "score": 72, "email": "carmen.diaz@gmail.com",        "touches": 3, "last_touch": "2025-12-25"},
            {"first_name": "Jerome",  "last_name": "Banks",     "title": "Amazon DSP Driver",      "company": "Speedy Deliveries LLC","location": "Lansing, IL",      "status": "Closing",        "score": 94, "email": "jerome.banks@gmail.com",       "touches": 5, "last_touch": "2025-12-28"},
            {"first_name": "Mia",     "last_name": "Fontaine",  "title": "Delivery Associate",     "company": "Shipt",               "location": "Oak Park, IL",      "status": "Nurture",        "score": 50, "email": "mia.fontaine@gmail.com",       "touches": 1, "last_touch": "2025-12-18"},
            {"first_name": "Kevin",   "last_name": "Osei",      "title": "Van Driver",             "company": "LaserShip",           "location": "Maywood, IL",       "status": "Qualified",      "score": 81, "email": "kevin.osei@gmail.com",         "touches": 3, "last_touch": "2025-12-27"},
        ]},
        "lead_lists": {"source": "indeed", "lists": [
            {"name": "Chicago Area DSP Drivers",  "count": 284, "enrolled": 198, "source": "Indeed",   "persona": "Delivery driver, 1+ yr exp",         "status": "Active"},
            {"name": "Milwaukee Route Drivers",   "count": 162, "enrolled": 112, "source": "Indeed",   "persona": "Driver, Milwaukee metro area",        "status": "Active"},
            {"name": "Amazon Flex Alumni",        "count": 78,  "enrolled": 78,  "source": "Internal", "persona": "Active Flex seeking consistent FT",  "status": "Active"},
            {"name": "Former UPS/FedEx Drivers",  "count": 124, "enrolled": 84,  "source": "LinkedIn", "persona": "Experienced route driver, 2+ yrs",   "status": "Active"},
            {"name": "Indy/Detroit Driver Pool",  "count": 96,  "enrolled": 62,  "source": "Indeed",   "persona": "Driver, willing to commute",          "status": "Paused"},
            {"name": "Q4 No-Show Re-engage",      "count": 28,  "enrolled": 28,  "source": "CRM",      "persona": "Previous no-show, rescheduled",       "status": "Active"},
        ]},
        "email_campaigns": {"campaigns": [
            {"name": "Chicago DSP Driver Recruitment Dec", "status": "Active",   "contacts": 198, "sent": 792, "opened": 225, "replied": 38, "meetings": 9, "open_rate": 28.4, "reply_rate": 4.8},
            {"name": "Milwaukee Route Driver Outreach",   "status": "Active",   "contacts": 112, "sent": 448, "opened": 127, "replied": 21, "meetings": 6, "open_rate": 28.3, "reply_rate": 4.7},
            {"name": "Amazon Flex Upsell Dec",            "status": "Active",   "contacts": 78,  "sent": 234, "opened": 74,  "replied": 14, "meetings": 5, "open_rate": 31.6, "reply_rate": 6.0},
            {"name": "Former Route Driver Re-engage Nov", "status": "Complete", "contacts": 84,  "sent": 168, "opened": 44,  "replied": 7,  "meetings": 2, "open_rate": 26.2, "reply_rate": 4.2},
        ]},
        "linkedin_campaigns": {"campaigns": []},
        "meetings": {"meetings": [
            {"prospect": "Marcus Webb",     "company": "FedEx Ground",        "date": "2026-01-08", "time": "9:00 AM CST",  "source": "email", "campaign": "Chicago DSP Driver Recruitment Dec", "status": "upcoming"},
            {"prospect": "Luis Pena",       "company": "PepsiCo",             "date": "2026-01-10", "time": "10:30 AM CST", "source": "email", "campaign": "Chicago DSP Driver Recruitment Dec", "status": "upcoming"},
            {"prospect": "Jerome Banks",    "company": "Speedy Deliveries LLC","date": "2026-01-07", "time": "11:00 AM CST", "source": "email", "campaign": "Milwaukee Route Driver Outreach",    "status": "upcoming"},
            {"prospect": "Darnell Cooper",  "company": "Self-employed",        "date": "2026-01-09", "time": "9:30 AM CST",  "source": "email", "campaign": "Amazon Flex Upsell Dec",             "status": "upcoming"},
            {"prospect": "Keisha Thompson", "company": "UPS Supply Chain",     "date": "2025-12-19", "time": "9:00 AM CST",  "source": "email", "campaign": "Chicago DSP Driver Recruitment Dec", "status": "held", "outcome": "Won"},
            {"prospect": "Tony Ruiz",       "company": "US Foods",             "date": "2025-12-16", "time": "9:30 AM CST",  "source": "email", "campaign": "Former Route Driver Re-engage Nov",  "status": "held", "outcome": "No-show"},
            {"prospect": "Angela Morris",   "company": "Self-employed",        "date": "2025-12-12", "time": "10:00 AM CST", "source": "email", "campaign": "Amazon Flex Upsell Dec",             "status": "held", "outcome": "Follow-up"},
        ]},
        "messaging_templates": {"styles": ["carnegie", "consultative"], "saved_templates": [
            {"channel": "email", "goal": "Driver recruitment — high-income Amazon DSP route", "performance": {"open_rate": 31.2, "reply_rate": 5.4, "meetings": 12}},
            {"channel": "email", "goal": "Amazon Flex upsell — consistent FT routes vs. gig", "performance": {"open_rate": 32.1, "reply_rate": 6.0, "meetings": 6}},
        ]},
        "recommendations": {"recommendations": [
            {"id": 1, "title": "Add referral bonus to outreach — drivers recruit drivers most effectively", "priority": "high"},
            {"id": 2, "title": "Post on CDL job boards (TruckersReport, Trucker Path) — lower CPL than Indeed", "priority": "high"},
            {"id": 3, "title": "Add SMS follow-up for no-shows — reduces rescheduling lag by 60%", "priority": "medium"},
            {"id": 4, "title": "Target Amazon Flex drivers directly — already vetted, 40% faster onboarding", "priority": "medium"},
        ]},
        "sync_status": {"instantly": {"last_sync_at": "2025-12-31T07:30:00Z"}},
    },
}

# ── BCAT Operations Data ─────────────────────────────────────────────────────

BCAT_OPERATIONS = {
    "kpis": {
        "fuel_spend_mtd":     41200,
        "insurance_monthly":  18400,
        "driver_payroll_mtd": 98600,
        "maintenance_mtd":    12800,
        "active_trucks":      22,
        "on_route":           14,
        "in_maintenance":     3,
        "avg_miles_per_truck": 8420,
        "cost_per_mile":      2.14,
        "revenue_per_mile":   3.28,
        "profit_per_mile":    1.14,
        "utilization_rate":   87.3,
    },
    "monthly_trends": [
        {"month": "2025-01", "fuel": 32800, "maintenance": 9400,  "insurance": 17200, "driver_wages": 82400, "revenue": 198000, "miles": 58000},
        {"month": "2025-02", "fuel": 34100, "maintenance": 9800,  "insurance": 17200, "driver_wages": 84800, "revenue": 207000, "miles": 61000},
        {"month": "2025-03", "fuel": 36200, "maintenance": 10400, "insurance": 17800, "driver_wages": 88600, "revenue": 224000, "miles": 66000},
        {"month": "2025-04", "fuel": 37400, "maintenance": 10800, "insurance": 17800, "driver_wages": 91200, "revenue": 236000, "miles": 69000},
        {"month": "2025-05", "fuel": 38900, "maintenance": 11200, "insurance": 18000, "driver_wages": 94800, "revenue": 248000, "miles": 73000},
        {"month": "2025-06", "fuel": 38100, "maintenance": 10900, "insurance": 18000, "driver_wages": 93400, "revenue": 242000, "miles": 71000},
        {"month": "2025-07", "fuel": 37200, "maintenance": 10600, "insurance": 18200, "driver_wages": 91400, "revenue": 234000, "miles": 69000},
        {"month": "2025-08", "fuel": 40200, "maintenance": 11800, "insurance": 18200, "driver_wages": 98200, "revenue": 259000, "miles": 76000},
        {"month": "2025-09", "fuel": 37800, "maintenance": 10800, "insurance": 18400, "driver_wages": 93200, "revenue": 238000, "miles": 70000},
        {"month": "2025-10", "fuel": 40600, "maintenance": 12100, "insurance": 18400, "driver_wages": 99400, "revenue": 262000, "miles": 77000},
        {"month": "2025-11", "fuel": 38600, "maintenance": 11400, "insurance": 18400, "driver_wages": 95800, "revenue": 245000, "miles": 72000},
        {"month": "2025-12", "fuel": 41200, "maintenance": 12800, "insurance": 18400, "driver_wages": 98600, "revenue": 220000, "miles": 80000},
    ],
    "cost_breakdown": [
        {"category": "Driver Wages",   "amount": 1101400, "pct": 41.2},
        {"category": "Fuel",           "amount":  453100, "pct": 16.9},
        {"category": "Insurance",      "amount":  219600, "pct":  8.2},
        {"category": "Maintenance",    "amount":  131200, "pct":  4.9},
        {"category": "Depreciation",   "amount":  268000, "pct": 10.0},
        {"category": "Tolls",          "amount":  134000, "pct":  5.0},
        {"category": "Admin & Other",  "amount":  107100, "pct":  4.0},
        {"category": "Lease / Rent",   "amount":  267800, "pct":  9.8},
    ],
    "fleet": [
        {"truck_id": "T-101", "driver": "James Kowalski",   "status": "On Route",     "miles_ytd": 94200, "last_pm": "2025-11-14", "next_pm_due": "2026-02-14", "pm_status": "OK"},
        {"truck_id": "T-102", "driver": "Marcus Webb",      "status": "On Route",     "miles_ytd": 88600, "last_pm": "2025-10-28", "next_pm_due": "2026-01-28", "pm_status": "Due Soon"},
        {"truck_id": "T-103", "driver": "Luis Pena",        "status": "In Maintenance","miles_ytd": 76400, "last_pm": "2025-09-30", "next_pm_due": "2025-12-30", "pm_status": "Overdue"},
        {"truck_id": "T-104", "driver": "Darnell Hayes",    "status": "On Route",     "miles_ytd": 91800, "last_pm": "2025-11-20", "next_pm_due": "2026-02-20", "pm_status": "OK"},
        {"truck_id": "T-105", "driver": "Sandra Reyes",     "status": "On Route",     "miles_ytd": 83200, "last_pm": "2025-12-01", "next_pm_due": "2026-03-01", "pm_status": "OK"},
        {"truck_id": "T-106", "driver": "Jerome Williams",  "status": "Yard",         "miles_ytd": 71400, "last_pm": "2025-11-08", "next_pm_due": "2026-02-08", "pm_status": "OK"},
        {"truck_id": "T-107", "driver": "Angela Torres",    "status": "On Route",     "miles_ytd": 98100, "last_pm": "2025-10-15", "next_pm_due": "2026-01-15", "pm_status": "Due Soon"},
        {"truck_id": "T-108", "driver": "Kevin Osei",       "status": "On Route",     "miles_ytd": 86400, "last_pm": "2025-11-28", "next_pm_due": "2026-02-28", "pm_status": "OK"},
        {"truck_id": "T-109", "driver": "Carmen Diaz",      "status": "In Maintenance","miles_ytd": 64200, "last_pm": "2025-08-20", "next_pm_due": "2025-11-20", "pm_status": "Overdue"},
        {"truck_id": "T-110", "driver": "Tony Ruiz",        "status": "On Route",     "miles_ytd": 79800, "last_pm": "2025-12-05", "next_pm_due": "2026-03-05", "pm_status": "OK"},
        {"truck_id": "T-111", "driver": "Mia Fontaine",     "status": "On Route",     "miles_ytd": 72600, "last_pm": "2025-11-18", "next_pm_due": "2026-02-18", "pm_status": "OK"},
        {"truck_id": "T-112", "driver": "Derek Banks",      "status": "On Route",     "miles_ytd": 88000, "last_pm": "2025-10-22", "next_pm_due": "2026-01-22", "pm_status": "Due Soon"},
        {"truck_id": "T-113", "driver": "Patricia Kim",     "status": "Yard",         "miles_ytd": 66800, "last_pm": "2025-12-10", "next_pm_due": "2026-03-10", "pm_status": "OK"},
        {"truck_id": "T-114", "driver": "Curtis Brown",     "status": "On Route",     "miles_ytd": 91200, "last_pm": "2025-11-04", "next_pm_due": "2026-02-04", "pm_status": "OK"},
        {"truck_id": "T-115", "driver": "Renee Taylor",     "status": "In Maintenance","miles_ytd": 58400, "last_pm": "2025-09-15", "next_pm_due": "2025-12-15", "pm_status": "Overdue"},
    ],
    "maintenance_log": [
        {"date": "2025-12-28", "truck_id": "T-103", "type": "Brake replacement",       "vendor": "Midwest Truck Service",  "cost": 2840, "status": "In Progress"},
        {"date": "2025-12-26", "truck_id": "T-109", "type": "Engine diagnostic + repair","vendor": "Fleet Pro Chicago",     "cost": 4120, "status": "In Progress"},
        {"date": "2025-12-22", "truck_id": "T-107", "type": "PM service (oil/filter)",  "vendor": "QuickLane Fleet",       "cost":  480, "status": "Completed"},
        {"date": "2025-12-19", "truck_id": "T-112", "type": "Tire replacement (4x)",   "vendor": "Goodyear Commercial",   "cost": 1860, "status": "Completed"},
        {"date": "2025-12-15", "truck_id": "T-115", "type": "Transmission service",    "vendor": "Midwest Truck Service", "cost": 3200, "status": "Scheduled"},
        {"date": "2025-12-14", "truck_id": "T-104", "type": "PM service (oil/filter)",  "vendor": "QuickLane Fleet",       "cost":  480, "status": "Completed"},
        {"date": "2025-12-10", "truck_id": "T-108", "type": "ELD replacement",          "vendor": "Samsara Telematics",    "cost":  640, "status": "Completed"},
        {"date": "2025-12-06", "truck_id": "T-102", "type": "PM service — due Jan 28",  "vendor": "QuickLane Fleet",       "cost":  480, "status": "Scheduled"},
        {"date": "2025-12-02", "truck_id": "T-106", "type": "DOT inspection prep",      "vendor": "Fleet Pro Chicago",     "cost":  320, "status": "Completed"},
        {"date": "2025-11-28", "truck_id": "T-101", "type": "PM service (oil/filter)",  "vendor": "QuickLane Fleet",       "cost":  480, "status": "Completed"},
        {"date": "2025-11-20", "truck_id": "T-110", "type": "Cooling system flush",     "vendor": "Midwest Truck Service", "cost":  920, "status": "Completed"},
        {"date": "2025-11-14", "truck_id": "T-111", "type": "Air filter + belt replace","vendor": "QuickLane Fleet",       "cost":  560, "status": "Completed"},
    ],
    "alerts": [
        {"level": "Critical", "message": "T-103 brake job in progress — truck unavailable, load reassigned to T-106", "date": "2025-12-28"},
        {"level": "Critical", "message": "T-109 engine failure — EST repair 5–7 days, driver reassigned to T-113 standby", "date": "2025-12-26"},
        {"level": "Warning",  "message": "T-115 transmission service overdue by 12 days — schedule immediately",          "date": "2025-12-28"},
        {"level": "Warning",  "message": "T-102 PM due Jan 28 — book QuickLane before Jan 20 to avoid route disruption", "date": "2025-12-27"},
        {"level": "Warning",  "message": "T-107 PM due Jan 15 — mileage approaching threshold (98,100 mi)",              "date": "2025-12-25"},
        {"level": "Info",     "message": "T-112 PM service scheduled for Jan 22 — QuickLane confirmed",                   "date": "2025-12-26"},
    ],
}

# ── BCAT Compliance Data ──────────────────────────────────────────────────────

BCAT_COMPLIANCE = {
    "driver_kpis": {
        "total_drivers": 18, "active": 15, "compliant": 12,
        "expiring_soon": 4,  "non_compliant": 2,
        "avg_violations_ytd": 0.4, "mvr_reviews_due": 3,
    },
    "drivers": [
        {"name": "James Kowalski",  "cdl_class": "A", "cdl_expiry": "2027-03-14", "medical_expiry": "2026-08-10", "drug_test": "2025-06-12", "violations": 0, "status": "Compliant"},
        {"name": "Marcus Webb",     "cdl_class": "A", "cdl_expiry": "2026-09-22", "medical_expiry": "2025-12-18", "drug_test": "2025-05-08", "violations": 0, "status": "Expiring Soon"},
        {"name": "Luis Pena",       "cdl_class": "A", "cdl_expiry": "2027-01-30", "medical_expiry": "2026-06-04", "drug_test": "2025-09-14", "violations": 1, "status": "Compliant"},
        {"name": "Darnell Hayes",   "cdl_class": "A", "cdl_expiry": "2026-11-08", "medical_expiry": "2026-11-08", "drug_test": "2025-03-20", "violations": 0, "status": "Compliant"},
        {"name": "Sandra Reyes",    "cdl_class": "A", "cdl_expiry": "2028-04-02", "medical_expiry": "2026-09-22", "drug_test": "2025-08-31", "violations": 0, "status": "Compliant"},
        {"name": "Jerome Williams", "cdl_class": "B", "cdl_expiry": "2026-07-15", "medical_expiry": "2025-11-30", "drug_test": "2025-04-17", "violations": 2, "status": "Non-Compliant"},
        {"name": "Angela Torres",   "cdl_class": "A", "cdl_expiry": "2027-08-20", "medical_expiry": "2026-02-14", "drug_test": "2025-12-01", "violations": 0, "status": "Expiring Soon"},
        {"name": "Kevin Osei",      "cdl_class": "A", "cdl_expiry": "2027-05-11", "medical_expiry": "2026-05-11", "drug_test": "2025-07-22", "violations": 0, "status": "Compliant"},
        {"name": "Carmen Diaz",     "cdl_class": "A", "cdl_expiry": "2026-02-28", "medical_expiry": "2026-01-05", "drug_test": "2025-10-08", "violations": 1, "status": "Expiring Soon"},
        {"name": "Tony Ruiz",       "cdl_class": "A", "cdl_expiry": "2027-10-04", "medical_expiry": "2026-10-04", "drug_test": "2025-11-19", "violations": 0, "status": "Compliant"},
        {"name": "Mia Fontaine",    "cdl_class": "A", "cdl_expiry": "2028-01-18", "medical_expiry": "2026-07-18", "drug_test": "2025-06-30", "violations": 0, "status": "Compliant"},
        {"name": "Derek Banks",     "cdl_class": "A", "cdl_expiry": "2026-06-12", "medical_expiry": "2025-12-28", "drug_test": "2025-02-14", "violations": 3, "status": "Non-Compliant"},
        {"name": "Patricia Kim",    "cdl_class": "A", "cdl_expiry": "2027-12-08", "medical_expiry": "2026-12-08", "drug_test": "2025-09-05", "violations": 0, "status": "Compliant"},
        {"name": "Curtis Brown",    "cdl_class": "A", "cdl_expiry": "2026-04-22", "medical_expiry": "2026-04-22", "drug_test": "2025-08-12", "violations": 1, "status": "Expiring Soon"},
        {"name": "Renee Taylor",    "cdl_class": "A", "cdl_expiry": "2027-02-16", "medical_expiry": "2026-02-16", "drug_test": "2025-05-24", "violations": 0, "status": "Compliant"},
    ],
    "equipment_kpis": {
        "total_trucks": 15, "compliant_trucks": 11, "trucks_expiring": 3, "trucks_non_compliant": 1,
        "total_trailers": 8, "compliant_trailers": 7, "trailers_expiring": 1, "expired_docs": 2,
    },
    "trucks": [
        {"unit_id": "T-101", "year": 2021, "make": "Peterbilt", "model": "579",  "dot_inspected": "2025-06-14", "dot_expiry": "2026-06-14", "reg_expiry": "2026-01-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-102", "year": 2020, "make": "Kenworth",  "model": "T680", "dot_inspected": "2025-04-28", "dot_expiry": "2026-04-28", "reg_expiry": "2026-04-30", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-103", "year": 2019, "make": "Freightliner","model":"Cascadia","dot_inspected":"2024-12-30","dot_expiry":"2025-12-30","reg_expiry":"2025-12-31","ifta": True,  "status": "Expiring Soon"},
        {"unit_id": "T-104", "year": 2022, "make": "Peterbilt", "model": "579",  "dot_inspected": "2025-07-20", "dot_expiry": "2026-07-20", "reg_expiry": "2026-07-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-105", "year": 2021, "make": "Kenworth",  "model": "T680", "dot_inspected": "2025-08-10", "dot_expiry": "2026-08-10", "reg_expiry": "2026-08-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-106", "year": 2018, "make": "Freightliner","model":"Cascadia","dot_inspected":"2025-03-08","dot_expiry":"2026-03-08","reg_expiry":"2026-03-31","ifta": True,  "status": "Compliant"},
        {"unit_id": "T-107", "year": 2020, "make": "Peterbilt", "model": "389",  "dot_inspected": "2025-09-15", "dot_expiry": "2026-09-15", "reg_expiry": "2026-09-30", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-108", "year": 2022, "make": "Volvo",     "model": "VNL",  "dot_inspected": "2025-05-22", "dot_expiry": "2026-05-22", "reg_expiry": "2026-05-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-109", "year": 2017, "make": "Freightliner","model":"Cascadia","dot_inspected":"2024-09-20","dot_expiry":"2025-09-20","reg_expiry":"2025-10-31","ifta": False, "status": "Non-Compliant"},
        {"unit_id": "T-110", "year": 2021, "make": "Kenworth",  "model": "T680", "dot_inspected": "2025-10-05", "dot_expiry": "2026-10-05", "reg_expiry": "2026-10-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-111", "year": 2020, "make": "Peterbilt", "model": "579",  "dot_inspected": "2025-06-18", "dot_expiry": "2026-06-18", "reg_expiry": "2026-06-30", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-112", "year": 2019, "make": "International","model":"LT",  "dot_inspected": "2025-02-14","dot_expiry": "2026-02-14", "reg_expiry": "2026-02-28", "ifta": True,  "status": "Expiring Soon"},
        {"unit_id": "T-113", "year": 2023, "make": "Peterbilt", "model": "579",  "dot_inspected": "2025-11-01", "dot_expiry": "2026-11-01", "reg_expiry": "2026-11-30", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-114", "year": 2021, "make": "Kenworth",  "model": "W900", "dot_inspected": "2025-07-30", "dot_expiry": "2026-07-30", "reg_expiry": "2026-07-31", "ifta": True,  "status": "Compliant"},
        {"unit_id": "T-115", "year": 2018, "make": "Freightliner","model":"Cascadia","dot_inspected":"2025-01-10","dot_expiry":"2026-01-10","reg_expiry":"2026-01-31","ifta": True,  "status": "Expiring Soon"},
    ],
    "trailers": [
        {"unit_id": "TR-201", "year": 2020, "type": "53ft Dry Van",  "dot_inspected": "2025-07-14", "dot_expiry": "2026-07-14", "reg_expiry": "2026-07-31", "status": "Compliant"},
        {"unit_id": "TR-202", "year": 2019, "type": "53ft Dry Van",  "dot_inspected": "2025-04-20", "dot_expiry": "2026-04-20", "reg_expiry": "2026-04-30", "status": "Compliant"},
        {"unit_id": "TR-203", "year": 2021, "type": "48ft Flatbed",  "dot_inspected": "2025-08-08", "dot_expiry": "2026-08-08", "reg_expiry": "2026-08-31", "status": "Compliant"},
        {"unit_id": "TR-204", "year": 2018, "type": "53ft Reefer",   "dot_inspected": "2024-11-28", "dot_expiry": "2025-11-28", "reg_expiry": "2025-12-31", "status": "Expiring Soon"},
        {"unit_id": "TR-205", "year": 2022, "type": "53ft Dry Van",  "dot_inspected": "2025-09-15", "dot_expiry": "2026-09-15", "reg_expiry": "2026-09-30", "status": "Compliant"},
        {"unit_id": "TR-206", "year": 2020, "type": "40ft Flatbed",  "dot_inspected": "2025-06-22", "dot_expiry": "2026-06-22", "reg_expiry": "2026-06-30", "status": "Compliant"},
        {"unit_id": "TR-207", "year": 2021, "type": "53ft Dry Van",  "dot_inspected": "2025-10-10", "dot_expiry": "2026-10-10", "reg_expiry": "2026-10-31", "status": "Compliant"},
        {"unit_id": "TR-208", "year": 2019, "type": "48ft Lowboy",   "dot_inspected": "2025-03-06", "dot_expiry": "2026-03-06", "reg_expiry": "2026-03-31", "status": "Compliant"},
    ],
}

# ── Agents Data ───────────────────────────────────────────────────────────────

AGENTS_DATA = [
    {
        "name": "FinanceAgent",
        "status": "idle",
        "description": "Ingests CSV data and computes all financial metrics for BCAT, Ivan Cartage, and Best Care.",
        "last_heartbeat": "2025-12-31T12:00:00Z",
        "last_task": "Processed brokerage export (Dec 2025) — 492 loads ingested",
        "registered_at": "2025-01-01T00:00:00Z",
    },
    {
        "name": "CoordinatorAgent",
        "status": "idle",
        "description": "Routes messages and orchestrates agents across Discord, Telegram, and email channels.",
        "last_heartbeat": "2025-12-31T12:00:00Z",
        "last_task": "Routed 14 Discord messages, 3 escalations handled",
        "registered_at": "2025-01-01T00:00:00Z",
    },
    {
        "name": "MarketingAgent",
        "status": "idle",
        "description": "Manages Google Ads, Facebook Ads, SEO analysis, and competitor tracking across all brands.",
        "last_heartbeat": "2025-12-31T11:45:00Z",
        "last_task": "Generated 5 new recommendations for BCAT Logistics (Dec review)",
        "registered_at": "2025-01-01T00:00:00Z",
    },
    {
        "name": "SalesAgent",
        "status": "idle",
        "description": "Manages outreach campaigns, lead lists, Apollo syncs, and meeting tracking.",
        "last_heartbeat": "2025-12-31T11:50:00Z",
        "last_task": "Synced 316 new leads from Apollo — BCAT Logistics workspace",
        "registered_at": "2025-01-01T00:00:00Z",
    },
    {
        "name": "DiscordBot",
        "status": "idle",
        "description": "Connects agents to the #finance Discord channel. Accepts CSV uploads and responds to commands.",
        "last_heartbeat": "2025-12-31T11:58:00Z",
        "last_task": "Processed ivan_expenses_dec2025.csv — 84 expense rows ingested",
        "registered_at": "2025-01-01T00:00:00Z",
    },
    {
        "name": "TelegramGateway",
        "status": "idle",
        "description": "Openclaw gateway connecting @big_ron_bot to the local agent system.",
        "last_heartbeat": "2025-12-31T11:55:00Z",
        "last_task": "Delivered weekly finance summary report",
        "registered_at": "2025-03-01T00:00:00Z",
    },
]
