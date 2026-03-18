import os
import threading
import logging
import config                                                    # must be first — raises if SECRET_KEY missing in prod
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from auth import login_required, verify_credentials
from finance_agent import FinanceAgent, get_ivan_expense_metrics
import agent_registry
import marketing_data as _md
from agents.marketing_agent import MarketingAgent

# ── Background bot launcher ───────────────────────────────────────────────────
_log = logging.getLogger(__name__)

def _start_discord_bot():
    if not os.environ.get('DISCORD_BOT_TOKEN', '').strip():
        _log.info('DISCORD_BOT_TOKEN not set — Discord bot skipped.')
        return
    try:
        import discord_bot
        discord_bot.run()
    except Exception as e:
        _log.error('Discord bot crashed: %s', e, exc_info=True)

def _start_telegram_bot():
    if not os.environ.get('TELEGRAM_BOT_TOKEN', '').strip():
        _log.info('TELEGRAM_BOT_TOKEN not set — Telegram bot skipped.')
        return
    try:
        import telegram_bot
        telegram_bot.run()
    except Exception as e:
        _log.error('Telegram bot crashed: %s', e, exc_info=True)

threading.Thread(target=_start_discord_bot, daemon=True, name='discord-bot').start()
threading.Thread(target=_start_telegram_bot, daemon=True, name='telegram-bot').start()

# Best Care real-data service layer (imported lazily to avoid startup failure
# if google-ads package is not yet installed)
try:
    from services import best_care_service as _bc
    from services import recommendation_service as _rec_svc
    _BC_AVAILABLE = True
except Exception as _bc_import_err:
    _BC_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning('Best Care services unavailable: %s', _bc_import_err)

app = Flask(__name__)

# ── Flask configuration from config.py ───────────────────────────────────────
app.secret_key                       = config.SECRET_KEY
app.config['SESSION_COOKIE_NAME']    = config.SESSION_COOKIE_NAME
app.config['SESSION_COOKIE_HTTPONLY']= config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SECURE']  = config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_SAMESITE']= config.SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_DOMAIN']  = config.SESSION_COOKIE_DOMAIN
app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME

finance_agent  = FinanceAgent()
marketing_agent = MarketingAgent()

agent_registry.register("Dashboard", "Flask web dashboard — serves finance data and agent status")


# ── Auth routes (public) ──────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))

    error = None
    email = ''

    if request.method == 'POST':
        email    = (request.form.get('email')    or '').strip()
        password = (request.form.get('password') or '').strip()

        if verify_credentials(email, password):
            session.permanent = True
            session['authenticated'] = True
            session['user_email']    = email
            next_url = request.form.get('next') or '/'
            # Safety: only allow relative redirects
            if not next_url.startswith('/'):
                next_url = '/'
            return redirect(next_url)

        error = 'Invalid email or password.'

    return render_template('login.html', error=error, email=email,
                           next=request.args.get('next', ''))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Protected dashboard ───────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard_api():
    finance_agent.ingest_data()

    ivan_metrics = get_ivan_expense_metrics()
    brokerage_metrics = finance_agent.calculate_brokerage_metrics()

    monthly_brokerage_summary = finance_agent.get_monthly_brokerage_summary()
    brokerage_top_customers_by_month = finance_agent.get_brokerage_top_customers_by_month()
    ivan_top_customers_by_month = finance_agent.get_ivan_top_customers_by_month()

    total_company_revenue = (
        float(ivan_metrics.get('ivan_cartage_revenue', 0)) +
        float(brokerage_metrics.get('gross_revenue', 0))
    )

    return jsonify({
        'report_start_date': '2026-01-01',
        'report_end_date': '2026-03-04',
        'total_company_revenue': total_company_revenue,
        'brokerage': {
            'gross_revenue': brokerage_metrics.get('gross_revenue', 0),
            'carrier_pay': brokerage_metrics.get('carrier_pay', 0),
            'gross_profit': brokerage_metrics.get('gross_profit', 0),
            'brokerage_margin': brokerage_metrics.get('brokerage_margin', brokerage_metrics.get('margin_percentage', 0)),
            'monthly_brokerage_summary': monthly_brokerage_summary,
            'brokerage_top_customers_by_month': brokerage_top_customers_by_month
        },
        'ivan': {
            'ivan_cartage_revenue': ivan_metrics.get('ivan_cartage_revenue', 0),
            'ivan_expenses': ivan_metrics.get('ivan_expenses', 0),
            'ivan_true_profit': ivan_metrics.get('ivan_true_profit', 0),
            'ivan_total_miles': ivan_metrics.get('ivan_total_miles', 0),
            'ivan_revenue_per_mile': ivan_metrics.get('ivan_revenue_per_mile', 0),
            'ivan_cost_per_mile': ivan_metrics.get('ivan_cost_per_mile', 0),
            'ivan_profit_per_mile': ivan_metrics.get('ivan_profit_per_mile', 0),
            'ivan_monthly_true_profit': ivan_metrics.get('ivan_monthly_true_profit', []),
            'ivan_expenses_category_monthly': ivan_metrics.get('ivan_expenses_category_monthly', []),
            'ivan_top_customers_by_month': ivan_top_customers_by_month
        }
    })

