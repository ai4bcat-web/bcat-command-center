import os
import sys
import threading
import logging
from pathlib import Path

# ── Logging — configure before any imports so all loggers inherit INFO level ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# ── Ensure project root is on sys.path so all agent/bot imports resolve ───────
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config                                                    # must be first — raises if SECRET_KEY missing in prod
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from auth import login_required
from finance_agent import FinanceAgent, get_ivan_expense_metrics
import agent_registry
import marketing_data as _md
from agents.marketing_agent import MarketingAgent
from agents.coordinator_agent import CoordinatorAgent

# ── Background bot launcher ───────────────────────────────────────────────────
_log = logging.getLogger(__name__)

def _start_discord_bot():
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    print(f"[discord-bot] Thread started. Token present: {bool(token)}", flush=True)
    if not token:
        print("[discord-bot] DISCORD_BOT_TOKEN is not set — bot will not start.", flush=True)
        print("[discord-bot] Add DISCORD_BOT_TOKEN=your_token to .env and restart.", flush=True)
        return
    print("[discord-bot] Importing discord_bot module...", flush=True)
    try:
        import discord_bot
        print("[discord-bot] Module loaded. Calling discord_bot.run()...", flush=True)
        discord_bot.run()
        print("[discord-bot] discord_bot.run() returned (bot stopped).", flush=True)
    except Exception as e:
        import traceback
        print(f"[discord-bot] CRASHED: {e}", flush=True)
        traceback.print_exc()

def _start_telegram_bot():
    if not os.environ.get('TELEGRAM_BOT_TOKEN', '').strip():
        _log.info('TELEGRAM_BOT_TOKEN not set — Telegram bot skipped.')
        return
    try:
        import telegram_bot
        telegram_bot.run()
    except Exception as e:
        _log.error('Telegram bot crashed: %s', e, exc_info=True)

# Bot threads are started in the __main__ block below (not at import time)
# so that Flask CLI commands, wsgi.py, and gunicorn don't accidentally
# launch duplicate bot connections.

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

# ── Core config ───────────────────────────────────────────────────────────────
app.secret_key                            = config.SECRET_KEY
app.config['SESSION_COOKIE_NAME']         = config.SESSION_COOKIE_NAME
app.config['SESSION_COOKIE_HTTPONLY']     = config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SECURE']       = config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_SAMESITE']     = config.SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_DOMAIN']       = config.SESSION_COOKIE_DOMAIN
app.config['PERMANENT_SESSION_LIFETIME']  = config.PERMANENT_SESSION_LIFETIME

# ── Extensions ────────────────────────────────────────────────────────────────
from extensions import db, migrate, login_manager, bcrypt, limiter, csrf

# These always init regardless of DB — login_manager must be attached before
# any request hits a @login_required route, even in local dev without a DB.
app.config['WTF_CSRF_ENABLED']          = config.WTF_CSRF_ENABLED
app.config['WTF_CSRF_TRUSTED_ORIGINS']  = config.WTF_CSRF_TRUSTED_ORIGINS
bcrypt.init_app(app)
limiter.init_app(app)
csrf.init_app(app)

login_manager.init_app(app)
login_manager.login_view    = 'login'
login_manager.login_message = ''

@login_manager.user_loader
def load_user(user_id):
    if not config.DATABASE_URL:
        from flask_login import UserMixin
        class _DevUser(UserMixin):
            id    = 0
            email = config.ADMIN_EMAIL
            name  = 'Admin'
            role  = 'admin'
            is_admin = True
            def has_permission(self, _): return True
        u = _DevUser()
        u.id = int(user_id)
        return u
    from models import User
    return User.query.get(int(user_id))

if config.DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI']        = config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS']      = {
        'pool_pre_ping': True,   # test connection before use — fixes SSL drop errors
        'pool_recycle':  300,    # recycle connections every 5 min
    }

    db.init_app(app)
    migrate.init_app(app, db)

    # Register CLI commands
    from cli import create_admin, seed_roles, create_user, list_users, reset_password, seed_schedule, fix_driver_types
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_roles)
    app.cli.add_command(create_user)
    app.cli.add_command(list_users)
    app.cli.add_command(reset_password)
    app.cli.add_command(seed_schedule)
    app.cli.add_command(fix_driver_types)

    # ── Auto-migrate schedule columns added after initial deploy ──────────────
    # Runs once at startup; safe to re-run (checks columns before altering).
    def _auto_migrate_schedule():
        try:
            from sqlalchemy import inspect as _si, text as _st
            with app.app_context():
                insp = _si(db.engine)
                # ── ivan_schedule_assignments ─────────────────────────────────
                if insp.has_table('ivan_schedule_assignments'):
                    cols = {c['name'] for c in insp.get_columns('ivan_schedule_assignments')}
                    with db.engine.begin() as conn:
                        _adds = [
                            ('is_complete',       'BOOLEAN DEFAULT FALSE'),
                            ('appt_status',       "VARCHAR(20) DEFAULT 'NEED'"),
                            ('pu_location_name',  "VARCHAR(200) DEFAULT ''"),
                            ('de_location_name',  "VARCHAR(200) DEFAULT ''"),
                            ('driver_start_city', "VARCHAR(100) DEFAULT ''"),
                            ('driver_start_state',"VARCHAR(10)  DEFAULT ''"),
                            ('pu_appt_status',    "VARCHAR(20) DEFAULT 'NEED'"),
                            ('de_appt_status',    "VARCHAR(20) DEFAULT 'NEED'"),
                            ('completed_at',      'TIMESTAMP NULL'),
                            # Round 9
                            ('e2open_closed',     'BOOLEAN DEFAULT FALSE'),
                            ('pu_appt_type',      "VARCHAR(10) DEFAULT 'APPT'"),
                            ('pu_fcfs_start',     "VARCHAR(20) DEFAULT ''"),
                            ('pu_fcfs_end',       "VARCHAR(20) DEFAULT ''"),
                            ('de_appt_type',      "VARCHAR(10) DEFAULT 'APPT'"),
                            ('de_fcfs_start',     "VARCHAR(20) DEFAULT ''"),
                            ('de_fcfs_end',       "VARCHAR(20) DEFAULT ''"),
                        ]
                        for col, defn in _adds:
                            if col not in cols:
                                conn.execute(_st(
                                    f'ALTER TABLE ivan_schedule_assignments ADD COLUMN {col} {defn}'
                                ))
                # ── ivan_loads ───────────────────────────────────────────────
                if insp.has_table('ivan_loads'):
                    lcols = {c['name'] for c in insp.get_columns('ivan_loads')}
                    with db.engine.begin() as conn:
                        _ladd = [
                            ('pick_count',    'INTEGER DEFAULT 1'),
                            ('drop_count',    'INTEGER DEFAULT 1'),
                            ('load_type',     "VARCHAR(50)  DEFAULT ''"),
                            ('carrier_name',  "VARCHAR(200) DEFAULT ''"),
                            ('shipment_ref',  "VARCHAR(20)  DEFAULT ''"),
                            ('shipment_color',"VARCHAR(10)  DEFAULT ''"),
                        ]
                        for col, defn in _ladd:
                            if col not in lcols:
                                conn.execute(_st(
                                    f'ALTER TABLE ivan_loads ADD COLUMN {col} {defn}'
                                ))
        except Exception as _me:
            _log.warning('Schedule column auto-migrate skipped: %s', _me)

    _auto_migrate_schedule()

    # ── Auto-migrate new equipment / task / invoice columns ───────────────────
    def _auto_migrate_equipment():
        try:
            from sqlalchemy import inspect as _si, text as _st
            with app.app_context():
                insp = _si(db.engine)
                if insp.has_table('ivan_equipment'):
                    ecols = {c['name'] for c in insp.get_columns('ivan_equipment')}
                    with db.engine.begin() as conn:
                        for col, defn in [
                            ('ifta_expiration_date',      "VARCHAR(20) DEFAULT ''"),
                            ('irp_expiration_date',       "VARCHAR(20) DEFAULT ''"),
                            ('assigned_driver_id',        "VARCHAR(50) DEFAULT ''"),
                            ('insurance_expiration_date',  "VARCHAR(20) DEFAULT ''"),
                            ('bobtail_insurance_date',     "VARCHAR(20) DEFAULT ''"),
                            ('fleet_manager_assignee',     "VARCHAR(50) DEFAULT ''"),
                            ('on_tollway_account',         'BOOLEAN DEFAULT FALSE'),
                        ]:
                            if col not in ecols:
                                conn.execute(_st(
                                    f'ALTER TABLE ivan_equipment ADD COLUMN {col} {defn}'
                                ))
                if insp.has_table('ivan_tasks'):
                    tcols = {c['name'] for c in insp.get_columns('ivan_tasks')}
                    if 'assignee' not in tcols:
                        with db.engine.begin() as conn:
                            conn.execute(_st("ALTER TABLE ivan_tasks ADD COLUMN assignee VARCHAR(100) DEFAULT ''"))
                if insp.has_table('ivan_invoices'):
                    icols = {c['name'] for c in insp.get_columns('ivan_invoices')}
                    if 'assignee' not in icols:
                        with db.engine.begin() as conn:
                            conn.execute(_st("ALTER TABLE ivan_invoices ADD COLUMN assignee VARCHAR(100) DEFAULT ''"))
        except Exception as _me:
            _log.warning('Equipment column auto-migrate skipped: %s', _me)

    _auto_migrate_equipment()

    # Create audit log table if it doesn't exist (new table — db.create_all handles this)
    def _ensure_audit_table():
        try:
            from sqlalchemy import inspect as _si
            with app.app_context():
                if not _si(db.engine).has_table('schedule_audit_logs'):
                    db.create_all()
        except Exception as _ae:
            _log.warning('Audit table init skipped: %s', _ae)

    _ensure_audit_table()

    def _seed_dsp_drivers():
        """Seed Chad Salerno and Roy Workman on first run if table is empty."""
        try:
            from models import DspDriver
            with app.app_context():
                if DspDriver.query.count() == 0:
                    from extensions import db as _db
                    _db.session.add(DspDriver(
                        name='Chad Salerno', driver_type='company',
                        active=True, default_payout_pct=0.0, fuel_card_holder=True,
                    ))
                    _db.session.add(DspDriver(
                        name='Roy Workman', driver_type='owner_op',
                        active=True, default_payout_pct=88.0, fuel_card_holder=False,
                    ))
                    _db.session.commit()
        except Exception as _se:
            _log.warning('DSP driver seed skipped: %s', _se)

    _seed_dsp_drivers()

    def _ensure_report_tables():
        """Create report_job_runs / driver_report_runs tables if they don't exist yet."""
        try:
            from sqlalchemy import inspect as _si
            with app.app_context():
                if not _si(db.engine).has_table('report_job_runs'):
                    db.create_all()
                    _log.info('Report tables created (report_job_runs, driver_report_runs).')
        except Exception as _re:
            _log.warning('Report table init skipped: %s', _re)

    _ensure_report_tables()

    def _migrate_amazon_trips_schema():
        """Migrate amazon_trips to composite (trip_id, driver) unique key.
        Only drops relay_current_week if it has the wrong schema (missing driver column).
        Never wipes relay_current_week if it already has the correct schema."""
        try:
            from sqlalchemy import text as _text, inspect as _si
            with app.app_context():
                inspector = _si(db.engine)
                with db.engine.begin() as conn:
                    # Drop the old unique index created by unique=True on trip_id
                    conn.execute(_text(
                        "ALTER TABLE amazon_trips DROP CONSTRAINT IF EXISTS amazon_trips_trip_id_key"
                    ))
                    # Create composite unique index if it doesn't exist
                    conn.execute(_text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_amazon_trips_trip_driver "
                        "ON amazon_trips(trip_id, driver) WHERE trip_id IS NOT NULL"
                    ))
                    # Only drop relay_current_week if driver column is missing (wrong schema).
                    # If it already has the right schema, leave it alone — don't wipe data.
                    if inspector.has_table('relay_current_week'):
                        cols = {c['name'] for c in inspector.get_columns('relay_current_week')}
                        if 'driver' not in cols:
                            conn.execute(_text("DROP TABLE relay_current_week"))
                            _log.info("relay_current_week dropped for schema upgrade.")
                db.create_all()
                _log.info("amazon_trips schema migration complete.")
        except Exception as _me:
            _log.warning("amazon_trips schema migration skipped: %s", _me)

    _migrate_amazon_trips_schema()

