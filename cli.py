"""
cli.py — Flask CLI commands for user and database management.
Register with: app.cli.add_command(...)  (done in dashboard.py)

Usage:
  flask create-admin           # seed first admin from env vars
  flask create-user            # interactive user creation
  flask list-users             # print all users
  flask reset-password <email> # set a new password
"""
import click
from flask.cli import with_appcontext
from extensions import db, bcrypt
from models import User, Role, Permission


# ── Seed default roles and permissions ────────────────────────────────────────

COMPANIES = ['bcat', 'ivan', 'bestcare', 'amazon', 'aiden', 'agents']
TABS = {
    'bcat':     ['finance', 'marketing', 'sales'],
    'ivan':     ['finance', 'equipment', 'drivers', 'dispatch'],
    'bestcare': ['finance', 'marketing', 'sales'],
}

def _seed_roles_and_permissions():
    """Idempotently create all roles and permissions."""
    # Build permission name list
    perm_names = []
    for c in COMPANIES:
        perm_names.append(f'view_company_{c}')
    for company, tabs in TABS.items():
        for tab in tabs:
            perm_names.append(f'view_tab_{company}_{tab}')
    perm_names += ['manage_users', 'upload_csv', 'edit_data']

    # Upsert permissions
    perms = {}
    for name in perm_names:
        p = Permission.query.filter_by(name=name).first()
        if not p:
            p = Permission(name=name)
            db.session.add(p)
        perms[name] = p
    db.session.flush()

    # Upsert roles
    def get_or_create_role(name, description):
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=description)
            db.session.add(r)
        return r

    admin_role = get_or_create_role('admin', 'Full access — all companies, all actions, user management')
    analyst_role = get_or_create_role('analyst', 'Read + upload access to all companies')
    viewer_role = get_or_create_role('viewer', 'Read-only access to all companies')
    ivan_manager_role = get_or_create_role('ivan_manager', 'Full access to Ivan Cartage only')
    amazon_operator_role = get_or_create_role('amazon_operator', 'Access to Amazon DSP only')
    ivan_equipment_role  = get_or_create_role('ivan_equipment',  'Ivan Cartage — equipment tab only')
    db.session.flush()

    # Admin: all permissions
    admin_role.permissions = list(perms.values())

    # Analyst: view all companies + tabs + upload
    analyst_perms = [p for k, p in perms.items()
                     if k.startswith('view_') or k == 'upload_csv']
    analyst_role.permissions = analyst_perms

    # Viewer: view all companies + tabs (no upload/edit)
    viewer_perms = [p for k, p in perms.items() if k.startswith('view_')]
    viewer_role.permissions = viewer_perms

    # Ivan manager: ivan company + all ivan tabs + upload/edit
    ivan_perms = [p for k, p in perms.items()
                  if 'ivan' in k or k == 'upload_csv' or k == 'edit_data']
    ivan_manager_role.permissions = ivan_perms

    # Amazon operator: amazon only
    amazon_perms = [p for k, p in perms.items()
                    if 'amazon' in k or k == 'upload_csv']
    amazon_operator_role.permissions = amazon_perms

    # Ivan equipment: ivan company + equipment tab only (read-only)
    ivan_equipment_role.permissions = [
        p for k, p in perms.items()
        if k in ('view_company_ivan', 'view_tab_ivan_equipment')
    ]

    db.session.commit()
    return {r.name: r for r in [admin_role, analyst_role, viewer_role,
                                  ivan_manager_role, amazon_operator_role,
                                  ivan_equipment_role]}


@click.command('create-admin')
@with_appcontext
def create_admin():
    """Seed the first admin user from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD env vars."""
    import config

    email    = (config.SEED_ADMIN_EMAIL    or '').strip()
    password = (config.SEED_ADMIN_PASSWORD or '').strip()
    name     = (config.SEED_ADMIN_NAME     or 'Admin').strip()

    if not email or not password:
        click.echo('ERROR: Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD in your environment.', err=True)
        raise SystemExit(1)

    db.create_all()
    roles = _seed_roles_and_permissions()

    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f'User {email} already exists — skipping creation.')
        if 'admin' not in existing.role_names:
            existing.roles.append(roles['admin'])
            db.session.commit()
            click.echo('Assigned admin role to existing user.')
        return

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=pw_hash, name=name, is_active=True)
    user.roles.append(roles['admin'])
    db.session.add(user)
    db.session.commit()
    click.echo(f'Admin user created: {email}')


