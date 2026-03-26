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
    'ivan':     ['finance', 'equipment', 'drivers'],
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

    # Ivan manager: ivan company + tabs
    ivan_perms = [p for k, p in perms.items()
                  if 'ivan' in k or k == 'upload_csv' or k == 'edit_data']
    ivan_manager_role.permissions = ivan_perms

    # Amazon operator: amazon only
    amazon_perms = [p for k, p in perms.items()
                    if 'amazon' in k or k == 'upload_csv']
    amazon_operator_role.permissions = amazon_perms

    db.session.commit()
    return {r.name: r for r in [admin_role, analyst_role, viewer_role,
                                  ivan_manager_role, amazon_operator_role]}


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