_DB_ENABLED = bool(config.DATABASE_URL)

finance_agent    = FinanceAgent()
marketing_agent  = MarketingAgent()
coordinator      = CoordinatorAgent()

# Explicit registration ensures all agents appear in /api/health and /api/agents
agent_registry.register("Dashboard",         "Flask web dashboard — serves finance data and agent status")
agent_registry.register("FinanceAgent",      "Financial data ingestion and metrics (Ivan Cartage, brokerage, Amazon)")
agent_registry.register("MarketingAgent",    "Marketing intelligence and campaign analysis")
agent_registry.register("CoordinatorAgent",  "Message routing and agent orchestration")


# ── Auth routes (public) ──────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute', error_message='Too many login attempts. Try again in a minute.')
def login():
    from flask_login import current_user, login_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    error = None
    email = ''

    if request.method == 'POST':
        email    = (request.form.get('email')    or '').strip()
        password = (request.form.get('password') or '').strip()

        if _DB_ENABLED:
            from models import User as UserModel
            from extensions import bcrypt as _bcrypt
            user = UserModel.query.filter_by(email=email.lower(), is_active=True).first()
            if user and _bcrypt.check_password_hash(user.password_hash, password):
                from datetime import datetime
                user.last_login_at = datetime.utcnow()
                from extensions import db as _db
                _db.session.commit()
                login_user(user, remember=True)
                next_url = request.form.get('next') or '/'
                if not next_url.startswith('/'):
                    next_url = '/'
                return redirect(next_url)
            error = 'Invalid email or password.'
        else:
            # Fallback: env-var auth for local dev (no DB)
            from werkzeug.security import check_password_hash
            from flask_login import UserMixin
            stored_email = (config.ADMIN_EMAIL or '').strip().lower()
            stored_hash  = (config.ADMIN_PASSWORD_HASH or '').strip()
            if (email.lower() == stored_email
                    and stored_hash
                    and check_password_hash(stored_hash, password)):
                # Create a minimal user so Flask-Login's current_user works
                class _DevUser(UserMixin):
                    id    = 0
                    email = stored_email
                    name  = 'Admin'
                    role  = 'admin'
                    is_admin = True
                    def has_permission(self, _): return True
                login_user(_DevUser(), remember=True)
                next_url = request.form.get('next') or '/'
                if not next_url.startswith('/'):
                    next_url = '/'
                return redirect(next_url)
            error = 'Invalid email or password.'

    return render_template('login.html', error=error, email=email,
                           next=request.args.get('next', ''))


@app.route('/logout', methods=['POST'])
def logout():
    from flask_login import logout_user
    from flask import session as _session
    logout_user()
    _session.clear()
    response = redirect(url_for('login'))
    response.delete_cookie('remember_token')
    return response


# ── Protected dashboard ───────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/domain-map')
@login_required
def domain_map():
    return render_template('domain_map.html')


# ── Admin panel ───────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_panel():
    if not _DB_ENABLED:
        return 'Admin panel requires database. Set DATABASE_URL.', 503
    from flask_login import current_user
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    from models import User, Role
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.all()
    return render_template('admin.html', users=users, roles=roles)


@app.route('/api/admin/users', methods=['GET'])
@login_required
def api_admin_users():
    if not _DB_ENABLED:
        return jsonify({'error': 'No database'}), 503
    from flask_login import current_user
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from models import User
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        'id':           u.id,
        'email':        u.email,
        'name':         u.name,
        'is_active':    u.is_active,
        'roles':        u.role_names,
        'last_login':   u.last_login_at.isoformat() if u.last_login_at else None,
        'created_at':   u.created_at.isoformat()
    } for u in users])


@app.route('/api/admin/users', methods=['POST'])
@login_required
def api_admin_create_user():
    if not _DB_ENABLED:
        return jsonify({'error': 'No database'}), 503
    from flask_login import current_user
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from models import User, Role
    from extensions import bcrypt as _bcrypt, db as _db

    data     = request.get_json() or {}
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()
    name     = (data.get('name')     or '').strip()
    role_names = data.get('roles', ['viewer'])

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    pw_hash = _bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=pw_hash,
                name=name or email.split('@')[0], is_active=True)

    for rname in role_names:
        role = Role.query.filter_by(name=rname).first()
        if role:
            user.roles.append(role)

    _db.session.add(user)
    _db.session.commit()
    return jsonify({'id': user.id, 'email': user.email, 'roles': user.role_names}), 201


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@login_required
def api_admin_update_user(user_id):
    if not _DB_ENABLED:
        return jsonify({'error': 'No database'}), 503
    from flask_login import current_user
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from models import User, Role
    from extensions import bcrypt as _bcrypt, db as _db

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'name'      in data: user.name      = data['name']
    if 'is_active' in data: user.is_active = bool(data['is_active'])
    if 'password'  in data and data['password']:
        user.password_hash = _bcrypt.generate_password_hash(data['password']).decode('utf-8')
    if 'roles'     in data:
        user.roles = [r for r in
                      [Role.query.filter_by(name=rn).first() for rn in data['roles']]
                      if r]

    _db.session.commit()
    return jsonify({'id': user.id, 'email': user.email, 'roles': user.role_names})


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_admin_delete_user(user_id):
    if not _DB_ENABLED:
        return jsonify({'error': 'No database'}), 503
    from flask_login import current_user
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from models import User
    from extensions import db as _db

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    _db.session.delete(user)
    _db.session.commit()
    return jsonify({'deleted': user_id})