@click.command('seed-roles')
@with_appcontext
def seed_roles():
    """Create/update all default roles and permissions (idempotent)."""
    db.create_all()
    roles = _seed_roles_and_permissions()
    click.echo('Roles and permissions seeded:')
    for name, role in roles.items():
        click.echo(f'  {name}: {len(role.permissions)} permissions')


@click.command('create-user')
@click.argument('email')
@click.argument('password')
@click.option('--name', default='', help='Display name')
@click.option('--role', default='viewer', help='Role name (admin/analyst/viewer/ivan_manager/amazon_operator)')
@with_appcontext
def create_user(email, password, name, role):
    """Create a new user.  flask create-user email@example.com password123 --role analyst"""
    roles = _seed_roles_and_permissions()
    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f'User {email} already exists.', err=True)
        raise SystemExit(1)

    assigned_role = roles.get(role)
    if not assigned_role:
        click.echo(f'Unknown role: {role}. Choose from: {", ".join(roles.keys())}', err=True)
        raise SystemExit(1)

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=pw_hash,
                name=name or email.split('@')[0], is_active=True)
    user.roles.append(assigned_role)
    db.session.add(user)
    db.session.commit()
    click.echo(f'User created: {email} (role: {role})')


@click.command('list-users')
@with_appcontext
def list_users():
    """List all users."""
    users = User.query.order_by(User.created_at).all()
    if not users:
        click.echo('No users found.')
        return
    click.echo(f'{"ID":<5} {"Email":<35} {"Name":<20} {"Roles":<25} {"Active":<8} {"Last Login"}')
    click.echo('-' * 100)
    for u in users:
        last = u.last_login_at.strftime('%Y-%m-%d %H:%M') if u.last_login_at else 'never'
        click.echo(f'{u.id:<5} {u.email:<35} {(u.name or ""):<20} {",".join(u.role_names):<25} {str(u.is_active):<8} {last}')


@click.command('reset-password')
@click.argument('email')
@click.argument('new_password')
@with_appcontext
def reset_password(email, new_password):
    """Reset a user password.  flask reset-password user@example.com newpass123"""
    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f'User {email} not found.', err=True)
        raise SystemExit(1)
    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    click.echo(f'Password updated for {email}')


