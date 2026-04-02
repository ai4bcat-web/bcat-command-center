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
    """Seed sample schedule data for the current week so the dispatch board renders immediately."""
    from datetime import date, timedelta
    from models import IvanScheduleEntry
    from extensions import db as _db

    # Find Monday of current week
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_str = monday.isoformat()

    # Delete any existing seed data for this week to allow re-seeding
    existing = IvanScheduleEntry.query.filter_by(week_start=week_str).all()
    for e in existing:
        _db.session.delete(e)
    _db.session.commit()

    def make(day_offset, row_order, entry_id, alexei_id, tms_id, pu_num,
             pu_appt, de_appt, pu_city, pu_state, de_city, de_state,
             notes, status, start_dh, between_dh, return_dh):
        day = (monday + timedelta(days=day_offset)).isoformat()
        return IvanScheduleEntry(
            id=entry_id, week_start=week_str, day_date=day, row_order=row_order,
            alexei_id=alexei_id, tms_id=tms_id, pu_number=pu_num,
            pu_appt=pu_appt, de_appt=de_appt,
            pu_city=pu_city, pu_state=pu_state,
            de_city=de_city, de_state=de_state,
            notes=notes, status=status,
            start_deadhead_miles=start_dh,
            between_deadhead_miles=between_dh,
            return_deadhead_miles=return_dh,
            total_deadhead_miles=start_dh + return_dh,
        )

    entries = [
        # Monday — 3 loads
        make(0,0,'seed-mon-1','PRO-10421','TMS-8801','PU-4421','07:00','11:30',
             'Chicago','IL','Racine','WI','Reefer — keep at 34°F','delivered',47,0,25),
        make(0,1,'seed-mon-2','PRO-10422','TMS-8802','PU-4422','13:00','17:00',
             'Kenosha','WI','Milwaukee','WI','','dispatched',18,0,22),
        make(0,2,'seed-mon-3','PRO-10423','TMS-8803','PU-4423','19:00','23:00',
             'Waukegan','IL','Joliet','IL','Drop and hook','pending',15,0,72),

        # Tuesday — 2 loads
        make(1,0,'seed-tue-1','PRO-10431','TMS-8811','PU-4431','06:30','10:00',
             'Chicago Heights','IL','Rockford','IL','','dispatched',55,0,105),
        make(1,1,'seed-tue-2','PRO-10432','TMS-8812','PU-4432','14:00','19:00',
             'Elgin','IL','Gary','IN','Flatbed — secure properly','pending',90,0,85),

        # Wednesday — 2 loads
        make(2,0,'seed-wed-1','PRO-10441','TMS-8821','PU-4441','08:00','13:00',
             'Joliet','IL','Indianapolis','IN','','pending',78,0,180),
        make(2,1,'seed-wed-2','PRO-10442','TMS-8822','PU-4442','15:00','20:00',
             'Aurora','IL','Champaign','IL','Liftgate required','pending',62,0,148),

        # Thursday — 1 load
        make(3,0,'seed-thu-1','PRO-10451','TMS-8831','PU-4451','07:00','12:00',
             'Milwaukee','WI','Detroit','MI','','pending',22,0,290),

        # Friday — 1 load
        make(4,0,'seed-fri-1','PRO-10461','TMS-8841','PU-4461','09:00','14:00',
             'Chicago','IL','St Louis','MO','','pending',47,0,310),
    ]

    for e in entries:
        _db.session.add(e)
    _db.session.commit()
    click.echo(f'Seeded {len(entries)} schedule entries for week of {week_str}.')
