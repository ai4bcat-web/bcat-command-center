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
    dot_inspection_date       = db.Column(db.String(20), default='')
    ifta_expiration_date      = db.Column(db.String(20), default='')
    irp_expiration_date       = db.Column(db.String(20), default='')
    assigned_driver_id        = db.Column(db.String(50), default='')
    insurance_expiration_date  = db.Column(db.String(20), default='')
    bobtail_insurance_date     = db.Column(db.String(20), default='')
    fleet_manager_assignee     = db.Column(db.String(50), default='')   # 'jason' | 'ryne' | ''
    on_tollway_account         = db.Column(db.Boolean,    default=False)
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
            'iftaExpirationDate': self.ifta_expiration_date or '',
            'irpExpirationDate': self.irp_expiration_date or '',
            'assignedDriverId': self.assigned_driver_id or '',
            'insuranceExpirationDate': self.insurance_expiration_date or '',
            'bobtailInsuranceDate': self.bobtail_insurance_date or '',
            'fleetManagerAssignee': self.fleet_manager_assignee or '',
            'onTollwayAccount': bool(self.on_tollway_account),
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
    assignee   = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'equipId': self.equip_id, 'title': self.title,
            'dueDate': self.due_date or '', 'priority': self.priority or 'med',
            'status': self.status or 'upcoming', 'notes': self.notes or '',
            'autoDot': self.auto_dot, 'assignee': self.assignee or '',
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
    assignee       = db.Column(db.String(100), default='')
    created_at     = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'equipId': self.equip_id,
            'date': self.date or '', 'vendor': self.vendor or '',
            'description': self.description or '', 'amount': self.amount or 0,
            'invoiceNumber': self.invoice_number or '',
            'paymentMethod': self.payment_method or '',
            'paymentDate': self.payment_date or '',
            'assignee': self.assignee or '',
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


class RelayCurrentWeek(db.Model):
    """Tracks exactly which trip IDs were in the most recent Amazon Relay weekly download.

    Cleared and repopulated by the relay_cron ingestor on every fetch.
    The report job queries this table instead of filtering by date, so the
    report always reflects exactly what Amazon exported for the current week.
    """
    __tablename__ = 'relay_current_week'

    trip_id    = db.Column(db.String(100), primary_key=True)
    fetched_at = db.Column(db.DateTime,    default=datetime.utcnow)


def set_current_week_trips(trip_ids: list[str]) -> int:
    """Replace the relay_current_week table with the given trip IDs.

    Call this inside a Flask app context immediately after fetching the
    current week's CSV from Amazon Relay.

    Returns the number of trip IDs stored.
    """
    db.session.query(RelayCurrentWeek).delete()
    now = datetime.utcnow()
    for tid in trip_ids:
        tid = (tid or '').strip()
        if tid:
            db.session.add(RelayCurrentWeek(trip_id=tid, fetched_at=now))
    db.session.commit()
    return len(trip_ids)