@click.command('seed-schedule')
@with_appcontext
def seed_schedule():
    """Seed multi-driver dispatch sample data for the current week."""
    from datetime import date, timedelta
    from models import IvanLoad, IvanScheduleAssignment
    from extensions import db as _db

    db.create_all()

    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    week   = monday.isoformat()
    def day(n): return (monday + timedelta(days=n)).isoformat()

    # Wipe previous seed data
    IvanScheduleAssignment.query.filter(
        IvanScheduleAssignment.id.like('asgn-seed-%')).delete(synchronize_session=False)
    IvanLoad.query.filter(
        IvanLoad.id.like('load-seed-%')).delete(synchronize_session=False)
    _db.session.commit()

    def load(lid, pro, tms, pu_num, pu_city, pu_st, de_city, de_st,
             pu_appt='', de_appt='', notes=''):
        return IvanLoad(id=lid, alexei_id=pro, tms_id=tms, pu_number=pu_num,
                        pu_city=pu_city, pu_state=pu_st,
                        de_city=de_city, de_state=de_st,
                        pu_appt=pu_appt, de_appt=de_appt, notes=notes)

    def asgn(aid, ld, date_str, driver, seq, action,
             orig_city, orig_st, dest_city, dest_st,
             pu_appt='', de_appt='', notes='',
             disp=False, pu=False, de=False, pw_r=False, pw_w=False, inv=False):
        return IvanScheduleAssignment(
            id=aid, load_id=ld.id, week_start=week, date=date_str,
            driver_name=driver, sequence_number=seq, action_type=action,
            origin_city=orig_city, origin_state=orig_st,
            dest_city=dest_city,  dest_state=dest_st,
            pu_appt=pu_appt, de_appt=de_appt, notes=notes,
            dispatched=disp, picked_up=pu, delivered=de,
            paperwork_received=pw_r, paperwork_reviewed=pw_w, invoicing_ready=inv)

    # ── Loads ──────────────────────────────────────────────────────────────────
    # L1: Chicago → Milwaukee  (Alexei, Mon, P&D — FULLY COMPLETE)
    L1 = load('load-seed-001','PRO-10421','TMS-8801','PU-4421',
               'Chicago','IL','Milwaukee','WI','07:00','11:30','Reefer 34°F')
    # L2: Kenosha → Rockford  (SPLIT — Alexei picks up Mon, Ivan delivers Tue)
    L2 = load('load-seed-002','PRO-10422','TMS-8802','PU-4422',
               'Kenosha','WI','Rockford','IL','13:00','09:00')
    # L3: Chicago → Detroit   (Ivan, Mon, P&D, partial progress)
    L3 = load('load-seed-003','PRO-10423','TMS-8803','PU-4423',
               'Chicago','IL','Detroit','MI','09:00','17:00','Team driver preferred')
    # L4: Waukegan → Milwaukee (Alexei, Tue)
    L4 = load('load-seed-004','PRO-10431','TMS-8811','PU-4431',
               'Waukegan','IL','Milwaukee','WI','06:30','10:00')
    # L5: Empty reposition (Alexei Tue seq 2 — no load reference, Milwaukee back to Chicago)
    L5 = load('load-seed-005','','','','Milwaukee','WI','Chicago','IL')
    # L6: Joliet → Indianapolis (Alexei, Wed)
    L6 = load('load-seed-006','PRO-10441','TMS-8821','PU-4441',
               'Joliet','IL','Indianapolis','IN','08:00','14:00')

    for l in [L1,L2,L3,L4,L5,L6]:
        _db.session.add(l)
    _db.session.flush()

    # ── Assignments ────────────────────────────────────────────────────────────
    assignments = [
        # MONDAY
        # Alexei seq 1 — PICKUP_AND_DELIVER L1 (FULLY COMPLETE → green row)
        asgn('asgn-seed-001', L1, day(0), 'Alexei', 1, 'PICKUP_AND_DELIVER',
             'Chicago','IL','Milwaukee','WI','07:00','11:30','Reefer 34°F',
             disp=True, pu=True, de=True, pw_r=True, pw_w=True, inv=True),
        # Alexei seq 2 — PICKUP L2, staged at yard overnight
        asgn('asgn-seed-002', L2, day(0), 'Alexei', 2, 'PICKUP',
             'Kenosha','WI','Pleasant Prairie','WI','13:00','',
             'Staging at yard overnight', disp=True, pu=True),
        # Ivan seq 1 — PICKUP_AND_DELIVER L3 (dispatched only)
        asgn('asgn-seed-003', L3, day(0), 'Ivan', 1, 'PICKUP_AND_DELIVER',
             'Chicago','IL','Detroit','MI','09:00','17:00',
             'Team driver preferred', disp=True),

        # TUESDAY
        # Ivan seq 1 — DELIVERY L2 (continuation of Alexei's Monday pickup)
        asgn('asgn-seed-004', L2, day(1), 'Ivan', 1, 'DELIVERY',
             'Pleasant Prairie','WI','Rockford','IL','','09:00'),
        # Alexei seq 1 — PICKUP_AND_DELIVER L4
        asgn('asgn-seed-005', L4, day(1), 'Alexei', 1, 'PICKUP_AND_DELIVER',
             'Waukegan','IL','Milwaukee','WI','06:30','10:00', disp=True),
        # Alexei seq 2 — REPOSITION back to Chicago (empty move)
        asgn('asgn-seed-006', L5, day(1), 'Alexei', 2, 'REPOSITION',
             'Milwaukee','WI','Chicago','IL'),

        # WEDNESDAY
        # Alexei seq 1 — PICKUP L6
        asgn('asgn-seed-007', L6, day(2), 'Alexei', 1, 'PICKUP',
             'Joliet','IL','Indianapolis','IN','08:00','14:00'),
    ]

    for a in assignments:
        _db.session.add(a)
    _db.session.commit()

    click.echo(f'Seeded {len(assignments)} assignments across 6 loads for week of {week}.')
    click.echo('  ✓ Green row: PRO-10421 (Alexei Mon, fully complete)')
    click.echo('  ✓ Split load: PRO-10422 (Alexei picks up Mon → Ivan delivers Tue)')
    click.echo('  ✓ Multi-move day: Alexei Tue has P&D + Reposition')
    click.echo('  ✓ Partial progress: PRO-10423 (Ivan Mon, dispatched only)')