@app.route('/api/agents', methods=['GET'])
@login_required
def agents_api():
    return jsonify(agent_registry.get_all())


# ---------------------------------------------------------------------------
# Marketing API
# ---------------------------------------------------------------------------

@app.route('/api/marketing/groups', methods=['GET'])
@login_required
def marketing_groups():
    return jsonify(_md.get_groups_summary())

@app.route('/api/marketing/<group_id>/overview', methods=['GET'])
@login_required
def marketing_overview(group_id):
    data = _md.get_overview(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/seo', methods=['GET'])
@login_required
def marketing_seo(group_id):
    data = _md.get_seo(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/google-ads', methods=['GET'])
@login_required
def marketing_google_ads(group_id):
    data = _md.get_google_ads(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/facebook-ads', methods=['GET'])
@login_required
def marketing_facebook_ads(group_id):
    data = _md.get_facebook_ads(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/competitors', methods=['GET'])
@login_required
def marketing_competitors(group_id):
    data = _md.get_competitors(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/knowledge-graph', methods=['GET'])
@login_required
def marketing_knowledge_graph(group_id):
    data = _md.get_knowledge_graph(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/recommendations', methods=['GET'])
@login_required
def marketing_recommendations(group_id):
    data = _md.get_recommendations(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/implementation-history', methods=['GET'])
@login_required
def marketing_implementation_history(group_id):
    data = _md.get_implementation_history(group_id)
    if data is None:
        return jsonify({"error": "Group not found"}), 404
    return jsonify(data)

@app.route('/api/marketing/<group_id>/analyze/<channel>', methods=['POST'])
@login_required
def marketing_analyze(group_id, channel):
    if channel == 'seo':
        result = marketing_agent.run_seo_analysis(group_id)
    elif channel == 'google_ads':
        result = marketing_agent.run_google_ads_analysis(group_id)
    elif channel == 'facebook_ads':
        result = marketing_agent.run_facebook_ads_analysis(group_id)
    elif channel == 'cross_channel':
        result = marketing_agent.generate_cross_channel_insights(group_id)
    elif channel == 'full':
        result = marketing_agent.run_full_analysis(group_id)
    else:
        return jsonify({"error": f"Unknown channel: {channel}"}), 400
    return jsonify(result)

@app.route('/api/marketing/<group_id>/implement/<rec_id>', methods=['POST'])
@login_required
def marketing_implement(group_id, rec_id):
    result = marketing_agent.approve_recommendation(group_id, rec_id)
    return jsonify(result)

@app.route('/api/marketing/<group_id>/generate-plan/<channel>', methods=['POST'])
@login_required
def marketing_generate_plan(group_id, channel):
    if channel == 'seo':
        result = marketing_agent.generate_seo_optimization_plan(group_id)
    elif channel == 'google_ads':
        result = marketing_agent.generate_google_ads_recommendations(group_id)
    elif channel == 'facebook_ads':
        result = marketing_agent.generate_facebook_ads_recommendations(group_id)
    else:
        return jsonify({"error": f"Unknown channel: {channel}"}), 400
    return jsonify(result)

@app.route('/api/marketing/status', methods=['GET'])
@login_required
def marketing_status():
    return jsonify(marketing_agent.get_status_summary())


# ---------------------------------------------------------------------------
# Best Care Auto Transport — Real Data API
# ---------------------------------------------------------------------------

def _bc_check():
    if not _BC_AVAILABLE:
        return jsonify({'error': 'Best Care services not available. Check server logs.'}), 503
    return None

@app.route('/api/best-care/sync-status', methods=['GET'])
@login_required
def bc_sync_status():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.get_sync_status())

@app.route('/api/best-care/sync/google-ads', methods=['POST'])
@login_required
def bc_sync_google_ads():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.sync_google_ads())

@app.route('/api/best-care/sync/calls', methods=['POST'])
@login_required
def bc_sync_calls():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.sync_calls())

@app.route('/api/best-care/sync/competitors', methods=['POST'])
@login_required
def bc_sync_competitors():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.sync_competitors())

@app.route('/api/best-care/sync/all', methods=['POST'])
@login_required
def bc_sync_all():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.sync_all())

@app.route('/api/best-care/dashboard', methods=['GET'])
@login_required
def bc_dashboard():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.get_dashboard_data())

@app.route('/api/best-care/monthly-performance', methods=['GET'])
@login_required
def bc_monthly_performance():
    err = _bc_check()
    if err: return err
    from services import attribution_service
    return jsonify({
        'monthly':     attribution_service.get_monthly_performance(),
        'assumptions': attribution_service.get_assumptions(),
    })

@app.route('/api/best-care/google-ads/monthly', methods=['GET'])
@login_required
def bc_gads_monthly():
    err = _bc_check()
    if err: return err
    from services import google_ads_service
    return jsonify(google_ads_service.get_monthly_summary())

@app.route('/api/best-care/google-ads/campaigns', methods=['GET'])
@login_required
def bc_gads_campaigns():
    err = _bc_check()
    if err: return err
    from services import google_ads_service
    return jsonify(google_ads_service.get_campaigns())

@app.route('/api/best-care/google-ads/keywords', methods=['GET'])
@login_required
def bc_gads_keywords():
    err = _bc_check()
    if err: return err
    from services import google_ads_service
    month = request.args.get('month')
    kws = google_ads_service.get_keywords()
    if month:
        kws = [k for k in kws if k.get('month', '').startswith(month)]
    return jsonify(kws)

@app.route('/api/best-care/google-ads/search-terms', methods=['GET'])
@login_required
def bc_gads_search_terms():
    err = _bc_check()
    if err: return err
    from services import google_ads_service
    month = request.args.get('month')
    terms = google_ads_service.get_search_terms()
    if month:
        terms = [t for t in terms if t.get('month', '').startswith(month)]
    return jsonify(terms)

@app.route('/api/best-care/calls/monthly', methods=['GET'])
@login_required
def bc_calls_monthly():
    err = _bc_check()
    if err: return err
    from services import eightx8_service
    return jsonify(eightx8_service.get_monthly_summary())

@app.route('/api/best-care/competitors', methods=['GET'])
@login_required
def bc_competitors():
    err = _bc_check()
    if err: return err
    from services import competitor_intel_service
    return jsonify({
        'competitors':    competitor_intel_service.get_competitor_summary(),
        'global_themes':  competitor_intel_service.get_global_themes(),
        'global_offers':  competitor_intel_service.get_global_offers(),
        'sync_status':    competitor_intel_service.get_sync_status(),
    })

@app.route('/api/best-care/recommendations', methods=['GET'])
@login_required
def bc_recommendations():
    err = _bc_check()
    if err: return err
    return jsonify(_rec_svc.get_recommendations())

@app.route('/api/best-care/recommendations/generate', methods=['POST'])
@login_required
def bc_generate_recommendations():
    err = _bc_check()
    if err: return err
    return jsonify(_bc.generate_recommendations())

@app.route('/api/best-care/recommendations/<rec_id>/implement', methods=['POST'])
@login_required
def bc_implement_recommendation(rec_id):
    err = _bc_check()
    if err: return err
    body      = request.get_json(silent=True) or {}
    action    = _rec_svc.queue_action(rec_id, body.get('action_type', 'generic'), body.get('params', {}))
    executed  = _rec_svc.execute_action(action['id'])
    return jsonify(executed)

@app.route('/api/best-care/implementation-queue', methods=['GET'])
@login_required
def bc_implementation_queue():
    err = _bc_check()
    if err: return err
    return jsonify(_rec_svc.get_queue())

@app.route('/api/best-care/assumptions', methods=['GET', 'POST'])
@login_required
def bc_assumptions():
    err = _bc_check()
    if err: return err
    from services import attribution_service
    if request.method == 'POST':
        body    = request.get_json(silent=True) or {}
        updated = attribution_service.save_config(body)
        attribution_service.calculate_and_cache()
        return jsonify(updated)
    return jsonify(attribution_service.get_assumptions())


# ── Sales service layer ────────────────────────────────────────────────────────
try:
    from services import sales_service as _sales
    _SALES_AVAILABLE = True
except Exception as _sales_import_err:
    _SALES_AVAILABLE = False
    import logging as _logging
    _logging.getLogger(__name__).warning('Sales services unavailable: %s', _sales_import_err)

def _sales_unavailable():
    return jsonify({'error': 'Sales services unavailable', 'ok': False}), 503

# ── Sales routes ───────────────────────────────────────────────────────────────

@app.route('/api/sales/workspaces', methods=['GET'])
@login_required
def sales_workspaces():
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_all_workspaces_summary())