class IvanScheduleEntry(db.Model):
    """
    One dispatched load on one day in the weekly driver schedule board.
    week_start is always a Monday (YYYY-MM-DD).
    row_order controls display order within the day (0-based).
    Deadhead miles are calculated client-side and stored here for persistence.
    """
    __tablename__ = 'ivan_schedule_entries'

    id                     = db.Column(db.String(50),  primary_key=True)
    week_start             = db.Column(db.String(10),  nullable=False, index=True)  # YYYY-MM-DD Monday
    day_date               = db.Column(db.String(10),  nullable=False, index=True)  # YYYY-MM-DD
    row_order              = db.Column(db.Integer,     nullable=False, default=0)
    alexei_id              = db.Column(db.String(100), default='')   # PRO #
    tms_id                 = db.Column(db.String(100), default='')
    pu_number              = db.Column(db.String(100), default='')
    pu_appt                = db.Column(db.String(20),  default='')   # HH:MM
    de_appt                = db.Column(db.String(20),  default='')   # HH:MM
    pu_city                = db.Column(db.String(100), default='')
    pu_state               = db.Column(db.String(10),  default='')
    de_city                = db.Column(db.String(100), default='')
    de_state               = db.Column(db.String(10),  default='')
    notes                  = db.Column(db.Text,        default='')
    status                 = db.Column(db.String(50),  default='')
    # Deadhead breakdown (miles) — recalculated when row order or cities change
    start_deadhead_miles   = db.Column(db.Float, default=0.0)   # base terminal → pu_city
    between_deadhead_miles = db.Column(db.Float, default=0.0)   # prev de_city → pu_city
    return_deadhead_miles  = db.Column(db.Float, default=0.0)   # de_city → base terminal (last row only)
    total_deadhead_miles   = db.Column(db.Float, default=0.0)   # sum of all segments
    created_at             = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at             = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                   self.id,
            'weekStart':            self.week_start,
            'dayDate':              self.day_date,
            'rowOrder':             self.row_order,
            'alexeiId':             self.alexei_id or '',
            'tmsId':                self.tms_id or '',
            'puNumber':             self.pu_number or '',
            'puAppt':               self.pu_appt or '',
            'deAppt':               self.de_appt or '',
            'puCity':               self.pu_city or '',
            'puState':              self.pu_state or '',
            'deCity':               self.de_city or '',
            'deState':              self.de_state or '',
            'notes':                self.notes or '',
            'status':               self.status or '',
            'startDeadheadMiles':   self.start_deadhead_miles or 0,
            'betweenDeadheadMiles': self.between_deadhead_miles or 0,
            'returnDeadheadMiles':  self.return_deadhead_miles or 0,
            'totalDeadheadMiles':   self.total_deadhead_miles or 0,
            'createdAt':  self.created_at.isoformat() if self.created_at else '',
            'updatedAt':  self.updated_at.isoformat() if self.updated_at else '',
        }


class IvanLoad(db.Model):
    """Master shipment record. One load may have multiple driver assignments across days."""
    __tablename__ = 'ivan_loads'

    id         = db.Column(db.String(50),  primary_key=True)
    alexei_id  = db.Column(db.String(100), default='')   # PRO #
    tms_id     = db.Column(db.String(100), default='')
    pu_number  = db.Column(db.String(100), default='')
    pu_city    = db.Column(db.String(100), default='')
    pu_state   = db.Column(db.String(10),  default='')
    de_city    = db.Column(db.String(100), default='')
    de_state   = db.Column(db.String(10),  default='')
    pu_appt      = db.Column(db.String(20),  default='')
    de_appt      = db.Column(db.String(20),  default='')
    notes        = db.Column(db.Text,        default='')
    # Round 9 additions
    pick_count   = db.Column(db.Integer,     default=1)
    drop_count   = db.Column(db.Integer,     default=1)
    load_type    = db.Column(db.String(50),  default='')   # E2OPEN | BCAT BROKER | IVAN BROKER | IVAN CUSTOMER
    carrier_name = db.Column(db.String(200), default='')
    # Round 10 additions
    shipment_ref   = db.Column(db.String(20),  default='')   # Short human ref e.g. S-A1B2C
    shipment_color = db.Column(db.String(10),  default='')   # Hex color override for non-done cards
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = db.relationship('IvanScheduleAssignment', backref='load',
                                  lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':          self.id,
            'alexeiId':    self.alexei_id    or '',
            'tmsId':       self.tms_id       or '',
            'puNumber':    self.pu_number    or '',
            'puCity':      self.pu_city      or '',
            'puState':     self.pu_state     or '',
            'deCity':      self.de_city      or '',
            'deState':     self.de_state     or '',
            'puAppt':      self.pu_appt      or '',
            'deAppt':      self.de_appt      or '',
            'notes':       self.notes        or '',
            'pickCount':     self.pick_count     if self.pick_count   is not None else 1,
            'dropCount':     self.drop_count     if self.drop_count   is not None else 1,
            'loadType':      self.load_type      or '',
            'carrierName':   self.carrier_name   or '',
            'shipmentRef':   self.shipment_ref   or '',
            'shipmentColor': self.shipment_color or '',
            'createdAt':   self.created_at.isoformat() if self.created_at else '',
            'updatedAt':   self.updated_at.isoformat() if self.updated_at else '',
        }