@app.route('/api/me')
@login_required
def api_me():
    """Return current user's identity and permissions for the frontend."""
    if _DB_ENABLED:
        from flask_login import current_user
        return jsonify(current_user.permissions_for_frontend())
    # Legacy no-DB mode: return full admin access
    from flask import session as _session
    return jsonify({
        'is_admin': True,
        'name':     _session.get('user_email', 'Admin'),
        'email':    _session.get('user_email', ''),
        'companies': ['bcat', 'ivan', 'bestcare', 'amazon', 'aiden', 'agents'],
        'tabs': {}
    })


@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard_api():
    finance_agent.ingest_data()

    ivan_metrics = get_ivan_expense_metrics()
    brokerage_metrics = finance_agent.calculate_brokerage_metrics()

    monthly_brokerage_summary = finance_agent.get_monthly_brokerage_summary()
    brokerage_top_customers_by_month = finance_agent.get_brokerage_top_customers_by_month()
    ivan_top_customers_by_month = finance_agent.get_ivan_top_customers_by_month()
    amazon_metrics = finance_agent.get_amazon_metrics()

    total_company_revenue = (
        float(ivan_metrics.get('ivan_cartage_revenue', 0)) +
        float(brokerage_metrics.get('gross_revenue', 0)) +
        float(amazon_metrics.get('total_bcat_revenue', 0))
    )

    return jsonify({
        'report_start_date': '2026-01-01',
        'report_end_date': '2026-03-04',
        'total_company_revenue': total_company_revenue,
        'amazon': amazon_metrics,
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

    # Agent status from registry
    registered_agents = {a['name']: a['status'] for a in agent_registry.get_all()}

    # Quick data-layer smoke test
    data_ok = False
    data_error = None
    try:
        finance_agent.ingest_data()
        m = finance_agent.calculate_brokerage_metrics()
        data_ok = m.get('gross_revenue', 0) >= 0
    except Exception as exc:
        data_error = str(exc)

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
        'agents': {
            'finance_agent':     registered_agents.get('FinanceAgent',     'not registered'),
            'marketing_agent':   registered_agents.get('MarketingAgent',   'not registered'),
            'coordinator_agent': registered_agents.get('CoordinatorAgent', 'not registered'),
            'dashboard':         registered_agents.get('Dashboard',        'not registered'),
        },
        'bots': {
            'discord':  {'running': _thread_alive('discord-bot'),  'token_set': _env('DISCORD_BOT_TOKEN')},
            'telegram': {'running': _thread_alive('telegram-bot'), 'token_set': _env('TELEGRAM_BOT_TOKEN')},
        },
        'data': {
            'layer_ok':           data_ok,
            'layer_error':        data_error,
            'brokerage_loads':    _csv('brokerage_loads.csv'),
            'ivan_cartage_loads': _csv('ivan_cartage_loads.csv'),
            'ivan_expenses':      _csv('ivan_expenses.csv'),
            'amazon_loads':       _csv('amazon_loads.csv'),
        },
        'services': {
            'best_care': _BC_AVAILABLE,
        },
    }
    return jsonify(status)


# ── Ivan Cartage Equipment API ────────────────────────────────────────────────

@app.route('/api/ivan/equipment', methods=['GET'])
@login_required
def ivan_equipment_list():
    from models import IvanEquipment
    items = IvanEquipment.query.order_by(IvanEquipment.unit_number).all()
    return jsonify([e.to_dict() for e in items])

@app.route('/api/ivan/equipment', methods=['POST'])
@login_required
def ivan_equipment_create():
    from models import IvanEquipment
    from extensions import db as _db
    d = request.get_json()
    e = IvanEquipment(
        id=d['id'], type=d.get('type','truck'), unit_number=d.get('unitNumber',''),
        nickname=d.get('nickname',''), vin=d.get('vin',''), plate=d.get('plate',''),
        make=d.get('make',''), model=d.get('model',''), year=d.get('year'),
        mileage=d.get('mileage'), ownership=d.get('ownership','owned'),
        insured=d.get('insured', True), dot_inspection_date=d.get('dotInspectionDate',''),
        ifta_expiration_date=d.get('iftaExpirationDate',''),
        irp_expiration_date=d.get('irpExpirationDate',''),
        assigned_driver_id=d.get('assignedDriverId',''),
        insurance_expiration_date=d.get('insuranceExpirationDate',''),
        fleet_manager_assignee=d.get('fleetManagerAssignee',''),
        on_tollway_account=d.get('onTollwayAccount', False),
        active=d.get('active', True), notes=d.get('notes','')
    )
    _db.session.add(e)
    _db.session.commit()
    return jsonify(e.to_dict()), 201

@app.route('/api/ivan/equipment/<eid>', methods=['PUT'])
@login_required
def ivan_equipment_update(eid):
    from models import IvanEquipment
    from extensions import db as _db
    e = IvanEquipment.query.get_or_404(eid)
    d = request.get_json()
    e.type=d.get('type', e.type); e.unit_number=d.get('unitNumber', e.unit_number)
    e.nickname=d.get('nickname', e.nickname); e.vin=d.get('vin', e.vin)
    e.plate=d.get('plate', e.plate); e.make=d.get('make', e.make)
    e.model=d.get('model', e.model); e.year=d.get('year', e.year)
    e.mileage=d.get('mileage', e.mileage); e.ownership=d.get('ownership', e.ownership)
    e.insured=d.get('insured', e.insured)
    e.dot_inspection_date=d.get('dotInspectionDate', e.dot_inspection_date)
    e.ifta_expiration_date=d.get('iftaExpirationDate', e.ifta_expiration_date)
    e.irp_expiration_date=d.get('irpExpirationDate', e.irp_expiration_date)
    e.assigned_driver_id=d.get('assignedDriverId', e.assigned_driver_id)
    e.insurance_expiration_date=d.get('insuranceExpirationDate', e.insurance_expiration_date)
    e.bobtail_insurance_date=d.get('bobtailInsuranceDate', e.bobtail_insurance_date)
    e.fleet_manager_assignee=d.get('fleetManagerAssignee', e.fleet_manager_assignee)
    e.on_tollway_account=d.get('onTollwayAccount', e.on_tollway_account)
    e.active=d.get('active', e.active); e.notes=d.get('notes', e.notes)
    _db.session.commit()
    return jsonify(e.to_dict())

@app.route('/api/ivan/equipment/<eid>', methods=['DELETE'])
@login_required
def ivan_equipment_delete(eid):
    from models import IvanEquipment
    from extensions import db as _db
    e = IvanEquipment.query.get_or_404(eid)
    _db.session.delete(e)
    _db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/ivan/tasks', methods=['GET'])
@login_required
def ivan_tasks_list():
    from models import IvanTask
    items = IvanTask.query.order_by(IvanTask.due_date).all()
    return jsonify([t.to_dict() for t in items])

@app.route('/api/ivan/tasks', methods=['POST'])
@login_required
def ivan_task_create():
    from models import IvanTask
    from extensions import db as _db
    d = request.get_json()
    t = IvanTask(
        id=d['id'], equip_id=d['equipId'], title=d.get('title',''),
        due_date=d.get('dueDate',''), priority=d.get('priority','med'),
        status=d.get('status','upcoming'), notes=d.get('notes',''),
        auto_dot=d.get('autoDot', False), assignee=d.get('assignee','')
    )
    _db.session.add(t)
    _db.session.commit()
    return jsonify(t.to_dict()), 201

@app.route('/api/ivan/tasks/<tid>', methods=['PUT'])
@login_required
def ivan_task_update(tid):
    from models import IvanTask
    from extensions import db as _db
    t = IvanTask.query.get_or_404(tid)
    d = request.get_json()
    t.title=d.get('title', t.title); t.due_date=d.get('dueDate', t.due_date)
    t.priority=d.get('priority', t.priority); t.status=d.get('status', t.status)
    t.notes=d.get('notes', t.notes); t.auto_dot=d.get('autoDot', t.auto_dot)
    t.assignee=d.get('assignee', t.assignee)
    _db.session.commit()
    return jsonify(t.to_dict())

@app.route('/api/ivan/tasks/<tid>', methods=['DELETE'])
@login_required
def ivan_task_delete(tid):
    from models import IvanTask
    from extensions import db as _db
    t = IvanTask.query.get_or_404(tid)
    _db.session.delete(t)
    _db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/ivan/invoices', methods=['GET'])
@login_required
def ivan_invoices_list():
    from models import IvanInvoice
    items = IvanInvoice.query.order_by(IvanInvoice.date.desc()).all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/ivan/invoices', methods=['POST'])
@login_required
def ivan_invoice_create():
    from models import IvanInvoice
    from extensions import db as _db
    d = request.get_json()
    inv = IvanInvoice(
        id=d['id'], equip_id=d['equipId'], date=d.get('date',''),
        vendor=d.get('vendor',''), description=d.get('description',''),
        amount=d.get('amount', 0), invoice_number=d.get('invoiceNumber',''),
        payment_method=d.get('paymentMethod',''), payment_date=d.get('paymentDate',''),
        assignee=d.get('assignee','')
    )
    _db.session.add(inv)
    _db.session.commit()
    return jsonify(inv.to_dict()), 201

@app.route('/api/ivan/invoices/<iid>', methods=['PUT'])
@login_required
def ivan_invoice_update(iid):
    from models import IvanInvoice
    from extensions import db as _db
    inv = IvanInvoice.query.get_or_404(iid)
    d = request.get_json()
    inv.date=d.get('date', inv.date); inv.vendor=d.get('vendor', inv.vendor)
    inv.description=d.get('description', inv.description)
    inv.amount=d.get('amount', inv.amount)
    inv.invoice_number=d.get('invoiceNumber', inv.invoice_number)
    inv.payment_method=d.get('paymentMethod', inv.payment_method)
    inv.payment_date=d.get('paymentDate', inv.payment_date)
    inv.assignee=d.get('assignee', inv.assignee)
    _db.session.commit()
    return jsonify(inv.to_dict())

@app.route('/api/ivan/invoices/<iid>', methods=['DELETE'])
@login_required
def ivan_invoice_delete(iid):
    from models import IvanInvoice
    from extensions import db as _db
    inv = IvanInvoice.query.get_or_404(iid)
    _db.session.delete(inv)
    _db.session.commit()
    return jsonify({'ok': True})


# ── Ivan Cartage — Dispatch Schedule (Load + Assignment model) ─────────────────

# ── Audit log helper ───────────────────────────────────────────────────────────

def _write_audit(entity_type, entity_id, action, before=None, after=None, summary=''):
    """Write one audit log record. Safe to call — never raises."""
    try:
        from flask_login import current_user as _cu
        from models import ScheduleAuditLog
        from extensions import db as _db
        import json
        record = ScheduleAuditLog(
            entity_type = entity_type,
            entity_id   = str(entity_id),
            action      = action,
            user_email  = getattr(_cu, 'email', '') or '',
            user_name   = getattr(_cu, 'name',  '') or '',
            before_json = json.dumps(before or {}),
            after_json  = json.dumps(after  or {}),
            summary     = (summary or '')[:500],
        )
        _db.session.add(record)
        _db.session.commit()
    except Exception as _ae:
        _log.warning('Audit write failed: %s', _ae)

def _asgn_summary(d):
    """Build a short human-readable summary from an assignment dict."""
    parts = []
    load = d.get('load') or {}
    pro = load.get('alexeiId') or ''
    if pro: parts.append('PRO ' + pro)
    drv = d.get('driverName') or ''
    if drv: parts.append(drv)
    dt = d.get('date') or ''
    if dt: parts.append(dt)
    act = d.get('actionType') or ''
    if act: parts.append(act)
    return ' — '.join(parts) if parts else (d.get('id') or '')

@app.route('/api/ivan/schedule', methods=['GET'])
@login_required
def ivan_schedule_list():
    """Return assignments for a week plus all loads for the dropdown.
    Query param: weekStart=YYYY-MM-DD (Monday)
    """
    from models import IvanScheduleAssignment, IvanLoad
    week_start = request.args.get('weekStart', '')
    if not week_start:
        return jsonify({'assignments': [], 'loads': []})
    assignments = (IvanScheduleAssignment.query
                   .filter_by(week_start=week_start)
                   .order_by(IvanScheduleAssignment.date,
                              IvanScheduleAssignment.driver_name,
                              IvanScheduleAssignment.sequence_number)
                   .all())
    loads = IvanLoad.query.order_by(IvanLoad.created_at.desc()).all()
    return jsonify({
        'assignments': [a.to_dict() for a in assignments],
        'loads':       [l.to_dict() for l in loads],
    })


@app.route('/api/ivan/loads', methods=['GET'])
@login_required
def ivan_loads_list():
    from models import IvanLoad
    loads = IvanLoad.query.order_by(IvanLoad.created_at.desc()).all()
    return jsonify([l.to_dict() for l in loads])


@app.route('/api/ivan/loads', methods=['POST'])
@login_required
def ivan_load_create():
    import uuid as _uuid
    from models import IvanLoad
    from extensions import db as _db
    d = request.get_json() or {}
    raw_id = d.get('id') or ('load-' + _uuid.uuid4().hex[:8])
    # Auto-generate a short human-readable shipment ref if not provided
    short = raw_id[-5:].upper()
    auto_ref = 'S-' + short
    load = IvanLoad(
        id             = raw_id,
        alexei_id      = d.get('alexeiId', ''),
        tms_id         = d.get('tmsId', ''),
        pu_number      = d.get('puNumber', ''),
        pu_city        = d.get('puCity', ''),
        pu_state       = (d.get('puState') or '').upper(),
        de_city        = d.get('deCity', ''),
        de_state       = (d.get('deState') or '').upper(),
        pu_appt        = d.get('puAppt', ''),
        de_appt        = d.get('deAppt', ''),
        notes          = d.get('notes', ''),
        pick_count     = int(d.get('pickCount', 1) or 1),
        drop_count     = int(d.get('dropCount', 1) or 1),
        load_type      = d.get('loadType', ''),
        carrier_name   = d.get('carrierName', ''),
        shipment_ref   = d.get('shipmentRef', '') or auto_ref,
        shipment_color = d.get('shipmentColor', '') or '',
    )
    _db.session.add(load)
    _db.session.commit()
    return jsonify(load.to_dict()), 201


@app.route('/api/ivan/loads/<lid>', methods=['PUT'])
@login_required
def ivan_load_update(lid):
    from models import IvanLoad
    from extensions import db as _db
    load = IvanLoad.query.get_or_404(lid)
    d = request.get_json() or {}
    if 'alexeiId'    in d: load.alexei_id    = d['alexeiId']
    if 'tmsId'       in d: load.tms_id       = d['tmsId']
    if 'puNumber'    in d: load.pu_number    = d['puNumber']
    if 'puCity'      in d: load.pu_city      = d['puCity']
    if 'puState'     in d: load.pu_state     = (d['puState'] or '').upper()
    if 'deCity'      in d: load.de_city      = d['deCity']
    if 'deState'     in d: load.de_state     = (d['deState'] or '').upper()
    if 'puAppt'      in d: load.pu_appt      = d['puAppt']
    if 'deAppt'      in d: load.de_appt      = d['deAppt']
    if 'notes'       in d: load.notes        = d['notes']
    if 'pickCount'     in d: load.pick_count     = int(d['pickCount']   or 1)
    if 'dropCount'     in d: load.drop_count     = int(d['dropCount']   or 1)
    if 'loadType'      in d: load.load_type      = d['loadType']      or ''
    if 'carrierName'   in d: load.carrier_name   = d['carrierName']   or ''
    if 'shipmentRef'   in d: load.shipment_ref   = d['shipmentRef']   or ''
    if 'shipmentColor' in d: load.shipment_color = d['shipmentColor'] or ''
    _db.session.commit()
    return jsonify(load.to_dict())


@app.route('/api/ivan/loads/<lid>', methods=['DELETE'])
@login_required
def ivan_load_delete(lid):
    from models import IvanLoad
    from extensions import db as _db
    load = IvanLoad.query.get_or_404(lid)
    _db.session.delete(load)
    _db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/ivan/schedule/assignments', methods=['POST'])
@login_required
def ivan_assignment_create():
    import uuid as _uuid
    from models import IvanScheduleAssignment
    from extensions import db as _db
    d = request.get_json() or {}
    a = IvanScheduleAssignment(
        id               = d.get('id') or ('asgn-' + _uuid.uuid4().hex[:8]),
        load_id          = d.get('loadId') or None,
        week_start       = d['weekStart'],
        date             = d['date'],
        driver_name      = d.get('driverName', ''),
        sequence_number  = int(d.get('sequenceNumber', 1)),
        action_type      = d.get('actionType', 'PICKUP'),
        origin_city      = d.get('originCity', ''),
        origin_state     = (d.get('originState') or '').upper(),
        dest_city        = d.get('destCity', ''),
        dest_state       = (d.get('destState') or '').upper(),
        pu_appt          = d.get('puAppt', ''),
        de_appt          = d.get('deAppt', ''),
        pu_location_name = d.get('puLocationName', ''),
        de_location_name = d.get('deLocationName', ''),
        pu_appt_status   = d.get('puApptStatus', 'NEED'),
        de_appt_status   = d.get('deApptStatus', 'NEED'),
        notes            = d.get('notes', ''),
        # Round 9
        e2open_closed    = bool(d.get('e2openClosed', False)),
        pu_appt_type     = d.get('puApptType', 'APPT') or 'APPT',
        pu_fcfs_start    = d.get('puFcfsStart', ''),
        pu_fcfs_end      = d.get('puFcfsEnd', ''),
        de_appt_type     = d.get('deApptType', 'APPT') or 'APPT',
        de_fcfs_start    = d.get('deFcfsStart', ''),
        de_fcfs_end      = d.get('deFcfsEnd', ''),
    )
    _db.session.add(a)
    _db.session.commit()
    after = a.to_dict()
    _write_audit('assignment', a.id, 'create', before={}, after=after,
                 summary='Created ' + _asgn_summary(after))
    return jsonify(after), 201


@app.route('/api/ivan/schedule/assignments/<aid>', methods=['PUT'])
@login_required
def ivan_assignment_update(aid):
    from models import IvanScheduleAssignment
    from extensions import db as _db
    a = IvanScheduleAssignment.query.get_or_404(aid)
    before = a.to_dict()
    d = request.get_json() or {}
    if 'loadId'         in d: a.load_id        = d['loadId'] or None
    if 'date'           in d: a.date            = d['date']
    if 'weekStart'      in d: a.week_start      = d['weekStart']
    if 'driverName'     in d: a.driver_name     = d['driverName']
    if 'sequenceNumber' in d: a.sequence_number = int(d['sequenceNumber'])
    if 'actionType'     in d: a.action_type     = d['actionType']
    if 'originCity'     in d: a.origin_city     = d['originCity']
    if 'originState'    in d: a.origin_state    = (d['originState'] or '').upper()
    if 'destCity'       in d: a.dest_city       = d['destCity']
    if 'destState'      in d: a.dest_state      = (d['destState'] or '').upper()
    if 'puAppt'         in d: a.pu_appt         = d['puAppt']
    if 'deAppt'         in d: a.de_appt         = d['deAppt']
    if 'notes'          in d: a.notes           = d['notes']
    if 'puLocationName' in d: a.pu_location_name = d['puLocationName']
    if 'deLocationName' in d: a.de_location_name = d['deLocationName']
    if 'puApptStatus'   in d: a.pu_appt_status  = d['puApptStatus']
    if 'deApptStatus'   in d: a.de_appt_status  = d['deApptStatus']
    if 'isComplete' in d:
        a.is_complete = bool(d['isComplete'])
        if a.is_complete and not a.completed_at:
            from datetime import datetime as _dt
            a.completed_at = _dt.utcnow()
        elif not a.is_complete:
            a.completed_at = None
    # Round 9
    if 'e2openClosed' in d: a.e2open_closed = bool(d['e2openClosed'])
    if 'puApptType'   in d: a.pu_appt_type  = d['puApptType'] or 'APPT'
    if 'puFcfsStart'  in d: a.pu_fcfs_start = d['puFcfsStart'] or ''
    if 'puFcfsEnd'    in d: a.pu_fcfs_end   = d['puFcfsEnd']   or ''
    if 'deApptType'   in d: a.de_appt_type  = d['deApptType'] or 'APPT'
    if 'deFcfsStart'  in d: a.de_fcfs_start = d['deFcfsStart'] or ''
    if 'deFcfsEnd'    in d: a.de_fcfs_end   = d['deFcfsEnd']   or ''
    _db.session.commit()
    after = a.to_dict()
    _write_audit('assignment', a.id, 'update', before=before, after=after,
                 summary='Updated ' + _asgn_summary(after))
    return jsonify(after)


@app.route('/api/ivan/schedule/assignments/<aid>', methods=['DELETE'])
@login_required
def ivan_assignment_delete(aid):
    from models import IvanScheduleAssignment
    from extensions import db as _db
    a = IvanScheduleAssignment.query.get_or_404(aid)
    before = a.to_dict()
    _db.session.delete(a)
    _db.session.commit()
    _write_audit('assignment', aid, 'delete', before=before, after={},
                 summary='Deleted ' + _asgn_summary(before))
    return jsonify({'ok': True})


# ── Audit log API ──────────────────────────────────────────────────────────────

@app.route('/api/ivan/schedule/audit', methods=['GET'])
@login_required
def ivan_schedule_audit():
    from models import ScheduleAuditLog
    limit = min(int(request.args.get('limit', 50)), 200)
    logs = (ScheduleAuditLog.query
            .order_by(ScheduleAuditLog.created_at.desc())
            .limit(limit).all())
    return jsonify([l.to_dict() for l in logs])


@app.route('/api/ivan/schedule/audit/<int:log_id>/revert', methods=['POST'])
@login_required
def ivan_schedule_audit_revert(log_id):
    """Revert a logged change back to its before state."""
    from models import ScheduleAuditLog, IvanScheduleAssignment, IvanLoad
    from extensions import db as _db
    import json

    record = ScheduleAuditLog.query.get_or_404(log_id)
    if record.reverted:
        return jsonify({'error': 'Already reverted'}), 400

    before = json.loads(record.before_json or '{}')
    after  = json.loads(record.after_json  or '{}')

    try:
        if record.entity_type == 'assignment':
            if record.action == 'update':
                a = IvanScheduleAssignment.query.get_or_404(record.entity_id)
                # Restore before state
                for col, attr in [
                    ('driverName','driver_name'), ('sequenceNumber','sequence_number'),
                    ('actionType','action_type'), ('originCity','origin_city'),
                    ('originState','origin_state'), ('destCity','dest_city'),
                    ('destState','dest_state'), ('puAppt','pu_appt'), ('deAppt','de_appt'),
                    ('puLocationName','pu_location_name'), ('deLocationName','de_location_name'),
                    ('puApptStatus','pu_appt_status'), ('deApptStatus','de_appt_status'),
                    ('notes','notes'), ('isComplete','is_complete'),
                    ('e2openClosed','e2open_closed'), ('puApptType','pu_appt_type'),
                    ('puFcfsStart','pu_fcfs_start'), ('puFcfsEnd','pu_fcfs_end'),
                    ('deApptType','de_appt_type'), ('deFcfsStart','de_fcfs_start'),
                    ('deFcfsEnd','de_fcfs_end'),
                ]:
                    if col in before:
                        setattr(a, attr, before[col])
                _db.session.commit()

            elif record.action == 'create':
                a = IvanScheduleAssignment.query.get(record.entity_id)
                if a:
                    _db.session.delete(a)
                    _db.session.commit()

            elif record.action == 'delete':
                if not IvanScheduleAssignment.query.get(before.get('id')):
                    a = IvanScheduleAssignment(
                        id               = before.get('id', 'asgn-reverted'),
                        load_id          = before.get('loadId') or None,
                        week_start       = before.get('weekStart', ''),
                        date             = before.get('date', ''),
                        driver_name      = before.get('driverName', ''),
                        sequence_number  = before.get('sequenceNumber', 1),
                        action_type      = before.get('actionType', 'PICKUP'),
                        origin_city      = before.get('originCity', ''),
                        origin_state     = before.get('originState', ''),
                        dest_city        = before.get('destCity', ''),
                        dest_state       = before.get('destState', ''),
                        pu_appt          = before.get('puAppt', ''),
                        de_appt          = before.get('deAppt', ''),
                        pu_location_name = before.get('puLocationName', ''),
                        de_location_name = before.get('deLocationName', ''),
                        pu_appt_status   = before.get('puApptStatus', 'NEED'),
                        de_appt_status   = before.get('deApptStatus', 'NEED'),
                        notes            = before.get('notes', ''),
                        is_complete      = before.get('isComplete', False),
                        e2open_closed    = before.get('e2openClosed', False),
                        pu_appt_type     = before.get('puApptType', 'APPT') or 'APPT',
                        pu_fcfs_start    = before.get('puFcfsStart', ''),
                        pu_fcfs_end      = before.get('puFcfsEnd', ''),
                        de_appt_type     = before.get('deApptType', 'APPT') or 'APPT',
                        de_fcfs_start    = before.get('deFcfsStart', ''),
                        de_fcfs_end      = before.get('deFcfsEnd', ''),
                    )
                    _db.session.add(a)
                    _db.session.commit()

    except Exception as _re:
        _log.warning('Audit revert error: %s', _re)
        return jsonify({'error': str(_re)}), 500

    record.reverted = True
    _db.session.commit()
    _write_audit(record.entity_type, record.entity_id, 'revert',
                 before=after, after=before,
                 summary='Reverted: ' + (record.summary or record.entity_id))
    return jsonify({'ok': True})


@app.route('/api/ivan/schedule/driver-day', methods=['GET'])
@login_required
def ivan_schedule_driver_day():
    """Return all assignments for a specific driver on a specific date.
    Query params: driver=Name&date=YYYY-MM-DD
    """
    from models import IvanScheduleAssignment
    driver = request.args.get('driver', '').strip()
    date   = request.args.get('date', '').strip()
    if not driver or not date:
        return jsonify([])
    assignments = (IvanScheduleAssignment.query
                   .filter_by(date=date, driver_name=driver)
                   .order_by(IvanScheduleAssignment.sequence_number)
                   .all())
    return jsonify([a.to_dict() for a in assignments])


@app.route('/api/ivan/schedule/shipments/<lid>/move', methods=['POST'])
@login_required
def ivan_shipment_move(lid):
    """Move all assignment legs for a load by offsetDays days.
    Body: { offsetDays: <int> }
    Preserves relative gaps between legs.
    """
    from models import IvanLoad, IvanScheduleAssignment
    from extensions import db as _db
    from datetime import date as _date, timedelta as _td
    import json

    load = IvanLoad.query.get_or_404(lid)
    d = request.get_json() or {}
    offset = int(d.get('offsetDays', 0))
    if offset == 0:
        return jsonify({'ok': True, 'moved': 0})

    assignments = IvanScheduleAssignment.query.filter_by(load_id=lid).all()
    moved = 0
    for a in assignments:
        try:
            old_dt = _date.fromisoformat(a.date)
            new_dt = old_dt + _td(days=offset)
            new_date = new_dt.isoformat()
            # Recalculate weekStart (Monday of new date)
            wd = new_dt.weekday()  # Mon=0
            mon = new_dt - _td(days=wd)
            new_week = mon.isoformat()
            before = a.to_dict()
            a.date = new_date
            a.week_start = new_week
            _db.session.commit()
            after = a.to_dict()
            _write_audit('assignment', a.id, 'update', before=before, after=after,
                         summary=f'Moved (shipment {load.shipment_ref or lid}) {before["date"]} → {new_date}')
            moved += 1
        except Exception as _me:
            _log.warning('Move leg error: %s', _me)

    return jsonify({'ok': True, 'moved': moved})


@app.route('/api/amazon/status')
@login_required
def amazon_status():
    """Debug endpoint — shows Amazon data source and DB table status."""
    result = {
        'db_enabled': _DB_ENABLED,
        'data_source': 'unknown',
        'trip_count': 0,
        'unique_drivers': [],
        'unique_weeks': [],
        'last_uploaded': None,
        'table_exists': False,
    }
    if _DB_ENABLED:
        try:
            from models import AmazonTrip
            from extensions import db as _db
            rows = AmazonTrip.query.order_by(AmazonTrip.uploaded_at.desc()).all()
            result['table_exists'] = True
            result['trip_count'] = len(rows)
            result['unique_drivers'] = sorted({r.driver for r in rows if r.driver})
            result['unique_weeks'] = sorted({r.trip_date[:7] for r in rows if r.trip_date})
            result['last_uploaded'] = rows[0].uploaded_at.isoformat() if rows else None
            result['data_source'] = 'database' if rows else 'mock (db empty)'
        except Exception as e:
            result['data_source'] = f'error: {e}'
    else:
        import os
        relay_path = 'amazon_relay.csv'
        result['data_source'] = 'relay_csv' if os.path.exists(relay_path) else 'mock'
    return jsonify(result)


@app.route('/ivan/export')
@login_required
def ivan_export_page():
    return '''<!DOCTYPE html><html><head><title>Ivan Export</title></head><body>
<h2>Exporting Ivan data from localStorage...</h2>
<script>
var data = {
  equipment: JSON.parse(localStorage.getItem("ivan_equipment") || "[]"),
  tasks: JSON.parse(localStorage.getItem("ivan_tasks") || "[]"),
  invoices: JSON.parse(localStorage.getItem("ivan_invoices") || "[]")
};
var blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
var a = document.createElement("a");
a.href = URL.createObjectURL(blob);
a.download = "ivan_export.json";
document.body.appendChild(a);
a.click();
document.body.innerHTML += "<p>Done! File downloaded. Now upload it on Railway at <b>/ivan/import-page</b></p>";
</script>
</body></html>'''


@app.route('/ivan/import-page')
@login_required
def ivan_import_page():
    return '''<!DOCTYPE html><html><head><title>Ivan Import</title></head><body>
<h2>Import Ivan Data</h2>
<form id="f">
  <input type="file" id="file" accept=".json"><br><br>
  <button type="submit">Import</button>
</form>
<pre id="result"></pre>
<script>
document.getElementById("f").onsubmit = function(e) {
  e.preventDefault();
  var reader = new FileReader();
  reader.onload = function(ev) {
    fetch("/api/ivan/import", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: ev.target.result
    }).then(function(r){ return r.json(); }).then(function(d){
      document.getElementById("result").textContent = JSON.stringify(d, null, 2);
    });
  };
  reader.readAsText(document.getElementById("file").files[0]);
};
</script>
</body></html>'''


@app.route('/api/ivan/import', methods=['POST'])
@csrf.exempt
@login_required
def ivan_import():
    """One-time bulk import endpoint. Skips records that already exist."""
    from models import IvanEquipment, IvanTask, IvanInvoice
    from extensions import db as _db
    d = request.get_json()
    imported = {'equipment': 0, 'tasks': 0, 'invoices': 0}
    for e in d.get('equipment', []):
        if not IvanEquipment.query.get(e['id']):
            _db.session.add(IvanEquipment(
                id=e['id'], type=e.get('type','truck'), unit_number=e.get('unitNumber',''),
                nickname=e.get('nickname',''), vin=e.get('vin',''), plate=e.get('plate',''),
                make=e.get('make',''), model=e.get('model',''), year=e.get('year'),
                mileage=e.get('mileage'), ownership=e.get('ownership','owned'),
                insured=e.get('insured', True), dot_inspection_date=e.get('dotInspectionDate',''),
                active=e.get('active', True), notes=e.get('notes','')
            ))
            imported['equipment'] += 1
    for t in d.get('tasks', []):
        tid = t.get('id') or t.get('maintenanceTaskId')
        eid = t.get('equipId') or t.get('equipmentId')
        if tid and eid and IvanEquipment.query.get(eid) and not IvanTask.query.get(tid):
            _db.session.add(IvanTask(
                id=tid, equip_id=eid, title=t.get('title',''),
                due_date=t.get('dueDate',''), priority=t.get('priority','med'),
                status=t.get('status','upcoming'), notes=t.get('notes',''),
                auto_dot=t.get('autoDot', False)
            ))
            imported['tasks'] += 1
    for inv in d.get('invoices', []):
        iid = inv.get('id')
        eid = inv.get('equipId') or inv.get('equipmentId')
        if iid and eid and IvanEquipment.query.get(eid) and not IvanInvoice.query.get(iid):
            _db.session.add(IvanInvoice(
                id=iid, equip_id=eid, date=inv.get('date',''),
                vendor=inv.get('vendor',''), description=inv.get('description',''),
                amount=inv.get('amount', 0), invoice_number=inv.get('invoiceNumber',''),
                payment_method=inv.get('paymentMethod',''), payment_date=inv.get('paymentDate','')
            ))
            imported['invoices'] += 1
    _db.session.commit()
    return jsonify({'ok': True, 'imported': imported})


# ── Amazon DSP — Driver & Expense API ─────────────────────────────────────────

@app.route('/api/dsp/drivers', methods=['GET'])
@login_required
def dsp_drivers_list():
    from models import DspDriver
    drivers = DspDriver.query.order_by(DspDriver.name).all()
    return jsonify([d.to_dict() for d in drivers])


@app.route('/api/dsp/drivers', methods=['POST'])
@login_required
def dsp_driver_create():
    from models import DspDriver
    from extensions import db as _db
    d = request.get_json() or {}
    drv = DspDriver(
        name               = d.get('name', ''),
        driver_type        = d.get('driverType', 'company'),
        phone              = d.get('phone', ''),
        email              = d.get('email', ''),
        active             = bool(d.get('active', True)),
        notes              = d.get('notes', ''),
        default_payout_pct = float(d.get('defaultPayoutPct') or 0),
        fuel_card_holder   = bool(d.get('fuelCardHolder', False)),
    )
    _db.session.add(drv)
    _db.session.commit()
    return jsonify(drv.to_dict()), 201


@app.route('/api/dsp/drivers/<int:did>', methods=['PUT'])
@login_required
def dsp_driver_update(did):
    from models import DspDriver
    from extensions import db as _db
    drv = DspDriver.query.get_or_404(did)
    d = request.get_json() or {}
    if 'name'             in d: drv.name               = d['name']
    if 'driverType'       in d: drv.driver_type         = d['driverType']
    if 'phone'            in d: drv.phone               = d['phone']
    if 'email'            in d: drv.email               = d['email']
    if 'active'           in d: drv.active              = bool(d['active'])
    if 'notes'            in d: drv.notes               = d['notes']
    if 'defaultPayoutPct' in d: drv.default_payout_pct  = float(d['defaultPayoutPct'] or 0)
    if 'fuelCardHolder'   in d: drv.fuel_card_holder    = bool(d['fuelCardHolder'])
    _db.session.commit()
    return jsonify(drv.to_dict())


@app.route('/api/dsp/drivers/<int:did>', methods=['DELETE'])
@login_required
def dsp_driver_delete(did):
    from models import DspDriver
    from extensions import db as _db
    drv = DspDriver.query.get_or_404(did)
    _db.session.delete(drv)
    _db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/dsp/drivers/<int:did>/expense-defaults', methods=['GET'])
@login_required
def dsp_expense_defaults_list(did):
    from models import DriverExpenseDefault
    defs = DriverExpenseDefault.query.filter_by(driver_id=did).all()
    return jsonify([x.to_dict() for x in defs])


@app.route('/api/dsp/drivers/<int:did>/expense-defaults', methods=['POST'])
@login_required
def dsp_expense_default_create(did):
    from models import DspDriver, DriverExpenseDefault
    from extensions import db as _db
    DspDriver.query.get_or_404(did)
    d = request.get_json() or {}
    obj = DriverExpenseDefault(
        driver_id     = did,
        category      = d.get('category', 'deduction'),
        label         = d.get('label', ''),
        amount        = float(d.get('amount') or 0),
        is_percentage = bool(d.get('isPercentage', False)),
        active        = bool(d.get('active', True)),
    )
    _db.session.add(obj)
    _db.session.commit()
    return jsonify(obj.to_dict()), 201


@app.route('/api/dsp/drivers/<int:did>/expense-defaults/<int:eid>', methods=['PUT'])
@login_required
def dsp_expense_default_update(did, eid):
    from models import DriverExpenseDefault
    from extensions import db as _db
    obj = DriverExpenseDefault.query.filter_by(id=eid, driver_id=did).first_or_404()
    d = request.get_json() or {}
    if 'category'     in d: obj.category      = d['category']
    if 'label'        in d: obj.label         = d['label']
    if 'amount'       in d: obj.amount        = float(d['amount'] or 0)
    if 'isPercentage' in d: obj.is_percentage = bool(d['isPercentage'])
    if 'active'       in d: obj.active        = bool(d['active'])
    _db.session.commit()
    return jsonify(obj.to_dict())


@app.route('/api/dsp/drivers/<int:did>/expense-defaults/<int:eid>', methods=['DELETE'])
@login_required
def dsp_expense_default_delete(did, eid):
    from models import DriverExpenseDefault
    from extensions import db as _db
    obj = DriverExpenseDefault.query.filter_by(id=eid, driver_id=did).first_or_404()
    _db.session.delete(obj)
    _db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/dsp/expenses', methods=['GET'])
@login_required
def dsp_expenses_list():
    from models import DriverExpense
    q = DriverExpense.query
    driver_id  = request.args.get('driverId')
    week_start = request.args.get('weekStart')
    if driver_id:  q = q.filter_by(driver_id=int(driver_id))
    if week_start: q = q.filter_by(week_start=week_start)
    rows = q.order_by(DriverExpense.week_start.desc(), DriverExpense.driver_id).all()
    return jsonify([r.to_dict() for r in rows])


@app.route('/api/dsp/expenses', methods=['POST'])
@login_required
def dsp_expense_create():
    from models import DriverExpense
    from extensions import db as _db
    d = request.get_json() or {}
    ext_ref   = (d.get('externalReference') or '').strip()
    driver_id = int(d.get('driverId') or 0)
    week_start = d.get('weekStart', '')
    # Idempotent: skip if same external_reference already exists
    if ext_ref and DriverExpense.query.filter_by(
        driver_id=driver_id, week_start=week_start, external_reference=ext_ref
    ).first():
        existing = DriverExpense.query.filter_by(
            driver_id=driver_id, week_start=week_start, external_reference=ext_ref
        ).first()
        return jsonify(existing.to_dict())
    obj = DriverExpense(
        driver_id          = driver_id,
        week_start         = week_start,
        category           = d.get('category', 'deduction'),
        label              = d.get('label', ''),
        amount             = float(d.get('amount') or 0),
        notes              = d.get('notes', ''),
        external_reference = ext_ref,
        import_batch_id    = d.get('importBatchId'),
    )
    _db.session.add(obj)
    _db.session.commit()
    return jsonify(obj.to_dict()), 201


@app.route('/api/dsp/expenses/<int:eid>', methods=['PUT'])
@login_required
def dsp_expense_update(eid):
    from models import DriverExpense
    from extensions import db as _db
    obj = DriverExpense.query.get_or_404(eid)
    d = request.get_json() or {}
    if 'category'  in d: obj.category  = d['category']
    if 'label'     in d: obj.label     = d['label']
    if 'amount'    in d: obj.amount    = float(d['amount'] or 0)
    if 'notes'     in d: obj.notes     = d['notes']
    if 'weekStart' in d: obj.week_start = d['weekStart']
    _db.session.commit()
    return jsonify(obj.to_dict())


@app.route('/api/dsp/expenses/<int:eid>', methods=['DELETE'])
@login_required
def dsp_expense_delete(eid):
    from models import DriverExpense
    from extensions import db as _db
    obj = DriverExpense.query.get_or_404(eid)
    _db.session.delete(obj)
    _db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/dsp/summary', methods=['GET'])
@login_required
def dsp_summary():
    """Weekly aggregated view: AmazonTrip revenue + DriverExpense totals per driver."""
    from models import DspDriver, DriverExpense, AmazonTrip
    week_start = request.args.get('weekStart', '')

    drivers  = DspDriver.query.filter_by(active=True).order_by(DspDriver.name).all()

    trips_q = AmazonTrip.query
    if week_start:
        from datetime import date as _date, timedelta as _td
        try:
            sun = _date.fromisoformat(week_start)
            sat = sun + _td(days=6)
            trips_q = trips_q.filter(
                AmazonTrip.trip_date >= sun.isoformat(),
                AmazonTrip.trip_date <= sat.isoformat(),
            )
        except Exception:
            pass
    trips = trips_q.all()

    expenses_q = DriverExpense.query
    if week_start:
        expenses_q = expenses_q.filter_by(week_start=week_start)
    expenses = expenses_q.all()

    result = []
    for drv in drivers:
        drv_trips    = [t for t in trips    if t.driver    == drv.name]
        drv_expenses = [e for e in expenses if e.driver_id == drv.id]
        gross        = sum(t.gross_load_revenue or 0 for t in drv_trips)
        trip_revenue = sum(t.trip_revenue      or 0 for t in drv_trips)
        total_exp    = sum(e.amount            or 0 for e in drv_expenses)
        net_payout   = trip_revenue - total_exp
        result.append({
            'driver':      drv.to_dict(),
            'tripCount':   len(drv_trips),
            'gross':       round(gross,        2),
            'tripRevenue': round(trip_revenue, 2),
            'expenses':    round(total_exp,    2),
            'netPayout':   round(net_payout,   2),
        })

    # Unmatched trips (driver name not in dsp_drivers)
    known_names = {d['driver']['name'] for d in result}
    unmatched = {}
    for t in trips:
        if t.driver and t.driver not in known_names:
            if t.driver not in unmatched:
                unmatched[t.driver] = {'trips': 0, 'gross': 0.0, 'tripRevenue': 0.0}
            unmatched[t.driver]['trips']       += 1
            unmatched[t.driver]['gross']       += t.gross_load_revenue or 0
            unmatched[t.driver]['tripRevenue'] += t.trip_revenue       or 0

    return jsonify({
        'weekStart':       week_start,
        'drivers':         result,
        'unmatched':       unmatched,
        'totalGross':      round(sum(r['gross']       for r in result), 2),
        'totalExpenses':   round(sum(r['expenses']    for r in result), 2),
        'totalNetPayout':  round(sum(r['netPayout']   for r in result), 2),
    })


@app.route('/api/dsp/ingest/trips', methods=['POST'])
@csrf.exempt
@login_required
def dsp_ingest_trips():
    """Agent-facing endpoint: push AmazonTrip records with import batch tracking.
    Body: { trips: [...], source: 'discord', filename: '', createdBy: '' }
    Future: replace @login_required with API-key auth for Discord agents.
    """
    from models import ImportBatch
    from extensions import db as _db
    from models import upsert_amazon_trips
    d = request.get_json() or {}
    trips = d.get('trips', [])
    if not trips:
        return jsonify({'ok': True, 'imported': 0})
    batch = ImportBatch(
        source        = d.get('source', 'api'),
        filename      = d.get('filename', ''),
        created_by    = d.get('createdBy', ''),
        notes         = d.get('notes', ''),
        rows_imported = len(trips),
    )
    _db.session.add(batch)
    _db.session.flush()
    count = upsert_amazon_trips(trips)
    _db.session.commit()
    return jsonify({'ok': True, 'imported': count, 'batchId': batch.id})


@app.route('/api/dsp/ingest/fuel', methods=['POST'])
@csrf.exempt
@login_required
def dsp_ingest_fuel():
    """Agent-facing endpoint: push DriverExpense fuel records with dedup.
    Body: { expenses: [{driverId, weekStart, amount, label, externalReference}], ... }
    """
    from models import DriverExpense, ImportBatch
    from extensions import db as _db
    d = request.get_json() or {}
    raw = d.get('expenses', [])
    if not raw:
        return jsonify({'ok': True, 'imported': 0})
    batch = ImportBatch(
        source        = d.get('source', 'api'),
        filename      = d.get('filename', ''),
        created_by    = d.get('createdBy', ''),
        notes         = d.get('notes', ''),
        rows_imported = len(raw),
    )
    _db.session.add(batch)
    _db.session.flush()
    count = 0
    for e in raw:
        ext_ref    = (e.get('externalReference') or '').strip()
        driver_id  = int(e.get('driverId') or 0)
        week_start = e.get('weekStart', '')
        if ext_ref and DriverExpense.query.filter_by(
            driver_id=driver_id, week_start=week_start, external_reference=ext_ref
        ).first():
            continue
        _db.session.add(DriverExpense(
            driver_id=driver_id, week_start=week_start,
            category=e.get('category', 'fuel'),
            label=e.get('label', 'Fuel'),
            amount=float(e.get('amount') or 0),
            notes=e.get('notes', ''),
            external_reference=ext_ref,
            import_batch_id=batch.id,
        ))
        count += 1
    _db.session.commit()
    return jsonify({'ok': True, 'imported': count, 'batchId': batch.id})


@app.route('/api/dsp/import-batches', methods=['GET'])
@login_required
def dsp_import_batches():
    from models import ImportBatch
    limit = min(int(request.args.get('limit', 20)), 100)
    batches = ImportBatch.query.order_by(ImportBatch.created_at.desc()).limit(limit).all()
    return jsonify([b.to_dict() for b in batches])


# ── Trip Report API ───────────────────────────────────────────────────────────

@app.route('/api/report/trigger', methods=['POST'])
@csrf.exempt
@login_required
def trigger_report_job():
    """Manually trigger the weekly trip report job (for testing / on-demand sends).

    The reporting window is always a Sunday–Saturday Amazon week.

    Body (JSON, all optional):
        dry_run      bool  — generate PDFs but skip email + Discord (default false)
        week_ending  str   — Saturday YYYY-MM-DD; auto-computes Sunday start
                             e.g. "2026-04-11" → reports Apr 5–11
        week_start   str   — explicit Sunday YYYY-MM-DD (use with week_end)
        week_end     str   — explicit Saturday YYYY-MM-DD (use with week_start)
        (if none supplied, auto-resolves to most recently completed Sunday–Saturday week)

    Returns:
        202 with {status, windowStart, windowEnd, dryRun}
        503 if DATABASE_URL is not set
    """
    if not _DB_ENABLED:
        return jsonify({'error': 'DATABASE_URL is required to run report jobs.'}), 503

    import threading
    from automation.trip_report.job import _window_from_params

    data         = request.get_json(silent=True) or {}
    dry_run      = bool(data.get('dry_run', False))
    force_resend = bool(data.get('force_resend', False))
    week_ending  = data.get('week_ending') or None
    week_start   = data.get('week_start')  or None
    week_end     = data.get('week_end')    or None

    window_start, window_end = _window_from_params(week_ending, week_start, week_end)

    def _run():
        try:
            from automation.trip_report.job import WeeklyTripHistoryReportJob
            job = WeeklyTripHistoryReportJob(app=app)
            job.run(
                dry_run      = dry_run,
                week_start   = window_start,
                week_end     = window_end,
                force_resend = force_resend,
            )
        except Exception as exc:
            _log.error("Manual report trigger failed: %s", exc, exc_info=True)

    t = threading.Thread(target=_run, daemon=True, name='report-job-manual')
    t.start()

    return jsonify({
        'status':      'triggered',
        'windowStart': window_start,
        'windowEnd':   window_end,
        'dryRun':      dry_run,
    }), 202


@app.route('/api/relay/trigger', methods=['POST'])
@csrf.exempt
@login_required
def trigger_relay_fetch():
    """Manually trigger an Amazon Relay fetch (relay_cron) on demand.

    Runs fetch + ingest in a background thread and returns immediately.
    Populates relay_current_week so the report job uses the correct trip list.

    Returns 202 with {status, windowStart, windowEnd}.
    """
    if not _DB_ENABLED:
        return jsonify({'error': 'DATABASE_URL is required.'}), 503

    from datetime import date, timedelta
    today        = date.today()
    days_since   = today.isoweekday() % 7   # Sun=0 … Sat=6
    window_start = (today - timedelta(days=days_since)).isoformat()
    window_end   = today.isoformat()

    def _run():
        import asyncio
        try:
            from automation.amazon_relay.fetcher  import fetch_relay_csv
            from automation.amazon_relay.ingestor import ingest_relay_csv
            _log.info("Manual relay fetch started — window %s–%s", window_start, window_end)
            csv_path = asyncio.run(fetch_relay_csv(window_start=window_start, window_end=window_end))
            _log.info("Relay fetch complete: %s (%s bytes)", csv_path, csv_path.stat().st_size if csv_path.exists() else 0)
            result = ingest_relay_csv(csv_path)
            _log.info("Relay ingest complete: %s", result)
        except Exception as exc:
            _log.error("Manual relay fetch failed: %s", exc, exc_info=True)

    t = threading.Thread(target=_run, daemon=True, name='relay-fetch-manual')
    t.start()

    return jsonify({
        'status':      'triggered',
        'windowStart': window_start,
        'windowEnd':   window_end,
    }), 202


@app.route('/api/report/debug/trips', methods=['GET'])
@login_required
def debug_trip_data():
    """Return raw AmazonTrip DB rows for debugging the report pipeline.

    Query params:
        limit     — max rows (default 50)
        driver    — filter by driver name (case-insensitive substring)
        date_from — YYYY-MM-DD start filter on trip_date
        date_to   — YYYY-MM-DD end filter on trip_date
    """
    if not _DB_ENABLED:
        return jsonify({'error': 'DATABASE_URL not set'})
    from models import AmazonTrip
    limit     = min(int(request.args.get('limit', 50)), 200)
    driver_q  = request.args.get('driver', '').strip().lower()
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to', '').strip()

    q = AmazonTrip.query
    if date_from:
        q = q.filter(AmazonTrip.trip_date >= date_from)
    if date_to:
        q = q.filter(AmazonTrip.trip_date <= date_to)
    q = q.order_by(AmazonTrip.trip_date.desc()).limit(limit)
    rows = q.all()

    if driver_q:
        rows = [r for r in rows if driver_q in (r.driver or '').lower()]

    # Summarise distinct drivers in result
    drivers = sorted({r.driver for r in rows if r.driver})
    return jsonify({
        'total_rows': len(rows),
        'distinct_drivers': drivers,
        'trips': [r.to_dict() for r in rows],
    })


@app.route('/api/report/runs', methods=['GET'])
@login_required
def list_report_runs():
    """Return recent report job runs with per-driver status."""
    if not _DB_ENABLED:
        return jsonify([])
    from models import ReportJobRun
    limit = min(int(request.args.get('limit', 10)), 50)
    runs  = ReportJobRun.query.order_by(ReportJobRun.started_at.desc()).limit(limit).all()
    result = []
    for run in runs:
        d = run.to_dict()
        d['driverReports'] = [dr.to_dict() for dr in run.driver_reports]
        result.append(d)
    return jsonify(result)


# ── Dev server entry point ────────────────────────────────────────────────────
# Production: use gunicorn (see Procfile / .replit).
if __name__ == '__main__':
    # Start bots only here — not at import time — so Flask CLI commands and
    # gunicorn/wsgi.py don't accidentally spawn duplicate bot connections.
    threading.Thread(target=_start_discord_bot, daemon=True, name='discord-bot').start()
    threading.Thread(target=_start_telegram_bot, daemon=True, name='telegram-bot').start()
    # use_reloader=False: prevents Werkzeug from forking a child that would
    # re-enter this block and start a second set of bot threads.
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False,
    )