@app.route('/api/sales/<workspace_id>/overview', methods=['GET'])
@login_required
def sales_overview(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_workspace_summary(workspace_id))

@app.route('/api/sales/<workspace_id>/sync-status', methods=['GET'])
@login_required
def sales_sync_status(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_sync_status(workspace_id))

@app.route('/api/sales/<workspace_id>/sync/instantly', methods=['POST'])
@login_required
def sales_sync_instantly(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.sync_instantly(workspace_id))

@app.route('/api/sales/<workspace_id>/sync/calendar', methods=['POST'])
@login_required
def sales_sync_calendar(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.sync_calendar(workspace_id))

@app.route('/api/sales/<workspace_id>/sync/all', methods=['POST'])
@login_required
def sales_sync_all(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.sync_all(workspace_id))

@app.route('/api/sales/<workspace_id>/leads', methods=['GET'])
@login_required
def sales_leads(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_leads(workspace_id))

@app.route('/api/sales/<workspace_id>/lead-lists', methods=['GET'])
@login_required
def sales_lead_lists(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_lead_lists(workspace_id))

@app.route('/api/sales/<workspace_id>/leads/scrape-maps', methods=['POST'])
@login_required
def sales_scrape_maps(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.scrape_google_maps(
        workspace_id,
        body.get('query', ''),
        body.get('location', ''),
        body.get('max_items', 100),
    ))