class IvanScheduleAssignment(db.Model):
    """
    One driver/day action leg for a load.
    A single IvanLoad may have multiple assignments (e.g. Driver A picks up Mon,
    Driver B delivers Tue). sequenceNumber orders a driver's actions within a day.
    """
    __tablename__ = 'ivan_schedule_assignments'

    id               = db.Column(db.String(50),  primary_key=True)
    load_id          = db.Column(db.String(50),  db.ForeignKey('ivan_loads.id'), nullable=True)
    week_start       = db.Column(db.String(10),  nullable=False, index=True)
    date             = db.Column(db.String(10),  nullable=False, index=True)
    driver_name      = db.Column(db.String(100), default='')
    sequence_number  = db.Column(db.Integer,     default=1)
    # PICKUP | DELIVERY | PICKUP_AND_DELIVER | REPOSITION | OTHER
    action_type      = db.Column(db.String(50),  default='PICKUP')
    origin_city      = db.Column(db.String(100), default='')
    origin_state     = db.Column(db.String(10),  default='')
    dest_city        = db.Column(db.String(100), default='')
    dest_state       = db.Column(db.String(10),  default='')
    pu_appt          = db.Column(db.String(20),  default='')
    de_appt          = db.Column(db.String(20),  default='')
    notes            = db.Column(db.Text,        default='')
    # Workflow checkboxes — kept for DB compatibility; no longer used in UI
    dispatched           = db.Column(db.Boolean, default=False)
    picked_up            = db.Column(db.Boolean, default=False)
    delivered            = db.Column(db.Boolean, default=False)
    paperwork_received   = db.Column(db.Boolean, default=False)
    paperwork_reviewed   = db.Column(db.Boolean, default=False)
    invoicing_ready      = db.Column(db.Boolean, default=False)
    # Legacy single appt_status — kept for DB compat; superseded by pu/de split
    appt_status          = db.Column(db.String(20), default='NEED')
    # Pickup / delivery location names (e.g. "Walmart DC #6045")
    pu_location_name     = db.Column(db.String(200), default='')
    de_location_name     = db.Column(db.String(200), default='')
    # Driver's starting city/state for this day (overrides BASE for deadhead calc)
    driver_start_city    = db.Column(db.String(100), default='')
    driver_start_state   = db.Column(db.String(10),  default='')
    # Per-leg appointment status (NEED | REQUESTED | APPOINTED)
    pu_appt_status       = db.Column(db.String(20), default='NEED')
    de_appt_status       = db.Column(db.String(20), default='NEED')
    # Manual completion flag — set explicitly by the dispatcher
    is_complete          = db.Column(db.Boolean,  default=False)
    completed_at         = db.Column(db.DateTime, nullable=True)
    # Round 9 additions
    e2open_closed        = db.Column(db.Boolean,    default=False)
    pu_appt_type         = db.Column(db.String(10), default='APPT')  # APPT | FCFS
    pu_fcfs_start        = db.Column(db.String(20), default='')
    pu_fcfs_end          = db.Column(db.String(20), default='')
    de_appt_type         = db.Column(db.String(10), default='APPT')  # APPT | FCFS
    de_fcfs_start        = db.Column(db.String(20), default='')
    de_fcfs_end          = db.Column(db.String(20), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                self.id,
            'loadId':            self.load_id          or '',
            'weekStart':         self.week_start,
            'date':              self.date,
            'driverName':        self.driver_name       or '',
            'sequenceNumber':    self.sequence_number,
            'actionType':        self.action_type       or 'PICKUP',
            'originCity':        self.origin_city       or '',
            'originState':       self.origin_state      or '',
            'destCity':          self.dest_city         or '',
            'destState':         self.dest_state        or '',
            'puAppt':            self.pu_appt           or '',
            'deAppt':            self.de_appt           or '',
            'puLocationName':    self.pu_location_name  or '',
            'deLocationName':    self.de_location_name  or '',
            'driverStartCity':   self.driver_start_city or '',
            'driverStartState':  self.driver_start_state or '',
            'puApptStatus':      self.pu_appt_status    or 'NEED',
            'deApptStatus':      self.de_appt_status    or 'NEED',
            'notes':             self.notes             or '',
            'isComplete':        bool(self.is_complete),
            'completedAt':       self.completed_at.isoformat() if self.completed_at else '',
            # Round 9
            'e2openClosed':      bool(self.e2open_closed),
            'puApptType':        self.pu_appt_type  or 'APPT',
            'puFcfsStart':       self.pu_fcfs_start or '',
            'puFcfsEnd':         self.pu_fcfs_end   or '',
            'deApptType':        self.de_appt_type  or 'APPT',
            'deFcfsStart':       self.de_fcfs_start or '',
            'deFcfsEnd':         self.de_fcfs_end   or '',
            'load':              self.load.to_dict() if self.load else None,
            'createdAt': self.created_at.isoformat() if self.created_at else '',
            'updatedAt': self.updated_at.isoformat() if self.updated_at else '',
        }


