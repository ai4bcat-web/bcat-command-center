"""
demo_app.py — BCAT Command Center Demo Dashboard

Runs on port 5051. Serves realistic mock data only.
Zero connection to production data, live APIs, or the live dashboard (port 5050).

Start:
    cd /Users/adminoid/AI_WORKSPACE/MultiAgent_Operations
    source .venv/bin/activate
    python3 demo_app.py
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request, abort

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import demo_data as D

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
    static_url_path="/static",
)

DEMO_PORT = int(os.getenv("DEMO_PORT", 5051))

# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("demo.html")

# ── Finance API ───────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(D.DASHBOARD_DATA)

# ── Marketing API ─────────────────────────────────────────────────────────────

def _mkt(group: str, section: str):
    grp = D.MARKETING_DATA.get(group, {})
    return grp.get(section, {})

@app.route("/api/marketing/<group>/overview")
def mkt_overview(group):
    data = _mkt(group, "overview")
    # competitors nested in overview for convenience
    return jsonify(data)

@app.route("/api/marketing/<group>/competitors")
def mkt_competitors(group):
    return jsonify(_mkt(group, "competitors") or [])

@app.route("/api/marketing/<group>/seo")
def mkt_seo(group):
    return jsonify(_mkt(group, "seo"))

@app.route("/api/marketing/<group>/google-ads")
def mkt_google_ads(group):
    return jsonify(_mkt(group, "google_ads"))

@app.route("/api/marketing/<group>/facebook-ads")
def mkt_facebook_ads(group):
    return jsonify(_mkt(group, "facebook_ads"))

@app.route("/api/marketing/<group>/knowledge-graph")
def mkt_knowledge_graph(group):
    return jsonify(_mkt(group, "knowledge_graph") or {"entities": [], "relationships": [], "insights": []})

@app.route("/api/marketing/<group>/recommendations")
def mkt_recommendations(group):
    return jsonify(_mkt(group, "recommendations") or [])

@app.route("/api/marketing/<group>/implementation-history")
def mkt_impl_history(group):
    return jsonify(_mkt(group, "implementation_history") or [])

@app.route("/api/marketing/<group>/analyze/<channel>", methods=["POST"])
def mkt_analyze(group, channel):
    return jsonify({"message": f"Analysis queued for {group} / {channel} — results ready in ~60s (demo)"})

@app.route("/api/marketing/<group>/generate-plan/<channel>", methods=["POST"])
def mkt_generate_plan(group, channel):
    return jsonify({"message": f"Plan generation queued for {group} / {channel} (demo)"})

@app.route("/api/marketing/<group>/implement/<int:rec_id>", methods=["POST"])
def mkt_implement(group, rec_id):
    return jsonify({"message": f"Recommendation {rec_id} queued for implementation (demo)"})

@app.route("/api/marketing/<group>/analyze/cross_channel", methods=["POST"])
def mkt_cross_channel(group):
    return jsonify({"message": f"Cross-channel analysis started for {group} (demo)"})

@app.route("/api/marketing/<group>/linkedin-campaigns")
def mkt_linkedin_campaigns(group):
    return jsonify(_mkt(group, "linkedin_campaigns") or [])

@app.route("/api/marketing/<group>/email-marketing")
def mkt_email_marketing(group):
    return jsonify(_mkt(group, "email_marketing") or {})

# ── Operations + Compliance API ───────────────────────────────────────────────

@app.route("/api/operations")
def api_operations():
    return jsonify(D.BCAT_OPERATIONS)

@app.route("/api/compliance")
def api_compliance():
    return jsonify(D.BCAT_COMPLIANCE)

# ── Best Care real-data endpoints (mocked) ───────────────────────────────────

@app.route("/api/best-care/sync-status")
def bc_sync_status():
    return jsonify({
        "google_ads":  {"last_sync": "2025-12-31T08:00:00Z", "status": "ok"},
        "calls":       {"last_sync": "2025-12-31T08:00:00Z", "status": "ok"},
        "competitors": {"last_sync": "2025-12-30T22:00:00Z", "status": "ok"},
    })

@app.route("/api/best-care/sync/all", methods=["POST"])
def bc_sync_all():
    return jsonify({"google_ads": {"ok": True}, "calls": {"ok": True}, "competitors": {"ok": True}})

@app.route("/api/best-care/sync/google-ads", methods=["POST"])
def bc_sync_google_ads():
    return jsonify({"ok": True, "records": 12})

@app.route("/api/best-care/assumptions")
def bc_assumptions():
    return jsonify({"GOOGLE_ADS_CID": "demo-****", "CALLS_SOURCE": "8x8 (demo)", "REVENUE_PER_LEAD": 820})

@app.route("/api/best-care/dashboard")
def bc_dashboard():
    return jsonify(D.BEST_CARE_DASHBOARD)

@app.route("/api/best-care/google-ads/monthly")
def bc_gads_monthly():
    return jsonify(D.MARKETING_DATA["best_care_auto"]["google_ads"]["trends"]["spend_conversions"])

@app.route("/api/best-care/google-ads/campaigns")
def bc_gads_campaigns():
    return jsonify(D.MARKETING_DATA["best_care_auto"]["google_ads"]["campaigns"])

@app.route("/api/best-care/google-ads/keywords")
def bc_gads_keywords():
    return jsonify([
        {"keyword": "auto transport company",    "clicks": 284, "conversions": 4, "cpa": 720},
        {"keyword": "car shipping quotes",        "clicks": 412, "conversions": 3, "cpa": 960},
        {"keyword": "enclosed auto transport",    "clicks": 98,  "conversions": 2, "cpa": 640},
        {"keyword": "vehicle transport midwest",  "clicks": 76,  "conversions": 1, "cpa": 1100},
    ])

@app.route("/api/best-care/recommendations")
def bc_recommendations():
    return jsonify(D.MARKETING_DATA["best_care_auto"]["recommendations"])

@app.route("/api/best-care/recommendations/generate", methods=["POST"])
def bc_recs_generate():
    return jsonify({"count": 3})

@app.route("/api/best-care/recommendations/<int:rec_id>/implement", methods=["POST"])
def bc_rec_implement(rec_id):
    return jsonify({"result": {"message": f"Recommendation {rec_id} queued (demo)"}})

@app.route("/api/best-care/implementation-queue")
def bc_impl_queue():
    return jsonify([
        {"id": 1, "action_type": "google_ads_budget", "status": "completed", "queued_at": "2025-12-02T10:00:00Z", "result": {"message": "Budget adjusted +$800/mo"}},
    ])

# ── Sales API ─────────────────────────────────────────────────────────────────

def _sales(workspace: str, section: str):
    ws = D.SALES_DATA.get(workspace, {})
    return ws.get(section, {})

@app.route("/api/sales/<workspace>/overview")
def sales_overview(workspace):
    d = _sales(workspace, "overview")
    return jsonify(d)

@app.route("/api/sales/<workspace>/daily")
def sales_daily(workspace):
    return jsonify(_sales(workspace, "daily"))

@app.route("/api/sales/<workspace>/activity")
def sales_activity(workspace):
    return jsonify(_sales(workspace, "activity"))

@app.route("/api/sales/<workspace>/leads")
def sales_leads(workspace):
    return jsonify(_sales(workspace, "leads"))

@app.route("/api/sales/<workspace>/lead-lists")
def sales_lead_lists(workspace):
    return jsonify(_sales(workspace, "lead_lists"))

@app.route("/api/sales/<workspace>/email/campaigns")
def sales_email_campaigns(workspace):
    return jsonify(_sales(workspace, "email_campaigns"))

@app.route("/api/sales/<workspace>/linkedin/campaigns")
def sales_linkedin_campaigns(workspace):
    return jsonify(_sales(workspace, "linkedin_campaigns"))

@app.route("/api/sales/<workspace>/leads/scraped")
def sales_leads_scraped(workspace):
    return jsonify({"leads": []})

@app.route("/api/sales/<workspace>/meetings")
def sales_meetings(workspace):
    return jsonify(_sales(workspace, "meetings"))

@app.route("/api/sales/<workspace>/messaging/templates")
def sales_messaging_templates(workspace):
    return jsonify(_sales(workspace, "messaging_templates"))

@app.route("/api/sales/<workspace>/recommendations")
def sales_recommendations(workspace):
    return jsonify(_sales(workspace, "recommendations"))

@app.route("/api/sales/<workspace>/sync-status")
def sales_sync_status(workspace):
    return jsonify(_sales(workspace, "sync_status"))

@app.route("/api/sales/<workspace>/sync/all", methods=["POST"])
def sales_sync_all(workspace):
    return jsonify({"ok": True, "message": "Demo sync complete"})

@app.route("/api/sales/<workspace>/sync/instantly", methods=["POST"])
def sales_sync_instantly(workspace):
    return jsonify({"ok": True})

@app.route("/api/sales/<workspace>/sync/calendar", methods=["POST"])
def sales_sync_calendar(workspace):
    return jsonify({"ok": True})

@app.route("/api/sales/<workspace>/leads/sync-apollo", methods=["POST"])
def sales_sync_apollo(workspace):
    return jsonify({"ok": True, "added": 47})

@app.route("/api/sales/<workspace>/leads/scrape-maps", methods=["POST"])
def sales_scrape_maps(workspace):
    return jsonify({"ok": True, "queued": True})

@app.route("/api/sales/<workspace>/leads/scrape-linkedin", methods=["POST"])
def sales_scrape_linkedin(workspace):
    return jsonify({"ok": True, "queued": True})

@app.route("/api/sales/<workspace>/email/enroll", methods=["POST"])
def sales_enroll(workspace):
    body = request.get_json(silent=True) or {}
    return jsonify({"count": len(body.get("emails", []))})

@app.route("/api/sales/<workspace>/messaging/generate", methods=["POST"])
def sales_msg_generate(workspace):
    return jsonify({
        "subject": "Quick question about your freight capacity",
        "body": "Hi {first_name},\n\nI noticed {company} is expanding operations in the Midwest — we've helped similar logistics firms cut carrier costs by 15–22% using our platform.\n\nWould a 15-min call make sense this week?\n\nBest,\nBCAT Team",
    })

@app.route("/api/sales/<workspace>/recommendations/generate", methods=["POST"])
def sales_recs_generate(workspace):
    return jsonify({"ok": True})

@app.route("/api/sales/<workspace>/recommendations/<int:rec_id>/implement", methods=["POST"])
def sales_rec_implement(workspace, rec_id):
    return jsonify({"ok": True})

@app.route("/api/sales/<workspace>/recommendations/<int:rec_id>/dismiss", methods=["POST"])
def sales_rec_dismiss(workspace, rec_id):
    return jsonify({"ok": True})

# ── Agents API ────────────────────────────────────────────────────────────────

@app.route("/api/agents")
def api_agents():
    return jsonify(D.AGENTS_DATA)

@app.route("/api/aiden/optimize-post", methods=["POST"])
def aiden_optimize_post():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400
    from content_optimizer import optimize_post
    result = optimize_post(content, data.get("content_type", "thought_leadership"), data.get("tone", "professional"))
    return jsonify(result)


@app.route("/api/aiden/generate-post", methods=["POST"])
def aiden_generate_post():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    from hook_generator import generate_post
    post = generate_post(topic, data.get("tone", "direct"), data.get("category", "industry"))
    return jsonify(post)


@app.route("/api/aiden/generate-hooks", methods=["POST"])
def aiden_generate_hooks():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    from hook_generator import generate_hooks
    hooks = generate_hooks(topic, data.get("style_mode", "operator_founder"), data.get("category", "industry"))
    return jsonify({"hooks": hooks, "ai_powered": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  BCAT Command Center — DEMO")
    print(f"  http://localhost:{DEMO_PORT}")
    print(f"  Using synthetic data only. Zero production impact.")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=DEMO_PORT, debug=False)