@app.route('/api/sales/<workspace_id>/leads/scrape-linkedin', methods=['POST'])
@login_required
def sales_scrape_linkedin(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.scrape_linkedin(
        workspace_id,
        body.get('search_url', ''),
        body.get('max_items', 200),
    ))

@app.route('/api/sales/<workspace_id>/leads/enrich', methods=['POST'])
@login_required
def sales_enrich_lead(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.enrich_lead(body.get('email', '')))

@app.route('/api/sales/<workspace_id>/leads/sync-apollo', methods=['POST'])
@login_required
def sales_sync_apollo(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.sync_apollo(
        workspace_id,
        titles=body.get('titles'),
        industries=body.get('industries'),
        locations=body.get('locations'),
        company_sizes=body.get('company_sizes'),
    ))

@app.route('/api/sales/<workspace_id>/leads/scraped', methods=['GET'])
@login_required
def sales_scraped_leads(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    source = request.args.get('source')
    return jsonify(_sales.get_scraped_leads(workspace_id, source))

@app.route('/api/sales/<workspace_id>/email/campaigns', methods=['GET'])
@login_required
def sales_email_campaigns(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_email_campaigns(workspace_id))

@app.route('/api/sales/<workspace_id>/email/enroll', methods=['POST'])
@login_required
def sales_enroll_leads(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.enroll_leads_to_campaign(
        workspace_id,
        body.get('campaign_id', ''),
        body.get('emails', []),
    ))

@app.route('/api/sales/<workspace_id>/linkedin/campaigns', methods=['GET'])
@login_required
def sales_linkedin_campaigns(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_linkedin_campaigns(workspace_id))

@app.route('/api/sales/<workspace_id>/daily', methods=['GET'])
@login_required
def sales_daily_results(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    days = int(request.args.get('days', 30))
    return jsonify(_sales.get_daily_results(workspace_id, days))

@app.route('/api/sales/<workspace_id>/messaging/templates', methods=['GET'])
@login_required
def sales_message_templates(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_message_templates(workspace_id))

@app.route('/api/sales/<workspace_id>/messaging/generate', methods=['POST'])
@login_required
def sales_generate_message(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.generate_message(
        workspace_id,
        body.get('style', 'concise'),
        body.get('channel', 'email'),
        body.get('goal', 'cold_intro'),
        body.get('variables', {}),
    ))

@app.route('/api/sales/<workspace_id>/messaging/bulk-generate', methods=['POST'])
@login_required
def sales_bulk_generate(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.bulk_generate_messages(
        workspace_id,
        body.get('style', 'concise'),
        body.get('channel', 'email'),
        body.get('goal', 'cold_intro'),
        body.get('leads', []),
        body.get('common_vars', {}),
    ))

@app.route('/api/sales/<workspace_id>/meetings', methods=['GET'])
@login_required
def sales_meetings(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_meetings(workspace_id))

@app.route('/api/sales/<workspace_id>/meetings/upcoming', methods=['GET'])
@login_required
def sales_meetings_upcoming(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    days = int(request.args.get('days', 7))
    return jsonify(_sales.get_upcoming_meetings(workspace_id, days))

@app.route('/api/sales/<workspace_id>/recommendations', methods=['GET'])
@login_required
def sales_recommendations(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_recommendations(workspace_id))

@app.route('/api/sales/<workspace_id>/recommendations/generate', methods=['POST'])
@login_required
def sales_generate_recommendations(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.generate_recommendations(workspace_id))

@app.route('/api/sales/<workspace_id>/recommendations/<rec_id>/implement', methods=['POST'])
@login_required
def sales_implement_rec(workspace_id, rec_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    body = request.get_json(silent=True) or {}
    return jsonify(_sales.implement_recommendation(workspace_id, rec_id, body.get('notes', '')))

@app.route('/api/sales/<workspace_id>/recommendations/<rec_id>/dismiss', methods=['POST'])
@login_required
def sales_dismiss_rec(workspace_id, rec_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.dismiss_recommendation(workspace_id, rec_id))

@app.route('/api/sales/<workspace_id>/activity', methods=['GET'])
@login_required
def sales_activity(workspace_id):
    if not _SALES_AVAILABLE: return _sales_unavailable()
    return jsonify(_sales.get_activity_log(workspace_id))


@app.route('/api/aiden/optimize-post', methods=['POST'])
@login_required
def aiden_optimize_post():
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'content is required'}), 400
    from content_optimizer import optimize_post
    result = optimize_post(content, data.get('content_type', 'thought_leadership'), data.get('tone', 'professional'))
    return jsonify(result)


@app.route('/api/aiden/generate-post', methods=['POST'])
@login_required
def aiden_generate_post():
    data = request.get_json(silent=True) or {}
    topic = (data.get('topic') or '').strip()
    if not topic:
        return jsonify({'error': 'topic is required'}), 400
    from hook_generator import generate_post
    post = generate_post(topic, data.get('tone', 'direct'), data.get('category', 'industry'))
    return jsonify(post)


@app.route('/api/aiden/generate-hooks', methods=['POST'])
@login_required
def aiden_generate_hooks():
    data = request.get_json(silent=True) or {}
    topic = (data.get('topic') or '').strip()
    if not topic:
        return jsonify({'error': 'topic is required'}), 400
    from hook_generator import generate_hooks
    hooks = generate_hooks(topic, data.get('style_mode', 'operator_founder'), data.get('category', 'industry'))
    return jsonify({'hooks': hooks, 'ai_powered': bool(os.environ.get('ANTHROPIC_API_KEY', '').strip())})


# ── Health / diagnostics endpoint (public — no login required) ───────────────
@app.route('/api/health', methods=['GET'])
def health():
    from pathlib import Path
    import threading as _threading

    root = Path(__file__).resolve().parent

    def _env(key):
        return bool(os.environ.get(key, '').strip())

    def _csv(name):
        p = root / name
        if not p.exists():
            return {'present': False}
        try:
            import pandas as pd
            df = pd.read_csv(p, nrows=1)
            rows = sum(1 for _ in open(p)) - 1
            return {'present': True, 'rows': rows, 'columns': list(df.columns)}
        except Exception as e:
            return {'present': True, 'error': str(e)}

    def _thread_alive(name):
        return any(t.name == name and t.is_alive() for t in _threading.enumerate())

    status = {
        'ok': True,
        'env': {
            'SECRET_KEY':           _env('SECRET_KEY'),
            'ADMIN_EMAIL':          _env('ADMIN_EMAIL'),
            'ADMIN_PASSWORD_HASH':  _env('ADMIN_PASSWORD_HASH'),
            'DISCORD_BOT_TOKEN':    _env('DISCORD_BOT_TOKEN'),
            'TELEGRAM_BOT_TOKEN':   _env('TELEGRAM_BOT_TOKEN'),
            'ANTHROPIC_API_KEY':    _env('ANTHROPIC_API_KEY'),
            'APP_BASE_URL':         _env('APP_BASE_URL'),
            'COOKIE_DOMAIN':        _env('COOKIE_DOMAIN'),
        },
        'data': {
            'brokerage_loads':      _csv('brokerage_loads.csv'),
            'ivan_cartage_loads':   _csv('ivan_cartage_loads.csv'),
            'ivan_expenses':        _csv('ivan_expenses.csv'),
            'amazon_loads':         _csv('amazon_loads.csv'),
        },
        'bots': {
            'discord':  _thread_alive('discord-bot'),
            'telegram': _thread_alive('telegram-bot'),
        },
        'services': {
            'best_care': _BC_AVAILABLE,
        },
    }
    return jsonify(status)


# ── Dev server entry point ────────────────────────────────────────────────────
# Production: use gunicorn (see Procfile / .replit).
if __name__ == '__main__':
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
    )