class ScheduleAuditLog(db.Model):
    """Records every create/update/delete on assignments and loads, with full before/after snapshots."""
    __tablename__ = 'schedule_audit_logs'

    id          = db.Column(db.Integer,     primary_key=True)
    entity_type = db.Column(db.String(50),  nullable=False)   # 'assignment' | 'load'
    entity_id   = db.Column(db.String(50),  nullable=False)
    action      = db.Column(db.String(20),  nullable=False)   # 'create' | 'update' | 'delete' | 'revert'
    user_email  = db.Column(db.String(255), default='')
    user_name   = db.Column(db.String(100), default='')
    before_json = db.Column(db.Text,        default='{}')
    after_json  = db.Column(db.Text,        default='{}')
    summary     = db.Column(db.String(500), default='')
    reverted    = db.Column(db.Boolean,     default=False)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':         self.id,
            'entityType': self.entity_type,
            'entityId':   self.entity_id,
            'action':     self.action,
            'userEmail':  self.user_email  or '',
            'userName':   self.user_name   or '',
            'beforeJson': self.before_json or '{}',
            'afterJson':  self.after_json  or '{}',
            'summary':    self.summary     or '',
            'reverted':   bool(self.reverted),
            'createdAt':  self.created_at.isoformat() if self.created_at else '',
        }


class RelaySession(db.Model):
    """Stores Amazon Relay browser cookies for headless session reuse on Railway."""
    __tablename__ = 'relay_sessions'

    id           = db.Column(db.Integer,  primary_key=True)
    cookies_json = db.Column(db.Text,     default='[]')
    saved_at     = db.Column(db.DateTime, default=datetime.utcnow)
    last_status  = db.Column(db.String(50), default='')   # 'ok', 'captcha', 'login_failed'
    last_error   = db.Column(db.Text,     default='')


# ── Amazon DSP — Driver Expense System ────────────────────────────────────────

class ImportBatch(db.Model):
    """Audit trail for imported DSP data (Discord uploads, CSV, API ingest)."""
    __tablename__ = 'import_batches'

    id            = db.Column(db.Integer,     primary_key=True)
    source        = db.Column(db.String(50),  default='manual')   # 'discord'|'manual'|'api'
    filename      = db.Column(db.String(500), default='')
    rows_imported = db.Column(db.Integer,     default=0)
    created_by    = db.Column(db.String(200), default='')
    notes         = db.Column(db.Text,        default='')
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    expenses = db.relationship('DriverExpense', backref='import_batch', lazy='dynamic')

    def to_dict(self):
        return {
            'id':           self.id,
            'source':       self.source        or 'manual',
            'filename':     self.filename      or '',
            'rowsImported': self.rows_imported or 0,
            'createdBy':    self.created_by    or '',
            'notes':        self.notes         or '',
            'createdAt':    self.created_at.isoformat() if self.created_at else '',
        }


