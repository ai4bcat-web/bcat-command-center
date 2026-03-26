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


# ── Ivan Cartage Equipment Models ─────────────────────────────────────────────

class IvanEquipment(db.Model):
    __tablename__ = 'ivan_equipment'
    id            = db.Column(db.String(50),  primary_key=True)
    type          = db.Column(db.String(20),  nullable=False)  # 'truck' | 'trailer'
    unit_number   = db.Column(db.String(50),  nullable=False)
    nickname      = db.Column(db.String(100), default='')
    vin           = db.Column(db.String(100), default='')
    plate         = db.Column(db.String(50),  default='')
    make          = db.Column(db.String(100), default='')
    model         = db.Column(db.String(100), default='')
    year          = db.Column(db.Integer,     nullable=True)
    mileage       = db.Column(db.Integer,     nullable=True)
    ownership     = db.Column(db.String(50),  default='owned')
    insured       = db.Column(db.Boolean,     default=True)
    dot_inspection_date = db.Column(db.String(20), default='')
    active        = db.Column(db.Boolean,     default=True)
    notes         = db.Column(db.Text,        default='')
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    tasks    = db.relationship('IvanTask',    backref='equipment', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('IvanInvoice', backref='equipment', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'type': self.type, 'unitNumber': self.unit_number,
            'nickname': self.nickname or '', 'vin': self.vin or '',
            'plate': self.plate or '', 'make': self.make or '',
            'model': self.model or '', 'year': self.year, 'mileage': self.mileage,
            'ownership': self.ownership or 'owned', 'insured': self.insured,
            'dotInspectionDate': self.dot_inspection_date or '',
            'active': self.active, 'notes': self.notes or '',
            'createdAt': self.created_at.isoformat() if self.created_at else ''
        }

class IvanTask(db.Model):
    __tablename__ = 'ivan_tasks'
    id         = db.Column(db.String(50),  primary_key=True)
    equip_id   = db.Column(db.String(50),  db.ForeignKey('ivan_equipment.id'), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    due_date   = db.Column(db.String(20),  default='')
    priority   = db.Column(db.String(20),  default='med')   # 'high' | 'med' | 'low'
    status     = db.Column(db.String(20),  default='upcoming')  # 'upcoming' | 'complete'
    notes      = db.Column(db.Text,        default='')
    auto_dot   = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'equipId': self.equip_id, 'title': self.title,
            'dueDate': self.due_date or '', 'priority': self.priority or 'med',
            'status': self.status or 'upcoming', 'notes': self.notes or '',
            'autoDot': self.auto_dot,
            'createdAt': self.created_at.isoformat() if self.created_at else ''
        }

class IvanInvoice(db.Model):
    __tablename__ = 'ivan_invoices'
    id             = db.Column(db.String(50),  primary_key=True)
    equip_id       = db.Column(db.String(50),  db.ForeignKey('ivan_equipment.id'), nullable=False)
    date           = db.Column(db.String(20),  default='')
    vendor         = db.Column(db.String(200), default='')
    description    = db.Column(db.Text,        default='')
    amount         = db.Column(db.Float,       default=0.0)
    invoice_number = db.Column(db.String(100), default='')
    payment_method = db.Column(db.String(100), default='')
    payment_date   = db.Column(db.String(20),  default='')
    created_at     = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'equipId': self.equip_id,
            'date': self.date or '', 'vendor': self.vendor or '',
            'description': self.description or '', 'amount': self.amount or 0,
            'invoiceNumber': self.invoice_number or '',
            'paymentMethod': self.payment_method or '',
            'paymentDate': self.payment_date or '',
            'createdAt': self.created_at.isoformat() if self.created_at else ''
        }


class AmazonTrip(db.Model):
    """Persistent store for Amazon Relay trip rows uploaded via Discord."""
    __tablename__ = 'amazon_trips'

    id                  = db.Column(db.Integer,     primary_key=True)
    trip_id             = db.Column(db.String(100), unique=True, nullable=True)
    trip_date           = db.Column(db.String(20),  default='')
    driver              = db.Column(db.String(200), default='')
    driver_type         = db.Column(db.String(50),  default='company')
    gross_load_revenue  = db.Column(db.Float,       default=0.0)
    deductions          = db.Column(db.Float,       default=0.0)
    company_percentage  = db.Column(db.Float,       default=0.0)
    bcat_revenue        = db.Column(db.Float,       default=0.0)
    trip_revenue        = db.Column(db.Float,       default=0.0)
    route               = db.Column(db.String(100), default='')
    stops               = db.Column(db.Integer,     nullable=True)
    status              = db.Column(db.String(100), default='')
    uploaded_at         = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'trip_id':            self.trip_id,
            'trip_date':          self.trip_date,
            'driver':             self.driver,
            'driver_type':        self.driver_type,
            'gross_load_revenue': self.gross_load_revenue,
            'deductions':         self.deductions,
            'company_percentage': self.company_percentage,
            'bcat_revenue':       self.bcat_revenue,
            'trip_revenue':       self.trip_revenue,
            'route':              self.route,
            'stops':              self.stops,
            'status':             self.status,
        }


def upsert_amazon_trips(trips: list) -> int:
    """
    Save a list of trip dicts to the database, upserting by trip_id.
    Returns the number of rows inserted/updated.
    Call this inside a Flask app context.
    """
    count = 0
    for t in trips:
        tid = (t.get('trip_id') or '').strip() or None
        if tid:
            row = AmazonTrip.query.filter_by(trip_id=tid).first()
        else:
            row = None

        if row is None:
            row = AmazonTrip(trip_id=tid)
            db.session.add(row)

        row.trip_date          = t.get('trip_date')          or ''
        row.driver             = t.get('driver')             or ''
        row.driver_type        = t.get('driver_type')        or 'company'
        row.gross_load_revenue = float(t.get('gross_load_revenue') or 0)
        row.deductions         = float(t.get('deductions')         or 0)
        row.company_percentage = float(t.get('company_percentage') or 0)
        row.bcat_revenue       = float(t.get('bcat_revenue')       or 0)
        row.trip_revenue       = float(t.get('trip_revenue')       or t.get('gross_load_revenue') or 0)
        row.route              = t.get('route')  or ''
        row.stops              = t.get('stops')
        row.status             = t.get('status') or ''
        count += 1

    db.session.commit()
    return count
