"""
models.py — SQLAlchemy models for users, roles, and permissions.
"""
from datetime import datetime
from flask_login import UserMixin
from extensions import db

# ── Junction tables ────────────────────────────────────────────────────────────

user_roles = db.Table(
    'user_roles',
    db.Column('user_id',    db.Integer, db.ForeignKey('users.id'),  primary_key=True),
    db.Column('role_id',    db.Integer, db.ForeignKey('roles.id'),  primary_key=True)
)

role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id',       db.Integer, db.ForeignKey('roles.id'),       primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

# ── Role ──────────────────────────────────────────────────────────────────────

class Role(db.Model):
    __tablename__ = 'roles'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(50),  unique=True, nullable=False)
    description = db.Column(db.String(200))

    permissions = db.relationship('Permission', secondary=role_permissions,
                                  back_populates='roles',  lazy='subquery')
    users       = db.relationship('User',       secondary=user_roles,
                                  back_populates='roles',  lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

# ── Permission ────────────────────────────────────────────────────────────────

class Permission(db.Model):
    __tablename__ = 'permissions'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

    roles = db.relationship('Role', secondary=role_permissions,
                            back_populates='permissions', lazy='subquery')

    def __repr__(self):
        return f'<Permission {self.name}>'

# ── User ──────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name          = db.Column(db.String(100))
    is_active     = db.Column(db.Boolean, default=True,  nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    roles = db.relationship('Role', secondary=user_roles,
                            back_populates='users', lazy='subquery')

    # Flask-Login requires get_id()
    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return any(r.name == 'admin' for r in self.roles)

    def has_permission(self, perm_name: str) -> bool:
        """True if user has permission, or user is admin (which bypasses all checks)."""
        if self.is_admin:
            return True
        for role in self.roles:
            for perm in role.permissions:
                if perm.name == perm_name:
                    return True
        return False

    def permissions_for_frontend(self) -> dict:
        """
        Returns a dict consumed by dashboard.js to show/hide tabs.
        {
          is_admin: bool,
          companies: ['bcat', 'ivan', ...],   # companies this user can see
          tabs: { 'ivan': ['equipment', 'finance'], ... }  # per-company tab overrides
        }
        Admin users get everything. Non-admins get only what their role permissions grant.
        """
        if self.is_admin:
            return {
                'is_admin': True,
                'name': self.name or self.email,
                'email': self.email,
                'companies': ['bcat', 'ivan', 'bestcare', 'amazon', 'aiden', 'agents'],
                'tabs': {}
            }

        companies, tabs = [], {}
        for role in self.roles:
            for perm in role.permissions:
                if perm.name.startswith('view_company_'):
                    c = perm.name[len('view_company_'):]
                    if c not in companies:
                        companies.append(c)
                elif perm.name.startswith('view_tab_'):
                    rest  = perm.name[len('view_tab_'):]
                    parts = rest.split('_', 1)
                    if len(parts) == 2:
                        company, tab = parts
                        tabs.setdefault(company, [])
                        if tab not in tabs[company]:
                            tabs[company].append(tab)
        return {
            'is_admin': False,
            'name':     self.name or self.email,
            'email':    self.email,
            'companies': companies,
            'tabs':      tabs
        }

    @property
    def role_names(self):
        return [r.name for r in self.roles]

    def __repr__(self):
        return f'<User {self.email}>'