class DspDriver(db.Model):
    """Amazon DSP driver profile — separate from Ivan Cartage drivers."""
    __tablename__ = 'dsp_drivers'

    id                 = db.Column(db.Integer,     primary_key=True)
    name               = db.Column(db.String(200), nullable=False)
    driver_type        = db.Column(db.String(50),  default='company')   # 'company'|'owner_op'
    phone              = db.Column(db.String(50),  default='')
    email              = db.Column(db.String(255), default='')
    active             = db.Column(db.Boolean,     default=True)
    notes              = db.Column(db.Text,        default='')
    default_payout_pct = db.Column(db.Float,       default=0.0)   # owner op payout %
    fuel_card_holder   = db.Column(db.Boolean,     default=False)
    created_at         = db.Column(db.DateTime,    default=datetime.utcnow)

    expenses         = db.relationship('DriverExpense',        backref='driver', lazy='dynamic',
                                       cascade='all, delete-orphan')
    expense_defaults = db.relationship('DriverExpenseDefault', backref='driver', lazy='dynamic',
                                       cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':               self.id,
            'name':             self.name,
            'driverType':       self.driver_type        or 'company',
            'phone':            self.phone              or '',
            'email':            self.email              or '',
            'active':           bool(self.active),
            'notes':            self.notes              or '',
            'defaultPayoutPct': self.default_payout_pct or 0.0,
            'fuelCardHolder':   bool(self.fuel_card_holder),
            'createdAt':        self.created_at.isoformat() if self.created_at else '',
        }


class DriverExpenseDefault(db.Model):
    """Recurring expense template for a DSP driver — pre-fills expense entry."""
    __tablename__ = 'driver_expense_defaults'

    id            = db.Column(db.Integer,     primary_key=True)
    driver_id     = db.Column(db.Integer,     db.ForeignKey('dsp_drivers.id'), nullable=False)
    category      = db.Column(db.String(50),  default='deduction')
    label         = db.Column(db.String(200), nullable=False, default='')
    amount        = db.Column(db.Float,       default=0.0)
    is_percentage = db.Column(db.Boolean,     default=False)
    active        = db.Column(db.Boolean,     default=True)

    def to_dict(self):
        return {
            'id':           self.id,
            'driverId':     self.driver_id,
            'category':     self.category     or 'deduction',
            'label':        self.label        or '',
            'amount':       self.amount       or 0.0,
            'isPercentage': bool(self.is_percentage),
            'active':       bool(self.active),
        }


class DriverExpense(db.Model):
    """Per-week expense entry for a DSP driver."""
    __tablename__ = 'driver_expenses'

    id                 = db.Column(db.Integer,     primary_key=True)
    driver_id          = db.Column(db.Integer,     db.ForeignKey('dsp_drivers.id'), nullable=False)
    week_start         = db.Column(db.String(10),  nullable=False, index=True)   # YYYY-MM-DD Sunday
    category           = db.Column(db.String(50),  default='deduction')
    label              = db.Column(db.String(200), default='')
    amount             = db.Column(db.Float,       default=0.0)
    notes              = db.Column(db.Text,        default='')
    external_reference = db.Column(db.String(200), default='')   # dedup key for agent ingest
    import_batch_id    = db.Column(db.Integer,     db.ForeignKey('import_batches.id'), nullable=True)
    created_at         = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                self.id,
            'driverId':          self.driver_id,
            'weekStart':         self.week_start,
            'category':          self.category           or 'deduction',
            'label':             self.label              or '',
            'amount':            self.amount             or 0.0,
            'notes':             self.notes              or '',
            'externalReference': self.external_reference or '',
            'importBatchId':     self.import_batch_id,
            'createdAt':         self.created_at.isoformat() if self.created_at else '',
        }


# ── Trip Report Automation ─────────────────────────────────────────────────────

class ReportJobRun(db.Model):
    """Audit record for each daily trip-report job execution."""
    __tablename__ = 'report_job_runs'

    id            = db.Column(db.Integer,    primary_key=True)
    job_type      = db.Column(db.String(50), default='daily_trip_report')
    report_date   = db.Column(db.String(10), nullable=False, index=True)   # YYYY-MM-DD (calendar date the job ran)
    window_start  = db.Column(db.String(10), default='')                   # YYYY-MM-DD first day of reporting window
    window_end    = db.Column(db.String(10), default='')                   # YYYY-MM-DD last day of reporting window
    status        = db.Column(db.String(20), default='running')            # running | completed | failed
    started_at    = db.Column(db.DateTime,   default=datetime.utcnow)
    completed_at  = db.Column(db.DateTime,   nullable=True)
    error         = db.Column(db.Text,       default='')
    summary       = db.Column(db.Text,       default='')
    total_trips   = db.Column(db.Integer,    default=0)
    total_revenue = db.Column(db.Float,      default=0.0)
    driver_count  = db.Column(db.Integer,    default=0)
    dry_run       = db.Column(db.Boolean,    default=False)

    driver_reports = db.relationship(
        'DriverReportRun', backref='job_run',
        lazy='dynamic', cascade='all, delete-orphan',
    )

    def to_dict(self):
        return {
            'id':           self.id,
            'jobType':      self.job_type,
            'reportDate':   self.report_date,
            'windowStart':  self.window_start,
            'windowEnd':    self.window_end,
            'status':       self.status,
            'startedAt':    self.started_at.isoformat()   if self.started_at   else '',
            'completedAt':  self.completed_at.isoformat() if self.completed_at else '',
            'error':        self.error        or '',
            'summary':      self.summary      or '',
            'totalTrips':   self.total_trips,
            'totalRevenue': self.total_revenue,
            'driverCount':  self.driver_count,
            'dryRun':       self.dry_run,
        }


class DriverReportRun(db.Model):
    """Per-driver report status within a job run — tracks PDF, email, Discord."""
    __tablename__ = 'driver_report_runs'

    id              = db.Column(db.Integer,    primary_key=True)
    job_run_id      = db.Column(db.Integer,    db.ForeignKey('report_job_runs.id'), nullable=False)
    driver_name     = db.Column(db.String(200), nullable=False)
    driver_type     = db.Column(db.String(50),  default='company')   # company | owner_op
    report_date     = db.Column(db.String(10),  nullable=False, index=True)  # YYYY-MM-DD
    window_start    = db.Column(db.String(10),  default='')
    window_end      = db.Column(db.String(10),  default='')
    trip_count      = db.Column(db.Integer,     default=0)
    total_revenue   = db.Column(db.Float,       default=0.0)
    pdf_path        = db.Column(db.String(500), default='')
    email_status    = db.Column(db.String(20),  default='pending')   # pending | sent | failed | skipped
    email_error     = db.Column(db.Text,        default='')
    email_sent_at   = db.Column(db.DateTime,    nullable=True)
    discord_status  = db.Column(db.String(20),  default='pending')   # pending | sent | failed | skipped
    discord_error   = db.Column(db.Text,        default='')
    discord_sent_at = db.Column(db.DateTime,    nullable=True)
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('job_run_id', 'driver_name', name='uq_driver_report_per_run'),
    )

    def to_dict(self):
        return {
            'id':             self.id,
            'jobRunId':       self.job_run_id,
            'driverName':     self.driver_name,
            'driverType':     self.driver_type,
            'reportDate':     self.report_date,
            'windowStart':    self.window_start,
            'windowEnd':      self.window_end,
            'tripCount':      self.trip_count,
            'totalRevenue':   self.total_revenue,
            'pdfPath':        self.pdf_path       or '',
            'emailStatus':    self.email_status,
            'emailError':     self.email_error    or '',
            'emailSentAt':    self.email_sent_at.isoformat()   if self.email_sent_at   else '',
            'discordStatus':  self.discord_status,
            'discordError':   self.discord_error  or '',
            'discordSentAt':  self.discord_sent_at.isoformat() if self.discord_sent_at else '',
            'createdAt':      self.created_at.isoformat()      if self.created_at      else '',
        }
